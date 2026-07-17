"""frameforge — the FrameForge v2 toolchain package.

This package is the home of the DDD restructuring described in
docs/architecture/rendering-ddd (proposal). It hosts the *rendering* bounded
context under `frameforge.rendering` and — since 2.5.0 — the authoritative
Pydantic model as `frameforge.model` (moved in from docs/models/ when the
project became a real installable package); the remaining conformance tooling
(tooling/validate.py, tooling/codemod.py) migrates in later steps.
"""

from . import rendering as rendering

#: The package version — one of the version literals `make bump` moves in
#: lockstep (RELEASE.md; §16 row 7). Kept a plain literal, not
#: `importlib.metadata.version`, so it is correct even when the package runs
#: uninstalled from a checkout (bin/ff-render, PYTHONPATH=src).
#: `tests/test_docs_in_sync.py` gates it against `[project] version`.
__version__ = "2.5.0"

__all__ = ["__version__", "rendering"]
