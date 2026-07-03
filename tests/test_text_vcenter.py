#!/usr/bin/env python3
"""
test_text_vcenter.py — regression for vertical centring of a single line of text
in its box (the "number in a badge sits high / flies to the top" defect).

Three bugs conspired here, all on the path that seats a badge number:

  1. text_style_resolver dropped the `v_align` shorthand (read `vertical_align`
     only), so `v_align: middle` never reached the renderer.
  2. A vertically-centred single line was seated on the *line-box* midpoint with a
     fixed 0.82x baseline ratio, so cap-only glyphs (digits, capitals) rode high.
  3. With no explicit vertical-align, a single line in a box taller than 2.4x the
     font *top-anchored* — throwing a badge number to the top of the shape.

The fix seats a single centred line on the box centre and defers the actual
centring to the SVG's own `dominant-baseline: central` (the font's real asc/desc
midpoint at draw time) — no hardcoded cap ratio, symmetric with how
`text-anchor: middle` centres horizontally. So the assertions check the emitted
`y` (deterministic geometry) AND that the centring attribute is present.
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")):
    if p not in sys.path:
        sys.path.insert(0, p)

from framegraph.sdk.conform import render_page_svgs  # noqa: E402


def _doc(style, box, text="8"):
    return {
        "dsl": "FrameGraph", "version": "2.3.0",
        "pages": [{
            "id": "p", "mode": "page", "canvas": {"size": [80, 96]},
            "layers": [{"id": "l", "objects": [
                {"type": "text", "box": list(box), "text": text, "style": style},
            ]}],
        }],
    }


def _first_text(doc):
    """(baseline_y, is_dominant_central) of the first <text> in the rendered SVG."""
    svg = render_page_svgs(doc)[0]
    m = re.search(r'<text\b[^>]*>', svg)
    assert m, f"no <text> in SVG: {svg[:400]}"
    tag = m.group(0)
    y = float(re.search(r'\by="(-?[\d.]+)"', tag).group(1))
    return y, ('dominant-baseline="central"' in tag)


def test_vmiddle_single_line_centres_on_box_centre():
    # v_align shorthand must resolve AND the line must seat on the box centre with
    # dominant-baseline, not the old 0.82 line-box baseline (which was 33.9 here).
    y, central = _first_text(_doc({"align": "center", "v_align": "middle", "font_size": 20},
                                  box=(10, 10, 40, 40)))
    assert abs(y - 30.0) < 0.5, f"baseline should be box centre 30, got {y}"
    assert central, "a centred single line must carry dominant-baseline=central"


def test_no_valign_single_line_centres_not_top():
    # tall box (h=56 > 2.4*size=48) with no v_align used to top-anchor (y~26.4).
    y, central = _first_text(_doc({"align": "center", "font_size": 20}, box=(10, 10, 40, 56)))
    assert abs(y - 38.0) < 0.5, f"baseline should be box centre 38, got {y}"
    assert central, "a lone line with no v_align must centre (dominant-baseline)"


def test_valign_top_single_line_unchanged():
    # explicit top still anchors at the box top (base = y + 0.82*size), no dominant-baseline.
    y, central = _first_text(_doc({"align": "center", "v_align": "top", "font_size": 20},
                                  box=(10, 10, 40, 40)))
    assert abs(y - (10 + 0.82 * 20)) < 0.5, f"top-anchored baseline moved: {y}"
    assert not central, "top-anchored text must NOT use dominant-baseline"


def test_multiline_still_top_anchors():
    # a wrapped paragraph keeps its first-line baseline near the box top, no centring.
    long = "one two three four five six seven eight nine ten eleven twelve"
    y, central = _first_text(_doc({"font_size": 12, "wrap": True}, box=(6, 6, 60, 80), text=long))
    assert y < 6 + 12 * 1.3, f"multi-line first baseline should top-anchor, got {y}"
    assert not central, "multi-line text must NOT use dominant-baseline"
