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
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

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


def test_transform_ops_to_tikz_scope():
    # The neutral transform op list (StyleValues.transform_ops) drives TikZ scope
    # options — proving 3b-3b's value objects work across backends.
    p = TikzPainter()
    out = p.transform_group("BODY", [("translate", ["3", "4"]), ("scale", ["2"])])
    # `transform shape` extends the scope transform to \node text (#53)
    assert out == ("\\begin{scope}[transform shape,shift={(3,4)},"
                   "xscale=2,yscale=2]\nBODY\\end{scope}\n")
    rot = p.transform_group("X", [("rotate", ["30", "10", "20"])])
    assert "rotate around={30:(10,20)}" in rot
    mat = p.transform_group("X", [("matrix", ["1", "0", "0", "1", "5", "6"])])
    assert "cm={1,0,0,1,(5,6)}" in mat
    assert p.transform_group("X", []) == "X"          # empty ops -> no scope


def test_skew_op_converts_angle_to_tangent():
    p = TikzPainter()
    out = p.transform_group("X", [("skewX", ["45"])])
    assert "xslant=1" in out                          # tan(45deg) == 1


def test_image_node():
    p = TikzPainter()
    out = p.image(0, 0, 100, 50, "fig.png")
    assert "\\includegraphics[width=100pt,height=50pt,keepaspectratio]" in out
    assert "\\detokenize{fig.png}" in out
    assert "anchor=center" in out and "at (50,25)" in out
    # preserve_aspect_ratio="none" stretches (no keepaspectratio)
    assert "keepaspectratio" not in p.image(0, 0, 10, 10, "f.png", preserve_aspect_ratio="none")


def test_clip_registry_and_wrap():
    p = TikzPainter()
    p.new_page()
    cid = p.clip_rect(0, 0, 10, 20)
    assert cid == "clip1"
    wrapped = p.clip_wrap("BODY", cid)
    assert wrapped == "\\begin{scope}\n\\clip (0,0) rectangle (10,20);\nBODY\\end{scope}\n"
    # ellipse + polygon clip geometry
    assert "ellipse (4pt and 2pt)" in p._clips[p.clip_ellipse(5, 5, 4, 2)]
    assert p._clips[p.clip_polygon("0,0 10,0 5,10")] == "(0,0) -- (10,0) -- (5,10) -- cycle"
    assert p.clip_wrap("BODY", "nonexistent") == "BODY"   # unknown id -> passthrough


def _grad_painter():
    from framegraph.rendering.domain.services.paint_resolver import ColorResolver
    return TikzPainter(ColorResolver({}))


def test_gradient_handle_is_value_object():
    from framegraph.rendering.domain.services.paint_resolver import GradientPaint
    p = _grad_painter()
    g = p.gradient({"kind": "linear", "stops": [{"position": 0, "color": "#000"}]})
    assert isinstance(g, GradientPaint) and g.spec["kind"] == "linear"


def test_linear_gradient_rect_to_shade():
    p = _grad_painter()
    g = p.gradient({"kind": "linear", "angle": 90,
                    "stops": [{"position": "0%", "color": "#ff0000"},
                              {"position": "100%", "color": "#0000ff"}]})
    out = p.rect(0, 0, 100, 50, g, None)
    assert out == ("\\shade[left color={rgb,255:red,255;green,0;blue,0},"
                   "right color={rgb,255:red,0;green,0;blue,255}] "
                   "(0,0) rectangle (100,50);\n")


def test_vertical_gradient_uses_top_bottom():
    p = _grad_painter()
    g = p.gradient({"kind": "linear", "angle": 180,
                    "stops": [{"position": 0, "color": "#ffffff"},
                              {"position": 1, "color": "#000000"}]})
    assert "top color=" in p.rect(0, 0, 10, 10, g, None)


def test_gradient_circle_clips_shade():
    p = _grad_painter()
    g = p.gradient({"kind": "radial",
                    "stops": [{"position": 0, "color": "#fff"}, {"position": 1, "color": "#000"}]})
    out = p.circle(50, 50, 20, g, None)
    assert "\\clip (50,50) circle (20pt);" in out and "inner color=" in out


def test_gradient_with_stroke_keeps_outline():
    p = _grad_painter()
    g = p.gradient({"kind": "linear",
                    "stops": [{"position": 0, "color": "#aa0000"}, {"position": 1, "color": "#0000aa"}]})
    out = p.rect(0, 0, 10, 10, g, Stroke(color="#000000", width=2))
    assert "\\shade[" in out and "\\path[draw=" in out and "line width=2pt" in out


def test_non_hex_stop_falls_back_to_solid():
    # a stop colour that is not hex (a bare CSS name TikZ can't mix) bails to a
    # solid first-stop fill rather than emitting a broken \shade.
    p = _grad_painter()
    g = p.gradient({"kind": "linear",
                    "stops": [{"position": 0, "color": "red"}, {"position": 1, "color": "blue"}]})
    out = p.rect(0, 0, 10, 10, g, None)
    assert "\\shade" not in out and "fill=red" in out


def test_path_data_to_tikz():
    p = TikzPainter()
    # straight segments -> chained TikZ path
    out = p.path("M10 10 L20 20 Z", None, Stroke(color="#000000"))
    assert out == "\\path[draw={rgb,255:red,0;green,0;blue,0},line width=1pt] (10,10) -- (20,20) -- cycle;\n"
    # cubic curve -> .. controls .. syntax
    assert "controls" in p.path("M0 0 C5 5 10 10 15 15", "#ff0000", None)
    # empty/invalid d -> no output
    assert p.path("", None, None) == "" and p.path(None, None, None) == ""


def test_path_with_arrow_markers_uses_draw():
    p = TikzPainter()
    out = p.path("M0 0 L10 0", None, Stroke(color="#000000"),
                 markers=Markers(color="#000000", end=True))
    assert out.startswith("\\draw[->,")


def test_clip_path_d_registers_geometry():
    p = TikzPainter()
    p.new_page()
    cid = p.clip_path_d("M0 0 L10 0 L10 10 Z")
    assert p._clips[cid] == "(0,0) -- (10,0) -- (10,10) -- cycle"


def test_text_tag_node_with_font_and_anchor():
    p = TikzPainter()
    st = {"family": "serif", "size": 12, "weight": "normal", "italic": False,
          "color": "#222222", "align": "left", "lh": 1.2}
    out = p.text_tag(10, 20, 80, 16, "Hi", st)
    assert out == ("\\node[anchor=west,inner sep=0pt,"
                   "font=\\fontsize{12}{13.44}\\selectfont,text width=80pt,"
                   "align=flush left,text={rgb,255:red,34;green,34;blue,34}] "
                   "at (10,28) {Hi};\n")


def test_text_tag_font_macro_threaded():
    # the document's font-macro registry, threaded in, prefixes the font command
    p = TikzPainter(font_macro=lambda fam: "\\myserif ")
    st = {"family": "serif", "size": 10, "weight": "bold", "italic": True,
          "color": "#000000", "align": "center"}
    out = p.text_tag(0, 0, 40, 20, "T", st)
    assert "font=\\myserif \\fontsize{10}{11.2}\\selectfont\\bfseries\\itshape" in out
    assert "anchor=center" in out and "align=center" in out and "at (20,10)" in out


def test_text_tag_align_right_and_escape():
    p = TikzPainter()
    st = {"family": "sans", "size": 11, "weight": 700, "italic": False,
          "color": "#000000", "align": "end"}
    out = p.text_tag(0, 0, 30, 10, "a&b_c", st)
    assert "anchor=east" in out and "at (30,5)" in out and "\\bfseries" in out
    assert "{a\\&b\\_c}" in out                  # LaTeX-escaped content


def test_text_tag_valign_and_empty():
    p = TikzPainter()
    assert p.text_tag(0, 0, 10, 10, "", {"align": "left"}) == ""
    st = {"family": "serif", "size": 8, "color": "#000", "align": "left", "valign": "top"}
    assert "at (0,4)" in p.text_tag(0, 0, 20, 20, "x", st)   # valign top -> y + size/2


def test_backend_specific_handle_fallbacks():
    p = TikzPainter()
    # filter: no <filter> in TikZ -> inert handle + passthrough wrap
    assert p.filter_wrap("BODY", p.filter_effect("shadow", {})) == "BODY"
    # image_pattern: no TikZ fill -> None (shape renders unfilled)
    assert p.image_pattern("bg.png", 0, 0, 10, 10) is None
    # marker: unused (arrows go via Markers VO) -> empty
    assert p.marker("#000") == ""


def test_embedded_svg_falls_back_to_title_text():
    p = TikzPainter()
    out = p.embedded_svg(0, 0, 40, 20, viewbox="0 0 40 20", color="#ff0000",
                         title="E = mc^2", body="<path/>")
    assert "<path/>" not in out                       # foreign SVG dropped
    assert "{E = mc\\textasciicircum{}2}" in out      # title text preserved + escaped
    assert "text={rgb,255:red,255;green,0;blue,0}" in out and "at (20,10)" in out


def test_tikz_painter_covers_full_scenepainter_surface():
    # TikzPainter now implements the entire ScenePainter port surface, plus the
    # anchor/style_group helpers the builder calls.
    from framegraph.rendering.domain.ports import ScenePainter
    port_methods = {m for m in vars(ScenePainter) if not m.startswith("_")}
    missing = {m for m in port_methods if not hasattr(TikzPainter, m)}
    assert missing == set(), f"unexpected gaps: {missing}"
    assert hasattr(TikzPainter, "anchor") and hasattr(TikzPainter, "style_group")


def test_text_block_one_node_per_line():
    p = TikzPainter()
    st = {"family": "serif", "size": 12, "weight": "normal", "italic": False,
          "color": "#000000", "align": "start"}
    out = p.text_block(40, "start", st, 12, ["one", "two"], 10, 14.4)
    assert out.count("\\node[") == 2 and "anchor=base west" in out
    assert "at (10,40)" in out and "at (10,54.4)" in out      # baseline grid
    assert "{one}" in out and "{two}" in out


def test_text_runs_concatenates_font_groups():
    p = TikzPainter()
    base = {"family": "serif", "size": 12, "weight": "normal", "italic": False, "color": "#000000"}
    em = {**base, "italic": True, "color": "#ff0000"}
    out = p.text_runs(40, "middle", 30, base, 12, [("a", base), ("b", em)])
    assert out.count("\\node[") == 1 and "anchor=base" in out
    assert "\\itshape" in out and "\\color{{rgb,255:red,255;green,0;blue,0}}" in out
    assert "a}" in out and "b}" in out          # each run text closes its font group


def test_anchor_and_style_group():
    p = TikzPainter()
    assert p.anchor("center") == "middle" and p.anchor("left") == "start"
    assert p.style_group("X", {"visibility": "hidden"}) == ""          # hidden -> dropped
    assert p.style_group("X", {"opacity": "0.5"}) == "\\begin{scope}[opacity=0.5]\nX\\end{scope}\n"
    assert p.style_group("X", {"mix-blend-mode": "multiply"}) == "X"   # unsupported -> passthrough
