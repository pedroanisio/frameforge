---
title: "FrameGraph vs the classical CG canon — strategic gap assessment & backlog"
status: APPROVED 2026-07-04 (operator) — F1 deferred + operator-approval-gated; backlog (§9) merged into docs/roadmap.md
date: "2026-07-04"
disclaimer:
  notice: >-
    No statement here should be taken for granted. Codebase claims cite file:line at
    repo HEAD 2.4.1; domain claims cite the reference corpus (¶ = sentence ordinal in
    doc 5f2e8322). Items touching modern CG (GPU/shaders/PBR/texture/ray tracing) are
    FLAGGED BRIDGES — beyond the ~1987 corpus — and marked as such per the operator's
    "corpus + flagged bridges" directive.
  generated_by: "Claude Opus 4.8 via Claude Code"
  method: >-
    Domain reference = the GraphQL knowledge corpus (kb v1.4.0, 91 docs, re-verified
    2026-07-04). Computational-CG source: Harrington, "Computer Graphics: A Programming
    Approach", 2nd ed. 1987 (doc 5f2e8322), whose 11-chapter pipeline (preface ¶21–39,
    ¶43–45) is the authoritative model. Codebase = frameforge HEAD 2.4.1.
supersedes_scope_of: docs/proposals/cg-canon-3d-alignment.md   # that doc is the detailed spec for backlog item B2
---

# FrameGraph vs the classical CG canon — strategic gap assessment

## 1. Executive summary

Measured against the classical computer-graphics pipeline (Harrington 1987, the corpus's
one deep computational source), **FrameGraph already implements most of the canon** — and,
in several places, its architecture *is* the canon: the Document IR is Harrington's
**"display file / metafile"** (¶23), the Layer/Object graph is his **"segments"** (¶44),
and the object-modelled-in-world-space heritage (¶43, GKS/PHIGS ¶45) is exactly FrameGraph's
retained model. Transforms, curves, 2D clipping (delegated), and — notably — **colour**
(the `chevreul`/`canon` modules implement the same Chevreul sources the corpus holds) are
strong and aligned.

The **strategic gaps cluster in two places**:

1. **The 3D leg of the pipeline is incomplete and partly incorrect.** Harrington pairs
   projection with **3-D clipping** (¶34) and hidden-surface removal with **back-face
   removal + a priority sort** (¶36); FrameGraph's `Scene3D` projects without clipping
   (crashes on `w≈0`, inverts on `w<0`) and sorts by average-z with no back-face cull and
   no z-buffer. *(Detailed spec: `cg-canon-3d-alignment.md` = backlog item **B2**.)*
2. **There is no formal viewing-pipeline abstraction.** The canon prescribes a named
   **world → normalized-device → viewport** coordinate pipeline (¶43); FrameGraph handles
   coordinates ad-hoc via `canvas`/`box`/`coordinate_mode`. A first-class viewing pipeline
   (**B1**) is the abstraction that makes B2 *correct by construction* and unifies 2D and 3D.

With the **true-3D scope block lifted** (2026-07-04), these stop being "a minimal 3D toy we
tolerate" and become the **foundation of a coherent strategic direction**: B1 (viewing
pipeline) → B2 (3D correctness) → **B3 (a real 3D scene graph)**, with smaller canon-grounded
additions (fractals **B4**, curved surfaces **B5**, shading completion **B6**). Two canon
topics are **out of fit** for a vector-document system and are parked as flagged bridges:
**ray tracing / global illumination (F1)** — **deferred and gated to explicit operator
approval** — and **texture mapping (F2)**, deferred behind B3.

Highest-value, lowest-risk first moves: **B1 + B2** (small, correctness-first, unblock everything downstream).

---

## 2. Source-grounded domain understanding — the canonical pipeline

Harrington's preface enumerates the pipeline as an 11-chapter progression (the authoritative
domain model). Verbatim stage list, with the coordinate/segment framing from ¶43–45:

| Ch | Stage | ¶ |
|---|---|---|
| 1 | Analytic geometry + **vector generation** (line drawing) | ¶21 |
| 2 | Line/**character drawing**; the **display file / metafile** (device interface) | ¶22–23 |
| 3 | **Polygon surfaces** + the **rasterization** problem | ¶24 |
| 4 | **Transformations** (translate / scale / rotate) | ¶25 |
| 5 | **Segmentation + visibility / attributes** | ¶26 |
| 6 | **Windowing + clipping** (completes 2D) | ¶28 |
| 7 | **Interactive techniques** (input-hardware interface) | ¶31 |
| 8 | **3-D**: geometry, **viewing transforms**, parallel + perspective **projection**, **3-D clipping** | ¶33–34 |
| 9 | **Hidden-surface / line removal** — back-face removal **+** priority (painter's) sort | ¶35–36 |
| 10 | **Shading and colour** | ¶37 |
| 11 | **Curved lines & surfaces** — arcs, interpolation, **fractals** | ¶38–39 |

Cross-cutting: *"Objects are modelled in **world-coordinate space**, and views… transformed to
**normalized device coordinates**"* (¶43); primitives group into **segments** (¶44); the model
follows the **GKS / PHIGS / CGI / CGM** retained-graphics standards (¶45).

**Corpus boundary (flagged bridges).** Pre-1987: OpenGL/shader = 0 corpus-wide; texture
mapping = 1 citation; "GPU" only in ML books; the canon says "scan conversion", not
"rasterization". Anything modern is a **bridge**, marked below.

---

## 3. Codebase assessment (FrameGraph as a CG system)

- **Architecture.** Geometry kernel (`sdk/geometry.py`: `Vec2/3`, `Mat3`, `Mat4`, `Camera`,
  `CubicBezier`, `Path`), modelling/scene (`sdk/draw.py::Scene3D`), booleans/topology
  (`planar`, `manifold`, `topology`, `lattices`, `fields`), hexagonal renderer (SVG/TikZ
  painters, HTML/PDF backends), colour craft (`chevreul`, `canon`), stroke-outline engine (`outline`).
- **Data model.** Retained `Document → Page → Layer → Object` — Harrington's display file (¶23)
  + segments (¶44). 3D lowers to it: `Scene3D.render` projects to 2D closed polylines.
- **Strengths (canon-aligned — *not* gaps).** Transforms (Ch4 → `Mat3`/`Mat4`); segments &
  visibility (Ch5 → Layer/Object + `z`/`opacity`/`visibility`); curves (Ch11 → `CubicBezier`,
  `catmull_rom`, `arc_to`, `parametric_surface`); **colour (Ch10 → Chevreul module,** implementing
  corpus sources); windowing/clipping (Ch6, 2D → SVG `clipPath` + `planar` booleans); the
  display-file/metafile heritage (¶23) and standards lineage (¶45).
- **Delegations (design choices, not gaps).** Vector generation / rasterization / antialiasing
  (Ch1/3) → SVG → Chromium/Cairo. FrameGraph is vector-first; the raster chapters live downstream.
- **Weaknesses (→ §4).** The 3D leg (Ch8–9) and the absence of a formal viewing pipeline (¶43).

---

## 4. Gap analysis — canon stage → FrameGraph status

| Canon stage | FrameGraph status | Verdict |
|---|---|---|
| Ch1 vector generation | delegated (SVG) | ✅ by design |
| Ch2 display file / metafile | **the Document IR** | ✅ strong alignment |
| Ch3 polygon + rasterization | polygons ✓; raster delegated | ✅ by design |
| Ch4 transformations | `Mat3`/`Mat4` | ✅ |
| Ch5 segments + attributes | Layer/Object + z/opacity/visibility | ✅ strong |
| Ch6 windowing + clipping (2D) | SVG clipPath + planar booleans; **window→viewport ad-hoc** | ◐ partial (see **B1**) |
| Ch7 interactive techniques | absent (static IR) | — separate axis (SVG.js-gap; *not* a CG-canon build here) |
| Ch8 3D geometry/viewing/projection/**clip** | transforms+projection ✓; **3-D clipping absent** | ○ **gap (B1/B2)** |
| Ch9 hidden-surface (back-face + priority) | avg-z sort only; **no back-face, no z-buffer** | ○ **gap (B2)** |
| Ch10 shading + colour | shading Lambert/Gouraud (default off); **colour strong** | ◐ shading (**B6**) / ✅ colour |
| Ch11 curves + surfaces + **fractals** | curves ✓, tessellated surfaces ✓; **no Bézier/B-spline patch, no fractal generator** | ◐ (**B4/B5**) |
| ¶43 world → NDC → viewport | ad-hoc canvas/box | ○ **gap (B1)** — no named pipeline |

**Strategic gaps, fit-ranked** (fit = alignment with FrameGraph's vector-first, verifiable,
document-IR nature):

- **Tier 1 (high fit / high value / unblocked):** **B1** viewing pipeline (¶43, Ch6/8); **B2**
  3D correctness — clipping + back-face + depth (Ch8–9).
- **Tier 2 (strategic direction, now unblocked):** **B3** true 3D scene graph (Ch8–11 foundation);
  **B4** fractal/procedural generator (¶39); **B5** curved-surface patches (Ch11); **B6** shading
  completion (Ch10).
- **Tier 3 (flagged bridges — deferred):** **F1** ray tracing / global illumination (canon has it,
  but FrameGraph is not a physically-based renderer — *out of fit*; **deferred and gated to explicit
  operator approval**); **F2** texture mapping (1 corpus citation; **deferred behind B3**).
- **Calibration (NOT gaps):** own scan-conversion/rasterization (delegated by design); interactive
  techniques Ch7 (a different axis — the static-IR/event question, tracked separately).

---

## 5. Proposed improvements (backlog items)

### B1 — Formal viewing pipeline: world → NDC → viewport
- **Problem.** Coordinate handling is ad-hoc; 3D projection and 2D placement don't share a
  rigorous, named pipeline, so correctness (clipping, aspect, fit) is re-derived per call site.
- **Evidence.** `Scene3D.render` hand-rolls fit/scale/offset ([draw.py:192–207](../../src/framegraph/sdk/draw.py#L192)); no window→viewport transform in `geometry.py`.
- **GraphQL support.** ¶43 "world-coordinate space… normalized device coordinates"; ¶28 windowing/clipping.
- **Change.** A small `ViewingPipeline` (world → view → projection → **clip** → NDC → viewport)
  in `sdk/geometry.py`, consumed by `Scene3D` and available to 2D. Names the stages B2 needs.
- **Benefit.** Makes B2 correct-by-construction; unifies 2D/3D; removes duplicated fit math.
- **Complexity.** **M**. Pure Python, additive.
- **Risks.** Must reproduce current `Scene3D` output when no clipping triggers (golden-pinned).
- **Validation.** Golden parity on existing 3D examples; unit tests on window→viewport aspect/fit.

### B2 — 3D pipeline correctness (clipping + back-face + depth)
- **Problem / Evidence / GraphQL / Change / Complexity / Risks / Validation:** fully specified in
  **`docs/proposals/cg-canon-3d-alignment.md`** (near-plane clipping, robust `Mat4.project`,
  back-face removal, depth-strategy option). Grounded in ¶34/36/3670/3713 and
  `draw.py:183/205`, `geometry.py:207`. **Complexity S–M**; correctness-first; defaults preserve output.

### B3 — True 3D scene graph (the direction the lifted block permits)
- **Problem.** `Scene3D` is a flat face list projected once; no nodes/instancing/hierarchy — so
  no reusable 3D assets, no per-node transforms, no scene composition.
- **Evidence.** `Scene3D.faces: list[...]` ([draw.py:95](../../src/framegraph/sdk/draw.py#L95)); `Scene3D` docstring "Minimal 3D scene."
- **GraphQL support.** Ch8–11 (the full 3D pipeline) + ¶43–45 (world-space objects, segments, PHIGS
  hierarchy). **Bridge note:** modern comparator is three.js; the *math* is all in-corpus.
- **Change.** A node hierarchy (transform per node, instancing, grouping) lowering through B1+B2;
  keep 2D-projection output as the default target (vector-first) with the raster path optional.
- **Benefit.** Reusable 3D authoring; the strategic payoff of lifting the block.
- **Complexity.** **L**. Gated on B1+B2.
- **Risks.** Scope; must not compromise the verifiable static IR. Design ADR required first.
- **Validation.** A composed multi-node scene golden; instancing correctness fixtures.

### B4 — Fractal / procedural generator (canon Ch11, ¶39)
- **Problem.** No first-class fractal/self-similar generator, though `manifold`/`lattices`/`fields`
  provide adjacent procedural geometry.
- **Evidence.** `sdk/manifold.py`, `sdk/lattices.py` exist; no fractal module.
- **GraphQL support.** ¶39 "arc generations, interpolations, and fractals are covered."
- **Change.** A small `sdk/fractal.py` (L-systems / IFS / recursive subdivision) emitting paths/polylines.
- **Benefit.** Vector-native, high-visual-payoff, corpus-grounded; strong demo/skill fit.
- **Complexity.** **S–M**. Additive, pure geometry.
- **Validation.** Golden fixtures per generator; determinism (seeded).

### B5 — Curved-surface patches (canon Ch11)
- **Problem.** 3D surfaces are tessellated quads (`parametric_surface`); no Bézier/B-spline patch.
- **Evidence.** [draw.py:108–130](../../src/framegraph/sdk/draw.py#L108).
- **GraphQL support.** Ch11 curved surfaces.
- **Change.** Bézier/B-spline patch primitive with adaptive tessellation, lowering through B1/B2.
- **Complexity.** **M**. Gated on B2. **Priority Low** until B3.
- **Validation.** Patch-vs-reference silhouette goldens.

### B6 — Shading model completion (canon Ch10)
- **Problem.** Shading is Lambert/Gouraud, default **off**; no flat default, no specular/Phong.
- **Evidence.** [draw.py:170–182](../../src/framegraph/sdk/draw.py#L170).
- **GraphQL support.** Ch10 shading & colour.
- **Change.** Add `flat` (sane default for closed meshes) + optional Phong/specular term.
- **Complexity.** **S**. **Bridge note:** texture-modulated shading is F2 (deferred).
- **Validation.** Shaded/unshaded and flat/gouraud golden pairs.

### F1 — Ray tracing / global illumination — **DEFER, operator-approval-gated (flagged bridge / out of fit)**
- The canon covers it (ray tracing + shadows), but it is inherently **per-fragment raster**, against
  FrameGraph's vector-first, verifiable-IR design — building it would fork the renderer's identity for
  little document-graphics value. **Operator decision (2026-07-04): deferred, not declined — kept in the
  backlog but gated so it can only ever be pulled on explicit operator approval** (never auto-scheduled,
  never pulled as a dependency of another item).

### F2 — Texture mapping — **DEFER (flagged bridge)**
- 1 corpus citation; only meaningful once B3 (true 3D) exists and only via the raster path. **Park behind B3.**

---

## 6. Implementation order

**Phase 0 — safety, tests, baseline docs.** Land the B2 failure-case goldens (near-plane crash,
behind-camera inversion, interpenetration) RED against `main`; add the "canon stage → FrameGraph
status" map (this §4) to Appendix A. *Exit:* fixtures reproduce every §4 defect; doc-sync passes.

**Phase 1 — foundational correctness (B1 + B2).** Viewing pipeline abstraction, then robust
projection + near-plane clip + back-face + depth on top of it. *Exit:* B2 fixtures GREEN, all
existing 3D goldens unchanged (defaults preserve output).

**Phase 2 — strategic direction (B3).** True 3D scene graph on the now-correct foundation; write
the design ADR first (pins the verifiable-IR contract). *Exit:* composed-scene + instancing goldens
pass; the static-IR hashing contract is provably intact.

**Phase 3 — canon completeness (B4 fractals, B5 surfaces, B6 shading).** Additive, independently
useful, vector-native. *Exit:* per-generator goldens; capability manifest updated.

**Phase 4 — optimization & observability.** 3D render diagnostics (faces culled/clipped/split,
degenerate-`w` drops); optional raster paths (F2 texture, any z-buffer mode) behind availability
detection. *Exit:* diagnostics surface in `run_sdk_code`; raster paths degrade gracefully.

*Sequencing rationale:* the viewing pipeline (B1) and correctness (B2) must precede the scene graph
(B3) — you cannot build reusable 3D on a projector that crashes behind the camera. Completeness
items (Phase 3) are independent and can interleave. Optimization is last so it never masks a
correctness bug.

---

## 7. Benefits

- **Domain alignment.** FrameGraph comes to implement the canonical pipeline *as named stages*
  (world→NDC→viewport→clip→project→cull→depth→shade), matching Harrington and the GKS/PHIGS
  lineage the roadmap already gestures at — with a truthful stage map in Appendix A.
- **Correctness.** Eliminates the `w≈0` crash and behind-camera inversion; makes `Camera.orbit()`
  animation and AI-authored 3D trustworthy in a golden-hash-gated pipeline.
- **Strategic payoff.** Turns the lifted true-3D block into a sequenced, buildable direction (B3)
  on a correct foundation, instead of an open-ended aspiration.
- **Extensibility & agent-readiness.** B1 gives clean coordinate seams; B4–B6 are vector-native,
  demo-friendly, skill-friendly additions; diagnostics make 3D failures observable.
- **Cost discipline.** B1/B2 are S–M and additive with output-preserving defaults; the expensive,
  out-of-fit item (ray tracing) is explicitly deferred and operator-approval-gated, not silently scheduled.

---

## 8. Risks and open questions

- **Fit boundary (F1/F2) — decided 2026-07-04.** Ray tracing (F1) is **deferred and gated to explicit
  operator approval** (out of fit for a vector-doc system, but kept in the backlog, not declined);
  texture (F2) is deferred behind B3. The remaining tension — whether a raster render identity is ever
  acceptable (same question as B2's `zbuffer` option) — is what any future F1 pull must resolve first.
- **Sequencing.** B1 (viewing pipeline) before B2/B3 is strongly recommended; confirm you want the
  abstraction rather than point-fixing `Scene3D`.
- **Scope vs 2D-first roadmap.** These are a coherent 3D programme; the roadmap is 2D-first.
  **Open question:** schedule B1/B2 now, or add the whole set to the **backlog** (§9) as a
  ready-to-pull unit and prioritize later?
- **Single-source domain reference.** The computational canon is one 1987 text; its *math* is
  timeless and sufficient for B1–B6, but every modern comparator (three.js, PBR, texture) is a
  **flagged bridge**, not corpus-grounded.
- **Interactive techniques (Ch7).** Deliberately excluded here — it's the static-IR/event axis
  (the SVG.js-parity question), tracked separately; flag if you want it folded in.

---

## 9. Backlog (ready to add to `docs/roadmap.md` on approval)

| ID | Item | Tier / fit | Canon | Complexity | Depends on | Detail |
|---|---|---|---|---|---|---|
| **B1** | Formal viewing pipeline (world→NDC→viewport, clip stage) | T1 high | ¶43, Ch6/8 | M | — | this doc §5 |
| **B2** | 3D pipeline correctness (clip + back-face + depth) | T1 high | Ch8–9 (¶34/36) | S–M | B1 | `cg-canon-3d-alignment.md` |
| **B3** | True 3D scene graph (nodes / instancing / hierarchy) | T2 direction | Ch8–11, ¶43–45 | L | B1, B2 | ADR required |
| **B4** | Fractal / procedural generator (`sdk/fractal.py`) | T2 | Ch11 (¶39) | S–M | — | this doc §5 |
| **B5** | Curved-surface patches (Bézier/B-spline) | T2 | Ch11 | M | B2 | this doc §5 |
| **B6** | Shading completion (flat default + Phong/specular) | T2 | Ch10 | S | B2 | this doc §5 |
| **F1** | Ray tracing / global illumination | T3 bridge | (ray-trace ch.) | — | — | **DEFER — operator-approval-gated** (out of fit) |
| **F2** | Texture mapping | T3 bridge | 1 citation | — | B3 | **DEFER** behind B3 |

*Recommended first pull:* **B1 → B2** (Phase 1) — small, correctness-first, unblocks B3–B6.

*Provenance: domain reference read live from the GraphQL corpus (kb v1.4.0, doc 5f2e8322,
Harrington 1987) via scoped KWIC + preface enumeration; codebase evidence at frameforge HEAD 2.4.1.
On approval, §9 is added to `docs/roadmap.md`.*
