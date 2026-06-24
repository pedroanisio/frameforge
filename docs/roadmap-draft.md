---
title: FrameGraph v2 — Roadmap (draft)
version: 2.2.0
status: DRAFT / design-target — not commitments
date: 2026-06-22
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
  the grammar fixes G-1 (landed) and G-2 (open); the TypeScript `@framegraph/*` names in it are
  illustrative sketches of the shipping Python API, and every formula's sign
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
    that closes it, and a proposed fix. Items 1, 2, and 4 are **partly built
    already** — each now states the *residual* gap after re-grounding against the
    SDK and renderer (see the Verification-status note); items 3 and 5 are **scope
    decisions worth making explicit** rather than gaps; item 6 is conditional on a
    live-presentation goal; item 7's geometry/3D SDK **already ships** (Appendix A
    documents it; G-1 landed, only G-2 remains); item 8 is an additive
    book-composition API surface informed by the permissive book corpus inspection;
    item 9 is a generative content object (prompt → image / block) resolved **once
    at build and pinned**, carrying a high determinism / trust risk that the design
    must contain.
    (Items keep their original IDs; sections run in priority order, so the IDs
    appear out of sequence.)

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
    states the *residual* gap, with file evidence.

## Ground-truth status (audited 2026-06-24)

> **This roadmap (dated 2026-06-22) is substantially stale.** A line-by-line audit
> against the live tree shows most "gaps" are already built. The gap analyses below
> are kept as design context, but the *status* is:

| # | Item | Roadmap said | TRUE state (audited) | Evidence / what remains |
|---|------|--------------|----------------------|-------------------------|
| 4 | Conformance + golden render | gap | ✅ **DONE** | `tooling/render_golden.py`, `tests/golden/oracle.lock.json` (SHA-256 lock, CI-gated); schema `$id` resolvable. |
| 2 | Accessibility / tagged export | gap | ✅ **SVG done**, PDF/UA open | `svg.py` a11y_wrap (decorative/role/alt/actual_text), root lang/title/desc, `_render_page_body_in_reading_order`, `tooling/check_accessibility.py`; tests. PDF/UA awaits a PDF backend. |
| 7 | Geometry / 3D authoring SDK | additive gap | ✅ **done** | `sdk/geometry.py` (A.1/A.2), `sdk/manifold.py`+Scene3D (A.5); **A.3** curve sampling, **A.4** structured log-base/pow-exp scales, **A.6** orthographic `multiview`, and **G-1** typed structured path segments (model `PathSeg`/`PathCommand` + EBNF `PathSegList`, JSON Schema `prefixItems`, enum-gated by `check_grammar_sync`) all landed. Only **G-2** (3D "declared, may not render") and minor scale extras (categorical/time) remain. |
| 1 | Diagram auto-layout | gap | ✅ **author-time done** | `sdk/topology.py`: 5 algorithms **plus `auto_layout`/`layout_kind`** — a graph now lays itself out from its declared edges (algorithm inferred: grid/radial/layered/spring), and `Graph.render()` auto-layouts by default. Remaining (optional): a *render-time* pass over `mode: page` diagram groups, or an ELK binding. |
| 3 | Data layer for charts | out of scope | ✅ decision holds | `sdk/chart.py` is a lowering helper, no data transforms (by design). |
| 5 | Print colour (ICC/CMYK) | deferred | ✅ decision holds | no ICC/CMYK code; hook not yet reserved. |
| 6 | Interaction / animation | low | ✅ decision holds | no animation primitives. |

> **Net (updated 2026-06-24):** item #7 (geometry SDK) is now **complete** (A.1–A.6
> + G-1), and #1 has author-time automatic layout. **No item has an open
> author-facing gap.** What remains is all deeper integration or externally gated:
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
| 4 | Conformance suite + reference-renderer semantics | **Medium** | Golden-lock harness exists → tolerance diff + schema URL remain |
| 3 | Data layer for charts | **Medium** | Scope decision → out of scope (provisional) |
| 5 | Print color management (ICC / CMYK) | **Medium** | Scope decision → deferred (provisional) |
| 7 | Geometry / transformed spaces / 3D authoring SDK | **Low** | SDK ships + G-1 landed → 1 grammar fix (G-2) remains |
| 8 | Book composition API | **Medium-High** | Additive product/API surface |
| 9 | Generative content objects (prompt → image / content) | **Medium** | Additive object + generation tier; high determinism / trust risk |
| 6 | Interaction / animation for presented decks | **Low** | Conditional on goal |

> Net ordering (most defensible first): wire the existing graph-layout engine into
> a render pass → finish accessible export (PDF/UA) → add a tolerance band over the
> existing golden lock. The data layer and print color are scope choices worth
> stating outright rather than leaving implied. The geometry / 3D SDK (item 7)
> **already ships** (`sdk.{geometry,draw,manifold,fields}`) — so it is lowest-risk
> and now **Low** priority: with G-1 landed, the residual is documentation plus one
> grammar fix (G-2), not a build.

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
   reading-order DOM ordering, `decorative` → `aria-hidden`) against the existing
   proxy, then add full PDF/UA tagging once a tagging PDF backend exists (today's
   PDF is untagged Chromium print). *Effort: S (finish SVG) → L (PDF/UA).*
2. **Item 4 — golden-render harness.** Pin the `b1/` fixtures to reference renders
   with an explicit tolerance before the big feature, so item 1 is regression-safe.
   *Effort: M. Enabler.*
3. **Item 1 — diagram auto-layout.** The flagship capability, now under golden-test
   protection: an ELK-backed layout tier for `mode: page` diagram groups keyed off
   the semantic graph, with absolute positioning as the override. *Effort: XL;
   depends on step 2.*
4. **Item 7 — geometry / 3D: document existing SDK + the remaining grammar fix.**
   The authoring math already ships in `sdk.{geometry,draw,manifold,fields}`, and
   **G-1 (typed structured path segments) has landed** — model `PathSeg`/`PathCommand`,
   EBNF `PathSegList`, JSON-Schema `prefixItems`, enum-gated by `grammar-check`. The
   residual work is documentation (Appendix A) plus G-2 (close the 3D "declared, may
   not render" trap). *Effort: S; parallelizable.*
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
    ([framegraph/rendering/domain/services/layout_engine.py](https://github.com/pedroanisio/frameforge/blob/main/framegraph/rendering/domain/services/layout_engine.py))
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

**Gap (reframed — a golden-lock harness exists; tolerance + schema URL remain).**
The format's stance — treat each construct as a proposal to verify against the
renderer — leaves "valid" underdetermined. FrameGraph already has the schema, the
models, the `b1/` authoritative fixtures as an oracle, the `--check-overflow`
text-fit gate, **and a working golden-render lock**: `tests/test_golden_render.py`
builds an oracle manifest, pins each fixture's per-page render to a SHA-256 lock,
and diffs current-vs-locked (detecting changed pages and page-count changes). What
it does *not* have is a **tolerance band** — the lock is exact-hash, so any
sub-pixel / font / AA change trips it — nor a **resolvable, versioned schema URL**
documents can self-declare against.

**Comparators.** The mature comparators close this loop. Vega-Lite publishes a
versioned JSON Schema and an example gallery, and its CI recompiles every example
to reference Vega specs and SVGs that serve as regression tests, with an explicit
backward-compatibility commitment.

**Fix (narrower — the harness exists).** Add a **tolerance mode** to the existing
`test_golden_render.py` lock (a perceptual / pixel-distance diff with an explicit
band, alongside the exact-hash mode) so cosmetically-irrelevant render changes do
not produce false failures, and version the schema at a **resolvable URL** the way
Vega-Lite does so documents can self-declare conformance. The corpus and diff
machinery are already in place.

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

### 7. Geometry, transformed spaces, and 3D authoring — the SDK already exists; one grammar fix remains

**Gap (reframed — the authoring layer already exists; G-1 has landed and only G-2
remains).** The grammar can *represent* arbitrary 2D geometry — `PathObject.d` (SVG
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
The genuine residual is one grammar-level item: **G-2** — the style module marks 3D
transforms and `perspective` as "declared, may not render"
(`grammar/framegraph-v2-style.ebnf` line 262), so emitting them is a trap. The SDK's
answer to G-2 is already the right one: project to 2D and emit primitives the
renderer draws.

**Comparator.** A 2D&3D vector language (Asymptote) computes geometry and 3D and
*projects to 2D vector output* rather than shipping a 3D scene to the page; D3's
scales (`linear` / `log` / `pow`) model the data→page frame mapping. The lesson is
that the geometry kernel belongs in the authoring tool, not the page renderer.

**Fix (documentation + one remaining grammar fix, not a build).** The author-time
math already ships in `framegraph.sdk.{geometry,draw,manifold,fields}` and **emits
only primitives the grammar has** — `path`, `polyline`, `group`, `matrix` —
resolving curves and 3D→2D projection at expansion time and pinning the result with
the hash contract. **G-1 is done**: a typed `list[PathSeg]` now sits alongside the
`d` string so paths are schema-checkable, landed in **both** the models and the EBNF
(`check_grammar_sync` enum-gates the `PathCommand` vocabulary across the two). The
remaining work is (a) **document** that SDK (Appendix A is effectively its spec) and
(b) ship **G-2**, explicitly marking the 3D transforms non-conformant (or specifying
a 3D renderer) so the "declared, may not render" trap is closed. Priority stays
**Low**: no new capability, one small grammar delta. Full design, math, and
grammar-fix table in **Appendix A** — now read as documentation of the existing SDK,
not a build proposal.

### 8. Book composition API — semantic layer above pages

**Gap.** The SDK can author pages and can now place controlled imported figures,
but there is no first-class surface for expressing a book as chapters, sections,
paragraphs, figures, tables, callouts, examples, formulas, and references before
pagination. Existing examples therefore hand-code book-like layout directly with
page coordinates or local helper classes, which proves the product shape but does
not give downstream tooling a stable API for import, restyling, pagination, or
book-wide numbering.

**Corpus evidence (2026-06-24).** The permissively licensed corpus inspection
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
`sdk.{geometry,draw,manifold,fields}` — and with **G-1 landed** (typed structured
path segments, schema-checkable and grammar-gated), what remains is documenting it
and one small grammar fix (G-2), so it carries **Low** priority and near-zero format
risk. The **Book composition
API** (item 8) is the clearest near-term product/API increment: semantic blocks and
deterministic pagination above the current page primitives, with imported figures
as controlled assets rather than raster-only shortcuts. **Generative content
objects** (item 9) are a genuinely new capability — prompt-to-asset embedded in the
document — but viable *only* if resolved once at a generation pass and pinned, with
PALS's-Law verification; a live render-time model call would forfeit the
determinism (golden locks) and hermeticity the format is built on. Interaction /
animation is lowest priority unless live presentation becomes a goal.

---

## Version 2.3 — split content from presentation + retarget to any surface (design direction)

> **Status:** DRAFT / design-target for a future **2.3** line — *not* a 2.2.0
> commitment. Recorded so the architecture moves toward it; the model, schema, and
> gates still describe 2.2.0 today.

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

> **Status:** documentation of an existing SDK + one remaining grammar fix
> (non-normative). This appendix is the design behind roadmap item 7 — and most of
> it **already exists** in `framegraph.sdk.{geometry,draw,manifold,fields}`. The
> TypeScript `@framegraph/*` names below are *illustrative interface sketches*; the
> real, shipping implementation is Python (`framegraph/sdk/geometry.py`, `draw.py`,
> `manifold.py`, `fields.py`) — e.g. `Mat3`/`Mat4`/`Path`/`Vec2`/`Vec3`/`Camera`/
> `quarter_circle_kappa` and `Scene3D.render`. Read this as a spec of what ships,
> not a build proposal; **G-1 (typed structured path segments) has landed**, so the
> only genuinely-open item is grammar fix G-2 (§A.7). NOTHING HERE SHOULD BE TAKEN FOR GRANTED: statements not backed by a real
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
