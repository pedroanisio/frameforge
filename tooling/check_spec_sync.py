#!/usr/bin/env python3
"""check_spec_sync.py — assert the normative spec prose still names what the models define.

The Pydantic models in ``models/frameforge.py`` are the source of truth; the schema
and the EBNF grammar are guarded against them (``build_schema.py --check``,
``check_grammar_sync.py``). The prose spec ``spec/frameforge-v2-spec.md`` declares
itself "the normative reference" but had NO guard — its example documents are
validated (``tests/test_doc_examples.py``) while its prose can silently describe an
older surface than the models (drift-risk-map Finding #4).

This is a *membership* gate, deliberately tolerant (the spec is prose, not a
machine artifact — mirroring ``check_grammar_sync``'s tolerance):

  ERROR  (fails the gate)
    - a core object ``type`` discriminator, a flow ``type``, or an inline ``kind``
      that the models define but the spec never mentions at all. A brand-new
      object type that ships without a spec paragraph fails here.

  WARN   (printed; promoted to ERROR by ``--strict``)
    - a core-object/Document field name absent from the spec prose (the spec is
      not a field-by-field reference, so missing fields are advisory, not fatal).

Membership is word-boundary substring against the raw spec text — enough to catch
a genuinely undocumented name without brittle false-fails on prose wording.

Exit status: 0 = in sync, 1 = drift (ERRORs, or anything under --strict),
2 = usage/internal error. Mirrors tooling/check_grammar_sync.py conventions.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import typing

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SPEC = os.path.join(ROOT, "docs", "spec", "frameforge-v2-spec.md")

# Introspect the models exactly like check_grammar_sync / validate.py: the in-repo
# source of truth shadows any installed distribution, and the ./frameforge package
# (if already imported) must not shadow models/frameforge.py.
sys.path.insert(0, os.path.join(ROOT, "docs"))
import models.frameforge as fg  # noqa: E402  (package-qualified: never shadow or evict the real package)

# Deprecated renderer-shortcut aliases the models accept but the normative surface
# omits (codemod normalises them); kept identical to check_grammar_sync.py.
MODEL_ONLY_ALIAS_TYPES = {"circle", "polygon", "curve", "bezier"}

SEV_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


class Finding:
    __slots__ = ("sev", "code", "msg")

    def __init__(self, sev: str, code: str, msg: str):
        self.sev, self.code, self.msg = sev, code, msg

    def __str__(self) -> str:
        return f"  {self.sev:5}  {self.code:18}  {self.msg}"


def _unwrap(t):
    return t.__origin__ if hasattr(t, "__metadata__") else t


def _union_members(alias):
    return [a for a in typing.get_args(_unwrap(alias))
            if isinstance(a, type) and hasattr(a, "model_fields")]


def _discriminators(alias, disc: str) -> set[str]:
    out: set[str] = set()
    for member in _union_members(alias):
        field = member.model_fields.get(disc)
        if field is None:
            continue
        ann = field.annotation
        if typing.get_origin(ann) is typing.Literal:
            out |= set(typing.get_args(ann))
    return out


def _field_names(alias) -> set[str]:
    out: set[str] = set()
    for member in _union_members(alias):
        out |= {(f.alias or n) for n, f in member.model_fields.items()}
    return out


def _present(spec: str, token: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(token)}(?![\w-])", spec) is not None


# drift-risk-map #6 — accepted backlog of core field names not yet named in the
# normative spec prose (additive style/paint props + a few container fields).
# These stay non-fatal WARNs; a field NOT on this list that is missing from the
# spec is a hard ERROR (see run_checks). Shrink this set as fields get documented;
# never grow it without an explicit reason.
SPEC_UNDOCUMENTED_BASELINE = frozenset({
    "actual_text", "alt", "appearance", "cell_padding", "control1", "control2",
    "description", "field", "fill_opacity", "glow", "header_height", "humanize",
    "indent", "items", "marker_color", "outer_ring", "placeholder", "ports",
    "preserve_aspect_ratio", "r", "row_height", "rows", "rx", "ry", "shadow",
    "spans", "stroke_opacity", "text_contract", "z", "zebra",
})


def run_checks(spec: str) -> list[Finding]:
    out: list[Finding] = []

    discriminator_groups = [
        ("object type", _discriminators(fg.VisualObject, "type") - MODEL_ONLY_ALIAS_TYPES),
        ("flow type", _discriminators(fg.Flowable, "type")),
        ("inline kind", _discriminators(fg.Inline, "kind")),
    ]
    for label, values in discriminator_groups:
        for v in sorted(values):
            if not _present(spec, v):
                out.append(Finding("ERROR", "type-undocumented",
                                   f"{label} {v!r} is defined in the models but never named in the spec"))

    fields = _field_names(fg.VisualObject) | {(f.alias or n) for n, f in fg.Document.model_fields.items()}
    for name in sorted(fields):
        if not _present(spec, name):
            # Ratchet (drift-risk-map #6): the fields on the accepted BASELINE stay
            # non-fatal WARNs (a documented backlog); any OTHER field missing from the
            # normative spec is a hard ERROR, so the gate can no longer silently accept
            # a *newly* undocumented field.
            baselined = name in SPEC_UNDOCUMENTED_BASELINE
            out.append(Finding(
                "WARN" if baselined else "ERROR", "field-undocumented",
                f"core field {name!r} is not named in the spec prose"
                + ("" if baselined else " (NEW — document it in the spec, or add it to "
                   "SPEC_UNDOCUMENTED_BASELINE with justification)")))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true",
                    help="treat WARN (missing field names) as failures too")
    ap.add_argument("--quiet", action="store_true", help="only print failures + the summary")
    args = ap.parse_args(argv)

    try:
        spec = open(SPEC, encoding="utf-8").read()
        findings = run_checks(spec)
    except Exception as e:  # noqa: BLE001
        print(f"check_spec_sync: internal error: {e}", file=sys.stderr)
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
    print(f"\ncheck_spec_sync: {status} — "
          f"{n['ERROR']} error(s), {n['WARN']} warning(s)"
          f"{' (--strict)' if args.strict else ''}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
