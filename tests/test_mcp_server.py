#!/usr/bin/env python3
"""Regression tests for the FrameGraph MCP feedback loop."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from framegraph.mcp.server import (  # noqa: E402
    create_server,
    list_sdk_clients,
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
    result = run_sdk_code(SDK_SCRIPT, session_id="loop-1", session_root=tmp_path)

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
    assert any(block.get("mimeType") == "image/svg+xml" for block in blocks)
    assert any(link["uri"] == "framegraph://session/loop-1/page/1.svg" for link in result["resources"])


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

    result = run_sdk_code(code, session_id="derive", session_root=tmp_path)

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

    result = run_sdk_client("examples/client.py", session_id="edited", session_root=tmp_path / "sessions", repo_root=tmp_path)

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
    result = run_sdk_code(SDK_SCRIPT, session_id="resources", session_root=tmp_path)
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
    } <= set(server.tools)
    assert "framegraph://session/{session_id}/document.yaml" in server.resources
    assert "framegraph://session/{session_id}/page/{page_number}.svg" in server.resources
    assert "framegraph://session/{session_id}/diagnostics.json" in server.resources
