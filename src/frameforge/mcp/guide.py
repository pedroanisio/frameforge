"""The model-facing FrameForge capability guide returned by the guide prompt."""
from __future__ import annotations


FRAMEFORGE_GUIDE = """\
# FrameForge MCP — what the SDK offers and the server's capabilities

FrameForge v2 is a document/graphics DSL. The Pydantic model is the source of
truth; the SDK lowers Python to validated YAML and this server renders it. Always
verify rendered output — CV/LLM output is unverified by default (PALS's Law).

This guide is hand-maintained prose and can drift behind the code. The
`describe_capabilities` tool is the authoritative, live-introspected source of
the model surface and the server's security posture — when this text and its
output disagree, `describe_capabilities` wins.

## Author with the SDK (`frameforge.sdk`)
Fluent builder:
    from frameforge.sdk import DocumentBuilder
    doc = DocumentBuilder(title="Deck", profile="deck")
    h1 = doc.define_text_style("h1", font_family="sans", font_size=48, color="#E8EAED")
    page = doc.page("p1", canvas={"size": [1280, 720], "units": "px"}, coordinate_mode="absolute")
    page.layer("main").rect([0, 0, 1280, 720], fill="#0E0F11")
    page.text([64, 96, 900, 80], "Hello", id="title", style=h1)
    doc.write(OUTPUT_YAML_PATH, fail_on_error=True)

- Primitives via `PageBuilder`: `.rect` `.text` `.line` `.image` `.ellipse` `.circle`
  `.polyline` `.polygon` `.path` `.curve`, plus `.icon`, `.dimension`, `.arc`,
  `.sector`, `.ring`, `.star`, `.add(obj)` / `.extend(objs)`, and
  `.stack(box, kind="row|column|grid|wrap")` layout groups. `DocumentBuilder.master()`
  exposes `running_header`, `running_footer`, and `footnote_area`; `define_counter`
  declares numbering series for generated labels.
  - `.connector(start, end, ...)` — anchored connector between objects (typed at
    HEAD): endpoints are an object id, a point, or `{"ref", "port"|"side", "offset"}`;
    optional `route=[...waypoints]` + `route_kind`, boxed `label`/`label_box`, and
    `arrow_start`/`arrow_end` markers (merged into the inline `stroke_style`).
- Paint (`frameforge.sdk.paint`): `stroke(width, color=...)`, `fill_stroke(...)`,
  `linear_gradient`/`radial_gradient`/`conic_gradient`,
  `hatch`/`dots`/`grid_pattern`/`pattern`, `glow`/`neon`/`shadow`/`soft_shadow`,
  `rgba`, and `text_style(size, color=...)` for the text subset of `Style`,
  including OpenType/variable-font fields (`feature_settings`, `variation_settings`,
  `variant_caps`, `variant_numeric`, `variant_ligatures`). Filter/style helpers:
  `blur_filter`, `turbulence`, `displacement_map`, `diffuse_lighting`,
  `specular_lighting`, `filter_chain`, `style_effects`, `effect`, `effect_stack`,
  and `appearance`. Stroke geometry MUST go through `stroke()` (paint in `stroke`,
  geometry in the inline `stroke_style` bundle); an inline `stroke_width` on a
  paint-only line/polyline/path is rejected.
- Widgets (`frameforge.sdk.widgets`): `avatar` `badge` `button` `card` `kpi` `pill`
  `progress` `table` `tabs` `toggle` `divider` `field`, plus `Panel`/`Theme`.
- Data & geometry (`frameforge.sdk.chart` / `.topology` / `.geometry` / `.draw`): `Chart`+`Frame` (series: `line`, `bars`, `scatter`, `area`, `pie`,
  `donut`, plus `marker`/`axes`/`legend`), `Graph`/`Node`/`Edge`, `Camera`/`Scene3D`/
  `Mat3`/`Mat4`, `CubicBezier`/`Path`, `ScalarField`/`VectorField`, `lattice`/`Lattice`/`manifold`
  (`frameforge.sdk.lattices` / `.fields` / `.manifold`), `greeble`, `grid_lines` (`frameforge.sdk.macros`).
  - Curve sampling: `parametric_curve(fn, domain)`, `function_plot(f, frame)`,
    `polar_plot(r, frame)` — adaptive subdivision, emit polyline/path.
  - Surfaces (`frameforge.sdk.manifold`): `sphere`/`torus`/`mobius`/`klein_bottle`/`saddle`/`wave`
    plus `parametric(fn, u=, v=)` and the bicubic patches `bezier_patch(net)` /
    `bspline_patch(net)` (4×4+ control grid → a tessellated `Scene3D`).
  - Geometry kernel (`frameforge.sdk.geometry`, CG-canon): `Mat3.reflect`/`mirror`; the
    named viewing pipeline `window_to_viewport(window, viewport)` / `ViewingPipeline`
    (the fit `Scene3D.render` uses); 2-D intersections (`segment_intersection`/
    `ray_segment_intersection`/`line_intersection`/`segment_polygon_intersections`),
    3-D intersections (`ray_plane_intersection`/`segment_plane_intersection`/
    `ray_triangle_intersection`) and curve×line (`segment_curve_intersections`/
    `line_curve_intersections`, de Casteljau); curves `CubicBezier.curvature`/`arc_length` +
    `polyline_length` and surfaces `surface_curvature(fn, u, v)` → `(K, H)`; comp-geometry
    `convex_hull`/`convex_hull_3d`/`aabb`/`aabb3`/`obb`/`polygon_area`/`point_in_polygon`.
  - `Scene3D.render(shading=, cull_backfaces=, near_clip=)` — opt-in `near_clip=True`
    Sutherland–Hodgman-clips faces straddling the near plane instead of dropping them.
  - Fractals (`frameforge.sdk.fractal`): an `lsystem` + `turtle` engine with
    `koch_curve`/`dragon_curve`/`sierpinski_arrowhead` presets — self-similar curves
    lowered to plain polylines.
  - `Frame` scales accept structured specs: `{"kind":"log","base":b}` / `{"kind":"pow","exp":e}`.
  - `multiview(scene, box=...)` — orthographic front/top/side/iso panel grid of a `Scene3D`.
  - `Graph.render(box=...)` auto-lays-out from declared edges (`auto_layout`/`layout_kind`);
    omit `positions` and the algorithm is inferred (grid/radial/layered/spring).
  - `Graph.to_object(box=..., algorithm="auto")` emits a DECLARATIVE `type: graph`
    object that `sdk.expand` lowers into a positioned group at expansion time —
    the render-time auto-layout bridge (nodes+edges in, computed geometry out;
    a node's `pos` overrides the algorithm). Prefer it over baking coordinates.
- Figures (`frameforge.sdk.figure`): `place_figure(source, box)` / `load_figure` /
  `FigureRef` import another FrameForge page's objects as editable children (not a frozen
  image); `FigureAsset` / `place_imported_figure` place an extracted book/PDF figure with
  caption + provenance.
- Design canon — START HERE for colour and type decisions, instead of ad-hoc picks:
  - Colour (`frameforge.sdk.chevreul`, after Chevreul 1839): `closed_palette(ground=,
    ink=, accent=)` assigns every colour a duty and emits a `defs.tokens.colors` fragment
    (dose per `AREA_GUIDE` ≈ 62/30/8); the six harmonies (`harmony_of_scale`,
    `harmony_of_hues`, `dominant_light`, `contrast_of_scale`, `contrast_of_hues`,
    `contrast_of_colours`) + `complement`/`tone_scale` pick colours that agree;
    `color_guide(base)` returns all six harmonies for any base colour (the declarative Color Guide); `contrast_ratio(a, b)` (WCAG) checks text-on-ground legibility BEFORE rendering;
    `grey_document(doc)` is the tone audit — render it next to the original to prove
    hierarchy survives without hue.
  - Typography (`frameforge.sdk.canon`, after Johnston 1906): `modular_scale(base, ratio)`
    for sizes that agree; `content_box(page_w, page_h, unit, side="recto"|"verso")` for
    the book margin canon (inner 1½ · top 2 · outer 3 · foot 4); `measure_fits(chars)`
    for the 45–75 chars/line band; `caps_tracking(font_size)` for all-caps labels.
- Markdown (`frameforge.sdk.markdown`): `from_markdown(text)` converts a whole
  CommonMark/GFM-subset document into a validated flow document (headings,
  lists, tables, code, quotes, images; front-matter; page breaks) — the fast
  path from prose to a paginated render.
- Geometry engines (compute in the SDK, emit plain paths — never hand-place what
  these can derive):
  - Planar kernel (`frameforge.sdk.planar`, Pathfinder-class): `union`/`intersect`/
    `subtract`/`divide` booleans on flattened rings (holes native — multi-ring
    even-odd paths), `offset_polygon(ring, d)` (miter, collapse-aware),
    `split_at(points, t)` / `cut_along(ring, p1, p2)` path surgery,
    `fill_regions(shapes)` (every bounded region of an overlay as its own fillable
    face, <=8 shapes), `to_path(rings, fill=...)` to emit.
  - Stroke outlines & brushes (`frameforge.sdk.outline`): `stroke_outline(points,
    width, profile=t->scale, pen_angle=, pen_thin=, cap=, join=, smooth=True)` lowers
    a centre-line to a CLOSED filled path — constant width = outline-stroke, profile
    = variable width, pen_angle = calligraphic nib; `repeat_along_path(points,
    spacing=, stamp=obj)` places copies by arc length with tangent rotation.
  - Clipping & masking (`frameforge.sdk.clip`): `clip_rect`/`clip_circle`/`clip_ellipse`/
    `clip_inset`/`clip_polygon`/`clip_path` build the `clip` bag for an object or group;
    `normalize_clip` canonicalises it. `mask_url`, `mask_gradient`, `mask_none`,
    `normalize_mask`, and `mask_style` build the model-native `style.mask` values.
    Nest a clip on a STATIC parent — a clip on a transformed group rides along inside
    the transform.
  - Regions & grading (`frameforge.sdk.region`): `select_in(doc, box)` / `extract_objects`
    pick objects by area; `region_grade` / `gradient_map(objects, ...)` apply a positional
    colour grade; `place_region` re-lays a captured region; `object_bbox` measures it.
  - SVG ingest & embedded lowering (`frameforge.sdk.io`): `svg_to_objects(svg, box=...)`
    ingests SVG text, a `.svg` path, or a `data:image/svg+xml` URI (plain/URL-encoded/
    base64) as native objects; `lower_embedded_svg(doc)` walks a document and replaces
    every embedded-SVG `image` (literal src or a `defs.assets` key) with a `group` of
    native objects fitted into its box — stable `<id>.<i>` child ids + `meta.region`
    provenance — so recolor/design_audit/planar/effects can reach detail that was
    trapped inside opaque image blobs.
- Style richness (2.4.0 object fields + helpers):
  - `effects: [{kind: "shadow"|"glow", preset?, color/blur/dx/dy/opacity?}, ...]` —
    an ORDERED effect stack (kinds may repeat, first->last); `appearance:
    [{fill?/stroke?/stroke_style?/opacity?}, ...]` — the same geometry painted once
    per pass, bottom->top. Use `effect_stack(effect(...), ...)` and
    `appearance({...}, ...)` instead of hand-writing those bags. Both render only
    when declared (absence is identity).
  - Backend support statement: Chromium has the highest CSS/SVG fidelity for
    filters, blend modes, masks, and `backdrop_filter`. The CairoSVG fallback can
    produce PNGs without a browser but is limited and may not honor those style
    effects fully; inspect render diagnostics and rerender with Chromium when
    those effects are material to the output.
  - `recolor(doc, mapping)` — one-call palette remap: `defs.tokens.colors` by name
    or value, paint literals and gradient stops; input never mutated.
  - Named gradient/pattern fills live in `defs.tokens.fill_styles` and resolve from
    any `fill:`/`stroke:` string.
- Type finesse (`frameforge.sdk.metrics`): `measure_text`/`wrap_text`/`text_height`
  size boxes to content BEFORE rendering; `kerned_spans(text, pairs=...)` applies
  explicit pair kerning as grammar-native spans; `font_kern_pairs(family, text,
  font_size=...)` reads the resolved font's kern table (fontTools; degrades to {}).
- Slide patterns (`frameforge.patterns`): `load_catalog()` — 375 typed layout
  patterns; `compose(pattern_id, fill)` validates a `{role: content}` payload and
  returns a full deck page (zone boxes from the placement vocabulary, treatments
  applied). Prefer a catalog pattern over hand-rolling a standard slide.
- Content library (`frameforge.library`): `load_theme(name)` — 7 consulting themes
  (bain/bcg/deloitte/ey/kpmg/mckinsey/pwc) as ready `defs.tokens` fragments;
  `load_symbols(pack)` + `support_text_styles(pack)` — cover/agenda/insight/hex
  symbol packs instantiated via `use` objects and lowered by `sdk.expand`;
  `honeycomb_capability_map(data)` / `module_hub_radial(data)` generate whole
  diagram pages from plain data dicts (render-ready, pre-expanded).
- Books (`frameforge.sdk.book`): `BookBuilder(title=, author=)` -> `.chapter(t)`
  -> `.section(t)` / `.para` / `.figure(obj, caption=)` composes front matter +
  chapters into ONE paginated flow document — numbering computed at build time
  (chapters `1`, sections `1.1`, captions `Figure 2.1 — ...`), chapters open on
  fresh pages, figures keep their captions (`keep_with_caption`), boxless
  geometry gets a derived size, and the TOC lists chapters only.
- Symbols & lowering (`frameforge.sdk.expand`): `expand(doc)` lowers grammar-level
  `use`/`component` objects into core primitives and pins asset/font hashes — run it
  before rendering any document that carries `defs.symbols`.
- Humanize (seeded imperfection): set `humanize: {seed: N, roughen: ..., drift_deg:
  ...}` on the document or any object — a deterministic hand-drawn wobble applied at
  expansion; absence is identity, same seed = same page.
- Validation: `validate_static_rules(doc) -> ValidationReport(ok, issues)`,
  `assert_golden(...)`; `HEAD_VERSION` is the current spec version.

## Flow defaults & reserved styles (ADR-0006)
The flow renderer injects NO undefined style — it renders only what the document
defines. Five reserved `tokens.styles` names carry the flow defaults (the
authoritative list is the engine's `RESERVED_STYLES` constant, exported live by
`describe_capabilities("style")`):
- **`body`** — the DEFAULT text style for every text surface. Define it to set
  the document face/size/colour; without it, text falls back to a single
  documented engine default (you usually do not want that).
- **`caption`** — styles generated figure and table captions.
- **`code`** — styles code blocks (fallback: monospace / 10 / #333).
- **`toc`** — styles generated table-of-contents entry lines.
- **`toc_title`** — styles the generated table-of-contents title.
Headings/lists resolve their own `style`; a `table` carries its chrome via
`style` (header_fill/header_text/cell_text/zebra_fill/grid_color/cell_size —
header_text/cell_text are colour-or-style-ref: a defined style name is a style
ref, any other string is a colour, identically in flow tables and TableObject) —
chrome it does not define is not drawn. Every render result reports a compact
`design` census (faces/sizes/weights/colours + sprawl health flags); the
`design_audit` tool returns the full drift-proof report for a session.

## Server tools
Discovery (look up, don't guess):
- `describe_capabilities` — LIVE introspection of the document model: no topic = the
  capability index (object types, flowable types, inline kinds, canvas presets, profiles,
  tool names, SDK export count); topic = `flowables`/`inlines`/`style`/`presets`/`tools`/
  `sdk` (the ENTIRE public SDK surface — every export with kind, signature and a one-line
  explanation, introspected live from `frameforge.sdk.__all__`), or a type name
  (`rect`, `paragraph`, `document`, `page`, `canvas`) for its fields + JSON schema.
  Check the schema BEFORE authoring instead of iterating on validation errors.
- `list_fonts` — the font families fontconfig can resolve; pass `family` to see what a
  request actually resolves to (`resolves.exact=false` = silent substitution) BEFORE a
  render swaps in a default face. Reports a session document's pinned `defs.tokens.fonts`.
- `get_guide` — this guide as a tool, for MCP clients that do not surface prompts.

Forward (author -> render):
- `run_sdk_code` / `run_sdk_client` — run Python that builds a doc, then validate + render SVG.
- `write_sdk_client` / `read_sdk_client` / `list_sdk_clients` — edit whitelisted SDK clients.
  `write_sdk_client` also does anchored edits: pass `old_string`+`new_string` (exact match,
  must be unique in the file) instead of re-sending the whole `code`. For a file too large
  for one `code` argument (some clients cap a single tool argument at ~tens of KB), build it
  in chunks: `append=true` with `allow_partial=true` on every chunk except the last. The
  whole file is capped at 2,000,000 bytes.
- `render_frameforge_yaml` — validate + render caller-supplied YAML directly.
- `get_session_resource` — read `frameforge://session/...` artifacts, transport-budgeted:
  text artifacts paginate (`offset`/`max_chars`, with `total_chars`/`next_offset`), JSON
  artifacts answer targeted `query='/rfc6901/pointer'` requests, and binary artifacts
  (PNG/PDF) return reference metadata — bytes, sha256, on-disk path — with `mode='blob'`
  as a small-file opt-in. No result ever exceeds `FRAMEFORGE_MCP_MAX_RESULT_CHARS`.
- `list_sessions` / `cleanup_sessions` — enumerate and prune per-session scratch dirs.
  Cleanup respects an age floor: sessions younger than `FRAMEFORGE_MCP_MIN_CLEANUP_AGE`
  seconds are never pruned, so a concurrent loop's live session survives a sweep.

Render options (the three render tools): `to='pdf'` additionally assembles the rendered
pages into a vector `document.pdf` (needs the `pdfout` group; reported under `result.pdf`
and as the `frameforge://session/<id>/document.pdf` resource). `scale` controls the PNG
raster zoom (2.0 = double resolution — DPI control). `real_metrics` ('auto'|true|false,
default 'auto' = on when fontTools is installed) measures text with real glyph advances
so wrap/ellipsis decisions match the rendered pixels; the result reports the resolved mode.

Render diagnostics: every successful render also returns a `result.diagnostics` block —
the renderer's structured feedback (`warnings` from the renderer AND painter,
`skipped_objects` swallowed by the per-object safety net, per-type `skipped_flowables`
counts, `font_fallbacks`, and an opt-in `layout` report) — persisted into the session's
`diagnostics.json`. Read it when a render is ok:true but looks wrong: a dropped flowable
or a swallowed object is reported there, not silently passed (PALS's Law).

Failures are structured: every tool returns `{ok: false, error, error_type?, hint?}` on an
expected failure (bad path, bad session id, missing dependency) — read the `hint`, it names
the fix (e.g. which tool lists valid inputs). `ok: false` always carries an `error`.

Security posture: `describe_capabilities(topic="security")` reports the live confinement.
Propose inputs are open by default — any readable path, the localhost-dev posture; set
`FRAMEFORGE_MCP_INPUT_ROOTS` (pathsep-joined roots) to confine the `propose_*` tools in a
hardened deployment. Client writes stay under the editable roots
(`FRAMEFORGE_MCP_EDIT_ROOTS`, default `static/examples`). SDK code runs in a subprocess
with secret-looking env vars stripped (`FRAMEFORGE_MCP_KEEP_ENV=1` keeps them).

Provenance (opt-in): the three render tools (`run_sdk_code` / `run_sdk_client` /
`render_frameforge_yaml`) accept `sign=True` to embed a FrameForge provenance
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
- `propose_from_svg` — ingest an existing SVG's elements as FrameForge objects
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
  down, = FrameForge page space), `bottom-left` (+y up), or `center` (+y up).
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
  selected pins to the nearest bright/dark/edge/centroid pixel, or sub-pixel edge with
  `snap_to='edge_subpixel'` — refine perpendicular to the local gradient),
  `transform` (translate+scale+rotate selected pins as a group about a pivot — fix
  proportions/perspective), `unpin`, `clear`, `viewport` (set/clear a crop), `pan`/`zoom`
  (aim stays put — coordinate continuity), `checkpoint`/`revert` (save + roll back state:
  try an adjustment, `score_reconstruction` it, undo if worse), `render`. The geometry-
  constraint actions place pins by the *right* method for a rigid mark — fit lines to
  edges, intersect them for corners, enforce symmetry (a luminance diff is blind to a
  single-corner offset): `fit_edge` (re-project selected pins onto one sub-pixel edge
  line — collinear + edge-accurate), `collinear` (project selected pins onto their best-
  fit line), `intersect` (set a corner pin at the meeting of two edges,
  `geometry={'edge1':[ids],'edge2':[ids],'target':id}`), `symmetrize` (enforce bilateral
  symmetry over pin pairs, `geometry={'pairs':[[l,r],...]}` — reports the outlier pair).
  Pins are image-anchored; refine over passes (`select={ids:[...]}` or `{group:...}` for
  multi-pin / group adjust) until pixel-exact.
- `detect_regions` — what closed/filled/stable regions does an image contain? Three
  methods: `closed` (purely topological enclosed faces — any line art), `flat` (fill
  partition: every maximal uniform-colour area, solid AND hollow, with outline-stroke
  recovery), `consensus` (default — ensemble mollified level sets, smooth Fourier
  boundaries; robust on tangled/open linework). Returns exact per-region geometry
  (`bbox_px` + `box_norm`, centroid in px and normalized, sampled fill, boundary
  polygon + holes) under `spatial`, optional shape-equivalence `classes`
  (`cluster='translation'|'congruent'`), and the annotated overlay as page 1. Regions
  feed `workspace` pins and `construct_vectors` points directly. Heuristic output —
  verify the overlay (PALS's Law).
- `construct_vectors` — draw FrameForge geometry from anchor points (workspace `pins`
  or explicit `points`): line, path/trace, curve, spline, arc (3 points = start /
  on-arc / end through their circumcircle, or 1 centre point + `r` + `start_deg`/
  `end_deg`), triangle, polygon, closed region, rect, ellipse, circle, star, and text
  (requires `"text"` + `"size"` font px; 1 anchor point = box top-left, or 2+ points =
  the bbox). Sizes the page to the source so it overlays 1:1,
  then validates + renders. Best for placing a handful of exact anchors by hand.
- `score_reconstruction` — the NUMERIC convergence signal: samples the constructed
  shapes and measures each sample's distance to the source's real edges, returning
  `on_edge_frac` (fraction within `tol` px of an edge) + mean/median/p90 distances over
  a match overlay (edges cyan, samples green on-edge / red off). Where `compare_images`
  shows you *where* it's off, this tells you *how far* — drive `on_edge_frac` up and the
  distances down across passes. Pass `symmetry_pairs`/`collinear_groups` to add a
  geometry-consistency report (`score.geometry`) — the internal-symmetry and edge-
  collinearity residuals that catch a single-corner offset the luminance % cannot see.
  Geometry points may be raw `[x, y]` pixels OR workspace pin/landmark id strings
  ("P3" / "A9"), resolved like shape `pins` — nudge a pin, re-score, no re-typing.
  Scored `text` shapes contribute no edge samples (glyph outlines are font geometry).
  Heuristic Sobel edges: a RELATIVE guide, not ground truth.
- `vectorize_image` — AUTOMATIC trace of a raster into editable FrameForge objects:
  `region` (k-means colour → filled polygons), `outline` (edges → polylines), `trace`
  (potrace Bézier → SVG ingest; smooth outlines of a crisp bi-level mark), `layers`
  (solid-bg logo tracer: AA-aware palette + even-odd holes — highest fidelity for flat,
  solid-background logos), or `auto` (classify the raster and route to the best of the
  four; the decision + presets are reported under `result.vectorize.auto`, and explicit
  args always win over the route's presets). `region_box` traces just a crop, placed
  1:1 in the full image; `ocr` adds text objects and reports the OCR backend status
  under `result.vectorize.ocr` (`ok` / `no_text` / `unavailable` / `error` — a missing
  Tesseract is never a silent empty list). Reach for this when hand-pinning an
  intricate mark can't converge — `trace` on a thresholded logomark reproduces its
  strokes far better than manual anchors; `layers` for a solid-background multi-colour
  logo.
  For GRADIENT/shaded art (glossy emblems, soft-shaded marks), add
  `fill_mode='gradient'`: every traced shape is re-painted from the SOURCE pixels —
  flat/linear/radial candidates fitted per shape and ranked by colour rms (the
  `fit_primitives` doctrine: a richer family must beat the simpler one, never win by
  default), so ramps become real multi-stop Gradient fills instead of posterised
  bands. Fitted gradients are emitted as EXACT user-space geometry — linear
  `line: [[x1,y1],[x2,y2]]` / radial px `at`+`radius` in each object's local
  space (SVG userSpaceOnUse) — so the ramp lands back on the sampled pixels
  precisely; the same fields are authorable by hand (plus `focal` for off-centre
  gloss and per-stop `opacity`). Works with `region`/`trace`/`layers`; the paint
  summary lands under `result.vectorize.paint`. In trace mode,
  `thresholds=[30, 110, 190]` runs one potrace pass per luminance level and
  stacks the layers darkest-first — base shapes, mid-tone planes, highlights —
  the multi-level recipe for shaded logo art. `supersample=2..3` (trace mode)
  upscales before thresholding so anti-aliased edges are located subpixel
  instead of quantised to whole pixels — kills the traced-edge halo on
  soft-edged sources (turdsize keeps source-pixel semantics; cost ~s²).
  Flat default is unchanged; all options are additive.
- `map_coordinates` — transpose coordinates: `homography` (fit + apply a projective map
  to points, from >=4 pairs), `to_3d` (lift 2D onto a plane), `project` (3D→2D via the
  SDK camera), or `warp` (apply the fitted homography to actually rectify/dewarp an
  image — perspective correction, emits the corrected PNG).

The CAD operator layer (parametric, computed, verified):
- Solids (`frameforge.sdk.solids`): `extrude(profile, depth)`, `revolve(profile,
  segments=, angle=)` (partial angles grow end caps), `sweep(profile, path3d)`
  (tangent-oriented rings, mitred corners), `loft(profiles, heights=)` — all
  emit `Scene3D` meshes for `render`/`multiview`. `section_loops(scene,
  plane_point=, plane_normal=)` cuts a scene into closed 2D loops;
  `section_object(...)` fits them into a frame as one even-odd hatched path —
  the engineering section view.
- Sketch surgery (`frameforge.sdk.planar`): `fillet_ring(ring, r)` /
  `chamfer_ring(ring, d)` round or cut corners (per-corner selection, oversized
  radii left sharp); `trim_segment` / `extend_segment` cut or prolong to a line.
- Patterns: `array(obj, linear=(dx, dy, n) | polar=(cx, cy, n) | along=pts,
  spacing=)` — geometry-translated linear instances, pivot-rotated polar groups
  (`rotate_items=False` orbits upright), tangent-rotated along-path stamps.
- Construction geometry: `construction: true` objects and `role: construction`
  layers are non-printing datums — excluded from renders unless the document
  sets `meta.show_construction`. Layer `role` also declares
  geometry/annotation/dimension intent.
- Document parameters (`frameforge.sdk.params`, `defs.params`): named numbers
  (or '=expr' strings over earlier ones); ANY '=expr' string field resolves
  before validation — geometry positions become numbers, `text` fields become
  formatted strings (driven dimension labels). Whitelisted arithmetic AST, never
  eval; resolved values are recorded under `meta.resolved_params`.

Primitives-first reconstruction (numeric loop closure):
- `fit_primitives` — measured point sets (e.g. detect_regions polygons) ->
  {line | circular arc | axis-aligned ellipse arc} PARAMETERS: centre/radius/
  radii, angular span, stroke thickness, angle, endpoints — typed straight into
  SDK primitives instead of traced paths. Best fit + all candidates ranked by a
  like-for-like radial rms; an ellipse must show a consistent axis gap above the
  band's noise floor to beat the circle.
- render tools accept `reference=<image>`: the result gains `reference_diff`
  with per-object GHOST VECTORS — each authored object's displacement toward its
  best match in the reference (page 1) — so corrections are typed from numbers,
  not eyeballed off an overlay's double image.
- every successful render archives page artifacts into a history ring (last 5;
  `revision` + `history` on the result); `diff_renders` compares any two —
  default latest vs previous ("did that nudge help?").
- `match_font` — rank resolvable families by shape similarity to a reference
  crop (ink-cropped NCC + aspect penalty); verify the winner in a real render.
- every image input also accepts a `data:image/<type>;base64,` URI — a pasted
  reference reaches the tools without touching the filesystem.
- `overlay_images(rotation=true)` opts into the full-similarity fit (2D
  Procrustes, >=2 pairs) and a rotated composite; the default stays
  rotation-free so tilt keeps surfacing honestly as residuals.
- SDK type-on-path (`frameforge.sdk.pathtext`): `text_on_path(points, text,
  size=, family=, offset=, ...)` sets type glyph-by-glyph along a polyline —
  real-metric advances measured on the offset path (concave side at +offset),
  tangent-following rotation; `offset_path`/`path_walker`/`path_length` are the
  underlying walkers. Wrap the extend in `page.lettering()`.

Reconstruction loop:
  measure_image (see the coordinate field) -> detect_regions (inventory the shapes:
  exact boxes/centroids/fills to seed pins from) -> workspace open + pin the key
  points -> zoom/pan and nudge pins over passes to refine -> construct_vectors from
  the pins -> score_reconstruction (a number: how far the vectors sit from the edges) +
  compare_images(source, reconstruction) (see the residual) -> nudge + rebuild until
  on_edge_frac stops climbing. For a rigid geometric mark, prefer the constraint path
  over eyeballing corners: `fit_edge` the long edges (sub-pixel), `intersect` them for
  corners, and `symmetrize` pin pairs — corners inherit the edges' sub-pixel accuracy,
  and symmetry catches the offset the diff can't. Use map_coordinates when the source is
  perspective-distorted or 3D; vectorize_image when hand-pinning an intricate mark can't
  converge.

Exactness (PALS's Law): the coordinate system, grid, rulers, explicit regions, pins,
and structural landmarks (A1..A9) are exact geometry — trust them. DETECTED landmarks
(L*) and `propose_*` output are unverified guesses — anchor to the structural ones and
verify. The overlay images are drawing aids; the `spatial` JSON is the source of truth.

## Resources
Every tool writes artifacts under `frameforge://session/<id>/`: `document.yaml`,
`page/<n>.svg`, `page/<n>.png`, `document.pdf` (after a `to='pdf'` render),
`diagnostics.json` (the full result incl. the complete `spatial` payload), and
`workspace.json` (persisted pins). Read `diagnostics.json` for the exact numbers behind
any measurement; the tool response only summarizes them.
Sessions are single-writer: run ONE agent (or loop) per `session_id` at a time —
concurrent writers race on `page/*.png` and `workspace.json`; give parallel work
distinct `session_id`s.
Only `workspace.json` (pins) persists: every image tool resets `page/*.png`, so
`page/1.png` holds the LAST tool's render. When a call replaces renders a DIFFERENT tool
left in the session, the result says so (`replaced_renders` + a `render_warning` naming
the prior tool). In a shared-session loop, pass a render's `page/1.png` URI to the next
tool before the following call overwrites it, or score/compare under a distinct
`session_id` to keep the reconstruction render viewable alongside.

## Migrating v0.1 documents
A predecessor-dialect document (`scene:`/`visual:` or `deck:`/`slides:`, float
version) converts mechanically: `uv run python tooling/codemod.py doc.yml --from-v01`
(see docs/migration-v01.md for the mapping table) — then validate and render as
usual. Do not hand-translate the envelope.

## Coach — one call, raster to styled document
- `coach_vectorize` — the Vector Construction Coach pipeline end to end: ingest a
  raster -> clean -> redraw (Bezier / snap) -> recolor -> gradientize -> paint
  atmosphere, all driven by a named `style` grammar (clean_line, flat_icon,
  blueprint, comic_ink, woodcut, children_book), then validate + render with the
  silhouette readability gate attached. One call: image -> styled FrameForge doc.
  Still UNVERIFIED heuristic geometry — the render + gate is the check.

## Workflow
Author or propose -> read the returned validation issues + the rendered PNG (or the
`render_warning` when raster is unavailable) -> refine the SDK code/YAML -> re-render.
For reconstruction, follow the loop above. Verify every result against pixels, never
against the YAML alone.
"""
