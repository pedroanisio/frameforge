#!/usr/bin/env python3
"""
test_docs_in_sync.py — P1 documentation drift gate.

Extends the repo's "generated + checked, never hand-drift" guarantee (which
build_schema.py --check already gives for the schema) to the prose. It asserts
that hand-written facts in README.md / CHANGELOG.md match what the tooling
actually produces — the exact class of rot we found: "72 $defs" when there were
77, "12/12 green" when 13 tests pass, and a Layout map pointing at a since-deleted
file.

Checks:
  * README's "<n> $defs" == the generated schema's $defs count
  * every "<a>/<b> green" claim (README + CHANGELOG) == the real test count
  * pyproject [project].version == models HEAD_VERSION, and the schema title
    carries that version
  * every concrete repo path named in the README "## Layout" map exists

Runs under pytest (`uv run pytest`) or standalone (`uv run python tests/test_docs_in_sync.py`).
"""
import os
import re
import subprocess
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 has no stdlib tomllib
    import tomli as tomllib  # type: ignore[no-redefine]

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(ROOT, "docs", "models"), os.path.join(ROOT, "docs", "schema")]
shadow = sys.modules.get("framegraph")
if shadow is not None and hasattr(shadow, "__path__"):
    del sys.modules["framegraph"]

import framegraph as fg  # noqa: E402
import build_schema as B  # noqa: E402

README = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
CHANGELOG = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
CLAUDE = open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8").read()
FIXTURE_STATUS = open(os.path.join(ROOT, "docs", "FIXTURE-STATUS.md"), encoding="utf-8").read()
DOCS_GITIGNORE = open(os.path.join(ROOT, "docs", ".gitignore"), encoding="utf-8").read()
MKDOCS = open(os.path.join(ROOT, "mkdocs.yml"), encoding="utf-8").read()
GEN_DOCS = open(os.path.join(ROOT, "tooling", "gen_docs.py"), encoding="utf-8").read()
ARCHITECTURE = open(os.path.join(ROOT, "docs", "architecture.md"), encoding="utf-8").read()
ROADMAP = open(os.path.join(ROOT, "docs", "roadmap.md"), encoding="utf-8").read()

_SKIP_DIRS = {".git", ".venv", "node_modules", "out", "__pycache__", ".pytest_cache", ".ruff_cache"}
_TRANSIENT_GENERATED_DOCS = {
    "docs/reference.md",
    "docs/grammar.md",
    "docs/spec.md",
    "docs/fixtures.md",
    "docs/changelog.md",
}
_TRACKED_GENERATED_DOCS = {
    "docs/sdk.md",
    "docs/sdk-api.md",
}


def _test_count():
    src = open(os.path.join(ROOT, "tests", "test_head.py"), encoding="utf-8").read()
    return len(re.findall(r"\ndef (test_\w+)", src))


def _exists_in_repo(name, want_dir):
    """A file/dir with this basename exists somewhere in the repo (heavy dirs pruned)."""
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        if (name in dirs) if want_dir else (name in files):
            return True
    return False


def _git_ls_files(*paths):
    out = subprocess.check_output(["git", "ls-files", *paths], cwd=ROOT, text=True)
    return set(out.splitlines())


def test_readme_defs_count_matches_schema():
    actual = len(B.build()["$defs"])
    m = re.search(r"(\d+)\s*\$defs", README)
    assert m, "README no longer states a '<n> $defs' count to keep honest"
    assert int(m.group(1)) == actual, f"README says {m.group(1)} $defs; the schema has {actual}"


def test_green_test_count_claims_match():
    actual = _test_count()
    claims = re.findall(r"(\d+)\s*/\s*(\d+)\s+green", README + "\n" + CHANGELOG)
    assert claims, "no 'N/N green' claim found to check"
    for a, b in claims:
        assert int(a) == int(b) == actual, f"'{a}/{b} green' disagrees with the real test count {actual}"


def test_version_alignment():
    pyproj = tomllib.load(open(os.path.join(ROOT, "pyproject.toml"), "rb"))
    assert pyproj["project"]["version"] == fg.HEAD_VERSION, \
        f"pyproject {pyproj['project']['version']} != HEAD_VERSION {fg.HEAD_VERSION}"
    assert fg.HEAD_VERSION in B.build()["title"], "schema title does not carry HEAD_VERSION"


def test_package_runtime_version_matches_pyproject():
    """The package exposes `framegraph.__version__` (§16 row 7), and it agrees
    with the declared `[project] version`. Read as a literal — importing the
    package would hit the models-module shadow (`framegraph` resolves to
    docs/models/framegraph.py in this suite), and the literal is what a real
    `pip install framegraph; framegraph.__version__` would return."""
    init = open(os.path.join(ROOT, "src", "framegraph", "__init__.py"),
                encoding="utf-8").read()
    m = re.search(r'^__version__ = "(\d+\.\d+\.\d+)"', init, re.M)
    assert m, "src/framegraph/__init__.py must define __version__"
    pyproj = tomllib.load(open(os.path.join(ROOT, "pyproject.toml"), "rb"))
    assert m.group(1) == pyproj["project"]["version"], (
        f"framegraph.__version__ {m.group(1)} != pyproject "
        f"{pyproj['project']['version']} — run `make bump`")


def test_layout_paths_exist():
    """The fenced block under '## Layout' is the README's map of the repo; every
    concrete file/dir it names (the left, pre-'←' column) must actually exist."""
    m = re.search(r"## Layout\s*```(.*?)```", README, re.S)
    assert m, "README has no '## Layout' code block"
    missing = []
    for line in m.group(1).splitlines():
        col = line.split("←")[0].strip()          # the path column only (skip annotations)
        if not col:
            continue
        tok = col.split()[0]
        if tok.endswith("/"):                      # a directory entry
            name = tok.rstrip("/")
            ok = os.path.isdir(os.path.join(ROOT, name)) or _exists_in_repo(os.path.basename(name), True)
            if not ok:
                missing.append(tok)
        elif re.search(r"\.\w+$", tok):            # a filename entry
            if "/" in tok:
                ok = os.path.exists(os.path.join(ROOT, tok))
            else:                                  # nested entries are bare basenames
                ok = _exists_in_repo(tok, False)
            if not ok:
                missing.append(tok)
    assert not missing, f"README Layout names paths that don't exist (deleted/renamed?): {missing}"


def test_generated_docs_tracking_policy_matches_git():
    tracked = _git_ls_files("docs")
    leaked = sorted(_TRANSIENT_GENERATED_DOCS & tracked)
    missing_tracked = sorted(_TRACKED_GENERATED_DOCS - tracked)

    assert not leaked, f"transient generated docs should stay ignored/untracked: {leaked}"
    assert not missing_tracked, f"committed generated SDK docs missing from git: {missing_tracked}"
    assert "Only docs/index.md" not in README + "\n" + DOCS_GITIGNORE + "\n" + GEN_DOCS
    assert "they are git-ignored" not in MKDOCS


def test_readme_fixture_status_claim_matches_generated_status():
    m = re.search(r"\*\*(\d+)/(\d+)\*\* have zero errors", FIXTURE_STATUS)
    assert m, "FIXTURE-STATUS.md no longer exposes the generated clean/total summary"
    clean, total = m.groups()

    assert f"{clean}/{total}" in README, (
        f"README should cite current generated fixture status {clean}/{total}"
    )
    assert "Two of the nine fixtures" not in README


def test_claude_guidelines_are_project_specific():
    forbidden = [
        "SEED VERSION",
        "Project Name",
        "<RELATIVE_PATH_TO_DISCLAIMER>",
        "Every README file in this repository **must** reference",
    ]
    for needle in forbidden:
        assert needle not in CLAUDE, f"CLAUDE.md still contains template/policy drift text: {needle}"
    if not os.path.exists(os.path.join(ROOT, "PURPOSE.md")):
        assert "@PURPOSE.md" not in CLAUDE, "CLAUDE.md references missing PURPOSE.md"


def test_architecture_doc_avoids_stale_line_anchors():
    assert "#L" not in ARCHITECTURE, "docs/architecture.md should not use fragile GitHub line anchors"


def test_roadmap_doc_avoids_stale_commit_pins():
    assert "verified_at_commit:" not in ROADMAP
    assert "bc90f15" not in ROADMAP


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
                failed += 1
    print(f"\n{'OK' if not failed else 'FAILED'} ({failed} failure(s))")
    sys.exit(1 if failed else 0)
