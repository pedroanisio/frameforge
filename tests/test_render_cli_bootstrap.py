"""frameforge-render bootstrap — works without PYTHONPATH, from the src layout.

Closes issue #35. Two root causes, both src-layout refactor casualties:

- ``frameforge.sdk.model`` hard-imports ``models.frameforge`` and relied on the
  caller exporting ``PYTHONPATH=docs`` — the Makefile compensates, the CLI
  front door did not, so ``uv run frameforge-render … --to svg`` crashed with
  ``ModuleNotFoundError: models``.
- ``frameforge.cli`` derived the repo root as ``HERE/..`` from its pre-refactor
  depth, so with the package under ``src/`` every ROOT-relative default (the
  ``out/render-cli`` output dir, discovery paths) landed under ``src/``.

Runs under pytest or standalone
(``uv run python tests/test_render_cli_bootstrap.py``).
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(ROOT, "src")

MINI_DOC = """\
dsl: FrameForge
version: 2.3.0
title: cli bootstrap smoke
pages:
- mode: page
  id: p1
  canvas: {size: [120, 80], units: px}
  layers:
  - id: l1
    objects:
    - {id: bg, type: rect, box: [0, 0, 120, 80], fill: '#fbfaf6'}
    - {id: hi, type: text, box: [10, 10, 100, 20], text: hello,
       style: {font_size: 12}}
"""


def _clean_env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def test_sdk_model_resolves_without_docs_on_path(tmp_path):
    """The root cause: importing the SDK model module must succeed with only
    ``src`` importable — no PYTHONPATH, no repo CWD (the fallback derives
    ``<repo>/docs`` from its own location)."""
    code = ("import sys; sys.path.insert(0, %r); "
            "from frameforge.sdk.model import HEAD_VERSION; print(HEAD_VERSION)" % SRC)
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, env=_clean_env(), cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip()


def test_cli_root_is_the_repository_root():
    """ROOT-relative defaults must anchor at the repo, not at ``src/``."""
    sys.path.insert(0, SRC)
    try:
        import frameforge.cli as cli
    finally:
        sys.path.remove(SRC)
    assert os.path.isfile(os.path.join(cli.ROOT, "pyproject.toml")), (
        f"cli.ROOT={cli.ROOT!r} is not the repository root")
    assert os.path.basename(cli.ROOT) != "src"


def test_cli_renders_end_to_end_without_pythonpath(tmp_path):
    """The user-visible contract: the render front door produces SVG pages in
    the requested out dir with no PYTHONPATH in the environment."""
    doc = tmp_path / "mini.fg.yaml"
    doc.write_text(MINI_DOC, encoding="utf-8")
    out = tmp_path / "out"
    code = ("import sys; sys.path.insert(0, %r); "
            "from frameforge.cli import main; "
            "sys.exit(main([%r, '--to', 'svg', '--out', %r]))"
            % (SRC, str(doc), str(out)))
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, env=_clean_env(), cwd=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    svgs = list(out.glob("*.svg"))
    assert svgs, f"no SVG written to {out}: {proc.stdout + proc.stderr}"
    assert "hello" in svgs[0].read_text(encoding="utf-8")



def test_tooling_launcher_is_pythonpath_and_cwd_free(tmp_path):
    """`uv run python tooling/frameforge_render.py` is the virtual-project
    front door (the [project.scripts] entry stays inert by the §2 decision):
    it must bootstrap src+docs itself and run from any CWD, clean env."""
    doc = tmp_path / "mini.fg.yaml"
    doc.write_text(MINI_DOC, encoding="utf-8")
    out = tmp_path / "out"
    launcher = os.path.join(ROOT, "tooling", "frameforge_render.py")
    proc = subprocess.run(
        [sys.executable, launcher, str(doc), "--to", "svg", "--out", str(out)],
        capture_output=True, text=True, env=_clean_env(), cwd=tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert list(out.glob("*.svg")), "launcher produced no SVG"

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
