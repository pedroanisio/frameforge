"""Model Context Protocol tools for SDK-code render feedback.

The public contract is intentionally narrow: callers provide Python code that
uses :mod:`framegraph.sdk`, the code emits or yields a FrameGraph document, and
this module validates and renders that generated YAML into per-session artifacts.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import unquote, urlparse

from framegraph.sdk.conform import render_page_svgs
from framegraph.sdk.io import parse, serialize
from framegraph.sdk.validate import ValidationReport, validate_static_rules

SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
DEFAULT_TIMEOUT_SECONDS = 10
MAX_CODE_BYTES = 200_000


def get_default_session_root() -> Path:
    """Return the default location for MCP session artifacts."""
    configured = os.environ.get("FRAMEGRAPH_MCP_SESSION_ROOT")
    if configured:
        return Path(configured).expanduser()
    return Path(tempfile.gettempdir()) / "framegraph-mcp-sessions"


def run_sdk_code(
    code: str,
    *,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_pages: int = 3,
    raster_png: bool = False,
) -> dict[str, Any]:
    """Execute Python SDK code, then validate and render its generated YAML.

    The executed code receives two globals:

    - ``SESSION_DIR``: path to the per-session scratch directory.
    - ``OUTPUT_YAML_PATH``: path where generated FrameGraph YAML should be written.

    If ``OUTPUT_YAML_PATH`` is not written, the harness derives YAML from a global
    named ``doc``, ``document``, or ``builder`` when it can.
    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code must be a non-empty string")
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        raise ValueError(f"code exceeds {MAX_CODE_BYTES} bytes")

    root = _session_root(session_root)
    sid = _session_id(session_id)
    session_dir = _prepare_session(root, sid)
    script_path = session_dir / "script.py"
    harness_path = session_dir / "_run_sdk.py"
    yaml_path = session_dir / "generated.fg.yaml"
    script_path.write_text(code, encoding="utf-8")
    harness_path.write_text(_harness_source(script_path, yaml_path, session_dir), encoding="utf-8")

    env = _subprocess_env()
    proc = subprocess.run(
        [sys.executable, str(harness_path)],
        cwd=str(session_dir),
        env=env,
        text=True,
        capture_output=True,
        timeout=max(1, int(timeout_seconds)),
        check=False,
    )

    result = _base_result(sid, session_dir, yaml_path, proc.stdout, proc.stderr, proc.returncode)
    if proc.returncode != 0:
        result["ok"] = False
        result["error"] = "sdk code exited with a non-zero status"
        _write_diagnostics(session_dir, result)
        return result
    if not yaml_path.exists():
        result["ok"] = False
        result["error"] = "sdk code did not generate FrameGraph YAML"
        _write_diagnostics(session_dir, result)
        return result

    rendered = _validate_and_render_yaml(
        yaml_path.read_text(encoding="utf-8"),
        session_id=sid,
        session_dir=session_dir,
        base_dir=session_dir,
        max_pages=max_pages,
        raster_png=raster_png,
    )
    result.update(rendered)
    _write_diagnostics(session_dir, result)
    return result


def render_framegraph_yaml(
    yaml_text: str,
    *,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    max_pages: int = 3,
    raster_png: bool = False,
) -> dict[str, Any]:
    """Validate and render caller-provided FrameGraph YAML."""
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        raise ValueError("yaml_text must be a non-empty string")
    root = _session_root(session_root)
    sid = _session_id(session_id)
    session_dir = _prepare_session(root, sid)
    yaml_path = session_dir / "generated.fg.yaml"
    yaml_path.write_text(yaml_text, encoding="utf-8")

    result = _base_result(sid, session_dir, yaml_path, "", "", 0)
    result.update(
        _validate_and_render_yaml(
            yaml_text,
            session_id=sid,
            session_dir=session_dir,
            base_dir=session_dir,
            max_pages=max_pages,
            raster_png=raster_png,
        )
    )
    _write_diagnostics(session_dir, result)
    return result


def read_session_resource(uri: str, *, session_root: str | Path | None = None) -> dict[str, str]:
    """Read a ``framegraph://session/...`` artifact as an MCP resource payload."""
    root = _session_root(session_root)
    parsed = urlparse(uri)
    if parsed.scheme != "framegraph" or parsed.netloc != "session":
        raise ValueError("resource URI must start with framegraph://session/")
    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("resource URI is missing a session id and artifact path")
    sid = _session_id(parts[0])
    session_dir = (root / sid).resolve()
    if not _is_relative_to(session_dir, root.resolve()):
        raise ValueError("resource URI escapes the session root")

    artifact = parts[1:]
    if artifact == ["document.yaml"]:
        path = session_dir / "generated.fg.yaml"
        mime = "application/x-yaml"
    elif artifact == ["diagnostics.json"]:
        path = session_dir / "diagnostics.json"
        mime = "application/json"
    elif len(artifact) == 2 and artifact[0] == "page" and artifact[1].endswith(".svg"):
        page_number = artifact[1][:-4]
        path = session_dir / _page_svg_name(_positive_int(page_number, "page_number"))
        mime = "image/svg+xml"
    elif len(artifact) == 2 and artifact[0] == "page" and artifact[1].endswith(".png"):
        page_number = artifact[1][:-4]
        path = session_dir / f"p{_positive_int(page_number, 'page_number'):03d}.png"
        mime = "image/png"
    else:
        raise ValueError(f"unsupported resource artifact: {'/'.join(artifact)!r}")

    if not path.exists():
        raise FileNotFoundError(str(path))
    if mime == "image/png":
        return {
            "uri": uri,
            "mimeType": mime,
            "blob": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
    return {"uri": uri, "mimeType": mime, "text": path.read_text(encoding="utf-8")}


def mcp_content_blocks(result: dict[str, Any]) -> list[dict[str, str]]:
    """Return MCP-style text/image content blocks for a run result."""
    summary = {
        "ok": result.get("ok"),
        "session_id": result.get("session_id"),
        "yaml_uri": result.get("yaml_uri"),
        "diagnostics_uri": result.get("diagnostics_uri"),
        "validation": result.get("validation"),
        "renders": [
            {key: render.get(key) for key in ("page", "uri", "mimeType", "sha256") if key in render}
            for render in result.get("renders", [])
        ],
        "error": result.get("error"),
    }
    blocks: list[dict[str, str]] = [
        {"type": "text", "text": json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)}
    ]
    for render in result.get("renders", []):
        path_value = render.get("path")
        mime = render.get("mimeType")
        if not path_value or not mime or not str(mime).startswith("image/"):
            continue
        data = Path(path_value).read_bytes()
        blocks.append(
            {
                "type": "image",
                "data": base64.b64encode(data).decode("ascii"),
                "mimeType": str(mime),
            }
        )
    return blocks


def create_server(
    *,
    session_root: str | Path | None = None,
    fastmcp_cls: Any | None = None,
):
    """Create the FastMCP server exposing the FrameGraph feedback tools."""
    if fastmcp_cls is None:
        try:
            from mcp.server.fastmcp import FastMCP as fastmcp_cls
        except ImportError as exc:
            raise RuntimeError(
                "The FrameGraph MCP server requires the optional `mcp` dependency group. "
                "Install it with `uv sync --group mcp`."
            ) from exc

    root = _session_root(session_root)
    server = fastmcp_cls(
        "FrameGraph",
        instructions=(
            "Execute Python code that uses framegraph.sdk, inspect the generated "
            "FrameGraph YAML, and read rendered SVG artifacts for visual feedback."
        ),
    )

    @server.tool()
    def run_sdk_code(
        code: str,
        session_id: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_pages: int = 3,
        raster_png: bool = False,
    ):
        """Run Python SDK code, validate its YAML, and return render feedback."""
        result = globals()["run_sdk_code"](
            code,
            session_id=session_id,
            session_root=root,
            timeout_seconds=timeout_seconds,
            max_pages=max_pages,
            raster_png=raster_png,
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def render_framegraph_yaml(
        yaml_text: str,
        session_id: str | None = None,
        max_pages: int = 3,
        raster_png: bool = False,
    ):
        """Validate and render FrameGraph YAML without executing Python code."""
        result = globals()["render_framegraph_yaml"](
            yaml_text,
            session_id=session_id,
            session_root=root,
            max_pages=max_pages,
            raster_png=raster_png,
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def get_session_resource(uri: str) -> dict[str, str]:
        """Read a FrameGraph MCP session resource by URI."""
        return read_session_resource(uri, session_root=root)

    @server.resource("framegraph://session/{session_id}/document.yaml")
    def session_document(session_id: str) -> str:
        return read_session_resource(
            f"framegraph://session/{session_id}/document.yaml",
            session_root=root,
        )["text"]

    @server.resource("framegraph://session/{session_id}/page/{page_number}.svg")
    def session_page(session_id: str, page_number: str) -> str:
        page = _positive_int(page_number, "page_number")
        return read_session_resource(
            f"framegraph://session/{session_id}/page/{page}.svg",
            session_root=root,
        )["text"]

    @server.resource("framegraph://session/{session_id}/diagnostics.json")
    def session_diagnostics(session_id: str) -> str:
        return read_session_resource(
            f"framegraph://session/{session_id}/diagnostics.json",
            session_root=root,
        )["text"]

    return server


def run() -> None:
    """Run the FrameGraph MCP server over the default FastMCP transport."""
    create_server().run()


def _session_root(session_root: str | Path | None) -> Path:
    root = Path(session_root) if session_root is not None else get_default_session_root()
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_id(session_id: str | None) -> str:
    sid = session_id or "session"
    if not SESSION_ID_RE.fullmatch(sid):
        raise ValueError("session_id must match [A-Za-z0-9][A-Za-z0-9_.-]{0,79}")
    return sid


def _prepare_session(root: Path, session_id: str) -> Path:
    session_dir = (root / session_id).resolve()
    if not _is_relative_to(session_dir, root):
        raise ValueError("session_id escapes the session root")
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _subprocess_env() -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[2]
    pythonpath = str(repo_root)
    if os.environ.get("PYTHONPATH"):
        pythonpath = pythonpath + os.pathsep + os.environ["PYTHONPATH"]
    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath
    return env


def _harness_source(script_path: Path, yaml_path: Path, session_dir: Path) -> str:
    return f"""\
from pathlib import Path

from framegraph.sdk.io import serialize

SESSION_DIR = {str(session_dir)!r}
OUTPUT_YAML_PATH = {str(yaml_path)!r}
namespace = {{
    "__file__": {str(script_path)!r},
    "__name__": "__main__",
    "SESSION_DIR": SESSION_DIR,
    "OUTPUT_YAML_PATH": OUTPUT_YAML_PATH,
}}
source = Path({str(script_path)!r}).read_text(encoding="utf-8")
exec(compile(source, {str(script_path)!r}, "exec"), namespace)
out = Path(OUTPUT_YAML_PATH)
if not out.exists():
    candidate = None
    for name in ("doc", "document", "builder"):
        value = namespace.get(name)
        if value is not None:
            candidate = value
            break
    if candidate is not None and hasattr(candidate, "build"):
        candidate = candidate.build()
    if candidate is None:
        raise SystemExit("no FrameGraph document found; write OUTPUT_YAML_PATH or set doc/document/builder")
    out.write_text(serialize(candidate, format="yaml"), encoding="utf-8")
"""


def _base_result(
    session_id: str,
    session_dir: Path,
    yaml_path: Path,
    stdout: str,
    stderr: str,
    returncode: int,
) -> dict[str, Any]:
    return {
        "ok": True,
        "session_id": session_id,
        "session_dir": str(session_dir),
        "yaml_path": str(yaml_path),
        "yaml_uri": f"framegraph://session/{session_id}/document.yaml",
        "diagnostics_path": str(session_dir / "diagnostics.json"),
        "diagnostics_uri": f"framegraph://session/{session_id}/diagnostics.json",
        "stdout": stdout,
        "stderr": stderr,
        "returncode": returncode,
        "validation": {"ok": False, "issues": []},
        "renders": [],
        "resources": [],
    }


def _validate_and_render_yaml(
    yaml_text: str,
    *,
    session_id: str,
    session_dir: Path,
    base_dir: Path,
    max_pages: int,
    raster_png: bool,
) -> dict[str, Any]:
    try:
        document = parse(yaml_text, forgiving=False)
        report = validate_static_rules(document)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"FrameGraph YAML validation failed: {exc}",
            "validation": {"ok": False, "issues": [{"severity": "error", "message": str(exc)}]},
            "renders": [],
            "resources": _resource_links(session_id, renders=[]),
        }

    renders: list[dict[str, Any]] = []
    if report.ok:
        svgs = render_page_svgs(document, base_dir=str(base_dir))
        for index, svg in enumerate(svgs[: max(0, int(max_pages)) or len(svgs)], 1):
            path = session_dir / _page_svg_name(index)
            path.write_text(svg, encoding="utf-8")
            renders.append(
                {
                    "page": index,
                    "path": str(path),
                    "uri": f"framegraph://session/{session_id}/page/{index}.svg",
                    "mimeType": "image/svg+xml",
                    "sha256": _sha256_text(svg),
                    "bytes": len(svg.encode("utf-8")),
                }
            )
        if raster_png:
            renders.extend(_try_rasterize_pngs([Path(item["path"]) for item in renders], session_dir, session_id))

    return {
        "ok": report.ok and bool(renders),
        "validation": _validation_payload(report),
        "renders": renders,
        "resources": _resource_links(session_id, renders=renders),
    }


def _validation_payload(report: ValidationReport) -> dict[str, Any]:
    return {
        "ok": report.ok,
        "issues": [
            {
                "rule_id": issue.rule_id,
                "severity": issue.severity,
                "path": issue.path,
                "message": issue.message,
            }
            for issue in report.issues
        ],
    }


def _resource_links(session_id: str, *, renders: list[dict[str, Any]]) -> list[dict[str, str]]:
    links = [
        {
            "type": "resource_link",
            "uri": f"framegraph://session/{session_id}/document.yaml",
            "name": "generated.fg.yaml",
            "mimeType": "application/x-yaml",
        },
        {
            "type": "resource_link",
            "uri": f"framegraph://session/{session_id}/diagnostics.json",
            "name": "diagnostics.json",
            "mimeType": "application/json",
        },
    ]
    for render in renders:
        path = Path(str(render.get("path", "")))
        links.append(
            {
                "type": "resource_link",
                "uri": str(render["uri"]),
                "name": path.name or f"page-{int(render['page']):03d}",
                "mimeType": str(render["mimeType"]),
            }
        )
    return links


def _maybe_call_tool_result(result: dict[str, Any]):
    try:
        from mcp.types import CallToolResult, ImageContent, TextContent
    except ImportError:
        return result

    content = []
    for block in mcp_content_blocks(result):
        if block["type"] == "text":
            content.append(TextContent(type="text", text=block["text"]))
        elif block["type"] == "image":
            content.append(
                ImageContent(
                    type="image",
                    data=block["data"],
                    mimeType=block["mimeType"],
                )
            )
    return CallToolResult(content=content, structuredContent=result, isError=not result.get("ok", False))


def _try_rasterize_pngs(svg_paths: list[Path], session_dir: Path, session_id: str) -> list[dict[str, Any]]:
    from framegraph.rendering.infrastructure.browser import BrowserRendererUnavailable, rasterize_svgs

    svgs = [path.read_text(encoding="utf-8") for path in svg_paths]
    try:
        pngs = rasterize_svgs(svgs, session_dir, base_dir=str(session_dir))
    except BrowserRendererUnavailable:
        return []
    renders = []
    for index, path in enumerate(pngs, 1):
        renders.append(
            {
                "page": index,
                "path": str(path),
                "uri": f"framegraph://session/{session_id}/page/{index}.png",
                "mimeType": "image/png",
                "bytes": path.stat().st_size,
            }
        )
    return renders


def _write_diagnostics(session_dir: Path, result: dict[str, Any]) -> None:
    safe = dict(result)
    safe["content"] = mcp_content_blocks(result)[:1]
    (session_dir / "diagnostics.json").write_text(
        json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _page_svg_name(page: int) -> str:
    return f"page-{page:03d}.svg"


def _positive_int(value: str, name: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if number < 1:
        raise ValueError(f"{name} must be positive")
    return number


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    run()
