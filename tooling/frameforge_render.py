#!/usr/bin/env python3
"""frameforge_render.py — render front-door launcher for uninstalled checkouts.

Since 2.5.0 the project is a real package: ``uv run ff-render`` (or an
installed ``ff-render``) is the primary invocation. This launcher keeps the
historical zero-setup path working — it bootstraps ``src`` onto ``sys.path``
so it runs even with a bare interpreter and no install, from any CWD::

    python tooling/frameforge_render.py doc.fg.yaml --to svg

It follows the tooling convention (every entry point carries its own
bootstrap), then delegates to :func:`frameforge.cli.main` — one surface,
zero duplicated logic (issue #35).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from frameforge.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
