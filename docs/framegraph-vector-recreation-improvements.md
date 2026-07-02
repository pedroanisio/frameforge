---
title: "Improving FrameGraph for Reference Image Recreation"
status: >-
  partially delivered — re-triaged 2026-07-01. The earlier claim that these
  observations were "folded into docs/roadmap-draft.md" was FALSE (the roadmap
  contains none of them) and is corrected here; see the status re-triage table.
context: "Written after recreating an abstract mixed-media reference image through framegraph.sdk over the FrameGraph MCP renderer."
disclaimer:
  notice: >-
    No information within this document should be taken for granted. Any
    statement or premise not backed by a real logical definition or a
    verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: >-
    Claude Opus 4.8 via Claude Code; status re-triage table + corrected
    provenance note by Claude Fable 5 via Claude Code (2026-07-01)
  date: "2026-06-24 (re-triaged 2026-07-01)"
---

# Improving FrameGraph for Reference Image Recreation

## Status re-triage (2026-07-01)

Correction (by Claude Fable 5 via Claude Code): this document previously
claimed its observations were "folded into docs/roadmap-draft.md". That was
false — the roadmap tracks none of these items. The true per-recommendation
status, verified against the live tree:

| # | Recommendation | Status (verified 2026-07-01) |
|---|---|---|
| 1 | Page-space PNG crop/zoom | **Partial** — crop/zoom landed in the *measurement* lane (`measure_image` crops, `compare_images` regions, `vectorize_image` crop, `workspace` viewport) but the MCP *render* tools (`run_sdk_code` / `run_sdk_client` / `render_framegraph_yaml`) still render whole pages only. |
| 2 | Crop around an object id | **Open** — no render tool accepts an object id. |
| 3 | Combined inspect report (PNG + structural facts) | **Open** — no `inspect` in `framegraph/sdk` or `framegraph/mcp`. |
| 4 | Reference-image analysis helpers | **Delivered** as MCP tools — `measure_image` (regions/landmarks/coordinate system) and `vectorize_image` colour-region clustering cover palette/region/line extraction. |
| 5 | Texture / dry-brush macros | **Open** — no `concrete`/`spray`/`dry_brush`/`feathered_blob`/`halftone` helpers exist (`greeble`/`hatch_fill`/`sparkline` are the closest SDK macros). |
| 6 | Stroke ergonomics (`cap`/`join` aliases) | **Delivered** — `framegraph.sdk.paint.stroke(width, color=…, cap=…, join=…)` normalises to the P3 paint/geometry split. |
| 7 | Blend/mask ergonomics | **Partial** — `clip_*` helpers ship in the SDK and the model carries `mix_blend_mode`/`mask`; no dedicated blend/mask authoring context managers were found. |
| 8 | Vectorization pipeline | **Delivered** — `vectorize_image` (region / outline / potrace trace / layers) plus `propose_from_image`/`propose_from_svg`. |

The open items (1-render-lane, 2, 3, 5) are not tracked in the roadmap; they
remain recorded here as the untracked residue of this note.

---

This note records what would most improve an AI author's ability to recreate a
reference image closely with FrameGraph. The observations come from a concrete
exercise: translating a tall abstract image with a gray concrete ground, neon
paint smears, black charcoal lines, splatters, translucent overlays, and gritty
texture into a FrameGraph vector document, then rendering it through MCP.

The short version: the SDK is already capable of describing the composition,
palette, and object structure. The gap is not basic shape vocabulary. The gap is
fast visual feedback, image-aware authoring tools, and higher-level texture and
trace primitives that preserve the messy, non-geometric qualities of the source.

## What worked

The SDK was effective for the large compositional structure:

- Tall canvas and page-space coordinates matched the reference image well.
- Layers made it natural to separate concrete background, paint fields, black
  charcoal marks, splatter, corrosion, and foreground scratches.
- Paths, polylines, ellipses, radial gradients, linear gradients, opacity, and
  stroke styles were enough to approximate the main visual vocabulary.
- Deterministic random seeds made texture repeatable.
- MCP raster output made it possible to inspect the actual PNG, not just the
  source YAML or SVG.

The best results came from authoring many small, ordinary primitives rather than
adding a new abstraction too early: mottled background dots, repeated scratches,
speckles, feathered paint fragments, and offset duplicate charcoal strokes.

## What failed or remained weak

Several parts of the reference were hard to reproduce faithfully:

- Paint smears in the source have photographic edges, pigment granularity,
  compression-like color mixing, and soft masks. Polygonal blobs and SVG
  gradients still read as vector art.
- Charcoal and spray marks have broken, dirty edges. A single stroked path is
  too clean unless surrounded by many particles and jittered duplicates.
- Concrete texture needs multi-scale noise. Hand-authored ellipses can suggest
  it, but the result is less organic than the reference.
- Fine visual tuning was slow because every pass required guessing coordinates,
  rendering the whole page, and manually inspecting the result.
- The AI author needed to reason from the reference image by eye. There was no
  SDK/MCP helper to extract a palette, dominant regions, line skeletons, or
  texture fields from the source.

The main lesson is that closer recreation needs a tighter perception-authoring
loop, not merely more primitive shapes.

## Highest-impact SDK improvements

### 1. Page-space PNG crop and zoom

Whole-page renders are useful for composition, but too coarse for tuning
texture, edge quality, and small defects. The SDK and MCP should support
page-space crop and scale as first-class output.

```python
render_png(doc, "whole.png", page=0, scale=2)
render_png(doc, "detail.png", page=0, crop=[420, 280, 260, 180], scale=4)
```

The crop must use FrameGraph page coordinates, not pixel coordinates. That keeps
the authoring and inspection coordinate systems identical.

### 2. Crop around object id

The author should be able to name an object or group and inspect it immediately.

```python
render_png(doc, "left-smear.png", around="cyan-smear-left", pad=32, scale=4)
```

This avoids coordinate bookkeeping and makes iterative refinement much faster.
For image recreation, this is especially useful for repeated local passes over
one region: a paint smear, a line intersection, a splatter cluster, or a texture
patch.

### 3. Combined visual inspection report

The most useful agentic primitive would return both a PNG and structural facts.

```python
img, report = inspect(doc, crop=[420, 280, 260, 180], scale=4)
```

For recreation work, the report should include:

- objects intersecting the crop;
- object ids, types, boxes, fills, strokes, and opacities;
- validation findings intersecting the crop;
- optional color histogram of the rendered crop;
- optional object count and overdraw estimate.

This fuses the visual loop with the document structure, which is much more
useful than forcing the author to inspect an image and parse a separate JSON
report.

### 4. Reference-image analysis helpers

The SDK or MCP should provide a small, deterministic image-analysis surface for
reference recreation. This should not be an image generator. It should extract
usable authoring facts from a supplied image.

Useful helpers:

```python
palette = inspect_reference("ref.jpeg").palette(k=12)
regions = inspect_reference("ref.jpeg").color_regions(k=24, min_area=80)
lines = inspect_reference("ref.jpeg").line_skeleton(threshold=0.72)
texture = inspect_reference("ref.jpeg").texture_map(tile=64)
```

For the abstract reference image, this would have helped identify:

- dominant gray ground tones;
- neon magenta, cyan, green, orange, and red clusters;
- long black line skeletons;
- splatter-heavy zones;
- concrete texture intensity by region.

The output should be page-space normalized so the author can convert findings
directly into FrameGraph objects.

### 5. Texture and dry-brush macros

The SDK needs procedural texture helpers that lower to ordinary FrameGraph
objects. These are still deterministic vector outputs, but they encode common
messy visual patterns.

Proposed helpers:

```python
layer.extend(texture.concrete([0, 0, W, H], seed=7, scale=0.8))
layer.extend(texture.spray([cx, cy], radius=80, density=0.7, color="#000"))
layer.extend(texture.dry_brush_path(points, width=8, breakup=0.45))
layer.extend(texture.feathered_blob(box, fill="#ff1689", roughness=0.35))
layer.extend(texture.halftone_noise(box, colors=[...], density=0.4))
```

The key is that these helpers should return inspectable primitives, not opaque
bitmaps by default. The user can still audit and crop them.

### 6. Better path/stroke ergonomics

During the recreation, stroke geometry had to use model-native names such as
`stroke_linecap`. That is correct at the model level, but the authoring layer
should accept ergonomic aliases and normalize them.

Examples:

```python
stroke(5, color="#111", cap="round", join="round")
path(..., stroke_style=stroke_style(width=5, cap="round"))
```

The SDK already has a `stroke()` helper, but complex generated code often still
assembles inline dictionaries. A stricter helper-first style or normalization
step would reduce failed render passes.

### 7. Blend modes and mask ergonomics

The reference image depends on layered translucent paint and photographic color
mixing. FrameGraph should make blend modes and masks easy to author.

Useful authoring forms:

```python
with layer.group(blend="multiply", opacity=0.65):
    ...

with layer.mask(feathered_blob(...)):
    layer.rect(..., fill=linear_gradient(...))
```

Even if the core model already supports relevant CSS fields, the SDK should
surface them in a way that fits art-making workflows.

### 8. Optional vectorization pipeline

A practical recreation workflow needs a bridge from raster reference to editable
vector approximation.

Proposed pipeline:

```python
trace = vectorize_reference(
    "ref.jpeg",
    modes=["regions", "strokes", "splatter"],
    max_objects=1200,
)
page.extend(trace.objects)
```

This should be deliberately approximate and editable. The goal is not perfect
autotrace. The goal is to bootstrap the layer stack so the AI author can polish
instead of starting from a blank canvas.

## MCP improvements

The MCP server should expose the same visual loop directly:

```python
run_sdk_code(..., raster_png=True, crop=[...], scale=4)
render_framegraph_yaml(..., raster_png=True, crop=[...], scale=4)
inspect_framegraph_yaml(..., crop=[...], scale=4)
inspect_reference_image(path="ref.jpeg")
```

For AI authoring, MCP should return:

- a PNG content block for the requested crop;
- the rendered SVG/YAML as linked resources;
- the structural report as JSON;
- warnings when the crop is too large or too low-resolution for visual reading.

The current whole-page PNG support is necessary, but crop and zoom are what make
it operationally useful.

## Recommended implementation order

1. Add `render_png(..., crop, around, scale)` to the SDK and MCP.
2. Add `inspect(..., crop, scale)` returning PNG plus intersecting object facts.
3. Add SDK normalization for stroke style aliases.
4. Add procedural texture macros for concrete, spray, dry brush, feathered blobs,
   and splatter.
5. Add reference-image analysis helpers for palette, regions, line skeletons,
   and texture maps.
6. Add an approximate vectorization pipeline that emits editable FrameGraph
   primitives.

This order improves the authoring loop before adding more visual vocabulary.
Without crop/zoom/inspect, richer primitives are harder to tune.

## Bottom line

To recreate images closer to the original, FrameGraph should become better at
three things:

1. **Seeing its own output** through cheap, high-DPI page-space crops.
2. **Understanding the reference** through palette, region, line, and texture
   extraction.
3. **Authoring messy media** through deterministic texture, spray, dry-brush,
   feathering, masks, and blend helpers.

The SDK does not need to become a photorealistic generator. It needs to become a
better deterministic visual workbench: reference-aware, crop-inspectable, and
rich enough to express imperfect physical marks without hand-writing hundreds of
low-level primitives each time.
