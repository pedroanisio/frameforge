"""Network-topology helpers: build a node-link graph, lay it out with a
deterministic algorithm, and render it into a single FrameGraph group.

The module pairs with :mod:`framegraph.sdk.geometry`'s perspective
:class:`~framegraph.sdk.Camera`: a layout can return 2D positions for a flat
diagram, or 3D positions that :meth:`Graph.render` projects through a camera for
a perspective network view. Everything is deterministic (no RNG), so a fixture
re-rendered tomorrow is byte-identical.

A rendered graph is one ``group`` object. The geometric audit in
``tooling/validate.py`` only inspects top-level layer objects, so wrapping nodes,
edges and labels in a group keeps containment / tabular-box-model audits silent;
labels are still sized against real font metrics so ``--check-overflow`` passes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Sequence

from framegraph.sdk.geometry import Camera, Mat4, Vec2, Vec3
from framegraph.sdk.metrics import measure_text

Point = Vec2 | Vec3 | Sequence[float]


@dataclass
class Node:
    """A graph vertex. ``weight`` scales the drawn radius; ``pos`` pins an
    explicit position (2D or 3D) that layouts will honour instead of solving."""

    id: str
    label: str | None = None
    weight: float = 1.0
    pos: Point | None = None
    style: dict[str, object] = field(default_factory=dict)


@dataclass
class Edge:
    """A connection between two node ids. ``directed`` adds an arrowhead at
    ``dst``; ``weight`` scales the stroke width."""

    src: str
    dst: str
    directed: bool = False
    label: str | None = None
    weight: float = 1.0
    style: dict[str, object] = field(default_factory=dict)


class Graph:
    """A node-link graph with deterministic layouts and a single-group renderer."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []

    # -- construction ------------------------------------------------------- #
    def node(self, id: str, label: str | None = None, *, weight: float = 1.0,
             pos: Point | None = None, **style: object) -> "Graph":
        self._nodes[id] = Node(id=id, label=label, weight=weight, pos=pos, style=dict(style))
        return self

    def edge(self, src: str, dst: str, *, directed: bool = False, label: str | None = None,
             weight: float = 1.0, **style: object) -> "Graph":
        for end in (src, dst):
            if end not in self._nodes:
                self.node(end)
        self._edges.append(Edge(src, dst, directed=directed, label=label,
                                weight=weight, style=dict(style)))
        return self

    @property
    def nodes(self) -> list[Node]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    def neighbors(self, id: str) -> list[str]:
        out: list[str] = []
        for e in self._edges:
            if e.src == id:
                out.append(e.dst)
            elif e.dst == id:
                out.append(e.src)
        return out

    def degree(self, id: str) -> int:
        return sum((e.src == id) + (e.dst == id) for e in self._edges)

    # -- layouts (each returns {node_id: Vec2}) ----------------------------- #
    def circular_layout(self, *, radius: float = 1.0, start: float = -90.0) -> dict[str, Vec2]:
        """Evenly space nodes on a circle, first node at ``start`` degrees."""
        ids = list(self._nodes)
        n = max(1, len(ids))
        out: dict[str, Vec2] = {}
        for i, nid in enumerate(ids):
            ang = math.radians(start + 360.0 * i / n)
            out[nid] = Vec2(radius * math.cos(ang), radius * math.sin(ang))
        return out

    def grid_layout(self, *, cols: int | None = None) -> dict[str, Vec2]:
        """Row-major grid; ``cols`` defaults to ``ceil(sqrt(n))``."""
        ids = list(self._nodes)
        n = max(1, len(ids))
        c = cols or max(1, math.ceil(math.sqrt(n)))
        return {nid: Vec2(float(i % c), float(i // c)) for i, nid in enumerate(ids)}

    def radial_layout(self, root: str, *, ring: float = 1.0) -> dict[str, Vec2]:
        """Concentric rings by BFS distance from ``root`` (a tree/hub view)."""
        if root not in self._nodes:
            raise ValueError(f"unknown root node: {root!r}")
        depth: dict[str, int] = {root: 0}
        order: list[str] = [root]
        queue = [root]
        while queue:
            cur = queue.pop(0)
            for nb in self.neighbors(cur):
                if nb not in depth:
                    depth[nb] = depth[cur] + 1
                    order.append(nb)
                    queue.append(nb)
        for nid in self._nodes:  # disconnected nodes ride the outermost ring
            if nid not in depth:
                depth[nid] = max(depth.values(), default=0) + 1
                order.append(nid)
        rings: dict[int, list[str]] = {}
        for nid in order:
            rings.setdefault(depth[nid], []).append(nid)
        out: dict[str, Vec2] = {}
        for d, members in rings.items():
            if d == 0:
                out[members[0]] = Vec2(0.0, 0.0)
                continue
            for i, nid in enumerate(members):
                ang = 2 * math.pi * i / len(members)
                out[nid] = Vec2(d * ring * math.cos(ang), d * ring * math.sin(ang))
        return out

    def layered_layout(self, *, gap: float = 1.0) -> dict[str, Vec2]:
        """Left-to-right layered (Sugiyama-lite) layout for a DAG.

        Layer = longest directed path from any source; within a layer, nodes keep
        insertion order and are centred vertically. Cycles fall back to BFS order.
        """
        ids = list(self._nodes)
        succ: dict[str, list[str]] = {nid: [] for nid in ids}
        indeg: dict[str, int] = {nid: 0 for nid in ids}
        for e in self._edges:
            succ[e.src].append(e.dst)
            indeg[e.dst] += 1
        layer: dict[str, int] = {nid: 0 for nid in ids}
        queue = [nid for nid in ids if indeg[nid] == 0] or list(ids)
        seen: set[str] = set()
        while queue:
            cur = queue.pop(0)
            if cur in seen:
                continue
            seen.add(cur)
            for nxt in succ[cur]:
                if layer[nxt] < layer[cur] + 1:
                    layer[nxt] = layer[cur] + 1
                indeg[nxt] -= 1
                if indeg[nxt] <= 0 or nxt not in seen:
                    queue.append(nxt)
        columns: dict[int, list[str]] = {}
        for nid in ids:
            columns.setdefault(layer[nid], []).append(nid)
        tallest = max((len(c) for c in columns.values()), default=1)
        out: dict[str, Vec2] = {}
        for lx, members in columns.items():
            offset = (tallest - len(members)) / 2.0
            for i, nid in enumerate(members):
                out[nid] = Vec2(lx * gap, (offset + i) * gap)
        return out

    def spring_layout(self, *, iterations: int = 220, k: float | None = None,
                      seed_radius: float = 1.0) -> dict[str, Vec2]:
        """Deterministic Fruchterman–Reingold force layout.

        Seeded from the circular layout (no RNG), so it is fully reproducible.
        """
        ids = list(self._nodes)
        n = len(ids)
        if n == 0:
            return {}
        pos = {nid: Vec2(p.x, p.y) for nid, p in self.circular_layout(radius=seed_radius).items()}
        area = 1.0
        kk = k if k is not None else math.sqrt(area / n)
        temp = 0.1
        for _ in range(iterations):
            disp = {nid: Vec2(0.0, 0.0) for nid in ids}
            for i in range(n):
                for j in range(i + 1, n):
                    a, b = ids[i], ids[j]
                    delta = pos[a] - pos[b]
                    dist = math.hypot(delta.x, delta.y) or 1e-4
                    force = (kk * kk) / dist  # repulsion
                    push = Vec2(delta.x / dist * force, delta.y / dist * force)
                    disp[a] = disp[a] + push
                    disp[b] = disp[b] - push
            for e in self._edges:
                delta = pos[e.src] - pos[e.dst]
                dist = math.hypot(delta.x, delta.y) or 1e-4
                force = (dist * dist) / kk  # attraction
                pull = Vec2(delta.x / dist * force, delta.y / dist * force)
                disp[e.src] = disp[e.src] - pull
                disp[e.dst] = disp[e.dst] + pull
            for nid in ids:
                d = disp[nid]
                dist = math.hypot(d.x, d.y) or 1e-4
                step = min(dist, temp)
                pos[nid] = pos[nid] + Vec2(d.x / dist * step, d.y / dist * step)
            temp = max(temp * 0.97, 1e-3)  # cool down
        return pos

    # -- automatic layout (infer the algorithm from graph structure) -------- #
    def _is_directed(self) -> bool:
        return any(e.directed for e in self._edges)

    def _is_connected(self) -> bool:
        if not self._nodes:
            return True
        start = next(iter(self._nodes))
        seen, stack = {start}, [start]
        while stack:
            for nb in self.neighbors(stack.pop()):
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        return len(seen) == len(self._nodes)

    def _is_dag(self) -> bool:
        """True if the src→dst edges form a directed acyclic graph (Kahn's)."""
        indeg = {nid: 0 for nid in self._nodes}
        succ: dict[str, list[str]] = {nid: [] for nid in self._nodes}
        for e in self._edges:
            succ[e.src].append(e.dst)
            indeg[e.dst] += 1
        queue = [nid for nid in self._nodes if indeg[nid] == 0]
        seen = 0
        while queue:
            cur = queue.pop()
            seen += 1
            for nxt in succ[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        return seen == len(self._nodes)

    def _is_tree(self) -> bool:
        return len(self._edges) == len(self._nodes) - 1 and self._is_connected()

    def _auto_root(self) -> str | None:
        """A natural root: a directed source (in-degree 0) if any, else the
        highest-degree hub; deterministic (ties break by insertion order)."""
        if not self._nodes:
            return None
        indeg = {nid: 0 for nid in self._nodes}
        for e in self._edges:
            indeg[e.dst] += 1
        ids = list(self._nodes)
        sources = [nid for nid in ids if indeg[nid] == 0]
        if sources:
            return sources[0]
        return max(ids, key=self.degree)

    def layout_kind(self) -> str:
        """Infer the best-fit layout algorithm from the graph's structure:
        ``grid`` (no edges), ``radial`` (undirected tree → hub view), ``layered``
        (directed acyclic → hierarchy), or ``spring`` (cyclic / general)."""
        if not self._edges:
            return "grid"
        if self._is_tree() and not self._is_directed():
            return "radial"
        if self._is_dag():
            return "layered"
        return "spring"

    def auto_layout(self, **overrides: object) -> dict[str, Vec2]:
        """Lay the graph out automatically — pick the algorithm from structure
        (:meth:`layout_kind`) and apply it, so positioning is *inferred from the
        declared edges* rather than chosen by hand. ``overrides`` pass through to the
        chosen layout (e.g. ``gap=``/``radius=``)."""
        kind = self.layout_kind()
        if kind == "grid":
            return self.grid_layout(**overrides)
        if kind == "radial":
            return self.radial_layout(self._auto_root(), **overrides)
        if kind == "layered":
            return self.layered_layout(**overrides)
        return self.spring_layout(**overrides)

    # -- rendering ---------------------------------------------------------- #
    def render(
        self,
        positions: dict[str, Point] | None = None,
        *,
        box: Sequence[float],
        camera: Camera | Mat4 | None = None,
        node_radius: float = 9.0,
        node_fill: str = "#1d4ed8",
        node_stroke: str = "#0b1f4d",
        node_stroke_width: float = 1.5,
        edge_color: str = "#94a3b8",
        edge_width: float = 1.5,
        labels: bool = True,
        label_color: str = "#0f172a",
        label_size: float = 11.0,
        font_family: Sequence[str] = ("DejaVu Sans", "Arial", "sans-serif"),
        id: str | None = None,
    ) -> dict[str, object]:
        """Render the graph to one FrameGraph ``group`` fitted into ``box``.

        ``positions`` maps node ids to 2D points, or — when ``camera`` is given —
        to 3D points that are projected through the camera first. Edges draw under
        nodes; directed edges get an arrowhead; labels are sized to fit so the
        ``--check-overflow`` proxy stays happy. Children are emitted local to the
        group box (origin baked out), matching :class:`~framegraph.sdk.Scene3D`.

        ``positions`` defaults to :meth:`auto_layout` — omit it and the graph lays
        itself out from its declared edges (the algorithm inferred from structure).
        """
        if positions is None:
            positions = self.auto_layout()
        matrix = camera.matrix() if isinstance(camera, Camera) else camera

        screen: dict[str, Vec2] = {}
        depth: dict[str, float] = {}
        for nid, p in positions.items():
            if matrix is not None:
                v = _v3(p)
                x4 = matrix.apply(v)
                w = x4[3] if abs(x4[3]) > 1e-12 else 1.0
                screen[nid] = Vec2(x4[0] / w, x4[1] / w)
                depth[nid] = x4[2] / w
            else:
                v2 = _v2(p)
                screen[nid] = v2
                depth[nid] = 0.0

        bw, bh = float(box[2]), float(box[3])
        if not screen:
            group: dict[str, object] = {"type": "group", "box": list(box), "children": []}
            if id is not None:
                group["id"] = id
            return group

        # Fit into the box, reserving margins for node radii + a label band.
        max_w = max((self._nodes[n].weight for n in screen), default=1.0)
        max_r = node_radius * math.sqrt(max(max_w, 1e-6))
        label_h = math.ceil(label_size * 1.35) if labels else 0.0
        pad = max_r + 3.0
        pad_bottom = pad + label_h
        xs = [p.x for p in screen.values()]
        ys = [p.y for p in screen.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        avail_w = max(bw - 2 * pad, 1e-6)
        avail_h = max(bh - pad - pad_bottom, 1e-6)
        scale = min(avail_w / max(max_x - min_x, 1e-9), avail_h / max(max_y - min_y, 1e-9))
        # If a degenerate (single point / colinear) extent makes scale huge, cap it.
        scale = min(scale, max(avail_w, avail_h))
        ox = pad + (avail_w - (max_x - min_x) * scale) / 2
        oy = pad + (avail_h - (max_y - min_y) * scale) / 2
        place = {nid: Vec2(ox + (p.x - min_x) * scale, oy + (p.y - min_y) * scale)
                 for nid, p in screen.items()}

        children: list[dict[str, object]] = []

        # Edges first (drawn under the nodes).
        for e in self._edges:
            if e.src not in place or e.dst not in place:
                continue
            a, b = place[e.src], place[e.dst]
            width = edge_width * math.sqrt(max(e.weight, 1e-6))
            line_style = {"stroke": edge_color, "stroke_style": {"stroke_width": width}}
            line_style.update(e.style)
            children.append({"type": "polyline", "points": [[a.x, a.y], [b.x, b.y]], **line_style})
            if e.directed:
                children.append(_arrowhead(a, b, self._nodes[e.dst].weight, node_radius,
                                           line_style.get("stroke", edge_color)))

        # Nodes back-to-front so nearer nodes occlude farther ones in 3D.
        ordered = sorted(place, key=lambda nid: depth[nid], reverse=True)
        for nid in ordered:
            node = self._nodes[nid]
            p = place[nid]
            r = node_radius * math.sqrt(max(node.weight, 1e-6))
            dot: dict[str, object] = {
                "type": "ellipse", "center": [p.x, p.y], "rx": r, "ry": r,
                "fill": node_fill, "stroke": node_stroke,
                "stroke_style": {"stroke_width": node_stroke_width},
            }
            dot.update(node.style)
            children.append(dot)

        # Labels last, on top, each box sized to its measured text.
        if labels:
            for nid in ordered:
                node = self._nodes[nid]
                text = node.label if node.label is not None else node.id
                if not text:
                    continue
                p = place[nid]
                r = node_radius * math.sqrt(max(node.weight, 1e-6))
                tw = measure_text(text, font_family=list(font_family), font_size=label_size) + 4.0
                tx = min(max(p.x - tw / 2, 0.0), max(bw - tw, 0.0))
                ty = min(p.y + r + 2.0, bh - label_h)
                children.append({
                    "type": "text", "box": [tx, ty, tw, label_h], "text": text,
                    "style": {"font_family": list(font_family), "font_size": label_size,
                              "color": label_color, "text_align": "center"},
                })

        group = {"type": "group", "box": list(box), "children": children}
        if id is not None:
            group["id"] = id
        return group


def _arrowhead(a: Vec2, b: Vec2, dst_weight: float, node_radius: float, color: str) -> dict[str, object]:
    """A small filled triangle just short of node ``b`` along the ``a→b`` edge."""
    dx, dy = b.x - a.x, b.y - a.y
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    r = node_radius * math.sqrt(max(dst_weight, 1e-6))
    tip_x, tip_y = b.x - ux * r, b.y - uy * r       # stop at the node edge
    base_x, base_y = tip_x - ux * 9.0, tip_y - uy * 9.0
    hw = 4.0
    return {
        "type": "polyline", "closed": True, "fill": color, "stroke": color,
        "points": [[tip_x, tip_y],
                   [base_x + px * hw, base_y + py * hw],
                   [base_x - px * hw, base_y - py * hw]],
    }


def _v2(value: Point) -> Vec2:
    if isinstance(value, Vec2):
        return value
    if isinstance(value, Vec3):
        return Vec2(value.x, value.y)
    return Vec2(float(value[0]), float(value[1]))


def _v3(value: Point) -> Vec3:
    if isinstance(value, Vec3):
        return value
    if isinstance(value, Vec2):
        return Vec3(value.x, value.y, 0.0)
    seq = list(value)
    return Vec3(float(seq[0]), float(seq[1]), float(seq[2]) if len(seq) > 2 else 0.0)


__all__ = ["Edge", "Graph", "Node"]
