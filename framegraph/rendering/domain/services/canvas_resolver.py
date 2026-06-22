"""CanvasResolver — page/master → (width, height) (pure).

Extracted from Renderer.canvas_wh + the module-level PRESETS/DEFAULT_WH
(tooling/render_fixtures.py). Resolves a page's canvas from an explicit `size`,
a named `preset`, or inheritance from its `master`, falling back to DEFAULT_WH.
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import is_point

PRESETS = {
    "A3": (842, 1191), "A4": (595, 842), "A5": (419.5, 595.3), "Letter": (612, 792),
    "Legal": (612, 1008), "Tabloid": (792, 1224), "deck-16x9": (1920, 1080),
    "deck-4x3": (1024, 768), "square": (1080, 1080), "phone": (390, 844),
    "tablet": (834, 1112), "web": (1280, 800),
}
DEFAULT_WH = (1280, 800)


class CanvasResolver:
    def __init__(self, masters):
        self.masters = masters or {}

    def resolve(self, page):
        c = page.get("canvas")
        if c is None and page.get("master"):
            c = (self.masters.get(page["master"]) or {}).get("canvas")
        if isinstance(c, str):
            return PRESETS.get(c, DEFAULT_WH)
        if isinstance(c, dict):
            if is_point(c.get("size")):
                return tuple(c["size"][:2])
            if c.get("preset"):
                return PRESETS.get(c["preset"], DEFAULT_WH)
        return DEFAULT_WH
