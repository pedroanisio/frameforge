#!/usr/bin/env python3
"""test_viewer_schema_contract.py — blocking guard, drift-risk-map Finding C7.

The JS viewer hand-mirrors the document model (it dispatches on object ``type``,
flow ``type``, and inline ``kind`` with hardcoded branches) and its CI job is
``continue-on-error``. Nothing asserted that the set of types the viewer knows
equals the set the model defines, so a new model type shipped a viewer that
silently dropped or mis-rendered it.

This puts the viewer↔model contract in the *blocking* pytest suite, independent
of the non-blocking viewer job. It reconciles the viewer's declared surface
(``viewer/dev/type-registry.json``) against the model's discriminators read from
``schema/frameforge-v2.schema.json`` — which ``schema-check`` already keeps
byte-exact to ``models/frameforge.py``. So a model change that is not reflected
in the registry becomes a ``test-failure`` here. The Node gate
``viewer/dev/schema-contract.mjs`` enforces the identical contract for viewer
developers; this is its language-neutral mirror, requiring no Node in CI.

This supersedes the earlier ``test_viewer_schema_parity.py``: it reconciles the
same object/flow coverage but (a) sources the viewer's declared surface from the
structured registry instead of a brittle regex over a ``new Set([...])`` literal,
(b) adds the **inline-kind** dimension that guard explicitly left out, and (c)
reconciles the registry against BOTH the byte-gated schema and the models
*directly* (so registry↔model drift is caught even if the schema were stale).

Runs under pytest or standalone (``uv run python tests/test_viewer_schema_contract.py``).
"""
from __future__ import annotations

import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SCHEMA_PATH = os.path.join(ROOT, "docs", "schema", "frameforge-v2.schema.json")
REGISTRY_PATH = os.path.join(ROOT, "viewer", "dev", "type-registry.json")

DIMENSIONS = ("object_types", "flow_types", "inline_kinds")


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def schema_discriminators(schema: dict) -> dict[str, set[str]]:
    """Derive the model's three discriminator sets from the JSON Schema.

    Locate each union (a property whose members are a oneOf/anyOf of >=4 $refs)
    and collect the literal ``type``/``kind`` const of its members. Located by
    content (anchor values), not container-field name, so a model field rename
    does not silently break the gate.
    """
    defs = schema.get("$defs", {})

    def member_refs(node):
        for key in ("oneOf", "anyOf"):
            members = node.get(key) if isinstance(node, dict) else None
            if isinstance(members, list):
                return [m["$ref"].split("/")[-1] for m in members if isinstance(m, dict) and "$ref" in m]
        return []

    def consts_of(refs, field):
        out = set()
        for ref in refs:
            prop = defs.get(ref, {}).get("properties", {}).get(field, {})
            if isinstance(prop, dict) and "const" in prop:
                out.add(prop["const"])
        return out

    unions = []
    for d in defs.values():
        for pd in (d.get("properties", {}) or {}).values():
            node = pd.get("items", pd) if isinstance(pd, dict) else pd
            refs = member_refs(node if isinstance(node, dict) else {})
            if len(refs) >= 4:
                unions.append(refs)

    def pick(field, *anchors):
        for refs in unions:
            consts = consts_of(refs, field)
            if all(a in consts for a in anchors):
                return consts
        return None

    return {
        "object_types": pick("type", "rect", "text"),
        "flow_types": pick("type", "paragraph", "heading"),
        "inline_kinds": pick("kind", "link", "ref"),
    }


def contract_violations(schema_sets: dict, registry: dict) -> list[str]:
    """Return human-readable contract violations (empty list = in sync)."""
    out: list[str] = []
    for dim in DIMENSIONS:
        schema_set = schema_sets.get(dim)
        if not schema_set:
            out.append(f"{dim}: could not locate this union in the schema (model restructured?).")
            continue
        supported = set(registry.get("supported", {}).get(dim, []))
        unsupported = set(registry.get("unsupported", {}).get(dim, {}).keys())
        extensions = set(registry.get("extensions", {}).get(dim, []))
        for t in schema_set:
            if t not in supported and t not in unsupported:
                out.append(f'{dim}: model defines "{t}" but the registry neither supports nor declares it.')
        for t in supported:
            if t not in schema_set and t not in extensions:
                out.append(f'{dim}: viewer claims "{t}" but the model has no such type and it is not a declared extension.')
            if t in unsupported:
                out.append(f'{dim}: "{t}" is in both supported and unsupported.')
        for t in unsupported:
            if t not in schema_set:
                out.append(f'{dim}: unsupported "{t}" is no longer in the model — stale allowlist entry.')
        for t in extensions:
            if t not in supported:
                out.append(f'{dim}: declared extension "{t}" is not in supported.')
    return out


def model_discriminators() -> dict[str, set[str]]:
    """Derive the same three sets *directly from the Pydantic models* (the true
    source of truth), independent of the generated schema. Mirrors the approach
    of the superseded test_viewer_schema_parity.py: object types drop the
    codemod-normalised aliases (curve/bezier/polygon/circle) that never reach a
    renderer. Imported lazily so a models-import hiccup cannot break collection."""
    import sys

    sys.path[:0] = [p for p in (os.path.join(ROOT, "tooling"), os.path.join(ROOT, "docs", "models"))
                    if p not in sys.path]
    import frameforge.model as fg
    import check_grammar_sync as C

    alias = set(C.MODEL_ONLY_ALIAS_TYPES)
    return {
        "object_types": set(C.model_type_map(fg.VisualObject, "type")) - alias,
        "flow_types": set(C.model_type_map(fg.Flowable, "type")),
        "inline_kinds": set(C.model_type_map(fg.Inline, "kind")),
    }


# --------------------------------------------------------------------------- #
#  Tests
# --------------------------------------------------------------------------- #
def _schema_and_registry():
    return _load(SCHEMA_PATH), _load(REGISTRY_PATH)


def test_registry_files_exist_and_parse():
    schema, registry = _schema_and_registry()
    assert schema.get("$defs"), "schema has no $defs"
    for key in ("supported", "unsupported", "extensions"):
        assert key in registry, f"type-registry.json missing '{key}'"


def test_all_three_unions_are_located():
    schema, _ = _schema_and_registry()
    sets = schema_discriminators(schema)
    for dim in DIMENSIONS:
        assert sets[dim], f"failed to locate the {dim} union in the schema"
    # sanity: the anchors really are present
    assert {"rect", "text", "table", "group"} <= sets["object_types"]
    assert {"paragraph", "heading", "list"} <= sets["flow_types"]
    assert {"ref", "cite", "link"} <= sets["inline_kinds"]


def test_contract_holds_on_current_tree():
    schema, registry = _schema_and_registry()
    violations = contract_violations(schema_discriminators(schema), registry)
    assert not violations, "viewer ⇄ model contract drift (C7):\n  " + "\n  ".join(violations)


def test_supported_and_unsupported_are_disjoint():
    _, registry = _schema_and_registry()
    for dim in DIMENSIONS:
        sup = set(registry["supported"].get(dim, []))
        uns = set(registry["unsupported"].get(dim, {}).keys())
        assert not (sup & uns), f"{dim}: overlap between supported and unsupported: {sup & uns}"


def test_documented_gaps_snapshot():
    """Lock the *current* known gaps so closing one (or a regression) forces a
    deliberate registry edit and is visible in review."""
    _, registry = _schema_and_registry()
    assert set(registry["unsupported"]["flow_types"]) == {"column_break", "keep_together", "image"}
    assert set(registry["unsupported"]["inline_kinds"]) == {"ref", "cite", "footnote"}
    assert registry["unsupported"]["object_types"] == {}
    # every documented gap carries a non-empty reason
    for dim in ("flow_types", "inline_kinds"):
        for name, reason in registry["unsupported"][dim].items():
            assert isinstance(reason, str) and reason.strip(), f"{dim}.{name} needs a reason"


def test_self_test_detects_injected_model_type():
    schema, registry = _schema_and_registry()
    sets = schema_discriminators(schema)
    for dim, ghost in (("object_types", "__ghost_obj__"),
                       ("flow_types", "__ghost_flow__"),
                       ("inline_kinds", "__ghost_inline__")):
        poisoned = {d: set(s) for d, s in sets.items()}
        poisoned[dim].add(ghost)
        violations = contract_violations(poisoned, registry)
        assert any(ghost in v for v in violations), f"gate missed an injected {dim} model type"


def test_self_test_detects_stale_allowlist():
    schema, registry = _schema_and_registry()
    sets = schema_discriminators(schema)
    stale = copy.deepcopy(registry)
    stale["unsupported"]["inline_kinds"]["__stale_kind__"] = "x"
    violations = contract_violations(sets, stale)
    assert any("__stale_kind__" in v for v in violations), "gate missed a stale allowlist entry"


def test_self_test_detects_orphan_supported_type():
    schema, registry = _schema_and_registry()
    sets = schema_discriminators(schema)
    orphan = copy.deepcopy(registry)
    orphan["supported"]["object_types"].append("__orphan_obj__")
    violations = contract_violations(sets, orphan)
    assert any("__orphan_obj__" in v for v in violations), "gate missed an orphan supported type"


def test_models_are_fully_covered():
    """Every canonical (post-codemod) model type is either rendered or explicitly
    unsupported — the coverage guarantee the superseded parity test provided,
    sourced model-direct so it holds even if the generated schema were stale.

    This is coverage-only (model ⊆ supported ∪ unsupported); the orphan/stale/
    extension reconciliation lives in the schema-direct contract, because the
    schema — not the post-alias model view — is the complete concrete type list
    (it still carries codemod aliases like circle/polygon that the viewer renders)."""
    _, registry = _schema_and_registry()
    missing = {}
    for dim, types in model_discriminators().items():
        supported = set(registry["supported"].get(dim, []))
        unsupported = set(registry["unsupported"].get(dim, {}).keys())
        gap = sorted(types - supported - unsupported)
        if gap:
            missing[dim] = gap
    assert not missing, f"viewer ⇄ MODEL drift (C7): model types neither rendered nor declared unsupported: {missing}"


def test_schema_and_models_agree():
    """Schema-derived and model-derived discriminators must match (object types
    modulo the codemod aliases the schema still lists) — a cross-check that the
    two derivations the rest of this file relies on are equivalent."""
    schema, _ = _schema_and_registry()
    s = schema_discriminators(schema)
    m = model_discriminators()
    assert s["flow_types"] == m["flow_types"], f"flow drift schema vs models: {s['flow_types'] ^ m['flow_types']}"
    assert s["inline_kinds"] == m["inline_kinds"], f"inline drift schema vs models: {s['inline_kinds'] ^ m['inline_kinds']}"
    # objects: models (post-alias) must be a subset of the schema union, which
    # still carries the alias types (circle/polygon) as concrete object defs.
    assert m["object_types"] <= s["object_types"], f"model object types missing from schema: {m['object_types'] - s['object_types']}"


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as exc:
                print(f"  FAIL  {name}: {exc}")
                failed += 1
    raise SystemExit(1 if failed else 0)
