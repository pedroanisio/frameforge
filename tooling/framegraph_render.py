#!/usr/bin/env python3
"""framegraph_render.py — the render front door for the *virtual* project.

``[project.scripts] framegraph-render`` is declared but deliberately inert
(``[tool.uv] package = false`` — codebase-standards §2): nothing installs a
console script, and ``python -m framegraph.cli`` cannot self-bootstrap the
``src`` layout. This launcher is the invocation that works everywhere, with
no PYTHONPATH and from any CWD::

    uv run python tooling/framegraph_render.py doc.fg.yaml --to svg

It follows the tooling convention (every entry point carries its own
bootstrap), then delegates to :func:`framegraph.cli.main` — one surface,
zero duplicated logic (issue #35).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
