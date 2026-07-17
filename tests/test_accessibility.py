#!/usr/bin/env python3
"""
test_accessibility.py — coverage + contract for tooling/check_accessibility.py,
the accessibility/tagged-export conformance lint (roadmap item 2).

Asserts (1) the checked-in reference fixture is fully clean, (2) each rule fires
at the right severity on a minimal synthetic doc, and (3) the CLI exit codes.
check_accessibility reads documents as data (no model import), so there is no
`frameforge` package shadow to evict here.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tooling"))

import check_accessibility as A  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "accessibility.fg.yaml")


def _codes(findings):
    return {f.code for f in findings}


# --------------------------------------------------------------------------- #
#  The reference fixture is the live contract                                  #
# --------------------------------------------------------------------------- #
def test_reference_fixture_is_clean():
    findings = A.check_doc(A._load(FIXTURE))
    assert findings == [], "reference fixture should be a11y-clean:\n" + "\n".join(
        str(f) for f in findings)


def test_cli_exit_zero_on_reference_fixture():
    assert A.main([FIXTURE]) == 0


# --------------------------------------------------------------------------- #
#  Each rule fires at the right severity                                       #
# --------------------------------------------------------------------------- #
def test_dangling_reading_order_is_error():
    doc = {"pages": [{"mode": "page", "id": "p", "reading_order": ["ghost"],
                      "layers": [{"objects": [{"type": "text", "id": "real", "text": "hi"}]}]}]}
    fs = A.check_doc(doc)
    assert any(f.code == "A11Y-1" and f.severity == "ERROR" for f in fs)


def test_duplicate_reading_order_is_error():
    doc = {"pages": [{"mode": "page", "id": "p", "reading_order": ["a", "a"],
                      "layers": [{"objects": [{"type": "text", "id": "a", "text": "x"}]}]}]}
    fs = A.check_doc(doc)
    assert sum(1 for f in fs if f.code == "A11Y-1" and f.severity == "ERROR") >= 1


def test_image_without_alt_is_warn():
    doc = {"pages": [{"mode": "page", "id": "p", "reading_order": ["img"],
                      "layers": [{"objects": [{"type": "image", "id": "img", "src": "x.png"}]}]}]}
    fs = A.check_doc(doc)
    assert any(f.code == "A11Y-2" and f.severity == "WARN" for f in fs)


def test_decorative_image_needs_no_alt():
    doc = {"pages": [{"mode": "page", "id": "p", "reading_order": [],
                      "layers": [{"objects": [
                          {"type": "image", "id": "img", "src": "x.png", "decorative": True}]}]}]}
    assert "A11Y-2" not in _codes(A.check_doc(doc))


def test_image_with_actual_text_only_is_clean_for_a11y2():
    doc = {"pages": [{"mode": "page", "id": "p", "reading_order": ["img"],
                      "layers": [{"objects": [
                          {"type": "image", "id": "img", "src": "x.png", "actual_text": "C = A·B"}]}]}]}
    assert "A11Y-2" not in _codes(A.check_doc(doc))


def test_page_without_reading_order_is_warn():
    doc = {"pages": [{"mode": "page", "id": "p",
                      "layers": [{"objects": [{"type": "text", "id": "t", "text": "x"}]}]}]}
    assert "A11Y-3" in _codes(A.check_doc(doc))


def test_incomplete_reading_order_is_warn():
    doc = {"pages": [{"mode": "page", "id": "p", "reading_order": ["a"],
                      "layers": [{"objects": [
                          {"type": "text", "id": "a", "text": "x"},
                          {"type": "text", "id": "b", "text": "y"}]}]}]}
    assert "A11Y-4" in _codes(A.check_doc(doc))


def test_object_without_id_under_reading_order_is_warn():
    doc = {"pages": [{"mode": "page", "id": "p", "reading_order": ["a"],
                      "layers": [{"objects": [
                          {"type": "text", "id": "a", "text": "x"},
                          {"type": "text", "text": "no id"}]}]}]}
    assert "A11Y-4" in _codes(A.check_doc(doc))


def test_flow_pages_skip_reading_order_rules():
    # a flow section has no reading_order concept; only A11Y-2 (figure/image alt) applies
    doc = {"pages": [{"mode": "flow", "id": "s", "master": "m", "story": []}]}
    assert A.check_doc(doc) == []


# --------------------------------------------------------------------------- #
#  CLI exit code on a failing document                                         #
# --------------------------------------------------------------------------- #
def test_cli_exit_one_on_dangling(tmp_path):
    bad = tmp_path / "bad.fg.yaml"
    bad.write_text(
        "dsl: FrameForge\nversion: \"2.2.0\"\npages:\n"
        "  - mode: page\n    id: p\n    reading_order: [ghost]\n"
        "    layers:\n      - id: l\n        objects:\n"
        "          - { type: text, id: real, box: [0,0,10,10], text: hi }\n",
        encoding="utf-8")
    assert A.main([str(bad)]) == 1
