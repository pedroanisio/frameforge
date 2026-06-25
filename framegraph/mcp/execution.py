"""The sandboxed subprocess that executes untrusted SDK code.

Secret-bearing env vars are stripped, a wall-clock timeout bounds the run, and an
overrun is reported as a structured ok:false result, never a raised traceback.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from framegraph.mcp.config import BUILD_FUNCTION_NAMES, SECRET_ENV_RE, _truthy_env
from framegraph.mcp.paths import get_default_repo_root
from framegraph.mcp.results import _base_result


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
