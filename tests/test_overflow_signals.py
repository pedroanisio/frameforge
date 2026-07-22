#!/usr/bin/env python3
"""test_overflow_signals.py — layout-time TYPED overflow signals.

Extends the issue-#44 lineage (per-object truncation records) into a typed,
first-class ``diagnostics["overflow"]`` channel emitted at layout/measure time
— before any pixels — closing the two blind spots the truncation records left:

  * ``overflow: visible`` spill was only an aggregate counter
    (``tstats["visible_overflow"]``) with no per-object record;
  * flow-mode overwide lines (an unbreakable word wider than the column) were
    priced inside the Knuth–Plass engine (badness 1e5+) but never reported.

The contract these tests pin:

  * TYPED — every signal is the dict form of the frozen dataclass
    ``OverflowSignal`` (rendering.domain.services.overflow): id, page, source
    (``text`` | ``flow``), kind (``width`` | ``height`` | ``lines``), policy,
    box [x,y,w,h], needed [w,h], acknowledged, detail.
  * COMPLETE — contained-policy clips signal alongside their truncation record;
    visible spill signals per object; flow overwide lines signal per line batch.
  * QUIET WHEN CLEAN — fitting text and healthy flow emit nothing; the channel
    always exists (empty list), so consumers never branch on key presence.
  * NON-DISRUPTIVE — tstats counters and ``truncations`` records are unchanged
    (regression guard on the existing surfaces).
  * PROPAGATED — the channel rides ``render_pages_with_stats(diagnostics=True)``,
    the ``sdk.conform.overflow_report()`` helper returns typed objects, the MCP
    render result carries it (warning names unacknowledged signals), and
    ``validate.py --text-fit`` surfaces flow/visible spill advisories.

Runs under pytest or standalone
(``uv run python tests/test_overflow_signals.py``).
"""
from __future__ import annotations

import dataclasses
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "tooling"), os.path.join(ROOT, "src"), ROOT]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from render_fixtures import Renderer                    # noqa: E402
from frameforge.rendering.domain.services.overflow import OverflowSignal  # noqa: E402
from frameforge.sdk.conform import overflow_report, render_pages_with_stats  # noqa: E402

LONG = ("A page works on the reader twice; once through its letters and once "
        "through its colour, and whatever third voice the designer admits.")
# No hyphens, no dictionary syllables: neither Knuth–Plass discretionaries nor
# pyphen may split it, so it MUST come out as one overwide line in a 120 px column.
UNBREAKABLE = "XF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEFX"


def _doc(text_obj):
    return {"dsl": "FrameForge", "version": "2.3.0", "title": "t",
            "pages": [{"mode": "page", "id": "p1",
                       "canvas": {"size": [400, 300], "units": "px"},
                       "layers": [{"id": "l1", "objects": [text_obj]}]}]}


def _flow_doc(paragraph_text):
    """A minimal flow section over a deliberately narrow (120 px) column."""
    return {"dsl": "FrameForge", "version": "2.3.0", "title": "t",
            "defs": {"masters": {
                "narrow": {"canvas": {"size": [400, 600], "units": "px"},
                           "regions": [{"id": "main", "box": [40, 40, 120, 500]}]}}},
            "pages": [{"mode": "flow", "id": "sec1", "master": "narrow",
                       "story": [{"type": "paragraph", "text": paragraph_text}]}]}


def _render(text_obj):
    doc = _doc(text_obj)
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    return r


# ── the typed signal itself ──────────────────────────────────────────────


def test_overflow_signal_is_a_frozen_dataclass_with_to_dict():
    assert dataclasses.is_dataclass(OverflowSignal)
    sig = OverflowSignal(id="x", page="p1", source="text", kind="width",
                         policy="visible", box=(0.0, 0.0, 10.0, 10.0),
                         needed=(20.0, 10.0), acknowledged=True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        sig.kind = "height"                             # type: ignore[misc]
    d = sig.to_dict()
    assert d["id"] == "x" and d["kind"] == "width"
    assert d["box"] == [0.0, 0.0, 10.0, 10.0] and d["needed"] == [20.0, 10.0]
    assert OverflowSignal.from_dict(d) == sig


# ── page-mode text: visible spill gets a per-object record ───────────────


def test_visible_spill_is_signalled_per_object():
    r = _render({"id": "spill", "type": "text", "box": [20, 20, 200, 18],
                 "text": LONG,
                 "style": {"font_size": 14, "line_height": 1.25,
                           "overflow": "visible"}})
    sigs = r.diagnostics["overflow"]
    assert len(sigs) == 1
    sig = sigs[0]
    assert sig["id"] == "spill" and sig["page"] == "p1"
    assert sig["source"] == "text" and sig["policy"] == "visible"
    assert sig["kind"] in ("width", "height")
    assert sig["box"] == [20, 20, 200, 18]
    needed_w, needed_h = sig["needed"]
    assert needed_w > 200 or needed_h > 18
    assert sig["acknowledged"] is True                  # visible was authored
    # regression: the aggregate counters and truncations are untouched
    assert r.tstats["visible_overflow"] == 1
    assert r.diagnostics["truncations"] == []


def test_contained_clip_signals_alongside_its_truncation_record():
    r = _render({"id": "lede", "type": "text", "box": [20, 20, 200, 18],
                 "text": LONG, "style": {"font_size": 14, "line_height": 1.25}})
    recs = r.diagnostics["truncations"]
    sigs = r.diagnostics["overflow"]
    assert len(recs) == 1 and len(sigs) == 1            # both channels, once each
    assert sigs[0]["id"] == recs[0]["id"] == "lede"
    assert sigs[0]["kind"] == recs[0]["kind"]
    assert sigs[0]["policy"] == "clip"
    assert sigs[0]["acknowledged"] is False             # silent containment default
    assert sigs[0]["source"] == "text"


def test_fitting_text_emits_no_signal_but_channel_exists():
    r = _render({"id": "ok", "type": "text", "box": [20, 20, 360, 260],
                 "text": "short and safe",
                 "style": {"font_size": 14, "line_height": 1.25}})
    assert r.diagnostics["overflow"] == []


# ── flow mode: overwide KP lines are reported, not just priced ───────────


def test_flow_overwide_line_is_signalled_once():
    doc = _flow_doc(f"before {UNBREAKABLE} after")
    _svgs, _tstats, diags = render_pages_with_stats(doc, diagnostics=True)
    sigs = [s for s in diags["overflow"] if s["source"] == "flow"]
    assert len(sigs) == 1                               # dry + real pass dedupe
    sig = sigs[0]
    assert sig["kind"] == "width"
    assert sig["page"] == "sec1"
    assert sig["acknowledged"] is False
    assert sig["needed"][0] > sig["box"][2] + 0.5       # line wider than column
    assert UNBREAKABLE[:24] in sig["detail"]            # names the culprit text


def test_healthy_flow_prose_emits_no_flow_signal():
    doc = _flow_doc("Short words wrap fine in a narrow column of prose.")
    _svgs, _tstats, diags = render_pages_with_stats(doc, diagnostics=True)
    assert [s for s in diags["overflow"] if s["source"] == "flow"] == []


# ── SDK propagation ──────────────────────────────────────────────────────


def test_overflow_report_returns_typed_signals():
    doc = _doc({"id": "spill", "type": "text", "box": [20, 20, 200, 18],
                "text": LONG,
                "style": {"font_size": 14, "line_height": 1.25,
                          "overflow": "visible"}})
    sigs = overflow_report(doc)
    assert len(sigs) == 1 and isinstance(sigs[0], OverflowSignal)
    assert sigs[0].id == "spill" and sigs[0].policy == "visible"


def test_overflow_report_empty_for_clean_document():
    doc = _doc({"id": "ok", "type": "text", "box": [20, 20, 360, 260],
                "text": "short and safe",
                "style": {"font_size": 14, "line_height": 1.25}})
    assert overflow_report(doc) == []


def test_flat_sdk_export():
    import frameforge.sdk as sdk
    assert sdk.OverflowSignal is OverflowSignal
    assert sdk.overflow_report is overflow_report
    assert "OverflowSignal" in sdk.__all__ and "overflow_report" in sdk.__all__


# ── MCP: signals inside the authoring loop ───────────────────────────────


def test_mcp_result_carries_overflow_and_warns_on_unacknowledged(tmp_path):
    import yaml as _yaml
    from frameforge.mcp.usecases import render_frameforge_yaml
    doc = _flow_doc(f"before {UNBREAKABLE} after")
    result = render_frameforge_yaml(_yaml.safe_dump(doc, sort_keys=False),
                                    session_id="ovf", session_root=tmp_path,
                                    raster_png=False)
    assert result["ok"] is True
    sigs = result["diagnostics"]["overflow"]
    assert any(s["source"] == "flow" for s in sigs)
    assert "overflow" in (result.get("render_warning") or "")


def test_mcp_acknowledged_visible_spill_does_not_warn(tmp_path):
    import yaml as _yaml
    from frameforge.mcp.usecases import render_frameforge_yaml
    doc = _doc({"id": "spill", "type": "text", "box": [20, 20, 200, 18],
                "text": LONG,
                "style": {"font_size": 14, "line_height": 1.25,
                          "overflow": "visible"}})
    result = render_frameforge_yaml(_yaml.safe_dump(doc, sort_keys=False),
                                    session_id="ovf2", session_root=tmp_path,
                                    raster_png=False)
    assert result["ok"] is True
    assert result["diagnostics"]["overflow"]            # recorded...
    assert "overflow signal" not in (result.get("render_warning") or "")  # ...not nagged


# ── CLI: validate --text-fit advisory tier ───────────────────────────────


def test_validate_text_fit_reports_layout_overflow(tmp_path):
    import subprocess
    import yaml as _yaml
    doc = _doc({"id": "spill", "type": "text", "box": [20, 20, 200, 18],
                "text": LONG,
                "style": {"font_size": 14, "line_height": 1.25,
                          "overflow": "visible"}})
    path = tmp_path / "spill.fg.yaml"
    path.write_text(_yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tooling", "validate.py"),
         str(path), "--text-fit"],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout + proc.stderr   # advisory tier
    assert "layout-overflow" in proc.stdout and "spill" in proc.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
