"""A collision report has to say WHICH text collided.

The detector keyed every record on the two objects' `id`s. Ids are optional, and
generated documents routinely omit them — a real 17-page spec reported 9
collisions as `ids: [None, None]`, which tells an author (or the LLM client that
emitted the document) that something overlaps but not what or where. An
unactionable signal is a silent failure with extra steps.

Each record now also carries the two ink rectangles and a short text excerpt, so
the offending objects are locatable with or without ids.
"""
from __future__ import annotations

from frameforge.rendering.application.renderer import Renderer


def _collisions(objects):
    doc = {"pages": [{
        "mode": "page", "id": "p", "canvas": {"size": [400, 200], "units": "px"},
        "layers": [{"id": "l", "objects": objects}],
    }]}
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    return r.diagnostics["collisions"]


OVERLAPPING = [
    {"type": "text", "box": [10, 10, 380, 60], "text": "Source ledger heading",
     "style": {"font_size": 14}},
    {"type": "text", "box": [10, 20, 380, 60], "text": "DISCLAIMER body text",
     "style": {"font_size": 14}},
]


def test_collision_locates_unidentified_objects():
    found = _collisions(OVERLAPPING)
    assert len(found) == 1
    c = found[0]
    assert c["ids"] == [None, None]                 # unchanged: ids stay optional
    # ...but the record is now actionable without them
    assert len(c["boxes"]) == 2
    for rect in c["boxes"]:
        assert len(rect) == 4
    assert "Source ledger" in c["texts"][0]
    assert "DISCLAIMER" in c["texts"][1]


def test_excerpts_are_bounded():
    long_text = "word " * 200
    found = _collisions([
        {"type": "text", "box": [10, 10, 380, 60], "text": long_text, "style": {"font_size": 14}},
        {"type": "text", "box": [10, 20, 380, 60], "text": long_text, "style": {"font_size": 14}},
    ])
    assert found, "expected a collision"
    for excerpt in found[0]["texts"]:
        assert len(excerpt) <= 60


def test_ids_are_still_reported_when_authored():
    found = _collisions([
        {**OVERLAPPING[0], "id": "ledger"},
        {**OVERLAPPING[1], "id": "disclaimer"},
    ])
    assert found[0]["ids"] == ["ledger", "disclaimer"]


def test_consented_overlap_is_still_not_reported():
    found = _collisions([
        {**OVERLAPPING[0], "overlap": "allowed"},
        {**OVERLAPPING[1], "overlap": "allowed"},
    ])
    assert found == []
