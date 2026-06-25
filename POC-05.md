---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-25"
---

# POC-05 — Redrawing *over* a trace: rough contours → clean, intentional lines

ARCHITECTURAL REQUIREMENT (PALS's LAW): every claim below is gated by an
executable check, not asserted in prose.

## The question

> *What about "redrawing" over?*

Tracing, colouring (POC-04), and guide-layers all preserve the trace's
**mechanical** geometry — straight segments and contour noise. **Redrawing over**
replaces it: the trace becomes the under-drawing, and we emit *new* FrameGraph
geometry that follows it but reads as deliberate art. POC-05
(`examples/poc5_redraw.py`, → `out/poc5/redraw.svg`) proves three redraw moves.

## The three moves

1. **SIMPLIFY** — `simplify` is Ramer–Douglas–Peucker: it drops points within a
   tolerance of the chord, keeping only meaningful vertices (endpoints always
   survive). On the office trace this cut **4657 → 3101** points at tol = 3.5.
2. **REDRAW SMOOTH** — `redraw_smooth` re-emits each polyline/polygon as a
   Catmull-Rom **`path`** (cubic Béziers via FrameGraph's `Path().through(...)`),
   with round caps/joins. Jagged contours become flowing strokes
   (**395 curve paths** emitted from the trace). Polygons stay closed and keep
   their fill; polylines become open strokes.
3. **SNAP PRIMITIVE** — `snap_primitives` recognises a near-circular or
   near-rectangular **polygon** and replaces it with a clean `ellipse` / `rect`.
   Circularity is the sound test: vertices near-equidistant from the centroid
   *and* the polygon filling ≈ π/4 of its bounding box (the area test excludes a
   square, whose corner/edge radii alone can sneak under the equidistance
   threshold).

The page shows the progression: **raw trace → smooth → simplified+smooth → bold
inked** (heavy simplify, thick round strokes — a confident-line restyle).

## Soundness gates

| Gate | Check | Result |
|---|---|---|
| Redraw produces curves | `redraw_smooth` emits `path` objects whose `d` carries cubic (`C`) segments | **PASS** (395) |
| Simplify reduces points | point count strictly drops after RDP | **PASS** (4657→3101) |
| It renders | page validates against the model and the SVG contains curve commands | **PASS** |

Run output:

```
[ingest] outline=573 polylines (1400x781)
[gate] redraw emits 395 smooth curve paths (was 0): PASS
[gate] simplify reduces points 4657 -> 3101: PASS
[info] primitive-snap recovered 0 clean ellipse/rect from blobs
[gate] page validates + renders curved paths: PASS
VERDICT: YES - the trace can be redrawn into clean, smooth art
```

### Honest limit (unbiased over flattering)

`snap_primitives` reported **0** on this run — and that is correct, not a bug.
`outline` mode yields open **polylines**; primitive-snap acts on closed
**polygons** (a `region` trace, or shapes you have already closed). The
capability is real and unit-tested on synthetic circles/squares; it simply has
nothing to act on in an outline-only trace. Reported verbatim rather than hidden.

Also honest: Catmull-Rom smoothing interpolates *through* the trace points, so it
cannot invent detail the trace dropped, and very dense noisy contours smooth into
slightly wandering strokes — `simplify` first (higher tol) is the lever, which is
exactly what the "simplified" and "bold inked" panels show.

## Reproduce

```
uv run --group vision python examples/poc5_redraw.py \
    demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg --out out/poc5
uv run python -m pytest tests/test_poc5_redraw.py -q      # 7 tests, no OpenCV
```

Pure geometry (`simplify`, `redraw_smooth`, `snap_primitives`, `is_circular`,
`is_rectangular`, `curve_count`) carries no OpenCV dependency and is unit-tested
directly; only the raster `trace` imports OpenCV (lazily).

## Where this sits in the pipeline

`ingest (POC-03) → colour / guide (POC-04) → redraw (POC-05)` is the full
raster-to-intentional-art path: load a picture, make it programmable, paint or
guide on it, then **redraw** the rough geometry into clean, deliberate FrameGraph
strokes and primitives.

## Verdict

**YES.** A trace can be redrawn over — simplified, smoothed into cubic-Bézier
paths, and snapped to clean primitives — turning a mechanical contour dump into
intentional vector art. The renderer is fully capable; fidelity of the redraw is
governed by the trace it is given and the simplify tolerance chosen.
