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
