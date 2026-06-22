"""Pure geometry helpers for FrameGraph authoring and expansion."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Vec2:
    """Two-dimensional vector in page space."""

    x: float
    y: float

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True)
class Vec3:
    """Three-dimensional vector used before projection to FrameGraph 2D."""

    x: float
    y: float
    z: float

    def tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass(frozen=True)
class Mat3:
    """2D affine matrix stored as SVG-compatible ``a,b,c,d,e,f``."""

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    @staticmethod
    def identity() -> "Mat3":
        return Mat3()

    @staticmethod
    def translate(tx: float, ty: float) -> "Mat3":
        return Mat3(e=tx, f=ty)

    @staticmethod
    def scale(sx: float, sy: float | None = None) -> "Mat3":
        return Mat3(a=sx, d=sx if sy is None else sy)

    @staticmethod
    def rotate(degrees: float) -> "Mat3":
        """Clockwise-positive rotation in FrameGraph's Y-down page space."""
        r = math.radians(degrees)
        co = math.cos(r)
        si = math.sin(r)
        return Mat3(co, si, -si, co, 0.0, 0.0)

    def __matmul__(self, other: "Mat3") -> "Mat3":
        return Mat3(
            a=self.a * other.a + self.c * other.b,
            b=self.b * other.a + self.d * other.b,
            c=self.a * other.c + self.c * other.d,
            d=self.b * other.c + self.d * other.d,
            e=self.a * other.e + self.c * other.f + self.e,
            f=self.b * other.e + self.d * other.f + self.f,
        )

    def apply(self, point: Vec2 | Sequence[float]) -> Vec2:
        p = _v2(point)
        return Vec2(self.a * p.x + self.c * p.y + self.e, self.b * p.x + self.d * p.y + self.f)

    def inverse(self) -> "Mat3":
        det = self.a * self.d - self.b * self.c
        if abs(det) < 1e-12:
            raise ValueError("matrix is not invertible")
        return Mat3(
            a=self.d / det,
            b=-self.b / det,
            c=-self.c / det,
            d=self.a / det,
            e=(self.c * self.f - self.d * self.e) / det,
            f=(self.b * self.e - self.a * self.f) / det,
        )

    def transform_fn(self) -> dict[str, object]:
        return {"fn": "matrix", "args": [self.a, self.b, self.c, self.d, self.e, self.f]}


@dataclass(frozen=True)
class Mat4:
    """Small 4x4 matrix for deterministic 3D projection helpers."""

    values: tuple[tuple[float, float, float, float], ...]

    @staticmethod
    def identity() -> "Mat4":
        return Mat4(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))

    @staticmethod
    def translate(tx: float, ty: float, tz: float) -> "Mat4":
        return Mat4(((1, 0, 0, tx), (0, 1, 0, ty), (0, 0, 1, tz), (0, 0, 0, 1)))

    @staticmethod
    def perspective(distance: float) -> "Mat4":
        if distance == 0:
            raise ValueError("perspective distance must be non-zero")
        return Mat4(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 1 / distance, 1)))

    @staticmethod
    def isometric() -> "Mat4":
        yaw = _mat4_rotate_y(math.radians(45))
        pitch = _mat4_rotate_x(math.atan(1 / math.sqrt(2)))
        return pitch @ yaw

    def __matmul__(self, other: "Mat4") -> "Mat4":
        rows = []
        for r in range(4):
            row = []
            for c in range(4):
                row.append(sum(self.values[r][k] * other.values[k][c] for k in range(4)))
            rows.append(tuple(row))
        return Mat4(tuple(rows))

    def apply(self, point: Vec3 | Sequence[float]) -> tuple[float, float, float, float]:
        p = _v3(point)
        v = (p.x, p.y, p.z, 1.0)
        return tuple(sum(self.values[r][c] * v[c] for c in range(4)) for r in range(4))

    def project(self, point: Vec3 | Sequence[float]) -> Vec2:
        x, y, _z, w = self.apply(point)
        if abs(w) < 1e-12:
            raise ValueError("projected point has zero homogeneous w")
        return Vec2(x / w, y / w)


@dataclass(frozen=True)
class CubicBezier:
    """Cubic Bézier segment with the formula stated in the SDK proposal."""

    p0: Vec2
    p1: Vec2
    p2: Vec2
    p3: Vec2

    def point(self, t: float) -> Vec2:
        u = 1.0 - t
        return (u**3) * self.p0 + (3 * u * u * t) * self.p1 + (3 * u * t * t) * self.p2 + (t**3) * self.p3

    @staticmethod
    def catmull_rom(points: Sequence[Vec2 | Sequence[float]]) -> list["CubicBezier"]:
        pts = [_v2(p) for p in points]
        if len(pts) < 2:
            return []
        out: list[CubicBezier] = []
        for i in range(len(pts) - 1):
            p_prev = pts[i - 1] if i > 0 else pts[i]
            p0 = pts[i]
            p3 = pts[i + 1]
            p_next = pts[i + 2] if i + 2 < len(pts) else p3
            c1 = p0 + (p3 - p_prev) * (1 / 6)
            c2 = p3 - (p_next - p0) * (1 / 6)
            out.append(CubicBezier(p0, c1, c2, p3))
        return out


class Path:
    """SVG path-data builder that emits FrameGraph ``path`` objects."""

    def __init__(self) -> None:
        self._segments: list[str] = []
        self._current: Vec2 | None = None

    def move_to(self, x: float, y: float) -> "Path":
        self._segments.append(f"M {_fmt(x)} {_fmt(y)}")
        self._current = Vec2(x, y)
        return self

    def line_to(self, x: float, y: float) -> "Path":
        self._segments.append(f"L {_fmt(x)} {_fmt(y)}")
        self._current = Vec2(x, y)
        return self

    def cubic_to(self, c1: Vec2 | Sequence[float], c2: Vec2 | Sequence[float], to: Vec2 | Sequence[float]) -> "Path":
        p1 = _v2(c1)
        p2 = _v2(c2)
        p3 = _v2(to)
        self._segments.append(
            f"C {_fmt(p1.x)} {_fmt(p1.y)} {_fmt(p2.x)} {_fmt(p2.y)} {_fmt(p3.x)} {_fmt(p3.y)}"
        )
        self._current = p3
        return self

    def quad_to(self, control: Vec2 | Sequence[float], to: Vec2 | Sequence[float]) -> "Path":
        c = _v2(control)
        p = _v2(to)
        self._segments.append(f"Q {_fmt(c.x)} {_fmt(c.y)} {_fmt(p.x)} {_fmt(p.y)}")
        self._current = p
        return self

    def arc_to(self, rx: float, ry: float, rotation: float, large: bool, sweep: bool, to: Vec2 | Sequence[float]) -> "Path":
        p = _v2(to)
        self._segments.append(
            f"A {_fmt(rx)} {_fmt(ry)} {_fmt(rotation)} {1 if large else 0} {1 if sweep else 0} {_fmt(p.x)} {_fmt(p.y)}"
        )
        self._current = p
        return self

    def through(self, points: Iterable[Vec2 | Sequence[float]]) -> "Path":
        pts = [_v2(p) for p in points]
        if not pts:
            return self
        if self._current is None:
            self.move_to(pts[0].x, pts[0].y)
            pts = pts[1:]
        for seg in CubicBezier.catmull_rom([self._current, *pts]):
            self.cubic_to(seg.p1, seg.p2, seg.p3)
        return self

    def close(self) -> "Path":
        self._segments.append("Z")
        return self

    def d(self) -> str:
        return " ".join(self._segments)

    def object(self, **fields: object) -> dict[str, object]:
        obj: dict[str, object] = {"type": "path", "d": self.d()}
        obj.update(fields)
        return obj


def quarter_circle_kappa() -> float:
    return (4 / 3) * (math.sqrt(2) - 1)


def _v2(point: Vec2 | Sequence[float]) -> Vec2:
    if isinstance(point, Vec2):
        return point
    return Vec2(float(point[0]), float(point[1]))


def _v3(point: Vec3 | Sequence[float]) -> Vec3:
    if isinstance(point, Vec3):
        return point
    return Vec3(float(point[0]), float(point[1]), float(point[2]))


def _fmt(value: float) -> str:
    return f"{value:.6g}"


def _mat4_rotate_x(radians: float) -> Mat4:
    co = math.cos(radians)
    si = math.sin(radians)
    return Mat4(((1, 0, 0, 0), (0, co, -si, 0), (0, si, co, 0), (0, 0, 0, 1)))


def _mat4_rotate_y(radians: float) -> Mat4:
    co = math.cos(radians)
    si = math.sin(radians)
    return Mat4(((co, 0, si, 0), (0, 1, 0, 0), (-si, 0, co, 0), (0, 0, 0, 1)))


__all__ = [
    "CubicBezier",
    "Mat3",
    "Mat4",
    "Path",
    "Vec2",
    "Vec3",
    "quarter_circle_kappa",
]
