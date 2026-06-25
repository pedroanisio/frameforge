---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-25"
---

# POC-04 — Colour & gradient a trace, or use it as a guide to draw on top

ARCHITECTURAL REQUIREMENT (PALS's LAW): every claim below is gated by an
executable check, not asserted in prose. Heuristic/AI output is untrusted until
verified.

## The two questions

> *Can we fill / add colours, gradients on those traces? Or use them as a
> guideline so we can draw on top of them?*

**Both, yes.** They are two distinct workflows, and FrameGraph supports each as a
native model feature (`Gradient` paint, `fill_opacity`/`opacity`). POC-04
(`examples/poc4_color_and_guide.py`, → `out/poc4/color_guide.svg`) proves both on
the office line-art with four panels.

## 1 — Fill / colour / gradient a trace

A `region` trace is **closed polygons**, and a polygon's `fill` may be a flat
colour *or* a FrameGraph `Gradient` (`{kind, stops, angle}`). An `outline` trace
is **open polylines** — those are the *lines*, not fillable areas. So the colour
recipe is:

> re-paint the `region` polygons, then lay the `outline` strokes on top.

- **`recolor_cycle(region, palette)`** — assign palette colours to fills by order
  (posterize). Panel 1 fills the figures/desk/backdrop with vivid flats under the
  black line art — a real flat-colour illustration.
- **`gradient_fills(region, …)`** — lift every flat fill into a 2-stop gradient
  (`hexshift` lightens/darkens the base colour for the stops). Panel 2.

### Honest limit (unbiased over flattering)

Colourising a trace by **tone** (luma→palette) only works when the *source has
tone*. Pure line-art on a near-white ground has almost no area colour to recover,
so a luma map washes out pale — that is why Panel 1 uses an explicit posterize
(`recolor_cycle`) and why, for line-art specifically, the **draw-on-top** path
below is the better way to add colour. Region-fill colourisation shines on
photographic / already-coloured sources, not on bare line drawings.

## 2 — Use it as a guide to draw on top

- **`as_guide(outline, opacity=0.18)`** — dim the line-art into a low-opacity
  "pencils" layer (Panel 3).
- **`author_overlay(...)`** — author NEW colour/gradient FrameGraph objects over
  the guide (a gradient window light, the presenter's jacket, a whiteboard tint,
  foliage), then re-lay the guide a touch darker for the final "ink" (Panel 4).

This is the ink-and-colour-over-pencils workflow: the trace is the under-drawing;
you paint native objects on top.

## Soundness gates

| Gate | Check | Result |
|---|---|---|
| Gradient fills are real | `gradient_fills` turns every flat fill into a `{stops:…}` dict; geometry unchanged | **PASS** |
| Guide is a guide | `as_guide` sets `opacity ≤ 0.3` on every object; geometry unchanged | **PASS** |
| It renders | page validates against the model and the SVG contains gradients | **PASS** |

Run output:

```
[ingest] region=61 polygons, outline=456 strokes (1400x781)
[gate] gradient_fills lifts 61/61 fills to gradients, geometry kept: PASS
[gate] guide layer is low-opacity, geometry kept: PASS
[gate] page validates + renders gradients: PASS
VERDICT: YES - colour, gradient, and draw-on-top all work
```

Unit tests (no OpenCV): `tests/test_poc4_color_and_guide.py` (7 tests) cover
`hexshift`, `gradient_fills`, `recolor_cycle`, `as_guide`, `author_overlay`,
`gradient_count`, and the page build.

## Reproduce

```
uv run --group vision python examples/poc4_color_and_guide.py \
    demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg --out out/poc4
uv run python -m pytest tests/test_poc4_color_and_guide.py -q
```

## Verdict

**YES to both.** Region traces take flat *and* gradient fills (colour the lines by
painting regions under them); and any trace can be dropped to a low-opacity guide
to draw native colour on top. The one honest caveat — tone-based colourisation
needs a toned source — is a property of line-art inputs, not of the renderer.
