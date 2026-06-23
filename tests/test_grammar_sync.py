#!/usr/bin/env python3
"""
test_grammar_sync.py — coverage + contract for tooling/check_grammar_sync.py,
the gate that keeps the EBNF grammar a faithful view of the Pydantic models.

It asserts three things:
  1. the tree is actually in sync (no ERROR findings) — this is the live gate;
  2. the extractor/introspection helpers behave (so a silent extraction break
     can't make the gate pass vacuously);
  3. the deliberate out-of-profile superset and model-only aliases are reported
     at the right severities (WARN / INFO), not as ERRORs.

Models-side import: check_grammar_sync puts models/ on sys.path and evicts the
rendering `framegraph` package shadow — see test_head.py for the same dance.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tooling"))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):  # the rendering package
    del sys.modules["framegraph"]

import check_grammar_sync as CGS  # noqa: E402


def _findings():
    return CGS.run_checks()


# --------------------------------------------------------------------------- #
#  The live gate                                                              #
# --------------------------------------------------------------------------- #
def test_grammar_core_profile_in_sync():
    errs = [f for f in _findings() if f.sev == "ERROR"]
    assert not errs, "EBNF ⇄ model core drift:\n" + "\n".join(str(f) for f in errs)


def test_gate_exit_codes():
    # Default gate is green; --strict (full parity) fails on the out-of-profile
    # superset, proving the strict knob actually bites.
    assert CGS.main(["--quiet"]) == 0
    assert CGS.main(["--strict", "--quiet"]) == 1


# --------------------------------------------------------------------------- #
#  Severities of the deliberate divergences                                   #
# --------------------------------------------------------------------------- #
def test_out_of_profile_superset_is_warn():
    blob = "\n".join(f.msg for f in _findings() if f.code == "out-of-profile")
    for t in ("connector", "uml.actor", "use", "component", "bar_chart"):
        assert t in blob, f"expected out-of-profile WARN to mention {t!r}"


def test_model_only_aliases_are_info_not_error():
    findings = _findings()
    assert any(f.code == "model-only-alias" and "circle" in f.msg for f in findings)
    assert not any(f.sev == "ERROR" and "circle" in f.msg for f in findings)


# --------------------------------------------------------------------------- #
#  Extractor / introspection helpers                                          #
# --------------------------------------------------------------------------- #
def test_production_extraction():
    prods = CGS.parse_productions(CGS.CORE_EBNF, CGS.STYLE_EBNF)
    assert {"VisualObject", "RectObject", "Overflow", "TableObject"} <= set(prods)
    assert CGS.type_literal(prods["RectObject"]) == "rect"
    assert CGS.type_literal(prods["RefInline"], "kind") == "ref"


def test_enum_extraction_matches_model():
    prods = CGS.parse_productions(CGS.CORE_EBNF, CGS.STYLE_EBNF)
    assert CGS.enum_values(prods["Overflow"]) == {"visible", "hidden", "clip", "scroll", "auto"}
    # the cm fix is committed to the grammar:
    assert "cm" in CGS.enum_values(prods["Units"])


def test_mixin_expansion_resolves_table_and_common_fields():
    prods = CGS.parse_productions(CGS.CORE_EBNF, CGS.STYLE_EBNF)
    tfields = CGS.production_fields(prods, "TableObject")
    assert {"rows", "columns", "zebra", "cell_padding"} <= tfields   # via TableBody
    assert {"id", "box", "style"} <= tfields                          # via common-object-fields
