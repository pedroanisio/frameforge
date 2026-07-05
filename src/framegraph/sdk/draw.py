"""Drawing helpers that solve geometry before emitting FrameGraph objects."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Callable, Iterable, Literal, Sequence

from framegraph.sdk.geometry import Camera, Mat4, Path, Vec2, Vec3, window_to_viewport

Scale = str | Callable[[float], float] | dict


@dataclass(frozen=True)
class Material:
    """Face material helper for SDK-authored 2D/3D geometry.

    The helper only expands to ordinary FrameGraph object fields. Translucency,
    blend modes and CSS filters already travel through the existing model/style
    surface; this class gives 3D helpers a single place to keep those fields
    together before :class:`Scene3D` bakes optional lighting into the face fill.
    """

    fill: str = "#dddddd"
    stroke: str | None = "#333333"
    opacity: float | None = None
    mix_blend_mode: str | None = None
    filter: object | None = None
    backdrop_filter: object | None = None

    def style(self) -> dict[str, object]:
        out: dict[str, object] = {"fill": self.fill}
        if self.stroke is not None:
            out["stroke"] = self.stroke
        if self.opacity is not None:
            out["opacity"] = self.opacity
        style: dict[str, object] = {}
        if self.mix_blend_mode is not None:
            style["mix_blend_mode"] = self.mix_blend_mode
        if self.filter is not None:
            style["filter"] = self.filter
        if self.backdrop_filter is not None:
            style["backdrop_filter"] = self.backdrop_filter
        if style:
            out["style"] = style
        return out

    def shaded(self, intensity: float) -> dict[str, object]:
        out = self.style()
        out["fill"] = _shade_color(self.fill, intensity)
        return out


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
        camera: Mat4 | Camera | None = None,
        box: Sequence[float],
        fill: str = "#ddd",
        stroke: str = "#333",
        material: Material | None = None,
        light: Vec3 | Sequence[float] = Vec3(-0.35, -0.65, 0.8),
        ambient: float = 0.38,
        diffuse: float = 0.62,
        shading: Literal["none", "lambert", "gouraud", "phong"] = "none",
        specular: float = 0.35,
        shininess: float = 16.0,
        cull_backfaces: bool = False,
        id: str | None = None,
    ) -> dict[str, object]:
        if camera is None:
            matrix = Mat4.isometric()
        elif isinstance(camera, Camera):
            matrix = camera.matrix()
        else:
            matrix = camera
        # View direction toward the camera, for the B6 Phong specular term; the
        # orthographic/isometric path has no eye, so default to a +z headlight.
        view_dir = (camera.eye - camera.target) if isinstance(camera, Camera) else Vec3(0.0, 0.0, 1.0)
        lit_faces = _face_lighting(
            self.faces, light, ambient=ambient, diffuse=diffuse, shading=shading,
            view=view_dir, specular=specular, shininess=shininess,
        )
        # B2: robust projection with a near-plane clip stage (G1/G2). try_project
        # returns None at/behind the near plane, so a straddling face is dropped
        # rather than crashing or mirror-flipping. Fully-in-front faces project
        # identically to the old path, so existing goldens are unchanged.
        projected = []
        for (face, style), intensity in zip(self.faces, lit_faces):
            pts = [matrix.try_project(p) for p in face]
            if any(q is None for q in pts):
                continue  # near-plane cull
            if cull_backfaces and _is_back_face(pts):
                continue  # back-face removal (G3, opt-in)
            projected.append((pts, _avg_z(matrix, face), style, intensity))
        all_points = [p for face, _z, _style, _intensity in projected for p in face]
        # Children are positioned LOCAL to the returned group's box: a renderer
        # translates a group's children by its box origin, so baking the box origin
        # (bx, by) into the points here as well would offset every face twice and
        # push the projection off-canvas. Only the box *extent* scales the fit.
        bw, bh = float(box[2]), float(box[3])
        if not all_points:
            children: list[dict[str, object]] = []
        else:
            min_x = min(p.x for p in all_points)
            max_x = max(p.x for p in all_points)
            min_y = min(p.y for p in all_points)
            max_y = max(p.y for p in all_points)
            # B1: the isotropic window→viewport fit scale now comes from the named
            # pipeline primitive (sdk.geometry.window_to_viewport) — a single source
            # of truth for the fit, not a second hand-rolled copy of the same
            # min-of-ratios math. Output-preserving: window_to_viewport(uniform=True)
            # returns Mat3.a == min(bw/ww, bh/wh), bit-identical to the former inline
            # expression, so the centring (ox/oy) and per-point mapping are unchanged
            # and existing goldens are byte-for-byte unmoved. The box *origin* stays
            # local — children are translated by the group box downstream.
            window = [min_x, min_y, max(max_x - min_x, 1e-9), max(max_y - min_y, 1e-9)]
            scale = window_to_viewport(window, [0.0, 0.0, bw, bh], uniform=True).a
            ox = (bw - (max_x - min_x) * scale) / 2
            oy = (bh - (max_y - min_y) * scale) / 2
            children = []
            base_material = material or Material(fill=fill, stroke=stroke)
            for face, _z, face_style, intensity in sorted(projected, key=lambda item: item[1]):
                style = dict(face_style)
                points = [[ox + (p.x - min_x) * scale, oy + (p.y - min_y) * scale] for p in face]
                # Canonical closed polyline — not the deprecated 'polygon' alias.
                face_material = style.pop("material", base_material)
                if isinstance(face_material, Material):
                    material_style = face_material.style()
                else:
                    material_style = base_material.style()
                obj: dict[str, object] = {"type": "polyline", "closed": True, "points": points}
                obj.update(material_style)
                obj.update(style)
                if shading != "none" and isinstance(obj.get("fill"), str):
                    obj["fill"] = _shade_color(str(obj["fill"]), intensity)
                children.append(obj)
        group: dict[str, object] = {"type": "group", "box": list(box), "children": children}
        if id is not None:
            group["id"] = id
        return group


# ---- parametric / function / polar curve sampling (roadmap Appendix A.3) --- #
def _xy(value: Sequence[float] | Vec2) -> tuple[float, float]:
    if isinstance(value, Vec2):
        return value.x, value.y
    return float(value[0]), float(value[1])


def _perp_distance(p: Vec2, a: Vec2, b: Vec2) -> float:
    """Perpendicular distance of `p` from the chord `a`→`b` (page units)."""
    dx, dy = b.x - a.x, b.y - a.y
    length = math.hypot(dx, dy)
    if length == 0.0:
        return math.hypot(p.x - a.x, p.y - a.y)
    return abs((p.x - a.x) * dy - (p.y - a.y) * dx) / length


def _refine(
    project: Callable[[float], Vec2],
    t0: float, t1: float, p0: Vec2, p1: Vec2,
    tolerance: float, depth: int, max_depth: int,
) -> list[Vec2]:
    """Adaptive (de Casteljau-style) subdivision: split the interval at its midpoint
    until the sampled midpoint lies within `tolerance` of the chord, concentrating
    points where curvature is high. Returns the samples AFTER p0 (the caller emits
    p0), so concatenation yields the ordered point list."""
    tm = 0.5 * (t0 + t1)
    pm = project(tm)
    if depth >= max_depth or _perp_distance(pm, p0, p1) <= tolerance:
        return [p1]
    return (_refine(project, t0, tm, p0, pm, tolerance, depth + 1, max_depth)
            + _refine(project, tm, t1, pm, p1, tolerance, depth + 1, max_depth))


def parametric_curve(
    fn: Callable[[float], Sequence[float] | Vec2],
    domain: tuple[float, float] = (0.0, 1.0),
    *,
    frame: "Frame | None" = None,
    tolerance: float = 0.5,
    init_segments: int = 16,
    max_depth: int = 16,
    emit: Literal["polyline", "path"] = "polyline",
    **fields: object,
) -> dict[str, object]:
    """Sample a parametric curve ``fn(t) -> (x, y)`` adaptively and emit a FrameGraph
    object (roadmap Appendix A.3 — the 2D curve sampler; ``parametric`` is the 3D
    surface builder).

    Each interval is split at its midpoint until the midpoint lies within
    ``tolerance`` page units of the chord, so samples concentrate where curvature is
    high — correct curves at low point counts. With a ``frame`` the curve is authored
    in data coordinates and flatness is measured in *page* space, so nonlinear scales
    (log/pow) sample correctly; without one ``fn`` is already page-space. ``emit`` is
    ``"polyline"`` or ``"path"`` (a smooth Catmull-Rom path through the samples).
    ``init_segments`` seeds the refinement so symmetric curves (e.g. a full sine)
    are not missed by a midpoint that coincidentally lands on the chord."""
    t0, t1 = float(domain[0]), float(domain[1])
    project = ((lambda t: frame.point(*_xy(fn(t)))) if frame is not None
               else (lambda t: Vec2(*_xy(fn(t)))))
    n = max(1, int(init_segments))
    ts = [t0 + (t1 - t0) * i / n for i in range(n + 1)]
    samples = [project(t) for t in ts]
    points = [samples[0]]
    for i in range(n):
        points.extend(_refine(project, ts[i], ts[i + 1], samples[i], samples[i + 1],
                              tolerance, 0, max_depth))
    if emit == "path":
        return Path().through(points).object(**fields)
    obj: dict[str, object] = {"type": "polyline", "points": [[p.x, p.y] for p in points]}
    obj.update(fields)
    return obj


def function_plot(
    f: Callable[[float], float],
    frame: "Frame",
    *,
    domain: tuple[float, float] | None = None,
    **kwargs: object,
) -> dict[str, object]:
    """Plot ``y = f(x)`` over the frame's x-domain (or ``domain``): the parametric
    curve ``(x, f(x))`` mapped through the frame (roadmap Appendix A.3)."""
    lo = frame.domain[0] if domain is None else float(domain[0])
    hi = frame.domain[2] if domain is None else float(domain[1])
    return parametric_curve(lambda x: (x, f(x)), (lo, hi), frame=frame, **kwargs)


def polar_plot(
    r: Callable[[float], float],
    frame: "Frame",
    *,
    domain: tuple[float, float] = (0.0, 2.0 * math.pi),
    **kwargs: object,
) -> dict[str, object]:
    """Plot a polar function ``radius = r(theta)`` as ``(r·cosθ, r·sinθ)`` mapped
    through the frame (roadmap Appendix A.3)."""
    def fn(theta: float) -> tuple[float, float]:
        radius = r(theta)
        return (radius * math.cos(theta), radius * math.sin(theta))
    return parametric_curve(fn, domain, frame=frame, **kwargs)


# ---- orthographic multiview (roadmap Appendix A.6) ------------------------ #
_VIEW_CAMERAS: dict[str, Callable[[], Mat4]] = {
    "front": Mat4.identity,                 # look down -Z (XY plane)
    "top": lambda: Mat4.rotate_x(90),       # look down -Y (XZ plane)
    "side": lambda: Mat4.rotate_y(90),      # look down -X (ZY plane)
    "iso": Mat4.isometric,                  # isometric 3/4 view
}


def multiview(
    scene: "Scene3D",
    *,
    box: Sequence[float],
    views: Sequence[str] = ("front", "top", "side", "iso"),
    cols: int = 2,
    gap: float = 8.0,
    labels: bool = True,
    label_size: float = 10.0,
    **render_kw: object,
) -> dict[str, object]:
    """Render a :class:`Scene3D` as an engineering **orthographic multiview** — a
    panel grid of front / top / side / isometric views (roadmap Appendix A.6).

    Each panel projects the scene through a pure-rotation camera, and ``Scene3D``'s
    projection drops depth without a perspective divide, so the views are true
    orthographic projections. ``render_kw`` (fill/stroke/shading/light/…) pass
    through to each :meth:`Scene3D.render`."""
    bx, by, bw, bh = (float(v) for v in box[:4])
    n = len(views)
    cols = max(1, min(int(cols), n))
    rows = math.ceil(n / cols)
    pw = (bw - gap * (cols - 1)) / cols
    ph = (bh - gap * (rows - 1)) / rows
    lh = (label_size + 4.0) if labels else 0.0       # reserved label band per panel
    children: list[dict[str, object]] = []
    for i, view in enumerate(views):
        cam = _VIEW_CAMERAS.get(view)
        if cam is None:
            raise ValueError(f"unknown view: {view!r} (use front/top/side/iso)")
        r, c = divmod(i, cols)
        px, py = bx + c * (pw + gap), by + r * (ph + gap)
        if labels:
            children.append({"type": "text", "box": [px, py, pw, lh], "text": view,
                             "style": {"size": label_size, "color": "#475569", "align": "left"}})
        # the scene renders below the label band so the two never overlap
        children.append(scene.render(camera=cam(), box=[px, py + lh, pw, max(ph - lh, 1.0)], **render_kw))
    return {"type": "group", "children": children}


def _log(value: float, base: float | None = None) -> float:
    if value <= 0:
        raise ValueError("log scale requires positive values")
    return math.log(value, base) if base else math.log(value)


def _pow(value: float, exp: float) -> float:
    return math.copysign(abs(value) ** exp, value)   # sign-preserving


def _apply_scale(value: float, scale: Scale) -> float:
    """Map a data value through a scale. Accepts a callable, a name
    (``"linear"``/``"log"``/``"pow2"``), or a structured spec — ``{"kind":"log",
    "base":b}`` / ``{"kind":"pow","exp":e}`` / ``{"kind":"linear"}`` (roadmap A.4)."""
    if callable(scale):
        return float(scale(value))
    if isinstance(scale, dict):
        kind = scale.get("kind", "linear")
        if kind == "linear":
            return value
        if kind == "log":
            return _log(value, scale.get("base"))
        if kind == "pow":
            return _pow(value, float(scale.get("exp", 1.0)))
        raise ValueError(f"unsupported scale kind: {kind!r}")
    if scale == "linear":
        return value
    if scale == "log":
        return _log(value)
    if scale == "pow2":
        return _pow(value, 2.0)
    raise ValueError(f"unsupported scale: {scale!r}")


def _norm(value: float, lo: float, hi: float) -> float:
    if abs(hi - lo) < 1e-12:
        raise ValueError("domain has zero extent after scaling")
    return (value - lo) / (hi - lo)


def _v3(value: Sequence[float] | Vec3) -> Vec3:
    if isinstance(value, Vec3):
        return value
    return Vec3(float(value[0]), float(value[1]), float(value[2]))


def _is_back_face(pts: Sequence[Vec2]) -> bool:
    """Screen-space back-face test (B2/G3): a face whose PROJECTED polygon winds
    clockwise — signed shoelace area < 0 in FrameGraph's Y-down page space — faces
    away from the camera. Degenerate faces (< 3 points) are never culled."""
    n = len(pts)
    if n < 3:
        return False
    area = sum(pts[i].x * pts[(i + 1) % n].y - pts[(i + 1) % n].x * pts[i].y for i in range(n)) / 2.0
    return area < 0.0


def _avg_z(matrix: Mat4, face: Sequence[Vec3]) -> float:
    """Painter's-algorithm depth key — LARGER = NEARER for every projection.

    :meth:`Scene3D.render` sorts ascending and paints in that order, so the face
    closest to the camera must yield the LARGEST key (drawn last, on top).

    The orthographic/isometric path (homogeneous ``w == 1``) already has larger
    transformed ``z`` = nearer. A real perspective projection inverts that — its
    NDC depth maps near ``-> -1`` and far ``-> +1`` — so the perspective key is
    negated to keep one consistent convention. Without this, perspective scenes
    painted far faces *over* near ones (harmless on a lone heightfield, which
    barely self-overlaps, but wrong for any solid or separated geometry).
    """
    w_row = matrix.values[3]
    perspective = (abs(w_row[0]) > 1e-9 or abs(w_row[1]) > 1e-9
                   or abs(w_row[2]) > 1e-9 or abs(w_row[3] - 1.0) > 1e-9)
    total = 0.0
    for p in face:
        x4 = matrix.apply(p)
        w = x4[3]
        total += x4[2] / w if abs(w) > 1e-12 else x4[2]
    key = total / max(1, len(face))
    return -key if perspective else key


def _face_lighting(
    faces: Sequence[tuple[list[Vec3], dict[str, object]]],
    light: Vec3 | Sequence[float],
    *,
    ambient: float,
    diffuse: float,
    shading: Literal["none", "lambert", "gouraud", "phong"],
    view: Vec3 | Sequence[float] | None = None,
    specular: float = 0.35,
    shininess: float = 16.0,
) -> list[float]:
    if shading == "none":
        return [1.0] * len(faces)
    light_dir = _normalize(_v3(light))
    ambient = max(0.0, min(1.0, ambient))
    diffuse = max(0.0, diffuse)
    if shading == "lambert":
        return [_light_intensity(_face_normal(face), light_dir, ambient, diffuse) for face, _style in faces]
    if shading == "phong":
        # Blinn-Phong: diffuse base + a specular highlight along the halfway
        # vector between the light and the viewer (B6). Global light + view, so
        # the halfway vector is constant across faces.
        view_dir = _normalize(_v3(view)) if view is not None else Vec3(0.0, 0.0, 1.0)
        half = _normalize(light_dir + view_dir)
        return [
            _light_intensity_phong(_face_normal(face), light_dir, half, ambient, diffuse, specular, shininess)
            for face, _style in faces
        ]
    if shading == "gouraud":
        vertex_normals: dict[tuple[float, float, float], Vec3] = {}
        for face, _style in faces:
            normal = _face_normal(face)
            for point in face:
                key = point.tuple()
                vertex_normals[key] = vertex_normals.get(key, Vec3(0.0, 0.0, 0.0)) + normal
        out = []
        for face, _style in faces:
            values = [
                _light_intensity(_normalize(vertex_normals[p.tuple()]), light_dir, ambient, diffuse)
                for p in face
            ]
            out.append(sum(values) / max(1, len(values)))
        return out
    raise ValueError(f"unsupported Scene3D shading mode: {shading!r}")


def _light_intensity(normal: Vec3, light_dir: Vec3, ambient: float, diffuse: float) -> float:
    lambert = max(0.0, _dot(normal, light_dir))
    return max(0.0, min(1.0, ambient + diffuse * lambert))


def _light_intensity_phong(
    normal: Vec3, light_dir: Vec3, half: Vec3,
    ambient: float, diffuse: float, specular: float, shininess: float,
) -> float:
    """Blinn-Phong intensity (B6): diffuse Lambert + a specular highlight
    ``specular·max(0, n·h)^shininess``, applied only where the face is lit."""
    lambert = max(0.0, _dot(normal, light_dir))
    spec = specular * (max(0.0, _dot(normal, half)) ** shininess) if lambert > 0.0 else 0.0
    return max(0.0, min(1.0, ambient + diffuse * lambert + spec))


def _face_normal(face: Sequence[Vec3]) -> Vec3:
    if len(face) < 3:
        return Vec3(0.0, 0.0, 1.0)
    origin = face[0]
    for i in range(1, len(face) - 1):
        normal = _cross(face[i] - origin, face[i + 1] - origin)
        if _length(normal) > 1e-12:
            return _normalize(normal)
    return Vec3(0.0, 0.0, 1.0)


def _shade_color(color: str, intensity: float) -> str:
    rgb = _parse_hex_color(color)
    if rgb is None:
        return color
    factor = max(0.0, min(1.0, intensity))
    return "#" + "".join(f"{max(0, min(255, round(channel * factor))):02x}" for channel in rgb)


def _parse_hex_color(color: str) -> tuple[int, int, int] | None:
    value = color.strip()
    if not value.startswith("#"):
        return None
    c = value[1:]
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return None
    try:
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except ValueError:
        return None


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x)


def _dot(a: Vec3, b: Vec3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def _length(v: Vec3) -> float:
    return math.sqrt(_dot(v, v))


def _normalize(v: Vec3) -> Vec3:
    length = _length(v)
    if length < 1e-12:
        return Vec3(0.0, 0.0, 1.0)
    return Vec3(v.x / length, v.y / length, v.z / length)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


__all__ = ["Frame", "Material", "Scene3D"]
