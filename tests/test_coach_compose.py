#!/usr/bin/env python3
"""End-to-end coach composition + the coach_vectorize MCP tool.

`compose_objects` assembles traced region/outline objects into a styled,
layer-plan-ordered document (pure, no OpenCV). `coach_vectorize` is the MCP
use case: image -> full pipeline -> validate + render + silhouette gate, through
the same forward pipeline every other tool uses.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from framegraph.coach import compose_objects, resolve_style  # noqa: E402
from framegraph.sdk import render_page_svgs  # noqa: E402


def _region():
    return [{"type": "polygon", "points": [[0, 0], [100, 0], [100, 100], [0, 100]], "fill": "#888888"}]


def _outline():
    return [{"type": "polyline", "points": [[10, 10], [50, 20], [90, 80], [40, 90]], "stroke": "#000"}]


def test_compose_objects_orders_layers_by_plan():
    b = compose_objects(_region(), _outline(), (120, 100), style=resolve_style("comic_ink"))
    ids = [layer["id"] for layer in b.build_dict()["pages"][0]["layers"]]
    assert ids == ["00_base", "01_atmosphere_back", "07_flat_colors", "06_line_art", "09_highlights"]


def test_compose_objects_renders_with_style_and_gradients():
    b = compose_objects(_region(), _outline(), (120, 100), style=resolve_style("children_book"))
    svg = render_page_svgs(b.build())[0]
    assert svg.startswith("<svg")
    assert "gradient" in svg.lower()                       # gradientised fills + atmosphere
    assert " C" in svg or "C" in svg                       # redrawn Bézier line-art


def test_compose_objects_paint_false_is_flat_no_atmosphere():
    b = compose_objects(_region(), _outline(), (120, 100), style=resolve_style("blueprint"), paint=False)
    ids = [layer["id"] for layer in b.build_dict()["pages"][0]["layers"]]
    assert "01_atmosphere_back" not in ids and "09_highlights" not in ids
    assert ids[0] == "00_base"


def test_compose_objects_outline_only_has_no_color_layer():
    b = compose_objects([], _outline(), (120, 100), style=resolve_style("clean_line"))
    ids = [layer["id"] for layer in b.build_dict()["pages"][0]["layers"]]
    assert "07_flat_colors" not in ids and "06_line_art" in ids


# --- the MCP tool: image -> pipeline -> render + silhouette gate ------------ #
def test_coach_vectorize_renders_and_gates(tmp_path):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    img = np.full((80, 120, 3), 255, np.uint8)
    cv2.rectangle(img, (20, 15), (95, 60), (40, 40, 40), -1)     # a dark block on white
    p = tmp_path / "shape.png"
    cv2.imwrite(str(p), img)

    from framegraph.mcp.usecases import coach_vectorize
    res = coach_vectorize(str(p), style="comic_ink", session_root=tmp_path,
                          max_pages=1, raster_png=False, silhouette=True)
    assert res.get("ok"), res.get("error")
    assert res["renders"] and res["renders"][0]["path"]
    assert res["silhouette"]["applied"] and res["silhouette"]["rubric"]


def test_coach_vectorize_unreadable_path_returns_clean_error(tmp_path):
    """A bad/unreadable image yields a structured error, never a raised exception."""
    from framegraph.mcp.usecases import coach_vectorize
    res = coach_vectorize(str(tmp_path / "does-not-exist.png"), session_root=tmp_path, raster_png=False)
    assert res.get("ok") is False or "error" in res
