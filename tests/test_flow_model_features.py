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
sys.path.insert(0, os.path.join(ROOT, "docs", "schema"))
sys.path.insert(0, os.path.join(ROOT, "tooling"))

import pytest  # noqa: E402
import yaml  # noqa: E402
from pydantic import ValidationError  # noqa: E402

import frameforge.model as fg  # noqa: E402
import build_schema as B  # noqa: E402
import validate as V  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "standard-model.fg.yaml")


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
# The fixture contains out-of-profile `use` objects, so it is validated through
# the profile-aware validator (the real gate), not strict Document.model_validate;
# feature presence is then asserted on the raw story (codebase-standards §8).
def test_standard_model_fixture_validates_with_no_errors():
    _, _findings, rc = V.validate_doc(FIXTURE)
    assert rc == 0, [str(f) for f in _findings if f.severity == "ERROR"]


def test_standard_model_fixture_has_no_overlap_warnings():
    """Figure-internal drawing primitives are marked `decorative`, so the §3.3
    free-group no-overlap audit is clean; the only remaining notices are the
    inherent §8.5 out-of-profile symbol-reuse constructs (use / defs.symbols)."""
    _, findings, _ = V.validate_doc(FIXTURE)
    warn_codes = sorted({f.code for f in findings if f.severity == "WARN"})
    assert "overlap" not in warn_codes, \
        [str(f) for f in findings if f.code == "overlap"][:5]
    assert set(warn_codes) <= {"out-of-profile"}, warn_codes


def test_standard_model_fixture_uses_all_four_features():
    doc = yaml.safe_load(open(FIXTURE, encoding="utf-8"))
    section = doc["pages"][0]
    assert section["mode"] == "flow"
    story = section["story"]

    # FlowSection.links
    assert any(l.get("relation") == "source" for l in section.get("links", []))

    # LinkInline somewhere in a paragraph's spans
    link_contents = [s.get("content") for fl in story if fl.get("type") == "paragraph"
                     for s in (fl.get("spans") or [])
                     if isinstance(s, dict) and s.get("kind") == "link"]
    assert ["Enrico Fermi"] in link_contents

    # MathFlow.alt and FigureFlow.units (every figure declares units)
    assert any(fl.get("type") == "math" and fl.get("alt") for fl in story)
    figs = [fl for fl in story if fl.get("type") == "figure"]
    assert figs and all(fl.get("units") == "px" for fl in figs)
