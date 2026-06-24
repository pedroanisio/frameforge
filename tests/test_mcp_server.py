#!/usr/bin/env python3
"""Regression tests for the FrameGraph MCP feedback loop."""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from framegraph.mcp.server import (  # noqa: E402
    cleanup_sessions,
    create_server,
    list_sdk_clients,
    list_sessions,
    mcp_content_blocks,
    read_session_resource,
    read_sdk_client,
    run_sdk_client,
    run_sdk_code,
    write_sdk_client,
)


SDK_SCRIPT = """
from framegraph.sdk import DocumentBuilder

doc = DocumentBuilder(title="Live MCP Render", profile="deck")
body = doc.define_text_style("body", font_family="sans", font_size=18, color="#14213d")
page = doc.page("p1", canvas={"size": [320, 180], "units": "px"}, reading_order=["title"])
page.layer("main").rect([0, 0, 320, 180], fill="#f7f7f2")
page.text([28, 32, 220, 36], "Rendered from SDK", id="title", style=body)
doc.write(OUTPUT_YAML_PATH, fail_on_error=True)
"""


def test_run_sdk_code_generates_yaml_validates_and_renders_svg(tmp_path):
    result = run_sdk_code(SDK_SCRIPT, session_id="loop-1", session_root=tmp_path, raster_png=False)

    assert result["ok"] is True
    assert result["session_id"] == "loop-1"
    assert result["yaml_path"].endswith("generated.fg.yaml")
    assert result["validation"]["ok"] is True
    assert result["stdout"] == ""
    assert result["stderr"] == ""

    yaml_text = (tmp_path / "loop-1" / "generated.fg.yaml").read_text(encoding="utf-8")
    assert "Live MCP Render" in yaml_text

    svg_path = tmp_path / "loop-1" / "page-001.svg"
    assert svg_path.exists()
    svg = svg_path.read_text(encoding="utf-8")
    assert "Rendered from SDK" in svg

    blocks = mcp_content_blocks(result)
    assert blocks[0]["type"] == "text"
    # SVG is not a vision-decodable media type: it must never be shipped as an image
    # block. It stays reachable as a resource link instead.
    assert not any(block.get("mimeType") == "image/svg+xml" for block in blocks)
    assert any(link["uri"] == "framegraph://session/loop-1/page/1.svg" for link in result["resources"])


def test_mcp_content_blocks_ships_png_not_svg_as_image(tmp_path):
    """A PNG render becomes an image block; an SVG render never does."""
    png = tmp_path / "p001.png"
    # 1x1 transparent PNG.
    png.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        )
    )
    svg = tmp_path / "page-001.svg"
    svg.write_text("<svg/>", encoding="utf-8")
    result = {
        "ok": True,
        "session_id": "blocks",
        "renders": [
            {"page": 1, "path": str(svg), "mimeType": "image/svg+xml"},
            {"page": 1, "path": str(png), "mimeType": "image/png"},
        ],
        "render_warning": None,
    }

    blocks = mcp_content_blocks(result)

    image_blocks = [block for block in blocks if block["type"] == "image"]
    assert [block["mimeType"] for block in image_blocks] == ["image/png"]


def test_render_warning_when_raster_backend_unavailable(tmp_path, monkeypatch):
    """raster_png=True but no browser backend -> ok stays True, but a warning is surfaced."""
    import framegraph.mcp.server as server

    def _unavailable(svg_paths, session_dir, session_id):
        return [], "PNG rasterization unavailable: stub. install the `browser` group."

    monkeypatch.setattr(server, "_try_rasterize_pngs", _unavailable)
    result = run_sdk_code(SDK_SCRIPT, session_id="warn", session_root=tmp_path, raster_png=True)

    assert result["ok"] is True  # SVG still rendered
    assert "render_warning" in result and "browser" in result["render_warning"]
    summary = json.loads(mcp_content_blocks(result)[0]["text"])
    assert summary["render_warning"] == result["render_warning"]


def test_render_exception_returns_structured_error_not_traceback(tmp_path, monkeypatch):
    import framegraph.mcp.server as server

    def _boom(document, base_dir):
        raise RuntimeError("renderer exploded")

    monkeypatch.setattr(server, "_render_page_svgs_bounded", _boom)
    result = run_sdk_code(SDK_SCRIPT, session_id="boom", session_root=tmp_path, raster_png=False)

    assert result["ok"] is False
    assert "renderer exploded" in result["error"]
    assert result["validation"]["ok"] is True  # validation passed; only render failed


def test_max_pages_zero_renders_all_pages(tmp_path):
    code = """
from framegraph.sdk import DocumentBuilder

doc = DocumentBuilder(title="Two Pages", profile="deck")
for pid in ("p1", "p2"):
    page = doc.page(pid, canvas={"size": [120, 80], "units": "px"})
    page.layer("main").rect([0, 0, 120, 80], fill="#ffffff")
doc.write(OUTPUT_YAML_PATH, fail_on_error=True)
"""
    result = run_sdk_code(code, session_id="allpages", session_root=tmp_path, max_pages=0, raster_png=False)

    assert result["ok"] is True
    svg_pages = [r for r in result["renders"] if r["mimeType"] == "image/svg+xml"]
    assert len(svg_pages) == 2  # max_pages=0 means "all pages", not "no pages"


def test_run_sdk_code_derives_yaml_from_document_variable(tmp_path):
    code = """
from framegraph.sdk import DocumentBuilder

builder = DocumentBuilder(title="Derived YAML", profile="deck")
builder.page("p", canvas={"size": [120, 80], "units": "px"}).layer("main").text(
    [10, 10, 80, 20],
    "derived",
    id="t",
)
doc = builder.build()
"""

    result = run_sdk_code(code, session_id="derive", session_root=tmp_path, raster_png=False)

    assert result["ok"] is True
    assert (tmp_path / "derive" / "generated.fg.yaml").exists()
    assert "Derived YAML" in (tmp_path / "derive" / "generated.fg.yaml").read_text(encoding="utf-8")
    assert "derived" in (tmp_path / "derive" / "page-001.svg").read_text(encoding="utf-8")


def test_run_sdk_code_rejects_unsafe_session_id(tmp_path):
    with pytest.raises(ValueError, match="session_id"):
        run_sdk_code("print('nope')", session_id="../escape", session_root=tmp_path)


def test_sdk_client_file_tools_edit_and_run_python_example(tmp_path):
    examples = tmp_path / "examples"
    examples.mkdir()
    client_path = examples / "client.py"
    client_path.write_text(
        """
from framegraph.sdk import DocumentBuilder

doc = DocumentBuilder(title="Editable client", profile="deck")
body = doc.define_text_style("body", font_family="sans", font_size=18, color="#1f2937")
page = doc.page("p1", canvas={"size": [240, 120], "units": "px"}, reading_order=["title"])
page.layer("main").rect([0, 0, 240, 120], fill="#ffffff")
page.text([20, 30, 180, 28], "before edit", id="title", style=body)
doc.write(OUTPUT_YAML_PATH, fail_on_error=True)
""".lstrip(),
        encoding="utf-8",
    )

    listed = list_sdk_clients(repo_root=tmp_path)
    assert listed["clients"] == [
        {
            "path": "examples/client.py",
            "bytes": client_path.stat().st_size,
            "sha256": listed["clients"][0]["sha256"],
        }
    ]

    read = read_sdk_client("examples/client.py", repo_root=tmp_path)
    assert read["path"] == "examples/client.py"
    assert "before edit" in read["code"]

    edited = read["code"].replace("before edit", "after edit")
    write = write_sdk_client("examples/client.py", edited, repo_root=tmp_path)
    assert write["path"] == "examples/client.py"
    assert write["bytes"] == len(edited.encode("utf-8"))
    assert "after edit" in client_path.read_text(encoding="utf-8")

    result = run_sdk_client(
        "examples/client.py",
        session_id="edited",
        session_root=tmp_path / "sessions",
        repo_root=tmp_path,
        raster_png=False,
    )

    assert result["ok"] is True
    assert result["client_path"] == str(client_path.resolve())
    assert "after edit" in (tmp_path / "sessions" / "edited" / "generated.fg.yaml").read_text(encoding="utf-8")
    assert "after edit" in (tmp_path / "sessions" / "edited" / "page-001.svg").read_text(encoding="utf-8")


def test_sdk_client_tools_reject_paths_outside_allowed_roots(tmp_path):
    examples = tmp_path / "examples"
    examples.mkdir()
    (tmp_path / "outside.py").write_text("print('outside')\n", encoding="utf-8")

    with pytest.raises(ValueError, match="allowed SDK client roots"):
        read_sdk_client("outside.py", repo_root=tmp_path)

    with pytest.raises(ValueError, match="Python"):
        write_sdk_client("examples/client.txt", "print('nope')\n", create=True, repo_root=tmp_path)


def test_read_session_resource_returns_yaml_svg_and_diagnostics(tmp_path):
    result = run_sdk_code(SDK_SCRIPT, session_id="resources", session_root=tmp_path, raster_png=False)
    assert result["ok"] is True

    document = read_session_resource("framegraph://session/resources/document.yaml", session_root=tmp_path)
    page = read_session_resource("framegraph://session/resources/page/1.svg", session_root=tmp_path)
    diagnostics = read_session_resource(
        "framegraph://session/resources/diagnostics.json",
        session_root=tmp_path,
    )

    assert document["mimeType"] == "application/x-yaml"
    assert "Live MCP Render" in document["text"]
    assert page["mimeType"] == "image/svg+xml"
    assert "Rendered from SDK" in page["text"]
    assert diagnostics["mimeType"] == "application/json"
    assert '"ok": true' in diagnostics["text"]


class FakeFastMCP:
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.tools = {}
        self.resources = {}
        self.prompts = {}

    def tool(self, **_kwargs):
        def decorate(func):
            self.tools[func.__name__] = func
            return func

        return decorate

    def resource(self, uri: str, **_kwargs):
        def decorate(func):
            self.resources[uri] = func
            return func

        return decorate

    def prompt(self, **_kwargs):
        def decorate(func):
            self.prompts[func.__name__] = func
            return func

        return decorate


def test_create_server_registers_feedback_loop_tools_and_resources(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    assert server.name == "FrameGraph"
    assert {
        "get_session_resource",
        "list_sdk_clients",
        "read_sdk_client",
        "render_framegraph_yaml",
        "run_sdk_client",
        "run_sdk_code",
        "write_sdk_client",
        "propose_from_image",
        "propose_from_document",
        "list_sessions",
        "cleanup_sessions",
    } <= set(server.tools)
    assert "framegraph://session/{session_id}/document.yaml" in server.resources
    assert "framegraph://session/{session_id}/page/{page_number}.svg" in server.resources
    assert "framegraph://session/{session_id}/diagnostics.json" in server.resources


def test_create_server_registers_authoring_guide_prompt(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    assert "framegraph_guide" in server.prompts
    guide = server.prompts["framegraph_guide"]()
    assert "DocumentBuilder" in guide
    assert "propose_from_image" in guide
    assert "PALS" in guide


def test_create_server_writes_structured_log_for_tool_instructions_and_responses(tmp_path):
    log_path = tmp_path / "mcp-events.jsonl"
    server = create_server(session_root=tmp_path, structured_log_path=log_path, fastmcp_cls=FakeFastMCP)

    result = server.tools["run_sdk_code"](SDK_SCRIPT, session_id="logged", raster_png=False)
    structured = getattr(result, "structuredContent", result)
    assert structured["ok"] is True

    with pytest.raises(FileNotFoundError):
        server.tools["read_sdk_client"]("examples/missing.py")

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]

    assert [event["tool"] for event in events] == ["run_sdk_code", "read_sdk_client"]
    assert events[0]["schema"] == "framegraph.mcp.structured_log.v1"
    assert events[0]["instruction"]["code"] == SDK_SCRIPT
    assert events[0]["instruction"]["session_id"] == "logged"
    assert events[0]["response"]["ok"] is True
    assert events[0]["response"]["session_id"] == "logged"
    assert events[1]["instruction"]["path"] == "examples/missing.py"
    assert events[1]["response"]["ok"] is False
    assert events[1]["response"]["error"]["type"] == "FileNotFoundError"


def test_subprocess_env_strips_secrets_by_default(tmp_path, monkeypatch):
    import framegraph.mcp.server as server

    monkeypatch.setenv("MY_API_TOKEN", "supersecret")
    monkeypatch.setenv("DEPLOY_PASSWORD", "hunter2")
    monkeypatch.setenv("PLAIN_SETTING", "fine")

    env = server._subprocess_env(tmp_path)
    assert "MY_API_TOKEN" not in env
    assert "DEPLOY_PASSWORD" not in env
    assert env.get("PLAIN_SETTING") == "fine"
    assert "PYTHONPATH" in env

    monkeypatch.setenv("FRAMEGRAPH_MCP_KEEP_ENV", "1")
    kept = server._subprocess_env(tmp_path)
    assert kept.get("MY_API_TOKEN") == "supersecret"


def test_new_generated_yaml_uses_content_hash_not_mtime(tmp_path):
    import framegraph.mcp.server as server

    examples = tmp_path / "examples"
    examples.mkdir()
    fixture = examples / "demo.fg.yaml"
    fixture.write_text("dsl: FrameGraph\n", encoding="utf-8")
    before = server._framegraph_yaml_snapshot(tmp_path)

    # A bare touch (mtime bump, identical bytes) must NOT be mistaken for output.
    stat = fixture.stat()
    os.utime(fixture, (stat.st_atime + 10, stat.st_mtime + 10))
    assert server._new_generated_yaml(tmp_path, before) is None

    # A real content change is detected.
    fixture.write_text("dsl: FrameGraph\nversion: '2.2.0'\n", encoding="utf-8")
    assert server._new_generated_yaml(tmp_path, before) == fixture


def test_structured_log_truncates_oversized_fields(tmp_path):
    import framegraph.mcp.server as server

    log_path = tmp_path / "log.jsonl"
    big = "x" * (server.STRUCTURED_LOG_MAX_FIELD_CHARS + 500)
    server._append_structured_log(log_path, {"tool": "t", "instruction": {"code": big}})

    event = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
    assert len(event["instruction"]["code"]) < len(big)
    assert "truncated" in event["instruction"]["code"]


def test_propose_confines_input_path_when_input_roots_set(tmp_path, monkeypatch):
    from framegraph.mcp.server import propose_from_image

    monkeypatch.setenv("FRAMEGRAPH_MCP_INPUT_ROOTS", str(tmp_path / "allowed"))
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"not really a png")

    result = propose_from_image(str(outside), session_id="confine", session_root=tmp_path)

    assert result["ok"] is False
    assert "FRAMEGRAPH_MCP_INPUT_ROOTS" in result["error"]


def test_propose_from_image_reports_missing_vision_group(tmp_path, monkeypatch):
    import framegraph.mcp.server as server

    # A None entry in sys.modules makes the in-function import raise ImportError,
    # standing in for an environment without the `vision` dependency group.
    monkeypatch.setitem(sys.modules, "framegraph.vision.application.service", None)

    result = server.propose_from_image(image_base64="AAAA", session_id="novision", session_root=tmp_path)

    assert result["ok"] is False
    assert "vision" in result["error"].lower()


def test_list_and_cleanup_sessions(tmp_path):
    run_sdk_code(SDK_SCRIPT, session_id="keep-me", session_root=tmp_path, raster_png=False)
    run_sdk_code(SDK_SCRIPT, session_id="drop-me", session_root=tmp_path, raster_png=False)

    listed = list_sessions(session_root=tmp_path)
    ids = {entry["session_id"] for entry in listed["sessions"]}
    assert {"keep-me", "drop-me"} <= ids
    assert all(entry["has_document"] for entry in listed["sessions"])

    # No selector is a no-op (safe by default).
    assert cleanup_sessions(session_root=tmp_path)["removed_count"] == 0

    # dry_run reports the selection without deleting.
    preview = cleanup_sessions(session_root=tmp_path, session_ids=["drop-me"], dry_run=True)
    assert preview["removed"] == ["drop-me"]
    assert (tmp_path / "drop-me").exists()

    done = cleanup_sessions(session_root=tmp_path, session_ids=["drop-me"])
    assert done["removed"] == ["drop-me"]
    assert not (tmp_path / "drop-me").exists()
    assert (tmp_path / "keep-me").exists()
