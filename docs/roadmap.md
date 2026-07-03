---
title: FrameGraph v2 — Roadmap
version: 2.2.0 (analysis baseline; repo HEAD moved to 2.3.0 on 2026-07-01 — see the Record-era note)
status: CANONICAL roadmap — sequence logic and priorities, still not dated commitments
date: 2026-06-22 (analysis) · 2026-07-02 (made canonical; federated index added)
method: >
  Gaps asserted against the EBNF + checked-in fixtures, then verified against the
  authoritative Pydantic models (`models/framegraph.py`, HEAD 2.2.0), and benchmarked
  against real specs of analogous systems (Typst, Vega-Lite, D2/dagre/ELK, Mermaid,
  PlantUML, PDF/UA, PDF/X). Item 7 and Appendix A are additionally derived from
  framegraph-v2.ebnf (PathObject, PolylineObject, ConnectorObject.Route, Point) and
  framegraph-v2-style.ebnf (TransformFn, perspective, transform_origin).
disclaimer: >
  This is a forward-looking gap analysis, not a delivery plan. "Missing" means
  "not expressible in the grammar/fixtures as inspected"; the models are the
  source of truth and could narrow a gap. Priorities reflect how defensible and
  consequential each gap is, not committed scheduling. Appendix A **documents the
  existing geometry/3D SDK** (`framegraph.sdk.{geometry,draw,manifold,fields}`) plus
  the grammar fixes G-1 and G-2 (both landed); the TypeScript `@framegraph/*` names in it are
  illustrative sketches of the shipping Python API, and every formula's sign
  convention must be verified against your renderer before use (canvas space is
  Y-DOWN, origin top-left). NOTHING IN THE APPENDIX SHOULD BE TAKEN FOR GRANTED.
appendix_references:
  - "Asymptote (Hammerlindl, Bowman, Prince): 2D & 3D vector graphics; Hobby-spline → 3D"
  - "Hobby (1986) / Knuth, The METAFONTbook ch.14: control-point selection"
  - "D3.js: curve interpolators and scales (linear/log/pow/time) — design model only"
  - "three.js: 3D scene graph — the comparator for *true* 3D (out of scope here)"
---

# FrameGraph v2 — Roadmap

!!! note "Canonical since 2026-07-02"
    Renamed from `roadmap-draft.md` and promoted to the **canonical roadmap**:
    the single index over every roadmap layer (see *The roadmap, federated*
    below). Canonical means this is where priorities and sequence live — it
    does **not** convert the sequence into dated commitments (the front-matter
    disclaimer stands).

!!! warning "Record era"
    This record pre-dates two 2026-07 events. (1) The src-layout refactor —
    read its paths through the mapping: `framegraph/` → `src/framegraph/`,
    `models/`, `schema/`, `grammar/`, `spec/` → `docs/…`, `fixtures/` →
    `tests/fixtures/`, `examples/` → `static/examples/`. (2) The **2.3.0
    release** (2026-07-01, an additive improvement pass unrelated to the
    "next minor" direction sketched at the end of this draft) — the `2.2.0`
    references below are this draft's analysis baseline, not HEAD. The prose
    is kept as written.

!!! note "What this is"
    A prioritized map of what FrameGraph cannot yet express, measured against the
    EBNF and the checked-in fixtures and benchmarked against the published specs
    of comparable systems. Each item states the gap, the evidence, the comparator
    that closes it, and a proposed fix. Items 1, 2, and 4 are **partly built
    already** — each now states the *residual* gap after re-grounding against the
    SDK and renderer (see the Verification-status note); items 3 and 5 are **scope
    decisions worth making explicit** rather than gaps; item 6 is conditional on a
    live-presentation goal; item 7's geometry/3D SDK **already ships** (Appendix A
    documents it; G-1 and G-2 both landed — item 7 complete); item 8 is an additive
    book-composition API surface informed by the permissive book corpus inspection;
    item 9 is a generative content object (prompt → image / block) resolved **once
    at build and pinned**, carrying a high determinism / trust risk that the design
    must contain; item 10 (added 2026-07-02) is the granular Adobe-suite parity
    programme over the 46-feature Illustrator teardown (Appendix B).
    (Items keep their original IDs; sections run in priority order, so the IDs
    appear out of sequence.)

## The roadmap, federated (canonical index)

This document owns the **product/format** roadmap. Three sibling layers are
tracked elsewhere and referenced here rather than duplicated:

| Layer | Source of truth | Content |
|---|---|---|
| Product / format (this doc) | the phases below | auto-layout wiring, PDF/UA, BookBuilder, generative objects, the 2.x split + 3.0 single-source direction |
| Engineering standards | [codebase-standards.md §16](codebase-standards.md) — the `[Target]` ledger | gating ruff, `mypy --strict`, coverage gate, TDD trees, golden drift tolerance, pre-commit, `__version__`/release recipe, CI matrix |
| Operational (tracked work) | GitHub, pinned umbrellas | [#36 — absorb framegraph v0.1.0](https://github.com/pedroanisio/frameforge/issues/36) (pattern catalog + fill bridge, UML 2.5 + full Sugiyama, `from-markdown`, symbol/token packs, deck corpus); [#43 — rename framegraph → frameforge](https://github.com/pedroanisio/frameforge/issues/43) (ADR-gated, idempotent engine, three slices); [#44 — silent text-clip diagnostics](https://github.com/pedroanisio/frameforge/issues/44); [#52 — Adobe-suite parity programme](https://github.com/pedroanisio/frameforge/issues/52) (item 10 made executable: workstreams #45–#51, teardown re-render as the progress metric) |
| Version trajectory | [CHANGELOG](../CHANGELOG.md) + rename ADR ([#37](https://github.com/pedroanisio/frameforge/issues/37)) | HEAD 2.3.0 → 2.4 (both DSL markers accepted + codemod, additive) → 3.0 (marker hard cut — which can carry this doc's 3.0 single-source milestone) |

Cross-links where the layers touch: item 1's optional "exact crossing
minimization beyond the current heuristics" is precisely what the absorption
plan imports ([#30](https://github.com/pedroanisio/frameforge/issues/30): the
sibling's 4-stage Sugiyama — cycle removal, median crossing minimization,
Brandes–Köpf — plus 14 UML composers); item 8's book-composition ambitions gain
a declarative on-ramp from the 375-pattern catalog + fill contract
([#28](https://github.com/pedroanisio/frameforge/issues/28)/[#29](https://github.com/pedroanisio/frameforge/issues/29))
and from the content library — 7 consulting themes, 4 symbol packs, 2
data-driven generators — delivered as `framegraph.library`
([#32](https://github.com/pedroanisio/frameforge/issues/32), see
[library.md](library.md));
and the text-fitting diagnostics gap ([#44](https://github.com/pedroanisio/frameforge/issues/44))
is a prerequisite of trustworthy book pagination (item 8) — silent content
loss and long-form composition cannot coexist.

!!! info "Verification status"
    Every gap below was checked against `models/framegraph.py` and the grammar at
    HEAD 2.2.0, not asserted from memory. Where the source contradicted the draft
    it was corrected (see item 1's container-layout note, the `uml.*` count, the
    refreshed model references for `widows`/`orphans` and `footnote_area`, and item 2,
    reframed after `alt`/`actual_text`/`reading_order` landed in the model).

!!! warning "Re-grounded against the implementation (2026-06-24)"
    An earlier pass checked the **format** (model + EBNF + fixtures) but not the
    **implementation**, and so overstated four gaps that the SDK/renderer/tests
    already fill. Capability questions live in `framegraph/sdk/*` and the renderer,
    not the wire format. Corrected here: **item 1** (graph layout already exists
    author-side in `sdk.topology`), **item 2** (SVG a11y is partly emitted by the
    SVG painter), **item 4** (`tests/test_golden_render.py` is a working
    golden-lock harness), and **item 7 / Appendix A** (the geometry/3D authoring
    SDK already ships in `sdk.{geometry,draw,manifold,fields}`). Each item now
    states the *residual* gap, with file evidence. A capability can be **delivered
    in the core (model/grammar/schema/renderer) yet not yet exposed in the SDK** —
    these are distinct milestones, and SDK support trails core delivery by design
    (see `adr-0002-sdk-lags-core-delivery.md`). "The SDK ships X" is therefore
    verified against `framegraph/sdk/`, never inferred from the model.

## Ground-truth status (audited 2026-06-24)

> **This roadmap (dated 2026-06-22) is substantially stale.** A line-by-line audit
> against the live tree shows most "gaps" are already built. The gap analyses below
> are kept as design context, but the *status* is:

| # | Item | Roadmap said | TRUE state (audited) | Evidence / what remains |
|---|------|--------------|----------------------|-------------------------|
| 4 | Conformance + golden render | gap | ✅ **DONE** | `tooling/render_golden.py`, `tests/golden/oracle.lock.json` (SHA-256 lock, CI-gated). **Tolerance band** added: exact hash primary + committed reference renders (`tests/golden/refs/`), numeric ±ε classifies cosmetic vs real drift (`--tolerance`/`--strict`). **Schema URL** versioned + resolvable-shaped (`…/schema/2.2.0/framegraph-v2.schema.json` + `version`). Residual: pixel/font/AA perceptual tolerance (raster-gated). |
| 2 | Accessibility / tagged export | gap | ✅ **SVG done**, PDF/UA open | `svg.py` a11y_wrap (decorative/role/alt/actual_text), root lang/title/desc, `tooling/check_accessibility.py`; tests. **2026-07-02:** reading-order *DOM ordering* was retired — DOM order IS paint order, and reordering emission painted listed content beneath unlisted backgrounds; `reading_order` now rides as `data-reading-order` metadata on the page group (paint order stays layer/z/document). PDF/UA awaits a PDF backend and must consume the metadata, not DOM order. |
| 7 | Geometry / 3D authoring SDK | additive gap | ✅ **done** | `sdk/geometry.py` (A.1/A.2), `sdk/manifold.py`+Scene3D (A.5); **A.3** curve sampling, **A.4** structured log-base/pow-exp scales, **A.6** orthographic `multiview`, **G-1** typed structured path segments (model `PathSeg`/`PathCommand` + EBNF `PathSegList`, JSON Schema `prefixItems`, enum-gated by `check_grammar_sync`), and **G-2** (`perspective` marked non-conformant in model + EBNF, validator WARN `non-conformant-3d`) all landed — **item 7 complete**. Only optional minor scale extras (categorical/time) remain. |
| 1 | Diagram auto-layout | gap | ✅ **author-time done** | `sdk/topology.py`: 5 algorithms **plus `auto_layout`/`layout_kind`** — a graph now lays itself out from its declared edges (algorithm inferred: grid/radial/layered/spring), and `Graph.render()` auto-layouts by default. Remaining (optional): a *render-time* pass over `mode: page` diagram groups, or an ELK binding. |
| 3 | Data layer for charts | out of scope | ✅ decision holds | `sdk/chart.py` is a lowering helper, no data transforms (by design). |
| 5 | Print colour (ICC/CMYK) | deferred | ✅ decision holds | no ICC/CMYK code; hook not yet reserved. |
| 6 | Interaction / animation | low | ✅ decision holds | no animation primitives. |
| — | Provenance / document signing *(unplanned — not an original item)* | not in roadmap | ✅ **shipped (opt-in)** | `framegraph/rendering/provenance.py` (`sign_svg`/`FrameForgeStamp`): a deterministic sha256 **content fingerprint** + tool/version + optional UTC timestamp, injected as an SVG `<metadata><frameforge …>` in a private namespace (`https://framegraph.dev/ns/provenance`). Opt-in via `render_fixtures.py --sign/--signed-at` and the MCP render tools (`sign=`/`signed_at=`); byte-identity (item 4 golden lock) preserved when off, and deterministic when no timestamp. A parallel recipe fingerprint ships in `recipe/sign.py`. Tests: `tests/test_provenance.py`. **Residual:** SDK exposure (none yet, per ADR 0002) and a **keyed/authenticated** signature (HMAC) if non-repudiation is ever needed — today it is tamper-*evident*, not authenticated. |

> **Net (updated 2026-06-25):** item #7 (geometry SDK) is now **complete** (A.1–A.6
> + G-1 + G-2), and #1 has author-time automatic layout. **No item (1–7) has an open
> author-facing gap** (items 8–9 remain unbuilt additive proposals). What remains is all deeper integration or externally gated:
> #1's optional *render-time* auto-layout pass (a model/renderer integration); #2's
> PDF/UA half (gated on a PDF backend that does not yet exist); and the ADR 0001
> LaTeX-fork deletion (gated on a `lualatex` toolchain). Scope decisions (#3/#5/#6)
> hold.

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

> Verified in `models/framegraph.py`: `widows`/`orphans`,
> `hyphenate_limit_chars`, `font_kerning`, `unicode_bidi`, `writing_mode`, and
> `footnote_area`; `oklch`/`lab`/`lch` in `grammar/framegraph-v2-style.ebnf`.
> `decorative`/`role`/`lang` exist, as do `alt`/`actual_text` on image/figure
> objects and per-page `reading_order`. The
> accessibility *vocabulary* is therefore present; only the tagged-export that
> consumes it remains (item 2, reframed).

## Priority at a glance

| # | Item | Priority | Kind |
|---|------|----------|------|
| 1 | Automatic *graph* layout for diagrams | **High** | Algorithms exist (`sdk.topology`) → render-time wiring remains |
| 2 | Accessibility / tagged-export model | **High** | Vocabulary + partial SVG a11y done → PDF/UA tagged export remains |
| 4 | Conformance suite + reference-renderer semantics | **Low** | Golden lock + **tolerance band** + versioned schema URL done → only raster-perceptual tolerance remains |
| 3 | Data layer for charts | **Medium** | Scope decision → out of scope (provisional) |
| 5 | Print color management (ICC / CMYK) | **Medium** | Scope decision → deferred (provisional) |
| 7 | Geometry / transformed spaces / 3D authoring SDK | **Low** | SDK ships; G-1 + G-2 landed → **complete** (optional scale extras only) |
| 8 | Book composition API | **Medium-High** | Additive product/API surface |
| 9 | Generative content objects (prompt → image / content) | **Medium** | Additive object + generation tier; high determinism / trust risk |
| 10 | Adobe-suite parity program (granular; Appendix B) | **Medium-High** | Programme of granular closures over the 46-feature Illustrator teardown |
| 6 | Interaction / animation for presented decks | **Low** | Conditional on goal |

> Net ordering (most defensible first): wire the existing graph-layout engine into
> a render pass → finish accessible export (PDF/UA) → add a tolerance band over the
> existing golden lock. The data layer and print color are scope choices worth
> stating outright rather than leaving implied. The geometry / 3D SDK (item 7)
> **already ships** (`sdk.{geometry,draw,manifold,fields}`) — so it is lowest-risk
> and now **Low** priority: with G-1 and G-2 both landed, item 7 is complete and the
> only residual is documentation, not a build.

## Implementation sequence (recommended)

Recommended *ordering* — sequence logic, **not** dates or commitments (see the
front-matter disclaimer). It departs from the "net ordering" above on purpose:
item 2's vocabulary already exists in the current model, so it is cheap to finish and
moves up; item 4 is an **enabler** that should precede the high-risk item-1 work,
so it moves ahead of item 1.

0. **Scope decisions — DECIDED (provisional, 2026-06-22).** Recorded so nothing
   downstream waits on them: item 3 (chart data layer) → **out of scope** (embed
   compiled Vega-Lite as a figure object); item 5 (print color) → **deferred**
   behind an optional target-level ICC / output-intent hook (no CMYK separation
   now). Both revisitable. *Effort: S.*
1. **Item 2 — accessibility export.** Vocabulary exists and the SVG painter
   already emits `role=`/`aria-*`; **complete** SVG a11y (`<title>`/`<desc>`,
   `data-reading-order` structure metadata, `decorative` → `aria-hidden`) against the existing
   proxy, then add full PDF/UA tagging once a tagging PDF backend exists (today's
   PDF is untagged Chromium print). *Effort: S (finish SVG) → L (PDF/UA).*
2. **Item 4 — golden-render harness.** Pin the `b1/` fixtures to reference renders
   with an explicit tolerance before the big feature, so item 1 is regression-safe.
   *Effort: M. Enabler.*
3. **Item 1 — diagram auto-layout.** The flagship capability, now under golden-test
   protection: an ELK-backed layout tier for `mode: page` diagram groups keyed off
   the semantic graph, with absolute positioning as the override. *Effort: XL;
   depends on step 2.*
4. **Item 7 — geometry / 3D: complete; document the existing SDK.** The authoring
   math ships in `sdk.{geometry,draw,manifold,fields}`, and **both grammar fixes have
   landed** — G-1 (typed structured path segments: model `PathSeg`/`PathCommand`, EBNF
   `PathSegList`, JSON-Schema `prefixItems`, enum-gated by `grammar-check`) and G-2
   (`perspective` marked non-conformant in model + EBNF, validator WARN
   `non-conformant-3d`). The only residual is documentation (Appendix A). *Effort: XS.*
5. **Item 8 — Book composition API.** Build the semantic authoring layer above
   pages: `BookBuilder`, chapter/section builders, block IR, deterministic
   single-column pagination, figure numbering/captions, `keep_with_caption`, and
   lowering to today's `DocumentBuilder` / `PageBuilder`. This can use the
   existing imported-figure asset metadata without changing the core grammar.
   *Effort: M → L; additive product surface.*
6. **Deferred / conditional.** Items 3 / 5 *implementation* only if a later decision
   reverses step 0; item 6 (interaction / animation) only if live presentation
   becomes a goal. *Lowest priority.*

> **Cross-cutting dependency:** item 2's PDF/UA half and item 4's reference-renderer
> semantics both presuppose a real renderer/exporter beyond today's SVG / matplotlib
> proxies. If one does not exist, building it is an implicit prerequisite beneath
> steps 1 (PDF), 2, and 3.

---

## Phase 1 — defensible gaps

### 1. Automatic *graph* layout for diagrams — the clearest gap

**Gap (reframed — placement algorithms exist in the SDK; the render-time pass
does not).** FrameGraph ships 17 `uml.*` object types plus connectors with
`route` kinds (straight / orthogonal / curved), and the **SDK already computes
graph layouts**: `framegraph/sdk/topology.py` (`Graph`) exposes `circular_layout`,
`grid_layout`, `radial_layout`, `layered_layout` (hierarchical / Sugiyama) and
`spring_layout` (force-directed) — each returning `dict[str, Vec2]` node positions
from declared nodes and edges — plus a `render()`. So "node placement is manual"
is too strong: the algorithms exist. What is missing is the **wiring** — nothing
in `framegraph/rendering/` invokes them, so there is no *declarative, render-time*
graph-placement pass keyed off the semantic graph for `mode: page` diagram groups;
you must call a layout method explicitly in the SDK and bake the coordinates.

!!! note "What already exists — and what it does not yet do"
    Two layers exist. **Container** layout: `Group.layout` with
    `kind: row | column | grid | free` plus `gap` / `row_gap` / `column_gap` /
    `padding` / `align`, realized by `LayoutEngine.arrange`
    ([src/framegraph/rendering/domain/services/layout_engine.py](../src/framegraph/rendering/domain/services/layout_engine.py))
    — a box-model packer that repositions a group's children into rows / columns /
    a grid and does **not** resize them; it cannot place nodes from edges.
    **Graph** layout: `sdk.topology.Graph.{layered,spring,circular,radial,grid}_layout`
    *does* place nodes from declared edges (and `spring_layout` relaxes a
    force model) — but author-side only, not as a render pass. So the gap is not
    "no graph engine"; it is the missing **bridge** that auto-invokes the existing
    engine at render time, plus optional obstacle-aware routing / exact crossing
    minimization beyond the current heuristics.

**Comparators.** Every analogous diagram-as-code tool computes placement from
declared nodes and edges — D2 bundles dagre and ELK (with TALA as a premium
engine), Mermaid uses dagre, PlantUML uses Graphviz's DOT. Dagre produces
layered / hierarchical layouts based on Graphviz's DOT algorithm; ELK suits
node-link diagrams with ports and direction. The category's whole appeal is that
the same input always produces the same output — no manual positioning, and
therefore no style drift across a team. FrameGraph's diagram side gives that up.

**Fix (narrower than first stated — the placement math is done).** Expose a
declarative auto-layout on `mode: page` diagram groups that calls the existing
`sdk.topology` engines from the semantic graph (it already has `bind`, ontology,
and edge directionality) and emits computed boxes at expansion time, with absolute
positioning as the override. Optionally adopt an external engine (ELK is
embeddable) for obstacle-aware routing and exact crossing minimization beyond the
current heuristics. Effort is **M–L (wiring + a render pass), not XL.**

### 2. Accessibility / tagged-export model

**Gap (reframed — vocabulary done, SVG a11y partly done, PDF/UA export missing).**
In the current model the *vocabulary* exists: `decorative`, `role`, `lang`,
**`alt`/`actual_text` on image and figure objects**, and a **per-page
`reading_order`** over object ids. The SVG proxy already *consumes* part of it —
`framegraph/rendering/infrastructure/painters/svg.py` emits `role=` (line 266) and
`aria-*` (lines 495, 501). What is still missing is the **PDF consumer**: no
exporter maps these into a tagged PDF **logical structure tree** — roles, alt
text, and a reading order independent of visual position — because there is no
tagging PDF backend (today's PDF is untagged Chromium print). So SVG a11y is
largely authorable *and* renderable already; an accessible **PDF/UA** artifact is
the part that cannot yet be produced.

**Comparators.** PDF/UA makes both non-negotiable: every meaningful element must
sit in a structure tree with the correct semantic role, every non-text element
must carry alternative text, and the tree's reading order must match the visual
reading order. This is increasingly a legal requirement, not a nicety — the ADA,
the European Accessibility Act, and Section 508 all reference WCAG as the accepted
standard.

**Fix (export-side, not a format change).** Implement the tagged-export pass: map
`reading_order` + `role` to a PDF structure tree, `alt`/`actual_text` to element
alternative text, and `decorative` to PDF artifacts. The authoring fields already
exist in the current model and grammar; what remains is renderer/exporter
work plus a conformance check that every non-`decorative` object is reachable in
some page's `reading_order`.

### 4. Conformance suite + reference-renderer semantics

**Gap (reframed — golden lock, tolerance band, and schema URL all landed; only
raster-perceptual tolerance remains).** The format's stance — treat each construct
as a proposal to verify against the renderer — leaves "valid" underdetermined.
FrameGraph has the schema, the models, the `b1/` authoritative fixtures as an oracle,
the `--check-overflow` text-fit gate, and a working golden-render lock
(`tooling/render_golden.py` + `tests/golden/oracle.lock.json`). The two former
residuals are now closed: a **numeric tolerance band** (exact hash stays primary;
on a mismatch the fresh render is compared against a committed reference under
`tests/golden/refs/` within a coordinate ±ε, classifying cosmetic vs real drift —
`--tolerance`/`--strict`), and a **resolvable, versioned schema URL**
(`…/schema/2.2.0/framegraph-v2.schema.json` + a `version` field) documents can
self-declare against. The only remaining piece is a **pixel/font/AA perceptual**
tolerance, which needs a raster backend (out of scope in this environment).

**Comparators.** The mature comparators close this loop. Vega-Lite publishes a
versioned JSON Schema and an example gallery, and its CI recompiles every example
to reference Vega specs and SVGs that serve as regression tests, with an explicit
backward-compatibility commitment.

**Fix (done — numeric tolerance + versioned URL landed).** The **tolerance mode** is
implemented as a numeric coordinate-distance band alongside the exact-hash lock
(committed reference renders + ±ε classification), so cosmetically-irrelevant
sub-pixel jitter no longer produces false failures while real drift still fails. The
schema is now versioned at a **resolvable URL** (`…/schema/2.2.0/…` + `version`) the
way Vega-Lite does, so documents can self-declare conformance. A perceptual
*pixel-distance* band (catching font/AA differences) remains a raster-gated follow-up.

---

## Phase 2 — scope decisions to make explicit

### 3. Data layer for charts

**Gap.** Charts take literal `ChartData`; the `transform` keyword is CSS visual
transforms (`TransformFn`), not data transforms. FrameGraph requires every chart
to be pre-aggregated upstream and every axis specified. Note that charts already
sit **outside the core conformance profile** (`models/framegraph.py`),
so treating the data layer as out-of-scope would be consistent with the existing
profile boundary, not a new exclusion.

**Comparator.** Vega-Lite exists precisely to close this: it maps data attributes
to visual channels and includes common data transforms (binning, aggregation,
sorting, filtering), auto-produces axes / legends / scales from a minimal spec,
and composes views through a layer / concat / facet / repeat algebra that aligns
scales and axes. The cost of FrameGraph's choice is real: no single source of
truth from data to multiple views.

**Decision (provisional, 2026-06-22): out of scope.** A document format need not be
a visualization grammar, and charts already sit outside the core profile, so this is
consistent with the existing boundary rather than a new exclusion. Authors embed
compiled Vega-Lite output as a figure object. Revisit only if first-class,
data-driven charts become a product goal — at which point the additive fix is a
minimal data + encoding block on the chart objects, not a reinvented algebra.

### 5. Print color management

**Gap.** Modern screen color is well covered (see calibration), but there is no
ICC output intent or CMYK separation. For the book / print target that is a real
omission.

**Comparator.** PDF/X-style print workflows require unambiguous color through a
specified ICC output intent or full color management, with fonts embedded.

**Decision (provisional, 2026-06-22): deferred behind a target-level hook.** Reserve
an optional output-intent / ICC reference on `RenderTarget` so print targets can
declare a profile and screen targets ignore it — but do not build CMYK separation
now. The reservation keeps it additive when a print target becomes real.

### 7. Geometry, transformed spaces, and 3D authoring — the SDK ships; both grammar fixes (G-1, G-2) have landed

**Gap (reframed — the authoring layer already exists; G-1 and G-2 have both
landed, so item 7 is complete).** The grammar can *represent* arbitrary 2D geometry — `PathObject.d` (SVG
path data), `PolylineObject.points`, `TransformFn.matrix` (full 2D affine) — and
**the SDK already computes it.** `framegraph/sdk/geometry.py` exports `Mat3`,
`Mat4`, `Path`, `Vec2`, `Vec3`, `CubicBezier`, `Camera`, and `quarter_circle_kappa`
(the exact arc constant Appendix A derives); `framegraph/sdk/draw.py` has
`Scene3D`, `Camera`, `Frame`, and `.render()` with orthographic / perspective /
isometric projection (including painter's-algorithm depth sort);
`framegraph/sdk/manifold.py` has `parametric` / `sphere` / `torus` / `saddle` /
`wave`; `framegraph/sdk/fields.py` has `VectorField` (a quiver). Five examples
already exercise it (`sdk_3d_scene.py`, `sdk_geometry_patterns.py`,
`topology_perspective.py`, `fields_lattices_manifolds.py`,
`geometry_topology_deck.py`). So this is **not** a missing authoring layer. **G-1
has now landed** — `PathObject.d` accepts a typed `list[PathSeg]` alongside the
string (model `PathSeg`/`PathCommand`, EBNF `PathSegList`, JSON-Schema `prefixItems`,
enum-gated by `check_grammar_sync`), so structured path geometry is schema-checkable.
**G-2 has now landed too**: `TransformFn` is 2D-only (no 3D functions exist), and the
lone 3D-declared surface — the `perspective` property — is marked NON-CONFORMANT in
the model and EBNF, with the validator emitting a `non-conformant-3d` WARN when it is
set. So the "declared, may not render" trap is closed: it surfaces at validation
instead of silently. The SDK's answer remains the right one — author 3D via Scene3D
2D-projection (§A.5), never the inert property.

**Comparator.** A 2D&3D vector language (Asymptote) computes geometry and 3D and
*projects to 2D vector output* rather than shipping a 3D scene to the page; D3's
scales (`linear` / `log` / `pow`) model the data→page frame mapping. The lesson is
that the geometry kernel belongs in the authoring tool, not the page renderer.

**Fix (now just documentation — both grammar fixes are done).** The author-time
math already ships in `framegraph.sdk.{geometry,draw,manifold,fields}` and **emits
only primitives the grammar has** — `path`, `polyline`, `group`, `matrix` —
resolving curves and 3D→2D projection at expansion time and pinning the result with
the hash contract. **G-1 is done** (a typed `list[PathSeg]` alongside the `d` string,
schema-checkable, landed in both models and EBNF, enum-gated by `check_grammar_sync`)
and **G-2 is done** (`perspective` marked non-conformant in model + EBNF, validator
WARN `non-conformant-3d`). The only remaining work is to **document** the SDK
(Appendix A is effectively its spec). Priority stays **Low** and item 7 carries no
open gap. Full design, math, and grammar-fix table in **Appendix A** — read as
documentation of the existing SDK, not a build proposal.

### 8. Book composition API — semantic layer above pages

**Gap.** The SDK can author pages and can now place controlled imported figures,
but there is no first-class surface for expressing a book as chapters, sections,
paragraphs, figures, tables, callouts, examples, formulas, and references before
pagination. Existing examples therefore hand-code book-like layout directly with
page coordinates or local helper classes, which proves the product shape but does
not give downstream tooling a stable API for import, restyling, pagination, or
book-wide numbering.

**Corpus evidence (2026-06-24).** The permissively licensed corpus inspection
(scope contract: [book-corpus-scope.md](book-corpus-scope.md), fetched by
`tooling/fetch_book_corpus.py`)
split the problem cleanly: Project Gutenberg EPUBs provide useful spine, chapter,
front-matter, and DOM structure pressure, while OpenStax PDFs provide the strong
figure/table/caption/formula/side-bar pressure. The immediate product need is not
another drawing primitive; it is a semantic composition layer that can accept
imported blocks and lower them to normal FrameGraph pages.

**Fix.** Add a `BookBuilder` layer above `DocumentBuilder`, with
`chapter()`, `section()`, `para()`, `figure()`, `table()`, `callout()`, `code()`,
and `formula()` authoring methods backed by a small block IR. The composer should
initially be deterministic and single-column: it paginates blocks, keeps captions
with figures, numbers figures/tables, emits TOC metadata, and lowers to existing
`PageBuilder` primitives. Imported PDF/EPUB figures should flow through
`FigureAsset` so provenance, source bounding boxes, caption text, license,
attribution, and confidence survive into the rendered group metadata.

**First increment.** Implement only the minimum surface needed to validate the
book-import workflow:

- `BookBuilder` plus chapter and section builders.
- Blocks for paragraph, heading, figure, table, callout, code, formula, and list.
- `FigureAsset` integration with figure numbering, captions, and
  `keep_with_caption`.
- Deterministic single-column pagination with page templates and page numbers.
- TOC/reference metadata sufficient for inspection and later export.
- Lowering to existing `DocumentBuilder` / `PageBuilder`; no new renderer contract.

**Not in this increment (as of 2026-06-24).** These are explicit non-goals for the
first Book API slice, not permanent exclusions:

- Full EPUB/PDF import automation. The first API accepts extracted blocks/assets;
  robust extractors can be added behind it.
- OCR-only scanned books and image-only PDFs.
- Multi-column magazine layout, side floats, arbitrary float collision avoidance,
  and advanced page-breaking optimization.
- Full math-heavy EPUB import, equation parsing, or semantic MathML/LaTeX
  preservation beyond a formula block placeholder.
- Bidirectional/RTL and complex-script book composition beyond the typography
  vocabulary already present in the model.
- Citation management, bibliography formatting, cross-reference resolution, and
  index generation.
- PDF/UA tagging and print/PDF export guarantees; those remain tied to item 2 and
  the renderer/exporter work.
- DRM/proprietary formats, non-permissive corpora, and license automation beyond
  carrying attribution/provenance metadata.
- A general data-visualization grammar; item 3 remains out of scope unless the
  chart-data decision is reopened.

### 9. Generative content objects — prompt → asset, resolved once and pinned

**Proposal.** A first-class object whose content is *produced by a model* from a
prompt — the requested capability: pass a prompt to an image endpoint and the
generated image lands in the document; or a prompt that yields a generated block
(prose, a diagram, a table). Working shape: a `GenerativeObject` carrying
`{ kind: "image" | "text" | "diagram", prompt, model, params (seed / size /
style), box, alt }`, which a generation pass resolves into a concrete `image` /
`figure` / flow block.

**The constraint that defines the whole design — determinism.** FrameGraph's
conformance rests on deterministic golden-render SHA-256 locks (item 4) and the
expansion + hash-pinning contract (`framegraph/sdk/expand.py`,
`framegraph/sdk/conform.py`). A model call is non-deterministic and
network-dependent; resolving it **live on every render** would break golden locks,
hermetic CI, offline builds, and reproducibility — the format's core promise. So
the object MUST NOT be a paint-time call. It resolves **once**, at a dedicated
generation tier — the same "compute at expansion, pin the result" move item 7 uses
for geometry: the pass calls the endpoint, embeds the returned bytes / block, and
**pins** them plus a content hash into the document. After resolution the document
is an ordinary deterministic FrameGraph doc with no live calls, and golden locks
apply to the *resolved* doc. The authored `prompt` is the **source**; the resolved
asset is the **compiled view** — the same source→compiled pattern as `segments`→`d`
and builders→model. A cache key over `(prompt, model, params)` makes re-runs
reproducible; an explicit `regenerate` forces a fresh draw.

**PALS's Law — verification is mandatory, not optional (see `CLAUDE.md`).** Model
output is untrusted, incomplete, and may be wrong by default. FrameGraph already
embodies this at *authoring* time: `framegraph/vision`
(`propose_from_document` / `propose_from_image`) emits explicitly **UNVERIFIED
drafts**. Item 9 promotes that pattern to a document object, so the same gate is
non-negotiable before a generated asset enters the deterministic doc:
**format / schema validation** (it is a real PNG / SVG / valid block),
**containment / overflow** checks against `box`, **mandatory a11y** (a generated
image with no `alt` / `actual_text` fails the gate — ties to item 2), and
**provenance** (model id, prompt, seed, timestamp, license, confidence). Reuse the
existing `FigureAsset` (`framegraph/sdk/figure.py`) so source / license /
attribution / confidence survive into the rendered group metadata. An unverified
generation is a draft, never a conformant artifact.

**Comparator.** No deterministic document format (Typst, Vega-Lite) embeds live
generation; this is novel, and its entire risk is exactly determinism + trust —
which is why the resolve-once-pin + mandatory-verification design above is the
load-bearing part, not the model call itself.

**Fix / first increment.**

- New `GenerativeObject` (or a `prompt`-bearing variant of `image` / `figure` /
  group), **out of the core conformance profile** (gated like charts under §8.5),
  so deterministic / offline targets can refuse it outright.
- A **generation tier** in expansion: resolve each object → validate (PALS gate) →
  embed as a normal `image` / `figure` / flow block → pin bytes + content hash +
  `FigureAsset` provenance (reuse `expand.py`'s `ExpandOptions` / `pin_assets` and
  the `conform.py` hashing).
- **Determinism preserved:** post-generation the doc has zero live calls; golden
  locks pin the resolved bytes. `(prompt, model, params)` cache → reproducible;
  `regenerate: true` → new draw.
- **a11y / provenance required:** generation without `alt` / `actual_text` fails;
  model, prompt, seed, license, timestamp, confidence are recorded.

**Priority / risk — Medium appeal, high design risk.** The value is real (figure
and illustration authoring without a separate tool), but it pushes directly against
the determinism and trust guarantees, so it is additive *only* with the
resolve-once-pin + verification design. Sequence it **after** item 4 (the golden
harness it relies on to stay honest) and item 2 (the a11y gate it must satisfy).

### 10. Adobe-suite parity — the granular closure programme

**Goal.** One stated product goal is that FrameGraph can *match the Adobe
suite* — capability for capability, reached declaratively (by grammar and tool
call, not cursor). The evidence base is the 46-feature teardown
**Adobe Illustrator 2024+2025 vs FrameGraph v2.3.0** (v3, 2026-07-02;
generator: `static/examples/illustrator_vs_framegraph.py`). Provenance:
Illustrator's surface mined from **three manuals** over the doc-ray corpus
([24] "Adobe Illustrator 2024 User's Guide", 231 pp, 2,283 sentences;
[25] "Master Adobe Illustrator 2025", 159 pp, 1,875 sentences;
[26] "BMG 106: Computer Graphics II — Adobe Illustrator", 257 pp), every
feature round-tripped to a source-sentence ordinal; FrameGraph coverage
quoted from the gated `docs/capability-manifest.json` (278 capabilities,
sha256-pinned in the teardown's audit block +
`static/examples/illustrator_vs_framegraph.audit.json`).

**Rubric (v3.1):** HAS = a direct *functional* equivalent (same user
outcome, even if authored declaratively); PARTIAL = narrower / missing
interactivity or output fidelity; REFRAMED = same end by naming / tool call /
author→render loop; NONE carries a three-way `gap_type` — **architectural**
(the declarative model precludes it), **maturity** (plausible in the model,
simply unbuilt), or **non-goal** (declared scope choice) — and every M/L row
carries a confidence tag. The audit is git-stamped (`source_identity()`:
frameforge commit + a dirty flag, "so the stamp cannot lie").

**Scoreboard at 2.3.0:** 51 features → **14 HAS** (27%), **17 PARTIAL**,
**4 REFRAMED**, **16 NONE** (7 architectural + 3 maturity + 6 non-goals —
the 3 maturity rows are precisely W1/W2's buildables). Full-or-partial
**61%**; *reachable by any route* (has+partial+reframed) **35/51 = 69%**.
Earlier cuts scored higher (v1: 44 features, one manual, 48% full; v2: 46
features, 63% full-or-partial) because each revision widened the surface and
tightened the rubric — the drops are honesty, not regression. The full
granular matrix, one disposition per feature, is **Appendix B**.

**The teardown runs both ways** — its closing page lists what FrameGraph has
natively that Illustrator lacks: long-form flow documents (TOC, footnotes,
bibliography), structural validation + golden locks before a pixel is drawn,
a diffable plain-text source of truth, parametric geometry (equation-driven
curves, lattices, manifolds — charts Illustrator *does* have moved to AI-51,
a HAS), the UI component kit, colour *science* (Chevreul harmonies + WCAG
contrast, not just swatches), and machine authoring (25 MCP tools). Parity
work must not trade these away.

**The closure programme** groups the actionable rows into workstreams
(per-row detail in Appendix B):

| WS | Workstream | Closes | Effort | Notes |
|----|-----------|--------|--------|-------|
| W1 | **Planar geometry kernel** — declarative path booleans (Pathfinder ops), path surgery (split-at / cut-along), **offset path** (outward/inward, Bézier-offset approximation), true Live-Paint region fills | AI-04, AI-05, AI-06, AI-17, AI-47 | M–L | Expansion-tier per §A.0: the SDK computes, the document receives plain `path` objects. Highest leverage: one kernel closes five rows |
| W2 | **Stroke, curve & type finesse** — `through()` smooth interpolation (Hobby/Catmull-Rom, §A.2); the **stroke-outline engine**: variable-width profiles, **outline-stroke conversion**, and calligraphic **brush** lowering all share one filled-outline emitter at expansion; scatter/art/pattern brushes = repeat-along-path; pair-kerning beyond `letter_spacing` | AI-09 (S), AI-12, AI-48, AI-49 (M–L shared engine), AI-24 (S) | S–L | AI-12/48/49 are one build in three verdicts: strokes become filled geometry |
| W3 | **Painterly colour** — freeform gradient + gradient mesh ("the single biggest gap") via expansion-tier subdivision shading (Scene3D Gouraud precedent); **shape/colour blend interpolation** (the Blend tool, declaratively: lerp matched anchors + colour at expansion) | AI-27, AI-28 (L), AI-29 (M) | M–L | Low priority; decision: emulate vs accept as the price of being a grammar |
| W4 | **Style & colour richness** — ordered effect stack (M); appearance stack: multiple fill/stroke passes per object, out of the core profile (M); a `recolor()` convenience over token swap + `gradient_map` (S); harmony suggestions as the declarative Color Guide over `sdk.chevreul` (XS–S) | AI-30, AI-32, AI-16, AI-18 | S–M | Profile-gated schema additions where schema changes at all |
| W5 | **Text threading** — named-frame chains (flow region → region) as the declarative threaded text | AI-22 | M | **Operator decision** — today's flow auto-paginates; explicit frame linking is a new contract |
| W6 | **Verdict corrections by documentation** — anchor editing = MCP `workspace` pin/nudge/snap; isolation mode = edit-by-id scoping; the coordinate pen's assistive half = `construct_vectors` + coach; artboards-vs-pages as a design difference; verify/document Scene3D `extrude`/`revolve` + `Material` against AI-40; guides/rulers/snap = exact coordinates + `canon.content_box` layout grids (optional SDK guide helpers) | AI-02, AI-03, AI-08, AI-36, AI-40, AI-50 | XS–S | No schema — document, strengthen evidence, re-verdict where honest |
| W7 | **Visual font identification** (Retype) — a vision-side classifier from rendered glyphs to `list_fonts` families | AI-45 | L | Deferred decision; the only Generative/AI-chapter row with an open build |

**Non-goals, reaffirmed** (6 declared in the matrix, honest limits — parity of
*capability*, not of cursor): freehand pointer input (AI-10; curve *fitting*
via `vectorize_image`/coach is the nearest declarative route, not claimed as
equivalence), type on a path (AI-23 — reversal is an operator decision),
envelope distort (AI-25), perspective grid (AI-37 — coheres with G-2's
non-conformant `perspective`), asset packaging (AI-42 — hermetic single-file
YAML with content-hashed assets makes a Package step moot; **changed from the
v1 disposition**, which had proposed building it), 3D mockup surface-wrap
(AI-46). PSD/EPS/DWG export (AI-41 residual) and CMYK separations (AI-15 →
item 5's deferred ICC hook) stand as before.

**Sequencing.** W6 is immediate (documentation); W1 is the flagship and wants
item 4's golden protection first; W2/W4 are steady S–M increments; W3, W5, W7
are operator-gated decisions. The teardown is re-runnable — re-render the
generator after each workstream and watch the scoreboard move.

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
strong on typographic, i18n, and color **vocabulary**. The defensible residual
work, in order, is **wiring the existing graph-layout algorithms (`sdk.topology`)
into a render-time pass**, **PDF/UA tagged export** (SVG a11y is already partly
emitted), and a **tolerance band + schema URL over the existing golden-render
lock**. The **data layer** and **print color management** are scope decisions
worth making explicit rather than leaving implied. The **geometry /
transformed-spaces / 3D authoring SDK** (item 7, Appendix A) already ships in
`sdk.{geometry,draw,manifold,fields}` — and with **both grammar fixes landed** (G-1
typed structured path segments, schema-checkable and grammar-gated; G-2 `perspective`
marked non-conformant with a validator WARN), item 7 is complete and the only residual
is documentation, so it carries **Low** priority and near-zero format risk. The **Book composition
API** (item 8) is the clearest near-term product/API increment: semantic blocks and
deterministic pagination above the current page primitives, with imported figures
as controlled assets rather than raster-only shortcuts. **Generative content
objects** (item 9) are a genuinely new capability — prompt-to-asset embedded in the
document — but viable *only* if resolved once at a generation pass and pinned, with
PALS's-Law verification; a live render-time model call would forfeit the
determinism (golden locks) and hermeticity the format is built on. Interaction /
animation is lowest priority unless live presentation becomes a goal.

---

## Next minor (drafted as "2.3"; that number shipped as an unrelated pass) — split content from presentation + retarget to any surface (design direction)

> **Status:** DRAFT / design-target for a future minor — *not* a commitment.
> Drafted when HEAD was 2.2.0 and labelled "2.3"; the 2.3.0 that actually
> shipped (2026-07-01) was an unrelated additive improvement pass, so this
> direction now targets **2.4 or later**. Recorded so the architecture moves
> toward it; the split described here remains unbuilt at HEAD.

The 2.x line so far keeps **content and presentation in one closed model**: a
`VisualObject`/`Flowable` carries its own `Style`, `box`, and canvas placement, so
*what a document says* (the data) and *how it looks* are co-mingled on the same node.
2.3 proposes to **separate them**, and to make rendering an explicit **mapping** that
retargets one content tree to many **surfaces** — print, screen, and the social-media
canvases the renderer already enumerates. (The deeper payoff this unlocks — deriving
many audience-specific artifacts from one source — is a 3.0 milestone, below.)

### 2.3-A — Split content from presentation

- A **content model** — the semantic graph (sections, blocks, figures, relations,
  `reading_order`) that says *what* a document is, independent of pixel/point
  geometry or styling.
- A **presentation model** — style, layout, canvas, paint, transforms (today's
  `Style` / `Group.layout` / canvas) that says *how* a given content tree is
  realized for a target.
- The two bind through a **mapping** (below), not through co-located fields. The
  closed model, semver gates, and golden determinism (*the sync guarantee*) must
  survive the split: the content tree stays the source of truth and presentation
  becomes a **resolved view**, the same discipline by which schema/grammar/docs are
  already resolved views of the model.

### 2.3-B — Retarget one content tree to any canvas / surface

- The same content should map to many **surfaces**: social-media formats (Instagram
  story/post, Facebook, LinkedIn, X, YouTube, TikTok, Pinterest), print sizes
  (A4, Letter), and screen — by pairing the content model with a **canvas preset** +
  presentation profile, so a document written once retargets to each, layout re-fit per
  surface rather than re-authored.
- The **canvas-preset surface already ships** as the first instance: HEAD enumerates
  social-media presets (`instagram-story` 1080×1920, `instagram-post`, `facebook-*`,
  `linkedin-*`, `youtube-thumbnail` / `youtube-banner`, `tiktok-video`, `pinterest-pin`, …)
  plus aspect-ratio aliases (`9x16`, `1x1`, `4x5`, `1.91x1`, …), synced across the model
  `PagePreset`, the grammar, the spec, and the renderer's `CanvasResolver` (gated by
  `make check` / `make package-check`). 2.3 makes the *retarget* itself first-class: one
  content tree + a target canvas → the surface-specific artifact.
- Output *formats* (SVG · PDF · LaTeX/TikZ · HTML · raster, via the backend-neutral
  `ScenePainter` port + `Document.targets`) are the orthogonal axis the same mapping
  drives. A surface that cannot represent a feature **degrades explicitly** — never
  silently — and same content + same surface ⇒ same artifact (golden-locked, PALS's Law).

---

## Version 3.0 — derive every artifact from one source (select + filter) (design direction)

> **Status:** DRAFT / design-target for a future **3.0** line, built on the 2.3 split —
> not a commitment; the model, schema, and gates describe 2.2.0 today.

The 2.3 split makes the deeper payoff possible: **one data source derives many
audience-specific artifacts.** The same quarterly results render as the formal
**SEC / investor report** (A4, full tables, compliance register) *and* the **media posts**
(an Instagram story, a LinkedIn card) — derived from the **same numbers** via
**filters / selects**, each selecting the subset its audience needs and retargeting (2.3)
to its surface, never re-keyed by hand.

- A declared **view** — a select / filter over the content graph — bound to a target
  surface + profile produces one audience artifact; many views over one source produce
  the full set (filing, deck, story, post).
- **One source of numbers.** A figure that changes once propagates to every derived
  artifact; the SEC table and the Instagram story can never disagree, because they read
  the same content.
- Deterministic and verifiable (PALS's Law): same source + same view + same surface ⇒
  same artifact (golden-locked). A view that selects an element a surface cannot
  represent **degrades explicitly**, never silently.
- **New surface area vs. 2.3.** 2.3 retargets *one whole document* to many canvases; 3.0
  adds the **selection layer** (which slice of the source each artifact shows) — a
  query / view model over the content graph, not just a canvas swap.

*Effort: XL — a milestone, dependent on 2.3-A.*

### Verifiable projection — the moat (content fidelity, not just determinism)

The determinism bullet above (same source + view + surface ⇒ same artifact) is necessary
but is **not** the differentiator — every templating engine is deterministic. The moat is
the stronger property: the projection is **provably faithful to the source**.

- A value shown in any view is **the same value** as in the source, by construction — a
  view may *select, aggregate, or hide*, but may not *fabricate or alter*.
- The system can **prove** it: every rendered figure carries provenance back to a source
  cell, and a **content-fidelity gate** fails if a view shows a number with no source
  lineage, or one that disagrees with it.

This is PALS's Law applied to **data → view** — the 3.0 analogue of the golden-render
lock, but over *content*, not pixels. It is the reason an agent can be trusted to post
earnings: the Instagram figure *is* the SEC figure, and the build can show its work. BI
suites and headless CMS fan one source to many channels, but none pair that with a typed,
verifiable IR spanning *compliance-grade print and social surfaces* plus a gate proving no
view distorts the source — that intersection is the 3.0 bet.

> **Relation to today's document signing (distinct axes — do not conflate).** The
> shipped provenance metatag (`framegraph/rendering/provenance.py`, status table above)
> proves the **rendered artifact's bytes** were not altered after render — a sha256
> fingerprint over the *output*. 3.0's verifiable projection proves the **content** is
> faithful to its *source* — a value shown traces to a source cell. The first is
> *output* tamper-evidence; the second is *content* fidelity. They are complementary
> instruments toward the same trust story, not the same gate: the metatag is groundwork
> a content-fidelity gate can build on (carry a source-lineage digest alongside the
> render fingerprint), but it does not by itself establish source faithfulness.

### Honest scope — what 3.0 costs

- **It reopens a closed decision.** Item 3 (data layer) is **out of scope** today ("no
  data transforms by design"). 3.0 reverses that *deliberately, at the document level* — a
  content-graph projection, not an in-chart data algebra (which item 3 still bars). Item 3
  explicitly left this open: "revisit only if a single source of truth from data to
  multiple views becomes a product goal."
- **Provenance must reach the leaf.** A real addition to the content model: every value
  carries a source reference that survives selection / aggregation into the artifact.
- **It likely needs the temporal axis.** Quarter-over-quarter comparatives are time
  series, and the IR has **no temporal axis** (`output-space.md` boundary) — a read-only
  data / time binding may be a prerequisite, distinct from animation (non-goal, item 6).

---

# Appendix A — Geometry, Transformed Spaces, and 3D (design proposal, non-normative)

> **Status:** documentation of an existing, complete SDK (both grammar fixes landed)
> (non-normative). This appendix is the design behind roadmap item 7 — and most of
> it **already exists** in `framegraph.sdk.{geometry,draw,manifold,fields}`. The
> TypeScript `@framegraph/*` names below are *illustrative interface sketches*; the
> real, shipping implementation is Python (`framegraph/sdk/geometry.py`, `draw.py`,
> `manifold.py`, `fields.py`) — e.g. `Mat3`/`Mat4`/`Path`/`Vec2`/`Vec3`/`Camera`/
> `quarter_circle_kappa` and `Scene3D.render`. Read this as a spec of what ships,
> not a build proposal; **both grammar fixes have landed** — G-1 (typed structured
> path segments) and G-2 (`perspective` marked non-conformant) — so item 7 is complete
> and the appendix is documentation of shipped work (§A.7). NOTHING HERE SHOULD BE TAKEN FOR GRANTED: statements not backed by a real
> definition (the code, the EBNF) or a citable reference may be invalid. The MATH is stated concretely so it
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
| G-1 ✅ **DONE** | `PathObject.d` was an opaque string the schema could not validate | builds correct `d`; the renderer lowers structured segments to the same path-data string | **landed**: `Path.d` is `Union[str, list[PathSeg]]` — a typed `PathSeg` union (M/L/H/V/C/S/Q/T/A/Z, absolute+relative) and a `PathCommand` alias; the JSON Schema validates command + arity via `prefixItems`; the EBNF carries `PathSegList`/`PathSeg`/`PathCommand` and `check_grammar_sync` enum-gates `PathCommand` across models + EBNF. `d` is the compiled view |
| G-2 ✅ **DONE** | `perspective` was "declared, may not render" — accepted but inert, a trap | refuses to emit 3D; projects to 2D instead (§A.5) | **marked explicitly non-conformant**: `TransformFn` is 2D-only (no 3D functions exist); `perspective` is annotated NON-CONFORMANT in the model + EBNF and the validator now WARNs (`non-conformant-3d`) when it is set, so the trap surfaces at validation instead of silently. Projection-only via the SDK Scene3D is the supported 3D path |
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

---

# Appendix B — Adobe Illustrator parity matrix (granular, 51 features · v3)

> **Status:** the granular evidence base of roadmap item 10 (teardown v3,
> 2026-07-02; supersedes the 44-feature v1 and 46-feature v2). Source:
> `static/examples/illustrator_vs_framegraph.py`; Illustrator surface mined
> from three manuals over doc-ray ("AI 2024 User's Guide" [24], "Master AI
> 2025" [25], "BMG 106: Computer Graphics II" [26]) with sentence-ordinal
> round-trips; FG coverage quoted from the gated capability manifest
> (sha256-pinned; full audit committed at
> `static/examples/illustrator_vs_framegraph.audit.json`). Verdicts: **HAS** direct
> *functional* equivalent · **PARTIAL** narrower/different form · **NONE**
> (`arch` = the declarative model precludes it · `non-goal` = declared scope
> choice) · **REFRAMED** same end by naming/tool-call. `·H/M/L` = evidence
> confidence. Dispositions reference the item-10 workstreams (W1…W7).

## A · Select & edit paths

| ID | Illustrator feature | Verdict | FrameGraph today | Disposition |
|----|--------------------|---------|------------------|-------------|
| AI-01 | Object selection | REFRAMED | name an object by id and act on it | settled — declaration replaces point-and-click |
| AI-02 | Anchor-point editing | PARTIAL ·M | path/bezier/curve points authored as coordinates | **W6**: MCP `workspace` pin/nudge/snap is the declarative Direct Selection — document |
| AI-03 | Isolation mode | PARTIAL ·M | structural nesting (group + layers); no in-place isolated edit | **W6**: edit-by-id scoping is the declarative isolation — document |
| AI-04 | Compound paths / Pathfinder | PARTIAL ·M | path `fill_rule` even-odd + holes; no live Pathfinder ops | **W1**: declarative boolean ops |
| AI-05 | Shape Builder | NONE ·H arch | no boolean shape merge | **W1** |
| AI-06 | Scissors & Knife | NONE ·H arch | no path surgery | **W1**: split-at / cut-along, S once the kernel exists |
| AI-47 | Offset path | NONE ·H maturity | no offset-path operation — deterministic geometry the model could express; unbuilt | **W1**: Bézier-offset approximation in the kernel, M |
| AI-48 | Outline stroke | NONE ·H maturity | no stroke→outline conversion — derivable, not paradigm-precluded | **W2**: the shared filled-outline emitter |

## B · Draw & primitives

| ID | Illustrator feature | Verdict | FrameGraph today | Disposition |
|----|--------------------|---------|------------------|-------------|
| AI-07 | Shape primitives | HAS | rect, ellipse, circle, polygon, line, polyline (17 object types) | settled |
| AI-08 | Pen tool (Bézier) | PARTIAL ·M | bezier / `Path` / `CubicBezier`, authored by coordinate | settled as design — coordinates are the pen; **W6** documents `construct_vectors` + coach as the assistive half |
| AI-09 | Curvature tool | PARTIAL ·M | curve object + `parametric_curve`; no live rubber-band | **W2**: `through()` smooth interpolation (§A.2), S |
| AI-10 | Pencil / freehand | NONE ·H non-goal | no freehand pointer input (declarative only) | **non-goal** reaffirmed; nearest declarative route is curve *fitting* (`vectorize_image`, coach) — noted, not claimed |
| AI-11 | Stroke controls | HAS | `stroke_style` width/dasharray/cap/join + connector markers | settled |
| AI-12 | Variable-width (Width Tool) | NONE ·H arch | stroke width is uniform — no width profile | **W2**: width profiles lowered to filled outline paths at expansion, M |
| AI-49 | Brushes (calligraphic / scatter / art / pattern / blob) | NONE ·H maturity | no brush engine — brush-along-path is declarable in principle; unbuilt | **W2**: calligraphic = width profiles; scatter/art/pattern = repeat-along-path at expansion, M–L |

## C · Colour system

| ID | Illustrator feature | Verdict | FrameGraph today | Disposition |
|----|--------------------|---------|------------------|-------------|
| AI-13 | Colour picker & swatches | HAS | hex/rgba values + `defs.tokens.colors` named palette | settled |
| AI-14 | Global colours | HAS | named tokens are global by construction | settled |
| AI-15 | CMYK / RGB modes | PARTIAL ·H | RGB/hex only — no CMYK, no separations | stays behind **item 5**'s deferred ICC output-intent hook |
| AI-16 | Recolor Artwork | PARTIAL ·M | `gradient_map` + `closed_palette` + token swap (declarative recolor) | **W4**: a `recolor()` convenience over the existing pieces, S |
| AI-17 | Live Paint | PARTIAL ·M | region toolkit: `select_in` / `place_region` / `region_grade` | **W1**: planar arrangement gives true fill-any-bounded-region |
| AI-18 | Colour science | PARTIAL ·M | Chevreul harmony + WCAG contrast tools — not a Color-Guide workflow | **W4**: harmony suggestions over `sdk.chevreul` as the declarative Color Guide, XS–S |
| AI-19 | Patterns | HAS | `pattern`, `grid_pattern`, `dots`, `hatch_fill` fills | settled |

## D · Type & text

| ID | Illustrator feature | Verdict | FrameGraph today | Disposition |
|----|--------------------|---------|------------------|-------------|
| AI-20 | Point & area type | HAS | text objects + flow paragraph/heading/list | settled |
| AI-21 | Character & paragraph | HAS | font_family/size/weight + paragraph flow (106 style props) | settled |
| AI-22 | Threaded text | PARTIAL ·M | flow auto-pagination continues overset; no interactive frame linking | **W5**: named-frame chains (region→region flow) — operator decision, M |
| AI-23 | Type on a path | NONE ·H non-goal | explicit scope limit | **non-goal** as declared; reversal is an operator decision (expansion-tier glyph placement, M, remains the lever) |
| AI-24 | Kerning & tracking | PARTIAL ·M | letter_spacing / line_height; no pair-kerning table | **W2**: real-metrics pair kerning (fontTools) or explicit kern pairs, S |
| AI-25 | Envelope distort | NONE ·H non-goal | text stays on its baseline grid | **non-goal**, reaffirmed |

## E · Gradient · effect · style

| ID | Illustrator feature | Verdict | FrameGraph today | Disposition |
|----|--------------------|---------|------------------|-------------|
| AI-26 | Linear / radial gradient | HAS | `linear_gradient` / `radial_gradient` paint | settled |
| AI-27 | Freeform gradient | NONE ·H arch | no freeform gradient | **W3**: subdivision-shading emulation, L, low priority — decision |
| AI-28 | Gradient mesh | NONE ·H arch | the single biggest gap | **W3**: same route (Scene3D Gouraud precedent) or accept — decision |
| AI-29 | Blend tool | NONE ·H arch | no shape-to-shape blend / interpolation | **W3**: declarative blend — lerp matched anchors + colour at expansion, M |
| AI-30 | Live effects | PARTIAL ·M | effects set: glow / neon / shadow / soft_shadow / hatch | **W4**: ordered effect stack per object, M |
| AI-31 | Graphic styles | HAS | named styles / text_styles / stroke_styles tokens | settled |
| AI-32 | Appearance stack | PARTIAL ·M | one style per object; no multi-fill stack | **W4**: multiple fill/stroke passes, out of the core profile, M |

## F · Layer · transform · page

| ID | Illustrator feature | Verdict | FrameGraph today | Disposition |
|----|--------------------|---------|------------------|-------------|
| AI-33 | Layers | HAS | ordered layers per page, z-index | settled |
| AI-34 | Transform tools | HAS | transform: Mat3 rotate / scale / translate / shear | settled |
| AI-35 | Align & distribute | HAS | layout groups: row / column / grid, align | settled |
| AI-36 | Artboards | PARTIAL ·M | multi-page flow doc (TOC, bibliography); no free spatial canvas | **W6**: pages-not-canvas is a design difference — document |
| AI-37 | Perspective grid | NONE ·H non-goal | flat page space | **non-goal** — coheres with G-2's non-conformant `perspective` |
| AI-50 | Guides, rulers & snap | PARTIAL ·M | `grid_pattern` + exact coordinates; no interactive guides/snap | **W6**: exact coordinates + `canon.content_box` grids are the declarative guides — document; optional SDK guide helpers, XS–S |

## G · Image · 3D · output

| ID | Illustrator feature | Verdict | FrameGraph today | Disposition |
|----|--------------------|---------|------------------|-------------|
| AI-38 | Embed / link raster | HAS | image object: embedded or src-referenced | settled |
| AI-39 | Image trace | REFRAMED ·H | `vectorize_image` MCP tool call | settled — same raster→vector end, declarative road |
| AI-40 | 3D & Materials | PARTIAL ·M | `Scene3D` + `Material` + `Camera` scene — not vector extrusion | **W6**: verify/document `extrude`/`revolve` + materials against this row, XS–S |
| AI-41 | Export formats | PARTIAL ·M | SVG / PNG / PDF / LaTeX (6 renderers); no PSD / EPS / DWG | proprietary/legacy targets stay **non-goals** |
| AI-42 | Package | NONE ·H non-goal | no asset-collection packaging step | **non-goal** (v2 change from v1's build proposal): hermetic single-file YAML + content-hashed assets make packaging moot |
| AI-51 | Graph tool (bar / pie / line charts) | HAS | `Chart` / `sparkline` / `function_plot` / `polar_plot` / `kpi` — data-bound | settled — and note the boundary: item 3's data *transforms* remain out of scope; these are data-bound marks |

## H · Generative / AI (Illustrator 2024)

| ID | Illustrator feature | Verdict | FrameGraph today | Disposition |
|----|--------------------|---------|------------------|-------------|
| AI-43 | Text to Vector Graphic | REFRAMED ·L | `propose_from_image` / `run_sdk_code` author→render loop | settled — the loop is the generative surface; item 9 is the pinned-object evolution |
| AI-44 | Generative Recolor | REFRAMED ·L | swap a palette token / `gradient_map`, re-render | settled; W4's `recolor()` makes it one call |
| AI-45 | Retype (font identification) | NONE ·H arch | `list_fonts` resolves families; no visual font ID | **W7**: vision-side font classifier, L — deferred decision |
| AI-46 | Mockup (3D surface wrap) | NONE ·H non-goal | no surface-wrap of art onto an object | **non-goal**, reaffirmed |

*End of Appendix B (v3). Re-run the teardown generator after each workstream
lands and watch the scoreboard move; the matrix is evidence, not aspiration.
Adobe and Adobe Illustrator are trademarks of Adobe Inc.; this is an
independent comparison, not affiliated with or endorsed by Adobe.*
\n