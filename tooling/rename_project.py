#!/usr/bin/env python3
"""rename_project.py — mechanically rename this codebase's identifier.

Rewrites the coined token ``framegraph`` (in every case variant) to
``frameforge`` across file *contents* and across file/directory *names*, then
reports exactly what it did. This is a purely mechanical string+path operation:
it does not understand code, so it also touches the DSL discriminator
(``dsl: FrameGraph``), the MCP tool names (``mcp__framegraph__*``), the URI
scheme (``framegraph://``), and the env-var prefix (``FRAMEGRAPH_*``) — every
place the identifier appears is the identifier, and a mechanical rename moves all
of them together.

Safety model
------------
- **Dry run is the default.** Nothing is written unless you pass ``--apply``.
- ``--dry-run`` forces preview and *vetoes* ``--apply`` if both are given.
- The scan runs in full BEFORE any write; if any path-rename would collide with
  an existing path, the apply aborts (use ``--force`` to rename what it can).
- Binary files (PDF, PNG, fonts, …) are never content-edited; they are still
  eligible for a *name* rename.
- The tool excludes its own file so it cannot corrupt itself, plus VCS, caches,
  virtualenvs, generated output, and ``*.egg-info`` by default.

Usage
-----
    python tooling/rename_project.py                 # dry run (default)
    python tooling/rename_project.py --verbose       # dry run, full file list
    python tooling/rename_project.py --apply          # actually rewrite + rename
    python tooling/rename_project.py --from foo --to bar --apply   # reuse elsewhere

After ``--apply`` on this repo, regenerate and re-gate the derived artifacts
(schema, manifest, examples index, golden lock, docs) and reinstall the package
so ``*.egg-info`` reflects the new name — e.g. ``make schema manifest
examples-index docs`` then ``make check``. The tool does the mechanical part;
the regeneration + gate is yours to run and verify (PALS's Law).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- default identifier and its case variants ------------------------------
# Order is irrelevant (all variants are the same length and mutually exclusive
# as strings), but longest-first is used when building the regex for safety.
DEFAULT_FROM = "framegraph"
DEFAULT_TO = "frameforge"

# Explicit variant table for the default rename. Compound casing (Pascal/camel)
# needs the frame|graph -> frame|forge word split, which cannot be derived from
# the bare tokens, so it is spelled out here.
DEFAULT_PAIRS: list[tuple[str, str]] = [
    ("FRAMEGRAPH", "FRAMEFORGE"),
    ("FrameGraph", "FrameForge"),
    ("Framegraph", "Frameforge"),
    ("frameGraph", "frameForge"),
    ("framegraph", "frameforge"),
]

# Directory names pruned from the walk entirely (never scanned or renamed).
DEFAULT_EXCLUDE_DIRS: set[str] = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "_tmp", "site", ".doc-quarantine",
    "out",  # regenerated render output; rebuild after rename
}
EXCLUDE_DIR_SUFFIXES = (".egg-info",)  # e.g. src/framegraph.egg-info (regenerated)

# Extensions treated as binary (content never edited; name still renameable).
BINARY_EXT: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".tiff",
    ".pdf", ".zip", ".gz", ".tar", ".xz", ".bz2", ".7z",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".o", ".a",
    ".mp4", ".mov", ".webm", ".mp3", ".wav",
}


@dataclass
class ContentChange:
    path: Path
    occurrences: int
    residual: int = 0  # source variants still present AFTER one transform pass (idempotency probe)
    sample_lines: list[tuple[int, str, str]] = field(default_factory=list)  # (lineno, before, after)


@dataclass
class PathRename:
    src: Path
    dst: Path
    is_dir: bool
    collision: bool = False


@dataclass
class Plan:
    content: list[ContentChange] = field(default_factory=list)
    renames: list[PathRename] = field(default_factory=list)
    binary_name_hits: list[Path] = field(default_factory=list)
    skipped_binaries_scanned: int = 0
    # mapping-level idempotency defect: target variants that themselves re-match
    # the pattern (e.g. --from frame --to framegraph). Populated by main().
    mapping_violations: list[str] = field(default_factory=list)

    @property
    def total_occurrences(self) -> int:
        return sum(c.occurrences for c in self.content)

    @property
    def collisions(self) -> list[PathRename]:
        return [r for r in self.renames if r.collision]

    @property
    def residual_files(self) -> list[ContentChange]:
        """Changed files where a source variant survives one transform pass."""
        return [c for c in self.content if c.residual]

    @property
    def is_idempotent(self) -> bool:
        """True iff a second application of the transform would be a no-op.

        Two independent conditions, both required:
        - no target variant re-matches the pattern (mapping-level, data-free), and
        - no scanned file retains a source variant after one pass (empirical,
          which also catches replacement-junction artifacts the mapping check
          cannot see).
        """
        return not self.mapping_violations and not self.residual_files


def build_pairs(src: str, dst: str) -> list[tuple[str, str]]:
    """Case-variant pairs for a from/to token.

    For the default framegraph->frameforge, returns the hand-verified compound
    table. For custom tokens, derives the three unambiguous forms
    (lower / UPPER / Capitalized) — compound Pascal/camel casing for arbitrary
    tokens must be added with --pair.
    """
    if src == DEFAULT_FROM and dst == DEFAULT_TO:
        pairs = list(DEFAULT_PAIRS)
    else:
        forms = [
            (src.lower(), dst.lower()),
            (src.upper(), dst.upper()),
            (src.capitalize(), dst.capitalize()),
        ]
        seen: set[str] = set()
        pairs = []
        for a, b in forms:
            if a not in seen:
                seen.add(a)
                pairs.append((a, b))
    return pairs


def apply_pairs(text: str, mapping: dict[str, str], pattern: re.Pattern[str]) -> tuple[str, int]:
    n = 0

    def _repl(m: re.Match[str]) -> str:
        nonlocal n
        n += 1
        return mapping[m.group(0)]

    return pattern.sub(_repl, text), n


def rename_name(name: str, mapping: dict[str, str], pattern: re.Pattern[str]) -> str:
    return pattern.sub(lambda m: mapping[m.group(0)], name)


def is_excluded_dir(name: str) -> bool:
    return name in DEFAULT_EXCLUDE_DIRS or name.endswith(EXCLUDE_DIR_SUFFIXES)


def looks_binary(path: Path, data: bytes) -> bool:
    if path.suffix.lower() in BINARY_EXT:
        return True
    if b"\x00" in data[:8192]:
        return True
    return False


def scan(root: Path, mapping: dict[str, str], pattern: re.Pattern[str],
         self_path: Path, extra_excludes: set[str], samples: int) -> Plan:
    plan = Plan()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # prune excluded directories in place
        dirnames[:] = [d for d in dirnames
                       if not is_excluded_dir(d) and d not in extra_excludes]

        dpath = Path(dirpath)
        # directory-name renames (recorded here; applied bottom-up later)
        for d in dirnames:
            if pattern.search(d):
                src = dpath / d
                dst = dpath / rename_name(d, mapping, pattern)
                plan.renames.append(PathRename(src, dst, is_dir=True))

        for fn in filenames:
            fpath = dpath / fn
            if fpath.resolve() == self_path:
                continue  # never touch this tool
            # file-name rename?
            if pattern.search(fn):
                dst = dpath / rename_name(fn, mapping, pattern)
                plan.renames.append(PathRename(fpath, dst, is_dir=False))

            # content scan
            try:
                data = fpath.read_bytes()
            except (OSError, PermissionError):
                continue
            if looks_binary(fpath, data):
                plan.skipped_binaries_scanned += 1
                if pattern.search(fn):
                    plan.binary_name_hits.append(fpath)
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                plan.skipped_binaries_scanned += 1
                continue
            new_text, n = apply_pairs(text, mapping, pattern)
            if n:
                # empirical idempotency probe: after one pass, does any source
                # variant remain (or get created across a replacement junction)?
                residual = len(pattern.findall(new_text))
                change = ContentChange(fpath, n, residual=residual)
                if samples:
                    for i, line in enumerate(text.splitlines(), start=1):
                        if pattern.search(line):
                            after = pattern.sub(lambda m: mapping[m.group(0)], line)
                            change.sample_lines.append((i, line.strip(), after.strip()))
                            if len(change.sample_lines) >= samples:
                                break
                plan.content.append(change)

    # detect collisions: target already exists AND is not itself being renamed away
    rename_srcs = {r.src for r in plan.renames}
    for r in plan.renames:
        if r.dst.exists() and r.dst not in rename_srcs:
            r.collision = True
    return plan


def do_apply(plan: Plan, mapping: dict[str, str], pattern: re.Pattern[str], force: bool) -> int:
    if not plan.is_idempotent and not force:
        print("\nABORT: the transform is NOT idempotent — nothing written. "
              "Applying it twice would keep changing the tree. "
              "Fix the mapping or re-run with --force to apply anyway.",
              file=sys.stderr)
        for t in plan.mapping_violations:
            print(f"  mapping: target {t!r} still matches the source pattern", file=sys.stderr)
        for c in plan.residual_files[:20]:
            print(f"  residual: {c.residual} source variant(s) survive in {c.path}", file=sys.stderr)
        return 3
    if plan.collisions and not force:
        print(f"\nABORT: {len(plan.collisions)} path collision(s) — nothing written. "
              f"Resolve them or re-run with --force to rename what is safe.",
              file=sys.stderr)
        for r in plan.collisions:
            print(f"  collision: {r.src}  ->  {r.dst} (target exists)", file=sys.stderr)
        return 2

    # 1) rewrite contents (paths still original)
    written = 0
    for c in plan.content:
        data = c.path.read_bytes().decode("utf-8")
        new_text, _ = apply_pairs(data, mapping, pattern)
        c.path.write_bytes(new_text.encode("utf-8"))
        written += 1

    # 2) rename paths bottom-up (deepest first) so parents stay valid
    renamed = 0
    for r in sorted(plan.renames, key=lambda x: len(x.src.parts), reverse=True):
        if r.collision:
            continue
        try:
            r.src.rename(r.dst)
            renamed += 1
        except OSError as e:
            print(f"  rename failed: {r.src} -> {r.dst}: {e}", file=sys.stderr)
    print(f"\nAPPLIED: rewrote {written} files, renamed {renamed} paths "
          f"({sum(r.is_dir for r in plan.renames if not r.collision)} dirs).")
    return 0


def report(plan: Plan, root: Path, verbose: bool, apply_mode: bool) -> None:
    rel = lambda p: p.relative_to(root)  # noqa: E731
    head = "PLAN (apply)" if apply_mode else "DRY RUN — no files will be written"
    print(f"=== {head} ===\n")

    # content changes
    changed = sorted(plan.content, key=lambda c: c.occurrences, reverse=True)
    print(f"Content changes: {len(changed)} files, {plan.total_occurrences} occurrences")
    limit = len(changed) if verbose else min(40, len(changed))
    for c in changed[:limit]:
        print(f"  {c.occurrences:5d}  {rel(c.path)}")
        if verbose:
            for lineno, before, after in c.sample_lines:
                print(f"         L{lineno}: {before}")
                print(f"           ->  {after}")
    if not verbose and len(changed) > limit:
        rest = changed[limit:]
        print(f"  ... and {len(rest)} more files ({sum(c.occurrences for c in rest)} occurrences) "
              f"[--verbose for the full list]")

    # path renames (always listed in full — small set)
    print(f"\nPath renames: {len(plan.renames)} "
          f"({sum(r.is_dir for r in plan.renames)} dirs, "
          f"{sum(not r.is_dir for r in plan.renames)} files)")
    for r in sorted(plan.renames, key=lambda x: str(x.src)):
        flag = "  <-- COLLISION (target exists)" if r.collision else ""
        kind = "dir " if r.is_dir else "file"
        print(f"  {kind}  {rel(r.src)}  ->  {rel(r.dst)}{flag}")

    # binaries whose NAME hits but content is left alone
    if plan.binary_name_hits:
        print(f"\nBinary files renamed by name only (content untouched): "
              f"{len(plan.binary_name_hits)}")
        for p in plan.binary_name_hits:
            print(f"  {rel(p)}")

    # idempotency assertion
    print("\n--- idempotency ---")
    if plan.is_idempotent:
        print("  IDEMPOTENT: a second run would be a no-op "
              "(no target variant re-matches; 0 source variants survive one pass).")
    else:
        print("  NOT IDEMPOTENT — re-applying would keep changing the tree:")
        for t in plan.mapping_violations:
            print(f"    mapping defect: target {t!r} still matches the source pattern")
        for c in plan.residual_files[:20]:
            print(f"    residual: {c.residual} source variant(s) survive in {rel(c.path)}")
        extra = len(plan.residual_files) - 20
        if extra > 0:
            print(f"    ... and {extra} more file(s) with residual matches")

    # summary
    print("\n--- summary ---")
    print(f"  files with content edits : {len(plan.content)}")
    print(f"  total string occurrences : {plan.total_occurrences}")
    print(f"  paths renamed            : {len(plan.renames)}")
    print(f"  collisions               : {len(plan.collisions)}")
    print(f"  binaries skipped (content): {plan.skipped_binaries_scanned}")
    print(f"  idempotent               : {'yes' if plan.is_idempotent else 'NO'}")
    if not apply_mode:
        print("\n  This was a DRY RUN. Re-run with --apply to write the changes.")
        if plan.collisions:
            print(f"  WARNING: {len(plan.collisions)} collision(s) would block --apply "
                  f"(or need --force).")
        if not plan.is_idempotent:
            print("  WARNING: non-idempotent transform would block --apply (or need --force).")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Mechanically rename the codebase identifier (default: framegraph -> frameforge).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    default_root = Path(__file__).resolve().parents[1]
    ap.add_argument("--root", type=Path, default=default_root,
                    help="repo root to operate on")
    ap.add_argument("--from", dest="src", default=DEFAULT_FROM,
                    help="source token (lowercase)")
    ap.add_argument("--to", dest="dst", default=DEFAULT_TO,
                    help="target token (lowercase)")
    ap.add_argument("--pair", action="append", default=[], metavar="OLD=NEW",
                    help="add/override an explicit case-variant pair (repeatable)")
    ap.add_argument("--apply", action="store_true",
                    help="actually write changes (default is a dry run)")
    ap.add_argument("--dry-run", action="store_true",
                    help="force preview only; vetoes --apply")
    ap.add_argument("--force", action="store_true",
                    help="with --apply, proceed past path collisions (rename what is safe)")
    ap.add_argument("--exclude", action="append", default=[], metavar="DIR",
                    help="additional directory name to prune (repeatable)")
    ap.add_argument("--samples", type=int, default=3,
                    help="sample changed lines to capture per file (for --verbose)")
    ap.add_argument("--verbose", action="store_true",
                    help="list every changed file and sample lines")
    ap.add_argument("--assert-idempotent", action="store_true",
                    help="exit non-zero (even in dry run) if the transform is not idempotent")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        ap.error(f"--root is not a directory: {root}")

    pairs = build_pairs(args.src, args.dst)
    for spec in args.pair:
        if "=" not in spec:
            ap.error(f"--pair must be OLD=NEW, got: {spec!r}")
        old, new = spec.split("=", 1)
        pairs = [(o, n) for (o, n) in pairs if o != old] + [(old, new)]

    mapping = {o: n for o, n in pairs}
    # longest-first alternation so no variant is shadowed by a prefix of another
    pattern = re.compile("|".join(re.escape(o) for o, _ in sorted(pairs, key=lambda p: -len(p[0]))))

    dry_run = args.dry_run or not args.apply
    self_path = Path(__file__).resolve()

    print(f"root      : {root}")
    print(f"variants  : {', '.join(f'{o}->{n}' for o, n in pairs)}")
    print(f"mode      : {'DRY RUN' if dry_run else 'APPLY'}\n")

    plan = scan(root, mapping, pattern, self_path, set(args.exclude), args.samples)
    # mapping-level idempotency precheck (data-free): does any target variant
    # itself re-match the source pattern? If so, the transform can never settle.
    plan.mapping_violations = [t for _, t in pairs if pattern.search(t)]

    report(plan, root, args.verbose, apply_mode=not dry_run)

    if args.assert_idempotent and not plan.is_idempotent:
        print("\nASSERTION FAILED: transform is not idempotent.", file=sys.stderr)
        return 4

    if dry_run:
        return 0
    return do_apply(plan, mapping, pattern, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
