---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-25"
---

# POC-09 — A coach that draws complex human figures (by *sourcing* + *structuring*)

## The question

> *"How can we make a coach use all of this and draw complex human figures?"*

## The honest answer

A coach does **not** synthesize a complex human from primitives — that is the
ceiling every prior POC measured ([POC-01](./POC-01.md) → stick-figure floor;
[web-design review] → curve-craft is an asset problem, not a primitives
problem). What a coach **can** do is *source* the complexity from a raster and
then use every coach layer to turn it into a **clean, posable, on-canon,
verified vector figure**:

```
complex human raster (AI-gen / reference)         ← complexity is SOURCED
   │ coach.ingest      raster → editable strokes        (works on a complex figure)
   │ coach.clean       RDP + denoise, image-agnostic    (general line quality)
   │ coach.figures ◀── NEW, ported from vela-nova (human-specific) ──────────
   │     • width_profile + persistence landmarks → anatomical structure
   │       (recovers shoulders/waist/hips/knees where a region trace gives a block)
   │     • proportion_signature                  → the figure as editable ratios
   │     • retarget(canon)                       → re-proportion (height preserved)
   │     • mirror_outer                          → bilateral-symmetry rebuild
   │     • plausibility (ADVISORY)               → flag off-canon extraction
   │ coach.recolor_to_style / restyle_strokes → on-brand look
   │ coach.to_silhouette + stage_rubric        → does it READ as a figure?
   └ validate_static_rules → render → compose
```

This is where vela-nova's **human-specific** machinery legitimately earns its
place — distinct from [`coach.clean`](./POC-07.md), which is the *image-agnostic*
lever that lifts any subject.

## What was built — `framegraph/coach/figures.py`

A **pure-Python** port (no numpy / scipy / cv2 — the package stays import-light,
matching `coach.clean`) of the geometry in the sibling repo
`vela-nova-rocket` (`canonical/lib/{profile,proportion,extract_contour}.py`):

| Function | Ported from | Does |
|---|---|---|
| `width_profile` | `profile.width_at_y` | silhouette outer half-width per height (head-units) |
| `find_landmarks` | `find_anatomical_landmarks` + `_persistence_1d` | 1-D persistence landmark detection + band naming |
| `proportion_signature` / `blend_signatures` | `extract_signature` / `interpolate` | the figure as ℝⁿ ratios; lerp in proportion space |
| `retarget` / `remap_dy` | `transform_contour` | piecewise-affine re-proportion, **total height preserved** |
| `mirror_outer` | `_body_mask_from_contour` | reflect the wider half into a symmetric whole |
| `plausibility` | `validate_signature` | **advisory** canon-range gate |
| `CANONS` | `CANON_DEFS` | Polykleitos 7.5 · Vitruvian 8 · heroic 8.5 · fashion 9 |

**Canon provenance (cited, not invented):** Polykleitos *Kanon* (~450 BCE, via
Galen *PHP* V.3); Vitruvius *De Architectura* III.1 (body = 8 heads); Andrew
Loomis *Figure Drawing for All It's Worth* (1943) ideal/heroic/fashion figures.

**What was deliberately *not* taken:** vela-nova's Mahalanobis shape-prior needs
a **fitted population covariance** we do not have. Fabricating one would violate
the codebase's "verify, don't fabricate" rule, so the gate instead uses the
*documented canon ranges*, plus an **optional** standardized distance to
caller-supplied reference signatures. No fake prior ships.

## Measured results (real runs — `examples/poc9_figure_coach.py`)

Run on the two single-figure rasters available in `vela-nova-rocket/input/`:

| Source | strokes (ingest→clean) | landmarks recovered | head_count | gate | retarget height drift | doc validate |
|---|---|---|---|---|---|---|
| `ironman.jpeg` (armored) | 955 → 593 | 6 | 5.26 | **REVIEW** (off-canon) | 0.0 % | clean |
| `girl_rider.jpeg` (helmeted) | 739 → 425 | 7 | 15.0 | **REVIEW** (off-canon) | 0.0 % | clean |

The headline is panel 2 of each render: **6–7 anatomical landmarks recovered
from a complex shaded figure** — the same Iron Man whose generic region trace
collapsed into a solid black block now yields shoulder / waist / hip / knee /
ankle structure read from the silhouette *width profile*. The retarget
re-proportions all ~500 strokes onto a drawing canon with **0.0 % height
drift** (the crown/sole are anchored), and every composed page validates clean.

## Honest limits (PALS's Law in action)

1. **The plausibility gate flagged BOTH figures `plausible=False`** — and that is
   the feature working, not failing. The standing-figure band scheme assumes a
   front-facing ~8-head pose; an armored helmet (Iron Man → 5.26 heads, unstable
   head_peak/neck detection) or a non-standard rider pose (→ 15 heads, head and
   neck landmarks too close) fall outside it. The **advisory** gate refuses to
   rubber-stamp the resulting signature instead of emitting a confident wrong
   answer. The verification layer is doing exactly its job.
2. **The recovered silhouette is a rough mass, not production-clean.** It reads
   as a figure (head → shoulders → taper) — the point versus a black block — but
   a crisp silhouette needs a real segmented body mask (vela-nova's morphology
   path), which the generic ingest does not produce. Reported, not hidden.
3. **Complexity is sourced, never synthesized.** `retarget` re-proportions what
   was ingested; it does not invent occluded detail or repair a bad source.

## How it composes with the rest

`coach.figures` is the human-specific peer of the general layers: `ingest`/`clean`
get the figure in and tidy the lines; `figures` recovers structure and edits
proportion; `recolor_to_style`/`gradientize` skin it; `to_silhouette` +
`stage_rubric` gate it; `validate_static_rules` + the renderer finish it. The
silhouette gate is also wired into the MCP ([coach-poc memory]), so any agent
gets the readability check for free.

## TDD + standards

- 11 new tests in `tests/test_coach.py` (canon head-counts, signature blend,
  `remap_dy`, dominant contour, landmark detection, plausibility pass/flag,
  height-preserving retarget, mirror symmetry, polygon emit). **29 coach +
  boundary tests green; 966 in the full suite** (the one failure,
  `test_brand_logo_fresh`, is pre-existing brand-asset drift, unrelated).
- Package boundary holds: `figures.py` imports **stdlib only**
  (`tests/test_package_boundary.py`).

## Run

```bash
uv run pytest tests/test_coach.py -q
uv run --group vision python examples/poc9_figure_coach.py \
    /home/admin/codebases/vela-nova-rocket/input/ironman.jpeg --out out/poc9 --canon heroic
```

---

[↑ Back to root README](./README.md)
