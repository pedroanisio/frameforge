"""A plain-text flow paragraph must be measured in ITS OWN face.

`emit_para` has two paths: the styled-spans path passed the paragraph's
resolved style into `Renderer.measure`, but the plain-`text` path did not — so
with `--real-metrics` on, a plain paragraph fell back to the 0.52-em average
estimate while a span-styled one used real glyph advances. Same document, same
face, two different line-break results (the ADR-0004 measure≠render hazard,
inside a single backend).

The regression is invisible in a sans (0.52 em is close to right) and severe in
an old-style serif: EB Garamond averages ~0.36 em, so the estimate over-measures
by ~43% and the engine breaks every line early, producing a ragged short column.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge_render.infrastructure import font_metrics as fmmod  # noqa: E402
from frameforge_render.infrastructure.font_metrics import FontMetrics  # noqa: E402
from tooling.render_fixtures import Renderer  # noqa: E402

WORDS = " ".join(["aaaa"] * 60)


def _doc(spans: bool):
    para = ({"type": "paragraph", "spans": [{"text": WORDS, "style": {"color": "#111111"}}]}
            if spans else {"type": "paragraph", "text": WORDS})
    return {
        "dsl": "FrameForge", "version": "2.5.0", "title": "t",
        # tokens live under `defs`, which is where the renderer reads them
        "defs": {"tokens": {"styles": {"body": {"font_family": ["Narrow"], "font_size": 10,
                                               "line_height": 1.4, "text_align": "left"}}},
                 "masters": {"m": {"canvas": {"size": [400, 400], "units": "px"},
                                   "margin": [20, 20, 20, 20],
                                   "regions": [{"id": "main", "box": [20, 20, 360, 360]}]}}},
        "pages": [{"mode": "flow", "id": "s", "master": "m", "media": "paged",
                   "story": [para]}],
    }


def _lines(doc, monkeypatch):
    """Number of laid-out text lines the flow engine emits for the paragraph."""
    narrow = FontMetrics({}, default_em=0.25, source_path="synthetic-narrow")
    monkeypatch.setattr(fmmod, "get_font_metrics", lambda fam, bold: narrow)
    r = Renderer(doc, ".", real_metrics=True)
    svg = r.render_page(doc["pages"][0])
    svg = svg[0] if isinstance(svg, (list, tuple)) else svg
    return str(svg).count("<text")


def test_plain_paragraph_uses_the_same_metrics_as_a_styled_one(monkeypatch):
    plain = _lines(_doc(spans=False), monkeypatch)
    styled = _lines(_doc(spans=True), monkeypatch)
    # 0.25-em advances: 360 px of column holds ~144 chars, so 300 chars of text
    # is ~3 lines. The estimate path (0.52 em) would need ~5.
    assert plain == styled, (
        f"plain paragraph laid out in {plain} lines, span-styled in {styled}: "
        "the plain path is not reaching the real font metrics"
    )
    assert plain <= 4, f"{plain} lines — measured on the estimate, not 0.25-em advances"


def _overflow(doc, monkeypatch, em: float = 0.25):
    """The typed layout-overflow signals a render of `doc` produces."""
    narrow = FontMetrics({}, default_em=em, source_path="synthetic-narrow")
    monkeypatch.setattr(fmmod, "get_font_metrics", lambda fam, bold: narrow)
    r = Renderer(doc, ".", real_metrics=True)
    for page in doc["pages"]:
        r.render_page(page)
    return r.diagnostics.get("overflow") or []


def test_plain_paragraph_does_not_report_phantom_overflow(monkeypatch):
    """`note_overwide_lines` must re-measure in the paragraph's OWN face.

    It re-measures each laid line to recover its natural width (LaidLine.width is
    the justify target, not the ink). The styled-spans path handed it the style;
    the plain path did not — so a line the engine had just fitted was re-measured
    on the 0.52-em estimate and reported as an ERROR-severity layout overflow.
    Every plain paragraph in any face narrower than the estimate raised one, which
    fails `validate --text-fit` and the repo's own overflow gate on correct output.
    """
    assert _overflow(_doc(spans=True), monkeypatch) == []       # was already clean
    assert _overflow(_doc(spans=False), monkeypatch) == [], (
        "a correctly fitted plain paragraph reported a layout overflow: the "
        "diagnostic is measuring in the wrong font"
    )


# --------------------------------------------------------------------------- #
# A justified line is compressed to its column by the shaper — not an overflow #
# --------------------------------------------------------------------------- #
# 3-letter words with a wide space (0.9 em): Knuth–Plass settles on 7-word lines
# whose natural ink is 159 px in a 150 px column, each inside the 18.9 px of
# inter-word shrink, and marks every one of them `justify`. The shaper then sets
# each to exactly 150 px via textLength. Deterministic — no font on the host.
WIDE_SPACE = {ord(" "): 0.9}
SEVEN = " ".join(["abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx"] * 5)


def _column_doc(text: str, width: int = 150):
    return {
        "dsl": "FrameForge", "version": "2.5.0", "title": "t",
        "defs": {"tokens": {"styles": {"body": {"font_family": ["Narrow"], "font_size": 10,
                                               "line_height": 1.4, "text_align": "justify"}}},
                 "masters": {"m": {"canvas": {"size": [width + 40, 400], "units": "px"},
                                   "margin": [20, 20, 20, 20],
                                   "regions": [{"id": "main", "box": [20, 20, width, 360]}]}}},
        "pages": [{"mode": "flow", "id": "s", "master": "m", "media": "paged",
                   "story": [{"type": "paragraph", "text": text}]}],
    }


def _signals(doc, monkeypatch):
    fm = FontMetrics(WIDE_SPACE, default_em=0.5, source_path="synthetic-wide-space")
    monkeypatch.setattr(fmmod, "get_font_metrics", lambda fam, bold: fm)
    r = Renderer(doc, ".", real_metrics=True)
    for page in doc["pages"]:
        r.render_page(page)
    return r.diagnostics.get("overflow") or []


def test_justified_lines_are_not_reported_as_width_overflow(monkeypatch):
    """Knuth–Plass admits a line whose natural ink exceeds the column when the
    inter-word shrink can absorb it (it skips only at r < -1), and the shaper
    then compresses that line to exactly `LaidLine.width`. Re-measuring such a
    line's natural width and calling it an overflow reports the ordinary
    operation of justification as an ERROR — enough of them to fail
    `validate --text-fit` and `make overflow` on correctly set output.

    The signal's own docstring scopes it to "an unbreakable box the engine admits
    at badness 1e5+". Those lines have no interior word gap, are never marked
    `justify`, and still report — see the test below.
    """
    assert _signals(_column_doc(SEVEN), monkeypatch) == [], (
        "justified prose reported width overflow: the shaper sets these lines to "
        "their column width, so their natural ink is not a spill"
    )


def test_an_unbreakable_token_wider_than_the_column_still_reports(monkeypatch):
    """The case the diagnostic exists for must survive the narrowing."""
    sig = _signals(_column_doc("x" * 60), monkeypatch)          # 300 px in a 150 px column
    assert sig, "a token wider than the column must still report"
    assert sig[0]["kind"] == "width"
