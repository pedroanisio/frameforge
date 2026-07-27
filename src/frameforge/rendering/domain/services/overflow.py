"""Layout-time typed overflow signals (the issue-#44 lineage, typed).

The per-object truncation records named what the containment net *discarded*;
this module types the broader family of layout overflow — everything the
measure pass can prove will not fit its box, whether it is then clipped,
shrunk, or allowed to spill — so every surface (renderer diagnostics, SDK
``overflow_report``, MCP result, ``validate.py --text-fit``) speaks one schema
instead of ad-hoc dicts.

A signal is emitted at layout/measure time, before any pixels, and never
alters the rendered bytes. The wire form is ``to_dict()`` (plain JSON-safe
dicts inside ``diagnostics["overflow"]``); ``from_dict`` restores the typed
value for SDK consumers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

__all__ = ["OverflowSignal"]


@dataclass(frozen=True)
class OverflowSignal:
    """One provable does-not-fit event, named at layout time.

    Fields:
      * ``id`` / ``page`` — the offending object id (or ``None`` for anonymous
        flow content) and the page/section id it lays out on.
      * ``source`` — ``"text"`` (an absolute text object's fit contract) or
        ``"flow"`` (the Knuth–Plass engine emitted a line wider than its
        column — priced internally as badness 1e5+ but previously unreported).
      * ``kind`` — the failing dimension: ``"width"``, ``"height"``, or
        ``"lines"`` (line-count clamp dropped content).
      * ``policy`` — the effective overflow policy that handled the excess
        (``"visible"``, ``"clip"``, ``"hidden"``, ``"shrink_to_fit"``, ...)
        or ``"flow"`` for flow-mode signals (flow never clips; it spills).
      * ``box`` — the authored/layout box ``(x, y, w, h)`` the content had.
      * ``needed`` — the laid-out extent ``(w, h)`` at the authored box width:
        width is the widest post-wrap line; height includes lines later clipped.
      * ``unwrapped_width`` — the single-line/pre-wrap width before line
        breaking, when meaningful. This is the width an author needs to prevent
        wrapping; it may exceed the box even when ``needed[0]`` does not.
      * ``acknowledged`` — the author explicitly chose an overflow behaviour
        (``overflow`` / ``text_overflow`` / ``max_lines``); ``False`` marks a
        silent default the author never opted into.
      * ``detail`` — a short head of the offending text, when known.
    """

    id: Optional[str]
    page: Optional[str]
    source: str
    kind: str
    policy: str
    box: tuple[float, float, float, float]
    needed: tuple[float, float]
    acknowledged: bool
    detail: str = field(default="")
    # Appended after the original positional fields so older Python callers
    # that passed ``detail`` positionally retain their meaning.
    unwrapped_width: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """The JSON-safe wire form used in ``diagnostics["overflow"]``."""
        return {
            "id": self.id,
            "page": self.page,
            "source": self.source,
            "kind": self.kind,
            "policy": self.policy,
            "box": [float(v) for v in self.box],
            "needed": [float(v) for v in self.needed],
            "unwrapped_width": (float(self.unwrapped_width)
                                if self.unwrapped_width is not None else None),
            "acknowledged": bool(self.acknowledged),
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OverflowSignal":
        """Restore a typed signal from its ``to_dict`` wire form."""
        return cls(
            id=data.get("id"),
            page=data.get("page"),
            source=str(data.get("source", "")),
            kind=str(data.get("kind", "")),
            policy=str(data.get("policy", "")),
            box=tuple(float(v) for v in (data.get("box") or (0, 0, 0, 0))[:4]),
            needed=tuple(float(v) for v in (data.get("needed") or (0, 0))[:2]),
            acknowledged=bool(data.get("acknowledged")),
            unwrapped_width=(float(data["unwrapped_width"])
                             if data.get("unwrapped_width") is not None else None),
            detail=str(data.get("detail", "")),
        )
