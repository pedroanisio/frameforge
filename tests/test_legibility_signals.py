#!/usr/bin/env python3
"""test_legibility_signals.py — READABILITY signals (the human-legibility gate).

FrameForge already reports what it *lost* (truncations, overflow, collisions).
This channel reports what it *kept but made unreadable*: type below the legible
floor, text that fails WCAG contrast against the ink actually painted behind it,
lines too long or too short to track, and leading too tight to separate them.

The contract these tests pin:

  * TYPED — every signal is the dict form of the frozen ``LegibilitySignal``
    (rendering.domain.services.legibility): page, code, level, value,
    threshold, unit, count, detail, basis.
  * UNIT-HONEST — type size is judged as a fraction of the page width (the only
    dpi-independent measure), with the pt equivalent of the SVG→PDF export path
    (1 canvas unit = 0.75 pt at cairosvg dpi=96) reported as the basis.
  * DRIFT-PROOF — every check reads the EMITTED SVG, the sink every visual
    feature must pass through, exactly like the design audit.
  * NO GUESSING — a backdrop the pass cannot resolve (transform in scope,
    gradient/pattern fill, unknown colour keyword) is reported as unverified,
    never assumed white (PALS's Law).
  * QUIET WHEN CLEAN — a well-set page emits nothing; the channel always
    exists, so consumers never branch on key presence.
  * PROPAGATED — the channel rides ``render_pages_with_stats(diagnostics=True)``
    and ``conform.legibility_report()``, and the MCP render warning names it.

Runs under pytest or standalone
(``uv run python tests/test_legibility_signals.py``).
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from frameforge.rendering.domain.services.legibility import (  # noqa: E402
    LegibilityPolicy,
    LegibilitySignal,
    assess_pages,
)


# --------------------------------------------------------------------------- #
#  helpers                                                                    #
# --------------------------------------------------------------------------- #
def svg(body: str, *, w: float = 794, h: float = 1123) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">{body}</svg>')


def text(s: str, *, size: float = 15, fill: str = "#1c1c1c", x: float = 40,
         y: float = 100, weight: str | None = None, dy: float | None = None,
         lines: list[str] | None = None) -> str:
    w = f";font-weight:{weight}" if weight else ""
    runs = lines or [s]
    # Built outside the f-string: quoting a nested f-string this way is PEP 701
    # (3.12+), and requires-python is >=3.10 — CI's 3.10 leg cannot parse it.
    def dy_attr(i: int) -> str:
        return f' dy="{dy}"' if dy is not None and i else ""
    spans = "".join(
        f'<tspan x="{x}"{dy_attr(i)}>{t}</tspan>'
        for i, t in enumerate(runs))
    return (f'<text y="{y}" style="font-family:Inter;font-size:{size}px;'
            f'fill:{fill}{w}">{spans}</text>')


def codes(signals: list[LegibilitySignal]) -> set[str]:
    return {s.code for s in signals}


WHITE_PAGE = '<rect width="100%" height="100%" fill="white"/>'


# --------------------------------------------------------------------------- #
#  type size                                                                  #
# --------------------------------------------------------------------------- #
def test_body_type_below_the_floor_is_flagged():
    """10 units on a 794-wide canvas (true A4 at 96 dpi) is 7.5 pt — the exact
    failure a reader meets as 'I cannot read this'."""
    page = svg(WHITE_PAGE + text("Body copy set far too small", size=10))
    signals = assess_pages([page])
    assert "type-too-small" in codes(signals)
    hit = next(s for s in signals if s.code == "type-too-small")
    assert hit.page == 1
    assert hit.level in {"warn", "error"}
    # the basis must state the physical equivalent, not just the ratio
    assert "7.5" in hit.basis and "pt" in hit.basis


def test_well_set_body_type_is_quiet():
    page = svg(WHITE_PAGE + text("Body copy set at a readable size", size=15))
    assert "type-too-small" not in codes(assess_pages([page]))


def test_type_floor_is_dpi_independent():
    """The same physical size on a points-based canvas must NOT be flagged:
    11.25 units on a 595-wide canvas is the same proportion as 15 on 794."""
    page = svg(WHITE_PAGE + text("Body copy", size=11.25, y=60), w=595, h=842)
    assert "type-too-small" not in codes(assess_pages([page]))


def test_severely_small_type_escalates_to_error():
    page = svg(WHITE_PAGE + text("Micro caption", size=6))
    hit = next(s for s in assess_pages([page]) if s.code == "type-too-small")
    assert hit.level == "error"


def test_repeated_small_type_is_aggregated_not_repeated():
    body = WHITE_PAGE + "".join(
        text(f"tiny line {i}", size=8, y=100 + 20 * i) for i in range(12))
    hits = [s for s in assess_pages([svg(body)]) if s.code == "type-too-small"]
    assert len(hits) == 1, "one signal per (page, size), with a count"
    assert hits[0].count == 12


# --------------------------------------------------------------------------- #
#  contrast (WCAG 2.1 SC 1.4.3)                                               #
# --------------------------------------------------------------------------- #
def test_low_contrast_text_on_page_background_is_flagged():
    page = svg(WHITE_PAGE + text("Grey on white", size=15, fill="#999999"))
    hit = next(s for s in assess_pages([page]) if s.code == "low-contrast")
    assert hit.threshold == pytest.approx(4.5)
    assert 2.5 < hit.value < 3.2  # #999 on #fff is ~2.85:1


def test_contrast_is_judged_against_the_rect_actually_painted_behind():
    """White-on-dark passes only if the pass resolves the dark rect; judging
    against the page background would wrongly fail it."""
    body = (WHITE_PAGE
            + '<rect x="0" y="80" width="794" height="120" fill="#222222"/>'
            + text("White on the dark band", size=15, fill="#ffffff", y=140))
    assert "low-contrast" not in codes(assess_pages([svg(body)]))

    body_bad = (WHITE_PAGE
                + '<rect x="0" y="80" width="794" height="120" fill="#222222"/>'
                + text("Dark on the dark band", size=15, fill="#333333", y=140))
    assert "low-contrast" in codes(assess_pages([svg(body_bad)]))


def test_large_text_uses_the_3_to_1_threshold():
    """WCAG large text (>= 24 CSS px, or >= 18.66 px bold) needs only 3:1."""
    page = svg(WHITE_PAGE + text("Big grey heading", size=30, fill="#949494"))
    hits = [s for s in assess_pages([page]) if s.code == "low-contrast"]
    assert not hits, "3.0:1 large-text threshold must apply"

    small = svg(WHITE_PAGE + text("Small grey label", size=15, fill="#949494"))
    assert "low-contrast" in codes(assess_pages([small]))


def test_unresolvable_backdrop_is_reported_not_assumed():
    body = ('<rect width="100%" height="100%" fill="url(#grad1)"/>'
            + text("Over an unknown ground", size=15, fill="#999999"))
    signals = assess_pages([svg(body)])
    assert "contrast-unverified" in codes(signals)
    assert "low-contrast" not in codes(signals), "must not guess a backdrop"


# --------------------------------------------------------------------------- #
#  measure and leading                                                        #
# --------------------------------------------------------------------------- #
def test_overlong_measure_is_flagged():
    long_line = "word " * 26  # ~130 characters
    page = svg(WHITE_PAGE + text("", size=15, lines=[long_line, long_line, long_line]))
    hit = next(s for s in assess_pages([page]) if s.code == "measure-too-long")
    assert hit.value > 100


def test_comfortable_measure_is_quiet():
    line = "A comfortable measure of roughly sixty-six characters here."
    page = svg(WHITE_PAGE + text("", size=15, lines=[line, line, line]))
    assert "measure-too-long" not in codes(assess_pages([page]))


def test_tight_leading_is_flagged():
    page = svg(WHITE_PAGE + text("", size=20, dy=20, lines=["one", "two", "three"]))
    hit = next(s for s in assess_pages([page]) if s.code == "leading-too-tight")
    assert hit.value == pytest.approx(1.0)


def test_normal_leading_is_quiet():
    page = svg(WHITE_PAGE + text("", size=20, dy=28, lines=["one", "two", "three"]))
    assert "leading-too-tight" not in codes(assess_pages([page]))


# --------------------------------------------------------------------------- #
#  canvas physical scale                                                      #
# --------------------------------------------------------------------------- #
def test_points_canvas_named_as_paper_reports_its_real_export_size():
    """The A4 preset is 595x842 canvas units; through the SVG->PDF path those
    export as 446x631 pt = 6.20x8.77 in, NOT ISO A4. Informational, because the
    proportions are internally consistent — but the author must be told."""
    page = svg(WHITE_PAGE + text("Body", size=11.25, y=60), w=595, h=842)
    hit = next(s for s in assess_pages([page]) if s.code == "print-scale-mismatch")
    assert hit.level == "info"
    assert "6.2" in hit.basis and "8.7" in hit.basis


def test_true_a4_canvas_has_no_scale_mismatch():
    page = svg(WHITE_PAGE + text("Body", size=15))
    assert "print-scale-mismatch" not in codes(assess_pages([page]))


# --------------------------------------------------------------------------- #
#  typed wire form + policy                                                   #
# --------------------------------------------------------------------------- #
def test_signal_round_trips_through_its_wire_form():
    page = svg(WHITE_PAGE + text("tiny", size=8))
    hit = next(s for s in assess_pages([page]) if s.code == "type-too-small")
    assert LegibilitySignal.from_dict(hit.to_dict()) == hit
    assert set(hit.to_dict()) == {
        "page", "code", "level", "value", "threshold", "unit", "count",
        "detail", "basis"}


def test_policy_thresholds_are_overridable():
    page = svg(WHITE_PAGE + text("Body copy", size=15))
    strict = LegibilityPolicy(min_size_fraction=1 / 30)
    assert "type-too-small" in codes(assess_pages([page], policy=strict))


def test_clean_page_emits_nothing():
    body = WHITE_PAGE + text("A properly set line of body copy on white paper.",
                             size=15, fill="#1c1c1c")
    assert assess_pages([svg(body)]) == []


# --------------------------------------------------------------------------- #
#  propagation                                                                #
# --------------------------------------------------------------------------- #
def test_channel_rides_the_render_diagnostics():
    from frameforge_sdk import DocumentBuilder
    from frameforge.conform import legibility_report

    doc = DocumentBuilder(title="legibility probe", profile="diagram")
    page = doc.page("p1", canvas={"size": [794, 1123]})
    page.rect([0, 0, 794, 1123], id="bg", style={"fill": "#ffffff"})
    page.text([40, 60, 600, 24], "Body copy set far too small to read", id="t1",
              style={"font_size": 10, "color": "#999999"})
    model = doc.build()

    signals = legibility_report(model)
    assert "type-too-small" in {s.code for s in signals}
    assert all(isinstance(s, LegibilitySignal) for s in signals)

    from frameforge.conform import render_pages_with_stats
    _svgs, _stats, diags = render_pages_with_stats(model, diagnostics=True)
    assert "legibility" in diags
    assert "type-too-small" in {d["code"] for d in diags["legibility"]}


def test_clean_document_has_an_empty_channel_not_a_missing_key():
    from frameforge_sdk import DocumentBuilder
    from frameforge.conform import render_pages_with_stats

    doc = DocumentBuilder(title="clean", profile="diagram")
    page = doc.page("p1", canvas={"size": [794, 1123]})
    page.rect([0, 0, 794, 1123], id="bg", style={"fill": "#ffffff"})
    page.text([40, 60, 600, 30], "Readable body copy on white paper.", id="t1",
              style={"font_size": 16, "color": "#1c1c1c"})
    _svgs, _stats, diags = render_pages_with_stats(doc.build(), diagnostics=True)
    assert diags.get("legibility") == []


def test_mcp_render_result_warns_and_carries_the_channel(tmp_path):
    """The surface an authoring agent actually reads: a render that produces
    unreadable output must NOT come back as a quiet ok:true."""
    import os as _os
    import sys as _sys

    root = _os.path.normpath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
    _sys.path[:0] = [root, _os.path.join(root, "src"), _os.path.join(root, "docs")]
    from frameforge_mcp.server import render_frameforge_yaml
    from frameforge_sdk import DocumentBuilder
    from frameforge_sdk.io import serialize

    b = DocumentBuilder(title="Unreadable Probe", profile="deck")
    p = b.page("p1", canvas={"size": [794, 1123], "units": "px"})
    layer = p.layer("main")
    layer.rect([0, 0, 794, 1123], fill="#ffffff")
    layer.text([40, 60, 700, 200], "Body copy an author believed was 10 pt.",
               style={"font_family": ["Inter", "sans-serif"], "font_size": 10,
                      "color": "#8a8a8a"})
    result = render_frameforge_yaml(serialize(b.build(), format="yaml"),
                                    session_root=str(tmp_path), raster_png=False)
    payload = result if isinstance(result, dict) else json.loads(result)

    codes_seen = {s["code"] for s in payload["diagnostics"]["legibility"]}
    assert "type-too-small" in codes_seen
    warning = (payload.get("render_warning") or "").lower()
    assert "legibility" in warning and "cannot read" in warning


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
