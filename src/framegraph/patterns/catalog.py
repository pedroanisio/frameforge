"""The slide-pattern catalog — 375 typed layout templates, loaded as data.

Absorbed from the sibling project (issue #28): each pattern declares zones
(role, controlled size vocabulary, placement, ``content_type``) plus a
hand-tuned ``enterprise_layout``. The catalog is DATA under ``data/patterns/``;
these models are the strict contract it must satisfy — the count is locked by
the test gate, so a silently truncated catalog fails instead of shrinking.

Rendering a pattern into v2 pages is the #29 bridge, deliberately out of
scope here.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

DATA_DIR = Path(__file__).resolve().parent / "data"
CATALOG_PATH = DATA_DIR / "patterns" / "slides-pattern-a.yml"

Size = Literal["xs", "small", "medium", "large", "xl", "full", "equal",
               "variable", "contextual"]
ContentType = Literal["title_body", "metric", "list_items", "key_value",
                      "comparison", "chart_data", "table_data", "image",
                      "axis_label", "decorative"]
Category = Literal["generic", "consulting", "expert"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Anchor(_Strict):
    """A 9-cell grid position."""

    h: Literal["left", "center", "right"]
    v: Literal["top", "middle", "bottom"]


class RelativePlacement(_Strict):
    """Position relative to another zone."""

    relation: str
    target: str


class Placement(_Strict):
    """Exactly one of: a grid anchor, a named region, or a relative position."""

    anchor: Optional[Anchor] = None
    region: Optional[str] = None
    relative: Optional[RelativePlacement] = None


class Span(_Strict):
    h: Optional[int] = None
    v: Optional[int] = None


class PatternZone(_Strict):
    role: str
    size: Size
    placement: Optional[Placement] = None
    content_type: Optional[ContentType] = None
    shape: Optional[str] = None
    span: Optional[Span] = None


class EnterpriseLayout(_Strict):
    """Hand-tuned absolute boxes + typography for a 1920×1080 canvas. The
    inner treatment/typography bags are intentionally open dictionaries —
    they are style data, not contract."""

    notes: Optional[str] = None
    canvas_overrides: Optional[dict[str, Any]] = None
    zones: Optional[dict[str, dict[str, Any]]] = None


class SlidePattern(_Strict):
    id: int = Field(ge=1)
    name: str
    layout_disposition: str
    zones: list[PatternZone]
    category: Optional[Category] = None
    use_case: Optional[str] = None
    enterprise_layout: Optional[EnterpriseLayout] = None

    def zone(self, role: str) -> PatternZone:
        for z in self.zones:
            if z.role == role:
                return z
        raise KeyError(f"pattern {self.id} has no zone {role!r}")


class Catalog(_Strict):
    patterns: list[SlidePattern]

    def get(self, pattern_id: int) -> SlidePattern:
        for p in self.patterns:
            if p.id == pattern_id:
                return p
        raise KeyError(f"no pattern with id {pattern_id} "
                       f"(catalog holds {len(self.patterns)})")


@lru_cache(maxsize=1)
def load_catalog(path: str | Path = CATALOG_PATH) -> Catalog:
    """Load and strictly validate the committed pattern catalog."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return Catalog(patterns=raw.get("slide_template_patterns") or [])


__all__ = ["Anchor", "Catalog", "ContentType", "EnterpriseLayout", "Placement",
           "PatternZone", "RelativePlacement", "Size", "SlidePattern", "Span",
           "CATALOG_PATH", "DATA_DIR", "load_catalog"]
