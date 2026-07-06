---
disclaimer:
  notice: >-
    No information within this document should be taken for granted. Any statement
    or premise not backed by a real logical definition or verifiable reference (the
    model, the EBNF, a test, an example) may be invalid, erroneous, or a
    hallucination. This ADR proposes a direction and stages it; nothing here ships
    until its slice is built and gated.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-07-05"
---

# ADR 0005 — Document-carried 3D scene graph (true 3D, projected deterministically)

## Status

**Proposed — operator-directed (Option B, 2026-07-05).** Unblocks roadmap backlog
**B3** (parked as "approved — ADR required first"). Staged into slices 5a–5e; each
slice is accepted independently on build + gate, like ADR-0001. This ADR **narrows**
the "keep 3D author-time" stance (§A.5, roadmap Item 7 / Appendix A.0; G-2) for one
sanctioned carrier — a new `scene3d` object — while leaving the 2D guard intact. It
follows the **2026-07-04 course correction that lifted the true-3D block.**

Prerequisites are met: **B1** (`window_to_viewport` + `ViewingPipeline`, adopted
inside `Scene3D.render`) and **B2** (`Mat4.try_project` + near-plane Sutherland–Hodgman
clip + back-face cull) are DELIVERED. The only remaining blocker was this ADR.

## Context

B3 wants a real 3D scene graph — **nodes, per-node transforms, instancing, hierarchy**
— so that 3D assets are reusable and scenes are composable. The lifted block created a
fork, and this ADR exists to choose a tine and pin the verifiability contract.

- **Option A — author-time scene graph.** The tree lives in the **SDK**; `render()`
  projects it and emits 2D `path`/`polyline`/`group`. No model/grammar change; the
  render boundary is untouched; golden-hashable by construction (it is exactly today's
  `Scene3D`, enriched with hierarchy). Safe and cheap — **but the 3D is ephemeral:**
  a single baked camera, no retargeting, no 3D export, nothing to inspect or round-trip.
- **Option B — document-carried 3D.** The document **carries** the 3D scene (a new
  object type). This is the payoff the lifted block was *for*: one 3D source →
  many camera projections (**retarget**), a separate **3D export** (glTF/PRC, à la
  Asymptote's PRC), and an inspectable/round-trippable 3D island. It touches the model
  source-of-truth, the grammar, expansion, and — the crux — the verifiability contract.

**Operator direction (2026-07-05): Option B.** Option A is recorded as the fallback
(see *Alternatives*), to be adopted only if B's determinism (below) proves intractable.

**The hard constraint that shapes everything.** `golden-check` pins each oracle page's
rendered output by **SHA-256** (codebase-standards §3/§8). Carrying 3D is therefore only
safe if the 3D **projects to byte-deterministic 2D**. A document that carries 3D but
renders non-reproducibly cannot be gated, and an ungated render is, by PALS's Law, a
defect. This is the make-or-break of Option B, and slice 5c is dedicated to it.

## Decision

Adopt **Option B as a dual model.** The document carries the 3D scene graph in a new
`scene3d` object, and — consistent with the backend-neutral render seam (ADR-0001) —
**each render target chooses how to consume it.** The same object round-trips through
either mode; they are complementary, not a fork:

- **Lowered mode** (2D targets: SVG · PNG · PDF · HTML · TikZ) — the **default and
  verifiable path.** A deterministic **expansion pass** projects `scene3d` to 2D
  `path`/`polyline`/`group`; the **projected 2D is the gated artifact** (pixel-golden).
  The renderer sees only 2D after expansion, so the render boundary — and every existing
  2D backend — is untouched.
- **Fully-3D mode** (3D targets: glTF / PRC export · an interactive WebGL / three.js-style
  viewer) — the scene graph is **preserved and emitted natively.** The document carries
  true 3D end-to-end, no flattening. This is a new `DocumentRenderer` adapter behind the
  same port that SVG/PDF already sit behind (ADR-0001); it adds a target, it does not
  change the 2D ones.

One document, one 3D source; the target picks the mode. Verification is **per mode**
(pin 3). Seven pins:

1. **New model object `scene3d` (`type: "scene3d"`).** A discriminated `ObjBase`
   subtype carrying: `nodes` (each = a `Mat4` transform + `mesh | children`, giving
   **hierarchy**), `instances` (a mesh id × a list of transforms, giving **instancing**),
   `camera` (eye/target/up/fov/near/far — the B2 `Camera`), `materials`, and `shading`
   (`none|lambert|gouraud|phong`, from B6). Meshes are the existing `Scene3D` products
   (`mesh`/`extrude`/`revolve`/`parametric_surface`/`bezier_patch`/`bspline_patch`).
2. **Expansion-time projection.** A new expansion pass lowers a `scene3d` object to a
   `group` of 2D `path`/`polyline`, **reusing the delivered pipeline** — B1
   `window_to_viewport` for the fit and B2 `try_project` + near-plane clip + back-face
   cull for correctness — pinned at expansion (the hash contract, like every other
   computed geometry). The renderer learns *nothing* new.
3. **Verification, per mode (the crux — slice 5c).** The two modes carry different, honest
   contracts:
   - *Lowered* → **pixel-golden, unchanged in kind.** Projected coordinates are emitted at
     **fixed decimal precision** (the discipline SVG coords already use), so the projected 2D
     **bytes are reproducible across environments** and `golden-check` applies as today. If
     fixed-precision projection cannot be made golden-stable, the **lowered** path falls back
     to author-time projection (Option A) — the fully-3D path is unaffected.
   - *Fully-3D* → **a content gate replaces the pixel gate.** An interactive/native render is
     *not* pixel-deterministic, so instead of hashing pixels we SHA-256 the **canonically
     serialized 3D scene** (meshes · node transforms · instances · cameras · materials). The
     carried 3D is reproducible even when its live render is not; the 3D is source-of-truth,
     its serialization is the gated artifact.
4. **Grammar / G-2, narrowed not reversed.** 3D transforms and `perspective` become
   **conformant *inside* the `scene3d` object's local 3D space** — a bounded island —
   and remain **non-conformant on arbitrary 2D objects** (G-2's guard stands for the 2D
   world). The EBNF, JSON-schema, and validator gain the `scene3d` grammar; `perspective`
   as a 2D `TransformFn` stays WARN. This is additive (a new object type) → semver-minor.
5. **Backward compatibility.** The SDK's author-time `Scene3D` becomes a **builder that
   emits the `scene3d` object** rather than pre-projecting. Callers who want eager 2D
   keep it (`Scene3D.render(...)` may still return the projected group); the object-emitting
   path is the new default for document authoring. Additive; a codemod only if a default flips.
6. **Retarget across modes.** One `scene3d` source drives both: several `RenderTarget`
   cameras → several 2D projections (lowered), *and* the same source → a glTF/PRC/viewer
   artifact (fully-3D). This is the 3.0 "retarget one content tree to any surface" direction
   realized in 3D — author once in world space, emit to a printed page or an interactive
   scene from the same object.
7. **Fully-3D is a `DocumentRenderer` adapter, not a boundary break.** The native path is a
   new backend behind the ADR-0001 port (like `HtmlDocumentRenderer`/`PdfTexDocumentRenderer`);
   2D backends lower the object, the 3D backend preserves it. It is where the gated **F2
   texture** work eventually lives (texture is meaningful fully-3D, moot once lowered to flat
   vector faces). Build is staged (5e) and `available()`-gated like the other optional backends.

### Staged slices (accepted independently, on build + gate)

| ID | Slice | Output invariant | Effort |
|----|-------|------------------|--------|
| **5a** | `scene3d` model object + EBNF + JSON-schema + validator (3D conformant *inside* the island; G-2 scoped to 2D) — *the shared carrier both modes read* | model/grammar change; `check_grammar_sync` + schema gate | M |
| **5b** | **Lowered mode** — expansion projection pass (`scene3d` → 2D `group`, reusing B1/B2); SDK `Scene3D` emits the object | renderer sees only 2D; golden pins the projected page | M–L |
| **5c** | **Determinism hardening (lowered)** — fixed-precision projected coords; cross-run/-env golden stability; the hash-contract test | golden-stable (the go/no-go for the *lowered* path) | M |
| **5d** | Full node/instancing/hierarchy semantics + composed-scene & instancing goldens (serves both modes) | additive; new fixtures | L |
| **5e** | **Fully-3D mode** — native `DocumentRenderer` adapter (glTF/PRC export first, interactive viewer next) + the canonical-serialization content gate + multi-camera retarget; F2 texture reconsiderable here | new target; `available()`-gated; content-hash gate | L–XL |

DoR/DoD (roadmap "surface-complete + tested") applies to each slice: SDK API +
regenerated capability manifest + `describe_capabilities` reachability + a runnable
`static/examples/` scene + tests + golden, `make check` green.

## Consequences

- **Payoff.** True document-carried 3D on a **dual model** — the *same* `scene3d` source
  lowers to a deterministic, golden-gated 2D page **or** emits a native, retargetable,
  inspectable 3D artifact. Print fidelity and interactive 3D from one authored scene: the
  full realization of lifting the block, on already-delivered B1/B2 foundations.
- **Cost.** Touches the **model source-of-truth**, the grammar/schema/validator,
  expansion, the hashing discipline, the SDK, tests and docs, plus a new 3D backend.
  Complexity **XL**, which is why it is staged (and why the lowered path — 5a–5d — is
  usable before the fully-3D backend, 5e, exists).
- **Risks (honest):**
  - **Determinism bounds the *lowered* path, not the ADR.** `golden-check` is exact
    SHA-256 and 3D projection is floating-point; fixed-precision emission (5c) is the
    mitigation and **must be proven golden-stable before 5d builds on it.** But because
    this is a dual model, a 5c failure only reverts *lowered* rendering to author-time
    projection (Option A) — the **fully-3D mode, gated on the content hash rather than
    pixels, is unaffected.** The risk is contained, not existential.
  - **Grammar surface.** A new conformant object type is a real model change; the 2D
    non-conformance guard (G-2) must be provably unaffected. Additive → semver-minor,
    but the `check_grammar_sync`/schema gates must stay green.
  - **Blast radius.** The projection pass sits in expansion, upstream of every backend;
    staging (5a model → 5b lower → 5c pin) keeps each step gated and reversible.
  - **F1/F2 unchanged.** Ray tracing stays operator-approval-gated; texture (F2) stays
    deferred, now with 5e as its eventual (still-gated) home.

### Alternatives considered

- **Option A — author-time scene graph (not chosen; the lowered path's fallback).**
  Cheaper (S–M), no model/grammar/hashing change, safe by construction — but the 3D is
  ephemeral (single camera, no retarget, no 3D export, not inspectable), so it does not
  deliver the document-carried payoff. It is retained as the **fallback for the lowered
  path only:** if 5c's determinism proves intractable, lowered rendering reverts to
  author-time projection while the fully-3D mode (which does not use the pixel gate)
  continues unaffected. So even a determinism failure does not sink B3.
- **B-native as the *sole* model (rejected).** Making the renderer always understand 3D —
  no lowered path — was rejected: it would break the "2D backends see only 2D primitives"
  boundary and force a 3D path into SVG/PDF/HTML for no gain. The **dual model** keeps
  native 3D as an *additional* adapter (pin 7) rather than a boundary break: the 2D
  backends stay pure, and the 3D backend is opt-in and `available()`-gated. This is the
  point of choosing B as a dual model rather than a single lowering.

[↑ Back to root README](../README.md)
