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
rendering `frameforge` package shadow — see test_head.py for the same dance.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tooling"))

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
    for t in ("uml.actor", "use", "component", "bar_chart"):
        assert t in blob, f"expected out-of-profile WARN to mention {t!r}"
    # connector is typed at HEAD (§3.11): it moved from the out-of-profile
    # superset into the core VisualObject union, so it must NOT be reported.
    assert "'connector'" not in blob, "typed connector must no longer be out-of-profile"


def test_model_only_aliases_are_info_not_error():
    findings = _findings()
    assert any(f.code == "model-only-alias" and "circle" in f.msg for f in findings)
    assert not any(f.sev == "ERROR" and "circle" in f.msg for f in findings)


# --------------------------------------------------------------------------- #
#  drift-risk-map #5 — per-object field drift is a hard error                  #
# --------------------------------------------------------------------------- #
def test_field_drift_is_a_hard_error_not_a_warn(monkeypatch):
    """A per-object field-name divergence in a CORE production must FAIL the gate
    (ERROR), not print a non-blocking WARN — else the normative grammar silently
    lies. The additive ObjBase fields (effects/appearance/humanize) are allowlisted;
    clearing the allowlist resurfaces them as drift, which must return as ERROR."""
    monkeypatch.setattr(CGS, "MODEL_ONLY_OBJ_FIELDS", frozenset())
    fd = [f for f in CGS.run_checks() if f.code == "field-drift"]
    assert fd, "expected field-drift once the additive-field allowlist is empty"
    assert all(f.sev == "ERROR" for f in fd), "field-drift must be ERROR-severity"


def test_no_unexpected_field_drift_in_current_tree():
    errs = [f.msg for f in CGS.run_checks() if f.code == "field-drift" and f.sev == "ERROR"]
    assert errs == [], "grammar ⇄ model field drift:\n" + "\n".join(errs)


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


# --------------------------------------------------------------------------- #
#  Expansion-tier authoring forms — the grammar must document them            #
# --------------------------------------------------------------------------- #
# `use`/`component`/`graph` are pre-expansion authoring objects: they appear in
# a .fg.yaml, are lowered to core geometry by sdk.expand, and never reach the
# validated document — so the model has no production for them and the core
# gate cannot force their presence. But they ARE part of the document format an
# author writes, so the grammar (the format's normative view) must document each
# as a VisualObject alternative with a production. This gate keeps a newly-added
# expansion form (like `graph`, roadmap item 1) from silently missing the
# grammar, the way it otherwise would.
EXPANSION_AUTHORING_TYPES = {
    "use": "UseObject",
    "component": "ComponentObject",
    "graph": "GraphObject",
}


def test_expand_dispatch_matches_the_documented_set():
    """The authoring types sdk.expand lowers are exactly the set the grammar
    is expected to document — so adding an expansion form without a grammar
    entry (or vice versa) trips this gate, not a silent doc drift."""
    import re
    expand_src = open(os.path.join(ROOT, "src", "frameforge", "sdk",
                                   "expand.py"), encoding="utf-8").read()
    dispatched = set(re.findall(r'kind == "([a-z_]+)"', expand_src))
    assert dispatched == set(EXPANSION_AUTHORING_TYPES), (
        f"sdk.expand dispatches {dispatched}, documented set is "
        f"{set(EXPANSION_AUTHORING_TYPES)} — update the grammar + this list "
        f"together")


def test_grammar_documents_every_expansion_authoring_form():
    prods = CGS.parse_productions(CGS.CORE_EBNF, CGS.STYLE_EBNF)
    obj_gram = CGS.grammar_type_map(prods, "VisualObject", "type")
    for type_tag, production in EXPANSION_AUTHORING_TYPES.items():
        assert type_tag in obj_gram, (
            f"expansion authoring type {type_tag!r} is not a VisualObject "
            f"alternative in the grammar")
        assert obj_gram[type_tag] == production, (
            f"{type_tag!r} maps to {obj_gram[type_tag]}, expected {production}")
        assert production in prods, f"no EBNF production for {production}"


def test_spec_lists_graph_among_extended_objects():
    spec = open(os.path.join(ROOT, "docs", "spec", "frameforge-v2-spec.md"),
                encoding="utf-8").read()
    assert "components/use/symbols/graphs" in spec, (
        "the spec's extended-objects list must include graphs")
    assert "pre-expansion authoring forms" in spec, (
        "the spec must explain that use/component/graph lower via sdk.expand")
