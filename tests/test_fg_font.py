"""fg-font: the fonts a document depends on must be enumerable, gate-able, and
packable so measure == render on any host (ADR-0004 / the pinned-font contract)."""
from __future__ import annotations

import json
import os
import sys
import zipfile

import yaml

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):   # evict a models-module shadow
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.fontpack import main, referenced_families  # noqa: E402


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


def test_install_extracts_pack_and_writes_scoped_fontconfig(tmp_path):
    p = tmp_path / "d.fg.yaml"
    p.write_text(yaml.safe_dump(_doc(["ZzzMissing", "serif"])))
    fp = tmp_path / "d.fp"
    assert main(["--pack", str(p), "--out", str(fp), "--allow-missing"]) == 0
    dest = tmp_path / "runtime"
    assert main(["--install", str(fp), "--dir", str(dest)]) == 0
    conf = (dest / "fonts.conf").read_text()
    assert (dest / "fonts").is_dir()
    assert str(dest / "fonts") in conf and "<include" in conf     # scoped + system fallback


def test_install_rejects_a_tampered_pack(tmp_path):
    fp = tmp_path / "bad.fp"
    with zipfile.ZipFile(fp, "w") as z:
        z.writestr("fonts/x.ttf", b"not-a-real-font")
        z.writestr("manifest.json", json.dumps({"fp_version": 1, "fonts": [
            {"family": "X", "bold": False, "file": "fonts/x.ttf", "sha256": "0" * 64}]}))
    assert main(["--install", str(fp), "--dir", str(tmp_path / "r")]) == 1   # sha256 mismatch


def test_google_slug_derivation():
    from frameforge.fontpack import google_slug
    assert google_slug("EB Garamond") == "ebgaramond"
    assert google_slug("Fira Sans") == "firasans"
    assert google_slug("JetBrains Mono") == "jetbrainsmono"


def test_check_fetch_passes_when_missing_family_is_on_google_fonts(tmp_path, monkeypatch, capsys):
    import frameforge.fontpack as fpmod
    monkeypatch.setattr(fpmod, "google_available", lambda fam: fam == "OnGoogleFonts")
    p = tmp_path / "d.fg.yaml"
    p.write_text(yaml.safe_dump(_doc(["OnGoogleFonts", "serif"])))
    assert main(["--check", str(p), "--fetch"]) == 0          # provisionable → self-healing pass
    out = capsys.readouterr().out
    assert "FETCHABLE" in out and "--pack --fetch" in out
    # ...but without --fetch the same doc is still a hard determinism failure
    assert main(["--check", str(p)]) == 1


def test_pack_fetch_provisions_missing_family_from_google_fonts(tmp_path, monkeypatch):
    import frameforge.fontpack as fpmod
    fake = tmp_path / "FetchedFont-Regular.ttf"
    fake.write_bytes(b"FAKEFONTDATA")                    # stand in for a downloaded TTF
    monkeypatch.setattr(fpmod, "fetch_google_font",
                        lambda fam, bold, cache: (str(fake) if not bold else None))
    p = tmp_path / "d.fg.yaml"
    p.write_text(yaml.safe_dump(_doc(["FetchedFont", "serif"])))
    out = tmp_path / "d.fp"
    assert main(["--pack", str(p), "--out", str(out), "--fetch"]) == 0   # fetched → packs
    with zipfile.ZipFile(out) as z:
        m = json.loads(z.read("manifest.json"))
        entry = next(e for e in m["fonts"] if e["family"] == "FetchedFont")
        assert entry["source"].startswith("google-fonts:")              # provenance stamped
        assert entry["file"] in z.namelist()
