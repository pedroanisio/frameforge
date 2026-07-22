"""Error-driven reconstruction refinement (Gap B6): visibility-aware refit.

The fitting lane samples each shape's FULL winding mask — including pixels a
later object paints over — so overlapped shapes inherit contaminated fits, and
nothing descends the residual after emission. This pass closes that loop:

1. **Ownership.** Every paintable entry claims its coverage region in paint
   order (fill shapes by their winding mask; A2 band overlays by their
   inner-stroke ring, reconstructed from the stroke width through the object
   transform). The last claimant per pixel owns it — exactly what the render
   shows.
2. **Refit.** Each ownable paint — flat hex, user-space linear ``line``,
   user-space radial ``at``+``radius`` — is refitted on its VISIBLE pixels
   (``fit_paint`` in user geometry, converted back to the object's local
   space). Legacy bbox/angle paints are not analytically evaluable here and
   are counted, never silently guessed (PALS).
3. **Guard.** A refit is kept only when that entry's analytic rms against the
   reference improves — the pass can only descend, and a second pass is a
   fixed point.

Pure vision-layer machinery (NumPy + PIL, lazily imported); deterministic.
"""
from __future__ import annotations

from typing import Any

from .vectorize import (
    _chamfer_distance,
    _object_transform,
    _paint_to_local,
    _shape_mask,
)

_DEFAULT_MIN_PIXELS = 24


def _stop_arrays(stops, np):
    try:
        pos = np.asarray(
            [float(str(s.get("position", "0%")).rstrip("%")) / 100.0 for s in stops],
            dtype=np.float64)
        cols = np.asarray(
            [[int(str(s["color"]).lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
             for s in stops], dtype=np.float64)
    except (KeyError, TypeError, ValueError):
        return None, None
    if len(pos) == 0 or np.any(np.diff(pos) < 0):
        return None, None
    return pos, cols


def _paint_eval(paint, xs, ys, tf, np):
    """Predicted RGB rows for a LOCAL-space paint at image-space pixels.

    Returns an ``(n, 3)`` array, or ``None`` when the paint is not analytically
    evaluable (bbox/angle gradients, patterns, tokens)."""
    if isinstance(paint, str):
        h = paint.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) < 6:
            return None
        try:
            rgb = np.asarray([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)
        except ValueError:
            return None
        return np.broadcast_to(rgb, (len(xs), 3))
    if not isinstance(paint, dict):
        return None
    pos, cols = _stop_arrays(paint.get("stops") or [], np)
    if pos is None:
        return None
    tx, ty, sx, sy = tf
    if paint.get("kind") == "linear" and paint.get("line") is not None:
        (lx1, ly1), (lx2, ly2) = paint["line"]
        x1, y1 = sx * lx1 + tx, sy * ly1 + ty        # local → image
        x2, y2 = sx * lx2 + tx, sy * ly2 + ty
        dx, dy = x2 - x1, y2 - y1
        denom = dx * dx + dy * dy or 1.0
        t = ((xs - x1) * dx + (ys - y1) * dy) / denom
    elif (paint.get("kind") == "radial" and paint.get("radius")
          and isinstance(paint.get("at"), (list, tuple))):
        ax, ay = paint["at"]
        cx, cy = sx * float(ax) + tx, sy * float(ay) + ty
        mag = (abs(sx) + abs(sy)) / 2.0 or 1.0
        r = float(paint["radius"]) * mag or 1.0
        t = np.hypot(xs - cx, ys - cy) / r
    else:
        return None
    t = np.clip(t, 0.0, 1.0)
    out = np.empty((len(xs), 3), dtype=np.float64)
    for ch in range(3):
        out[:, ch] = np.interp(t, pos, cols[:, ch])
    return out


def _entry_mask(obj, size, np):
    """(kind, mask, tf) for one paintable object, or None.

    ``kind`` is ``"fill"`` (winding mask) or ``"stroke"`` (an A2 band
    overlay's inner-stroke ring). Rects are the vectorize lane's page
    backgrounds; groups/other types are out of this pass's scope."""
    W, H = size
    t = obj.get("type")
    if t == "rect" and obj.get("box") is not None and obj.get("fill") is not None:
        try:
            x, y, w, h = (float(v) for v in obj["box"][:4])
        except (TypeError, ValueError):
            return None
        mask = np.zeros((H, W), dtype=bool)
        mask[max(0, int(y)):int(y + h), max(0, int(x)):int(x + w)] = True
        return "fill", mask, (0.0, 0.0, 1.0, 1.0)
    if t not in ("polygon", "path"):
        return None
    shaped = _shape_mask(obj, size)
    if shaped is None:
        return None
    mask = np.asarray(shaped[0]) > 0
    tf = _object_transform(obj) or (0.0, 0.0, 1.0, 1.0)
    if "fill" in obj and obj.get("fill") is not None:
        return "fill", mask, tf
    if obj.get("stroke") is not None and (obj.get("style") or {}).get("clip_path"):
        width_local = (obj.get("stroke_style") or {}).get("stroke_width")
        try:
            width_local = float(width_local)
        except (TypeError, ValueError):
            return None
        mag = (abs(tf[2]) + abs(tf[3])) / 2.0 or 1.0
        depth = width_local * mag / 2.0
        if depth <= 0:
            return None
        dist = _chamfer_distance(mask)
        return "stroke", (dist > 0) & (dist <= depth), tf
    return None


def refine_document(
    document: "dict[str, Any]",
    image,
    *,
    min_pixels: int = _DEFAULT_MIN_PIXELS,
) -> dict[str, Any]:
    """Refine page 1's fitted paints against ``image``, in place.

    ``image`` must match the page canvas pixel-for-pixel (refinement compares
    per pixel; a mismatch raises rather than silently rescaling). Returns
    ``{"refit", "improved", "skipped", "unevaluable", "rms_before",
    "rms_after"}`` — the rms pair is measured over the owned pixels of every
    entry whose CURRENT paint is analytically evaluable, so before/after are
    like-for-like.
    """
    import numpy as np

    pages = document.get("pages") or []
    page = pages[0] if pages else {}
    W, H = image.size
    size = ((page.get("canvas") or {}).get("size") or [])
    if len(size) >= 2 and (int(size[0]), int(size[1])) != (W, H):
        raise ValueError(
            f"reference size {W}x{H} does not match the page canvas size "
            f"{int(size[0])}x{int(size[1])} — refinement compares pixel-for-pixel")
    src = np.asarray(image.convert("RGB"), dtype=np.float64)

    entries: list[tuple[dict, str, Any, tuple]] = []
    for layer in (page.get("layers") or []):
        for obj in (layer.get("objects") or []):
            if not isinstance(obj, dict):
                continue
            got = _entry_mask(obj, image.size, np)
            if got is not None and got[1].any():
                entries.append((obj, got[0], got[1], got[2]))

    owner = np.full((H, W), -1, dtype=np.int32)
    for i, (_, _, mask, _) in enumerate(entries):
        owner[mask] = i

    from ..domain.gradient_fit import fit_paint

    refit = improved = skipped = unevaluable = 0
    sq_before = sq_after = 0.0
    n_metric = 0
    for i, (obj, kind, _mask, tf) in enumerate(entries):
        ys, xs = np.nonzero(owner == i)
        if len(ys) == 0:
            continue
        fx, fy = xs.astype(np.float64), ys.astype(np.float64)
        target = src[ys, xs]
        paint = obj.get("fill") if kind == "fill" else obj.get("stroke")
        pred_old = _paint_eval(paint, fx, fy, tf, np)
        if pred_old is None:
            unevaluable += 1
            continue
        err_old = float(((pred_old - target) ** 2).sum())
        if len(ys) < max(3, int(min_pixels)):
            skipped += 1
            sq_before += err_old
            sq_after += err_old
            n_metric += target.size
            continue
        out = fit_paint(np.stack([fx, fy], axis=1), target, geometry="user")
        new_paint = out["fill"]
        if isinstance(new_paint, dict):
            new_paint = _paint_to_local(dict(new_paint), obj)
        pred_new = _paint_eval(new_paint, fx, fy, tf, np)
        err_new = (float(((pred_new - target) ** 2).sum())
                   if pred_new is not None else float("inf"))
        refit += 1
        if err_new < err_old - 1e-9:
            improved += 1
            if kind == "fill":
                obj["fill"] = new_paint
            else:
                obj["stroke"] = new_paint
            final = err_new
        else:
            final = err_old
        sq_before += err_old
        sq_after += final
        n_metric += target.size

    return {
        "refit": refit,
        "improved": improved,
        "skipped": skipped,
        "unevaluable": unevaluable,
        "rms_before": round((sq_before / n_metric) ** 0.5, 4) if n_metric else 0.0,
        "rms_after": round((sq_after / n_metric) ** 0.5, 4) if n_metric else 0.0,
    }


__all__ = ["refine_document"]
