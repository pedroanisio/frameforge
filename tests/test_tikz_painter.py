#!/usr/bin/env python3
"""TikzPainter — the second ScenePainter backend (ADR 0001 slice 3b-5a).

Pins that the neutral value objects produced by the (backend-agnostic) Renderer —
`Stroke`, `Markers`, colour/`none` fills — drive correct TikZ from the same port
surface that drives SvgPainter. This is the concrete proof that 3b-2/3b-3's
parameter neutralization actually enables a non-SVG backend.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.infrastructure.painters.tikz import TikzPainter  # noqa: E402
from framegraph.rendering.domain.services.stroke_resolver import Markers, Stroke  # noqa: E402


def test_rect_fill_and_stroke_value_objects():
    p = TikzPainter()
    out = p.rect(0, 0, 10, 20, "#ff0000", Stroke(color="#000000", width=2))
    assert out == ("\\path[fill={rgb,255:red,255;green,0;blue,0},"
                   "draw={rgb,255:red,0;green,0;blue,0},line width=2pt] "
                   "(0,0) rectangle (10,20);\n")


def test_rect_radius_and_no_fill():
    p = TikzPainter()
    out = p.rect(5, 5, 10, 10, None, Stroke(color="#000000"), radius=3)
    # no fill opts; default line width 1; rounded corners
    assert out == ("\\path[draw={rgb,255:red,0;green,0;blue,0},line width=1pt,"
                   "rounded corners=3pt] (5,5) rectangle (15,15);\n")


def test_stroke_dash_cap_join_to_tikz():
    p = TikzPainter()
    s = Stroke(color="#000000", width=1, dash="4 2", linecap="round", linejoin="bevel")
    opts = ",".join(p._stroke_opts(s))
    assert "dash pattern=on 4pt off 2pt" in opts
    assert "line cap=round" in opts
    assert "line join=bevel" in opts


def test_line_markers_to_arrow_tip():
    p = TikzPainter()
    out = p.line(0, 0, 10, 0, Stroke(color="#000000"), markers=Markers(color="#000000", end=True))
    assert out.startswith("\\draw[->,draw=")
    both = p.line(0, 0, 10, 0, Stroke(color="#000000"), markers=Markers(color="#000000", start=True, end=True))
    assert both.startswith("\\draw[<->,")


def test_poly_open_vs_closed():
    p = TikzPainter()
    line = p.poly("polyline", "0,0 10,0 10,10", None, Stroke(color="#000000"))
    assert "cycle" not in line and "(0,0) -- (10,0) -- (10,10)" in line
    poly = p.poly("polygon", "0,0 10,0 10,10", "#00ff00", Stroke(color="#000000"))
    assert poly.endswith("-- cycle;\n") and "fill={rgb,255:red,0;green,255;blue,0}" in poly


def test_circle_and_ellipse():
    p = TikzPainter()
    assert p.circle(5, 5, 4, "none", None) == "\\path (5,5) circle (4pt);\n"
    assert p.ellipse(5, 5, 4, 2, "none", None) == "\\path (5,5) ellipse (4pt and 2pt);\n"


def test_group_and_document_wrappers():
    p = TikzPainter()
    p.new_page()
    assert p.group("BODY", translate=(3, 4)) == (
        "\\begin{scope}[shift={(3,4)}]\nBODY\\end{scope}\n")
    assert p.group("BODY") == "BODY"            # no-op group is bare content in TikZ
    doc = p.document(100, 200, "BODY")
    assert doc.startswith("\\noindent\\begin{tikzpicture}[x=1pt,y=-1pt]\n")
    assert "use as bounding box] (0,0) rectangle (100,200)" in doc
    assert doc.endswith("BODY\\end{tikzpicture}\n")


def test_gradient_url_fill_deferred():
    # url(#…) gradient fills are not yet supported (3b-5b); they must not emit
    # invalid TikZ — they simply contribute no fill option.
    p = TikzPainter()
    assert p._fill_opts("url(#grad1)") == []
