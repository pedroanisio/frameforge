"""A stateful, session-persisted coordinate workspace — the AI's precise "mouse".

``measure`` and ``mark_points`` are stateless: each call is a pure function of its
inputs. Reconstructing a raster into vectors, though, is *iterative* — pin a few
anchors, look, nudge one 0.01 to the left, pin more, look again, refine over several
passes. That needs memory. This module holds that memory: a workspace bound to one
image, persisted as ``workspace.json`` in the MCP session dir, carrying a set of
named **pins** (anchor points, stored canonically in image pixels) and the current
**viewport** (a crop + zoom). Pins survive across tool calls, so they can be reused,
nudged, pinned in groups, and adjusted together or independently until the
reconstruction is pixel-accurate.

Everything geometric is delegated to :mod:`framegraph.vision.infrastructure.measure`
(coordinate systems, rulers/grid, zoom-aware crops, multi-frame point resolution), so
a pin reads out in every frame — full image, coordinate system, and viewport — exactly
like a measured point. Pins are anchored to the image, so a pin's coordinates never
change when the viewport pans or zooms: that is the "fixed aim / coordinate
continuity" the workspace guarantees.

⚠ PALS's LAW: pin coordinates are exact (they are just numbers the caller set or
nudged); the *overlay* is a drawing aid. Detected landmarks used as anchors are the
same UNVERIFIED hints as elsewhere.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .image_compare import Region, _font, _pil, load_rgb
from .measure import (
    CoordinateSystem,
    CropTransform,
    Landmark,
    Measurement,
    _draw_points,
    _Viewport,
    annotate,
    crop_transform,
    nice_step,
    point_frames,
    resolve_point_spec,
    structural_landmarks,
)

WORKSPACE_FILE = "workspace.json"
_TRUTHY_UNITS = ("norm", "px", "viewport")


@dataclass
class Pin:
    """A persisted anchor point, stored canonically in image pixels."""

    id: str
    x: float
    y: float
    group: str = ""
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "x": self.x, "y": self.y, "group": self.group, "label": self.label}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Pin":
        return cls(str(d["id"]), float(d["x"]), float(d["y"]),
                   str(d.get("group", "")), str(d.get("label", "")))


@dataclass
class WorkspaceState:
    """The persisted workspace: image binding, pins, viewport, id counter."""

    image_ref: str
    width: int
    height: int
    origin: str = "top-left"
    pins: list[Pin] = field(default_factory=list)
    viewport: tuple[float, float, float, float] | None = None
    viewport_name: str = "viewport"
    seq: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_ref": self.image_ref,
            "width": self.width,
            "height": self.height,
            "origin": self.origin,
            "pins": [p.to_dict() for p in self.pins],
            "viewport": list(self.viewport) if self.viewport else None,
            "viewport_name": self.viewport_name,
            "seq": self.seq,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "WorkspaceState":
        vp = d.get("viewport")
        return cls(
            image_ref=str(d["image_ref"]),
            width=int(d["width"]),
            height=int(d["height"]),
            origin=str(d.get("origin", "top-left")),
            pins=[Pin.from_dict(p) for p in d.get("pins", [])],
            viewport=tuple(float(v) for v in vp) if vp else None,
            viewport_name=str(d.get("viewport_name", "viewport")),
            seq=int(d.get("seq", 0)),
        )

    # -- coordinate helpers --------------------------------------------------
    def cs(self) -> CoordinateSystem:
        return CoordinateSystem(self.origin, self.width, self.height)

    def viewport_transform(self) -> CropTransform | None:
        if not self.viewport:
            return None
        return crop_transform(self.viewport_name, self.viewport, self.cs())

    def anchors(self) -> dict[str, Landmark]:
        """Structural anchors (A1..A9) plus every pin, keyed by id, for spec resolution."""
        cs = self.cs()
        out: dict[str, Landmark] = {lm.id: lm for lm in structural_landmarks(cs)}
        for p in self.pins:
            out[p.id] = Landmark(p.id, "pin", p.x, p.y, cs.to_cs(p.x, p.y), source="pin")
        return out


def load_state(session_dir: Path) -> WorkspaceState | None:
    path = session_dir / WORKSPACE_FILE
    if not path.is_file():
        return None
    return WorkspaceState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_state(session_dir: Path, state: WorkspaceState) -> None:
    (session_dir / WORKSPACE_FILE).write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# mutations
# ─────────────────────────────────────────────────────────────
def _select(state: WorkspaceState, select: Any) -> list[Pin]:
    """Resolve a selector to pins: None/'all' → all; {'ids': [...]}; {'group': g}."""
    if select in (None, "all", "*"):
        return list(state.pins)
    if isinstance(select, dict):
        if "ids" in select:
            want = {str(i) for i in select["ids"]}
            return [p for p in state.pins if p.id in want]
        if "group" in select:
            g = str(select["group"])
            return [p for p in state.pins if p.group == g]
    raise ValueError("select must be null/'all', {'ids': [...]}, or {'group': str}")


def add_pins(state: WorkspaceState, specs: Sequence[Any]) -> list[Pin]:
    """Resolve point specs (any frame; may reference existing pins) and add them."""
    cs = state.cs()
    vp = state.viewport_transform()
    added: list[Pin] = []
    for spec in specs:
        anchors = state.anchors()  # rebuilt so a spec can reference a just-added pin
        px, py = resolve_point_spec(spec, cs, anchors, vp)
        if isinstance(spec, dict) and spec.get("id"):
            pid = str(spec["id"])
        else:
            state.seq += 1
            pid = f"P{state.seq}"
        pin = Pin(pid, px, py,
                  str(spec.get("group", "")) if isinstance(spec, dict) else "",
                  str(spec.get("label", "")) if isinstance(spec, dict) else "")
        # replacing an existing id updates it in place (reuse / re-pin)
        state.pins = [p for p in state.pins if p.id != pid]
        state.pins.append(pin)
        added.append(pin)
    return added


def _delta_px(state: WorkspaceState, dx: float, dy: float, unit: str) -> tuple[float, float]:
    """Convert a nudge delta in the chosen unit to image pixels."""
    unit = unit if unit in _TRUTHY_UNITS else "norm"
    if unit == "px":
        return float(dx), float(dy)
    if unit == "viewport":
        vp = state.viewport_transform()
        if vp is None:
            raise ValueError("unit 'viewport' needs a viewport; set one first")
        # a viewport-fraction step, expressed in source pixels
        return float(dx) * vp.size_px[0], float(dy) * vp.size_px[1]
    return float(dx) * state.width, float(dy) * state.height  # norm


def nudge_pins(state: WorkspaceState, select: Any, dx: float, dy: float, unit: str) -> list[Pin]:
    """Move selected pins by a delta (the AI 'mouse': e.g. 0.01 norm left = dx=-0.01)."""
    ddx, ddy = _delta_px(state, dx, dy, unit)
    moved = _select(state, select)
    for p in moved:
        p.x += ddx
        p.y += ddy
    return moved


def move_pins(state: WorkspaceState, select: Any, to: Any) -> list[Pin]:
    """Set selected pins' absolute position to a single point spec."""
    cs = state.cs()
    vp = state.viewport_transform()
    px, py = resolve_point_spec(to, cs, state.anchors(), vp)
    moved = _select(state, select)
    for p in moved:
        p.x, p.y = px, py
    return moved


def remove_pins(state: WorkspaceState, select: Any) -> int:
    victims = {p.id for p in _select(state, select)}
    before = len(state.pins)
    state.pins = [p for p in state.pins if p.id not in victims]
    return before - len(state.pins)


def set_viewport(state: WorkspaceState, box: Sequence[float] | None, *, name: str = "viewport") -> None:
    if box is None:
        state.viewport = None
        return
    if len(box) != 4:
        raise ValueError("viewport box must be [x, y, w, h] normalized 0..1")
    state.viewport = tuple(float(v) for v in box)
    state.viewport_name = name


def pan_viewport(state: WorkspaceState, dnx: float, dny: float) -> None:
    if not state.viewport:
        raise ValueError("no viewport to pan; set one first")
    x, y, w, h = state.viewport
    state.viewport = (x + float(dnx), y + float(dny), w, h)


def zoom_viewport(state: WorkspaceState, factor: float, aim: Any = None) -> None:
    """Zoom the viewport by ``factor`` about an aim point (default: viewport centre).

    The aim is any point spec (a pin id via {"landmark": "P1"}, norm, px, ...); it
    stays centred, so the target the AI is inspecting does not drift — fixed aim.
    """
    if not state.viewport:
        raise ValueError("no viewport to zoom; set one first")
    if factor <= 0:
        raise ValueError("zoom factor must be > 0")
    x, y, w, h = state.viewport
    if aim is not None:
        ax, ay = resolve_point_spec(aim, state.cs(), state.anchors(), state.viewport_transform())
        cx, cy = ax / state.width, ay / state.height
    else:
        cx, cy = x + w / 2, y + h / 2
    nw, nh = w / factor, h / factor
    state.viewport = (cx - nw / 2, cy - nh / 2, nw, nh)


# ─────────────────────────────────────────────────────────────
# rendering
# ─────────────────────────────────────────────────────────────
def render(image_bytes: bytes, state: WorkspaceState, *,
           grid: bool = True, rulers: bool = True, connect: bool = False) -> Measurement:
    """Render the workspace: overlay with pins, an optional viewport crop, and spatial."""
    Image, _, ImageDraw, _, _ = _pil()
    img = load_rgb(image_bytes)
    cs = state.cs()
    step = nice_step(max(state.width, state.height))
    lms = structural_landmarks(cs)
    vp_xform = state.viewport_transform()
    pts = [(p.x, p.y, p.label or p.id) for p in state.pins]

    identity = _Viewport(0.0, 0.0, 1.0)
    base = annotate(img, cs, identity, step=step, label_every=2, grid=grid, rulers=rulers,
                    landmarks=lms, crops=(vp_xform,) if vp_xform else ())
    over = base.convert("RGBA")
    layer = Image.new("RGBA", over.size, (0, 0, 0, 0))
    _draw_points(ImageDraw.Draw(layer), pts, identity, connect=connect, font=_font(16, bold=True))
    overlay = Image.alpha_composite(over, layer).convert("RGB")

    crops: list[tuple[str, Any]] = []
    if vp_xform is not None:
        from .measure import _render_crop
        crop_view = _render_crop(img, cs, vp_xform, step, 2, grid, rulers, lms).convert("RGBA")
        clayer = Image.new("RGBA", crop_view.size, (0, 0, 0, 0))
        cvp = _Viewport(vp_xform.origin_px[0], vp_xform.origin_px[1], vp_xform.scale)
        _draw_points(ImageDraw.Draw(clayer), pts, cvp, connect=connect, font=_font(16, bold=True))
        crops.append((vp_xform.name, Image.alpha_composite(crop_view, clayer).convert("RGB")))

    pin_records = []
    for p in state.pins:
        rec = {"id": p.id, "group": p.group, "label": p.label}
        rec.update(point_frames(p.x, p.y, cs, vp_xform))
        pin_records.append(rec)

    spatial = {
        "image": {"width_px": state.width, "height_px": state.height},
        "coordinate_system": cs.describe(),
        "viewport": vp_xform.to_dict() if vp_xform else None,
        "pin_count": len(state.pins),
        "pins": pin_records,
        "reconstruction_hint": (
            "Pins persist across calls (reuse by id/group). Nudge in norm/px/viewport "
            "units to refine over passes; pins are image-anchored, so their coordinates "
            "hold as the viewport moves. Feed pins into construct_vectors to draw."
        ),
    }
    return Measurement(overlay=overlay, spatial=spatial, crops=crops)


def region_from_viewport(state: WorkspaceState) -> Region | None:
    if not state.viewport:
        return None
    return Region(state.viewport_name, state.viewport)
