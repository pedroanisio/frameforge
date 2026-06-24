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


def _derive_code(marker: str) -> str:
    """SDK code that exposes a built document (the *derive* path) without writing
    ``OUTPUT_YAML_PATH`` — the path where session reuse could serve a stale render."""
    return f"""
from framegraph.sdk import DocumentBuilder

builder = DocumentBuilder(title="Stale Probe", profile="deck")
page = builder.page("p1", canvas={{"size": [200, 120], "units": "px"}})
page.layer("main").rect([0, 0, 200, 120], fill="#ffffff")
page.text([10, 10, 180, 28], {marker!r}, id="t")
doc = builder.build()
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


def test_run_sdk_code_rerun_same_session_rerenders_edited_document(tmp_path):
    """Re-running edited code under the SAME session_id must render the NEW document.

    Regression: the harness derives YAML only when OUTPUT_YAML_PATH is absent and
    the session dir was never cleared, so a second run reused the first run's stale
    generated.fg.yaml (the documented "rotate the session id" workaround). Per-run
    outputs are now reset so a reused session re-renders the edit.
    """
    first = run_sdk_code(
        _derive_code("alpha-marker"), session_id="reuse", session_root=tmp_path, raster_png=False
    )
    assert first["ok"] is True
    assert "alpha-marker" in (tmp_path / "reuse" / "generated.fg.yaml").read_text(encoding="utf-8")

    second = run_sdk_code(
        _derive_code("beta-marker"), session_id="reuse", session_root=tmp_path, raster_png=False
    )
    assert second["ok"] is True
    yaml_text = (tmp_path / "reuse" / "generated.fg.yaml").read_text(encoding="utf-8")
    assert "beta-marker" in yaml_text
    assert "alpha-marker" not in yaml_text
    assert "beta-marker" in (tmp_path / "reuse" / "page-001.svg").read_text(encoding="utf-8")


def test_run_sdk_client_rerun_same_session_rerenders_edited_client(tmp_path):
    """The same stale-session fix must hold for the editable-client entry point."""
    examples = tmp_path / "examples"
    examples.mkdir()
    client = examples / "probe.py"
    sessions = tmp_path / "sessions"

    client.write_text(_derive_code("alpha-client"), encoding="utf-8")
    first = run_sdk_client(
        "examples/probe.py", session_id="cl", session_root=sessions, repo_root=tmp_path, raster_png=False
    )
    assert first["ok"] is True
    assert "alpha-client" in (sessions / "cl" / "generated.fg.yaml").read_text(encoding="utf-8")

    client.write_text(_derive_code("beta-client"), encoding="utf-8")
    second = run_sdk_client(
        "examples/probe.py", session_id="cl", session_root=sessions, repo_root=tmp_path, raster_png=False
    )
    assert second["ok"] is True
    yaml_text = (sessions / "cl" / "generated.fg.yaml").read_text(encoding="utf-8")
    assert "beta-client" in yaml_text
    assert "alpha-client" not in yaml_text


def test_run_sdk_code_subprocess_timeout_returns_structured_error(tmp_path):
    """A build that overruns ``timeout_seconds`` yields a structured ok:false result,
    not a raised ``subprocess.TimeoutExpired`` (mirrors the render-timeout contract)."""
    result = run_sdk_code(
        "import time\ntime.sleep(5)\n",
        session_id="slow",
        session_root=tmp_path,
        timeout_seconds=1,
        raster_png=False,
    )
    assert result["ok"] is False
    assert result["timed_out"] is True
    assert "timeout_seconds" in result["error"]
    assert result["validation"]["ok"] is False


def test_run_sdk_client_subprocess_timeout_returns_structured_error(tmp_path):
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "slow.py").write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    result = run_sdk_client(
        "examples/slow.py",
        session_id="slowcl",
        session_root=tmp_path / "sessions",
        repo_root=tmp_path,
        timeout_seconds=1,
        raster_png=False,
    )
    assert result["ok"] is False
    assert result["timed_out"] is True
    assert "timeout_seconds" in result["error"]
    assert result["client_path"].endswith("slow.py")


_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _multi_page_code(n: int) -> str:
    return f"""
from framegraph.sdk import DocumentBuilder

b = DocumentBuilder(title="Pages", profile="deck")
for i in range({n}):
    page = b.page(f"p{{i + 1}}", canvas={{"size": [160, 100], "units": "px"}})
    page.layer("main").rect([0, 0, 160, 100], fill="#ffffff")
    page.text([10, 10, 140, 24], f"PAGE-{{i + 1}}", id=f"t{{i}}")
doc = b.build()
"""


def _fake_rasterize_svg(svg, out_path, *, base_dir=None, scale=1.0, playwright_module=None):
    out = os.fspath(out_path)
    with open(out, "wb") as fh:
        fh.write(_PNG_1X1)
    from pathlib import Path as _P

    return _P(out)


def test_pages_selector_renders_only_named_pages_with_true_page_numbers(tmp_path):
    """`pages` selects specific 1-based pages; render entries carry the TRUE page number.

    Regression guard: the loop previously labelled renders with a post-slice sequential
    index, which is wrong for any non-prefix selection.
    """
    result = run_sdk_code(
        _multi_page_code(4), session_id="sel", session_root=tmp_path, pages="2-3", raster_png=False
    )

    assert result["ok"] is True
    svg_renders = [r for r in result["renders"] if r["mimeType"] == "image/svg+xml"]
    assert [r["page"] for r in svg_renders] == [2, 3]
    assert [r["uri"] for r in svg_renders] == [
        "framegraph://session/sel/page/2.svg",
        "framegraph://session/sel/page/3.svg",
    ]
    assert (tmp_path / "sel" / "page-002.svg").exists()
    assert (tmp_path / "sel" / "page-003.svg").exists()
    assert not (tmp_path / "sel" / "page-001.svg").exists()
    assert "PAGE-2" in (tmp_path / "sel" / "page-002.svg").read_text(encoding="utf-8")


def test_pages_selector_accepts_int_list(tmp_path):
    result = run_sdk_code(
        _multi_page_code(4), session_id="sellist", session_root=tmp_path, pages=[1, 4], raster_png=False
    )
    svg_renders = [r for r in result["renders"] if r["mimeType"] == "image/svg+xml"]
    assert [r["page"] for r in svg_renders] == [1, 4]


def test_mcp_content_blocks_caps_inlined_images(tmp_path):
    """Only the first N PNG renders are inlined as image blocks; the rest stay resource links."""
    import framegraph.mcp.server as server

    renders = []
    for page in range(1, 7):
        png = tmp_path / f"p{page:03d}.png"
        png.write_bytes(_PNG_1X1)
        renders.append({"page": page, "path": str(png), "mimeType": "image/png"})
    result = {"ok": True, "session_id": "cap", "renders": renders, "render_warning": None}

    blocks = server.mcp_content_blocks(result)

    image_blocks = [b for b in blocks if b["type"] == "image"]
    assert len(image_blocks) == server._max_inline_images()
    assert len(image_blocks) < len(renders)
    summary = json.loads(blocks[0]["text"])
    assert summary["images_total"] == 6
    assert summary["images_inlined"] == server._max_inline_images()


def test_rasterization_respects_page_cap_and_uses_true_page_filenames(tmp_path, monkeypatch):
    """P4: rasterization is capped; truncation is reported, ok stays True, PNGs keep true-page names."""
    import framegraph.mcp.server as server

    monkeypatch.setattr(
        "framegraph.rendering.infrastructure.browser.rasterize_svg", _fake_rasterize_svg
    )
    monkeypatch.setattr(server, "_raster_max_pages", lambda: 1)

    result = run_sdk_code(
        _multi_page_code(3), session_id="cap2", session_root=tmp_path, pages="2-3", raster_png=True
    )

    assert result["ok"] is True
    png_renders = [r for r in result["renders"] if r["mimeType"] == "image/png"]
    assert [r["page"] for r in png_renders] == [2]  # cap=1, first SELECTED page is 2
    assert (tmp_path / "cap2" / "p002.png").exists()
    assert png_renders[0]["uri"] == "framegraph://session/cap2/page/2.png"
    assert "render_warning" in result and "1 of 2" in result["render_warning"]
    # both selected pages still have SVG renders (only the raster was truncated)
    svg_renders = [r for r in result["renders"] if r["mimeType"] == "image/svg+xml"]
    assert [r["page"] for r in svg_renders] == [2, 3]


def test_rasterization_respects_time_budget(tmp_path, monkeypatch):
    """P4: a soft time budget stops the raster loop between pages with a structured warning."""
    import framegraph.mcp.server as server

    monkeypatch.setattr(
        "framegraph.rendering.infrastructure.browser.rasterize_svg", _fake_rasterize_svg
    )
    monkeypatch.setattr(server, "_raster_max_pages", lambda: 99)
    monkeypatch.setattr(server, "_raster_timeout", lambda: 1.0)
    # deadline base = 100.0; page-0 check 100.0 (<=101 -> rasterize); page-1 check 102.0 (> deadline -> stop)
    clock = iter([100.0, 100.0, 102.0, 102.0, 102.0])
    monkeypatch.setattr(server.time, "monotonic", lambda: next(clock))

    session_dir = tmp_path / "budget"
    session_dir.mkdir()
    pairs = []
    for page in (1, 2, 3):
        svg = session_dir / f"page-{page:03d}.svg"
        svg.write_text("<svg/>", encoding="utf-8")
        pairs.append((page, svg))

    renders, warning = server._try_rasterize_pngs(pairs, session_dir, "budget")

    assert [r["page"] for r in renders] == [1]
    assert warning is not None and "1 of 3" in warning


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
    assert "framegraph://session/{session_id}/page/{page_number}.png" in server.resources
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


# --- Finding 1: model-facing structuredContent must not carry unbounded streams ---


def test_clamp_stream_keeps_head_and_tail_with_marker():
    import framegraph.mcp.server as server

    limit = server.TRANSPORT_STREAM_MAX_CHARS
    text = "HEAD" + ("x" * (limit + 4_000)) + "TAIL"
    clamped = server._clamp_stream(text, limit)

    assert len(clamped) < len(text)
    assert clamped.startswith("HEAD")  # start of a traceback survives
    assert clamped.endswith("TAIL")  # the final exception line survives
    assert "truncated" in clamped
    # A stream within the limit is returned verbatim (no marker, identity).
    assert server._clamp_stream("small output", limit) == "small output"


def test_run_sdk_code_tool_bounds_streams_but_diagnostics_keep_full(tmp_path):
    """The transported structuredContent clamps stdout/stderr; the on-disk
    diagnostics resource keeps the full stream so debugging is not lost."""
    import framegraph.mcp.server as server

    noise = server.TRANSPORT_STREAM_MAX_CHARS + 5_000
    code = (
        f'print("N" * {noise})\n'
        "from framegraph.sdk import DocumentBuilder\n"
        'doc = DocumentBuilder(title="Chatty", profile="deck")\n'
        'page = doc.page("p1", canvas={"size": [120, 80], "units": "px"})\n'
        'page.layer("main").rect([0, 0, 120, 80], fill="#ffffff")\n'
        "doc.write(OUTPUT_YAML_PATH, fail_on_error=True)\n"
    )
    srv = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)

    result = srv.tools["run_sdk_code"](code, session_id="chatty", raster_png=False)
    structured = getattr(result, "structuredContent", result)

    # Transported copy is bounded and marked.
    assert structured["ok"] is True
    assert len(structured["stdout"]) < noise
    assert "truncated" in structured["stdout"]

    # Full stream is preserved on disk, reachable as a resource.
    diagnostics = read_session_resource(
        "framegraph://session/chatty/diagnostics.json", session_root=tmp_path
    )
    assert ("N" * 2_000) in diagnostics["text"]

    # The library function keeps full fidelity for non-MCP callers (e.g. the live server).
    full = server.run_sdk_code(code, session_id="lib", session_root=tmp_path, raster_png=False)
    assert len(full["stdout"]) >= noise


# --- Finding 2: tool input schemas describe their parameters ---


def test_tool_schemas_describe_their_parameters(tmp_path):
    server = create_server(session_root=tmp_path)  # real FastMCP builds the schema
    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}

    run_props = tools["run_sdk_code"].parameters["properties"]
    for param in ("code", "max_pages", "raster_png", "timeout_seconds", "pages", "session_id"):
        assert run_props[param].get("description"), f"run_sdk_code.{param} has no description"

    # detector_names was the worst offender: a bare list[str] with no hint of valid values.
    image_props = tools["propose_from_image"].parameters["properties"]
    detector_desc = image_props["detector_names"].get("description", "")
    assert "color_region" in detector_desc and "vlm" in detector_desc


# --- Finding 3: rendered PNG pages are addressable as resources, not just via a tool ---


def test_session_page_png_resource_returns_png_bytes(tmp_path):
    server = create_server(session_root=tmp_path, fastmcp_cls=FakeFastMCP)
    uri = "framegraph://session/{session_id}/page/{page_number}.png"
    assert uri in server.resources

    session_dir = tmp_path / "shot"
    session_dir.mkdir()
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )
    (session_dir / "p001.png").write_bytes(png_bytes)

    payload = server.resources[uri]("shot", "1")
    assert payload == png_bytes  # binary content returned as raw bytes, not base64 text


# --- text-fit telemetry: clipped text is surfaced even though the render is ok ---

CLIP_SCRIPT = """
from framegraph.sdk import DocumentBuilder
b = DocumentBuilder(title="clip", profile="diagram")
layer = b.page("p", canvas={"size": [200, 120], "units": "px"}, coordinate_mode="absolute").layer("m")
layer.text([10, 10, 120, 16],
           "This is a long sentence that cannot fit inside a sixteen pixel tall box and will be clipped.",
           style={"font_family": ["DejaVu Sans", "Arial"], "font_size": 14})
doc = b.build()
"""


def test_render_surfaces_clipped_text_fit_telemetry(tmp_path):
    """A render that clips text stays ok:true but reports text_fit + an advisory warning."""
    result = run_sdk_code(CLIP_SCRIPT, session_id="clip", session_root=tmp_path, raster_png=False)
    assert result["ok"] is True
    assert result["text_fit"]["clipped"] >= 1
    assert "clipped" in (result.get("render_warning") or "")


TWO_OBJECT_SCRIPT = """
from framegraph.sdk import DocumentBuilder
b = DocumentBuilder(title="two", profile="diagram")
m = b.page("p", canvas={"size": [100, 100], "units": "px"}, coordinate_mode="absolute").layer("m")
m.rect([0, 0, 50, 50], fill="#111")
m.rect([50, 50, 50, 50], fill="#222")
doc = b.build()
"""


def test_render_refuses_oversized_document_before_rendering(tmp_path, monkeypatch):
    """An over-cap document is refused up front (bounds the un-killable render thread)."""
    monkeypatch.setenv("FRAMEGRAPH_MCP_RENDER_MAX_OBJECTS", "1")
    result = run_sdk_code(TWO_OBJECT_SCRIPT, session_id="big", session_root=tmp_path, raster_png=False)
    assert result["ok"] is False
    assert "too large" in result["error"]
    assert result["renders"] == []
    assert result["validation"]["ok"] is True  # it's valid — just too large to render in-process


def test_mcp_guide_names_headline_sdk_capabilities():
    """The model-facing guide must keep naming the SDK's headline capabilities.

    The capability list inside FRAMEGRAPH_GUIDE is hand-maintained prose and has
    silently drifted before (it once omitted the figure-import lane and `text_style`).
    This pins that each headline public capability is both a real export and discoverable
    in the guide, so a new SDK capability cannot ship invisible to MCP agents.
    """
    import framegraph.sdk as sdk
    from framegraph.mcp.server import FRAMEGRAPH_GUIDE

    headline = [
        "DocumentBuilder", "stroke", "fill_stroke", "text_style",
        "Chart", "Scene3D", "Graph", "table", "badge",
        "place_figure", "FigureRef", "validate_static_rules",
    ]
    missing_export = [name for name in headline if name not in sdk.__all__]
    assert missing_export == [], f"headline names that are not public exports: {missing_export}"
    missing_guide = [name for name in headline if name not in FRAMEGRAPH_GUIDE]
    assert missing_guide == [], (
        f"FRAMEGRAPH_GUIDE omits headline SDK capabilities {missing_guide} — update the "
        "guide in framegraph/mcp/server.py when the SDK surface grows"
    )
