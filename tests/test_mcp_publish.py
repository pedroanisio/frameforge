#!/usr/bin/env python3
"""``FRAMEFORGE_MCP_PUBLISH_ROOT`` — durable published output for sessions.

The session scratchpad is ephemeral by design (tempdir, 5-revision ring,
swept by ``cleanup_sessions``); durable output existed only when a client ran
directly and wrote ``out/`` by hand. This knob gives the MCP a publish path:

  * unset ⇒ publishing disabled — behaviour identical to before (pinned);
  * set + ``publish=true`` on a render tool ⇒ the session's DELIVERABLES are
    copied to ``<root>/<session_id>/`` with a sha256 manifest;
  * deliverables = document.fg.yaml (renamed from generated.fg.yaml),
    document.pdf, page-*.svg, p*.png, diagnostics.json (the caveats travel
    with the claim — PALS); scratch (history/, workspace.json, runner) stays
    out;
  * re-publishing a session overwrites its directory in place;
  * ``publish=true`` without a root is a STRUCTURED, fail-fast error naming
    the env var — never a silent no-op — and nothing is rendered;
  * a publish root inside the session root is refused (publishing into the
    scratchpad is a config error);
  * ``cleanup_sessions`` never touches the publish root.
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

from frameforge.mcp import config as C  # noqa: E402
from frameforge.mcp.sessions import publish_session  # noqa: E402
from frameforge.mcp.sessions import cleanup_sessions  # noqa: E402
from frameforge.mcp.usecases import run_sdk_code  # noqa: E402

SDK_SCRIPT = """
from frameforge.sdk import DocumentBuilder
doc = DocumentBuilder(title="Publish Probe", profile="deck")
page = doc.page("p1", canvas={"size": [200, 120], "units": "px"})
page.layer("main").rect([0, 0, 200, 120], fill="#f5f5f0")
page.text([20, 30, 160, 30], "published", id="t")
doc.write(OUTPUT_YAML_PATH, fail_on_error=True)
"""


# --- config reader --------------------------------------------------------- #
def test_publish_root_unset_is_none(monkeypatch):
    monkeypatch.delenv("FRAMEFORGE_MCP_PUBLISH_ROOT", raising=False)
    assert C.publish_root() is None


def test_publish_root_reads_env(monkeypatch, tmp_path):
    monkeypatch.setenv("FRAMEFORGE_MCP_PUBLISH_ROOT", str(tmp_path / "pub"))
    assert C.publish_root() == (tmp_path / "pub").expanduser()


# --- publish_session unit contract ----------------------------------------- #
def _render_session(tmp_path, sid="probe"):
    res = run_sdk_code(SDK_SCRIPT, session_id=sid, session_root=tmp_path / "sessions",
                       raster_png=False)
    assert res["ok"] is True
    return res


def test_publish_copies_deliverables_with_manifest(tmp_path):
    _render_session(tmp_path)
    out = publish_session("probe", session_root=tmp_path / "sessions",
                          publish_root=tmp_path / "pub", revision=1)
    assert out["ok"] is True
    pub = tmp_path / "pub" / "probe"
    names = sorted(p.name for p in pub.iterdir())
    assert "document.fg.yaml" in names          # renamed deliverable
    assert "page-001.svg" in names
    assert "diagnostics.json" in names          # caveats travel with the claim
    assert "manifest.json" in names
    # scratch stays out
    assert "generated.fg.yaml" not in names
    assert "_run_sdk_client.py" not in names and "_run_sdk.py" not in names
    assert "history" not in names and "workspace.json" not in names
    manifest = json.loads((pub / "manifest.json").read_text())
    assert manifest["session_id"] == "probe" and manifest["revision"] == 1
    listed = {f["name"] for f in manifest["files"]}
    assert "document.fg.yaml" in listed and "page-001.svg" in listed
    for f in manifest["files"]:
        assert f["bytes"] > 0 and len(f["sha256"]) == 64


def test_republish_overwrites_in_place(tmp_path):
    _render_session(tmp_path)
    publish_session("probe", session_root=tmp_path / "sessions",
                    publish_root=tmp_path / "pub", revision=1)
    stale = tmp_path / "pub" / "probe" / "stale-leftover.svg"
    stale.write_text("old")
    out = publish_session("probe", session_root=tmp_path / "sessions",
                          publish_root=tmp_path / "pub", revision=2)
    assert out["ok"] is True
    assert not stale.exists(), "re-publish must replace the directory, not accrete"
    manifest = json.loads((tmp_path / "pub" / "probe" / "manifest.json").read_text())
    assert manifest["revision"] == 2


def test_publish_root_inside_session_root_is_refused(tmp_path):
    _render_session(tmp_path)
    out = publish_session("probe", session_root=tmp_path / "sessions",
                          publish_root=tmp_path / "sessions" / "pub", revision=1)
    assert out["ok"] is False
    assert "session root" in out["error"].lower()


# --- render-tool wiring ---------------------------------------------------- #
def test_render_with_publish_lands_published_block(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_PUBLISH_ROOT", str(tmp_path / "pub"))
    res = run_sdk_code(SDK_SCRIPT, session_id="wired", session_root=tmp_path / "s",
                       raster_png=False, publish=True)
    assert res["ok"] is True
    pub = res["published"]
    assert pub["ok"] is True
    assert pub["dir"] == str(tmp_path / "pub" / "wired")
    assert any(f["name"] == "document.fg.yaml" for f in pub["files"])
    assert (tmp_path / "pub" / "wired" / "manifest.json").is_file()


def test_publish_true_without_root_fails_fast_and_renders_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv("FRAMEFORGE_MCP_PUBLISH_ROOT", raising=False)
    res = run_sdk_code(SDK_SCRIPT, session_id="noroot", session_root=tmp_path / "s",
                       raster_png=False, publish=True)
    assert res["ok"] is False
    assert "FRAMEFORGE_MCP_PUBLISH_ROOT" in res["error"]
    assert not (tmp_path / "s" / "noroot" / "generated.fg.yaml").exists(), \
        "fail-fast means the render must not have run"


def test_publish_false_is_byte_identical_no_publish_block(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_PUBLISH_ROOT", str(tmp_path / "pub"))
    res = run_sdk_code(SDK_SCRIPT, session_id="plain", session_root=tmp_path / "s",
                       raster_png=False)
    assert res["ok"] is True
    assert "published" not in res
    assert not (tmp_path / "pub").exists(), "publish=false must not touch the root"


def test_cleanup_sessions_never_touches_publish_root(tmp_path, monkeypatch):
    monkeypatch.setenv("FRAMEFORGE_MCP_PUBLISH_ROOT", str(tmp_path / "s" / "pub-nested-NO"))
    _render_session(tmp_path, sid="sweep")
    publish_dir = tmp_path / "pub"
    publish_session("sweep", session_root=tmp_path / "sessions",
                    publish_root=publish_dir, revision=1)
    swept = cleanup_sessions(session_root=tmp_path / "sessions",
                             session_ids=["sweep"])
    assert swept.get("ok", True) in (True,)
    assert not (tmp_path / "sessions" / "sweep").exists(), "session itself IS swept"
    assert (publish_dir / "sweep" / "manifest.json").is_file(), \
        "cleanup swept the published output"


def test_missing_session_is_structured(tmp_path):
    out = publish_session("ghost", session_root=tmp_path / "sessions",
                          publish_root=tmp_path / "pub", revision=1)
    assert out["ok"] is False and "ghost" in out["error"]


def test_all_three_render_tools_expose_publish(tmp_path):
    """The MCP surface itself carries the parameter — all three render tools."""
    import inspect

    from frameforge.mcp import server as server_mod

    class FakeFastMCP:
        def __init__(self, name, **kwargs):
            self.tools = {}
        def tool(self, **_kw):
            def dec(f):
                self.tools[f.__name__] = f
                return f
            return dec
        def resource(self, uri, **_kw):
            def dec(f):
                return f
            return dec
        def prompt(self, **_kw):
            def dec(f):
                return f
            return dec

    server = server_mod.create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)
    for tool in ("run_sdk_code", "run_sdk_client", "render_frameforge_yaml"):
        params = inspect.signature(server.tools[tool]).parameters
        assert "publish" in params, f"{tool} does not expose publish="
        assert params["publish"].default is False
