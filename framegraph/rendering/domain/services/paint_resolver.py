"""ColorResolver — token/colour dereference (pure).

Extracted from Renderer.color (tooling/render_fixtures.py). Resolves a colour
reference to an SVG colour string, 'none', or None:

  * a tokens.colors key            → recurse on its value
  * a paint dict (gradient/pattern) → first stop's colour, or `background`
  * a literal                      → hex / rgb()/rgba() / CSS name, passed through
  * 'none'/'transparent'           → 'none'
  * 'currentColor'                 → '#222' (the proxy's stand-in)

This is the pure core of paint resolution. Gradient *emission* (the SVG
<linearGradient>/<radialGradient> in <defs>) remains in the painter until the
value-object Scene lands in step 4; the eventual PaintResolver will return a
ResolvedPaint value object and the painter will emit from it.
"""
from __future__ import annotations


class ColorResolver:
    def __init__(self, colors):
        self.colors = colors or {}

    def resolve(self, c, depth=0):
        if c is None or depth > 8:
            return None
        if isinstance(c, dict):                      # a paint object (gradient/pattern)
            stops = c.get("stops")
            if stops:
                return self.resolve(stops[0].get("color"), depth + 1)
            return self.resolve(c.get("background"), depth + 1)
        if isinstance(c, str):
            s = c.strip()
            if s in self.colors:
                return self.resolve(self.colors[s], depth + 1)
            low = s.lower()
            if low in ("none", "transparent"):
                return "none"
            if low == "currentcolor":
                return "#222"
            return s                                  # hex / rgb()/rgba() / css name
        return None
