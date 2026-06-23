"""Box-geometry layout helpers for the FrameGraph SDK.

These are pure functions: given a container box and spacing, they return the
absolute child boxes that tile it. They compute coordinates only — nothing here
lowers to the model — so the results compose with every :class:`PageBuilder`
primitive and with the charting helpers in :mod:`framegraph.sdk.chart`.

There are two complementary ways to lay out a group in FrameGraph:

* **Renderer-arranged** — author a group with a ``layout`` and let the engine
  place children at draw time (it repositions only; children keep their authored
  width/height)::

      page.group(children, box=[x, y, w, h], layout={"kind": "row", "gap": 12})

* **Static** — resolve the child boxes up front with the functions here, so you
  keep full control of every coordinate. This is the path a slide deck or a
  chart panel wants, because the boxes feed directly into ``rect``/``text``/charts.

A box is ``[x, y, w, h]`` in page units. Padding follows the CSS convention used
by the renderer's layout engine: a scalar, ``[vertical, horizontal]``, or
``[top, right, bottom, left]``.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterator, Sequence

BoxLike = Sequence[float]
Pad = float | Sequence[float]


@dataclass(frozen=True)
class Box(Sequence[float]):
    """Author-friendly ``[x, y, w, h]`` wrapper.

    ``Box`` behaves like a four-item sequence, so it can be passed anywhere the
    SDK accepts a raw box list. Use :meth:`list` when a mutable/plain list is
    needed for assertions or handwritten object dicts.
    """

    x: float
    y: float
    w: float
    h: float

    @classmethod
    def from_xywh(cls, box: Sequence[float]) -> "Box":
        """Coerce any ``[x, y, w, h]`` sequence to a :class:`Box`."""
        x, y, w, h = _xywh(box)
        return cls(x, y, w, h)

    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def center(self) -> list[float]:
        return [self.x + self.w / 2, self.y + self.h / 2]

    def list(self) -> list[float]:
        """Return this box as a plain ``[x, y, w, h]`` list."""
        return [self.x, self.y, self.w, self.h]

    def inset(self, pad: Pad) -> "Box":
        """Return this box shrunk inward by ``pad``."""
        return Box.from_xywh(inset(self, pad))

    def move(self, dx: float = 0.0, dy: float = 0.0) -> "Box":
        """Return this box translated by ``dx``/``dy``."""
        return Box(self.x + dx, self.y + dy, self.w, self.h)

    def resize(self, w: float | None = None, h: float | None = None) -> "Box":
        """Return this box with a replaced width and/or height."""
        return Box(self.x, self.y, self.w if w is None else w, self.h if h is None else h)

    def row(
        self,
        count: int | None = None,
        *,
        gap: float = 0.0,
        pad: Pad = 0.0,
        weights: Sequence[float] | None = None,
    ) -> list["Box"]:
        """Split this box into horizontal child boxes."""
        return [Box.from_xywh(b) for b in row(self, count, gap=gap, pad=pad, weights=weights)]

    def column(
        self,
        count: int | None = None,
        *,
        gap: float = 0.0,
        pad: Pad = 0.0,
        weights: Sequence[float] | None = None,
    ) -> list["Box"]:
        """Split this box into vertical child boxes."""
        return [Box.from_xywh(b) for b in column(self, count, gap=gap, pad=pad, weights=weights)]

    def grid(
        self,
        *,
        cols: int,
        rows: int | None = None,
        count: int | None = None,
        gap: float = 0.0,
        row_gap: float | None = None,
        col_gap: float | None = None,
        pad: Pad = 0.0,
    ) -> list["Box"]:
        """Tile this box into a row-major grid of child boxes."""
        return [
            Box.from_xywh(b)
            for b in grid(
                self,
                cols=cols,
                rows=rows,
                count=count,
                gap=gap,
                row_gap=row_gap,
                col_gap=col_gap,
                pad=pad,
            )
        ]

    def __iter__(self) -> Iterator[float]:
        return iter((self.x, self.y, self.w, self.h))

    def __len__(self) -> int:
        return 4

    def __getitem__(self, index):
        return self.list()[index]


def inset(box: Sequence[float], pad: Pad) -> list[float]:
    """Return ``box`` shrunk inward by ``pad`` on each side."""
    x, y, w, h = _xywh(box)
    t, r, b, left = _pad4(pad)
    return [x + left, y + t, max(0.0, w - left - r), max(0.0, h - t - b)]


def row(
    box: Sequence[float],
    count: int | None = None,
    *,
    gap: float = 0.0,
    pad: Pad = 0.0,
    weights: Sequence[float] | None = None,
) -> list[list[float]]:
    """Split ``box`` into a horizontal strip of child boxes.

    Provide ``count`` for equal columns, or ``weights`` for proportional ones
    (e.g. ``weights=[2, 1]`` gives a 2:1 split). ``gap`` is the px space between
    children; ``pad`` insets the container first.
    """
    x, y, w, h = _xywh(inset(box, pad))
    ws = _weights(count, weights)
    inner = max(0.0, w - gap * (len(ws) - 1))
    total = sum(ws) or 1.0
    out: list[list[float]] = []
    cx = x
    for wi in ws:
        cw = inner * (wi / total)
        out.append([cx, y, cw, h])
        cx += cw + gap
    return out


def column(
    box: Sequence[float],
    count: int | None = None,
    *,
    gap: float = 0.0,
    pad: Pad = 0.0,
    weights: Sequence[float] | None = None,
) -> list[list[float]]:
    """Split ``box`` into a vertical stack of child boxes (see :func:`row`)."""
    x, y, w, h = _xywh(inset(box, pad))
    ws = _weights(count, weights)
    inner = max(0.0, h - gap * (len(ws) - 1))
    total = sum(ws) or 1.0
    out: list[list[float]] = []
    cy = y
    for wi in ws:
        ch = inner * (wi / total)
        out.append([x, cy, w, ch])
        cy += ch + gap
    return out


def grid(
    box: Sequence[float],
    *,
    cols: int,
    rows: int | None = None,
    count: int | None = None,
    gap: float = 0.0,
    row_gap: float | None = None,
    col_gap: float | None = None,
    pad: Pad = 0.0,
) -> list[list[float]]:
    """Tile ``box`` into a uniform ``cols``-wide grid, row-major.

    Give ``rows`` for a fixed grid, or ``count`` to size the grid to that many
    cells (rows are derived). ``gap`` sets both axes unless ``row_gap`` /
    ``col_gap`` override it.
    """
    if cols < 1:
        raise ValueError("grid() needs cols >= 1")
    if rows is None and count is None:
        raise ValueError("grid() needs either rows or count")
    cg = gap if col_gap is None else col_gap
    rg = gap if row_gap is None else row_gap
    n = count if count is not None else rows * cols  # type: ignore[operator]
    if rows is None:
        rows = max(1, math.ceil(n / cols))
    x, y, w, h = _xywh(inset(box, pad))
    cell_w = max(0.0, (w - (cols - 1) * cg) / cols)
    cell_h = max(0.0, (h - (rows - 1) * rg) / rows)
    out: list[list[float]] = []
    for i in range(n):
        c, r = i % cols, i // cols
        out.append([x + c * (cell_w + cg), y + r * (cell_h + rg), cell_w, cell_h])
    return out


# ---- internals ------------------------------------------------------------ #

def _xywh(box: Sequence[float]) -> tuple[float, float, float, float]:
    if len(box) < 4:
        raise ValueError(f"box must be [x, y, w, h]; got {box!r}")
    return (float(box[0]), float(box[1]), float(box[2]), float(box[3]))


def _weights(count: int | None, weights: Sequence[float] | None) -> list[float]:
    if weights is not None:
        ws = [float(x) for x in weights]
        if not ws:
            raise ValueError("weights must be non-empty")
        return ws
    if count is None:
        raise ValueError("provide either count or weights")
    if count < 1:
        raise ValueError("count must be >= 1")
    return [1.0] * count


def _pad4(pad: Pad) -> tuple[float, float, float, float]:
    """Resolve padding to (top, right, bottom, left), CSS-style."""
    if isinstance(pad, (int, float)) and not isinstance(pad, bool):
        v = float(pad)
        return (v, v, v, v)
    vals = [float(v) for v in pad]
    if len(vals) == 4:
        return (vals[0], vals[1], vals[2], vals[3])
    if len(vals) == 2:
        return (vals[0], vals[1], vals[0], vals[1])
    if len(vals) == 1:
        return (vals[0], vals[0], vals[0], vals[0])
    raise ValueError("pad must be a scalar or a list of 1, 2, or 4 values")


__all__ = ["Box", "BoxLike", "column", "grid", "inset", "row"]
