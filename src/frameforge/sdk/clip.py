"""Clip-path constructors for the FrameForge SDK.

These assemble the plain ``{shape, args}`` dicts the authoritative ``ClipPath``
model already accepts (``frameforge.model.ClipPath``) and the SVG proxy already
honours (``render_fixtures`` ``_style_clip_id``). They add no schema of their own;
they only spare callers hand-building the style bag and getting the argument
names right.

Pair them with :meth:`frameforge.sdk.PageBuilder.group` / :meth:`~PageBuilder.frame`
via ``clip=...``, or drop the result straight into a primitive's style::

    layer.group(children, clip=clip_rect([64, 64, 480, 320]))     # panel clip
    layer.rect(box, fill=grad, style={"clip_path": clip_circle()})

``polygon`` / ``path`` carry **absolute** page geometry, so they clip a box-less
group; ``inset`` / ``circle`` / ``ellipse`` derive from the clipped object's own
``box`` when their args are omitted (and so need a boxed subject).
"""
from __future__ import annotations

from typing import Any, Sequence

from frameforge.sdk.geometry import Path as _GeomPath, Vec2

Point = Sequence[float]


def clip_rect(box: Sequence[float]) -> dict[str, Any]:
    """Clip to an absolute rectangle ``[x, y, w, h]``.

    Lowered to a ``polygon`` of the four corners (not ``inset``) so it clips a
    group that has no ``box`` of its own — the manga-panel case.
    """
    x, y, w, h = (float(v) for v in tuple(box)[:4])
    return {"shape": "polygon",
            "args": {"points": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]}}


def clip_inset(
    top: float,
    right: float | None = None,
    bottom: float | None = None,
    left: float | None = None,
    *,
    box: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Clip to an inset of the subject box (CSS ``inset()`` order: T, R, B, L).

    With one value the inset is uniform. ``box`` overrides the derived subject
    rectangle when the clipped object has no usable box.
    """
    r = top if right is None else right
    b = top if bottom is None else bottom
    left_ = r if left is None else left
    args: dict[str, Any] = {"top": top, "right": r, "bottom": b, "left": left_}
    if box is not None:
        args["box"] = [float(v) for v in tuple(box)[:4]]
    return {"shape": "inset", "args": args}


def clip_circle(center: Point | None = None, r: float | None = None) -> dict[str, Any]:
    """Clip to a circle; with no args it derives centre + radius from the box."""
    args: dict[str, Any] = {}
    if center is not None:
        args["center"] = _point(center)
    if r is not None:
        args["r"] = float(r)
    return _shape("circle", args)


def clip_ellipse(center: Point | None = None, rx: float | None = None,
                 ry: float | None = None) -> dict[str, Any]:
    """Clip to an ellipse; omitted args derive from the box (see :func:`clip_circle`)."""
    args: dict[str, Any] = {}
    if center is not None:
        args["center"] = _point(center)
    if rx is not None:
        args["rx"] = float(rx)
    if ry is not None:
        args["ry"] = float(ry)
    return _shape("ellipse", args)


def clip_polygon(points: Sequence[Point]) -> dict[str, Any]:
    """Clip to an absolute polygon through ``points`` (``Vec2`` or ``[x, y]``)."""
    return {"shape": "polygon", "args": {"points": [_point(p) for p in points]}}


def clip_path(d: Any) -> dict[str, Any]:
    """Clip to an SVG path; ``d`` may be a string or a :class:`frameforge.sdk.Path`."""
    if isinstance(d, _GeomPath):
        d = d.d()
    return {"shape": "path", "args": {"d": d}}


def normalize_clip(clip: Any) -> dict[str, Any] | str:
    """Coerce a ``clip=`` argument to a model ``clip_path`` value.

    Accepts a box ``[x, y, w, h]`` (→ :func:`clip_rect`), a points list
    (→ :func:`clip_polygon`), a :class:`~frameforge.sdk.Path` (→ :func:`clip_path`),
    an already-built ``{shape, args}`` dict, or a raw CSS ``clip-path`` string.
    """
    if isinstance(clip, _GeomPath):
        return clip_path(clip)
    if isinstance(clip, str):
        return clip
    if isinstance(clip, dict):
        return clip
    if isinstance(clip, (list, tuple)):
        if len(clip) == 4 and all(isinstance(v, (int, float)) for v in clip):
            return clip_rect(clip)
        return clip_polygon(clip)
    raise TypeError(
        "clip must be a box [x, y, w, h], a points list, a clip dict, a Path, "
        f"or a CSS clip-path string; got {type(clip).__name__}"
    )


def mask_none() -> str:
    """Return the model's explicit no-mask sentinel."""
    return "none"


def mask_url(src: str) -> dict[str, str]:
    """Build an image mask source from a URL, data URI, or ``defs.assets`` key."""
    return {"url": src}


def mask_gradient(gradient: dict[str, Any]) -> dict[str, Any]:
    """Return a gradient mask source.

    The model accepts gradients anywhere an ``ImagePaint`` mask is valid; this
    helper names that route so authors do not have to infer it from the schema.
    """
    return gradient


def normalize_mask(mask: Any) -> dict[str, Any] | str:
    """Coerce a mask source to a model ``style.mask`` value."""
    if mask is None:
        return mask_none()
    if isinstance(mask, str):
        return mask
    if isinstance(mask, dict):
        return mask
    raise TypeError(
        "mask must be None, a string, or an ImagePaint dict such as "
        f"mask_url(...); got {type(mask).__name__}"
    )


def mask_style(mask: Any) -> dict[str, Any]:
    """Bundle a mask source under an object's inline ``style`` field."""
    return {"style": {"mask": normalize_mask(mask)}}


# ---- internals ------------------------------------------------------------ #
def _shape(shape: str, args: dict[str, Any]) -> dict[str, Any]:
    return {"shape": shape, "args": args} if args else {"shape": shape}


def _point(value: Any) -> list[float]:
    if isinstance(value, Vec2):
        return [value.x, value.y]
    return [float(value[0]), float(value[1])]


__all__ = [
    "clip_circle",
    "clip_ellipse",
    "clip_inset",
    "clip_path",
    "clip_polygon",
    "clip_rect",
    "mask_gradient",
    "mask_none",
    "mask_style",
    "mask_url",
    "normalize_mask",
    "normalize_clip",
]
