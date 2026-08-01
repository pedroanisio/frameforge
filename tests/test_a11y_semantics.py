"""Unit gates for the derived-accessibility domain service.

The inference used to be private to the standalone HTML renderer, where it was
reachable only through a full document render. It is a pure function of one
object now, so its edge cases can be stated directly — which matters, because
the failure mode is silent: a wrong answer here does not crash, it just makes a
page worse for someone using a screen reader.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from frameforge_render.domain.services.a11y import (  # noqa: E402
    GEOMETRY_TYPES, derive_semantics, icon_label)


# --------------------------------------------------------------------------- #
# icon_label — a name only when the glyph reads as words                        #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("glyph,expected", [
    ("calendar", "calendar"),
    ("calendar-check", "calendar check"),
    ("calendar_check", "calendar check"),
    ("calendar check", "calendar check"),
    ("arrow2", "arrow2"),
    ("box-3d-front", "box 3d front"),
])
def test_word_glyphs_become_readable_names(glyph, expected):
    assert icon_label(glyph) == expected


@pytest.mark.parametrize("glyph", [
    "★", "→", "", "", "   ", "✓", "1234", "-leading", "??",
    None, 42, ["calendar"],
])
def test_non_word_glyphs_have_no_usable_name(glyph):
    """Announcing a raw symbol is worse than staying silent."""
    assert icon_label(glyph) is None


# --------------------------------------------------------------------------- #
# derive_semantics                                                             #
# --------------------------------------------------------------------------- #
def test_group_is_a_grouping():
    assert derive_semantics({"type": "group"}) == {"role": "group", "label": None}


@pytest.mark.parametrize("otype", sorted(GEOMETRY_TYPES))
def test_bare_geometry_is_hidden(otype):
    assert derive_semantics({"type": otype}) == {"hidden": True}


def test_named_icon_is_an_image_with_a_name():
    assert derive_semantics({"type": "icon", "glyph": "calendar-check"}) == {
        "role": "img", "label": "calendar check"}


def test_symbol_icon_is_hidden_rather_than_mislabelled():
    assert derive_semantics({"type": "icon", "glyph": "★"}) == {"hidden": True}


def test_icon_without_a_glyph_is_hidden():
    assert derive_semantics({"type": "icon"}) == {"hidden": True}


def test_labelled_image_is_announced_as_an_image():
    """`ImageObject.label` is the model's name for an image; it must reach AT.

    The model spells this `label`, not `alt`, so the authored-field path in the
    painters does not pick it up — without this the placeholder rendered a
    visible caption that no screen reader could attribute to a graphic.
    """
    assert derive_semantics({"type": "image", "label": "Team photo"}) == {
        "role": "img", "label": "Team photo"}


def test_unlabelled_image_gets_no_opinion():
    """An unnamed image is not automatically decorative — the author may simply
    not have named it yet, and hiding real content is worse than leaving it."""
    assert derive_semantics({"type": "image"}) is None
    assert derive_semantics({"type": "image", "label": "  "}) is None


@pytest.mark.parametrize("obj", [
    {"type": "rect"}, {"type": "text"}, {"type": "table"},
    {"type": "uml.classifier_box"}, {"type": "unknown-future-type"},
])
def test_types_with_no_implied_semantics_return_none(obj):
    """Silence is the correct answer — the backend then emits nothing extra."""
    assert derive_semantics(obj) is None


@pytest.mark.parametrize("glyph", ["x", "a", "7"])
def test_single_character_glyphs_are_not_names(glyph):
    """A lone character is a symbol, not a word — announcing it is noise.

    (The standalone renderer rejected anything under three characters. Two-letter
    words like "ok" and "up" are legitimate names, so the floor is one character,
    and this is a deliberate widening of the old rule.)
    """
    assert icon_label(glyph) is None


@pytest.mark.parametrize("glyph", ["ok", "up", "no"])
def test_two_letter_words_are_names(glyph):
    assert icon_label(glyph) == glyph


@pytest.mark.parametrize("obj", [None, "line", 7, [], {"no": "type"}, {"type": 3}])
def test_malformed_input_is_answered_with_none_not_an_exception(obj):
    """This runs inside a render; raising here would cost a whole page."""
    assert derive_semantics(obj) is None


def test_service_states_no_backend_opinion():
    """The result is neutral data — no markup, no SVG or HTML vocabulary."""
    result = derive_semantics({"type": "group"})
    assert set(result) <= {"role", "label", "hidden"}
    assert "<" not in str(result)
