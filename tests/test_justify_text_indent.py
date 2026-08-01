"""Justified absolute text honors ``style.text_indent`` on its first line.

The flow engine has supported ``first_line_indent`` in ``layout_paragraph``
since ADR-0003, and the style resolver surfaces ``text_indent`` — but the
absolute-text justify paths (plain and span-aware) never passed it through,
so a justified paragraph could not carry the book first-line indent.
"""

import re

from frameforge_sdk import DocumentBuilder, span
from frameforge.conform import render_page_svgs

IND = 24.0
X = 100
W = 300
TEXT = ("the quick brown fox jumps over the lazy dog and keeps running "
        "until the sentence is long enough to wrap across several lines "
        "of a narrow justified column without any trouble at all")


def _svg(*, indent, use_spans):
    b = DocumentBuilder(title="indent-fixture")
    p = b.page("p1", canvas={"size": [500, 400], "units": "px"},
               coordinate_mode="absolute")
    style = {"font_family": ["serif"], "font_size": 12, "line_height": 1.5,
             "align": "justify"}
    if indent:
        style["text_indent"] = IND
    content = ([span(TEXT[:40], font=["serif"]),
                span(TEXT[40:80], italic=True, font=["serif"]),
                span(TEXT[80:], font=["serif"])]
               if use_spans else TEXT)
    p.text([X, 50, W, 300], content, style=style)
    doc = b.build()
    return render_page_svgs(doc)[0]


def _line_xs(svg):
    """Start x of every emitted text line (the first tspan's x), in order."""
    out = []
    for m in re.finditer(r"<text[^>]*>(.*?)</text>", svg, re.S):
        t = re.search(r'<tspan[^>]*\bx="([0-9.]+)"', m.group(1))
        if t:
            out.append(float(t.group(1)))
    return out


def test_span_justify_first_line_indent():
    xs = _line_xs(_svg(indent=True, use_spans=True))
    assert len(xs) >= 3, "fixture must wrap to several lines"
    assert xs[0] == X + IND, f"first line should start at x+indent, got {xs[0]}"
    assert all(x == X for x in xs[1:]), f"later lines should sit at x, got {xs[1:]}"


def test_span_justify_no_indent_unchanged():
    xs = _line_xs(_svg(indent=False, use_spans=True))
    assert len(xs) >= 3
    assert all(x == X for x in xs), f"without text_indent every line sits at x, got {xs}"


def test_justified_shrink_lines_are_not_reported_clipped():
    """A KP shrink-set line measures naturally wider than the column but is
    painted flushed to it via textLength — the containment telemetry must not
    report it as width loss."""
    from frameforge.rendering.application.renderer import Renderer
    text = ("And now he will grind himself against it, she thought. Let him "
            "grind. A blade is not asked to forgive the whetstone. But he "
            "will not do it alone.")
    b = DocumentBuilder(title="shrink-fixture")
    p = b.page("p1", canvas={"size": [794, 1123], "units": "px"},
               coordinate_mode="absolute")
    p.text([130, 100, 534, 27 * 20],
           [span(text[:40], italic=True, font=["TeX Gyre Pagella", "serif"]),
            span(text[40:], font=["TeX Gyre Pagella", "serif"])],
           style={"font_family": ["TeX Gyre Pagella", "serif"], "font_size": 16,
                  "line_height": 1.6875, "align": "justify", "text_indent": 16})
    doc = b.build().model_dump(by_alias=True, exclude_none=True)
    r = Renderer(doc, ".")
    for page in doc.get("pages", []):
        r.render_page(page)
    trunc = (r.diagnostics or {}).get("truncations") or []
    assert not trunc, f"flushed shrink lines reported as loss: {trunc}"


def test_justified_overfull_last_line_is_compressed_not_clipped():
    """A KP shrink-set FINAL line has no flush flag; painting it at natural
    width pushes it past the column into the clip. The painter must compress
    it to the column (textLength) instead — TeX's overfull-last-line rule."""
    from frameforge.rendering.application.renderer import Renderer
    text = ("Paul gripped back and gave him the only true blessing he had: "
            "“The timing is good. I have seen the schedule boards in "
            "Carthag.”")
    b = DocumentBuilder(title="overfull-fixture")
    p = b.page("p1", canvas={"size": [794, 1123], "units": "px"},
               coordinate_mode="absolute")
    p.text([130, 100, 534, 27 * 30],
           [span(text[:30], italic=True, font=["TeX Gyre Pagella", "serif"]),
            span(text[30:], font=["TeX Gyre Pagella", "serif"])],
           style={"font_family": ["TeX Gyre Pagella", "serif"], "font_size": 16,
                  "line_height": 1.6875, "align": "justify", "text_indent": 16})
    doc = b.build().model_dump(by_alias=True, exclude_none=True)
    r = Renderer(doc, ".")
    for page in doc.get("pages", []):
        r.render_page(page)
    trunc = (r.diagnostics or {}).get("truncations") or []
    assert not trunc, f"overfull last line reported as loss: {trunc}"


def test_plain_justify_first_line_indent():
    svg = _svg(indent=True, use_spans=False)
    # The plain justified path emits one <text> block of tspans; the first
    # tspan must carry the indented x.
    tx = [float(m.group(1))
          for m in re.finditer(r'<tspan[^>]*\bx="([0-9.]+)"', svg)]
    assert len(tx) >= 3, "fixture must wrap to several lines"
    assert tx[0] == X + IND, f"first line should start at x+indent, got {tx[0]}"
    assert all(x == X for x in tx[1:]), f"later lines should sit at x, got {tx[1:]}"
