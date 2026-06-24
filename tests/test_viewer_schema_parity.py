#!/usr/bin/env python3
"""
test_viewer_schema_parity.py — P1 guard: the JS viewer covers every model type.

Closes drift-risk-map Finding #7. The browser viewer hand-mirrors the document
shape: `viewer/dev/fixture-coverage.mjs` hardcodes `ABSOLUTE_TYPES` / `FLOW_TYPES`
render-policy sets. Nothing asserted those sets cover the types the models define,
and the whole viewer CI job is `continue-on-error` (non-blocking) — so a new model
object/flow type would never fail CI; the viewer would just silently drop it.

This puts a **blocking** parity assertion in the main pytest gate (independent of
the non-blocking node job): every canonical, non-deprecated object/flow type the
models define must be declared by the viewer. The viewer's flow coverage is the
union of FLOW_TYPES and ABSOLUTE_TYPES (an object type embedded in a flow is
rendered via the absolute path — mirroring the `covered` check in the .mjs).

Known, pre-existing gaps in the work-in-progress viewer are listed explicitly in
``KNOWN_FLOW_GAPS`` so they are *documented* rather than silent; any NEW gap fails.
Finer-grained enum gaps the viewer still carries (e.g. `ref`/`cite`/`footnote`
inlines, `wrap`/`free` layout, `angular` dimension) live inside the JSX dispatch,
not in these declared sets, and are out of scope for this type-level guard.

Runs under pytest or standalone (`uv run python tests/test_viewer_schema_parity.py`).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(ROOT, "tooling"), os.path.join(ROOT, "models")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

import framegraph as fg  # noqa: E402
import check_grammar_sync as C  # noqa: E402

COVERAGE_MJS = os.path.join(ROOT, "viewer", "dev", "fixture-coverage.mjs")

# Deprecated renderer-shortcut aliases the codemod normalises away before a
# document reaches any renderer; the viewer need not declare them.
ALIAS = C.MODEL_ONLY_ALIAS_TYPES

# Flow types the WIP viewer does not yet render (silently no-ops). Documented here
# so they are visible and locked: a NEW unhandled type is a failure, these are not.
KNOWN_FLOW_GAPS = {"column_break", "keep_together"}


def _js_set(name):
    src = open(COVERAGE_MJS, encoding="utf-8").read()
    m = re.search(name + r"\s*=\s*new Set\(\[(.*?)\]\)", src, re.S)
    assert m, f"could not find `{name}` set in {os.path.relpath(COVERAGE_MJS, ROOT)} " \
              f"(was the viewer coverage file restructured?)"
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def _model_object_types():
    return set(C.model_type_map(fg.VisualObject, "type")) - ALIAS


def _model_flow_types():
    return set(C.model_type_map(fg.Flowable, "type"))


def test_viewer_covers_every_object_type():
    declared = _js_set("ABSOLUTE_TYPES")
    missing = sorted(_model_object_types() - declared)
    assert not missing, (
        f"viewer ABSOLUTE_TYPES is missing object types the models define: {missing}. "
        f"Add them to viewer/dev/fixture-coverage.mjs (and wire their render policy)."
    )


def test_viewer_covers_every_flow_type():
    declared = _js_set("FLOW_TYPES") | _js_set("ABSOLUTE_TYPES")
    missing = sorted(_model_flow_types() - declared - KNOWN_FLOW_GAPS)
    assert not missing, (
        f"viewer FLOW_TYPES is missing flow types the models define: {missing}. "
        f"Add them to viewer/dev/fixture-coverage.mjs, or to KNOWN_FLOW_GAPS if the "
        f"WIP viewer intentionally no-ops them."
    )


def test_known_gaps_are_real_and_minimal():
    """KNOWN_FLOW_GAPS must list only genuine, still-present gaps — so the allowlist
    shrinks as the viewer catches up instead of masking fixed types."""
    declared = _js_set("FLOW_TYPES") | _js_set("ABSOLUTE_TYPES")
    flow = _model_flow_types()
    for gap in KNOWN_FLOW_GAPS:
        assert gap in flow, f"KNOWN_FLOW_GAPS lists {gap!r} which is not a model flow type"
        assert gap not in declared, \
            f"{gap!r} is now declared by the viewer — drop it from KNOWN_FLOW_GAPS"


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
                failed += 1
    print(f"\n{'OK' if not failed else 'FAILED'} ({failed} failure(s))")
    sys.exit(1 if failed else 0)
