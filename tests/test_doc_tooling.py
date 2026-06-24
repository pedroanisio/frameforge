#!/usr/bin/env python3
"""
test_doc_tooling.py — coverage for the documentation/schema generators that the
gates run but pytest never imported (so they read 0% / 34%):

  * schema/build_schema.py   — build(), and main() --check / write / validate-a-doc
  * tooling/gen_status.py    — build() table + the --check drift contract
  * tooling/gen_docs.py      — the schema-reference + grammar generators, and a
                               full generate()+nav check (renders the gallery)

Write/`--check` paths are pointed at tmp via monkeypatch so the committed
FIXTURE-STATUS.md / schema are never clobbered. Models-side import (these tools
put models/ on sys.path), so evict a package shadow first — see test_head.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "schema"))
sys.path.insert(0, os.path.join(ROOT, "tooling"))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):  # the rendering package
    del sys.modules["framegraph"]

import build_schema as B  # noqa: E402
import gen_status as GS  # noqa: E402
import gen_docs as GD  # noqa: E402


# --------------------------------------------------------------------------- #
#  build_schema.py                                                            #
# --------------------------------------------------------------------------- #
def test_build_schema_build_shape():
    schema = B.build()
    assert schema["$schema"].endswith("/schema")
    assert schema["title"].startswith("FrameGraph v2")
    assert "pages" in schema["properties"]
    assert "Style" in schema["$defs"] and len(schema["$defs"]) >= 70


def test_build_schema_check_is_in_sync():
    assert B.main(["--check"]) == 0  # the committed schema matches a fresh build


def test_build_schema_write_then_validate(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "SCHEMA_PATH", str(tmp_path / "schema.json"))
    assert B.main([]) == 0
    assert os.path.exists(tmp_path / "schema.json")
    # a known-good fixture validates against the freshly written schema/models
    assert B.main([os.path.join(ROOT, "fixtures", "calendar-3day.fg.yaml")]) == 0


# --------------------------------------------------------------------------- #
#  gen_status.py                                                              #
# --------------------------------------------------------------------------- #
def test_gen_status_build_table():
    md = GS.build()
    assert "| Fixture |" in md and "have zero errors" in md
    assert md.count("|") > 10  # at least a few rows


def test_gen_status_write_then_check(tmp_path, monkeypatch):
    monkeypatch.setattr(GS, "OUT", str(tmp_path / "FIXTURE-STATUS.md"))
    assert GS.main([]) == 0
    assert os.path.exists(tmp_path / "FIXTURE-STATUS.md")
    assert GS.main(["--check"]) == 0          # just written -> in sync
    open(GS.OUT, "a", encoding="utf-8").write("drift\n")
    assert GS.main(["--check"]) == 1          # now stale -> non-zero


# --------------------------------------------------------------------------- #
#  gen_docs.py                                                                #
# --------------------------------------------------------------------------- #
def test_gen_reference_lists_every_model():
    md = GD.gen_reference()
    assert "# Schema reference" in md
    assert "## `Document`" in md and "## `Style`" in md
    assert "| Property | Type | Required | Description |" in md


def test_gen_grammar_embeds_both_ebnf():
    md = GD.gen_grammar()
    assert "```ebnf" in md
    assert "Core grammar" in md and "Style module" in md


def test_gen_docs_check_generates_and_resolves_nav():
    # heavy: generate() renders the fixture gallery (subprocess) + asserts nav exists
    assert GD.main(["--check"]) == 0


def test_gen_docs_sdk_regenerates_only_the_committed_snapshots(tmp_path, monkeypatch):
    # the fast `--sdk` fix path: writes ONLY sdk.md / sdk-api.md (no fixture
    # gallery), so refreshing the snapshot after an SDK change is cheap.
    monkeypatch.setattr(GD, "DOCS", str(tmp_path))
    assert GD.main(["--sdk"]) == 0
    assert sorted(os.listdir(tmp_path)) == ["sdk-api.md", "sdk.md"]
    assert "API" in open(tmp_path / "sdk-api.md", encoding="utf-8").read()
    # what it wrote is exactly what the --check gate rebuilds (self-consistent)
    assert not GD.stale_tracked_pages()
