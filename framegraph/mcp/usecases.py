"""The MCP feedback-loop use cases — thin orchestrators over a uniform runner.

Each public function validates its own inputs, constructs the appropriate
:class:`~framegraph.mcp.sources.DocumentSource`, and hands it to :func:`_run_source`,
which drives the single shared tail: produce the document, then validate + render it
and persist diagnostics. The five entry points used to copy that tail verbatim; the
runner removes the duplication so a new entry point is a new source, not a new copy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from framegraph.mcp.config import DEFAULT_TIMEOUT_SECONDS, MAX_CODE_BYTES
from framegraph.mcp.pipeline import _validate_and_render_yaml
from framegraph.mcp.results import _write_diagnostics
from framegraph.mcp.security import _assert_input_path_allowed
from framegraph.mcp.sources import (
    DocumentSource,
    ProposalSource,
    RawYamlSource,
    SdkClientSource,
    SdkCodeSource,
    _vision_error,
    _VISION_GROUP_HINT,
)


def _run_source(
    source: DocumentSource,
    *,
    max_pages: int,
    raster_png: bool,
    pages: str | list[int] | None,
    sign: bool,
    signed_at: str | None,
    silhouette: bool = False,
) -> dict[str, Any]:
    """Drive any document source: produce, then (if produced) validate + render.

    Every entry point funnels through here so the produce → validate → render →
    diagnostics tail has exactly one implementation.
    """
    produced = source.produce()
    result = produced.result
    if produced.proceed:
        rendered = _validate_and_render_yaml(
            produced.yaml_path.read_text(encoding="utf-8"),
            session_id=produced.sid,
            session_dir=produced.session_dir,
            base_dir=produced.base_dir,
            max_pages=max_pages,
            raster_png=raster_png,
            pages=pages,
            sign=sign,
            signed_at=signed_at,
            silhouette=silhouette,
        )
        result.update(rendered)
    _write_diagnostics(produced.session_dir, result)
    return result


def run_sdk_code(
    code: str,
    *,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_pages: int = 3,
    raster_png: bool = True,
    pages: str | list[int] | None = None,
    sign: bool = False,
    signed_at: str | None = None,
    silhouette: bool = False,
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
    source = SdkCodeSource(
        code=code,
        timeout_seconds=timeout_seconds,
        session_id=session_id,
        session_root=session_root,
    )
    return _run_source(
        source, max_pages=max_pages, raster_png=raster_png, pages=pages,
        sign=sign, signed_at=signed_at, silhouette=silhouette,
    )


def run_sdk_client(
    path: str,
    *,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_pages: int = 3,
    raster_png: bool = True,
    invoke_main: bool = False,
    pages: str | list[int] | None = None,
    sign: bool = False,
    signed_at: str | None = None,
    silhouette: bool = False,
    repo_root: str | Path | None = None,
    edit_roots: str | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Run an editable Python SDK client file, then validate and render YAML."""
    source = SdkClientSource(
        path=path,
        timeout_seconds=timeout_seconds,
        invoke_main=invoke_main,
        repo_root=repo_root,
        edit_roots=edit_roots,
        session_id=session_id,
        session_root=session_root,
    )
    return _run_source(
        source, max_pages=max_pages, raster_png=raster_png, pages=pages,
        sign=sign, signed_at=signed_at, silhouette=silhouette,
    )


def render_framegraph_yaml(
    yaml_text: str,
    *,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    max_pages: int = 3,
    raster_png: bool = True,
    pages: str | list[int] | None = None,
    sign: bool = False,
    signed_at: str | None = None,
    silhouette: bool = False,
) -> dict[str, Any]:
    """Validate and render caller-provided FrameGraph YAML."""
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        raise ValueError("yaml_text must be a non-empty string")
    source = RawYamlSource(yaml_text=yaml_text, session_id=session_id, session_root=session_root)
    return _run_source(
        source, max_pages=max_pages, raster_png=raster_png, pages=pages,
        sign=sign, signed_at=signed_at, silhouette=silhouette,
    )


def propose_from_image(
    image_path: str | None = None,
    *,
    image_base64: str | None = None,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    max_pages: int = 3,
    raster_png: bool = True,
    pages: str | list[int] | None = None,
    title: str = "Proposed from image",
    detector_names: list[str] | None = None,
) -> dict[str, Any]:
    """Propose a draft FrameGraph document from an image, then validate and render it.

    The proposal is unverified CV/VLM output; rendering it through the forward
    pipeline (the same one ``render_framegraph_yaml`` uses) is the verification.
    """
    if not image_path and not image_base64:
        raise ValueError("provide image_path or image_base64")
    if image_path and not image_base64:
        try:
            _assert_input_path_allowed(image_path)
        except ValueError as exc:
            return _vision_error(str(exc))
    try:
        from framegraph.vision.application.service import propose_from_image as _vision_propose
    except ImportError:
        return _vision_error(_VISION_GROUP_HINT)

    try:
        if image_base64:
            proposal = _vision_propose(image_base64, is_base64=True, title=title, detector_names=detector_names)
        else:
            proposal = _vision_propose(image_path, is_base64=False, title=title, detector_names=detector_names)
    except RuntimeError as exc:
        return _vision_error(str(exc))
    source = ProposalSource(proposal=proposal, session_id=session_id, session_root=session_root)
    return _run_source(
        source, max_pages=max_pages, raster_png=raster_png, pages=pages, sign=False, signed_at=None,
    )


def propose_from_document(
    path: str,
    *,
    page: int = 1,
    dpi: int = 144,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    max_pages: int = 3,
    raster_png: bool = True,
    pages: str | list[int] | None = None,
    title: str | None = None,
    detector_names: list[str] | None = None,
) -> dict[str, Any]:
    """Propose a draft FrameGraph document from a rasterised PDF page, then validate and render it."""
    try:
        _assert_input_path_allowed(path)
    except ValueError as exc:
        return _vision_error(str(exc))
    try:
        from framegraph.vision.application.service import propose_from_document as _vision_propose
    except ImportError:
        return _vision_error(_VISION_GROUP_HINT)

    try:
        proposal = _vision_propose(path, page=page, dpi=dpi, title=title, detector_names=detector_names)
    except (RuntimeError, ValueError) as exc:
        return _vision_error(str(exc))
    source = ProposalSource(proposal=proposal, session_id=session_id, session_root=session_root)
    return _run_source(
        source, max_pages=max_pages, raster_png=raster_png, pages=pages, sign=False, signed_at=None,
    )


def _coerce_paint(value: Any) -> Any:
    """Accept a solid ``#hex`` string or a JSON ramp ``[[pos, "#hex"], ...]``.

    Region/default paint arrives over the wire as JSON, so a ramp is a list of
    ``[position, colour]`` pairs; lower it to the ``(float, str)`` tuples
    :func:`framegraph.sdk.region.region_grade` expects.
    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return [(float(stop[0]), str(stop[1])) for stop in value]
    raise ValueError("a ramp must be a #hex string or a list of [position, colour] pairs")


def propose_from_svg(
    svg_path: str | None = None,
    *,
    svg_text: str | None = None,
    regions: list[dict[str, Any]] | None = None,
    default_ramp: Any = None,
    title: str = "Proposed from SVG",
    session_id: str | None = None,
    session_root: str | Path | None = None,
    max_pages: int = 3,
    raster_png: bool = True,
    pages: str | list[int] | None = None,
) -> dict[str, Any]:
    """Ingest an SVG into a FrameGraph document, optionally grade it by region, then render.

    Lowers the SVG's elements to FrameGraph primitives (1:1, no raster step) via
    :func:`framegraph.vision.infrastructure.svg_import.svg_to_objects`, sizes a page
    to the drawing's extent, and renders it through the same forward pipeline the
    other tools use. When ``regions`` is given, each object is recoloured by the
    region its centroid falls in (``framegraph.sdk.region.region_grade``): every
    region is ``{"box": [x, y, w, h], "ramp": "#hex" | [[pos, "#hex"], ...]}``;
    objects outside every region take ``default_ramp`` (omit it to leave them
    unchanged). Region clip/transform stay in the SDK (``place_region``), reachable
    via ``run_sdk_code``.
    """
    if not svg_text and not svg_path:
        return _vision_error("provide svg_path or svg_text")
    if svg_path and not svg_text:
        try:
            _assert_input_path_allowed(svg_path)
        except ValueError as exc:
            return _vision_error(str(exc))

    from framegraph.sdk.author import DocumentBuilder
    from framegraph.sdk.io import serialize
    from framegraph.sdk.region import object_bbox, region_grade
    from framegraph.vision.infrastructure.svg_import import svg_to_objects

    try:
        objects = svg_to_objects(svg_text if svg_text else svg_path)
    except (ValueError, OSError) as exc:
        return _vision_error(f"could not parse SVG: {exc}")
    if not objects:
        return _vision_error("the SVG produced no drawable objects")

    boxes = [bb for bb in (object_bbox(o) for o in objects) if bb is not None]
    if not boxes:
        return _vision_error("the SVG produced no positioned geometry")
    width = max(bb[2] for bb in boxes)
    height = max(bb[3] for bb in boxes)

    if regions:
        try:
            specs = [(list(r["box"]), _coerce_paint(r.get("ramp"))) for r in regions]
        except (KeyError, TypeError, ValueError) as exc:
            return _vision_error(f"invalid regions spec: {exc}")
        objects = region_grade(objects, specs, default=_coerce_paint(default_ramp))

    builder = DocumentBuilder(title=title, lang="en")
    page = builder.page("svg", canvas={"size": [width, height], "units": "px"},
                        coordinate_mode="absolute")
    layer = page.layer("ingest")
    with layer.bleed():
        for obj in objects:
            layer.add(obj)

    source = RawYamlSource(yaml_text=serialize(builder.build(), format="yaml"),
                           session_id=session_id, session_root=session_root)
    return _run_source(
        source, max_pages=max_pages, raster_png=raster_png, pages=pages, sign=False, signed_at=None,
    )
