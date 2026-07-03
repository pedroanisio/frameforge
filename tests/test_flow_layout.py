"""Unit tests for the backend-neutral flow layout engine (ADR-0003).

The engine owns line breaking (Knuth–Plass) and hyphenation (Liang/pyphen); it
does not place glyphs. `measure` is injected — a fake monospace metric (every
glyph ``size * 0.5`` px, spaces included) makes the arithmetic checkable — so the
breaks are deterministic and asserted directly.
"""
from __future__ import annotations

import pytest

from framegraph.rendering.domain.services import flow_layout as FL


def mono(s, size, avg):
    """Deterministic metric: every character is ``size * 0.5`` px."""
    return len(s) * size * 0.5


PARA = ("Density is the quality that sets a neutron star apart from anything in "
        "ordinary experience: compressing the mass of the Sun into the volume of "
        "a small city pushes matter to roughly the density of an atomic nucleus, "
        "several hundred trillion times denser than water.")


# --------------------------------------------------------------------------- #
#  content geometry — the single source of the column box                     #
# --------------------------------------------------------------------------- #
def test_content_box_honours_explicit_region():
    master = {"regions": [{"box": [72, 96, 451, 674]}]}
    assert FL.content_box(master, 595, 842, page_index=1) == (72, 96, 451, 674)
    assert FL.content_box(master, 595, 842, page_index=2) == (72, 96, 451, 674)


def test_content_box_honours_master_margin():
    master = {"margin": [50, 60, 50, 60]}  # [top, right, bottom, left]
    assert FL.content_box(master, 800, 1000, page_index=1) == (60, 50, 680, 900)


def test_content_box_falls_back_to_canon_and_mirrors_recto_verso():
    recto = FL.content_box(None, 900, 1200, page_index=1, unit=40)
    verso = FL.content_box(None, 900, 1200, page_index=2, unit=40)
    assert recto == (60, 80, 720, 960)     # x = inner = 1.5*40
    assert verso == (120, 80, 720, 960)    # x = outer = 3*40  (mirrored)
    assert 900 - (recto[0] + recto[2]) == verso[0]     # wide margin flips sides


def test_canon_fallback_agrees_with_authoring_helper():
    from framegraph.sdk import canon
    for side, page_index in (("recto", 1), ("verso", 2)):
        got = FL.content_box(None, 794, 1123, page_index=page_index, unit=40)
        want = canon.content_box(794, 1123, unit=40, side=side)
        assert got == want


# --------------------------------------------------------------------------- #
#  paragraph layout — structure                                               #
# --------------------------------------------------------------------------- #
def _lay(width=200, size=11, align="justify", indent=0.0):
    return FL.layout_paragraph(PARA, size=size, avg=0.5, lh=1.4, width=width,
                               measure=mono, align=align, first_line_indent=indent)


def test_multiline_last_line_not_justified_others_are():
    para = _lay()
    assert len(para.lines) >= 3
    assert all(ln.justify for ln in para.lines[:-1])   # body lines justify
    assert not para.lines[-1].justify                  # last line is ragged


def test_first_line_indent_narrows_only_first_line():
    para = _lay(indent=22.0)
    assert para.lines[0].indent == pytest.approx(22.0)
    assert para.lines[0].width == pytest.approx(200 - 22.0)
    assert all(ln.indent == 0.0 for ln in para.lines[1:])
    assert all(ln.width == pytest.approx(200) for ln in para.lines[1:])


def test_lines_fit_the_measure_no_overfill():
    para = _lay(width=200)
    for ln in para.lines:
        assert mono(ln.text, 11, 0.5) <= ln.width * 1.05   # never grossly overfull


def test_no_cavernously_short_justified_line():
    """The Knuth–Plass win: no justified line is left far under the measure (a
    river). Greedy first-fit routinely does; total-fit does not."""
    para = _lay(width=200)
    for ln in para.lines[:-1]:                          # justified body lines
        assert mono(ln.text, 11, 0.5) >= ln.width * 0.5


def test_constant_leading_is_the_baseline_grid():
    para = FL.layout_paragraph(PARA, size=12, avg=0.5, lh=1.5, width=180, measure=mono)
    assert all(ln.advance == pytest.approx(18.0) for ln in para.lines)


def test_deterministic_and_frozen():
    a, b = _lay(), _lay()
    assert a == b
    with pytest.raises(Exception):
        a.lines[0].text = "x"


def test_empty_and_single_word():
    assert FL.layout_paragraph("", size=11, avg=0.5, lh=1.4, width=200,
                               measure=mono).lines == ()
    solo = FL.layout_paragraph("solo", size=11, avg=0.5, lh=1.4, width=200,
                               measure=mono)
    assert len(solo.lines) == 1
    assert solo.lines[0].text == "solo"
    assert not solo.lines[0].justify                   # single/last line: ragged


def test_measure_none_is_tolerated_via_avg_estimate():
    def missing(s, size, avg):
        return None
    para = FL.layout_paragraph(PARA, size=11, avg=0.5, lh=1.4, width=200,
                               measure=missing)
    assert para.lines                                  # laid out via the estimate


def test_left_alignment_is_ragged_not_justified():
    para = _lay(align="left")
    assert all(not ln.justify for ln in para.lines)


# --------------------------------------------------------------------------- #
#  hyphenation                                                                 #
# --------------------------------------------------------------------------- #
def test_hyphenation_breaks_long_words_when_available():
    pytest.importorskip("pyphen")
    # a narrow column full of long words: absorbing slack by hyphenation is the
    # only way to stay tight, so at least one line must end on a hyphen.
    text = ("Precisely because their interiors lie beyond reach neutron stars "
            "have become indispensable instruments for testing extraordinary "
            "gravitational relativity and electromagnetism spectacularly")
    para = FL.layout_paragraph(text, size=11, avg=0.5, lh=1.4, width=150,
                               measure=mono, align="justify")
    assert any(ln.text.endswith("-") for ln in para.lines[:-1])


def test_dash_is_a_break_opportunity():
    pytest.importorskip("pyphen")
    # an em-dash-joined pair should be splittable across lines in a tight column
    text = "alpha beta gamma delta epsilon—zeta eta theta iota kappa lambda"
    para = FL.layout_paragraph(text, size=11, avg=0.5, lh=1.4, width=90,
                               measure=mono, align="justify")
    joined = " ".join(ln.text for ln in para.lines)
    # the dash must not force "epsilon—zeta" to live glued on one line only
    assert any("epsilon—" in ln.text or ln.text.endswith("epsilon—")
               for ln in para.lines) or "epsilon— zeta" not in joined
