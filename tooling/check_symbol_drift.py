#!/usr/bin/env python3
"""Prose-vs-live symbol drift gate.

The generated surfaces are already drift-proof: ``manifest-check`` proves
``docs/capability-manifest.json`` matches the live tree, ``schema-check`` proves
the schema does, ``docs-check`` proves the generated pages do. **Hand-written
prose was the hole.** ``docs/roadmap.md`` claimed "25 MCP tools" for six
releases while the registry grew to 31, and nothing failed, because no gate ever
compared an English sentence to the code.

This closes that. Two checks, both cheap and both offline:

``counts``
    Every "N MCP tools" claim in tracked Markdown must equal the live tool
    count. This is the exact drift that shipped, and it has no false positives.

``symbols``
    Every backticked snake_case identifier in tracked Markdown must resolve
    against the live symbol universe — MCP tools and prompts, SDK exports, every
    name defined anywhere under ``src/``, and every property in the generated
    schema. An identifier that resolves nowhere is either a rename that prose
    missed or a capability that was never built.

**Authority chain.** Tool and prompt names come from the *committed* capability
manifest rather than by importing the server. ``manifest-check`` already proves
that file matches the live registry, so chaining off it keeps this gate free of
the optional ``mcp`` dependency group while inheriting the same guarantee: prose
== manifest == live tree.

The remaining names are harvested by parsing ``src/`` with ``ast`` — no imports,
so an absent optional group (opencv, playwright) can never turn a missing
extra into a phantom drift finding.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tracked_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "capability-manifest.json"
SCHEMA = ROOT / "docs" / "schema" / "frameforge-v2.schema.json"

# Generated Markdown is gated by its own generator; historical records document
# the tree as it was, so a retired name in them is accurate, not drift.
EXCLUDED_PREFIXES = (
    "tests/data/",
    "reports/",
    ".doc-quarantine/",
    "docs/posts/",
    "docs/proposals/",
    "docs/decisions/",
    "patent-reference/",
)
EXCLUDED_FILES = {
    "CHANGELOG.md",
    "docs/changelog.md",
    "docs/reference.md",
    "docs/spec.md",
    "docs/grammar.md",
    "docs/sdk.md",
    "docs/sdk-api.md",
    "docs/fixtures.md",
    "docs/examples.md",
    "docs/FIXTURE-STATUS.md",
    "FIXTURE-STATUS.md",
    "docs/library.md",
    # A migration proposal names both sides of every rename by design — the old
    # symbol is the point of the row, not a stale reference.
    "frameforge-api-rename-map.md",
}

# "N MCP tools" and the phrasings the tree actually uses.
COUNT_PATTERNS = (
    re.compile(r"\b(\d+)\s+MCP tools?\b"),
    re.compile(r"\bMCP tools?\s*\((\d+)\)"),
    re.compile(r"\b(\d+)\s+tools?\s+(?:over|via|through)\s+MCP\b"),
)

# Backticked snake_case, e.g. `run_sdk_code`. Single-word spans are excluded:
# they are overwhelmingly prose, filenames and CLI words, not API symbols.
SYMBOL_SPAN = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`")

# Names that resolve nowhere in the tree by design. Each entry states why, so
# the list stays auditable instead of becoming a silencer. The gate reports
# entries that no longer appear anywhere, so it prunes itself.
ALLOWED: dict[str, str] = {
    "forbidden_patterns": (
        "FLAM file-metadata key. CLAUDE.md specifies the vocabulary; the tree "
        "ships no FLAM reader, which CLAUDE.md states outright."
    ),
    "test_ref": "FLAM file-metadata key — see forbidden_patterns",
    "pull_request": "GitHub Actions event name, not a FrameForge symbol",
    "dry_brush": (
        "gap register: docs/frameforge-vector-recreation-improvements.md names "
        "it precisely to record that no such helper exists"
    ),
    "free_main": (
        "spec-level layout quantity. layout_engine.py names it in a comment "
        "(§3.6g) rather than binding it to an identifier."
    ),
}


def _fail(msg: str) -> None:
    print(f"check_symbol_drift: {msg}")


def prose_lines(text: str) -> list[tuple[int, str]]:
    """(line_no, line) for prose only — fenced code blocks are stripped.

    A fenced block holds *example payloads*: authored object ids, YAML keys, a
    document's own vocabulary. Those are data, not API symbols, and policing
    them would flag every tutorial. Inline backticks in prose are the surface
    where a renamed function actually goes stale unnoticed.
    """
    out: list[tuple[int, str]] = []
    fence: str | None = None
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if fence is None:
            if stripped.startswith(("```", "~~~")):
                fence = stripped[:3]
                continue
            out.append((line_no, line))
        elif stripped.startswith(fence):
            fence = None
    return out


def local_names(text: str) -> set[str]:
    """Identifiers a document introduces itself, in its own examples.

    A tutorial that builds ``ink_left`` in a code block and then discusses it in
    the next paragraph is not drifting — the name is defined right there. Same
    for a spec naming an intermediate quantity, or a README walking through its
    own sample deck. Scoping these per-document keeps the gate precise without
    excluding whole directories, so a tutorial that *does* name a renamed tool
    still fails.
    """
    names: set[str] = set()
    fence: str | None = None
    in_front_matter = False
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if line_no == 1 and stripped == "---":
            in_front_matter = True
            continue
        if in_front_matter:
            if stripped == "---":
                in_front_matter = False
            else:
                key = stripped.split(":", 1)[0].lstrip("- ")
                if re.fullmatch(r"[a-z][a-z0-9_]*", key):
                    names.add(key)
            continue
        if fence is None:
            if stripped.startswith(("```", "~~~")):
                fence = stripped[:3]
        elif stripped.startswith(fence):
            fence = None
        else:
            names.update(re.findall(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b", line))
    return names


def doc_files() -> list[str]:
    """Tracked Markdown whose prose this gate is responsible for."""
    files = tracked_files.tracked_on_disk(ROOT, "*.md")
    return [
        f
        for f in files
        if f not in EXCLUDED_FILES and not f.startswith(EXCLUDED_PREFIXES)
    ]


HARVEST_ROOTS = ("src", "tooling", "static/examples", "docs")

# Tests are harvested *shallowly* — module stems and def/class names only.
# Prose legitimately cites "`test_head`" and a named test function, but a local
# variable inside an unrelated test is not a public name, and admitting every
# one of them would inflate the universe until the gate stopped biting.
SHALLOW_ROOTS = ("tests",)

# The root conftest.py defines the fixtures AGENTS.md tells test authors to use
# (``models_fg``). It sits in neither tree above.
SHALLOW_FILES = ("conftest.py",)


def _harvest_python(universe: set[str]) -> None:
    """Every name *defined* in the Python tree, via ast — no imports.

    Module basenames count: prose says "`font_metrics`" meaning the module, and
    "`test_head`" meaning the test file. Both are live references.
    """
    paths: list[tuple[Path, bool]] = []
    for rel in HARVEST_ROOTS:
        paths.extend((p, False) for p in (ROOT / rel).rglob("*.py"))
    for rel in SHALLOW_ROOTS:
        paths.extend((p, True) for p in (ROOT / rel).rglob("*.py"))
    paths.extend((ROOT / name, True) for name in SHALLOW_FILES if (ROOT / name).is_file())
    for path, shallow in paths:
        # This module's own source names every allowance as a string literal.
        # Harvesting it would make each ALLOWED key "defined" by the very act of
        # allowing it — the allowance would silently justify itself.
        if path.resolve() == Path(__file__).resolve():
            continue
        universe.add(path.stem)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        if shallow:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    universe.add(node.name)
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                universe.add(node.name)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = node.args
                    for arg in (*args.args, *args.posonlyargs, *args.kwonlyargs):
                        universe.add(arg.arg)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                universe.add(node.target.id)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        universe.add(target.id)
            elif isinstance(node, ast.keyword) and node.arg:
                universe.add(node.arg)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # Registry keys and literal option values are addressed by name
                # in prose ("`fill_mode`", "`pdf-tex`") but never bound to one.
                if SYMBOL_SPAN.fullmatch(f"`{node.value}`"):
                    universe.add(node.value)


def _harvest_schema(universe: set[str]) -> None:
    """Every property name in the generated schema — the DSL's field vocabulary."""
    try:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return

    def walk(node: object) -> None:
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, dict):
                universe.update(props)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(schema)


def _harvest_document_ids(universe: set[str]) -> None:
    """Object ids authored in tracked documents and the viewer's own sources.

    Prose legitimately names a fixture's objects ("on `slide_05_palette` the
    deck places…"). Those ids live in YAML/JS, which ``ast`` never sees.
    """
    patterns = ("tests/fixtures/**/*.yaml", "tests/fixtures/**/*.yml",
                "viewer/**/*.yml", "viewer/*.jsx", "viewer/*.js", "static/**/*.yaml")
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if "node_modules" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            universe.update(re.findall(r"""\bid:\s*["']?([a-z][a-z0-9_]*)""", text))
            universe.update(re.findall(r"""["']id["']\s*:\s*["']([a-z][a-z0-9_]*)""", text))


@lru_cache(maxsize=1)
def live_symbols() -> tuple[frozenset[str], tuple[str, ...]]:
    """(every name the tree *defines*, the MCP tool list).

    Deliberately excludes ``ALLOWED``: callers union it in. Keeping the two
    apart is what lets the gate notice an allowance the tree has since grown a
    real definition for — folding them together makes that check impossible.

    Cached because harvesting the whole tree costs ~2 s and the answer cannot
    change within a run.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tools = list(manifest["mcp"]["tools"])
    universe: set[str] = set(tools)
    universe.update(manifest["mcp"]["prompts"])
    universe.update(manifest["sdk"]["public_exports"])
    _harvest_python(universe)
    _harvest_schema(universe)
    _harvest_document_ids(universe)
    return frozenset(universe), tuple(tools)


def check_counts(files: list[str], tool_count: int) -> list[str]:
    problems = []
    for rel in files:
        text = tracked_files.read_tracked(ROOT, rel)
        if text is None:
            continue
        for line_no, line in prose_lines(text):
            for pattern in COUNT_PATTERNS:
                for match in pattern.finditer(line):
                    claimed = int(match.group(1))
                    if claimed != tool_count:
                        problems.append(
                            f"  {rel}:{line_no} claims {claimed} MCP tools; "
                            f"the registry has {tool_count}"
                        )
    return problems


def check_symbols(files: list[str], universe: set[str]) -> tuple[list[str], set[str]]:
    problems: list[str] = []
    seen: set[str] = set()
    for rel in files:
        text = tracked_files.read_tracked(ROOT, rel)
        if text is None:
            continue
        scope = universe | local_names(text)
        for line_no, line in prose_lines(text):
            for name in SYMBOL_SPAN.findall(line):
                seen.add(name)
                if name not in scope:
                    problems.append(
                        f"  {rel}:{line_no} references `{name}`, which the tree "
                        "does not define (renamed, removed, or never built)"
                    )
    return problems, seen


def evaluate() -> tuple[list[str], list[str]]:
    """(blocking problems, advisory notes)."""
    defined, tools = live_symbols()
    files = doc_files()
    problems = check_counts(files, len(tools))
    symbol_problems, seen = check_symbols(files, set(defined) | set(ALLOWED))
    problems += symbol_problems
    notes = [
        f"  ALLOWED entry '{name}' no longer appears in any tracked doc — drop it"
        for name in sorted(ALLOWED)
        if name not in seen
    ]
    # An allowance that the tree now defines has served its purpose. Reporting
    # it keeps the list from quietly outliving the gap it documented.
    notes += [
        f"  ALLOWED entry '{name}' now resolves in the tree — drop it"
        for name in sorted(ALLOWED)
        if name in defined
    ]
    return problems, notes


def main() -> int:
    problems, notes = evaluate()
    for note in notes:
        print(f"check_symbol_drift: advisory\n{note}")
    if problems:
        _fail(f"{len(problems)} prose reference(s) drifted from the live tree:")
        for problem in problems:
            print(problem)
        print(
            "\nFix the prose, or — if the name is correct and simply lives "
            "outside the tree — add it to ALLOWED in tooling/check_symbol_drift.py "
            "with the reason."
        )
        return 1
    print(
        "check_symbol_drift: OK — every documented symbol and tool count "
        "matches the live tree."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
