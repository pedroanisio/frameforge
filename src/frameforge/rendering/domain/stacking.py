"""The ONE per-object stacking key, shared by every paint-order site.

The model declares two per-object stacking controls with near-identical
wording — `ObjBase.z` (model.py, "Stacking order within the layer") and
`Style.z_index` ("Stacking order within the parent") — and before this module
each backend honored a different one: the SVG renderer only `style.z_index`
(`ObjBase.z` was dead), the pdf-tex `FigureTikz` walker only `o["z"]`, the HTML
backend neither. Same document, different stacking per backend.

Precedence (the contract, stated in both model field descriptions and the
spec): the object-level `z` wins over `style.z_index`; default 0.0; sorts are
STABLE so objects declaring neither keep document order and emitted bytes are
unchanged. Declaring both with different values is reported by the renderer as
a `z_conflict` warning — the precedence is deterministic, never silent.
"""
from __future__ import annotations

from frameforge.rendering.domain.geometry import num


def effective_z(obj: dict, style: dict | None = None) -> float:
    """Stacking sort key for one object: `obj['z']`, else `style['z_index']`, else 0.

    `style` is the object's RESOLVED style dict (callers that can dereference
    token-ref styles pass the resolution; callers that cannot pass the inline
    dict via `inline_effective_z`)."""
    if not isinstance(obj, dict):
        return 0.0
    z = obj.get("z")
    if z is not None:
        return num(z, 0) or 0.0
    zi = (style or {}).get("z_index")
    return num(zi, 0) or 0.0


def inline_effective_z(obj: dict) -> float:
    """`effective_z` for walkers without a style-ref resolver (FigureTikz, the
    HTML backend): honors inline `style` dicts; token-ref styles fall back to
    `obj['z']`/0 — the documented limitation of those backends."""
    if not isinstance(obj, dict):
        return 0.0
    style = obj.get("style")
    return effective_z(obj, style if isinstance(style, dict) else None)


def z_conflict(obj: dict, style: dict | None = None):
    """`(z, z_index)` when the object declares BOTH with different values —
    the renderer turns this into a `z_conflict` warning — else None."""
    if not isinstance(obj, dict):
        return None
    z = obj.get("z")
    zi = (style or {}).get("z_index")
    if z is None or zi is None:
        return None
    zf, zif = num(z, 0) or 0.0, num(zi, 0) or 0.0
    return (z, zi) if zf != zif else None
