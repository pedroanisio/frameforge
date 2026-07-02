"""The MCP feedback-loop use cases — thin orchestrators over a uniform runner.

Each public function validates its own inputs, constructs the appropriate
:class:`~framegraph.mcp.sources.DocumentSource`, and hands it to :func:`_run_source`,
which drives the single shared tail: produce the document, then validate + render it
and persist diagnostics. The five entry points used to copy that tail verbatim; the
runner removes the duplication so a new entry point is a new source, not a new copy.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from framegraph.mcp.config import DEFAULT_TIMEOUT_SECONDS, MAX_CODE_BYTES
from framegraph.mcp.paths import _session_root
from framegraph.mcp.pipeline import _validate_and_render_yaml
from framegraph.mcp.results import _write_diagnostics
from framegraph.mcp.security import _assert_input_path_allowed
from framegraph.mcp.sessions import (
    _prepare_session,
    _previous_session_tool,
    _prior_render_artifacts,
    _reset_session_inputs,
    _reset_session_outputs,
    _reset_session_renders,
    _session_id,
    read_session_resource,
)
from framegraph.mcp.sources import (
    DocumentSource,
    ProposalSource,
    RawYamlSource,
    SdkClientSource,
    SdkCodeSource,
    _vision_error,
    _VISION_GROUP_HINT,
)


def _session_replacement_info(session_dir: Path, tool: str) -> dict[str, Any] | None:
    """Pre-reset check: is this call about to replace a DIFFERENT tool's renders?

    Iterating in place with the same tool is the intended loop and stays quiet;
    a different tool overwriting a prior tool's ``page/N.png`` in a shared
    session (the default id is ``'session'``) is the silent-clobber case the
    guide warns about — surface it in the result instead.
    """
    prior = _prior_render_artifacts(session_dir)
    previous = _previous_session_tool(session_dir)
    if prior and previous and previous != tool:
        return {
            "count": len(prior),
            "previous_tool": previous,
            "note": (
                f"replaced {len(prior)} rendered artifact(s) a prior '{previous}' call left in "
                "this session — pass a distinct session_id to keep both renders"
            ),
        }
    return None


def _apply_session_stamp(
    result: dict[str, Any], *, tool: str, replaced: dict[str, Any] | None
) -> None:
    """Record the producing tool (for the next call's replacement check) + any note."""
    result["tool"] = tool
    if replaced:
        result["replaced_renders"] = replaced
        existing = result.get("render_warning")
        result["render_warning"] = f"{existing}; {replaced['note']}" if existing else replaced["note"]


def _run_source(
    source: DocumentSource,
    *,
    max_pages: int,
    raster_png: bool,
    pages: str | list[int] | None,
    sign: bool,
    signed_at: str | None,
    silhouette: bool = False,
    to: str = "png",
    scale: float = 1.0,
    real_metrics: bool | str = "auto",
    tool: str | None = None,
) -> dict[str, Any]:
    """Drive any document source: produce, then (if produced) validate + render.

    Every entry point funnels through here so the produce → validate → render →
    diagnostics tail has exactly one implementation. Build inputs are reset
    before ``produce`` (hermetic builds; SDK sources also reset defensively),
    but rendered artifacts are cleared only once a new render is imminent — a
    FAILED build leaves the previous call's renders intact.
    """
    session_dir = _session_root(source.session_root) / _session_id(source.session_id)
    replaced = _session_replacement_info(session_dir, tool) if tool else None
    if session_dir.is_dir():
        _reset_session_inputs(session_dir)
    produced = source.produce()
    result = produced.result
    if produced.proceed:
        _reset_session_renders(produced.session_dir)
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
            to=to,
            scale=scale,
            real_metrics=real_metrics,
        )
        result.update(rendered)
    if tool:
        _apply_session_stamp(result, tool=tool, replaced=replaced)
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
    to: str = "png",
    scale: float = 1.0,
    real_metrics: bool | str = "auto",
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
        to=to, scale=scale, real_metrics=real_metrics, tool="run_sdk_code",
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
    to: str = "png",
    scale: float = 1.0,
    real_metrics: bool | str = "auto",
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
        to=to, scale=scale, real_metrics=real_metrics, tool="run_sdk_client",
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
    to: str = "png",
    scale: float = 1.0,
    real_metrics: bool | str = "auto",
) -> dict[str, Any]:
    """Validate and render caller-provided FrameGraph YAML."""
    if not isinstance(yaml_text, str) or not yaml_text.strip():
        raise ValueError("yaml_text must be a non-empty string")
    source = RawYamlSource(yaml_text=yaml_text, session_id=session_id, session_root=session_root)
    return _run_source(
        source, max_pages=max_pages, raster_png=raster_png, pages=pages,
        sign=sign, signed_at=signed_at, silhouette=silhouette,
        to=to, scale=scale, real_metrics=real_metrics, tool="render_framegraph_yaml",
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
        tool="propose_from_image",
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
        tool="propose_from_document",
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
        tool="propose_from_svg",
    )


def _resolve_image_arg(arg: str, *, session_root: str | Path | None) -> bytes:
    """Read image bytes from a filesystem path or a ``framegraph://session`` PNG URI.

    Accepting a session URI closes the render→compare loop: a page just rendered by
    ``run_sdk_client`` can be compared against a reference without the caller having
    to know its scratch-file path. Filesystem paths are confined by
    ``_assert_input_path_allowed`` (the same guard the propose tools use).
    """
    if not isinstance(arg, str) or not arg.strip():
        raise ValueError("image argument must be a non-empty path or framegraph:// URI")
    if arg.startswith("framegraph://"):
        payload = read_session_resource(arg, session_root=session_root)
        blob = payload.get("blob")
        if not blob:
            raise ValueError(f"resource {arg} is not a raster image (expected a .png)")
        return base64.b64decode(blob)
    _assert_input_path_allowed(arg)
    path = Path(arg).expanduser()
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return path.read_bytes()


def _parse_regions(regions: list[dict[str, Any]] | None, grid: list[int] | None):
    """Build the region list: explicit ``regions`` win, else a ``grid``, else 2×3."""
    from framegraph.vision.infrastructure.image_compare import Region, auto_regions

    if regions:
        out = []
        for i, r in enumerate(regions):
            box = r.get("box") if isinstance(r, dict) else None
            if not box or len(box) != 4:
                raise ValueError(
                    f"region {i} needs a normalized box [x, y, w, h] in 0..1")
            name = str(r.get("name") or f"region {i + 1}")
            out.append(Region(name, tuple(float(v) for v in box)))
        return out
    if grid:
        if len(grid) != 2:
            raise ValueError("grid must be [cols, rows]")
        return auto_regions(int(grid[0]), int(grid[1]))
    return auto_regions(2, 3)


def _compare_resources(session_id: str, renders: list[dict[str, Any]]) -> list[dict[str, str]]:
    links = [{
        "type": "resource_link",
        "uri": f"framegraph://session/{session_id}/diagnostics.json",
        "name": "diagnostics.json",
        "mimeType": "application/json",
    }]
    for render in renders:
        links.append({
            "type": "resource_link",
            "uri": str(render["uri"]),
            "name": Path(str(render["path"])).name,
            "mimeType": str(render["mimeType"]),
        })
    return links


def compare_images(
    reference: str,
    candidate: str,
    *,
    regions: list[dict[str, Any]] | None = None,
    grid: list[int] | None = None,
    diff: bool = True,
    align: bool = False,
    label_reference: str = "reference",
    label_candidate: str = "recreation",
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Compose zoomed side-by-side comparison panels of two images for visual QA.

    Renders an overview plus one ``reference | candidate | difference`` panel per
    region — each cropped by a normalized box, scaled up, and stamped with a naive
    pixel-match score — so a vision model can *see* where a recreation is off rather
    than eyeball two downscaled thumbnails. ``reference``/``candidate`` are each a
    filesystem path or a ``framegraph://session/<id>/page/<n>.png`` URI.

    ⚠ PALS's LAW: the pixel-match score is a naive luminance-difference hint, not a
    verdict; the panels (judged visually) are the signal. See
    :mod:`framegraph.vision.infrastructure.image_compare`.
    """
    try:
        ref_bytes = _resolve_image_arg(reference, session_root=session_root)
        cand_bytes = _resolve_image_arg(candidate, session_root=session_root)
    except (ValueError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        from framegraph.vision.infrastructure.image_compare import build_panels
    except RuntimeError as exc:  # Pillow missing
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        region_objs = _parse_regions(regions, grid)
        panels = build_panels(
            ref_bytes, cand_bytes, regions=region_objs, diff=diff, align=align,
            labels=(label_reference, label_candidate),
        )
    except (ValueError, OSError) as exc:
        return {"ok": False, "error": f"could not build comparison: {exc}",
                "renders": [], "resources": []}

    root = _session_root(session_root)
    sid = _session_id(session_id)
    session_dir = _prepare_session(root, sid)
    replaced = _session_replacement_info(session_dir, "compare_images")
    _reset_session_outputs(session_dir)

    renders: list[dict[str, Any]] = []
    comparison: list[dict[str, Any]] = []
    for idx, panel in enumerate(panels, start=1):
        path = session_dir / f"p{idx:03d}.png"
        panel.image.save(path, format="PNG")
        renders.append({
            "page": idx,
            "label": panel.name,
            "path": str(path),
            "uri": f"framegraph://session/{sid}/page/{idx}.png",
            "mimeType": "image/png",
            "bytes": path.stat().st_size,
        })
        comparison.append({
            "panel": idx,
            "region": panel.name,
            "pixel_match_pct": panel.match_pct,
            "metrics": panel.metrics,
        })

    result = {
        "ok": True,
        "session_id": sid,
        "session_dir": str(session_dir),
        "reference": reference,
        "candidate": candidate,
        "region_count": len(region_objs),
        "renders": renders,
        "resources": _compare_resources(sid, renders),
        "comparison": comparison,
        "diagnostics_path": str(session_dir / "diagnostics.json"),
        "diagnostics_uri": f"framegraph://session/{sid}/diagnostics.json",
    }
    _apply_session_stamp(result, tool="compare_images", replaced=replaced)
    _write_diagnostics(session_dir, result)
    return result


def _parse_named_boxes(items: list[dict[str, Any]] | None, *, kind: str):
    """Parse ``[{"name": str, "box": [x, y, w, h]}]`` (normalized) into Regions."""
    from framegraph.vision.infrastructure.image_compare import Region

    out = []
    for i, r in enumerate(items or []):
        box = r.get("box") if isinstance(r, dict) else None
        if not box or len(box) != 4:
            raise ValueError(f"{kind} {i} needs a normalized box [x, y, w, h] in 0..1")
        name = str(r.get("name") or f"{kind}{i + 1}")
        out.append(Region(name, tuple(float(v) for v in box)))
    return out


def _measure_regions(regions: list[dict[str, Any]] | None, region_grid: list[int] | None):
    """Explicit named regions win; else a [cols, rows] grid; else none."""
    from framegraph.vision.infrastructure.image_compare import auto_regions

    if regions:
        return _parse_named_boxes(regions, kind="region")
    if region_grid:
        if len(region_grid) != 2:
            raise ValueError("region_grid must be [cols, rows]")
        return auto_regions(int(region_grid[0]), int(region_grid[1]))
    return []


def _write_image_pages(session_dir: Path, sid: str,
                       pages: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    """Save ``(label, PIL image)`` pages to the session dir as p001.png, p002.png, ..."""
    renders: list[dict[str, Any]] = []
    for idx, (label, page_img) in enumerate(pages, start=1):
        path = session_dir / f"p{idx:03d}.png"
        page_img.save(path, format="PNG")
        renders.append({
            "page": idx,
            "label": label,
            "path": str(path),
            "uri": f"framegraph://session/{sid}/page/{idx}.png",
            "mimeType": "image/png",
            "bytes": path.stat().st_size,
        })
    return renders


def _viewport_region(viewport: dict[str, Any] | None):
    """Parse a single ``{"name", "box": [x, y, w, h]}`` viewport into a Region or None."""
    if viewport is None:
        return None
    from framegraph.vision.infrastructure.image_compare import Region

    box = viewport.get("box") if isinstance(viewport, dict) else None
    if not box or len(box) != 4:
        raise ValueError('viewport needs a normalized box [x, y, w, h] in 0..1')
    name = str(viewport.get("name") or "viewport")
    return Region(name, tuple(float(v) for v in box))


def measure_image(
    image: str,
    *,
    regions: list[dict[str, Any]] | None = None,
    region_grid: list[int] | None = None,
    zooms: list[dict[str, Any]] | None = None,
    origin: str = "top-left",
    grid: bool = True,
    grid_step: int | None = None,
    rulers: bool = True,
    label_every: int = 2,
    landmarks: bool = True,
    detect_landmarks: bool = True,
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Overlay a measurement layer on an image and extract exact spatial metadata.

    Turns a rasterized image into a reliable coordinate reference for vector
    reconstruction: the returned overlay PNG (same pixel size as the source, so
    coordinates read 1:1) carries a grid, edge rulers labelled in the chosen
    coordinate system, region boxes with stable IDs, and landmark crosshairs; the
    ``spatial`` payload carries the exact numbers (coordinate system, per-region
    bbox/centroid/area/offset, structural + detected landmarks, and — for each zoom
    crop — the ``origin``+``scale`` transform back to source pixels). ``image`` is a
    filesystem path or a ``framegraph://session/<id>/page/<n>.png`` URI.

    ⚠ PALS's LAW: the coordinate system, grid, rulers, explicit regions, and
    structural landmarks (A1..A9) are exact geometry; *detected* landmarks (L*) are
    UNVERIFIED CV guesses — anchor to the structural anchors, treat the rest as hints.
    """
    try:
        image_bytes = _resolve_image_arg(image, session_root=session_root)
    except (ValueError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        from framegraph.vision.infrastructure.measure import build_measurement
    except RuntimeError as exc:  # Pillow missing
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        region_objs = _measure_regions(regions, region_grid)
        zoom_objs = _parse_named_boxes(zooms, kind="zoom")
        measurement = build_measurement(
            image_bytes,
            regions=region_objs,
            origin=origin,
            grid=grid,
            grid_step=grid_step,
            rulers=rulers,
            label_every=label_every,
            landmarks=landmarks,
            detect_landmarks=detect_landmarks,
            zooms=zoom_objs,
        )
    except (ValueError, OSError) as exc:
        return {"ok": False, "error": f"could not build measurement: {exc}",
                "renders": [], "resources": []}

    root = _session_root(session_root)
    sid = _session_id(session_id)
    session_dir = _prepare_session(root, sid)
    replaced = _session_replacement_info(session_dir, "measure_image")
    _reset_session_outputs(session_dir)

    pages: list[tuple[str, Any]] = [("overlay", measurement.overlay)]
    pages.extend(measurement.crops)
    renders = _write_image_pages(session_dir, sid, pages)

    result = {
        "ok": True,
        "session_id": sid,
        "session_dir": str(session_dir),
        "image": image,
        "renders": renders,
        "resources": _compare_resources(sid, renders),
        "spatial": measurement.spatial,
        "diagnostics_path": str(session_dir / "diagnostics.json"),
        "diagnostics_uri": f"framegraph://session/{sid}/diagnostics.json",
    }
    _apply_session_stamp(result, tool="measure_image", replaced=replaced)
    _write_diagnostics(session_dir, result)
    return result


def mark_points(
    image: str,
    *,
    points: list[dict[str, Any]],
    viewport: dict[str, Any] | None = None,
    connect: bool = False,
    origin: str = "top-left",
    grid: bool = True,
    rulers: bool = True,
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Mark coordinate points on an image and resolve each in every reference frame.

    The AI's "aim + click": ``points`` may be given in any frame (normalized, source
    pixels, coordinate-system units, an offset from a landmark, or viewport pixels);
    each is drawn as a numbered crosshair and reported back in the full image (px +
    coordinate system + normalized) and, when a ``viewport`` crop is set, in viewport
    pixels. Points are anchored to the image, so the crosshair stays fixed as the
    viewport moves. ``connect`` previews the path they would trace.
    """
    if not isinstance(points, list) or not points:
        return {"ok": False, "error": "points must be a non-empty list", "renders": [], "resources": []}
    try:
        image_bytes = _resolve_image_arg(image, session_root=session_root)
    except (ValueError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        from framegraph.vision.infrastructure.measure import build_marks
    except RuntimeError as exc:  # Pillow missing
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        vp_box = _viewport_region(viewport)
        measurement = build_marks(
            image_bytes, points, viewport_box=vp_box, origin=origin,
            grid=grid, rulers=rulers, connect=connect,
        )
    except (ValueError, OSError) as exc:
        return {"ok": False, "error": f"could not mark points: {exc}",
                "renders": [], "resources": []}

    root = _session_root(session_root)
    sid = _session_id(session_id)
    session_dir = _prepare_session(root, sid)
    replaced = _session_replacement_info(session_dir, "mark_points")
    _reset_session_outputs(session_dir)

    pages: list[tuple[str, Any]] = [("marks", measurement.overlay)]
    pages.extend(measurement.crops)
    renders = _write_image_pages(session_dir, sid, pages)

    result = {
        "ok": True,
        "session_id": sid,
        "session_dir": str(session_dir),
        "image": image,
        "renders": renders,
        "resources": _compare_resources(sid, renders),
        "spatial": measurement.spatial,
        "diagnostics_path": str(session_dir / "diagnostics.json"),
        "diagnostics_uri": f"framegraph://session/{sid}/diagnostics.json",
    }
    _apply_session_stamp(result, tool="mark_points", replaced=replaced)
    _write_diagnostics(session_dir, result)
    return result


def overlay_images(
    base: str,
    overlay: str,
    *,
    landmarks: list[dict[str, Any]],
    opacity: float = 0.5,
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Align an overlay image onto a base by matched landmarks and extract the offsets.

    ``landmarks`` is a list of ``{"base": [x, y], "overlay": [x, y]}`` pairs (source
    pixels, or 0..1 fractions with ``"norm": true``). Fits the scale+translation that
    best maps overlay→base, reports each pair's raw offset and post-fit residual, and
    emits an aligned composite. Rotation/shear are not modelled (large residuals flag
    them). ``base``/``overlay`` are filesystem paths or framegraph://session PNG URIs.
    """
    if not isinstance(landmarks, list) or not landmarks:
        return {"ok": False, "error": "landmarks must be a non-empty list of {base, overlay} pairs",
                "renders": [], "resources": []}
    try:
        base_bytes = _resolve_image_arg(base, session_root=session_root)
        overlay_bytes = _resolve_image_arg(overlay, session_root=session_root)
    except (ValueError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        from framegraph.vision.infrastructure.overlay_align import build_overlay
    except RuntimeError as exc:  # Pillow missing
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        composite, spatial = build_overlay(
            base_bytes, overlay_bytes, landmarks=landmarks, opacity=opacity,
        )
    except (ValueError, OSError) as exc:
        return {"ok": False, "error": f"could not build overlay: {exc}",
                "renders": [], "resources": []}

    root = _session_root(session_root)
    sid = _session_id(session_id)
    session_dir = _prepare_session(root, sid)
    replaced = _session_replacement_info(session_dir, "overlay_images")
    _reset_session_outputs(session_dir)

    renders = _write_image_pages(session_dir, sid, [("aligned-overlay", composite)])

    result = {
        "ok": True,
        "session_id": sid,
        "session_dir": str(session_dir),
        "base": base,
        "overlay": overlay,
        "renders": renders,
        "resources": _compare_resources(sid, renders),
        "spatial": spatial,
        "diagnostics_path": str(session_dir / "diagnostics.json"),
        "diagnostics_uri": f"framegraph://session/{sid}/diagnostics.json",
    }
    _apply_session_stamp(result, tool="overlay_images", replaced=replaced)
    _write_diagnostics(session_dir, result)
    return result


def workspace(
    action: str = "render",
    *,
    image: str | None = None,
    points: list[dict[str, Any]] | None = None,
    select: Any = None,
    to: dict[str, Any] | None = None,
    dx: float = 0.0,
    dy: float = 0.0,
    unit: str = "norm",
    viewport: dict[str, Any] | None = None,
    factor: float | None = None,
    aim: dict[str, Any] | None = None,
    snap_to: str = "bright",
    radius: int = 4,
    scale: float = 1.0,
    rotate: float = 0.0,
    tag: str | None = None,
    index: int = -1,
    geometry: dict[str, Any] | None = None,
    origin: str = "top-left",
    grid: bool = True,
    rulers: bool = True,
    connect: bool = False,
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Stateful coordinate workspace: persist + refine anchor pins across passes.

    One workspace lives per ``session_id`` (persisted as ``workspace.json``). Actions:
    ``open`` (bind an image), ``pin`` (add points in any frame; may reference existing
    pins/landmarks), ``nudge`` (move selected pins by a delta — the AI "mouse", e.g.
    ``unit='norm', dx=-0.01``), ``move`` (absolute), ``unpin``/``clear``, ``viewport``
    (set/clear a crop), ``pan``/``zoom`` (with a fixed aim), and ``render``. Every call
    re-renders the overlay (+ viewport crop) with all pins and returns each pin resolved
    in every frame. Pins are image-anchored, so their coordinates hold as the viewport moves.
    """
    from framegraph.vision.infrastructure import workspace as ws

    try:
        root = _session_root(session_root)
        sid = _session_id(session_id)
        session_dir = _prepare_session(root, sid)
    except ValueError as exc:
        # A bad session_id is an expected input error: return the shared envelope
        # (the sibling tools' contract) instead of raising out of the use case.
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}
    replaced = _session_replacement_info(session_dir, "workspace")
    state = ws.load_state(session_dir)
    action = (action or "render").lower()
    action_info: dict[str, Any] = {}

    try:
        if action == "open":
            if not image:
                raise ValueError("action 'open' needs an image")
            img_bytes = _resolve_image_arg(image, session_root=session_root)
            from framegraph.vision.infrastructure.image_compare import load_rgb
            w, h = load_rgb(img_bytes).size
            state = ws.WorkspaceState(image_ref=image, width=w, height=h, origin=origin)
        else:
            if state is None:
                raise ValueError("no workspace in this session; call action='open' with an image first")
            if action == "pin":
                if not points:
                    raise ValueError("action 'pin' needs a non-empty 'points' list")
                ws.add_pins(state, points)
            elif action == "nudge":
                ws.nudge_pins(state, select, float(dx), float(dy), unit)
            elif action == "move":
                if to is None:
                    raise ValueError("action 'move' needs a 'to' point")
                ws.move_pins(state, select, to)
            elif action == "unpin":
                ws.remove_pins(state, select)
            elif action == "clear":
                state.pins = []
            elif action == "viewport":
                box = viewport.get("box") if isinstance(viewport, dict) else None
                name = str(viewport.get("name", "viewport")) if isinstance(viewport, dict) else "viewport"
                ws.set_viewport(state, box, name=name)
            elif action == "pan":
                ws.pan_viewport(state, float(dx), float(dy))
            elif action == "zoom":
                if factor is None:
                    raise ValueError("action 'zoom' needs a 'factor'")
                ws.zoom_viewport(state, float(factor), aim)
            elif action == "snap":
                snap_bytes = _resolve_image_arg(state.image_ref, session_root=session_root)
                g = geometry or {}
                if snap_to == "edge_subpixel":
                    _, snap_info = ws.snap_pins_subpixel(
                        state, select, snap_bytes,
                        band=float(g.get("band", 8.0)), search_dir=g.get("search_dir"),
                        min_strength=float(g.get("min_strength", 6.0)))
                    action_info["snapped"] = snap_info
                else:
                    snapped = ws.snap_pins(state, select, snap_bytes, to=snap_to, radius=radius)
                    action_info["snapped"] = [p.id for p in snapped]
            elif action == "fit_edge":
                g = geometry or {}
                edge_bytes = _resolve_image_arg(state.image_ref, session_root=session_root)
                _, info = ws.fit_edge_pins(state, select, edge_bytes,
                                           band=float(g.get("band", 6.0)),
                                           step=float(g.get("step", 2.0)),
                                           min_strength=float(g.get("min_strength", 6.0)))
                action_info["fit_edge"] = info
            elif action == "collinear":
                _, info = ws.collinear_pins(state, select)
                action_info["collinear"] = info
            elif action == "symmetrize":
                g = geometry or {}
                _, info = ws.symmetrize_pins(state, g.get("pairs") or [], axis=g.get("axis"))
                action_info["symmetrize"] = info
            elif action == "intersect":
                g = geometry or {}
                if not (g.get("edge1") and g.get("edge2") and g.get("target")):
                    raise ValueError("action 'intersect' needs geometry={'edge1':[ids], "
                                     "'edge2':[ids], 'target':id}")
                inter_bytes = _resolve_image_arg(state.image_ref, session_root=session_root)
                _, info = ws.intersect_to_pin(
                    state, inter_bytes, edge1=g["edge1"], edge2=g["edge2"], target=g["target"],
                    band=float(g.get("band", 6.0)), step=float(g.get("step", 2.0)),
                    min_strength=float(g.get("min_strength", 6.0)))
                action_info["intersect"] = info
            elif action == "transform":
                moved = ws.transform_pins(state, select, translate=(float(dx), float(dy)),
                                          scale=float(scale), rotate=float(rotate), about=aim)
                action_info["transformed"] = [p.id for p in moved]
            elif action == "checkpoint":
                action_info["checkpoint_index"] = ws.checkpoint_state(state, tag)
            elif action == "revert":
                action_info.update(ws.revert_state(state, int(index)))
            elif action in ("render", "status"):
                pass
            else:
                raise ValueError(f"unknown action {action!r}")
    except (ValueError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        img_bytes = _resolve_image_arg(state.image_ref, session_root=session_root)
        measurement = ws.render(img_bytes, state, grid=grid, rulers=rulers, connect=connect)
    except (ValueError, FileNotFoundError, RuntimeError, OSError) as exc:
        return {"ok": False, "error": f"could not render workspace: {exc}",
                "renders": [], "resources": []}

    _reset_session_outputs(session_dir)
    ws.save_state(session_dir, state)
    pages: list[tuple[str, Any]] = [("workspace", measurement.overlay)]
    pages.extend(measurement.crops)
    renders = _write_image_pages(session_dir, sid, pages)

    result = {
        "ok": True,
        "session_id": sid,
        "session_dir": str(session_dir),
        "action": action,
        "image": state.image_ref,
        "renders": renders,
        "resources": _compare_resources(sid, renders),
        "spatial": measurement.spatial,
        "checkpoint_count": len(state.checkpoints),
        "diagnostics_path": str(session_dir / "diagnostics.json"),
        "diagnostics_uri": f"framegraph://session/{sid}/diagnostics.json",
    }
    if action_info:
        result["action_info"] = action_info
    _apply_session_stamp(result, tool="workspace", replaced=replaced)
    _write_diagnostics(session_dir, result)
    return result


def _resolve_shape_points(shapes: list[dict[str, Any]], anchors: dict[str, tuple[float, float]]):
    """Turn each shape's ``pins`` (workspace ids/landmarks) into image-pixel ``points``."""
    out = []
    for i, sh in enumerate(shapes):
        sh = dict(sh)
        if sh.get("pins"):
            pts = []
            for pid in sh["pins"]:
                key = str(pid)
                if key not in anchors:
                    raise ValueError(f"shape {i}: unknown pin/landmark {key!r}")
                pts.append(list(anchors[key]))
            sh["points"] = pts
        out.append(sh)
    return out


def construct_vectors(
    shapes: list[dict[str, Any]],
    *,
    image: str | None = None,
    from_workspace: str | None = None,
    width: int | None = None,
    height: int | None = None,
    background: str | None = None,
    title: str = "Vector reconstruction",
    raster_png: bool = True,
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Draw FrameGraph vector geometry from anchor points, then validate + render it.

    ``shapes`` is a list of ``{"kind": ..., "points"|"pins": [...], "style"?: {...}}``.
    ``points`` are image pixels; ``pins`` reference a workspace's pin ids (or structural
    landmarks A1..A9) — resolved from the ``from_workspace`` (or ``session_id``) workspace.
    The page is sized to the source (workspace/image dims, or explicit width/height), so
    the drawing overlays the raster 1:1. Compare the render against the source with
    ``compare_images`` to iterate toward pixel accuracy.
    """
    if not isinstance(shapes, list) or not shapes:
        return {"ok": False, "error": "shapes must be a non-empty list", "renders": [], "resources": []}

    root = _session_root(session_root)
    state = None
    ws_ref = from_workspace or session_id
    if ws_ref:
        from framegraph.vision.infrastructure import workspace as ws
        ws_dir = root / _session_id(ws_ref)
        if ws_dir.exists():
            state = ws.load_state(ws_dir)

    W = int(width) if width else None
    H = int(height) if height else None
    if not (W and H) and state is not None:
        W, H = state.width, state.height
    if not (W and H) and image:
        try:
            img_bytes = _resolve_image_arg(image, session_root=session_root)
            from framegraph.vision.infrastructure.image_compare import load_rgb
            W, H = load_rgb(img_bytes).size
        except (ValueError, FileNotFoundError, OSError) as exc:
            return {"ok": False, "error": str(exc), "renders": [], "resources": []}
    if not (W and H):
        return {"ok": False, "error": "need a canvas size: pass width+height, a from_workspace, or an image",
                "renders": [], "resources": []}

    anchors = _workspace_anchors(ws_ref, session_root)

    try:
        resolved = _resolve_shape_points(shapes, anchors)
        from framegraph.vision.infrastructure.construct import build_document
        yaml_text, summaries = build_document(
            resolved, width=W, height=H, background=background, title=title)
    except (ValueError, KeyError, TypeError) as exc:
        return {"ok": False, "error": f"could not construct vectors: {exc}",
                "renders": [], "resources": []}

    source = RawYamlSource(yaml_text=yaml_text, session_id=session_id, session_root=session_root)
    result = _run_source(
        source, max_pages=1, raster_png=raster_png, pages=None, sign=False, signed_at=None,
        tool="construct_vectors")
    result["construction"] = summaries
    result["shape_count"] = len(summaries)
    if image:
        result["source_image"] = image
    return result


def _workspace_anchors(ws_ref: str | None, session_root: str | Path | None):
    """Resolve a workspace's pins + structural landmarks to {id: (x_px, y_px)} (or {}).

    Returns ``{}`` when there is no such workspace — including the common case where the
    session DIR exists (any image tool creates it) but has no ``workspace.json`` yet, so
    ``load_state`` returns ``None``. Without this guard a shared session_id across e.g.
    construct_vectors → score_reconstruction would crash dereferencing ``None.pins``.
    """
    if not ws_ref:
        return {}
    from framegraph.vision.infrastructure import workspace as ws
    ws_dir = _session_root(session_root) / _session_id(ws_ref)
    if not ws_dir.exists():
        return {}
    state = ws.load_state(ws_dir)
    if state is None:
        return {}
    from framegraph.vision.infrastructure.measure import structural_landmarks
    anchors = {p.id: (p.x, p.y) for p in state.pins}
    anchors.update({lm.id: (lm.x_px, lm.y_px) for lm in structural_landmarks(state.cs())})
    return anchors


def score_reconstruction(
    image: str,
    shapes: list[dict[str, Any]],
    *,
    from_workspace: str | None = None,
    roi: list[float] | None = None,
    tol: float = 2.0,
    symmetry_pairs: list[Any] | None = None,
    collinear_groups: list[Any] | None = None,
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Score how well constructed vector ``shapes`` sit on the source image's edges.

    The NUMERIC convergence signal for the raster→vector loop: complements
    ``compare_images`` (which shows *where* a reconstruction is off) by reporting *how
    far* — ``on_edge_frac`` (fraction of shape samples within ``tol`` px of a detected
    edge) plus mean/median/p90 distances. Drive ``on_edge_frac`` up and the distances
    down across refinement passes. ``shapes`` use the same schema as
    ``construct_vectors`` (``points`` image px, or ``pins`` referencing a
    ``from_workspace``); ``roi`` is an optional ``[x0, y0, x1, y1]`` pixel window.

    ``symmetry_pairs`` (``[[[lx,ly],[rx,ry]], ...]``) and ``collinear_groups``
    (``[[[x,y],...], ...]``) add a **geometry-consistency** report under
    ``score.geometry`` — the internal-symmetry and edge-collinearity residuals that
    catch a single-corner offset (e.g. a 9 px apex shift) an image-wide luminance match
    is blind to. This is the metric the luminance % could not be.

    ⚠ PALS's LAW: edges come from an adaptive Sobel heuristic — use the score as a
    RELATIVE guide across passes, not an absolute correctness proof.
    """
    if not isinstance(shapes, list) or not shapes:
        return {"ok": False, "error": "shapes must be a non-empty list", "renders": [], "resources": []}
    try:
        img_bytes = _resolve_image_arg(image, session_root=session_root)
    except (ValueError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        from framegraph.vision.infrastructure import matchscore
    except ImportError:
        return _vision_error(_VISION_GROUP_HINT)

    try:
        anchors = _workspace_anchors(from_workspace or session_id, session_root)
        resolved = _resolve_shape_points(shapes, anchors)
        overlay, score = matchscore.build_score_overlay(img_bytes, resolved,
                                                        roi=roi, tol=float(tol))
    except (ValueError, KeyError, TypeError, RuntimeError, OSError) as exc:
        return {"ok": False, "error": f"could not score reconstruction: {exc}",
                "renders": [], "resources": []}

    if "error" in score:
        # a scoring failure (no edges / no samples in roi): match the sibling tools'
        # degraded envelope — a top-level `error` and no artifacts — rather than writing
        # a misleading overlay with the reason buried in `score`.
        return {"ok": False, "error": score["error"], "score": score,
                "renders": [], "resources": []}

    if symmetry_pairs or collinear_groups:
        from framegraph.vision.domain import geometry as _geom
        try:
            # geometry args accept workspace pin/landmark ids ("P3" / "A9") as well
            # as raw [x, y] points — resolved against the SAME anchors the shape
            # `pins` use, so a nudged pin re-scores without re-typing coordinates.
            resolved_pairs, resolved_groups = matchscore.resolve_geometry_args(
                symmetry_pairs, collinear_groups, anchors)
            score["geometry"] = _geom.consistency_report(
                symmetry_pairs=resolved_pairs, collinear_groups=resolved_groups,
                tol=float(tol))
        except (ValueError, TypeError, IndexError) as exc:
            score["geometry"] = {"error": f"could not compute consistency: {exc}"}

    root = _session_root(session_root)
    sid = _session_id(session_id)
    session_dir = _prepare_session(root, sid)
    replaced = _session_replacement_info(session_dir, "score_reconstruction")
    _reset_session_outputs(session_dir)
    renders = _write_image_pages(session_dir, sid, [("match-score", overlay)])

    result = {
        "ok": True,
        "session_id": sid,
        "session_dir": str(session_dir),
        "image": image,
        "renders": renders,
        "resources": _compare_resources(sid, renders),
        "score": score,
        "diagnostics_path": str(session_dir / "diagnostics.json"),
        "diagnostics_uri": f"framegraph://session/{sid}/diagnostics.json",
    }
    _apply_session_stamp(result, tool="score_reconstruction", replaced=replaced)
    _write_diagnostics(session_dir, result)
    return result


def detect_regions(
    image: str,
    *,
    method: str = "consensus",
    cluster: str | None = None,
    cluster_tol: float = 0.90,
    overlay: bool = True,
    max_regions: int = 400,
    include_polygons: bool = True,
    tunables: dict[str, Any] | None = None,
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Detect an image's closed/filled/stable regions and report exact geometry.

    Wraps the pure :func:`framegraph.vision.infrastructure.regions.detect_regions`
    in the shared session envelope: the annotated overlay becomes the session's
    page-1 render artifact and the detection payload rides ``spatial`` (method,
    params, region list with ``bbox_px`` + ``box_norm`` + centroids + sampled
    fill + polygon/holes, optional shape-equivalence ``classes``). Regions feed
    ``workspace`` pins and ``construct_vectors`` points directly: ``bbox_px`` /
    ``centroid_px`` are image pixels, ``box_norm`` the normalized box the other
    tools accept.

    ⚠ PALS's LAW: thresholds, k-means palettes, and level-set ensembles are
    heuristics — verify the overlay + numbers against the source, never trust
    the region list alone.
    """
    try:
        image_bytes = _resolve_image_arg(image, session_root=session_root)
    except (ValueError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    try:
        from framegraph.vision.infrastructure import regions as _regions
    except ImportError:
        return _vision_error(_VISION_GROUP_HINT)

    try:
        root = _session_root(session_root)
        sid = _session_id(session_id)
        session_dir = _prepare_session(root, sid)
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}
    replaced = _session_replacement_info(session_dir, "detect_regions")

    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="fg-regions-"))
    overlay_final: Path | None = None
    try:
        # Preserve the vector suffix: regions.load_image rasterises only *.svg
        # paths, so writing SVG bytes to a .png-named file would hand raw XML
        # to cv2.imread (documented '.svg — rasterised first' support).
        is_svg = (isinstance(image, str) and image.lower().endswith(".svg")) or (
            b"<svg" in image_bytes[:512].lower())
        src = tmp / ("src.svg" if is_svg else "src.png")
        src.write_bytes(image_bytes)
        overlay_tmp = tmp / "overlay.png" if overlay else None
        try:
            analysis = _regions.detect_regions(
                src, method,
                overlay_path=overlay_tmp,
                include_polygons=include_polygons,
                cluster=cluster,
                cluster_tol=float(cluster_tol),
                max_regions=int(max_regions),
                **dict(tunables or {}),
            )
        except ImportError as exc:
            return _vision_error(f"region detection backend unavailable: {exc}",
                                 hint="install the `vision` group (OpenCV + NumPy)")
        except (ValueError, TypeError) as exc:
            return {"ok": False, "error": f"could not detect regions: {exc}",
                    "hint": "method is 'closed' | 'flat' | 'consensus'; tunables are "
                            "method-specific (unknown names are rejected, not ignored)",
                    "renders": [], "resources": []}
        # Success: only now replace the session's prior render artifacts, so a
        # failed call never clobbers what the previous tool left behind.
        _reset_session_outputs(session_dir)
        if overlay_tmp is not None and overlay_tmp.exists():
            overlay_final = session_dir / "p001.png"
            shutil.copyfile(overlay_tmp, overlay_final)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    renders: list[dict[str, Any]] = []
    if overlay_final is not None:
        renders.append({
            "page": 1,
            "label": f"regions:{method}",
            "path": str(overlay_final),
            "uri": f"framegraph://session/{sid}/page/1.png",
            "mimeType": "image/png",
            "bytes": overlay_final.stat().st_size,
        })

    # the pure function's payload IS the spatial numbers; its ok/overlay_path
    # bookkeeping belongs to the envelope, not the payload.
    spatial = {k: v for k, v in analysis.items() if k not in ("ok", "overlay_path")}
    spatial["image"] = dict(spatial.get("image") or {}, path=image)
    result = {
        "ok": True,
        "session_id": sid,
        "session_dir": str(session_dir),
        "image": image,
        "renders": renders,
        "resources": _compare_resources(sid, renders),
        "spatial": spatial,
        "diagnostics_path": str(session_dir / "diagnostics.json"),
        "diagnostics_uri": f"framegraph://session/{sid}/diagnostics.json",
    }
    _apply_session_stamp(result, tool="detect_regions", replaced=replaced)
    _write_diagnostics(session_dir, result)
    return result


def map_coordinates(
    mode: str,
    *,
    points: list[list[float]] | None = None,
    pairs: list[dict[str, Any]] | None = None,
    plane: dict[str, Any] | None = None,
    camera: dict[str, Any] | None = None,
    image: str | None = None,
    out_size: list[int] | None = None,
    width: int | None = None,
    height: int | None = None,
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Transpose coordinates between 2D/3D frames: homography, plane lift, projection, warp.

    - ``mode='homography'``: fit a projective transform from ``pairs``
      (``[{"src": [x, y], "dst": [x, y]}]``, >=4) and apply it to ``points``.
    - ``mode='to_3d'``: lift 2D ``points`` onto a 3D ``plane`` ({origin, u, v}; default z=0).
    - ``mode='project'``: project 3D ``points`` through a ``camera`` ({eye, target, up,
      fov, ...}); returns NDC and, with ``width``/``height``, pixels.
    - ``mode='warp'``: fit the homography from ``pairs`` and rectify ``image`` into an
      ``out_size`` [w, h] canvas (perspective correction); emits the dewarped PNG.
    """
    try:
        from framegraph.vision.infrastructure import mapping3d
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}

    mode = (mode or "").lower()
    if mode == "warp":
        if not pairs or len(pairs) < 4:
            return {"ok": False, "error": "warp needs >= 4 pairs of {src, dst}", "renders": [], "resources": []}
        if not image:
            return {"ok": False, "error": "warp needs an 'image'", "renders": [], "resources": []}
        try:
            image_bytes = _resolve_image_arg(image, session_root=session_root)
            from framegraph.vision.infrastructure.image_compare import load_rgb
            iw, ih = load_rgb(image_bytes).size
            osz = out_size or [iw, ih]
            H = mapping3d.fit_homography([(p["src"], p["dst"]) for p in pairs])
            warped = mapping3d.warp_image(image_bytes, H, osz)
        except (ValueError, FileNotFoundError, KeyError, TypeError, RuntimeError, OSError) as exc:
            return {"ok": False, "error": f"could not warp: {exc}", "renders": [], "resources": []}
        root = _session_root(session_root)
        sid = _session_id(session_id)
        session_dir = _prepare_session(root, sid)
        replaced = _session_replacement_info(session_dir, "map_coordinates")
        _reset_session_outputs(session_dir)
        renders = _write_image_pages(session_dir, sid, [("rectified", warped)])
        result = {
            "ok": True, "session_id": sid, "session_dir": str(session_dir),
            "mode": "warp", "image": image, "renders": renders,
            "resources": _compare_resources(sid, renders),
            "spatial": {"matrix": [[round(v, 8) for v in row] for row in H],
                        "out_size": [int(osz[0]), int(osz[1])]},
            "diagnostics_path": str(session_dir / "diagnostics.json"),
            "diagnostics_uri": f"framegraph://session/{sid}/diagnostics.json",
        }
        _apply_session_stamp(result, tool="map_coordinates", replaced=replaced)
        _write_diagnostics(session_dir, result)
        return result

    try:
        if mode == "homography":
            if not pairs or len(pairs) < 4:
                raise ValueError("homography needs >= 4 pairs of {src, dst}")
            pair_list = [(p["src"], p["dst"]) for p in pairs]
            spatial = mapping3d.homography_map(pair_list, points or [])
        elif mode == "to_3d":
            pl = plane or {}
            spatial = mapping3d.lift_to_plane(
                points or [],
                origin=pl.get("origin", (0.0, 0.0, 0.0)),
                u=pl.get("u", (1.0, 0.0, 0.0)),
                v=pl.get("v", (0.0, 1.0, 0.0)),
            )
        elif mode == "project":
            spatial = mapping3d.project_points(
                points or [], camera=camera, width=width, height=height)
        else:
            raise ValueError(f"unknown mode {mode!r}; use 'homography', 'to_3d', 'project', or 'warp'")
    except (ValueError, KeyError, TypeError, RuntimeError) as exc:
        return {"ok": False, "error": f"could not map coordinates: {exc}"}

    return {"ok": True, "mode": mode, "spatial": spatial}


def _shift_path_d(d: str, dx: float, dy: float) -> str:
    """Shift an absolute M/L/Z path ``d`` (as emitted by the layers tracer) by (dx, dy).

    Returns the string unchanged if it uses any command this simple shifter doesn't
    handle, so it never silently corrupts a curve path.
    """
    toks = str(d).split()
    out: list[str] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t in ("M", "L"):
            if i + 2 >= len(toks):
                return d
            out += [t, "%.2f" % (float(toks[i + 1]) + dx), "%.2f" % (float(toks[i + 2]) + dy)]
            i += 3
        elif t == "Z":
            out.append("Z")
            i += 1
        else:
            return d
    return " ".join(out)


def _translate_objects(objects: list[dict[str, Any]], dx: float, dy: float) -> list[dict[str, Any]]:
    """Shift every object's geometry by (dx, dy) — for placing a cropped trace in the full image."""
    if not dx and not dy:
        return objects
    for o in objects:
        if isinstance(o.get("points"), list):
            o["points"] = [[float(p[0]) + dx, float(p[1]) + dy] for p in o["points"]]
        if isinstance(o.get("d"), str):
            o["d"] = _shift_path_d(o["d"], dx, dy)
        box = o.get("box")
        if isinstance(box, list) and len(box) >= 2:
            o["box"] = [float(box[0]) + dx, float(box[1]) + dy, *box[2:]]
        center = o.get("center")
        if isinstance(center, list) and len(center) == 2:
            o["center"] = [float(center[0]) + dx, float(center[1]) + dy]
    return objects


def vectorize_image(
    image: str,
    *,
    mode: str = "region",
    region_box: list[float] | None = None,
    colors: int | None = None,
    detail: float | None = None,
    min_area: float | None = None,
    max_dim: int | None = None,
    ink: str = "#1E2440",
    stroke_width: float = 1.0,
    threshold: int | None = None,
    invert: Any = "auto",
    turdsize: int = 2,
    alphamax: float = 1.0,
    opttolerance: float = 0.2,
    fill: str = "#000000",
    background: str | None = None,
    ocr: bool = False,
    title: str = "Vectorized reconstruction",
    raster_png: bool = True,
    session_id: str | None = None,
    session_root: str | Path | None = None,
) -> dict[str, Any]:
    """Trace a raster into editable FrameGraph vector objects, then validate + render it.

    Modes: ``region`` (k-means colour → filled polygons; best for flat/logo art),
    ``outline`` (edge → polylines), ``trace`` (potrace Bézier → SVG ingest; smooth
    curves — needs the potrace binary), ``layers`` (solid-bg logo tracer), or
    ``auto`` (classify the raster and route to the best mode — the decision +
    presets are reported under ``result.vectorize.auto``; explicit args always
    win over the route's presets). ``region_box`` (normalized) vectorizes just a
    crop, placed back in full-image coordinates. ``ocr=True`` adds Tesseract text
    objects and reports the OCR backend status under ``result.vectorize.ocr``
    (never a silent empty list). Sizes the page to the source so the
    reconstruction overlays 1:1; diff it against the source with ``compare_images``.
    """
    try:
        image_bytes = _resolve_image_arg(image, session_root=session_root)
    except (ValueError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc), "renders": [], "resources": []}

    import tempfile

    try:
        from PIL import Image
    except ImportError:
        return {"ok": False, "error": "vectorize needs Pillow (the `vision` group)",
                "renders": [], "resources": []}

    auto_meta: dict[str, Any] | None = None
    ocr_status: dict[str, Any] | None = None
    tmp = Path(tempfile.mkdtemp(prefix="fg-vec-"))
    try:
        src = tmp / "src.png"
        src.write_bytes(image_bytes)
        img = Image.open(src).convert("RGB")
        W, H = img.size
        ox = oy = 0.0
        try:
            if mode == "auto":
                from framegraph.vision.infrastructure.vectorize import resolve_auto_mode
                mode, auto_meta = resolve_auto_mode(src)
                # Route presets apply ONLY to args the caller left unset (None
                # sentinel) — an explicitly passed value always wins over the
                # router, even when it equals the documented default (PALS:
                # the router is a heuristic the caller can override).
                presets = auto_meta["presets"]
                if "colors" in presets and colors is None:
                    colors = int(presets["colors"])
                if "detail" in presets and detail is None:
                    detail = float(presets["detail"])
                if "min_area" in presets and min_area is None:
                    min_area = float(presets["min_area"])
                if "max_dim" in presets and max_dim is None:
                    max_dim = int(presets["max_dim"])
            # Resolve remaining sentinels to the documented defaults.
            colors = 8 if colors is None else int(colors)
            detail = 0.004 if detail is None else float(detail)
            min_area = 90.0 if min_area is None else float(min_area)
            max_dim = 900 if max_dim is None else int(max_dim)
            if mode in ("region", "outline"):
                from framegraph.vision.infrastructure.vectorize import raster_to_objects
                if region_box:
                    from framegraph.vision.infrastructure.measure import denorm_box
                    ox, oy, cw, ch = denorm_box(
                        region_box[0], region_box[1], region_box[2], region_box[3], W, H)
                    crop_path = tmp / "crop.png"
                    img.crop((int(ox), int(oy), int(round(ox + cw)), int(round(oy + ch)))).save(crop_path)
                    objects, _, _ = raster_to_objects(
                        crop_path, mode=mode, colors=colors, detail=detail,
                        min_area=min_area, max_dim=0, ink=ink, stroke_width=stroke_width)
                    _translate_objects(objects, ox, oy)
                    page_w, page_h = W, H
                else:
                    objects, page_w, page_h = raster_to_objects(
                        src, mode=mode, colors=colors, detail=detail, min_area=min_area,
                        max_dim=max_dim, ink=ink, stroke_width=stroke_width)
                backend = f"opencv:{mode}"
            elif mode == "trace":
                from framegraph.vision.infrastructure.svg_import import svg_to_objects
                from framegraph.vision.infrastructure.vectorize import trace_to_svg
                svg, tmeta = trace_to_svg(
                    src, region_box=region_box, threshold=threshold, invert=invert,
                    turdsize=turdsize, alphamax=alphamax, opttolerance=opttolerance, fill=fill)
                box = tmeta["region_px"] if region_box else None
                if region_box:
                    ox, oy = tmeta["region_px"][0], tmeta["region_px"][1]
                objects = svg_to_objects(svg, box=box)
                page_w, page_h = W, H
                backend = "potrace"
            elif mode == "layers":
                from framegraph.vision.infrastructure.vectorize import raster_to_layers
                if region_box:
                    from framegraph.vision.infrastructure.measure import denorm_box
                    ox, oy, cw, ch = denorm_box(
                        region_box[0], region_box[1], region_box[2], region_box[3], W, H)
                    crop_path = tmp / "crop.png"
                    img.crop((int(ox), int(oy), int(round(ox + cw)), int(round(oy + ch)))).save(crop_path)
                    objects, _, _ = raster_to_layers(crop_path, max_colors=colors, detail=detail)
                    _translate_objects(objects, ox, oy)
                    page_w, page_h = W, H
                else:
                    objects, page_w, page_h = raster_to_layers(src, max_colors=colors, detail=detail)
                backend = "opencv:layers"
            else:
                return {"ok": False,
                        "error": f"unknown mode {mode!r}; use 'auto', 'region', 'outline', "
                                 "'trace', or 'layers'",
                        "renders": [], "resources": []}
            if ocr:
                # The status variant makes the degradation observable (PALS's Law):
                # a silent [] was indistinguishable from a text-free image.
                from framegraph.vision.infrastructure.vectorize import ocr_text_objects_status
                ocr_objects, ocr_status = ocr_text_objects_status(src)
                objects = list(objects) + ocr_objects
        except ImportError as exc:
            return {"ok": False, "error": f"vectorize backend unavailable: {exc}. "
                    "region/outline need the `vision` group (OpenCV); trace needs the potrace binary.",
                    "renders": [], "resources": []}
        except (RuntimeError, ValueError, OSError) as exc:
            return {"ok": False, "error": f"could not vectorize: {exc}", "renders": [], "resources": []}
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    if not objects:
        return {"ok": False, "error": "the image produced no drawable objects (tune colors/threshold/min_area)",
                "renders": [], "resources": []}

    from framegraph.sdk.author import DocumentBuilder
    from framegraph.sdk.io import serialize

    builder = DocumentBuilder(title=title, lang="en")
    page = builder.page("vectorized", canvas={"size": [int(page_w), int(page_h)], "units": "px"},
                        coordinate_mode="absolute")
    if background:
        page.rect([0, 0, int(page_w), int(page_h)], fill=background)
    layer = page.layer("ingest")
    with layer.bleed():
        for obj in objects:
            layer.add(obj)

    source = RawYamlSource(yaml_text=serialize(builder.build(), format="yaml"),
                           session_id=session_id, session_root=session_root)
    result = _run_source(
        source, max_pages=1, raster_png=raster_png, pages=None, sign=False, signed_at=None,
        tool="vectorize_image")
    result["vectorize"] = {
        "mode": mode, "backend": backend, "object_count": len(objects),
        "page_px": [int(page_w), int(page_h)],
        "region_px": [round(ox, 2), round(oy, 2)] if region_box else None,
    }
    if auto_meta is not None:
        result["vectorize"]["auto"] = auto_meta
    if ocr_status is not None:
        result["vectorize"]["ocr"] = ocr_status
    result["source_image"] = image
    return result


def apply_anchored_edit(code: str, old_string: str, new_string: str) -> str:
    """Exact-match, single-occurrence replacement for ``write_sdk_client`` edits.

    The anchored-edit alternative to whole-file replacement: ``old_string`` must
    match the current file content exactly once (extend it with surrounding lines
    until unique), mirroring the contract of editor-style replace tools.
    """
    if not isinstance(old_string, str) or not old_string:
        raise ValueError("old_string must be a non-empty string")
    if not isinstance(new_string, str):
        raise ValueError("new_string must be a string")
    if old_string == new_string:
        raise ValueError("old_string and new_string are identical — nothing to change")
    count = code.count(old_string)
    if count == 0:
        raise ValueError(
            "old_string was not found in the client file — read_sdk_client the current "
            "contents and pass the exact text to replace"
        )
    if count > 1:
        raise ValueError(
            f"old_string matches {count} locations — extend it with surrounding lines "
            "until it is unique"
        )
    return code.replace(old_string, new_string, 1)
