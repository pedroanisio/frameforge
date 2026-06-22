#!/usr/bin/env python3
"""Regression coverage for the LaTeX/TikZ rendering backend."""
from __future__ import annotations

import copy
import os
import sys

import yaml

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.infrastructure.latex import transpile  # noqa: E402
from tooling import render_latex as CLI  # noqa: E402


DOC = {
    "dsl": "FrameGraph",
    "version": "2.2.0",
    "profile": "report",
    "title": "LaTeX parity smoke",
    "defs": {
        "tokens": {
            "colors": {
                "ink": "#123456",
                "paper": "#ffffff",
                "rule": "#999999",
                "accent": "#e8302a",
            },
            "text_styles": {
                "body": {"font_family": "serif", "font_size": 11, "color": "ink"},
                "h1": {"font_family": "sans", "font_size": 18, "font_weight": 700, "color": "accent"},
                "fig_caption": {"font_family": "sans", "font_size": 9, "font_style": "italic", "color": "ink"},
            },
            "stroke_styles": {
                "arrow": {"color": "#123456", "width": 2, "arrow_end": True},
            },
        },
        "masters": {
            "article": {"canvas": {"size": [320, 240]}},
        },
        "assets": {
            "logo": {"src": "assets/logo a.png", "kind": "image", "media_type": "image/png"},
            "embedded": {"data": "data:image/png;base64,AAAA", "kind": "image"},
        },
        "symbols": {
            "dot": {
                "box": [0, 0, 10, 10],
                "objects": [{"type": "ellipse", "center": [5, 5], "rx": 5, "ry": 5, "fill": "accent"}],
            },
        },
    },
    "pages": [
        {
            "mode": "flow",
            "id": "p",
            "master": "article",
            "story": [
                {"type": "toc", "title": "Contents"},
                {"type": "heading", "level": 1, "id": "intro", "text": "A&B"},
                {
                    "type": "paragraph",
                    "spans": [
                        "Inline ",
                        {"kind": "math", "tex": r"E = mc^2"},
                        " and ",
                        {"kind": "link", "href": "https://example.org/a_b#c", "content": ["link_text"]},
                        " see ",
                        {"kind": "ref", "target": "eq-energy", "show": "label"},
                        " cited ",
                        {"kind": "cite", "key": ["einstein1905", "noether1918"], "prefix": "see", "locator": "p. 12"},
                        " note",
                        {"kind": "footnote", "content": [{"type": "paragraph", "text": "Footnote A&B"}]},
                        " code ",
                        {"kind": "code", "text": "x_y"},
                    ],
                },
                {"type": "spacer", "height": 9},
                {"type": "keep_together", "children": [{"type": "paragraph", "text": "Kept with next line."}]},
                {"type": "page_break"},
                {
                    "type": "image",
                    "src": "logo",
                    "width": 96,
                    "height": 24,
                    "caption": "Raster #1",
                    "credit": "Image credit",
                },
                {"type": "image", "src": "embedded", "alt": "Embedded image fallback"},
                {"type": "math", "tex": r"\int_0^1 x^2\,dx = \frac{1}{3}"},
                {"type": "math", "id": "eq-energy", "tex": r"E = mc^2"},
                {
                    "type": "figure",
                    "id": "fig-smoke",
                    "size": [120, 60],
                    "object": {
                        "type": "group",
                        "box": [0, 0, 120, 60],
                        "children": [
                            {"type": "rect", "box": [0, 0, 120, 60], "fill": "#f7f7f7", "stroke": "#333333"},
                            {"type": "use", "symbol": "dot", "box": [20, 20, 10, 10]},
                            {"type": "line", "from": [40, 30], "to": [95, 30], "stroke_style": "arrow"},
                            {"type": "text", "box": [45, 34, 50, 14], "text": "A_B", "style": "body"},
                            {"type": "path", "d": "M 6 52 L 24 52 L 15 42 Z", "fill": "accent"},
                            {"type": "curve", "from": [32, 52], "control1": [42, 42], "control2": [52, 62], "to": [62, 52], "stroke": "#333333"},
                            {"type": "icon", "glyph": "*", "box": [100, 8, 12, 12], "color": "accent"},
                            {"type": "bullet_list", "box": [70, 38, 42, 18], "items": ["one", "two"], "style": "fig_caption"},
                            {"type": "dimension", "kind": "linear", "from": [8, 8], "to": [38, 8], "value": "auto", "suffix": " pt"},
                            {"type": "table", "box": [78, 4, 36, 22], "rows": [["q", "r"], ["s", "t"]]},
                            {"type": "image", "box": [4, 18, 20, 14], "src": "diagram.png", "alt": "Diagram"},
                            {"type": "image", "box": [28, 18, 20, 14], "src": "logo", "alt": "Logo"},
                            {"type": "component", "box": [122, 0, 44, 24], "component": "Card", "title": "Panel", "body": "Body"},
                            {"type": "connector", "from": [120, 30], "to": [165, 30], "label": "link"},
                            {"type": "legend", "box": [122, 36, 70, 12], "items": [{"label": "Series", "color": "accent"}]},
                            {"type": "chip_row", "origin": [122, 50], "items": [{"text": "api", "width": 24}], "height": 10},
                            {"type": "bar_chart", "box": [170, 2, 24, 20], "data": [1, 3, 2]},
                            {"type": "line_chart", "box": [170, 30, 24, 20], "data": [1, 4, 2]},
                            {"type": "uml.classifier_box", "box": [196, 0, 48, 34], "name": "Order", "attributes": ["id"], "operations": ["total"]},
                            {"type": "uml.lifeline", "box": [196, 38, 40, 42], "name": "svc", "type_name": "API"},
                            {"type": "uml.actor", "box": [246, 0, 28, 42], "name": "User"},
                            {"type": "uml.activity_node", "box": [246, 46, 30, 22], "kind": "decision", "name": "ok?"},
                            {"type": "uml.pseudostate", "box": [278, 2, 16, 16], "kind": "final"},
                            {"type": "uml.marker_glyph", "position": [286, 34], "kind": "filled_diamond", "color": "accent"},
                            {"type": "uml.fragment_frame", "box": [296, 0, 44, 28], "kind": "alt"},
                            {"type": "uml.timing_lane", "box": [296, 34, 52, 24], "name": "clock", "states": ["A", "B"]},
                        ],
                    },
                    "caption": "Figure #1",
                },
                {
                    "type": "bibliography",
                    "title": "References",
                    "entries": [
                        {"id": "einstein1905", "text": "A. Einstein, 1905."},
                        {"id": "noether1918", "text": "E. Noether, 1918."},
                    ],
                },
            ],
        }
    ],
}


def test_transpile_emits_native_latex_math_and_tikz():
    tex = transpile(DOC)
    assert "\\documentclass" in tex
    assert "paperwidth=320pt,paperheight=240pt" in tex
    assert "A\\&B\\label{fg:intro}" in tex
    assert "\\tableofcontents" in tex
    assert r"\(E = mc^2\)" in tex
    assert r"\[" in tex and r"\int_0^1 x^2\,dx = \frac{1}{3}" in tex
    assert r"E = mc^2\label{fg:eq-energy}" in tex
    assert r"\href{https://example.org/a\_b\#c}{link\_text}" in tex
    assert r"\ref{fg:eq-energy}" in tex
    assert r"\cite[see, p. 12]{einstein1905,noether1918}" in tex
    assert r"\footnote{Footnote A\&B}" in tex
    assert r"\texttt{x\_y}" in tex
    assert r"\vspace{9pt}" in tex
    assert "\\begin{samepage}" in tex and "Kept with next line." in tex
    assert "\\clearpage" in tex
    assert r"\includegraphics[width=96pt,height=24pt,keepaspectratio]{\detokenize{assets/logo a.png}}" in tex
    assert "Raster \\#1" in tex
    assert "Image credit" in tex
    assert "Embedded image fallback" in tex
    assert "\\begin{tikzpicture}[x=1pt,y=-1pt]" in tex
    assert "rectangle (120,60)" in tex
    assert "ellipse (5pt and 5pt)" in tex
    assert "->" in tex
    assert "A\\_B" in tex
    assert "-- cycle" in tex
    assert ".. controls (42,42) and (52,62) .. (62,52)" in tex
    assert "{*}" in tex
    assert "{one}" in tex and "{two}" in tex
    assert "<->" in tex and "30 pt" in tex
    assert "{q}" in tex and "{t}" in tex
    assert "{Diagram}" in tex
    assert r"\includegraphics[width=20pt,height=14pt,keepaspectratio]{\detokenize{assets/logo a.png}}" in tex
    assert "{Panel}" in tex and "{Body}" in tex
    assert "{link}" in tex
    assert "{Series}" in tex
    assert "{api}" in tex
    assert "(173,15.333) rectangle" in tex
    assert "line width=1.2pt" in tex
    assert "{Order}" in tex and "{total}" in tex
    assert "{svc: API}" in tex
    assert "{User}" in tex and "{ok?}" in tex
    assert "{alt}" in tex
    assert "{clock}" in tex and "{A}" in tex and "{B}" in tex
    assert "Figure \\#1\\label{fg:fig-smoke}" in tex
    assert "\\begin{thebibliography}{99}" in tex
    assert "\\bibitem{einstein1905}A. Einstein, 1905." in tex


def test_transpile_emits_extended_latex_flow_controls():
    doc = copy.deepcopy(DOC)
    doc["defs"]["glossary"] = {
        "lagrangian": {"term": "Lagrangian", "definition": "Function for dynamics"},
    }
    doc["pages"][0]["story"] = [
        {
            "type": "paragraph",
            "spans": [
                "Indexed",
                {"kind": "index", "term": "Gauge field", "sort": "gauge field"},
                " term ",
                {"kind": "gloss", "term": "Lagrangian", "show": "short"},
                {"kind": "margin_note", "content": [{"type": "paragraph", "text": "Side A&B"}]},
                {"kind": "footnote", "content": [{"type": "paragraph", "text": "Collected note"}]},
            ],
        },
        {"type": "glossary", "title": "Glossary"},
        {"type": "endnotes", "title": "Notes"},
        {"type": "index", "title": "Concept Index", "columns": 2},
    ]

    tex = transpile(doc)

    assert r"Indexed\index{gauge field@Gauge field}" in tex
    assert r"Lagrangian\index{Lagrangian}" in tex
    assert r"\marginpar{\footnotesize Side A\&B}" in tex
    assert r"\textsuperscript{1}" in tex
    assert r"\item Collected note" in tex
    assert "Glossary" in tex
    assert r"\item[Lagrangian] Function for dynamics" in tex
    assert r"\renewcommand{\indexname}{Concept Index}" in tex
    assert r"\printindex" in tex
    assert r"\usepackage{makeidx}" in tex
    assert r"\usepackage[normalem]{ulem}" in tex
    assert r"\makeindex" in tex


def test_transpile_numbered_math_uses_equation_environment():
    doc = copy.deepcopy(DOC)
    doc["pages"][0]["story"] = [
        {"type": "math", "tex": "a=b"},
        {
            "type": "math",
            "id": "eq-numbered",
            "number": {"series": "equation", "prefix": "(", "suffix": ")"},
            "tex": "E=mc^2",
        },
        {
            "type": "paragraph",
            "spans": ["See ", {"kind": "ref", "target": "eq-numbered", "show": "number"}, "."],
        },
    ]

    tex = transpile(doc)

    assert "\\[\na=b\n\\]" in tex
    assert "\\begin{equation}\nE=mc^2\\label{fg:eq-numbered}\n\\end{equation}" in tex
    assert r"See \ref{fg:eq-numbered}." in tex


def test_transpile_uses_declared_token_fonts_for_flow_text():
    doc = copy.deepcopy(DOC)
    doc["defs"]["tokens"]["fonts"] = {
        "sans": {"family": "Inter"},
        "brand": {"family": "Source Serif 4"},
    }
    doc["defs"]["tokens"]["text_styles"]["body"]["font_family"] = "brand"
    doc["defs"]["tokens"]["text_styles"]["h1"]["font_family"] = "sans"
    doc["pages"][0]["story"] = [
        {"type": "heading", "level": 1, "text": "Head"},
        {"type": "paragraph", "text": "Body"},
    ]

    tex = transpile(doc)

    assert r"\IfFontExistsTF{Inter}{\newfontfamily\fgffa{Inter}}{\newcommand\fgffa{}}" in tex
    assert r"\IfFontExistsTF{Source Serif 4}{\newfontfamily\fgffb{Source Serif 4}}{\newcommand\fgffb{}}" in tex
    assert r"{\fgffa\fontsize{18}" in tex
    assert r"{\fgffb\fontsize{11}" in tex


def test_render_latex_cli_tex_only_writes_tex(tmp_path):
    src = tmp_path / "latex-smoke.fg.yaml"
    src.write_text(yaml.safe_dump(DOC), encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "logo a.png").write_bytes(b"not decoded in tex-only mode")
    out = tmp_path / "out"

    rc = CLI.main([str(src), "--out", str(out), "--tex-only", "-q"])
    assert rc == 0

    tex_path = out / "latex-smoke.tex"
    assert tex_path.exists()
    tex = tex_path.read_text(encoding="utf-8")
    assert "\\begin{document}" in tex
    assert r"\(E = mc^2\)" in tex
    assert rf"\detokenize{{{tmp_path / 'assets' / 'logo a.png'}}}" in tex


def test_transpile_page_mode_emits_full_page_tikz():
    doc = {
        "dsl": "FrameGraph",
        "version": "2.2.0",
        "pages": [
            {
                "mode": "page",
                "id": "p",
                "canvas": {"size": [200, 120]},
                "layers": [
                    {
                        "id": "l",
                        "objects": [
                            {"type": "rect", "box": [10, 20, 40, 30], "fill": "#ff0000"},
                            {"type": "text", "box": [20, 60, 80, 20], "text": "Page text"},
                        ],
                    }
                ],
            }
        ],
    }

    tex = transpile(doc)

    assert "paperwidth=200pt,paperheight=120pt" in tex
    assert "\\begin{tikzpicture}[x=1pt,y=-1pt]" in tex
    assert "\\path[use as bounding box] (0,0) rectangle (200,120);" in tex
    assert "rectangle (50,50)" in tex
    assert "Page text" in tex


def test_transpile_page_mode_text_spans_keep_run_styles():
    doc = {
        "dsl": "FrameGraph",
        "version": "2.2.0",
        "defs": {
            "tokens": {
                "colors": {"ink": "#111111", "muted": "#777777"},
                "fonts": {
                    "brand": {"family": "Source Serif 4"},
                    "label": {"family": "Inter"},
                },
                "text_styles": {
                    "base": {"font": "brand", "size": 16, "color": "ink"},
                    "label": {"font": "label", "size": 13, "weight": 700, "color": "muted"},
                    "emph": {"font": "brand", "size": 16, "italic": True, "color": "ink"},
                },
            }
        },
        "pages": [
            {
                "mode": "page",
                "id": "p",
                "canvas": {"size": [300, 120]},
                "layers": [
                    {
                        "objects": [
                            {
                                "type": "text",
                                "box": [20, 40, 260, 22],
                                "style": "base",
                                "spans": [
                                    {"text": "Label ", "style": "label"},
                                    {"text": "styled value", "style": "emph"},
                                ],
                            }
                        ]
                    }
                ],
            }
        ],
    }

    tex = transpile(doc)

    assert r"\IfFontExistsTF{Source Serif 4}{\newfontfamily\fgffa{Source Serif 4}}{\newcommand\fgffa{}}" in tex
    assert r"\IfFontExistsTF{Inter}{\newfontfamily\fgffb{Inter}}{\newcommand\fgffb{}}" in tex
    assert r"font=\fgffb\fontsize{13}{14.56}\selectfont\bfseries" in tex
    assert r"font=\fgffa\fontsize{16}{17.92}\selectfont\itshape" in tex
    assert "{Label }" in tex
    assert "{styled value}" in tex


def test_transpile_page_mode_emits_tikz_transform_scopes():
    doc = {
        "dsl": "FrameGraph",
        "version": "2.2.0",
        "pages": [
            {
                "mode": "page",
                "id": "p",
                "canvas": {"size": [770, 200]},
                "layers": [
                    {
                        "objects": [
                            {
                                "type": "rect",
                                "box": [48, 64, 58, 54],
                                "fill": "#2e86de",
                                "opacity": 0.82,
                                "style": {"transform": [{"fn": "translate_y", "args": [22]}]},
                            },
                            {
                                "type": "rect",
                                "box": [172, 64, 58, 54],
                                "fill": "#2e86de",
                                "style": {"transform": [{"fn": "scale_y", "args": [1.6]}]},
                            },
                            {
                                "type": "rect",
                                "box": [296, 64, 58, 54],
                                "fill": "#2e86de",
                                "style": {"transform": [{"fn": "skew_y", "args": [18]}]},
                            },
                            {
                                "type": "rect",
                                "box": [420, 64, 58, 54],
                                "fill": "#2e86de",
                                "style": {"transform": [{"fn": "rotate", "args": [20]}]},
                            },
                            {
                                "type": "rect",
                                "box": [544, 64, 58, 54],
                                "fill": "#2e86de",
                                "style": {
                                    "transform": [{"fn": "rotate", "args": [20]}],
                                    "transform_origin": [544, 64],
                                },
                            },
                            {
                                "type": "rect",
                                "box": [668, 64, 58, 54],
                                "fill": "#2e86de",
                                "style": {
                                    "transform": [
                                        {"fn": "translate_y", "args": [14]},
                                        {"fn": "rotate", "args": [16]},
                                    ],
                                },
                            },
                        ]
                    }
                ],
            }
        ],
    }

    tex = transpile(doc)

    assert r"\begin{scope}[opacity=0.82,shift={(0,22)}]" in tex
    assert r"\begin{scope}[shift={(201,91)},yscale=1.6,shift={(-201,-91)}]" in tex
    assert r"\begin{scope}[shift={(325,91)},yslant=0.325,shift={(-325,-91)}]" in tex
    assert r"\begin{scope}[rotate around={20:(449,91)}]" in tex
    assert r"\begin{scope}[rotate around={20:(544,64)}]" in tex
    assert r"\begin{scope}[shift={(0,14)},rotate around={16:(697,91)}]" in tex


def test_render_latex_cli_lists_framegraph_docs(tmp_path, capsys):
    flow = tmp_path / "flow.fg.yaml"
    page = tmp_path / "page.fg.yaml"
    flow.write_text(yaml.safe_dump(DOC), encoding="utf-8")
    non_flow = {**DOC, "pages": [{"id": "p", "layers": [{"objects": []}]}]}
    page.write_text(yaml.safe_dump(non_flow), encoding="utf-8")

    rc = CLI.main([str(tmp_path), "--list"])
    assert rc == 0
    listed = capsys.readouterr().out
    assert "flow.fg.yaml" in listed
    assert "page.fg.yaml" in listed
