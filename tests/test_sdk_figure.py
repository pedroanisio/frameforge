#!/usr/bin/env python3
"""Tests for live FrameGraph figure imports."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (
    DocumentBuilder,
    FigureAsset,
    FigureProvenance,
    FigureRef,
    load_figure,
    place_figure,
    place_imported_figure,
    serialize,
)
from framegraph.sdk.validate import validate_static_rules


def _plate(builder: DocumentBuilder) -> int:
    page = builder.page("plate", canvas={"size": [200, 100], "units": "px"}, coordinate_mode="absolute")
    page.layer("bg").rect([0, 0, 200, 100], id="back", fill="#fff")
    page.layer("marks").text([10, 10, 80, 20], "Live", id="label")
    return 100


def test_load_figure_from_callable_selects_layers_and_canvas_box():
    ref = FigureRef.from_callable(_plate, page="plate")

    content = load_figure(ref, layers=["marks"])

    assert content.page_id == "plate"
    assert content.source_box == (0.0, 0.0, 200.0, 100.0)
    assert content.layers == ("marks",)
    assert [obj["id"] for obj in content.objects] == ["label"]


def test_place_figure_contain_alignment_prefixes_ids_and_marks_decorative():
    placement = place_figure(
        FigureRef.from_callable(_plate),
        [10, 20, 100, 100],
        fit="contain",
        align="top-left",
        id_prefix="fig1-",
    )

    transform = placement.group["style"]["transform"][0]["args"]
    assert transform == [0.5, 0.0, 0.0, 0.5, 10.0, 20.0]
    assert placement.drawn_box == (10.0, 20.0, 100.0, 50.0)
    assert placement.group["decorative"] is True
    assert [obj["id"] for obj in placement.group["children"]] == ["fig1-back", "fig1-label"]
    assert all(obj["decorative"] is True for obj in placement.group["children"])


def test_page_builder_figure_merges_source_defs_and_validates():
    source = DocumentBuilder()
    color = source.define_color("figure_blue", "#2563eb")
    plate = source.page("plate", canvas={"size": [80, 40], "units": "px"}).layer("main")
    plate.rect([0, 0, 80, 40], fill=color)

    target = DocumentBuilder()
    page = target.page("p", canvas={"size": [200, 120], "units": "px"}, coordinate_mode="absolute").layer("main")
    page.figure(FigureRef.from_builder(source, page="plate"), [20, 20, 160, 80])

    doc = target.build()
    assert doc.defs.tokens.colors["figure_blue"] == "#2563eb"
    report = validate_static_rules(doc)
    assert report.ok, report.issues


def test_figure_ref_from_path_imports_yaml(tmp_path):
    source = DocumentBuilder()
    source.page("plate", canvas={"size": [60, 30], "units": "px"}).layer("main").rect([0, 0, 60, 30], fill="#fff")
    path = tmp_path / "plate.fg.yaml"
    path.write_text(serialize(source.build(), format="yaml"), encoding="utf-8")

    content = FigureRef.from_path(path, page="plate").load()

    assert content.source_box == (0.0, 0.0, 60.0, 30.0)
    assert len(content.objects) == 1


def test_place_imported_figure_preserves_provenance_caption_and_geometry():
    asset = FigureAsset.from_pdf_image(
        "assets/biology-fig-1-1.jpg",
        source="openstax-biology-2e.pdf",
        page=29,
        box=[108, 157, 826, 443],
        id="bio-fig-1-1",
        number="1.1",
        caption="This NASA image is a composite of satellite-based views of Earth.",
        alt="Earth from space",
        intrinsic_size=[826, 443],
        license="CC-BY-4.0",
        attribution="Biology 2e, OpenStax, Rice University, CC BY 4.0",
        confidence=0.91,
        tags=["figure", "captioned"],
    )

    placement = place_imported_figure(
        asset,
        [20, 30, 300, 220],
        fit="contain",
        align="top-left",
        caption_height=48,
        id_prefix="import-",
    )

    group = placement.group
    figure_meta = group["meta"]["framegraph.figure"]
    image, caption = group["children"]
    assert group["id"] == "import-bio-fig-1-1"
    assert image["type"] == "image"
    assert image["box"] == pytest.approx([20.0, 30.0, 300.0, 160.89588377723972])
    assert image["decorative"] is False
    assert caption["text"].startswith("Figure 1.1. This NASA image")
    assert placement.caption_box == (20.0, 202.0, 300.0, 48.0)
    assert figure_meta["provenance"]["source"] == "openstax-biology-2e.pdf"
    assert figure_meta["provenance"]["page"] == 29
    assert figure_meta["provenance"]["box"] == [108.0, 157.0, 826.0, 443.0]
    assert figure_meta["provenance"]["license"] == "CC-BY-4.0"
    assert figure_meta["tags"] == ["figure", "captioned"]
    assert figure_meta["confidence"] == 0.91


def test_page_builder_imported_figure_lowers_to_valid_group():
    asset = FigureAsset(
        src="figures/alice-cover.jpg",
        id="alice-cover",
        intrinsic_size=[800, 1104],
        caption="Project Gutenberg EPUB cover image.",
        provenance=FigureProvenance(
            source="pg-alice.epub",
            format="epub",
            locator="OEBPS/wrap0000.xhtml",
            selector="svg image[xlink:href]",
            license="PD-US",
        ),
    )
    builder = DocumentBuilder()
    page = builder.page("p", canvas={"size": [360, 320], "units": "px"}, coordinate_mode="absolute").layer("main")

    page.imported_figure(asset, [24, 24, 180, 260], caption_position="below")

    doc = builder.build()
    obj = doc.pages[0].layers[0].objects[0]
    assert obj.type == "group"
    assert obj.meta["framegraph.figure"]["provenance"]["format"] == "epub"
    report = validate_static_rules(doc)
    assert report.ok, report.issues
