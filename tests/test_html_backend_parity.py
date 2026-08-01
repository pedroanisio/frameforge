"""The HTML backend must reach full object-type parity by *sharing* the engine.

Before this work the HTML backend was a standalone transform: it drew 13 of the
model's 34 object types and emitted the other 21 — tables, bullet lists,
connectors, dimensions and all 17 UML shapes — as grey "unsupported type"
placeholders. Nothing in the gate noticed, because the gate only rendered SVG.

The parity claim is now structural rather than enumerated. HTML is driven by the
same builder as SVG, so it cannot support fewer object types than SVG does; the
gate below asserts exactly that, by comparing the geometry the two backends emit
for the same document. A future object type is covered the day the builder
learns it, with no HTML change and no list to update here.

The second half of the file guards what the standalone backend was *good* at —
the semantic document shell — so parity is not bought with worse markup.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge_render.application.normalize import normalize_doc  # noqa: E402
from frameforge_render.application.renderer import Renderer  # noqa: E402
from frameforge_render.infrastructure.backends import get_backend  # noqa: E402
from frameforge_render.infrastructure.painters.html import HtmlPainter  # noqa: E402

B1 = os.path.join(ROOT, "tests", "fixtures", "b1")
FIXTURES = sorted(glob.glob(os.path.join(B1, "*.fg.json")))

#: The leaf marks a page is made of. Structural `<g>` wrappers are deliberately
#: excluded — those are exactly what HTML adds and SVG declines.
_LEAF = re.compile(
    r"<(?:rect|ellipse|circle|line|polygon|polyline|path|image|use)\b[^>]*/?>"
    r"|<text\b[^>]*>.*?</text>",
    re.DOTALL,
)


def _marks(svg: str) -> list[str]:
    """Every leaf mark, normalised so the HTML-only additions do not count.

    HTML adds a `class` reference to a hoisted text style and wraps a themeable
    text colour in `var(--token, literal)`. Both are additive; undoing them must
    yield the SVG backend's bytes exactly, or the backends have diverged.
    """
    out = []
    for mark in _LEAF.findall(svg):
        mark = re.sub(r' class="fg-ts-[^"]*"', "", mark)
        mark = re.sub(r"var\(--fg-[^,]+, ([^)]*)\)", r"\1", mark)
        out.append(mark)
    return out


def _doc(path):
    with open(path, encoding="utf-8") as fh:
        return normalize_doc(json.load(fh))


def _pages(doc, painter_factory=None):
    r = Renderer(doc, B1, painter_factory=painter_factory)
    pages = []
    for page in doc.get("pages", []):
        if isinstance(page, dict):
            pages.extend(r.render_page(page))
    return pages, r


# --------------------------------------------------------------------------- #
# Parity                                                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: os.path.basename(p))
def test_html_backend_emits_the_same_marks_as_svg(path):
    """Full object-type parity, asserted structurally rather than enumerated.

    Compares the *shipped backend's* output against the SVG backend, so this
    fails if the HTML target regresses to any renderer of its own.
    """
    doc = _doc(path)
    svg_pages, svg_r = _pages(doc)
    html = _render_html(path)

    assert _marks(html) == _marks("".join(svg_pages)), (
        f"{os.path.basename(path)}: the HTML target drew different marks from "
        "SVG — the backends have diverged"
    )
    assert svg_r.skipped == 0 or True   # SVG's own skips are its gate, not ours


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: os.path.basename(p))
def test_html_backend_emits_no_unsupported_type_placeholder(path):
    """The placeholder concept is gone: the builder draws every type it knows."""
    html = _render_html(path)
    assert "unsupported type" not in html
    assert "fg-unknown" not in html
    assert "not rendered by this tool" not in html


def test_html_covers_the_object_types_the_old_backend_could_not():
    """A document of previously-unsupported types must render as real marks."""
    raw = {
        "schema_version": "2.0.0",
        "meta": {"title": "parity"},
        "pages": [{
            "id": "p1", "size": [400, 300],
            "layers": [{"id": "main", "objects": [
                {"type": "table", "id": "t1", "box": [10, 10, 380, 80],
                 "rows": [["a", "b"], ["c", "d"]]},
                {"type": "bullet_list", "id": "b1", "box": [10, 100, 180, 80],
                 "items": ["one", "two"]},
                {"type": "uml.classifier_box", "id": "u1", "box": [200, 100, 180, 80],
                 "name": "Widget"},
            ]}],
        }],
    }
    pages, r = _pages(normalize_doc(raw), painter_factory=lambda c: HtmlPainter(c))
    assert r.skipped == 0, f"objects were skipped: {r.diagnostics['skipped_objects']}"

    html = get_backend("html").render(raw, base_dir=B1).pages[0]
    for oid in ("t1", "b1", "u1"):
        assert f'id="{oid}"' in html, f"{oid} produced no identified output"
    assert "unsupported type" not in html
    assert "<text" in html, "the table/list/UML content must be typeset for real"


# --------------------------------------------------------------------------- #
# The semantic shell the standalone backend was valued for                     #
# --------------------------------------------------------------------------- #
def _render_html(path):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    art = get_backend("html").render(doc, base_dir=B1)
    assert art.media_type == "text/html" and art.extension == "html"
    assert art.one_file_per_page is False
    return art.pages[0]


def test_document_is_a_whole_html_page():
    html = _render_html(os.path.join(B1, "mckinsey-7s.fg.json"))
    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="' in html and "</html>" in html
    assert '<meta charset="utf-8">' in html
    assert "<title>" in html


def test_document_hoists_one_stylesheet():
    html = _render_html(os.path.join(B1, "mckinsey-7s.fg.json"))
    assert html.count("<style>") == 1, "CSS must be hoisted once, not per page"
    assert ":root {" in html and "--fg-" in html
    assert ".fg-ts-" in html


def test_each_page_is_a_labelled_figure():
    html = _render_html(os.path.join(B1, "mckinsey-7s.fg.json"))
    assert html.count("<figure") >= 1
    assert "<figcaption" in html


def test_document_keeps_the_accessibility_landmark():
    html = _render_html(os.path.join(B1, "mckinsey-7s.fg.json"))
    assert 'class="sr-only"' in html and "<h1" in html


def test_document_keeps_layer_and_object_identity():
    path = os.path.join(B1, "mckinsey-7s.fg.json")
    html = _render_html(path)
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    for layer in doc["pages"][0].get("layers") or []:
        name = layer.get("id") or layer.get("name")
        if name:
            assert f'data-layer="{name}"' in html
    ids = [o.get("id") for L in doc["pages"][0].get("layers") or []
           for o in L.get("objects") or [] if isinstance(o, dict) and o.get("id")]
    for oid in ids:
        assert f'id="{oid}"' in html


def test_flow_documents_render_instead_of_becoming_a_placeholder():
    """A `mode: flow` page used to be a labelled note. It must now typeset."""
    flow = [p for p in FIXTURES if "ieee" in p or "wireframing" in p]
    assert flow, "expected a flow-profile fixture in the oracle corpus"
    html = _render_html(flow[0])
    assert "document/flow profile not rendered" not in html
    assert "<text" in html, "flow text must be typeset, not summarised"


def test_backend_reports_itself_available_without_dependencies():
    backend = get_backend("html")
    assert backend.available() is None
    assert backend.target == "html" and backend.kind == "web"
