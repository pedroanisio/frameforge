"""Thin launcher for ``fg-font`` — the implementation lives in the installable
package (:mod:`framegraph.fontpack`) so it can be the ``fg-font`` console script.
This wrapper keeps ``uv run python tooling/fg_font.py …``, the ``make font-*``
targets, and the tests working without installing the package."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "docs"))

from framegraph.fontpack import (  # noqa: E402,F401
    install_pack, main, pack_families, referenced_families, scope_font_pack,
)

if __name__ == "__main__":
    raise SystemExit(main())
