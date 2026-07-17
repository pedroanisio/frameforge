"""Semantic / accessibility contract for the HTML DocumentRenderer backend.

These tests assert the *structure* of the emitted HTML (figure/figcaption,
landmark heading, role="group", and the model-driven ``decorative`` →
``aria-hidden`` mapping), not pixel output. They are deliberately small and
deterministic — no network, no headless browser.

The renderer moved from ``tooling/frameforge_to_html.py`` into the package as
``frameforge.rendering.infrastructure.backends.html`` (the `DocumentRenderer`
port); the pure `render_document` transform is unchanged, so this contract
holds across the move.
"""

from __future__ import annotations

import sys
from pathlib import Path

# A codemod/models test earlier in the suite may cache the MODELS module as
# `frameforge`; evict that non-package shadow so the rendering package imports
# (see conftest.py's shadow-module rule).
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.rendering.infrastructure.backends import html as fgh  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _doc(objects: list[dict], *, title: str = "Sample") -> dict:
    return {
        "dsl": "FrameForge",
        "version": "2.0.0",
        "title": title,
        "pages": [
            {
                "mode": "page",
                "id": "p1",
                "canvas": {"size": [400, 300], "units": "px"},
                "layers": [{"id": "main", "z": 0, "objects": objects}],
            }
        ],
    }


def test_document_has_figure_figcaption_and_landmark_h1():
    out = fgh.render_document(_doc([{"type": "rect", "id": "bg", "box": [0, 0, 10, 10]}]))
    assert '<h1 class="sr-only">Sample</h1>' in out
    assert '<figure class="fg-figure"' in out
    assert "<figcaption" in out
    # figure is named by its caption
    assert 'aria-labelledby="fg-figcap-0"' in out
    assert 'id="fg-figcap-0"' in out


def test_decorative_object_is_hidden_from_assistive_tech():
    out = fgh.render_document(
        _doc([{"type": "rect", "id": "deco", "box": [0, 0, 10, 10], "decorative": True}])
    )
    # the decorative rect carries aria-hidden ...
    rect_tag = next(line for line in out.splitlines() if 'id="deco"' in line)
    assert 'aria-hidden="true"' in rect_tag


def test_decorative_group_drops_role_and_hides_subtree():
    out = fgh.render_document(
        _doc(
            [
                {
                    "type": "group",
                    "id": "g",
                    "box": [0, 0, 100, 100],
                    "decorative": True,
                    "children": [{"type": "rect", "id": "c", "box": [0, 0, 10, 10]}],
                }
            ]
        )
    )
    group_tag = next(line for line in out.splitlines() if 'id="g"' in line)
    assert 'aria-hidden="true"' in group_tag
    assert 'role="group"' not in group_tag  # decorative wins over the role


def test_non_decorative_group_is_role_group():
    out = fgh.render_document(
        _doc(
            [
                {
                    "type": "group",
                    "id": "g",
                    "box": [0, 0, 100, 100],
                    "children": [{"type": "rect", "id": "c", "box": [0, 0, 10, 10]}],
                }
            ]
        )
    )
    group_tag = next(line for line in out.splitlines() if 'id="g"' in line)
    assert 'role="group"' in group_tag


def test_icon_with_word_glyph_gets_accessible_name():
    out = fgh.render_document(
        _doc([{"type": "icon", "id": "i", "box": [0, 0, 16, 16], "glyph": "calendar-check"}])
    )
    icon_tag = next(line for line in out.splitlines() if 'id="i"' in line)
    assert 'role="img"' in icon_tag
    assert 'aria-label="calendar check"' in icon_tag


def test_icon_with_raw_glyph_is_hidden():
    out = fgh.render_document(
        _doc([{"type": "icon", "id": "i", "box": [0, 0, 16, 16], "glyph": "★"}])
    )
    icon_tag = next(line for line in out.splitlines() if 'id="i"' in line)
    assert 'aria-hidden="true"' in icon_tag
    assert "role=" not in icon_tag


def test_image_placeholder_is_labelled_role_img():
    out = fgh.render_document(
        _doc([{"type": "image", "id": "im", "box": [0, 0, 80, 80],
               "src": "missing.png", "placeholder": True, "label": "Team photo"}])
    )
    img_tag = next(line for line in out.splitlines() if 'id="im"' in line)
    assert 'role="img"' in img_tag
    assert 'aria-label="Team photo"' in img_tag


def test_line_geometry_is_aria_hidden():
    out = fgh.render_document(
        _doc([{"type": "line", "id": "ln", "from": [0, 0], "to": [50, 50]}])
    )
    assert '<svg aria-hidden="true"' in out


def test_icon_label_helper_rejects_symbols():
    assert fgh._icon_label("calendar") == "calendar"
    assert fgh._icon_label("arrow_right") == "arrow right"
    assert fgh._icon_label("★") is None
    assert fgh._icon_label("") is None
    assert fgh._icon_label("ok") is None  # too short to be a name


# --------------------------------------------------------------------------- #
# Correctness fixes: styles bucket, vector primitives, presets, flow pages    #
# --------------------------------------------------------------------------- #


def test_styles_bucket_generates_css_class():
    """A style defined under `styles` (not `text_styles`) must still yield a
    `.fg-ts-<name>` class that a `style:` reference can resolve to."""
    doc = _doc([{"type": "text", "id": "t", "box": [0, 0, 100, 20],
                 "text": "Hi", "style": "title"}])
    doc["defs"] = {"tokens": {"styles": {"title": {"font_size": 22, "weight": 700}}}}
    out = fgh.render_document(doc)
    assert ".fg-ts-title{" in out          # class was generated from `styles`
    assert "font-size:22" in out           # (renders as 22.0px)
    text_tag = next(line for line in out.splitlines() if 'id="t"' in line)
    assert "fg-ts-title" in text_tag        # and the text references it


def test_styles_wins_over_text_styles_on_collision():
    doc = _doc([])
    doc["defs"] = {"tokens": {
        "text_styles": {"h": {"font_size": 10}},
        "styles": {"h": {"font_size": 30}},
    }}
    out = fgh.render_document(doc)
    assert "font-size:30.0px" in out
    assert "font-size:10.0px" not in out


def test_polyline_and_polygon_render_as_svg():
    out = fgh.render_document(
        _doc([{"type": "polyline", "id": "pl",
               "points": [[0, 0], [10, 20], [30, 5]], "stroke": "#f00"}])
    )
    assert "<polyline points=" in out
    assert 'id="pl"' in out
    out2 = fgh.render_document(
        _doc([{"type": "polygon", "id": "pg",
               "points": [[0, 0], [10, 0], [5, 10]], "fill": "#0f0"}])
    )
    assert "<polygon points=" in out2


def test_closed_polyline_becomes_polygon():
    out = fgh.render_document(
        _doc([{"type": "polyline", "id": "pl", "closed": True,
               "points": [[0, 0], [10, 0], [5, 10]]}])
    )
    assert "<polygon points=" in out


def test_path_renders_from_string_and_segments():
    out = fgh.render_document(
        _doc([{"type": "path", "id": "p", "d": "M0 0 L10 10 Z", "stroke": "#fff"}])
    )
    assert '<path d="M0 0 L10 10 Z"' in out
    seg = fgh.render_document(
        _doc([{"type": "path", "id": "p2", "d": [["M", 0, 0], ["L", 5, 5]]}])
    )
    assert "<path d=" in seg and "M 0 0" in seg


def test_circle_renders_as_round_element():
    out = fgh.render_document(
        _doc([{"type": "circle", "id": "c", "center": [50, 50], "r": 20,
               "fill": "#abc"}])
    )
    circle_tag = next(line for line in out.splitlines() if 'id="c"' in line)
    assert "border-radius:50%" in circle_tag


def test_curve_renders_cubic_path():
    out = fgh.render_document(
        _doc([{"type": "curve", "id": "cv", "from": [0, 0], "to": [40, 0],
               "control1": [10, 30], "control2": [30, 30], "stroke": "#fff"}])
    )
    assert "<path d=" in out
    path_line = next(ln for ln in out.splitlines() if 'id="cv"' in ln)
    assert " C " in path_line  # cubic segment


def test_canvas_preset_string_resolves_to_pixels():
    from frameforge.rendering.domain.services.canvas_resolver import DEFAULT_WH
    assert fgh.canvas_size({"canvas": "deck-16x9"}) == (1920, 1080)
    assert fgh.canvas_size({"canvas": {"preset": "A4"}}) == (595, 842)
    assert fgh.canvas_size({"canvas": {"size": [320, 240]}}) == (320, 240)
    # the canvas-less default is the ONE canonical default — not an HTML-private one
    assert fgh.canvas_size({"canvas": "nonexistent"}) == DEFAULT_WH == (1280, 800)


def test_preset_table_matches_model_page_presets():
    """Guard against drift: our preset keys must equal the model's PagePreset."""
    import importlib.util as _u
    spec = _u.spec_from_file_location("fgmodel", ROOT / "docs" / "models" / "frameforge.py")
    model = _u.module_from_spec(spec)
    spec.loader.exec_module(model)
    import typing
    preset_literal = set(typing.get_args(model.PagePreset))
    assert set(fgh._CANVAS_PRESETS) == preset_literal


def test_html_canvas_table_is_the_shared_canonical_not_a_mirror():
    """drift-risk-map #4: the HTML backend must use the SAME preset table (keys AND
    size values) as the canonical render path, so a size can never diverge between
    `--to svg`/`pdf-tex` and `--to html`. Enforced by sharing the object, not copying."""
    from frameforge.rendering.domain.services import canvas_resolver as CR
    # identity: the HTML symbol IS the canonical table (a shared import, no copy)
    assert fgh._CANVAS_PRESETS is CR.PRESETS
    # value-level guard (would catch a future divergence even if the copy returned)
    assert dict(fgh._CANVAS_PRESETS) == dict(CR.PRESETS)
    assert fgh.canvas_size({"canvas": "nonexistent"}) == CR.DEFAULT_WH


def test_font_family_may_be_a_list():
    """`Style.font_family` is a StrList — a list must not crash font_stack."""
    assert fgh.Tokens({}).font_stack(["Inter", "sans-serif"]) == "'Inter', sans-serif"
    # a token entry is expanded to family + fallback
    tk = fgh.Tokens({"defs": {"tokens": {"fonts": {
        "ui": {"family": "Inter", "fallback": ["Arial"]}}}}})
    assert tk.font_stack(["ui", "monospace"]) == "'Inter', 'Arial', monospace"


def test_styles_with_list_font_family_renders():
    doc = _doc([{"type": "text", "id": "t", "box": [0, 0, 100, 20],
                 "text": "Hi", "style": "body"}])
    doc["defs"] = {"tokens": {"styles": {
        "body": {"font_family": ["Inter", "sans-serif"], "font_size": 14}}}}
    out = fgh.render_document(doc)            # must not raise
    assert "font-family:'Inter', sans-serif" in out


def test_flow_section_renders_labelled_placeholder_not_empty():
    doc = {
        "dsl": "FrameForge", "version": "2.0.0", "title": "Mixed",
        "pages": [{"mode": "flow", "id": "ch1", "master": "m",
                   "story": [{"type": "paragraph", "text": "x"},
                             {"type": "paragraph", "text": "y"}]}],
    }
    out = fgh.render_document(doc)
    assert "fg-flow-note" in out
    assert "flow section" in out
    assert "<code>ch1</code>" in out
    assert "2 flowable(s)" in out


# --------------------------------------------------------------------------- #
# Paint fidelity: gradients, fill_opacity, group transforms                    #
# (regressions for the gray page-background + missing badge-number bugs)       #
# --------------------------------------------------------------------------- #
_RADIAL = {"kind": "radial", "at": "50% 50%", "shape": "circle",
           "stops": [{"color": "#F8F3EA", "position": "0%"},
                     {"color": "#F3EEE4", "position": "100%"}]}


def test_gradient_rect_emits_real_css_gradient_not_gray():
    out = fgh.render_document(_doc([
        {"type": "rect", "id": "bg", "box": [0, 0, 400, 300], "fill": _RADIAL}]))
    assert "radial-gradient" in out
    assert "#F3EEE4" in out and "#F8F3EA" in out
    assert "#888888" not in out           # the old flat-gray fallback is gone


def test_gradient_polygon_emits_svg_gradient_def_not_gray():
    out = fgh.render_document(_doc([
        {"type": "polygon", "points": [[0, 0], [100, 0], [50, 80]], "fill": _RADIAL}]))
    assert "<radialGradient" in out
    assert "fill:url(#fgg-" in out
    assert "#888888" not in out


def test_fill_opacity_tints_a_circle_so_overlaid_text_stays_legible():
    # a badge: a 20%-opacity coloured disc with the number in the same colour on
    # top. Without fill_opacity the disc is solid and hides the number.
    out = fgh.render_document(_doc([
        {"type": "circle", "id": "b", "center": [40, 40], "r": 9,
         "fill": "#A6442E", "fill_opacity": 0.2}]))
    assert "rgba(166,68,46,0.2)" in out


def test_group_style_transform_is_applied_to_the_group_div():
    # the transform rides in the `style` bag (a CSS property), placing the whole
    # subtree — here a translate onto the page.
    group = {
        "type": "group", "style": {"transform": [
            {"fn": "matrix", "args": [1.0, 0.0, 0.0, 1.0, 76.0, 76.0]}]},
        "children": [{"type": "rect", "id": "k", "box": [0, 0, 10, 10], "fill": "#000000"}],
    }
    out = fgh.render_document(_doc([group]))
    assert "transform:matrix(1,0,0,1,76,76)" in out
    assert "transform-origin:0 0" in out
