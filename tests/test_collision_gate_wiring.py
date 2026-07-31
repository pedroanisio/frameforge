"""The collision gate must FIRE BY DEFAULT — the detector is not the gate.

`tests/test_collision_detector.py` proves the render-time detector is correct:
it compares drawn ink, honours `overlap: allowed`, and does not flood on boxes.
This file gates the part that actually protects a document, and that was
missing: a 17-page spec whose cover painted an entire content block on top of
another one passed `validate` and rendered to PNG/PDF without emitting a single
line about it, because

* the check was opt-in (`--check-collision`, default off),
* its worst verdict was WARN "never fails the build on its own", and
* no Makefile target, gate, or test ever passed the flag.

A detector nothing runs is not a gate. The contract here:

* the check runs by DEFAULT; `--no-check-collision` is the deliberate override
  (the "force"), so silence has to be asked for rather than inherited;
* severity SCALES WITH MAGNITUDE. Estimate-mode metrics are unverified (PALS's
  Law) and that is the stated reason the verdict stayed advisory — but glyph
  advance estimation errs by a few px per line, so it cannot manufacture a
  466x64 px text-on-text overlap. Above `GROSS_COLLISION_AREA` the finding is an
  ERROR; below it stays a WARN, so measurement noise still never fails a build.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "tooling")]

import validate as V  # noqa: E402

BIGFONT = {"font_family": ["DejaVu Sans", "sans-serif"], "font_size": 20}


def _doc(objects):
    page = {"mode": "page", "id": "cover",
            "canvas": {"size": [400, 200], "units": "px"},
            "rendering": {"coordinate_mode": "absolute"},
            "layers": [{"id": "main", "z": 0, "objects": objects}]}
    return {"dsl": "FrameForge", "version": "2.0.0", "title": "t",
            "defs": {"tokens": {}}, "pages": [page]}


def _txt(oid, box, text="OVERLAPPING WIDE TEXT", **extra):
    return {"type": "text", "id": oid, "box": box, "text": text,
            "style": BIGFONT, **extra}


def _write(tmp_path, doc):
    import json
    p = tmp_path / "doc.fg.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return str(p)


# A whole block stacked on another one — the re-metro cover's failure, reduced.
GROSS = [_txt("ledger", [10, 40, 380, 30]), _txt("disclaimer", [10, 40, 380, 30])]


def test_collision_check_runs_without_being_asked(tmp_path):
    """The regression: validate_doc(path) with NO flags stayed silent."""
    _doc_, findings, _rc = V.validate_doc(_write(tmp_path, _doc(GROSS)))
    assert any(f.code == "collision" for f in findings), (
        "a page with text painted on text validated clean by default — the "
        "collision gate must not require --check-collision to fire")


def test_gross_collision_is_an_error_not_a_warning(tmp_path):
    _doc_, findings, rc = V.validate_doc(_write(tmp_path, _doc(GROSS)))
    hits = [f for f in findings if f.code == "collision"]
    assert hits, "no collision reported"
    assert any(f.severity == "ERROR" for f in hits), (
        "an ink overlap far larger than any metrics-estimation error must fail, "
        f"not warn: {[(f.severity, f.msg) for f in hits]}")
    assert rc != 0, "a document that paints text over text must not exit clean"


def test_sub_threshold_overlap_still_only_warns(tmp_path):
    """Measurement noise must never fail a build (PALS's Law stays honoured)."""
    objs = [_txt("a", [10, 40, 200, 30], text="TIGHT"),
            _txt("b", [96, 40, 200, 30], text="TIGHT")]
    _doc_, findings, _rc = V.validate_doc(_write(tmp_path, _doc(objs)))
    for f in (f for f in findings if f.code == "collision"):
        assert f.severity == "WARN", f"small overlap must stay advisory: {f.msg}"


def test_consented_overlap_never_fires(tmp_path):
    objs = [_txt("a", [10, 40, 380, 30], overlap="allowed"),
            _txt("b", [10, 40, 380, 30], overlap="allowed")]
    _doc_, findings, _rc = V.validate_doc(_write(tmp_path, _doc(objs)))
    assert not [f for f in findings if f.code == "collision"], (
        "declared overlap is a first-class effect, not a defect")


def test_the_override_exists_and_silences_it(tmp_path):
    """Silence must be explicitly asked for — the 'force'."""
    _doc_, findings, _rc = V.validate_doc(_write(tmp_path, _doc(GROSS)),
                                          check_collision=False)
    assert not [f for f in findings if f.code == "collision"]


def test_clean_document_stays_clean(tmp_path):
    objs = [_txt("a", [10, 10, 380, 30]), _txt("b", [10, 120, 380, 30])]
    _doc_, findings, _rc = V.validate_doc(_write(tmp_path, _doc(objs)))
    assert not [f for f in findings if f.code == "collision"]
