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
content block; the SVG is kept as a resource link. Rasterization prefers headless
Chromium (`browser` group + `playwright install chromium`, highest CSS fidelity)
and falls back to CairoSVG (browser-free; `mcp`/`pdfout` group) so a PNG is
produced even without a browser; each render reports the `backend` it used. Only
when *neither* backend is available does the result carry a `render_warning` and
ship SVG/diagnostics text alone — read the warning, install a backend, re-render.

Inverse (image/document -> author):
- `propose_from_image` — classical OpenCV/numpy detectors (+ an optional VLM lane)
  propose a DRAFT document from a screenshot/photo.
- `propose_from_document` — the same pipeline over a rasterised PDF page.
- `propose_from_svg` — ingest an existing SVG's elements as FrameGraph objects
  (1:1 vector lowering), optionally recoloured by region.
  The `propose_*` drafts are UNVERIFIED: each round-trips through validate + render
  so you see whether it holds, lists which detectors ran vs were skipped, and returns
  the per-object observations. A starting point to refine with the SDK — never final.

Visual QA:
- `compare_images` — crop matching regions from a reference and a candidate, lay them
  out reference|candidate|difference (bright red = mismatch) scaled up, so you *see*
  where a recreation is off. Each region also reports real `metrics` (NCC/RMSE/MAE/
  pct_diff); `align=True` phase-aligns the candidate first (so a pure offset doesn't read
  as error) and reports the `shift_px`. Scores are relative hints, not verdicts — the
  panels are the signal (PALS's Law).

## Coordinate-aware reconstruction (raster -> precise vectors)
The measurement + workspace tools give you a coordinate-aware "mouse" for turning a
raster into exact vector geometry. Eight tools, one loop.

Coordinate frames (a point is reported in all that apply):
- image px — pixels from the image origin; the canonical, exact frame.
- coordinate system — image px re-expressed under `origin` = `top-left` (default, +y
  down, = FrameGraph page space), `bottom-left` (+y up), or `center` (+y up).
- normalized — fractions 0..1 of width/height (resolution-independent).
- viewport px — pixels within the current zoom crop; a crop is enlarged but its rulers
  stay labelled in SOURCE coordinates, and `source_px = crop.origin_px + read_px/scale`.

Tools:
- `measure_image` — overlay an auto grid + rulers + coordinate system on an image (and
  optional zoom crops), box + ID named regions, anchor landmarks; returns the overlay
  PNG (same pixel size as the source, so it reads 1:1) plus an exact `spatial` payload:
  coordinate system, per-region bbox/centroid/area/offset, landmarks, and each crop's
  origin+scale back to source px.
- `mark_points` — aim + click (stateless): give points in any frame and get numbered
  crosshairs plus each point resolved in every frame; `connect` previews the traced path.
- `overlay_images` — align an overlay onto a base by matched landmark pairs (opacity
  adjustable); reports per-pair offset + residual + the best-fit scale+translation and
  emits the aligned composite.
- `workspace` — a STATEFUL pin board bound to one image; state persists per session_id
  (`workspace.json`). Actions: `open` (bind image), `pin` (points in any frame; may
  reference existing pins by id), `nudge` (move selected pins by a delta — the mouse:
  `unit='norm'|'px'|'viewport'`, e.g. dx=-0.01 = a hair left), `move`, `snap` (snap
  selected pins to the nearest bright/dark/edge/centroid pixel — pixel-accurate refine),
  `transform` (translate+scale+rotate selected pins as a group about a pivot — fix
  proportions/perspective), `unpin`, `clear`, `viewport` (set/clear a crop), `pan`/`zoom`
  (aim stays put — coordinate continuity), `checkpoint`/`revert` (save + roll back state:
  try an adjustment, `score_reconstruction` it, undo if worse), `render`. Pins are
  image-anchored; refine over passes (`select={ids:[...]}` or `{group:...}` for multi-pin
  / group adjust) until pixel-exact.
- `construct_vectors` — draw FrameGraph geometry from anchor points (workspace `pins`
  or explicit `points`): line, path/trace, curve, spline, triangle, polygon, closed
  region, rect, ellipse, circle, star. Sizes the page to the source so it overlays 1:1,
  then validates + renders. Best for placing a handful of exact anchors by hand.
- `score_reconstruction` — the NUMERIC convergence signal: samples the constructed
  shapes and measures each sample's distance to the source's real edges, returning
  `on_edge_frac` (fraction within `tol` px of an edge) + mean/median/p90 distances over
  a match overlay (edges cyan, samples green on-edge / red off). Where `compare_images`
  shows you *where* it's off, this tells you *how far* — drive `on_edge_frac` up and the
  distances down across passes. Heuristic Sobel edges: a RELATIVE guide, not ground truth.
- `vectorize_image` — AUTOMATIC trace of a raster into editable FrameGraph objects:
  `region` (k-means colour → filled polygons), `outline` (edges → polylines), `trace`
  (potrace Bézier → SVG ingest; smooth outlines of a crisp bi-level mark), or `layers`
  (solid-bg logo tracer: AA-aware palette + even-odd holes — highest fidelity for flat,
  solid-background logos). `region_box` traces just a crop, placed 1:1 in the full image;
  `ocr` adds text objects. Reach for this when hand-pinning an intricate mark can't
  converge — `trace` on a thresholded logomark reproduces its strokes far better than
  manual anchors; `layers` for a solid-background multi-colour logo.
- `map_coordinates` — transpose coordinates: `homography` (fit + apply a projective map
  to points, from >=4 pairs), `to_3d` (lift 2D onto a plane), `project` (3D→2D via the
  SDK camera), or `warp` (apply the fitted homography to actually rectify/dewarp an
  image — perspective correction, emits the corrected PNG).

Reconstruction loop:
  measure_image (see the coordinate field) -> workspace open + pin the key points ->
  zoom/pan and nudge pins over passes to refine -> construct_vectors from the pins ->
  score_reconstruction (a number: how far the vectors sit from the edges) +
  compare_images(source, reconstruction) (see the residual) -> nudge + rebuild until
  on_edge_frac stops climbing. Use map_coordinates when the source is perspective-
  distorted or 3D; vectorize_image when hand-pinning an intricate mark can't converge.

Exactness (PALS's Law): the coordinate system, grid, rulers, explicit regions, pins,
and structural landmarks (A1..A9) are exact geometry — trust them. DETECTED landmarks
(L*) and `propose_*` output are unverified guesses — anchor to the structural ones and
verify. The overlay images are drawing aids; the `spatial` JSON is the source of truth.

## Resources
Every tool writes artifacts under `framegraph://session/<id>/`: `document.yaml`,
`page/<n>.svg`, `page/<n>.png`, `diagnostics.json` (the full result incl. the complete
`spatial` payload), and `workspace.json` (persisted pins). Read `diagnostics.json` for
the exact numbers behind any measurement; the tool response only summarizes them.
Only `workspace.json` (pins) persists: every image tool resets `page/*.png`, so
`page/1.png` holds the LAST tool's render. In a shared-session loop, pass a render's
`page/1.png` URI to the next tool before the following call overwrites it, or score/compare
under a distinct `session_id` to keep the reconstruction render viewable alongside.

## Workflow
Author or propose -> read the returned validation issues + the rendered PNG (or the
`render_warning` when raster is unavailable) -> refine the SDK code/YAML -> re-render.
For reconstruction, follow the loop above. Verify every result against pixels, never
against the YAML alone.
"""
