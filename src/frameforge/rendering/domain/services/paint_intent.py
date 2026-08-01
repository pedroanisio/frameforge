"""Paint-intent signals — "the author asked for ink; the engine painted otherwise".

The other three render channels report what a render *lost* (``truncations``,
``overflow``), what it *collided* (``collisions``), and what it *kept but made
unreadable* (``legibility``). This module reports the fourth failure mode: the
authored appearance was discarded, and the engine either substituted its own
default or painted nothing at all.

  * ``inert-stroke-declaration``  stroke intent written in style keys that are
                                  not read as stroke on that object type;
  * ``invisible-shape``           the shape resolved to no fill AND no stroke —
                                  it emits geometry and paints zero ink;
  * ``injected-stroke-default``   the engine substituted its fallback stroke for
                                  paint the document never declared.

THE DEFECT THIS EXISTS TO CATCH
-------------------------------
Found in the wild (2026-07-31, the tile-object concept spec)::

    {type: line,     style: {color: '#d5d0c6', width: 1}}  ->  stroke="#000" width=1
    {type: polyline, style: {color: '#6b757e', width: 1}}  ->  fill="none", NO STROKE

Both are schema-legal: :class:`~frameforge.model.Style` really does carry
``color``, ``width`` and ``dash`` fields. But on a stroke-painted shape
``Style.color`` is *text* colour, ``Style.width`` is *box* width and
``Style.dash`` is unrelated to ``stroke_dasharray`` — none of them is stroke
paint. The P3 single form put paint in ``stroke`` and geometry in
``stroke_style``; a document that keeps the pre-P3 bundle shape inside ``style``
passes every gate and still loses its appearance.

``line`` then falls back to ``Stroke("#000", 1)`` — wrong colour *and* wrong
weight, but visible, so it survives review. ``polyline``/``polygon``/``path``/
``curve`` have no fallback: ``fill="none"`` with no stroke paints nothing, and
the object is invisible while remaining present in model, validation and SVG.

TWO SURFACES, AN HONEST SPLIT (measured, not assumed)
-----------------------------------------------------
:func:`inert_stroke_keys` is *static*: it needs only the object and its resolved
style bag, so ``tooling/validate.py`` runs it with no render. Measured over the
committed fixture corpus it fires **0** times — it is precise enough to gate.

Invisibility is *not* statically decidable. A shape can take paint from a
group-inherited style, a token, a stroke-outline lowering, or a fill resolved
from a pattern; a static guess at "unfilled and unstroked" flagged **124**
objects in the same corpus, none of which actually rendered blank. So
``invisible-shape`` and ``injected-stroke-default`` are decided at the one place
that knows the answer — the renderer, after fill and stroke are resolved — and
ride ``diagnostics["paint"]``.

NO GUESSING (PALS's Law)
------------------------
``dimension`` reads its own ``style`` as a *text* style (``dimension_renderer``
draws the measurement label from it), so ``color`` genuinely applies there. It
is excluded from :data:`STROKE_PAINTED_TYPES` rather than misreported.

OBSERVE, NEVER MUTATE
---------------------
This channel changes no rendered byte. The substitutions above are long-standing
behaviour that the golden corpus depends on; the fix for a signalled document is
to author the paint correctly (``tooling/codemod.py --fix-inert-stroke`` does it
mechanically), not for the engine to start guessing differently.

The wire form is ``to_dict()`` (JSON-safe dicts inside ``diagnostics["paint"]``);
``from_dict`` restores the typed value for SDK consumers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

__all__ = [
    "INERT_STROKE_KEYS",
    "PaintSignal",
    "STROKE_PAINTED_TYPES",
    "inert_stroke_keys",
    "remedy_for",
]


#: Object types whose visible ink is the stroke, and which never read `color`/
#: `width`/`dash` from their own style bag. `dimension` is deliberately absent:
#: it renders its measurement label from `style`, so `color` applies there.
STROKE_PAINTED_TYPES: frozenset[str] = frozenset({
    "line", "polyline", "polygon", "path", "curve", "bezier", "connector",
})

#: Style keys that carry the shape of the pre-P3 stroke bundle and validate as
#: unrelated CSS properties. `opacity` is excluded — it is a real, read key.
INERT_STROKE_KEYS: tuple[str, ...] = ("color", "width", "dash")

#: The style/object keys that DO declare stroke paint or geometry. Any of these
#: means the author used a read form and the rule must stay silent.
_DECLARED_STROKE_KEYS: tuple[str, ...] = (
    "stroke", "stroke_style", "stroke_width", "stroke_dasharray",
    "stroke_linecap", "stroke_linejoin", "stroke_opacity", "border",
)

#: `INERT_STROKE_KEYS` -> the P3 spelling that actually paints.
_REMEDY_KEYS = {"color": "stroke", "width": "stroke_width", "dash": "stroke_dasharray"}


@dataclass(frozen=True)
class PaintSignal:
    """One paint-intent event: what was authored vs. what was painted.

    Fields:
      * ``id`` / ``page`` — the offending object id (``None`` when anonymous)
        and the page id it draws on.
      * ``type`` — the object type, so a consumer can group by shape family.
      * ``code`` — ``"inert-stroke-declaration"``, ``"invisible-shape"`` or
        ``"injected-stroke-default"``.
      * ``level`` — ``"warn"`` for the two authoring defects; ``"info"`` for a
        bare substitution the author may well have intended.
      * ``declared`` — the authored key/value evidence (e.g.
        ``{"color": "#d5d0c6", "width": 1}``), empty when nothing was declared.
      * ``substituted`` — what the engine actually painted (e.g.
        ``{"stroke": "#000", "stroke_width": 1.0}``, or
        ``{"fill": "none", "stroke": None}`` for an invisible shape).
      * ``remedy`` — the exact P3 spelling that paints what was asked for.
      * ``detail`` — a one-line human explanation.
    """

    id: Optional[str]
    page: Optional[str]
    type: str
    code: str
    level: str
    declared: dict[str, Any]
    substituted: dict[str, Any]
    remedy: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe wire form (the shape stored in ``diagnostics['paint']``)."""
        return {
            "id": self.id,
            "page": self.page,
            "type": self.type,
            "code": self.code,
            "level": self.level,
            "declared": dict(self.declared),
            "substituted": dict(self.substituted),
            "remedy": self.remedy,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PaintSignal":
        """Restore the typed value from :meth:`to_dict`."""
        return cls(
            id=d.get("id"),
            page=d.get("page"),
            type=d.get("type", ""),
            code=d.get("code", ""),
            level=d.get("level", "warn"),
            declared=dict(d.get("declared") or {}),
            substituted=dict(d.get("substituted") or {}),
            remedy=d.get("remedy", ""),
            detail=d.get("detail", ""),
        )


def _declares_stroke(obj: Any, style: Any) -> bool:
    """True when stroke paint/geometry is declared in any form the engine reads."""
    obj = obj if isinstance(obj, dict) else {}
    style = style if isinstance(style, dict) else {}
    if obj.get("stroke") is not None or obj.get("stroke_style") is not None:
        return True
    return any(style.get(k) is not None for k in _DECLARED_STROKE_KEYS)


def inert_stroke_keys(obj: Any, style: Any) -> tuple[str, ...]:
    """The style keys that read as stroke intent but are not stroke on `obj`.

    Static and exact: `obj` is the raw object dict and `style` its *resolved*
    style bag (token refs already dereferenced by the caller). Returns the
    present :data:`INERT_STROKE_KEYS` in declaration order, or ``()`` when the
    object is not stroke-painted, declares its stroke in a read form, or carries
    none of the keys.
    """
    obj = obj if isinstance(obj, dict) else {}
    style = style if isinstance(style, dict) else {}
    if obj.get("type") not in STROKE_PAINTED_TYPES:
        return ()
    if _declares_stroke(obj, style):
        return ()
    return tuple(k for k in INERT_STROKE_KEYS if style.get(k) is not None)


def remedy_for(style: Any, keys: tuple[str, ...]) -> str:
    """The P3 spelling that paints what `keys` were reaching for.

    ``{'color': '#d5d0c6', 'width': 1}`` becomes
    ``stroke: '#d5d0c6' + stroke_style: {stroke_width: 1}`` — copy-pasteable,
    because an authoring agent that mis-spelled it once will mis-spell the fix.
    """
    style = style if isinstance(style, dict) else {}
    paint = style.get("color") if "color" in keys else None
    geometry = {_REMEDY_KEYS[k]: style[k] for k in keys if k != "color" and k in style}
    parts = []
    if paint is not None:
        parts.append(f"stroke: {paint!r}")
    if geometry:
        body = ", ".join(f"{k}: {v!r}" for k, v in geometry.items())
        parts.append(f"stroke_style: {{{body}}}")
    if not parts:                                    # pragma: no cover — keys non-empty
        return "declare paint in `stroke` and geometry in `stroke_style`"
    return " + ".join(parts)
