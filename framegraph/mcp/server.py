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
    compare_images as _uc_compare_images,
    construct_vectors as _uc_construct_vectors,
    map_coordinates as _uc_map_coordinates,
    mark_points as _uc_mark_points,
    measure_image as _uc_measure_image,
    overlay_images as _uc_overlay_images,
    workspace as _uc_workspace,
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
    map_coordinates as map_coordinates,
    mark_points as mark_points,
    measure_image as measure_image,
    overlay_images as overlay_images,
    workspace as workspace,
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
        result = _logged_call(
            log_path,
            "compare_images",
            {
                "reference": reference,
                "candidate": candidate,
                "regions": regions,
                "grid": grid,
                "diff": diff,
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
        result = _logged_call(
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
        result = _logged_call(
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
        result = _logged_call(
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
                "'unpin', 'clear', 'viewport' (set/clear a crop), 'pan', 'zoom', or 'render'."
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
        aim: Annotated[dict | None, Field(description="For 'zoom': the point kept centred (fixed aim), any frame; default viewport centre.")] = None,
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
        result = _logged_call(
            log_path,
            "workspace",
            {
                "action": action, "image": image, "points": points, "select": select,
                "to": to, "dx": dx, "dy": dy, "unit": unit, "viewport": viewport,
                "factor": factor, "aim": aim, "origin": origin, "grid": grid,
                "rulers": rulers, "connect": connect, "session_id": session_id,
            },
            lambda: _uc_workspace(
                action, image=image, points=points, select=select, to=to,
                dx=dx, dy=dy, unit=unit, viewport=viewport, factor=factor, aim=aim,
                origin=origin, grid=grid, rulers=rulers, connect=connect,
                session_id=session_id, session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def construct_vectors(
        shapes: Annotated[
            list[dict],
            Field(description=(
                'Shapes to draw, each {"kind": one of line/path/trace/polyline/curve/spline/'
                'triangle/polygon/closed/rect/ellipse/circle/star, "points": [[x,y],...] (image px) '
                'OR "pins": [ids from the workspace / landmarks A1..A9], optional "style": '
                '{stroke, stroke_width, fill}, and for circle/star optional "r"/"points_count"/"inner_ratio"}.'
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
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Draw FrameGraph vector geometry from anchor points, then validate + render it.

        Turns marked coordinates (workspace pins or explicit image pixels) into real SDK
        primitives (line, path, curve/spline, polygon, triangle, rect, circle, ellipse,
        star, closed region), authors a FrameGraph document sized to the source so it
        overlays the raster 1:1, and runs it through validate + render. Diff the render
        against the source with ``compare_images`` and refine the pins to converge.
        """
        result = _logged_call(
            log_path,
            "construct_vectors",
            {
                "shapes": shapes, "image": image, "from_workspace": from_workspace,
                "width": width, "height": height, "background": background,
                "title": title, "session_id": session_id,
            },
            lambda: _uc_construct_vectors(
                shapes, image=image, from_workspace=from_workspace, width=width,
                height=height, background=background, title=title,
                session_id=session_id, session_root=root,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def map_coordinates(
        mode: Annotated[
            str,
            Field(description="'homography' (fit + apply a projective transform), 'to_3d' (lift 2D onto a plane), or 'project' (3D→2D via a camera)."),
        ],
        points: Annotated[
            list[list[float]] | None,
            Field(description="Points to transform: [x, y] for homography/to_3d, [x, y, z] for project."),
        ] = None,
        pairs: Annotated[
            list[dict] | None,
            Field(description='For "homography": >=4 correspondences [{"src": [x, y], "dst": [x, y]}].'),
        ] = None,
        plane: Annotated[
            dict | None,
            Field(description='For "to_3d": {"origin": [x,y,z], "u": [x,y,z], "v": [x,y,z]} (default: z=0 plane).'),
        ] = None,
        camera: Annotated[
            dict | None,
            Field(description='For "project": {"eye", "target", "up": [x,y,z], "fov", "aspect", "near", "far"} (all optional).'),
        ] = None,
        width: Annotated[int | None, Field(description="For 'project': map NDC to pixels of this width.")] = None,
        height: Annotated[int | None, Field(description="For 'project': map NDC to pixels of this height.")] = None,
        session_id: Annotated[str | None, Field(description=_DESC_SESSION_ID)] = None,
    ):
        """Transpose coordinates between 2D and 3D frames for perspective/spatial reconstruction.

        `homography` rectifies a perspective-distorted plane (or maps source→reference)
        from >=4 point pairs; `to_3d` lifts 2D image points onto a 3D plane; `project`
        projects 3D points to 2D through the SDK camera (the renderer's own math). Honest
        scope: a plane-to-plane projective map + a pinhole camera — no lens distortion or
        multi-view calibration.
        """
        result = _logged_call(
            log_path,
            "map_coordinates",
            {
                "mode": mode, "points": points, "pairs": pairs, "plane": plane,
                "camera": camera, "width": width, "height": height, "session_id": session_id,
            },
            lambda: _uc_map_coordinates(
                mode, points=points, pairs=pairs, plane=plane, camera=camera,
                width=width, height=height, session_id=session_id, session_root=root,
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
    "compare_images",
    "measure_image",
    "mark_points",
    "overlay_images",
    "workspace",
    "construct_vectors",
    "map_coordinates",
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
