"""Semantic / accessibility contract for ``framegraph_to_html.py``.

These tests assert the *structure* of the emitted HTML (figure/figcaption,
landmark heading, role="group", and the model-driven ``decorative`` →
``aria-hidden`` mapping), not pixel output. They are deliberately small and
deterministic — no network, no headless browser.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "framegraph_to_html", ROOT / "framegraph_to_html.py"
)
fgh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fgh)


def _doc(objects: list[dict], *, title: str = "Sample") -> dict:
    return {
        "dsl": "FrameGraph",
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
    assert fgh.canvas_size({"canvas": "deck-16x9"}) == (1920, 1080)
    assert fgh.canvas_size({"canvas": {"preset": "A4"}}) == (595, 842)
    assert fgh.canvas_size({"canvas": {"size": [320, 240]}}) == (320, 240)
    assert fgh.canvas_size({"canvas": "nonexistent"}) == (800, 600)  # default


def test_preset_table_matches_model_page_presets():
    """Guard against drift: our preset keys must equal the model's PagePreset."""
    import importlib.util as _u
    spec = _u.spec_from_file_location("fgmodel", ROOT / "models" / "framegraph.py")
    model = _u.module_from_spec(spec)
    spec.loader.exec_module(model)
    import typing
    preset_literal = set(typing.get_args(model.PagePreset))
    assert set(fgh._CANVAS_PRESETS) == preset_literal


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
        "dsl": "FrameGraph", "version": "2.0.0", "title": "Mixed",
        "pages": [{"mode": "flow", "id": "ch1", "master": "m",
                   "story": [{"type": "paragraph", "text": "x"},
                             {"type": "paragraph", "text": "y"}]}],
    }
    out = fgh.render_document(doc)
    assert "fg-flow-note" in out
    assert "flow section" in out
    assert "<code>ch1</code>" in out
    assert "2 flowable(s)" in out
