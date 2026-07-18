#!/usr/bin/env python3
"""defs.params — the associative core: document parameters + expressions.

Parameters live in the document (not only in the authoring program); any
string field of the form "=expr" resolves against them before validation, so
geometry and labels stay driven by the same numbers. The evaluator is a
whitelisted arithmetic AST — never Python eval.
"""
from __future__ import annotations

import math
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from frameforge.sdk.params import eval_expr, resolve_params  # noqa: E402


def test_eval_arithmetic_and_math_whitelist():
    assert eval_expr("2*w + 3", {"w": 5}) == 13
    assert eval_expr("sin(pi/2)", {}) == pytest.approx(1.0)
    assert eval_expr("min(a, b) + sqrt(4)", {"a": 7, "b": 3}) == pytest.approx(5.0)
    assert eval_expr("-(w**2) % 7", {"w": 3}) == pytest.approx((-9) % 7)


def test_eval_rejects_everything_outside_the_whitelist():
    for bad in ("__import__('os')", "().__class__", "params['x']",
                "open('x')", "lambda: 1", "x if x else 0", "unknown_name"):
        with pytest.raises(ValueError):
            eval_expr(bad, {"x": 1})


def test_resolve_params_chains_and_walks_nested_structures():
    doc = {
        "defs": {"params": {"w": 120, "h": "=w/2", "margin": 10}},
        "pages": [{"mode": "page", "id": "p1",
                   "canvas": {"size": ["=w+2*margin", "=h+2*margin"], "units": "px"},
                   "layers": [{"id": "m", "objects": [
                       {"type": "rect", "box": ["=margin", "=margin", "=w", "=h"],
                        "fill": "#EEE"},
                       {"type": "text", "box": [0, 0, 100, 20], "text": "=w"},
                   ]}]}],
    }
    out = resolve_params(doc)
    assert out["pages"][0]["canvas"]["size"] == [140, 80]
    rect = out["pages"][0]["layers"][0]["objects"][0]
    assert rect["box"] == [10, 10, 120, 60]
    label = out["pages"][0]["layers"][0]["objects"][1]
    assert label["text"] == "120"                      # driven label, string-typed
    assert doc["pages"][0]["layers"][0]["objects"][0]["box"][2] == "=w"   # input untouched


def test_resolve_params_reports_unknown_names():
    with pytest.raises(ValueError, match="depth"):
        resolve_params({"defs": {"params": {"w": "=q+1"}}, "pages": []})


def test_plain_strings_and_docs_without_params_pass_through():
    doc = {"defs": {}, "pages": [{"mode": "page", "id": "p", "canvas": {"size": [10, 10]},
                                  "layers": [{"id": "m", "objects": [
                                      {"type": "text", "box": [0, 0, 5, 5],
                                       "text": "= not math =="}]}]}]}
    out = resolve_params(doc)
    assert out == doc


def _yaml(w):
    return f"""
dsl: FrameForge
version: "2.5.0"
title: params
profile: diagram
defs:
  params:
    w: {w}
    h: "=w/2"
pages:
  - mode: page
    id: p1
    canvas: {{size: [300, 200], units: px}}
    layers:
      - id: main
        objects:
          - {{type: rect, box: [0, 0, 300, 200], fill: "#FFFFFF"}}
          - {{type: rect, box: [20, 20, "=w", "=h"], fill: "#3355AA"}}
          - {{type: text, box: [20, 150, 200, 30], text: "=w", style: {{font_size: 20, color: "#111111"}}}}
"""


def test_pipeline_resolves_params_end_to_end(tmp_path):
    from frameforge.mcp.usecases import render_frameforge_yaml
    r1 = render_frameforge_yaml(_yaml(120), session_id="par1", session_root=tmp_path,
                                raster_png=False)
    assert r1["ok"] is True, r1.get("validation")
    svg = (tmp_path / "par1" / "page-001.svg").read_text(encoding="utf-8")
    assert 'width="120' in svg and ">120<" in svg.replace("\n", "")
    r2 = render_frameforge_yaml(_yaml(200), session_id="par2", session_root=tmp_path,
                                raster_png=False)
    svg2 = (tmp_path / "par2" / "page-001.svg").read_text(encoding="utf-8")
    assert 'width="200' in svg2
