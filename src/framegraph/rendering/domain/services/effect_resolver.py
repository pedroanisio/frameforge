"""EffectResolver — normalises an object's `shadow` / `glow` field to params.

Ported from the legacy renderer's effect machinery and adapted to the v2 model,
where `shadow`/`glow` are `Effect = bool | str | EffectObject` (models L406;
grammar L832). The resolver maps:

  * None / False / "none" / ""  → no effect (None)
  * True                        → the default (medium) preset for that kind
  * a preset name (str)         → small / medium / large; any other non-empty
                                  string falls back to medium (tolerant proxy)
  * EffectObject (dict)         → the medium preset overridden by the provided
                                  color / blur / dx / dy / opacity

Colour is resolved here (via the injected ColorResolver) to a solid value, so
the painter stays free of token knowledge. The `<filter>` SVG itself is built by
the painter; this is the pure, backend-agnostic policy half.
"""
from __future__ import annotations

import re

# A CSS colour written as a function — rgb()/rgba()/hsl()/hsla() — kept intact
# while tokenising a shadow string, since it contains internal commas/spaces.
_FUNC_COLOR_RE = re.compile(r"(?:rgba?|hsla?)\([^)]*\)", re.IGNORECASE)
_NUMBER_RE = re.compile(r"^[+-]?\d*\.?\d+")

# Presets carried over from the legacy renderer (sensible drop-shadow / glow
# defaults). They are a proxy convenience for the bool/string Effect forms, not
# part of the normative model (EffectObject has no `preset` key).
SHADOW_PRESETS: dict[str, dict] = {
    "small": {"dx": 0, "dy": 1, "blur": 1.5, "color": "#000000", "opacity": 0.10},
    "medium": {"dx": 0, "dy": 2, "blur": 4.0, "color": "#000000", "opacity": 0.14},
    "large": {"dx": 0, "dy": 4, "blur": 8.0, "color": "#000000", "opacity": 0.18},
}
GLOW_PRESETS: dict[str, dict] = {
    "small": {"blur": 2.0, "color": "#FFD700", "opacity": 0.45},
    "medium": {"blur": 4.0, "color": "#FFD700", "opacity": 0.55},
    "large": {"blur": 8.0, "color": "#FFD700", "opacity": 0.65},
}
_DEFAULT_COLOR = {"shadow": "#000000", "glow": "#FFD700"}


class EffectResolver:
    def __init__(self, color_resolver):
        self._color = color_resolver

    def resolve(self, value, kind: str) -> dict | None:
        if value is None or value is False:
            return None
        presets = SHADOW_PRESETS if kind == "shadow" else GLOW_PRESETS
        if value is True:
            params = dict(presets["medium"])
        elif isinstance(value, str):
            key = value.strip().lower()
            if key in ("", "none"):
                return None
            params = dict(presets.get(key, presets["medium"]))
        elif isinstance(value, dict):
            params = dict(presets["medium"])
            for k in ("color", "blur", "dx", "dy", "opacity"):
                if value.get(k) is not None:
                    params[k] = value[k]
        else:
            return None
        params["color"] = self._color.resolve(params.get("color")) or _DEFAULT_COLOR[kind]
        return params

    def style_effects(self, style: dict) -> list[tuple[str, dict]]:
        """Return SVG-filter-compatible effects from the CSS style surface.

        The SVG proxy renders the deterministic subset that maps cleanly to SVG
        filters: box-shadow / drop-shadow and blur. Other CSS filters remain a
        declarable style surface for targets with native CSS support.
        """
        out: list[tuple[str, dict]] = []
        out.extend(("shadow", p) for p in self._box_shadow(style.get("box_shadow")))
        out.extend(self._filter(style.get("filter")))
        return out

    def _box_shadow(self, value) -> list[dict]:
        if value in (None, False, "none", ""):
            return []
        items = value if isinstance(value, list) else [value]
        out = []
        for item in items:
            # A CSS-string shadow (ShadowVal = Union[str, Shadow]) is model-valid;
            # parse it instead of dropping it (a silent failure otherwise).
            if isinstance(item, str):
                out.extend(self._parse_shadow_string(item))
                continue
            if not isinstance(item, dict) or item.get("inset"):
                continue
            params = {
                "dx": item.get("offset_x", item.get("x", 0)),
                "dy": item.get("offset_y", item.get("y", 0)),
                "blur": item.get("blur", 0),
                "color": item.get("color", "#000000"),
                "opacity": item.get("opacity", 0.25),
            }
            params["color"] = self._color.resolve(params.get("color")) or "#000000"
            out.append(params)
        return out

    def _parse_shadow_string(self, text: str) -> list[dict]:
        """Parse a CSS ``box-shadow`` string into drop-shadow render params.

        Handles comma-separated shadows of the form
        ``[inset]? <dx> <dy> [blur] [spread] [color]`` with hex, named, or
        ``rgb()/rgba()/hsl()/hsla()`` colours. ``inset`` shadows are skipped
        (consistent with the structured path, which has no inner-shadow model).
        Any alpha in the colour is lifted into ``opacity`` so the painter's
        ``flood-opacity`` reflects it; an opaque colour yields ``opacity`` 1.0.
        """
        out: list[dict] = []
        for part in _split_commas_outside_parens(text):
            part = part.strip()
            if not part or "inset" in part.lower():
                continue
            color: str | None = None
            match = _FUNC_COLOR_RE.search(part)
            if match:
                color = match.group(0)
                part = (part[: match.start()] + " " + part[match.end():]).strip()
            lengths: list[float] = []
            for token in part.split():
                number = _NUMBER_RE.match(token)
                if number and (token[0].isdigit() or token[0] in "+-."):
                    lengths.append(float(number.group(0)))
                elif color is None:
                    color = token  # hex or named colour
            if len(lengths) < 2:
                continue  # CSS requires at least <offset-x> <offset-y>
            solid, opacity = _split_alpha(color or "#000000")
            out.append({
                "dx": lengths[0],
                "dy": lengths[1],
                "blur": lengths[2] if len(lengths) > 2 else 0,
                "color": self._color.resolve(solid) or solid,
                "opacity": opacity,
            })
        return out

    def _filter(self, value) -> list[tuple[str, dict]]:
        if value in (None, False, "none", ""):
            return []
        items = value if isinstance(value, list) else [value]
        out: list[tuple[str, dict]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("fn") or item.get("kind") or item.get("name")
            if name == "blur":
                out.append(("blur", {"blur": item.get("value", 0)}))
            elif name == "drop_shadow":
                shadows = self._box_shadow(item.get("shadow"))
                out.extend(("shadow", p) for p in shadows)
            elif name in {"turbulence", "displacement_map", "diffuse_lighting", "specular_lighting"}:
                params = {k: v for k, v in item.items() if k not in {"fn", "kind", "name"}}
                if params.get("lighting_color") is not None:
                    params["lighting_color"] = self._color.resolve(params.get("lighting_color")) or params.get("lighting_color")
                out.append((name, params))
        return out


def _split_commas_outside_parens(text: str) -> list[str]:
    """Split on commas that are not inside parentheses (so ``rgba(…)`` stays whole)."""
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def _split_alpha(color: str) -> tuple[str, float]:
    """Split a colour into (opaque-colour, alpha). Opaque colours yield alpha 1.0."""
    c = color.strip()
    func = re.fullmatch(r"(rgba?|hsla?)\(([^)]*)\)", c, re.IGNORECASE)
    if func:
        head = func.group(1).lower()
        args = [a.strip() for a in func.group(2).split(",")]
        if head in ("rgba", "hsla") and len(args) == 4:
            try:
                alpha = max(0.0, min(1.0, float(args[3])))
            except ValueError:
                alpha = 1.0
            stem = "rgb" if head == "rgba" else "hsl"
            return f"{stem}({', '.join(args[:3])})", alpha
        return c, 1.0
    hex8 = re.fullmatch(r"#([0-9a-fA-F]{8})", c)
    if hex8:
        h = hex8.group(1)
        return f"#{h[:6]}", int(h[6:8], 16) / 255.0
    hex4 = re.fullmatch(r"#([0-9a-fA-F]{4})", c)
    if hex4:
        h = hex4.group(1)
        rgb = "".join(ch * 2 for ch in h[:3])
        return f"#{rgb}", int(h[3] * 2, 16) / 255.0
    return c, 1.0
