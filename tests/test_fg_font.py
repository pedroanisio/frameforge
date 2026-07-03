"""fg-font: the fonts a document depends on must be enumerable, gate-able, and
packable so measure == render on any host (ADR-0004 / the pinned-font contract)."""
from __future__ import annotations

import json
import os
import sys
import zipfile

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tooling.fg_font import main, referenced_families  # noqa: E402


def test_referenced_families_expands_tokens_and_filters_generics():
    doc = {
        "defs": {"tokens": {
            "fonts": {"body": {"family": "Bitstream Charter", "fallback": ["serif"]},
                      "brand": "Inter"},
            "styles": {"h1": {"font_family": ["Inter", "sans-serif"]}}}},
        "pages": [{"layers": [{"objects": [
            {"type": "text", "style": {"font_family": "body"}},          # tokens key
            {"type": "text", "style": {"font_family": ["EB Garamond", "serif"]}}]}]}],
    }
    fams = referenced_families(doc)
    assert {"Bitstream Charter", "Inter", "EB Garamond"} <= fams
    assert "serif" not in fams and "sans-serif" not in fams              # generics filtered


def _doc(family):
    return {"pages": [{"layers": [{"objects": [
        {"type": "text", "style": {"font_family": family}}]}]}]}


def test_check_fails_on_substituted_font(tmp_path, capsys):
    p = tmp_path / "d.fg.yaml"
    p.write_text(yaml.safe_dump(_doc(["ZzzNoSuchFace", "serif"])))
    assert main(["--check", str(p)]) == 1                               # substitution → non-zero
    assert "SUBSTITUTED" in capsys.readouterr().out


def test_check_passes_when_only_generics(tmp_path):
    p = tmp_path / "d.fg.yaml"
    p.write_text(yaml.safe_dump(_doc(["serif"])))
    assert main(["--check", str(p)]) == 0        # no concrete family → nothing can substitute


def test_pack_produces_a_valid_fp_with_manifest(tmp_path):
    p = tmp_path / "d.fg.yaml"
    p.write_text(yaml.safe_dump(_doc(["ZzzMissing", "serif"])))
    out = tmp_path / "d.fp"
    assert main(["--pack", str(p), "--out", str(out), "--allow-missing"]) == 0
    with zipfile.ZipFile(out) as z:
        assert "manifest.json" in z.namelist()
        m = json.loads(z.read("manifest.json"))
        assert m["fp_version"] == 1 and isinstance(m["fonts"], list)


def test_pack_fails_without_allow_missing(tmp_path):
    p = tmp_path / "d.fg.yaml"
    p.write_text(yaml.safe_dump(_doc(["ZzzMissing"])))
    assert main(["--pack", str(p), "--out", str(tmp_path / "x.fp")]) == 1   # refuses to lie
