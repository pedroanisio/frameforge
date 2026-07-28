"""Deterministic randomness and point sampling for FrameForge authoring.

The module computes ordinary :class:`~frameforge.sdk.geometry.Vec2` values in
FrameForge's Y-down page space.  It never changes the document schema or the
global :mod:`random` state.  ``Rand`` is intended for reproducible authoring,
simulation, and layout—not cryptography; use :mod:`secrets` for security
tokens.

``poisson_disk`` implements the grid-accelerated algorithm from Robert
Bridson, *Fast Poisson Disk Sampling in Arbitrary Dimensions* (SIGGRAPH 2007
sketches).  The other samplers are deterministic O(n) constructions; Poisson
sampling is expected O(n) for a fixed candidate budget ``k``.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from random import Random
from typing import Any, TypeVar

from frameforge.sdk._seed import stable_seed
from frameforge.sdk.geometry import Vec2, _v2

__all__ = [
    "Rand",
    "halton",
    "jittered_grid",
    "poisson_disk",
]

T = TypeVar("T")
_COORDINATE_DIGITS = 12


def _point(x: float, y: float) -> Vec2:
    """Quantize computed geometry so serialized output is host-stable."""
    return Vec2(round(float(x), _COORDINATE_DIGITS), round(float(y), _COORDINATE_DIGITS))


def _positive(name: str, value: float) -> float:
    resolved = float(value)
    if not math.isfinite(resolved) or resolved <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return resolved


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _box4(box: Sequence[float]) -> tuple[float, float, float, float]:
    try:
        if len(box) != 4:
            raise ValueError
        x, y, width, height = (float(value) for value in box)
    except (TypeError, ValueError) as exc:
        raise ValueError("box must be [x, y, width, height]") from exc
    if not all(math.isfinite(value) for value in (x, y, width, height)):
        raise ValueError("box values must be finite")
    if width <= 0 or height <= 0:
        raise ValueError("box width and height must be positive")
    return x, y, width, height


class Rand:
    """Deterministic non-cryptographic random stream.

    ``seed`` may be any stably stringifiable value, including strings, integers,
    and tuples.  :meth:`derive` creates an independent named sub-stream from the
    original seed, so its output is unaffected by parent draws or the order in
    which other sub-streams are created.  ``randint`` includes both endpoints,
    matching :class:`random.Random`.
    """

    def __init__(self, seed: Any = 0) -> None:
        self._seed = stable_seed(seed)
        self._random = Random(self._seed)

    def derive(self, *parts: Any) -> Rand:
        """Return an independent named stream derived from this stream's seed."""
        return Rand(stable_seed(self._seed, *parts))

    def uniform(self, lo: float = 0.0, hi: float = 1.0) -> float:
        """Return a uniformly distributed float in the inclusive range bounds."""
        return self._random.uniform(lo, hi)

    def randint(self, lo: int, hi: int) -> int:
        """Return an integer in ``[lo, hi]`` (both endpoints inclusive)."""
        return self._random.randint(lo, hi)

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Return one Gaussian draw with mean ``mu`` and deviation ``sigma``."""
        return self._random.gauss(mu, sigma)

    def choice(self, seq: Sequence[T]) -> T:
        """Choose one member of ``seq`` without modifying it."""
        return self._random.choice(seq)

    def sample(self, seq: Sequence[T], k: int) -> list[T]:
        """Choose ``k`` unique members of ``seq`` without modifying it."""
        return self._random.sample(seq, k)

    def shuffled(self, seq: Sequence[T]) -> list[T]:
        """Return a shuffled copy of ``seq``; never mutate the caller's value."""
        result = list(seq)
        self._random.shuffle(result)
        return result

    def point_in_rect(self, box: Sequence[float]) -> Vec2:
        """Return an area-uniform point inside ``box=[x, y, width, height]``."""
        x, y, width, height = _box4(box)
        return _point(self.uniform(x, x + width), self.uniform(y, y + height))

    def point_in_circle(self, cx: float, cy: float, r: float) -> Vec2:
        """Return a point uniformly distributed by area inside a circle."""
        radius = _positive("r", r)
        if not math.isfinite(cx) or not math.isfinite(cy):
            raise ValueError("cx and cy must be finite")
        angle = self.uniform(0.0, 2.0 * math.pi)
        distance = radius * math.sqrt(self.uniform())
        return _point(cx + distance * math.cos(angle), cy + distance * math.sin(angle))

    def jitter(self, p: Vec2 | Sequence[float], radius: float) -> Vec2:
        """Return ``p`` displaced by an area-uniform amount within ``radius``."""
        resolved = float(radius)
        if not math.isfinite(resolved) or resolved < 0:
            raise ValueError("radius must be a non-negative finite number")
        point = _v2(p)
        if not math.isfinite(point.x) or not math.isfinite(point.y):
            raise ValueError("p coordinates must be finite")
        if resolved == 0:
            return point
        delta = self.point_in_circle(0.0, 0.0, resolved)
        return _point(point.x + delta.x, point.y + delta.y)


def _radical_inverse(index: int, base: int) -> float:
    inverse = 1.0 / base
    factor = inverse
    result = 0.0
    while index:
        index, digit = divmod(index, base)
        result += digit * factor
        factor *= inverse
    return result


def halton(
    n: int,
    *,
    base_x: int = 2,
    base_y: int = 3,
    box: Sequence[float] | None = None,
    skip: int = 0,
) -> list[Vec2]:
    """Return ``n`` deterministic low-discrepancy Halton points in O(n).

    Terms start at index one.  ``skip`` discards that many head terms; ``box``
    maps the unit-square sequence into ``[x, y, width, height]``.
    """
    count = _positive_int("n", n)
    bx = _positive_int("base_x", base_x)
    by = _positive_int("base_y", base_y)
    if bx < 2:
        raise ValueError("base_x must be >= 2")
    if by < 2:
        raise ValueError("base_y must be >= 2")
    if isinstance(skip, bool) or not isinstance(skip, int) or skip < 0:
        raise ValueError("skip must be a non-negative integer")
    x, y, width, height = (0.0, 0.0, 1.0, 1.0) if box is None else _box4(box)
    return [
        _point(
            x + width * _radical_inverse(index, bx),
            y + height * _radical_inverse(index, by),
        )
        for index in range(skip + 1, skip + count + 1)
    ]


def poisson_disk(
    box: Sequence[float],
    *,
    radius: float,
    k: int = 30,
    rand: Rand | None = None,
    max_points: int | None = None,
) -> list[Vec2]:
    """Return Bridson Poisson-disk points with minimum separation ``radius``.

    A background grid makes the expected cost O(n * k) and memory O(n).
    ``max_points`` is a caller-requested hard cap: generation returns immediately
    once that many points have been accepted.  The default stream is ``Rand(0)``.
    """
    x, y, width, height = _box4(box)
    resolved_radius = _positive("radius", radius)
    attempts = _positive_int("k", k)
    if max_points is not None:
        cap = _positive_int("max_points", max_points)
    else:
        cap = None
    source = Rand(0) if rand is None else rand
    if not isinstance(source, Rand):
        raise TypeError("rand must be a Rand instance or None")

    cell = resolved_radius / math.sqrt(2.0)
    columns = max(1, math.ceil(width / cell))
    rows = max(1, math.ceil(height / cell))
    # Sparse cells keep memory proportional to accepted output, including when
    # max_points caps a sampler over an otherwise enormous theoretical grid.
    grid: dict[tuple[int, int], Vec2] = {}

    def grid_coords(point: Vec2) -> tuple[int, int]:
        return (
            min(columns - 1, int((point.x - x) / cell)),
            min(rows - 1, int((point.y - y) / cell)),
        )

    def store(point: Vec2) -> None:
        grid[grid_coords(point)] = point

    radius_squared = resolved_radius * resolved_radius

    def acceptable(candidate: Vec2) -> bool:
        if not (x <= candidate.x <= x + width and y <= candidate.y <= y + height):
            return False
        column, row = grid_coords(candidate)
        for neighbour_row in range(max(0, row - 2), min(rows, row + 3)):
            for neighbour_column in range(max(0, column - 2), min(columns, column + 3)):
                neighbour = grid.get((neighbour_column, neighbour_row))
                if neighbour is None:
                    continue
                dx = candidate.x - neighbour.x
                dy = candidate.y - neighbour.y
                if dx * dx + dy * dy < radius_squared:
                    return False
        return True

    first = source.point_in_rect((x, y, width, height))
    points = [first]
    active = [first]
    store(first)
    if cap == 1:
        return points

    while active:
        active_index = source.randint(0, len(active) - 1)
        origin = active[active_index]
        accepted = False
        for _ in range(attempts):
            angle = source.uniform(0.0, 2.0 * math.pi)
            # Uniform by area in the annulus [radius, 2 * radius].
            distance = resolved_radius * math.sqrt(1.0 + 3.0 * source.uniform())
            candidate = _point(
                origin.x + distance * math.cos(angle),
                origin.y + distance * math.sin(angle),
            )
            if not acceptable(candidate):
                continue
            points.append(candidate)
            active.append(candidate)
            store(candidate)
            accepted = True
            if cap is not None and len(points) >= cap:
                return points
            break
        if not accepted:
            active.pop(active_index)
    return points


def jittered_grid(
    box: Sequence[float],
    *,
    nx: int,
    ny: int,
    amount: float = 1.0,
    rand: Rand | None = None,
) -> list[Vec2]:
    """Return one point per cell deterministically in row-major order.

    ``amount=0`` returns exact centres; ``amount=1`` permits displacement up to
    half a cell on each axis.  Runtime and output size are O(nx * ny).
    """
    x, y, width, height = _box4(box)
    columns = _positive_int("nx", nx)
    rows = _positive_int("ny", ny)
    resolved_amount = float(amount)
    if not math.isfinite(resolved_amount) or not 0.0 <= resolved_amount <= 1.0:
        raise ValueError("amount must be a finite number in [0, 1]")
    source = Rand(0) if rand is None else rand
    if not isinstance(source, Rand):
        raise TypeError("rand must be a Rand instance or None")

    cell_width = width / columns
    cell_height = height / rows
    jitter_x = resolved_amount * cell_width / 2.0
    jitter_y = resolved_amount * cell_height / 2.0
    points: list[Vec2] = []
    for row in range(rows):
        centre_y = y + (row + 0.5) * cell_height
        for column in range(columns):
            centre_x = x + (column + 0.5) * cell_width
            points.append(
                _point(
                    centre_x + source.uniform(-jitter_x, jitter_x),
                    centre_y + source.uniform(-jitter_y, jitter_y),
                )
            )
    return points
