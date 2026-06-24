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

Accepted, staged. Slice **3a** is implemented. Slice **3b** is well advanced —
**3b-1** (application layer builds zero SVG), **3b-2** (`stroke` → `Stroke`),
**3b-3** (markers, transforms, text-style audit), and **3b-4** (port completion) are
done. The painter's neutral-parameter surface is complete; only **3b-5** (a second
backend driven through the port, collapsing the LaTeX fork) remains — scoped in the
milestone table below.

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
| **3b-3** | Neutralize the remaining SVG-string-shaped painter params | ✅ **done** | M | byte-identical (transforms: 1 reviewed re-pin) |
| **3b-4** | Complete + correct the `ScenePainter` port surface | ✅ **done** | S | declaration-only |
| **3b-5** | Second adapter: drive LaTeX/TikZ through the port, delete the fork | in progress | L–XL | golden re-pin (new target) |

**3b-3 — remaining non-neutral params (done):**

- **Markers / arrowheads** ✅ (3b-3a). A neutral `Markers{color,start,end}` value
  object (`stroke_resolver`); `Renderer._arrow_markers` returns it, the SVG
  marker-`<defs>` registration + ref formatting moved into `SvgPainter._marker_attrs`,
  and `line`/`poly`/`path` take a neutral `markers=` param. `RenderContext.arrow_attrs`
  → `arrow_markers`. Byte-identical.
- **Transforms** ✅ (3b-3b). `StyleValues.svg_transform` → `transform_ops()` returning
  a neutral op list `[(fn,[args]), …]` (origin sandwich expanded to explicit
  `translate` ops); `SvgPainter.format_transform` owns the SVG syntax;
  `transform_group(inner, ops)` formats internally. One operator-approved re-pin: the
  flow site's `translate(x,y)` normalized to `translate(x y)` (18 transforms,
  SVG-equivalent) — verified the *only* change across 252 pages.
- **Text style** ✅ (audit). `text_tag`/`text_block`/`text_runs` already receive a
  neutral style dict (`st` = family/size/weight/italic/color/align/lh); the painter's
  `font_style` formats it. No SVG leaks — no change needed.
- `fill` is already near-neutral (a colour/url the painter formats via `fill_attr`).

After 3b-3 the only non-neutral painter inputs left are the **opaque backend handles**
(gradient/clip/filter/marker ids) — inherently backend-specific (3b-4) — and the
residual `extra=` (one inert `fill="none"` on UML lines).

**3b-4 — port surface, completed:**

- **Missing declarations** added — `image_pattern`, `clip_polygon`, `clip_path_d`
  (builder-called, were absent from the `ScenePainter` Protocol).
- **Stale annotation** fixed — `RenderContext.shape_stroke` now typed `Stroke | None`.
- **Backend-specific handle methods** (`gradient`/`image_pattern`/`clip_*`/`filter_*`/
  `marker`/`embedded_svg`) documented as returning opaque handles, distinct from the
  neutral geometry primitives — so a backend author knows which to reimplement vs.
  format. Confirmed structurally: every `ScenePainter` method exists on `SvgPainter`.

**3b-5 — the payoff and the real port test.** The LaTeX path
(`latex/document.py::_Transpiler`, `latex/tikz.py::FigureTikz`, ~3,480 LOC, its own
`transpile()` walk via `tooling/render_latex.py`) is today a **separate fork**, not
driven through `ScenePainter`.

*Grounded reframing (from mapping the fork).* `FigureTikz` does not merely
reimplement the 8 geometry primitives — it independently re-derives **every**
figure object (the 14 `uml.*` types, charts, dimensions, tables, components, …).
But after 3b-1…3b-4 the Renderer + sub-renderers build *all* of those through
`ScenePainter` primitive calls. So the fix is **not** a method-by-method port of
`FigureTikz`: a `TikzPainter` implementing the port makes the *same Renderer* emit
TikZ for every object type, and `FigureTikz`'s ~2,700 lines of figure logic become
**redundant** — the fork is replaced, not translated. The `_Transpiler` document
scaffold (preamble, flow emitters, page setup) stays LaTeX-specific and simply
calls the Renderer-via-`TikzPainter` where it used to call `FigureTikz.render`.

Staged (not byte-identical — TikZ is a new target; assertion-based LaTeX tests get
updated and a per-fixture review replaces the hand-verified output):

- **3b-5a** ✅ `TikzPainter` adapter — geometry primitives (`rect`/`ellipse`/
  `circle`/`line`/`poly`), grouping, page wrapper, and the `Stroke`/`Markers`/fill→
  TikZ formatters. Additive; proves the neutral port drives a second backend.
- **3b-5b** ✅ `transform_group` (the neutral transform ops → TikZ scope opts, skew→
  tangent — 3b-3b's value objects working in TikZ), `image`, and clip scoping
  (`clip_rect`/`clip_ellipse`/`clip_polygon`/`clip_wrap` via an id→geometry registry,
  showing the port's id-handle model adapts to TikZ's inline `\clip`). Additive.
- **3b-5c** the integration — and the genuinely hard, non-additive part:
  - **SVG path data** (`path`, `clip_path_d`): ✅ **done** — the ~308-line `d`→TikZ
    converter is relocated verbatim out of `FigureTikz` into the neutral, pure
    `painters/tikz_path.py` (a third module to avoid the painters↔latex import
    cycle); `FigureTikz` delegates (byte-identical), and `TikzPainter.path`/
    `clip_path_d` consume it. Gradient-on-path falls back to a solid first stop.
  - **Parameter neutralization is now complete across the port.** The
    `text_block`/`text_runs` `style`-string leak (which 3b-3's audit missed) is
    closed: they take the neutral style dict + fitted size, and SvgPainter formats
    the font internally — byte-identical (golden unchanged). So **every input the
    Renderer hands the painter is now a neutral value** (Stroke / Markers /
    GradientPaint / transform ops / style dict / colour-url fill); the builder
    passes a non-SVG backend zero pre-formatted SVG. What remains is purely the TikZ
    *implementation* of `text_block`/`text_runs` and the wire-up — both gated on a
    LaTeX engine to validate (none in the current environment).
  - **Text** — the font-coupling decision is **resolved**: `text_tag` ✅. The painter
    only gets a resolved style dict, and faithful TikZ text needs the `_Transpiler`'s
    font-macro registry — so the registry is **threaded in** as an optional
    `font_macro` callable on `TikzPainter.__init__` (the Renderer supplies it at
    wiring time; absent it, the font degrades to the default family). `text_tag`
    emits a `\node` (anchor/align/`_text_y`/font-chain/colour) on the proven latex/
    convention. Remaining: `text_block`/`text_runs` (multi-line/styled spans) and the
    CSS text-feature tail (variants/letter-spacing/bidi/decorations).
  - **Handle methods done.** `filter_effect`/`filter_wrap`/`image_pattern`/
    `embedded_svg`/`marker` now have honest TikZ fallbacks (filters pass through —
    TikZ effects are per-shape; image-pattern fill → unfilled; embedded SVG →
    accessible-title text node; marker inert since arrowheads flow via the `Markers`
    value object). **TikzPainter now implements the entire `ScenePainter` port except
    `text_block`/`text_runs`** (a structural test pins this) — the adapter is
    wire-up-ready.
  - **Original def+ref framing.** These *looked* like they encode SVG's `<defs>`+
    `url(#id)` model. On inspection that framing was overstated — the port already
    defines `gradient()` as returning an **opaque backend handle**, and `paint()`
    delegates to it, so **no contract change is needed**: each backend returns its
    own handle. ✅ **Gradient is done** — `GradientPaint` (paint_resolver) is TikZ's
    handle; `SvgPainter.gradient` still returns `url(#…)` (SVG byte-identical),
    `TikzPainter.gradient` returns the value object and the fill-bearing primitives
    render it inline as `\shade` (shape-coupled, since the primitive has the
    geometry). `marker` is already internal via the `Markers` value object. Genuinely
    SVG-specific remainders: `filter_effect`/`filter_wrap` (TikZ shadows differ),
    `embedded_svg` (foreign-SVG embed — a TikZ backend falls back), `image_pattern`.
  - **Wire + delete**: drive the Renderer with `TikzPainter`, route `_Transpiler`'s
    figure path through it, delete `FigureTikz` (~2,700 LOC), rewrite the
    assertion-based LaTeX tests, and validate by `lualatex` compile + per-fixture
    review (there is no `.tex` golden lock to lean on).

With 3b-3 and 3b-4 landed, the painter's *neutral* surface is complete: every
geometry primitive takes value objects (`Stroke`, `Markers`, transform ops, colour/
url fills) and the port declares the full surface. **3b-5 is all that remains** — the
second adapter that proves the seam by construction and collapses the LaTeX fork.

## Consequences

- After 3a, the sub-renderers depend on a small, documented, mockable contract
  rather than the Renderer's private surface — and that contract *is* the
  primitives list 3b must supply, so 3a is genuine groundwork, not ceremony.
- 3b remains the real backend-neutral payoff (collapsing the LaTeX/Chromium forks).
  Its parameter-neutralization half is being delivered byte-identically, slice by
  slice (3b-2 `stroke` done; 3b-3/3b-4 next, no re-pin); only the second adapter
  itself (3b-5) introduces a new output target and the golden re-pin that implies.

[↑ Back to root README](../README.md)
