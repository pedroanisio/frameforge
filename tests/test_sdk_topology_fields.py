#!/usr/bin/env python3
"""Public-surface tests for the topology / perspective / field / lattice / manifold helpers."""
from __future__ import annotations

import math
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    Camera,
    DocumentBuilder,
    Graph,
    ScalarField,
    Vec3,
    VectorField,
    lattice,
    manifold,
)
from frameforge.sdk.geometry import Mat4  # noqa: E402


def _validates(*groups, size=(400, 300)):
    """Add the groups to a page and run them through full model validation."""
    builder = DocumentBuilder(profile="diagram")
    layer = builder.page("p", canvas={"size": list(size), "units": "px"},
                         coordinate_mode="absolute").layer("main")
    for g in groups:
        layer.add(g)
    return builder.build()


# --- perspective camera ----------------------------------------------------- #
def test_camera_projects_finite_and_matches_lookat_projection():
    cam = Camera(eye=Vec3(3, 2, 4), target=Vec3(0, 0, 0), fov=45, aspect=1.6)
    p = cam.project((0, 0, 0))
    assert math.isfinite(p.x) and math.isfinite(p.y)
    # Camera.matrix() == projection @ view, and project divides by w.
    direct = (cam.projection() @ cam.view()).project((0.5, -0.2, 0.3))
    via = cam.project((0.5, -0.2, 0.3))
    assert via.x == pytest.approx(direct.x)
    assert via.y == pytest.approx(direct.y)


def test_camera_orbit_preserves_radius():
    cam = Camera(eye=Vec3(0, 0, 5), target=Vec3(0, 0, 0))
    r0 = math.dist(cam.eye.tuple(), cam.target.tuple())
    moved = cam.orbit(azimuth=37, elevation=12)
    r1 = math.dist(moved.eye.tuple(), moved.target.tuple())
    assert r1 == pytest.approx(r0)
    assert moved.eye.tuple() != cam.eye.tuple()


def test_perspective_fov_rejects_bad_planes():
    with pytest.raises(ValueError):
        Mat4.perspective_fov(45, 1.0, near=0.0, far=10.0)
    with pytest.raises(ValueError):
        Mat4.perspective_fov(45, 1.0, near=5.0, far=1.0)


# --- topology --------------------------------------------------------------- #
def test_graph_layouts_cover_every_node():
    g = Graph()
    for a, b in [("a", "b"), ("b", "c"), ("c", "d"), ("a", "d")]:
        g.edge(a, b)
    ids = {n.id for n in g.nodes}
    for layout in (g.circular_layout(), g.grid_layout(), g.radial_layout("a"),
                   g.layered_layout(), g.spring_layout(iterations=30)):
        assert set(layout) == ids


def test_spring_layout_is_deterministic():
    g = Graph()
    for a, b in [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")]:
        g.edge(a, b)
    first = g.spring_layout(iterations=80)
    second = g.spring_layout(iterations=80)
    for nid in first:
        assert first[nid].tuple() == pytest.approx(second[nid].tuple())


def test_graph_render_emits_one_group_with_edges_nodes_labels_in_box():
    g = Graph().node("a", "a").node("b", "b")
    g.edge("a", "b", directed=True)
    box = [10, 20, 200, 160]
    grp = g.render(g.circular_layout(), box=box, id="net")
    assert grp["type"] == "group" and grp["box"] == box and grp["id"] == "net"
    types = {c["type"] for c in grp["children"]}
    assert {"polyline", "ellipse", "text"} <= types
    pts = [p for c in grp["children"] if c["type"] == "polyline" for p in c["points"]]
    assert all(0 <= x <= box[2] and 0 <= y <= box[3] for x, y in pts)
    _validates(grp)


def test_graph_render_3d_projects_through_camera():
    g = Graph()
    for a, b in [("n0", "n1"), ("n1", "n2"), ("n2", "n0")]:
        g.edge(a, b)
    pos = {"n0": Vec3(-1, 0, 0), "n1": Vec3(1, 0, 0), "n2": Vec3(0, 1, 1)}
    cam = Camera(eye=Vec3(2, 2, 3), fov=50)
    grp = g.render(pos, box=[0, 0, 240, 200], camera=cam, labels=False)
    assert grp["children"]
    _validates(grp)


def test_graph_render_empty_is_safe():
    grp = Graph().render({}, box=[5, 5, 100, 80], id="empty")
    assert grp["children"] == [] and grp["box"] == [5, 5, 100, 80]
    _validates(grp)


# --- fields ----------------------------------------------------------------- #
def test_vector_field_renders_arrows_inside_box():
    vf = VectorField(lambda x, y: (-y, x), domain=(-1, -1, 1, 1))
    grp = vf.render(box=[0, 0, 200, 200], steps_x=6, steps_y=6)
    assert grp["children"]
    assert all(c["type"] == "polyline" for c in grp["children"])
    _validates(grp)


def test_scalar_field_heatmap_and_contours_validate():
    sf = ScalarField(lambda x, y: math.sin(2 * x) * math.cos(2 * y), domain=(-1.5, -1.5, 1.5, 1.5))
    hm = sf.heatmap(box=[0, 0, 200, 160], steps_x=12, steps_y=10)
    ct = sf.contours(box=[0, 0, 200, 160], levels=5, steps_x=20, steps_y=16)
    assert all(c["type"] == "rect" for c in hm["children"])
    assert ct["children"] and all(c["type"] == "polyline" for c in ct["children"])
    _validates(hm, ct)


# --- lattices --------------------------------------------------------------- #
@pytest.mark.parametrize("kind", ["square", "triangular", "honeycomb", "cubic", "bcc", "fcc"])
def test_lattice_kinds_build_points_and_bonds(kind):
    lat = lattice(kind, nx=3, ny=3, nz=2)
    assert lat.points and lat.bonds
    grp = lat.render(box=[0, 0, 220, 200])
    _validates(grp)


def test_lattice_rejects_unknown_kind():
    with pytest.raises(ValueError):
        lattice("hyperdiamond")


def test_lattice_3d_projects_through_camera():
    grp = lattice("fcc", nx=2, ny=2, nz=2).render(
        box=[0, 0, 240, 220], camera=Camera(eye=Vec3(3, 2, 3), fov=46))
    assert grp["children"]
    _validates(grp)


# --- manifolds -------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["sphere", "torus", "mobius", "klein_bottle", "saddle"])
def test_manifold_surfaces_render_through_camera(name):
    scene = getattr(manifold, name)(steps_u=10, steps_v=8) if name != "saddle" \
        else manifold.saddle(steps=10)
    grp = scene.render(box=[0, 0, 200, 180], camera=Camera(eye=Vec3(2.5, 2, 3.2), fov=46))
    assert grp["type"] == "group" and grp["children"]
    _validates(grp)


def test_wave_interference_surface_renders():
    scene = manifold.wave(sources=[(-0.5, -0.5), (0.5, 0.5)], steps=12)
    grp = scene.render(box=[0, 0, 200, 180], camera=Camera(eye=Vec3(2.5, 2, 3.2), fov=46),
                       fill="#bae6fd", stroke="#0369a1")
    assert grp["children"]
    _validates(grp)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
