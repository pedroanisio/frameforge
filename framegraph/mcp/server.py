"""FrameGraph MCP server — composition root and backward-compatible facade.

The server's behaviour is split across focused modules (``config``, ``sessions``,
``execution``, ``pipeline``, ``sources``, ``usecases``, ``transport``, ``logging``,
``results``, ``security``, ``discovery``, ``clients``). This module wires them into a
FastMCP server via :func:`create_server` and re-exports the public + historically
module-level names so ``from framegraph.mcp.server import ...`` keeps working for the
live server, the package ``__init__``, and the test suite.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

# -- names create_server uses directly ------------------------------------------
from framegraph.mcp.config import DEFAULT_TIMEOUT_SECONDS
from framegraph.mcp.descriptions import (
    _DESC_CLIENT_PATH,
    _DESC_DETECTORS,
    _DESC_MAX_PAGES,
    _DESC_PAGES,
    _DESC_RASTER,
    _DESC_SESSION_ID,
    _DESC_SIGN,
    _DESC_SIGNED_AT,
    _DESC_SILHOUETTE,
    _DESC_TIMEOUT,
)
from framegraph.mcp.guide import FRAMEGRAPH_GUIDE
from framegraph.mcp.paths import _repo_root, _session_root
from framegraph.mcp.sessions import read_session_resource
from framegraph.mcp.logging import _logged_call, _structured_log_path
from framegraph.mcp.transport import _maybe_call_tool_result
from framegraph.mcp.util import _positive_int

# The tool wrappers call the use cases under aliases so the inner FastMCP-decorated
# functions can keep the public tool names without shadowing the use case (this is
# what the old ``globals()[...]`` indirection worked around — now made explicit).
from framegraph.mcp.clients import (
    list_sdk_clients as _uc_list_sdk_clients,
    read_sdk_client as _uc_read_sdk_client,
    write_sdk_client as _uc_write_sdk_client,
)
from framegraph.mcp.sessions import (
    cleanup_sessions as _uc_cleanup_sessions,
    list_sessions as _uc_list_sessions,
)
from framegraph.mcp.usecases import (
    propose_from_document as _uc_propose_from_document,
    propose_from_image as _uc_propose_from_image,
    propose_from_svg as _uc_propose_from_svg,
    render_framegraph_yaml as _uc_render_framegraph_yaml,
    run_sdk_client as _uc_run_sdk_client,
    run_sdk_code as _uc_run_sdk_code,
)

# -- backward-compatible re-exports ---------------------------------------------
# Re-exported (redundant-alias form marks the intent) so ``from
# framegraph.mcp.server import X`` and ``server.X`` keep resolving for the live
# server, the package __init__, and the test suite. Not used inside this module.
from framegraph.mcp.config import (
    STRUCTURED_LOG_MAX_FIELD_CHARS as STRUCTURED_LOG_MAX_FIELD_CHARS,
    TRANSPORT_STREAM_MAX_CHARS as TRANSPORT_STREAM_MAX_CHARS,
)
from framegraph.mcp.paths import (
    get_default_repo_root as get_default_repo_root,
    get_default_session_root as get_default_session_root,
)
from framegraph.mcp.clients import (
    list_sdk_clients as list_sdk_clients,
    read_sdk_client as read_sdk_client,
    write_sdk_client as write_sdk_client,
)
from framegraph.mcp.sessions import (
    cleanup_sessions as cleanup_sessions,
    list_sessions as list_sessions,
)
from framegraph.mcp.usecases import (
    propose_from_document as propose_from_document,
    propose_from_image as propose_from_image,
    propose_from_svg as propose_from_svg,
    render_framegraph_yaml as render_framegraph_yaml,
    run_sdk_client as run_sdk_client,
    run_sdk_code as run_sdk_code,
)
from framegraph.mcp.transport import (
    mcp_content_blocks as mcp_content_blocks,
    _clamp_stream as _clamp_stream,
    _max_inline_images as _max_inline_images,
)
from framegraph.mcp.logging import _append_structured_log as _append_structured_log
from framegraph.mcp.execution import _subprocess_env as _subprocess_env
from framegraph.mcp.discovery import (
    _framegraph_yaml_snapshot as _framegraph_yaml_snapshot,
    _new_generated_yaml as _new_generated_yaml,
)


def create_server(
    *,
    session_root: str | Path | None = None,
    repo_root: str | Path | None = None,
    edit_roots: str | list[str] | tuple[str, ...] | None = None,
    structured_log_path: str | Path | None = None,
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
    repo = _repo_root(repo_root)
    log_path = _structured_log_path(root, structured_log_path)
    server = fastmcp_cls(
        "FrameGraph",
        instructions=(
            "Execute or edit Python clients that use framegraph.sdk, inspect the "
            "generated FrameGraph YAML, and read rendered SVG artifacts for visual feedback."
        ),
    )

    @server.tool()
    def list_sdk_clients():
        """List editable Python SDK clients under the configured safe roots."""
        return _logged_call(
            log_path,
            "list_sdk_clients",
            {},
            lambda: _uc_list_sdk_clients(repo_root=repo, edit_roots=edit_roots),
        )

    @server.tool()
    def read_sdk_client(
        path: Annotated[str, Field(description=_DESC_CLIENT_PATH)],
    ) -> dict[str, Any]:
        """Read an editable Python SDK client file."""
        return _logged_call(
            log_path,
            "read_sdk_client",
            {"path": path},
            lambda: _uc_read_sdk_client(path, repo_root=repo, edit_roots=edit_roots),
        )

    @server.tool()
    def write_sdk_client(
        path: Annotated[str, Field(description=_DESC_CLIENT_PATH)],
        code: Annotated[str, Field(description="Full new contents of the SDK client file (replaces the file).")],
        create: Annotated[
            bool, Field(description="Allow creating the file when it does not yet exist; false requires an existing file.")
        ] = False,
    ) -> dict[str, Any]:
        """Replace or create an editable Python SDK client file."""
        return _logged_call(
            log_path,
            "write_sdk_client",
            {"path": path, "code": code, "create": create},
            lambda: _uc_write_sdk_client(path, code, create=create, repo_root=repo, edit_roots=edit_roots),
        )

    @server.tool()
    def run_sdk_client(
        path: Annotated[str, Field(description=_DESC_CLIENT_PATH)],
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
        timeout_seconds: Annotated[int, Field(description=_DESC_TIMEOUT)] = DEFAULT_TIMEOUT_SECONDS,
        max_pages: Annotated[int, Field(description=_DESC_MAX_PAGES)] = 3,
        raster_png: Annotated[bool, Field(description=_DESC_RASTER)] = True,
        invoke_main: Annotated[
            bool,
            Field(description="Execute the client as __main__ (runs its `if __name__ == '__main__'` block) instead of importing it."),
        ] = False,
        pages: Annotated[str | None, Field(description=_DESC_PAGES)] = None,
        sign: Annotated[bool, Field(description=_DESC_SIGN)] = False,
        signed_at: Annotated[str | None, Field(description=_DESC_SIGNED_AT)] = None,
        silhouette: Annotated[bool, Field(description=_DESC_SILHOUETTE)] = False,
    ):
        """Run an editable Python SDK client, validate its YAML, and return render feedback.

        ``pages`` selects specific 1-based pages to render (e.g. ``"6-10,15"``), overriding
        ``max_pages``; omit it to render the first ``max_pages`` pages (``<=0`` = all).
        """
        result = _logged_call(
            log_path,
            "run_sdk_client",
            {
                "path": path,
                "session_id": session_id,
                "timeout_seconds": timeout_seconds,
                "max_pages": max_pages,
                "raster_png": raster_png,
                "invoke_main": invoke_main,
                "pages": pages,
                "sign": sign,
                "signed_at": signed_at,
                "silhouette": silhouette,
            },
            lambda: _uc_run_sdk_client(
                path,
                session_id=session_id,
                session_root=root,
                timeout_seconds=timeout_seconds,
                max_pages=max_pages,
                raster_png=raster_png,
                invoke_main=invoke_main,
                pages=pages,
                sign=sign,
                signed_at=signed_at,
                silhouette=silhouette,
                repo_root=repo,
                edit_roots=edit_roots,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def run_sdk_code(
        code: Annotated[
            str,
            Field(description="Python source that uses framegraph.sdk and emits a document: write OUTPUT_YAML_PATH, or expose a doc/document/builder global or a build() function."),
        ],
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
        timeout_seconds: Annotated[int, Field(description=_DESC_TIMEOUT)] = DEFAULT_TIMEOUT_SECONDS,
        max_pages: Annotated[int, Field(description=_DESC_MAX_PAGES)] = 3,
        raster_png: Annotated[bool, Field(description=_DESC_RASTER)] = True,
        pages: Annotated[str | None, Field(description=_DESC_PAGES)] = None,
        sign: Annotated[bool, Field(description=_DESC_SIGN)] = False,
        signed_at: Annotated[str | None, Field(description=_DESC_SIGNED_AT)] = None,
        silhouette: Annotated[bool, Field(description=_DESC_SILHOUETTE)] = False,
    ):
        """Run Python SDK code, validate its YAML, and return render feedback.

        ``pages`` selects specific 1-based pages to render (e.g. ``"6-10,15"``), overriding
        ``max_pages``; omit it to render the first ``max_pages`` pages (``<=0`` = all).
        """
        result = _logged_call(
            log_path,
            "run_sdk_code",
            {
                "code": code,
                "session_id": session_id,
                "timeout_seconds": timeout_seconds,
                "max_pages": max_pages,
                "raster_png": raster_png,
                "pages": pages,
                "sign": sign,
                "signed_at": signed_at,
                "silhouette": silhouette,
            },
            lambda: _uc_run_sdk_code(
                code,
                session_id=session_id,
                session_root=root,
                timeout_seconds=timeout_seconds,
                max_pages=max_pages,
                raster_png=raster_png,
                pages=pages,
                sign=sign,
                signed_at=signed_at,
                silhouette=silhouette,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def render_framegraph_yaml(
        yaml_text: Annotated[
            str,
            Field(description="FrameGraph document as YAML text to validate and render directly, without executing any Python."),
        ],
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
        max_pages: Annotated[int, Field(description=_DESC_MAX_PAGES)] = 3,
        raster_png: Annotated[bool, Field(description=_DESC_RASTER)] = True,
        pages: Annotated[str | None, Field(description=_DESC_PAGES)] = None,
        sign: Annotated[bool, Field(description=_DESC_SIGN)] = False,
        signed_at: Annotated[str | None, Field(description=_DESC_SIGNED_AT)] = None,
        silhouette: Annotated[bool, Field(description=_DESC_SILHOUETTE)] = False,
    ):
        """Validate and render FrameGraph YAML without executing Python code.

        ``pages`` selects specific 1-based pages to render (e.g. ``"6-10,15"``), overriding
        ``max_pages``; omit it to render the first ``max_pages`` pages (``<=0`` = all).
        """
        result = _logged_call(
            log_path,
            "render_framegraph_yaml",
            {
                "yaml_text": yaml_text,
                "session_id": session_id,
                "max_pages": max_pages,
                "raster_png": raster_png,
                "pages": pages,
                "sign": sign,
                "signed_at": signed_at,
                "silhouette": silhouette,
            },
            lambda: _uc_render_framegraph_yaml(
                yaml_text,
                session_id=session_id,
                session_root=root,
                max_pages=max_pages,
                raster_png=raster_png,
                pages=pages,
                sign=sign,
                signed_at=signed_at,
                silhouette=silhouette,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def propose_from_image(
        image_path: Annotated[
            str | None, Field(description="Filesystem path to the source image. Provide this or image_base64.")
        ] = None,
        image_base64: Annotated[
            str | None, Field(description="Base64-encoded image bytes. Provide this or image_path.")
        ] = None,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
        max_pages: Annotated[int, Field(description=_DESC_MAX_PAGES)] = 3,
        raster_png: Annotated[bool, Field(description=_DESC_RASTER)] = True,
        pages: Annotated[str | None, Field(description=_DESC_PAGES)] = None,
        title: Annotated[str, Field(description="Title for the proposed draft document.")] = "Proposed from image",
        detector_names: Annotated[list[str] | None, Field(description=_DESC_DETECTORS)] = None,
    ):
        """Propose a DRAFT FrameGraph document from an image (OpenCV/numpy + optional VLM), then validate and render it."""
        result = _logged_call(
            log_path,
            "propose_from_image",
            {
                "image_path": image_path,
                "image_base64_bytes": len(image_base64) if image_base64 else 0,
                "session_id": session_id,
                "max_pages": max_pages,
                "raster_png": raster_png,
                "pages": pages,
                "title": title,
                "detector_names": detector_names,
            },
            lambda: _uc_propose_from_image(
                image_path,
                image_base64=image_base64,
                session_id=session_id,
                session_root=root,
                max_pages=max_pages,
                raster_png=raster_png,
                pages=pages,
                title=title,
                detector_names=detector_names,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def propose_from_document(
        path: Annotated[str, Field(description="Filesystem path to the source PDF.")],
        page: Annotated[int, Field(description="1-based PDF page number to rasterize and analyze.")] = 1,
        dpi: Annotated[
            int, Field(description="Resolution (DPI) to rasterize the PDF page at before detection.")
        ] = 144,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
        max_pages: Annotated[int, Field(description=_DESC_MAX_PAGES)] = 3,
        raster_png: Annotated[bool, Field(description=_DESC_RASTER)] = True,
        pages: Annotated[str | None, Field(description=_DESC_PAGES)] = None,
        title: Annotated[
            str | None, Field(description="Title for the proposed draft document; defaults to the source name.")
        ] = None,
        detector_names: Annotated[list[str] | None, Field(description=_DESC_DETECTORS)] = None,
    ):
        """Propose a DRAFT FrameGraph document from a rasterised PDF page, then validate and render it."""
        result = _logged_call(
            log_path,
            "propose_from_document",
            {
                "path": path,
                "page": page,
                "dpi": dpi,
                "session_id": session_id,
                "max_pages": max_pages,
                "raster_png": raster_png,
                "pages": pages,
                "title": title,
                "detector_names": detector_names,
            },
            lambda: _uc_propose_from_document(
                path,
                page=page,
                dpi=dpi,
                session_id=session_id,
                session_root=root,
                max_pages=max_pages,
                raster_png=raster_png,
                pages=pages,
                title=title,
                detector_names=detector_names,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def propose_from_svg(
        svg_path: Annotated[
            str | None, Field(description="Filesystem path to a .svg file. Provide this or svg_text.")
        ] = None,
        svg_text: Annotated[
            str | None, Field(description="SVG document as text. Provide this or svg_path.")
        ] = None,
        regions: Annotated[
            list[dict] | None,
            Field(description="Optional region-level grade: a list of "
                  '{"box": [x, y, w, h], "ramp": "#hex" | [[pos, "#hex"], ...]}. Each object is '
                  "recoloured by the region its centroid falls in (most-specific window first)."),
        ] = None,
        default_ramp: Annotated[
            Any,
            Field(description="Paint for objects in no region: a '#hex' string or a "
                  "[[pos, '#hex'], ...] ramp. Omit to leave unmatched objects unchanged."),
        ] = None,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
        max_pages: Annotated[int, Field(description=_DESC_MAX_PAGES)] = 3,
        raster_png: Annotated[bool, Field(description=_DESC_RASTER)] = True,
        pages: Annotated[str | None, Field(description=_DESC_PAGES)] = None,
        title: Annotated[str, Field(description="Title for the ingested document.")] = "Proposed from SVG",
    ):
        """Ingest an SVG into a FrameGraph document (1:1 vector lowering), optionally recolour it by region, then validate and render.

        Unlike ``propose_from_image`` (which re-detects from pixels), this lowers the
        SVG's own elements to FrameGraph primitives. ``regions`` applies a region-level
        colour grade; region clip/transform stay in the SDK (``place_region``) via
        ``run_sdk_code``.
        """
        result = _logged_call(
            log_path,
            "propose_from_svg",
            {
                "svg_path": svg_path,
                "svg_text_bytes": len(svg_text) if svg_text else 0,
                "regions": regions,
                "default_ramp": default_ramp,
                "session_id": session_id,
                "max_pages": max_pages,
                "raster_png": raster_png,
                "pages": pages,
                "title": title,
            },
            lambda: _uc_propose_from_svg(
                svg_path,
                svg_text=svg_text,
                regions=regions,
                default_ramp=default_ramp,
                session_id=session_id,
                session_root=root,
                max_pages=max_pages,
                raster_png=raster_png,
                pages=pages,
                title=title,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.prompt()
    def framegraph_guide() -> str:
        """Guide to what the FrameGraph SDK offers and the server's authoring + proposal tools."""
        return _logged_call(log_path, "prompt.framegraph_guide", {}, lambda: FRAMEGRAPH_GUIDE)

    @server.tool()
    def get_session_resource(
        uri: Annotated[
            str,
            Field(description="A framegraph://session/<id>/<artifact> URI: document.yaml, diagnostics.json, page/N.svg, or page/N.png. Prefer the registered resources; this tool exists for clients that do not surface resources."),
        ],
    ) -> dict[str, str]:
        """Read a FrameGraph MCP session resource by URI."""
        return _logged_call(
            log_path,
            "get_session_resource",
            {"uri": uri},
            lambda: read_session_resource(uri, session_root=root),
        )

    @server.tool()
    def list_sessions() -> dict[str, Any]:
        """List per-session scratch directories with their artifact counts and size."""
        return _logged_call(
            log_path,
            "list_sessions",
            {},
            lambda: _uc_list_sessions(session_root=root),
        )

    @server.tool()
    def cleanup_sessions(
        session_ids: Annotated[
            list[str] | None,
            Field(description="Remove exactly these session ids. Takes precedence over older_than_seconds."),
        ] = None,
        older_than_seconds: Annotated[
            float | None,
            Field(description="Remove sessions whose directory is older than this many seconds (used only when session_ids is omitted)."),
        ] = None,
        dry_run: Annotated[
            bool, Field(description="Report the selection without deleting anything.")
        ] = False,
    ) -> dict[str, Any]:
        """Remove session scratch dirs by id or age (no selector removes nothing)."""
        return _logged_call(
            log_path,
            "cleanup_sessions",
            {"session_ids": session_ids, "older_than_seconds": older_than_seconds, "dry_run": dry_run},
            lambda: _uc_cleanup_sessions(
                session_root=root,
                session_ids=session_ids,
                older_than_seconds=older_than_seconds,
                dry_run=dry_run,
            ),
        )

    @server.resource("framegraph://session/{session_id}/document.yaml")
    def session_document(session_id: str) -> str:
        return _logged_call(
            log_path,
            "resource.session_document",
            {"session_id": session_id},
            lambda: read_session_resource(
                f"framegraph://session/{session_id}/document.yaml",
                session_root=root,
            )["text"],
        )

    @server.resource("framegraph://session/{session_id}/page/{page_number}.svg")
    def session_page(session_id: str, page_number: str) -> str:
        page = _positive_int(page_number, "page_number")
        return _logged_call(
            log_path,
            "resource.session_page",
            {"session_id": session_id, "page_number": page_number},
            lambda: read_session_resource(
                f"framegraph://session/{session_id}/page/{page}.svg",
                session_root=root,
            )["text"],
        )

    @server.resource(
        "framegraph://session/{session_id}/page/{page_number}.png", mime_type="image/png"
    )
    def session_page_png(session_id: str, page_number: str) -> bytes:
        page = _positive_int(page_number, "page_number")
        payload = _logged_call(
            log_path,
            "resource.session_page_png",
            {"session_id": session_id, "page_number": page_number},
            lambda: read_session_resource(
                f"framegraph://session/{session_id}/page/{page}.png",
                session_root=root,
            ),
        )
        return base64.b64decode(payload["blob"])

    @server.resource("framegraph://session/{session_id}/diagnostics.json")
    def session_diagnostics(session_id: str) -> str:
        return _logged_call(
            log_path,
            "resource.session_diagnostics",
            {"session_id": session_id},
            lambda: read_session_resource(
                f"framegraph://session/{session_id}/diagnostics.json",
                session_root=root,
            )["text"],
        )

    return server


def run() -> None:
    """Run the FrameGraph MCP server over the default FastMCP transport."""
    create_server().run()


__all__ = [
    "create_server",
    "run",
    "run_sdk_code",
    "run_sdk_client",
    "render_framegraph_yaml",
    "propose_from_image",
    "propose_from_document",
    "list_sdk_clients",
    "read_sdk_client",
    "write_sdk_client",
    "read_session_resource",
    "list_sessions",
    "cleanup_sessions",
    "mcp_content_blocks",
    "get_default_session_root",
    "get_default_repo_root",
    "FRAMEGRAPH_GUIDE",
]
