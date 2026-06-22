#!/usr/bin/env python3
"""Regression coverage for the LaTeX/TikZ rendering backend."""
from __future__ import annotations

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
                {"type": "heading", "level": 1, "text": "A&B"},
                {
                    "type": "paragraph",
                    "spans": [
                        "Inline ",
                        {"kind": "math", "tex": r"E = mc^2"},
                        " and ",
                        {"kind": "link", "href": "https://example.org/a_b#c", "content": ["link_text"]},
                    ],
                },
                {"type": "math", "tex": r"\int_0^1 x^2\,dx = \frac{1}{3}"},
                {
                    "type": "figure",
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
            ],
        }
    ],
}


def test_transpile_emits_native_latex_math_and_tikz():
    tex = transpile(DOC)
    assert "\\documentclass" in tex
    assert "paperwidth=320pt,paperheight=240pt" in tex
    assert "A\\&B" in tex
    assert r"\(E = mc^2\)" in tex
    assert r"\[" in tex and r"\int_0^1 x^2\,dx = \frac{1}{3}" in tex
    assert r"\href{https://example.org/a\_b\#c}{link\_text}" in tex
    assert "\\begin{tikzpicture}[x=1pt,y=-1pt]" in tex
    assert "rectangle (120,60)" in tex
    assert "ellipse (5pt and 5pt)" in tex
    assert "->" in tex
    assert "A\\_B" in tex
    assert "Figure \\#1" in tex


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
