#!/usr/bin/env python3
"""Author-intent escape hatches on the SDK.

Two context managers let an author declare intent the static rules already honour
(or are taught to honour), so dense art validates clean without per-object
boilerplate:

  * ``page.bleed()``     — stamps ``decorative=True`` on everything added in the
    block (the validator already exempts decorative objects from the containment
    and free-group overlap rules).
  * ``page.lettering()`` — stamps ``meta.role="lettering"`` on text added in the
    block, which the tabular-box-model heuristic skips (see test_validate.py).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder  # noqa: E402

CANVAS = {"size": [300, 300], "units": "px"}


def _page_objs(b):
    doc = b.build_dict(expand_reuse=False)
    return [o for ly in doc["pages"][0]["layers"] for o in ly.get("objects", [])]


def _fresh():
    b = DocumentBuilder(title="b", profile="diagram", lang="en")
    pg = b.page("p", canvas=CANVAS, coordinate_mode="absolute").layer("main")
    return b, pg


def test_bleed_marks_decorative_and_restores():
    b, pg = _fresh()
    with pg.bleed():
        pg.rect([-50, 0, 100, 100], fill="#000000")
        pg.line([0, 0], [10, 10], stroke="#000000")
    pg.rect([0, 0, 10, 10], fill="#ffffff")
    objs = _page_objs(b)
    assert objs[0].get("decorative") is True
    assert objs[1].get("decorative") is True
    assert objs[2].get("decorative") is None          # outside the block, untouched


def test_bleed_does_not_clobber_explicit_flag():
    b, pg = _fresh()
    with pg.bleed():
        pg.rect([0, 0, 10, 10], fill="#000000", decorative=False)
    assert _page_objs(b)[0].get("decorative") is False


def test_lettering_marks_text_only():
    b, pg = _fresh()
    with pg.lettering():
        pg.text([0, 0, 100, 20], "hi", style={"font_size": 12})
        pg.rect([0, 0, 10, 10], fill="#000000")
    objs = _page_objs(b)
    txt = next(o for o in objs if o["type"] == "text")
    rect = next(o for o in objs if o["type"] == "rect")
    assert txt["meta"]["role"] == "lettering"
    assert rect.get("meta") is None


def test_lettering_preserves_existing_meta():
    b, pg = _fresh()
    with pg.lettering():
        pg.text([0, 0, 50, 20], "x", style={"font_size": 12}, meta={"k": "v"})
    o = _page_objs(b)[0]
    assert o["meta"]["role"] == "lettering" and o["meta"]["k"] == "v"


def test_bleed_and_lettering_compose():
    b, pg = _fresh()
    with pg.bleed(), pg.lettering():
        pg.text([-10, 0, 100, 20], "x", style={"font_size": 12})
    o = _page_objs(b)[0]
    assert o["decorative"] is True and o["meta"]["role"] == "lettering"


def test_extend_under_bleed_is_stamped():
    b, pg = _fresh()
    with pg.bleed():
        pg.extend([{"type": "rect", "box": [0, 0, 10, 10], "fill": "#000000"}])
    assert _page_objs(b)[0].get("decorative") is True
