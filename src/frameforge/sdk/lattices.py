"""Crystal/grid lattice generators.

Build the classic 2D (square, triangular, honeycomb) and 3D (cubic, bcc, fcc)
lattices as point sets with nearest-neighbour bonds, then render them through the
topology :class:`~frameforge.sdk.Graph` — flat for 2D, or projected through a
perspective :class:`~frameforge.sdk.Camera` for 3D. Everything is deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Sequence

from frameforge.sdk.geometry import Camera, Mat4, Vec3
from frameforge.sdk.topology import Graph

_BASIS = {
    "cubic": [(0.0, 0.0, 0.0)],
    "bcc": [(0.0, 0.0, 0.0), (0.5, 0.5, 0.5)],
    "fcc": [(0.0, 0.0, 0.0), (0.5, 0.5, 0.0), (0.5, 0.0, 0.5), (0.0, 0.5, 0.5)],
}


@dataclass
class Lattice:
    """A set of named lattice sites in 3D plus nearest-neighbour bonds."""

    points: dict[str, Vec3] = field(default_factory=dict)
    bonds: list[tuple[str, str]] = field(default_factory=list)

    def graph(self) -> Graph:
        g = Graph()
        for name in self.points:
            g.node(name)
        for a, b in self.bonds:
            g.edge(a, b)
        return g

    def render(
        self,
        *,
        box: Sequence[float],
        camera: Camera | Mat4 | None = None,
        node_radius: float = 5.0,
        node_fill: str = "#1e293b",
        node_stroke: str = "#0f172a",
        edge_color: str = "#94a3b8",
        edge_width: float = 1.2,
        id: str | None = None,
    ) -> dict[str, object]:
        positions = {name: p for name, p in self.points.items()}
        return self.graph().render(
            positions, box=box, camera=camera, node_radius=node_radius,
            node_fill=node_fill, node_stroke=node_stroke, edge_color=edge_color,
            edge_width=edge_width, labels=False, id=id,
        )


def lattice(kind: str, *, nx: int = 4, ny: int = 4, nz: int = 1, a: float = 1.0,
            bond_tol: float = 1e-3) -> Lattice:
    """Build a finite lattice block.

    2D kinds (``"square"``, ``"triangular"``, ``"honeycomb"``) ignore ``nz``;
    3D kinds (``"cubic"``, ``"bcc"``, ``"fcc"``) use the conventional cubic cell
    with the appropriate motif. Bonds join each pair of sites at the lattice's
    minimum interatomic distance (± ``bond_tol``).
    """
    kind = kind.lower()
    raw: list[tuple[float, float, float]] = []
    if kind == "square":
        raw = [(i * a, j * a, 0.0) for j in range(ny) for i in range(nx)]
    elif kind == "triangular":
        for j in range(ny):
            for i in range(nx):
                raw.append(((i + (0.5 if j % 2 else 0.0)) * a, j * a * math.sqrt(3) / 2, 0.0))
    elif kind == "honeycomb":
        dy = a * math.sqrt(3) / 2
        for j in range(ny):
            for i in range(nx):
                x0 = i * a * 1.5
                y0 = j * 2 * dy + (dy if i % 2 else 0.0)
                raw.append((x0, y0, 0.0))
                raw.append((x0 + a * 0.5, y0 + dy, 0.0))
    elif kind in _BASIS:
        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    for bx, by, bz in _BASIS[kind]:
                        raw.append(((i + bx) * a, (j + by) * a, (k + bz) * a))
    else:
        raise ValueError(f"unknown lattice kind: {kind!r}")

    # de-duplicate coincident sites (shared cell corners)
    uniq: list[tuple[float, float, float]] = []
    seen: set[tuple[int, int, int]] = set()
    for p in raw:
        key = (round(p[0] / a * 2), round(p[1] / a * 2), round(p[2] / a * 2))
        if key not in seen:
            seen.add(key)
            uniq.append(p)

    points = {f"s{i}": Vec3(*p) for i, p in enumerate(uniq)}
    names = list(points)
    # nearest-neighbour distance
    best = math.inf
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            best = min(best, _dist(points[names[i]], points[names[j]]))
    bonds: list[tuple[str, str]] = []
    if math.isfinite(best):
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if abs(_dist(points[names[i]], points[names[j]]) - best) <= best * 0.02 + bond_tol:
                    bonds.append((names[i], names[j]))
    return Lattice(points=points, bonds=bonds)


def _dist(a: Vec3, b: Vec3) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


__all__ = ["Lattice", "lattice"]
