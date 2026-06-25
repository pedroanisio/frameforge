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
