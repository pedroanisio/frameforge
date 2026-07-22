#!/usr/bin/env python3
"""RED → contract for edge-aware descent (H2) + visibility-aware banding (H1).

Two measured failures drive this pair:

* H2 — the G3 descent's cost is flat claim-vs-background COLOUR; when the
  document's paint is uninformative (wrong/equal to the ground), nothing
  guides the geometry, and residual contour misalignment is exactly what made
  interior detail unpaintable. The cost gains an EDGE term: the candidate
  outline's boundary is pulled onto the reference's edge field (gradient
  edges → distance transform). ``edge_weight=0`` restores the pure-colour
  behaviour byte-for-byte.

* H1 — the fitting-lane banding (`apply_gradient_fills(bands=N)`) samples a
  shape's FULL mask, so on session documents it ingests occluded/misaligned
  pixels — measured on the clone-v3 lotus: 0.94 → 0.77 NCC. The refine lane
  gains `refine_band_shading`: rim bands anchored on the shape's OWN distance
  field, each band's paint fitted on its VISIBLE pixels only (the B6
  ownership discipline per band), overlays emitted through the A2 idiom and
  replaced idempotently on re-runs. `refine_reconstruction(bands=N)` chains
  geometry → bands → paints.
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


def _petal(width=110, shift=0.0, fill="#d0d0e0", **kw):
    return stroke_outline(_spine(shift), width, profile=_flame, cap="round",
                          join="round", fill=fill, **kw)


def _mask(obj):
    from frameforge.vision.infrastructure.vectorize import _shape_mask

    return np.asarray(_shape_mask(obj, SIZE)[0]) > 0


def _doc(*objects, bg="#101010"):
    return {"dsl": "FrameForge", "version": "2.2.0",
            "pages": [{"mode": "page", "id": "p",
                       "canvas": {"size": [SIZE[0], SIZE[1]], "units": "px"},
                       "layers": [{"id": "l", "objects": [
                           {"type": "rect", "box": [0, 0, SIZE[0], SIZE[1]],
                            "fill": bg}, *objects]}]}]}


def _iou(a, b):
    return float((a & b).sum()) / float((a | b).sum())


# ---------------------------------------------------------------- H2: edge term
def _edge_scene():
    """A reference with STRONG edges but a document paint that matches the
    ground — pure colour cost cannot guide the shifted outline home."""
    from PIL import Image

    img = np.full((SIZE[1], SIZE[0], 3), 0x10, dtype=np.uint8)
    img[_mask(_petal(fill="#d0d0e0"))] = (0xD0, 0xD0, 0xE0)
    reference = Image.fromarray(img)
    wrong = _petal(shift=14.0, fill="#101010")     # paint == ground: colour-blind
    return reference, wrong


def test_edge_term_recovers_when_colour_is_uninformative():
    from frameforge.vision.infrastructure.refine import refine_geometry

    reference, wrong = _edge_scene()
    truth = _mask(_petal())
    assert _iou(_mask(wrong), truth) < 0.80

    doc = _doc(wrong)
    refine_geometry(doc, reference)                # edge term ON by default
    refined = doc["pages"][0]["layers"][0]["objects"][1]
    assert _iou(_mask(refined), truth) >= 0.90, \
        "the edge field must pull the outline onto the reference contour"


def test_edge_weight_zero_restores_pure_colour_behaviour():
    from frameforge.vision.infrastructure.refine import refine_geometry

    reference, wrong = _edge_scene()
    truth = _mask(_petal())
    doc = _doc(wrong)
    refine_geometry(doc, reference, edge_weight=0.0)
    refined = doc["pages"][0]["layers"][0]["objects"][1]
    assert _iou(_mask(refined), truth) < 0.80, \
        "without the edge term a ground-coloured outline has no colour signal"


def test_edge_term_is_descent_only_at_the_truth():
    from PIL import Image

    from frameforge.vision.infrastructure.refine import refine_geometry

    img = np.full((SIZE[1], SIZE[0], 3), 0x10, dtype=np.uint8)
    img[_mask(_petal(fill="#4488ff"))] = (0x44, 0x88, 0xFF)
    doc = _doc(_petal(fill="#4488ff"))
    truth = _mask(_petal(fill="#4488ff"))
    refine_geometry(doc, Image.fromarray(img))
    refined = doc["pages"][0]["layers"][0]["objects"][1]
    assert _iou(_mask(refined), truth) >= 0.97, "truth must stay at truth"


# ------------------------------------------------------------ H1: banded refit
def _shaded_reference(mask):
    """Dark contour-following rim → bright core over the given mask."""
    from PIL import Image

    from frameforge.vision.domain.spine_fit import chamfer_distance

    dist = chamfer_distance(mask.astype(np.uint8), max_rounds=64)
    img = np.zeros((SIZE[1], SIZE[0], 3), dtype=np.float64)
    t = np.clip(dist / 14.0, 0.0, 1.0)
    rim = np.array([25.0, 20.0, 80.0])
    core = np.array([210.0, 200.0, 245.0])
    shaded = rim[None, None, :] + (core - rim)[None, None, :] * t[..., None]
    img[mask] = shaded[mask]
    return Image.fromarray(img.astype(np.uint8))


def test_band_refit_is_visibility_aware():
    """An occluder covers part of the rim with a contaminant colour; the rim
    band's fitted paint must come from the VISIBLE rim only."""
    from PIL import Image

    from frameforge.vision.infrastructure.refine import refine_band_shading

    body = _petal(fill="#808080")
    mask = _mask(body)
    ref = np.asarray(_shaded_reference(mask)).copy()
    # occluder: a green square over the petal's mid-left rim
    occ_box = [140, 380, 120, 160]
    occluder = {"type": "rect", "box": occ_box, "fill": "#20c020"}
    ref[380:540, 140:260] = (0x20, 0xC0, 0x20)

    doc = _doc(body, occluder)
    summary = refine_band_shading(doc, Image.fromarray(ref), bands=3)
    assert summary["banded"] >= 1 and summary["rings"] >= 1

    objs = doc["pages"][0]["layers"][0]["objects"]
    rings = [o for o in objs
             if o.get("stroke") is not None and "fill" not in o
             and (o.get("style") or {}).get("clip_path")]
    assert rings, "rim bands must be emitted as self-clipped stroke overlays"
    for ring in rings:
        paints = ring["stroke"]
        stops = (paints.get("stops") if isinstance(paints, dict) else None) or []
        cols = [s["color"] for s in stops] if stops else [paints]
        for c in cols:
            g = int(str(c).lstrip("#")[2:4], 16)
            r = int(str(c).lstrip("#")[0:2], 16)
            assert not (g > 140 and r < 90), \
                f"ring paint {c} is contaminated by the occluder green"


def test_band_refit_improves_on_flat_refit():
    from PIL import Image

    from frameforge.vision.infrastructure.refine import (
        refine_band_shading, refine_document,
    )

    body = _petal(fill="#808080")
    mask = _mask(body)
    ref = _shaded_reference(mask)

    flat_doc = _doc(_petal(fill="#808080"))
    flat = refine_document(flat_doc, ref)

    band_doc = _doc(_petal(fill="#808080"))
    refine_band_shading(band_doc, ref, bands=3)
    banded = refine_document(band_doc, ref)
    assert banded["rms_after"] < 0.75 * flat["rms_after"], \
        (banded["rms_after"], flat["rms_after"])


def test_decorative_overlays_neither_occlude_nor_get_banded():
    """Craft overlays (rims/gloss, decorative=True) sit ON a body: they must
    not steal the body's visible pixels for band statistics, and they must
    never be banded themselves — measured on the clone-v3 lotus, letting them
    occlude inverts the ring fits into bright halos."""
    from frameforge.vision.infrastructure.refine import refine_band_shading

    body = _petal(fill="#808080")
    ref = _shaded_reference(_mask(body))

    plain_doc = _doc(body)
    refine_band_shading(plain_doc, ref, bands=3)

    body2 = _petal(fill="#808080")
    rim = {"type": "path", "d": body2["d"], "decorative": True,
           "stroke": "#111144", "stroke_style": {"stroke_width": 12},
           "style": {"clip_path": {"shape": "path", "args": {"d": body2["d"]}}}}
    gloss = _petal(width=20, fill="#ffffff")
    gloss["decorative"] = True
    craft_doc = _doc(body2, rim, gloss)
    summary = refine_band_shading(craft_doc, ref, bands=3)
    assert summary["banded"] == 1, "only the BODY is banded, never the craft overlays"

    def ring_paints(doc):
        return [o["stroke"] for o in doc["pages"][0]["layers"][0]["objects"]
                if isinstance(o.get("meta"), dict) and "band" in o["meta"]]

    assert ring_paints(craft_doc) == ring_paints(plain_doc), \
        "decorative overlays must not change the band statistics"


def test_band_shading_is_idempotent():
    from frameforge.vision.infrastructure.refine import refine_band_shading

    body = _petal(fill="#808080")
    ref = _shaded_reference(_mask(body))
    doc = _doc(body)
    refine_band_shading(doc, ref, bands=3)
    n1 = len(doc["pages"][0]["layers"][0]["objects"])
    refine_band_shading(doc, ref, bands=3)
    n2 = len(doc["pages"][0]["layers"][0]["objects"])
    assert n1 == n2, "re-running must REPLACE band overlays, never stack them"


def test_bands_1_is_a_noop():
    import copy

    from frameforge.vision.infrastructure.refine import refine_band_shading

    body = _petal(fill="#808080")
    ref = _shaded_reference(_mask(body))
    doc = _doc(body)
    keep = copy.deepcopy(doc)
    summary = refine_band_shading(doc, ref, bands=1)
    assert doc == keep and summary.get("banded", 0) == 0


# ------------------------------------------------------------------- mcp lane
def test_mcp_bands_flag_roundtrip(tmp_path):
    pytest.importorskip("cairosvg")
    import yaml as _yaml

    from frameforge.mcp.usecases import refine_reconstruction, render_frameforge_yaml

    body = _petal(fill="#808080")
    ref_img = _shaded_reference(_mask(body))
    ref_path = tmp_path / "ref.png"
    ref_img.save(ref_path)

    r = render_frameforge_yaml(yaml_text=_yaml.safe_dump(_doc(body), sort_keys=False),
                               session_id="h1", session_root=tmp_path,
                               raster_png=False)
    assert r.get("ok") is True, r.get("error")

    out = refine_reconstruction(session_id="h1", image=str(ref_path),
                                bands=3, raster_png=False, session_root=tmp_path)
    assert out.get("ok") is True, out.get("error")
    assert out["refine"]["shading"]["banded"] >= 1
    assert out["validation"]["ok"] is True

    plain = refine_reconstruction(session_id="h1", image=str(ref_path),
                                  raster_png=False, session_root=tmp_path)
    assert plain.get("ok") is True
    assert "shading" not in plain["refine"], "banding is opt-in"


def test_mcp_tool_exposes_bands(tmp_path):
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
    assert "bands" in params and params["bands"].default == 1
