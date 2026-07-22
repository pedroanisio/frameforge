#!/usr/bin/env python3
"""RED → contract for geometry refinement (Gap G3: descent on spine params).

`refine_reconstruction` (B6) descends over PAINTS on frozen geometry; the
authored lane needs the dual. Two pieces close it:

* **Provenance.** ``sdk.outline.stroke_outline`` embeds its generative
  parameters as ``meta.stroke_outline`` — the flattened spine polyline, width,
  sampled profile, caps/joins — so an emitted petal remains a PARAMETRIC
  object, not a frozen path (``emit_params=False`` opts out; a user ``meta``
  bag is merged, never clobbered).
* **Descent.** ``refine_geometry(document, image)`` walks every object carrying
  that provenance and coordinate-descends a 9-parameter displacement family —
  global Δ, tip-weighted Δ, base-weighted Δ, bow (sin πt) Δ, width scale —
  minimizing the analytic claim-vs-background error against the reference.
  Bounded steps, accept-only-if-better: the pass can only descend, and it is
  deterministic. Geometry is rebuilt through stroke_outline itself, so the
  refined object stays byte-consistent with its own provenance.

Acceptance is RECOVERY: a petal authored with the wrong width (−22%) and a
shifted spine (+10 px) against a reference rendered from the TRUE parameters
must come back to IoU ≥ 0.93 with width within 8%.

MCP: ``refine_reconstruction(session, image, geometry=True)`` runs the
geometry pass BEFORE the paint pass; the summary gains a ``geometry`` block.
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
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

np = pytest.importorskip("numpy")
pytest.importorskip("PIL")

from frameforge.sdk.outline import stroke_outline  # noqa: E402

SIZE = (600, 800)
PETAL_FILL = "#4488ff"


def _spine(shift=0.0, n=48):
    b, c1, c2, e = (150 + shift, 700), (180 + shift, 420), (390 + shift, 180), (520 + shift, 120)
    pts = []
    for i in range(n + 1):
        s = i / n
        u = 1.0 - s
        pts.append((
            u**3 * b[0] + 3 * u * u * s * c1[0] + 3 * u * s * s * c2[0] + s**3 * e[0],
            u**3 * b[1] + 3 * u * u * s * c1[1] + 3 * u * s * s * c2[1] + s**3 * e[1],
        ))
    return pts


def _flame(t, peak=0.4):
    if t <= peak:
        return math.sin(min(max(t / peak, 0.0), 1.0) * math.pi / 2.0) ** 0.7
    x = min(max((t - peak) / (1.0 - peak), 0.0), 1.0)
    return math.cos(x * math.pi / 2.0) ** 0.9


def _petal(width, shift=0.0, **kw):
    return stroke_outline(_spine(shift), width, profile=_flame, cap="round",
                          join="round", fill=PETAL_FILL, **kw)


def _mask(obj):
    from frameforge.vision.infrastructure.vectorize import _shape_mask

    return np.asarray(_shape_mask(obj, SIZE)[0]) > 0


def _reference_image():
    """The truth: the TRUE petal painted flat on black."""
    from PIL import Image

    img = np.zeros((SIZE[1], SIZE[0], 3), dtype=np.uint8)
    img[_mask(_petal(110))] = (0x44, 0x88, 0xFF)
    return Image.fromarray(img)


def _doc(obj):
    return {"dsl": "FrameForge", "version": "2.2.0",
            "pages": [{"mode": "page", "id": "p",
                       "canvas": {"size": [SIZE[0], SIZE[1]], "units": "px"},
                       "layers": [{"id": "l", "objects": [
                           {"type": "rect", "box": [0, 0, SIZE[0], SIZE[1]],
                            "fill": "#000000"},
                           obj]}]}]}


def _iou(a, b):
    return float((a & b).sum()) / float((a | b).sum())


# ------------------------------------------------------------- provenance lane
def test_stroke_outline_embeds_generative_params():
    obj = _petal(110)
    prov = obj["meta"]["stroke_outline"]
    assert prov["width"] == 110
    assert len(prov["profile"]) == 16
    assert prov["profile"][0] < 0.2 and max(prov["profile"]) > 0.95
    assert len(prov["spine"]) >= 20 and len(prov["spine"][0]) == 2
    assert prov["cap"] == "round" and prov["join"] == "round"


def test_provenance_opt_out_and_user_meta_survive():
    bare = _petal(110, emit_params=False)
    assert "meta" not in bare
    tagged = _petal(110, meta={"role": "wing"})
    assert tagged["meta"]["role"] == "wing"
    assert "stroke_outline" in tagged["meta"]


# ---------------------------------------------------------------- descent lane
def test_recovery_of_width_and_position():
    from frameforge.vision.infrastructure.refine import refine_geometry

    wrong = _petal(86, shift=10.0)
    true_mask = _mask(_petal(110))
    assert _iou(_mask(wrong), true_mask) < 0.85, "the setup must start off-truth"

    doc = _doc(wrong)
    summary = refine_geometry(doc, _reference_image())
    assert summary["refined"] >= 1 and summary["improved"] >= 1
    assert summary["sq_after"] < summary["sq_before"]

    refined = doc["pages"][0]["layers"][0]["objects"][1]
    prov = refined["meta"]["stroke_outline"]
    assert prov["width"] == pytest.approx(110, rel=0.08)
    assert _iou(_mask(refined), true_mask) >= 0.93


def test_descent_only_at_the_truth():
    from frameforge.vision.infrastructure.refine import refine_geometry

    doc = _doc(_petal(110))
    true_mask = _mask(_petal(110))
    summary = refine_geometry(doc, _reference_image())
    assert summary["sq_after"] <= summary["sq_before"] + 1e-6
    refined = doc["pages"][0]["layers"][0]["objects"][1]
    assert _iou(_mask(refined), true_mask) >= 0.97, "truth must stay at truth"


def test_objects_without_provenance_are_skipped_untouched():
    from frameforge.vision.infrastructure.refine import refine_geometry

    frozen = _petal(86, emit_params=False)
    import copy
    keep = copy.deepcopy(frozen)
    doc = _doc(frozen)
    summary = refine_geometry(doc, _reference_image())
    assert summary["skipped"] >= 1
    assert doc["pages"][0]["layers"][0]["objects"][1] == keep


def test_refine_geometry_is_deterministic():
    from frameforge.vision.infrastructure.refine import refine_geometry

    d1 = _doc(_petal(86, shift=10.0))
    s1 = refine_geometry(d1, _reference_image())
    d2 = _doc(_petal(86, shift=10.0))
    s2 = refine_geometry(d2, _reference_image())
    assert d1 == d2 and s1 == s2


def test_size_mismatch_is_loud():
    from PIL import Image

    from frameforge.vision.infrastructure.refine import refine_geometry

    with pytest.raises(ValueError, match="size"):
        refine_geometry(_doc(_petal(110)), Image.new("RGB", (64, 64)))


# ------------------------------------------------------------------- mcp lane
def test_mcp_geometry_flag_roundtrip(tmp_path):
    pytest.importorskip("cairosvg")
    import yaml as _yaml

    from frameforge.mcp.usecases import refine_reconstruction, render_frameforge_yaml

    ref_path = tmp_path / "ref.png"
    _reference_image().save(ref_path)
    doc = _doc(_petal(86, shift=10.0))
    r = render_frameforge_yaml(yaml_text=_yaml.safe_dump(doc, sort_keys=False),
                               session_id="g3", session_root=tmp_path,
                               raster_png=False)
    assert r.get("ok") is True, r.get("error")

    out = refine_reconstruction(session_id="g3", image=str(ref_path),
                                geometry=True, raster_png=False,
                                session_root=tmp_path)
    assert out.get("ok") is True, out.get("error")
    geo = out["refine"]["geometry"]
    assert geo["improved"] >= 1 and geo["sq_after"] < geo["sq_before"]
    assert out["validation"]["ok"] is True

    plain = refine_reconstruction(session_id="g3", image=str(ref_path),
                                  raster_png=False, session_root=tmp_path)
    assert plain.get("ok") is True
    assert "geometry" not in plain["refine"], "geometry pass is opt-in"


def test_mcp_tool_exposes_geometry_flag(tmp_path):
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
    params = inspect.signature(srv.tools["refine_reconstruction"]).parameters
    assert "geometry" in params
    assert params["geometry"].default is False
