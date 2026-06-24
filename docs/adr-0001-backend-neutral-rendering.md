---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "claude-opus-4-8 via Claude Code"
  date: "2026-06-24"
---

# ADR 0001 — Backend-neutral rendering & sub-renderer decoupling (Increment 3)

## Status

Accepted, staged. Slice **3a** is implemented. Slice **3b** is in progress —
steps **3b-1** (application layer builds zero SVG) and **3b-2** (the `stroke`
parameter is a neutral `Stroke` value object) are done; the remainder (the rest of
the parameter neutralization, completing the port, and a second backend) is scoped
in the milestone table below.

### Update (3b-1): the builder was already painter-mediated

Inspection corrected this ADR's initial pessimism (per §14, the prior claim is
revised against the evidence). The builder does **not** itself do SVG string
composition: it calls **29 painter methods** and concatenates their opaque
return values, and the effect/transform/clip/group wrapping already delegates to
the painter (`style_group`, `clip_wrap`, `transform_group`, …). Only **two** raw
`<svg>`/`<g>` literals remained in the application layer (a MathJax embed and a
scale group); both were routed through painter methods (`embedded_svg`,
`transform_group`), **byte-identically**. The application layer now constructs no
SVG syntax at all — so the real neutrality blocker is narrower than "rewrite the
composition core."

## Context

Increments 1–2 decomposed the monolithic SVG `Renderer` (2107 → 1397 lines) into
the rendering bounded context's application layer plus cohesive collaborators:
pure dependency-inverted domain services (`TextFitter`, `StyleValues`,
`math_text`), an infrastructure math adapter (`MathSvgRenderer`), and two drawing
*sub-renderers* (`UmlRenderer`, `DimensionRenderer`). Every step was byte-identical
against the golden render baseline.

Two coupling problems remain, and they are **distinct** even though both are
filed under "Increment 3":

1. **Sub-renderer back-reference.** `UmlRenderer`/`DimensionRenderer` reach into
   the concrete `Renderer`'s surface — including *private* methods
   (`_shape_fill`, `_shape_stroke`, `_arrow_attrs`, `_painter`) — via a `self._r`
   back-reference. They depend on the whole Renderer, not a named contract.

2. **SVG-shaped painter port.** `ScenePainter` methods *return SVG string
   fragments* (`rect()` → `'<rect .../>'`) that the builder concatenates and wraps
   (`_with_effects`/`_with_transform`/`_with_style_clip` are string operations).
   Because the port's currency is SVG text, a LaTeX or Chromium backend cannot
   implement it — which is exactly why LaTeX renders through a *separate*
   `render_latex.py`/`_Transpiler`/`FigureTikz` fork rather than as an adapter.

## Hard constraint

`golden-check` pins each b1/ oracle page's SVG output by SHA-256
(codebase-standards.md §3/§8). Any refactor that is **not** byte-identical fails
the gate until the lock is re-pinned with `make golden`. This constraint shapes
the staging below: byte-identical work lands freely; output-changing work needs a
deliberate re-pin budget and review.

## Decision

Split Increment 3 into two slices by whether they can be byte-identical.

### Slice 3a — `RenderContext` (decouple the sub-renderers) — byte-identical ✅

Introduce a `RenderContext` Protocol (`domain/ports.py`) naming the minimal
rendering-primitives contract the sub-renderers need: `color`, `text_style`,
`render_text`, `measure`, `ellipsize`, `shape_fill/stroke/radius`, `arrow_attrs`,
`obj`, `painter`, `stroke_styles`, and `note_skip()`. A thin application adapter
(`RendererContext`) satisfies it by delegating to the `Renderer`; the sub-renderers
depend on the **Protocol**, not the concrete Renderer.

- **Why:** dependency inversion for the sub-renderers; a named, *mockable*
  contract; and — importantly — this contract is the explicit list of primitives
  a future backend-neutral builder must provide. It turns an implicit reach-into-
  privates into a documented seam.
- **Cost/risk:** S. Pure indirection; behaviour and bytes unchanged.

### Slice 3b — backend-neutral emission (LaTeX/Chromium as adapters) — NOT byte-identical ⚠️

Make the builder emit backend-neutral primitives so each backend produces its own
output. Two candidate shapes, both **large rewrites of the string-composition
core**:

- **(i) Retained-mode `Scene`.** The builder emits primitive *value objects* (a
  display list) instead of strings; each backend (SVG, LaTeX, Chromium) consumes
  the Scene. The `ScenePainter` docstring already names this as the target. Gives
  an inspectable second IR; biggest blast radius (every emit site + all `_with_*`
  composition becomes value-object construction).
- **(ii) Accumulate-mode painter.** Painter methods append to the painter's own
  buffer instead of returning fragments; the builder drives without concatenating.
  Smaller conceptual change, but `_with_effects`/`_with_transform`/`_with_style_clip`
  group-wrapping still has to move into the painter.

**Revised understanding (post 3b-1).** The composition is *already* in the painter,
so the remaining blocker is narrower: the port's **parameter shapes are
SVG-flavored** — `painter.rect(..., fill, stroke, ...)` receives pre-formatted SVG
attribute strings (e.g. `stroke` is `' stroke="#000" stroke-width="1"'`, built by
`_shape_stroke`/`_border_stroke`). A LaTeX/Chromium adapter cannot consume those.
The remaining 3b work splits into the milestones below. The original framing —
**neutralize the painter parameters** (pass neutral value objects: a
`Stroke{color,width,dash,...}`, a `Fill`/paint, radii — each backend formats them)
— is preserved here for context, since its hardest piece (`stroke`) is now done:

   **Finding (revised estimate → L–XL, not L).** `stroke` is not a clean
   parameter: `StrokeResolver.resolve` builds a **10-attribute ordered SVG string**
   (`stroke`/`-width`/`-dasharray`/`-dashoffset`/`-linecap`/`-linejoin`/
   `-miterlimit`/`paint-order`/`vector-effect`/`-opacity`), and the builder treats
   it as a **composable fragment** — `stroke + self._arrow_attrs(o)` concatenates
   it with arrow-marker attribute strings across ~7 sites, over ~44 painter-
   primitive calls. Neutralizing it therefore needs a `Stroke` *and* a marker/arrow
   value object plus an object-level composition model, not a mechanical parameter
   swap. The SVG backend can still format to identical bytes (no re-pin), but this
   is a **dedicated, carefully-staged effort** with real byte-identity risk — not a
   single drop-in change. `fill` is already near-neutral (a colour/url value the
   painter formats via `fill_attr`), so it is the cheap part.

   **Update (3b-2): `stroke` is now neutralized.** A backend-neutral
   `Stroke{color,width,dash,dashoffset,linecap,linejoin,miterlimit,paint_order,
   vector_effect,opacity}` value object (`stroke_resolver.Stroke`) is the painter's
   `stroke` parameter at every primitive call. `StrokeResolver.fields(o) -> Stroke`
   resolves it; the SVG backend formats it via `StrokeResolver.format_attr` (the
   one place SVG stroke bytes are produced). `_shape_stroke`/`_border_stroke` return
   `Stroke | None`; the ~44 primitive calls and every hand-written stroke literal
   were converted; the ~7 arrow-composition sites moved their marker attributes to a
   contained `extra=` trailing-attrs param on `line`/`poly`/`path` (markers are
   genuinely backend-specific — their value-object is a later slice). Delivered in
   two byte-identical steps: **3b-2a** (Stroke value object + `resolve = format_attr
   ∘ fields` split) and **3b-2b** (painter + all consumers migrated). Verified
   byte-identical across all 252 fixture pages; no golden re-pin. `tests/
   test_stroke_value.py` pins the value object and formatter.

### Remaining milestones (post-3b-2, grounded against the live tree)

`stroke` — the hard one — is done (above). The set below is what is left to make a
non-SVG backend droppable, each item grounded in the current `ports.py` /
`painters/svg.py` / `latex/`:

| ID | Milestone | Status | Effort | Output invariant |
|----|-----------|--------|--------|------------------|
| **3b-2** | Neutralize the `stroke` parameter (`Stroke` value object) | ✅ **done** | L | byte-identical (verified, 252 pages) |
| **3b-3** | Neutralize the remaining SVG-string-shaped painter params | next | M | byte-identical |
| **3b-4** | Complete + correct the `ScenePainter` port surface | next (cheap) | S | declaration-only |
| **3b-5** | Second adapter: drive LaTeX/TikZ through the port, delete the fork | after 3b-4 | L–XL | golden re-pin (new target) |

**3b-3 — remaining non-neutral params.** Inspection finds these still SVG-flavored:

- **Markers / arrowheads.** Deferred by 3b-2: `RenderContext.arrow_attrs(o) -> str`
  and `painter.marker(...) -> str` emit SVG marker refs/defs, threaded through the
  new `extra=` param on `line`/`poly`/`path`. Needs a neutral `Marker`/arrowhead
  value object so a backend draws its own arrowheads.
- **Transforms.** `transform_group(inner, transform: str)` takes a raw SVG
  `transform` string. Neutralize to a transform value object (an affine matrix /
  `TransformFn` list the backend formats).
- **Text style.** Audit that `text_tag`/`text_block`/`text_runs` receive only
  neutral style dicts (`st`), not pre-baked SVG — likely already neutral; confirm.
- `fill` is already near-neutral (a colour/url the painter formats via `fill_attr`).

**3b-4 — port surface is partial and partly stale (confirmed):**

- **Missing declarations** — called by the builder but absent from the
  `ScenePainter` Protocol: `image_pattern`, `clip_polygon`, `clip_path_d`.
- **Stale annotation** — `RenderContext.shape_stroke(o, style) -> str` now returns
  `Stroke | None` after 3b-2; the `-> str` is wrong.
- **Document the backend-specific handle methods** (`gradient`/`clip_*`/`filter_*`/
  `marker`/`embedded_svg` return opaque ids/fragments; `clip_id`/`filter_id` are
  backend handles) as explicitly backend-specific, distinct from the neutral
  geometry primitives — so a backend author knows which to reimplement vs. format.

**3b-5 — the payoff and the real port test.** The LaTeX path
(`latex/document.py::_Transpiler`, `latex/tikz.py::FigureTikz`, ~3,480 LOC, its own
`transpile()` walk via `tooling/render_latex.py`) is today a **separate fork**, not
driven through `ScenePainter`. Re-driving it through the Renderer + a `TikzPainter`
adapter and deleting the fork is both the proof the port is genuinely neutral and
the maintenance win (one builder, two backends). Unlike 3b-2/3b-3/3b-4 this is *not*
byte-identical — TikZ is a different target, so it needs a reviewed `make golden`
re-pin for the LaTeX corpus, decided per-fixture.

3b-3 and 3b-4 are **byte-identical** for the SVG backend (no re-pin); 3b-4 is the
cheap quick win and unblocks 3b-5. Only 3b-5 introduces a new output target and the
golden re-pin that implies.

## Consequences

- After 3a, the sub-renderers depend on a small, documented, mockable contract
  rather than the Renderer's private surface — and that contract *is* the
  primitives list 3b must supply, so 3a is genuine groundwork, not ceremony.
- 3b remains the real backend-neutral payoff (collapsing the LaTeX/Chromium forks).
  Its parameter-neutralization half is being delivered byte-identically, slice by
  slice (3b-2 `stroke` done; 3b-3/3b-4 next, no re-pin); only the second adapter
  itself (3b-5) introduces a new output target and the golden re-pin that implies.

[↑ Back to root README](../README.md)
