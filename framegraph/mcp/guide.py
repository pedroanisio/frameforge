"""The model-facing FrameGraph capability guide returned by the guide prompt."""
from __future__ import annotations


FRAMEGRAPH_GUIDE = """\
# FrameGraph MCP — what the SDK offers and the server's capabilities

FrameGraph v2 is a document/graphics DSL. The Pydantic model is the source of
truth; the SDK lowers Python to validated YAML and this server renders it. Always
verify rendered output — CV/LLM output is unverified by default (PALS's Law).

## Author with the SDK (`framegraph.sdk`)
Fluent builder:
    from framegraph.sdk import DocumentBuilder
    doc = DocumentBuilder(title="Deck", profile="deck")
    h1 = doc.define_text_style("h1", font_family="sans", font_size=48, color="#E8EAED")
    page = doc.page("p1", canvas={"size": [1280, 720], "units": "px"}, coordinate_mode="absolute")
    page.layer("main").rect([0, 0, 1280, 720], fill="#0E0F11")
    page.text([64, 96, 900, 80], "Hello", id="title", style=h1)
    doc.write(OUTPUT_YAML_PATH, fail_on_error=True)

- Primitives via `PageBuilder`: `.rect` `.text` `.line` `.image`, plus `.add(obj)` /
  `.extend(objs)` and `.stack(box, kind="row|column|grid|wrap")` layout groups.
- Paint (`framegraph.sdk.paint`): `stroke(width, color=...)`, `fill_stroke(...)`,
  `linear_gradient`/`radial_gradient`, `hatch`/`dots`/`grid_pattern`/`pattern`,
  `glow`/`neon`/`shadow`/`soft_shadow`, `rgba`, and `text_style(size, color=...)` for the
  text subset of `Style`. Stroke geometry MUST go through `stroke()` (paint in `stroke`,
  geometry in the inline `stroke_style` bundle); an inline `stroke_width` on a
  paint-only line/polyline/path is rejected.
- Widgets (`framegraph.sdk.widgets`): `avatar` `badge` `button` `card` `kpi` `pill`
  `progress` `table` `tabs` `toggle` `divider` `field`, plus `Panel`/`Theme`.
- Data & geometry: `Chart`+`Frame`, `Graph`/`Node`/`Edge`, `Camera`/`Scene3D`/`Mat3`/
  `Mat4`, `CubicBezier`/`Path`, `ScalarField`/`VectorField`, `lattice`/`manifold`,
  `greeble`, `grid_lines`.
  - Curve sampling: `parametric_curve(fn, domain)`, `function_plot(f, frame)`,
    `polar_plot(r, frame)` — adaptive subdivision, emit polyline/path.
  - `Frame` scales accept structured specs: `{"kind":"log","base":b}` / `{"kind":"pow","exp":e}`.
  - `multiview(scene, box=...)` — orthographic front/top/side/iso panel grid of a `Scene3D`.
  - `Graph.render(box=...)` auto-lays-out from declared edges (`auto_layout`/`layout_kind`);
    omit `positions` and the algorithm is inferred (grid/radial/layered/spring).
- Figures (`framegraph.sdk.figure`): `place_figure(source, box)` / `load_figure` /
  `FigureRef` import another FrameGraph page's objects as editable children (not a frozen
  image); `FigureAsset` / `place_imported_figure` place an extracted book/PDF figure with
  caption + provenance.
- Validation: `validate_static_rules(doc) -> ValidationReport(ok, issues)`,
  `assert_golden(...)`; `HEAD_VERSION` is the current spec version.

## Server tools
Forward (author -> render):
- `run_sdk_code` / `run_sdk_client` — run Python that builds a doc, then validate + render SVG.
- `write_sdk_client` / `read_sdk_client` / `list_sdk_clients` — edit whitelisted SDK clients.
- `render_framegraph_yaml` — validate + render caller-supplied YAML directly.
- `get_session_resource` — read `framegraph://session/...` artifacts (YAML, SVG, diagnostics).
- `list_sessions` / `cleanup_sessions` — enumerate and prune per-session scratch dirs.

Provenance (opt-in): the three render tools (`run_sdk_code` / `run_sdk_client` /
`render_framegraph_yaml`) accept `sign=True` to embed a FrameForge provenance
metatag — a sha256 content fingerprint + tool + version — in every rendered SVG.
`signed_at` sets a fixed UTC timestamp shared by all pages (omit for render time;
pass `""` for a deterministic, fingerprint-only stamp). Signing never alters the
visual render; the result reports `signed: {applied, timestamp}`.

## Seeing the render (visual verification)
A vision model can only *see* a raster (PNG), not SVG. The render tools therefore
rasterize to PNG by default (`raster_png=True`) and attach the PNG as an image
content block; the SVG is kept as a resource link. Rasterization needs the
`browser` dependency group plus `playwright install chromium`. When that backend
is absent the result carries a `render_warning` and ships only the SVG/diagnostics
text — read the warning, install the backend, and re-render to actually verify.

Inverse (image/document -> author), the additional capability:
- `propose_from_image` — classical OpenCV/numpy detectors (+ an optional VLM lane)
  propose a DRAFT document from a screenshot/photo.
- `propose_from_document` — the same pipeline over a rasterised PDF page.
  Both proposals are UNVERIFIED: each tool round-trips the draft through
  validate + render so you immediately see whether it holds, lists which
  detectors ran vs were skipped, and returns the per-object observations. Treat
  the result as a starting point to refine with the SDK — never as final.

## Workflow
Author or propose -> read the returned validation issues + the rendered PNG (or
the `render_warning` when raster is unavailable) -> refine the SDK code/YAML ->
re-render. Verify every rendered result against pixels, never against the YAML alone.
"""
