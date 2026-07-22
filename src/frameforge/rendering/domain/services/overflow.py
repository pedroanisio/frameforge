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
      * ``needed`` — the measured extent ``(w, h)`` the content actually
        requires.
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
            detail=str(data.get("detail", "")),
        )
