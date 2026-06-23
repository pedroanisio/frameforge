#!/usr/bin/env python3
"""install_fonts.py — install a curated set of advanced typefaces for the renderers.

The SVG proxy (cairosvg), the browser viewer and the LaTeX backend all resolve a
document's ``font_family`` *by name* through the OS font stack (fontconfig on
Linux). If a named family isn't installed it silently falls back to a generic
serif/sans, so a deck that asks for ``IBM Plex Serif`` renders in DejaVu/Times.

This script downloads a curated catalogue of modern, OpenType-rich, mostly
*variable* fonts from the open ``google/fonts`` repository and installs them into
the per-user font directory, then rebuilds the font cache. Stdlib only — no pip
deps — so it runs in a bare environment.

Usage::

    uv run python tooling/install_fonts.py                 # install the whole catalogue
    uv run python tooling/install_fonts.py --list          # print the catalogue, install nothing
    uv run python tooling/install_fonts.py --only "Inter,Fraunces,JetBrains Mono"
    uv run python tooling/install_fonts.py --category serif # one group only
    uv run python tooling/install_fonts.py --static-only    # skip variable faces, grab static weights
    uv run python tooling/install_fonts.py --dest ~/.fonts --force --dry-run

A ``GITHUB_TOKEN`` in the environment is used (if present) to lift the anonymous
API rate limit. Exit code is non-zero if any requested family fails to install.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import urllib.error
import urllib.request

API = "https://api.github.com/repos/google/fonts/contents"
LICENSES = ("ofl", "apache", "ufl")
# Static weights worth keeping when a family has no variable file.
WANT_STATIC = {"Regular", "Italic", "Medium", "MediumItalic", "SemiBold",
               "SemiBoldItalic", "Bold", "BoldItalic"}

# Catalogue of advanced faces, grouped. Each entry is (family label, google/fonts slug).
CATALOG: dict[str, list[tuple[str, str]]] = {
    "sans": [
        ("Inter", "inter"),
        ("IBM Plex Sans", "ibmplexsans"),
        ("Source Sans 3", "sourcesans3"),
        ("Work Sans", "worksans"),
        ("Manrope", "manrope"),
        ("Sora", "sora"),
        ("Space Grotesk", "spacegrotesk"),
        ("Archivo", "archivo"),
        ("Epilogue", "epilogue"),
        ("Libre Franklin", "librefranklin"),
        ("Plus Jakarta Sans", "plusjakartasans"),
        ("Be Vietnam Pro", "bevietnampro"),
        ("Figtree", "figtree"),
        ("DM Sans", "dmsans"),
    ],
    "serif": [
        ("IBM Plex Serif", "ibmplexserif"),
        ("Source Serif 4", "sourceserif4"),
        ("Fraunces", "fraunces"),
        ("Newsreader", "newsreader"),
        ("Spectral", "spectral"),
        ("Lora", "lora"),
        ("Literata", "literata"),
        ("Crimson Pro", "crimsonpro"),
        ("Playfair Display", "playfairdisplay"),
        ("Bricolage Grotesque", "bricolagegrotesque"),
        ("Instrument Serif", "instrumentserif"),
    ],
    "mono": [
        ("JetBrains Mono", "jetbrainsmono"),
        ("IBM Plex Mono", "ibmplexmono"),
        ("Fira Code", "firacode"),
        ("Space Mono", "spacemono"),
        ("Red Hat Mono", "redhatmono"),
    ],
}


def _request(url: str) -> bytes:
    headers = {"User-Agent": "framegraph-install-fonts", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _list_dir(slug: str) -> list[dict] | None:
    """Return the directory listing for a font slug, trying each license folder."""
    for lic in LICENSES:
        try:
            data = _request(f"{API}/{lic}/{slug}")
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429):
                raise SystemExit("GitHub API rate limit hit — set GITHUB_TOKEN and retry.")
            continue
        except urllib.error.URLError as exc:
            raise SystemExit(f"network error: {exc}")
        return json.loads(data)
    return None


def _choose(files: list[dict], *, static_only: bool, all_weights: bool,
            include_italic: bool) -> list[dict]:
    ttf = [f for f in files if f.get("name", "").lower().endswith(".ttf")]
    variable = [f for f in ttf if "[" in f["name"]]
    if variable and not static_only:
        chosen = variable
    else:
        chosen = []
        for f in ttf:
            if "[" in f["name"]:
                continue
            stem = f["name"].rsplit(".", 1)[0]
            token = stem.split("-")[-1] if "-" in stem else "Regular"
            if all_weights or token in WANT_STATIC:
                chosen.append(f)
    if not include_italic:
        non_italic = [f for f in chosen if "italic" not in f["name"].lower()]
        chosen = non_italic or chosen  # never return empty if a face is italic-only
    return chosen


def _download(url: str, path: str) -> int:
    data = _request(url)
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)


def _selected(args) -> list[tuple[str, str]]:
    if args.only:
        wanted = {n.strip().lower() for n in args.only.split(",") if n.strip()}
        out = [(lbl, slug) for grp in CATALOG.values() for (lbl, slug) in grp
               if lbl.lower() in wanted or slug in wanted]
        missing = wanted - {lbl.lower() for lbl, _ in out} - {slug for _, slug in out}
        for m in sorted(missing):
            print(f"  ! not in catalogue: {m}")
        return out
    if args.category:
        return list(CATALOG.get(args.category, []))
    return [pair for grp in CATALOG.values() for pair in grp]


def _font_dir(dest: str | None) -> str:
    if dest:
        return os.path.expanduser(dest)
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Fonts/framegraph")
    return os.path.expanduser("~/.local/share/fonts/fg")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Install a curated set of advanced fonts.")
    ap.add_argument("--dest", help="install directory (default: ~/.local/share/fonts/fg)")
    ap.add_argument("--only", help="comma-separated family names or slugs to install")
    ap.add_argument("--category", choices=sorted(CATALOG), help="install one group only")
    ap.add_argument("--static-only", action="store_true", help="skip variable faces; fetch static weights")
    ap.add_argument("--all-weights", action="store_true", help="for static families, fetch every weight")
    ap.add_argument("--no-italic", action="store_true", help="skip italic faces")
    ap.add_argument("--force", action="store_true", help="re-download files that already exist")
    ap.add_argument("--no-cache", action="store_true", help="don't run fc-cache afterwards")
    ap.add_argument("--dry-run", action="store_true", help="resolve and report, download nothing")
    ap.add_argument("--list", action="store_true", help="print the catalogue and exit")
    args = ap.parse_args(argv)

    if args.list:
        for cat, fonts in CATALOG.items():
            print(f"\n{cat.upper()}")
            for lbl, slug in fonts:
                print(f"  {lbl:24s} ({slug})")
        total = sum(len(v) for v in CATALOG.values())
        print(f"\n{total} families. Install all: uv run python tooling/install_fonts.py")
        return 0

    dest = _font_dir(args.dest)
    if not args.dry_run:
        os.makedirs(dest, exist_ok=True)
    families = _selected(args)
    if not families:
        print("nothing selected.")
        return 1

    print(f"Installing {len(families)} families -> {dest}\n")
    installed = downloaded = failed = 0
    for label, slug in families:
        listing = _list_dir(slug)
        if not listing:
            print(f"  FAIL {label}: not found in google/fonts")
            failed += 1
            continue
        chosen = _choose(listing, static_only=args.static_only, all_weights=args.all_weights,
                         include_italic=not args.no_italic)
        if not chosen:
            print(f"  FAIL {label}: no usable .ttf face")
            failed += 1
            continue
        kind = "variable" if any("[" in f["name"] for f in chosen) else "static"
        print(f"  {label}  [{kind}, {len(chosen)} file(s)]")
        for f in chosen:
            path = os.path.join(dest, f["name"])
            if args.dry_run:
                print(f"      - {f['name']}")
                continue
            if os.path.exists(path) and not args.force:
                print(f"      = {f['name']} (exists)")
                continue
            try:
                size = _download(f["download_url"], path)
                downloaded += 1
                print(f"      + {f['name']} ({size // 1024} KB)")
            except (urllib.error.URLError, OSError) as exc:
                print(f"      ! {f['name']}: {exc}")
                failed += 1
        installed += 1

    if not args.dry_run and not args.no_cache and platform.system() != "Darwin":
        if subprocess.run(["fc-cache", "-f", dest], capture_output=True).returncode == 0:
            print("\nfont cache rebuilt (fc-cache -f).")
        else:
            print("\nwarning: fc-cache failed or unavailable.")

    print(f"\nDone: {installed} families, {downloaded} files downloaded, {failed} failures.")
    print("Verify with:  fc-list | grep -iE 'plex|inter|fraunces|jetbrains'")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
