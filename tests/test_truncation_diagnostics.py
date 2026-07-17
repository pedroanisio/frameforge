"""Per-object truncation diagnostics — nothing silent about content loss.

Closes issue #44: the text-fit containment ("clip/ellipsis net") discarded
content while every surface reported success — an aggregate `clipped` count
with no names. These tests pin the new contract:

- the RENDERER records every content-losing text object in
  ``diagnostics["truncations"]`` — id, box, lines kept/dropped, the head of
  the dropped text, and whether the clip was **acknowledged** (the author
  explicitly opted in via `overflow`/`text_overflow: ellipsis`/`max_lines`)
  or silent (the containment default);
- ``render_fixtures --check-overflow`` NAMES the objects and its strict mode
  fails on unacknowledged loss;
- the MCP render result carries the records (and its warning names ids), so
  an authoring agent sees the loss inside the loop;
- ``validate.py --text-fit`` surfaces the same records as advisory WARNs.

Runs under pytest or standalone
(``uv run python tests/test_truncation_diagnostics.py``).
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "tooling"), os.path.join(ROOT, "src"), ROOT]

from render_fixtures import Renderer  # noqa: E402

LONG = ("A page works on the reader twice; once through its letters and once "
        "through its colour, and whatever third voice the designer admits.")


def _doc(text_obj):
    return {"dsl": "FrameForge", "version": "2.3.0", "title": "t",
            "pages": [{"mode": "page", "id": "p1",
                       "canvas": {"size": [400, 300], "units": "px"},
                       "layers": [{"id": "l1", "objects": [text_obj]}]}]}


def _render(text_obj):
    doc = _doc(text_obj)
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    return r


# ── the renderer names what it drops ─────────────────────────────────────


def test_silent_line_clip_is_recorded_with_dropped_text():
    r = _render({"id": "lede", "type": "text", "box": [20, 20, 200, 18],
                 "text": LONG, "style": {"font_size": 14, "line_height": 1.25}})
    recs = r.diagnostics["truncations"]
    assert len(recs) == 1
    rec = recs[0]
    assert rec["id"] == "lede" and rec["page"] == "p1"
    assert rec["lines_dropped"] >= 1 and rec["lines_kept"] >= 1
    assert rec["dropped_text"] and rec["dropped_text"] in LONG
    assert rec["acknowledged"] is False       # containment default = silent
    # records are the MATERIAL-loss subset of the aggregate clip count
    assert 1 <= len(recs) <= r.tstats["clipped"]


def test_explicit_optin_is_acknowledged():
    r = _render({"id": "teaser", "type": "text", "box": [20, 20, 200, 40],
                 "text": LONG,
                 "style": {"font_size": 14, "line_height": 1.25, "max_lines": 2,
                           "text_overflow": "ellipsis"}})
    recs = r.diagnostics["truncations"]
    assert len(recs) == 1 and recs[0]["acknowledged"] is True


def test_fitting_text_produces_no_record():
    r = _render({"id": "ok", "type": "text", "box": [20, 20, 360, 260],
                 "text": "short and safe", "style": {"font_size": 14, "line_height": 1.25}})
    assert r.diagnostics["truncations"] == []
    assert r.tstats["clipped"] == 0


def test_cosmetic_descender_trim_is_not_content_loss():
    """A box a hair shorter than the line leaves the clip-path (aggregate
    still counts it) but names nothing: no line was dropped, no glyph cut."""
    r = _render({"id": "snug", "type": "text", "box": [20, 20, 360, 18],
                 "text": "one comfortable line", "style": {"font_size": 14, "line_height": 1.25}})
    assert r.diagnostics["truncations"] == []


def test_single_line_width_clip_is_recorded():
    r = _render({"id": "label", "type": "text", "box": [20, 20, 60, 18],
                 "text": "UNBREAKABLE-IDENTIFIER-WIDER-THAN-BOX",
                 "style": {"font_size": 14, "white_space": "nowrap"}})
    recs = r.diagnostics["truncations"]
    assert len(recs) == 1 and recs[0]["kind"] == "width"


# ── the overflow gate names them and can fail on silent loss ─────────────


def test_overflow_report_names_objects_and_strict_fails():
    from render_fixtures import truncation_report
    r = _render({"id": "lede", "type": "text", "box": [20, 20, 200, 18],
                 "text": LONG, "style": {"font_size": 14, "line_height": 1.25}})
    lines, unacknowledged = truncation_report({"doc.fg.yaml": r.diagnostics["truncations"]})
    joined = "\n".join(lines)
    assert "lede" in joined and "doc.fg.yaml" in joined
    assert unacknowledged == 1                # strict mode fails on this


# ── MCP: the loss is visible inside the authoring loop ───────────────────


def test_mcp_render_result_carries_truncations(tmp_path):
    import yaml as _yaml
    from frameforge.mcp.usecases import render_frameforge_yaml
    doc = _doc({"id": "lede", "type": "text", "box": [20, 20, 200, 18],
                "text": LONG, "style": {"font_size": 14, "line_height": 1.25}})
    result = render_frameforge_yaml(_yaml.safe_dump(doc, sort_keys=False),
                                    session_id="trunc", session_root=tmp_path,
                                    raster_png=False)
    assert result["ok"] is True
    recs = result["diagnostics"]["truncations"]
    assert recs and recs[0]["id"] == "lede"
    assert "lede" in (result.get("render_warning") or "")


# ── validate --text-fit: the advisory WARN tier ──────────────────────────


def test_validate_text_fit_warns_per_object(tmp_path):
    # validate.py owns the model-vs-package import dance, so it is exercised
    # the way the gate runs it: as its own process.
    import subprocess
    import yaml as _yaml
    doc = _doc({"id": "lede", "type": "text", "box": [20, 20, 200, 18],
                "text": LONG, "style": {"font_size": 14, "line_height": 1.25}})
    path = tmp_path / "trunc.fg.yaml"
    path.write_text(_yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tooling", "validate.py"),
         str(path), "--text-fit"],
        capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout + proc.stderr   # advisory, not an error
    assert "text-truncated" in proc.stdout and "lede" in proc.stdout
    assert "SILENT content loss" in proc.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
