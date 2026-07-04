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

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

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

    @staticmethod
    def reflect(
        axis: str | Sequence[Vec2 | Sequence[float]] = "x",
    ) -> "Mat3":
        """Reflection matrix (Mortenson §3.6, B7).

        ``axis`` is ``"x"`` (mirror across the x-axis, ``y -> -y``), ``"y"``
        (across the y-axis, ``x -> -x``), or a **line** given as two distinct
        points ``(p0, p1)`` — mirror through that line, wherever it sits. The map
        is orientation-reversing (``det == -1``) and its own inverse.
        """
        if axis == "x":
            return Mat3(a=1.0, d=-1.0)
        if axis == "y":
            return Mat3(a=-1.0, d=1.0)
        if isinstance(axis, str):
            raise ValueError(f"reflect axis must be 'x', 'y', or a (p0, p1) line; got {axis!r}")
        p0 = _v2(axis[0])
        p1 = _v2(axis[1])
        dx, dy = p1.x - p0.x, p1.y - p0.y
        if dx * dx + dy * dy < 1e-24:
            raise ValueError("reflect line needs two distinct points")
        # Reflection across a line through the origin at angle θ is
        #   [ cos2θ  sin2θ ]
        #   [ sin2θ -cos2θ ]  (holds in any 2D frame, Y-up or Y-down).
        theta2 = 2.0 * math.atan2(dy, dx)
        co, si = math.cos(theta2), math.sin(theta2)
        linear = Mat3(a=co, b=si, c=si, d=-co)
        # Conjugate by translation so the mirror line passes through p0.
        return Mat3.translate(p0.x, p0.y) @ linear @ Mat3.translate(-p0.x, -p0.y)

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

    @staticmethod
    def rotate_x(degrees: float) -> "Mat4":
        return _mat4_rotate_x(math.radians(degrees))

    @staticmethod
    def rotate_y(degrees: float) -> "Mat4":
        return _mat4_rotate_y(math.radians(degrees))

    @staticmethod
    def rotate_z(degrees: float) -> "Mat4":
        co = math.cos(math.radians(degrees))
        si = math.sin(math.radians(degrees))
        return Mat4(((co, -si, 0, 0), (si, co, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))

    @staticmethod
    def look_at(
        eye: Vec3 | Sequence[float],
        target: Vec3 | Sequence[float] = Vec3(0.0, 0.0, 0.0),
        up: Vec3 | Sequence[float] = Vec3(0.0, 1.0, 0.0),
    ) -> "Mat4":
        """Right-handed view matrix (à la ``gluLookAt``) looking down ``-z``."""
        e = _v3(eye)
        f = _normalize3(_v3(target) - e)
        s = _normalize3(_cross3(f, _v3(up)))
        u = _cross3(s, f)
        return Mat4((
            (s.x, s.y, s.z, -_dot3(s, e)),
            (u.x, u.y, u.z, -_dot3(u, e)),
            (-f.x, -f.y, -f.z, _dot3(f, e)),
            (0.0, 0.0, 0.0, 1.0),
        ))

    @staticmethod
    def perspective_fov(fov: float, aspect: float = 1.0, near: float = 0.1, far: float = 100.0) -> "Mat4":
        """Standard right-handed perspective projection.

        ``fov`` is the vertical field of view in degrees. The ``y`` row is
        negated so world-up projects to screen-up under FrameGraph's Y-down page
        space (otherwise the autofit in :class:`~framegraph.sdk.Scene3D` would
        flip the scene upside-down).
        """
        if near <= 0 or far <= near:
            raise ValueError("perspective_fov needs 0 < near < far")
        g = 1.0 / math.tan(math.radians(fov) / 2.0)
        return Mat4((
            (g / aspect, 0.0, 0.0, 0.0),
            (0.0, -g, 0.0, 0.0),
            (0.0, 0.0, (far + near) / (near - far), (2 * far * near) / (near - far)),
            (0.0, 0.0, -1.0, 0.0),
        ))

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
class Camera:
    """A perspective (or orthographic-ish) camera that composes a view +
    projection ``Mat4`` for :class:`~framegraph.sdk.Scene3D` and topology
    rendering.

    ``eye`` looks at ``target`` with ``up`` defining roll; ``fov`` is the
    vertical field of view in degrees. Call :meth:`matrix` for the combined
    ``projection @ view`` transform, or pass the ``Camera`` straight to a
    renderer that accepts one.
    """

    eye: Vec3 = Vec3(3.0, 2.5, 4.0)
    target: Vec3 = Vec3(0.0, 0.0, 0.0)
    up: Vec3 = Vec3(0.0, 1.0, 0.0)
    fov: float = 45.0
    aspect: float = 1.0
    near: float = 0.1
    far: float = 100.0

    def view(self) -> Mat4:
        return Mat4.look_at(self.eye, self.target, self.up)

    def projection(self) -> Mat4:
        return Mat4.perspective_fov(self.fov, self.aspect, self.near, self.far)

    def matrix(self) -> Mat4:
        return self.projection() @ self.view()

    def project(self, point: Vec3 | Sequence[float]) -> Vec2:
        return self.matrix().project(point)

    def orbit(self, *, azimuth: float = 0.0, elevation: float = 0.0) -> "Camera":
        """Return a new camera with the eye orbited around ``target``.

        ``azimuth``/``elevation`` are degrees; the orbit radius is preserved.
        Handy for sweeping a perspective deck frame-by-frame without redoing the
        spherical trigonometry each time.
        """
        offset = self.eye - self.target
        radius = math.sqrt(offset.x**2 + offset.y**2 + offset.z**2)
        if radius < 1e-9:
            return self
        az = math.atan2(offset.x, offset.z) + math.radians(azimuth)
        el = math.asin(max(-1.0, min(1.0, offset.y / radius))) + math.radians(elevation)
        el = max(-math.pi / 2 + 1e-3, min(math.pi / 2 - 1e-3, el))
        co = math.cos(el)
        new_eye = self.target + Vec3(radius * co * math.sin(az), radius * math.sin(el), radius * co * math.cos(az))
        return Camera(new_eye, self.target, self.up, self.fov, self.aspect, self.near, self.far)


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
        # Parallel structured form (G-1): one typed `[cmd, *coords]` list per
        # segment, carrying raw numbers. `d()` compiles the string view; the
        # structured view is the schema-checkable source (model `PathSeg`).
        self._struct: list[list] = []
        self._current: Vec2 | None = None

    def move_to(self, x: float, y: float) -> "Path":
        self._segments.append(f"M {_fmt(x)} {_fmt(y)}")
        self._struct.append(["M", x, y])
        self._current = Vec2(x, y)
        return self

    def line_to(self, x: float, y: float) -> "Path":
        self._segments.append(f"L {_fmt(x)} {_fmt(y)}")
        self._struct.append(["L", x, y])
        self._current = Vec2(x, y)
        return self

    def cubic_to(self, c1: Vec2 | Sequence[float], c2: Vec2 | Sequence[float], to: Vec2 | Sequence[float]) -> "Path":
        p1 = _v2(c1)
        p2 = _v2(c2)
        p3 = _v2(to)
        self._segments.append(
            f"C {_fmt(p1.x)} {_fmt(p1.y)} {_fmt(p2.x)} {_fmt(p2.y)} {_fmt(p3.x)} {_fmt(p3.y)}"
        )
        self._struct.append(["C", p1.x, p1.y, p2.x, p2.y, p3.x, p3.y])
        self._current = p3
        return self

    def quad_to(self, control: Vec2 | Sequence[float], to: Vec2 | Sequence[float]) -> "Path":
        c = _v2(control)
        p = _v2(to)
        self._segments.append(f"Q {_fmt(c.x)} {_fmt(c.y)} {_fmt(p.x)} {_fmt(p.y)}")
        self._struct.append(["Q", c.x, c.y, p.x, p.y])
        self._current = p
        return self

    def arc_to(self, rx: float, ry: float, rotation: float, large: bool, sweep: bool, to: Vec2 | Sequence[float]) -> "Path":
        p = _v2(to)
        large_f, sweep_f = (1 if large else 0), (1 if sweep else 0)
        self._segments.append(
            f"A {_fmt(rx)} {_fmt(ry)} {_fmt(rotation)} {large_f} {sweep_f} {_fmt(p.x)} {_fmt(p.y)}"
        )
        self._struct.append(["A", rx, ry, rotation, large_f, sweep_f, p.x, p.y])
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
        self._struct.append(["Z"])
        return self

    def d(self) -> str:
        return " ".join(self._segments)

    def segments(self) -> list[list]:
        """The structured G-1 form: a list of typed ``[cmd, *coords]`` segments
        (the schema-checkable source the `d` string compiles from)."""
        return [list(seg) for seg in self._struct]

    def object(self, *, structured: bool = False, **fields: object) -> dict[str, object]:
        """Emit a ``path`` object. ``structured=True`` authors the typed G-1
        segment list (`d` as `list[PathSeg]`); the default emits the `d` string —
        byte-identical to prior output, so golden renders are unaffected."""
        obj: dict[str, object] = {"type": "path", "d": self.segments() if structured else self.d()}
        obj.update(fields)
        return obj


def quarter_circle_kappa() -> float:
    return (4 / 3) * (math.sqrt(2) - 1)


def mirror(
    points: Iterable[Vec2 | Sequence[float]],
    axis: str | Sequence[Vec2 | Sequence[float]] = "x",
) -> list[Vec2]:
    """Reflect a sequence of points across ``axis`` (see :meth:`Mat3.reflect`, B7).

    Returns the mirrored points as ``Vec2`` — the primitive for building a
    symmetric shape from one half (mirror the half, then join the two).
    """
    m = Mat3.reflect(axis)
    return [m.apply(p) for p in points]


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


def _cross3(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x)


def _dot3(a: Vec3, b: Vec3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def _normalize3(v: Vec3) -> Vec3:
    length = math.sqrt(_dot3(v, v))
    if length < 1e-12:
        raise ValueError("cannot normalize a zero-length vector")
    return Vec3(v.x / length, v.y / length, v.z / length)


def _mat4_rotate_x(radians: float) -> Mat4:
    co = math.cos(radians)
    si = math.sin(radians)
    return Mat4(((1, 0, 0, 0), (0, co, -si, 0), (0, si, co, 0), (0, 0, 0, 1)))


def _mat4_rotate_y(radians: float) -> Mat4:
    co = math.cos(radians)
    si = math.sin(radians)
    return Mat4(((co, 0, si, 0), (0, 1, 0, 0), (-si, 0, co, 0), (0, 0, 0, 1)))


__all__ = [
    "Camera",
    "CubicBezier",
    "Mat3",
    "Mat4",
    "Path",
    "Vec2",
    "Vec3",
    "mirror",
    "quarter_circle_kappa",
]
