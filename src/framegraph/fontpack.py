"""fg-font — inspect, gate, and pack the fonts a FrameGraph document depends on.

The layout metric (`font_metrics`) and every rasterizer (Chromium / cairo /
LaTeX) must resolve the **same font file**, or justified/wrapped text diverges
(ADR-0004: measure-time ≠ render-time). This makes that a portable *contract*,
operationalising the model's pinned-font concept (`FontDef` src+hash, §9.6):

  fg-font --list                  families THIS runtime resolves (reference these)
  fg-font --check DOC             non-zero exit if any content font substitutes
  fg-font --pack DOC --out P.fp   bundle DOC's fonts + a manifest → render anywhere
  fg-font --pack DOC --fetch      provision missing families from Google Fonts first
  fg-font --install P.fp --dir D  extract a pack into a scoped fontconfig (consume)

A ``.fp`` pack is a zip: ``manifest.json`` (family → file + sha256) + ``fonts/*``.
Point fontconfig **and** `font_metrics` at the pack's ``fonts/`` and measure ==
render on any host — no 9 GB image required. ``--fetch`` makes the pack
self-provisioning: a family absent from the host is pulled from the open
``google/fonts`` corpus and stamped ``source: "google-fonts:<slug>"`` in the
manifest, so packs are reproducible even off a font-rich image.

Registered as the ``fg-font`` console script; ``tooling/fg_font.py`` and the
``make font-*`` targets are thin wrappers. A render CLI's ``--font-pack`` calls
:func:`scope_font_pack`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

import yaml

from framegraph.rendering.infrastructure import font_metrics as FM

_GENERIC = {"sans-serif", "serif", "monospace", "system-ui", "cursive", "fantasy",
            "sans", "mono", "ui-sans-serif", "ui-serif", "ui-monospace"}


# --------------------------------------------------------------------------- #
#  Which concrete families does a document actually reference?                #
# --------------------------------------------------------------------------- #
def _token_family_map(doc: dict) -> dict[str, str]:
    """``defs.tokens.fonts`` name → concrete primary family."""
    out: dict[str, str] = {}
    fonts = (((doc.get("defs") or {}).get("tokens") or {}).get("fonts") or {})
    for name, val in fonts.items():
        if isinstance(val, dict) and val.get("family"):
            out[name] = str(val["family"])
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
            for concrete in _split_chain(tok.get(name, name)):
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
    for fam in tok.values():
        add(fam)
    return found


# --------------------------------------------------------------------------- #
#  Resolution                                                                  #
# --------------------------------------------------------------------------- #
def _resolve(family: str, bold: bool):
    resolved, matched, _ = FM.resolve_report(family, bold)
    path = FM._resolve_font_file(family, bold) if matched else None
    return resolved, matched, path


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
#  Google Fonts proxy: provision a missing family from the open google/fonts   #
# --------------------------------------------------------------------------- #
_GF_API = "https://api.github.com/repos/google/fonts/contents"


def google_slug(family: str) -> str:
    """A family name → its google/fonts directory slug (``EB Garamond`` →
    ``ebgaramond``, ``Fira Sans`` → ``firasans``)."""
    return "".join(family.lower().split()).replace("-", "")


def _gf_listing(slug: str):
    import urllib.request
    for lic in ("ofl", "apache", "ufl"):
        try:
            with urllib.request.urlopen(f"{_GF_API}/{lic}/{slug}", timeout=10) as r:
                return json.loads(r.read())
        except Exception:
            continue
    return None


def google_available(family: str) -> bool:
    """True if google/fonts has a downloadable TTF for ``family`` — cheap: lists
    the directory (one API call) and downloads nothing. Powers ``--check --fetch``."""
    listing = _gf_listing(google_slug(family))
    return bool(listing) and any(
        isinstance(f, dict) and str(f.get("name", "")).lower().endswith(".ttf")
        for f in listing)


def fetch_google_font(family: str, bold: bool, cache_dir: str) -> str | None:
    """Download a Google Fonts TTF for ``family`` (bold or regular) into
    ``cache_dir``; return its path, or None if google/fonts has no such family or
    the network is unavailable. Pure best-effort — never raises."""
    import urllib.request
    listing = _gf_listing(google_slug(family))
    if not listing:
        return None
    ttfs = [f for f in listing if isinstance(f, dict)
            and str(f.get("name", "")).lower().endswith(".ttf")]

    def score(name: str) -> tuple:
        n = name.lower()
        italic = "italic" in n
        is_bold = "bold" in n
        variable = "[wght]" in n or "-vf" in n
        want = 0 if (is_bold == bold and not italic) else (1 if variable and not italic else 2)
        return (want, 0 if variable else 1, len(name))

    ttfs.sort(key=lambda f: score(str(f["name"])))
    if not ttfs or not ttfs[0].get("download_url"):
        return None
    chosen = ttfs[0]
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, chosen["name"])
    try:
        with urllib.request.urlopen(chosen["download_url"], timeout=30) as r:
            data = r.read()
        with open(path, "wb") as fh:
            fh.write(data)
        return path
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  Pack (produce) + install/scope (consume)                                    #
# --------------------------------------------------------------------------- #
def pack_families(families, allow_missing=False, fetch=False, cache_dir=None):
    """``(manifest_entries, {arc: src_path}, missing)`` for a set of families.
    With ``fetch=True``, a family that does not resolve locally is provisioned
    from Google Fonts and stamped ``source: "google-fonts:<slug>"``."""
    entries, files, missing = [], {}, []
    cache = cache_dir or tempfile.mkdtemp(prefix="fg-gf-")
    for fam in sorted(families):
        for bold in (False, True):
            resolved, matched, path = _resolve(fam, bold)
            source = "local"
            if not path and fetch:
                path = fetch_google_font(fam, bold, cache)
                if path:
                    resolved, source = fam, f"google-fonts:{google_slug(fam)}"
            if not path or not os.path.isfile(path):
                if not bold:
                    missing.append(fam)
                continue
            arc = "fonts/" + os.path.basename(path)
            files[arc] = path
            entries.append({"family": fam, "bold": bold, "file": arc,
                            "resolved": resolved, "sha256": _sha256(path), "source": source})
    return entries, files, missing


def install_pack(pack_path: str, dest_dir: str) -> tuple[str, int]:
    """Extract a ``.fp`` into ``dest_dir`` (verifying every sha256) and write a
    scoped ``fonts.conf`` adding its ``fonts/`` on top of the system config.
    Returns ``(conf_path, face_count)``; raises ValueError on a hash mismatch."""
    dest = os.path.abspath(dest_dir)
    fonts_dir = os.path.join(dest, "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    with zipfile.ZipFile(pack_path) as z:
        manifest = json.loads(z.read("manifest.json"))
        for entry in manifest.get("fonts", []):
            data = z.read(entry["file"])
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError(f"sha256 mismatch for {entry['file']} — pack corrupt/tampered")
            with open(os.path.join(fonts_dir, os.path.basename(entry["file"])), "wb") as fh:
                fh.write(data)
    conf = os.path.join(dest, "fonts.conf")
    with open(conf, "w") as fh:
        fh.write('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
                 f'<fontconfig>\n  <dir>{fonts_dir}</dir>\n'
                 f'  <cachedir>{os.path.join(dest, "cache")}</cachedir>\n'
                 '  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n</fontconfig>\n')
    if shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", fonts_dir],
                       env={**os.environ, "FONTCONFIG_FILE": conf}, capture_output=True, check=False)
    return conf, len(manifest.get("fonts", []))


def scope_font_pack(pack_path: str) -> str:
    """Install a ``.fp`` into a temp dir and point THIS process's fontconfig (and,
    by clearing its caches, `font_metrics`) at it — so measure and any subprocess
    rasterizer launched afterwards resolve the packed faces. Returns the temp dir.
    Call it *before* launching Chromium/cairo (a render CLI's ``--font-pack``)."""
    tmp = tempfile.mkdtemp(prefix="fg-fontpack-")
    conf, _ = install_pack(pack_path, tmp)
    os.environ["FONTCONFIG_FILE"] = conf
    try:
        FM.clear_cache()
    except Exception:
        pass
    return tmp


# --------------------------------------------------------------------------- #
#  Subcommands + CLI                                                           #
# --------------------------------------------------------------------------- #
def cmd_list(_args) -> int:
    if shutil.which("fc-list") is None:
        print("fc-list not available — cannot enumerate fonts", file=sys.stderr)
        return 2
    out = subprocess.run(["fc-list", "-f", "%{family}\n"], capture_output=True,
                         text=True, check=False).stdout
    families = sorted({ln.split(",")[0].strip() for ln in out.splitlines() if ln.strip()})
    print(f"# {len(families)} resolvable families in this runtime "
          f"(reference these, or pin+pack a font):")
    for fam in families:
        print(fam)
    return 0


def cmd_check(args) -> int:
    doc = yaml.safe_load(open(args.doc, encoding="utf-8"))
    families = sorted(referenced_families(doc))
    fetch = getattr(args, "fetch", False)
    subs, fetchable = [], []
    for fam in families:
        resolved, matched, _ = _resolve(fam, False)
        if matched:
            print(f"  [{'ok':^11}] {fam!r:32} -> {resolved!r}")
        elif fetch and google_available(fam):
            fetchable.append(fam)
            print(f"  [{'FETCHABLE':^11}] {fam!r:32} -> {'google-fonts:' + google_slug(fam)!r}")
        else:
            subs.append(fam)
            print(f"  [{'SUBSTITUTED':^11}] {fam!r:32} -> {resolved!r}")
    if subs:
        tail = "" if fetch else " (or --fetch to accept families provisionable from Google Fonts)"
        print(f"\nFAIL: {len(subs)} content font(s) will be SUBSTITUTED — layout measured a "
              f"different face than the rasterizer draws (justified/wrapped text will diverge). "
              f"Pin + pack them (`fg-font --pack`) or install them{tail}.", file=sys.stderr)
        return 1
    if fetchable:
        print(f"\nOK: all {len(families)} families resolve — {len(fetchable)} via Google Fonts; run "
              f"`fg-font --pack --fetch` to pin them so measure == render everywhere.")
        return 0
    print(f"\nOK: all {len(families)} referenced families resolve to themselves (measure == render).")
    return 0


def cmd_pack(args) -> int:
    doc = yaml.safe_load(open(args.doc, encoding="utf-8"))
    entries, files, missing = pack_families(referenced_families(doc), args.allow_missing,
                                            fetch=args.fetch)
    if missing and not args.allow_missing:
        hint = ("" if args.fetch else " (or --fetch to pull them from Google Fonts)")
        print(f"FAIL: cannot pin {missing} (not installed / substituted / not on Google Fonts). "
              f"Install them{hint}, or pass --allow-missing to pack what resolves.", file=sys.stderr)
        return 1
    manifest = {"fp_version": 1, "generated_from": os.path.basename(args.doc), "fonts": entries}
    out = args.out or (os.path.splitext(args.doc)[0] + ".fp")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        for arc, path in sorted(files.items()):
            z.write(path, arc)
    print(f"wrote {out}: {len(entries)} face(s), {len(files)} file(s) "
          f"({len({e['family'] for e in entries})} families)")
    return 0


def cmd_install(args) -> int:
    try:
        conf, n = install_pack(args.install, args.dir)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"installed {n} face(s) → {os.path.join(os.path.abspath(args.dir), 'fonts')}")
    print(f"export FONTCONFIG_FILE={conf}   # then measure (font_metrics) == render (rasterizer)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fg-font", description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true", help="list resolvable families")
    ap.add_argument("--check", metavar="DOC", help="fail if a content font substitutes")
    ap.add_argument("--pack", metavar="DOC", help="bundle a doc's fonts into a .fp pack")
    ap.add_argument("--install", metavar="P.fp", help="extract a .fp into a scoped fontconfig")
    ap.add_argument("--dir", help="target dir (with --install)")
    ap.add_argument("--out", help="output .fp path (with --pack)")
    ap.add_argument("--fetch", action="store_true",
                    help="Google Fonts proxy: with --pack, provision missing families; "
                         "with --check, accept families provisionable from Google Fonts")
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
    if args.install:
        if not args.dir:
            ap.error("--install requires --dir")
        return cmd_install(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
