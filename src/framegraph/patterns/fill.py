"""The fill contract: a typed ``{role: content}`` payload per pattern.

Every zone's ``content_type`` implies a default Pydantic shape (a SWOT
quadrant is ``list[str]``, a metric is ``{label, value, trend?}``); a
**sidecar** under ``data/fills/`` may override a zone with richer item shapes
(the Business Model Canvas proof: ``revenue_streams`` items become
``{label, metric}`` objects) and carries a committed ``example_fill`` used as
the round-trip smoke. Validation is strict: unknown roles are rejected, and
every non-decorative content zone is required (issue #28).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, create_model

from framegraph.patterns.catalog import (
    DATA_DIR,
    Catalog,
    PatternZone,
    SlidePattern,
    load_catalog,
)

FILLS_DIR = DATA_DIR / "fills"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── default content shapes per content_type ──────────────────────────────


class TitleBody(_Strict):
    title: str
    body: Optional[str] = None


class Metric(_Strict):
    label: str
    value: str
    trend: Optional[str] = None


class Comparison(_Strict):
    left: str
    right: str


class ChartData(_Strict):
    type: str
    series: list[dict[str, Any]]


class TableData(_Strict):
    headers: list[str]
    rows: list[list[str]]


class ImageContent(_Strict):
    src: str
    alt: Optional[str] = None


class AxisLabel(_Strict):
    title: str
    units: Optional[str] = None


_DEFAULT_SHAPES: dict[str, Any] = {
    "title_body": TitleBody,
    "metric": Metric,
    "list_items": list[str],
    "key_value": dict[str, str],
    "comparison": Comparison,
    "chart_data": ChartData,
    "table_data": TableData,
    "image": ImageContent,
    "axis_label": AxisLabel,
    # `decorative` carries no content; `None` content_type accepts anything
}


# ── sidecars ─────────────────────────────────────────────────────────────


class SidecarFieldSpec(_Strict):
    type: str = "string"
    required: bool = False


class SidecarZoneOverride(_Strict):
    item_kind: str = Field(pattern="^(object|string)$")
    item_fields: Optional[dict[str, SidecarFieldSpec]] = None


class PatternFillSidecar(_Strict):
    pattern_id: int
    zones: dict[str, SidecarZoneOverride] = Field(default_factory=dict)
    example_fill: Optional[dict[str, Any]] = None


@lru_cache(maxsize=1)
def load_sidecars(fills_dir: str | Path = FILLS_DIR) -> dict[int, PatternFillSidecar]:
    """Every committed sidecar, keyed by pattern id, strictly validated."""
    out: dict[int, PatternFillSidecar] = {}
    for path in sorted(Path(fills_dir).glob("*.yml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        sidecar = PatternFillSidecar(**raw)
        out[sidecar.pattern_id] = sidecar
    return out


# ── the derived fill model ───────────────────────────────────────────────

_TYPE_MAP = {"string": str}


def _item_model(role: str, override: SidecarZoneOverride) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for name, spec in (override.item_fields or {}).items():
        py_type = _TYPE_MAP.get(spec.type, str)
        fields[name] = (py_type, ...) if spec.required else (Optional[py_type], None)
    return create_model(f"Fill_{role}_Item", __config__=ConfigDict(extra="forbid"),
                        **fields)


def _zone_annotation(zone: PatternZone,
                     override: SidecarZoneOverride | None) -> tuple[Any, Any]:
    if override is not None and override.item_kind == "object":
        return (list[_item_model(zone.role, override)], ...)
    shape = _DEFAULT_SHAPES.get(zone.content_type or "")
    if zone.content_type == "decorative":
        return (Optional[Any], None)
    if shape is None:                       # unannotated zone: accept anything
        return (Optional[Any], None)
    return (shape, ...)


def derive_fill_model(pattern: SlidePattern,
                      sidecar: PatternFillSidecar | None = None) -> type[BaseModel]:
    """The strict payload model for one pattern (sidecar overrides applied)."""
    overrides = (sidecar.zones if sidecar else {}) or {}
    fields = {z.role: _zone_annotation(z, overrides.get(z.role))
              for z in pattern.zones}
    return create_model(f"Fill_{pattern.id}", __config__=ConfigDict(extra="forbid"),
                        **fields)


def load_fill(pattern_id: int, payload: dict[str, Any], *,
              catalog: Catalog | None = None,
              sidecars: dict[int, PatternFillSidecar] | None = None) -> dict[str, Any]:
    """Validate a ``{role: content}`` payload for a pattern; returns the
    normalized plain dict. Raises ``pydantic.ValidationError`` on any unknown
    role, missing required zone, or item-shape mismatch."""
    pattern = (catalog or load_catalog()).get(pattern_id)
    sidecar = (sidecars if sidecars is not None else load_sidecars()).get(pattern_id)
    model = derive_fill_model(pattern, sidecar)
    return model(**payload).model_dump(exclude_none=True)


__all__ = ["FILLS_DIR", "PatternFillSidecar", "SidecarFieldSpec",
           "SidecarZoneOverride", "derive_fill_model", "load_fill",
           "load_sidecars"]
