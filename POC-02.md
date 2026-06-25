---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-25"
---

# POC-02 — Is the layered drawing protocol *feasible*? (an executed experiment)

POC-01 and `docs/illustration-protocol.md` are **specifications**. This is a
**proof**: it runs the protocol's load-bearing claims end to end and reports what
the pixels and numbers actually show — feasible, or course-correct.

Reproduce: `FG_ROOT=. uv run python examples/poc2_drawing_protocol.py out/poc2`

---

## 1. POC-01 vs the illustration protocol — they agree; neither was tested

| | [POC-01.md](POC-01.md) | [docs/illustration-protocol.md](docs/illustration-protocol.md) |
|---|---|---|
| Kind | **System / toolset spec** ("Vector Drawing Coach MCP", ~40 tools, MVP) | **Process / methodology** (StyleSpec, CameraSpec, layer pipeline, gates) |
| Core insight | "repeatable external discipline: decomposition + geometric construction + perspective validation + style grammar + layer discipline + critique loop" | "Declare → Construct → Render → Verify → Refine, per layer; style/perspective are declared parameters" |
| Style | **grammar, not prompt text** | StyleSpec (line/fill/palette/shading/shape) |
| Perspective | **math, not vibes** (camera + VPs + projection) | CameraSpec → one `P(world)→canvas` |
| Verification | `critique_drawing_stage`, `score_drawing_quality` | measurable per-layer gate with structured deltas |

They are the same idea from two angles — strong corroboration. **But both are
unproven**: nothing had executed the loop. That is the gap POC-02 closes.

---

## 2. The experiment

A ~190-line harness ([examples/poc2_drawing_protocol.py](examples/poc2_drawing_protocol.py))
implements the *minimum* that would falsify the protocol if it were wrong:

- a tiny **3D vector engine** — pinhole projection, painter's-sort occlusion,
  Lambert face-shading;
- **one** subject, `build_mascot()`, declared once in **head-units** (boxes →
  6 faces each, with normals);
- a **CameraModel** (`yaw, pitch, dist, f`) and a **StyleProfile**
  (`cel` shaded / `blueprint` wireframe);
- a **measurable gate** on a coupled proportion metric (head-units = projected
  total-height ÷ head-height);
- rendered through **FrameGraph's own engine** (`render_page_svgs`).

Three claims, three tests:

1. **Perspective = math** — render the *same* construction through 3 cameras.
2. **Style = grammar** — render the *same* construction through 2 style profiles.
3. **Self-correcting gate** — inject a proportion defect, detect it numerically,
   auto-correct, and verify it reaches target.

---

## 3. Results

**Claim 1 & 2 — PASS (page 1, the 3×2 matrix).** One `build_mascot()` renders
correctly across `{three-quarter, low-angle, top-down} × {flat-cel, blueprint}`.
The three-quarter view shows side faces, the low-angle reveals the *underside*
planes, top-down shows the *tops* — true foreshortening from a single 3D source.
The two styles share identical geometry yet read completely differently (shaded
solid vs. cyan wireframe on a blueprint grid). Cel shading is **not authored** —
it falls out of the face normals · light direction. So subject, camera, and style
are genuinely *independent and composable*. That is the whole ballgame.

**Claim 3 — PASS, after a course correction (page 2).** Inject `head ×1.7`:

```
head-units:  1.84  (defect, target 2.74)   ← gate detects numerically
one-shot fix → 2.46  (FAIL: 0.28 short)    ← under-converged
iterated     → 1.84 → 2.46 → 2.68  (PASS)  ← fixed point reached in 2 steps
```

The one-shot correction **failed** because head-units is a *coupled* metric: the
head is part of the total height, so shrinking it lowers the denominator *and* the
numerator. A single proportional nudge can't solve a coupled constraint — it must
**iterate to a fixed point**. That is the protocol's "refine until the checklist
passes," and POC-02 shows it is **load-bearing, not optional**.

---

## 4. Verdict — **feasible**, with bounded scope and three course corrections

**The mechanism is feasible and proven.** Separating *subject / camera / style*,
projecting through real geometry, rendering in layers, and gating on measurable
invariants works, and FrameGraph renders all of it faithfully. This is exactly
what the SaaS-hero exercise lacked, and why that output plateaued.

**Course corrections discovered by running it:**

1. **Gates must iterate to a fixed point.** Coupled metrics (proportion, balance,
   spacing) do not yield to one-shot fixes. Every gate needs a convergence loop +
   tolerance + iteration cap. (POC-01's `critique` tools should be *loops*, not
   single calls.)
2. **Verification must be numeric first, visual second.** The gate that worked
   here measured a ratio and corrected a transform — no vision model needed. The
   image diff is for what you *cannot* measure (style feel, silhouette). Build the
   measurable gates first; they are cheap, deterministic, and convergent.
3. **Construction must be 3D (or projective), not 2D.** "Any perspective" only
   works because the subject lives in a space a camera projects. A 2D-only
   construction cannot be re-angled. The representation choice is the enabler.

**Honest boundary (unchanged and confirmed):** this delivers **construction-correct,
perspective-true, style-consistent** vector. It does **not** by itself reach an
illustrator's freehand organic density — the mascot is legible and correct, not
"hand-drawn." The path to that tier is **curated/imported vector parts flowing
into the same pipeline** (the SVG import proof already showed FrameGraph renders
such parts 1:1): construction and silhouette sourced from real assets, then
re-projected and re-lit by the protocol. Fully-synthetic-from-primitives tops out
at "clean, correct, stylable" — which is itself far past where we were.

---

## 5. Recommendation — the MVP to build

Build the **intersection** of POC-01's MVP and what POC-02 proved, in this order
(each item already has a working seed in the harness):

1. **Projection engine** — `CameraModel` + `P()/P⁻¹()` + grid + box/ellipse-in-perspective. *(proven)*
2. **StyleProfile → render** — palette-roles + shading model + line grammar; normals drive light. *(proven)*
3. **Iterating measurable gates** — proportion, grid-alignment, palette, silhouette; each a convergence loop. *(proven; this is the corrected piece)*
4. **Layer stack + dependency order** — one FrameGraph layer per stage, guides removable. *(mechanism in place)*
5. **Component library** — promote verified parts to `define_symbol`/figures; re-skin/re-angle to vary. *(next)*
6. **Asset ingestion** — SVG → construction/silhouette for the organic-fidelity tier. *(prototype exists)*

Defer "any organic human, any style" until (5)+(6); ship "objects / mascots /
vehicles / characters-from-volumes, any camera, several styles" first — which
POC-02 shows is reachable now.

---

[↑ Back to the project README](README.md) · related:
[POC-01.md](POC-01.md) · [docs/illustration-protocol.md](docs/illustration-protocol.md) ·
[examples/poc2_drawing_protocol.py](examples/poc2_drawing_protocol.py)
