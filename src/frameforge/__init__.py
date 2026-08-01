"""frameforge — the FrameForge v2 toolchain package.

Since 2.5.0 this package carries the authoritative Pydantic model as
`frameforge.model` (moved in from docs/models/ when the project became a real
installable package).

Since the 2026-08-01 splits it carries what *uses* the engine rather than what
*is* the engine: `frameforge.conform` (verification — every helper in it needs
real pixels to answer) and `frameforge.cli` (the `ff-render` front door). The
rendering bounded context is the `frameforge-render` distribution; authoring is
`frameforge-sdk`; the agent surface is `frameforge-mcp`; the raster→vector lane
is `frameforge-vision`.
"""

# NOT re-exported: `frameforge.rendering` moved to the `frameforge-render`
# distribution on 2026-08-01 and is imported as `frameforge_render`. An alias
# here would keep the old path importable and let new code go on writing it,
# which is the drift the split was meant to end. The break is deliberate.

#: The package version — one of the version literals `make bump` moves in
#: lockstep (RELEASE.md; §16 row 7). Kept a plain literal, not
#: `importlib.metadata.version`, so it is correct even when the package runs
#: uninstalled from a checkout (bin/ff-render, PYTHONPATH=src).
#: `tests/test_docs_in_sync.py` gates it against `[project] version`.
__version__ = "2.8.2"

__all__ = ["__version__"]
