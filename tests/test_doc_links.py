#!/usr/bin/env python3
"""
test_doc_links.py — guard documentation → repository cross-references against drift.

Closes the CRITICAL vector from the drift-risk map (Finding #6). Hand-authored
docs (``docs/architecture.md``, ``README.md``, …) link to source files via GitHub
``blob``/``tree`` URLs. Those links are a *manual mirror* of the repo's file
layout with no automated guard, so two silent rot modes exist:

  * **path rot** — a rename/move/delete leaves ``[docs/models/framegraph.py](…/blob/
    main/docs/models/framegraph.py)`` pointing at a 404, with nothing to flag it;
  * **line rot** — a ``#Lnnn`` anchor silently lies the moment code shifts above
    it (the map found ``class Document`` linked to ``#L1033`` while it lived at
    ``#L1059``).

This converts that coupling from ``silent`` to ``test-failure``:

  * every ``github.com/pedroanisio/frameforge`` ``blob|tree`` link resolves to a
    path that exists in the working tree;
  * any ``#Lnnn`` / ``#Lnnn-Lmmm`` anchor points at a real, non-blank,
    non-comment line, and — when the link *text* carries a ``path:line`` suffix —
    the visible line number agrees with the URL anchor.

Complements ``test_docs_in_sync.py::test_architecture_doc_avoids_stale_line_anchors``
(which bans ``#L`` anchors in ``architecture.md`` outright): this validates the
*paths* that ban does not cover, across every committed doc, and validates any
anchor that legitimately appears elsewhere.

Runs under pytest (``uv run pytest``) or standalone
(``uv run python tests/test_doc_links.py``). Auto-collected by the ``test`` gate,
so it runs in CI without further wiring.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

# A markdown link [text](url) whose url is one of THIS repo's GitHub blob/tree
# permalinks, with an optional #Ln or #Ln-Lm anchor.
_LINK = re.compile(
    r"\[(?P<text>[^\]]*)\]\("
    r"https://github\.com/pedroanisio/frameforge/(?P<kind>blob|tree)/[^/]+/"
    r"(?P<path>[^)#\s]+)"
    r"(?:#L(?P<l1>\d+)(?:-L(?P<l2>\d+))?)?"
    r"\)"
)
# Code-comment leaders we refuse a line anchor to land on (a def/class/statement
# is the useful target; a comment line is a sign the anchor has slipped).
_COMMENT_PREFIXES = ("#", "//", "<!--")


def _docs_to_check():
    """Tracked, hand-authored markdown that may carry repo links. Uses ``git
    ls-files`` so the *generated* pages (gitignored, untracked) are excluded by
    construction — only source-of-truth prose is checked."""
    out = subprocess.check_output(
        ["git", "ls-files", "docs/*.md", "README.md", "CHANGELOG.md", "docs/spec/*.md"],
        cwd=ROOT, text=True,
    )
    return [p for p in out.splitlines() if os.path.isfile(os.path.join(ROOT, p))]


def link_violations(text, *, root=ROOT):
    """Every project repo link in ``text`` that fails to resolve, as a list of
    human-readable strings. Pure over ``(text, root)`` so it is unit-testable on
    synthetic input (see ``test_guard_actually_catches_drift``)."""
    bad = []
    for m in _LINK.finditer(text):
        kind, path = m.group("kind"), m.group("path")
        abspath = os.path.join(root, path)
        exists = os.path.isdir(abspath) if kind == "tree" else os.path.isfile(abspath)
        if not exists:
            bad.append(f"{kind} link to missing path: {path}")
            continue

        l1, l2 = m.group("l1"), m.group("l2")
        if l1 is None:
            continue
        if kind != "blob":
            bad.append(f"line anchor on a non-file ({kind}) link: {path}#L{l1}")
            continue

        lines = open(abspath, encoding="utf-8").read().splitlines()
        for raw in filter(None, (l1, l2)):
            n = int(raw)
            if not (1 <= n <= len(lines)):
                bad.append(f"{path}#L{n}: line out of range (file has {len(lines)} lines)")
            elif not lines[n - 1].strip():
                bad.append(f"{path}#L{n}: anchors a blank line")
            elif lines[n - 1].lstrip().startswith(_COMMENT_PREFIXES):
                bad.append(f"{path}#L{n}: anchors a comment line, not a definition")

        # Internal consistency: a link whose visible text ends in ":<n>" must
        # agree with the URL's #L<n> (catches "text says :1033, URL says #L1059").
        mt = re.search(r":(\d+)\s*$", m.group("text"))
        if mt and mt.group(1) != l1:
            bad.append(f"{path}: link text says :{mt.group(1)} but URL anchors #L{l1}")
    return bad


def test_doc_repo_links_resolve_and_anchors_are_valid():
    offenders = {}
    for rel in _docs_to_check():
        v = link_violations(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        if v:
            offenders[rel] = v
    assert not offenders, "stale documentation -> repo links:\n" + "\n".join(
        f"  {rel}:\n    " + "\n    ".join(v) for rel, v in offenders.items()
    )


def test_guard_actually_catches_drift():
    """Prove the guard is not vacuous: it must report each P0 failure mode —
    an out-of-range line anchor, a renamed/missing path, and a text/URL line
    mismatch — on synthetic input."""
    base = "https://github.com/pedroanisio/frameforge/blob/main"
    synthetic = (
        f"[docs/models/framegraph.py:99999]({base}/docs/models/framegraph.py#L99999)\n"
        f"[gone]({base}/docs/models/does_not_exist.py)\n"
        f"[docs/models/framegraph.py:1]({base}/docs/models/framegraph.py#L41)\n"
    )
    v = link_violations(synthetic)
    assert any("out of range" in x for x in v), v
    assert any("missing path" in x for x in v), v
    assert any("link text says" in x for x in v), v


def test_some_links_are_actually_checked():
    """Coverage floor: the scan must find real links (so a future refactor that
    silently empties the doc set can't make this suite pass vacuously)."""
    found = sum(len(_LINK.findall(open(os.path.join(ROOT, rel), encoding="utf-8").read()))
                for rel in _docs_to_check())
    assert found >= 10, f"expected the docs to carry repo links; found only {found}"


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
                failed += 1
    print(f"\n{'OK' if not failed else 'FAILED'} ({failed} failure(s))")
    sys.exit(1 if failed else 0)
