#!/usr/bin/env python3
"""test_sdk_error_conventions.py — library edge cases raise the module-typed error.

The SDK convention is a typed ``ValueError`` for out-of-domain input (e.g.
``sdk/layout.py`` `grid()` raises ``ValueError`` for `cols < 1`). Two helpers
diverged, raising a bare ``IndexError`` / ``ZeroDivisionError`` on plausible input;
these tests pin the convention.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

import pytest  # noqa: E402

from frameforge.sdk import ScalarField, VectorField  # noqa: E402
from frameforge.sdk.widgets import dropdown  # noqa: E402


def test_dropdown_rejects_an_out_of_range_selection():
    # e.g. a dropdown re-rendered after its item list shrank.
    with pytest.raises(ValueError):
        dropdown([0, 0, 120, 30], ["a", "b"], selected=5)


def test_dropdown_rejects_a_negative_selection():
    with pytest.raises(ValueError):
        dropdown([0, 0, 120, 30], ["a", "b"], selected=-1)


def test_dropdown_accepts_a_valid_selection():
    obj = dropdown([0, 0, 120, 30], ["a", "b"], selected=1)
    assert obj["type"] == "group"


def test_vector_field_render_rejects_zero_steps():
    vf = VectorField(lambda x, y: (x, y))
    with pytest.raises(ValueError):
        vf.render(box=[0, 0, 100, 100], steps_x=0)
    with pytest.raises(ValueError):
        vf.render(box=[0, 0, 100, 100], steps_y=0)


def test_scalar_field_heatmap_rejects_zero_steps():
    sf = ScalarField(lambda x, y: x + y)
    with pytest.raises(ValueError):
        sf.heatmap(box=[0, 0, 100, 100], steps_x=0)
