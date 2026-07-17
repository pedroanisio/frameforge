#!/usr/bin/env python3
"""
test_render_cli.py — coverage for the render_fixtures.py *driver* (discover /
stem_of / write_index / main), which the suite never exercised (the renderer
internals are covered by test_rendering_svg_semantics / test_element_render).

Renderer-only import (the `frameforge` package must win) — evict a models-module
shadow first, per test_rendering_svg_semantics.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # the models module
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from tooling import render_fixtures as R  # noqa: E402

CAL = os.path.join(R.FIXTURES, "calendar-3day.fg.yaml")
LEGACY_COVER = os.path.join(R.FIXTURES, "newset", "cover-minimal-sidebar.yml")
LEGACY_AGENDA = os.path.join(R.FIXTURES, "newset", "agenda-left-pane.yml")


# --- discover / stem_of ------------------------------------------------------- #
def test_stem_of_keeps_extension_and_relpath():
    assert R.stem_of(os.path.join(R.FIXTURES, "b1", "x.fg.json")) == "b1_x.fg.json"
    assert R.stem_of("/tmp/y.fg.yaml") == "y.fg.yaml"


def test_discover_file_glob_dir_default_and_missing():
    assert [d[0] for d in R.discover([CAL])] == [CAL]
    glob_docs = R.discover([os.path.join(R.FIXTURES, "*.fg.yaml")])
    assert len(glob_docs) >= 3 and all(d[1]["dsl"] == "FrameForge" for d in glob_docs)
    assert len(R.discover([os.path.join(R.FIXTURES, "b1")])) >= 1   # directory walk
    assert len(R.discover([])) >= 8                                  # defaults to fixtures/
    assert R.discover(["/no/such/path.fg.yaml"]) == []              # nothing matches


def test_legacy_presentation_decks_normalize_to_pages():
    docs = dict(R.discover([LEGACY_COVER, LEGACY_AGENDA]))
    assert set(docs) == {LEGACY_COVER, LEGACY_AGENDA}
    cover = docs[LEGACY_COVER]
    agenda = docs[LEGACY_AGENDA]
    assert cover["version"] == "2.2.0"
    assert cover["pages"][0]["layers"][0]["objects"][0]["type"] == "group"
    assert cover["pages"][0]["layers"][0]["objects"][0]["children"][3]["text"] == "Docusign Workshop 1.1"
    assert agenda["pages"][0]["layers"][0]["objects"][0]["children"][0]["fill"] == "ink_navy"


# --- write_index -------------------------------------------------------------- #
def test_write_index_both_modes(tmp_path):
    R.write_index(str(tmp_path), [("doc1", "doc1/index.html", ["doc1/p001.svg"])],
                  "Contact sheet", page_links=False)
    assert (tmp_path / "index.html").exists()
    R.write_index(str(tmp_path), [("d", "", ["p001.svg", "p002.svg"])], "Per-doc", page_links=True)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Per-doc" in html and "p001.svg" in html


# --- main() ------------------------------------------------------------------- #
def test_main_list(capsys):
    assert R.main(["--list"]) == 0
    assert "document(s)." in capsys.readouterr().out


def test_main_renders_single_doc(tmp_path):
    rc = R.main([CAL, "--out", str(tmp_path), "--max-pages", "1", "-q"])
    assert rc == 0
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / R.stem_of(CAL) / "p001.svg").exists()


def test_main_renders_legacy_deck(tmp_path):
    rc = R.main([LEGACY_COVER, "--out", str(tmp_path), "--max-pages", "1", "-q"])
    assert rc == 0
    svg = (tmp_path / R.stem_of(LEGACY_COVER) / "p001.svg").read_text(encoding="utf-8")
    assert "Docusign Workshop 1.1" in svg


def test_main_no_documents_found(tmp_path):
    assert R.main(["/no/such/file.fg.yaml", "--out", str(tmp_path)]) == 1


def test_main_all_flag_list(capsys):
    # the --all branch of discover(); --list keeps it fast (no rendering)
    assert R.main(["--all", "--list"]) == 0
    assert "document(s)." in capsys.readouterr().out


def test_main_single_doc_overflow_report(tmp_path, capsys):
    # the --check-overflow report path (one doc keeps it fast)
    rc = R.main([CAL, "--out", str(tmp_path), "--max-pages", "1", "--check-overflow", "-q"])
    out = capsys.readouterr().out
    assert rc == 0 and "overflow check" in out
