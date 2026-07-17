"""Drift guards for hand-maintained doc surfaces with no generator.

Closes the gap list from the 2026-07-17 redaction-reconciliation pass: three
couplings that had rotted silently because nothing mechanical compared the
hand-written side to its source of truth.

  1. docs/index.md "minimal document" example ``version:`` ⇄ ``HEAD_VERSION``
     (the literal sat at 2.2.0 through three releases — it validates at any
     version, so test_doc_examples.py alone cannot catch staleness).
  2. AGENTS.md make-target table ⇄ the Makefile ``check`` prerequisites
     (the table lagged the gate list twice, most recently when ``public-check``
     landed mid-session).
  3. docs/BRAND.md §4 palette ⇄ the logo generator's colour constants
     (matching today by discipline only).

Each guard is a pure detector asserted twice: against the live tree (sync
proof) and against synthetic drifted input (proof the detector fires — the
red path of the TDD loop, kept as a permanent self-test).
"""

import os
import re
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import frameforge.model as fg  # noqa: E402


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
# Detectors (pure functions over file text — unit-testable with drifted input)


def index_example_version(index_md: str) -> str:
    """Extract ``version:`` from the first fenced yaml block in docs/index.md."""
    m = re.search(r"```yaml\n(.*?)```", index_md, re.S)
    assert m, "docs/index.md no longer contains a fenced yaml example"
    doc = yaml.safe_load(m.group(1))
    assert isinstance(doc, dict) and "version" in doc, (
        "the fenced yaml example lost its version: field"
    )
    return str(doc["version"])


def makefile_check_prereqs(makefile: str) -> list[str]:
    """The prerequisite target names of the ``check:`` rule."""
    m = re.search(r"^check:([^\n#]*)", makefile, re.M)
    assert m, "Makefile lost its check: rule"
    return m.group(1).split()


def undocumented_gates(agents_md: str, prereqs: list[str]) -> list[str]:
    """check-gate names that AGENTS.md never mentions as a `target` token."""
    return [p for p in prereqs if f"`{p}`" not in agents_md]


def brand_palette(brand_md: str) -> dict:
    """token -> hex from the §4 palette table rows (| `token` | `#hex` | ...)."""
    rows = re.findall(r"^\| `([a-z-]+)` \| `(#[0-9A-Fa-f]{6})` \|", brand_md, re.M)
    return {token: hexval.upper() for token, hexval in rows}


def generator_colors(logo_py: str) -> dict:
    """CONSTANT -> hex from the logo generator's module-level colour literals."""
    pairs = re.findall(r'^([A-Z_]+) *= *"(#[0-9A-Fa-f]{6})"', logo_py, re.M)
    return {name: hexval.upper() for name, hexval in pairs}


# The five brand tokens the generator also defines. gate-green / drift-red /
# grid / mute are BRAND-only (no generator constant) — nothing to couple.
BRAND_TO_GENERATOR = {
    "ink": "INK",
    "paper": "PAPER",
    "canvas": "CANVAS",
    "frame-blue": "FRAME",
    "graph-cyan": "GRAPH",
}


# --------------------------------------------------------------------------- #
# Live-tree guards (the gates)


def test_index_example_version_is_head():
    assert index_example_version(_read("docs/index.md")) == fg.HEAD_VERSION, (
        "docs/index.md's minimal-document example pins a stale version: "
        "update the literal to HEAD_VERSION (RELEASE.md §7 grep-sweep)"
    )


def test_agents_documents_every_check_gate():
    prereqs = makefile_check_prereqs(_read("Makefile"))
    missing = undocumented_gates(_read("AGENTS.md"), prereqs)
    assert not missing, (
        f"make check gained gate(s) AGENTS.md does not document: {missing} — "
        "add a make-targets table row"
    )


def test_check_prereqs_are_real_targets():
    makefile = _read("Makefile")
    ghosts = [
        p
        for p in makefile_check_prereqs(makefile)
        if not re.search(rf"^{re.escape(p)}:", makefile, re.M)
    ]
    assert not ghosts, f"check: names prerequisite(s) with no rule: {ghosts}"


def test_brand_palette_matches_logo_generator():
    palette = brand_palette(_read("docs/BRAND.md"))
    colors = generator_colors(_read("static/examples/frameforge_logo.py"))
    drifted = {
        token: (palette.get(token), colors.get(const))
        for token, const in BRAND_TO_GENERATOR.items()
        if palette.get(token) != colors.get(const)
    }
    assert not drifted, (
        f"BRAND.md §4 palette and frameforge_logo.py disagree: {drifted} — "
        "the generator is the source of truth for the five shared tokens"
    )


# --------------------------------------------------------------------------- #
# Red-path self-tests: prove each detector fires on drifted input


DRIFTED_INDEX = '```yaml\ndsl: FrameForge\nversion: "2.2.0"\npages: []\n```\n'


def test_detector_flags_stale_index_version():
    assert index_example_version(DRIFTED_INDEX) != fg.HEAD_VERSION


def test_detector_flags_undocumented_gate():
    agents_without_public_check = "| `check` | ... |\n| `test` | ... |\n"
    missing = undocumented_gates(
        agents_without_public_check, ["check", "test", "public-check"]
    )
    assert missing == ["public-check"]


def test_detector_flags_palette_drift():
    drifted_brand = "| `ink` | `#000000` | wrong on purpose |\n"
    live_generator = _read("static/examples/frameforge_logo.py")
    palette = brand_palette(drifted_brand)
    colors = generator_colors(live_generator)
    assert palette["ink"] != colors["INK"]


def test_detectors_reject_structural_loss():
    with pytest.raises(AssertionError):
        index_example_version("no yaml fence here")
    with pytest.raises(AssertionError):
        makefile_check_prereqs("no check rule here")


if __name__ == "__main__":  # standalone runner, mirroring test_head.py
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    raise SystemExit(1 if failures else 0)
