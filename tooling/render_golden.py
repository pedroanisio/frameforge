#!/usr/bin/env python3
"""render_golden.py — golden-render harness for the b1/ authoritative oracle.

Roadmap item 4 / codebase-standards §8: pin each oracle fixture's per-page SVG
output so any change in rendered output is caught as a potential regression. The
b1/ set is the project's oracle (the fixtures `tests/test_head.py` asserts), so it
is the right thing to freeze.

Rather than commit ~85 SVG files (large, churny diffs), this stores a compact
**hash lock** — one JSON of per-page SHA-256 digests. The gate (`--check`, the
default) re-renders and compares, naming any drifted fixture/page; `--update`
re-pins the lock after an intentional render change.

Rendering goes through the Renderer API (decoupled from the CLI output layout) and
is deterministic (no clock/random in the renderer). Exit: 0 = matches the lock,
1 = drift or missing lock, 2 = internal error. Mirrors the repo's other gates.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)  # import the renderer (which itself puts ROOT on sys.path)

import yaml  # noqa: E402
from render_fixtures import Renderer  # noqa: E402

# The authoritative oracle: b1/*.fg.json (the fixtures test_head.py asserts).
ORACLE_GLOB = os.path.join(ROOT, "fixtures", "b1", "*.fg.json")
LOCK = os.path.join(ROOT, "tests", "golden", "oracle.lock.json")


def _page_hashes(path: str) -> list[str]:
    """Render one fixture and return a SHA-256 per emitted SVG page, in order."""
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)            # safe_load parses both JSON and YAML
    r = Renderer(doc, os.path.dirname(path))
    hashes: list[str] = []
    for page in (doc.get("pages") or []):
        for svg in r.render_page(page):
            hashes.append(hashlib.sha256(svg.encode("utf-8")).hexdigest())
    return hashes


def build() -> dict[str, list[str]]:
    """`{fixture-rel-path: [per-page sha256]}` for the whole oracle, sorted."""
    return {
        os.path.relpath(path, ROOT): _page_hashes(path)
        for path in sorted(glob.glob(ORACLE_GLOB))
    }


def load_lock():
    if not os.path.exists(LOCK):
        return None
    with open(LOCK, encoding="utf-8") as fh:
        return json.load(fh)


def write_lock(manifest: dict) -> None:
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    with open(LOCK, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")


def diff(current: dict, locked: dict) -> list[str]:
    """Human-readable drift between the freshly rendered and locked manifests."""
    lines = []
    for missing in sorted(set(locked) - set(current)):
        lines.append(f"  removed: {missing} (in lock, not rendered)")
    for added in sorted(set(current) - set(locked)):
        lines.append(f"  new: {added} (rendered, not in lock — run --update)")
    for k in sorted(set(current) & set(locked)):
        cur, lock = current[k], locked[k]
        if cur == lock:
            continue
        if len(cur) != len(lock):
            lines.append(f"  {k}: page count {len(lock)} -> {len(cur)}")
        for i in range(min(len(cur), len(lock))):
            if cur[i] != lock[i]:
                lines.append(f"  {k} page {i + 1}: render changed")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true", help="re-pin the lock to the current renders")
    args = ap.parse_args(argv)

    try:
        current = build()
    except Exception as e:  # noqa: BLE001 — surface any renderer breakage clearly
        print(f"render_golden: internal error: {e}", file=sys.stderr)
        return 2

    n_pages = sum(len(v) for v in current.values())
    if args.update:
        write_lock(current)
        print(f"render_golden: wrote {os.path.relpath(LOCK, ROOT)} "
              f"({len(current)} fixtures, {n_pages} pages)")
        return 0

    locked = load_lock()
    if locked is None:
        print(f"render_golden: no lock at {os.path.relpath(LOCK, ROOT)}; "
              f"create it with `make golden`", file=sys.stderr)
        return 1

    drift = diff(current, locked)
    if drift:
        print("render_golden: DRIFT — rendered output differs from the golden lock:")
        print("\n".join(drift))
        print("\nIf this change is intentional, re-pin with: make golden")
        return 1

    print(f"render_golden: OK — {len(current)} oracle fixtures, {n_pages} pages match the lock")
    return 0


if __name__ == "__main__":
    sys.exit(main())
