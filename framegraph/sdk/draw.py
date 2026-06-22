"""Drawing helpers that solve geometry before emitting FrameGraph objects."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Callable, Iterable, Sequence

from framegraph.sdk.geometry import Mat4, Path, Vec2, Vec3

Scale = str | Callable[[float], float]


@dataclass(frozen=True)
class Frame:
    """Map a data domain into a FrameGraph page box."""

    domain: tuple[float, float, float, float]
    box: tuple[float, float, float, float]
    x_scale: Scale = "linear"
    y_scale: Scale = "linear"

    def point(self, x: float, y: float) -> Vec2:
        xmin, ymin, xmax, ymax = self.domain
        bx, by, bw, bh = self.box
        sx0 = _apply_scale(xmin, self.x_scale)
        sx1 = _apply_scale(xmax, self.x_scale)
        sy0 = _apply_scale(ymin, self.y_scale)
        sy1 = _apply_scale(ymax, self.y_scale)
        sx = _norm(_apply_scale(x, self.x_scale), sx0, sx1)
        sy = _norm(_apply_scale(y, self.y_scale), sy0, sy1)
        return Vec2(bx + sx * bw, by + (1 - sy) * bh)

    def polyline(self, points: Iterable[Sequence[float]], **fields: object) -> dict[str, object]:
        obj: dict[str, object] = {
            "type": "polyline",
            "points": [[p.x, p.y] for p in (self.point(float(x), float(y)) for x, y in points)],
        }
        obj.update(fields)
        return obj

    def path(self, points: Iterable[Sequence[float]], **fields: object) -> dict[str, object]:
        mapped = [self.point(float(x), float(y)) for x, y in points]
        path = Path()
        if mapped:
            path.move_to(mapped[0].x, mapped[0].y)
            for p in mapped[1:]:
                path.line_to(p.x, p.y)
        return path.object(**fields)


@dataclass
class Scene3D:
    """Minimal 3D scene that projects meshes to FrameGraph 2D polygons."""

    faces: list[tuple[list[Vec3], dict[str, object]]] = field(default_factory=list)

    def mesh(
        self,
        vertices: Sequence[Sequence[float] | Vec3],
        faces: Sequence[Sequence[int]],
        **style: object,
    ) -> "Scene3D":
        verts = [_v3(v) for v in vertices]
        for face in faces:
            self.faces.append(([verts[i] for i in face], dict(style)))
        return self

    def parametric_surface(
        self,
        fn: Callable[[float, float], Sequence[float] | Vec3],
        *,
        u: tuple[float, float],
        v: tuple[float, float],
        steps_u: int,
        steps_v: int,
        **style: object,
    ) -> "Scene3D":
        grid = [
            [
                _v3(fn(_lerp(u[0], u[1], i / steps_u), _lerp(v[0], v[1], j / steps_v)))
                for j in range(steps_v + 1)
            ]
            for i in range(steps_u + 1)
        ]
        for i in range(steps_u):
            for j in range(steps_v):
                self.faces.append(
                    ([grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]], dict(style))
                )
        return self

    def extrude(self, polygon: Sequence[Sequence[float]], depth: float, **style: object) -> "Scene3D":
        front = [Vec3(float(x), float(y), 0.0) for x, y in polygon]
        back = [Vec3(p.x, p.y, depth) for p in front]
        self.faces.append((front, dict(style)))
        self.faces.append((list(reversed(back)), dict(style)))
        n = len(front)
        for i in range(n):
            self.faces.append(([front[i], front[(i + 1) % n], back[(i + 1) % n], back[i]], dict(style)))
        return self

    def revolve(
        self,
        profile: Sequence[Sequence[float]],
        *,
        segments: int = 24,
        **style: object,
    ) -> "Scene3D":
        rings: list[list[Vec3]] = []
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            co = math.cos(angle)
            si = math.sin(angle)
            rings.append([Vec3(float(r) * co, float(y), float(r) * si) for r, y in profile])
        for i in range(segments):
            for j in range(len(profile) - 1):
                self.faces.append(
                    ([rings[i][j], rings[i + 1][j], rings[i + 1][j + 1], rings[i][j + 1]], dict(style))
                )
        return self

    def render(
        self,
        *,
        camera: Mat4 | None = None,
        box: Sequence[float],
        fill: str = "#ddd",
        stroke: str = "#333",
        id: str | None = None,
    ) -> dict[str, object]:
        matrix = camera or Mat4.isometric()
        projected = [([matrix.project(p) for p in face], _avg_z(matrix, face), style) for face, style in self.faces]
        all_points = [p for face, _z, _style in projected for p in face]
        bx, by, bw, bh = (float(box[0]), float(box[1]), float(box[2]), float(box[3]))
        if not all_points:
            children: list[dict[str, object]] = []
        else:
            min_x = min(p.x for p in all_points)
            max_x = max(p.x for p in all_points)
            min_y = min(p.y for p in all_points)
            max_y = max(p.y for p in all_points)
            scale = min(bw / max(max_x - min_x, 1e-9), bh / max(max_y - min_y, 1e-9))
            ox = bx + (bw - (max_x - min_x) * scale) / 2
            oy = by + (bh - (max_y - min_y) * scale) / 2
            children = []
            for face, _z, style in sorted(projected, key=lambda item: item[1]):
                points = [[ox + (p.x - min_x) * scale, oy + (p.y - min_y) * scale] for p in face]
                obj: dict[str, object] = {"type": "polygon", "points": points, "fill": fill, "stroke": stroke}
                obj.update(style)
                children.append(obj)
        group: dict[str, object] = {"type": "group", "box": list(box), "children": children}
        if id is not None:
            group["id"] = id
        return group


def _apply_scale(value: float, scale: Scale) -> float:
    if callable(scale):
        return float(scale(value))
    if scale == "linear":
        return value
    if scale == "log":
        if value <= 0:
            raise ValueError("log scale requires positive values")
        return math.log(value)
    if scale == "pow2":
        return math.copysign(abs(value) ** 2, value)
    raise ValueError(f"unsupported scale: {scale!r}")


def _norm(value: float, lo: float, hi: float) -> float:
    if abs(hi - lo) < 1e-12:
        raise ValueError("domain has zero extent after scaling")
    return (value - lo) / (hi - lo)


def _v3(value: Sequence[float] | Vec3) -> Vec3:
    if isinstance(value, Vec3):
        return value
    return Vec3(float(value[0]), float(value[1]), float(value[2]))


def _avg_z(matrix: Mat4, face: Sequence[Vec3]) -> float:
    return sum(matrix.apply(p)[2] for p in face) / max(1, len(face))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


__all__ = ["Frame", "Scene3D"]
