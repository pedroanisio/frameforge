#!/usr/bin/env python3
"""Story/flow authoring tests for the Python FrameForge SDK.

Covers the ``frameforge.sdk.flow`` builders (FlowBuilder + DocumentBuilder
``section``/``master`` wiring), the rich-inline additions to ``macros.md`` /
``macros.span``, and the span-list form of ``PageBuilder.text``. Every builder
must round-trip through the authoritative model (``DocumentBuilder.build``)
and, where cheap, through the SVG proxy renderer.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import (  # noqa: E402
    DocumentBuilder,
    FlowBuilder,
    MasterBuilder,
    md,
    render_page_svgs,
    span,
)
from frameforge.sdk.validate import validate_static_rules  # noqa: E402


def _builder_with_master() -> tuple[DocumentBuilder, MasterBuilder]:
    builder = DocumentBuilder(title="flow suite", profile="report")
    master = (
        builder.master("body", {"size": [400, 600], "units": "px"})
        .margin([40, 40, 40, 40])
        .region("main", [40, 40, 320, 500])
    )
    return builder, master


# --------------------------------------------------------------------------- #
#  FlowBuilder: one helper per Flowable type
# --------------------------------------------------------------------------- #
def test_flow_builder_covers_every_flowable_type():
    builder, master = _builder_with_master()
    photo = builder.define_asset("photo", "photo.png", kind="image")
    with builder.section("chapter", master=master.handle) as flow:
        flow.heading(1, "Chapter One", id="ch1")
        flow.para("Plain paragraph.")
        flow.bullet(["alpha", "beta"])
        flow.numbered(["first", "second"])
        flow.image(photo, alt="A photo", caption="Fig. 1")
        flow.figure({"type": "rect", "box": [0, 0, 80, 40], "fill": "#eee"},
                    caption="A rect", id="fig-rect")
        flow.code("print('hi')", "python")
        flow.math("e^{i\\pi} + 1 = 0", alt="Euler's identity")
        flow.table(["Name", "Qty"], [["bolt", 4], ["nut", 8]])
        flow.toc(of="headings", levels=[1, 2], title="Contents")
        flow.bibliography(title="References")
        flow.spacer(height=12)
        flow.page_break()
        flow.column_break()
        with flow.block(role="note", fill="#f6f6f6") as note:
            note.para("Inside a block.")
        with flow.keep_together() as keep:
            keep.heading(2, "Kept")
            keep.para("Kept with its heading.")

    doc = builder.build()
    section = doc.pages[0]
    assert section.mode == "flow" and section.master == "body"
    assert [item.type for item in section.story] == [
        "heading", "paragraph", "list", "list", "image", "figure", "code",
        "math", "table", "toc", "bibliography", "spacer", "page_break",
        "column_break", "block", "keep_together",
    ]
    # every Flowable variant is expressible → the union is fully helper-covered
    assert section.story[0].level == 1 and section.story[0].id == "ch1"
    assert section.story[2].ordered is None and section.story[3].ordered is True
    assert section.story[4].src == "photo" and section.story[4].caption == "Fig. 1"
    assert section.story[5].object.type == "rect"
    assert section.story[6].language == "python"
    assert section.story[8].header == ["Name", "Qty"]
    assert section.story[14].children[0].type == "paragraph"
    assert section.story[15].children[0].type == "heading"

    report = validate_static_rules(doc)
    errors = [issue for issue in report.issues if issue.severity == "error"]
    assert errors == []


def test_flow_builder_is_usable_standalone_with_flow():
    builder, master = _builder_with_master()
    story = FlowBuilder().heading(1, "T").para("Body.").story()
    builder.flow("s", master=master.handle, story=story)
    doc = builder.build()
    assert [item.type for item in doc.pages[0].story] == ["heading", "paragraph"]


def test_section_passes_flow_section_fields_through():
    builder, master = _builder_with_master()
    with builder.section("s", master=master.handle, media="paged",
                         meta={"kind": "chapter"}) as flow:
        flow.para("Body.")
    doc = builder.build()
    assert doc.pages[0].media == "paged"
    assert doc.pages[0].meta == {"kind": "chapter"}


def test_para_and_list_items_lower_markdown_inlines_to_spans():
    builder, master = _builder_with_master()
    with builder.section("s", master=master.handle) as flow:
        flow.para("plain text")
        flow.para("has **bold** words")
        flow.para([span("lead", bold=True), " tail"])
        flow.bullet(["plain", "with *emphasis*"])
    doc = builder.build()
    story = doc.pages[0].story
    assert story[0].text == "plain text" and story[0].spans is None
    bold = story[1].spans[1]
    assert bold.text == "bold" and bold.style.font_weight == "bold"
    assert story[2].spans[0].text == "lead"
    assert story[3].items[0] == "plain"
    emphasised = story[3].items[1].spans[1]
    assert emphasised.text == "emphasis" and emphasised.style.font_style == "italic"


# --------------------------------------------------------------------------- #
#  md() / span(): rich inline forms
# --------------------------------------------------------------------------- #
def test_md_lowers_bold_and_italic_to_styled_spans():
    parts = md("a **b** *c* `d`")
    assert parts == [
        "a ",
        {"text": "b", "style": {"font_weight": "bold"}},
        " ",
        {"text": "c", "style": {"font_style": "italic"}},
        " ",
        {"kind": "code", "text": "d"},
    ]


def test_md_keeps_existing_inline_forms_working():
    parts = md("see [docs](https://x.test) and {ref:fig-1}")
    assert parts[1] == {"kind": "link", "href": "https://x.test", "content": ["docs"]}
    assert parts[3] == {"kind": "ref", "target": "fig-1"}


def test_span_helper_builds_styled_spans_and_links():
    assert span("hi") == {"text": "hi"}
    assert span("hi", bold=True, italic=True, color="#c00") == {
        "text": "hi",
        "style": {"font_weight": "bold", "font_style": "italic", "color": "#c00"},
    }
    assert span("hi", font="Inter", size=14, letter_spacing=0.5) == {
        "text": "hi",
        "style": {"font_family": "Inter", "font_size": 14, "letter_spacing": 0.5},
    }
    linked = span("go", link="https://x.test", bold=True)
    assert linked == {
        "kind": "link",
        "href": "https://x.test",
        "content": [{"text": "go", "style": {"font_weight": "bold"}}],
    }


def test_page_text_accepts_span_lists():
    builder = DocumentBuilder()
    layer = builder.page("p", canvas={"size": [200, 100], "units": "px"}).layer("main")
    layer.text([10, 10, 180, 24], [span("Total: ", bold=True), "42"], id="t")
    doc = builder.build()
    obj = doc.pages[0].layers[0].objects[0]
    assert obj.text is None
    assert obj.spans[0].text == "Total: " and obj.spans[0].style.font_weight == "bold"
    assert obj.spans[1] == "42"


# --------------------------------------------------------------------------- #
#  MasterBuilder: regions, running content, footnote area
# --------------------------------------------------------------------------- #
def test_master_builder_lowers_full_page_master():
    builder = DocumentBuilder()
    master = (
        builder.master("chapter", {"size": [400, 600], "units": "px"})
        .margin([40, 40, 40, 40])
        .region("main", [40, 60, 320, 460], columns=2, column_gap=16, next="side")
        .region("side", [40, 530, 320, 30])
        .running_header([{"type": "text", "box": [40, 20, 320, 16], "text": "FrameForge"}])
        .running_footer([{"type": "rect", "box": [40, 570, 320, 1], "fill": "#ddd"}])
        .page_number(True)
        .footnote_area("notes", [40, 540, 320, 40])
        .fixed([{"type": "rect", "box": [0, 0, 400, 8], "fill": "#124"}])
    )
    with builder.section("s", master=master) as flow:
        flow.para("Body.")

    doc = builder.build()
    lowered = doc.defs.masters["chapter"]
    assert lowered.margin == [40, 40, 40, 40]
    assert [region.id for region in lowered.regions] == ["main", "side"]
    assert lowered.regions[0].columns == 2 and lowered.regions[0].next == "side"
    assert lowered.running.header[0].type == "text"
    assert lowered.running.footer[0].type == "rect"
    assert lowered.running.page_number is True
    assert lowered.footnote_area.id == "notes"
    assert lowered.fixed[0].fill == "#124"

    report = validate_static_rules(doc)
    assert not [issue for issue in report.issues if issue.severity == "error"]


def test_master_builder_region_cycle_still_caught_by_static_rules():
    builder = DocumentBuilder()
    master = (
        builder.master("loop", {"size": [200, 200], "units": "px"})
        .region("a", [10, 10, 80, 80], next="b")
        .region("b", [110, 10, 80, 80], next="a")
    )
    with builder.section("s", master=master) as flow:
        flow.para("Body.")
    report = validate_static_rules(builder.build())
    assert any(issue.rule_id == "reference-cycle" for issue in report.issues)


# --------------------------------------------------------------------------- #
#  render smoke: the lowered story paginates through the proxy renderer
# --------------------------------------------------------------------------- #
def test_flow_document_renders_and_paginates():
    builder, master = _builder_with_master()
    with builder.section("chapter", master=master.handle) as flow:
        flow.heading(1, "Render Smoke")
        flow.para("First page body copy.")
        flow.bullet(["one", "two"])
        flow.code("x = 1", "python")
        flow.page_break()
        flow.para("Second page body copy.")
    svgs = render_page_svgs(builder.build())
    assert len(svgs) >= 2
    assert "Render Smoke" in svgs[0]
    assert any("Second page body copy" in svg for svg in svgs)


# --------------------------------------------------------------------------- #
#  Running page furniture: master.fixed / running header+footer / page_number
#  (PageMaster.running + StringSet were schema-only — docs/models/frameforge.py
#  declared them, MasterBuilder already had .fixed/.running_header/
#  .running_footer/.page_number, but src/frameforge/rendering had ZERO
#  handling of them; grep across the whole rendering package turned up no
#  "running"/"fixed" reads at all. This is the renderer-side implementation.)
# --------------------------------------------------------------------------- #
def _running_builder_with_master() -> tuple[DocumentBuilder, MasterBuilder]:
    """A master carrying every furniture kind, authored through the SCHEMA's own
    substitution mechanism: `Text.field` (docs/models/frameforge.py:1081 —
    "Running field substitution: 'page'/'pages' counters, or the grammar's
    {string: <name>} form for named strings"). `field` REPLACES the object's
    `text`, so the authored `text` is only a placeholder and "page N of M" is
    composed from separate objects — the same shape the committed b1 oracles use
    (`{"text": "0", "field": "page"}` in ieee-reference-guide.fg.json). There is
    no `{{token}}` template convention: it appears nowhere in the model, the
    EBNF, or the spec.
    """
    builder = DocumentBuilder(title="running suite", profile="report")
    small = {"font_size": 9}
    master = (
        builder.master("body", {"size": [400, 600], "units": "px"})
        .margin([60, 40, 60, 40])
        .region("main", [40, 60, 320, 480])
        .fixed([{"type": "text", "box": [40, 10, 320, 16], "text": "FIXED LOGO",
                "style": {"font_size": 8}}])
        # running header: the named running string a heading's `set_string` sets.
        .running_header([{"type": "text", "box": [40, 30, 320, 16], "text": "CHAPTER",
                          "field": {"string": "chapter"}, "style": small}])
        # running footer: "page <n> of <total>" composed from the two counters.
        .running_footer([
            {"type": "text", "box": [40, 565, 34, 16], "text": "page", "style": small},
            {"type": "text", "box": [76, 565, 22, 16], "text": "0",
             "field": "page", "style": small},
            {"type": "text", "box": [100, 565, 20, 16], "text": "of", "style": small},
            {"type": "text", "box": [122, 565, 22, 16], "text": "0",
             "field": "pages", "style": small},
        ])
        .page_number(True)
    )
    return builder, master


def test_master_fixed_objects_appear_on_every_flow_page():
    builder, master = _running_builder_with_master()
    with builder.section("chapter", master=master.handle) as flow:
        flow.heading(1, "One", set_string=[{"name": "chapter"}])
        for i in range(30):
            flow.para(f"Body paragraph number {i} of chapter one, padded out to force a break.")
    svgs = render_page_svgs(builder.build())
    assert len(svgs) >= 2, "test needs >=2 pages to prove per-page furniture, not luck on page 1"
    for svg in svgs:
        assert "FIXED LOGO" in svg


def test_running_header_tracks_the_most_recent_set_string_heading():
    builder, master = _running_builder_with_master()
    with builder.section("chapter", master=master.handle) as flow:
        flow.heading(1, "Chapter One", set_string=[{"name": "chapter"}])
        for i in range(25):
            flow.para(f"Chapter one filler paragraph {i} to push the next heading onto a later page.")
        flow.heading(1, "Chapter Two", set_string=[{"name": "chapter"}])
        for i in range(25):
            flow.para(f"Chapter two filler paragraph {i}.")
    svgs = render_page_svgs(builder.build())
    assert len(svgs) >= 3, "test needs >=3 pages to prove the running header actually changes"
    # the placeholder must be substituted, not painted literally
    assert "CHAPTER" not in svgs[0]
    assert "Chapter One" in svgs[0]
    # the LAST page must show chapter two's running header — proves per-page
    # resolution against the dry-pass log, not a single static value baked
    # in once for the whole flow section
    assert "Chapter Two" in svgs[-1]


def test_page_number_and_total_are_correct_and_change_per_page():
    builder, master = _running_builder_with_master()
    with builder.section("chapter", master=master.handle) as flow:
        flow.heading(1, "One", set_string=[{"name": "chapter"}])
        # Digit-free body copy: every numeral in the rendered text is therefore a
        # counter that `field` substitution produced, never body content — which
        # is what makes the numeric assertions below unambiguous.
        for _ in range(40):
            flow.para("Padding paragraph to force several pages of flow content.")
    svgs = render_page_svgs(builder.build())
    n = len(svgs)
    assert n >= 3
    # the authored "0" placeholders must be substituted, never painted literally
    assert ">0<" not in svgs[0]
    for i, svg in enumerate(svgs):
        # `field: "page"` — each page shows its OWN number, not page 1's …
        assert f">{i + 1}<" in svg, f"page {i + 1} does not render its own page number"
        # … and `field: "pages"` shows the section total on every page.
        assert f">{n}<" in svg, f"page {i + 1} does not render the section total {n}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
