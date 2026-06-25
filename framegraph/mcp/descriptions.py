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
    "Also rasterize each rendered page to PNG so a vision model can see it (needs the "
    "'browser' group); false renders SVG only."
)
_DESC_PAGES = (
    "Render exactly these 1-based pages, e.g. '6-10,15'; overrides max_pages. Omit to use max_pages."
)
_DESC_DETECTORS = (
    "Restrict which detectors run; omit to run all available. Known names: color_region, "
    "shape, line, text, vlm."
)
_DESC_CLIENT_PATH = (
    "Repo-relative path to the SDK client .py file, under the allowed edit roots (default: examples/)."
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
