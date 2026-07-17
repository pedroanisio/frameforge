---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-07-03"
status: proposal
---

# Collision-Free Layout — the overlap model

**Status:** proposal · **Scope:** the 2.5D page/layer overlap model — not `Scene3D`'s
projected 3D, which this collision model does not cover (out of scope *for this proposal*;
the project-wide true-3D scope block was lifted 2026-07-04, so 3D collision handling is
future work, not a permanent exclusion).

## Purpose

Define when a layout is **collision-free**, on the premise that **overlap is a
first-class effect, not a defect**. FrameForge is a design tool: overlapping
type, watermarks bleeding through text, captions over images, and deliberately
illegible stacks are all things it MUST allow. The model therefore never judges
legibility or aesthetics. It distinguishes exactly one thing: an overlap the
author *stacked on purpose* from one that *collided by accident*.

---

## 1 · The canvas is a 3D space

A document occupies a canvas **C** with axes `x, y, z`.

- `x` — horizontal position on the page.
- `y` — vertical position on the page.
- `z` — **stacking axis** (layer / paint order).

The viewport **VP** is **top-down orthographic**: the canvas is viewed straight
along `z` toward the `x, y` plane, with no perspective distortion. A consequence
that governs everything below: **`z` is not visible as depth.** The orthographic
projection discards the `z` axis — displacement along `z` never moves, resizes,
or hides anything in the image; it changes only **which element paints over which**
(higher `z` paints later, on top).

## 2 · Elements are boxes in C

Every element is an axis-aligned box in **C**: an `x, y` **footprint** and a
`z`-**slab** (its layer band). Two elements share a *layer* when their `z`-slabs
coincide; they are on *different layers* when their `z`-slabs are disjoint.

> **Note (correcting "depth ≠ 0 to be visible").** Depth is the element's `z`-slab
> — it places the element on a layer so that "same layer" versus "different layer"
> is well-defined. It is **not** a visibility condition: under the orthographic
> `VP`, depth is the projected-away axis. **Visibility** is governed by the `x, y`
> footprint (non-zero area) and paint (a non-empty fill/stroke/glyph) — a flat
> element is fully visible.

## 3 · Collision = volume intersection in C

> Two elements **collide** iff their boxes intersect in **C** — i.e. they overlap
> in `x` **and** `y` **and** `z` simultaneously.

Collision detection is evaluated on the 3D space of **C**, not on the flattened
projection. Two corollaries fall straight out, and they are the whole point:

- **Different layers never collide.** Elements whose `z`-slabs are disjoint do not
  intersect in **C** *no matter how completely they overlap in `x, y`* — opaque or
  transparent. This is **layering**, and it is the mechanism for every overlap
  *effect*. Their projected overlap is intended; `z` orders it.
- **Same layer + `x, y` overlap = a real intersection.** Elements sharing a
  `z`-slab that also overlap in `x, y` occupy the same volume of **C**. This is the
  candidate collision — two things placed in the *same* layer-cell.

## 4 · Overlap is an effect

Cross-layer overlap (§3, corollary 1) is always permitted and needs no
declaration. Opacity is the author's instrument — the model does not care whether
the top layer hides or blends with the one beneath. A watermark under body text,
a caption over a photo, a double-exposure title: all are `z`-separated stacks, all
collision-free by construction.

## 5 · Same-layer overlap requires consent

The only thing left to classify is a **same-layer** `x, y` intersection (§3,
corollary 2). It may be a deliberate same-layer effect (two overlapping strokes,
interleaved glyphs by design) or an accident (two headers that ran into each
other). Geometry cannot tell intent from accident, so intent MUST be **declared**:

> Every element participating in a same-layer intersection MUST carry
> `overlap: allowed` (default: unset). If, and only if, **all** elements in the
> shared region declare it, the overlap is an intended effect. Otherwise it is a
> **collision**.

`overlap: allowed` is the renamed, corrected form of the earlier `collision =
true` flag — named for what it licenses (the overlap), with `default = false`
preserved so accidents are caught, not waved through. The mutual requirement
stops one element from unilaterally overlapping another.

## 6 · Definition

> A layout is **collision-free** iff every same-layer `x, y` intersection is
> unanimously declared `overlap: allowed`.

Equivalently: no *unintended* volume intersection remains in **C**. Cross-layer
overlaps are never collisions; same-layer overlaps are collisions unless every
party consented.

## 7 · How it is evaluated

Three facts fix the check:

1. **Footprint = rendered ink**, not the authoring box. The `x, y` extent that
   counts is the element's actual painted region after layout, font metrics,
   wrap, and clipping. Two elements in adjacent or loosely-sized boxes whose ink
   never touches do **not** intersect — using the authoring box instead
   over-reports overlaps massively (a box is a layout region, routinely larger
   than its ink).
2. **Same layer = shared `z`-slab** — in the page model, the same
   `page.layers[]` container.
3. Because (1) requires the rendered ink, the collision predicate is **evaluable
   only at render time**, where wrap and real glyph advances exist. See
   `docs/decisions/collision-gate/` for the gate-placement analysis this implies.

## Worked examples

| Case | Layers | `x, y` ink | Declared? | Verdict |
|---|---|---|---|---|
| Proxy headers ("Board's Voting Recommendation" ∩ "More Information") | same | overlap | no | **collision** |
| Watermark behind body text | different (`z`-sep) | overlap | — | effect (fine) |
| Caption over a photo | different (`z`-sep) | overlap | — | effect (fine) |
| Double-exposure title (two texts, one layer, both `overlap: allowed`) | same | overlap | yes (all) | effect (fine) |
| Label + value in adjacent boxes (`Age:` / `62`) | same | **do not touch** | — | not a collision |

The first row is the defect that motivated this document; the last row is the
false positive a box-based check raises and an ink-based check does not.
