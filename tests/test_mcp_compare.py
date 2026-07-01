#!/usr/bin/env python3
"""The compare_images tool must let an agent *see* where a recreation is off.

It crops matching regions from a reference and a candidate, lays them out
reference|candidate|difference, and stamps a naive pixel-match score. These tests
pin the metric's endpoints, the panel composition, the end-to-end result shape (image
content blocks + per-region metrics), input-path confinement, and session-URI input.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

pytest.importorskip("PIL")

from PIL import Image  # noqa: E402

from framegraph.mcp.server import compare_images, mcp_content_blocks  # noqa: E402
from framegraph.mcp.sessions import _prepare_session  # noqa: E402
from framegraph.vision.infrastructure.image_compare import (  # noqa: E402
    Region,
    auto_regions,
    build_panels,
    pixel_match,
)


def _png(path, color, size=(240, 180)):
    Image.new("RGB", size, color).save(path, format="PNG")
    return str(path)


def _png_bytes(color, size=(240, 180)) -> bytes:
    from io import BytesIO

    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_pixel_match_endpoints():
    """Identical crops score 100; opposite (black vs white) scores ~0."""
    black = Image.new("RGB", (64, 64), (0, 0, 0))
    white = Image.new("RGB", (64, 64), (255, 255, 255))
    assert pixel_match(black, black) == 100.0
    assert pixel_match(black, white) <= 1.0


def test_build_panels_overview_plus_one_per_region():
    """build_panels emits an overview then one composed panel per region."""
    ref = _png_bytes((20, 20, 20))
    cand = _png_bytes((240, 240, 240))
    regions = [Region("top", (0.0, 0.0, 1.0, 0.5)), Region("bottom", (0.0, 0.5, 1.0, 0.5))]
    panels = build_panels(ref, cand, regions=regions, diff=True)

    assert [p.name for p in panels] == ["overview", "top", "bottom"]
    for panel in panels:
        assert panel.image.width > 0 and panel.image.height > 0
        assert 0.0 <= panel.match_pct <= 100.0
    # dark-vs-light regions must read as a clearly low match, not a false pass
    assert panels[1].match_pct <= 20.0


def test_auto_regions_grid_covers_image():
    regions = auto_regions(2, 3)
    assert len(regions) == 6
    assert regions[0].box == (0.0, 0.0, 0.5, 1 / 3)
    assert all(0.0 <= v <= 1.0 for r in regions for v in r.box)


def test_compare_images_writes_panels_and_surfaces_metrics(tmp_path):
    """End to end: PNGs on disk, image content blocks, and per-region match scores."""
    ref = _png(tmp_path / "ref.png", (18, 18, 22))
    cand = _png(tmp_path / "cand.png", (240, 238, 232))
    result = compare_images(
        ref, cand,
        regions=[{"name": "mark", "box": [0.1, 0.1, 0.4, 0.4]}],
        session_id="cmp", session_root=tmp_path,
    )

    assert result["ok"] is True
    # overview + 1 region, all raster PNGs that exist on disk
    assert len(result["renders"]) == 2
    for render in result["renders"]:
        assert render["mimeType"] == "image/png"
        assert os.path.isfile(render["path"])
    # metrics present and surfaced in the model-facing text summary
    assert [c["region"] for c in result["comparison"]] == ["overview", "mark"]
    summary = json.loads(mcp_content_blocks(result)[0]["text"])
    assert "comparison" in summary
    # image blocks are emitted for the panels (raster contract)
    image_blocks = [b for b in mcp_content_blocks(result) if b["type"] == "image"]
    assert len(image_blocks) == 2


def test_compare_images_default_grid_when_no_regions(tmp_path):
    """No regions and no grid falls back to a 2x3 grid (plus the overview)."""
    ref = _png(tmp_path / "r.png", (10, 10, 10))
    cand = _png(tmp_path / "c.png", (10, 10, 10))
    result = compare_images(ref, cand, session_id="grid", session_root=tmp_path)
    assert result["ok"] is True
    assert len(result["renders"]) == 1 + 6


def test_compare_images_missing_file_is_structured_error(tmp_path):
    ref = _png(tmp_path / "ref.png", (0, 0, 0))
    result = compare_images(ref, str(tmp_path / "nope.png"),
                            session_id="missing", session_root=tmp_path)
    assert result["ok"] is False
    assert "error" in result and result["renders"] == []


def test_compare_images_respects_input_root_confinement(tmp_path, monkeypatch):
    """With FRAMEGRAPH_MCP_INPUT_ROOTS set, a path outside it is refused."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.png"
    _png(outside, (0, 0, 0))
    ref = _png(allowed / "ref.png", (0, 0, 0))
    monkeypatch.setenv("FRAMEGRAPH_MCP_INPUT_ROOTS", str(allowed))

    result = compare_images(ref, str(outside), session_id="confine", session_root=tmp_path)
    assert result["ok"] is False
    assert "FRAMEGRAPH_MCP_INPUT_ROOTS" in result["error"]


def test_compare_images_accepts_session_png_uri(tmp_path):
    """A candidate given as a framegraph://session/<id>/page/<n>.png URI resolves."""
    ref = _png(tmp_path / "ref.png", (200, 200, 200))
    # stage a page render as if a prior run_sdk_client had produced it
    session_dir = _prepare_session(tmp_path.resolve(), "prior")
    Image.new("RGB", (240, 180), (30, 30, 30)).save(session_dir / "p001.png", format="PNG")

    result = compare_images(
        ref, "framegraph://session/prior/page/1.png",
        regions=[{"name": "whole", "box": [0.0, 0.0, 1.0, 1.0]}],
        session_id="fromuri", session_root=tmp_path,
    )
    assert result["ok"] is True
    assert len(result["renders"]) == 2
