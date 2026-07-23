"""Inline runs inherit their parent object's style; links survive every backend.

Three coupled contracts (GH P1-1 / P1-2 / P1-3):

**P1-1 — a run inherits its parent text object.** A ``text`` object's ``spans``
are inline runs *inside that object*, so a run declaring only ``{"color": ...}``
must keep the object's family, size and weight. ``Renderer._span_runs`` used to
resolve each span style from the DOCUMENT default instead, so
``TextStyleResolver.resolve`` re-materialised ``font-family`` from
``tokens.styles.body``. Visible defect: a monospaced code block whose runs carry
syntax colours rendered every coloured run in the UI sans face.

**P1-2 — the HTML backend keeps per-run styles.** It used to flatten ``spans``
into one plain string, dropping every run style, so the brand wordmark
(``"Frame"`` ink + ``"Forge"`` blue) and every ``fan()`` label inherited the
document body colour and vanished on a light ground.

**P1-3 — links are real in HTML too.** SVG already wraps an object ``href`` and
a ``{"kind": "link"}`` run in ``<a href>`` (``tests/test_link_render.py`` owns
that surface); HTML emitted none, so an exported page had zero clickable
elements. ``Page.links`` (the ``PageLink`` model) was rendered by no backend at
all.

The backends must AGREE: declared run properties are honoured, undeclared ones
are inherited, and an authored link is a real anchor everywhere.
"""

from __future__ import annotations

import re
import sys

# A codemod/models test earlier in the suite may cache the MODELS module as
# `frameforge`; evict that non-package shadow (see conftest.py's shadow rule).
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.rendering.application.renderer import Renderer  # noqa: E402
from frameforge.rendering.infrastructure.backends import html as fgh  # noqa: E402

MONO = ["IBM Plex Mono", "monospace"]


def _doc(objects, *, styles=None, links=None, title="Sample"):
    defs = {"tokens": {}}
    if styles:
        defs["tokens"]["styles"] = styles
    page = {
        "mode": "page", "id": "p1",
        "canvas": {"size": [800, 400], "units": "px"},
        "rendering": {"coordinate_mode": "absolute"},
        "layers": [{"id": "main", "z": 0, "objects": objects}],
    }
    if links:
        page["links"] = links
    return {"dsl": "FrameForge", "version": "2.0.0", "title": title,
            "defs": defs, "pages": [page]}


def _svg(doc) -> str:
    return "".join(Renderer(doc, ".").render_page(doc["pages"][0]))


def _runs(svg: str) -> list[str]:
    return re.findall(r'<tspan[^>]*style="([^"]*)"', svg)


def _obj_frag(html_out: str, oid: str) -> str:
    frag = html_out[html_out.index(f'id="{oid}"'):]
    return frag[:frag.index("</div>")]


# A code line: the object is monospace; the runs carry only colours.
CODE_OBJ = {
    "type": "text", "id": "code", "box": [0, 0, 600, 30],
    "style": {"font_family": MONO, "font_size": 16, "font_weight": 400},
    "spans": [
        {"text": "print", "style": {"color": "#12B0C3"}},
        {"text": "(x)", "style": {"color": "#FBFAF6"}},
    ],
}

# The brand lockup: one text, two coloured runs, no per-run family.
LOCKUP_OBJ = {
    "type": "text", "id": "lockup", "box": [0, 40, 400, 40],
    "style": {"font_family": ["Inter", "sans-serif"], "font_size": 24,
              "font_weight": 700},
    "spans": [
        {"text": "Frame", "style": {"color": "#15181E"}},
        {"text": "Forge", "style": {"color": "#1F4FD8"}},
    ],
}


# --------------------------------------------------------------------------- #
# P1-1 — SVG: a run inherits the parent object's font
# --------------------------------------------------------------------------- #
def test_svg_run_inherits_parent_font_family():
    """A run declaring only `color` must NOT re-declare the default family."""
    runs = _runs(_svg(_doc([CODE_OBJ])))
    assert runs, "expected per-run tspans"
    for style in runs:
        assert "IBM Plex Mono" in style, (
            f"run lost the object's monospace family: {style!r}")
        assert "Inter" not in style, f"run re-materialised a default family: {style!r}"


def test_svg_run_inherits_parent_size_and_weight():
    runs = _runs(_svg(_doc([LOCKUP_OBJ])))
    assert runs
    for style in runs:
        assert "font-size:24px" in style, f"run lost the object's size: {style!r}"
        assert "font-weight:700" in style, f"run lost the object's weight: {style!r}"


def test_svg_run_declared_property_still_wins():
    """Inheritance must not swallow what the run DOES declare."""
    obj = dict(CODE_OBJ, spans=[
        {"text": "bold", "style": {"font_weight": 700, "color": "#D23B2B"}},
        {"text": "plain", "style": {"color": "#1E9E5A"}},
    ])
    runs = _runs(_svg(_doc([obj])))
    assert "font-weight:700" in runs[0] and "#D23B2B" in runs[0]
    assert "font-weight" not in runs[1] and "#1E9E5A" in runs[1]
    assert "IBM Plex Mono" in runs[0], "an overriding run still inherits the family"


def test_svg_run_font_size_is_the_fitted_size_documented_limit():
    """PINNED LIMITATION: a per-run `font_size` is not honoured on this path.

    The text fitter measures and shrinks the whole object at ONE size, and the
    painter formats every run at that fitted size — mixed-size runs would break
    fit, justification and baseline placement together. Inheritance (P1-1) is
    about the properties a run does NOT declare; honouring a declared per-run
    size is a separate, larger change. This test exists so the limit is visible
    and cannot regress silently into a half-working state.
    """
    obj = dict(CODE_OBJ, spans=[{"text": "big", "style": {"font_size": 32}}])
    runs = _runs(_svg(_doc([obj])))
    assert "font-size:16px" in runs[0], "per-run size unexpectedly honoured"
    assert "font-size:32px" not in runs[0]


def test_svg_run_inherits_document_body_style_when_object_declares_none():
    """With no object style, runs still fall back to the document `body`."""
    doc = _doc(
        [{"type": "text", "id": "t", "box": [0, 0, 400, 30],
          "spans": [{"text": "a", "style": {"color": "#15181E"}}]}],
        styles={"body": {"font_family": ["Georgia", "serif"], "font_size": 18}},
    )
    runs = _runs(_svg(doc))
    assert "Georgia" in runs[0] and "font-size:18px" in runs[0]


def test_svg_run_without_style_is_unchanged():
    """Regression guard: a bare string run keeps using the object style."""
    obj = {"type": "text", "id": "t", "box": [0, 0, 400, 30],
           "style": {"font_family": MONO, "font_size": 16},
           "spans": ["plain ", {"text": "hot", "style": {"color": "#D23B2B"}}]}
    svg = _svg(_doc([obj]))
    assert "IBM Plex Mono" in svg and "#D23B2B" in svg


# --------------------------------------------------------------------------- #
# P1-2 — HTML: per-run styles reach the markup, and agree with SVG
# --------------------------------------------------------------------------- #
def test_html_emits_one_run_per_span_with_its_own_colour():
    out = fgh.render_document(_doc([LOCKUP_OBJ]))
    assert "#15181E" in out, "first run lost its colour"
    assert "#1F4FD8" in out, "second run lost its colour"


def test_html_runs_nest_inside_one_wrapper_span():
    """`.fg-text>span` is a block rule: sibling runs would stack vertically."""
    frag = _obj_frag(fgh.render_document(_doc([LOCKUP_OBJ])), "lockup")
    assert frag.count("<span") == 3, f"runs must nest in one wrapper: {frag!r}"


def test_html_run_does_not_re_declare_an_undeclared_family():
    frag = _obj_frag(fgh.render_document(_doc([CODE_OBJ])), "code")
    for style in re.findall(r'<span style="([^"]*)"', frag):
        assert "Inter" not in style, f"run re-materialised a default family: {style!r}"


def test_backends_agree_on_which_runs_are_coloured():
    """Cross-backend parity: same document, same set of authored run colours."""
    doc = _doc([CODE_OBJ, LOCKUP_OBJ])
    svg_colours = set(re.findall(r"fill:(#[0-9A-Fa-f]{6})", _svg(doc)))
    html_colours = set(re.findall(r"color:(#[0-9A-Fa-f]{6})", fgh.render_document(doc)))
    for authored in {"#12B0C3", "#FBFAF6", "#15181E", "#1F4FD8"}:
        assert authored in svg_colours, f"SVG dropped {authored}"
        assert authored in html_colours, f"HTML dropped {authored}"


# --------------------------------------------------------------------------- #
# P1-3 — links are real in HTML, as they already are in SVG
# --------------------------------------------------------------------------- #
LINK_OBJ = {
    "type": "text", "id": "nav", "box": [0, 0, 400, 30],
    "style": {"font_family": MONO, "font_size": 16},
    "spans": ["read the ",
              {"kind": "link", "href": "https://frameforge.hefestus.io/spec",
               "content": ["spec"]}],
}


def test_html_link_span_is_a_real_anchor():
    out = fgh.render_document(_doc([LINK_OBJ]))
    assert 'href="https://frameforge.hefestus.io/spec"' in out, (
        "HTML dropped an authored link — the run is inert text")
    frag = _obj_frag(out, "nav")
    assert "spec" in frag and "read the " in frag


def test_html_object_level_href_is_an_anchor():
    """Parity with SVG's object-level `href` (tests/test_link_render.py)."""
    out = fgh.render_document(_doc([
        {"type": "rect", "id": "cta", "box": [0, 0, 80, 40], "fill": "#1F4FD8",
         "href": "https://frameforge.hefestus.io"}]))
    assert 'href="https://frameforge.hefestus.io"' in out
    assert "<a " in out


def test_html_link_without_href_does_not_emit_an_empty_anchor():
    """Edge case: a link run missing `href` degrades to plain text."""
    obj = dict(LINK_OBJ, spans=[{"kind": "link", "content": ["nowhere"]}])
    frag = _obj_frag(fgh.render_document(_doc([obj])), "nav")
    assert "nowhere" in frag
    assert "<a " not in frag, "emitted an anchor with no destination"


def test_html_link_escapes_its_href():
    """A quote in the href must not break out of the attribute."""
    obj = dict(LINK_OBJ, spans=[
        {"kind": "link", "href": 'https://x.test/"><script>', "content": ["x"]}])
    out = fgh.render_document(_doc([obj]))
    assert "<script>" not in out, "href was not escaped"


def test_html_external_page_link_becomes_navigation():
    """`Page.links` (PageLink) was modelled but rendered by no backend."""
    out = fgh.render_document(_doc(
        [{"type": "rect", "id": "bg", "box": [0, 0, 10, 10]}],
        links=[{"to": "https://frameforge.hefestus.io", "external": True,
                "label": "Home", "relation": "external"},
               {"to": "p2", "relation": "next", "label": "Next page"}]))
    assert 'href="https://frameforge.hefestus.io"' in out, "external PageLink dropped"
    assert 'href="#page-p2"' in out, "internal PageLink dropped"
    assert "Home" in out and "Next page" in out
    assert 'rel="next"' in out, "PageLink.relation lost"


def test_html_page_links_are_a_labelled_nav_landmark():
    out = fgh.render_document(_doc(
        [{"type": "rect", "id": "bg", "box": [0, 0, 10, 10]}],
        links=[{"to": "p2", "label": "Next", "relation": "next"}]))
    assert "<nav" in out and "aria-label=" in out


def test_html_page_link_falls_back_to_its_target_when_unlabelled():
    """Edge case: PageLink.label is optional — never emit an empty anchor."""
    out = fgh.render_document(_doc(
        [{"type": "rect", "id": "bg", "box": [0, 0, 10, 10]}],
        links=[{"to": "p7"}]))
    assert 'href="#page-p7"' in out
    assert "><</a>" not in out and "></a>" not in out


def test_page_anchor_target_exists_for_internal_links():
    """An internal PageLink must have something to jump to."""
    out = fgh.render_document(_doc(
        [{"type": "rect", "id": "bg", "box": [0, 0, 10, 10]}],
        links=[{"to": "p1", "label": "Self"}]))
    assert 'id="page-p1"' in out, "no anchor target for an internal link"


# --------------------------------------------------------------------------- #
# Regression: the ORIGINAL failures, reproduced from the real authored sources
# --------------------------------------------------------------------------- #
def test_regression_code_panel_runs_stay_monospaced():
    """The exact defect: a mono code line whose runs carry only syntax colours.

    Reported from `static/examples/frameforge_landing.py`, whose code panel drew
    half its lines in the UI sans face. Every run must keep IBM Plex Mono and
    NONE may name the document's sans.
    """
    obj = {"type": "text", "id": "line", "box": [0, 0, 640, 26],
           "style": {"font_family": MONO, "font_size": 16, "font_weight": 400},
           "spans": [
               {"text": "from", "style": {"color": "#12B0C3"}},
               {"text": " frameforge.sdk ", "style": {"color": "#FBFAF6"}},
               {"text": "import", "style": {"color": "#12B0C3"}},
               {"text": " DocumentBuilder", "style": {"color": "#FBFAF6"}}]}
    doc = _doc([obj], styles={"body": {"font_family": ["Inter", "sans-serif"]}})
    for style in _runs(_svg(doc)):
        assert "IBM Plex Mono" in style
        assert "Inter" not in style


def test_regression_brand_wordmark_keeps_both_colours_in_html():
    """The other original defect: `wordmark()` — one text, two coloured runs.

    Both runs vanished in HTML (flattened to a plain string, so they inherited
    the document body colour and went near-white on a light ground).
    """
    out = fgh.render_document(_doc([LOCKUP_OBJ]))
    frag = _obj_frag(out, "lockup")
    assert "Frame" in frag and "Forge" in frag
    assert "#15181E" in frag and "#1F4FD8" in frag


def test_regression_fan_labels_are_not_the_body_colour_in_html():
    """`fan()` labels are single-run coloured spans on a light ground."""
    obj = {"type": "text", "id": "label", "box": [0, 0, 360, 35],
           "style": {"font_family": MONO, "font_size": 16, "font_weight": 600},
           "spans": [{"text": "frameforge-v2.schema.json",
                      "style": {"color": "#15181E"}}]}
    frag = _obj_frag(fgh.render_document(_doc([obj])), "label")
    assert "#15181E" in frag, "the label lost its ink colour"


# --------------------------------------------------------------------------- #
# Edge cases
# --------------------------------------------------------------------------- #
def test_empty_spans_list_renders_nothing_but_does_not_crash():
    obj = {"type": "text", "id": "t", "box": [0, 0, 100, 20], "spans": []}
    assert "id=\"t\"" in fgh.render_document(_doc([obj]))
    _svg(_doc([obj]))


def test_span_with_empty_style_dict_inherits_everything():
    obj = dict(CODE_OBJ, spans=[{"text": "x", "style": {}}])
    style = _runs(_svg(_doc([obj])))[0]
    assert "IBM Plex Mono" in style and "font-size:16px" in style


def test_span_style_by_token_name_also_inherits():
    """A run may name a `tokens.styles` entry, not just an inline dict."""
    doc = _doc(
        [dict(CODE_OBJ, spans=[{"text": "x", "style": "hot"}])],
        styles={"hot": {"color": "#D23B2B"}},
    )
    style = _runs(_svg(doc))[0]
    assert "#D23B2B" in style, "token-named run style lost its colour"
    assert "IBM Plex Mono" in style, "token-named run style lost the inherited family"


def test_run_does_not_inherit_box_only_properties():
    """`max_lines`/`overflow` belong to the box, never to an inline run."""
    from frameforge.rendering.domain.services.text_style_resolver import (
        TextStyleResolver, INHERITED_TEXT_PROPERTIES)
    r = TextStyleResolver({}, {}, _NullColor())
    base = r.resolve({"font_family": "mono", "max_lines": 3, "overflow": "hidden",
                      "direction": "rtl"})
    run = r.resolve({"color": "#111"}, base)
    assert run["max_lines"] is None, "a run inherited a box property"
    assert run["overflow"] is None, "a run inherited a box property"
    assert run["direction"] == "rtl", "an inheritable property was lost"
    for key in ("overflow", "max_lines", "valign", "text_overflow", "min_font_size"):
        assert key not in INHERITED_TEXT_PROPERTIES


def test_run_does_not_re_emit_metric_affecting_properties():
    """A run must NOT re-declare properties that change its rendered width.

    The fitter measures a line ONCE from the object's base style, with a
    per-character estimate that models none of these. The run already inherits
    them through CSS (it lives inside the parent `<text>`/`<div>`), so
    re-emitting them buys nothing — but it would let the run's drawn width drift
    from the width that was measured for it, which is how text starts
    overflowing its box. Pinned after a first cut of this change re-emitted
    `letter-spacing`/`hyphens` on every run and moved four golden pages.
    """
    from frameforge.rendering.domain.services.text_style_resolver import (
        TextStyleResolver, INHERITED_TEXT_PROPERTIES)
    metric_affecting = (
        "letter_spacing", "word_spacing", "font_stretch", "text_transform",
        "font_variant", "font_variant_caps", "font_variant_numeric",
        "font_variant_ligatures", "font_feature_settings",
        "font_variation_settings", "font_kerning", "tab_size", "hyphens",
        "hanging_punctuation", "hyphenate_character", "hyphenate_limit_chars",
    )
    for key in metric_affecting:
        assert key not in INHERITED_TEXT_PROPERTIES, (
            f"{key} changes rendered width but is not modelled by the fitter")

    r = TextStyleResolver({}, {}, _NullColor())
    base = r.resolve({"font_family": "serif", "letter_spacing": "0.35em"})
    run = r.resolve({"color": "#111"}, base)
    assert run["letter_spacing"] is None, "run re-emitted a metric-affecting property"


class _NullColor:
    @staticmethod
    def resolve(v):
        return v


def test_resolve_without_base_is_unchanged():
    """The no-base path must be byte-identical — every existing caller uses it."""
    from frameforge.rendering.domain.services.text_style_resolver import TextStyleResolver
    r = TextStyleResolver({}, {}, _NullColor())
    assert r.resolve({"color": "#111"}) == r.resolve({"color": "#111"}, None)


# --------------------------------------------------------------------------- #
# Integration paths: SDK authoring, the flow renderer, and a real end-to-end
# --------------------------------------------------------------------------- #
def test_sdk_authored_spans_inherit_through_the_builder():
    """The SDK is the authoring front door — inheritance must survive lowering."""
    from frameforge.sdk import DocumentBuilder
    b = DocumentBuilder(title="t", profile="diagram")
    page = b.page("p", canvas={"size": [400, 100], "units": "px"},
                  coordinate_mode="absolute")
    page.text([0, 0, 380, 30],
              [{"text": "Frame", "style": {"color": "#15181E"}},
               {"text": "Forge", "style": {"color": "#1F4FD8"}}],
              style={"font_family": MONO, "font_size": 18, "font_weight": 700})
    doc = b.build_dict()
    for style in _runs(_svg(doc)):
        assert "IBM Plex Mono" in style, "SDK-authored run lost the family"
        assert "font-weight:700" in style, "SDK-authored run lost the weight"


def test_flow_paragraph_spans_inherit_the_paragraph_style():
    """The flow lane shares `_span_runs`; a wrapped paragraph must inherit too."""
    doc = {
        "dsl": "FrameForge", "version": "2.0.0", "title": "f",
        "defs": {"tokens": {"styles": {"body": {"font_family": ["Inter", "sans-serif"]}}}},
        "pages": [{
            "mode": "flow", "id": "f1",
            "canvas": {"size": [400, 300], "units": "px"},
            "story": [{"type": "paragraph",
                       "style": {"font_family": MONO, "font_size": 14},
                       "spans": ["plain ", {"text": "hot", "style": {"color": "#D23B2B"}}]}],
        }],
    }
    svg = "".join(Renderer(doc, ".").render_page(doc["pages"][0]))
    assert "#D23B2B" in svg, "flow run lost its colour"
    assert "IBM Plex Mono" in svg, "flow run lost the paragraph family"


def test_end_to_end_html_export_of_a_linked_styled_document():
    """One document -> HTML: runs keep colour, links are anchors, nav exists."""
    doc = _doc(
        [LOCKUP_OBJ,
         {"type": "text", "id": "cta", "box": [0, 90, 400, 30],
          "style": {"font_size": 16},
          "spans": ["read the ", {"kind": "link", "content": ["spec"],
                                  "href": "https://frameforge.hefestus.io/spec"}]},
         {"type": "rect", "id": "btn", "box": [0, 130, 80, 30],
          "fill": "#1F4FD8", "href": "https://frameforge.hefestus.io"}],
        links=[{"to": "p2", "label": "Next", "relation": "next"}],
    )
    out = fgh.render_document(doc)
    assert out.count("<a ") >= 3, "expected an inline link, an object link and a nav link"
    assert "#15181E" in out and "#1F4FD8" in out
    assert "<nav" in out
    # the document still parses as one well-formed tree
    assert out.count("<a ") == out.count("</a>")


def test_regression_bold_run_inside_an_italic_grey_note():
    """The oracle corpus proved the OLD output wrong (tests/fixtures/b1).

    `ieee-reference-guide` authors a `note` paragraph (serif, grey `muted`,
    italic) containing a run styled `b` == `{"weight": "bold"}` — nothing else.
    Before inheritance, that run rendered BLACK and UPRIGHT: asking for "bold"
    silently reset the colour and dropped the italic. This pins the corrected
    behaviour that re-pinned the golden lock.
    """
    doc = _doc(
        [{"type": "text", "id": "note", "box": [0, 0, 400, 40], "style": "note",
          "spans": [{"text": "Scope note.", "style": "b"}, " The rest."]}],
        styles={"note": {"font": "serif", "size": 9.5, "color": "#5a5a5a",
                         "italic": True, "line_height": 1.3},
                "b": {"weight": "bold"}},
    )
    run = _runs(_svg(doc))[0]
    assert "font-weight:bold" in run, "the run's own declaration was lost"
    assert "#5a5a5a" in run, "bold run reset the paragraph colour to the default"
    assert "font-style:italic" in run, "bold run dropped the paragraph italic"
