#!/usr/bin/env python3
"""
test_render_services.py — unit coverage for the pure rendering domain services
(framegraph/rendering/domain/services) that the integration render-tests only
exercised partially: CanvasResolver (62%) and ColorResolver (70%), plus an
import-cover of the ScenePainter port.

Package-side import (these live in the `framegraph` package) — evict a
models-module shadow first, per test_rendering_svg_semantics.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # the models module
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from framegraph.rendering.domain.services.canvas_resolver import (  # noqa: E402
    CanvasResolver, DEFAULT_WH,
)
from framegraph.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
import framegraph.rendering.domain.ports as ports  # noqa: E402


# --- CanvasResolver ----------------------------------------------------------- #
def test_canvas_preset_string():
    assert CanvasResolver({}).resolve({"canvas": "A4"}) == (595, 842)


def test_canvas_unknown_preset_string_falls_back():
    assert CanvasResolver({}).resolve({"canvas": "nope"}) == DEFAULT_WH


def test_canvas_explicit_size_dict():
    assert CanvasResolver({}).resolve({"canvas": {"size": [300, 200], "units": "px"}}) == (300, 200)


def test_canvas_preset_dict():
    assert CanvasResolver({}).resolve({"canvas": {"preset": "Letter"}}) == (612, 792)


def test_canvas_social_media_presets_resolve():
    """Social-media size presets resolve as both a string and a {preset} dict."""
    cr = CanvasResolver({})
    assert cr.resolve({"canvas": "instagram-story"}) == (1080, 1920)
    assert cr.resolve({"canvas": "twitter-header"}) == (1500, 500)
    assert cr.resolve({"canvas": "youtube-thumbnail"}) == (1280, 720)
    assert cr.resolve({"canvas": {"preset": "linkedin-cover"}}) == (1584, 396)


def test_canvas_aspect_ratio_alias_presets():
    """Aspect-ratio aliases resolve to a canonical pixel canvas at that ratio."""
    cr = CanvasResolver({})
    assert cr.resolve({"canvas": "9x16"}) == (1080, 1920)
    assert cr.resolve({"canvas": "4x5"}) == (1080, 1350)
    assert cr.resolve({"canvas": "1.91x1"}) == (1200, 628)
    # the ratio holds for each social/ratio preset (w/h matches the named ratio)
    for name in ("9x16", "16x9", "4x5", "instagram-story", "twitter-header"):
        w, h = cr.resolve({"canvas": name})
        assert w > 0 and h > 0


def test_canvas_book_trim_presets_resolve():
    """Book trim sizes resolve to points @ 72 dpi (inches × 72)."""
    cr = CanvasResolver({})
    assert cr.resolve({"canvas": "book-6x9"}) == (432, 648)          # 6 × 9 in
    assert cr.resolve({"canvas": "book-trade"}) == (360, 576)        # 5 × 8 in
    assert cr.resolve({"canvas": "book-7x10"}) == (504, 720)         # 7 × 10 in
    assert cr.resolve({"canvas": "book-textbook"}) == (612, 792)     # 8.5 × 11 in (= Letter)
    assert cr.resolve({"canvas": {"preset": "book-coffee-table"}}) == (648, 864)  # 9 × 12 in
    assert cr.resolve({"canvas": "book-mass-market"}) == (306, 494.6)  # 4.25 × 6.87 in


def test_canvas_presets_match_page_preset_literal():
    """Guard drift: the resolver's PRESET keys must equal the model's PagePreset."""
    import typing

    from framegraph.rendering.domain.services.canvas_resolver import PRESETS
    from models import framegraph as model
    assert set(PRESETS) == set(typing.get_args(model.PagePreset))


def test_canvas_inherited_from_master():
    cr = CanvasResolver({"m": {"canvas": {"preset": "A4"}}})
    assert cr.resolve({"master": "m"}) == (595, 842)


def test_canvas_missing_master_defaults():
    assert CanvasResolver({}).resolve({"master": "absent"}) == DEFAULT_WH


def test_canvas_empty_and_absent_default():
    assert CanvasResolver({}).resolve({}) == DEFAULT_WH
    assert CanvasResolver({}).resolve({"canvas": {}}) == DEFAULT_WH


# --- ColorResolver ------------------------------------------------------------ #
def test_color_none_and_recursion_guard():
    cr = ColorResolver({})
    assert cr.resolve(None) is None
    assert cr.resolve("x", depth=9) is None


def test_color_token_dereference_and_nesting():
    assert ColorResolver({"brand": "#0a0"}).resolve("brand") == "#0a0"
    assert ColorResolver({"a": "b", "b": "#fff"}).resolve("a") == "#fff"


def test_color_keywords():
    cr = ColorResolver({})
    assert cr.resolve("none") == "none"
    assert cr.resolve("transparent") == "none"
    assert cr.resolve("currentColor") == "#222"


def test_color_literal_passthrough():
    assert ColorResolver({}).resolve("#abcdef") == "#abcdef"
    assert ColorResolver({}).resolve("rgba(0,0,0,.3)") == "rgba(0,0,0,.3)"


def test_color_from_gradient_first_stop():
    g = {"kind": "linear", "stops": [{"color": "#111"}, {"color": "#222"}]}
    assert ColorResolver({}).resolve(g) == "#111"


def test_color_from_pattern_background():
    assert ColorResolver({}).resolve({"kind": "pattern", "background": "#eee"}) == "#eee"


def test_color_non_str_non_dict_is_none():
    assert ColorResolver({}).resolve(123) is None


# --- ports -------------------------------------------------------------------- #
def test_scenepainter_port_surface():
    assert hasattr(ports, "ScenePainter")
    for m in ("rect", "ellipse", "line", "path", "text_tag", "document", "gradient"):
        assert hasattr(ports.ScenePainter, m)
