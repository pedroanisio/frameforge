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
            if isinstance(item, str) or not isinstance(item, dict) or item.get("inset"):
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
        return out
