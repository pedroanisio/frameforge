#!/usr/bin/env python3
"""check_grammar_sync.py — automated EBNF ⇄ Pydantic consistency gate.

The Pydantic models in ``models/framegraph.py`` are the source of truth; the two
``grammar/*.ebnf`` files are a hand-maintained *view* (README §"Grammar ⇄
models"). Nothing previously enforced that the view stays faithful — this script
does, so drift fails CI instead of silently rotting.

It does NOT parse the grammar with a full grammar engine (the EBNF is hand-kept
and explicitly "not guaranteed byte-identical", so a strict parser would brittly
reject cosmetic quirks). Instead it does a *tolerant* structural extraction —
production headers, quoted terminals, ``"field" , ":"`` slots, and
``"type" , ":" , "<lit>"`` discriminators — and diffs that against introspection
of the imported models.

Policy (the "deep core profile" the project actually commits to):

  ERROR  (fails the gate)
    - a core object/flow ``type`` discriminator present on one side only
    - a shared enum (module-level ``Literal`` alias whose name also names a
      pure-string EBNF production) whose value sets differ

  WARN   (printed; promoted to ERROR by ``--strict``)
    - grammar object/flow/inline kinds with no Pydantic model (the deliberate
      out-of-profile superset — charts, connectors, the UML zoo, …)
    - per-core-object field-name drift between the production and the model

  INFO
    - model-only deprecated aliases the grammar intentionally omits
      (circle/polygon/curve/bezier — normalised away by tooling/codemod.py)

Exit status: 0 = in sync, 1 = drift (ERRORs, or anything under --strict),
2 = usage/internal error. Mirrors tooling/validate.py conventions.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import typing

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
# Import the *models* module as ``framegraph`` exactly like validate.py, so the
# in-repo source of truth shadows any installed distribution of the same name.
sys.path.insert(0, os.path.join(ROOT, "models"))
# The rendering package ``framegraph`` (./framegraph) shares the name; if it is
# already imported (e.g. under pytest) it would shadow models/framegraph.py.
# Evict the package so we always introspect the source of truth — see test_head.
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
import framegraph as fg  # noqa: E402

CORE_EBNF = os.path.join(ROOT, "grammar", "framegraph-v2.ebnf")
STYLE_EBNF = os.path.join(ROOT, "grammar", "framegraph-v2-style.ebnf")

# The 17 object types the models type strictly (kept identical to
# validate.py:CORE_OBJECT_TYPES — the single definition of "core profile").
CORE_OBJECT_TYPES = {
    "rect", "ellipse", "circle", "line", "polyline", "polygon", "path", "curve",
    "bezier", "text", "image", "icon", "bullet_list", "dimension", "connector",
    "table", "group",
}
# Deprecated renderer-shortcut aliases the models accept but the grammar's
# normative shape set deliberately omits (codemod.py normalises them). Present
# only in the models by design — reported as INFO, never ERROR.
MODEL_ONLY_ALIAS_TYPES = {"circle", "polygon", "curve", "bezier"}

# EBNF "mixins": productions inlined into others by reference. Expanded when
# computing a production's full field set.
FIELD_MIXINS = {"common-object-fields", "break-fields", "TextContent", "TableBody"}

# Structural EBNF terminals (quoted punctuation) to ignore when harvesting
# enum values from a production.
_STRUCT = set("{}[](),:|;=")

# --------------------------------------------------------------------------- #
#  Findings                                                                    #
# --------------------------------------------------------------------------- #
SEV_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


class Finding:
    __slots__ = ("sev", "code", "msg")

    def __init__(self, sev: str, code: str, msg: str):
        self.sev, self.code, self.msg = sev, code, msg

    def __str__(self) -> str:
        return f"  {self.sev:5}  {self.code:18}  {self.msg}"


# --------------------------------------------------------------------------- #
#  Tolerant EBNF extraction                                                    #
# --------------------------------------------------------------------------- #
def _strip_comments(text: str) -> str:
    """Drop ``(* ... *)`` comments, preserving newlines so line-anchored
    production headers stay at column 0."""
    return re.sub(r"\(\*.*?\*\)",
                  lambda m: "\n" * m.group(0).count("\n"),
                  text, flags=re.DOTALL)


def parse_productions(*paths: str) -> dict[str, str]:
    """Return ``{production-name: rhs-text}`` across the given grammar files."""
    prods: dict[str, str] = {}
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            text = _strip_comments(fh.read())
        headers = list(re.finditer(r"(?m)^([A-Za-z][A-Za-z0-9_-]*)[ \t]*=", text))
        for i, h in enumerate(headers):
            start = h.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            rhs = text[start:end]
            cut = rhs.rfind(";")           # strip the rule terminator
            prods[h.group(1)] = rhs[:cut] if cut != -1 else rhs
    return prods


def _field_slots(rhs: str) -> set[str]:
    """Field keywords declared directly in a production: the ``"name" , ":"``
    pattern (covers both required and ``[ "name" , ":" ... ]`` optional slots)."""
    return set(re.findall(r'"([A-Za-z_][A-Za-z0-9_-]*)"\s*,\s*":"', rhs))


def production_fields(prods: dict[str, str], name: str,
                      _seen: set[str] | None = None) -> set[str]:
    """Full field set of an object/flow production, expanding known mixins."""
    _seen = _seen or set()
    if name in _seen or name not in prods:
        return set()
    _seen.add(name)
    rhs = prods[name]
    fields = _field_slots(rhs)
    for mixin in FIELD_MIXINS:
        if re.search(rf"(?<![\w-]){re.escape(mixin)}(?![\w-])", rhs):
            fields |= production_fields(prods, mixin, _seen)
    return fields


def type_literal(rhs: str, disc: str = "type") -> str | None:
    """The fixed discriminator literal: ``"<disc>" , ":" , "<lit>"``."""
    m = re.search(rf'"{disc}"\s*,\s*":"\s*,\s*"([^"]+)"', rhs)
    return m.group(1) if m else None


def union_member_names(prods: dict[str, str], name: str) -> list[str]:
    """Production names referenced by a ``A | B | C`` union production."""
    if name not in prods:
        return []
    idents = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", prods[name])
    return [i for i in idents if i in prods]


def enum_values(rhs: str) -> set[str]:
    """Quoted alternatives of an enum production, minus structural punctuation
    and minus any ``"name" , ":"`` field keywords (so mixed productions still
    yield just their literal alternatives)."""
    quoted = set(re.findall(r'"([^"]*)"', rhs))
    return {v for v in quoted if v not in _STRUCT} - _field_slots(rhs)


def is_pure_enum(rhs: str) -> bool:
    """A production whose alternatives are all string terminals (no object/array
    forms) — safe to compare value-for-value against a ``Literal``."""
    return "{" not in rhs and "[" not in rhs and bool(re.search(r'"[^"]+"', rhs))


# --------------------------------------------------------------------------- #
#  Pydantic introspection                                                      #
# --------------------------------------------------------------------------- #
def _unwrap(t):
    """``Annotated[X, ...] -> X``."""
    return t.__origin__ if hasattr(t, "__metadata__") else t


def union_members(alias) -> list[type]:
    """Model classes inside an (optionally Annotated) discriminated Union."""
    return [a for a in typing.get_args(_unwrap(alias))
            if isinstance(a, type) and hasattr(a, "model_fields")]


def discriminator_values(model: type, disc: str) -> set[str]:
    field = model.model_fields.get(disc)
    if field is None:
        return set()
    ann = field.annotation
    return set(typing.get_args(ann)) if typing.get_origin(ann) is typing.Literal else set()


def model_field_names(model: type) -> set[str]:
    return {(f.alias or n) for n, f in model.model_fields.items()}


def model_literal_aliases() -> dict[str, set[str]]:
    """Every module-level ``Literal[...]`` alias -> its value set."""
    out = {}
    for name, val in vars(fg).items():
        if typing.get_origin(val) is typing.Literal:
            out[name] = set(typing.get_args(val))
    return out


def model_type_map(alias, disc: str) -> dict[str, str]:
    """``{discriminator-literal: model-class-name}`` for a model union."""
    out: dict[str, str] = {}
    for member in union_members(alias):
        for lit in discriminator_values(member, disc):
            out[lit] = member.__name__
    return out


def grammar_type_map(prods: dict[str, str], union_name: str,
                     disc: str = "type") -> dict[str, str]:
    """``{discriminator-literal: production-name}`` for a grammar union."""
    out: dict[str, str] = {}
    for member in union_member_names(prods, union_name):
        lit = type_literal(prods[member], disc)
        if lit:
            out[lit] = member
    return out


# --------------------------------------------------------------------------- #
#  The checks                                                                  #
# --------------------------------------------------------------------------- #
def check_discriminated(out: list[Finding], kind: str, model_map: dict[str, str],
                        grammar_map: dict[str, str], *, core: set[str] | None = None,
                        aliases: set[str] = frozenset()) -> None:
    m, g = set(model_map), set(grammar_map)

    if core is not None:
        for t in sorted(core - m):
            out.append(Finding("ERROR", "core-missing-model",
                               f"core {kind} type {t!r} is not modelled in the union"))

    for t in sorted(m - g):
        if t in aliases:
            out.append(Finding("INFO", "model-only-alias",
                               f"{kind} type {t!r} ({model_map[t]}) is a deprecated "
                               f"model-only alias; intentionally absent from the grammar"))
        else:
            out.append(Finding("ERROR", "model-not-in-grammar",
                               f"{kind} type {t!r} ({model_map[t]}) has no grammar production"))

    for t in sorted(g - m):
        out.append(Finding("WARN", "out-of-profile",
                           f"grammar {kind} type {t!r} ({grammar_map[t]}) has no Pydantic "
                           f"model (out-of-profile superset; validated loosely)"))


def check_enums(out: list[Finding], prods: dict[str, str]) -> None:
    for name, model_vals in sorted(model_literal_aliases().items()):
        rhs = prods.get(name)
        if rhs is None or not is_pure_enum(rhs):
            continue
        gram_vals = enum_values(rhs)
        if model_vals == gram_vals:
            continue
        only_m = ", ".join(sorted(model_vals - gram_vals)) or "—"
        only_g = ", ".join(sorted(gram_vals - model_vals)) or "—"
        out.append(Finding("ERROR", "enum-drift",
                           f"enum {name}: in models not grammar: {{{only_m}}}; "
                           f"in grammar not models: {{{only_g}}}"))


def check_object_fields(out: list[Finding], prods: dict[str, str],
                        model_map: dict[str, str], grammar_map: dict[str, str]) -> None:
    for t in sorted(set(model_map) & set(grammar_map) & CORE_OBJECT_TYPES):
        m_fields = model_field_names(getattr(fg, model_map[t]))
        g_fields = production_fields(prods, grammar_map[t])
        only_m = sorted(m_fields - g_fields)
        only_g = sorted(g_fields - m_fields)
        if only_m or only_g:
            parts = []
            if only_m:
                parts.append(f"model-only: {', '.join(only_m)}")
            if only_g:
                parts.append(f"grammar-only: {', '.join(only_g)}")
            out.append(Finding("WARN", "field-drift",
                               f"object {t!r}: " + "; ".join(parts)))


# --------------------------------------------------------------------------- #
#  Inline (un-named) style enums                                               #
# --------------------------------------------------------------------------- #
# The named style enums (FontStyle, BlendMode, Overflow, …) are module-level
# Literal aliases, already covered by check_enums(). But most style enums are
# *inline* on the field — ``[ "text_align" , ":" , ( "left" | "right" | … ) ]`` —
# and were never compared to the models' inline Literal fields (drift-risk-map
# Finding #3). The grammar's field names are underscore-form and match the model
# field names verbatim, so the two sides can be lined up by field name.
_INLINE_SLOT = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*,\s*":"\s*,\s*(.*)$')


def style_inline_enum_slots() -> dict[str, set[str]]:
    """``{field: {literal, …}}`` for every ``"field" , ":" , ( "a" | "b" )`` slot in
    the style grammar. Quoted structural punctuation is dropped, so a slot whose
    value is a named production / bare ``string`` / ``Length`` yields no literals
    and is skipped by callers."""
    text = _strip_comments(open(STYLE_EBNF, encoding="utf-8").read())
    slots: dict[str, set[str]] = {}
    for line in text.splitlines():
        m = _INLINE_SLOT.search(line)
        if not m:
            continue
        vals = {v for v in re.findall(r'"([^"]*)"', m.group(2)) if v not in _STRUCT}
        if vals:
            slots.setdefault(m.group(1), set()).update(vals)
    return slots


def _literal_strings(ann) -> set[str]:
    """Every ``str`` value inside a (possibly Optional/Union-nested) annotation's
    ``Literal``s."""
    out: set[str] = set()
    if typing.get_origin(ann) is typing.Literal:
        out |= {a for a in typing.get_args(ann) if isinstance(a, str)}
    for a in typing.get_args(ann):
        out |= _literal_strings(a)
    return out


def _admits_free_str(ann) -> bool:
    """True if the annotation accepts an arbitrary ``str`` (so the grammar may list
    sample values without lying)."""
    if ann is str:
        return True
    return any(_admits_free_str(a) for a in typing.get_args(ann))


def model_closed_field_enums() -> dict[str, set[str]]:
    """``{field: {value, …}}`` for every model field whose annotation pins a *closed*
    string set — a ``Literal`` with no bare ``str`` alternative. A field that is
    open (admits free ``str``) in any model is excluded everywhere: enumerating
    sample values of a free-text field is not a contract violation."""
    closed: dict[str, set[str]] = {}
    open_fields: set[str] = set()
    for obj in vars(fg).values():
        mf = getattr(obj, "model_fields", None)
        if not mf:
            continue
        for fname, f in mf.items():
            vals = _literal_strings(f.annotation)
            if not vals:
                continue
            if _admits_free_str(f.annotation):
                open_fields.add(fname)
            else:
                closed.setdefault(fname, set()).update(vals)
    for f in open_fields:
        closed.pop(f, None)
    return closed


def check_inline_enums(out: list[Finding], slots: dict[str, set[str]] | None = None) -> None:
    """ERROR when a style-grammar inline enum offers a value no closed model field of
    that name accepts — i.e. the grammar lies to authors about a closed enum. The
    reverse (a model value the grammar omits) is intentionally not gated: field-name
    collisions across models make it noisy, and an under-documented grammar is not a
    correctness hazard. ``slots`` defaults to the live grammar; pass a dict to test."""
    model = model_closed_field_enums()
    if slots is None:
        slots = style_inline_enum_slots()
    for field, gvals in sorted(slots.items()):
        mvals = model.get(field)
        if mvals is None:
            continue  # no closed model field of this name — nothing to lie about
        bogus = sorted(gvals - mvals)
        if bogus:
            out.append(Finding("ERROR", "inline-enum-drift",
                               f"style enum {field!r}: grammar offers value(s) the model "
                               f"rejects: {{{', '.join(bogus)}}}"))


def run_checks() -> list[Finding]:
    prods = parse_productions(CORE_EBNF, STYLE_EBNF)
    out: list[Finding] = []

    obj_model = model_type_map(fg.VisualObject, "type")
    obj_gram = grammar_type_map(prods, "VisualObject", "type")
    check_discriminated(out, "object", obj_model, obj_gram,
                        core=CORE_OBJECT_TYPES, aliases=MODEL_ONLY_ALIAS_TYPES)

    flow_model = model_type_map(fg.Flowable, "type")
    flow_gram = grammar_type_map(prods, "Flowable", "type")
    check_discriminated(out, "flow", flow_model, flow_gram)

    # Inlines discriminate on "kind"; str/Span carry none, so this is membership-
    # only (no core set, no aliases): grammar-only kinds surface as WARN.
    inline_model = model_type_map(fg.Inline, "kind")
    inline_gram = grammar_type_map(prods, "Inline", "kind")
    check_discriminated(out, "inline", inline_model, inline_gram)

    check_enums(out, prods)
    check_inline_enums(out)
    check_object_fields(out, prods, obj_model, obj_gram)
    return out


# --------------------------------------------------------------------------- #
#  CLI                                                                         #
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true",
                    help="treat WARN findings as failures too (full grammar↔model parity)")
    ap.add_argument("--quiet", action="store_true", help="only print failures + the summary")
    args = ap.parse_args(argv)

    try:
        findings = run_checks()
    except Exception as e:  # noqa: BLE001 — surface any introspection breakage clearly
        print(f"check_grammar_sync: internal error: {e}", file=sys.stderr)
        return 2

    fail_sevs = {"ERROR", "WARN"} if args.strict else {"ERROR"}
    findings.sort(key=lambda f: (SEV_ORDER[f.sev], f.code, f.msg))
    failures = [f for f in findings if f.sev in fail_sevs]

    for f in findings:
        if args.quiet and f.sev not in fail_sevs:
            continue
        print(f)

    n = {s: sum(1 for f in findings if f.sev == s) for s in ("ERROR", "WARN", "INFO")}
    status = "DRIFT" if failures else "in sync"
    print(f"\ncheck_grammar_sync: {status} — "
          f"{n['ERROR']} error(s), {n['WARN']} warning(s), {n['INFO']} info"
          f"{' (--strict)' if args.strict else ''}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
