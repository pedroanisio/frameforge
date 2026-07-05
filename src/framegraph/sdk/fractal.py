"""Fractal / procedural generator (CG-canon backlog B4; Harrington Ch11, ¶39).

A small, deterministic **L-system + turtle** engine that lowers self-similar
curves to plain FrameGraph geometry (polylines). Like the rest of the SDK it
*computes* and emits ordinary 2D points — nothing here changes the schema (§A.0).

Turtle command alphabet:

* ``F`` / ``G`` — step forward, drawing (both draw; two symbols so an L-system can
  rewrite them differently, e.g. the dragon curve);
* ``+`` / ``-`` — turn left / right by ``angle_deg`` (``+`` is CCW in math terms,
  which appears clockwise on FrameGraph's Y-down page);
* ``[`` / ``]`` — push / pop turtle state; a bracketed run is a **branch** and
  becomes its own polyline (plants/trees);
* any other symbol is an inert rewrite variable (ignored by the turtle).

Coordinate convention: page space is Y-down (see ``geometry`` module).
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence

from framegraph.sdk.geometry import Vec2, _v2

__all__ = [
    "dragon_curve",
    "koch_curve",
    "lsystem",
    "sierpinski_arrowhead",
    "turtle",
]


def lsystem(axiom: str, rules: Mapping[str, str], iterations: int) -> str:
    """Expand ``axiom`` by ``iterations`` parallel rewrites under ``rules`` (a
    symbol with no rule maps to itself). Deterministic."""
    if iterations < 0:
        raise ValueError("iterations must be >= 0")
    s = axiom
    for _ in range(iterations):
        s = "".join(rules.get(ch, ch) for ch in s)
    return s


def turtle(
    commands: str,
    *,
    angle_deg: float,
    step: float = 1.0,
    start: Vec2 | Sequence[float] = (0.0, 0.0),
    heading_deg: float = 0.0,
) -> list[list[Vec2]]:
    """Interpret a turtle ``commands`` string into a list of polylines (one per
    connected run; brackets branch). Each polyline is a list of ``Vec2``."""
    pos = _v2(start)
    heading = math.radians(heading_deg)
    ang = math.radians(angle_deg)
    stack: list[tuple[Vec2, float, list[Vec2]]] = []
    polylines: list[list[Vec2]] = []
    current: list[Vec2] = [pos]
    for ch in commands:
        if ch in ("F", "G"):
            pos = Vec2(pos.x + step * math.cos(heading), pos.y + step * math.sin(heading))
            current.append(pos)
        elif ch == "+":
            heading += ang
        elif ch == "-":
            heading -= ang
        elif ch == "[":
            # save the trunk (pos + heading + its polyline) and branch off a new one.
            stack.append((pos, heading, current))
            current = [pos]
        elif ch == "]":
            if len(current) >= 2:
                polylines.append(current)
            pos, heading, current = stack.pop()  # the trunk resumes, unbroken
        # other symbols are inert rewrite variables.
    if len(current) >= 2:
        polylines.append(current)
    return polylines


def _single(commands: str, *, angle_deg: float, step: float) -> list[Vec2]:
    """Run a non-branching turtle program and return its one polyline (or the
    bare start point for a degenerate/empty program)."""
    polys = turtle(commands, angle_deg=angle_deg, step=step)
    return polys[0] if polys else [Vec2(0.0, 0.0)]


def koch_curve(iterations: int, *, step: float = 1.0) -> list[Vec2]:
    """The Koch curve after ``iterations`` (axiom ``F``, rule ``F→F+F--F+F``,
    60°). ``iterations`` segments = ``4**iterations``; points = ``4**n + 1``."""
    commands = lsystem("F", {"F": "F+F--F+F"}, iterations)
    return _single(commands, angle_deg=60.0, step=step)


def dragon_curve(iterations: int, *, step: float = 1.0) -> list[Vec2]:
    """The Heighway dragon after ``iterations`` (axiom ``F``, rules
    ``F→F+G``, ``G→F-G``, 90°). Segments = ``2**iterations``."""
    commands = lsystem("F", {"F": "F+G", "G": "F-G"}, iterations)
    return _single(commands, angle_deg=90.0, step=step)


def sierpinski_arrowhead(iterations: int, *, step: float = 1.0) -> list[Vec2]:
    """The Sierpiński arrowhead curve (axiom ``F``, rules ``F→G-F-G``,
    ``G→F+G+F``, 60°) — it fills the Sierpiński triangle in the limit."""
    commands = lsystem("F", {"F": "G-F-G", "G": "F+G+F"}, iterations)
    return _single(commands, angle_deg=60.0, step=step)
