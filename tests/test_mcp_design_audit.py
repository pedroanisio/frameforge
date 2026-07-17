#!/usr/bin/env python3
"""MCP design-audit surface (refinements #1-#3 on the audit work).

The MCP is verification-first (PALS's Law): render-side signals must be visible on
the result. These tests pin three additions:
  #1  every render result carries a compact design-token census (`result["design"]`),
      and a sprawl doc surfaces a `render_warning` — like text-fit/truncations do;
  #3  a `design_audit` tool returns the FULL census for a session's last render;
  #2  the reserved-style contract (`body`/`caption`, ADR-0006) is documented in the
      `style` capability topic and the guide.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.mcp.server import (  # noqa: E402
    FRAMEFORGE_GUIDE,
    describe_capabilities,
    design_audit,
    read_session_resource,
    render_frameforge_yaml,
)
from frameforge.rendering.application.audit import compact_census  # noqa: E402
from frameforge.sdk import DocumentBuilder  # noqa: E402
from frameforge.sdk.io import serialize  # noqa: E402

_INTER = ["Inter", "sans-serif"]


def _clean_yaml() -> str:
    b = DocumentBuilder(title="Audit Probe", profile="deck")
    p = b.page("p1", canvas={"size": [320, 200], "units": "px"})
    L = p.layer("main")
    L.rect([0, 0, 320, 200], fill="#ffffff")
    L.text([20, 20, 280, 34], "Title", style={
        "font_family": _INTER, "font_size": 20, "font_weight": 700, "color": "#111827"})
    L.text([20, 70, 280, 20], "body text at one size", style={
        "font_family": _INTER, "font_size": 11, "color": "#374151"})
    return serialize(b.build(), format="yaml")


def _sprawl_yaml() -> str:
    b = DocumentBuilder(title="Sprawl Probe", profile="deck")
    p = b.page("p1", canvas={"size": [320, 400], "units": "px"})
    L = p.layer("main")
    L.rect([0, 0, 320, 400], fill="#ffffff")
    for i, size in enumerate([9, 10, 11, 12, 13, 14, 16, 18]):  # 8 distinct sizes → sprawl
        L.text([20, 20 + i * 40, 280, 30], f"line {i}", style={
            "font_family": _INTER, "font_size": size, "color": "#111827"})
    return serialize(b.build(), format="yaml")


# --------------------------------------------------------------------------- #
#  #1 — compact census on every render result                                 #
# --------------------------------------------------------------------------- #
def test_render_result_carries_design_census(tmp_path):
    r = render_frameforge_yaml(_clean_yaml(), session_id="census1",
                               session_root=tmp_path, raster_png=False)
    assert r["ok"] is True
    d = r["design"]
    assert set(d) >= {"faces", "sizes", "weights", "colours", "health"}
    assert d["faces"] == 1                      # one Inter chain
    assert d["sizes"] == 2                      # 20 + 11
    assert isinstance(d["health"], list) and d["health"]


def test_sprawl_render_surfaces_a_warning(tmp_path):
    r = render_frameforge_yaml(_sprawl_yaml(), session_id="census2",
                               session_root=tmp_path, raster_png=False)
    assert r["ok"] is True
    assert r["design"]["sizes"] >= 7
    codes = {f["code"] for f in r["design"]["health"]}
    assert "type-scale-sprawl" in codes
    # a sprawl warning must be visible on the result, not buried (PALS's Law)
    assert r.get("render_warning") and "design" in r["render_warning"].lower()


def test_compact_census_matches_helper_contract():
    fake = {
        "svg": {
            "font_family": {"n_distinct": 1}, "font_size_px": {"n_distinct": 3},
            "font_weight": {"n_distinct": 2},
            "text_color": {"distinct": ["#111", "#222"]},
            "shape_fill": {"distinct": ["#fff"]},
            "stroke_color": {"distinct": ["#222"]},   # dup with text → 3 unique
        },
        "health": [{"level": "ok", "code": "within-budget", "message": "-"}],
    }
    c = compact_census(fake)
    assert c == {"faces": 1, "sizes": 3, "weights": 2, "colours": 3,
                 "health": fake["health"]}


# --------------------------------------------------------------------------- #
#  #3 — the design_audit tool over a session's last render                     #
# --------------------------------------------------------------------------- #
def test_design_audit_tool_returns_full_report(tmp_path):
    render_frameforge_yaml(_clean_yaml(), session_id="da1",
                           session_root=tmp_path, raster_png=False)
    a = design_audit(session_id="da1", session_root=tmp_path)
    assert a["ok"] is True
    assert a["audit"]["svg"]["font_size_px"]["n_distinct"] == 2
    # full report carries the generic model walk (drift-proof feature census)
    assert "object_and_flow_types" in a["audit"]["model"]
    assert "text" in a["audit"]["model"]["object_and_flow_types"]
    assert isinstance(a["verdict"], str) and a["design"]["faces"] == 1


def test_design_audit_without_a_render_errors_clearly(tmp_path):
    a = design_audit(session_id="empty", session_root=tmp_path)
    assert a["ok"] is False and "render" in a["error"].lower()


def test_design_audit_persists_readable_resources(tmp_path):
    render_frameforge_yaml(_clean_yaml(), session_id="da2",
                           session_root=tmp_path, raster_png=False)
    a = design_audit(session_id="da2", session_root=tmp_path)
    uris = {r["uri"] for r in a["resources"]}
    assert any(u.endswith("audit.json") for u in uris)
    payload = read_session_resource("frameforge://session/da2/audit.json",
                                    session_root=tmp_path)
    assert payload["mimeType"] == "application/json"
    assert json.loads(payload["text"])["svg"]["font_family"]["n_distinct"] == 1


# --------------------------------------------------------------------------- #
#  #2 — reserved-style contract is documented                                 #
# --------------------------------------------------------------------------- #
def test_style_capability_topic_documents_reserved_styles():
    cap = describe_capabilities(topic="style")
    blob = json.dumps(cap).lower()
    assert "body" in blob and "caption" in blob and "adr-0006" in blob


def test_guide_documents_reserved_styles():
    g = FRAMEFORGE_GUIDE.lower()
    assert "body" in g and "caption" in g
    assert "reserved" in g or "no-injection" in g or "adr-0006" in g
