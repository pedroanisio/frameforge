#!/usr/bin/env python3
"""Reference-diff render mode — per-object ghost vectors (recon gap F2).

The reconstruction loop's expensive step was human: render, overlay, eyeball
the ghosting, guess "+14px". A render invoked with ``reference=`` now measures
it: each authored object's rendered patch is searched for in the reference and
the displacement comes back as data, so the correction is typed from numbers.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

np = pytest.importorskip("numpy")

from frameforge.vision.domain.ghosting import ghost_vectors  # noqa: E402


def _field(square_xy, size=(120, 90), sq=14):
    arr = np.full((size[1], size[0]), 240.0)
    x, y = square_xy
    arr[y:y + sq, x:x + sq] = 20.0
    return arr


def test_ghost_vector_recovers_known_shift():
    render = _field((30, 40))
    reference = _field((35, 43))
    out = ghost_vectors(render, reference,
                        [{"id": "sq", "box": [26, 36, 22, 22]}], search=12)
    assert len(out) == 1
    v = out[0]
    assert v["id"] == "sq"
    assert v["offset_px"] == [5, 3]
    assert v["score"] > 0.9


def test_flat_patches_are_skipped_as_unmeasurable():
    render = _field((30, 40))
    reference = _field((30, 40))
    out = ghost_vectors(render, reference,
                        [{"id": "flat", "box": [80, 8, 20, 20]},
                         {"id": "sq", "box": [26, 36, 22, 22]}], search=8)
    ids = [v["id"] for v in out]
    assert "flat" not in ids and "sq" in ids
    assert out[0]["offset_px"] == [0, 0]


def test_vectors_sorted_by_displacement_magnitude():
    render = np.full((90, 160), 240.0)
    render[20:32, 20:32] = 10.0
    render[60:72, 100:112] = 10.0
    reference = np.full((90, 160), 240.0)
    reference[22:34, 21:33] = 10.0        # moved (1, 2)
    reference[64:76, 107:119] = 10.0      # moved (7, 4)
    out = ghost_vectors(render, reference,
                        [{"id": "small", "box": [16, 16, 20, 20]},
                         {"id": "big", "box": [96, 56, 20, 20]}], search=12)
    assert [v["id"] for v in out] == ["big", "small"]
    assert out[0]["offset_px"] == [7, 4]
    assert out[1]["offset_px"] == [1, 2]


def _yaml(square_x):
    from frameforge.sdk import DocumentBuilder, serialize
    b = DocumentBuilder(title="ghost", profile="diagram")
    pg = b.page("p1", canvas={"size": [160, 120], "units": "px"})
    pg.layer("main")
    pg.rect([0, 0, 160, 120], fill="#F2F2F2")
    pg.rect([square_x, 40, 22, 22], fill="#101010", id="probe")
    return serialize(b.build(), format="yaml")


def _render_png(yaml_text, tmp_path, sid):
    from frameforge.mcp.usecases import render_frameforge_yaml
    out = render_frameforge_yaml(yaml_text, session_id=sid, session_root=tmp_path,
                                 raster_png=True)
    if not out.get("ok") or not any(r.get("mimeType") == "image/png"
                                    for r in out.get("renders", [])):
        pytest.skip("no raster backend available in this environment")
    return next(r["path"] for r in out["renders"] if r.get("mimeType") == "image/png")


def test_render_with_reference_reports_object_ghosts(tmp_path):
    from frameforge.mcp.usecases import render_frameforge_yaml
    ref_png = _render_png(_yaml(square_x=58), tmp_path, "ghost-ref")
    out = render_frameforge_yaml(_yaml(square_x=50), session_id="ghost-cand",
                                 session_root=tmp_path, raster_png=True,
                                 reference=ref_png)
    assert out["ok"] is True
    diff = out["reference_diff"]
    probes = [v for v in diff["ghost_vectors"] if v["id"] == "probe"]
    assert probes, f"probe object missing from ghost vectors: {diff['ghost_vectors']}"
    assert probes[0]["offset_px"][0] == pytest.approx(8, abs=1)
    assert abs(probes[0]["offset_px"][1]) <= 1
    assert diff["summary"]["objects_measured"] >= 1


def test_reference_without_raster_is_a_structured_note(tmp_path):
    from frameforge.mcp.usecases import render_frameforge_yaml
    out = render_frameforge_yaml(_yaml(square_x=50), session_id="ghost-norast",
                                 session_root=tmp_path, raster_png=False,
                                 reference="/nonexistent/ref.png")
    assert out["ok"] is True
    assert out["reference_diff"]["ok"] is False
    assert "raster" in out["reference_diff"]["error"] or \
        "resolve" in out["reference_diff"]["error"]


def test_object_boxes_survive_exotic_objects(tmp_path):
    """A stroke_outline path carries `d` as a list — one exotic object must
    neither raise nor evict the measurable objects from the diff (field bug
    found reconstructing a real poster)."""
    from frameforge.mcp.usecases import _doc_object_boxes
    from frameforge.sdk import DocumentBuilder, serialize
    from frameforge.sdk.outline import stroke_outline
    b = DocumentBuilder(title="exotic", profile="diagram")
    pg = b.page("p1", canvas={"size": [160, 120], "units": "px"})
    pg.layer("main")
    band = stroke_outline([(10, 100), (60, 40), (140, 30)], 8.0, smooth=True)
    band["fill"] = "#333333"
    pg.add(band)
    pg.rect([50, 40, 22, 22], fill="#101010", id="probe")
    yml = tmp_path / "doc.yaml"
    yml.write_text(serialize(b.build(), format="yaml"), encoding="utf-8")
    boxes = _doc_object_boxes(yml, img_w=160, img_h=120)
    ids = [bx["id"] for bx in boxes]
    assert "probe" in ids
