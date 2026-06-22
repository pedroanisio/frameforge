---
title: "FrameGraph SDK — Consolidated Proposal (refined)"
status: proposal / non-normative
supersedes:
  - framegraph-sdk-interface.md
  - framegraph-sdk-geometry.md
derived_from:
  - framegraph-v2.ebnf
  - framegraph-v2-style.ebnf
  - anthropic_claude_deck_improved_framegraph.yml (measured fixture)
  - framegraph-geom.js (executed reference implementation)
references:
  - "Typst: measurement→placement→breaking layout; introspection over iterations"
  - "Vega-Lite: published versioned JSON Schema + example gallery compiled as regression tests"
  - "D2 / dagre / ELK: automatic graph layout engines"
  - "PDF/UA: structure tree, semantic roles, alt text, reading order"
  - "Asymptote: 2D&3D vector language that projects 3D→2D; Hobby spline control points"
disclaimer: >
  NOTHING HERE SHOULD BE TAKEN FOR GRANTED. This is a design proposal, not a
  specification. The `@framegraph/*` package names describe a language-neutral
  interface and are not shipped JavaScript packages. The Python implementation
  now lives under `framegraph.sdk` and is tested in `tests/test_sdk.py`. The
  Pydantic models are the source of truth; this is a downstream view to be
  reconciled against them. Any statement not backed by a real definition (the
  EBNF files), a citable reference, or an executed result may be invalid or a
  hallucination. Math is stated so it can be checked, not trusted; verify sign
  conventions against your own renderer.
---

# FrameGraph SDK — Consolidated Proposal (refined)

This consolidates the layered-interface and geometry proposals into one document
and folds in two threads that previously had no home: the comparison findings
against analogous systems, and the conformance discipline the reference
implementation forced into view. Section 10 lists exactly what changed.

---

## 1. Three principles that decide everything downstream

Every later choice follows from one of these, so they come first.

**1.1 The models are the source of truth.** The grammar's own headers state it:
Pydantic v2 models are canonical, the JSON Schema is generated from them, the
EBNF is a non-normative view. The SDK binds to the models/schema; the EBNF is
documentation. One package is generated from the schema; everything else imports
from it and may not re-declare a core type, so the tiers cannot drift.

**1.2 Describe vs solve — the line that assigns work to a tier.** A computation
belongs to whichever party can perform it deterministically. This single
distinction resolves what was previously an ad-hoc, per-feature decision:

| Concern | Who solves it | Why | Tier |
|---------|---------------|-----|------|
| Layout / sizing / fit | the renderer's measure pass | it owns font metrics and box resolution | author *describes* (sets `Layout`/`Sizing`); never writes computed boxes |
| Geometry / curves / 3D projection | the SDK | the page renderer is not a geometry kernel | SDK *solves* at expansion; emits concrete 2D |

So a `grid` helper sets fields and stops; a `Scene3D` helper runs the full
projection and emits polygons. Confusing the two is the recurring authoring bug.

**1.3 The renderer is the final arbiter — therefore conformance is not
optional.** The format states that every construct is a proposal to verify
against the renderer. Left as an aside, that sentence is a liability; made
concrete, it is a test corpus (§8). The mature comparators all close this loop —
Vega-Lite ships a versioned schema and recompiles its example gallery as
regression tests. FrameGraph needs the same, and the reference implementation
proved why (§8).

---

## 2. Architecture — one package map

```
@framegraph/model      Tier 0  GENERATED from JSON Schema. Closed types, value types,
                               discriminated unions. The only generated package.
@framegraph/geometry   Tier 0  Pure math: Vec2/Vec3, Mat3/Mat4, Path, parametric
                               sampling, projection. No document dependency; unit-testable
                               against the formulas in §3.3.
@framegraph/validate   Tier 1  validateStaticRules + the rule catalogue (§4). Catches
                               everything the schema cannot express.
@framegraph/author     Tier 2  DocumentBuilder, handles, builders.
   ├─ /macros                  theme(), md``, intermediate methods (defer-vs-flatten).
   └─ /draw                    Path/Frame/Scene3D builders → VisualObjects.
@framegraph/expand     Tier 3  Asset resolution, hashing, use/component instantiation,
                               AND geometry/projection realization (§6).
@framegraph/io         —       serialize (closed write) / parse (forgiving read).
@framegraph/conform    —       Golden corpus + math property tests (§8).
```

Dependency order: `model` ← everything; `geometry` is standalone; `validate`,
`author`, `expand`, `io`, `conform` all consume `model`; `author/draw` consumes
`geometry`; `expand` realizes both asset and geometry computation.

### 2.1 Python SDK implemented in this repository

The Python SDK maps the package tiers above onto importable modules under
`framegraph.sdk`:

| Proposal tier | Python module | Implemented surface |
|---|---|---|
| `@framegraph/model` | `framegraph.sdk.model` | imports `models.framegraph` as the sole authority; exposes `Document`, `HEAD_VERSION`, validation, and plain-dict conversion |
| `@framegraph/geometry` | `framegraph.sdk.geometry` | `Vec2`, `Vec3`, `Mat3`, `Mat4`, `CubicBezier`, `Path`, and the quarter-circle kappa helper |
| `@framegraph/validate` | `framegraph.sdk.validate` | `ValidationReport`, `Issue`, `validate_static_rules()` over Pydantic structure plus the existing static validator |
| `@framegraph/author` | `framegraph.sdk.author` | `DocumentBuilder`, `PageBuilder`, and nominal `Handle` values for defs/tokens |
| `@framegraph/author/macros` | `framegraph.sdk.macros` | `theme()`, `md()`, and `paragraph()` macros that lower to token definitions and `Inline` / flow fragments |
| `@framegraph/author/draw` | `framegraph.sdk.draw` | `Frame` data-space mapping and `Scene3D` mesh/surface/extrude/revolve helpers that emit 2D visual objects |
| `@framegraph/expand` | `framegraph.sdk.expand` | deterministic asset/font hash pinning and post-expansion model validation |
| `@framegraph/io` | `framegraph.sdk.io` | validated JSON/YAML parse and canonical JSON/YAML serialization |
| `@framegraph/conform` | `framegraph.sdk.conform` | proxy-render SVG extraction and per-page SHA-256 golden helpers |

The Python binding deliberately does not generate or redeclare core model types.
Every public document-producing API validates through `models.framegraph.Document`.
Unsupported future constructs, such as component slot content, must be
represented as SDK-side helpers that lower to current 2D model objects before
`build()` / `expand()`, or they fail validation. The shipped `Scene3D` follows
that rule: it projects to a `group` of 2D polygons before the model sees it.

---

## 3. Tier 0 — the closed model and the leaf vocabulary

### 3.1 The model contract (canonical statement)

Objects are **closed** (`extra="forbid"`): no index signature, and a single
`meta?: Record<string, unknown>` is the only open data. The large sets are
**discriminated** — `VisualObject` on `type` (37 members: 5 primitives, dimension,
text/image/icon, 2 charts, legend/bullet_list/chip_row/table, connector, group,
component, use, 19 `uml.*`), `Flowable` on `type` (17 members), `PageProducer` on
`mode` (`page`|`flow`). `TextContent` is `text` XOR `spans`; `Inline` is keyed on
`kind`. This tier is generated; the hand-written form documents the contract the
generator must honor.

### 3.2 Value types and handles (canonical statement)

Value types are branded so a bare `string`/`number[]` cannot pose as a validated
value: `SemVer`, `Length` (= `number | \`${number}${LengthUnit}\` | LengthToken`),
`Box = [Length,Length,Length,Length]`, `Point = [number,number]` (unitless),
`Color` (CSS string or `ColorHandle`), `Angle`. Every `defs` key has a nominal
handle (`ColorHandle`, `MasterHandle`, `SymbolHandle`, …); reference sites take
the handle, never a string, moving dangling-reference errors to compile time. The
sole runtime-checked reference is `cite` (the bibliography is an external file).

### 3.3 Geometry algebra (`@framegraph/geometry`)

The math leaf vocabulary, framework-free and independently testable. `Mat3` is a
2D affine that maps 1:1 to `TransformFn matrix(a,b,c,d,e,f)`; `Mat4` is 3D with a
`project()` that does the perspective divide. The checkable formulas:

- Cubic Bézier: `B(t) = (1−t)³P₀ + 3(1−t)²t·P₁ + 3(1−t)t²·P₂ + t³P₃`.
- Catmull-Rom → Bézier (uniform): `C₁ = Pᵢ + (Pᵢ₊₁−Pᵢ₋₁)/6`, `C₂ = Pᵢ₊₁ − (Pᵢ₊₂−Pᵢ)/6`.
- Quarter-circle control offset: `κ = (4/3)(√2 − 1) ≈ 0.5523`.
- Isometric tilt: `arctan(1/√2) ≈ 35.264°`, after a 45° yaw, then orthographic.
- Convention: page space is **Y-down**, so a mathematically positive rotation reads clockwise.

---

## 4. Tier 1 — the consolidated rule catalogue (`@framegraph/validate`)

```ts
interface ValidationReport { ok: boolean; issues: Issue[]; }
interface Issue { ruleId: string; severity: "error"|"warning"; path: string; message: string; }
function validateStaticRules(model: Document, opts?: { targets?: string[] }): ValidationReport;
```

`path` is a JSON pointer to the offending node. One catalogue, merging the
structural and geometry rules that were previously split:

- **Reference resolution** — `bind`→semantic node; `master`→masters; `component`→components; `symbol`→symbols; `style`→text_styles/styles; `stroke_style` (string)→stroke_styles; `Color` token arm→colors; `font`→fonts; `glyph`→glyph_map; `src`→assets; counter `series`/`reset_with`→counters; `cite`→bib; `ref`→an existing id.
- **Exactly-one-of** — `TextContent` (text XOR spans); `CanvasObject` (preset XOR size); `Anchor` (string | Point | object).
- **Structural conditionals** — `grid_span` only under a grid-layout parent; a flow `master` declares ≥1 region.
- **Chaining** — `FlowRegion.next` / `PageMaster.next` resolve without cycles.
- **Per-target integrity** — each `target` resolves every reference it touches after its adjustments.
- **Determinism precondition** — `Layout`/`Sizing` inputs suffice for the measure pass to be deterministic (the fit-safe contract; §9 F-1).
- **Geometry rules** (new, from the draw layer) — `path.d` parses as valid path data; computed geometry uses absolute units only (no `%`/`fr` inside sampled coordinates); the SDK never emits 3D transforms or `perspective` (it projects instead; §9 G-2).

---

## 5. Tier 2 — authoring (`@framegraph/author`)

### 5.1 Builder + handles

`define*` methods return handles; `page`/`flow` open builders; `build()` produces
the Tier-0 model or throws. References are correct by construction because the
only token a ref site accepts is a handle.

### 5.2 Macros (`/macros`)

All sugar is a total function into the validated model and threads handles:
`theme()` collapses the tokens block to one call; the `` md`…` `` tagged template
parses rich text to `Inline[]` while interpolating handles (so cross-refs stay
statically checked); intermediate methods (`header`, `numberedPanel`, `panelRow`)
lower to model fragments. **Lowering rule:** emit `use`/`component` when the
format's parameterization can carry the abstraction, flatten only when it cannot.
Content-bearing reuse goes through `group` or `use`+`params`, never `component`
(see §9 C-1).

### 5.3 Draw (`/draw`) — geometry that solves

`Path` (moveTo/cubicTo/quadTo/arcTo/`through`), `Frame.fit(domain, box, scales)`
for transformed/data spaces, and `Scene3D` (mesh/parametricSurface/extrude/revolve
+ `render(camera, box)`). These **solve** per §1.2 and emit `path`/`polyline`/
`group`. `Frame` pre-applies nonlinear scales (log/pow/polar a matrix can't
express) and only uses a `matrix` group transform for pure-affine view frames.

---

## 6. Tier 3 — expansion, the single home for computed output (`@framegraph/expand`)

```ts
function expand(model: Document, opts?: ExpandOptions): Promise<ExpandedDocument>;
```

This resolves and hash-pins assets/imports, instantiates `use`/`component`, **and
realizes all geometry and 3D projection** — curve flattening, frame application,
`Scene3D.render`. Stating this once removes the earlier ambiguity about where
geometry runs: it runs here, offline and deterministic, and is pinned with the
asset hashes so the document is reproducible. After expansion the renderer sees
only 2D primitives that exist in the grammar today.

---

## 7. io — serialization (`@framegraph/io`)

`serialize(model, {format})` writes canonical JSON/YAML (closed). `parse(text)`
is forgiving: unknown union members fall through a left-to-right parser fallback
rather than throwing, so newer documents degrade instead of breaking.

---

## 8. Conformance and testing (`@framegraph/conform`) — promoted to first-class

This is the refinement the reference implementation made unavoidable.

**Golden corpus.** Each fixture (the Anthropic deck is the seed) is pinned to a
reference render; any change diffs against it. This is how "the renderer is the
arbiter" becomes operational rather than rhetorical, mirroring Vega-Lite's
recompile-the-gallery regression approach.

**Math property tests for `@framegraph/geometry`.** Because the geometry package
is pure and the formulas in §3.3 are explicit, they are directly testable:
round-trip `Mat3.mul`/`inverse` to identity; verify Bézier endpoints; verify the
quarter-circle radius error stays within tolerance for the κ approximation;
verify projected sphere face counts and absence of `NaN`.

**The motivating case.** The reference implementation's adaptive sampler used a
midpoint-only flatness test. Executed, it rendered `sin(x)` over `[−2π, 2π]` as a
flat line: the curve crosses the chord midpoint at `t=0`, so a single midpoint
check wrongly reported "flat" and returned only the endpoints. Inspection would
have passed it; execution caught it. The fix (force `minDepth` uniform
subdivisions before adaptive refinement) is verified by re-running. The lesson is
the policy: geometry correctness is enforced by the executable corpus, never by
reading the code.

---

## 9. Consolidated gap & roadmap register

One register replacing the three previous ID schemes. **Class**: `SDK` = workaround
available now; `GRAMMAR` = needs a model/grammar change; `ECO` = ecosystem/process.

| ID | Gap (grounded) | Sev | Class | Fix |
|----|----------------|-----|-------|-----|
| D-1 | Diagrams: 19 `uml.*` types + connectors, but node placement is manual/absolute — no auto-layout, unlike dagre/ELK/Graphviz | high | GRAMMAR+SDK | add an optional auto-layout pass over the semantic graph (it already has `bind`/edges), or embed ELK; keep absolute as override |
| A-1 | Accessibility: has `decorative`, `role`, `lang`, but no **alt text** and no **reading-order/structure tree** independent of visual position; deck side can't export tagged/PDF-UA | high | GRAMMAR | add `alt`/`actual_text` to image/figure; add a per-page reading-order list → tagged structure tree on export |
| C-1 | `ComponentObject` exposes only visual overrides; `ComponentDef` declares slots but instances have no slot-content channel; only `use` has `params` | med | GRAMMAR | add `slots`/`content` to `ComponentObject`, or document that content reuse goes through `use`/`symbol` |
| G-1 | `path.d` is an opaque string the schema cannot validate | med | GRAMMAR+SDK | add structured `segments: PathSeg[]` alongside `d`; validator parses `d` until then |
| L-1 | `Color` resolves a token; `Length` has no token arm, so a spacing scale can't be locked at the data layer | med | GRAMMAR | add `tokens.space`/`tokens.lengths`; let `Length` resolve a bare token name, mirroring `Color` |
| K-1 | No conformance corpus / reference-render semantics; "valid" is underdetermined | med | ECO | §8 corpus; version the schema at a resolvable URL |
| U-1 | `Length` defined twice (core vs style), both via special sequence; out-of-set units uncatchable by grammar | low | GRAMMAR | one shared `Unit` production both files import; validator enforces it |
| DAT-1 | Charts take literal data; no data→encoding mapping or transforms (vs Vega-Lite) | low | SDK | likely intentional scope — state it; embed compiled Vega-Lite as a figure when needed |
| PR-1 | No ICC/CMYK/output-intent; screen color only | low | GRAMMAR | add an output-intent reference at the target level for print targets |
| G-2 | 3D transforms/`perspective` "declared, may not render" — a trap | n/a | resolved | SDK never emits them; projects to 2D at expansion (§6) |
| F-1 | Fit-safe decks rely on shrink-to-fit; computed layout shifts fit to the measure pass | n/a | resolved | keep the fit contract on text styles; enforce via golden render (§8) |

**Calibration (do not re-add as gaps).** Verified against the grammar: typography
(`widows`/`orphans`/`hyphens` with limits, kerning, ligatures, variable-font axes)
and i18n (`direction`, `unicode_bidi`, vertical `writing_mode`) are **well
covered**. The earlier instinct to list them as weaknesses was wrong.

**Build sequence.** (1) `@framegraph/model` codegen — nothing else is real until
the generated types exist. (2) `@framegraph/validate` with the §4 catalogue.
(3) `@framegraph/conform` seed corpus (the deck), pinned. (4) `@framegraph/author`
+ `/macros`, then `/draw` on top of `@framegraph/geometry`. (5) `@framegraph/expand`
projection. **Grammar fixes to push first:** D-1 (auto-layout) and A-1 (a11y) are
the two that change what the format can *do*; G-1/L-1/C-1 are the smaller additive
ones.

---

## 10. What this refinement changed

- Promoted **conformance/testing** from scattered asides to a first-class concern (§8), motivated by the executed bug.
- Stated **describe-vs-solve** (§1.2) as the principle that assigns computations to tiers, replacing per-feature reasoning.
- Merged the **two package layouts** into one map (§2) and integrated `@framegraph/geometry` and `/draw`.
- Recorded the **implemented Python mapping** in §2.1: `framegraph.sdk.{model,geometry,validate,author,expand,io,conform}`.
- Fixed the **home of geometry computation**: it runs at expansion (§6), stated once.
- Unified the **three gap ID schemes** into one prioritized register (§9) and classified each as SDK / GRAMMAR / ECO.
- Folded in the **comparison findings** (auto-layout, accessibility, conformance, data, print color) that previously lived only in chat.
- Recorded the **calibration correction**: typography and i18n are not gaps.

*End of refined proposal. Re-read the disclaimer before relying on any part.*
