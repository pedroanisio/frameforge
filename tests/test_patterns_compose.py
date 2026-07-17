"""frameforge.patterns.compose — filled patterns become v2 pages (issue #29).

The bridge over the #28 catalog: `compose(pattern_id, fill)` returns a full,
validated FrameForge document whose single page realizes the pattern — zone
boxes computed deterministically from the anchor vocabulary, treatments
(card fill/stroke/corner/accent-bar/label slot) applied from the pattern's
`enterprise_layout`, and content emitted per `content_type` as plain core
objects. The acceptance gate is the issue's own: every sidecared pattern's
committed `example_fill` composes, validates, and renders with **zero
uncontained text**.

Runs under pytest or standalone (``uv run python tests/test_patterns_compose.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from pydantic import ValidationError  # noqa: E402

from frameforge.patterns import compose, load_sidecars  # noqa: E402
from frameforge.sdk.model import validate_document  # noqa: E402

SIDECARS = load_sidecars()


def _texts(doc):
    out = []
    for layer in doc["pages"][0]["layers"]:
        for obj in layer["objects"]:
            if obj.get("type") == "text":
                out.append(str(obj.get("text", "")))
            if obj.get("type") == "bullet_list":
                out.extend(str(i) for i in obj.get("items", []))
    return "\n".join(out)


def test_swot_composes_to_a_validated_quadrant_page():
    doc = compose(10, SIDECARS[10].example_fill)
    validate_document(doc)
    page = doc["pages"][0]
    assert page["mode"] == "page"
    rects = [o for layer in page["layers"] for o in layer["objects"]
             if o.get("type") == "rect"]
    assert len(rects) >= 4                     # one card per quadrant at least
    text = _texts(doc)
    assert "STRENGTHS" in text and "THREATS" in text          # zone labels
    assert "Strong brand recognition in target segment" in text  # content


def test_bmc_object_items_render_their_labels():
    doc = compose(44, SIDECARS[44].example_fill)
    validate_document(doc)
    text = _texts(doc)
    fill = SIDECARS[44].example_fill
    first = fill["revenue_streams"][0]
    assert first["label"] in text and first["metric"] in text


def test_compose_is_deterministic():
    a = compose(10, SIDECARS[10].example_fill)
    b = compose(10, SIDECARS[10].example_fill)
    assert a == b


def test_bad_fill_is_rejected_before_any_layout():
    with pytest.raises(ValidationError):
        compose(10, {"strengths": ["ok"]})     # three required zones missing


def test_unknown_pattern_raises_keyerror():
    with pytest.raises(KeyError):
        compose(9999, {})


def test_every_sidecared_pattern_renders_with_no_uncontained_text():
    """The issue's acceptance gate, as a test: all 17 example fills compose,
    validate, and render through the real SVG proxy with zero text spilling a
    containing box."""
    from frameforge.sdk import render_pages_with_stats
    for pid, sidecar in sorted(SIDECARS.items()):
        doc = compose(pid, sidecar.example_fill)
        validate_document(doc)
        svgs, stats = render_pages_with_stats(doc, base_dir=str(ROOT))
        assert svgs, f"pattern {pid} rendered no pages"
        assert stats.get("uncontained", 0) == 0, (
            f"pattern {pid}: {stats.get('uncontained')} uncontained text object(s)")


def test_composed_pages_render_with_no_clipped_text():
    """Regression (book round): compose's page title and zone labels sat in
    boxes shorter than their line box (~1.35 default line-height) — every
    composed page counted clipped text objects. Single-line display slots
    pin line_height 1.0."""
    from frameforge.sdk import render_pages_with_stats
    doc = compose(10, {"strengths": ["Deterministic"],
                       "weaknesses": ["Proxy fonts"],
                       "opportunities": ["Corpus growth"],
                       "threats": ["Silent loss"]})
    _, stats = render_pages_with_stats(doc, base_dir=str(ROOT))
    assert stats.get("clipped", 0) == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
