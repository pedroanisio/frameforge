#!/usr/bin/env python3
"""bump_version.py — move the FrameForge HEAD version across every hand-edited site.

The package version is a single *logical* source of truth (`pyproject [project]
version`) but lives, by necessity, in four hand-edited literals that the gates
cross-check so a divergence can never ship:

  1. pyproject.toml            `version = "X.Y.Z"`          (the declared version)
  2. src/frameforge/model.py   `HEAD_VERSION = "X.Y.Z"`     (the models' report)
  3. tests/test_head.py        `HEAD_VERSION == "X.Y.Z"`    (the version pin)
  4. README.md                 `**FrameForge v2** (`X.Y.Z`)`(the human headline)

`tests/test_head.py` pins (2)==(3) and generated-in-sync schema; `tests/
test_docs_in_sync.py` pins (1)==(2) and the schema title. So `make check` FAILS
on any half-bump — this tool just moves all four together so it passes first try.

It does NOT regenerate derived artifacts (schema / manifest / docs) or edit the
CHANGELOG — the `make bump` target chains the regen, and the CHANGELOG entry is a
human judgement. See RELEASE.md for the full procedure.

Usage::

    python tooling/bump_version.py 2.4.0            # rewrite all four sites
    python tooling/bump_version.py 2.4.0 --dry-run  # show the edits, write nothing
    python tooling/bump_version.py --check          # assert the four sites agree

Exit: 0 = done / in sync, 1 = mismatch (--check) or bad input, 2 = a site not found.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# Prose/comments that hardcode the version but are NOT gated (RELEASE.md §7). We
# don't rewrite them — prose is context-sensitive — but we list them so a bump
# doesn't silently leave a stale "v2.3.0" in a demo or a doc.
COSMETIC_GLOBS = ("static/examples/*.py", "skills/**/*.md", "skills/**/*.py",
                  "plugin/skills/**/*.md")

# (label, path, regex with a `(pre)(version)(post)` shape). The version group (2)
# is the only thing rewritten, so surrounding text/comments are preserved.
SITES = [
    ("pyproject.toml", "pyproject.toml",
     re.compile(r'^(version = ")(\d+\.\d+\.\d+)(")', re.M)),
    ("models HEAD_VERSION", "src/frameforge/model.py",
     re.compile(r'^(HEAD_VERSION = ")(\d+\.\d+\.\d+)(")', re.M)),
    ("test_head pin", "tests/test_head.py",
     re.compile(r'(HEAD_VERSION == ")(\d+\.\d+\.\d+)(")')),
    ("README headline", "README.md",
     re.compile(r'(\*\*FrameForge v2\*\* \(`)(\d+\.\d+\.\d+)(`\))')),
    ("package __version__", "src/frameforge/__init__.py",
     re.compile(r'^(__version__ = ")(\d+\.\d+\.\d+)(")', re.M)),
    # Claude Code plugin. The manifest version is what pins an installed plugin:
    # Claude Code only re-fetches when this string changes, so a missed bump
    # strands every installed user on the previous release.
    ("plugin manifest", "plugin/.claude-plugin/plugin.json",
     re.compile(r'^(  "version": ")(\d+\.\d+\.\d+)(")', re.M)),
    # The runtime image tag the plugin launches. Must move with the release or
    # the plugin serves a stale toolchain against a current manifest.
    ("plugin runtime image", "plugin/.claude-plugin/plugin.json",
     re.compile(r'(ghcr\.io/pedroanisio/frameforge:)(\d+\.\d+\.\d+)(")')),
    ("marketplace manifest", ".claude-plugin/marketplace.json",
     re.compile(r'^(  "version": ")(\d+\.\d+\.\d+)(")', re.M)),
]


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _current() -> dict[str, str | None]:
    """The version literal found at each site (None if the pattern is missing)."""
    found: dict[str, str | None] = {}
    for label, rel, rx in SITES:
        m = rx.search(_read(rel))
        found[label] = m.group(2) if m else None
    return found


def check() -> int:
    found = _current()
    missing = [lbl for lbl, v in found.items() if v is None]
    if missing:
        print(f"bump_version: SITE NOT FOUND — {', '.join(missing)} "
              "(pattern drifted; update tooling/bump_version.py:SITES)")
        return 2
    distinct = set(found.values())
    if len(distinct) == 1:
        print(f"bump_version: OK — all {len(found)} version sites agree at {distinct.pop()}")
        return 0
    print("bump_version: MISMATCH — version sites disagree:")
    for lbl, v in found.items():
        print(f"    {v}   {lbl}")
    return 1


def _cosmetic_sweep(old: str) -> list[tuple[str, int]]:
    """Ungated files that still mention the old version literal (prose/comments)."""
    hits: list[tuple[str, int]] = []
    for pat in COSMETIC_GLOBS:
        for path in glob.glob(os.path.join(ROOT, pat), recursive=True):
            try:
                n = open(path, encoding="utf-8").read().count(old)
            except OSError:
                continue
            if n:
                hits.append((os.path.relpath(path, ROOT), n))
    return sorted(hits)


def bump(new: str, dry_run: bool) -> int:
    if not _SEMVER.match(new):
        print(f"bump_version: '{new}' is not a MAJOR.MINOR.PATCH version")
        return 1
    old = _current().get("pyproject.toml")
    rc = 0
    for label, rel, rx in SITES:
        text = _read(rel)
        m = rx.search(text)
        if not m:
            print(f"bump_version: SITE NOT FOUND — {label} ({rel})")
            rc = 2
            continue
        old = m.group(2)
        if old == new:
            print(f"  ={new}  {label} ({rel}) — already at target")
            continue
        updated = rx.sub(lambda mm: mm.group(1) + new + mm.group(3), text, count=1)
        print(f"  {old} -> {new}  {label} ({rel})")
        if not dry_run:
            with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as fh:
                fh.write(updated)
    if dry_run:
        print("\nbump_version: --dry-run, nothing written.")
        return rc
    if rc == 0:
        print(f"\nbump_version: rewrote {len(SITES)} sites to {new}.\n"
              "Next (see RELEASE.md): make schema manifest examples-index  ·  "
              "update CHANGELOG.md  ·  make check  ·  make docker-build")
        cosmetic = _cosmetic_sweep(old) if old and old != new else []
        if cosmetic:
            print(f"\n  ungated: {old} still appears in prose/comments (review by hand, RELEASE.md §7):")
            for rel, n in cosmetic:
                print(f"    {n}x  {rel}")
    return rc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Move the FrameForge HEAD version across every hand-edited site.")
    ap.add_argument("version", nargs="?", help="new MAJOR.MINOR.PATCH version")
    ap.add_argument("--check", action="store_true", help="assert the sites agree; do not edit")
    ap.add_argument("--dry-run", action="store_true", help="show edits, write nothing")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    if not args.version:
        ap.error("give a version (e.g. 2.4.0) or --check")
    return bump(args.version, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
