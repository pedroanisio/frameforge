#!/usr/bin/env python3
"""RED → contract for page-level raster post effects (Gap A3).

A crisp vector render asymptotes below a soft-media reference (JPEG bloom
around bright edges, sensor/compression grain in the blacks, AA softness) —
the measured residual of the lotus reconstruction. A3 adds `Page.post`:

    post:
      blur:  1.5                       # gaussian soft-focus, px
      bloom: {radius: 8, strength: 0.6, threshold: 0.75}
      grain: {amount: 0.04, seed: 7}   # deterministic seeded noise

Semantics pinned here:
* post effects are RASTER-stage: SVG/PDF/TeX output is byte-unaffected, and
  the renderer notes a structured warning so the degradation is observable
  (PALS — a vector consumer must know the page declares raster-only paint);
* fixed application order blur → bloom → grain, radii in canvas px (scaled
  by the raster zoom);
* grain is DETERMINISTIC: same seed → identical bytes, no wall-clock entropy;
* the model is strict: negative radii, out-of-range strengths, unknown keys
  are validation errors.
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

from pydantic import ValidationError  # noqa: E402

from frameforge.model import Document  # noqa: E402
from tooling.render_fixtures import Renderer  # noqa: E402


def _doc(post=None, objects=None):
    page = {"mode": "page", "id": "p", "canvas": {"size": [120, 80], "units": "px"},
            "layers": [{"id": "l", "objects": objects or [
                {"type": "rect", "box": [0, 0, 120, 80], "fill": "#000000"},
                {"type": "rect", "box": [40, 20, 40, 30], "fill": "#ffffff"}]}]}
    if post is not None:
        page["post"] = post
    return {"dsl": "FrameForge", "version": "2.2.0", "pages": [page]}


_POST = {"blur": 1.5,
         "bloom": {"radius": 8, "strength": 0.6, "threshold": 0.75},
         "grain": {"amount": 0.04, "seed": 7}}


# ------------------------------------------------------------------ model lane
def test_page_post_validates():
    doc = Document.model_validate(_doc(post=_POST))
    post = doc.pages[0].post
    assert post.blur == 1.5
    assert post.bloom.strength == 0.6
    assert post.grain.seed == 7


def test_page_post_defaults_are_deterministic():
    doc = Document.model_validate(_doc(post={"grain": {"amount": 0.05}}))
    assert doc.pages[0].post.grain.seed == 0        # fixed default seed, no entropy


@pytest.mark.parametrize("bad", [
    {"blur": -1},
    {"bloom": {"radius": 0}},
    {"bloom": {"radius": 4, "strength": 1.5}},
    {"bloom": {"radius": 4, "threshold": 2.0}},
    {"grain": {"amount": 1.5}},
    {"grain": {"amount": 0.1, "seed": -1}},
    {"sharpen": 2},                                  # unknown effect: closed model
])
def test_page_post_is_strict(bad):
    with pytest.raises(ValidationError):
        Document.model_validate(_doc(post=bad))


# ----------------------------------------------------------------- raster lane
pil = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _flat(img):
    rgb = img.convert("RGB")
    getter = getattr(rgb, "get_flattened_data", rgb.getdata)
    return list(getter())


def _test_image():
    img = Image.new("RGB", (120, 80), (5, 5, 8))
    px = img.load()
    for y in range(20, 50):
        for x in range(40, 80):
            px[x, y] = (250, 245, 250)
    return img


def test_identity_when_no_effects():
    from frameforge.rendering.infrastructure.raster_post import apply_post_effects

    img = _test_image()
    assert _flat(apply_post_effects(img, None)) == _flat(img)
    assert _flat(apply_post_effects(img, {})) == _flat(img)


def test_grain_is_seed_deterministic():
    from frameforge.rendering.infrastructure.raster_post import apply_post_effects

    img = _test_image()
    a = apply_post_effects(img, {"grain": {"amount": 0.05, "seed": 7}})
    b = apply_post_effects(img, {"grain": {"amount": 0.05, "seed": 7}})
    c = apply_post_effects(img, {"grain": {"amount": 0.05, "seed": 8}})
    assert _flat(a) == _flat(b), "same seed must be byte-identical"
    assert _flat(a) != _flat(c), "a different seed must change the noise"
    assert _flat(a) != _flat(img), "grain must actually apply"


def test_blur_reduces_high_frequency_energy():
    from frameforge.rendering.infrastructure.raster_post import apply_post_effects

    def hf_energy(img):
        # squared gradient energy — total variation (sum |Δ|) is invariant
        # under monotone smoothing, so it cannot detect a blur; squares can.
        g = img.convert("L")
        w, h = g.size
        px = g.load()
        return sum((px[x + 1, y] - px[x, y]) ** 2 for y in range(h) for x in range(w - 1))

    img = _test_image()
    out = apply_post_effects(img, {"blur": 2.0})
    assert hf_energy(out) < 0.6 * hf_energy(img)


def test_bloom_brightens_near_bright_regions_only():
    from frameforge.rendering.infrastructure.raster_post import apply_post_effects

    img = _test_image()
    out = apply_post_effects(
        img, {"bloom": {"radius": 6, "strength": 0.8, "threshold": 0.7}})
    src, dst = img.load(), out.convert("RGB").load()
    near = sum(dst[38, 35]) - sum(src[38, 35])       # 2px outside the bright rect
    far = sum(dst[5, 75]) - sum(src[5, 75])          # far corner
    assert near > 15, f"halo must brighten the rim (got +{near})"
    assert far <= 3, f"far pixels must stay dark (got +{far})"


def test_scale_multiplies_effect_radii():
    from frameforge.rendering.infrastructure.raster_post import apply_post_effects

    img = _test_image().resize((240, 160), Image.NEAREST)
    a = apply_post_effects(img, {"blur": 2.0}, scale=2.0)
    b = apply_post_effects(img, {"blur": 4.0}, scale=1.0)
    assert _flat(a) == _flat(b), "radius is canvas px: scale=2 doubles the raster radius"


# ------------------------------------------------------------------- svg lane
def test_vector_output_is_unaffected_and_warned():
    with_post, r1 = _render_page(_doc(post=_POST))
    without, _r0 = _render_page(_doc(post=None))
    assert with_post == without, "post effects must never change the vector bytes"
    warnings = r1.diagnostics.get("warnings", [])
    assert any(w.get("kind") == "post_raster_only" for w in warnings), warnings


def _render_page(doc):
    r = Renderer(doc, ".")
    svg = r.render_page(doc["pages"][0])[0]
    return svg, r


# ------------------------------------------------------------------- mcp lane
def test_mcp_raster_applies_post_deterministically(tmp_path):
    pytest.importorskip("cairosvg")
    import yaml as _yaml

    from frameforge.mcp.usecases import render_frameforge_yaml

    plain = _yaml.safe_dump(_doc(post=None), sort_keys=False)
    posted = _yaml.safe_dump(_doc(post={"grain": {"amount": 0.06, "seed": 3}}),
                             sort_keys=False)
    r0 = render_frameforge_yaml(yaml_text=plain, session_id="post-a",
                                session_root=tmp_path)
    r1 = render_frameforge_yaml(yaml_text=posted, session_id="post-b",
                                session_root=tmp_path)
    r2 = render_frameforge_yaml(yaml_text=posted, session_id="post-c",
                                session_root=tmp_path)
    assert r0.get("ok") and r1.get("ok") and r2.get("ok")
    p0 = (tmp_path / "post-a" / "p001.png").read_bytes()
    p1 = (tmp_path / "post-b" / "p001.png").read_bytes()
    p2 = (tmp_path / "post-c" / "p001.png").read_bytes()
    assert p1 != p0, "grain must change the raster"
    assert p1 == p2, "seeded grain must be run-deterministic"
    applied = [e.get("post_effects") for e in r1["renders"]
               if str(e.get("path", "")).endswith(".png")]
    assert applied and applied[0] == ["grain"], applied


def test_flow_documents_skip_post_with_observable_warning():
    from frameforge.mcp.pipeline import page_post_specs

    flow_doc = {"dsl": "FrameForge", "version": "2.2.0",
                "defs": {"masters": {"m": {"regions": [
                    {"id": "body", "box": [10, 10, 100, 60]}]}}},
                "pages": [
                    {"mode": "page", "id": "p1", "post": {"blur": 1.0},
                     "layers": [{"id": "l", "objects": []}]},
                    {"mode": "flow", "id": "s1", "master": "m",
                     "story": [{"type": "paragraph", "text": "hi"}]},
                ]}
    specs, warning = page_post_specs(flow_doc)
    assert specs is None
    assert warning and "flow" in warning.lower()

    page_doc = _doc(post={"blur": 1.0})
    specs, warning = page_post_specs(page_doc)
    assert warning is None
    assert specs == {1: {"blur": 1.0}}
