#!/usr/bin/env python3
"""Every `FRAMEFORGE_*` env var the code reads is documented — and only those.

Drift-risk-map MODERATE #8: ~22 env knobs are consumed under src/ but the
`mcp/README.md` configuration table named 11, and the `EDIT_ROOTS` row stated
a wrong default (`examples` vs the real `static/examples`). A new deployment
silently takes defaults for knobs the operator cannot discover. Pinned here:

  * consumed ⊆ documented (a new knob cannot ship undocumented);
  * documented ⊆ consumed (the table cannot advertise ghost knobs);
  * the `EDIT_ROOTS` row states the real default.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

README = os.path.join(ROOT, "src", "frameforge", "mcp", "README.md")

# an env READ (or write) — not a Python constant named FRAMEFORGE_*
_READ = re.compile(
    r"(?:environ\.get\(|getenv\(|environ\[|_positive_env\(|_truthy_env\()"
    r"\s*[\"'](FRAMEFORGE_[A-Z_]+)")


def _consumed():
    out = set()
    for base, _dirs, files in os.walk(os.path.join(ROOT, "src")):
        for fn in files:
            if fn.endswith(".py"):
                with open(os.path.join(base, fn), encoding="utf-8") as fh:
                    out |= set(_READ.findall(fh.read()))
    # container-only knobs are consumed by the docker entry scripts (shell
    # ${FRAMEFORGE_X:-...} expansions), not by the Python package — count them
    # so the table may cross-reference them without becoming a ghost row.
    docker_dir = os.path.join(ROOT, "docker")
    if os.path.isdir(docker_dir):
        for fn in os.listdir(docker_dir):
            if fn.endswith(".sh"):
                with open(os.path.join(docker_dir, fn), encoding="utf-8") as fh:
                    out |= set(re.findall(r"\$\{(FRAMEFORGE_[A-Z_]+)", fh.read()))
    return out


def _documented():
    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"## Configuration \(environment variables\).*?(?=\n## )", text, re.S)
    assert m, "mcp/README.md configuration section moved — update this test"
    return set(re.findall(r"FRAMEFORGE_[A-Z_]+", m.group(0))), m.group(0)


def test_census_is_not_empty():
    assert len(_consumed()) >= 15, "env census regex matched almost nothing — patterns changed?"


def test_every_consumed_env_var_is_documented():
    documented, _ = _documented()
    missing = _consumed() - documented
    assert not missing, (
        f"env var(s) {sorted(missing)} are read under src/ but absent from the "
        "mcp/README.md configuration table — document them (one row each)")


def test_every_documented_env_var_is_consumed():
    documented, _ = _documented()
    ghosts = documented - _consumed()
    assert not ghosts, (
        f"mcp/README.md documents env var(s) {sorted(ghosts)} that nothing "
        "under src/ reads — stale rows")


def test_edit_roots_row_states_the_real_default():
    from frameforge.mcp.config import DEFAULT_CLIENT_ROOTS
    _, section = _documented()
    row = next((ln for ln in section.splitlines()
                if "FRAMEFORGE_MCP_EDIT_ROOTS" in ln), "")
    assert row, "EDIT_ROOTS row missing from the table"
    for root in DEFAULT_CLIENT_ROOTS:
        assert root in row, (
            f"EDIT_ROOTS row does not state the real default {root!r} "
            f"(config.DEFAULT_CLIENT_ROOTS) — row: {row.strip()}")


def test_stated_numeric_defaults_equal_the_code_defaults():
    """The documented default for every numeric knob is the CODE's default —
    change a constant without updating its row and this fails. Sourced from
    the config constants, never restated here."""
    from frameforge.mcp import config as cfg

    expected = {
        "FRAMEFORGE_MCP_RENDER_TIMEOUT": cfg.DEFAULT_RENDER_TIMEOUT_SECONDS,
        "FRAMEFORGE_MCP_RENDER_MAX_PAGES": cfg.DEFAULT_RENDER_MAX_PAGES_HARD,
        "FRAMEFORGE_MCP_RENDER_MAX_OBJECTS": cfg.DEFAULT_RENDER_MAX_OBJECTS,
        "FRAMEFORGE_MCP_RASTER_MAX_PAGES": cfg.DEFAULT_RASTER_MAX_PAGES,
        "FRAMEFORGE_MCP_RASTER_TIMEOUT": cfg.DEFAULT_RASTER_TIMEOUT_SECONDS,
        "FRAMEFORGE_MCP_MAX_INLINE_IMAGES": cfg.DEFAULT_MAX_INLINE_IMAGES,
        "FRAMEFORGE_MCP_MAX_RESULT_CHARS": cfg.DEFAULT_MAX_RESULT_CHARS,
        "FRAMEFORGE_MCP_MAX_TEXT_CHARS": cfg.DEFAULT_MAX_TEXT_CHARS,
        "FRAMEFORGE_MCP_MIN_CLEANUP_AGE": cfg.DEFAULT_MIN_CLEANUP_AGE_SECONDS,
    }
    _, section = _documented()
    rows = {ln.split("`")[1]: ln for ln in section.splitlines()
            if ln.startswith("| `FRAMEFORGE_")}
    wrong = []
    for var, default in expected.items():
        row = rows.get(var, "")
        if not row:
            wrong.append(f"{var}: no table row")
            continue
        # numbers may be typeset with separators — normalize before comparing
        normalized = row.replace(",", "").replace("_", "")
        if f"default: {default}" not in normalized:
            wrong.append(f"{var}: row does not state 'default: {default}' "
                         f"(code default) — row: {row.strip()}")
    assert not wrong, "stated defaults drifted from code defaults:\n  " + "\n  ".join(wrong)
