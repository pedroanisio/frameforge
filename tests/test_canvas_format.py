#!/usr/bin/env python3
"""
test_canvas_format.py — canvas resolution correctness for the pixel-perfect
campaign (docs/bhag-pixel-perfect-4k.md):

* DIM-1 — the screen resolution ladder (qhd/4k/uhd/8k) resolves, is visible in
  the model's PagePreset Literal + describe_capabilities, and an UNKNOWN preset
  name is loud (structured callback or stdlib warning) instead of silently
  substituting the 1280x800 default canvas.
* DIM-2 — CanvasObject.orientation swaps the preset width/height (landscape)
  and asserts portrait, per the model docstring.
* DIM-3 — CanvasObject.units mm/cm/in convert to px at CSS 96 dpi; pt/px stay
  1:1 per the documented renderer convention.
* NUMFMT — `fnum_precise` companion formatter (9 significant digits) exists
  without changing `fnum` semantics for existing call sites.

Package-side import (these live in the `frameforge` package) — evict a
models-module shadow first, per test_rendering_svg_semantics.py.
"""
import os
import sys
import typing
import warnings

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # the models module
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.mcp.discovery import describe_capabilities  # noqa: E402
from frameforge.rendering.domain.geometry import fnum, fnum_precise  # noqa: E402
from frameforge.rendering.domain.services.canvas_resolver import (  # noqa: E402
    CanvasResolver, DEFAULT_WH, PRESETS,
)

LADDER = {"qhd": (2560, 1440), "4k": (3840, 2160), "uhd": (3840, 2160), "8k": (7680, 4320)}


# --- DIM-1: screen resolution ladder ------------------------------------------ #
def test_screen_resolution_ladder_resolves():
    cr = CanvasResolver({})
    for name, wh in LADDER.items():
        assert cr.resolve({"canvas": name}) == wh
        assert cr.resolve({"canvas": {"preset": name}}) == wh


def test_ladder_present_in_model_literal():
    """The additive PagePreset entries keep the two drift gates true."""
    from models import frameforge as model
    literal = set(typing.get_args(model.PagePreset))
    assert set(LADDER) <= literal
    assert set(PRESETS) == literal


def test_ladder_visible_in_describe_capabilities():
    """describe_capabilities introspects the model live — no cached preset list."""
    presets = describe_capabilities("presets")["canvas_presets"]
    assert set(LADDER) <= set(presets)


# --- DIM-1: unknown preset must be loud ---------------------------------------- #
def test_unknown_preset_warns_via_stdlib_and_falls_back():
    cr = CanvasResolver({})
    with pytest.warns(UserWarning, match="unknown canvas preset 'nope'"):
        assert cr.resolve({"canvas": "nope"}) == DEFAULT_WH
    with pytest.warns(UserWarning, match="unknown canvas preset '4K-uhd'"):
        assert cr.resolve({"canvas": {"preset": "4K-uhd"}}) == DEFAULT_WH


def test_unknown_preset_reports_through_warn_callback():
    """With a renderer-shaped warn(kind, message, **details) sink, the event is
    structured and the stdlib channel stays quiet."""
    events = []
    cr = CanvasResolver({}, warn=lambda kind, message, **d: events.append((kind, message, d)))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert cr.resolve({"canvas": "nope"}) == DEFAULT_WH
    assert caught == []
    assert events and events[0][0] == "canvas_preset_unknown"
    assert events[0][2] == {"preset": "nope"}


def test_no_canvas_default_stays_silent():
    """DEFAULT_WH for the no-preset case is intended behavior — no warning."""
    cr = CanvasResolver({})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert cr.resolve({}) == DEFAULT_WH
        assert cr.resolve({"canvas": {}}) == DEFAULT_WH
    assert caught == []


# --- DIM-2: orientation -------------------------------------------------------- #
def test_orientation_landscape_swaps_portrait_preset():
    cr = CanvasResolver({})
    assert cr.resolve({"canvas": {"preset": "A4", "orientation": "landscape"}}) == (842, 595)
    assert cr.resolve({"canvas": {"preset": "9x16", "orientation": "landscape"}}) == (1920, 1080)


def test_orientation_portrait_asserts_portrait():
    cr = CanvasResolver({})
    assert cr.resolve({"canvas": {"preset": "16x9", "orientation": "portrait"}}) == (1080, 1920)
    assert cr.resolve({"canvas": {"preset": "4k", "orientation": "portrait"}}) == (2160, 3840)


def test_orientation_identity_when_already_matching():
    cr = CanvasResolver({})
    assert cr.resolve({"canvas": {"preset": "A4", "orientation": "portrait"}}) == (595, 842)
    assert cr.resolve({"canvas": {"preset": "16x9", "orientation": "landscape"}}) == (1920, 1080)
    # square presets have no direction to assert — identity either way
    assert cr.resolve({"canvas": {"preset": "square", "orientation": "landscape"}}) == (1080, 1080)


# --- DIM-3: physical units convert at CSS 96 dpi ------------------------------- #
def test_units_mm_converts_at_css_96dpi():
    cr = CanvasResolver({})
    w, h = cr.resolve({"canvas": {"size": [210, 297], "units": "mm"}})
    assert w == pytest.approx(210 * 96 / 25.4)   # 793.7008 px — A4 width
    assert h == pytest.approx(297 * 96 / 25.4)   # 1122.5197 px — A4 height


def test_units_cm_and_in_convert():
    cr = CanvasResolver({})
    assert cr.resolve({"canvas": {"size": [2.54, 2.54], "units": "cm"}}) == \
        pytest.approx((96.0, 96.0))
    assert cr.resolve({"canvas": {"size": [8.5, 11], "units": "in"}}) == \
        pytest.approx((816.0, 1056.0))


def test_units_pt_px_and_absent_stay_one_to_one():
    cr = CanvasResolver({})
    assert cr.resolve({"canvas": {"size": [595, 842], "units": "pt"}}) == (595, 842)
    assert cr.resolve({"canvas": {"size": [300, 200], "units": "px"}}) == (300, 200)
    assert cr.resolve({"canvas": {"size": [300, 200]}}) == (300, 200)


# --- NUMFMT: fnum_precise companion formatter ----------------------------------- #
def test_fnum_precise_keeps_multiplicative_precision():
    s = 3600 / 6100                       # 0.5901639... — the NUMFMT-1 worked example
    assert abs(float(fnum_precise(s)) - s) < 1e-8
    # a 4K-extent multiply of the round-trip error stays deep below a pixel
    assert abs(float(fnum_precise(s)) - s) * 6100 < 1e-4
    assert fnum_precise(0.99949) == "0.99949"     # fnum would collapse this to '1'


def test_fnum_precise_integers_compact():
    assert fnum_precise(3840) == "3840"
    assert fnum_precise(2.0) == "2"


def test_fnum_semantics_unchanged():
    assert fnum(0.5901639344262295) == "0.59"
    assert fnum(0.99950001) == "1"
    assert fnum(12) == "12"
