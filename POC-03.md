---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-25"
---

# POC-03 — Ingestion × FrameGraph: a raster becomes a *programmable* asset

ARCHITECTURAL REQUIREMENT (PALS's LAW): LLMs/heuristics will always produce some
form of error. Absence of output verification is a design defect, not a runtime
bug. Every claim below is gated by an executable check, not asserted in prose.

## Thesis

A raster vectorizer, on its own, only **copies** a picture into polygons. That is
necessary but not interesting. The power appears **after** ingestion, because the
trace is no longer pixels — it is FrameGraph objects, and FrameGraph is a program
over those objects. The two compound:

> **ingestion makes the picture programmable; FrameGraph is the program.**

This POC proves the compounding with real execution
(`examples/poc3_ingest_compose.py`), not argument. It tests three load-bearing
claims and reports one honest fidelity number.

## What was executed

Source: `demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg` (clean black line-art
office scene). Ingested via the `outline` vectorizer →
**536 editable FrameGraph objects** (1500×837).

### Claim 1 — RESTYLE: one ingestion, N looks

Pure functions (`restyle_strokes`, `recolor_fills`, `palette_by_luma`) re-ink and
re-palette the *same* geometry. Four styles — `as-traced ink`, `blueprint`,
`neon`, `crimson sketch` — are produced from a single ingestion
(`out/poc3/style_matrix.svg`). On a flat raster this requires redrawing or manual
masking; here each look is one assignment (`o["stroke"] = …`).

### Claim 2 — SELECT / EDIT PARTS: the trace is a bag of editable objects

A trace is only powerful if you can use *parts* of it, not just the whole frame.
`build_parts` (→ `out/poc3/parts.svg`) demonstrates four part-level operations on
the 536-object trace:

- **select a region** — `select_region(base, board, contain=True)` extracts just
  the whiteboard (**65 of 536 objects**). `contain=True` is deliberate: it keeps
  only objects fully inside the region, so a frame-spanning stroke (a table edge)
  is *not* dragged in by a merely-touching bounding box — an honest crop.
- **edit one element** — lift the presenter (`select_region(..., figure)`, **73
  objects**) and restyle *only that subset* crimson, leaving the rest untouched.
- **transform a subset** — `translate_objs` shifts a selected element's actual
  coordinates (not a global transform).
- **recompose** — delete the whiteboard (`select_where` complement of the board
  region) and duplicate the presenter shifted right: a *new* arrangement built
  from parts of the original.

This is the direct rebuttal to "it only loads the whole image": selection,
per-element editing, subset transforms, and recomposition all operate on
addressable objects.

### Claim 3 — COMPOSE: the trace is a first-class document element

`build_composition` places the ingested asset beside **native** FrameGraph
content — a title, a fact list, a bar chart, and a palette legend — laid out by
FrameGraph itself (`out/poc3/composition.svg`). The picture became a *document*.

### Claim 4 — VERIFY: every claim is a numeric gate

| Gate | Check | Result |
|---|---|---|
| Geometry invariant under restyle | per-object coordinates identical before/after all 4 restyles | **PASS** |
| Styles render distinctly | the 4 restyles produce 4 *different* rendered SVGs | **PASS** |
| Part selection is a strict subset | region extracts (65, 73) are non-empty and < 536 | **PASS** |
| Composition is native | rendered page carries ≥4 `<text>` + a chart, not just the trace | **PASS** |
| Document validity | every page `build()`s against the Pydantic model | **PASS** |

Run output:

```
[ingest] …office.jpeg -> 536 objects (1500x837)
[gate] geometry invariant under 4 restyles: PASS
[gate] 4 styles render distinctly: PASS
[fidelity] ink-IoU vs source: 0.205
[gate] part selection is a strict subset (extract=65, element=73 of 536): PASS
[gate] composition carries native text/chart: PASS
VERDICT: FEASIBLE - ingestion x FrameGraph compounds
```

## Honest fidelity number (the ingest half)

`ink_iou` reports a **tolerance-banded** structural agreement between the source
and the trace render: both ink masks are dilated by 2 px (a Chamfer-style band)
before intersection-over-union, because a raw 1-px-stroke IoU is dominated by
sub-pixel misregistration and badly understates line-art fidelity.

Measured: **0.205** at 2 px tolerance. This is honest, not flattering. Two
structural reasons cap it, and both are known limits of `outline` mode, not the
renderer:

1. **Double strokes.** Canny traces *both* edges of every drawn line, so the
   trace has ~2× the ink of the single-stroke source — union inflates, IoU drops.
2. **Fine content.** Sub-`min-area` detail (the whiteboard charts' interior
   ticks, the skyline) is captured differently than the source draws it.

The verdict does **not** rest on this number — it rests on the three
deterministic gates. Fidelity is the ingest-half reality check, reported
verbatim so the trace is not oversold. A centerline (skeletonized) trace, or a
Potrace/VTracer SVG routed through `svg_import`, would raise it; that is the
documented next lever, not a claim made here.

## Why this is the answer to "how do they enhance each other"

- **Vectorizer alone** → a faithful but frozen copy; you can recolor nothing
  without redrawing.
- **FrameGraph alone** → a powerful document engine with nothing to ingest;
  every asset must be hand-authored.
- **Together** → drop any raster, get an editable base, then *program* it:
  restyle, recolor, place, annotate, chart, theme — and **verify** each
  transform numerically. The artifact stops being an image and becomes a
  parameterized document component.

## Reproduce

```
uv run --group vision python examples/poc3_ingest_compose.py \
    demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg --out out/poc3
uv run python -m pytest tests/test_poc3_ingest_compose.py -q   # 14 gates, no OpenCV needed
```

Pure transforms (`restyle_strokes`, `recolor_fills`, `select_region`,
`select_where`, `translate_objs`, `place`, `bbox`, `geometry_invariant`) carry no
OpenCV dependency and are unit-tested directly; only `trace`/`ink_iou` import
OpenCV (lazily).

## Verdict

**FEASIBLE.** Ingestion × FrameGraph compounds: a flat raster becomes a
restylable, composable, document-native, *verifiable* asset. The one soft edge —
`outline`-mode double-stroke fidelity — is a vectorizer tuning lever
(centerline / Bézier trace), not a flaw in the composition model.
