"""framegraph.rendering.domain — the pure rendering core.

No I/O, no rendering backend, no third-party deps beyond the standard library.
Everything here can run in the dependency-free environment the SVG proxy
promises (stdlib + PyYAML, and PyYAML is only used at the edges, not here).
"""
