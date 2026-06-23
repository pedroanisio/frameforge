"""Paint, stroke and effect constructors for the FrameGraph SDK.

These helpers assemble the plain ``dict`` / ``str`` values the authoritative
model already accepts — ``Paint`` / ``Gradient`` for fills and strokes, an inline
``Style`` bundle for stroke geometry, and an ``Effect`` object for shadows and
glows. They add no schema of their own; they only spare callers the boilerplate
of hand-building gradient stops, honouring the P3 paint/geometry stroke split,
and expressing translucency portably.

Every visual primitive on :class:`framegraph.sdk.PageBuilder` already forwards
arbitrary fields to the model, so the results compose directly::

    layer.rect(box, fill=linear_gradient([("#1B1B3A", 0), ("#7C5C8E", 1)], angle=180))
    layer.path(p, **stroke(3, color="#E8743B", cap="round"))
    layer.ellipse(c, r, r, fill="#FCC23D", glow=glow(blur=8, color="#FFE6A0"))
"""
from __future__ import annotations

from typing import Any, Literal, Sequence, Union

Color = str
Position = Union[float, int, str]
Stop = Union[Color, "tuple[Color, Position]"]
PatternKind = Literal["hatch", "cross_hatch", "dots", "grid"]


def rgba(color: Color, alpha: float) -> str:
    """Return ``color`` at ``alpha`` (0..1) as a CSS ``rgba()`` string.

    ``rgba()`` is preferred over 8-digit ``#rrggbbaa`` because every SVG
    rasteriser in the toolchain honours it, so translucent paint composites
    identically everywhere. ``color`` must be ``#rgb`` or ``#rrggbb``; ``alpha``
    is clamped to the unit interval.
    """
    r, g, b = _hex_rgb(color)
    a = max(0.0, min(1.0, float(alpha)))
    return f"rgba({r},{g},{b},{a:g})"


def linear_gradient(
    stops: Sequence[Stop],
    *,
    angle: float | int | str | None = None,
    repeating: bool | None = None,
) -> dict[str, Any]:
    """Build a linear-gradient ``Paint`` from ``stops``.

    Each stop is ``(color, position)`` — where ``position`` is a CSS string
    (``"50%"``) or a unit-interval float — or a bare colour, in which case stops
    are spread evenly from 0% to 100%. ``angle`` orients the gradient (e.g.
    ``180`` for top-to-bottom).
    """
    grad: dict[str, Any] = {"kind": "linear", "stops": _stops(stops)}
    if angle is not None:
        grad["angle"] = angle
    if repeating is not None:
        grad["repeating"] = repeating
    return grad


def radial_gradient(
    stops: Sequence[Stop],
    *,
    at: str | Sequence[float] | None = None,
    shape: str | None = None,
    repeating: bool | None = None,
) -> dict[str, Any]:
    """Build a radial-gradient ``Paint`` from ``stops`` (see :func:`linear_gradient`).

    ``at`` is the centre (``"50% 40%"`` or a point); ``shape`` is ``"circle"`` or
    ``"ellipse"``. A glow halo is a radial gradient from an opaque colour to the
    same colour at zero alpha (see :func:`rgba`).
    """
    grad: dict[str, Any] = {"kind": "radial", "stops": _stops(stops)}
    if at is not None:
        grad["at"] = at
    if shape is not None:
        grad["shape"] = shape
    if repeating is not None:
        grad["repeating"] = repeating
    return grad


def pattern(
    kind: PatternKind,
    *,
    fg: Color | None = None,
    bg: Color | None = None,
    scale: float | int | str | None = None,
    angle: float | int | str | None = None,
) -> dict[str, Any]:
    """Build a tiled pattern ``Paint``.

    ``kind`` is one of the model's pattern arms: ``"hatch"``,
    ``"cross_hatch"``, ``"dots"``, or ``"grid"``. The ergonomic names map onto
    the core model fields: ``fg`` -> ``stroke``, ``bg`` -> ``background``, and
    ``scale`` -> ``spacing``.
    """
    paint: dict[str, Any] = {"kind": "pattern", "pattern": kind}
    if angle is not None:
        paint["angle"] = angle
    if scale is not None:
        paint["spacing"] = scale
    if fg is not None:
        paint["stroke"] = fg
    if bg is not None:
        paint["background"] = bg
    return paint


def stroke(
    width: float,
    *,
    color: Color | None = None,
    dash: Sequence[float] | None = None,
    cap: str | None = None,
    join: str | None = None,
    miterlimit: float | None = None,
) -> dict[str, Any]:
    """Build a primitive's stroke fields, honouring the P3 paint/geometry split.

    Returns a dict to splat into a primitive: paint goes in ``stroke`` and all
    geometry (``width``/``dash``/``cap``/``join``) in the inline ``stroke_style``
    bundle — the only shape the model accepts (an inline-geometry ``stroke`` is
    rejected). ``color`` is optional, so a geometry-only stroke is valid.
    """
    geometry: dict[str, Any] = {"stroke_width": width}
    if dash is not None:
        geometry["stroke_dasharray"] = list(dash)
    if cap is not None:
        geometry["stroke_linecap"] = cap
    if join is not None:
        geometry["stroke_linejoin"] = join
    if miterlimit is not None:
        geometry["stroke_miterlimit"] = miterlimit
    fields: dict[str, Any] = {"stroke_style": geometry}
    if color is not None:
        fields["stroke"] = color
    return fields


def shadow(
    *,
    dx: float = 0.0,
    dy: float = 0.0,
    blur: float = 0.0,
    color: Color | None = None,
    opacity: float | None = None,
) -> dict[str, Any]:
    """Build a drop-shadow ``Effect`` (offset ``dx, dy`` with ``blur``)."""
    effect: dict[str, Any] = {"dx": dx, "dy": dy, "blur": blur}
    if color is not None:
        effect["color"] = color
    if opacity is not None:
        effect["opacity"] = opacity
    return effect


def glow(
    *,
    blur: float,
    color: Color | None = None,
    opacity: float | None = None,
) -> dict[str, Any]:
    """Build a glow ``Effect`` — a soft, offset-free halo of radius ``blur``."""
    effect: dict[str, Any] = {"blur": blur}
    if color is not None:
        effect["color"] = color
    if opacity is not None:
        effect["opacity"] = opacity
    return effect


def effects(
    *,
    glow: dict[str, Any] | None = None,
    shadow: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bundle :func:`glow` / :func:`shadow` into the object-level fields they belong on.

    ``glow`` and ``shadow`` are *object* fields on the model, not stroke geometry —
    a glow merged into ``stroke_style`` is silently dropped, and an unknown key
    there fails validation. This returns ``{"glow": ..., "shadow": ...}`` (omitting
    the ``None`` ones) to splat once at the primitive's top level, so a caller's own
    stroke helper can keep merging into ``stroke_style`` without ever swallowing an
    effect::

        layer.ellipse(c, r, r, fill="#FCC23D",
                      **stroke(2, color="#E8743B"),
                      **effects(glow=glow(blur=8, color="#FFE6A0")))
    """
    out: dict[str, Any] = {}
    if glow is not None:
        out["glow"] = glow
    if shadow is not None:
        out["shadow"] = shadow
    return out


# ---- internals ------------------------------------------------------------ #

def _hex_rgb(color: Color) -> tuple[int, int, int]:
    c = color.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        raise ValueError(f"rgba() needs a #rgb or #rrggbb colour; got {color!r}")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _stops(stops: Sequence[Stop]) -> list[dict[str, Any]]:
    items = list(stops)
    n = len(items)
    if n == 0:
        raise ValueError("a gradient needs at least one stop")
    out: list[dict[str, Any]] = []
    for i, stop in enumerate(items):
        if isinstance(stop, (tuple, list)):
            color, position = stop
        else:
            color, position = stop, (i / (n - 1) if n > 1 else 0.0)
        out.append({"color": color, "position": _position(position)})
    return out


def _position(position: Position) -> str:
    if isinstance(position, str):
        return position
    return f"{float(position) * 100:g}%"


__all__ = [
    "effects",
    "glow",
    "linear_gradient",
    "pattern",
    "radial_gradient",
    "rgba",
    "shadow",
    "stroke",
]
