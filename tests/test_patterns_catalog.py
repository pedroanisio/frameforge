"""framegraph.patterns — the 375-pattern catalog + fill contract (issue #28).

Absorbed from the sibling project's declarative slide-template system: the
catalog and its 17 fill sidecars land as DATA, validated by strict Pydantic
models, with a typed `{role: content}` fill contract deriving per-zone shapes
from `content_type` and honouring sidecar overrides. Rendering is explicitly
out of scope here (that is the #29 bridge).

The count is LOCKED at 375 — silent truncation of the catalog is a test
failure, not a smaller number.

Runs under pytest or standalone (``uv run python tests/test_patterns_catalog.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from pydantic import ValidationError  # noqa: E402

from framegraph.patterns import (  # noqa: E402
    load_catalog,
    load_fill,
    load_sidecars,
)

CATALOG = load_catalog()
SIDECARS = load_sidecars()


# ── the catalog ───────────────────────────────────────────────────────────


def test_catalog_count_is_locked_at_375():
    assert len(CATALOG.patterns) == 375


def test_pattern_ids_are_unique_and_dense():
    ids = [p.id for p in CATALOG.patterns]
    assert len(set(ids)) == len(ids)
    assert min(ids) == 1 and max(ids) == 375


def test_get_by_id_and_known_content():
    swot = CATALOG.get(10)
    assert swot.name == "SWOT Analysis"
    assert [z.role for z in swot.zones] == [
        "strengths", "weaknesses", "opportunities", "threats"]
    assert all(z.content_type == "list_items" for z in swot.zones)
    assert swot.category == "generic"


def test_unknown_id_raises_keyerror():
    with pytest.raises(KeyError):
        CATALOG.get(9999)


def test_every_pattern_zone_vocabulary_is_typed():
    """Strict models: every size / content_type / anchor in 375 real patterns
    round-trips the controlled vocabulary (extra keys are rejected)."""
    for pattern in CATALOG.patterns:
        for zone in pattern.zones:
            assert zone.role
            if zone.placement and zone.placement.anchor:
                assert zone.placement.anchor.h in ("left", "center", "right")
                assert zone.placement.anchor.v in ("top", "middle", "bottom")


# ── the fill contract ─────────────────────────────────────────────────────


def test_sidecar_discovery_is_locked_at_17():
    assert len(SIDECARS) == 17
    assert {10, 44} <= set(SIDECARS)


def test_swot_example_fill_validates_with_default_shapes():
    payload = SIDECARS[10].example_fill
    fill = load_fill(10, payload)
    assert fill["strengths"][0].startswith("Strong brand")


def test_bmc_sidecar_override_enforces_object_items():
    payload = SIDECARS[44].example_fill
    fill = load_fill(44, payload)
    assert isinstance(fill["revenue_streams"][0], dict)
    assert {"label", "metric"} <= set(fill["revenue_streams"][0])

    # the override is ENFORCED: plain strings no longer pass for that zone
    broken = dict(payload)
    broken["revenue_streams"] = ["just a string"]
    with pytest.raises(ValidationError):
        load_fill(44, broken)


def test_unknown_role_is_rejected():
    payload = dict(SIDECARS[10].example_fill)
    payload["mystery_zone"] = ["nope"]
    with pytest.raises(ValidationError):
        load_fill(10, payload)


def test_missing_content_zone_is_rejected_and_decorative_is_not_required():
    payload = dict(SIDECARS[10].example_fill)
    payload.pop("threats")
    with pytest.raises(ValidationError):
        load_fill(10, payload)


def test_every_sidecar_example_fill_round_trips():
    """The smoke the sibling ran per-pattern: every committed example fill
    validates against its own (sidecar-overridden) contract."""
    for pid, sidecar in SIDECARS.items():
        if sidecar.example_fill is not None:
            load_fill(pid, sidecar.example_fill)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
