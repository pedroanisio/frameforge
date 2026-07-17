#!/usr/bin/env python3
"""Session render history + diff_renders — convergence you can measure (F4).

Every render used to overwrite page artifacts in place, so "did that nudge
help?" could only be answered from memory. Renders now archive into a
history ring (last five revisions) and diff_renders compares any two —
default: latest against previous.
"""
from __future__ import annotations

import io
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from pathlib import Path  # noqa: E402

from frameforge.mcp.usecases import diff_renders, render_frameforge_yaml  # noqa: E402


def _yaml(fill="#ffffff"):
    from frameforge.sdk import DocumentBuilder, serialize
    b = DocumentBuilder(title="hist", profile="diagram")
    pg = b.page("p1", canvas={"size": [120, 80], "units": "px"})
    pg.layer("main").rect([0, 0, 120, 80], fill=fill)
    return serialize(b.build(), format="yaml")


def test_renders_accumulate_history_revisions(tmp_path):
    r1 = render_frameforge_yaml(_yaml("#ffffff"), session_id="h",
                                session_root=tmp_path, raster_png=False)
    assert r1["ok"] is True
    assert r1["revision"] == 1
    r2 = render_frameforge_yaml(_yaml("#000000"), session_id="h",
                                session_root=tmp_path, raster_png=False)
    assert r2["revision"] == 2
    hist = Path(tmp_path) / "h" / "history"
    assert (hist / "rev-001" / "page-001.svg").is_file()
    assert (hist / "rev-002" / "page-001.svg").is_file()
    assert r2["history"]["revisions"] == [1, 2]
    # the two archived revisions really are different documents
    a = (hist / "rev-001" / "page-001.svg").read_text(encoding="utf-8")
    b = (hist / "rev-002" / "page-001.svg").read_text(encoding="utf-8")
    assert a != b


def test_history_ring_keeps_last_five(tmp_path):
    shades = ["#111111", "#222222", "#333333", "#444444", "#555555", "#666666", "#777777"]
    for shade in shades:
        out = render_frameforge_yaml(_yaml(shade), session_id="ring",
                                     session_root=tmp_path, raster_png=False)
    assert out["revision"] == 7
    assert out["history"]["revisions"] == [3, 4, 5, 6, 7]
    hist = Path(tmp_path) / "ring" / "history"
    assert sorted(p.name for p in hist.iterdir()) == [
        "rev-003", "rev-004", "rev-005", "rev-006", "rev-007"]


def _write_png(path: Path, square_x: int):
    PIL = pytest.importorskip("PIL.Image")
    img = PIL.new("RGB", (64, 48), (255, 255, 255))
    for dx in range(8):
        for dy in range(8):
            img.putpixel((square_x + dx, 20 + dy), (0, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    path.write_bytes(buf.getvalue())


def test_diff_renders_latest_vs_previous(tmp_path):
    sess = Path(tmp_path) / "d"
    _write_png(sess / "history" / "rev-001" / "p001.png", square_x=10)
    _write_png(sess / "history" / "rev-002" / "p001.png", square_x=18)
    out = diff_renders(session_id="d", session_root=tmp_path)
    assert out["ok"] is True
    assert out["diffed"] == {"reference_rev": 1, "candidate_rev": 2}
    assert out["comparison"], "expected per-region comparison metrics"


def test_diff_renders_needs_two_revisions(tmp_path):
    sess = Path(tmp_path) / "solo"
    _write_png(sess / "history" / "rev-001" / "p001.png", square_x=10)
    out = diff_renders(session_id="solo", session_root=tmp_path)
    assert out["ok"] is False
    assert "revision" in out["error"]


def test_server_registers_diff_renders(tmp_path):
    from frameforge.mcp.server import create_server

    class _Fake:
        def __init__(self, name, **kw):
            self.tools, self.resources, self.prompts = {}, {}, {}

        def tool(self, **_kw):
            def dec(fn):
                self.tools[fn.__name__] = fn
                return fn
            return dec

        def resource(self, uri, **_kw):
            def dec(fn):
                self.resources[uri] = fn
                return fn
            return dec

        def prompt(self, **_kw):
            def dec(fn):
                self.prompts[fn.__name__] = fn
                return fn
            return dec

    server = create_server(session_root=tmp_path, fastmcp_cls=_Fake)
    assert "diff_renders" in server.tools
