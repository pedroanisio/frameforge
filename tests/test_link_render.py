#!/usr/bin/env python3
"""
test_link_render.py — hyperlinks must be EMITTED, not just modelled.

Three surfaces:
* any visual object dict carrying ``href`` -> its rendered SVG is wrapped in
  ``<a href="...">`` (dict-level pass-through; the model field is owned by the
  schema layer),
* rich ``text.spans`` with a ``{"kind": "link"}`` inline -> the run's tspan is
  wrapped in ``<a href>`` on the single-line fast path,
* flow paragraphs whose ``spans`` contain a LinkInline -> the wrapped lines emit
  ``<a href>`` around the link words.

Renderer-only (no models import): evict a models-module shadow first — mirror of
the guard in test_element_render.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # a non-package (the models module)
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from tooling.render_fixtures import Renderer  # noqa: E402


def _page_svg(objects):
    doc = {"dsl": "FrameForge", "version": "2.2.0",
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [400, 200]},
                      "layers": [{"id": "l", "objects": objects}]}]}
    return Renderer(doc, ".").render_page(doc["pages"][0])[0]


def _flow_svgs(story):
    doc = {"dsl": "FrameForge", "version": "2.2.0",
           "pages": [{"mode": "flow", "id": "p", "canvas": {"size": [400, 300]},
                      "story": story}]}
    return Renderer(doc, ".").render_page(doc["pages"][0])


def test_object_href_wraps_in_anchor():
    svg = _page_svg([{"type": "rect", "box": [10, 10, 80, 40], "fill": "#123456",
                      "href": "https://example.com/docs"}])
    assert '<a href="https://example.com/docs">' in svg
    a_inner = svg.split('<a href="https://example.com/docs">', 1)[1]
    assert "<rect" in a_inner.split("</a>", 1)[0]


def test_object_without_href_is_unchanged():
    svg = _page_svg([{"type": "rect", "box": [10, 10, 80, 40], "fill": "#123456"}])
    assert "<a " not in svg


def test_text_span_link_emits_anchor_around_run():
    svg = _page_svg([{"type": "text", "box": [10, 10, 300, 24],
                      "spans": ["see ",
                                {"kind": "link", "href": "https://example.com",
                                 "content": ["the docs"]},
                                " for details"]}])
    assert '<a href="https://example.com">' in svg
    linked = svg.split('<a href="https://example.com">', 1)[1].split("</a>", 1)[0]
    assert "the docs" in linked
    assert "see" in svg and "for details" in svg


def test_flow_paragraph_link_emits_anchor():
    svgs = _flow_svgs([{"type": "paragraph",
                        "spans": ["Read ",
                                  {"kind": "link", "href": "https://example.com/spec",
                                   "content": ["the spec"]},
                                  " before writing code."]}])
    svg = "".join(svgs)
    assert '<a href="https://example.com/spec">' in svg
    linked = svg.split('<a href="https://example.com/spec">', 1)[1].split("</a>", 1)[0]
    assert "the" in linked and "spec" in linked
    assert "Read" in svg and "before" in svg


def test_flow_paragraph_without_links_unchanged():
    svgs = _flow_svgs([{"type": "paragraph", "text": "plain prose"}])
    assert "<a " not in "".join(svgs)


def test_flow_link_survives_wrapping():
    long_prefix = "word " * 40
    svgs = _flow_svgs([{"type": "paragraph",
                        "spans": [long_prefix,
                                  {"kind": "link", "href": "https://example.com/x",
                                   "content": ["linked words here"]},
                                  " " + "tail " * 20]}])
    svg = "".join(svgs)
    assert svg.count('<a href="https://example.com/x">') >= 1
    assert "linked" in svg and "tail" in svg


if __name__ == "__main__":
    test_object_href_wraps_in_anchor()
    print("OK")
