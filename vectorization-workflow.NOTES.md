---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-04"
---

# AI-Assisted Vectorization Workflow — implementation note

A single 1440×1000 product/landing composition that sells a raster→vector
service ("from messy bitmap to editable production vector"). Authored entirely
with FrameGraph SDK primitives — **no raster image is imported**; the low-res
JPG on the Input side is *simulated* out of vector pixel blocks.

## Deliverables

| File | What it is |
|---|---|
| `static/examples/vectorization_workflow.py` | The SDK client (source of truth for the asset). |
| `vectorization-workflow.fg.yaml` | Serialized FrameGraph document — the **named-layer, editable source**. |
| `vectorization-workflow.svg` | True render through the repository SVG proxy. |
| `vectorization-workflow.png` | Rasterized via headless Chromium (`tooling/render_chromium.py`). |

Regenerate: `uv run python static/examples/vectorization_workflow.py` then
`uv run python tooling/render_chromium.py vectorization-workflow.fg.yaml --out out/vectorization --max-pages 1`.

## Primitives used

Only the FrameGraph primitive set: `rect` (with `radius` for rounded cards),
`text` (token text-styles + per-span inline styles), `line`, `ellipse` /
`circle`, `polygon`, `path` (cubic béziers for the transform-node glyph and the
export icon), plus `linear_gradient` / `radial_gradient` paint, `rgba()` alpha,
and `effects(shadow=…)` soft shadows. Layout uses absolute coordinates on a
single page with a `bleed()` context for decorative overflow (dot grid, corner
glows, chroma ghost).

## How the low-quality bitmap effect is simulated (vector, not raster)

The Input mark is generated in `draw_pixel_mark()` from the *same* normalized
emblem geometry as the clean output (`_emblem_color(u,v)` — point-in-triangle +
point-in-circle tests over a 26×26 grid), then degraded with layered vector
artifacts, all seeded (`random.Random(0xC0FFEE)`) so it is deterministic:

1. **Quantization** — each grid cell is a filled `rect`, giving chunky "pixels"
   and jagged, aliased edges for free.
2. **Colour jitter** — per-cell RGB jitter (±22, occasional ±34 "dead pixel")
   simulates JPEG colour banding.
3. **Chroma ghost** — a faint magenta/cyan-shifted copy offset down-right (JPEG
   chroma bleed), drawn in the `bleed()` pass.
4. **Scan noise** — sparse random speckle cells in the background region.
5. **Compression haze** — a translucent white wash, horizontal scanline bars,
   and "mosquito" speckle blocks near edges.
6. **Fuzzy wordmark** — the wordmark is double-printed with a 1.4px offset and
   reduced opacity to read as low-res type.

## How the clean vector output is layered

`draw_vector_mark()` rebuilds the identical mark as smooth, crisp geometry,
painted back-to-front in editable sub-layers: **sun** (amber radial-lit
`ellipse` + ring) → **back peak** (violet gradient `polygon`) → **front peak**
(blue gradient `polygon` + white snow-facet) → **ground** (charcoal rounded
`rect`). Editable-vector cues are drawn on top: white anchor squares at every
polygon vertex and a béziér control-handle pair on the apex, plus a dashed
artboard frame and a crisp wordmark.

## Named layers (semantic groups)

The document is organized into nine named layers, preserved verbatim in the
`.fg.yaml` source (z-order top-down):

`background · hero · before_after_panel · input_bitmap_simulation ·
output_vector_reconstruction · workflow_pipeline · api_flow_card · value_cards ·
annotations`

Note on editability: the **`.fg.yaml` is the layered, inspectable, editable
artifact** — layer identity, object structure, tokens and per-object styles all
live there. The SVG proxy renderer flattens to paint order (every primitive is
still an individual, inspectable SVG element, but the layer *names* are not
emitted as `<g id>` wrappers). Edit the `.py`/`.yaml` and re-render.

## Reusable SDK components

These local helpers are written to be lifted into other clients:

- `card(L, box, …)` — rounded panel with token fill/border and soft/lift shadow.
- `pill(L, x, y, label, …)` — auto-sized dot+label chip.
- `arrow(L, x1,y1,x2,y2, …)` — line with a computed two-stroke arrowhead.
- `lg()` / `rg()` — angle- and point-based gradient shorthands.
- `icon_upload / icon_analyze / icon_rebuild / icon_review / icon_export` —
  24px primitive line-art icons, reused across the pipeline and the value cards.
- `_emblem_color(u,v)` + `draw_pixel_mark` / `draw_vector_mark` — the
  before/after "same mark, reconstructed" pattern, parameterized by one shared
  normalized geometry so any emblem can be swapped in.

## Honesty framing

The copy is deliberately "AI-assisted", not "automatic": the pipeline includes
an explicit **Human review** step, the transform node is labelled **AI + human**,
the API card ends with a human-review gate row (`POST /jobs/{id}/approve`), and
the footer states *"AI-assisted · human-reviewed · not fully automatic."* The
asset does not overclaim full automation.
