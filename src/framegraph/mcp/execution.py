"""The sandboxed subprocess that executes untrusted SDK code.

Secret-bearing env vars are stripped, a wall-clock timeout bounds the run, and an
overrun is reported as a structured ok:false result, never a raised traceback.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from framegraph.mcp.config import BUILD_FUNCTION_NAMES, SECRET_ENV_RE, _truthy_env
from framegraph.mcp.paths import get_default_repo_root
from framegraph.mcp.results import _base_result

# Sidecar the harness writes when the built document fails schema validation, so
# the parent process can lower the Pydantic errors into structured issues instead
# of leaving them as an opaque traceback in stderr.
BUILD_ERROR_FILE = "build_error.json"


def _pythonpath_roots(root: Path) -> list[str]:
    """Import roots under ``root`` (src layout): the root itself, plus ``src/``
    (the ``framegraph`` package) and ``docs/`` (the ``models`` namespace)."""
    entries = [str(root)]
    for sub in ("src", "docs"):
        candidate = root / sub
        if candidate.is_dir():
            entries.append(str(candidate))
    return entries


def _subprocess_env(repo_root: Path) -> dict[str, str]:
    pythonpath_entries = _pythonpath_roots(repo_root)
    package_root = get_default_repo_root()
    if package_root != repo_root:
        pythonpath_entries += [
            entry for entry in _pythonpath_roots(package_root)
            if entry not in pythonpath_entries
        ]
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


def _harness_source(script_path: Path, yaml_path: Path, session_dir: Path, *, invoke_main: bool = True) -> str:
    module_name = "__main__" if invoke_main else "__framegraph_mcp_client__"
    return f"""\
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from framegraph.sdk.io import serialize

SESSION_DIR = {str(session_dir)!r}
OUTPUT_YAML_PATH = {str(yaml_path)!r}
BUILD_ERROR_PATH = str(Path(SESSION_DIR) / {BUILD_ERROR_FILE!r})
BUILD_FUNCTION_NAMES = {BUILD_FUNCTION_NAMES!r}


def _pointer(loc):
    if not loc:
        return ""
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in loc)


def _emit_validation_error(exc):
    issues = [
        {{
            "rule_id": "structure",
            "severity": "error",
            "path": _pointer(err.get("loc", ())),
            "message": str(err.get("msg", "")),
        }}
        for err in exc.errors()
    ]
    Path(BUILD_ERROR_PATH).write_text(
        json.dumps({{"error": "document failed schema validation", "issues": issues}}),
        encoding="utf-8",
    )
    print("FrameGraph document failed schema validation: "
          + str(len(issues)) + " issue(s)", file=sys.stderr)
    raise SystemExit(1)


namespace = {{
    "__file__": {str(script_path)!r},
    "__name__": {module_name!r},
    "SESSION_DIR": SESSION_DIR,
    "OUTPUT_YAML_PATH": OUTPUT_YAML_PATH,
}}
source = Path({str(script_path)!r}).read_text(encoding="utf-8")
try:
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
except ValidationError as exc:
    _emit_validation_error(exc)
"""


def _read_build_error(session_dir: Path) -> dict[str, Any] | None:
    """Return the structured build-error sidecar a failed harness run wrote, if any."""
    path = Path(session_dir) / BUILD_ERROR_FILE
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _apply_build_error(result: dict[str, Any], session_dir: Path) -> None:
    """Enrich a non-zero result with structured validation issues from the sidecar.

    Turns an opaque "exited with a non-zero status" into the same
    ``validation.issues`` shape the YAML path produces, when the failure was a
    document schema-validation error.
    """
    data = _read_build_error(session_dir)
    if not data:
        return
    issues = data.get("issues") or []
    result["validation"] = {"ok": False, "issues": issues}
    if data.get("error"):
        result["error"] = data["error"]


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
