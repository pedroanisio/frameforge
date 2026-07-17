#!/usr/bin/env python3
"""Regression: importing the schema generator must not shadow the package.

docs/schema/build_schema.py historically put ``docs/models`` at ``sys.path[0]``
and ran ``import frameforge`` — registering the MODEL FILE as the ``frameforge``
package in ``sys.modules`` for the rest of the process. Everything importing the
real package afterwards (the MCP server, the SDK, the root conftest fixture
test) then received a module without ``__path__``, producing order-dependent
test failures (the deterministic repro was ``pytest test_capability_manifest.py
test_doc_tooling.py`` → 6 failures). The canonical import for the model source
is package-qualified ``models.frameforge`` (what the root conftest uses); this
gate pins that the generator no longer hijacks the package name.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_PROBE = """
import sys
sys.path[:0] = [{root!r}, {src!r}, {docs!r}, {schema!r}]
import build_schema                      # the generator under test
shadow = sys.modules.get("frameforge")
assert shadow is None or hasattr(shadow, "__path__"), (
    "build_schema import left a shadowed sys.modules['frameforge']: %r" % shadow)
import frameforge
assert hasattr(frameforge, "__path__"), "the real package must still resolve"
assert build_schema.fg.__name__ == "models.frameforge", (
    "the generator must use the canonical package-qualified model import, got %r"
    % build_schema.fg.__name__)
print("OK")
"""


def test_build_schema_import_leaves_no_package_shadow():
    code = _PROBE.format(
        root=ROOT,
        src=os.path.join(ROOT, "src"),
        docs=os.path.join(ROOT, "docs"),
        schema=os.path.join(ROOT, "docs", "schema"),
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT
    )
    assert proc.returncode == 0 and "OK" in proc.stdout, (
        f"shadow regression: stdout={proc.stdout!r} stderr={proc.stderr[-800:]!r}"
    )


_TOOLING_PROBE = """
import sys, importlib
sys.path[:0] = [{root!r}, {src!r}, {docs!r}, {tooling!r}]
mod = importlib.import_module({name!r})
shadow = sys.modules.get("frameforge")
assert shadow is None or hasattr(shadow, "__path__"), (
    "importing %s left a shadowed sys.modules['frameforge']: %r" % ({name!r}, shadow))
import frameforge
assert hasattr(frameforge, "__path__")
print("OK")
"""

_SHADOW_PRONE_SCRIPTS = [
    "validate", "codemod", "check_spec_sync", "check_grammar_sync", "gen_docs",
]


def _probe_script(name: str) -> None:
    code = _TOOLING_PROBE.format(
        root=ROOT, src=os.path.join(ROOT, "src"), docs=os.path.join(ROOT, "docs"),
        tooling=os.path.join(ROOT, "tooling"), name=name,
    )
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0 and "OK" in proc.stdout, (
        f"{name}: shadow or import failure — stdout={proc.stdout!r} "
        f"stderr={proc.stderr[-600:]!r}"
    )


def test_no_tooling_script_shadows_the_package():
    """Every in-process-importable tooling script must leave the package name
    alone (the endemic `sys.path.insert(docs/models); import frameforge` pattern
    is the mine — each script that carried it poisons all later imports)."""
    for name in _SHADOW_PRONE_SCRIPTS:
        _probe_script(name)


def test_schema_still_builds_after_the_import_change():
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "docs", "schema", "build_schema.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert proc.returncode == 0, f"build_schema --check broke: {proc.stderr[-800:]}"
