#!/usr/bin/env python3
"""Every surface must report text collisions the same way.

A collision — unintended same-layer text-on-text ink — is now an ERROR-severity
health flag. It has to read the same through every door, or an author who
verifies through one door ships a defect another door would have caught:

  * CLI      `--to audit` → report["collisions"] + a `text-collision` health flag
  * SDK      `collision_report()` → records carrying enough to LOCATE the pair
  * MCP      `design_audit` → the same report, for a session's last render
  * MCP      every render result → the census health + a `render_warning`

The locatability requirement is load-bearing: `ids` are optional and generated
documents routinely omit them, so a record (and every message built from one)
must fall back to the text excerpts rather than saying "<anonymous> × <anonymous>".
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.application.audit import (  # noqa: E402
    audit_document, compact_census)
from frameforge_sdk import DocumentBuilder  # noqa: E402
from frameforge.conform import collision_report

_SANS = ["DejaVu Sans", "sans-serif"]


def _colliding_doc(with_ids: bool = False):
    """Two text blocks sharing the same y-band — the re-metro cover's defect."""
    b = DocumentBuilder(title="Collision Probe", profile="deck")
    p = b.page("p1", canvas={"size": [400, 200], "units": "px"})
    L = p.layer("main")
    L.rect([0, 0, 400, 200], fill="#ffffff")
    st = {"font_family": _SANS, "font_size": 14, "color": "#101418"}
    L.text([10, 10, 380, 60], "Source ledger", style=st,
           **({"id": "ledger"} if with_ids else {}))
    L.text([10, 20, 380, 60], "DISCLAIMER body", style=st,
           **({"id": "disclaimer"} if with_ids else {}))
    return b.build()


# --------------------------------------------------------------------------- #
#  SDK
# --------------------------------------------------------------------------- #
def test_sdk_collision_report_records_are_locatable():
    found = collision_report(_colliding_doc())
    assert found, "expected the overlapping text blocks to be reported"
    rec = found[0]
    # the documented record keys must all be present
    for key in ("ids", "page", "layer", "area", "overlap", "metrics", "boxes", "texts"):
        assert key in rec, f"collision record is missing {key!r}"
    assert rec["ids"] == [None, None]              # ids stay optional
    assert any("Source ledger" in t for t in rec["texts"])
    assert len(rec["boxes"]) == 2 and all(len(box) == 4 for box in rec["boxes"])


def test_sdk_collision_report_is_empty_for_a_clean_document():
    b = DocumentBuilder(title="Clean", profile="deck")
    p = b.page("p1", canvas={"size": [400, 200], "units": "px"})
    L = p.layer("main")
    L.text([10, 10, 380, 30], "one", style={"font_family": _SANS, "font_size": 12})
    L.text([10, 120, 380, 30], "two", style={"font_family": _SANS, "font_size": 12})
    assert collision_report(b.build()) == []


# --------------------------------------------------------------------------- #
#  Audit report (the CLI + MCP `design_audit` payload)
# --------------------------------------------------------------------------- #
def test_audit_flag_names_the_text_when_ids_are_absent():
    doc = _colliding_doc()
    collisions = collision_report(doc)
    report = audit_document(doc.model_dump(by_alias=True, exclude_none=True),
                            ["<svg></svg>"], collisions=collisions)
    flag = next(f for f in report["health"] if f["code"] == "text-collision")
    assert flag["level"] == "error"
    assert "anonymous" not in flag["message"]
    assert "Source ledger" in flag["message"]


def test_audit_flag_prefers_ids_when_they_exist():
    doc = _colliding_doc(with_ids=True)
    report = audit_document(doc.model_dump(by_alias=True, exclude_none=True),
                            ["<svg></svg>"], collisions=collision_report(doc))
    flag = next(f for f in report["health"] if f["code"] == "text-collision")
    assert "ledger" in flag["message"] and "disclaimer" in flag["message"]


# --------------------------------------------------------------------------- #
#  Compact census — what rides on EVERY MCP render result
# --------------------------------------------------------------------------- #
def test_compact_census_carries_the_collision_flag():
    doc = _colliding_doc()
    report = audit_document(doc.model_dump(by_alias=True, exclude_none=True),
                            ["<svg></svg>"], collisions=collision_report(doc))
    census = compact_census(report)
    assert "collisions" in census, "census must count collisions for the render result"
    assert census["collisions"] >= 1
    assert any(f["code"] == "text-collision" for f in census["health"])


def test_compact_census_reports_zero_when_clean():
    report = audit_document({"pages": []}, ["<svg></svg>"], collisions=[])
    assert compact_census(report)["collisions"] == 0


# --------------------------------------------------------------------------- #
#  MCP — the render result and the `design_audit` tool
# --------------------------------------------------------------------------- #
def _render(tmp_path, doc, session_id="collision-parity"):
    from frameforge_mcp.server import render_frameforge_yaml
    from frameforge_sdk.io import serialize
    return render_frameforge_yaml(serialize(doc, format="yaml"),
                                  session_id=session_id, session_root=tmp_path,
                                  raster_png=False)


def test_mcp_render_result_surfaces_the_collision(tmp_path):
    result = _render(tmp_path, _colliding_doc())
    assert result["ok"] is True, result.get("error")
    assert result["design"]["collisions"] >= 1
    assert result["diagnostics"]["collisions"], "diagnostics must carry the records"
    # the nag must LOCATE the pair, not print "<anonymous> × <anonymous>"
    warning = result.get("render_warning") or ""
    assert "collision" in warning
    assert "anonymous" not in warning
    assert "Source ledger" in warning


def test_mcp_design_audit_matches_the_cli_report(tmp_path):
    _render(tmp_path, _colliding_doc())
    from frameforge_mcp.server import design_audit
    audit = design_audit(session_id="collision-parity", session_root=tmp_path)
    assert audit["ok"] is True, audit.get("error")
    assert audit["audit"]["collisions"], "design_audit must report what the CLI reports"
    assert any(f["code"] == "text-collision" for f in audit["audit"]["health"])
    assert audit["design"]["collisions"] >= 1


def test_mcp_clean_document_reports_no_collisions(tmp_path):
    b = DocumentBuilder(title="Clean", profile="deck")
    p = b.page("p1", canvas={"size": [400, 200], "units": "px"})
    L = p.layer("main")
    L.text([10, 10, 380, 30], "one", style={"font_family": _SANS, "font_size": 12})
    L.text([10, 120, 380, 30], "two", style={"font_family": _SANS, "font_size": 12})
    result = _render(tmp_path, b.build(), session_id="collision-clean")
    assert result["design"]["collisions"] == 0
    assert "collision" not in (result.get("render_warning") or "")
