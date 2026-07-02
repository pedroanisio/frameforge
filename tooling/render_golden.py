#!/usr/bin/env python3
"""render_golden.py — golden-render harness for the b1/ authoritative oracle.

Roadmap item 4 / codebase-standards §8: pin each oracle fixture's per-page SVG
output so any change in rendered output is caught as a potential regression. The
b1/ set is the project's oracle (the fixtures `tests/test_head.py` asserts), so it
is the right thing to freeze.

This stores a compact **hash lock** — one JSON of per-page SHA-256 digests — as the
**primary** gate (`--check`, the default): exact-match, full sensitivity, a tiny
diffable file. Alongside it, a **reference render** of each page is committed under
`tests/golden/refs/` as a **tolerance oracle**: when a page's hash differs, the
fresh render is compared *numerically* against its reference within a coordinate
tolerance (`--tolerance`, default 0.5), so a hash mismatch is classified —

  - **cosmetic** (non-numeric skeleton identical; every number within ±ε): reported,
    not a failure — the kind of sub-pixel float jitter the exact hash over-reports;
  - **real drift** (skeleton differs, a number moves beyond ±ε, or page/ref missing):
    a failure, exactly as before.

`--strict` treats cosmetic drift as a failure too (pure exact mode). `--update`
re-pins both the lock and the reference renders. The tolerance is *numeric only*
(coordinate/value jitter); pixel/font/AA perceptual tolerance would need a raster
backend and is out of scope here.

Rendering goes through the Renderer API (decoupled from the CLI output layout) and
is deterministic (no clock/random in the renderer). Exit: 0 = within tolerance,
1 = real drift or missing lock, 2 = internal error. Mirrors the repo's other gates.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)  # import the renderer (which itself puts ROOT on sys.path)

import yaml  # noqa: E402
from render_fixtures import Renderer  # noqa: E402

# The authoritative oracle: b1/*.fg.json (the fixtures test_head.py asserts).
ORACLE_GLOB = os.path.join(ROOT, "tests", "fixtures", "b1", "*.fg.json")
LOCK = os.path.join(ROOT, "tests", "golden", "oracle.lock.json")
REFS = os.path.join(ROOT, "tests", "golden", "refs")
DEFAULT_TOLERANCE = 0.5

# A signed integer/decimal/scientific number — the unit compared with tolerance.
_NUM = re.compile(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?")


def _page_svgs(path: str) -> list[str]:
    """Render one fixture and return the emitted SVG string per page, in order."""
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)            # safe_load parses both JSON and YAML
    # real_metrics=False pins estimate-mode text measurement: an explicit bool
    # always wins over FRAMEGRAPH_REAL_METRICS, so a user's env var cannot cause
    # spurious golden drift (the lock is byte-exact estimate-mode output).
    # FRAMEGRAPH_MATH_SVG=fallback pins math the same way: golden hashes must not
    # depend on whether the optional node + viewer/node_modules MathJax toolchain
    # resolves on this machine (CI never installs it). Scoped + restored so a
    # shared pytest process does not inherit the override.
    previous = os.environ.get("FRAMEGRAPH_MATH_SVG")
    os.environ["FRAMEGRAPH_MATH_SVG"] = "fallback"
    try:
        r = Renderer(doc, os.path.dirname(path), real_metrics=False)
        svgs: list[str] = []
        for page in (doc.get("pages") or []):
            svgs.extend(r.render_page(page))
        return svgs
    finally:
        if previous is None:
            os.environ.pop("FRAMEGRAPH_MATH_SVG", None)
        else:
            os.environ["FRAMEGRAPH_MATH_SVG"] = previous


def build_svgs() -> dict[str, list[str]]:
    """`{fixture-rel-path: [per-page svg]}` for the whole oracle, sorted."""
    return {
        os.path.relpath(path, ROOT): _page_svgs(path)
        for path in sorted(glob.glob(ORACLE_GLOB))
    }


def _hash(svg: str) -> str:
    return hashlib.sha256(svg.encode("utf-8")).hexdigest()


def build() -> dict[str, list[str]]:
    """`{fixture-rel-path: [per-page sha256]}` — the hash manifest (primary gate)."""
    return {k: [_hash(s) for s in svgs] for k, svgs in build_svgs().items()}


def _ref_path(fixture_relpath: str, page_index: int) -> str:
    """Committed reference-render path for one page (1-based filename)."""
    stem = os.path.basename(fixture_relpath).split(".")[0]
    return os.path.join(REFS, stem, f"p{page_index + 1:03d}.svg")


def within_tolerance(ref: str, cur: str, eps: float) -> bool:
    """True when `cur` differs from `ref` only by numeric jitter within ±eps.

    The non-numeric *skeleton* (everything between the numbers) must match exactly;
    every paired number must be within eps. A differing skeleton, a different count
    of numbers, or any number beyond eps is real drift (False). Because eps < 1, any
    integer change (a colour digit, an id, an added segment) is caught — only
    sub-eps coordinate jitter passes.
    """
    if ref == cur:
        return True
    ref_skeleton, cur_skeleton = _NUM.split(ref), _NUM.split(cur)
    if ref_skeleton != cur_skeleton:
        return False
    ref_nums, cur_nums = _NUM.findall(ref), _NUM.findall(cur)
    if len(ref_nums) != len(cur_nums):
        return False
    return all(abs(float(a) - float(b)) <= eps for a, b in zip(ref_nums, cur_nums))


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


def write_refs(svgs_by_fixture: dict[str, list[str]]) -> None:
    """Re-pin the reference renders (the tolerance oracle). Stale page files from a
    shorter render are removed so a dropped page cannot leave an orphan reference."""
    for fixture, svgs in svgs_by_fixture.items():
        stem = os.path.basename(fixture).split(".")[0]
        d = os.path.join(REFS, stem)
        os.makedirs(d, exist_ok=True)
        for old in glob.glob(os.path.join(d, "p*.svg")):
            os.remove(old)
        for i, svg in enumerate(svgs):
            with open(_ref_path(fixture, i), "w", encoding="utf-8") as fh:
                fh.write(svg)


def diff(current: dict, locked: dict) -> list[str]:
    """Hash-level drift between the freshly rendered and locked manifests (the exact,
    pre-tolerance comparison). `classify` layers the tolerance band on top of this."""
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


def classify(svgs_by_fixture: dict, locked: dict, eps: float) -> tuple[list[str], list[str]]:
    """Split drift into (real, cosmetic) lines by comparing each hash-mismatched page
    against its committed reference within ±eps."""
    current = {k: [_hash(s) for s in svgs] for k, svgs in svgs_by_fixture.items()}
    real: list[str] = []
    cosmetic: list[str] = []
    for missing in sorted(set(locked) - set(current)):
        real.append(f"  removed: {missing} (in lock, not rendered)")
    for added in sorted(set(current) - set(locked)):
        real.append(f"  new: {added} (rendered, not in lock — run --update)")
    for k in sorted(set(current) & set(locked)):
        cur, lock = current[k], locked[k]
        if cur == lock:
            continue
        if len(cur) != len(lock):
            real.append(f"  {k}: page count {len(lock)} -> {len(cur)}")
        for i in range(min(len(cur), len(lock))):
            if cur[i] == lock[i]:
                continue
            ref_file = _ref_path(k, i)
            if not os.path.exists(ref_file):
                real.append(f"  {k} page {i + 1}: render changed (no reference — run --update)")
                continue
            with open(ref_file, encoding="utf-8") as fh:
                ref_svg = fh.read()
            if within_tolerance(ref_svg, svgs_by_fixture[k][i], eps):
                cosmetic.append(f"  {k} page {i + 1}: within ±{eps} (cosmetic numeric jitter)")
            else:
                real.append(f"  {k} page {i + 1}: render changed beyond ±{eps}")
    return real, cosmetic


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true",
                    help="re-pin the lock AND the reference renders to the current output")
    ap.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE,
                    help=f"coordinate tolerance band for cosmetic drift (default {DEFAULT_TOLERANCE})")
    ap.add_argument("--strict", action="store_true",
                    help="treat cosmetic (within-tolerance) drift as a failure too (pure exact mode)")
    args = ap.parse_args(argv)

    try:
        svgs = build_svgs()
    except Exception as e:  # noqa: BLE001 — surface any renderer breakage clearly
        print(f"render_golden: internal error: {e}", file=sys.stderr)
        return 2

    n_pages = sum(len(v) for v in svgs.values())
    if args.update:
        write_lock({k: [_hash(s) for s in v] for k, v in svgs.items()})
        write_refs(svgs)
        print(f"render_golden: wrote {os.path.relpath(LOCK, ROOT)} + references under "
              f"{os.path.relpath(REFS, ROOT)} ({len(svgs)} fixtures, {n_pages} pages)")
        return 0

    locked = load_lock()
    if locked is None:
        print(f"render_golden: no lock at {os.path.relpath(LOCK, ROOT)}; "
              f"create it with `make golden`", file=sys.stderr)
        return 1

    real, cosmetic = classify(svgs, locked, args.tolerance)
    if real or (args.strict and cosmetic):
        print("render_golden: DRIFT — rendered output differs from the golden lock:")
        print("\n".join(real + (cosmetic if args.strict else [])))
        print("\nIf this change is intentional, re-pin with: make golden")
        return 1

    if cosmetic:
        print(f"render_golden: OK (within ±{args.tolerance}) — {len(cosmetic)} page(s) drifted "
              f"cosmetically; re-pin with `make golden` to refresh the lock:")
        print("\n".join(cosmetic))
        return 0

    print(f"render_golden: OK — {len(svgs)} oracle fixtures, {n_pages} pages match the lock")
    return 0


if __name__ == "__main__":
    sys.exit(main())
