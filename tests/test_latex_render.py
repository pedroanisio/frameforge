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
    assert r"\makeindex" in tex


def test_render_latex_cli_tex_only_writes_tex(tmp_path):
    src = tmp_path / "latex-smoke.fg.yaml"
    src.write_text(yaml.safe_dump(DOC), encoding="utf-8")
    out = tmp_path / "out"

    rc = CLI.main([str(src), "--out", str(out), "--tex-only", "-q"])
    assert rc == 0

    tex_path = out / "latex-smoke.tex"
    assert tex_path.exists()
    tex = tex_path.read_text(encoding="utf-8")
    assert "\\begin{document}" in tex
    assert r"\(E = mc^2\)" in tex
    assert rf"\detokenize{{{tmp_path / 'assets' / 'logo a.png'}}}" in tex


def test_render_latex_cli_lists_only_flow_docs(tmp_path, capsys):
    flow = tmp_path / "flow.fg.yaml"
    page = tmp_path / "page.fg.yaml"
    flow.write_text(yaml.safe_dump(DOC), encoding="utf-8")
    non_flow = {**DOC, "pages": [{"id": "p", "layers": [{"objects": []}]}]}
    page.write_text(yaml.safe_dump(non_flow), encoding="utf-8")

    rc = CLI.main([str(tmp_path), "--list"])
    assert rc == 0
    listed = capsys.readouterr().out
    assert "flow.fg.yaml" in listed
    assert "page.fg.yaml" not in listed
