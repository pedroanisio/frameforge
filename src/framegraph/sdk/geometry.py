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

    def try_project(self, point: Vec3 | Sequence[float], *, near_eps: float = 1e-9) -> Vec2 | None:
        """Robust projection (B2/G1): returns ``None`` for a point at or behind the
        near plane (``w <= near_eps``) instead of raising or mirror-inverting, so a
        clip stage can drop it. For a point in front the result is identical to
        :meth:`project`."""
        x, y, _z, w = self.apply(point)
        if w <= near_eps:
            return None
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
class ViewingPipeline:
    """The named viewing pipeline (B1, Harrington ¶43/Ch6/8):
    world → view → projection → **clip** → NDC → viewport.

    ``camera`` supplies the view+projection; ``box`` is the target viewport
    ``[x, y, w, h]``. :meth:`project` maps world points to fitted page coordinates
    — the same aspect-preserving fit :class:`Scene3D` uses — after clipping points
    behind the near plane. It is **output-preserving**: it reproduces the existing
    render fit without touching the renderer (goldens are unmoved), giving a clean
    coordinate seam for downstream work. Robust segment near-plane clipping,
    back-face culling, and depth ordering are B2's job."""

    camera: Camera
    box: Sequence[float]

    def project(self, points: Iterable[Vec3 | Sequence[float]]) -> list[Vec2]:
        """World points → clipped, projected, box-fitted :class:`Vec2` page
        coordinates. Points at/behind the near plane are dropped."""
        cam = self.camera.matrix()
        projected: list[Vec2] = []
        for p in points:
            x, y, _z, w = cam.apply(_v3(p))
            if w <= 1e-9:  # at or behind the near plane — clipped out
                continue
            projected.append(Vec2(x / w, y / w))
        if not projected:
            return []
        xs = [q.x for q in projected]
        ys = [q.y for q in projected]
        window = [min(xs), min(ys), max(max(xs) - min(xs), 1e-9), max(max(ys) - min(ys), 1e-9)]
        m = window_to_viewport(window, [float(v) for v in self.box], uniform=True)
        return [m.apply(q) for q in projected]


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

    def derivative(self, t: float) -> Vec2:
        """First derivative ``B'(t)`` (the hodograph / velocity). B9."""
        u = 1.0 - t
        return (3 * u * u) * (self.p1 - self.p0) + (6 * u * t) * (self.p2 - self.p1) + (3 * t * t) * (self.p3 - self.p2)

    def second_derivative(self, t: float) -> Vec2:
        """Second derivative ``B''(t)`` (acceleration). B9."""
        u = 1.0 - t
        return (6 * u) * (self.p2 - 2 * self.p1 + self.p0) + (6 * t) * (self.p3 - 2 * self.p2 + self.p1)

    def curvature(self, t: float) -> float:
        """Signed curvature ``κ(t) = (x'y'' − y'x'') / (x'² + y'²)^{3/2}`` (B9,
        Mortenson §6.7). ``|κ| = 1/R`` (R the osculating-circle radius); the sign
        encodes bend direction. Returns 0.0 at a cusp (zero speed)."""
        d1 = self.derivative(t)
        d2 = self.second_derivative(t)
        speed_sq = d1.x * d1.x + d1.y * d1.y
        if speed_sq < 1e-18:
            return 0.0
        return (d1.x * d2.y - d1.y * d2.x) / (speed_sq**1.5)

    def arc_length(self, tolerance: float = 1e-8) -> float:
        """Total arc length ``∫₀¹ |B'(t)| dt`` via adaptive Simpson on the speed
        (B9). ``tolerance`` bounds the quadrature error."""
        def speed(t: float) -> float:
            d = self.derivative(t)
            return math.hypot(d.x, d.y)

        return _adaptive_simpson(speed, 0.0, 1.0, tolerance)

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


# --------------------------------------------------------------------------- #
#  B8 — 2D geometric-intersection primitives (hit-testing / snapping / clip).  #
#  Each is a parametric 2D cross-product solve; the 3D-plane and curve          #
#  intersections named in the backlog are this item's documented expansion.    #
# --------------------------------------------------------------------------- #
_ON = 1e-9  # inclusive endpoint tolerance for on-segment / on-ray tests


def _cross2(ux: float, uy: float, vx: float, vy: float) -> float:
    return ux * vy - uy * vx


def _intersect_params(a0: Vec2, d1: Vec2, b0: Vec2, d2: Vec2) -> tuple[float, float] | None:
    """Solve ``a0 + t·d1 == b0 + u·d2`` for ``(t, u)``; ``None`` when the two
    directions are parallel (cross of directions ≈ 0, which also covers the
    collinear case)."""
    denom = _cross2(d1.x, d1.y, d2.x, d2.y)
    if abs(denom) < 1e-12:
        return None
    diff = b0 - a0
    t = _cross2(diff.x, diff.y, d2.x, d2.y) / denom
    u = _cross2(diff.x, diff.y, d1.x, d1.y) / denom
    return (t, u)


def line_intersection(
    a0: Vec2 | Sequence[float], a1: Vec2 | Sequence[float],
    b0: Vec2 | Sequence[float], b1: Vec2 | Sequence[float],
) -> Vec2 | None:
    """Intersection of the two **infinite lines** through ``(a0, a1)`` and
    ``(b0, b1)``; ``None`` if the lines are parallel (or coincident)."""
    a0, a1, b0, b1 = _v2(a0), _v2(a1), _v2(b0), _v2(b1)
    params = _intersect_params(a0, a1 - a0, b0, b1 - b0)
    if params is None:
        return None
    t, _u = params
    return a0 + (a1 - a0) * t


def segment_intersection(
    a0: Vec2 | Sequence[float], a1: Vec2 | Sequence[float],
    b0: Vec2 | Sequence[float], b1: Vec2 | Sequence[float],
) -> Vec2 | None:
    """Intersection point of two **segments**, or ``None`` if they do not cross.
    Parallel and collinear inputs return ``None`` (a collinear overlap is a
    span, not a single point — out of scope for this primitive)."""
    a0, a1, b0, b1 = _v2(a0), _v2(a1), _v2(b0), _v2(b1)
    params = _intersect_params(a0, a1 - a0, b0, b1 - b0)
    if params is None:
        return None
    t, u = params
    if -_ON <= t <= 1 + _ON and -_ON <= u <= 1 + _ON:
        return a0 + (a1 - a0) * t
    return None


def ray_segment_intersection(
    origin: Vec2 | Sequence[float], direction: Vec2 | Sequence[float],
    s0: Vec2 | Sequence[float], s1: Vec2 | Sequence[float],
) -> Vec2 | None:
    """Where the ray from ``origin`` along ``direction`` meets segment
    ``s0``–``s1``; ``None`` if it misses or the segment lies behind the ray."""
    origin, s0, s1 = _v2(origin), _v2(s0), _v2(s1)
    d = _v2(direction)
    params = _intersect_params(origin, d, s0, s1 - s0)
    if params is None:
        return None
    t, u = params
    if t >= -_ON and -_ON <= u <= 1 + _ON:
        return origin + d * t
    return None


def segment_polygon_intersections(
    a0: Vec2 | Sequence[float], a1: Vec2 | Sequence[float],
    polygon: Iterable[Vec2 | Sequence[float]],
) -> list[Vec2]:
    """Every point where segment ``a0``–``a1`` crosses an edge of ``polygon`` (a
    closed ring of points), de-duplicated (a crossing through a shared vertex is
    found on both incident edges). Order is not significant."""
    a0, a1 = _v2(a0), _v2(a1)
    pts = [_v2(p) for p in polygon]
    n = len(pts)
    out: list[Vec2] = []
    for i in range(n):
        hit = segment_intersection(a0, a1, pts[i], pts[(i + 1) % n])
        if hit is not None and not any(
            abs(hit.x - q.x) < _ON and abs(hit.y - q.y) < _ON for q in out
        ):
            out.append(hit)
    return out


# --------------------------------------------------------------------------- #
#  B8 residual — line/segment × cubic Bézier. De Casteljau subdivision: prune  #
#  a sub-curve when all four controls sit on one side of the query line, else  #
#  split at the midpoint until the control polygon is flat, then intersect its #
#  chord. Mortenson §7 (curve/curve & curve/line intersection by subdivision). #
# --------------------------------------------------------------------------- #
_CURVE_MAX_DEPTH = 40  # subdivision-recursion guard (2^-40 curve span ≪ any tol)


def _bezier_split(cb: CubicBezier, t: float = 0.5) -> tuple[CubicBezier, CubicBezier]:
    """De Casteljau split of ``cb`` at parameter ``t`` into (left, right) cubics."""
    ab = cb.p0 + (cb.p1 - cb.p0) * t
    bc = cb.p1 + (cb.p2 - cb.p1) * t
    cd = cb.p2 + (cb.p3 - cb.p2) * t
    abc = ab + (bc - ab) * t
    bcd = bc + (cd - bc) * t
    mid = abc + (bcd - abc) * t
    return CubicBezier(cb.p0, ab, abc, mid), CubicBezier(mid, bcd, cd, cb.p3)


def _curve_flat(cb: CubicBezier, tol: float) -> bool:
    """Is ``cb`` within ``tol`` of its own ``p0``–``p3`` chord? (max perpendicular
    deviation of the two interior controls; a null chord falls back to spread)."""
    base = cb.p3 - cb.p0
    length = math.hypot(base.x, base.y)
    if length < tol:
        return max(math.hypot(p.x - cb.p0.x, p.y - cb.p0.y) for p in (cb.p1, cb.p2)) < tol
    nx, ny = -base.y / length, base.x / length  # unit normal to the chord
    d1 = abs((cb.p1.x - cb.p0.x) * nx + (cb.p1.y - cb.p0.y) * ny)
    d2 = abs((cb.p2.x - cb.p0.x) * nx + (cb.p2.y - cb.p0.y) * ny)
    return max(d1, d2) < tol


def _chord_hit(a0: Vec2, d1: Vec2, c0: Vec2, c3: Vec2, bounded: bool) -> Vec2 | None:
    """Intersect the query (line through ``a0`` along ``d1``) with the chord
    ``c0``–``c3``; the chord param must stay in [0,1], and the query param too
    when ``bounded`` (a segment). Returns the point or ``None``."""
    params = _intersect_params(a0, d1, c0, c3 - c0)
    if params is None:
        return None
    qt, ct = params  # a0 + qt·d1 == c0 + ct·(c3 − c0)
    if not (-_ON <= ct <= 1 + _ON):
        return None
    if bounded and not (-_ON <= qt <= 1 + _ON):
        return None
    return c0 + (c3 - c0) * ct


def _curve_hits(a0: Vec2, a1: Vec2, curve: CubicBezier, tol: float, bounded: bool) -> list[Vec2]:
    d1 = a1 - a0
    if math.hypot(d1.x, d1.y) < 1e-12:
        return []  # a degenerate (point) query has no well-defined direction
    length = math.hypot(d1.x, d1.y)
    nx, ny = -d1.y / length, d1.x / length  # unit normal to the query line

    def side(p: Vec2) -> float:
        return (p.x - a0.x) * nx + (p.y - a0.y) * ny

    out: list[Vec2] = []
    stack: list[tuple[CubicBezier, int]] = [(curve, 0)]
    while stack:
        cb, depth = stack.pop()
        s = (side(cb.p0), side(cb.p1), side(cb.p2), side(cb.p3))
        if min(s) > tol or max(s) < -tol:
            continue  # convex hull entirely on one side → no crossing here
        if depth >= _CURVE_MAX_DEPTH or _curve_flat(cb, tol):
            hit = _chord_hit(a0, d1, cb.p0, cb.p3, bounded)
            if hit is not None:
                out.append(hit)
            continue
        left, right = _bezier_split(cb, 0.5)
        stack.append((left, depth + 1))
        stack.append((right, depth + 1))

    merge = max(tol * 100, 1e-7)  # fold hits reported by two adjacent leaves
    merged: list[Vec2] = []
    for p in out:
        if not any(abs(p.x - q.x) < merge and abs(p.y - q.y) < merge for q in merged):
            merged.append(p)
    return merged


def segment_curve_intersections(
    a0: Vec2 | Sequence[float], a1: Vec2 | Sequence[float],
    curve: CubicBezier, *, tolerance: float = 1e-7,
) -> list[Vec2]:
    """Every point where **segment** ``a0``–``a1`` crosses cubic Bézier ``curve``
    (B8 residual). A curve can meet a line up to three times, so a list is
    returned; order is not significant. ``tolerance`` bounds the flatten error."""
    return _curve_hits(_v2(a0), _v2(a1), curve, tolerance, bounded=True)


def line_curve_intersections(
    a0: Vec2 | Sequence[float], a1: Vec2 | Sequence[float],
    curve: CubicBezier, *, tolerance: float = 1e-7,
) -> list[Vec2]:
    """Every point where the **infinite line** through ``a0``, ``a1`` crosses cubic
    Bézier ``curve`` (B8 residual) — the unbounded companion to
    :func:`segment_curve_intersections`."""
    return _curve_hits(_v2(a0), _v2(a1), curve, tolerance, bounded=False)


# --------------------------------------------------------------------------- #
#  B9 — curvature & arc-length (curves). Curvature is on CubicBezier; arc      #
#  length integrates |B'(t)| by adaptive Simpson; polyline_length is exact.    #
# --------------------------------------------------------------------------- #
def _adaptive_simpson(f, a: float, b: float, tol: float, max_depth: int = 50) -> float:
    fa, fb, fm = f(a), f(b), f((a + b) / 2)
    whole = (b - a) / 6 * (fa + 4 * fm + fb)
    return _simpson_rec(f, a, b, fa, fm, fb, whole, tol, max_depth)


def _simpson_rec(f, a: float, b: float, fa: float, fm: float, fb: float,
                 whole: float, tol: float, depth: int) -> float:
    m = (a + b) / 2
    flm, frm = f((a + m) / 2), f((m + b) / 2)
    left = (m - a) / 6 * (fa + 4 * flm + fm)
    right = (b - m) / 6 * (fm + 4 * frm + fb)
    if depth <= 0 or abs(left + right - whole) <= 15 * tol:
        return left + right + (left + right - whole) / 15  # Richardson refinement
    return (_simpson_rec(f, a, m, fa, flm, fm, left, tol / 2, depth - 1)
            + _simpson_rec(f, m, b, fm, frm, fb, right, tol / 2, depth - 1))


def polyline_length(points: Iterable[Vec2 | Sequence[float]]) -> float:
    """Total length of the open polyline through ``points`` (0.0 for < 2 points).
    The exact discrete analogue of :meth:`CubicBezier.arc_length` (B9)."""
    pts = [_v2(p) for p in points]
    return sum(
        math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y)
        for i in range(len(pts) - 1)
    )


# --------------------------------------------------------------------------- #
#  B10 — convex hull + computational-geometry primitives (Mortenson §21).      #
#  Broad-phase bounding for B8, layout/packing, hit-test acceleration.         #
# --------------------------------------------------------------------------- #
def convex_hull(points: Iterable[Vec2 | Sequence[float]]) -> list[Vec2]:
    """The 2D convex hull of ``points`` as a convex ring (Andrew's monotone
    chain, O(n log n)). Duplicate points are collapsed and collinear edge points
    excluded; 0/1/2 distinct points return themselves."""
    coords = sorted({_v2(p).tuple() for p in points})
    pts = [Vec2(x, y) for x, y in coords]
    if len(pts) <= 2:
        return pts

    def cross(o: Vec2, a: Vec2, b: Vec2) -> float:
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

    lower: list[Vec2] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[Vec2] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    # drop each list's last point (shared with the other list's first).
    return lower[:-1] + upper[:-1]


def aabb(points: Iterable[Vec2 | Sequence[float]]) -> tuple[Vec2, Vec2]:
    """Axis-aligned bounding box of ``points`` as ``(min_corner, max_corner)``.
    Raises ``ValueError`` on empty input."""
    pts = [_v2(p) for p in points]
    if not pts:
        raise ValueError("aabb needs at least one point")
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    return (Vec2(min(xs), min(ys)), Vec2(max(xs), max(ys)))


def polygon_area(ring: Iterable[Vec2 | Sequence[float]]) -> float:
    """Signed area of the polygon ``ring`` (shoelace). The sign encodes winding;
    ``abs`` is the orientation-free area. Fewer than 3 points → 0.0."""
    pts = [_v2(p) for p in ring]
    n = len(pts)
    if n < 3:
        return 0.0
    s = sum(pts[i].x * pts[(i + 1) % n].y - pts[(i + 1) % n].x * pts[i].y for i in range(n))
    return s / 2.0


def point_in_polygon(
    point: Vec2 | Sequence[float], ring: Iterable[Vec2 | Sequence[float]]
) -> bool:
    """True if ``point`` is inside the polygon ``ring`` (even-odd ray crossing).
    A point exactly on an edge is a boundary case and may test either way."""
    p = _v2(point)
    pts = [_v2(q) for q in ring]
    n = len(pts)
    inside = False
    j = n - 1
    for i in range(n):
        pi, pj = pts[i], pts[j]
        if (pi.y > p.y) != (pj.y > p.y):
            x_cross = (pj.x - pi.x) * (p.y - pi.y) / (pj.y - pi.y) + pi.x
            if p.x < x_cross:
                inside = not inside
        j = i
    return inside


def obb(points: Iterable[Vec2 | Sequence[float]]) -> list[Vec2]:
    """The minimum-area **oriented** bounding box of ``points`` as 4 corners
    (rotating calipers on the convex hull — the min-area rectangle shares an edge
    with the hull, Mortenson §21). Never looser than :func:`aabb`; strictly
    tighter for a rotated shape. Degenerate (< 3 hull points) → the AABB rect."""
    hull = convex_hull(points)
    if len(hull) < 3:
        lo, hi = aabb(hull if hull else list(points))
        return [Vec2(lo.x, lo.y), Vec2(hi.x, lo.y), Vec2(hi.x, hi.y), Vec2(lo.x, hi.y)]
    best_area: float | None = None
    best_corners: list[Vec2] = []
    n = len(hull)
    for i in range(n):
        edge = hull[(i + 1) % n] - hull[i]
        theta = math.atan2(edge.y, edge.x)
        c, s = math.cos(-theta), math.sin(-theta)
        rot = [(p.x * c - p.y * s, p.x * s + p.y * c) for p in hull]
        minx = min(q[0] for q in rot)
        maxx = max(q[0] for q in rot)
        miny = min(q[1] for q in rot)
        maxy = max(q[1] for q in rot)
        area = (maxx - minx) * (maxy - miny)
        if best_area is None or area < best_area:
            cc, ss = math.cos(theta), math.sin(theta)
            best_area = area
            best_corners = [
                Vec2(x * cc - y * ss, x * ss + y * cc)
                for (x, y) in ((minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy))
            ]
    return best_corners


def aabb3(points: Iterable[Vec3 | Sequence[float]]) -> tuple[Vec3, Vec3]:
    """3D axis-aligned bounding box of ``points`` as ``(min_corner, max_corner)``.
    Raises ``ValueError`` on empty input (the 3D analogue of :func:`aabb`)."""
    pts = [_v3(p) for p in points]
    if not pts:
        raise ValueError("aabb3 needs at least one point")
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    zs = [p.z for p in pts]
    return (Vec3(min(xs), min(ys), min(zs)), Vec3(max(xs), max(ys), max(zs)))


def convex_hull_3d(
    points: Iterable[Vec3 | Sequence[float]],
) -> list[tuple[Vec3, Vec3, Vec3]]:
    """The 3D convex hull of ``points`` as **outward-oriented triangular faces**
    (each a tuple of three Vec3 whose normal points away from the hull centroid).

    Brute-force face enumeration — a triple is a hull face iff every other point
    lies on one side of its plane (coplanar points allowed). O(n⁴), intended for
    modest point counts (bounding a mesh, hit-test acceleration). Duplicate points
    are collapsed; a set with fewer than 4 non-coplanar points yields no faces
    (coplanar sets have no 3D hull volume — use :func:`convex_hull` in 2D)."""
    uniq: list[Vec3] = []
    seen: set[tuple[float, float, float]] = set()
    for p in points:
        v = _v3(p)
        key = (round(v.x, 12), round(v.y, 12), round(v.z, 12))
        if key not in seen:
            seen.add(key)
            uniq.append(v)
    n = len(uniq)
    if n < 4:
        return []
    center = Vec3(sum(p.x for p in uniq) / n, sum(p.y for p in uniq) / n,
                  sum(p.z for p in uniq) / n)
    eps = 1e-9
    faces: list[tuple[Vec3, Vec3, Vec3]] = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                a, b, c = uniq[i], uniq[j], uniq[k]
                normal = _cross3(b - a, c - a)
                if _dot3(normal, normal) < eps * eps:
                    continue  # collinear triple — no plane
                pos = neg = 0
                for m in range(n):
                    if m in (i, j, k):
                        continue
                    d = _dot3(normal, uniq[m] - a)
                    if d > eps:
                        pos += 1
                    elif d < -eps:
                        neg += 1
                if (pos and neg) or (pos == 0 and neg == 0):
                    continue  # interior triple, or a fully coplanar set
                fc = Vec3((a.x + b.x + c.x) / 3, (a.y + b.y + c.y) / 3, (a.z + b.z + c.z) / 3)
                # orient the winding so the face normal points away from the centre.
                if _dot3(normal, fc - center) < 0:
                    faces.append((a, c, b))
                else:
                    faces.append((a, b, c))
    return faces


# --------------------------------------------------------------------------- #
#  B1 — the window→viewport transform (Harrington Ch6, ¶43). The named 2D      #
#  stage that Scene3D.render hand-rolled; ViewingPipeline (above) composes it. #
# --------------------------------------------------------------------------- #
def window_to_viewport(
    window: Sequence[float],
    viewport: Sequence[float],
    *,
    uniform: bool = False,
) -> Mat3:
    """The affine mapping the ``window`` rect onto the ``viewport`` rect, each an
    ``[x, y, w, h]`` box (Harrington Ch6, B1). With ``uniform=True`` the scale is
    isotropic (``min`` of the two axes) and the fitted window is centred in the
    viewport — the aspect-preserving "fit". Raises ``ValueError`` on a zero-area
    window."""
    wx, wy, ww, wh = (float(v) for v in window)
    vx, vy, vw, vh = (float(v) for v in viewport)
    if abs(ww) < 1e-12 or abs(wh) < 1e-12:
        raise ValueError("window_to_viewport needs a non-degenerate window")
    if uniform:
        s = min(vw / ww, vh / wh)
        sx = sy = s
        ox = vx + (vw - ww * s) / 2
        oy = vy + (vh - wh * s) / 2
    else:
        sx, sy = vw / ww, vh / wh
        ox, oy = vx, vy
    # x' = sx·(x − wx) + ox = sx·x + (ox − sx·wx); likewise y.
    return Mat3(a=sx, d=sy, e=ox - sx * wx, f=oy - sy * wy)


# --------------------------------------------------------------------------- #
#  B8 (residual) — 3D plane / triangle intersections. A plane is (point,       #
#  normal); the triangle test is Möller–Trumbore.                              #
# --------------------------------------------------------------------------- #
def _ray_plane_t(origin: Vec3, direction: Vec3, plane_point: Vec3, plane_normal: Vec3) -> float | None:
    denom = _dot3(direction, plane_normal)
    if abs(denom) < 1e-12:
        return None  # parallel to the plane
    return _dot3(plane_point - origin, plane_normal) / denom


def ray_plane_intersection(
    origin: Vec3 | Sequence[float], direction: Vec3 | Sequence[float],
    plane_point: Vec3 | Sequence[float], plane_normal: Vec3 | Sequence[float],
) -> Vec3 | None:
    """Where the ray from ``origin`` along ``direction`` meets the plane through
    ``plane_point`` with ``plane_normal``; ``None`` if parallel or the plane lies
    behind the ray."""
    o, d = _v3(origin), _v3(direction)
    t = _ray_plane_t(o, d, _v3(plane_point), _v3(plane_normal))
    if t is None or t < -1e-9:
        return None
    return o + d * t


def segment_plane_intersection(
    a: Vec3 | Sequence[float], b: Vec3 | Sequence[float],
    plane_point: Vec3 | Sequence[float], plane_normal: Vec3 | Sequence[float],
) -> Vec3 | None:
    """Where segment ``a``–``b`` crosses the plane through ``plane_point`` with
    ``plane_normal``; ``None`` if parallel or the crossing is outside the segment."""
    a3, b3 = _v3(a), _v3(b)
    d = b3 - a3
    t = _ray_plane_t(a3, d, _v3(plane_point), _v3(plane_normal))
    if t is None or t < -1e-9 or t > 1 + 1e-9:
        return None
    return a3 + d * t


def ray_triangle_intersection(
    origin: Vec3 | Sequence[float], direction: Vec3 | Sequence[float],
    v0: Vec3 | Sequence[float], v1: Vec3 | Sequence[float], v2: Vec3 | Sequence[float],
) -> Vec3 | None:
    """Möller–Trumbore ray/triangle intersection; ``None`` on a parallel ray, a
    barycentric miss, or a triangle behind the ray origin."""
    o, d = _v3(origin), _v3(direction)
    a0, a1, a2 = _v3(v0), _v3(v1), _v3(v2)
    edge1, edge2 = a1 - a0, a2 - a0
    h = _cross3(d, edge2)
    det = _dot3(edge1, h)
    if abs(det) < 1e-12:
        return None  # ray parallel to the triangle plane
    inv = 1.0 / det
    s = o - a0
    u = inv * _dot3(s, h)
    if u < -1e-9 or u > 1 + 1e-9:
        return None
    q = _cross3(s, edge1)
    v = inv * _dot3(d, q)
    if v < -1e-9 or u + v > 1 + 1e-9:
        return None
    t = inv * _dot3(edge2, q)
    if t < 1e-9:
        return None  # behind the ray origin (or at it)
    return o + d * t


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
    "ViewingPipeline",
    "aabb",
    "aabb3",
    "convex_hull",
    "convex_hull_3d",
    "obb",
    "line_intersection",
    "mirror",
    "point_in_polygon",
    "polygon_area",
    "polyline_length",
    "quarter_circle_kappa",
    "ray_plane_intersection",
    "ray_segment_intersection",
    "ray_triangle_intersection",
    "line_curve_intersections",
    "segment_curve_intersections",
    "segment_intersection",
    "segment_plane_intersection",
    "segment_polygon_intersections",
    "window_to_viewport",
]
