"""write_sdk_client dispatch, chunked append, size limits, and transport round-trip.

Regression cover for the defect where a large ``code`` argument arrived at the
server as ``None`` (dropped by the client's per-argument transport limit) and the
tool answered with a bare "provide code", indistinguishable from operator error.

These tests exercise the layer the previous suite skipped:

* the *dispatch* (``usecases.write_or_edit_client``) — full replace, anchored
  edit, chunked append, and the improved empty-``code`` diagnostic — which the
  server tool wrapper now delegates to (previously the branch logic lived inline
  in the wrapper and had zero coverage);
* the ``clients.write_sdk_client`` size boundary (cap applies to the *result*);
* an end-to-end round-trip through the FastMCP tool layer with a large argument,
  proving the server + FastMCP handle it — so the ~20 KB cap seen in practice is
  in the external MCP client bridge, not here.

Runs under pytest or standalone (``uv run python tests/test_mcp_write_dispatch.py``).
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from framegraph.mcp.clients import read_sdk_client, write_sdk_client  # noqa: E402
from framegraph.mcp.config import MAX_CLIENT_BYTES  # noqa: E402
from framegraph.mcp.server import create_server  # noqa: E402
from framegraph.mcp.usecases import write_or_edit_client  # noqa: E402

CODE = "def build():\n    return {'dsl': 'FrameGraph'}\n"


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("FRAMEGRAPH_MCP_EDIT_ROOTS", raising=False)
    r = tmp_path / "repo"
    (r / "static" / "examples").mkdir(parents=True)
    return r


def _w(repo: Path, **kw):
    kw.setdefault("repo_root", repo)
    kw.setdefault("edit_roots", "static/examples")
    return write_or_edit_client(**kw)


# --- full replace ---------------------------------------------------------- #
def test_full_replace_create(repo: Path) -> None:
    res = _w(repo, path="a.py", code=CODE, create=True)
    assert res["ok"] and res["created"] is True
    assert (repo / "static" / "examples" / "a.py").read_text() == CODE


# --- improved empty-code diagnostic (the actual defect) -------------------- #
def test_none_code_names_transport_limit_and_alternatives(repo: Path) -> None:
    with pytest.raises(ValueError) as ei:
        _w(repo, path="a.py", code=None, create=True)
    msg = str(ei.value)
    assert "per-argument transport limit" in msg          # not a bare "provide code"
    assert "append=true" in msg and "anchored edit" in msg  # both size-safe escapes named


def test_blank_code_is_treated_as_missing(repo: Path) -> None:
    with pytest.raises(ValueError, match="per-argument transport limit"):
        _w(repo, path="a.py", code="   \n  ", create=True)


# --- anchored edit (was entirely untested) -------------------------------- #
def test_anchored_edit_happy_path(repo: Path) -> None:
    _w(repo, path="a.py", code=CODE, create=True)
    res = _w(repo, path="a.py", old_string="'FrameGraph'", new_string="'FrameGraph2'")
    assert res["ok"]
    assert "'FrameGraph2'" in (repo / "static" / "examples" / "a.py").read_text()


def test_anchored_edit_not_found(repo: Path) -> None:
    _w(repo, path="a.py", code=CODE, create=True)
    with pytest.raises(ValueError, match="was not found"):
        _w(repo, path="a.py", old_string="NOPE", new_string="x")


def test_anchored_edit_multi_match(repo: Path) -> None:
    _w(repo, path="a.py", code="x=1\nx=1\n", create=True)
    with pytest.raises(ValueError, match="matches 2 locations"):
        _w(repo, path="a.py", old_string="x=1", new_string="x=2")


def test_anchored_edit_identical(repo: Path) -> None:
    _w(repo, path="a.py", code=CODE, create=True)
    with pytest.raises(ValueError, match="identical"):
        _w(repo, path="a.py", old_string="build", new_string="build")


def test_anchored_needs_both_sides(repo: Path) -> None:
    _w(repo, path="a.py", code=CODE, create=True)
    with pytest.raises(ValueError, match="needs both"):
        _w(repo, path="a.py", old_string="build")


def test_code_and_anchored_are_mutually_exclusive(repo: Path) -> None:
    _w(repo, path="a.py", code=CODE, create=True)
    with pytest.raises(ValueError, match="not both"):
        _w(repo, path="a.py", code=CODE, old_string="build", new_string="make")


# --- chunked append (P7) --------------------------------------------------- #
def test_append_builds_file_in_partial_chunks(repo: Path) -> None:
    # a chunk that is not valid Python on its own — allowed because partial
    r1 = _w(repo, path="big.py", code="def build():\n", create=True, allow_partial=True)
    assert r1["created"] is True and r1["partial"] is True
    # final chunk completes the file and is compiled (allow_partial defaults False)
    r2 = _w(repo, path="big.py", code="    return {'dsl': 'FrameGraph'}\n", append=True)
    assert r2["appended"] is True and r2["partial"] is False
    text = (repo / "static" / "examples" / "big.py").read_text()
    assert text == "def build():\n    return {'dsl': 'FrameGraph'}\n"
    compile(text, "big.py", "exec")  # the assembled file is valid


def test_append_creates_when_absent(repo: Path) -> None:
    res = _w(repo, path="fresh.py", code=CODE, append=True)
    assert res["ok"] and res["created"] is True and res["appended"] is False
    assert (repo / "static" / "examples" / "fresh.py").read_text() == CODE


def test_partial_chunk_that_never_completes_is_written_but_uncompiled(repo: Path) -> None:
    res = _w(repo, path="p.py", code="def build(:\n", create=True, allow_partial=True)
    assert res["partial"] is True  # no SyntaxError raised because compile was skipped


# --- size boundary (P3) ---------------------------------------------------- #
def test_large_payload_under_cap_is_accepted(repo: Path) -> None:
    big = '"""' + ("x" * 1_000_000) + '"""\nY = 1\n'
    res = write_sdk_client("big.py", big, create=True, repo_root=repo, edit_roots="static/examples")
    assert res["ok"] and res["bytes"] == len(big.encode())


def test_over_cap_is_rejected_on_the_result(repo: Path) -> None:
    over = '"""' + ("x" * (MAX_CLIENT_BYTES + 10)) + '"""\n'
    with pytest.raises(ValueError, match="content exceeds"):
        write_sdk_client("big.py", over, create=True, repo_root=repo, edit_roots="static/examples")


def test_append_cap_applies_to_cumulative_content(repo: Path) -> None:
    half = '"""' + ("x" * (MAX_CLIENT_BYTES - 100)) + '"""\n'
    write_sdk_client("g.py", half, create=True, allow_partial=True,
                     repo_root=repo, edit_roots="static/examples")
    with pytest.raises(ValueError, match="content exceeds"):
        write_sdk_client("g.py", "x" * 500, append=True, allow_partial=True,
                         repo_root=repo, edit_roots="static/examples")


# --- end-to-end FastMCP transport round-trip (P4) -------------------------- #
def test_fastmcp_tool_layer_round_trips_a_large_argument(repo: Path) -> None:
    srv = create_server(repo_root=repo, edit_roots="static/examples")
    big = '"""' + ("z" * 250_000) + '"""\nQ = 2\n'
    asyncio.run(srv.call_tool("write_sdk_client",
                              {"path": "static/examples/rt.py", "code": big, "create": True}))
    written = repo / "static" / "examples" / "rt.py"
    assert written.exists() and written.stat().st_size == len(big.encode())


def test_fastmcp_none_code_surfaces_improved_diagnostic(repo: Path) -> None:
    srv = create_server(repo_root=repo, edit_roots="static/examples")
    res = asyncio.run(srv.call_tool("write_sdk_client",
                                    {"path": "static/examples/rt.py", "code": None}))
    assert "per-argument transport limit" in json.dumps(res, default=str)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
