"""The builder must offer a backend the *structure* it walked, not just geometry.

Driving a backend through `ScenePainter` gives it every mark to paint, but the
SVG-era seam threw away two things a semantic backend needs and cannot rebuild:

* **layers** — `_render_page_body` concatenated each layer's output into one
  string, so a painter never learned where a layer started, what it was called,
  or what its `z` was. HTML's `<section class="fg-layer" data-layer=… data-z=…>`
  is unreconstructable from the flattened result.
* **object identity** — the authored `id` and `type` reached the painter only
  incidentally, through `a11y_wrap`, whose contract is accessibility. A backend
  needing `id="hero"` on the element had nowhere honest to read it.

Both are now explicit port seams (`layer_group`, `object_group`). Neither may
change what a geometric backend emits: SVG and TikZ implement them as identity
passthroughs, so the golden oracle is byte-for-byte unaffected — a structural
seam that alters paint would be a regression, not a feature.

These gates exist for the DRY/SOLID HTML backend: it is the first backend whose
output is *structure-bearing*, and without these seams porting it onto the shared
builder would trade 21 unsupported object types for a loss of semantic markup.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge_render.application.renderer import Renderer  # noqa: E402
from frameforge_render.domain.services.paint_resolver import ColorResolver  # noqa: E402
from frameforge_render.domain.services.text_style_resolver import (  # noqa: E402
    TextStyleResolver)
from frameforge_render.infrastructure.painters.svg import SvgPainter  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "b1", "mckinsey-7s.fg.json")


class RecordingPainter(SvgPainter):
    """A real, conformant painter that also records the structural seam calls.

    Subclassing the reference backend (rather than faking the whole port) keeps
    the document renderable, so these tests exercise the true builder path.
    """

    def __init__(self, color_resolver, warn=None):
        super().__init__(color_resolver, warn)
        self.layers: list[dict] = []
        self.objects: list[dict] = []

    def layer_group(self, inner, layer):
        self.layers.append(layer)
        return super().layer_group(inner, layer)

    def object_group(self, inner, obj):
        self.objects.append(obj)
        return super().object_group(inner, obj)


def _doc():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def _drive(doc, page=None):
    painter = {}

    def factory(color):
        painter["p"] = RecordingPainter(color)
        return painter["p"]

    renderer = Renderer(doc, ".", painter_factory=factory)
    out = "".join(renderer.render_page(page if page is not None else doc["pages"][0]))
    return painter["p"], out, renderer


# --------------------------------------------------------------------------- #
# The layer seam                                                               #
# --------------------------------------------------------------------------- #
def test_builder_offers_every_layer_through_the_layer_seam():
    doc = _doc()
    page = doc["pages"][0]
    expected = [L for L in page.get("layers") or []
                if L.get("role") != "construction"]
    assert expected, "fixture must have at least one paintable layer"

    painter, _out, _r = _drive(doc, page)

    assert len(painter.layers) == len(expected), (
        f"builder called layer_group {len(painter.layers)}x for "
        f"{len(expected)} layers — a semantic backend cannot rebuild the "
        "layer tree from a flattened string"
    )


def test_layer_seam_receives_the_authored_layer_identity():
    """`id`/`name` and `z` must survive — they are the DOM attributes HTML emits."""
    doc = _doc()
    painter, _out, _r = _drive(doc)

    for layer in painter.layers:
        assert isinstance(layer, dict), "layer_group must receive the layer node"
    names = {L.get("id") or L.get("name") for L in painter.layers}
    assert names - {None}, "no layer identity reached the painter"


def test_layers_are_offered_in_paint_order():
    """The seam must not disturb the z-sorted paint order the builder computed."""
    doc = _doc()
    painter, _out, _r = _drive(doc)
    zs = [L.get("z", 0) for L in painter.layers]
    assert zs == sorted(zs), f"layers reached the painter out of z order: {zs}"


# --------------------------------------------------------------------------- #
# The object-identity seam                                                     #
# --------------------------------------------------------------------------- #
def test_builder_offers_every_object_through_the_object_seam():
    doc = _doc()
    painter, _out, renderer = _drive(doc)
    assert renderer.skipped == 0, "fixture must render cleanly"
    assert painter.objects, "no object reached object_group"

    ids = [o.get("id") for o in painter.objects if isinstance(o, dict)]
    assert any(ids), "object identity never reached the painter"


def test_object_seam_includes_group_children():
    """Nested objects must be offered too, or HTML cannot nest its DOM."""
    doc = _doc()
    page = doc["pages"][0]
    top = [o for L in page.get("layers") or [] for o in L.get("objects") or []]
    groups = [o for o in top if isinstance(o, dict) and o.get("type") == "group"]
    assert groups, "fixture must contain a group to make this meaningful"

    painter, _out, _r = _drive(doc, page)
    assert len(painter.objects) > len(top), (
        f"object_group saw {len(painter.objects)} objects for {len(top)} "
        "top-level ones — group children were not offered"
    )


# --------------------------------------------------------------------------- #
# Structural seams must not alter paint                                        #
# --------------------------------------------------------------------------- #
def test_structural_seams_leave_svg_byte_identical():
    """SVG implements both seams as identity — the oracle must not shift."""
    doc = _doc()
    page = doc["pages"][0]
    plain = "".join(Renderer(doc, ".").render_page(page))
    recorded = "".join(
        Renderer(doc, ".", painter_factory=lambda c: RecordingPainter(c)).render_page(page))
    assert plain == recorded, (
        "the recording subclass changed SVG output — layer_group/object_group "
        "are not identity passthroughs on the SVG backend"
    )


# --------------------------------------------------------------------------- #
# Token provenance: the two token kinds a semantic backend re-materialises      #
# --------------------------------------------------------------------------- #
def test_resolved_text_style_carries_its_source_token_name():
    """A backend must be able to emit `.fg-ts-title`, not just inline font rules.

    The resolver flattens `style: "title"` into a literal dict; without the
    source name, CSS-class hoisting is impossible and every text object gets a
    duplicated inline style instead.
    """
    resolver = TextStyleResolver({"title": {"size": 32, "weight": 700}}, {},
                                 ColorResolver({}))
    st = resolver.resolve("title")
    assert st.get("style_ref") == "title", (
        "resolved style dropped its source token name — a backend cannot hoist "
        f"it to a class; got keys {sorted(st)}"
    )


def test_inline_style_dict_has_no_token_name():
    """An anonymous inline style has no token to name — it must not invent one."""
    resolver = TextStyleResolver({}, {}, ColorResolver({}))
    st = resolver.resolve({"size": 12})
    assert st.get("style_ref") is None


def test_color_resolver_maps_a_literal_back_to_its_token():
    """A backend must be able to emit `var(--fg-navy)` instead of `#14213f`."""
    resolver = ColorResolver({"navy": "#14213f", "ink": "#2b3a4f"})
    assert resolver.token_for("#14213f") == "navy"
    assert resolver.token_for("#2b3a4f") == "ink"
    assert resolver.token_for("#ff0000") is None


def test_token_reverse_map_is_case_insensitive_and_deterministic():
    """Authoring casing must not decide whether a token is recovered."""
    resolver = ColorResolver({"navy": "#14213F", "alias": "#14213f"})
    assert resolver.token_for("#14213f") == "navy", "first declared token wins"
    assert resolver.token_for("#14213F") == "navy"
