#!/usr/bin/env python3
"""RED → contract for error-driven reconstruction refinement (Gap B6).

The fitting lane samples each shape's FULL mask — including pixels occluded by
later objects — so overlapped shapes inherit contaminated fits, and nothing on
the surface descends the residual after emission. B6 adds the refinement pass:

* OWNERSHIP: paint-order occupancy per pixel (fill shapes by their winding
  mask; A2 band overlays by their inner-stroke ring), so each object owns
  exactly the pixels it visibly shows;
* REFIT: every ownable paint (hex, user-space linear `line`, user-space
  radial `at`+`radius`) is refitted on its VISIBLE pixels, in user geometry,
  converted back to the object's local space;
* GUARDED: a refit is kept only when that object's analytic rms against the
  reference improves — the loop can only descend;
* MEASURED: the summary reports rms_before / rms_after over owned pixels,
  and the whole pass is deterministic.

MCP surface: `refine_reconstruction(session_id, image)` refines a vectorize
session's generated.fg.yaml in place and re-renders it.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

pytest.importorskip("PIL")
pytest.importorskip("numpy")
from PIL import Image  # noqa: E402


def _ramp_image():
    """A horizontal ramp field with a flat blue block painted over its middle."""
    img = Image.new("RGB", (200, 100), (0, 0, 0))
    px = img.load()
    for y in range(10, 90):
        for x in range(10, 190):
            t = (x - 10) / 179.0
            px[x, y] = (int(20 + 220 * t), 60, 40)
    for y in range(20, 70):
        for x in range(80, 150):
            px[x, y] = (30, 60, 220)
    return img


def _doc(objects, size=(200, 100)):
    return {"dsl": "FrameForge", "version": "2.2.0",
            "pages": [{"mode": "page", "id": "p",
                       "canvas": {"size": list(size), "units": "px"},
                       "layers": [{"id": "l", "objects": objects}]}]}


def _occluded_doc():
    a = {"type": "polygon", "fill": "#777777",
         "points": [[10, 10], [190, 10], [190, 90], [10, 90]]}
    b = {"type": "polygon", "fill": "#1e3cdc",
         "points": [[80, 20], [150, 20], [150, 70], [80, 70]]}
    return _doc([a, b]), a, b


# ---------------------------------------------------------------- engine lane
def test_refine_refits_on_visible_pixels_only():
    from frameforge.vision.infrastructure.refine import refine_document

    doc, a, b = _occluded_doc()
    summary = refine_document(doc, _ramp_image())
    assert summary["refit"] >= 1
    assert summary["rms_after"] < summary["rms_before"]
    fill = a["fill"]
    assert isinstance(fill, dict) and fill["kind"] == "linear", fill
    (x1, y1), (x2, y2) = fill["line"]
    assert abs(x2 - x1) > 5 * abs(y2 - y1), "the visible ramp axis is horizontal"
    # endpoint stops must recover the ramp extremes, not the blue block
    def chan(stop):
        return int(stop["color"].lstrip("#")[0:2], 16)
    reds = [chan(s) for s in fill["stops"]]
    assert max(reds) > 180 and min(reds) < 80, reds


def test_refine_only_descends_and_is_deterministic():
    from frameforge.vision.infrastructure.refine import refine_document

    img = _ramp_image()
    doc1, _, _ = _occluded_doc()
    s1 = refine_document(doc1, img)
    doc2, _, _ = _occluded_doc()
    s2 = refine_document(doc2, img)
    assert doc1 == doc2 and s1 == s2, "refinement must be deterministic"
    # a second pass over the already-refined doc must not regress
    s3 = refine_document(doc1, img)
    assert s3["rms_after"] <= s1["rms_after"] + 1e-6


def test_refine_handles_band_overlays():
    from frameforge.vision.infrastructure.refine import refine_document
    from frameforge.vision.infrastructure.vectorize import apply_gradient_fills

    img = Image.new("RGB", (200, 120), (0, 0, 0))
    px = img.load()
    for y in range(30, 90):
        for x in range(40, 160):
            d = min(x - 39, 160 - x, y - 29, 90 - y)
            t = min(d / 12.0, 1.0)
            px[x, y] = (int(20 + 180 * t), 30, int(60 + 160 * t))
    objs = [{"type": "polygon", "fill": "#808080",
             "points": [[40, 30], [160, 30], [160, 90], [40, 90]]}]
    apply_gradient_fills(objs, img, min_pixels=200, bands=3)
    assert len(objs) == 3
    doc = _doc(objs, size=(200, 120))
    summary = refine_document(doc, img)
    assert summary["rms_after"] <= summary["rms_before"] + 1e-6


def test_refine_size_mismatch_is_loud():
    from frameforge.vision.infrastructure.refine import refine_document

    doc, _, _ = _occluded_doc()
    with pytest.raises(ValueError, match="size"):
        refine_document(doc, Image.new("RGB", (64, 64)))


# ------------------------------------------------------------------- mcp lane
def test_mcp_refine_reconstruction_roundtrip(tmp_path):
    pytest.importorskip("cv2")
    import yaml as _yaml

    from frameforge.mcp.usecases import refine_reconstruction, vectorize_image

    src = tmp_path / "scene.png"
    _ramp_image().save(src)
    res = vectorize_image(image=str(src), mode="region", fill_mode="gradient",
                          colors=4, raster_png=False, session_id="ref-s",
                          session_root=tmp_path)
    assert res.get("ok") is True, res.get("error")
    before = (tmp_path / "ref-s" / "generated.fg.yaml").read_text(encoding="utf-8")

    out = refine_reconstruction(session_id="ref-s", image=str(src),
                                raster_png=False, session_root=tmp_path)
    assert out.get("ok") is True, out.get("error")
    ref = out["refine"]
    assert ref["rms_after"] <= ref["rms_before"] + 1e-6
    assert "refit" in ref and "improved" in ref
    after = (tmp_path / "ref-s" / "generated.fg.yaml").read_text(encoding="utf-8")
    doc = _yaml.safe_load(after)
    assert doc["pages"], "the refined document must stay a valid FrameForge doc"
    assert out["validation"]["ok"] is True


def test_mcp_refine_missing_session_is_structured(tmp_path):
    from frameforge.mcp.usecases import refine_reconstruction

    out = refine_reconstruction(session_id="nope", image=__file__,
                                session_root=tmp_path)
    assert out.get("ok") is False
    assert "session" in str(out.get("error", "")).lower()


def test_mcp_tool_exposes_refine_reconstruction(tmp_path):
    import inspect

    from frameforge.mcp.server import create_server

    class FakeFastMCP:
        def __init__(self, name, **kwargs):
            self.tools = {}

        def tool(self, **_kw):
            def decorate(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorate

        def resource(self, uri, **_kw):
            def decorate(fn):
                return fn
            return decorate

        def prompt(self, **_kw):
            def decorate(fn):
                return fn
            return decorate

    srv = create_server(fastmcp_cls=FakeFastMCP, session_root=tmp_path)
    assert "refine_reconstruction" in srv.tools
    params = inspect.signature(srv.tools["refine_reconstruction"]).parameters
    assert "session_id" in params and "image" in params
    assert params["min_pixels"].default == 24
