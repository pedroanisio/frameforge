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
