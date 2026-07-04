"""drift-risk-map #8 — the validator's hand-maintained type sets must equal the model.

`tooling/validate.py` keeps `CORE_OBJECT_TYPES` / `CORE_FLOW_TYPES` / `PURE_SHAPES`
/ `BOXLESS` as hand-written string sets that duplicate the model's discriminated
unions. Nothing linked them before, so adding an object type to the model but not
to these sets made the validator **silently under-validate** the new type (its
type-specific rules simply never ran). These tests cross-check the sets against
the authoritative unions the capability-manifest generator already extracts —
converting that silent gap into a loud test failure.
"""
from __future__ import annotations

import os
import sys

# The framegraph PACKAGE must own sys.modules, not the docs/models shadow module
# a prior test may have cached; evict the non-package binding and put src/ back in
# front, then lock the package in.
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import framegraph.sdk.model  # noqa: F401,E402  — lock the package

import gen_capability_manifest as G  # noqa: E402  (tooling/, via conftest)
import validate as V  # noqa: E402


def test_core_object_types_equal_the_model_object_union():
    assert set(V.CORE_OBJECT_TYPES) == set(G.model_object_types())


def test_core_flow_types_equal_the_model_flow_union():
    assert set(V.CORE_FLOW_TYPES) == set(G.model_flow_types())


def test_pure_shapes_and_boxless_are_subsets_of_the_model_types():
    obj, flow = set(G.model_object_types()), set(G.model_flow_types())
    assert set(V.PURE_SHAPES) <= obj, "PURE_SHAPES lists a non-object type"
    assert set(V.BOXLESS) <= (obj | flow), "BOXLESS lists an unknown type"
