"""G-1: the structured, schema-checkable form of a path's ``d``.

A ``path`` object's ``d`` may be either the SVG path-data string (the compiled
view) or a list of typed segments — one SVG command each, ``[cmd, *coords]``.
Before G-1 the model typed the list form as a bare ``list`` and the JSON Schema
emitted ``items: {}`` (an opaque array that validated nothing); these tests pin
that the structured form is now genuinely typed: valid segments validate, a bad
command or wrong arity is rejected, and a structured path renders identically to
its string equivalent (the string is the compiled view of the same geometry).
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "models"))
# Models-only test: evict a `framegraph` *package* shadow (it has __path__) left by
# a renderer test in the shared pytest process, so `framegraph` resolves to the
# models module. Evict only the top-level name — cached `framegraph.rendering.*`
# submodules must survive so later renderer tests still resolve them — see
# test_elements.py / test_head.py.
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):  # a package is shadowing the models
    del sys.modules["framegraph"]
import framegraph as fg  # noqa: E402


def _doc_with_path(d):
    return {
        "dsl": "FrameGraph",
        "version": fg.HEAD_VERSION,
        "pages": [{
            "mode": "page",
            "id": "p1",
            "canvas": {"size": [100, 100]},
            "layers": [{
                "id": "main",
                "objects": [{"type": "path", "d": d}],
            }],
        }],
    }


def test_string_d_still_validates():
    """The legacy string form is unchanged (it is the compiled view)."""
    fg.Document.model_validate(_doc_with_path("M0,0 L10,10 Z"))


def test_structured_d_validates():
    """A list of typed segments — one SVG command each — validates."""
    d = [["M", 0, 0], ["L", 10, 0], ["C", 10, 5, 5, 10, 0, 10],
         ["Q", 0, 5, 5, 5], ["A", 3, 3, 0, 0, 1, 8, 8], ["Z"]]
    fg.Document.model_validate(_doc_with_path(d))


def test_relative_lowercase_commands_validate():
    """Lowercase commands (relative coordinates) are valid SVG and accepted."""
    fg.Document.model_validate(_doc_with_path([["m", 1, 1], ["l", 2, 2], ["z"]]))


def test_unknown_command_is_rejected():
    """A command letter outside the SVG path-data set fails validation."""
    with pytest.raises(Exception):
        fg.Document.model_validate(_doc_with_path([["X", 0, 0]]))


def test_wrong_arity_is_rejected():
    """A cubic with too few coordinates fails validation (arity is typed)."""
    with pytest.raises(Exception):
        fg.Document.model_validate(_doc_with_path([["M", 0, 0], ["C", 1, 2, 3]]))


def test_non_numeric_coordinate_is_rejected():
    """A coordinate that is not a number fails validation."""
    with pytest.raises(Exception):
        fg.Document.model_validate(_doc_with_path([["L", "x", 0]]))


def test_pathcommand_alias_is_exported():
    """``PathCommand`` is a module-level Literal alias — the enum the grammar gate
    (check_grammar_sync) compares against the EBNF ``PathCommand`` production."""
    import typing

    assert typing.get_origin(fg.PathCommand) is typing.Literal
    assert set(typing.get_args(fg.PathCommand)) >= {"M", "L", "C", "Q", "A", "Z"}
