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
import json
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

# -- names create_server uses directly ------------------------------------------
from framegraph.mcp.config import DEFAULT_TIMEOUT_SECONDS
from framegraph.mcp.descriptions import (
    _DESC_CLIENT_PATH,
    _DESC_COACH_MODES,
    _DESC_COACH_PAINT,
    _DESC_COACH_STYLE,
    _DESC_DETECTORS,
    _DESC_MAX_PAGES,
    _DESC_PAGES,
    _DESC_RASTER,
    _DESC_REAL_METRICS,
    _DESC_REGION_METHOD,
    _DESC_REGION_TUNABLES,
    _DESC_SCALE,
    _DESC_SESSION_ID,
    _DESC_SIGN,
    _DESC_SIGNED_AT,
    _DESC_SILHOUETTE,
    _DESC_TIMEOUT,
    _DESC_TO,
    _DESC_TOPIC,
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
from framegraph.mcp.discovery import (
    describe_capabilities as _uc_describe_capabilities,
    list_fonts as _uc_list_fonts,
)
from framegraph.mcp.usecases import (
    apply_anchored_edit as _uc_apply_anchored_edit,
    compare_images as _uc_compare_images,
    construct_vectors as _uc_construct_vectors,
    detect_regions as _uc_detect_regions,
    map_coordinates as _uc_map_coordinates,
    mark_points as _uc_mark_points,
    measure_image as _uc_measure_image,
    overlay_images as _uc_overlay_images,
    score_reconstruction as _uc_score_reconstruction,
    vectorize_image as _uc_vectorize_image,
    workspace as _uc_workspace,
    coach_vectorize as _uc_coach_vectorize,
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
    compare_images as compare_images,
    construct_vectors as construct_vectors,
    detect_regions as detect_regions,
    map_coordinates as map_coordinates,
    mark_points as mark_points,
    measure_image as measure_image,
    overlay_images as overlay_images,
    score_reconstruction as score_reconstruction,
    vectorize_image as vectorize_image,
    workspace as workspace,
    coach_vectorize as coach_vectorize,
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
    describe_capabilities as describe_capabilities,
    list_fonts as list_fonts,
    _framegraph_yaml_snapshot as _framegraph_yaml_snapshot,
    _new_generated_yaml as _new_generated_yaml,
)


# --------------------------------------------------------------------------- #
#  Tool error envelope + result shaping                                       #
# --------------------------------------------------------------------------- #


def _tool_failure_hint(tool: str, exc: BaseException) -> str | None:
    """An actionable next step for the common expected tool failures."""
    message = str(exc)
    if isinstance(exc, SyntaxError):
        return "the client code must be valid Python — fix the syntax error and retry"
    if isinstance(exc, FileNotFoundError):
        if tool in ("read_sdk_client", "write_sdk_client", "run_sdk_client"):
            return (
                "call list_sdk_clients to see the editable client files "
                "(its allowed_roots field names the writable directories)"
            )
        if tool == "get_session_resource":
            return (
                "call list_sessions to see which sessions exist; every render tool resets "
                "page-*.svg/p*.png in its session, so only the LAST call's artifacts remain"
            )
        return (
            "check the path — image arguments accept a filesystem path or a "
            "framegraph://session/<id>/page/<n>.png URI"
        )
    if "allowed SDK client roots" in message:
        return (
            "call list_sdk_clients — its allowed_roots field lists the writable directories "
            "(configure with FRAMEGRAPH_MCP_EDIT_ROOTS)"
        )
    if "session_id" in message:
        return (
            "session ids must match [A-Za-z0-9][A-Za-z0-9_.-]{0,79}; omit session_id for the "
            "default 'session'"
        )
    if "FRAMEGRAPH_MCP_INPUT_ROOTS" in message:
        return (
            "the server confines input paths to FRAMEGRAPH_MCP_INPUT_ROOTS; move the file "
            "under an allowed root or adjust that variable"
        )
    if "resource URI" in message or "framegraph://" in message:
        return (
            "session resource URIs look like framegraph://session/<id>/ + document.yaml | "
            "document.pdf | page/<n>.svg | page/<n>.png | diagnostics.json | workspace.json"
        )
    return None


def _error_envelope(tool: str, exc: BaseException) -> dict[str, Any]:
    """The shared structured-failure shape every tool returns instead of raising."""
    envelope: dict[str, Any] = {
        "ok": False,
        "error": str(exc) or type(exc).__name__,
        "error_type": type(exc).__name__,
        "renders": [],
        "resources": [],
    }
    hint = _tool_failure_hint(tool, exc)
    if hint:
        envelope["hint"] = hint
    return envelope


def _enveloped(tool: str, call):
    """Run a use case, lowering expected input/filesystem failures into the envelope.

    Unexpected exceptions still raise (and are logged) — masking a genuine bug as
    an input error would hide it from the operator (fix root causes, PALS's Law).
    """
    try:
        return call()
    except (ValueError, OSError, SyntaxError) as exc:
        return _error_envelope(tool, exc)


def _logged_enveloped_call(log_path: Path, tool: str, instruction: dict[str, Any], call):
    """`_logged_call` with the expected-failure envelope applied to the call.

    The log then records the envelope the client actually received, not a raise.
    """
    return _logged_call(log_path, tool, instruction, lambda: _enveloped(tool, call))


def _plain_tool_result(result: Any):
    """CallToolResult for dict-returning tools: full JSON text + a real isError flag.

    The render tools go through :func:`_maybe_call_tool_result` (image blocks +
    summary); the plain dict tools previously returned raw dicts, so ``isError``
    was never meaningful for them. The full JSON stays the text block (nothing
    like ``code`` may be summarized away). Without the ``mcp`` package the dict
    passes through unchanged, exactly like ``_maybe_call_tool_result``.
    """
    if not isinstance(result, dict):
        return result
    try:
        from mcp.types import CallToolResult, TextContent
    except ImportError:
        return result
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
            )
        ],
        structuredContent=result,
        isError=result.get("ok", True) is False,
    )


def _registered_tool_names(server: Any) -> list[str]:
    """The live tool names, from FastMCP's manager or a test double's registry."""
    manager = getattr(server, "_tool_manager", None)
    if manager is not None:
        try:
            return sorted(tool.name for tool in manager.list_tools())
        except (AttributeError, TypeError):
            pass
    tools = getattr(server, "tools", None)
    if isinstance(tools, dict):
        return sorted(tools)
    return []


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
            "FrameGraph is a document/graphics DSL: author with the Python SDK, this "
            "server validates + renders it, and you verify against the rendered pixels. "
            "Capabilities, by group:\n"
            "• Author → render: run_sdk_code / run_sdk_client / render_framegraph_yaml "
            "(build a doc, get validation issues + a PNG); write_sdk_client / "
            "read_sdk_client / list_sdk_clients (edit whitelisted clients). The full SDK "
            "is importable in run_sdk_code — incl. sdk.planar (Pathfinder booleans / "
            "offset / path surgery / region fills), sdk.outline (stroke_outline width "
            "profiles + calligraphic pen, repeat_along_path brushes), recolor + "
            "chevreul.color_guide, ordered `effects` + multi-pass `appearance` object "
            "fields, framegraph.patterns (375-pattern catalog, compose) and "
            "framegraph.library (7 themes, symbol packs, honeycomb/module generators); "
            "v0.1-dialect documents migrate via tooling/codemod.py --from-v01.\n"
            "• Image → draft: propose_from_image / propose_from_document / propose_from_svg "
            "(UNVERIFIED drafts, round-tripped through render).\n"
            "• Visual QA: compare_images (zoomed reference|candidate|diff panels + real "
            "NCC/RMSE/MAE metrics; align=True phase-aligns first).\n"
            "• Coordinate-aware reconstruction (raster → precise vectors): measure_image "
            "(grid + rulers + coordinate system + regions + landmarks + zoom crops), "
            "mark_points (resolve points in every frame), overlay_images (landmark "
            "alignment + offsets), workspace (a stateful pin board — the AI 'mouse': "
            "pin / nudge / move / snap / transform / pan / zoom / checkpoint+revert, "
            "multi-pass refine, state persists per session_id), detect_regions (what "
            "closed/filled/stable regions does an image contain — exact bbox/centroid/"
            "fill/polygon per region, three methods + shape clustering), construct_vectors "
            "(draw SDK geometry from anchor points), vectorize_image (AUTO trace: auto / "
            "region / outline / trace(potrace) / layers), score_reconstruction (NUMERIC convergence: "
            "how far the drawn vectors sit from the source's edges — on_edge_frac / "
            "mean_dist, complements compare_images), map_coordinates (homography / 2D↔3D / "
            "warp image rectification).\n"
            "• Sessions/resources: artifacts live at framegraph://session/<id>/... "
            "(document.yaml, page/<n>.svg, page/<n>.png, diagnostics.json, workspace.json).\n"
            "ARCHITECTURAL CONTRACT (PALS's Law): all CV/LLM output is unverified by "
            "default — verify every result against the rendered PNG, never the YAML alone. "
            "Call the `framegraph_guide` prompt for the full SDK + workflow reference."
        ),
    )

    @server.tool()
    def list_sdk_clients():
        """List editable Python SDK clients under the configured safe roots."""
        return _plain_tool_result(_logged_call(
            log_path,
            "list_sdk_clients",
            {},
            lambda: _enveloped(
                "list_sdk_clients",
                lambda: _uc_list_sdk_clients(repo_root=repo, edit_roots=edit_roots),
            ),
        ))

    @server.tool()
    def read_sdk_client(
        path: Annotated[str, Field(description=_DESC_CLIENT_PATH)],
    ):
        """Read an editable Python SDK client file."""
        return _plain_tool_result(_logged_call(
            log_path,
            "read_sdk_client",
            {"path": path},
            lambda: _enveloped(
                "read_sdk_client",
                lambda: _uc_read_sdk_client(path, repo_root=repo, edit_roots=edit_roots),
            ),
        ))

    @server.tool()
    def write_sdk_client(
        path: Annotated[str, Field(description=_DESC_CLIENT_PATH)],
        code: Annotated[
            str | None,
            Field(description="Full new contents of the SDK client file (replaces the file). Omit when using old_string/new_string."),
        ] = None,
        create: Annotated[
            bool, Field(description="Allow creating the file when it does not yet exist; false requires an existing file.")
        ] = False,
        old_string: Annotated[
            str | None,
            Field(description="Anchored edit: the exact text to replace. Must match the current file exactly once (extend with surrounding lines until unique). Use with new_string instead of `code`."),
        ] = None,
        new_string: Annotated[
            str | None,
            Field(description="Anchored edit: the replacement text for old_string."),
        ] = None,
    ):
        """Replace, create, or anchored-edit an editable Python SDK client file.

        Two modes: full replace (pass ``code``) or an anchored edit (pass
        ``old_string`` + ``new_string`` — an exact-match, single-occurrence
        replacement, so iterating on a large client does not re-transmit it).
        """
        def _call():
            if old_string is not None or new_string is not None:
                if code is not None:
                    raise ValueError("pass either full `code` or an old_string/new_string edit, not both")
                if old_string is None or new_string is None:
                    raise ValueError("an anchored edit needs both old_string and new_string")
                current = _uc_read_sdk_client(path, repo_root=repo, edit_roots=edit_roots)["code"]
                edited = _uc_apply_anchored_edit(current, old_string, new_string)
                return _uc_write_sdk_client(path, edited, create=False, repo_root=repo, edit_roots=edit_roots)
            if code is None:
                raise ValueError("provide `code` (full replace) or old_string/new_string (anchored edit)")
            return _uc_write_sdk_client(path, code, create=create, repo_root=repo, edit_roots=edit_roots)

        return _plain_tool_result(_logged_call(
            log_path,
            "write_sdk_client",
            {"path": path, "code": code, "create": create,
             "old_string": old_string, "new_string": new_string},
            lambda: _enveloped("write_sdk_client", _call),
        ))

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
        to: Annotated[str, Field(description=_DESC_TO)] = "png",
        scale: Annotated[float, Field(description=_DESC_SCALE)] = 1.0,
        real_metrics: Annotated[bool | str, Field(description=_DESC_REAL_METRICS)] = "auto",
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
                "to": to,
                "scale": scale,
                "real_metrics": real_metrics,
            },
            lambda: _enveloped("run_sdk_client", lambda: _uc_run_sdk_client(
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
                to=to,
                scale=scale,
                real_metrics=real_metrics,
                repo_root=repo,
                edit_roots=edit_roots,
            )),
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
        to: Annotated[str, Field(description=_DESC_TO)] = "png",
        scale: Annotated[float, Field(description=_DESC_SCALE)] = 1.0,
        real_metrics: Annotated[bool | str, Field(description=_DESC_REAL_METRICS)] = "auto",
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
                "to": to,
                "scale": scale,
                "real_metrics": real_metrics,
            },
            lambda: _enveloped("run_sdk_code", lambda: _uc_run_sdk_code(
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
                to=to,
                scale=scale,
                real_metrics=real_metrics,
            )),
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
        to: Annotated[str, Field(description=_DESC_TO)] = "png",
        scale: Annotated[float, Field(description=_DESC_SCALE)] = 1.0,
        real_metrics: Annotated[bool | str, Field(description=_DESC_REAL_METRICS)] = "auto",
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
                "to": to,
                "scale": scale,
                "real_metrics": real_metrics,
            },
            lambda: _enveloped("render_framegraph_yaml", lambda: _uc_render_framegraph_yaml(
                yaml_text,
                session_id=session_id,
                session_root=root,
                max_pages=max_pages,
                raster_png=raster_png,
                pages=pages,
                sign=sign,
                signed_at=signed_at,
                silhouette=silhouette,
                to=to,
                scale=scale,
                real_metrics=real_metrics,
            )),
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
        result = _logged_enveloped_call(
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
    def coach_vectorize(
        image_path: Annotated[str, Field(description="Filesystem path to the source image (line-art or illustration).")],
        style: Annotated[str, Field(description=_DESC_COACH_STYLE)] = "children_book",
        modes: Annotated[str, Field(description=_DESC_COACH_MODES)] = "region,outline",
        paint: Annotated[bool, Field(description=_DESC_COACH_PAINT)] = True,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
        max_pages: Annotated[int, Field(description=_DESC_MAX_PAGES)] = 3,
        raster_png: Annotated[bool, Field(description=_DESC_RASTER)] = True,
        pages: Annotated[str | None, Field(description=_DESC_PAGES)] = None,
        silhouette: Annotated[bool, Field(description=_DESC_SILHOUETTE)] = True,
    ):
        """Run the Vector Construction Coach pipeline on an image (ingest → clean → redraw → recolor → paint), styled by the named grammar, then validate, render, and gate it."""
        result = _logged_call(
            log_path,
            "coach_vectorize",
            {
                "image_path": image_path,
                "style": style,
                "modes": modes,
                "paint": paint,
                "session_id": session_id,
                "max_pages": max_pages,
                "raster_png": raster_png,
                "pages": pages,
                "silhouette": silhouette,
            },
            lambda: _uc_coach_vectorize(
                image_path,
                style=style,
                modes=modes,
                paint=paint,
                session_id=session_id,
                session_root=root,
                max_pages=max_pages,
                raster_png=raster_png,
                pages=pages,
                silhouette=silhouette,
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
        result = _logged_enveloped_call(
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
        result = _logged_enveloped_call(
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

    @server.tool()
    def compare_images(
        reference: Annotated[
            str,
            Field(description="Reference/source image: a filesystem path or a framegraph://session/<id>/page/<n>.png URI."),
        ],
        candidate: Annotated[
            str,
            Field(description="Candidate/recreation image to compare against the reference: a filesystem path or a framegraph://session/<id>/page/<n>.png URI (e.g. a page just rendered by run_sdk_client)."),
        ],
        regions: Annotated[
            list[dict] | None,
            Field(description='Named crops to zoom into, as [{"name": str, "box": [x, y, w, h]}] with all values normalized 0..1 (fractions of width/height). Omit to auto-split.'),
        ] = None,
        grid: Annotated[
            list[int] | None,
            Field(description="Auto-split both images into a [cols, rows] grid of regions when `regions` is omitted (defaults to [2, 3])."),
        ] = None,
        diff: Annotated[
            bool, Field(description="Include a per-region difference cell (bright red = mismatch).")
        ] = True,
        align: Annotated[
            bool, Field(description="Phase-align the candidate onto the reference before scoring, so a pure offset doesn't read as error (adds `metrics.shift_px`).")
        ] = False,
        label_reference: Annotated[str, Field(description="Caption for the reference column.")] = "reference",
        label_candidate: Annotated[str, Field(description="Caption for the candidate column.")] = "recreation",
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Compose zoomed side-by-side comparison panels of two images for visual QA.

        Emits an overview plus one ``reference | candidate | difference`` panel per
        region — each crop scaled up and stamped with a naive pixel-match score — so a
        vision model can *see* where a recreation is off instead of eyeballing two
        downscaled thumbnails. The pixel-match score is a hint (luminance difference),
        not a verdict; the panels are the signal.
        """
        result = _logged_enveloped_call(
            log_path,
            "compare_images",
            {
                "reference": reference,
                "candidate": candidate,
                "regions": regions,
                "grid": grid,
                "diff": diff,
                "align": align,
                "label_reference": label_reference,
                "label_candidate": label_candidate,
                "session_id": session_id,
            },
            lambda: _uc_compare_images(
                reference,
                candidate,
                regions=regions,
                grid=grid,
                diff=diff,
                align=align,
                label_reference=label_reference,
                label_candidate=label_candidate,
                session_id=session_id,
                session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def measure_image(
        image: Annotated[
            str,
            Field(description="Image to measure: a filesystem path or a framegraph://session/<id>/page/<n>.png URI."),
        ],
        regions: Annotated[
            list[dict] | None,
            Field(description='Named regions to box + ID + measure, as [{"name": str, "box": [x, y, w, h]}] with values normalized 0..1. Each gets a stable id (R1, R2, ...) plus exact bbox/centroid/area/offset in the spatial payload.'),
        ] = None,
        region_grid: Annotated[
            list[int] | None,
            Field(description="Segment the image into a [cols, rows] grid of measured regions when `regions` is omitted."),
        ] = None,
        zooms: Annotated[
            list[dict] | None,
            Field(description='Zoomed crops to also emit, as [{"name": str, "box": [x, y, w, h]}] normalized 0..1. Each crop is enlarged but its rulers stay labelled in SOURCE coordinates; its origin+scale transform back to source pixels is in spatial.crops.'),
        ] = None,
        origin: Annotated[
            str,
            Field(description="Coordinate-system origin: 'top-left' (image/page space, +y down; default), 'bottom-left' (+y up), or 'center' (+y up)."),
        ] = "top-left",
        grid: Annotated[bool, Field(description="Draw the measurement grid.")] = True,
        grid_step: Annotated[
            int | None,
            Field(description="Grid/ruler tick spacing in source pixels (0/omit = a round auto step from the image size)."),
        ] = None,
        rulers: Annotated[bool, Field(description="Draw edge rulers (top + left) labelled in coordinate-system units.")] = True,
        label_every: Annotated[int, Field(description="Label (and emphasise) every Nth grid tick.")] = 2,
        landmarks: Annotated[bool, Field(description="Draw + report landmark anchors (the exact structural anchors A1..A9 always; detected L* when enabled).")] = True,
        detect_landmarks: Annotated[bool, Field(description="Also run the CV detectors for extra (UNVERIFIED) landmark anchors. Needs the vision group.")] = True,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Overlay an auto grid + rulers + coordinate system on an image and extract exact spatial metadata.

        Turns a rasterized image into a reliable coordinate reference for vector
        reconstruction: the overlay PNG keeps the source's pixel size (so coordinates
        read 1:1) and carries a grid, edge rulers, region boxes with stable IDs, and
        landmark crosshairs; the ``spatial`` payload carries the exact numbers
        (coordinate system, per-region bbox/centroid/area/offset, structural + detected
        landmarks, and each zoom crop's origin+scale transform back to source pixels).

        ⚠ PALS's LAW: the coordinate system, grid, rulers, explicit regions, and
        structural landmarks (A1..A9) are exact geometry; detected landmarks (L*) are
        UNVERIFIED CV guesses — anchor to the structural anchors, treat the rest as hints.
        """
        result = _logged_enveloped_call(
            log_path,
            "measure_image",
            {
                "image": image,
                "regions": regions,
                "region_grid": region_grid,
                "zooms": zooms,
                "origin": origin,
                "grid": grid,
                "grid_step": grid_step,
                "rulers": rulers,
                "label_every": label_every,
                "landmarks": landmarks,
                "detect_landmarks": detect_landmarks,
                "session_id": session_id,
            },
            lambda: _uc_measure_image(
                image,
                regions=regions,
                region_grid=region_grid,
                zooms=zooms,
                origin=origin,
                grid=grid,
                grid_step=grid_step,
                rulers=rulers,
                label_every=label_every,
                landmarks=landmarks,
                detect_landmarks=detect_landmarks,
                session_id=session_id,
                session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def mark_points(
        image: Annotated[
            str,
            Field(description="Image to mark on: a filesystem path or a framegraph://session/<id>/page/<n>.png URI."),
        ],
        points: Annotated[
            list[dict],
            Field(description=(
                'Ordered points to mark. Each is ONE of: {"norm": [nx, ny]} (0..1 of the full image), '
                '{"px": [x, y]} (source pixels), {"cs": [cx, cy]} (coordinate-system units), '
                '{"landmark": "A9", "dx": 0, "dy": 0} (offset from a landmark), or '
                '{"viewport_px": [vx, vy]} (pixels in the `viewport` crop). Optional "label" per point.'
            )),
        ],
        viewport: Annotated[
            dict | None,
            Field(description='Optional current view as {"name": str, "box": [x, y, w, h]} normalized 0..1. Points are anchored to the IMAGE, so the crosshairs stay fixed as the viewport moves; the marked view is emitted zoomed with rulers in source coordinates.'),
        ] = None,
        connect: Annotated[
            bool, Field(description="Draw a polyline through the points in order (a preview of the path they would trace).")
        ] = False,
        origin: Annotated[str, Field(description="Coordinate-system origin: 'top-left' (default), 'bottom-left', or 'center'.")] = "top-left",
        grid: Annotated[bool, Field(description="Draw the measurement grid behind the marks.")] = True,
        rulers: Annotated[bool, Field(description="Draw edge rulers.")] = True,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Mark coordinate points on an image and resolve each in every frame (image / coordinate-system / viewport).

        The AI's "aim + click": give points in any frame and get back an annotated
        image with numbered crosshairs plus, per point, its coordinates in the full
        image (px + coordinate system + normalized) and in the current viewport crop.
        Because points are anchored to the image, the crosshair stays fixed while the
        viewport moves. ``connect`` previews the path the points would trace — the
        bridge to the (later) vector-construction commands.
        """
        result = _logged_enveloped_call(
            log_path,
            "mark_points",
            {
                "image": image,
                "points": points,
                "viewport": viewport,
                "connect": connect,
                "origin": origin,
                "grid": grid,
                "rulers": rulers,
                "session_id": session_id,
            },
            lambda: _uc_mark_points(
                image,
                points=points,
                viewport=viewport,
                connect=connect,
                origin=origin,
                grid=grid,
                rulers=rulers,
                session_id=session_id,
                session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def overlay_images(
        base: Annotated[
            str,
            Field(description="Base/source image: a filesystem path or a framegraph://session/<id>/page/<n>.png URI."),
        ],
        overlay: Annotated[
            str,
            Field(description="Overlay image to align onto the base: a filesystem path or a framegraph://session/<id>/page/<n>.png URI."),
        ],
        landmarks: Annotated[
            list[dict],
            Field(description=(
                'Matched landmark pairs, as [{"base": [x, y], "overlay": [x, y]}]. Coordinates are '
                'source pixels by default; set "norm": true on a pair to give both as 0..1 fractions. '
                'One pair → translation only; two or more → best-fit scale + translation.'
            )),
        ],
        opacity: Annotated[
            float, Field(description="Overlay opacity in the aligned composite, 0..1.")
        ] = 0.5,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Align an overlay image onto a base by matched landmarks and extract the coordinate offsets.

        Computes the offset between each landmark pair, fits a scale+translation that
        best maps overlay→base (rotation is not modelled), reports per-pair residuals,
        and emits an aligned composite so the fit is visible. Use it to compare, align,
        and reconstruct visual structures across a source and a reference.
        """
        result = _logged_enveloped_call(
            log_path,
            "overlay_images",
            {
                "base": base,
                "overlay": overlay,
                "landmarks": landmarks,
                "opacity": opacity,
                "session_id": session_id,
            },
            lambda: _uc_overlay_images(
                base,
                overlay,
                landmarks=landmarks,
                opacity=opacity,
                session_id=session_id,
                session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def workspace(
        action: Annotated[
            str,
            Field(description=(
                "Workspace action: 'open' (bind an image — required first), 'pin' (add points), "
                "'nudge' (move selected pins by a delta — the AI mouse), 'move' (absolute), "
                "'snap' (snap selected pins to the nearest bright/dark/edge/centroid pixel, or "
                "sub-pixel edge with snap_to='edge_subpixel'), 'fit_edge' (re-project selected pins "
                "onto one sub-pixel edge line — collinear + edge-accurate), 'collinear' (project "
                "selected pins onto their best-fit line), 'symmetrize' (enforce bilateral symmetry "
                "over pin pairs, geometry={'pairs':[[l,r],...]}), 'intersect' (set a corner pin at "
                "the meeting of two edges, geometry={'edge1':[ids],'edge2':[ids],'target':id}), "
                "'transform' (translate+scale+rotate selected pins as a group), 'unpin', 'clear', "
                "'viewport' (set/clear a crop), 'pan', 'zoom', 'checkpoint' (save state), "
                "'revert' (restore a checkpoint), or 'render'/'status' (aliases: re-render the "
                "current state without changing it)."
            )),
        ] = "render",
        image: Annotated[
            str | None,
            Field(description="For 'open': the image path or framegraph://session/<id>/page/<n>.png URI to bind."),
        ] = None,
        points: Annotated[
            list[dict] | None,
            Field(description='For "pin": points to add, each in any frame — {"norm"|"px"|"cs"|"viewport_px": [a,b]} or {"landmark": id, "dx"?, "dy"?}; optional "id"/"group"/"label". A spec may reference an existing pin id.'),
        ] = None,
        select: Annotated[
            dict | None,
            Field(description='Which pins an action targets: omit for all, or {"ids": [...]} or {"group": name}. Enables multi-adjust.'),
        ] = None,
        to: Annotated[dict | None, Field(description="For 'move': the absolute target point (any frame).")] = None,
        dx: Annotated[float, Field(description="For 'nudge'/'pan': x delta (see 'unit'; e.g. -0.01 norm = left).")] = 0.0,
        dy: Annotated[float, Field(description="For 'nudge'/'pan': y delta.")] = 0.0,
        unit: Annotated[str, Field(description="Nudge unit: 'norm' (fraction of image; default), 'px', or 'viewport'.")] = "norm",
        viewport: Annotated[
            dict | None,
            Field(description='For "viewport": {"name"?, "box": [x, y, w, h]} normalized 0..1 to set, or omit box to clear.'),
        ] = None,
        factor: Annotated[float | None, Field(description="For 'zoom': zoom factor (>1 zooms in).")] = None,
        aim: Annotated[dict | None, Field(description="For 'zoom' (kept centred) / 'transform' (pivot): a point in any frame; default viewport centre / selection centroid.")] = None,
        snap_to: Annotated[str, Field(description="For 'snap': target — 'bright', 'dark', 'edge', 'centroid', or 'edge_subpixel' (sub-pixel edge via the gradient normal).")] = "bright",
        radius: Annotated[int, Field(description="For 'snap': search window radius in pixels.")] = 4,
        scale: Annotated[float, Field(description="For 'transform': uniform scale about the pivot.")] = 1.0,
        rotate: Annotated[float, Field(description="For 'transform': rotation in degrees about the pivot.")] = 0.0,
        tag: Annotated[str | None, Field(description="For 'checkpoint': an optional label.")] = None,
        index: Annotated[int, Field(description="For 'revert': checkpoint index (default -1 = latest).")] = -1,
        geometry: Annotated[
            dict | None,
            Field(description=(
                "Args for the constraint actions: 'symmetrize' → {'pairs':[[leftId,rightId],...], "
                "'axis'?}; 'intersect' → {'edge1':[ids],'edge2':[ids],'target':id}; sub-pixel edge "
                "tuning for fit_edge/intersect/snap → {'band'?,'step'?,'min_strength'?,'search_dir'?}."
            )),
        ] = None,
        origin: Annotated[str, Field(description="For 'open': coordinate origin ('top-left'/'bottom-left'/'center').")] = "top-left",
        grid: Annotated[bool, Field(description="Draw the measurement grid.")] = True,
        rulers: Annotated[bool, Field(description="Draw edge rulers.")] = True,
        connect: Annotated[bool, Field(description="Draw a polyline through the pins in order.")] = False,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Stateful coordinate workspace — the AI's precise pointer for multi-pass reconstruction.

        One workspace persists per ``session_id``: pins (anchor points) and a viewport
        survive across calls, so the AI can pin, look, nudge (e.g. 0.01 left), pin more,
        and refine over passes until pixel-accurate. Pins are image-anchored, so their
        coordinates hold as the viewport pans/zooms (fixed aim). Every call re-renders the
        overlay (+ viewport crop) and returns each pin resolved in every frame.
        """
        result = _logged_enveloped_call(
            log_path,
            "workspace",
            {
                "action": action, "image": image, "points": points, "select": select,
                "to": to, "dx": dx, "dy": dy, "unit": unit, "viewport": viewport,
                "factor": factor, "aim": aim, "snap_to": snap_to, "radius": radius,
                "scale": scale, "rotate": rotate, "tag": tag, "index": index,
                "geometry": geometry,
                "origin": origin, "grid": grid, "rulers": rulers, "connect": connect,
                "session_id": session_id,
            },
            lambda: _uc_workspace(
                action, image=image, points=points, select=select, to=to,
                dx=dx, dy=dy, unit=unit, viewport=viewport, factor=factor, aim=aim,
                snap_to=snap_to, radius=radius, scale=scale, rotate=rotate, tag=tag,
                index=index, geometry=geometry, origin=origin, grid=grid, rulers=rulers,
                connect=connect, session_id=session_id, session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def construct_vectors(
        shapes: Annotated[
            list[dict],
            Field(description=(
                'Shapes to draw, each {"kind": one of line/path/trace/polyline/curve/spline/arc/'
                'triangle/polygon/closed/rect/ellipse/circle/star/text, "points": [[x,y],...] (image px) '
                'OR "pins": [ids from the workspace / landmarks A1..A9], optional "style": '
                '{stroke, stroke_width, fill}, for circle/star optional "r"/"points_count"/"inner_ratio". '
                'arc: 3 points (start/on-arc/end through their circumcircle) or 1 centre point + '
                '"r" + "start_deg"/"end_deg". text: requires "text" and "size" (font px); 1 anchor '
                'point (box top-left) or 2+ points (the bbox).'
            )),
        ],
        image: Annotated[
            str | None,
            Field(description="Optional source image (path or session URI) — used for canvas size and as the diff reference."),
        ] = None,
        from_workspace: Annotated[
            str | None,
            Field(description="Session id of a workspace whose pins the shapes reference (defaults to session_id)."),
        ] = None,
        width: Annotated[int | None, Field(description="Canvas width px (overrides workspace/image dims).")] = None,
        height: Annotated[int | None, Field(description="Canvas height px.")] = None,
        background: Annotated[str | None, Field(description="Optional page background colour (e.g. '#ffffff').")] = None,
        title: Annotated[str, Field(description="Title for the reconstruction document.")] = "Vector reconstruction",
        raster_png: Annotated[bool, Field(description=_DESC_RASTER)] = True,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Draw FrameGraph vector geometry from anchor points, then validate + render it.

        Turns marked coordinates (workspace pins or explicit image pixels) into real SDK
        primitives (line, path, curve/spline, polygon, triangle, rect, circle, ellipse,
        star, closed region), authors a FrameGraph document sized to the source so it
        overlays the raster 1:1, and runs it through validate + render. Diff the render
        against the source with ``compare_images`` and refine the pins to converge.
        """
        result = _logged_enveloped_call(
            log_path,
            "construct_vectors",
            {
                "shapes": shapes, "image": image, "from_workspace": from_workspace,
                "width": width, "height": height, "background": background,
                "title": title, "raster_png": raster_png, "session_id": session_id,
            },
            lambda: _uc_construct_vectors(
                shapes, image=image, from_workspace=from_workspace, width=width,
                height=height, background=background, title=title,
                raster_png=raster_png, session_id=session_id, session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def score_reconstruction(
        image: Annotated[
            str,
            Field(description="Source image (filesystem path or framegraph://session/<id>/page/<n>.png URI) whose edges the shapes are scored against."),
        ],
        shapes: Annotated[
            list[dict],
            Field(description=(
                'Shapes to score — same schema as construct_vectors: each {"kind": one of '
                'line/path/trace/polyline/curve/spline/arc/triangle/polygon/closed/rect/ellipse/'
                'circle/star/text, "points": [[x,y],...] (image px) OR "pins": [workspace ids / '
                'landmarks A1..A9], and for circle/star optional "r"/"points_count"/"inner_ratio"}. '
                "'text' contributes no edge samples (glyph outlines are font geometry)."
            )),
        ],
        from_workspace: Annotated[
            str | None,
            Field(description="Session id of a workspace whose pins the shapes reference (defaults to session_id)."),
        ] = None,
        roi: Annotated[
            list[float] | None,
            Field(description="Optional [x0, y0, x1, y1] pixel window to score within (defaults to the whole image)."),
        ] = None,
        tol: Annotated[
            float, Field(description="A shape sample within this many pixels of a detected edge counts as on-edge.")
        ] = 2.0,
        symmetry_pairs: Annotated[
            list | None,
            Field(description='Optional bilateral pairs [[left, right], ...] to check for symmetry — adds a geometry-consistency report (catches a single-corner offset the luminance % is blind to). Each point is [x, y] image px OR a workspace pin/landmark id string ("P3", "A9"), resolved against from_workspace like shape pins.'),
        ] = None,
        collinear_groups: Annotated[
            list | None,
            Field(description='Optional point groups [[p1, p2, ...], ...] that should each lie on one straight edge — adds each group\'s collinearity residual. Points are [x, y] image px or workspace pin/landmark id strings, like symmetry_pairs.'),
        ] = None,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Score how well constructed vector shapes sit on the source image's edges.

        The NUMERIC convergence signal for the raster→vector loop — complements
        ``compare_images`` (which shows *where* a recreation is off) by reporting *how
        far*: ``on_edge_frac`` (fraction of shape samples within ``tol`` px of a detected
        edge) plus mean/median/p90 distances, over a match overlay (source dimmed, edges
        cyan, samples green on-edge / red off). Drive ``on_edge_frac`` up and distances
        down across passes. ``symmetry_pairs``/``collinear_groups`` add a
        geometry-consistency report (``score.geometry``) — symmetry-axis and edge
        collinearity residuals a whole-image luminance match cannot see. Edges are an
        adaptive-Sobel heuristic — a RELATIVE guide, not ground truth (PALS's Law).
        """
        result = _logged_enveloped_call(
            log_path,
            "score_reconstruction",
            {
                "image": image, "shapes": shapes, "from_workspace": from_workspace,
                "roi": roi, "tol": tol, "symmetry_pairs": symmetry_pairs,
                "collinear_groups": collinear_groups, "session_id": session_id,
            },
            lambda: _uc_score_reconstruction(
                image, shapes, from_workspace=from_workspace, roi=roi, tol=tol,
                symmetry_pairs=symmetry_pairs, collinear_groups=collinear_groups,
                session_id=session_id, session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def map_coordinates(
        mode: Annotated[
            str,
            Field(description="'homography' (fit + apply a projective transform to points), 'to_3d' (lift 2D onto a plane), 'project' (3D→2D via a camera), or 'warp' (rectify an image by the fitted homography)."),
        ],
        points: Annotated[
            list[list[float]] | None,
            Field(description="Points to transform: [x, y] for homography/to_3d, [x, y, z] for project."),
        ] = None,
        pairs: Annotated[
            list[dict] | None,
            Field(description='For "homography"/"warp": >=4 correspondences [{"src": [x, y], "dst": [x, y]}].'),
        ] = None,
        plane: Annotated[
            dict | None,
            Field(description='For "to_3d": {"origin": [x,y,z], "u": [x,y,z], "v": [x,y,z]} (default: z=0 plane).'),
        ] = None,
        camera: Annotated[
            dict | None,
            Field(description='For "project": {"eye", "target", "up": [x,y,z], "fov", "aspect", "near", "far"} (all optional).'),
        ] = None,
        image: Annotated[
            str | None,
            Field(description="For 'warp': the image (path or session URI) to rectify."),
        ] = None,
        out_size: Annotated[
            list[int] | None,
            Field(description="For 'warp': output canvas [w, h] (default: the source size)."),
        ] = None,
        width: Annotated[int | None, Field(description="For 'project': map NDC to pixels of this width.")] = None,
        height: Annotated[int | None, Field(description="For 'project': map NDC to pixels of this height.")] = None,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Transpose coordinates between 2D and 3D frames for perspective/spatial reconstruction.

        `homography` rectifies a perspective-distorted plane (or maps source→reference)
        from >=4 point pairs; `to_3d` lifts 2D image points onto a 3D plane; `project`
        projects 3D points to 2D through the SDK camera; `warp` applies the fitted
        homography to actually dewarp an image (emits the rectified PNG). Honest scope: a
        plane-to-plane projective map + a pinhole camera — no lens distortion or
        multi-view calibration.
        """
        result = _logged_enveloped_call(
            log_path,
            "map_coordinates",
            {
                "mode": mode, "points": points, "pairs": pairs, "plane": plane,
                "camera": camera, "image": image, "out_size": out_size,
                "width": width, "height": height, "session_id": session_id,
            },
            lambda: _uc_map_coordinates(
                mode, points=points, pairs=pairs, plane=plane, camera=camera,
                image=image, out_size=out_size,
                width=width, height=height, session_id=session_id, session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def vectorize_image(
        image: Annotated[
            str,
            Field(description="Image to vectorize: a filesystem path or a framegraph://session/<id>/page/<n>.png URI."),
        ],
        mode: Annotated[
            str,
            Field(description="'region' (k-means colour → filled polygons; default), 'outline' (edges → polylines), 'trace' (potrace Bézier → SVG ingest; smooth curves, needs potrace), 'layers' (solid-bg logo tracer: AA-aware palette + even-odd holes — the highest-fidelity flat-logo mode), or 'auto' (classify the raster and route to the best of the four; the decision, classification, and applied presets are reported under result.vectorize.auto — explicit args always win over the presets)."),
        ] = "region",
        region_box: Annotated[
            list[float] | None,
            Field(description="Vectorize only this normalized [x, y, w, h] crop, placed back in full-image coordinates. Omit to vectorize the whole image."),
        ] = None,
        colors: Annotated[int | None, Field(description="region mode: number of quantised colours to trace (default 8; leave unset to let mode='auto' pick its route preset — an explicit value always wins).")] = None,
        detail: Annotated[float | None, Field(description="Douglas–Peucker epsilon as a fraction of contour length (higher = simpler; default 0.004; unset lets mode='auto' pick).")] = None,
        min_area: Annotated[float | None, Field(description="Drop contours below this pixel area (noise floor; default 90; unset lets mode='auto' pick).")] = None,
        max_dim: Annotated[int | None, Field(description="Downscale the longest side to this before tracing (whole-image region/outline; default 900, 0 = no scaling; unset lets mode='auto' pick).")] = None,
        ink: Annotated[str, Field(description="outline mode: stroke colour for the polylines.")] = "#1E2440",
        stroke_width: Annotated[float, Field(description="outline mode: stroke width for the polylines, in px.")] = 1.0,
        background: Annotated[str | None, Field(description="Optional page background colour (e.g. '#2e3238' for a light mark on dark).")] = None,
        threshold: Annotated[int | None, Field(description="trace mode: 0..255 bi-level threshold (omit = 128).")] = None,
        invert: Annotated[bool | None, Field(description="trace mode: invert so bright pixels are the traced foreground; omit for auto (invert when the ground is dark).")] = None,
        turdsize: Annotated[int, Field(description="trace mode: potrace speckle suppression — drop paths of fewer than this many pixels.")] = 2,
        alphamax: Annotated[float, Field(description="trace mode: potrace corner threshold (0 = sharp polygons only, 1.0 = default smoothing, up to 4/3 = smoothest).")] = 1.0,
        opttolerance: Annotated[float, Field(description="trace mode: potrace curve-optimization tolerance (higher = fewer, looser Bézier segments).")] = 0.2,
        fill: Annotated[str, Field(description="trace mode: fill colour for the traced paths.")] = "#000000",
        ocr: Annotated[bool, Field(description="Also add Tesseract-detected text objects (needs the tesseract binary).")] = False,
        title: Annotated[str, Field(description="Title for the reconstruction document.")] = "Vectorized reconstruction",
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Trace a raster into editable FrameGraph vector objects, then validate + render it.

        The pixel-accurate complement to manual pin-and-construct: `region` k-means-traces
        flat colour into filled polygons (ideal for logos/flat art), `outline` traces edges
        into polylines, and `trace` runs potrace for smooth Bézier outlines lowered through
        the SVG-ingest path. `region_box` vectorizes just a crop, placed 1:1 in the full
        image; `ocr` adds text objects. Diff the render against the source with `compare_images`.
        """
        result = _logged_enveloped_call(
            log_path,
            "vectorize_image",
            {
                "image": image, "mode": mode, "region_box": region_box, "colors": colors,
                "detail": detail, "min_area": min_area, "max_dim": max_dim, "ink": ink,
                "stroke_width": stroke_width, "background": background,
                "threshold": threshold, "invert": invert, "turdsize": turdsize,
                "alphamax": alphamax, "opttolerance": opttolerance,
                "fill": fill, "ocr": ocr, "title": title, "session_id": session_id,
            },
            lambda: _uc_vectorize_image(
                image, mode=mode, region_box=region_box, colors=colors, detail=detail,
                min_area=min_area, max_dim=max_dim, ink=ink, stroke_width=stroke_width,
                background=background,
                threshold=threshold, invert="auto" if invert is None else invert,
                turdsize=turdsize, alphamax=alphamax, opttolerance=opttolerance,
                fill=fill, ocr=ocr, title=title, session_id=session_id, session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def detect_regions(
        image: Annotated[
            str,
            Field(description="Image to analyze: a filesystem path (raster, or .svg — rasterised first) or a framegraph://session/<id>/page/<n>.png URI."),
        ],
        method: Annotated[str, Field(description=_DESC_REGION_METHOD)] = "consensus",
        cluster: Annotated[
            str | None,
            Field(description="Optionally group regions into shape-equivalence classes: 'translation' (same shape AND orientation — the repeated-tile count) or 'congruent' (same shape, any pose). Adds spatial.classes plus a shape_class per region."),
        ] = None,
        cluster_tol: Annotated[
            float,
            Field(description="Cluster match threshold: translation = minimum top-left-aligned mask IoU; congruent = 1-tol relative feature tolerance."),
        ] = 0.90,
        overlay: Annotated[
            bool,
            Field(description="Render the annotated region overlay PNG as the session's page 1 (regions painted with their sampled fill, borders drawn, a one-line count banner)."),
        ] = True,
        max_regions: Annotated[
            int,
            Field(description="Report at most this many regions (largest area first); spatial.region_count still carries the full count."),
        ] = 400,
        include_polygons: Annotated[
            bool,
            Field(description="Include each region's simplified boundary polygon (+ hole polygons) in image pixels."),
        ] = True,
        tunables: Annotated[dict | None, Field(description=_DESC_REGION_TUNABLES)] = None,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Detect an image's closed/filled/stable regions and extract their exact geometry.

        Three methods, one funnel: `closed` finds purely topological enclosed faces
        (line art), `flat` partitions every maximal uniform fill (solid shapes and
        hollow interiors alike, with outline-stroke recovery), and `consensus` keeps
        what an ensemble of mollified level sets agrees on (smooth C-infinity
        boundaries; robust on tangled linework). The `spatial` payload carries each
        region's bbox_px + box_norm + centroid (px and normalized) + sampled fill +
        polygon/holes — coordinates that feed `workspace` pins and
        `construct_vectors` points directly. ⚠ Heuristic output (PALS's Law): verify
        the overlay + numbers against the source.
        """
        result = _logged_enveloped_call(
            log_path,
            "detect_regions",
            {
                "image": image, "method": method, "cluster": cluster,
                "cluster_tol": cluster_tol, "overlay": overlay,
                "max_regions": max_regions, "include_polygons": include_polygons,
                "tunables": tunables, "session_id": session_id,
            },
            lambda: _uc_detect_regions(
                image, method=method, cluster=cluster, cluster_tol=cluster_tol,
                overlay=overlay, max_regions=max_regions,
                include_polygons=include_polygons, tunables=tunables,
                session_id=session_id, session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.prompt()
    def framegraph_guide() -> str:
        """Guide to what the FrameGraph SDK offers and the server's authoring + proposal tools."""
        return _logged_call(log_path, "prompt.framegraph_guide", {}, lambda: FRAMEGRAPH_GUIDE)

    @server.tool()
    def get_guide() -> str:
        """Return the FrameGraph capability guide — the same text as the `framegraph_guide` prompt.

        The guide is registered as a prompt, but not every MCP client surfaces
        prompts; this tool is the fallback so any agent can retrieve the full
        SDK + workflow reference in-band.
        """
        return _logged_call(log_path, "get_guide", {}, lambda: FRAMEGRAPH_GUIDE)

    @server.tool()
    def describe_capabilities(
        topic: Annotated[str | None, Field(description=_DESC_TOPIC)] = None,
    ):
        """Runtime discovery of the FrameGraph document model (live, read-only introspection).

        Sourced from the authoritative Pydantic model (``models/framegraph.py``)
        at call time — the same module validation runs against — so it cannot
        drift. Omit ``topic`` for the compact capability index; pass a catalog
        topic (``flowables``/``inlines``/``style``/``presets``/``tools``) or a
        type name (``rect``, ``paragraph``, ``document``, ...) for details +
        JSON schema. Use it to look up fields BEFORE authoring instead of
        iterating on validation errors.
        """
        return _plain_tool_result(_logged_enveloped_call(
            log_path,
            "describe_capabilities",
            {"topic": topic},
            lambda: _uc_describe_capabilities(topic, tool_names=_registered_tool_names(server)),
        ))

    @server.tool()
    def list_fonts(
        family: Annotated[
            str | None,
            Field(description="Optional family name to resolution-check (e.g. 'Inter ExtraLight'): reports what fontconfig actually resolves it to under `resolves`, so a silent substitution is caught BEFORE rendering."),
        ] = None,
        contains: Annotated[
            str | None,
            Field(description="Case-insensitive substring filter for the enumerated families."),
        ] = None,
        limit: Annotated[
            int, Field(description="Return at most this many families (<=0 = all); `family_count` always reports the full match count."),
        ] = 500,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Enumerate the font families fontconfig can resolve, plus a session's pinned fonts.

        Rendering resolves families via fontconfig, and an unresolved family
        silently substitutes a default face — check availability here first.
        When the session holds a rendered document, its ``defs.tokens.fonts``
        pins are reported as ``pinned_fonts``. Degrades to a structured error
        (with an install hint) when fontconfig is absent.
        """
        return _plain_tool_result(_logged_enveloped_call(
            log_path,
            "list_fonts",
            {"family": family, "contains": contains, "limit": limit, "session_id": session_id},
            lambda: _uc_list_fonts(
                family, contains=contains, limit=limit,
                session_id=session_id, session_root=root,
            ),
        ))

    @server.tool()
    def get_session_resource(
        uri: Annotated[
            str,
            Field(description="A framegraph://session/<id>/<artifact> URI: document.yaml, document.pdf, diagnostics.json, page/N.svg, or page/N.png. Prefer the registered resources; this tool exists for clients that do not surface resources."),
        ],
    ):
        """Read a FrameGraph MCP session resource by URI."""
        return _plain_tool_result(_logged_enveloped_call(
            log_path,
            "get_session_resource",
            {"uri": uri},
            lambda: read_session_resource(uri, session_root=root),
        ))

    @server.tool()
    def list_sessions():
        """List per-session scratch directories with their artifact counts and size."""
        return _plain_tool_result(_logged_enveloped_call(
            log_path,
            "list_sessions",
            {},
            lambda: _uc_list_sessions(session_root=root),
        ))

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
    ):
        """Remove session scratch dirs by id or age (no selector removes nothing)."""
        return _plain_tool_result(_logged_enveloped_call(
            log_path,
            "cleanup_sessions",
            {"session_ids": session_ids, "older_than_seconds": older_than_seconds, "dry_run": dry_run},
            lambda: _uc_cleanup_sessions(
                session_root=root,
                session_ids=session_ids,
                older_than_seconds=older_than_seconds,
                dry_run=dry_run,
            ),
        ))

    @server.resource("framegraph://session/{session_id}/document.yaml")
    def session_document(session_id: str) -> str:
        """The validated FrameGraph YAML a render tool produced for this session."""
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
        """The vector SVG for page N (1-based) — exact geometry; not vision-decodable."""
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
        """The rasterized PNG for page N (1-based) — the vision-decodable render to verify against."""
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

    @server.resource(
        "framegraph://session/{session_id}/document.pdf", mime_type="application/pdf"
    )
    def session_document_pdf(session_id: str) -> bytes:
        """The assembled vector PDF — present after a render tool ran with to='pdf'."""
        payload = _logged_call(
            log_path,
            "resource.session_document_pdf",
            {"session_id": session_id},
            lambda: read_session_resource(
                f"framegraph://session/{session_id}/document.pdf",
                session_root=root,
            ),
        )
        return base64.b64decode(payload["blob"])

    @server.resource("framegraph://session/{session_id}/diagnostics.json")
    def session_diagnostics(session_id: str) -> str:
        """The full result of the last call in this session — validation issues, render
        metadata, subprocess streams, and the complete `spatial` coordinate payload
        (coordinate system, regions, landmarks, crop transforms, pins) that the tool
        response summarizes. Read this for the exact numbers behind a measurement."""
        return _logged_call(
            log_path,
            "resource.session_diagnostics",
            {"session_id": session_id},
            lambda: read_session_resource(
                f"framegraph://session/{session_id}/diagnostics.json",
                session_root=root,
            )["text"],
        )

    @server.resource("framegraph://session/{session_id}/workspace.json")
    def session_workspace(session_id: str) -> str:
        """The persisted `workspace` state for this session: the bound image, the pin
        set (ids, image-pixel coordinates, groups, labels), and the current viewport.
        Present only after `workspace` action='open'; this is what makes pins survive
        across calls for multi-pass reconstruction."""
        return _logged_call(
            log_path,
            "resource.session_workspace",
            {"session_id": session_id},
            lambda: read_session_resource(
                f"framegraph://session/{session_id}/workspace.json",
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
    "propose_from_svg",
    "compare_images",
    "measure_image",
    "mark_points",
    "overlay_images",
    "workspace",
    "construct_vectors",
    "detect_regions",
    "score_reconstruction",
    "map_coordinates",
    "vectorize_image",
    "list_sdk_clients",
    "read_sdk_client",
    "write_sdk_client",
    "read_session_resource",
    "list_sessions",
    "cleanup_sessions",
    "describe_capabilities",
    "list_fonts",
    "mcp_content_blocks",
    "get_default_session_root",
    "get_default_repo_root",
    "FRAMEGRAPH_GUIDE",
]
