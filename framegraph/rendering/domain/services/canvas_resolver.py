"""CanvasResolver — page/master → (width, height) (pure).

Extracted from Renderer.canvas_wh + the module-level PRESETS/DEFAULT_WH
(tooling/render_fixtures.py). Resolves a page's canvas from an explicit `size`,
a named `preset`, or inheritance from its `master`, falling back to DEFAULT_WH.
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import is_point

PRESETS = {
    # Print (points; 72 dpi)
    "A3": (842, 1191), "A4": (595, 842), "A5": (419.5, 595.3), "Letter": (612, 792),
    "Legal": (612, 1008), "Tabloid": (792, 1224),
    # Screen / deck / device
    "deck-16x9": (1920, 1080), "deck-4x3": (1024, 768), "square": (1080, 1080),
    "phone": (390, 844), "tablet": (834, 1112), "web": (1280, 800),
    # Social-media canvases — platform creator-guideline sizes in px. These are
    # conventions that shift with each platform; the normative model does not
    # enumerate them, so they live here as a render-time author convenience.
    "instagram-square": (1080, 1080), "instagram-portrait": (1080, 1350),
    "instagram-landscape": (1080, 566), "instagram-story": (1080, 1920),
    "facebook-post": (1200, 630), "facebook-cover": (820, 312),
    "facebook-story": (1080, 1920),
    "twitter-post": (1600, 900), "twitter-header": (1500, 500),
    "linkedin-post": (1200, 627), "linkedin-cover": (1584, 396),
    "youtube-thumbnail": (1280, 720), "youtube-banner": (2560, 1440),
    "tiktok-video": (1080, 1920), "pinterest-pin": (1000, 1500),
    "snapchat": (1080, 1920), "story": (1080, 1920),
    # Aspect-ratio aliases — a canonical pixel canvas at the named ratio.
    "1x1": (1080, 1080), "4x5": (1080, 1350), "5x4": (1350, 1080),
    "9x16": (1080, 1920), "16x9": (1920, 1080), "2x3": (1080, 1620),
    "3x2": (1620, 1080), "1.91x1": (1200, 628), "3x1": (1500, 500),
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
