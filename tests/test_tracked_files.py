"""The tracked-file enumerator must not confuse the index with the worktree.

``git ls-files`` reports the *index*; the gates read the *worktree*. The two
diverge routinely (unstaged deletion, sparse checkout, a concurrent session
mid-edit), and every gate that fed an index entry straight to ``open()`` turned
that ordinary divergence into a ``FileNotFoundError`` traceback instead of a
finding. These tests pin the split: index membership and readable content are
two different questions with two different answers.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tooling"))

import check_disclaimers as CD  # noqa: E402
import check_doc_links as CDL  # noqa: E402
import check_public_readiness as CPR  # noqa: E402
import gen_examples_index as GEI  # noqa: E402
import gen_status as GS  # noqa: E402
import tracked_files as TF  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo(tmp_path: Path, files: dict[str, str], *, delete: tuple[str, ...]) -> Path:
    """A real git repo where ``delete`` names tracked files removed from disk."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "gate@example.invalid")
    _git(tmp_path, "config", "user.name", "gate")
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "commit.gpgsign=false", "commit", "-qm", "seed")
    for rel in delete:
        (tmp_path / rel).unlink()
    return tmp_path


def _md_repo(tmp_path: Path) -> Path:
    return _repo(
        tmp_path,
        {"kept.md": "---\ndisclaimer: yes\n---\nkept\n", "gone.md": "gone\n"},
        delete=("gone.md",),
    )


# ── the shared enumerator ────────────────────────────────────────────────────

def test_tracked_paths_reports_index_membership_including_deleted_entries(tmp_path):
    repo = _md_repo(tmp_path)

    assert TF.tracked_paths(repo, "*.md") == ["gone.md", "kept.md"]


def test_tracked_on_disk_omits_index_entries_missing_from_the_worktree(tmp_path):
    repo = _md_repo(tmp_path)

    assert TF.tracked_on_disk(repo, "*.md") == ["kept.md"]


def test_tracked_paths_handles_paths_containing_spaces(tmp_path):
    repo = _repo(tmp_path, {"a doc with spaces.md": "x\n"}, delete=())

    assert TF.tracked_paths(repo, "*.md") == ["a doc with spaces.md"]


def test_tracked_paths_is_empty_outside_a_git_repository(tmp_path):
    assert TF.tracked_paths(tmp_path) == []


def test_read_tracked_prefers_the_worktree_copy(tmp_path):
    repo = _md_repo(tmp_path)
    (repo / "kept.md").write_text("edited\n", encoding="utf-8")

    assert TF.read_tracked(repo, "kept.md") == "edited\n"


def test_read_tracked_falls_back_to_the_indexed_blob_when_the_file_is_deleted(tmp_path):
    repo = _md_repo(tmp_path)

    assert TF.read_tracked(repo, "gone.md") == "gone\n"


# ── the three gates that crashed ─────────────────────────────────────────────

def test_secret_scan_survives_a_tracked_file_absent_from_the_worktree():
    """The exact reported crash: a `` D`` entry blew up the whole gate."""
    finding = CPR._check_secret_literals(["no/such/file/on/disk.md"])

    assert finding.ok


def test_secret_scan_still_catches_a_real_secret(tmp_path, monkeypatch):
    # Split so this source file does not itself contain a literal matching the
    # AWS pattern — a fixture written inline makes the scanner flag its own test
    # and the public-readiness gate fails on a false positive. The value is
    # AWS's published example key; it is assembled at runtime, so the assertion
    # below still exercises the real pattern.
    fixture_key = "AKIA" + "IOSFODNN7EXAMPLE"
    (tmp_path / "leak.md").write_text(f"token = {fixture_key}\n", encoding="utf-8")
    monkeypatch.setattr(CPR, "ROOT", tmp_path)

    finding = CPR._check_secret_literals(["leak.md"])

    assert not finding.ok
    assert "aws access key" in finding.detail


def test_tracked_artifact_check_still_flags_an_offender_deleted_from_disk():
    """Index membership, not worktree presence: filtering this list would let a
    tracked ``out/`` artifact slip the gate whenever it is locally deleted."""
    finding = CPR._check_no_tracked_local_artifacts(["out/leaked.svg"])

    assert not finding.ok


def test_issue_config_check_reports_instead_of_crashing_when_config_is_missing(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(CPR, "ROOT", tmp_path)

    finding = CPR._check_issue_config_matches_enabled_features()

    assert not finding.ok
    assert "config.yml" in finding.detail


def test_disclaimer_gate_skips_docs_deleted_from_the_worktree(tmp_path, monkeypatch):
    repo = _md_repo(tmp_path)
    monkeypatch.setattr(CD, "ROOT", repo)

    assert CD.tracked_md() == ["kept.md"]


def test_doc_link_gate_skips_docs_deleted_from_the_worktree(tmp_path, monkeypatch):
    repo = _md_repo(tmp_path)
    monkeypatch.setattr(CDL, "ROOT", repo)

    assert CDL.tracked_md() == [repo / "kept.md"]


# ── the two generators: index-faithful, never truncated in silence ───────────

def test_examples_index_summarizes_a_deleted_example_from_the_indexed_blob(
    tmp_path, monkeypatch
):
    """A generator's output is gated against the *index*, so a locally deleted
    example must keep its row rather than crash or silently vanish."""
    repo = _repo(
        tmp_path,
        {"static/examples/gone.py": '"""Stated intent."""\n'},
        delete=("static/examples/gone.py",),
    )
    monkeypatch.setattr(GEI, "ROOT", str(repo))

    assert GEI.tracked_examples() == ["static/examples/gone.py"]
    assert GEI.summarize("static/examples/gone.py") == "Stated intent."


def test_status_generator_warns_and_skips_a_deleted_fixture(tmp_path, monkeypatch, capsys):
    repo = _repo(
        tmp_path,
        {"tests/fixtures/kept.fg.yaml": "doc: {}\n", "tests/fixtures/gone.fg.yaml": "doc: {}\n"},
        delete=("tests/fixtures/gone.fg.yaml",),
    )
    monkeypatch.setattr(GS, "ROOT", str(repo))

    files = GS.fixture_files()

    assert [Path(f).name for f in files] == ["kept.fg.yaml"]
    assert "gone.fg.yaml" in capsys.readouterr().err
