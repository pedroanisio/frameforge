"""Painter kit — render-safe atmosphere primitives for guided-draw compositions.

The guided-draw showcase paints native colour over a line-art guide. A flat fill
per region reads as "filled", not "painted". This kit adds the depth cues a real
illustration has — soft glow, atmospheric haze, a unifying light wash, and a
vignette — built ONLY from gradients + transparency, because the browser-free
rasteriser (cairosvg) renders gradients and alpha but ignores SVG blur filters
and `mix-blend-mode`. So every primitive here survives rasterisation; nothing
relies on a filter that silently drops.

All helpers return plain FrameGraph object dicts (or gradient-paint dicts), so
they are pure, composable, and unit-testable without OpenCV.
"""
from __future__ import annotations

from typing import Any, Sequence

Obj = dict[str, Any]
Stop = dict[str, Any]


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def fade(hex_color: str, alpha: float) -> str:
    """A colour at a given alpha as ``rgba(...)`` — the building block of glow/haze.

    Transparent gradient stops are how we fake soft light without a blur filter
    (which cairosvg drops). ``alpha`` is clamped to [0, 1]."""
    r, g, b = _hex_rgb(hex_color)
    a = max(0.0, min(1.0, alpha))
    return f"rgba({r}, {g}, {b}, {a:g})"


def stop(color: str, position: float) -> Stop:
    """A gradient stop at ``position`` (a fraction 0..1 -> percent)."""
    return {"color": color, "position": f"{position * 100:g}%"}


def linear(stops: Sequence[Stop], angle: str = "180deg", *, repeating: bool = False) -> dict[str, Any]:
    g: dict[str, Any] = {"kind": "linear", "angle": angle, "stops": list(stops)}
    if repeating:
        g["repeating"] = True
    return g


def radial(stops: Sequence[Stop], at: str = "50% 50%") -> dict[str, Any]:
    return {"kind": "radial", "at": at, "stops": list(stops)}


def glow(cx: float, cy: float, r: float, color: str = "#FFF3D0", *,
         core: float = 0.95, spread: float = 2.4) -> list[Obj]:
    """A soft light source: a bright core plus a wide halo fading to transparent."""
    halo = radial([stop(fade(color, 0.55), 0.0), stop(fade(color, 0.22), 0.45),
                   stop(fade(color, 0.0), 1.0)])
    disc = radial([stop(fade(color, core), 0.0), stop(fade(color, core * 0.9), 0.6),
                   stop(fade(color, 0.0), 1.0)])
    return [
        {"type": "ellipse", "center": [cx, cy], "rx": r * spread, "ry": r * spread, "fill": halo},
        {"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "fill": disc},
    ]


def vignette(w: float, h: float, *, color: str = "#0A0E16", strength: float = 0.5) -> Obj:
    """A frame-darkening oval: transparent centre -> ``color`` at the edges."""
    return {"type": "rect", "box": [0, 0, w, h],
            "fill": radial([stop(fade(color, 0.0), 0.0), stop(fade(color, 0.0), 0.62),
                            stop(fade(color, strength), 1.0)], at="50% 48%")}


def haze(box: Sequence[float], color: str = "#DCEBFF", *, opacity: float = 0.35,
         angle: str = "180deg") -> Obj:
    """Atmospheric depth: ``color`` fading to transparent across ``box``."""
    x, y, bw, bh = box
    return {"type": "rect", "box": [x, y, bw, bh],
            "fill": linear([stop(fade(color, opacity), 0.0), stop(fade(color, 0.0), 1.0)], angle)}


def wash(box: Sequence[float], top: str, bottom: str, *, opacity: float = 0.25,
         angle: str = "180deg") -> Obj:
    """A unifying light gradient over the whole frame (low opacity)."""
    x, y, bw, bh = box
    return {"type": "rect", "box": [x, y, bw, bh],
            "fill": linear([stop(fade(top, opacity), 0.0), stop(fade(bottom, opacity), 1.0)], angle)}


def soft_shadow(cx: float, cy: float, rx: float, ry: float, *, color: str = "#0A1428",
                strength: float = 0.4) -> Obj:
    """A contact/cast shadow: a radial blob fading out (no blur filter needed)."""
    return {"type": "ellipse", "center": [cx, cy], "rx": rx, "ry": ry,
            "fill": radial([stop(fade(color, strength), 0.0), stop(fade(color, 0.0), 1.0)])}
