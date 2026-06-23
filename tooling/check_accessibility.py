#!/usr/bin/env python3
"""check_accessibility.py — accessibility / tagged-export conformance lint.

Roadmap item 2: the models now carry the accessibility *vocabulary* — `decorative`
on every visual object, `alt`/`actual_text` on image (and figure) objects, and a
per-page `reading_order` over object ids. The vocabulary existing does not make a
document accessible; this checker enforces that it is used *coherently*, so a
future tagged export (SVG a11y today, PDF/UA structure tree later) is well defined.

  ERROR  (fails the gate)
    A11Y-1  a page's `reading_order` references an id no object on the page has,
            or lists the same id twice — a structure tree built from it would be
            broken or ambiguous.

  WARN   (advisory; `--strict` promotes to ERROR)
    A11Y-2  a non-`decorative` image object has neither `alt` nor `actual_text`
            (no alternative text for a meaningful non-text element).
    A11Y-3  a `mode: page` page with non-decorative objects declares no
            `reading_order` (reading order is undefined for assistive tech).
    A11Y-4  a page declares `reading_order` but a top-level non-decorative object
            is not reachable in it (missing id, or id not listed).

This is a focused lint layered on top of `validate.py` (which owns structural
validity); it reads the document as data and assumes well-formed shapes, guarding
defensively. Exit: 0 = clean, 1 = errors (or any finding under `--strict`),
2 = load error. Mirrors `tooling/validate.py` conventions.
"""
from __future__ import annotations

import argparse
import os
import sys

import yaml

# Object types whose model carries `alt`/`actual_text` (Image; figures are a flow
# type handled separately). Icons have no alt field, so they are not flagged.
ALT_TYPES = {"image"}


class Finding:
    __slots__ = ("severity", "code", "msg", "path")

    def __init__(self, severity, code, msg, path):
        self.severity, self.code, self.msg, self.path = severity, code, msg, path

    def __str__(self):
        return f"  [{self.severity}] {self.code} @ {self.path}: {self.msg}"


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _walk_visual(node, path, sink):
    """Append (obj, path) for every visual object, recursing into groups."""
    if not isinstance(node, dict) or not node.get("type"):
        return
    sink.append((node, path))
    if node.get("type") == "group":
        for i, ch in enumerate(node.get("children") or []):
            _walk_visual(ch, f"{path}.children[{i}]", sink)


def _page_objects(page):
    """Return (all, top): every visual object (groups recursed) and the
    top-level layer objects only — `reading_order` sequences the top level."""
    all_objs: list[tuple[dict, str]] = []
    top: list[tuple[dict, str]] = []
    for li, layer in enumerate(page.get("layers") or []):
        if not isinstance(layer, dict):
            continue
        for oi, o in enumerate(layer.get("objects") or []):
            opath = f"layers[{li}].objects[{oi}]"
            if isinstance(o, dict) and o.get("type"):
                top.append((o, opath))
            _walk_visual(o, opath, all_objs)
    return all_objs, top


def check_doc(doc) -> list[Finding]:
    """Accessibility findings for one parsed document."""
    findings: list[Finding] = []
    pages = doc.get("pages", []) if isinstance(doc, dict) else []
    for pi, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        base = f"pages[{pi}]"
        all_objs, top = _page_objects(page)
        ids_present = {o.get("id") for o, _ in all_objs if o.get("id")}

        # A11Y-2 — images anywhere on the page need alternative text.
        for o, opath in all_objs:
            if (o.get("type") in ALT_TYPES and not o.get("decorative")
                    and not o.get("alt") and not o.get("actual_text")):
                findings.append(Finding("WARN", "A11Y-2",
                                        "non-decorative image has neither `alt` nor `actual_text`",
                                        f"{base}.{opath}"))

        if page.get("mode") != "page":
            continue  # `reading_order` is a page-mode concept (flows read in story order)

        ro = page.get("reading_order")
        if ro is None:
            if any(not o.get("decorative") for o, _ in top):
                findings.append(Finding("WARN", "A11Y-3",
                                        "page has non-decorative objects but no `reading_order`; "
                                        "reading order is undefined for assistive tech", base))
            continue
        if not isinstance(ro, list):
            continue  # structural problem — validate.py owns it

        # A11Y-1 — every entry must resolve to a real id, and be unique.
        seen: set = set()
        for j, rid in enumerate(ro):
            if rid in seen:
                findings.append(Finding("ERROR", "A11Y-1",
                                        f"`reading_order` lists id {rid!r} more than once",
                                        f"{base}.reading_order[{j}]"))
            seen.add(rid)
            if rid not in ids_present:
                findings.append(Finding("ERROR", "A11Y-1",
                                        f"`reading_order` references id {rid!r} but no object "
                                        f"on the page has it", f"{base}.reading_order[{j}]"))

        # A11Y-4 — every top-level meaningful object must be reachable.
        for o, opath in top:
            if o.get("decorative"):
                continue
            oid = o.get("id")
            if oid is None:
                findings.append(Finding("WARN", "A11Y-4",
                                        "non-decorative object has no `id`, so it cannot appear "
                                        "in `reading_order`", f"{base}.{opath}"))
            elif oid not in seen:
                findings.append(Finding("WARN", "A11Y-4",
                                        f"object id {oid!r} is not listed in the page "
                                        f"`reading_order`", f"{base}.{opath}"))
    return findings


def check_file(path, strict=False):
    try:
        doc = _load(path)
    except Exception as exc:  # noqa: BLE001 — surface any parse error as a finding
        return [Finding("ERROR", "load", f"could not parse: {exc}", path)], 2
    findings = check_doc(doc)
    if strict:
        for f in findings:
            if f.severity == "WARN":
                f.severity = "ERROR"
    errs = sum(1 for f in findings if f.severity == "ERROR")
    return findings, (1 if errs else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("documents", nargs="+")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--quiet", action="store_true", help="only print the per-file summary lines")
    args = ap.parse_args(argv)

    rc = 0
    for path in args.documents:
        findings, code = check_file(path, strict=args.strict)
        rc = max(rc, code)
        e = sum(1 for f in findings if f.severity == "ERROR")
        w = sum(1 for f in findings if f.severity == "WARN")
        status = "FAIL" if e else ("WARN" if w else "PASS")
        print(f"{status}  {os.path.basename(path)}  ({e} error(s), {w} warning(s))")
        if not args.quiet:
            for f in findings:
                print(f)
    print(f"\ncheck_accessibility: {'FAIL' if rc == 1 else 'OK'} — "
          f"checked {len(args.documents)} document(s)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
