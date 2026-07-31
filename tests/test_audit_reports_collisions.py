"""`--to audit` must report overlapping text, not just contrast and type size.

The audit is the verification surface an author (or an LLM client) runs before
shipping a document. It lifted legibility signals into `health` but not text
collisions — so a 17-page spec whose cover ran two independent y-cursors over the
same band audited as merely "low contrast + small type" while the loudest defect,
five overlapping text blocks, went unmentioned. A verification surface that omits
the most visible failure class trains authors to trust a clean bill of health.
"""
from __future__ import annotations

from frameforge.rendering.application.audit import audit_document


DOC = {"dsl": "FrameForge", "version": "2.8.0", "pages": [{
    "mode": "page", "id": "cover", "canvas": {"size": [400, 200], "units": "px"},
    "layers": [{"id": "l", "objects": [
        {"type": "text", "box": [10, 10, 380, 60], "text": "Source ledger",
         "style": {"font_size": 14}},
        {"type": "text", "box": [10, 20, 380, 60], "text": "DISCLAIMER body",
         "style": {"font_size": 14}},
    ]}],
}]}

COLLISION = {"ids": [None, None], "page": "cover", "layer": 0, "area": 2408.0,
             "metrics": "estimate", "overlap": [152.9, 15.8],
             "boxes": [[10, 10, 390, 70], [10, 20, 390, 80]],
             "texts": ["Source ledger", "DISCLAIMER body"]}


def test_collisions_reach_the_health_list():
    report = audit_document(DOC, ["<svg></svg>"], collisions=[COLLISION])
    codes = [f["code"] for f in report["health"]]
    assert "text-collision" in codes
    flag = next(f for f in report["health"] if f["code"] == "text-collision")
    assert flag["level"] == "error"
    # locatable without ids: the message has to name the page and the text
    assert "cover" in flag["message"]
    assert "Source ledger" in flag["message"]


def test_collisions_are_kept_as_structured_data():
    report = audit_document(DOC, ["<svg></svg>"], collisions=[COLLISION])
    assert report["collisions"] == [COLLISION]


def test_no_collisions_is_a_present_empty_channel():
    """An empty list must mean "checked and clean", never "not checked"."""
    report = audit_document(DOC, ["<svg></svg>"], collisions=[])
    assert report["collisions"] == []
    assert [f for f in report["health"] if f["code"] == "text-collision"] == []


def test_audit_still_works_without_collision_data():
    report = audit_document(DOC, ["<svg></svg>"])
    assert report["collisions"] == []
