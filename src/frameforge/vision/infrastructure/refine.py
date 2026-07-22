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


# --------------------------------------------------------------------------- #
#  Geometry refinement (Gap G3): descent on stroke_outline parameters          #
# --------------------------------------------------------------------------- #

#: Displacement family over a provenance spine: global Δ, tip-weighted Δ
#: (weight t), base-weighted Δ (weight 1−t), bow Δ (weight sin πt), and a
#: multiplicative width scale — 9 parameters that cover the fitting lane's
#: real error modes (placement, tip/base landing, bow, erosion-narrowed width)
#: while PRESERVING the spine's fine detail (no re-parameterisation).
_GEO_STEPS_PX = (8.0, 3.0)
_GEO_WIDTH_FACTORS = (1.10, 1.04)


def _apply_geo_params(prov, v):
    """The displacement family applied to a provenance dict → (spine, width)."""
    import math

    spine = prov["spine"]
    n = len(spine)
    gdx, gdy, tdx, tdy, bdx, bdy, mdx, mdy, ws = v
    out = []
    for i, (x, y) in enumerate(spine):
        t = i / (n - 1) if n > 1 else 0.0
        bow = math.sin(math.pi * t)
        out.append((x + gdx + t * tdx + (1.0 - t) * bdx + bow * mdx,
                    y + gdy + t * tdy + (1.0 - t) * bdy + bow * mdy))
    return out, prov["width"] * ws


def _rebuild_outline(obj, prov, spine, width):
    """Re-emit the object through stroke_outline with new geometry, in place.

    Non-geometric fields (fill, id, decorative, stroke, style, …) carry over;
    the provenance meta is refreshed by stroke_outline itself, so the refined
    object stays byte-consistent with its own parameters."""
    from frameforge.sdk.outline import stroke_outline

    from ..domain.spine_fit import spine_profile

    passthrough = {k: v for k, v in obj.items()
                   if k not in ("type", "d", "meta")}
    user_meta = {k: v for k, v in (obj.get("meta") or {}).items()
                 if k != "stroke_outline"}
    if user_meta:
        passthrough["meta"] = user_meta
    profile = (spine_profile(prov["profile"])
               if prov.get("profile") else None)
    kwargs = {"cap": prov.get("cap", "butt"), "join": prov.get("join", "miter")}
    if prov.get("pen_angle") is not None:
        kwargs["pen_angle"] = prov["pen_angle"]
        kwargs["pen_thin"] = prov.get("pen_thin", 0.25)
    new_obj = stroke_outline(spine, width, profile=profile, **kwargs,
                             **passthrough)
    old_d = obj.get("d")
    obj.clear()
    obj.update(new_obj)
    return old_d


def refine_geometry(
    document: "dict[str, Any]",
    image,
    *,
    max_iters: int = 2,
    min_pixels: int = 64,
    margin: int = 60,
) -> dict[str, Any]:
    """Descend stroke_outline GEOMETRY against ``image``, in place (G3).

    Walks page 1's objects carrying ``meta.stroke_outline`` provenance (fill-
    bearing bodies; overlays are synchronised, not descended), and coordinate-
    descends the 9-parameter displacement family per object, minimising the
    analytic claim-vs-background error inside a fixed window: claimed pixels
    cost ``|own paint − reference|²``, unclaimed free pixels cost
    ``|background paint − reference|²``. Later objects in paint order occlude
    (their initial regions are excluded). Steps are bounded and accepted only
    on strict improvement — the pass can only descend and is deterministic.

    After a body moves, its dependent overlays (the A2/craft idiom: rim
    strokes sharing the body's ``d``, and any ``style.clip_path`` referencing
    it) are re-pointed at the new outline so the document stays coherent.

    Returns ``{"refined", "improved", "skipped", "unevaluable", "sq_before",
    "sq_after"}``; raises ``ValueError`` on a canvas/reference size mismatch.
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

    objects: list[dict] = []
    for layer in (page.get("layers") or []):
        for obj in (layer.get("objects") or []):
            if isinstance(obj, dict):
                objects.append(obj)

    # the background predictor: the first fill-bearing object (the page ground)
    bg_paint = None
    bg_tf = (0.0, 0.0, 1.0, 1.0)
    for obj in objects:
        if obj.get("fill") is not None:
            bg_paint = obj.get("fill")
            bg_tf = _object_transform(obj) or bg_tf
            break

    refinable: list[tuple[int, dict]] = []
    skipped = unevaluable = 0
    for idx, obj in enumerate(objects):
        prov = (obj.get("meta") or {}).get("stroke_outline")
        if not isinstance(prov, dict) or not prov.get("spine"):
            if obj.get("type") == "path":
                skipped += 1
            continue
        if obj.get("fill") is None:
            skipped += 1
            continue
        refinable.append((idx, obj))

    # occlusion: masks of every LATER paint-bearing entry, from the initial state
    entry_masks: dict[int, Any] = {}
    for idx, obj in enumerate(objects):
        got = _entry_mask(obj, image.size, np)
        if got is not None:
            entry_masks[idx] = got[1]

    refined = improved = 0
    sq_before_total = sq_after_total = 0.0
    for idx, obj in refinable:
        prov = obj["meta"]["stroke_outline"]
        tf = _object_transform(obj) or (0.0, 0.0, 1.0, 1.0)
        base_mask = entry_masks.get(idx)
        if base_mask is None or int(base_mask.sum()) < min_pixels:
            skipped += 1
            continue
        ys, xs = np.nonzero(base_mask)
        y0 = max(0, int(ys.min()) - margin)
        y1 = min(H, int(ys.max()) + margin + 1)
        x0 = max(0, int(xs.min()) - margin)
        x1 = min(W, int(xs.max()) + margin + 1)
        win_ys, win_xs = np.mgrid[y0:y1, x0:x1]
        fy = win_ys.ravel().astype(np.float64)
        fx = win_xs.ravel().astype(np.float64)
        target = src[y0:y1, x0:x1].reshape(-1, 3)

        own_pred = _paint_eval(obj.get("fill"), fx, fy, tf, np)
        bg_pred = _paint_eval(bg_paint, fx, fy, bg_tf, np)
        if own_pred is None or bg_pred is None:
            unevaluable += 1
            continue
        own_err = ((own_pred - target) ** 2).sum(axis=1)
        bg_err = ((bg_pred - target) ** 2).sum(axis=1)

        occluded = np.zeros((H, W), dtype=bool)
        for j, m in entry_masks.items():
            if j > idx:
                occluded |= m
        free = ~occluded[y0:y1, x0:x1].ravel()

        def cost(v):
            spine, width = _apply_geo_params(prov, v)
            if width <= 1.0:
                return float("inf"), None
            from frameforge.sdk.outline import stroke_outline

            from ..domain.spine_fit import spine_profile

            probe = stroke_outline(
                spine, width,
                profile=(spine_profile(prov["profile"])
                         if prov.get("profile") else None),
                cap=prov.get("cap", "butt"), join=prov.get("join", "miter"),
                emit_params=False, fill="#000")
            shaped = _shape_mask(probe, image.size)
            if shaped is None:
                return float("inf"), None
            m = (np.asarray(shaped[0]) > 0)[y0:y1, x0:x1].ravel()
            claimed = m & free
            err = float(own_err[claimed].sum() + bg_err[free & ~m].sum())
            return err, None

        v = [0.0] * 8 + [1.0]
        best, _ = cost(v)
        start = best
        for _sweep in range(max(1, int(max_iters))):
            moved = False
            for k in range(9):
                if k == 8:
                    trials = ([f for f in _GEO_WIDTH_FACTORS]
                              + [1.0 / f for f in _GEO_WIDTH_FACTORS])
                    for f in trials:
                        cand = list(v)
                        cand[8] = v[8] * f
                        c, _ = cost(cand)
                        if c < best - 1e-9:
                            best, v, moved = c, cand, True
                else:
                    for step in _GEO_STEPS_PX:
                        for sign in (1.0, -1.0):
                            cand = list(v)
                            cand[k] = v[k] + sign * step
                            c, _ = cost(cand)
                            if c < best - 1e-9:
                                best, v, moved = c, cand, True
            if not moved:
                break

        refined += 1
        sq_before_total += start
        sq_after_total += best
        if best < start - 1e-9:
            improved += 1
            spine, width = _apply_geo_params(prov, v)
            old_d = _rebuild_outline(obj, prov, spine, round(width, 2))
            new_d = obj.get("d")
            # synchronise dependent overlays: same-d rims and self-clips
            for other in objects:
                if other is obj or not isinstance(other, dict):
                    continue
                if other.get("d") == old_d:
                    other["d"] = new_d
                clip = ((other.get("style") or {}).get("clip_path") or {})
                if isinstance(clip, dict) and (clip.get("args") or {}).get("d") == old_d:
                    clip["args"]["d"] = new_d

    return {
        "refined": refined,
        "improved": improved,
        "skipped": skipped,
        "unevaluable": unevaluable,
        "sq_before": round(sq_before_total, 1),
        "sq_after": round(sq_after_total, 1),
    }


__all__ = ["refine_document", "refine_geometry"]
