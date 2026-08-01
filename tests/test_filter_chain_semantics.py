#!/usr/bin/env python3
"""Stacked self-contained filter preset semantics (GitHub #80 Option 1)."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "docs")]

from frameforge.mcp.discovery import describe_capabilities  # noqa: E402
from frameforge.mcp.guide import FRAMEFORGE_GUIDE  # noqa: E402
from frameforge_sdk import DocumentBuilder, displacement_map, filter_chain, style_effects, turbulence, validate_static_rules  # noqa: E402
from frameforge.conform import render_page_svgs


def _document(*filters):
    builder = DocumentBuilder(title="Filter presets", profile="diagram")
    layer = builder.page(
        "p1",
        canvas={"size": [180, 100], "units": "px"},
        coordinate_mode="absolute",
    ).layer("main")
    layer.rect(
        [20, 20, 120, 50],
        fill="#336699",
        **style_effects(filter=filter_chain(*filters)),
    )
    return builder.build()


def test_mixed_primitive_presets_warn_with_the_named_displacement_idiom():
    document = _document(
        turbulence(base_frequency=0.08, seed=18497, opacity=0.3),
        displacement_map(scale=16),
    )

    report = validate_static_rules(document, text_fit=False)
    warnings = [issue for issue in report.issues if issue.rule_id == "filter-chain-presets"]
    assert report.ok is True
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning.severity == "warning"
    assert warning.path == "/pages/0/layers/0/objects/0/style/filter"
    assert "stacked self-contained presets" in warning.message
    assert "put base_frequency, num_octaves, seed, and type on displacement_map" in warning.message
    assert "do not prepend turbulence" in warning.message

    single = validate_static_rules(
        _document(displacement_map(scale=16, base_frequency=0.08, seed=18497)),
        text_fit=False,
    )
    assert not [issue for issue in single.issues if issue.rule_id == "filter-chain-presets"]


def test_renderer_contract_remains_two_stacked_self_contained_presets():
    svg = render_page_svgs(
        _document(
            turbulence(base_frequency=0.08, seed=18497, opacity=0.3),
            displacement_map(scale=16),
        )
    )[0]

    assert svg.count("<filter ") == 2
    assert svg.count('<g filter="url(#fx') == 2
    assert 'baseFrequency="0.08"' in svg
    assert 'seed="18497"' in svg
    assert '<feBlend in="SourceGraphic" in2="texture" mode="multiply"/>' in svg
    assert '<feDisplacementMap in="SourceGraphic" in2="noise" scale="16"' in svg


def test_filter_chain_semantics_are_visible_in_sdk_model_discovery_and_guide():
    sentence = "stacked self-contained presets"
    assert sentence in (inspect.getdoc(filter_chain) or "")
    description = describe_capabilities("style")["properties"]["filter"]["description"]
    assert sentence in description
    assert sentence in FRAMEFORGE_GUIDE
