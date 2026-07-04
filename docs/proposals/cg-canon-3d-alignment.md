---
title: "Aligning FrameGraph's graphics pipeline with the classical CG canon"
status: PROPOSAL — awaiting operator approval; on approval, merge into docs/roadmap.md (extends Item 7 + Appendix A)
date: "2026-07-04"
disclaimer:
  notice: >-
    No statement here should be taken for granted. Codebase claims cite file:line
    at repo HEAD 2.4.1; domain claims cite the reference corpus (¶ = sentence
    ordinal) and could be narrowed by re-reading. Recommendations touching modern
    CG (GPU/shaders/PBR/texture) are FLAGGED BRIDGES — beyond the corpus, marked as such.
  generated_by: "Claude Opus 4.8 via Claude Code"
  method: >-
    Domain reference = the GraphQL knowledge corpus (kb API v1.4.0), primary source
    "Computer Graphics: A Programming Approach", Harrington, 2nd ed. 1987 —
    document 5f2e8322, probed by scoped KWIC. Codebase = frameforge HEAD 2.4.1.
domain_reference:
  - "Harrington, Computer Graphics: A Programming Approach, 2nd ed. (McGraw-Hill, 1987) — corpus doc 5f2e8322"
  - "Corpus boundary: pre-1987. No GPU/shaders/PBR; texture mapping = 1 bibliography citation only."
---

# Aligning FrameGraph's graphics pipeline with the classical CG canon

## 1. Executive summary

**Current state.** FrameGraph's **2D** vector-graphics core is mature and, measured
against the classical CG canon, *well aligned*: it uses homogeneous coordinates
throughout (`Mat3`), models a retained scene of addressable objects (the canon's
"segments"/display-file model), and ships curves, arcs, planar booleans, clipping
(delegated to SVG `clipPath`), gradients, and a Chevreul-based colour module that
implements the very sources the corpus contains. The **3D** subsystem
(`sdk/draw.py::Scene3D`, self-described *"Minimal 3D scene"*) implements the front
of the classical pipeline — modelling, homogeneous transforms, perspective/parallel
projection, an optional Lambert/Gouraud shading pass — but **omits the two pipeline
stages the canon pairs with projection**, and its depth resolution is a heuristic
with documented failure cases and no mitigation.

**Main problems found (all in the 3D path; the 2D path is calibrated as *not* broken).**

1. **Projection is not robust and is not preceded by clipping.** `Mat4.project`
   ([geometry.py:207](../../src/framegraph/sdk/geometry.py#L207)) divides by the
   homogeneous `w` but **raises `ValueError` when `|w|<1e-12`** and has **no `w>0`
   guard**, and `Scene3D.render` projects *every* vertex directly
   ([draw.py:183](../../src/framegraph/sdk/draw.py#L183)). Geometry on or behind the
   camera plane therefore **crashes the render** (w≈0) or **projects inverted** (w<0).
   The canon treats "three-dimensional clipping" as a first-class stage *between*
   projection and rasterization (¶34) precisely to prevent this.
2. **No back-face removal.** `Scene3D.render` performs no normal-vs-viewer test. The
   canon: *"if the normal vector points toward the viewer, the face is visible…
   otherwise… a back face… should be removed"* (¶3670), and pairs back-face removal
   *with* the painter's algorithm as the two hidden-surface methods (¶36).
3. **Painter's-algorithm depth heuristic with no fallback.** Hidden surfaces are
   resolved by an **average-z priority sort** (`sorted(..., key=_avg_z)`,
   [draw.py:205](../../src/framegraph/sdk/draw.py#L205) / `_avg_z`
   [draw.py:423](../../src/framegraph/sdk/draw.py#L423)). Average-z is a known-incorrect
   ordering for interpenetrating or cyclically-overlapping faces; there is no polygon
   splitting and no z-buffer. The canon documents the **Z-buffer** as the robust
   per-fragment alternative (¶3713/3717).

**Highest-value improvements** (small, correctness-first — and, since the **true-3D block
was lifted 2026-07-04**, the *foundations* any real 3D needs): make projection robust +
clip against the near plane (P1), add back-face removal (P2), and give depth-resolution a
correct strategy option (P2/P3). Together these turn `Scene3D` from "works for a
hand-checked convex mesh in a fixed pose" into "correct-by-construction for arbitrary
meshes and camera moves" — the property AI agents, `Camera.orbit()` animation, **and any
future true-3D scene graph** all need. **This extends roadmap Item 7 / Appendix A**, which
document the geometry SDK's 2D-projection baseline but do not address these correctness
gaps or cite the canon; with the scope block lifted, they read as the **prerequisites** for
the now-accepted true-3D direction, not a detour around it.

---

## 2. Source-grounded domain understanding (the CG canon from the corpus)

The domain reference is the corpus's one deep computational-CG source, Harrington
(1987), probed directly. The **classical 3D pipeline** it teaches, in order:

| Stage | Canon evidence (¶ = sentence ordinal in doc 5f2e8322) |
|---|---|
| Modelling (meshes, curved surfaces) | curved lines & surfaces chapter |
| Viewing transform, **homogeneous coordinates** | ¶1405 *"introduce homogeneous coordinates… in anticipation of three-dimensional perspective transformations"* |
| **Parallel + perspective projection** | ¶34 *"parallel projection, perspective projection…"* |
| **3-D clipping (against the view volume)** | ¶34 *"…and three-dimensional clipping are discussed"* |
| **Hidden-surface removal**: back-face removal **+** painter's priority sort | ¶36 *"removal of back faces; …a priority sort for… the painter's algorithm"*; ¶3670 back-face normal test; ¶3622 painter's |
| — robust alternative: **Z-buffer** | ¶3713/3717 Z-buffer initialised to large negative, per-point depth compare |
| Shading & colour | shading & colour chapter |

For **2D**, the canon adds windowing & clipping (¶28), scan conversion / Bresenham,
and the raster / frame-buffer model — and a **retained "segments"** model (a scene as
addressable, attributed subpictures), which is structurally FrameGraph's Layer/Object graph.

**Corpus boundary (flagged bridges).** The reference is pre-1987: **zero** OpenGL/shader
hits corpus-wide, texture mapping appears **only as a 1984 citation**, and "GPU" occurs
only in the corpus's ML books. Any recommendation about texture mapping, PBR, or
programmable pipelines is therefore a **flagged bridge** (my knowledge, not corpus-grounded)
and is marked as such below.

---

## 3. Codebase assessment (FrameGraph as a CG system)

- **Architecture.** A geometry kernel in `sdk/` (`Vec2/Vec3`, `Mat3` 2D-affine,
  `Mat4`+`Camera` 3D, `CubicBezier`/`catmull_rom`, `Path`), a modelling/scene layer
  (`draw.Scene3D`), booleans/topology (`planar`, `manifold`, `topology`, `lattices`),
  a hexagonal renderer (domain `ScenePainter`/`DocumentRenderer` ports → SVG/TikZ
  painters, HTML/PDF backends), and a colour-craft module (`chevreul`, `canon`).
- **Data model.** A retained scene (`Document → Page → Layer → Object`) — a direct
  analogue of the canon's "segments." 3D is *lowered* to this: `Scene3D.render`
  projects faces to 2D closed polylines and returns a group
  ([draw.py:162–211](../../src/framegraph/sdk/draw.py#L162)).
- **2D pipeline (mature, aligned).** Homogeneous `Mat3` (`translate/scale/rotate/@/inverse`,
  [geometry.py:55](../../src/framegraph/sdk/geometry.py#L55)); curves + `arc_to`; planar
  booleans; clipping via SVG `clipPath`; gradients/patterns; Chevreul colour.
- **3D pipeline (minimal).** `Scene3D` offers `mesh/parametric_surface/extrude/revolve`;
  `render()` builds a projection matrix (isometric default, or `Camera`), runs an optional
  lighting pass (`_face_lighting`, `shading ∈ {none,lambert,gouraud}`, default **none**),
  projects all faces, and paints them back-to-front by `_avg_z`.
- **Rasterization / antialiasing.** Delegated to SVG→Chromium/Cairo (vector-first). This
  is a *legitimate design choice* — the canon's scan-conversion/antialiasing chapters are
  satisfied downstream — and is **not** flagged as a gap.
- **Strengths (calibration — explicitly *not* problems).** Homogeneous coordinates (canon
  ¶1405); retained "segments" model; rich 2D curves/booleans/clipping; Chevreul colour
  module implementing corpus sources (`The Laws of Contrast of Colour`, Chevreul).
- **Weaknesses.** Concentrated entirely in 3D correctness — §4.

---

## 4. Gap analysis (implementation vs. canonical domain model)

| # | Gap | Code evidence | Canon evidence | Severity |
|---|---|---|---|---|
| **G1** | Projection not robust: crashes on `w≈0`, inverts on `w<0` | geometry.py:207–211 (raise on `|w|<1e-12`, no `w>0`); draw.py:183 projects all | ¶34 (3-D clipping is a pipeline stage) | **High (correctness / crash)** |
| **G2** | No view-volume / **near-plane clipping** before the perspective divide | draw.py:183; no clip stage in `Scene3D` | ¶34 *"three-dimensional clipping"* | **High** |
| **G3** | No **back-face removal** | `Scene3D.render` has no normal test | ¶3670, ¶36 (canon pairs it with painter's) | **Med (correctness + fill waste)** |
| **G4** | Depth resolved by **average-z only**; fails on interpenetrating/cyclic faces; no split, no z-buffer | draw.py:205, `_avg_z` draw.py:423 | ¶3622 (painter's), ¶3713/3717 (Z-buffer alternative) | **Med** |
| **G5** | Shading basic (Lambert/Gouraud, default off); no specular/Phong, no texture | draw.py:170–182 | shading chapter; *texture = corpus boundary* | **Low (+ flagged bridge)** |

**Not gaps (to avoid overclaiming):** 2D clipping (delegated, correct), homogeneous
transforms (present & correct), curves/surfaces (present), scan-conversion/antialiasing
(delegated by design), colour (aligned). The proposal deliberately does **not** touch these.

---

## 5. Proposed improvements

### I1 — Robust projection + near-plane clipping (fixes G1, G2)
- **Problem.** A single vertex on/behind the camera plane crashes the render or mirrors the mesh.
- **Evidence.** geometry.py:207–211; draw.py:183.
- **GraphQL support.** ¶34: 3-D clipping is a named stage between projection and imaging.
- **Change.** Insert a clip stage in `Scene3D.render` *before* projecting: transform faces to
  clip/eye space, **Sutherland–Hodgman-clip each face against the near plane** (and optionally
  the full frustum), then perspective-divide the survivors. Change `Mat4.project` to **not raise**
  on degenerate `w` — return `None`/skip so a face can be clipped rather than crashing.
- **Benefit.** No crashes; correct perspective for any camera pose; unlocks safe `Camera.orbit()` sweeps.
- **Complexity.** **S** (near-plane only) → **M** (full 6-plane frustum). Pure Python, isolated to `draw.py`/`geometry.py`.
- **Risks/trade-offs.** Near-plane clipping can split a triangle into a quad (more faces); negligible at deck scale.
- **Validation.** Golden fixtures: a cube straddling the near plane; an `orbit()` sweep through 360° with a vertex crossing behind the eye — assert no exception and monotone silhouette (no mirror flip).

### I2 — Back-face removal (fixes G3)
- **Problem.** Back faces are projected and painted, then overdrawn — wasted fill and, for concave meshes, wrong.
- **Evidence.** No normal test in `Scene3D.render`.
- **GraphQL support.** ¶3670 (normal-toward-viewer test); ¶36 (canon's first hidden-surface method).
- **Change.** Compute each face's world/eye-space normal; cull faces whose normal faces away from the eye
  (sign configurable for winding). Expose `cull: "back"|"front"|"none"` on `render()` (default `"back"` for closed meshes, `"none"` for open surfaces like `parametric_surface`).
- **Benefit.** Correctness for closed solids; ~½ the polygons to sort/paint.
- **Complexity.** **S**. One cross-product + dot per face.
- **Risks.** Winding must be consistent; `extrude/revolve` already emit consistent winding — verify. Open surfaces must default to no-cull (hence the flag).
- **Validation.** Fixture: a sphere (`revolve`) renders no interior faces; a single open patch is unaffected.

### I3 — Correct depth strategy (fixes G4)
- **Problem.** Average-z mis-orders interpenetrating/cyclic faces with no recourse.
- **Evidence.** draw.py:205, `_avg_z` draw.py:423.
- **GraphQL support.** ¶3622 painter's; ¶3713/3717 Z-buffer as the robust alternative.
- **Change.** Keep avg-z as the default (cheap, vector-native), but add `depth: "avg_z" | "split" | "zbuffer"`:
  `split` = detect overlapping-and-mis-ordered pairs and split along the offending plane (correct, still vector);
  `zbuffer` = **flagged bridge** — a raster-only path (render per-fragment depth into the Cairo/Chromium pass), acceptable because it lives *below* the SVG seam and does not vectorize.
- **Benefit.** A correct option for the cases avg-z gets wrong, without abandoning vector output for the common case.
- **Complexity.** `split` = **L**; `zbuffer` = **M** but raster-only. Default path unchanged → zero regression risk.
- **Risks.** `split` is the classic hard case (Newell–Newell–Sancha); ship it behind the flag, not as default.
- **Validation.** The canonical two-interpenetrating-triangles and three-cyclic-quads fixtures; assert `split` matches a reference z-buffer raster within tolerance (reuse `compare_images`).

### I4 — Shading polish + honest boundary (addresses G5)
- **Problem.** Shading is off by default and shallow; texture/PBR are absent.
- **Evidence.** draw.py:170–182.
- **GraphQL support.** shading chapter (Lambert/Gouraud is *in* canon); **texture/PBR are a flagged bridge**.
- **Change.** Small: document that Lambert/Gouraud exist and how to enable them; consider `shading="flat"` as a
  sane default for closed meshes. Do **not** build texture/PBR here — record it as an out-of-corpus bridge in Appendix A.
- **Complexity.** **XS** (docs + default) / **XL** (texture — explicitly deferred, operator-gated).
- **Validation.** A shaded-vs-unshaded golden pair.

### I5 — Conformance documentation + regression net (cross-cutting)
- **Problem.** Appendix A documents the SDK but not *which canonical pipeline stages exist, are delegated, or are absent*.
- **Change.** Add a "Scene3D vs. the classical pipeline" table to Appendix A (stage → status: implemented /
  delegated / absent / flagged-bridge), citing the same ¶ evidence; land the fixtures from I1–I3 as the regression net.
- **Benefit.** The roadmap stops implying parity it doesn't have; future contributors and agents get a truthful map.
- **Complexity.** **S**. Validation is the doc-sync gate (`make check`).

---

## 6. Implementation order

**Phase 0 — safety, tests, baseline docs.** Land the failure-case golden fixtures *first*
(near-plane crash, behind-camera inversion, interpenetrating & cyclic faces) so they go
RED against current `main`; write the I5 "Scene3D vs pipeline" table. *Exit when:* the
fixtures reproduce every §4 defect and the doc-sync gate passes.

**Phase 1 — low-risk correctness (I1 robust `project` + near-plane clip).** No public API
change; `Mat4.project` stops raising, `Scene3D` gains an internal near-plane clip. *Exit when:*
the crash/inversion fixtures go GREEN and all existing 3D goldens are unchanged.

**Phase 2 — domain-model alignment (I2 back-face removal; I3 `split` option).** Adds
`cull`/`depth` knobs. *Exit when:* closed-solid and interpenetration fixtures pass and the
open-surface fixture is provably unaffected (defaults preserve current output).

**Phase 3 — workflow/API (surface the knobs; I4 shading default + docs).** Expose
`cull`/`depth`/`shading` on the SDK `scene3d`/`mark3d` authoring path and document them;
default closed meshes to `cull="back"`, `shading="flat"`. *Exit when:* SDK docs regenerate
and the capability manifest reflects the new options.

**Phase 4 — optimization & observability.** Render diagnostics (faces culled / clipped /
split, degenerate-`w` drops) surfaced in the render report; the optional raster `zbuffer`
path (flagged bridge) behind availability detection like the other raster backends. *Exit when:*
diagnostics appear in `run_sdk_code` output and the raster path degrades gracefully when absent.

*Sequencing rationale:* correctness fixes (P1) must precede model changes (P2) so each new
knob is proven against a stable, non-crashing baseline; API exposure (P3) waits until the
behavior it exposes is correct; optimization (P4) is last so it never masks a correctness bug.

---

## 7. Benefits

- **Correctness.** Eliminates a hard crash (`w≈0`) and a silent visual corruption
  (behind-camera inversion, mis-ordered interpenetration) — the difference between "3D that
  demos" and "3D you can trust in a pipeline that gates on golden hashes."
- **Domain alignment.** `Scene3D` comes to implement the canonical stage sequence
  (transform → **clip** → project → **cull** + depth-resolve → shade) the corpus prescribes,
  and Appendix A tells the truth about which stages are implemented vs delegated vs bridged.
- **Agent-readiness.** AI-authored 3D (and `Camera.orbit()` animation frames) stop producing
  mirrored/crashing frames — essential for the MCP `run_sdk_code` loop and PALS-style verification.
- **Extensibility & operational safety.** `cull`/`depth`/`shading` become explicit seams;
  render diagnostics make 3D failures observable instead of silent.
- **Cost discipline.** Every P0–P2 item is S/M, pure-Python, isolated to `draw.py`/`geometry.py`,
  with defaults that preserve current output — high correctness yield, low blast radius,
  and framed as the **project-to-2D baseline's** correctness layer — which, with the true-3D
  block lifted (2026-07-04), is exactly the foundation the now-in-scope true-3D direction builds on.

---

## 8. Risks and open questions

- **Scope (updated 2026-07-04 — block lifted).** The roadmap's true-3D block is withdrawn, so
  true 3D (three.js-level, a document-carried 3D scene graph) is now an accepted direction. These
  correctness fixes (robust projection, near-plane clipping, back-face removal, depth resolution)
  are **prerequisites** for it — you cannot ship real 3D on a projector that crashes on a vertex
  behind the camera or mis-orders interpenetrating faces. They also stand alone: `Scene3D` ships
  today, so they fix a live correctness bug regardless of how far the true-3D direction is taken.
  The remaining open question is *sequencing* — do the true-3D scene-graph design now, or land these
  foundations first (recommended) and design true 3D on a correct base.
- **Vector-first tension (I3).** A true z-buffer is per-fragment and cannot vectorize; the honest
  options are `split` (vector, hard) or a raster-only `zbuffer` mode (flagged bridge). **Decision needed:**
  is a raster-only correctness mode acceptable below the SVG seam?
- **Single-source, single-era domain reference.** The corpus's computational CG is one 1987 text;
  its math (transforms, clipping, hidden-surface) is timeless and sufficient for G1–G4, but anything
  modern (texture/PBR/GPU) is a **flagged bridge**, not corpus-grounded. Confirm the classical scope is the target.
- **Winding assumptions (I2).** Back-face culling assumes consistent face winding from
  `extrude/revolve/parametric_surface`; must be verified per generator before enabling by default.
- **Priority.** The roadmap is 2D-first. **Open question:** is 3D correctness worth a slot now, or
  parked behind the 2D items — merged into the roadmap as a documented, ready-to-pull unit either way?

---

*Provenance: domain reference read live from the GraphQL corpus (kb v1.4.0, doc 5f2e8322,
Harrington 1987) via scoped KWIC; codebase evidence cited at frameforge HEAD 2.4.1. On
approval this merges into `docs/roadmap.md` as a corpus-grounded extension of Item 7 / Appendix A.*
