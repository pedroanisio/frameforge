#!/usr/bin/env python3
"""Render tests for the UmlRenderer sub-renderer (out-of-core UML zoo).

Exercises the extracted UML drawing routines through the Renderer's object
dispatch with the real dotted type names, asserting they draw genuine geometry
rather than the dashed out-of-profile placeholder.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.application.renderer import Renderer  # noqa: E402

PLACEHOLDER = 'stroke-dasharray="3 3"'   # the out-of-profile dashed stub marker


def _draw(o):
    return Renderer({}, ".").obj(o)


def test_classifier_box_draws_real_box_and_name():
    svg = _draw({
        "type": "uml.classifier_box", "box": [10, 10, 160, 90],
        "name": "Account", "attributes": ["+id: int"], "operations": ["+save()"],
    })
    assert '<rect x="10" y="10" width="160" height="90"' in svg
    assert 'fill="#fff"' in svg          # real fill, not the grey placeholder
    assert PLACEHOLDER not in svg
    assert "Account" in svg              # the classifier name is rendered


def test_lifeline_and_activation_bar_draw():
    life = _draw({"type": "uml.lifeline", "box": [200, 10, 40, 200], "name": "DB"})
    assert life and PLACEHOLDER not in life and "<rect" in life or "<line" in life

    bar = _draw({"type": "uml.activation_bar", "box": [210, 40, 20, 120]})
    assert bar.startswith("<") and PLACEHOLDER not in bar


def test_glyph_box_actor_draws():
    svg = _draw({"type": "uml.actor", "box": [10, 10, 40, 80], "name": "User"})
    assert svg and PLACEHOLDER not in svg
