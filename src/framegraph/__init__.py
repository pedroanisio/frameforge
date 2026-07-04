"""framegraph — the FrameGraph v2 toolchain package.

This package is the home of the DDD restructuring described in
docs/architecture/rendering-ddd (proposal). It currently hosts the *rendering*
bounded context under `framegraph.rendering`; the conformance/schema context
(models/, schema/, tooling/validate.py, tooling/codemod.py) is migrated in
later steps.
"""

from . import rendering as rendering

#: The package version — one of the version literals `make bump` moves in
#: lockstep (RELEASE.md; §16 row 7). Kept a plain literal, not
#: `importlib.metadata.version`, because this is a *virtual* project
#: (`[tool.uv] package = false`): it is never installed, so no dist metadata
#: exists to read. `tests/test_docs_in_sync.py` gates it against
#: `[project] version`.
__version__ = "2.4.1"

__all__ = ["__version__", "rendering"]
