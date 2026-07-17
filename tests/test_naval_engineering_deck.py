#!/usr/bin/env python3
"""Regression tests for the SDK demo deck in ``examples/naval_engineering_deck.py``.

The demo is a worked exercise of the public SDK drawing surface (DocumentBuilder,
Frame, Path, Scene3D). These tests pin three things:

  * it builds a 30-page document that validates with zero rule *errors*;
  * building it twice is deterministic (the page counter must reset); and
  * every page — including the Scene3D isometric block — rasterises through the
    proxy renderer to non-trivial SVG (guards the Scene3D box-local regression).
"""
from __future__ import annotations

import importlib.util
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk.conform import render_page_svgs  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402


def _load_demo():
    path = os.path.join(ROOT, "static", "examples", "naval_engineering_deck.py")
    spec = importlib.util.spec_from_file_location("naval_engineering_deck", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DEMO = _load_demo()


def test_demo_deck_builds_and_validates():
    doc = DEMO.build_deck().build()
    assert len(doc.pages) == DEMO.TOTAL_PAGES == 30

    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    assert not errors, f"unexpected validation errors: {errors[:5]}"
    assert report.ok


def test_demo_deck_build_is_deterministic():
    """Repeated builds must be byte-identical — the page counter has to reset."""
    first = DEMO.build_deck().build().model_dump(by_alias=True, exclude_none=True)
    second = DEMO.build_deck().build().model_dump(by_alias=True, exclude_none=True)
    assert first == second
    # the last page number really did reset to the deck size, not 60
    assert DEMO._page_no == DEMO.TOTAL_PAGES


def test_demo_deck_renders_every_page_nonblank():
    doc = DEMO.build_deck().build()
    svgs = render_page_svgs(doc, base_dir=ROOT)
    assert len(svgs) == DEMO.TOTAL_PAGES
    # every page carries real geometry, not just a background rect
    for idx, svg in enumerate(svgs, 1):
        assert svg.lstrip().startswith("<svg"), f"page {idx} is not an SVG"
        assert svg.count("<") > 20, f"page {idx} rendered nearly empty"


def test_demo_scene3d_block_renders_inside_canvas():
    """The isometric hull block must land inside the page (Scene3D box-local fix)."""
    import re

    doc = DEMO.build_deck().build()
    # locate the page that carries the Scene3D group by its id
    page_idx = next(
        i for i, page in enumerate(doc.pages)
        for layer in (page.layers or [])
        for obj in (layer.objects or [])
        if getattr(obj, "id", None) == "hull_block"
    )
    svg = render_page_svgs(doc, base_dir=ROOT)[page_idx]
    # The proxy positions the group with an SVG translate and emits the faces as
    # local points inside it. Combine the two to recover absolute coordinates: the
    # old double-offset bug pushed these past the right edge of the 1280-wide page.
    tx, ty = (float(v) for v in
              re.search(r"translate\(([-\d.]+),([-\d.]+)\)", svg).groups())
    local = [tuple(map(float, m.split(",")))
             for pts in re.findall(r'points="([^"]+)"', svg)
             for m in pts.split()]
    assert local, "no Scene3D faces rendered"
    absolute = [(tx + x, ty + y) for x, y in local]
    # the panel sits on the right half of the canvas, fully on-page
    assert all(600 < x <= DEMO.W and 0 <= y <= DEMO.H for x, y in absolute)
