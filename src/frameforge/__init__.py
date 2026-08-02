"""frameforge — the FrameForge v2 toolchain package.

This package carries what *uses* the engine rather than what *is* the engine:
`frameforge.conform` (verification — every helper in it needs real pixels to
answer) and `frameforge.cli` (the `ff-render` front door). The document CONTRACT
is the `frameforge-api` distribution; the rendering bounded context is
`frameforge-render`; authoring is `frameforge-sdk`; the agent surface is
`frameforge-mcp`; the raster→vector lane is `frameforge-vision`.
"""

# NOT re-exported: `frameforge.rendering` moved to the `frameforge-render`
# distribution on 2026-08-01 and is imported as `frameforge_render`. An alias
# here would keep the old path importable and let new code go on writing it,
# which is the drift the split was meant to end. The break is deliberate.
#
# `frameforge.model` is gone for the same reason, and for a worse one. It was
# carried here as "the single source of truth" while `frameforge-api` shipped
# the same models under its own clock, and the two drifted two minor versions
# apart — 105 `$defs` against 119 — with every gate in this repo checking the
# local copy against itself, so nothing could see it. The contract now has ONE
# definition: `frameforge_api.model`. Import it from there.

#: The package version — one of the version literals `make bump` moves in
#: lockstep (RELEASE.md; §16 row 7). Kept a plain literal, not
#: `importlib.metadata.version`, so it is correct even when the package runs
#: uninstalled from a checkout (bin/ff-render, PYTHONPATH=src).
#: `tests/test_docs_in_sync.py` gates it against `[project] version`.
__version__ = "2.11.0"

__all__ = ["__version__"]
