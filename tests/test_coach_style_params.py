#!/usr/bin/env python3
"""Style-aware cleanup/redraw params — the clean/redraw stages obey the grammar.

``cleanup_params`` / ``redraw_params`` map a resolved StyleProfile onto the kwargs
the clean and redraw stages take, so a woodcut decimates differently than a
clean_line and the stroke weight comes from the style. Pure derivation (no
OpenCV); the kwargs feed coach.clean / coach.redraw unchanged.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from framegraph.coach import (  # noqa: E402
    STYLES, cleanup_params, clean, node_count, redraw, redraw_params, resolve_style,
)


def _arc(n=60, r=80.0):
    import math
    return [[r * math.cos(math.pi * i / (n - 1)), r * math.sin(math.pi * i / (n - 1))]
            for i in range(n)]


def test_cleanup_params_track_detail_and_edge():
    flat = cleanup_params(resolve_style("flat_icon"))      # low detail, clean_closed
    comic = cleanup_params(resolve_style("comic_ink"))     # high detail
    wood = cleanup_params(resolve_style("woodcut"))        # high detail, carved edge
    assert flat["eps"] > comic["eps"]                      # low detail simplifies harder
    assert flat["smooth"] > wood["smooth"]                 # clean_closed smooths > carved
    assert all("min_span" in p for p in (flat, comic, wood))


def test_redraw_params_take_weight_and_snap_from_style():
    blue = resolve_style("blueprint")
    comic = resolve_style("comic_ink")
    pb, pc = redraw_params(blue), redraw_params(comic)
    assert pb["width"] == blue.outer and pc["width"] == comic.outer
    assert pc["width"] > pb["width"]                       # comic ink is heavier
    assert redraw_params(resolve_style("flat_icon"))["snap"] is True   # clean_closed -> snap


def test_every_registered_style_yields_usable_kwargs():
    for name in STYLES:
        cp, rp = cleanup_params(resolve_style(name)), redraw_params(resolve_style(name))
        assert cp["eps"] > 0 and rp["simplify_tol"] > 0 and rp["width"] >= 0
        assert isinstance(rp["snap"], bool)


def test_params_drive_the_actual_stages():
    """The derived kwargs plug straight into clean() and redraw()."""
    objs = [{"type": "polyline", "points": _arc(), "stroke": "#000"}]
    cleaned = clean(objs, **cleanup_params(resolve_style("flat_icon")))
    assert node_count(cleaned) < node_count(objs)          # low-detail style simplified it
    drawn = redraw(objs, **redraw_params(resolve_style("comic_ink")))
    assert drawn[0]["type"] == "path"                      # redrawn to a curve
    assert drawn[0]["stroke_style"]["stroke_width"] == resolve_style("comic_ink").outer
