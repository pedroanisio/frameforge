#!/usr/bin/env python3
"""`pick_engine` must verify the engine RUNS, not just that its files exist.

Found via `--to pdf-tex` on a host where `lualatex` is present (with
luaotfload) but the binary crashes on launch (a broken `ld.so` — rc 127
before it reads any .tex). Auto-selection picked the crashing engine and the
compile died with a generic "lualatex failed" that hid the real cause, while
a working `pdflatex` sat right there unused.

Pinned here:
  * auto falls back to pdflatex when lualatex is present-but-unrunnable;
  * a `--version` smoke test is the discriminator (cheap, cached);
  * an EXPLICIT engine choice is respected (returned if on PATH) — the user
    owns that decision;
  * a failed compile surfaces the log tail so an ld.so/env crash is visible,
    not swallowed.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.infrastructure.latex import compile as C  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_cache():
    C._engine_runs.cache_clear()
    yield
    C._engine_runs.cache_clear()


def _fake_which(present):
    return lambda name: (f"/usr/bin/{name}" if name in present else None)


def _fake_runs(runnable):
    return lambda engine: engine in runnable


# --- the reported failure ------------------------------------------------- #
def test_auto_falls_back_when_lualatex_present_but_crashes(monkeypatch):
    """Exact repro: lualatex + luaotfload present, but lualatex won't RUN."""
    monkeypatch.setattr(C.shutil, "which", _fake_which({"lualatex", "pdflatex"}))
    monkeypatch.setattr(C, "_has_luaotfload", lambda: True)
    monkeypatch.setattr(C, "_engine_runs", _fake_runs({"pdflatex"}))
    assert C.pick_engine("auto") == "pdflatex"


def test_auto_prefers_lualatex_when_it_actually_runs(monkeypatch):
    monkeypatch.setattr(C.shutil, "which", _fake_which({"lualatex", "pdflatex"}))
    monkeypatch.setattr(C, "_has_luaotfload", lambda: True)
    monkeypatch.setattr(C, "_engine_runs", _fake_runs({"lualatex", "pdflatex"}))
    assert C.pick_engine("auto") == "lualatex"


def test_auto_none_when_neither_runs(monkeypatch):
    monkeypatch.setattr(C.shutil, "which", _fake_which({"lualatex", "pdflatex"}))
    monkeypatch.setattr(C, "_has_luaotfload", lambda: True)
    monkeypatch.setattr(C, "_engine_runs", _fake_runs(set()))
    assert C.pick_engine("auto") is None


def test_auto_uses_pdflatex_when_luaotfload_missing(monkeypatch):
    """The pre-existing luaotfload gate still applies (before the run check)."""
    monkeypatch.setattr(C.shutil, "which", _fake_which({"lualatex", "pdflatex"}))
    monkeypatch.setattr(C, "_has_luaotfload", lambda: False)
    monkeypatch.setattr(C, "_engine_runs", _fake_runs({"lualatex", "pdflatex"}))
    assert C.pick_engine("auto") == "pdflatex"


# --- explicit choice is the user's to make -------------------------------- #
def test_explicit_engine_is_respected_even_if_unverified(monkeypatch):
    monkeypatch.setattr(C.shutil, "which", _fake_which({"lualatex", "pdflatex"}))
    # do not smoke-test an explicit request — return it, let it fail loudly
    assert C.pick_engine("lualatex") == "lualatex"
    assert C.pick_engine("pdflatex") == "pdflatex"


def test_explicit_engine_absent_is_none(monkeypatch):
    monkeypatch.setattr(C.shutil, "which", _fake_which({"pdflatex"}))
    assert C.pick_engine("lualatex") is None


# --- the smoke test itself ------------------------------------------------- #
def test_engine_runs_true_on_zero_exit(monkeypatch):
    class P:
        returncode = 0
    monkeypatch.setattr(C.subprocess, "run", lambda *a, **k: P())
    assert C._engine_runs("pdflatex") is True


def test_engine_runs_false_on_nonzero_exit(monkeypatch):
    """rc 127 = the ld.so crash that started this."""
    class P:
        returncode = 127
    monkeypatch.setattr(C.subprocess, "run", lambda *a, **k: P())
    assert C._engine_runs("lualatex") is False


def test_engine_runs_false_when_launch_raises(monkeypatch):
    def boom(*a, **k):
        raise OSError("cannot exec")
    monkeypatch.setattr(C.subprocess, "run", boom)
    assert C._engine_runs("lualatex") is False


# --- the failure surfaces its cause --------------------------------------- #
def test_compile_document_error_includes_log_tail(monkeypatch):
    """A failed compile must name the real cause (e.g. an ld.so crash), not a
    generic 'engine failed'."""
    monkeypatch.setattr(C, "pick_engine", lambda engine: "lualatex")
    monkeypatch.setattr(C, "transpile", lambda doc, asset_base=None: "\\documentclass{article}")

    def fake_compile(tex_path, engine="lualatex", quiet=True, passes=2, log_sink=None):
        if log_sink is not None:
            log_sink.append("Inconsistency detected by ld.so: ... "
                            "elf_machine_rela_relative Assertion failed")
        return None

    monkeypatch.setattr(C, "compile_tex", fake_compile)
    with pytest.raises(RuntimeError, match="ld.so"):
        C.compile_document({"dsl": "FrameForge"}, engine="auto")


def test_compile_tex_populates_log_sink_on_failure(monkeypatch, tmp_path):
    class P:
        returncode = 1
        stdout = "! LaTeX Error: something broke\nline 2\n"
        stderr = "extra stderr detail\n"
    monkeypatch.setattr(C.subprocess, "run", lambda *a, **k: P())
    tex = tmp_path / "doc.tex"
    tex.write_text("\\documentclass{article}")
    sink: list[str] = []
    assert C.compile_tex(str(tex), engine="pdflatex", log_sink=sink) is None
    assert sink and "LaTeX Error" in sink[0]
