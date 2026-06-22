---
title: FrameGraph v2 — Roadmap (draft)
version: 2.2.0
status: DRAFT / design-target — not commitments
date: 2026-06-22
verified_at_commit: bc90f15   # line citations below hold at this commit; re-verify if HEAD has moved
method: >
  Gaps asserted against the EBNF + checked-in fixtures, then verified against the
  authoritative Pydantic models (models/framegraph.py, HEAD 2.2.0 @ bc90f15), and benchmarked
  against real specs of analogous systems (Typst, Vega-Lite, D2/dagre/ELK, Mermaid,
  PlantUML, PDF/UA, PDF/X). Item 7 and Appendix A are additionally derived from
  framegraph-v2.ebnf (PathObject, PolylineObject, ConnectorObject.Route, Point) and
  framegraph-v2-style.ebnf (TransformFn, perspective, transform_origin).
disclaimer: >
  This is a forward-looking gap analysis, not a delivery plan. "Missing" means
  "not expressible in the grammar/fixtures as inspected"; the models are the
  source of truth and could narrow a gap. Priorities reflect how defensible and
  consequential each gap is, not committed scheduling. Appendix A is a design
  proposal, not a specification: the `@framegraph/*` packages and symbols in it
  are invented to describe an interface and do not exist, and every formula's sign
  convention must be verified against your renderer before use (canvas space is
  Y-DOWN, origin top-left). NOTHING IN THE APPENDIX SHOULD BE TAKEN FOR GRANTED.
appendix_references:
  - "Asymptote (Hammerlindl, Bowman, Prince): 2D & 3D vector graphics; Hobby-spline → 3D"
  - "Hobby (1986) / Knuth, The METAFONTbook ch.14: control-point selection"
  - "D3.js: curve interpolators and scales (linear/log/pow/time) — design model only"
  - "three.js: 3D scene graph — the comparator for *true* 3D (out of scope here)"
---

# FrameGraph v2 — Roadmap (draft)

!!! note "What this is"
    A prioritized map of what FrameGraph cannot yet express, measured against the
    EBNF and the checked-in fixtures and benchmarked against the published specs
    of comparable systems. Each item states the gap, the evidence, the comparator
    that closes it, and a proposed fix. Items 1, 2, and 4 are defensible gaps;
    items 3 and 5 are **scope decisions worth making explicit** rather than gaps;
    item 6 is conditional on a live-presentation goal; item 7 is an additive
    author-time SDK whose full design lives in Appendix A.
    (Items keep their original IDs; sections run in priority order, so the IDs
    appear out of sequence.)

!!! info "Verification status"
    Every gap below was checked against `models/framegraph.py` and the grammar at
    HEAD 2.2.0, not asserted from memory. Where the source contradicted the draft
    it was corrected (see item 1's container-layout note, the `uml.*` count, the
    refreshed line citations for `widows`/`orphans` and `footnote_area`, and item 2,
    reframed after `alt`/`actual_text`/`reading_order` landed in the model at bc90f15).

## Calibration — what is *not* missing

Before the gaps, a correction, because inspecting the grammar overturns the
obvious guess. One would expect a YAML document format to be thin on typography
and internationalization. It is not. FrameGraph already carries:

- **Typography:** `widows`, `orphans`, `hyphens` with `hyphenate_limit_chars`
  (total / before / after), `font_kerning`, ligature and variable-font axis controls.
- **Internationalization:** full bidi (`direction`, `unicode_bidi` across the whole
  CSS set) and vertical writing modes (`vertical-rl` / `vertical-lr`) for CJK.
- **Document furniture:** `footnote_area`, footnote / endnote placement.
- **Color:** modern wide-gamut color (`oklch` / `lab` / `lch`).

So on typographic and i18n **vocabulary** FrameGraph is competitive with mature
systems, and listing those as gaps would be wrong. The real caveat is the layout
**engine** that honors them — see the cross-cutting note below — which is a
different thing from the controls themselves.

> Verified in `models/framegraph.py`: `widows`/`orphans` (L717–718),
> `hyphenate_limit_chars` (L253), `font_kerning` (L235), `unicode_bidi` (L261),
> `writing_mode` (L259), `footnote_area` (L913); `oklch`/`lab`/`lch` in
> `grammar/framegraph-v2-style.ebnf` (L279). `decorative`/`role`/`lang` exist —
> and, as of commit bc90f15, so do `alt`/`actual_text` (Image L610–611, ImageFlow
> L787–788, FigureFlow L799–800) and per-page `reading_order` (Page L954). The
> accessibility *vocabulary* is therefore present; only the tagged-export that
> consumes it remains (item 2, reframed).

## Priority at a glance

| # | Item | Priority | Kind |
|---|------|----------|------|
| 1 | Automatic *graph* layout for diagrams | **High** | Missing capability |
| 2 | Accessibility / tagged-export model | **High** | Vocabulary done → tagged export remains |
| 4 | Conformance suite + reference-renderer semantics | **High** | Missing capability |
| 3 | Data layer for charts | **Medium** | Scope decision |
| 5 | Print color management (ICC / CMYK) | **Medium** | Scope decision |
| 7 | Geometry / transformed spaces / 3D authoring SDK | **Medium** | Additive capability |
| 6 | Interaction / animation for presented decks | **Low** | Conditional on goal |

> Net ordering (most defensible first): diagram auto-layout → accessible export →
> conformance corpus. The data layer and print color are scope choices worth
> stating outright rather than leaving implied. The geometry / 3D SDK (item 7) is
> additive and renderer-neutral — high leverage for diagram, engineering, and math
> figures, but lower-risk and lower-priority than the foundational gaps because it
> emits only primitives the grammar already has.

---

## Phase 1 — defensible gaps

### 1. Automatic *graph* layout for diagrams — the clearest gap

**Gap.** FrameGraph ships 17 `uml.*` object types plus connectors with `route`
kinds (straight / orthogonal / curved), but node *placement* is manual: you
author every box's coordinates, exactly as the fixture does. It models the
*result* of routing but not the *computation* of layout.

!!! note "What already exists — and why it does not close this"
    FrameGraph does have **container** layout: `Group.layout` with
    `kind: row | column | grid | free` plus `gap` / `row_gap` / `column_gap` /
    `padding` / `align`, realized by `LayoutEngine.arrange`
    ([framegraph/rendering/domain/services/layout_engine.py](../framegraph/rendering/domain/services/layout_engine.py)).
    That is a box-model packer — it repositions a group's children into rows /
    columns / a grid and does **not** resize them. It is not a **graph** engine:
    it cannot place nodes from declared edges, route around obstacles, or minimize
    crossings. So the gap is specifically *graph / diagram* auto-layout, not
    "no layout at all."

**Comparators.** Every analogous diagram-as-code tool computes placement from
declared nodes and edges — D2 bundles dagre and ELK (with TALA as a premium
engine), Mermaid uses dagre, PlantUML uses Graphviz's DOT. Dagre produces
layered / hierarchical layouts based on Graphviz's DOT algorithm; ELK suits
node-link diagrams with ports and direction. The category's whole appeal is that
the same input always produces the same output — no manual positioning, and
therefore no style drift across a team. FrameGraph's diagram side gives that up.

**Fix.** Define an optional auto-layout pass keyed off the semantic graph (it
already has `bind`, ontology, and edge directionality) that emits computed boxes
before render — or formally adopt an external engine (ELK is embeddable) as the
layout tier for `mode: page` diagram groups, leaving absolute positioning as the
override.

### 2. Accessibility / tagged-export model

**Gap (reframed — the authoring surface now exists).** As of commit bc90f15 the
*vocabulary* is in the model: `decorative`, `role`, `lang`, **`alt`/`actual_text`
on image and figure objects** (Image L610–611, ImageFlow L787–788, FigureFlow
L799–800), and a **per-page `reading_order`** over object ids (Page L954). What is
still missing is the **consumer**: no exporter maps these into a tagged PDF
**logical structure tree** — roles, alt text, and a reading order independent of
visual position. So the fields can be authored, but an accessible artifact cannot
yet be produced from a deck like the fixture.

**Comparators.** PDF/UA makes both non-negotiable: every meaningful element must
sit in a structure tree with the correct semantic role, every non-text element
must carry alternative text, and the tree's reading order must match the visual
reading order. This is increasingly a legal requirement, not a nicety — the ADA,
the European Accessibility Act, and Section 508 all reference WCAG as the accepted
standard.

**Fix (export-side, not a format change).** Implement the tagged-export pass: map
`reading_order` + `role` to a PDF structure tree, `alt`/`actual_text` to element
alternative text, and `decorative` to PDF artifacts. The authoring fields already
exist (the model/grammar work landed at bc90f15); what remains is renderer/exporter
work plus a conformance check that every non-`decorative` object is reachable in
some page's `reading_order`.

### 4. Conformance suite + reference-renderer semantics

**Gap.** The format's stance — treat each construct as a proposal to verify
against the renderer — is honest but leaves "valid" underdetermined. FrameGraph
has the schema, the models, the `b1/` authoritative fixtures as an oracle (the HEAD
assertion suite validates them), and the `--check-overflow` text-fit gate — but no
*golden-render* corpus with an explicit tolerance that pins correct output
geometrically. (`codebase-standards.md` §8 already tags that golden-snapshot
harness `[Target]`.)

**Comparators.** The mature comparators close this loop. Vega-Lite publishes a
versioned JSON Schema and an example gallery, and its CI recompiles every example
to reference Vega specs and SVGs that serve as regression tests, with an explicit
backward-compatibility commitment.

**Fix.** Make the existing fixtures (the deck is a good start) golden tests — pin
each to a reference render and diff on every change — and version the schema at a
resolvable URL the way Vega-Lite does, so documents can self-declare conformance.

---

## Phase 2 — scope decisions to make explicit

### 3. Data layer for charts

**Gap.** Charts take literal `ChartData`; the `transform` keyword is CSS visual
transforms (`TransformFn`), not data transforms. FrameGraph requires every chart
to be pre-aggregated upstream and every axis specified. Note that charts already
sit **outside the core conformance profile** ([models/framegraph.py:21](../models/framegraph.py#L21)),
so treating the data layer as out-of-scope would be consistent with the existing
profile boundary, not a new exclusion.

**Comparator.** Vega-Lite exists precisely to close this: it maps data attributes
to visual channels and includes common data transforms (binning, aggregation,
sorting, filtering), auto-produces axes / legends / scales from a minimal spec,
and composes views through a layer / concat / facet / repeat algebra that aligns
scales and axes. The cost of FrameGraph's choice is real: no single source of
truth from data to multiple views.

**Decision / fix.** This may be a deliberate scope choice — a document format need
not be a visualization grammar. If it stays out of scope, **say so explicitly**
and lean on embedding compiled Vega-Lite output as a figure object. If not, add a
minimal data + encoding block to the chart objects rather than reinventing the
algebra.

### 5. Print color management

**Gap.** Modern screen color is well covered (see calibration), but there is no
ICC output intent or CMYK separation. For the book / print target that is a real
omission.

**Comparator.** PDF/X-style print workflows require unambiguous color through a
specified ICC output intent or full color management, with fonts embedded.

**Fix.** Add an optional output-intent / ICC reference at the target level so print
targets can declare a profile; screen targets ignore it.

### 7. Geometry, transformed spaces, and 3D authoring — additive SDK, not a format change

**Gap.** The grammar can *represent* arbitrary 2D geometry — `PathObject.d` (SVG
path data), `PolylineObject.points`, and `TransformFn.matrix` (full 2D affine) —
but there is no authoring layer that *computes* it: no vector / matrix algebra, no
curve interpolation (Catmull-Rom / Hobby), no parametric / function / polar
sampling, and no coordinate **frames** that map data or engineering units onto the
page. 3D is worse than missing: the style module marks 3D transforms and
`perspective` as "declared, may not render," so emitting them is a trap — a
structurally valid document that no target draws.

**Comparator.** A 2D&3D vector language (Asymptote) computes geometry and 3D and
*projects to 2D vector output* rather than shipping a 3D scene to the page; D3's
scales (`linear` / `log` / `pow`) model the data→page frame mapping. The lesson is
that the geometry kernel belongs in the authoring tool, not the page renderer.

**Fix.** Add author-time SDK packages (`@framegraph/geometry`,
`@framegraph/author/draw`) that own the math and **emit only primitives the
grammar already has** — `path`, `polyline`, `group`, `matrix` — resolving curves
and 3D→2D projection at expansion time and pinning the result with the existing
hash contract. The only optional grammar change is G-1: a structured
`segments: PathSeg[]` alongside `d`, so geometry becomes schema-checkable — and if
adopted it must land in **both** the models and the EBNF, which the `grammar-check`
CI gate now enforces for the core profile (so it cannot silently drift).
Because it is additive and renderer-neutral, its priority is **Medium** despite
being a missing capability. Full design, math, and grammar-fix table in
**Appendix A**.

---

## Phase 3 — conditional

### 6. Interaction / animation for presented decks

**Gap.** The style module explicitly parks interaction / animation outside its
scope, and there are no transition / build primitives. For static or PDF decks
this is fine; for *presented* decks it is a gap versus reveal.js / Slidev /
PowerPoint.

**Priority.** Lowest — pursue only if presenting live is a goal.

---

## Cross-cutting note — vocabulary vs. engine

Tying back to the calibration: FrameGraph has the typographic *controls* (widows,
orphans, keep-together, breaks) but not a specified *engine* that realizes them.
Typst, by contrast, **is** the engine — it runs measurement, then placement, then
page-breaking, with frames as the positioned units, and resolves cross-document
dependencies like counters and citations through introspection over multiple
layout iterations, which its pure language makes safe to re-run. FrameGraph defers
that algorithm to "the renderer" and only asserts a determinism precondition. So
the gap is not the vocabulary; it is that the contract for *how*
widows / orphans / keep-together are honored lives outside the format — which loops
straight back to item 4 (no reference semantics).

## Net assessment

FrameGraph's distinctive bet — one substrate spanning decks and books with a
semantic graph attached — is real and uncommon; most tools pick one lane. It is
strong on typographic, i18n, and color **vocabulary**. The defensible missing
pieces, in order, are **diagram auto-layout**, **accessible / tagged export**, and
a **conformance corpus**. The **data layer** and **print color management** are
scope decisions worth making explicit rather than leaving implied. A **geometry /
transformed-spaces / 3D authoring SDK** (item 7, Appendix A) is high-leverage but
additive — it ships entirely in author-time math that emits today's 2D primitives,
so it carries Medium priority and near-zero format risk. Interaction / animation is
lowest priority unless live presentation becomes a goal.

---

# Appendix A — Geometry, Transformed Spaces, and 3D (design proposal, non-normative)

> **Status:** proposal / non-normative. This appendix is the full design behind
> roadmap item 7. NOTHING HERE SHOULD BE TAKEN FOR GRANTED. The `@framegraph/*`
> packages and symbols are invented to describe an interface and do not exist.
> Statements not backed by a real definition (the EBNF files) or a citable
> reference may be invalid or a hallucination. The MATH is stated concretely so it
> can be checked; verify each formula and sign convention against your own
> renderer's coordinate system before relying on it. Coordinate convention assumed
> throughout: page / canvas space is Y-DOWN, origin top-left (so a mathematically
> positive rotation appears clockwise on the page) — flagged again where it bites.
> Derived from `framegraph-v2.ebnf` (PathObject, PolylineObject,
> ConnectorObject.Route, Point) and `framegraph-v2-style.ebnf` (TransformFn,
> perspective, transform_origin); references in the front-matter `appendix_references`.
>
> **Language note:** the interfaces below are shown in TypeScript for concision, but
> this repo's authoring/tooling stack is Python (`tooling/*.py`) + YAML and the only
> JavaScript is the viewer (a consumer). The design is pure math and language-neutral;
> a Python implementation reusing the existing expansion/`codemod` tooling is the more
> natural fit here. The TS is illustrative, not a committed language choice.

## A.0. The constraint that shapes the entire design

The grammar fixes what is representable, and that splits the problem in two:

- **2D is fully expressible.** `PathObject` carries `d: string` (an SVG path-data string: `M/L/C/Q/A/Z`), `PolylineObject` carries `points: [Point]`, and `TransformFn` includes `matrix` (full 2D affine). So arbitrary 2D geometry and any 2D affine map already fit. For 2D the SDK adds **ergonomics and correct math only** — no format change.
- **3D is not.** The style module marks 3D transforms and `perspective` as "declared, may not render." Emitting them is a trap: a structurally valid document that no target draws.

Therefore the geometry layer **solves** geometry and projection itself and **emits 2D**, at expansion time, pinned for reproducibility. This is the inverse of the layout rule ("describe, don't solve"): the page renderer is not a geometry kernel, so the SDK must do the math. This is exactly how a 2D&3D vector language operates — it computes 3D and refines Bézier control points down to a projected 2D result rather than shipping a 3D scene to the page.

One working-space rule follows immediately: `Point` is unitless 2D numbers in canvas space, and `Length` may be relative (`%`, `fr`). **Computed geometry operates in absolute canvas units only**; relative lengths are resolved to numbers before any geometry math runs. Mixing `fr` into a curve sample is undefined.

---

## A.1. The algebra: vectors and matrices (`@framegraph/geometry`)

A pure-math package with no document dependency. Everything else lowers through it.

```ts
export type Vec2 = readonly [number, number];
export type Vec3 = readonly [number, number, number];

// 2D affine as a 3×3 homogeneous matrix. Stored row-major:
//   [ a  c  e ]      x' = a·x + c·y + e
//   [ b  d  f ]      y' = b·x + d·y + f
//   [ 0  0  1 ]
// This maps 1:1 to TransformFn matrix(a,b,c,d,e,f) (CSS/SVG order).
export interface Mat3 {
  readonly a: number; readonly b: number; readonly c: number;
  readonly d: number; readonly e: number; readonly f: number;
  apply(p: Vec2): Vec2;
  mul(other: Mat3): Mat3;          // composition (this ∘ other)
  inverse(): Mat3;
  toTransformFn(): TransformFn;    // { fn:"matrix", args:[a,b,c,d,e,f] }
}

export const Mat3: {
  identity: Mat3;
  translate(tx: number, ty: number): Mat3;        // e=tx, f=ty
  scale(sx: number, sy?: number): Mat3;           // a=sx, d=sy
  // ROTATION by θ (radians). a=cosθ, b=sinθ, c=−sinθ, d=cosθ.
  // NOTE Y-down: positive θ appears CLOCKWISE on the page.
  rotate(theta: number, origin?: Vec2): Mat3;
  skewX(theta: number): Mat3;                     // c = tan(θ)
  skewY(theta: number): Mat3;                     // b = tan(θ)
  reflect(axis: "x" | "y" | { throughLine: [Vec2, Vec2] }): Mat3;
  from(fns: TransformFn[]): Mat3;                  // fold a TransformFn list into one matrix
};

// 3D affine/projective as a 4×4 homogeneous matrix (column vector convention:
// p' = M · [x y z 1]ᵀ, then perspective divide screen = (x'/w', y'/w')).
export interface Mat4 {
  apply(p: Vec3): Vec3;            // affine apply (w assumed 1)
  project(p: Vec3): Vec2;          // apply + perspective divide → screen 2D
  mul(other: Mat4): Mat4;
  inverse(): Mat4;
}
```

Two correctness notes worth stating because they are the usual source of wrong output: composition is matrix multiply (so `A.mul(B)` applies `B` first, then `A`), and on a Y-down page a positive rotation reads clockwise. Both are encoded above so callers don't re-derive them.

---

## A.2. The 2D path algebra (lowers to `PathObject.d`)

An immutable builder. Each method returns a new path; the terminal `.toObject()` compiles to `{ type:"path", d: "…" }`.

```ts
export interface Path {
  moveTo(p: Vec2): Path;
  lineTo(p: Vec2): Path;
  cubicTo(c1: Vec2, c2: Vec2, end: Vec2): Path;   // SVG "C"
  quadTo(c: Vec2, end: Vec2): Path;               // SVG "Q"
  arcTo(end: Vec2, opts: { rx: number; ry: number; xRot?: number;
        largeArc?: boolean; sweep?: boolean }): Path; // SVG "A"
  close(): Path;
  // higher-level ergonomics ↓
  through(points: Vec2[], curve?: CurveKind): Path;  // smooth interpolation
  transform(m: Mat3): Path;                          // bakes the matrix into points
  toObject(): PathObject;                            // emits { type:"path", d }
}
```

**The Bézier math, stated concretely** (so it can be checked):

A cubic segment with endpoints `P0, P3` and controls `P1, P2`:

$$B(t) = (1-t)^3 P_0 + 3(1-t)^2 t\,P_1 + 3(1-t)t^2 P_2 + t^3 P_3,\quad t\in[0,1]$$

Quadratic: $B(t) = (1-t)^2 P_0 + 2(1-t)t\,P_1 + t^2 P_2$.

`through(points, curve)` offers two interpolation modes, each with an exact rule:

- **Catmull-Rom → Bézier** (uniform, the cheap default). For the segment from `P_i` to `P_{i+1}` with neighbours `P_{i-1}, P_{i+2}`, emit a cubic with
  `C1 = P_i + (P_{i+1} − P_{i-1})/6` and `C2 = P_{i+1} − (P_{i+2} − P_i)/6`.
  This passes through every input point with C¹ continuity.
- **Hobby spline** (the prettier, tension-controllable option). Choose control points by Hobby's algorithm with a `tension` parameter, as popularized by MetaPost/METAFONT. Asymptote uses exactly this: its `..` operator chooses control points by the algorithm in Knuth's METAFONTbook ch.14, and the user can still customize direction, tension, and curl, where higher tension straightens the curve toward a line. A `tension` of 1 is the neutral default.

**Arcs as Béziers** (true circles aren't representable by a single cubic). A quarter circle from `(r,0)` to `(0,r)` uses control points offset by `κr` where the magic constant is

$$\kappa = \tfrac{4}{3}\left(\sqrt{2}-1\right) \approx 0.5522847498$$

For higher accuracy, subdivide into more segments — the same approach a vector language takes: Asymptote approximates a circle as a Bézier curve and offers a higher-accuracy `Circle`/`Arc` with an explicit segment count. `arcTo` lowers to SVG `A` (the renderer rasterizes it), but for filled/offset geometry the SDK can flatten to cubics using `κ` so downstream math (offsets, booleans) operates on Béziers.

The builder works in absolute canvas numbers; `.transform(m)` bakes a `Mat3` into the points so the emitted `d` is already in page space (no reliance on a renderer transform).

---

## A.3. Parametric curves and fitting (math / physics)

```ts
export interface SampleOpts { domain: [number, number]; tolerance?: number; emit?: "polyline" | "path"; }
export function parametric(p: (t: number) => Vec2, opts: SampleOpts): VisualObject;
export function functionPlot(f: (x: number) => number, opts: SampleOpts & { frame: Frame }): VisualObject;
export function polarPlot(r: (theta: number) => number, opts: SampleOpts & { frame: Frame }): VisualObject;
export function vectorField(F: (p: Vec2) => Vec2, grid: GridSpec, frame: Frame): VisualObject; // quiver
```

`parametric` samples adaptively rather than at fixed steps. The subdivision test is a concrete **flatness criterion**: a cubic (or the chord of a sampled interval) is "flat enough" when both control offsets fall within tolerance ε of the chord `P0→P3`, i.e. the perpendicular distance of `P1` and `P2` from line `P0P3` is `< ε`. While that fails, split at `t = ½` (de Casteljau, numerically stable) and recurse. This concentrates samples where curvature is high — correct curves at low point counts. `emit: "polyline"` lowers to `PolylineObject`; `emit: "path"` fits cubics through the samples via the §A.2 interpolators.

`functionPlot`/`polarPlot`/`vectorField` are thin wrappers: they sample in *data* coordinates and pass the points through a `Frame` (§A.4) to reach page space. Arrowheads for fields lower to small filled `path`s.

---

## A.4. Transformed spaces — coordinate frames (the "transformed spaces" ask)

A `Frame` is a map from a logical/data coordinate system to page coordinates. It is the abstraction that makes engineering drawings (real units), math plots (data domains), and nested local spaces ergonomic.

```ts
export type Scale = "linear" | { kind: "log"; base?: number } | { kind: "pow"; exp: number };

export interface Frame {
  // affine part (logical → page) + optional per-axis nonlinear scale
  readonly affine: Mat3;
  readonly xScale: Scale;
  readonly yScale: Scale;
  to(p: Vec2): Vec2;               // logical → page
  from(p: Vec2): Vec2;             // page → logical (inverse; only when invertible)
  compose(child: Frame): Frame;    // change of basis = matrix product (+ scale fold)
}

export const Frame: {
  // map a data rectangle [x0,x1]×[y0,y1] onto a page Box, honoring Y-down.
  fit(domain: { x: [number, number]; y: [number, number] }, into: Box,
      scales?: { x?: Scale; y?: Scale }): Frame;
  identity: Frame;
};
```

Two lowering strategies, and the choice is not cosmetic:

- **Pre-apply (preferred for data/nonlinear frames).** The SDK pushes every geometry point through `frame.to(...)` and emits already-transformed 2D. This is exact, renderer-independent, and the *only* correct option when the scale is nonlinear (log/pow/polar) — a `matrix` cannot express those.
- **Group transform (only for pure-affine view frames).** Emit a `group` with `transform: [matrix(...)]` from `frame.affine.toTransformFn()`. Compact, but limited to affine and dependent on the renderer's transform fidelity.

Data scales follow the model proven by D3 (`scaleLinear/scaleLog/scalePow`): a domain→range map applied per axis. Because they are nonlinear, they must be pre-applied. Composition of frames (a plot inside a panel inside a page) is matrix multiplication of the affine parts with the scales folded in — a single resolved `Frame` at emit time, no nested renderer transforms to trust.

---

## A.5. 3D authoring → 2D projection (the honest 3D story)

The document never carries true 3D. A `Scene3D` is authored in 3D, and a `Camera` projects it to 2D primitives the renderer already supports. This mirrors how a 2D&3D vector language ships output: Asymptote generalizes MetaPost path construction to three dimensions but its result is vector graphics (PostScript/PDF/SVG), with 3D PRC as a separate export.

```ts
export type CameraKind =
  | { kind: "orthographic" }
  | { kind: "perspective"; fovY: number; near?: number; far?: number }
  | { kind: "isometric" }                       // engineering preset
  | { kind: "dimetric"; angle: number };

export interface Scene3D {
  mesh(vertices: Vec3[], faces: number[][], style?: FaceStyle): Scene3D;
  parametricSurface(s: (u: number, v: number) => Vec3, grid: GridSpec): Scene3D; // → quad mesh
  extrude(profile: Path, depth: number, dir?: Vec3): Scene3D;
  revolve(profile: Path, axis: [Vec3, Vec3], turns?: number): Scene3D;            // lathe
  transform(m: Mat4): Scene3D;
  render(camera: Camera, into: Box, opts?: ProjectOpts): VisualObject; // → group of 2D polygons/paths
}
```

**Projection math, stated concretely.** With view matrix `V` (world→camera), a world point `Pw` becomes `Pc = V·Pw`.

- **Orthographic:** drop the depth axis after the view transform — screen `= (Xc, Yc)`, scaled to the target `Box`.
- **Perspective (pinhole):** with the camera looking down `−Z`, screen `= (f·Xc / −Zc, f·Yc / −Zc)`, where focal length `f = (H/2) / tan(fovY/2)` for target height `H`. Equivalently: a 4×4 projection matrix `P` gives `[x',y',z',w'] = P·[X,Y,Z,1]`, then perspective divide `(x'/w', y'/w')`. (Sign of `Z` depends on handedness — verify against your renderer; `Mat4.project` encodes one convention.)
- **Isometric:** rotate 45° about the vertical axis, then `arctan(1/√2) ≈ 35.264°` about the horizontal axis, then orthographic. This produces the equal-foreshortening axes engineers expect. `dimetric` exposes the tilt angle for the two-ratio variant.

**Depth, shading, culling — all computed, all emitted as 2D:**

- **Hidden-surface ordering** uses the painter's algorithm: sort faces by camera-space depth (e.g. centroid `Zc`), then map draw order onto the 2D objects' `z` field. State the limitation plainly: painter's order is wrong for interpenetrating or cyclically-overlapping faces — a 2D page renderer has no z-buffer to fix this. For correctness on hard cases, the SDK can subdivide faces along intersections, but the honest default is "convex-ish scenes only."
- **Backface culling** drops faces whose normal points away from the camera (`n · viewDir > 0`).
- **Flat shading** computes a per-face fill from `max(0, n · lightDir)` and emits a solid `Color` — no gradient meshes needed.
- **3D curves/splines** are interpolated in 3D and projected; the recursive-refinement approach keeps them smooth under projection, the same technique a vector language uses to approximate a perspective-invariant spline.

Output of `render(...)` is a `group` of closed `polyline`/`path` objects with computed fills and `z` order — nothing the renderer hasn't always supported.

---

## A.6. Engineering helpers (reuse what the grammar already has)

- **Dimensions** lower to the existing `DimensionObject` — no new primitive.
- **Section hatching** uses the existing pattern `Fill` (the grammar has `kind:"pattern"` with a hatch `angle`).
- **Orthographic multiview** (front/top/side) is three `Scene3D.render` calls with orthographic cameras aimed down each axis, placed in a panel grid.
- **Math labels** use the existing `MathInline`/`MathFlow` (`tex`) — geometry and equations share one document, the way a math-figure language pairs drawings with TeX labels.

---

## A.7. Where this meets the grammar (gaps + fixes)

| ID | Gap (grounded) | What the SDK does | Grammar fix |
|----|----------------|-------------------|-------------|
| G-1 | `PathObject.d` is an opaque string the schema cannot validate | builds correct `d`; ships a `d`-parser in the validator | add optional structured `segments: PathSeg[]` (typed M/L/C/Q/A/Z) alongside `d`, so geometry is schema-checkable; `d` becomes the compiled view — enforced by `grammar-check` (must land in models + EBNF) |
| G-2 | 3D transforms / `perspective` are "declared, may not render" — a trap | refuses to emit them; projects to 2D instead (§A.5) | either deprecate/mark them explicitly non-conformant, or specify a real 3D renderer; until then, projection-only is the supported path |
| G-3 | `Point` is unitless 2D; `Length` may be relative (`%`,`fr`) — geometry over relative units is undefined | resolves all lengths to absolute canvas numbers before any geometry math | document the rule: computed geometry is absolute-units-only |
| G-4 | curves/projection are not reproducible if recomputed per render | computes them once at **expansion** (Tier 3) and pins the result with the hash set | none — reuse the existing expansion/hashing contract |

---

## A.8. How it slots into the existing SDK

```
@framegraph/geometry      # NEW. Pure math: Vec2/Vec3, Mat3/Mat4, Path, parametric, projection.
                          # No document dependency; independently testable against the formulas above.
@framegraph/author/draw   # NEW. Builders that consume geometry and emit VisualObjects
                          # (path / polyline / group). Frames, Scene3D.render live here.
@framegraph/expand        # 3D→2D projection and curve flattening are realized HERE, then pinned.
@framegraph/model         # unchanged — receives only 2D primitives it already defines.
```

The render boundary is unchanged: after expansion the renderer sees `path`, `polyline`, `group`, and `matrix` — primitives in the grammar today. All the new power lives in math the SDK owns, not in format the renderer must learn. The single decision that makes this safe is keeping 3D as author-time projection (§A.5, G-2); the moment the SDK emits a 3D transform it can't guarantee, the guarantee is gone.

---

*End of Appendix A. Re-read the disclaimer; verify every formula's sign convention against your renderer before relying on it.*
