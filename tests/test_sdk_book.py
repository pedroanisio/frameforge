"""sdk.book — the Book composition API (roadmap item 8).

The semantic authoring layer above pages: ``BookBuilder`` composes front
matter + chapters/sections into ONE validated ``mode: flow`` document,
lowering through :class:`FlowBuilder`. Numbering is computed at build time
(§A.0: the SDK computes, the document receives literal numbered text — the
renderer has no counter engine): chapters ``1``, sections ``1.1``, figures
``Figure 2.1`` per chapter. ``keep_with_caption`` keeps a figure and its
caption on one page via the flow keep-group; every chapter opens on a new
page. Deterministic: same calls → identical document.

Runs under pytest or standalone (``uv run python tests/test_sdk_book.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from framegraph.sdk import BookBuilder, render_pages_with_stats  # noqa: E402
from framegraph.sdk.model import validate_document  # noqa: E402

LOREM = ("The quick brown fox jumps over the lazy dog and keeps running "
         "through the meadow toward the river, where the story continues "
         "for long enough to wrap across several lines of a book column. ")


def _demo_book(chapters=2, figures=True):
    book = BookBuilder(title="A Small Book", author="Test Author")
    for c in range(1, chapters + 1):
        ch = book.chapter(f"Chapter Title {c}")
        ch.para(LOREM * 4)
        sec = ch.section(f"First Section of {c}")
        sec.para(LOREM * 3)
        if figures:
            sec.figure({"type": "rect", "box": [0, 0, 320, 120],
                        "fill": "#0f7d88"},
                       caption=f"A teal plate in chapter {c}",
                       alt=f"teal rectangle {c}")
        sec2 = ch.section(f"Second Section of {c}")
        sec2.para(LOREM * 2)
    return book


# ── structure & numbering ───────────────────────────────────────────────


def _story(doc):
    flows = [p for p in doc["pages"] if p.get("mode") == "flow"]
    assert flows, "the book must lower to a flow section"
    return flows[0]["story"], flows[0]


def test_book_builds_a_validated_flow_document():
    doc = _demo_book().build()
    validate_document(doc)
    assert doc["title"] == "A Small Book"
    assert doc["profile"] == "book"


def test_chapters_and_sections_are_numbered_at_build_time():
    story, _ = _story(_demo_book().build())
    headings = [f for f in story if f["type"] == "heading"]
    texts = [h["text"] for h in headings]
    assert "1 · Chapter Title 1" in texts
    assert "1.1 · First Section of 1" in texts
    assert "2.2 · Second Section of 2" in texts
    lvl = {h["text"]: h["level"] for h in headings}
    assert lvl["1 · Chapter Title 1"] == 1
    assert lvl["2.2 · Second Section of 2"] == 2


def test_figures_number_per_chapter():
    story, _ = _story(_demo_book().build())
    figures = [f for f in story if f["type"] == "figure"]
    assert [f["caption"] for f in figures] == [
        "Figure 1.1 — A teal plate in chapter 1",
        "Figure 2.1 — A teal plate in chapter 2",
    ]


def test_figures_keep_with_caption_by_default():
    story, _ = _story(_demo_book().build())
    figures = [f for f in story if f["type"] == "figure"]
    for fig in figures:
        assert fig.get("break_inside") == "avoid", \
            "keep_with_caption: the figure block must not split"


def test_chapters_open_on_a_new_page():
    story, _ = _story(_demo_book().build())
    chapter_heads = [f for f in story if f["type"] == "heading"
                     and f["level"] == 1]
    assert all(h.get("break_before") == "page" for h in chapter_heads[1:]), \
        "every chapter after the first opens on a fresh page"


def test_toc_lists_the_heading_series():
    story, _ = _story(_demo_book(chapters=3).build())
    tocs = [f for f in story if f["type"] == "toc"]
    assert len(tocs) == 1
    first_chapter = next(f for f in story if f["type"] == "heading"
                         and f["text"].startswith("1 ·"))
    assert story.index(tocs[0]) < story.index(first_chapter), \
        "the TOC belongs to the front matter, before chapter 1"


def test_front_matter_carries_title_and_author():
    story, section = _story(_demo_book().build())
    joined = str(story)
    assert "A Small Book" in joined and "Test Author" in joined
    heading_texts = [f.get("text", "") for f in story
                     if f["type"] == "heading"]
    assert "A Small Book" not in heading_texts, \
        "the title is front-matter display — the book must not list itself " \
        "in its own contents"


def test_build_is_deterministic():
    assert _demo_book().build() == _demo_book().build()


def test_boxless_path_figures_get_a_derived_size():
    """A figure whose object carries no box (e.g. a stroke_outline path)
    must not silently reserve zero flow height and paint over the next
    block — the builder derives the bbox from the geometry."""
    book = BookBuilder(title="T")
    ch = book.chapter("C")
    ch.figure({"type": "path",
               "d": [["M", 10, 40], ["L", 200, 10], ["L", 300, 70], ["Z"]],
               "fill": "#111111"}, caption="swash")
    story, _ = _story(book.build())
    fig = next(f for f in story if f["type"] == "figure")
    assert fig.get("size"), "boxless geometry must get a derived size"
    w, h = fig["size"]
    assert w == pytest.approx(300) and h == pytest.approx(70)


# ── the render gate ─────────────────────────────────────────────────────


def test_book_paginates_and_renders_clean():
    doc = _demo_book(chapters=3).build()
    svgs, stats = render_pages_with_stats(doc, base_dir=str(ROOT))
    assert len(svgs) >= 4, "three chapters + front matter must paginate"
    assert stats.get("clipped", 0) == 0
    joined = "\n".join(svgs)
    assert "Figure 2.1" in joined, "numbered captions must reach the pixels"
    assert "1.1 · First Section of 1" in joined


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
