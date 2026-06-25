---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-25"
---

# Coach synthesis — what we built, how it maps to the coach, what to improve

ARCHITECTURAL REQUIREMENT (PALS's LAW): claims here are tied to live modules and
tests, not asserted. The coach's own design rule holds: it scaffolds the process,
it does not fake quality or measurement.

## 1. What this session achieved (the exploration lane)

| Artifact | Proves |
|---|---|
| `tooling/vectorize_image.py` + `framegraph/vision/…/vectorize.py`, `svg_import.py` | raster → editable FrameGraph objects (region fills / outline line-art / OCR) |
| **POC-03** ingest×compose | the trace is *programmable*: restyle, **select a region / edit one element / recompose**, place beside native text+chart; gated (geometry-invariant, distinct renders, strict-subset) |
| **POC-04** colour/guide | fill + **gradient** region traces; use line-art as a low-opacity **guide** to draw on top |
| **POC-05** redraw | **redraw over** a trace: RDP-simplify, **smooth to Catmull-Rom cubic paths**, **snap blobs to clean primitives** |
| `guided_paint` + guided-draw showcase | render-safe **atmosphere** (glow/haze/vignette/wash) → finished painted illustration over a guide |

## 2. How the maintainer's `framegraph/coach/` distilled it

The coach is the **honest, buildable subset** — it reuses the SDK, keeps creativity
with the model, and ships rubrics (advisory), not fake scores. It independently
converged on much of the exploration lane, and added the process scaffold:

| Coach module | Relationship to our work |
|---|---|
| `coach.ingest` (`ingest`/`recolor_to_style`/`gradientize`) | **same lane** as POC-03/04 (vectorize + re-skin + gradient) — now canonical |
| `coach.clean` (`denoise`/`simplify_strokes`/`smooth_strokes`, RDP) | **same lever** as POC-05's `simplify` (RDP was duplicated in both) |
| `coach.style` (`StyleProfile`, `resolve_style`) | **formalises** POC-04's ad-hoc palettes into style-as-grammar (weights/fill/hatch/palette) |
| `coach.layers` (`STAGES`, `validate_order`) | **new** — the "no detail before structure" discipline (the highest-value rule) |
| `coach.silhouette` (`to_silhouette`) | **new** — readability gate (flatten → judge); wired into MCP |
| `coach.intent`, `coach.critique` | **new** — typed brief + per-stage advisory rubrics |

**Finding:** the exploration POCs and the coach overlapped (RDP, hexshift,
gradientize, recolor were implemented twice). The coach is the right home; the
POCs are the proofs that justified it.

## 3. The gap we closed this turn

The coach could ingest, clean, and *recolour*, but its colour stages
(`07_flat_colors` → `09_highlights`) produced **flat** output — it had **no depth
toolset**. The one piece of the exploration lane the coach was missing was the
painting layer, and it lived only in `examples/`.

**Contribution — `framegraph/coach/paint.py`** (boundary-clean: sdk + stdlib):

- Promotes the render-safe primitives (`glow`, `haze`, `vignette`, `wash`,
  `soft_shadow`, `fade`/`stop`/`linear`/`radial`) into the coach.
- Adds **`atmosphere(style, w, h)`** — depth **driven by the resolved
  `StyleProfile` palette** (key-light glow from the palette's lightest colour,
  vignette from its darkest). Paint that is *on-brand by construction*, not
  hand-picked — this is the "improve **with** the coach" part, not just a port.
- DRY: `examples/guided_paint.py` is now a thin re-export of `coach.paint`
  (RDP/hexshift/atmosphere live in one place).

The hard constraint is encoded, not hidden: cairosvg (the browser-free
rasteriser) **drops blur filters and `mix-blend-mode`** (verified), so every
primitive fakes soft light with *transparent gradient stops* — it survives the
fallback path a real browser would render anyway.

`examples/coach_paint_showcase.py` runs the whole coach in one pass on a real
image — `parse_intent → resolve_style → create_plan/validate → ingest(region+
outline) → clean → recolor_to_style → gradientize → atmosphere → to_silhouette` —
turning a photo into an on-brand, atmospheric, layer-disciplined illustration,
with the silhouette gate on the cleaned line-art.

## 4. What to improve next (ranked)

1. **`coach.redraw`** — fold POC-05's `redraw_smooth` (Catmull-Rom cubic paths)
   and `snap_primitives` (blob→ellipse/rect) into the coach's `06_line_art`
   stage. Today `coach.clean.smooth_strokes` only moving-averages *polylines*; it
   cannot emit true Bézier strokes or recognise primitives. (S)
2. **Style-aware cleanup** — let `clean`'s `eps`/`smooth` come from the
   `StyleProfile` (`woodcut` ≠ `clean_line` simplification). (S)
3. **Browser/resvg rasteriser path** — so the *blur* versions of glow/shadow
   render (not just the transparent-gradient fallback). The model already emits
   correct filters; only the rasteriser is the limit. (M)
4. **Ingestion fidelity gate** — render→compare-to-source (POC-03's tolerance-
   banded ink-IoU) as a coach gate beside `silhouette`, to auto-tune
   colors/detail. (M)
5. **Semantic selection** — POC-03's region selection is geometric (bbox);
   segmentation (SAM/rembg) would make "the figure" a *named* layer. (L)

## Verdict

The session's exploration converged with the coach; the coach is the canonical
home. The one missing capability — a render-safe, **style-driven** painting layer
— is now in the coach (`coach.paint`), unifying the colour stages and producing
on-brand depth. Next highest-value: bring the redraw (smooth+snap) lane in too.
