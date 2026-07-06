"""framegraph.patterns — the declarative slide-template catalog (issue #28).

A bounded context in the §13 layout: 375 typed layout patterns + 17 fill
sidecars as committed data, a strict loader, and the ``{role: content}`` fill
contract. Rendering patterns into v2 pages is the #29 bridge and lives
elsewhere; nothing here touches the document schema.
"""
from framegraph.patterns.catalog import (
    Anchor,
    CATALOG_PATH,
    Catalog,
    EnterpriseLayout,
    Placement,
    PatternZone,
    RelativePlacement,
    SlidePattern,
    Span,
    load_catalog,
)
from framegraph.patterns.compose import CANVAS_H, CANVAS_W, DEFAULT_TOKENS, compose
from framegraph.patterns.fill import (
    FILLS_DIR,
    PatternFillSidecar,
    SidecarFieldSpec,
    SidecarZoneOverride,
    derive_fill_model,
    load_fill,
    load_sidecars,
)

__all__ = [
    "Anchor",
    "CANVAS_H",
    "CANVAS_W",
    "DEFAULT_TOKENS",
    "compose",
    "CATALOG_PATH",
    "Catalog",
    "EnterpriseLayout",
    "FILLS_DIR",
    "PatternFillSidecar",
    "Placement",
    "PatternZone",
    "RelativePlacement",
    "SidecarFieldSpec",
    "SidecarZoneOverride",
    "SlidePattern",
    "Span",
    "derive_fill_model",
    "load_catalog",
    "load_fill",
    "load_sidecars",
]
