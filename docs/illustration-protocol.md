---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-25"
---

# The Illustration Protocol — teaching an AI to draw any style, any perspective, in layers

A repeatable process for guiding an AI agent to produce illustration-grade vector
art incrementally — the way an illustrator actually works — instead of emitting
final shapes blind and hoping a vision loop rescues them.

> **Why this exists.** An LLM hand-placing primitives plateaus at "clean and
> recognizable," never "drawn," because it skips the steps a human never skips:
> it does not *declare the rules*, does not *build construction scaffolds*, has no
> *perspective coordinate system*, and runs a vision loop that returns impressions
> ("looks blobby") instead of *measurable deltas* ("head is 1.3 units, spec says
> 1.0 → scale 0.77 about the neck"). This protocol fixes those four omissions.

The renderer is not the bottleneck — FrameForge draws arbitrary bezier/gradient
vector faithfully. Fidelity is an **authoring discipline** problem, and discipline
is teachable as a process.

---

## Core principle

> Drawing = **Declare → Construct → Render → Verify → Refine**, applied per layer,
> never out of order. Style and perspective are **parameters declared up front**,
> not properties that emerge from drawing.

Two ideas do the heavy lifting:

1. **Separate the *what* from the *how* from the *where*.** Subject (what), style
   (how it looks), and camera (where it is seen from) are three independent specs.
   Hold two fixed and you can vary the third — that is what "any style, any
   perspective" means operationally.
2. **Construction before contour, contour before colour, colour before light,
   light before detail.** Each stage is its own layer, built on the verified one
   below it. The hard geometry is locked *before* anything is rendered, so the
   vision pass only polishes — it never has to rescue.

---

## Step 0 — Declare two contracts (before a single shape)

The agent must fill in and **echo back** both specs before drawing. Committing to
them in writing is what makes the result checkable.

### StyleSpec — the "how it looks" rulebook

```jsonc
{
  "line":        { "mode": "outline|none", "weight": 2.0, "variation": 0.0,
                   "cap": "round", "join": "round", "color": "#1E2440" },
  "fill":        { "model": "flat|linear|radial|cel", "direction": 120 },
  "palette":     { "base": "#7C3AED", "shadow": "#5B21B6", "highlight": "#A78BFA",
                   "accent": "#22D3EE", "skin": "#F4C7A6", "ink": "#1E2440" },
  "shading":     { "model": "none|cel2|soft|rim", "light_dir": [-1, -1],
                   "shadow_alpha": 0.22, "highlight_alpha": 0.5 },
  "shape":       { "language": "geometric|organic", "corner_radius": 12,
                   "roundness": 0.6 },
  "figure":      { "head_units": 6.5, "stylization": 0.7 },
  "detail":      { "budget": "low|medium|high", "face": "minimal|expressive" }
}
```

### CameraSpec — the "from what angle" rulebook

```jsonc
{
  "projection":  "orthographic|isometric|dimetric|one_point|two_point|three_point|oblique",
  "horizon_y":   320,
  "vanishing":   [[ -400, 320 ], [ 1700, 320 ]],   // VP positions in canvas space
  "ground_y":    560,
  "up_axis":     [0, -1],
  "scale_ref":   { "unit_px_at_horizon": 8, "unit_px_at_ground": 22 }
}
```

The CameraSpec yields a single projection function `P(world) -> canvas` (and an
inverse) that **every** object obeys. "Any perspective" = pick a projection +
parameters; the whole scene then snaps to the same space.

> **Test for completeness:** if two different agents fill the same two specs, their
> outputs should be recognisably the *same style from the same angle*. If they
> can't, the spec is under-specified — add fields until it can.

---

## The layer pipeline — multiple steps, one layer each, each gated

Build in order, L0 → L8. Every stage is a **separate render layer** so guides can be toggled
or removed. **Do not start a layer until the one below it has passed its gate.**

| # | Layer | What it contains | Gate (must pass before next) |
|---|-------|------------------|------------------------------|
| L0 | **Thumbnail / blocking** | rough masses (rects/ellipses) for the big shapes; focal point; rule-of-thirds | composition reads at thumbnail size |
| L1 | **Perspective scaffold** | horizon, VP lines, ground plane, depth grid from CameraSpec (a *guide* layer) | grid consistent; all masses sit on it |
| L2 | **Construction** | primitive solids per subject — a figure = stacked spheres/cylinders/boxes *in perspective*; a device = boxes; proportions from StyleSpec | proportions & anchor points match spec; everything on the grid |
| L3 | **Silhouette / contour** | clean outline shapes wrapping the construction | passes the **squint test** — readable as a black silhouette |
| L4 | **Local colour (flats)** | base fills by palette *role*, no shading yet | palette conformance; flat read is clean |
| L5 | **Shading & light** | shadow/highlight shapes from one light direction (cel or soft per spec) | one consistent light; depth reads |
| L6 | **Detail** | faces, props, textures — within the detail budget | detail supports the read, doesn't clutter |
| L7 | **Effects & polish** | gradients, glow, ambient occlusion, accents | effects are subtle, intentional |
| L8 | **Integration** | place into the page composition; balance vs siblings; consistency | cohesive with the rest of the set |

Each row is a literal FrameForge layer: `page.layer("L2-construction")`, etc. Guide
layers (L1, and the construction lines of L2) are deleted or hidden before export.

---

## The verification gate (this is how the vision loop becomes precise)

The loop only works if each gate compares against a **target** and emits
**localised, measurable deltas** — not impressions.

For every layer, before proceeding:

1. **Render just this layer** (plus the construction beneath it) to PNG using a
   real rasterizer (browser, or CairoSVG fallback — never judge a degraded proxy).
2. **Compare to a target.** The target is one of:
   - a **reference image** (overlay it; diff by region), or
   - the **spec invariants** (proportion ratios, grid alignment, palette hexes,
     silhouette coverage %).
3. **Emit a structured delta list**, not prose:

   ```jsonc
   [ { "element": "head", "observed_units": 1.3, "expected_units": 1.0,
       "fix": "scale 0.77 about (cx, neck_y)" },
     { "element": "left_arm", "observed_angle": 12, "expected_angle": 28,
       "fix": "rotate +16 about shoulder" },
     { "element": "jacket", "observed": "#8B5CF6", "expected_palette.base": "#7C3AED",
       "fix": "recolor base" } ]
   ```
4. **Apply fixes** as transforms/edits to *that layer only*; re-render; repeat until
   the gate's checklist passes.
5. **Freeze** the layer and move on.

Because construction (L2) is *measurable*, you correct geometry while it is cheap —
a few solids — long before it is expensive to fix (after colour and detail). By the
time you render finishes, the geometry is already right.

---

## Reuse — the library that makes style consistent and fast

- The moment a part (an eye, a hand, a wheel, a leaf) passes its gate, **save it as
  a parameterised component** (FrameForge `define_symbol` / a figure) with its
  construction intact.
- Compose scenes from the growing library. Cohesion across an entire pack comes
  from a **shared StyleSpec + shared library**, not from redrawing.
- **Re-style** = swap the StyleSpec and re-skin library parts (same construction,
  new line/fill/palette/shading). **Re-angle** = swap the CameraSpec and re-project
  placements (same parts, new `P`). This is the lever for "any style, any angle."

---

## Refinement loop & exit criteria

- Passes are **goal-scoped**, not counted: a *geometry* pass, a *colour* pass, a
  *light* pass, a *polish* pass — each with its own checklist.
- Maintain a **defect ledger**; every pass must reduce it.
- **Exit** when the checklists pass or the marginal gain per pass drops below a
  threshold — never "after N iterations." Five aimless passes beat nothing; five
  *gated* passes converge.

---

## How this maps onto FrameForge today

| Protocol need | FrameForge mechanism |
|---|---|
| Ordered, toggleable layers | `page.layer(...)` per stage; delete guide layers before export |
| Construction solids, contours | `ellipse` / `rect` / `polygon` / `path` primitives |
| Perspective placement | per-object `style.transform` (`translate/scale/rotate/matrix`); a computed `P()` in the client |
| Reusable parts | `define_symbol` / `symbol` / figures (`place_figure`, `FigureRef`) |
| Sourcing construction refs / real assets | SVG → FrameForge import (paths render 1:1) |
| The verification gate | MCP `run_sdk_code` → render → `measure_image` / `mark_points` / `overlay_images` to localise, `compare_images` for NCC/RMSE region diffs, `score_reconstruction` for numeric geometry convergence |
| Style/Camera specs | plain dicts the client consumes; echo them in the doc title/meta |

---

## Worked micro-example (one figure, 3/4 view, flat-cel style)

1. **Declare.** StyleSpec: `fill=cel`, `figure.head_units=6.5`, `shading=cel2`,
   `light_dir=[-1,-1]`. CameraSpec: `projection=two_point`, horizon at y=300,
   VPs at (−500,300) and (1800,300).
2. **L1 scaffold.** Draw horizon + two VP fans; mark a ground footprint box for the
   figure, projected through `P`.
3. **L2 construction.** Stack a head sphere, ribcage box, pelvis box, limb
   cylinders — each sized in head-units, each face aligned to a VP. *Gate:* total
   height = 6.5 head-units; feet on the ground box.
4. **L3 contour.** Wrap the solids in one continuous outline. *Gate:* squint test.
5. **L4 flats.** Skin, jacket=palette.base, trousers=palette.shadow. *Gate:* hexes
   match.
6. **L5 light.** One shadow shape on the −light side of each mass at `shadow_alpha`;
   one rim highlight. *Gate:* single consistent light.
7. **L6 detail.** Two-dot eyes, hair shape, a held object — within budget.
   Promote the eye + hand to the library.

Same figure, **new style**: swap StyleSpec to `fill=soft`, `line=none` → re-skin
L3–L5. Same figure, **new angle**: swap CameraSpec to `one_point` → re-project L1–L2,
re-wrap L3.

---

## Honest limits

- This reliably produces **construction-correct, style-consistent,
  perspective-true** vector — a large step beyond "clean primitives." It does **not**
  by itself conjure an illustrator's freehand organic density; the highest tier
  still benefits from **imported/curated vector parts** flowing into the same
  pipeline (L2/L3 sourced from real assets, then re-styled and re-lit by L4–L7).
- The protocol's value is bounded by spec quality and gate honesty: an
  under-specified StyleSpec or a gate that accepts "good enough" will plateau early.
  The discipline *is* the deliverable.

---

[↑ Back to the project README](../README.md) ·
related: [static/examples/saas_hero_headers.py](../static/examples/saas_hero_headers.py) ·
[src/frameforge/mcp/README.md](../src/frameforge/mcp/README.md)
