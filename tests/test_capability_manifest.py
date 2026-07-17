"""Drift gates for the generated capability + documentation surfaces.

Three committed artifacts are generated from the live tree and must not
hand-drift (same contract as ``build_schema.py --check`` / ``gen_status.py``):

- ``docs/capability-manifest.json`` — the machine-readable core-vs-SDK-vs-MCP
  status tracking ADR-0002 mandates, built purely by introspection
  (``tooling/gen_capability_manifest.py``: model unions, SDK exports/builders,
  MCP tool registry, renderer entry points, validator codes).
- ``docs/error-codes.md`` — must document every validator finding code in
  ``tooling/validate.py`` and every SDK ``rule_id`` in
  ``frameforge/sdk/validate.py`` (codes are extracted from the sources, so a
  new code cannot land undocumented).
- ``docs/examples.md`` — must list exactly the tracked ``examples/*.py``
  scripts (``tooling/gen_examples_index.py``).

This file deliberately carries no ``sys.path`` bootstrap: the root
``conftest.py`` provides it (repo root + ``tooling/`` + ``schema/``).
"""
from __future__ import annotations

import json
import os
import subprocess

import gen_capability_manifest as M
import gen_examples_index as X

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


# --------------------------------------------------------------------------- #
#  Capability manifest                                                        #
# --------------------------------------------------------------------------- #
def test_committed_manifest_matches_fresh_build():
    path = os.path.join(ROOT, "docs", "capability-manifest.json")
    assert os.path.exists(path), (
        "docs/capability-manifest.json is missing — run `make manifest` and commit it"
    )
    with open(path, encoding="utf-8") as fh:
        committed = fh.read()
    assert committed == M.render(), (
        "docs/capability-manifest.json is stale — run `make manifest` and commit the result"
    )


def test_manifest_capabilities_carry_tri_state_status():
    manifest = json.loads(M.render())
    caps = manifest["capabilities"]
    assert caps, "manifest has no capabilities"
    for cap in caps:
        assert set(cap) >= {"name", "kind", "core", "sdk", "mcp"}, cap
        for layer in ("core", "sdk", "mcp"):
            assert isinstance(cap[layer], bool), cap
    kinds = {cap["kind"] for cap in caps}
    assert {"object_type", "flow_type", "inline_kind", "canvas_preset",
            "sdk_export", "mcp_tool"} <= kinds


def test_manifest_model_section_is_introspected_not_hardcoded():
    manifest = json.loads(M.render())
    model = manifest["model"]
    # Anchors that exist in the live model unions; enumerations must carry them.
    assert "rect" in model["object_types"]
    assert "group" in model["object_types"]
    assert "toc" in model["flow_types"]
    assert "footnote" in model["inline_kinds"]
    assert "A4" in model["canvas_presets"]
    assert model["style_property_count"] > 50
    assert manifest["version"], "manifest must carry HEAD_VERSION"


def test_manifest_mcp_tools_come_from_the_live_registry():
    tools = M.mcp_tool_names()
    # Anchors: the author->render lane and the measurement layer must be present.
    assert "run_sdk_code" in tools
    assert "measure_image" in tools
    assert "vectorize_image" in tools
    manifest = json.loads(M.render())
    assert manifest["mcp"]["tools"] == sorted(tools)


def test_manifest_sdk_exports_match_the_package_all():
    manifest = json.loads(M.render())
    assert "DocumentBuilder" in manifest["sdk"]["public_exports"]
    assert manifest["sdk"]["public_exports"] == sorted(M.sdk_public_exports())


# --------------------------------------------------------------------------- #
#  Error-code reference                                                       #
# --------------------------------------------------------------------------- #
def _error_codes_doc() -> str:
    path = os.path.join(ROOT, "docs", "error-codes.md")
    assert os.path.exists(path), "docs/error-codes.md is missing"
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def test_error_codes_doc_covers_every_tooling_validator_code():
    codes = M.tooling_finding_codes()
    assert "stroke-single-form" in codes, "extractor lost a known validator code"
    doc = _error_codes_doc()
    missing = sorted(c for c in codes if f"`{c}`" not in doc)
    assert not missing, (
        f"docs/error-codes.md does not document validator code(s): {missing}"
    )


def test_error_codes_doc_covers_every_sdk_rule_id():
    rule_ids = M.sdk_rule_ids()
    assert "reference-cycle" in rule_ids, "extractor lost a known SDK rule_id"
    doc = _error_codes_doc()
    missing = sorted(r for r in rule_ids if f"`{r}`" not in doc)
    assert not missing, (
        f"docs/error-codes.md does not document SDK rule_id(s): {missing}"
    )


def test_manifest_validator_section_uses_the_same_extraction():
    manifest = json.loads(M.render())
    assert manifest["validator"]["tooling_codes"] == sorted(M.tooling_finding_codes())
    assert manifest["validator"]["sdk_rule_ids"] == sorted(M.sdk_rule_ids())


# --------------------------------------------------------------------------- #
#  Examples index                                                             #
# --------------------------------------------------------------------------- #
def _tracked_examples() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files", "static/examples/*.py"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    return {os.path.basename(p) for p in out.split() if p}


def test_examples_index_lists_exactly_the_tracked_examples():
    path = os.path.join(ROOT, "docs", "examples.md")
    assert os.path.exists(path), (
        "docs/examples.md is missing — run `make examples-index` and commit it"
    )
    with open(path, encoding="utf-8") as fh:
        listed = X.listed_files(fh.read())
    tracked = _tracked_examples()
    assert listed == tracked, (
        "docs/examples.md is out of sync with tracked examples/*.py — run "
        f"`make examples-index` (missing: {sorted(tracked - listed)}; "
        f"orphaned: {sorted(listed - tracked)})"
    )


# --------------------------------------------------------------------------- #
#  conftest contract                                                          #
# --------------------------------------------------------------------------- #
def test_root_conftest_provides_package_and_models_fixture(models_fg):
    import frameforge as pkg

    assert hasattr(pkg, "__path__"), "`import frameforge` must resolve the package"
    assert isinstance(models_fg.HEAD_VERSION, str)
    assert hasattr(models_fg, "Document")
