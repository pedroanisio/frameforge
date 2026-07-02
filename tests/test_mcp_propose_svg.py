#!/usr/bin/env python3
"""MCP ``propose_from_svg`` — ingest an SVG and optionally grade it by region.

Exposes the SVG ingestion lane (until now reachable only by writing a Python
client) as a first-class MCP verb, with optional region-level recolouring via the
SDK :func:`framegraph.sdk.region.region_grade`.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.mcp.server import propose_from_svg  # noqa: E402

SVG = (
    '<svg viewBox="0 0 100 100">'
    '<rect width="100" height="100" fill="#ffffff"/>'
    '<rect x="10" y="10" width="20" height="20" fill="#808080"/>'
    "</svg>"
)


def _yaml(result) -> str:
    return open(result["yaml_path"], encoding="utf-8").read()


def test_plain_ingest_renders_and_keeps_paint(tmp_path):
    result = propose_from_svg(svg_text=SVG, session_root=str(tmp_path), raster_png=False)
    assert result["ok"] is True
    assert result["validation"]["ok"] is True
    assert result["renders"], "expected at least one rendered page"
    assert "#ffffff" in _yaml(result)          # original paint preserved


def test_region_grade_recolours_by_region(tmp_path):
    regions = [{"box": [0, 0, 40, 40], "ramp": "#ff0000"}]
    result = propose_from_svg(
        svg_text=SVG, regions=regions, default_ramp="#0000ff",
        session_root=str(tmp_path), raster_png=False,
    )
    assert result["ok"] is True
    text = _yaml(result)
    assert "#ff0000" in text                   # small rect (centroid in region) → red
    assert "#0000ff" in text                   # big rect (no region) → default blue
    assert "#808080" not in text               # the graded paint replaced the original


def test_ramp_stops_accepted_as_pairs(tmp_path):
    regions = [{"box": [0, 0, 40, 40], "ramp": [[0.0, "#000000"], [1.0, "#00ff00"]]}]
    result = propose_from_svg(
        svg_text=SVG, regions=regions, session_root=str(tmp_path), raster_png=False,
    )
    assert result["ok"] is True
    # the #808080 (mid-luminance) small rect lands partway up the black→green ramp
    assert "#ff0000" not in _yaml(result)


def test_missing_input_is_a_structured_error(tmp_path):
    result = propose_from_svg(session_root=str(tmp_path), raster_png=False)
    assert result["ok"] is False and "error" in result
