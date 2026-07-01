"""Raster → FrameGraph vectorizer (the ingestion front-end).

Turns a bitmap into editable FrameGraph vector objects with OpenCV (the optional
``vision`` dependency group). Two modes:

- ``region``  — k-means colour quantisation → per-colour contours → filled
  polygons. A flat, editable *vector base* of the image.
- ``outline`` — Canny edges → contours → polylines. The image's *full outline*
  as line art.

Emits plain FrameGraph object dicts (no model import), so the renderer draws them
directly and the package boundary stays clean. OpenCV/NumPy are imported lazily,
so importing this module costs nothing until a function runs.

Honest limits: output is *polygonal* (straight segments), not Bézier-smooth — for
smooth curves route a Potrace/VTracer SVG through ``svg_import``. Soft gradients
posterise into colour bands (control with ``colors``). This is a faithful,
editable base, not a semantic one; per-object *named* layers need the
segmentation/OCR tiers layered on top.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def image_size(path: "str | Path") -> tuple[int, int]:
    """Return the (width, height) of an image without vectorising it."""
    import cv2
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"could not read image: {path}")
    h, w = img.shape[:2]
    return w, h


def _load_scaled(path, max_dim):
    import cv2
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"could not read image: {path}")
    h, w = img.shape[:2]
    longest = max(w, h)
    if max_dim and longest > max_dim:
        s = max_dim / longest
        img = cv2.resize(img, (int(round(w * s)), int(round(h * s))), interpolation=cv2.INTER_AREA)
    return img


def _hex_bgr(bgr) -> str:
    b, g, r = (int(v) for v in bgr)
    return "#%02X%02X%02X" % (r, g, b)


def _contour_polys(mask, *, detail, min_area, closed):
    import cv2
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL if closed else cv2.RETR_LIST,
                               cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for c in cnts:
        if closed:
            if cv2.contourArea(c) < min_area:
                continue
            eps = max(0.5, detail * cv2.arcLength(c, True))
            ap = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
            if len(ap) >= 3:
                polys.append((cv2.contourArea(c), [[float(x), float(y)] for x, y in ap]))
        else:
            if cv2.arcLength(c, False) < min_area:
                continue
            ap = cv2.approxPolyDP(c, max(0.8, detail * 1000), False).reshape(-1, 2)
            if len(ap) >= 2:
                polys.append((cv2.arcLength(c, False), [[float(x), float(y)] for x, y in ap]))
    return polys


def raster_to_objects(
    path: "str | Path",
    *,
    mode: str = "region",
    colors: int = 10,
    detail: float = 0.004,
    min_area: float = 90.0,
    max_dim: int = 900,
    ink: str = "#1E2440",
    stroke_width: float = 1.0,
) -> tuple[list[dict[str, Any]], int, int]:
    """Vectorise ``path``; return ``(objects, width, height)`` in image pixels.

    ``mode='region'`` traces filled polygons over ``colors`` quantised colours;
    ``mode='outline'`` traces edges into polylines. ``detail`` is the
    Douglas–Peucker epsilon as a fraction of contour length (higher = simpler);
    ``min_area`` drops noise.
    """
    import cv2
    import numpy as np

    img = _load_scaled(path, max_dim)
    h, w = img.shape[:2]
    objs: list[dict[str, Any]] = []

    if mode == "region":
        z = img.reshape(-1, 3).astype(np.float32)
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
        k = max(2, int(colors))
        _, labels, centers = cv2.kmeans(z, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
        centers = centers.astype(np.uint8)
        lab = labels.reshape(h, w)
        shapes = []
        kernel = np.ones((3, 3), np.uint8)
        for ci in range(k):
            mask = (lab == ci).astype(np.uint8) * 255
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            hexc = _hex_bgr(centers[ci])
            for area, pts in _contour_polys(mask, detail=detail, min_area=min_area, closed=True):
                shapes.append((area, pts, hexc))
        shapes.sort(key=lambda t: -t[0])              # big shapes first, detail on top
        objs = [{"type": "polygon", "points": pts, "fill": hexc} for _, pts, hexc in shapes]
        return objs, w, h

    if mode == "outline":
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Auto-Canny: thresholds from the image median, so contrast is adapted to
        # rather than guessed (a fixed 60/160 misses low-contrast edges).
        med = float(np.median(gray))
        lo = int(max(0, 0.55 * med))
        hi = int(min(255, max(lo + 30, 1.33 * med)))
        edges = cv2.Canny(gray, lo, hi)
        edges = cv2.dilate(edges, np.ones((2, 2), np.uint8))
        for _, pts in _contour_polys(edges, detail=detail, min_area=max(8.0, min_area / 3), closed=False):
            objs.append({"type": "polyline", "points": pts, "stroke": ink,
                         "stroke_style": {"stroke_width": stroke_width}})
        return objs, w, h

    raise ValueError(f"unknown mode {mode!r} (expected 'region' or 'outline')")


_POTRACE_HINT = (
    "smooth (Bézier) tracing needs the `potrace` binary on PATH (Debian/Ubuntu: "
    "`apt install potrace`; it ships in the FrameGraph Docker image). The `region`/"
    "`outline` modes need no extra binary."
)


def potrace_path() -> str | None:
    """Return the potrace executable path, or None when it is not installed."""
    return shutil.which("potrace")


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


def _potrace_hex(color: str) -> str:
    """potrace's --color needs a 6-digit #rrggbb; expand a 3-digit #rgb shorthand."""
    c = (color or "").strip()
    if len(c) == 4 and c.startswith("#"):
        return "#" + "".join(ch * 2 for ch in c[1:])
    return c


def trace_to_svg(path: "str | Path", *, region_box: "list[float] | None" = None,
                 threshold: int | None = None, invert: Any = "auto",
                 turdsize: int = 2, alphamax: float = 1.0, opttolerance: float = 0.2,
                 fill: str = "#000000") -> tuple[str, dict[str, Any]]:
    """Threshold + potrace-trace an image (or a normalized region) into SVG text.

    The smooth-curve complement to :func:`raster_to_objects`: potrace fits Bézier
    outlines to the thresholded ink, which the caller lowers to FrameGraph objects
    via :func:`framegraph.vision.infrastructure.svg_import.svg_to_objects`
    (``box=region_px`` fits the traced crop back to its place in the full image).
    Returns ``(svg_text, meta)``; ``meta`` carries the pixel region, threshold,
    invert decision, and traced path count.
    """
    exe = potrace_path()
    if not exe:
        raise RuntimeError(_POTRACE_HINT)
    from PIL import Image, ImageStat

    img = Image.open(str(path)).convert("RGB")
    W, H = img.size
    if region_box:
        x, y, w, h = region_box
        ox, oy = _clamp01(x) * W, _clamp01(y) * H
        cw = max(1.0, (_clamp01(x + w) - _clamp01(x)) * W)
        ch = max(1.0, (_clamp01(y + h) - _clamp01(y)) * H)
        crop = img.crop((int(ox), int(oy), int(round(ox + cw)), int(round(oy + ch))))
    else:
        ox, oy, cw, ch, crop = 0.0, 0.0, float(W), float(H), img

    gray = crop.convert("L")
    mean = ImageStat.Stat(gray).mean[0]
    # potrace traces BLACK (0) as foreground; `invert=auto` makes the bright pixels
    # the foreground when the ground is dark (a light mark on a dark panel).
    do_invert = (mean < 127.0) if invert == "auto" else bool(invert)
    thr = int(threshold) if threshold is not None else 128
    bw = gray.point(lambda v: 255 if v >= thr else 0, mode="1")
    if do_invert:
        bw = bw.point(lambda v: 0 if v else 255, mode="1")

    tmp = Path(tempfile.mkdtemp(prefix="fg-trace-"))
    try:
        src, out = tmp / "in.bmp", tmp / "out.svg"
        bw.save(src)  # 1-bit BMP; potrace reads BMP + PNM
        cmd = [exe, str(src), "--svg", "-o", str(out),
               "--turdsize", str(int(turdsize)), "--alphamax", str(float(alphamax)),
               "--opttolerance", str(float(opttolerance))]
        if fill:
            cmd += ["--color", _potrace_hex(fill)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"potrace failed: {proc.stderr.strip() or proc.returncode}")
        svg_text = out.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    meta = {
        "backend": "potrace",
        "image": {"width_px": W, "height_px": H},
        "region_px": [round(ox, 2), round(oy, 2), round(cw, 2), round(ch, 2)],
        "threshold": thr,
        "inverted": do_invert,
        "path_count": svg_text.count("<path"),
    }
    return svg_text, meta


def ocr_text_objects(path: "str | Path", *, max_dim: int = 1400,
                     min_conf: float = 60.0, color: str = "#1E2440") -> list[dict[str, Any]]:
    """Detect text via Tesseract → editable FrameGraph ``text`` objects.

    Returns an empty list when ``pytesseract`` / the Tesseract binary is absent,
    so callers can treat OCR as a best-effort enrichment layer.
    """
    try:
        import cv2
        import pytesseract
        from pytesseract import Output
    except Exception:
        return []
    img = _load_scaled(path, max_dim)
    try:
        data = pytesseract.image_to_data(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), output_type=Output.DICT)
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for i, word in enumerate(data.get("text", [])):
        word = (word or "").strip()
        try:
            conf = float(data["conf"][i])
        except (ValueError, KeyError):
            conf = -1.0
        if not word or conf < min_conf:
            continue
        x, y, ww, hh = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        out.append({"type": "text", "box": [float(x), float(y), float(ww), float(hh)], "text": word,
                    "style": {"font_family": ["Inter", "Arial", "sans-serif"],
                              "font_size": float(hh), "font_weight": 700, "color": color,
                              "vertical_align": "middle"}})
    return out


# --------------------------------------------------------------------------- #
#  layered logo tracer  --  solid-bg detect + AA-aware palette + even-odd holes
# --------------------------------------------------------------------------- #
def _hex_rgb(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(max(0, min(255, round(float(v))))) for v in rgb[:3])


def _solid_fill(img, mask) -> str:
    """The layer's true fill, read from its ERODED interior (ignores AA edge pixels)."""
    import cv2
    import numpy as np

    er = cv2.erode(mask.astype("uint8"), np.ones((5, 5), "uint8"))
    px = np.asarray(img, float)[er > 0] if er.any() else np.asarray(img, float)[mask]
    return _hex_rgb([np.median(px[:, i]) for i in range(3)])


def _trace_mask_d(mask, box, *, up: int, eps: float, min_area: float) -> str:
    """cv2 contour trace of a binary mask inside ``box`` → one SVG ``d`` (even-odd holes)."""
    import cv2

    sub = mask[box[1]:box[3], box[0]:box[2]].astype("uint8") * 255
    if sub.size == 0:
        return ""
    big = cv2.resize(sub, (sub.shape[1] * up, sub.shape[0] * up), interpolation=cv2.INTER_LINEAR)
    _, bw = cv2.threshold(big, 127, 255, cv2.THRESH_BINARY)
    cnts, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    ox, oy = box[0], box[1]
    parts = []
    for c in cnts:
        if cv2.contourArea(c) < (up * up) * min_area:
            continue
        p = cv2.approxPolyDP(c, eps * cv2.arcLength(c, True), True).reshape(-1, 2).astype(float)
        p[:, 0] = p[:, 0] / up + ox
        p[:, 1] = p[:, 1] / up + oy
        parts.append("M " + " L ".join("%.2f %.2f" % (x, y) for x, y in p) + " Z")
    return " ".join(parts)


def raster_to_layers(
    path: "str | Path",
    *,
    max_colors: int = 4,
    detail: float = 0.0012,
    min_area: float = 2.0,
    upscale: int = 6,
    bg_diff: float = 40.0,
    exclude_corner: bool = False,
) -> tuple[list[dict[str, Any]], int, int]:
    """Layered tracer for flat / logo art on a SOLID background.

    Detects the background from the corners, clusters the *eroded* foreground into
    its distinct true colours (so anti-aliased edge pixels don't spawn phantom
    colours), assigns every pixel to its nearest colour, and traces each colour layer
    with cv2 (all nesting levels → even-odd holes). Emits one ``path`` object per
    layer (largest first, so fine detail paints on top). Returns ``(objects, w, h)``.

    Honest limit: assumes a solid background — a gradient/photographic ground
    posterises. Straight-segment paths (no Béziers); use ``trace`` (potrace) for
    smooth curves, ``region`` for a quick colour base.
    """
    import cv2
    import numpy as np
    from PIL import Image

    img = Image.open(str(path)).convert("RGB")
    W, H = img.size
    A = np.asarray(img, float)
    g = A.mean(2)
    bg = np.median(np.array([A[5, 5], A[5, W - 6], A[H - 6, 5], A[H - 6, W - 6]]), 0)
    fg = np.abs(g - float(bg.mean())) > bg_diff
    if exclude_corner:
        fg[int(H * 0.72):, :int(W * 0.12)] = False
    if not fg.any():
        return [], W, H
    ys, xs = np.where(fg)
    box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)

    er = cv2.erode(fg.astype("uint8"), np.ones((5, 5), "uint8"), iterations=2).astype(bool)
    src = er if er.sum() > 500 else fg
    px = np.float32(np.asarray(img)[src])
    if len(px) == 0:
        return [], W, H
    uniq = len(np.unique(px.astype(np.uint8).reshape(-1, 3), axis=0))
    K = int(min(8, max(1, uniq)))
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, lab, cen = cv2.kmeans(px, K, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(lab.flatten(), minlength=K)
    kept = []
    for i in np.argsort(-counts):
        if counts[i] < 30:
            continue
        if any(np.linalg.norm(cen[i] - k) < 40.0 for k in kept):
            continue
        kept.append(cen[i])
        if len(kept) >= max_colors:
            break
    if not kept:
        return [], W, H

    C = np.array([bg] + list(kept), float)
    full = ((A.reshape(-1, 1, 3) - C.reshape(1, -1, 3)) ** 2).sum(-1).argmin(1).reshape(H, W)
    masks = [full == (i + 1) for i in range(len(kept))]
    order = sorted(range(len(masks)), key=lambda i: -int(masks[i].sum()))

    objs: list[dict[str, Any]] = []
    for k in order:
        d = _trace_mask_d(masks[k], box, up=upscale, eps=detail, min_area=min_area)
        if not d:
            continue
        objs.append({"type": "path", "d": d, "fill": _solid_fill(img, masks[k]),
                     "style": {"fill_rule": "evenodd"}})
    return objs, W, H
