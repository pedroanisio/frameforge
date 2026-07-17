"""Editable SDK-client roots — persistent out-of-repo roots (docker /work).

The MCP server confines ``read/write/list_sdk_clients`` to configured roots.
Historically every root was forced *inside* the repository, which in the Docker
image means the ephemeral ``--rm`` container layer: clients written over MCP
vanished when the container exited. These tests pin the widened contract:

- explicitly configured absolute roots MAY live outside the repository
  (e.g. ``/work/clients`` on the persistent named volume);
- the default (``static/examples``) stays repo-relative and unchanged;
- traversal outside the configured roots is still rejected with the
  established error message;
- paths from outside-repo roots are reported as absolute paths (repo-relative
  reporting is impossible for them by construction).

Runs under pytest or standalone (``uv run python tests/test_mcp_edit_roots.py``).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from frameforge.mcp.clients import (  # noqa: E402
    list_sdk_clients,
    read_sdk_client,
    write_sdk_client,
)
from frameforge.mcp.security import _client_roots, _resolve_client_path  # noqa: E402

CODE = "def build():\n    return {'dsl': 'FrameForge'}\n"


@pytest.fixture()
def tmp_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("FRAMEFORGE_MCP_EDIT_ROOTS", raising=False)
    repo = tmp_path / "repo"
    (repo / "static" / "examples").mkdir(parents=True)
    return repo


@pytest.fixture()
def work_root(tmp_path: Path) -> Path:
    work = tmp_path / "work" / "clients"
    work.mkdir(parents=True)
    return work


def test_default_roots_stay_repo_relative(tmp_repo: Path) -> None:
    roots = _client_roots(tmp_repo, None)
    assert roots == [(tmp_repo / "static" / "examples").resolve()]


def test_configured_absolute_outside_root_is_honored(tmp_repo: Path, work_root: Path) -> None:
    roots = _client_roots(tmp_repo, [str(work_root)])
    assert roots == [work_root.resolve()]


def test_env_var_mixes_repo_and_outside_roots(
    tmp_repo: Path, work_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "FRAMEFORGE_MCP_EDIT_ROOTS", os.pathsep.join([str(work_root), "static/examples"])
    )
    roots = _client_roots(tmp_repo, None)
    assert roots == [work_root.resolve(), (tmp_repo / "static" / "examples").resolve()]


def test_write_create_and_read_roundtrip_in_outside_root(
    tmp_repo: Path, work_root: Path
) -> None:
    target = work_root / "deck.py"
    written = write_sdk_client(
        str(target), CODE, create=True, repo_root=tmp_repo, edit_roots=[str(work_root)]
    )
    assert written["ok"] and target.is_file()
    # outside the repo there is no repo-relative form — the report is absolute
    assert written["path"] == target.resolve().as_posix()

    read = read_sdk_client(str(target), repo_root=tmp_repo, edit_roots=[str(work_root)])
    assert read["ok"] and read["code"] == CODE


def test_relative_path_falls_back_to_outside_root(tmp_repo: Path, work_root: Path) -> None:
    written = write_sdk_client(
        "poster.py", CODE, create=True, repo_root=tmp_repo, edit_roots=[str(work_root)]
    )
    assert written["ok"]
    assert (work_root / "poster.py").is_file()


def test_existing_file_wins_over_create_target(tmp_repo: Path, work_root: Path) -> None:
    """A bare name that already exists in a later root edits it in place."""
    existing = tmp_repo / "static" / "examples" / "logo.py"
    existing.write_text(CODE, encoding="utf-8")
    roots = [str(work_root), "static/examples"]
    written = write_sdk_client(
        "logo.py", CODE + "# v2\n", create=True, repo_root=tmp_repo, edit_roots=roots
    )
    assert written["ok"] and written["created"] is False
    assert existing.read_text(encoding="utf-8").endswith("# v2\n")
    assert not (work_root / "logo.py").exists()


def test_list_spans_repo_and_outside_roots(tmp_repo: Path, work_root: Path) -> None:
    (tmp_repo / "static" / "examples" / "a.py").write_text(CODE, encoding="utf-8")
    (work_root / "b.py").write_text(CODE, encoding="utf-8")
    roots = [str(work_root), "static/examples"]
    listed = list_sdk_clients(repo_root=tmp_repo, edit_roots=roots)
    names = {Path(client["path"]).name for client in listed["clients"]}
    assert names == {"a.py", "b.py"}
    assert work_root.resolve().as_posix() in listed["allowed_roots"]
    assert "static/examples" in listed["allowed_roots"]


def test_traversal_outside_configured_roots_is_rejected(
    tmp_repo: Path, work_root: Path, tmp_path: Path
) -> None:
    stray = tmp_path / "elsewhere" / "x.py"
    stray.parent.mkdir(parents=True)
    stray.write_text(CODE, encoding="utf-8")
    with pytest.raises(ValueError, match="allowed SDK client roots"):
        _resolve_client_path(
            str(stray), repo_root=tmp_repo, edit_roots=[str(work_root)], must_exist=True
        )
    with pytest.raises(ValueError, match="allowed SDK client roots"):
        _resolve_client_path(
            "../escape.py", repo_root=tmp_repo, edit_roots=[str(work_root)], must_exist=False
        )


def test_non_python_suffix_still_rejected(tmp_repo: Path, work_root: Path) -> None:
    with pytest.raises(ValueError, match=r"\.py file"):
        _resolve_client_path(
            "notes.txt", repo_root=tmp_repo, edit_roots=[str(work_root)], must_exist=False
        )


def test_legacy_absolute_repo_relative_input_still_resolves(tmp_repo: Path) -> None:
    """'/static/examples/foo.py' (leading slash) keeps resolving into the repo."""
    target = tmp_repo / "static" / "examples" / "foo.py"
    target.write_text(CODE, encoding="utf-8")
    resolved = _resolve_client_path(
        "/static/examples/foo.py", repo_root=tmp_repo, edit_roots=None, must_exist=True
    )
    assert resolved == target.resolve()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
