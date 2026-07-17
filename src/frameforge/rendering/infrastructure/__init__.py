"""frameforge.rendering.infrastructure — adapters for the rendering ports.

Backend/IO-specific code lives here so the domain core stays pure. Currently:
`painters.svg.SvgPainter` (a ScenePainter that emits SVG). Loaders, the
matplotlib painter, text measurers, and the contact-sheet writer arrive in
later migration steps.
"""
