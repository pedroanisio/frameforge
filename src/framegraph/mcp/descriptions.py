"""Shared parameter descriptions for the registered MCP tool signatures.

Referenced from ``Annotated[..., Field(description=...)]`` so each parameter's
semantics land in the tool's input JSON schema.
"""
from __future__ import annotations


_DESC_SESSION_ID = (
    "Reuse a prior session id to overwrite its artifacts in place; omit for the default "
    "'session'. Must match [A-Za-z0-9][A-Za-z0-9_.-]{0,79}."
)
_DESC_TIMEOUT = (
    "Wall-clock budget in seconds for the build subprocess; an overrun returns ok:false "
    "with timed_out set, never a raised traceback."
)
_DESC_MAX_PAGES = "Render only the first N pages (<=0 renders all). Ignored when 'pages' is given."
_DESC_RASTER = (
    "Also rasterize each rendered page to PNG so a vision model can see it. Prefers headless "
    "Chromium (the 'browser' group) and falls back to CairoSVG (the 'mcp'/'pdfout' group); "
    "false renders SVG only."
)
_DESC_PAGES = (
    "Render exactly these 1-based pages, e.g. '6-10,15'; overrides max_pages. Omit to use max_pages."
)
_DESC_DETECTORS = (
    "Restrict which detectors run; omit to run all available. Known names: color_region, "
    "shape, line, text, vlm."
)
_DESC_CLIENT_PATH = (
    "Repo-relative path to the SDK client .py file, under the allowed edit roots (default: static/examples/)."
)
_DESC_SIGN = (
    "Embed a FrameForge provenance metatag (sha256 content fingerprint + tool + version, "
    "plus a UTC timestamp) in each rendered SVG. Off by default; signing is opt-in and never "
    "changes the visual render."
)
_DESC_SIGNED_AT = (
    "Fixed UTC sign timestamp (ISO-8601) shared by every page; only used when sign=True. Omit "
    "for render time; pass an empty string for a deterministic, fingerprint-only stamp (no timestamp)."
)
_DESC_SILHOUETTE = (
    "Run the silhouette readability gate: flatten the document to solid black-on-white before "
    "rendering, so you can judge whether the construction reads as a recognizable shape BEFORE "
    "adding detail. Returns a 'silhouette' block with a checklist; the judgement is yours "
    "(advisory). Use it on illustration/figure construction, not on text-heavy layouts."
)
_DESC_TO = (
    "Export target: 'png' (default — the raster feedback loop) or 'pdf' (additionally assemble "
    "the rendered pages into a vector document.pdf; needs the 'pdfout' group). The PDF is "
    "reported under result.pdf and as the framegraph://session/<id>/document.pdf resource."
)
_DESC_SCALE = (
    "Raster zoom for the PNG pages: 1.0 renders at the SVG's pixel size; 2.0 doubles the output "
    "resolution (DPI control for zoom-in inspection or print-quality raster). SVG/PDF output is "
    "unaffected."
)
_DESC_REAL_METRICS = (
    "Text measurement mode for wrap/shrink/ellipsis decisions: 'auto' (default — real glyph "
    "advances via fontTools when it is installed), true (force real metrics), or false "
    "(per-character estimate). The resolved mode is reported as result.real_metrics."
)
_DESC_TOPIC = (
    "Optional capability topic: omit for the compact index (object types, flowable types, inline "
    "kinds, canvas presets, profiles, tools); or one of 'flowables' | 'inlines' | 'style' | "
    "'presets' | 'tools'; or a type/model name ('rect', 'paragraph', 'document', 'page', "
    "'canvas') for its live JSON schema."
)
_DESC_REGION_METHOD = (
    "Detection method: 'closed' (purely topological enclosed faces — any line art: floor plans, "
    "mazes, sketches), 'flat' (fill partition: every maximal uniform-colour area is one region — "
    "solid shapes and hollow interiors alike), or 'consensus' (default — ensemble mollified "
    "level sets across a (sigma, level) grid, smooth Fourier boundaries; robust on tangled/open "
    "linework)."
)
_DESC_REGION_TUNABLES = (
    "Method-specific tuning knobs as an object (unknown names are rejected, not ignored). "
    "closed: {invert, auto_polarity, threshold_method: 'otsu'|'adaptive', block, c, close "
    "(gap-sealing px), open_gap (erase strokes thinner than N px), min_area}. "
    "flat: {colors (k-means palette size), min_area, dark_thresh (solid-vs-hollow luminance), "
    "fill_erode (reclassify thin strokes as 'outline')}. "
    "consensus: {sigmas: [..], levels: [..], agree (fraction), harmonics (Fourier low-pass per "
    "loop), min_area}."
)
