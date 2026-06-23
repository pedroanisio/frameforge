#!/usr/bin/env python3
"""
test_a11y_render.py — SVG accessibility emission (roadmap item 2, renderer half).

Asserts the renderer turns the accessibility vocabulary into SVG a11y markup:
document `lang` + `<title>`/`<desc>`, `role="img"` + `<title>`/`<desc>` for images
with alt/actual_text, and `aria-hidden` for decorative objects — while leaving
objects with no accessibility semantics byte-for-byte unwrapped.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tooling"))

import yaml  # noqa: E402
from render_fixtures import Renderer  # noqa: E402

FIXTURE = os.path.join(ROOT, "fixtures", "accessibility.fg.yaml")


def _render_fixture():
    doc = yaml.safe_load(open(FIXTURE, encoding="utf-8"))
    return Renderer(doc, ".").render_page(doc["pages"][0])[0]


def test_root_carries_lang_and_title():
    svg = _render_fixture()
    assert 'xml:lang="en"' in svg
    assert "<title>Accessibility demo</title>" in svg


def test_image_emits_role_alt_and_actual_text():
    svg = _render_fixture()
    assert 'role="img"' in svg
    assert "System architecture diagram" in svg          # alt -> <title> / aria-label
    assert "<desc>client to API to database</desc>" in svg  # actual_text -> <desc>


def test_reading_order_controls_page_dom_order():
    svg = _render_fixture()
    title_pos = svg.index("Accessible by construction")
    subtitle_pos = svg.index("alt text, actual_text")
    diagram_pos = svg.index("System architecture diagram")
    footer_pos = svg.index("FrameGraph v2")
    backdrop_pos = svg.index('aria-hidden="true"')
    assert title_pos < subtitle_pos < diagram_pos < footer_pos < backdrop_pos


def test_decorative_object_is_aria_hidden():
    assert 'aria-hidden="true"' in _render_fixture()


def test_role_alt_and_actual_text_wrap_non_image_objects():
    doc = {"pages": [{"mode": "page", "id": "p", "canvas": "deck-16x9",
                      "layers": [{"objects": [{"type": "rect", "role": "graphics-symbol",
                                               "box": [0, 0, 10, 10], "fill": "#000",
                                               "alt": "Black square",
                                               "actual_text": "a ten by ten black square"}]}]}]}
    svg = Renderer(doc, ".").render_page(doc["pages"][0])[0]
    assert 'role="graphics-symbol"' in svg
    assert '<title>Black square</title>' in svg
    assert '<desc>a ten by ten black square</desc>' in svg


def test_plain_object_is_not_wrapped():
    doc = {"pages": [{"mode": "page", "id": "p", "canvas": "deck-16x9",
                      "layers": [{"objects": [{"type": "rect", "box": [0, 0, 10, 10], "fill": "#000"}]}]}]}
    svg = Renderer(doc, ".").render_page(doc["pages"][0])[0]
    assert "aria-hidden" not in svg and 'role="img"' not in svg


def test_document_without_lang_or_title_omits_them():
    doc = {"pages": [{"mode": "page", "id": "p", "canvas": "deck-16x9", "layers": []}]}
    svg = Renderer(doc, ".").render_page(doc["pages"][0])[0]
    assert "xml:lang" not in svg
    assert "<title>" not in svg
