"""Model Context Protocol tools for SDK-code render feedback.

The public contract is intentionally narrow: callers provide Python code that
uses :mod:`framegraph.sdk`, the code emits or yields a FrameGraph document, and
this module validates and renders that generated YAML into per-session artifacts.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from typing import Any
from urllib.parse import unquote, urlparse

from framegraph.sdk.conform import render_page_svgs
from framegraph.sdk.io import parse
from framegraph.sdk.validate import ValidationReport, validate_static_rules

SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
# Wall-clock budget for the code-execution subprocess. A build that exceeds it is
# reported as a structured ``ok:false`` (see ``_subprocess_timeout_result``), not a
# raised traceback. 20s leaves headroom for heavier decks (3D meshes, large fixtures)
# while still bounding a runaway client; callers can raise it per call.
DEFAULT_TIMEOUT_SECONDS = 20
MAX_CODE_BYTES = 200_000
MAX_CLIENT_BYTES = 2_000_000
DEFAULT_CLIENT_ROOTS = ("examples",)
BUILD_FUNCTION_NAMES = ("build", "build_deck", "build_book", "build_package")
FRAMEGRAPH_YAML_PATTERNS = ("*.fg.yaml", "*.fg.yml", "*.framegraph.yaml", "*.framegraph.yml")
STRUCTURED_LOG_SCHEMA = "framegraph.mcp.structured_log.v1"

# Vision models can only decode raster image bytes; SVG is not a viewable image
# media type, so an ``image/svg+xml`` content block reaches the model as an
# undecodable payload (silently dropped at best). Only these mimes are emitted as
# image content blocks — SVG stays a resource link / text artifact.
VIEWABLE_IMAGE_MIME = ("image/png", "image/jpeg", "image/gif", "image/webp")
# The in-process SVG renderer is not subprocess-isolated; a pathological (but
# schema-valid) document could spin without bound. This soft ceiling caps the
# response latency. Honest limit: it bounds the *response*, not the CPU work — a
# runaway render keeps running in a detached daemon thread until it finishes.
DEFAULT_RENDER_TIMEOUT_SECONDS = 30
# Structured-log hygiene: rotate the JSONL once it crosses this size and clamp
# any single oversized instruction/response string so one giant payload cannot
# bloat (or leak) the whole log.
STRUCTURED_LOG_MAX_BYTES = 5_000_000
STRUCTURED_LOG_MAX_FIELD_CHARS = 20_000
# Env var name fragments that almost always carry a secret. The code-execution
# subprocess runs untrusted SDK code, so these are stripped from its environment
# unless ``FRAMEGRAPH_MCP_KEEP_ENV`` is truthy. Matching is case-insensitive.
SECRET_ENV_RE = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|PRIVATE", re.IGNORECASE)


class RenderTimeoutError(RuntimeError):
    """Raised when in-process SVG rendering exceeds the soft time budget."""

FRAMEGRAPH_GUIDE = """\
# FrameGraph MCP — what the SDK offers and the server's capabilities

FrameGraph v2 is a document/graphics DSL. The Pydantic model is the source of
truth; the SDK lowers Python to validated YAML and this server renders it. Always
verify rendered output — CV/LLM output is unverified by default (PALS's Law).

## Author with the SDK (`framegraph.sdk`)
Fluent builder:
    from framegraph.sdk import DocumentBuilder
    doc = DocumentBuilder(title="Deck", profile="deck")
    h1 = doc.define_text_style("h1", font_family="sans", font_size=48, color="#E8EAED")
    page = doc.page("p1", canvas={"size": [1280, 720], "units": "px"}, coordinate_mode="absolute")
    page.layer("main").rect([0, 0, 1280, 720], fill="#0E0F11")
    page.text([64, 96, 900, 80], "Hello", id="title", style=h1)
    doc.write(OUTPUT_YAML_PATH, fail_on_error=True)

- Primitives via `PageBuilder`: `.rect` `.text` `.line` `.image`, plus `.add(obj)` /
  `.extend(objs)` and `.stack(box, kind="row|column|grid|wrap")` layout groups.
- Paint (`framegraph.sdk.paint`): `stroke(width, color=...)`, `fill_stroke(...)`,
  `linear_gradient`/`radial_gradient`, `hatch`/`dots`/`grid_pattern`/`pattern`,
  `glow`/`neon`/`shadow`/`soft_shadow`, `rgba`. Stroke geometry MUST go through
  `stroke()` (paint in `stroke`, geometry in the inline `stroke_style` bundle);
  an inline `stroke_width` on a paint-only line/polyline/path is rejected.
- Widgets (`framegraph.sdk.widgets`): `avatar` `badge` `button` `card` `kpi` `pill`
  `progress` `table` `tabs` `toggle` `divider` `field`, plus `Panel`/`Theme`.
- Data & geometry: `Chart`+`Frame`, `Graph`/`Node`/`Edge`, `Camera`/`Scene3D`/`Mat3`/
  `Mat4`, `CubicBezier`/`Path`, `ScalarField`/`VectorField`, `lattice`/`manifold`,
  `greeble`, `grid_lines`.
- Validation: `validate_static_rules(doc) -> ValidationReport(ok, issues)`,
  `assert_golden(...)`; `HEAD_VERSION` is the current spec version.

## Server tools
Forward (author -> render):
- `run_sdk_code` / `run_sdk_client` — run Python that builds a doc, then validate + render SVG.
- `write_sdk_client` / `read_sdk_client` / `list_sdk_clients` — edit whitelisted SDK clients.
- `render_framegraph_yaml` — validate + render caller-supplied YAML directly.
- `get_session_resource` — read `framegraph://session/...` artifacts (YAML, SVG, diagnostics).
- `list_sessions` / `cleanup_sessions` — enumerate and prune per-session scratch dirs.

## Seeing the render (visual verification)
A vision model can only *see* a raster (PNG), not SVG. The render tools therefore
rasterize to PNG by default (`raster_png=True`) and attach the PNG as an image
content block; the SVG is kept as a resource link. Rasterization needs the
`browser` dependency group plus `playwright install chromium`. When that backend
is absent the result carries a `render_warning` and ships only the SVG/diagnostics
text — read the warning, install the backend, and re-render to actually verify.

Inverse (image/document -> author), the additional capability:
- `propose_from_image` — classical OpenCV/numpy detectors (+ an optional VLM lane)
  propose a DRAFT document from a screenshot/photo.
- `propose_from_document` — the same pipeline over a rasterised PDF page.
  Both proposals are UNVERIFIED: each tool round-trips the draft through
  validate + render so you immediately see whether it holds, lists which
  detectors ran vs were skipped, and returns the per-object observations. Treat
  the result as a starting point to refine with the SDK — never as final.

## Workflow
Author or propose -> read the returned validation issues + the rendered PNG (or
the `render_warning` when raster is unavailable) -> refine the SDK code/YAML ->
re-render. Verify every rendered result against pixels, never against the YAML alone.
"""


def get_default_session_root() -> Path:
    """Return the default location for MCP session artifacts."""
    configured = os.environ.get("FRAMEGRAPH_MCP_SESSION_ROOT")
    if configured:
        return Path(configured).expanduser()
    return Path(tempfile.gettempdir()) / "framegraph-mcp-sessions"


def get_default_repo_root() -> Path:
    """Return the repository root that contains this MCP package."""
    return Path(__file__).resolve().parents[2]


def run_sdk_code(
    code: str,
    *,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_pages: int = 3,
    raster_png: bool = True,
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
    _reset_session_outputs(session_dir)
    script_path = session_dir / "script.py"
    harness_path = session_dir / "_run_sdk.py"
    yaml_path = session_dir / "generated.fg.yaml"
    script_path.write_text(code, encoding="utf-8")
    harness_path.write_text(_harness_source(script_path, yaml_path, session_dir), encoding="utf-8")

    env = _subprocess_env(get_default_repo_root())
    try:
        proc = subprocess.run(
            [sys.executable, str(harness_path)],
            cwd=str(session_dir),
            env=env,
            text=True,
            capture_output=True,
            timeout=max(1, int(timeout_seconds)),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        result = _subprocess_timeout_result(
            "SDK code", session_id=sid, session_dir=session_dir, yaml_path=yaml_path,
            exc=exc, timeout_seconds=timeout_seconds,
        )
        _write_diagnostics(session_dir, result)
        return result

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


def list_sdk_clients(
    *,
    repo_root: str | Path | None = None,
    edit_roots: str | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """List editable Python SDK client files under the configured safe roots."""
    root = _repo_root(repo_root)
    roots = _client_roots(root, edit_roots)
    clients: list[dict[str, Any]] = []
    for allowed_root in roots:
        if not allowed_root.exists():
            continue
        for path in sorted(allowed_root.rglob("*.py")):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if not any(_is_relative_to(resolved, candidate) for candidate in roots):
                continue
            data = resolved.read_bytes()
            clients.append(
                {
                    "path": _repo_relative_path(resolved, root),
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    return {
        "ok": True,
        "repo_root": str(root),
        "allowed_roots": [_repo_relative_path(path, root) for path in roots],
        "clients": clients,
    }


def read_sdk_client(
    path: str,
    *,
    repo_root: str | Path | None = None,
    edit_roots: str | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Read a whitelisted Python SDK client file for MCP-assisted editing."""
    root = _repo_root(repo_root)
    client_path = _resolve_client_path(path, repo_root=root, edit_roots=edit_roots, must_exist=True)
    code = client_path.read_text(encoding="utf-8")
    return {
        "ok": True,
        "path": _repo_relative_path(client_path, root),
        "absolute_path": str(client_path),
        "bytes": len(code.encode("utf-8")),
        "sha256": _sha256_text(code),
        "code": code,
    }


def write_sdk_client(
    path: str,
    code: str,
    *,
    create: bool = False,
    repo_root: str | Path | None = None,
    edit_roots: str | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Replace or create a whitelisted Python SDK client file."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code must be a non-empty string")
    if len(code.encode("utf-8")) > MAX_CLIENT_BYTES:
        raise ValueError(f"code exceeds {MAX_CLIENT_BYTES} bytes")

    root = _repo_root(repo_root)
    client_path = _resolve_client_path(path, repo_root=root, edit_roots=edit_roots, must_exist=not create)
    if client_path.exists() and not client_path.is_file():
        raise ValueError("SDK client path must resolve to a file")
    if not client_path.exists() and not create:
        raise FileNotFoundError(str(client_path))
    compile(code, _repo_relative_path(client_path, root), "exec")

    previous_sha = None
    if client_path.exists():
        previous_sha = hashlib.sha256(client_path.read_bytes()).hexdigest()
    client_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = client_path.with_name(f".{client_path.name}.tmp")
    tmp_path.write_text(code, encoding="utf-8")
    tmp_path.replace(client_path)

    data = client_path.read_bytes()
    return {
        "ok": True,
        "path": _repo_relative_path(client_path, root),
        "absolute_path": str(client_path),
        "created": previous_sha is None,
        "previous_sha256": previous_sha,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def run_sdk_client(
    path: str,
    *,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_pages: int = 3,
    raster_png: bool = True,
    invoke_main: bool = False,
    repo_root: str | Path | None = None,
    edit_roots: str | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Run an editable Python SDK client file, then validate and render YAML."""
    root = _repo_root(repo_root)
    client_path = _resolve_client_path(path, repo_root=root, edit_roots=edit_roots, must_exist=True)
    session_base = _session_root(session_root)
    sid = _session_id(session_id)
    session_dir = _prepare_session(session_base, sid)
    _reset_session_outputs(session_dir)
    harness_path = session_dir / "_run_sdk_client.py"
    yaml_path = session_dir / "generated.fg.yaml"
    snapshot = _framegraph_yaml_snapshot(root)

    harness_path.write_text(
        _harness_source(client_path, yaml_path, session_dir, invoke_main=invoke_main),
        encoding="utf-8",
    )
    env = _subprocess_env(root)
    try:
        proc = subprocess.run(
            [sys.executable, str(harness_path)],
            cwd=str(root),
            env=env,
            text=True,
            capture_output=True,
            timeout=max(1, int(timeout_seconds)),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        result = _subprocess_timeout_result(
            "SDK client", session_id=sid, session_dir=session_dir, yaml_path=yaml_path,
            exc=exc, timeout_seconds=timeout_seconds,
        )
        result["client_path"] = str(client_path)
        result["client_uri"] = _repo_relative_path(client_path, root)
        _write_diagnostics(session_dir, result)
        return result

    result = _base_result(sid, session_dir, yaml_path, proc.stdout, proc.stderr, proc.returncode)
    result["client_path"] = str(client_path)
    result["client_uri"] = _repo_relative_path(client_path, root)
    if proc.returncode != 0:
        result["ok"] = False
        result["error"] = "SDK client exited with a non-zero status"
        _write_diagnostics(session_dir, result)
        return result
    if not yaml_path.exists():
        generated = _new_generated_yaml(root, snapshot)
        if generated is not None:
            shutil.copyfile(generated, yaml_path)
            result["generated_yaml_source"] = str(generated)
    if not yaml_path.exists():
        result["ok"] = False
        result["error"] = "SDK client did not generate FrameGraph YAML"
        _write_diagnostics(session_dir, result)
        return result

    rendered = _validate_and_render_yaml(
        yaml_path.read_text(encoding="utf-8"),
        session_id=sid,
        session_dir=session_dir,
        base_dir=root,
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
    raster_png: bool = True,
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


def propose_from_image(
    image_path: str | None = None,
    *,
    image_base64: str | None = None,
    session_id: str | None = None,
    session_root: str | Path | None = None,
    max_pages: int = 3,
    raster_png: bool = True,
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
    return _render_proposal(
        proposal, session_id=session_id, session_root=session_root, max_pages=max_pages, raster_png=raster_png
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
    return _render_proposal(
        proposal, session_id=session_id, session_root=session_root, max_pages=max_pages, raster_png=raster_png
    )


_VISION_GROUP_HINT = (
    "The vision proposal lane needs the optional `vision` dependency group. "
    "Install it with `uv sync --group vision` (or launch the MCP server with "
    "`--group vision`)."
)


def _vision_error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message, "proposal": None, "renders": [], "resources": []}


def _assert_input_path_allowed(path: str) -> None:
    """Confine propose inputs to ``FRAMEGRAPH_MCP_INPUT_ROOTS`` when it is set.

    Unset (the default) preserves the open localhost-dev behavior: any readable
    path is accepted. Setting the env var to a ``os.pathsep``-joined list of roots
    locks the propose tools to those directories so the server cannot be used as a
    confused-deputy file reader in a hardened deployment.
    """
    configured = os.environ.get("FRAMEGRAPH_MCP_INPUT_ROOTS")
    if not configured:
        return
    roots = [Path(entry).expanduser().resolve() for entry in configured.split(os.pathsep) if entry]
    if not roots:
        return
    resolved = Path(path).expanduser().resolve()
    if not any(_is_relative_to(resolved, root) for root in roots):
        raise ValueError("input path is outside the allowed FRAMEGRAPH_MCP_INPUT_ROOTS")


def _render_proposal(
    proposal: Any,
    *,
    session_id: str | None,
    session_root: str | Path | None,
    max_pages: int,
    raster_png: bool,
) -> dict[str, Any]:
    import yaml as _yaml

    yaml_text = _yaml.safe_dump(dict(proposal.document), sort_keys=False, allow_unicode=True)
    result = render_framegraph_yaml(
        yaml_text,
        session_id=session_id,
        session_root=session_root,
        max_pages=max_pages,
        raster_png=raster_png,
    )
    result["proposal"] = _proposal_summary(proposal)
    return result


def _proposal_summary(proposal: Any) -> dict[str, Any]:
    return {
        "object_count": len(proposal.observations),
        "detectors_run": list(proposal.detectors_run),
        "detectors_skipped": [{"name": s.name, "reason": s.reason} for s in proposal.detectors_skipped],
        "observations": [
            {
                "kind": o.kind,
                "bbox": [round(float(v), 2) for v in o.bbox] if o.bbox else None,
                "confidence": o.confidence,
                "detector": o.detector,
            }
            for o in proposal.observations
        ],
    }


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


def list_sessions(*, session_root: str | Path | None = None) -> dict[str, Any]:
    """List per-session scratch directories under the session root with their size."""
    root = _session_root(session_root)
    sessions: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not SESSION_ID_RE.fullmatch(entry.name):
            continue
        files = [path for path in entry.rglob("*") if path.is_file()]
        sessions.append(
            {
                "session_id": entry.name,
                "has_document": (entry / "generated.fg.yaml").exists(),
                "svg_pages": len(list(entry.glob("page-*.svg"))),
                "png_pages": len(list(entry.glob("p*.png"))),
                "bytes": sum(path.stat().st_size for path in files),
                "modified": _iso_from_timestamp(entry.stat().st_mtime),
                "document_uri": f"framegraph://session/{entry.name}/document.yaml",
            }
        )
    return {
        "ok": True,
        "session_root": str(root),
        "session_count": len(sessions),
        "sessions": sessions,
    }


def cleanup_sessions(
    *,
    session_root: str | Path | None = None,
    session_ids: list[str] | None = None,
    older_than_seconds: float | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove session scratch dirs by id or age. No criteria removes nothing (safe by default).

    Exactly one selector applies: ``session_ids`` removes those ids; otherwise
    ``older_than_seconds`` removes sessions whose directory mtime is older than the
    cutoff. ``dry_run`` reports the selection without deleting. The structured log
    lives as a file at the root and is never a deletion target.
    """
    root = _session_root(session_root)
    cutoff = None
    if session_ids is None and older_than_seconds is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - float(older_than_seconds)

    selected: list[Path] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not SESSION_ID_RE.fullmatch(entry.name):
            continue
        if session_ids is not None:
            if entry.name in session_ids:
                selected.append(entry)
        elif cutoff is not None and entry.stat().st_mtime < cutoff:
            selected.append(entry)

    removed: list[str] = []
    for entry in selected:
        target = entry.resolve()
        if not _is_relative_to(target, root):  # defense in depth — never escape the root
            continue
        if not dry_run:
            shutil.rmtree(target, ignore_errors=True)
        removed.append(entry.name)
    return {
        "ok": True,
        "session_root": str(root),
        "dry_run": dry_run,
        "removed_count": len(removed),
        "removed": removed,
    }


def _iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def mcp_content_blocks(result: dict[str, Any]) -> list[dict[str, str]]:
    """Return MCP-style text/image content blocks for a run result.

    Only raster renders (:data:`VIEWABLE_IMAGE_MIME`) become image blocks — SVG is
    not a vision-decodable media type, so it is reported as a resource link in the
    text summary instead of an undecodable image payload.
    """
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
        "render_warning": result.get("render_warning"),
        "error": result.get("error"),
    }
    blocks: list[dict[str, str]] = [
        {"type": "text", "text": json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)}
    ]
    for render in result.get("renders", []):
        path_value = render.get("path")
        mime = render.get("mimeType")
        if not path_value or str(mime) not in VIEWABLE_IMAGE_MIME:
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
            lambda: globals()["list_sdk_clients"](repo_root=repo, edit_roots=edit_roots),
        )

    @server.tool()
    def read_sdk_client(path: str) -> dict[str, Any]:
        """Read an editable Python SDK client file."""
        return _logged_call(
            log_path,
            "read_sdk_client",
            {"path": path},
            lambda: globals()["read_sdk_client"](path, repo_root=repo, edit_roots=edit_roots),
        )

    @server.tool()
    def write_sdk_client(path: str, code: str, create: bool = False) -> dict[str, Any]:
        """Replace or create an editable Python SDK client file."""
        return _logged_call(
            log_path,
            "write_sdk_client",
            {"path": path, "code": code, "create": create},
            lambda: globals()["write_sdk_client"](path, code, create=create, repo_root=repo, edit_roots=edit_roots),
        )

    @server.tool()
    def run_sdk_client(
        path: str,
        session_id: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_pages: int = 3,
        raster_png: bool = True,
        invoke_main: bool = False,
    ):
        """Run an editable Python SDK client, validate its YAML, and return render feedback."""
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
            },
            lambda: globals()["run_sdk_client"](
                path,
                session_id=session_id,
                session_root=root,
                timeout_seconds=timeout_seconds,
                max_pages=max_pages,
                raster_png=raster_png,
                invoke_main=invoke_main,
                repo_root=repo,
                edit_roots=edit_roots,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def run_sdk_code(
        code: str,
        session_id: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_pages: int = 3,
        raster_png: bool = True,
    ):
        """Run Python SDK code, validate its YAML, and return render feedback."""
        result = _logged_call(
            log_path,
            "run_sdk_code",
            {
                "code": code,
                "session_id": session_id,
                "timeout_seconds": timeout_seconds,
                "max_pages": max_pages,
                "raster_png": raster_png,
            },
            lambda: globals()["run_sdk_code"](
                code,
                session_id=session_id,
                session_root=root,
                timeout_seconds=timeout_seconds,
                max_pages=max_pages,
                raster_png=raster_png,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def render_framegraph_yaml(
        yaml_text: str,
        session_id: str | None = None,
        max_pages: int = 3,
        raster_png: bool = True,
    ):
        """Validate and render FrameGraph YAML without executing Python code."""
        result = _logged_call(
            log_path,
            "render_framegraph_yaml",
            {
                "yaml_text": yaml_text,
                "session_id": session_id,
                "max_pages": max_pages,
                "raster_png": raster_png,
            },
            lambda: globals()["render_framegraph_yaml"](
                yaml_text,
                session_id=session_id,
                session_root=root,
                max_pages=max_pages,
                raster_png=raster_png,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def propose_from_image(
        image_path: str | None = None,
        image_base64: str | None = None,
        session_id: str | None = None,
        max_pages: int = 3,
        raster_png: bool = True,
        title: str = "Proposed from image",
        detector_names: list[str] | None = None,
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
                "title": title,
                "detector_names": detector_names,
            },
            lambda: globals()["propose_from_image"](
                image_path,
                image_base64=image_base64,
                session_id=session_id,
                session_root=root,
                max_pages=max_pages,
                raster_png=raster_png,
                title=title,
                detector_names=detector_names,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.tool()
    def propose_from_document(
        path: str,
        page: int = 1,
        dpi: int = 144,
        session_id: str | None = None,
        max_pages: int = 3,
        raster_png: bool = True,
        title: str | None = None,
        detector_names: list[str] | None = None,
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
                "title": title,
                "detector_names": detector_names,
            },
            lambda: globals()["propose_from_document"](
                path,
                page=page,
                dpi=dpi,
                session_id=session_id,
                session_root=root,
                max_pages=max_pages,
                raster_png=raster_png,
                title=title,
                detector_names=detector_names,
            ),
        )
        return _maybe_call_tool_result(result)

    @server.prompt()
    def framegraph_guide() -> str:
        """Guide to what the FrameGraph SDK offers and the server's authoring + proposal tools."""
        return _logged_call(log_path, "prompt.framegraph_guide", {}, lambda: FRAMEGRAPH_GUIDE)

    @server.tool()
    def get_session_resource(uri: str) -> dict[str, str]:
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
            lambda: globals()["list_sessions"](session_root=root),
        )

    @server.tool()
    def cleanup_sessions(
        session_ids: list[str] | None = None,
        older_than_seconds: float | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Remove session scratch dirs by id or age (no selector removes nothing)."""
        return _logged_call(
            log_path,
            "cleanup_sessions",
            {"session_ids": session_ids, "older_than_seconds": older_than_seconds, "dry_run": dry_run},
            lambda: globals()["cleanup_sessions"](
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


def _session_root(session_root: str | Path | None) -> Path:
    root = Path(session_root) if session_root is not None else get_default_session_root()
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _repo_root(repo_root: str | Path | None) -> Path:
    return (Path(repo_root) if repo_root is not None else get_default_repo_root()).expanduser().resolve()


def _structured_log_path(session_root: Path, configured: str | Path | None) -> Path:
    path = configured
    if path is None:
        path = os.environ.get("FRAMEGRAPH_MCP_STRUCT_LOG_PATH")
    if path is None:
        path = session_root / "mcp-structured-log.jsonl"
    resolved = Path(path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _logged_call(log_path: Path, tool: str, instruction: dict[str, Any], call):
    started_at = _utc_now()
    try:
        response = call()
    except Exception as exc:
        _append_structured_log(
            log_path,
            {
                "schema": STRUCTURED_LOG_SCHEMA,
                "timestamp": started_at,
                "tool": tool,
                "instruction": _json_safe(instruction),
                "response": {
                    "ok": False,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                },
            },
        )
        raise
    _append_structured_log(
        log_path,
        {
            "schema": STRUCTURED_LOG_SCHEMA,
            "timestamp": started_at,
            "tool": tool,
            "instruction": _json_safe(instruction),
            "response": _json_safe(response),
        },
    )
    return response


def _append_structured_log(path: Path, event: dict[str, Any]) -> None:
    line = json.dumps(_truncate_log_strings(event), ensure_ascii=False, sort_keys=True) + "\n"
    try:
        if path.exists() and path.stat().st_size + len(line.encode("utf-8")) > STRUCTURED_LOG_MAX_BYTES:
            path.replace(path.with_name(path.name + ".1"))
    except OSError:
        pass
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def _truncate_log_strings(value: Any) -> Any:
    """Clamp oversized strings so one giant payload cannot bloat (or leak) the log."""
    if isinstance(value, dict):
        return {key: _truncate_log_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_truncate_log_strings(item) for item in value]
    if isinstance(value, str) and len(value) > STRUCTURED_LOG_MAX_FIELD_CHARS:
        kept = value[:STRUCTURED_LOG_MAX_FIELD_CHARS]
        return f"{kept}…[truncated {len(value) - STRUCTURED_LOG_MAX_FIELD_CHARS} chars]"
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        json.dumps(value)
    except TypeError:
        return repr(value)
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _reset_session_outputs(session_dir: Path) -> None:
    """Remove a prior run's generated artifacts so a reused ``session_id`` re-renders fresh.

    The code-execution harness only (re)derives the document when ``OUTPUT_YAML_PATH``
    is absent (see :func:`_harness_source`), so a leftover ``generated.fg.yaml`` from an
    earlier run under the same ``session_id`` would be re-rendered in place of the edited
    document. Clearing the per-run outputs (the generated YAML and any page SVG/PNG
    renders) makes each invocation hermetic without forcing callers to rotate the id.
    """
    stale = [
        session_dir / "generated.fg.yaml",
        *session_dir.glob("page-*.svg"),
        *session_dir.glob("p*.png"),
    ]
    for path in stale:
        path.unlink(missing_ok=True)


def _subprocess_env(repo_root: Path) -> dict[str, str]:
    pythonpath_entries = [str(repo_root)]
    package_root = get_default_repo_root()
    if package_root != repo_root:
        pythonpath_entries.append(str(package_root))
    pythonpath = os.pathsep.join(pythonpath_entries)
    if os.environ.get("PYTHONPATH"):
        pythonpath = pythonpath + os.pathsep + os.environ["PYTHONPATH"]
    env = os.environ.copy()
    if not _truthy_env("FRAMEGRAPH_MCP_KEEP_ENV"):
        # The harness executes untrusted SDK code; strip likely-secret vars so a
        # generated client cannot exfiltrate credentials inherited from the server.
        for name in [key for key in env if SECRET_ENV_RE.search(key)]:
            del env[name]
    env["PYTHONPATH"] = pythonpath
    return env


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _harness_source(script_path: Path, yaml_path: Path, session_dir: Path, *, invoke_main: bool = True) -> str:
    module_name = "__main__" if invoke_main else "__framegraph_mcp_client__"
    return f"""\
from pathlib import Path

from framegraph.sdk.io import serialize

SESSION_DIR = {str(session_dir)!r}
OUTPUT_YAML_PATH = {str(yaml_path)!r}
BUILD_FUNCTION_NAMES = {BUILD_FUNCTION_NAMES!r}
namespace = {{
    "__file__": {str(script_path)!r},
    "__name__": {module_name!r},
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
    if candidate is None:
        for name in BUILD_FUNCTION_NAMES:
            value = namespace.get(name)
            if callable(value):
                candidate = value()
                break
    if candidate is not None and hasattr(candidate, "build"):
        candidate = candidate.build()
    if candidate is None:
        raise SystemExit("no FrameGraph document found; write OUTPUT_YAML_PATH, set doc/document/builder, or expose build()")
    out.write_text(serialize(candidate, format="yaml"), encoding="utf-8")
"""


def _client_roots(repo_root: Path, edit_roots: str | list[str] | tuple[str, ...] | None) -> list[Path]:
    configured = edit_roots
    if configured is None:
        configured = os.environ.get("FRAMEGRAPH_MCP_EDIT_ROOTS")
    if configured is None:
        entries: list[str] = list(DEFAULT_CLIENT_ROOTS)
    elif isinstance(configured, str):
        entries = [entry for entry in configured.split(os.pathsep) if entry]
    else:
        entries = list(configured)

    roots: list[Path] = []
    for entry in entries:
        candidate = Path(entry).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve()
            if not _is_relative_to(resolved, repo_root):
                as_repo_relative = (repo_root / str(entry).lstrip("/")).resolve()
                resolved = as_repo_relative
        else:
            resolved = (repo_root / candidate).resolve()
        if not _is_relative_to(resolved, repo_root):
            raise ValueError("editable SDK client roots must stay inside the repository")
        roots.append(resolved)
    if not roots:
        raise ValueError("at least one editable SDK client root is required")
    return roots


def _resolve_client_path(
    path: str,
    *,
    repo_root: Path,
    edit_roots: str | list[str] | tuple[str, ...] | None,
    must_exist: bool,
) -> Path:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path must be a non-empty string")
    raw = Path(path).expanduser()
    if raw.is_absolute():
        resolved = raw.resolve()
        if not _is_relative_to(resolved, repo_root):
            resolved = (repo_root / str(path).lstrip("/")).resolve()
    else:
        resolved = (repo_root / raw).resolve()
    if resolved.suffix != ".py":
        raise ValueError("SDK client path must be a Python .py file")
    allowed_roots = _client_roots(repo_root, edit_roots)
    if not any(_is_relative_to(resolved, root) for root in allowed_roots):
        raise ValueError("SDK client path must stay under the allowed SDK client roots")
    if must_exist and not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    return resolved


def _repo_relative_path(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root).as_posix()


def _framegraph_yaml_snapshot(repo_root: Path) -> dict[Path, str]:
    """Content-hash snapshot of candidate fixtures before a client run.

    Hashes (not mtimes) so the post-run diff only fires on *content* change — a
    fixture merely ``touch``-ed by an unrelated process is no longer mistaken for
    this client's output, which the mtime heuristic could do.
    """
    return {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in _framegraph_yaml_candidates(repo_root)
        if path.is_file()
    }


def _new_generated_yaml(repo_root: Path, before: dict[Path, str]) -> Path | None:
    changed: list[Path] = []
    for path in _framegraph_yaml_candidates(repo_root):
        if not path.is_file():
            continue
        previous = before.get(path)
        current = hashlib.sha256(path.read_bytes()).hexdigest()
        if previous is None or current != previous:
            changed.append(path)
    if not changed:
        return None
    # Tie-break by mtime when several fixtures changed in the same run.
    return max(changed, key=lambda candidate: candidate.stat().st_mtime_ns)


def _framegraph_yaml_candidates(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for root in (repo_root / "examples", repo_root / "fixtures"):
        if not root.exists():
            continue
        for pattern in FRAMEGRAPH_YAML_PATTERNS:
            candidates.extend(root.rglob(pattern))
    return candidates


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


def _decode_stream(value: Any) -> str:
    """Coerce a captured subprocess stream (``str``, ``bytes``, or ``None``) to text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def _subprocess_timeout_result(
    label: str,
    *,
    session_id: str,
    session_dir: Path,
    yaml_path: Path,
    exc: subprocess.TimeoutExpired,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Structured ``ok:false`` result for a build subprocess that overran its budget.

    Mirrors the render-timeout contract (a structured payload, never a raised
    traceback): it surfaces whatever stdout/stderr was captured before the kill plus
    an actionable hint to raise ``timeout_seconds``. ``returncode`` is ``-1`` (the
    process was terminated, not exited).
    """
    budget = max(1, int(timeout_seconds))
    result = _base_result(
        session_id,
        session_dir,
        yaml_path,
        _decode_stream(exc.stdout),
        _decode_stream(exc.stderr),
        -1,
    )
    result["ok"] = False
    result["timed_out"] = True
    result["error"] = (
        f"{label} exceeded the {budget}s execution budget; raise timeout_seconds "
        "or simplify the document."
    )
    return result


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
    render_warning: str | None = None
    if report.ok:
        try:
            svgs = _render_page_svgs_bounded(document, base_dir)
        except RenderTimeoutError as exc:
            return _render_failure(session_id, report, str(exc), warning=str(exc))
        except Exception as exc:  # noqa: BLE001 — render is third-party-ish; surface it structured
            return _render_failure(session_id, report, f"FrameGraph render failed: {exc}")

        for index, svg in enumerate(svgs[_page_slice(max_pages, len(svgs))], 1):
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
            pngs, render_warning = _try_rasterize_pngs(
                [Path(item["path"]) for item in renders], session_dir, session_id
            )
            renders.extend(pngs)

    result = {
        "ok": report.ok and bool(renders),
        "validation": _validation_payload(report),
        "renders": renders,
        "resources": _resource_links(session_id, renders=renders),
    }
    if render_warning:
        result["render_warning"] = render_warning
    return result


def _render_failure(
    session_id: str, report: ValidationReport, error: str, *, warning: str | None = None
) -> dict[str, Any]:
    """Structured result for a render that crashed or timed out (validation passed)."""
    result: dict[str, Any] = {
        "ok": False,
        "error": error,
        "validation": _validation_payload(report),
        "renders": [],
        "resources": _resource_links(session_id, renders=[]),
    }
    if warning:
        result["render_warning"] = warning
    return result


def _render_page_svgs_bounded(document: Any, base_dir: Path) -> list[str]:
    """Render page SVGs under :data:`DEFAULT_RENDER_TIMEOUT_SECONDS` (env-overridable).

    Runs the pure-Python renderer in a daemon thread and joins with a timeout so a
    pathological document bounds the *response* latency. The work itself is not
    force-killed (Python cannot interrupt CPU-bound bytecode); a timed-out render
    keeps running detached until it completes, then is discarded.
    """
    timeout = _render_timeout()
    box: dict[str, Any] = {}

    def _target() -> None:
        try:
            box["value"] = render_page_svgs(document, base_dir=str(base_dir))
        except BaseException as exc:  # noqa: BLE001 — re-raised on the calling thread
            box["error"] = exc

    worker = threading.Thread(target=_target, name="framegraph-render", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise RenderTimeoutError(
            f"FrameGraph render exceeded {timeout:g}s (FRAMEGRAPH_MCP_RENDER_TIMEOUT)"
        )
    if "error" in box:
        raise box["error"]
    return box.get("value", [])


def _render_timeout() -> float:
    raw = os.environ.get("FRAMEGRAPH_MCP_RENDER_TIMEOUT")
    if raw:
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return float(DEFAULT_RENDER_TIMEOUT_SECONDS)


def _page_slice(max_pages: int, total: int) -> slice:
    """Page window for the render. ``max_pages <= 0`` means "all pages" (documented)."""
    limit = int(max_pages)
    if limit <= 0:
        return slice(None)
    return slice(0, limit)


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


def _try_rasterize_pngs(
    svg_paths: list[Path], session_dir: Path, session_id: str
) -> tuple[list[dict[str, Any]], str | None]:
    """Rasterize page SVGs to PNG. Returns ``(renders, warning)``.

    A non-``None`` warning means no viewable raster was produced — the model gets
    only SVG/diagnostics text — so the warning names the missing backend instead of
    failing silently.
    """
    try:
        from framegraph.rendering.infrastructure.browser import (
            BrowserRendererUnavailable,
            rasterize_svgs,
        )
    except ImportError as exc:
        return [], f"PNG rasterization unavailable: {exc}"

    svgs = [path.read_text(encoding="utf-8") for path in svg_paths]
    try:
        pngs = rasterize_svgs(svgs, session_dir, base_dir=str(session_dir))
    except BrowserRendererUnavailable as exc:
        return [], (
            f"PNG rasterization unavailable: {exc} The model cannot see SVG, so this "
            "render was not visually verified — install the `browser` group and run "
            "`uv run playwright install chromium`."
        )
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
    return renders, None


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
