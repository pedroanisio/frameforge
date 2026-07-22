#!/usr/bin/env python3
"""RED → contract for AA-aware subpixel tracing (Gap B5).

``trace_to_svg`` binarises at native resolution, so an anti-aliased boundary
quantises to integer-pixel cells before potrace ever sees it — the traced
curve carries a systematic ~half-pixel wobble that shows up as the edge halo
in reconstruction diffs (the lotus-emblem 97% ceiling). ``supersample=s``
upscales the grayscale BEFORE thresholding: the threshold crossing is located
on a 1/s px grid, and the caller's ``svg_to_objects(box=...)`` fit divides the
s×-larger potrace viewport back down — geometry lands subpixel-accurately in
the SAME output coordinates.

Contract pinned here:
* accuracy: the traced boundary of an AA disk lands measurably closer to the
  true radius at s=3 than at s=1;
* turdsize keeps SOURCE-pixel semantics (potrace sees s²-scaled speckles, so
  the effective turdsize is ``turdsize * s²``);
* meta reports ``supersample`` + ``turdsize_effective`` + the traced (upscaled)
  pixel size, while ``image``/``region_px`` stay in SOURCE coordinates;
* ``supersample`` outside 1..4 is a loud ValueError, never a silent clamp.
"""
from __future__ import annotations

import math
import os
import shutil
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

pytest.importorskip("PIL")
from PIL import Image, ImageDraw  # noqa: E402

_HAS_POTRACE = shutil.which("potrace") is not None

pytestmark = pytest.mark.skipif(not _HAS_POTRACE, reason="potrace binary not installed")

_R, _C = 60.0, (100.0, 100.0)


def _aa_disk_png(tmp_path, name="disk.png"):
    """A white disk with a true anti-aliased edge: drawn 4× and LANCZOS-downscaled."""
    big = Image.new("L", (800, 800), 0)
    ImageDraw.Draw(big).ellipse([400 - 240, 400 - 240, 400 + 240, 400 + 240], fill=255)
    img = big.resize((200, 200), Image.LANCZOS)
    p = tmp_path / name
    img.convert("RGB").save(p)
    return str(p)


def _traced_radial_error(img_path, supersample):
    """Trace the disk and measure mean |radius − R| of the boundary points."""
    from frameforge.vision.domain.gradient_fit import flatten_path_d
    from frameforge.vision.infrastructure.svg_import import svg_to_objects
    from frameforge.vision.infrastructure.vectorize import _object_transform, trace_to_svg

    svg_text, meta = trace_to_svg(img_path, threshold=128, supersample=supersample)
    objs = svg_to_objects(svg_text, box=[0, 0, 200, 200])
    paths = [o for o in objs if o.get("type") == "path" and o.get("d")]
    assert paths, f"no traced paths (meta={meta})"
    errs = []
    for obj in paths:
        tf = _object_transform(obj)
        assert tf is not None, obj.get("style")
        tx, ty, sx, sy = tf
        for sub in flatten_path_d(obj["d"]):
            for x, y in sub:
                px, py = sx * x + tx, sy * y + ty
                errs.append(abs(math.hypot(px - _C[0], py - _C[1]) - _R))
    # potrace optimises a circle into a handful of long cubics; flatten_path_d
    # samples 4 on-curve points per cubic — a dozen points is a real outline.
    assert len(errs) >= 12, f"too few outline samples ({len(errs)})"
    return sum(errs) / len(errs), meta


def test_supersample_improves_boundary_placement(tmp_path):
    img = _aa_disk_png(tmp_path)
    err1, meta1 = _traced_radial_error(img, 1)
    err3, meta3 = _traced_radial_error(img, 3)
    assert meta1["supersample"] == 1 and meta3["supersample"] == 3
    assert err3 < err1, f"supersampling must not worsen placement ({err3:.3f} vs {err1:.3f})"
    assert err3 < 0.30, f"s=3 must land subpixel (mean radial error {err3:.3f}px)"


def test_turdsize_keeps_source_pixel_semantics(tmp_path):
    """A 3×3 speck must stay dropped at s=3 when turdsize says 'drop < 12 px'."""
    from frameforge.vision.infrastructure.vectorize import trace_to_svg

    img = Image.new("L", (200, 200), 0)
    d = ImageDraw.Draw(img)
    d.rectangle([30, 30, 79, 79], fill=255)          # the real shape (50×50)
    d.rectangle([150, 150, 152, 152], fill=255)      # a 3×3 = 9 px speck
    p = tmp_path / "speck.png"
    img.convert("RGB").save(p)

    for s in (1, 3):
        svg_text, meta = trace_to_svg(str(p), threshold=128, turdsize=12, supersample=s)
        assert meta["path_count"] == 1, \
            f"s={s}: speck must be dropped (turdsize=12 source px), got {meta['path_count']}"
    assert meta["turdsize_effective"] == 12 * 9


def test_meta_keeps_source_coordinates(tmp_path):
    from frameforge.vision.infrastructure.vectorize import trace_to_svg

    img = _aa_disk_png(tmp_path)
    _, meta = trace_to_svg(img, threshold=128, supersample=2)
    assert meta["image"] == {"width_px": 200, "height_px": 200}
    assert meta["region_px"] == [0.0, 0.0, 200.0, 200.0]
    assert meta["traced_px"] == [400, 400]


def test_supersample_bounds_are_loud(tmp_path):
    from frameforge.vision.infrastructure.vectorize import trace_to_svg

    img = _aa_disk_png(tmp_path)
    for bad in (0, 5, -1):
        with pytest.raises(ValueError, match="supersample"):
            trace_to_svg(img, supersample=bad)


def test_default_supersample_is_identity(tmp_path):
    from frameforge.vision.infrastructure.vectorize import trace_to_svg

    img = _aa_disk_png(tmp_path)
    _, meta = trace_to_svg(img, threshold=128)
    assert meta["supersample"] == 1
    assert meta["turdsize_effective"] == 2          # the unscaled default


def test_usecase_lane_fits_supersampled_trace_back_to_page(tmp_path):
    """The MCP lane must box-fit a FULL-IMAGE supersampled trace: the potrace
    viewport is s×-larger than the page, so skipping the fit (the pre-B5
    invariant 'viewport == page') lands every shape at s× scale — caught by the
    lotus end-to-end run, pinned here."""
    import yaml

    from frameforge.mcp.usecases import vectorize_image
    from frameforge.vision.domain.gradient_fit import flatten_path_d
    from frameforge.vision.infrastructure.vectorize import _object_transform

    img = _aa_disk_png(tmp_path)
    res = vectorize_image(image=img, mode="trace", supersample=2, threshold=128,
                          raster_png=False, session_id="ss-fit", session_root=tmp_path)
    assert res.get("ok") is True, res.get("error")
    assert res["vectorize"]["supersample"] == 2
    doc = yaml.safe_load(
        (tmp_path / "ss-fit" / "generated.fg.yaml").read_text(encoding="utf-8"))
    xs, ys = [], []
    for layer in doc["pages"][0]["layers"]:
        for obj in layer["objects"]:
            if obj.get("type") != "path" or not obj.get("d"):
                continue
            tf = _object_transform(obj)
            assert tf is not None, obj.get("style")
            tx, ty, sx, sy = tf
            for sub in flatten_path_d(obj["d"]):
                for x, y in sub:
                    xs.append(sx * x + tx)
                    ys.append(sy * y + ty)
    assert xs, "the trace must produce path geometry"
    # the disk lives in a 200×200 page; unfitted s=2 geometry would reach ~320+
    assert max(xs) <= 205 and max(ys) <= 205, (max(xs), max(ys))
    assert min(xs) >= -5 and min(ys) >= -5
