#!/usr/bin/env python3
"""Story/flow authoring tests for the Python FrameGraph SDK.

Covers the ``framegraph.sdk.flow`` builders (FlowBuilder + DocumentBuilder
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
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    FlowBuilder,
    MasterBuilder,
    md,
    render_page_svgs,
    span,
)
from framegraph.sdk.validate import validate_static_rules  # noqa: E402


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
        .running_header([{"type": "text", "box": [40, 20, 320, 16], "text": "FrameGraph"}])
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
