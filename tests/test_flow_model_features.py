#!/usr/bin/env python3
"""
test_flow_model_features.py — the four flow/inline features added to close the
gaps catalogued in fixtures/standard-model.fg.yaml's meta.provenance:

  * LinkInline      — inline hyperlink kind in the Inline union
  * FlowSection.links — section-level navigation (mirrors Page.links)
  * MathFlow.alt    — plain-text fallback for accessibility
  * FigureFlow.units — coordinate-unit declaration on a figure

Asserts the models accept them, the generated schema carries them, malformed
forms are rejected, and the authoritative fixture actually exercises each one
(the oracle — codebase-standards §6/§8).

Models-side import (models/ on sys.path); evict a rendering-package shadow
first, per test_head.py.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "models"))
sys.path.insert(0, os.path.join(ROOT, "schema"))
sys.path.insert(0, os.path.join(ROOT, "tooling"))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):   # the rendering package
    del sys.modules["framegraph"]

import pytest  # noqa: E402
import yaml  # noqa: E402
from pydantic import ValidationError  # noqa: E402

import framegraph as fg  # noqa: E402
import build_schema as B  # noqa: E402
import validate as V  # noqa: E402

FIXTURE = os.path.join(ROOT, "fixtures", "standard-model.fg.yaml")


# --- the models accept the new forms ----------------------------------------- #
def test_link_inline_parses_inside_a_paragraph():
    p = fg.ParagraphFlow.model_validate(
        {"type": "paragraph", "spans": ["see ",
         {"kind": "link", "href": "https://example.org", "content": ["here"], "title": "t"}]}
    )
    link = p.spans[1]
    assert isinstance(link, fg.LinkInline)
    assert link.href == "https://example.org" and link.content == ["here"]


def test_flow_section_links_math_alt_and_figure_units():
    section = fg.FlowSection.model_validate({
        "mode": "flow", "id": "s", "master": "m",
        "links": [{"to": "https://x", "relation": "next", "label": "n", "external": True}],
        "story": [
            {"type": "math", "tex": "a=b", "alt": "a equals b"},
            {"type": "figure", "units": "px", "size": [10, 10],
             "object": {"type": "rect", "box": [0, 0, 10, 10]}},
        ],
    })
    assert section.links[0].relation == "next"
    assert section.story[0].alt == "a equals b"
    assert section.story[1].units == "px"


# --- malformed forms are rejected (negative coverage) ------------------------ #
def test_link_inline_requires_href_and_content():
    with pytest.raises(ValidationError):
        fg.ParagraphFlow.model_validate(
            {"type": "paragraph", "spans": [{"kind": "link", "content": ["x"]}]})  # no href


def test_figure_units_rejects_unknown_unit():
    with pytest.raises(ValidationError):
        fg.FigureFlow.model_validate(
            {"type": "figure", "units": "furlongs", "size": [1, 1],
             "object": {"type": "rect", "box": [0, 0, 1, 1]}})


# --- the schema is generated in sync (codebase-standards §8) ------------------ #
def test_schema_carries_the_new_surface():
    schema = B.build()
    defs = schema["$defs"]
    assert "LinkInline" in defs
    assert "alt" in defs["MathFlow"]["properties"]
    assert "units" in defs["FigureFlow"]["properties"]
    assert "links" in defs["FlowSection"]["properties"]


# --- the authoritative fixture exercises every feature (the oracle) ----------- #
def test_standard_model_fixture_uses_all_four_features():
    doc = fg.Document.model_validate(yaml.safe_load(open(FIXTURE, encoding="utf-8")))
    section = doc.pages[0]
    assert isinstance(section, fg.FlowSection)

    # FlowSection.links
    assert section.links and any(l.relation == "source" for l in section.links)

    # LinkInline somewhere in the story's paragraph spans
    links = [s for fl in section.story if isinstance(fl, fg.ParagraphFlow)
             for s in (fl.spans or []) if isinstance(s, fg.LinkInline)]
    assert any(l.content == ["Enrico Fermi"] for l in links)

    # MathFlow.alt and FigureFlow.units
    assert any(isinstance(fl, fg.MathFlow) and fl.alt for fl in section.story)
    figs = [fl for fl in section.story if isinstance(fl, fg.FigureFlow)]
    assert figs and all(fl.units == "px" for fl in figs)
