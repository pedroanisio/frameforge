"""Region operations over a flat FrameGraph object list.

These are the SDK primitives behind *region-based transformation*: treat an
ingested drawing (e.g. the output of
:func:`framegraph.vision.infrastructure.svg_import.svg_to_objects`) as a list of
individually-addressable object dicts, then

* :func:`select_in` — pick the objects in a rectangular window (by intersection,
  containment, or centroid);
* :func:`place_region` — map a sub-window of the drawing into a target box with an
  optional affine, clipped to the target. The clip is carried on a *static* outer
  group and the transform on an inner group, so the clip masks in page space — a
  clip applied on the same element as the transform would ride along inside the
  transformed frame and fail to mask;
* :func:`gradient_map` — recolour objects by luminance through a colour ramp;
* :func:`region_grade` — recolour *by region level*: assign each object to a region
  by its centroid, then apply that region's ramp.

Honest limits: :func:`object_bbox` derives a path's box from the coordinate pairs
in its ``d`` string. That is exact for the ``M``/``L``/``C``/``Q``/``T``/``Z``
polyline-and-curve paths the SVG importer emits, and approximate for ``H``/``V``
(single-axis) or ``A`` (arc flags) commands. Paint is recoloured only when it is a
``#rgb``/``#rrggbb`` string; ``none``, ``url(...)`` and named colours pass through.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Optional, Sequence

from framegraph.sdk.clip import clip_rect
from framegraph.sdk.geometry import Mat3

Box = Sequence[float]
Ramp = Sequence[tuple[float, str]]
Paint = "str | Ramp"

_NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


# --------------------------------------------------------------------------- #
#  Geometry                                                                    #
# --------------------------------------------------------------------------- #
def object_bbox(obj: dict[str, Any]) -> Optional[tuple[float, float, float, float]]:
    """Return ``(x0, y0, x1, y1)`` for ``obj``, or ``None`` if it carries no geometry.

    Supports ``rect``/``image`` (``box``), ``path`` (coordinate pairs in ``d``),
    ``ellipse``/``circle`` (``center`` + radii), ``line`` (``from``/``to``), and
    ``polyline``/``polygon`` (``points``). See the module docstring for the path
    approximation.
    """
    t = obj.get("type")
    if t in ("rect", "image"):
        box = obj.get("box")
        if isinstance(box, (list, tuple)) and len(box) >= 4:
            x, y, w, h = (float(v) for v in box[:4])
            return (x, y, x + w, y + h)
        return None
    if t == "path":
        nums = [float(v) for v in _NUM.findall(obj.get("d", ""))]
        pts = list(zip(nums[0::2], nums[1::2]))
        return _points_bbox(pts)
    if t in ("ellipse", "circle"):
        c = obj.get("center")
        if not (isinstance(c, (list, tuple)) and len(c) >= 2):
            return None
        cx, cy = float(c[0]), float(c[1])
        rx = float(obj.get("rx", obj.get("r", 0)) or 0)
        ry = float(obj.get("ry", obj.get("r", rx)) or rx)
        return (cx - rx, cy - ry, cx + rx, cy + ry)
    if t == "line":
        a, b = obj.get("from"), obj.get("to")
        if a and b:
            return _points_bbox([(float(a[0]), float(a[1])), (float(b[0]), float(b[1]))])
        return None
    if t in ("polyline", "polygon"):
        pts = [(float(p[0]), float(p[1])) for p in obj.get("points", []) if len(p) >= 2]
        return _points_bbox(pts)
    return None


def _points_bbox(pts: Sequence[tuple[float, float]]):
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _centroid(bb: tuple[float, float, float, float]) -> tuple[float, float]:
    return ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)


def _in_box(point, box: Box) -> bool:
    x, y = point
    bx, by, bw, bh = box
    return bx <= x <= bx + bw and by <= y <= by + bh


# --------------------------------------------------------------------------- #
#  Selection                                                                   #
# --------------------------------------------------------------------------- #
def select_in(objects: Sequence[dict[str, Any]], box: Box, *, mode: str = "intersect") -> list[dict[str, Any]]:
    """Return deep copies of the objects that fall in ``box`` ``[x, y, w, h]``.

    ``mode`` is ``"intersect"`` (bbox overlaps ``box`` — the default), ``"contain"``
    (bbox lies fully inside ``box``), or ``"center"`` (bbox centroid is inside
    ``box``). Objects with no geometry are dropped. The result aliases nothing in
    the input, so callers may mutate it freely.
    """
    if mode not in ("intersect", "contain", "center"):
        raise ValueError(f"select_in mode must be intersect/contain/center, got {mode!r}")
    bx, by, bw, bh = box
    bx1, by1 = bx + bw, by + bh
    out: list[dict[str, Any]] = []
    for obj in objects:
        bb = object_bbox(obj)
        if bb is None:
            continue
        x0, y0, x1, y1 = bb
        if mode == "intersect":
            hit = x1 >= bx and x0 <= bx1 and y1 >= by and y0 <= by1
        elif mode == "contain":
            hit = x0 >= bx and y0 >= by and x1 <= bx1 and y1 <= by1
        else:
            hit = _in_box(_centroid(bb), box)
        if hit:
            out.append(copy.deepcopy(obj))
    return out


# --------------------------------------------------------------------------- #
#  Placement (clip + transform)                                                #
# --------------------------------------------------------------------------- #
def _fit(source: Box, target: Box) -> Mat3:
    """Aspect-preserved, centred map from ``source`` box to ``target`` box."""
    sx, sy, sw, sh = source
    tx, ty, tw, th = target
    s = min(tw / sw, th / sh) if sw and sh else 1.0
    ex = tx + (tw - sw * s) / 2 - sx * s
    ey = ty + (th - sh * s) / 2 - sy * s
    return Mat3(a=s, b=0.0, c=0.0, d=s, e=ex, f=ey)


def place_region(
    objects: Sequence[dict[str, Any]],
    source_box: Box,
    target_box: Box,
    *,
    transform: "Mat3 | None" = None,
    clip: bool = True,
    select: "str | None" = None,
    style: "dict[str, Any] | None" = None,
    **fields: Any,
) -> dict[str, Any]:
    """Map ``source_box`` of ``objects`` into ``target_box`` as one transformed group.

    ``source_box`` is fitted (aspect-preserved, centred) into ``target_box``. An
    optional ``transform`` (a :class:`~framegraph.sdk.Mat3`) is applied about the
    source region's centre, in source space, before the fit — use it to rotate /
    scale / shear / mirror the region. With ``clip`` (default), the result is masked
    to ``target_box``; the clip is carried on a static outer group while the
    transform sits on the inner group, so the mask is evaluated in page space.

    ``style`` attaches CSS / compositing fields to the region as a unit —
    ``opacity``, ``mix_blend_mode``, ``filter``/``backdrop_filter``, ``box_shadow``,
    or the bounded raw-``css`` escape. It rides on the clip wrapper (or the
    transformed group when ``clip`` is false); ``place_region`` owns the geometry, so
    its ``transform``/``clip_path`` are never overwritten by ``style``. To style a
    region *in place* (no move), pass the same box as ``source_box`` and
    ``target_box``. Note a region-level ``filter`` drop-shadow is clipped to
    ``target_box`` like any other content.

    ``select`` (``"intersect"``/``"contain"``/``"center"``) first narrows the input
    to the objects in ``source_box``; omit it to place every object. Extra ``fields``
    (e.g. ``id=...``, ``meta=...``) are set on the returned group so a placed region
    can later be copied with :func:`extract_objects`. Returns a single ``group``
    object dict — add it with ``page.add(...)``.
    """
    chosen = select_in(objects, source_box, mode=select) if select else [copy.deepcopy(o) for o in objects]
    base = _fit(source_box, target_box)
    if transform is not None:
        sx, sy, sw, sh = source_box
        cx, cy = sx + sw / 2, sy + sh / 2
        base = base @ Mat3.translate(cx, cy) @ transform @ Mat3.translate(-cx, -cy)
    inner = {"type": "group", "children": chosen,
             "style": {"transform": [base.transform_fn()]}, "decorative": True}
    if not clip:
        if style:
            inner["style"] = {**style, **inner["style"]}      # geometry keys win
        return {**fields, **inner}                            # fields add id/meta; group keys win
    outer = {"type": "group", "children": [inner],
             "style": {"clip_path": clip_rect(target_box)}, "decorative": True}
    if style:
        outer["style"] = {**style, **outer["style"]}          # clip_path wins
    return {**fields, **outer}


# --------------------------------------------------------------------------- #
#  Colour grade                                                                #
# --------------------------------------------------------------------------- #
def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hexc(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def _luminance(h: str) -> float:
    r, g, b = _rgb(h)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def _ramp_color(level: float, ramp: Ramp) -> str:
    """Sample a 0..1 ``level`` on a sorted multi-stop ``ramp`` of ``(pos, hex)``."""
    stops = sorted(ramp, key=lambda s: s[0])
    level = max(0.0, min(1.0, level))
    if level <= stops[0][0]:
        return _hexc(_rgb(stops[0][1]))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if level <= p1:
            t = 0.0 if p1 == p0 else (level - p0) / (p1 - p0)
            a, b = _rgb(c0), _rgb(c1)
            return _hexc(a[i] + (b[i] - a[i]) * t for i in range(3))
    return _hexc(_rgb(stops[-1][1]))


def _is_hex(v: Any) -> bool:
    return isinstance(v, str) and bool(_HEX.match(v))


def _recolor(obj: dict[str, Any], paint: Paint) -> dict[str, Any]:
    """Return a copy of ``obj`` whose hex fill/stroke is recoloured.

    ``paint`` is a solid ``#hex`` string (flat fill) or a ramp of ``(pos, hex)``
    stops (luminance gradient map). Non-hex paint is left untouched.
    """
    obj = copy.deepcopy(obj)
    for key in ("fill", "stroke"):
        if _is_hex(obj.get(key)):
            obj[key] = paint if isinstance(paint, str) else _ramp_color(_luminance(obj[key]), paint)
    return obj


def gradient_map(objects: Sequence[dict[str, Any]], ramp: Ramp) -> list[dict[str, Any]]:
    """Recolour every object by luminance through ``ramp`` (a global gradient map).

    Each ``#hex`` fill/stroke is mapped to the ramp colour at its luminance; darker
    paint lands near the first stop, lighter near the last. Returns deep copies.
    """
    return [_recolor(o, ramp) for o in objects]


def region_grade(
    objects: Sequence[dict[str, Any]],
    regions: Sequence[tuple[Box, Paint]],
    *,
    default: "Paint | None" = None,
) -> list[dict[str, Any]]:
    """Recolour by region level — each object graded by the region it falls in.

    ``regions`` is an ordered list of ``(box, paint)``; an object is assigned to the
    first region whose ``box`` contains its centroid (so list the most specific
    windows first). ``paint`` is a solid ``#hex`` or a ramp (see :func:`gradient_map`).
    Objects in no region get ``default`` (a paint), or are left unchanged when
    ``default`` is ``None``. Returns deep copies.
    """
    out: list[dict[str, Any]] = []
    for obj in objects:
        bb = object_bbox(obj)
        paint: "Paint | None" = default
        if bb is not None:
            center = _centroid(bb)
            for box, region_paint in regions:
                if _in_box(center, box):
                    paint = region_paint
                    break
        out.append(_recolor(obj, paint) if paint is not None else copy.deepcopy(obj))
    return out


# --------------------------------------------------------------------------- #
#  Cross-document copy — pull elements out of a built document                  #
# --------------------------------------------------------------------------- #
def _obj_transform(obj: dict[str, Any]) -> Any:
    style = obj.get("style")
    return style.get("transform") if isinstance(style, dict) else None


def _wrap_in_transforms(obj: dict[str, Any], tchain: list[Any]) -> dict[str, Any]:
    """Nest ``obj`` under one group per ancestor transform (outermost ancestor last)."""
    node = obj
    for transform in reversed(tchain):
        node = {"type": "group", "children": [node],
                "style": {"transform": copy.deepcopy(transform)}, "decorative": True}
    return node


def _collect_by_id(obj: dict[str, Any], tchain: list[Any], want: set[str],
                   found: list[dict[str, Any]], bake: bool) -> None:
    if obj.get("id") in want:
        found.append(_wrap_in_transforms(copy.deepcopy(obj), tchain if bake else []))
        return                                          # whole subtree comes with it
    if obj.get("type") == "group":
        t = _obj_transform(obj)
        child_chain = tchain + ([t] if t is not None else [])
        for child in obj.get("children", []) or []:
            _collect_by_id(child, child_chain, want, found, bake)


def extract_objects(
    source: Any,
    *,
    page: "str | int | None" = None,
    layer: "str | Sequence[str] | None" = None,
    ids: "str | Sequence[str] | None" = None,
    bake: bool = True,
) -> list[dict[str, Any]]:
    """Copy drawable objects out of a FrameGraph document, for pasting elsewhere.

    ``source`` is anything :func:`framegraph.sdk.place_figure` accepts — a
    :class:`~framegraph.sdk.DocumentBuilder`, a document/dict, a
    ``.fg.yaml``/``.fg.json`` path, or a :class:`~framegraph.sdk.figure.FigureRef`.
    ``page`` selects the page (id or index; default first); ``layer`` restricts to a
    layer (id or ids).

    Without ``ids`` the page's top-level objects (of the selected layers) are
    returned verbatim — a layer copy. With ``ids`` the tree is searched recursively
    and each object with a matching ``id`` is returned; a matched ``group`` brings
    its whole subtree. With ``bake`` (default), a matched object nested under
    transformed ancestor groups is wrapped in those ancestors' transforms so it
    keeps its world placement when added to another page; ``bake=False`` returns it
    in its local coordinates. Returns deep copies — the source is never mutated.

    Honest limit: only ancestor ``style.transform`` is replayed onto the copy.
    Positioning that comes from a group's ``layout`` (row/column/grid) is not baked;
    ``id`` lookup uses authored ids (``expand_reuse=False``), so an element reachable
    only through a symbol ``use`` is not found.
    """
    from framegraph.sdk.figure import FigureRef, load_figure   # lazy: avoid import cycle

    ref = source if isinstance(source, FigureRef) else FigureRef(source, page=page, expand_reuse=False)
    content = load_figure(ref, layers=layer)
    objects = [copy.deepcopy(o) for o in content.objects]
    if ids is None:
        return objects
    want = {ids} if isinstance(ids, str) else set(ids)
    found: list[dict[str, Any]] = []
    for obj in objects:
        _collect_by_id(obj, [], want, found, bake)
    return found


__all__ = [
    "extract_objects",
    "gradient_map",
    "object_bbox",
    "place_region",
    "region_grade",
    "select_in",
]
