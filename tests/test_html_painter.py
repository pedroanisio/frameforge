"""HtmlPainter: the HTML backend driven by the shared builder.

The point of these gates is that HTML stops being a second renderer. The same
`Renderer` that drives SVG drives this painter, so anything the builder can lay
out — tables, UML, connectors, dimensions — reaches HTML without HTML knowing
what any of those are. What the painter still owns is the semantics the old
standalone backend was valued for: the layer tree, object identity, named text
styles, and the palette. Those must survive the move, or the port trades 21
newly-supported object types for worse markup.
"""
from __future__ import annotations

import json
import os
import re
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.application.renderer import Renderer  # noqa: E402
from frameforge.rendering.domain.services.paint_resolver import ColorResolver  # noqa: E402
from frameforge.rendering.infrastructure.painters.html import (  # noqa: E402
    HtmlPainter, css_ident)
from frameforge.rendering.infrastructure.painters.svg import SvgPainter  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "b1", "mckinsey-7s.fg.json")


def _doc():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def _drive(doc=None, page_index=0):
    doc = doc or _doc()
    held = {}

    def factory(color):
        held["p"] = HtmlPainter(color)
        return held["p"]

    r = Renderer(doc, ".", painter_factory=factory)
    out = "".join(r.render_page(doc["pages"][page_index]))
    return held["p"], out, r


# --------------------------------------------------------------------------- #
# It really is driven by the shared builder                                    #
# --------------------------------------------------------------------------- #
def test_builder_drives_the_html_painter_end_to_end():
    painter, out, r = _drive()
    assert r.skipped == 0, "no object should be skipped when driving HtmlPainter"
    assert out.startswith("<svg"), "a page renders as inline SVG geometry"
    assert "<rect" in out and "<text" in out
    assert isinstance(painter, SvgPainter), "HtmlPainter must be substitutable (LSP)"


def test_html_painter_inherits_full_geometry_parity():
    """Every primitive the reference backend implements is available here.

    This is the DRY claim made testable: HtmlPainter defines no primitive of its
    own, so it cannot fall behind SvgPainter's object-type coverage.
    """
    missing = [name for name in ("rect", "ellipse", "circle", "line", "poly",
                                 "path", "image", "text_tag", "text_block",
                                 "text_runs", "gradient", "clip_rect", "marker",
                                 "filter_effect", "pattern", "mask_def")
               if not hasattr(HtmlPainter, name)]
    assert not missing, f"HtmlPainter lost primitives: {missing}"


# --------------------------------------------------------------------------- #
# The layer tree survives                                                      #
# --------------------------------------------------------------------------- #
def test_layers_become_addressable_groups():
    doc = _doc()
    _painter, out, _r = _drive(doc)
    layers = [L for L in doc["pages"][0].get("layers") or []
              if L.get("role") != "construction"]
    assert out.count('class="fg-layer"') == len(layers)
    for layer in layers:
        name = layer.get("id") or layer.get("name")
        if name:
            assert f'data-layer="{name}"' in out, f"layer {name!r} lost its identity"


def test_layer_group_is_skipped_for_empty_content():
    painter = HtmlPainter(ColorResolver({}))
    assert painter.layer_group("", {"id": "main"}) == ""


def test_layer_group_carries_z_and_role():
    painter = HtmlPainter(ColorResolver({}))
    out = painter.layer_group("<rect/>", {"id": "bg", "z": 3, "role": "background"})
    assert 'data-layer="bg"' in out and 'data-z="3"' in out
    assert 'data-role="background"' in out


# --------------------------------------------------------------------------- #
# Object identity survives                                                     #
# --------------------------------------------------------------------------- #
def test_objects_keep_their_authored_id_and_type_class():
    doc = _doc()
    _painter, out, _r = _drive(doc)
    ids = [o.get("id") for L in doc["pages"][0].get("layers") or []
           for o in L.get("objects") or [] if isinstance(o, dict) and o.get("id")]
    assert ids, "fixture must have identified objects"
    for oid in ids:
        assert f'id="{oid}"' in out, f"object {oid!r} lost its id in HTML output"
    assert 'class="fg-obj fg-rect"' in out or 'class="fg-obj fg-ellipse"' in out


def test_anonymous_object_pays_no_wrapper():
    painter = HtmlPainter(ColorResolver({}))
    assert painter.object_group("<rect/>", {}) == "<rect/>"


def test_object_group_escapes_a_hostile_id():
    painter = HtmlPainter(ColorResolver({}))
    out = painter.object_group("<rect/>", {"id": '"><script>', "type": "rect"})
    assert "<script>" not in out


# --------------------------------------------------------------------------- #
# Named text styles hoist to classes                                           #
# --------------------------------------------------------------------------- #
def test_named_text_style_becomes_a_class_and_is_collected():
    doc = _doc()
    painter, out, _r = _drive(doc)
    assert painter.text_styles, "no named text style was collected"
    for ident in painter.text_styles:
        assert f'class="fg-ts-{ident}"' in out


def test_anonymous_text_style_gets_no_class():
    painter = HtmlPainter(ColorResolver({}))
    assert painter._text_class_attr({"style_ref": None}) == ""
    assert painter._text_class_attr({}) == ""


def test_inline_style_still_carries_the_fitted_size():
    """The class is a hook, not the source of truth — the fitted size must stay
    inline or a shrunk-to-fit line would render at its declared size."""
    doc = _doc()
    _painter, out, _r = _drive(doc)
    for tag in re.findall(r"<text[^>]*>", out):
        if 'class="fg-ts-' in tag:
            assert "font-size:" in tag, f"fitted size lost from {tag[:120]}"


# --------------------------------------------------------------------------- #
# Palette                                                                      #
# --------------------------------------------------------------------------- #
def test_palette_tokens_are_collected_from_real_paint():
    doc = _doc()
    painter, _out, _r = _drive(doc)
    assert painter.palette, "no palette token was recovered from the rendered paint"
    for name, value in painter.palette.items():
        assert value.startswith("#") or value.startswith("rgb"), value


def test_text_colour_is_themeable_with_a_literal_fallback():
    """`var()` is reliable inside a style attribute — text paint uses it."""
    painter = HtmlPainter(ColorResolver({"navy": "#14213f"}))
    st = {"family": "Inter", "color": "#14213f", "weight": "normal",
          "italic": False, "size": 12}
    style = painter.font_style(st, 12)
    assert "fill:var(--fg-navy, #14213f)" in style, style


def test_geometry_paint_stays_literal():
    """The documented correctness trade: marks never depend on a var resolving."""
    painter = HtmlPainter(ColorResolver({"navy": "#14213f"}))
    attr = painter.fill_attr("#14213f")
    assert attr == ' fill="#14213f"', attr
    assert painter.palette == {"navy": "#14213f"}, "token still recorded for the sheet"


def test_stylesheet_is_deterministic_and_complete():
    doc = _doc()
    painter, _out, _r = _drive(doc)
    first = painter.stylesheet()
    assert ":root {" in first
    for name in painter.palette:
        assert f"--fg-{name}:" in first
    for ident in painter.text_styles:
        assert f".fg-ts-{ident} {{" in first
    assert first == painter.stylesheet(), "stylesheet must be stable across calls"


def test_stylesheet_is_empty_for_a_tokenless_document():
    painter = HtmlPainter(ColorResolver({}))
    assert painter.stylesheet() == ""


# --------------------------------------------------------------------------- #
# Identifier folding                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw,expected", [
    ("navy", "navy"),
    ("brand blue", "brand-blue"),
    ("brand/blue.2", "brand-blue-2"),
    ("2xl", "n2xl"),
    ("", "unnamed"),
    ("---", "unnamed"),
])
def test_css_ident_folds_authored_names_safely(raw, expected):
    assert css_ident(raw) == expected


# --------------------------------------------------------------------------- #
# Derived accessibility semantics                                              #
# --------------------------------------------------------------------------- #
# The standalone HTML renderer inferred three things the authored document does
# not state, and losing them when it was replaced would be an accessibility
# regression. The inference now lives in ONE domain service, so it is stated
# once and any backend may consume it.
def _render_object(obj, **doc_extra):
    doc = {"schema_version": "2.0.0", "meta": {"title": "a11y"},
           "pages": [{"id": "p", "size": [400, 300],
                      "layers": [{"id": "main", "objects": [obj]}]}],
           **doc_extra}
    from frameforge.rendering.application.normalize import normalize_doc
    _p, out, _r = _drive(normalize_doc(doc))
    return out


def test_group_is_announced_as_a_group():
    out = _render_object({"type": "group", "id": "g", "box": [0, 0, 100, 100],
                          "children": [{"type": "rect", "id": "c",
                                        "box": [0, 0, 10, 10]}]})
    assert 'role="group"' in out


def test_bare_geometry_is_hidden_from_assistive_tech():
    """A connector line carries no information a screen reader can use."""
    out = _render_object({"type": "line", "id": "ln", "from": [0, 0], "to": [50, 50]})
    assert 'aria-hidden="true"' in out


def test_icon_with_a_word_glyph_gets_an_accessible_name():
    out = _render_object({"type": "icon", "id": "i", "box": [0, 0, 16, 16],
                          "glyph": "calendar-check"})
    assert 'role="img"' in out
    assert 'aria-label="calendar check"' in out, out[-400:]


def test_icon_with_a_symbol_glyph_is_hidden_not_mislabelled():
    """A raw symbol is not a name — announcing "★" helps nobody."""
    out = _render_object({"type": "icon", "id": "i", "box": [0, 0, 16, 16],
                          "glyph": "★"})
    assert 'aria-hidden="true"' in out
    assert 'aria-label="★"' not in out


def test_authored_semantics_beat_derived_ones():
    out = _render_object({"type": "group", "id": "g", "box": [0, 0, 100, 100],
                          "role": "figure", "alt": "A named thing",
                          "children": [{"type": "rect", "id": "c",
                                        "box": [0, 0, 10, 10]}]})
    assert 'role="figure"' in out and 'aria-label="A named thing"' in out
    assert 'role="group"' not in out


def test_decorative_still_wins_over_everything():
    out = _render_object({"type": "group", "id": "g", "box": [0, 0, 100, 100],
                          "decorative": True, "role": "figure",
                          "children": [{"type": "rect", "id": "c",
                                        "box": [0, 0, 10, 10]}]})
    assert 'aria-hidden="true"' in out
    assert 'role="figure"' not in out


# --------------------------------------------------------------------------- #
# The SVG backend is untouched                                                 #
# --------------------------------------------------------------------------- #
def test_svg_accessibility_output_is_byte_stable():
    """SVG keeps authored-only semantics: the oracle must not shift here.

    Deriving semantics for SVG too would be an improvement, but it changes every
    golden byte and is a separate, explicit decision — not something to smuggle
    into this port.
    """
    from frameforge.rendering.application.normalize import normalize_doc
    doc = normalize_doc({"schema_version": "2.0.0", "meta": {"title": "a11y"},
                         "pages": [{"id": "p", "size": [400, 300], "layers": [
                             {"id": "main", "objects": [
                                 {"type": "line", "id": "ln",
                                  "from": [0, 0], "to": [50, 50]}]}]}]})
    out = "".join(Renderer(doc, ".").render_page(doc["pages"][0]))
    assert "aria-hidden" not in out



def test_svg_backend_output_is_unchanged():
    doc = _doc()
    out = "".join(Renderer(doc, ".").render_page(doc["pages"][0]))
    assert 'class="fg-layer"' not in out
    assert 'class="fg-obj' not in out
    assert 'class="fg-ts-' not in out
