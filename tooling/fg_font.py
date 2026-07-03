"""fg-font — inspect, gate, and pack the fonts a FrameGraph document depends on.

The layout metric (`font_metrics`) and every rasterizer (Chromium / cairo /
LaTeX) must resolve the **same font file**, or justified/wrapped text diverges
(ADR-0004: measure-time ≠ render-time). This tool makes that a portable
*contract* instead of a hope, operationalising the model's existing pinned-font
concept (`FontDef` src+hash, §9.6):

  fg-font --list                  families THIS runtime resolves (reference these)
  fg-font --check DOC             non-zero exit if any content font substitutes
  fg-font --pack DOC --out P.fp   bundle DOC's fonts + a manifest → render anywhere

A ``.fp`` pack is a zip: ``manifest.json`` (family → file + sha256) + ``fonts/*``.
An external renderer points fontconfig **and** `font_metrics` at the pack's
``fonts/`` dir, so measure == render on any host — no 9 GB image required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "docs"))

import yaml  # noqa: E402
from framegraph.rendering.infrastructure import font_metrics as FM  # noqa: E402

_GENERIC = {"sans-serif", "serif", "monospace", "system-ui", "cursive", "fantasy",
            "sans", "mono", "ui-sans-serif", "ui-serif", "ui-monospace"}


# --------------------------------------------------------------------------- #
#  Which concrete families does a document actually reference?                #
# --------------------------------------------------------------------------- #
def _token_family_map(doc: dict) -> dict[str, str]:
    """``defs.tokens.fonts`` name → concrete primary family (FontDef.family or the
    string's first concrete entry)."""
    out: dict[str, str] = {}
    fonts = (((doc.get("defs") or {}).get("tokens") or {}).get("fonts") or {})
    for name, val in fonts.items():
        if isinstance(val, dict):
            fam = val.get("family")
            if fam:
                out[name] = str(fam)
        elif isinstance(val, str):
            out[name] = val
    return out


def _split_chain(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip().strip("'\"") for p in str(value).split(",") if p.strip()]


def referenced_families(doc: dict) -> set[str]:
    """Every concrete (non-generic) family the document could draw — tokens.fonts,
    every style's ``font_family``/``font``, and inline overrides — with tokens.fonts
    keys expanded to their concrete family."""
    tok = _token_family_map(doc)
    found: set[str] = set()

    def add(value) -> None:
        for name in _split_chain(value):
            fam = tok.get(name, name)                 # expand a tokens.fonts key
            for concrete in _split_chain(fam):
                if concrete.lower() not in _GENERIC:
                    found.add(concrete)

    def walk(node) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                if key in ("font_family", "font") and val is not None:
                    add(val)
                else:
                    walk(val)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    for fam in tok.values():                          # families declared but unused still pack
        add(fam)
    return found


# --------------------------------------------------------------------------- #
#  Subcommands                                                                 #
# --------------------------------------------------------------------------- #
def cmd_list(_args) -> int:
    if shutil.which("fc-list") is None:
        print("fc-list not available — cannot enumerate fonts", file=sys.stderr)
        return 2
    out = subprocess.run(["fc-list", "-f", "%{family}\n"], capture_output=True,
                         text=True, check=False).stdout
    families = sorted({line.split(",")[0].strip() for line in out.splitlines() if line.strip()})
    print(f"# {len(families)} resolvable families in this runtime "
          f"(reference these, or pin+pack a font):")
    for fam in families:
        print(fam)
    return 0


def _resolve(family: str, bold: bool):
    """(resolved_family, matched, file) for one concrete family."""
    resolved, matched, _ = FM.resolve_report(family, bold)
    path = FM._resolve_font_file(family, bold) if matched else None
    return resolved, matched, path


def cmd_check(args) -> int:
    doc = yaml.safe_load(open(args.doc, encoding="utf-8"))
    families = sorted(referenced_families(doc))
    substitutions = []
    for fam in families:
        resolved, matched, _ = _resolve(fam, False)
        status = "ok" if matched else "SUBSTITUTED"
        print(f"  [{status:^11}] {fam!r:32} -> {resolved!r}")
        if not matched:
            substitutions.append((fam, resolved))
    if substitutions:
        print(f"\nFAIL: {len(substitutions)} content font(s) will be SUBSTITUTED — layout "
              f"measured a different face than the rasterizer draws (justified/wrapped text "
              f"will diverge). Pin + pack them (`fg-font --pack`) or install them.",
              file=sys.stderr)
        return 1
    print(f"\nOK: all {len(families)} referenced families resolve to themselves "
          f"(measure == render).")
    return 0


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_pack(args) -> int:
    doc = yaml.safe_load(open(args.doc, encoding="utf-8"))
    families = sorted(referenced_families(doc))
    entries, files, missing = [], {}, []
    for fam in families:
        for bold in (False, True):
            resolved, matched, path = _resolve(fam, bold)
            if not path or not os.path.isfile(path):
                if not bold:
                    missing.append(fam)
                continue
            arc = "fonts/" + os.path.basename(path)
            files[arc] = path
            entries.append({"family": fam, "bold": bold, "file": arc,
                            "resolved": resolved, "sha256": _sha256(path)})
    if missing and not args.allow_missing:
        print(f"FAIL: cannot pin {missing} (not installed / substituted). Install them or "
              f"pass --allow-missing to pack what resolves.", file=sys.stderr)
        return 1
    manifest = {"fp_version": 1, "generated_from": os.path.basename(args.doc),
                "fonts": entries}
    out = args.out or (os.path.splitext(args.doc)[0] + ".fp")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        for arc, path in sorted(files.items()):
            z.write(path, arc)
    print(f"wrote {out}: {len(entries)} face(s), {len(files)} file(s) "
          f"({len(set(e['family'] for e in entries))} families)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fg-font", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    ap.add_argument("--list", action="store_true", help="list resolvable families")
    ap.add_argument("--check", metavar="DOC", help="fail if a content font substitutes")
    ap.add_argument("--pack", metavar="DOC", help="bundle a doc's fonts into a .fp pack")
    ap.add_argument("--out", help="output .fp path (with --pack)")
    ap.add_argument("--allow-missing", action="store_true", help="pack what resolves; skip misses")
    args = ap.parse_args(argv)
    if args.list:
        return cmd_list(args)
    if args.check:
        args.doc = args.check
        return cmd_check(args)
    if args.pack:
        args.doc = args.pack
        return cmd_pack(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
