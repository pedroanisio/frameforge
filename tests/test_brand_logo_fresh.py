#!/usr/bin/env python3
"""
Brand logo masters must stay fresh against their generator.

`examples/framegraph_logo.py` owns the logo geometry and writes committed brand
masters. The generated SVG/YAML snapshots are user-facing assets, so stale output
must fail in the assertion suite instead of becoming silent repository drift.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_logo_module():
    path = ROOT / "examples" / "framegraph_logo.py"
    spec = importlib.util.spec_from_file_location("framegraph_logo_under_test", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_brand_logo_assets_match_fresh_build():
    logo = _load_logo_module()

    outputs = logo.build_outputs()

    assert logo.stale_outputs(ROOT / "brand", outputs) == []


def test_stale_outputs_detects_missing_and_changed_files(tmp_path):
    logo = _load_logo_module()
    outputs = {
        "framegraph-mark.svg": "<svg>fresh</svg>",
        "framegraph-logo.fg.yaml": "title: fresh\n",
    }

    (tmp_path / "framegraph-mark.svg").write_text("<svg>old</svg>", encoding="utf-8")

    assert sorted(logo.stale_outputs(tmp_path, outputs)) == [
        "framegraph-logo.fg.yaml",
        "framegraph-mark.svg",
    ]
