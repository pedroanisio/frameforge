"""Semantic / accessibility contract for the HTML DocumentRenderer backend.

These tests assert the *structure* of the emitted HTML — figure/figcaption, the
landmark heading, the accessibility mapping, the hoisted stylesheet, and paint
fidelity — not pixel output. They are deliberately small and deterministic: no
network, no headless browser.

History
-------
The backend used to be a standalone renderer that drew shapes as absolutely
-positioned `<div>`s and supported 13 of the model's 34 object types. It is now
an assembler over the shared builder (see the module docstring in
`…backends.html`), so shapes are inline SVG and every object type the engine
knows is drawn.

This file was rewritten with that change. Each assertion below is the *same
capability* the standalone contract guarded, restated against the new output —
the accessibility mapping, the `styles` bucket generating a class, vector
primitives, canvas presets, gradients, fill-opacity and group transforms all
still hold. Two entries changed meaning on purpose and say so where they appear:
a `mode: flow` page now typesets instead of showing a placeholder, and shapes
are SVG elements instead of styled divs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# A codemod/models test earlier in the suite may cache the MODELS module as
# `frameforge`; evict that non-package shadow so the rendering package imports
# (see conftest.py's shadow-module rule).
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge_render.infrastructure.backends import html as fgh  # noqa: E402

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


def _object_markup(out: str, oid: str) -> str:
    """The markup from an object's identity group to the end of the document.

    Object identity is a `<g id=…>` and its accessibility group wraps it, so the
    semantics for `oid` sit immediately before it. Returning a window around the
    id keeps these assertions readable without parsing XML.
    """
    idx = out.index(f'id="{oid}"')
    return out[max(0, idx - 200):idx + 400]


# --------------------------------------------------------------------------- #
# Document shell + accessibility                                               #
# --------------------------------------------------------------------------- #
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
    assert 'aria-hidden="true"' in _object_markup(out, "deco")


def test_decorative_group_drops_role_and_hides_subtree():
    out = fgh.render_document(
        _doc([{"type": "group", "id": "g", "box": [0, 0, 100, 100], "decorative": True,
               "children": [{"type": "rect", "id": "c", "box": [0, 0, 10, 10]}]}])
    )
    markup = _object_markup(out, "g")
    assert 'aria-hidden="true"' in markup
    # decorative wins over the derived role (the `<figure role="group">` shell is
    # document furniture, not this object, so scope the check to the object)
    assert 'role="group"' not in markup


def test_non_decorative_group_is_role_group():
    out = fgh.render_document(
        _doc([{"type": "group", "id": "g", "box": [0, 0, 100, 100],
               "children": [{"type": "rect", "id": "c", "box": [0, 0, 10, 10]}]}])
    )
    assert 'role="group"' in out


def test_icon_with_word_glyph_gets_accessible_name():
    out = fgh.render_document(
        _doc([{"type": "icon", "id": "i", "box": [0, 0, 16, 16], "glyph": "calendar-check"}])
    )
    assert 'role="img"' in out
    assert 'aria-label="calendar check"' in out


def test_icon_with_raw_glyph_is_hidden():
    out = fgh.render_document(
        _doc([{"type": "icon", "id": "i", "box": [0, 0, 16, 16], "glyph": "★"}])
    )
    assert 'aria-hidden="true"' in out
    assert 'role="img"' not in out


def test_image_placeholder_is_labelled_role_img():
    out = fgh.render_document(
        _doc([{"type": "image", "id": "im", "box": [0, 0, 80, 80],
               "src": "missing.png", "placeholder": True, "label": "Team photo"}])
    )
    assert 'role="img"' in out
    assert 'aria-label="Team photo"' in out


def test_line_geometry_is_aria_hidden():
    out = fgh.render_document(
        _doc([{"type": "line", "id": "ln", "from": [0, 0], "to": [50, 50]}])
    )
    assert 'aria-hidden="true"' in out


def test_icon_label_helper_rejects_symbols():
    """The helper moved to the domain so every backend can share one rule."""
    from frameforge_render.domain.services.a11y import icon_label
    assert icon_label("calendar") == "calendar"
    assert icon_label("arrow_right") == "arrow right"
    assert icon_label("★") is None
    assert icon_label("") is None
    assert icon_label("x") is None            # a lone character is a symbol
    assert icon_label("ok") == "ok"           # deliberately wider than the old rule


# --------------------------------------------------------------------------- #
# Styles bucket, vector primitives, presets, flow pages                        #
# --------------------------------------------------------------------------- #
def test_styles_bucket_generates_css_class():
    """A style defined under `styles` (not `text_styles`) must still yield a
    `.fg-ts-<name>` class that a `style:` reference resolves to."""
    doc = _doc([{"type": "text", "id": "t", "box": [0, 0, 100, 20],
                 "text": "Hi", "style": "title"}])
    doc["defs"] = {"tokens": {"styles": {"title": {"font_size": 22, "weight": 700}}}}
    out = fgh.render_document(doc)
    assert ".fg-ts-title {" in out            # class hoisted from `styles`
    assert "font-size:22px" in out
    assert 'class="fg-ts-title"' in out       # and the text references it


def test_text_styles_is_resolved_first_on_a_name_collision():
    """BUG FIXED BY THE PORT.

    `model.Tokens.text_styles` documents itself as the "legacy namespace;
    superseded by `styles`, **still resolved first by the renderer**". The shared
    `TextStyleResolver` obeys that; the standalone HTML backend had it inverted
    and let `styles` win, so one document could resolve a colliding style name
    two different ways depending only on the output target. Driving both targets
    from one resolver is what makes that impossible.
    """
    doc = _doc([{"type": "text", "id": "t", "box": [0, 0, 100, 40],
                 "text": "Hi", "style": "h"}])
    doc["defs"] = {"tokens": {
        "text_styles": {"h": {"font_size": 10}},
        "styles": {"h": {"font_size": 30}},
    }}
    out = fgh.render_document(doc)
    assert "font-size:10px" in out
    assert "font-size:30px" not in out

    # ...and the SVG target agrees, which is the whole point.
    from frameforge_render.application.normalize import normalize_doc
    from frameforge_render.application.renderer import Renderer
    data = normalize_doc(doc)
    svg = "".join(Renderer(data, ".").render_page(data["pages"][0]))
    assert "font-size:10px" in svg


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
    """Now a real `<circle>`. The standalone backend approximated one with a div
    and `border-radius:50%`; the element is exact and needs no approximation."""
    out = fgh.render_document(
        _doc([{"type": "circle", "id": "c", "center": [50, 50], "r": 20, "fill": "#abc"}])
    )
    assert '<circle cx="50" cy="50" r="20"' in out


def test_curve_renders_cubic_path():
    out = fgh.render_document(
        _doc([{"type": "curve", "id": "cv", "from": [0, 0], "to": [40, 0],
               "control1": [10, 30], "control2": [30, 30], "stroke": "#fff"}])
    )
    assert "<path d=" in out
    assert " C " in out                       # cubic segment


def test_canvas_preset_string_resolves_to_pixels():
    from frameforge_render.domain.services.canvas_resolver import DEFAULT_WH
    assert fgh.canvas_size({"canvas": "deck-16x9"}) == (1920, 1080)
    assert fgh.canvas_size({"canvas": {"preset": "A4"}}) == (595, 842)
    assert fgh.canvas_size({"canvas": {"size": [320, 240]}}) == (320, 240)
    # the canvas-less default is the ONE canonical default — not an HTML-private one
    assert fgh.canvas_size({"canvas": "nonexistent"}) == DEFAULT_WH == (1280, 800)


def test_preset_table_matches_model_page_presets():
    """Guard against drift: our preset keys must equal the model's PagePreset."""
    import typing

    import frameforge.model as model
    preset_literal = set(typing.get_args(model.PagePreset))
    assert set(fgh._CANVAS_PRESETS) == preset_literal


def test_html_canvas_table_is_the_shared_canonical_not_a_mirror():
    """drift-risk-map #4: the HTML backend must use the SAME preset table (keys AND
    size values) as the canonical render path, so a size can never diverge between
    `--to svg`/`pdf-tex` and `--to html`. Enforced by sharing the object, not copying."""
    from frameforge_render.domain.services import canvas_resolver as CR
    # identity: the HTML symbol IS the canonical table (a shared import, no copy)
    assert fgh._CANVAS_PRESETS is CR.PRESETS
    # value-level guard (would catch a future divergence even if the copy returned)
    assert dict(fgh._CANVAS_PRESETS) == dict(CR.PRESETS)
    assert fgh.canvas_size({"canvas": "nonexistent"}) == CR.DEFAULT_WH


def test_font_family_may_be_a_list():
    """`Style.font_family` is a StrList — a list must not crash the font stack.

    Resolution moved to the shared `TextStyleResolver`, so this now guards the
    ONE implementation both SVG and HTML use rather than an HTML-private copy.
    """
    from frameforge_render.domain.services.paint_resolver import ColorResolver
    from frameforge_render.domain.services.text_style_resolver import TextStyleResolver
    resolver = TextStyleResolver({}, {}, ColorResolver({}))
    st = resolver.resolve({"font_family": ["Inter", "sans-serif"]})
    assert st["family"] == "Inter, sans-serif"


def test_styles_with_list_font_family_renders():
    doc = _doc([{"type": "text", "id": "t", "box": [0, 0, 100, 20],
                 "text": "Hi", "style": "body"}])
    doc["defs"] = {"tokens": {"styles": {
        "body": {"font_family": ["Inter", "sans-serif"], "font_size": 14}}}}
    out = fgh.render_document(doc)            # must not raise
    assert "font-family:Inter, sans-serif" in out


def test_flow_section_typesets_instead_of_showing_a_placeholder():
    """BEHAVIOUR CHANGE (intentional).

    The standalone backend could not typeset the document/flow profile, so it
    emitted a labelled note saying so. Driving the shared builder means flow is
    laid out for real — the placeholder is gone, and its absence is the point.
    """
    doc = {
        "dsl": "FrameForge", "version": "2.0.0", "title": "Mixed",
        "defs": {"masters": {"m": {"regions": [
            {"id": "body", "box": [40, 40, 500, 700]}]}}},
        "pages": [{"mode": "flow", "id": "ch1", "master": "m",
                   "canvas": {"size": [595, 842], "units": "px"},
                   "story": [{"type": "paragraph", "text": "alpha"},
                             {"type": "paragraph", "text": "beta"}]}],
    }
    out = fgh.render_document(doc)
    assert "fg-flow-note" not in out
    assert "document/flow profile not rendered" not in out
    assert "alpha" in out and "beta" in out    # the story is really typeset


# --------------------------------------------------------------------------- #
# Paint fidelity: gradients, fill_opacity, group transforms                    #
# (regressions for the gray page-background + missing badge-number bugs)       #
# --------------------------------------------------------------------------- #
_RADIAL = {"kind": "radial", "at": "50% 50%", "shape": "circle",
           "stops": [{"color": "#F8F3EA", "position": "0%"},
                     {"color": "#F3EEE4", "position": "100%"}]}


def test_gradient_rect_emits_a_real_gradient_not_gray():
    out = fgh.render_document(_doc([
        {"type": "rect", "id": "bg", "box": [0, 0, 400, 300], "fill": _RADIAL}]))
    assert "<radialGradient" in out
    assert "#F3EEE4" in out and "#F8F3EA" in out
    assert "#888888" not in out               # the old flat-gray fallback is gone


def test_gradient_polygon_emits_a_gradient_def_not_gray():
    out = fgh.render_document(_doc([
        {"type": "polygon", "points": [[0, 0], [100, 0], [50, 80]], "fill": _RADIAL}]))
    assert "<radialGradient" in out
    assert 'fill="url(#' in out
    assert "#888888" not in out


def test_fill_opacity_tints_a_circle_so_overlaid_text_stays_legible():
    # a badge: a 20%-opacity coloured disc with the number in the same colour on
    # top. Without fill_opacity the disc is solid and hides the number.
    out = fgh.render_document(_doc([
        {"type": "circle", "id": "b", "center": [40, 40], "r": 9,
         "fill": "#A6442E", "fill_opacity": 0.2}]))
    assert 'fill="#A6442E" fill-opacity="0.2"' in out


def test_group_style_transform_is_applied_to_the_group():
    # the transform rides in the `style` bag (a CSS property), placing the whole
    # subtree — here a translate onto the page.
    group = {
        "type": "group", "style": {"transform": [
            {"fn": "matrix", "args": [1.0, 0.0, 0.0, 1.0, 76.0, 76.0]}]},
        "children": [{"type": "rect", "id": "k", "box": [0, 0, 10, 10], "fill": "#000000"}],
    }
    out = fgh.render_document(_doc([group]))
    assert 'transform="matrix(1 0 0 1 76 76)"' in out


# --------------------------------------------------------------------------- #
# The duplication that motivated the port must not come back                   #
# --------------------------------------------------------------------------- #
def test_backend_defines_no_renderer_of_its_own():
    """The module is an assembler: no per-object-type rendering may live here.

    A `_render_<type>` method reappearing means someone started re-implementing
    the engine in the backend again — the exact drift this port removed.
    """
    import frameforge_render
    from pathlib import Path as _P
    # The engine is its own distribution since 2026-08-01; read its source there.
    source = (_P(frameforge_render.__file__).resolve().parent / "infrastructure"
              / "backends" / "html.py").read_text(encoding="utf-8")
    assert "def _render_" not in source
    # the placeholder machinery is gone with it (prose in the module's history
    # note is not code, so check for the emitter, not the phrase)
    assert "fg-unknown" not in source
    assert "fg-flow-note" not in source


@pytest.mark.parametrize("symbol", ["load_document", "maybe_validate",
                                    "canvas_size", "page_link_href",
                                    "render_page_links", "render_document"])
def test_public_helpers_survived_the_port(symbol):
    """These are the module's published surface; the port must not silently
    drop one (`render_page_links` in particular is the only backend that can
    carry authored `Page.links` navigation at all)."""
    assert hasattr(fgh, symbol)


def test_page_links_render_as_a_navigation_landmark():
    doc = _doc([{"type": "rect", "id": "bg", "box": [0, 0, 10, 10]}])
    doc["pages"][0]["links"] = [
        {"to": "p2", "label": "Next"},
        {"to": "https://example.com", "label": "Home", "external": True},
    ]
    out = fgh.render_document(doc)
    assert '<nav class="fg-pagelinks"' in out
    assert 'href="#page-p2"' in out
    assert 'href="https://example.com"' in out and 'target="_blank"' in out
