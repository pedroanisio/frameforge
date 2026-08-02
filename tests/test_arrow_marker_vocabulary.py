"""Arrow-marker vocabulary: validated at the model, screaming at the renderer.

The defect these pin (found 2026-07-27 processing external agent feedback): an
unknown `arrow_start`/`arrow_end` marker name was silently coerced to the
default filled triangle at `SvgPainter.marker()` — an agent probing `triangle`,
`arrow`, `open`, `dot`, `bar`, `concave` got seven byte-identical renders and
concluded markers are undifferentiated. Substitution must SCREAM (the
`font_substitution` precedent) and authored documents must fail validation with
the vocabulary in the message.

Three layers, one vocabulary:
  * model: `ArrowMarkerKind` Literal rejects unknown names at validation time;
  * renderer (raw-dict path, e.g. render_fixtures): `arrow_marker_fallback`
    warning + graceful default, in `diagnostics["warnings"]`;
  * painter: `_MARKER_SHAPES` stays the geometry authority — a sync test keeps
    the three statements of the vocabulary identical.
"""
from __future__ import annotations

import os
import sys
import typing

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):   # evict a models-module shadow
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import pydantic  # noqa: E402

import frameforge_api.model as fg  # noqa: E402
from frameforge_render.infrastructure.painters import svg as svg_painter  # noqa: E402
from tooling.render_fixtures import Renderer  # noqa: E402

VOCAB = ("filled_triangle", "hollow_triangle", "filled_diamond",
         "hollow_diamond", "open_arrow")


# --------------------------------------------------------------------------- #
#  Model layer                                                                 #
# --------------------------------------------------------------------------- #
def test_model_rejects_unknown_marker_kind_and_names_the_vocabulary():
    with pytest.raises(pydantic.ValidationError) as ei:
        fg.Style(arrow_end="triangle")
    msg = str(ei.value)
    for kind in VOCAB:
        assert kind in msg, f"validation message must list {kind!r}"


def test_model_rejects_unknown_kind_on_arrow_start():
    with pytest.raises(pydantic.ValidationError):
        fg.Style(arrow_start="dot")


@pytest.mark.parametrize("kind", list(VOCAB) + [True, False])
def test_model_accepts_vocabulary_and_booleans(kind):
    st = fg.Style(arrow_end=kind, arrow_start=kind)
    assert st.arrow_end == kind and st.arrow_start == kind


def test_document_with_unknown_kind_in_stroke_styles_fails_validation():
    # StrokeStyle is a projection of Style (model.py: `StrokeStyle = Style`),
    # so tokens.stroke_styles bundles must reject unknown kinds too.
    doc = {
        "dsl": "FrameForge", "version": "2.2.0",
        "defs": {"tokens": {"stroke_styles": {"bad": {"stroke": "#000",
                                                      "arrow_end": "concave"}}}},
        "pages": [{"mode": "page", "id": "p", "canvas": {"size": [100, 100]},
                   "layers": [{"id": "l", "objects": []}]}],
    }
    with pytest.raises(pydantic.ValidationError):
        fg.Document.model_validate(doc)


# --------------------------------------------------------------------------- #
#  Single source: Literal ⇄ exported tuple ⇄ painter geometry                  #
# --------------------------------------------------------------------------- #
def test_vocabulary_is_single_sourced():
    lit = set(typing.get_args(fg.ArrowMarkerKind))
    assert lit == set(VOCAB)
    assert set(fg.ARROW_MARKER_KINDS) == lit
    assert set(svg_painter._MARKER_SHAPES) == lit
    assert svg_painter._DEFAULT_MARKER in lit


# --------------------------------------------------------------------------- #
#  Renderer layer (raw-dict path bypasses pydantic — must warn, not silently   #
#  substitute)                                                                 #
# --------------------------------------------------------------------------- #
def _render(stroke_style):
    doc = {"pages": [{
        "mode": "page", "id": "p", "canvas": {"size": [100, 100], "units": "px"},
        "layers": [{"id": "l", "objects": [
            {"type": "line", "id": "edge1", "from": [0, 0], "to": [80, 0],
             "stroke": "#112233", "stroke_style": stroke_style}]}],
    }]}
    r = Renderer(doc, ".")
    svgs = r.render_page(doc["pages"][0])
    return "".join(svgs), r.diagnostics


def test_renderer_warns_and_falls_back_on_unknown_kind():
    svg, diags = _render({"arrow_end": "triangle"})
    # graceful degradation: the default filled triangle still renders …
    assert "<marker " in svg and 'marker-end="url(#' in svg
    assert "M0,0 L8,2.5 L0,5 Z" in svg              # _MARKER_SHAPES["filled_triangle"]
    # … but the substitution SCREAMS, with everything an agent needs to fix it.
    falls = [w for w in diags["warnings"] if w["kind"] == "arrow_marker_fallback"]
    assert len(falls) == 1
    w = falls[0]
    assert w["requested"] == "triangle"
    assert w["substituted"] == "filled_triangle"
    assert set(w["valid"]) == set(VOCAB)
    assert w["id"] == "edge1"
    for kind in VOCAB:
        assert kind in w["message"]


def test_renderer_warns_on_unknown_arrow_start_too():
    _, diags = _render({"arrow_start": "bar"})
    assert any(w["kind"] == "arrow_marker_fallback" and w["requested"] == "bar"
               for w in diags["warnings"])


@pytest.mark.parametrize("kind", list(VOCAB) + [True])
def test_renderer_stays_silent_on_valid_kinds(kind):
    svg, diags = _render({"arrow_end": kind})
    assert "<marker " in svg
    assert not [w for w in diags["warnings"] if w["kind"] == "arrow_marker_fallback"]


def test_renderer_emits_no_marker_and_no_warning_without_arrows():
    svg, diags = _render({"stroke_width": 2})
    assert "<marker " not in svg
    assert not [w for w in diags["warnings"] if w["kind"] == "arrow_marker_fallback"]
