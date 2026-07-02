#!/usr/bin/env python3
"""Bullet-list vertical spacing — items must never overlap.

Regression for the migrated-deck bug: bullet_lists carried a small authored
`gap` (0/1/2 px), and the proxy treated `gap` as the *total* line pitch
(`cy += gap`). Every item then stacked ~1-2px below the previous one and the
list collapsed into an unreadable smear — e.g.
out/render/b1_docusign-deck-v2.fg.json/p023.svg, where four 11px bullets landed
at y=185.12 / 187.12 / 189.12 / 191.12.

The renderer now floors the per-item advance at the line height (size*lh), so a
too-small gap can never cause overlap, while a deliberately large gap is still
honoured (the floor is a minimum, not a clamp).

Renderer-only import guard mirrors test_element_render.py (evict any models
module shadowing the `framegraph` rendering package).
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # a non-package (the models module)
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from tooling.render_fixtures import Renderer  # noqa: E402


def _item_baselines(items, *, gap, size):
    """Render a bullet_list and return the baseline y of each item's text run."""
    obj = {"type": "bullet_list", "items": list(items), "gap": gap,
           "box": [0, 0, 400, 400], "style": {"font_size": size}}
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [400, 400]},
                      "layers": [{"id": "l", "objects": [obj]}]}]}
    out = Renderer(doc, ".").render_page(doc["pages"][0])
    svg = "".join(out) if isinstance(out, list) else out
    ys = []
    for it in items:
        m = re.search(r'<text x="[\d.]+" y="([\d.]+)"[^>]*>' + re.escape(it) + r"</text>", svg)
        assert m, f"item {it!r} did not render a text run"
        ys.append(float(m.group(1)))
    return ys


def _text_runs(obj, canvas=(400, 400)):
    """Render one object and return every emitted text run as (x, y, size, content)."""
    doc = {"dsl": "FrameGraph", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": list(canvas)},
                      "layers": [{"id": "l", "objects": [obj]}]}]}
    out = Renderer(doc, ".").render_page(doc["pages"][0])
    svg = "".join(out) if isinstance(out, list) else out
    runs = []
    for m in re.finditer(
        r'<text x="([\d.]+)" y="([\d.]+)"[^>]*font-size:([\d.]+)px[^>]*>([^<]*)</text>', svg
    ):
        runs.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4)))
    return runs


def _deltas(ys):
    return [b - a for a, b in zip(ys, ys[1:])]


def test_tiny_gap_does_not_overlap():
    # The authored gap (2px) is far below one line. Pre-fix this produced a 2px
    # pitch (overlap); the line-height floor must advance each item by >= 1 line.
    size = 12
    ys = _item_baselines(["AAA", "BBB", "CCC"], gap=2, size=size)
    deltas = _deltas(ys)
    assert all(d >= size for d in deltas), f"bullets overlap with a tiny gap: deltas={deltas}"


def test_zero_gap_falls_back_to_default_pitch():
    # gap=0 is falsy -> the default pitch (size*1.5) applies; still no overlap.
    size = 10
    ys = _item_baselines(["one", "two", "three"], gap=0, size=size)
    deltas = _deltas(ys)
    assert all(d >= size for d in deltas), f"bullets overlap with a zero gap: deltas={deltas}"


def test_large_gap_is_honoured_not_clamped():
    # The floor is a minimum, not a clamp: a deliberately large gap must still
    # space items out by that amount.
    size = 12
    gap = 40
    ys = _item_baselines(["x", "y", "z"], gap=gap, size=size)
    deltas = _deltas(ys)
    assert all(abs(d - gap) < 0.5 for d in deltas), f"large gap not honoured: deltas={deltas}"


def test_long_item_wraps_within_box_width():
    # A long item must wrap to the box width instead of running off the side as a
    # single line (the amazon-proxy p003/p006 overflow: a 172-char bullet shot out
    # to x=857 in a 492-wide box). Every emitted line must fit, and the following
    # item must sit below all the wrapped lines.
    size = 10
    box_w = 200
    avg = 0.52  # the renderer's per-char advance estimate for a plain sans run
    long = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron"
    runs = _text_runs({"type": "bullet_list", "items": [long, "tail"], "gap": 4,
                       "box": [0, 0, box_w, 300], "style": {"font_size": size}})
    # marker runs sit at x=0; text runs are indented. Split them out.
    text_runs = [r for r in runs if r[0] > size]
    tail = [r for r in text_runs if r[3] == "tail"]
    assert tail, f"following item not rendered: {runs}"
    first_item_lines = [r for r in text_runs if r[1] < tail[0][1] and r[3] != "tail"]
    # the long item wrapped to more than one line ...
    assert len(first_item_lines) >= 2, f"long item did not wrap: {first_item_lines}"
    # ... and no wrapped line spills past the box's right edge ...
    for x, y, fs, content in first_item_lines:
        right = x + len(content) * fs * avg
        assert right <= box_w + 1, f"line overflows box width ({right:.1f} > {box_w}): {content!r}"
    # ... and the next item clears the last wrapped line (no overlap).
    last_line_y = max(r[1] for r in first_item_lines)
    assert tail[0][1] - last_line_y >= size, "following item overlaps the wrapped lines"
