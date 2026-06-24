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
step **3b-1** (application layer builds zero SVG) is done; the substantial
remainder (parameter neutralization + a second backend) is scoped below.

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
The substantial remaining 3b work is therefore:

1. **Neutralize the painter parameters** — pass neutral value objects (a
   `Stroke{color,width,dash,...}`, a `Fill`/paint, radii) instead of SVG attribute
   strings; each backend formats them. The SVG backend can format them to the
   *same* bytes, so this **can stay byte-identical** for SVG (no re-pin) if done
   carefully — contrary to this ADR's first claim.
2. **Complete the `ScenePainter` port** to declare all ~30 methods a backend must
   implement (it is currently partial).
3. **Add a second adapter** (the existing LaTeX `_Transpiler`/`FigureTikz` is the
   natural candidate to port onto the port, then delete the fork).

Steps 1–2 are **L** and largely byte-identical; step 3 is **L–XL**. Only if a
backend cannot reproduce a given byte sequence does a reviewed `make golden`
re-pin become necessary — a per-case decision, not a blanket one.

## Consequences

- After 3a, the sub-renderers depend on a small, documented, mockable contract
  rather than the Renderer's private surface — and that contract *is* the
  primitives list 3b must supply, so 3a is genuine groundwork, not ceremony.
- 3b remains the real backend-neutral payoff (collapsing the LaTeX/Chromium forks)
  but is gated by the byte-identity constraint and is scheduled as its own XL
  effort with an explicit golden re-pin.

[↑ Back to root README](../README.md)
