#!/usr/bin/env python3
"""
test_schema_descriptions.py — the generated schema must be self-describing.

The JSON Schema is the machine-readable contract agents consume; a schema whose
properties carry no `description` forces every consumer back into the EBNF
comments and spec prose. This gate asserts:

  1. COVERAGE — >= 95% of all properties across `$defs` (and the document root)
     carry a non-empty `description`. New fields without one fail here.
  2. KEY SEMANTICS VERBATIM — a handful of load-bearing descriptions (units,
     +y-down coordinates, the text-XOR-spans invariant, sizing modes, font
     pinning, connector endpoints) are asserted exactly, so a careless rewording
     that drops the invariant fails loudly.

Runs against a FRESH build from the models (the source of truth); the separate
`schema-check` gate keeps the committed file byte-identical to that build.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [os.path.join(ROOT, "docs", "models"), os.path.join(ROOT, "docs", "schema")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):  # the rendering package
    del sys.modules["framegraph"]

import build_schema as B  # noqa: E402

SCHEMA = B.build()
MIN_COVERAGE = 0.95


def _properties(schema):
    """Yield (path, property-node) for every property in $defs and the root."""
    for name, d in schema.get("$defs", {}).items():
        for pname, node in (d.get("properties") or {}).items():
            yield f"$defs.{name}.{pname}", node
    for pname, node in (schema.get("properties") or {}).items():
        yield f"(root).{pname}", node


def test_schema_property_description_coverage():
    total, missing = 0, []
    for path, node in _properties(SCHEMA):
        total += 1
        if not (isinstance(node, dict) and node.get("description")):
            missing.append(path)
    assert total > 500, f"schema shrank unexpectedly ({total} properties)"
    coverage = (total - len(missing)) / total
    assert coverage >= MIN_COVERAGE, (
        f"schema description coverage {coverage:.1%} < {MIN_COVERAGE:.0%}; "
        f"undescribed: {missing[:25]}{' …' if len(missing) > 25 else ''}"
    )


def _desc(model, prop):
    return SCHEMA["$defs"][model]["properties"][prop].get("description")


def test_text_xor_spans_invariant_is_stated():
    assert _desc("Text", "text") == "Plain text content; exactly one of `text` or `spans` (XOR)."
    assert _desc("Text", "spans") == "Styled inline runs; exactly one of `text` or `spans` (XOR)."


def test_box_states_coordinate_convention():
    d = _desc("Rect", "box")
    assert d == ("Placement box [x, y, w, h], parent-local, +y down; under row/column/grid "
                 "layout the authored x/y are replaced by computed positions (§3.6).")


def test_length_string_branch_states_units_and_contexts():
    # The Box alias' items carry the Length union; its string branch must name
    # the enforced unit set and the %/fr resolution contexts.
    box = SCHEMA["$defs"]["Rect"]["properties"]["box"]
    arr = box["anyOf"][0] if "anyOf" in box else box
    str_branch = [b for b in arr["items"]["anyOf"] if b.get("type") == "string"][0]
    assert str_branch["description"] == (
        "Length string: '<n><unit>' with unit pt|px|pc|mm|cm|in|em|rem (absolute; "
        "bare numbers are pt/px, treated 1:1) or %|fr (relative — % resolves against "
        "the container content-box, fr only inside a layout container; spec §3.4/§3.6g).")
    assert str_branch.get("pattern"), "Length string branch lost its unit pattern"


def test_sizing_modes_are_explained():
    assert _desc("Sizing", "width") == ("Width mode: fixed (authored box), hug (measure content; "
                                        "invalid on pure shapes), fill (share container free space).")


def test_font_pinning_semantics_are_stated():
    assert _desc("FontDef", "hash") == ("Content hash of `src`; src+hash = a PINNED font, required "
                                        "for content-sized text (§9.6 determinism).")


def test_connector_endpoint_shape_is_stated():
    assert _desc("Connector", "from") == ("Start endpoint: [x, y] point or "
                                          "{ref|object, port|side, offset, point}.")


def test_gradient_stop_position_states_offset_normalisation():
    assert _desc("GradientStop", "position") == (
        "Stop position along the gradient line (length or '<n>%'); authoritative key — "
        "the legacy `offset` (incl. 0..1 unit-interval numbers) is accepted and "
        "normalised to `position`.")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("OK")
