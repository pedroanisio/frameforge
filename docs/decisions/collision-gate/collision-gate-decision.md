---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
    The corpus false-positive counts are reproducible scans against the
    committed fixtures at analysis time; the "~0.62 uppercase advance" is
    an estimate, not a measured Ember value — the O7 gating question in
    §Follow-Ups exists precisely because that must be verified, not assumed.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-07-03"
status: proposal
revision: 2
---

# Decision Analysis: Enforcing the collision model in `make check`

**Decision id:** `collision-gate/2026-07` · **Status:** P0+O1 IMPLEMENTED · rev 2
**Horizon:** core CI infrastructure — multi-year · **Trigger:** `amazon-proxy-2026` page 1 header overlap
**Model (settled):** `docs/spec/viewport-definition-proposal.md`
**Companion visual:** `collision-gate-decision.html` + `diagram-{A,B,C}.svg`

---

## Update — P0 + O1 landed (2026-07-23)

The recommended primary path (**P0 + O1**, advisory) is now implemented:

- **P0** — `overlap: Optional[Literal["allowed"]]` on `ObjBase` (model + schema +
  grammar in sync; default `None` = no consent). Read only by the detector; it
  changes nothing about how an object draws.
- **O1** — a render-time, per-layer, **ink**-based detector in the `Renderer`
  (`_detect_collisions`, fed by the ink rectangle `render_text` stashes). It
  reports same-layer text-on-text overlaps that lack unanimous `overlap: allowed`
  to `diagnostics["collisions"]`, each tagged with the metrics mode
  (`estimate`/`real`, per B4/PALS). Scoped to top-level layer text — table/flow
  cells are excluded (Follow-Up #4 resolved: yes, top-level only).

Surfaces: `sdk.collision_report()`; MCP render results (`diagnostics.collisions`
+ a `render_warning`); the opt-in `validate.py --check-collision [--real-metrics]`
advisory WARN (`collision` code, `docs/error-codes.md`). It is **not** in
`make check` — advisory, non-build-blocking, exactly as the recommendation
specifies.

**Corpus scan (Follow-Up #3, answered):** 531 same-layer ink overlaps across b1,
concentrated in `docusign-deck-v2` (254) and `amazon-proxy-2026` (23) — matching
this doc's prediction. These are the accident-vs-effect retrofit; triaging them
(and promoting O1 to a hard-fail via O7's pinned metrics table) remains the
operator-gated follow-up. **The `amazon-proxy` page-10 header overlap that
triggered this analysis is NOT in this set** — it is a text-overflow from font
substitution (the estimate lays the line out to fit, the substituted face draws
it wider), tracked as its own root cause (GH #88), whose fix is real metrics, not
the collision gate.

## Update — what changed since rev 1

Rev 1 asked *"where can a text-collision gate live?"* and framed collision as a
**legibility** problem (is text-on-text readable?). The design conversation
**settled the model**, and it is not legibility — it is **consent**:

> **Collision = an *unintended* overlap.** Overlap itself is a first-class effect
> (watermarks, captions over images, double-exposure type). The system never
> judges aesthetics. It flags only overlaps that were not stacked on purpose.
> Full definition: `docs/spec/viewport-definition-proposal.md`.

Four consequences reprice this analysis:

1. **Opacity is out.** Rev 1's "Rule B" made the check opacity-aware (occlusion
   resolves, transparency doesn't). The consent model is opacity-blind — it is
   pure volume geometry plus an authored flag. That whole branch is **superseded**.
2. **Cross-layer overlap is exempt by construction.** Collision is a 3D-AABB
   intersection: same `x,y` **and** same `z`-slab (layer). Elements on different
   layers never intersect, however completely they overlap in `x,y`. This
   resolves rev 1's biggest worry — "z-order overlaps are legitimate" — with a
   principled exemption instead of a fuzzy opacity/role heuristic.
3. **A new prerequisite appears (P0):** the model needs an `overlap: allowed`
   attribute (default false, mutually required). That is a schema change, not a
   validator tweak — it reprices the option space.
4. **Rev 1's "O3 authoring gate" is absorbed.** The `overlap: allowed` field *is*
   the authoring mechanism; the old `tabular-box-model` promotion survives only as
   a complementary nudge, not a standalone option.

**Unchanged and reconfirmed:** the measurement finding. Box-overlap floods;
reliable overlap needs rendered **ink**; ink needs layout + metrics; therefore the
check is evaluable only at **render time**. Every reframe has left this intact.

---

## Context

### What is being decided

The *what* is now decided (the consent model above). The open decision is
**how to enforce it in `make check`** — specifically its **placement**
(render-time, where ink exists) and its **determinism/enforcement** level, given
that real ink measurement depends on installed fonts.

### Binding constraints (prune the option space)

- **B1 — the static validator has no fonts and no wrap engine**, and must not
  import the render package. A static geometric check provably floods (below).
- **B2 — `make check` must be deterministic** across machines. The golden and
  overflow gates deliberately run *estimate* metrics mode for this reason.
- **B3 — real glyph advances need fontTools + resolvable fonts**, reproducible
  only inside the font-rich `frameforge` Docker image today.
- **B4 — PALS's Law**: estimate output is unverified by default; the gate must be
  honest about what it actually verified.

### Soft constraints (rank, don't eliminate)

- **S1** — a WARN-only gate gets ignored; hard-fail is preferred *where it can be
  made deterministic*.
- **S2** — minimize coupling of `make check` to Docker.
- **S3** — reuse existing machinery (`render_text`'s real geometry;
  `--check-overflow` telemetry).
- **S4** — the model must be authorable: `overlap: allowed` is how intent is
  declared, not inferred.

### Success axes

Detection reliability · false-positive safety · determinism · enforcement
strength (hard-fail > advisory) · implementation cost · decoupling (from Docker) ·
authorability.

---

## The finding (reconfirmed) — why the check is render-time

A static geometric check on authoring boxes was run four ways against the full
committed corpus (`tests/fixtures` + `b1`), scanned **within each layer**:

| Approach | Metrics | False positives | Why it fails |
|---|---|---:|---|
| Raw box overlap (any two same-layer text) | none | **1090** | boxes are layout regions, routinely bigger than their ink |
| Box overlap + ink-separation suppressor | estimate | **775** | still blind to wrap and real glyph width |
| Per-line ink-box overlap, both axes | estimate | **617** | single-line estimate over-reaches wrapped paragraphs |
| Overlap *within* a detected table grid | none | **floods** | 150-wide cells on 130px centres overlap *by design* |

Under the consent model these same-layer overlaps split into **accidents**
(collisions) and **declared effects** (`overlap: allowed`). Separating them
requires knowing whether the *ink* actually intersects — which a box check
cannot see. The residual noise traces to three render-only facts:

1. **Real glyph widths** — uppercase advances ≈ 0.60, not the fallback 0.52 (the
   proxy's actual cause).
2. **Text wrap** — a single-line estimate calls `"Global Assessment & Impact
   Analysis"` 255px wide when it wraps to fit its box.
3. **Loose / adjacent boxes** — `Age:` next to `62` never touch in ink.

**The proxy defect, measured:** header boxes `[330,232,160,24]` and
`[462,232,90,24]` share a layer and overlap by 28px. Under the renderer's estimate
(0.52×) the ink sits ~7px clear — so estimate-mode `make check` sees nothing.
Under real Ember uppercase advances (~0.62×) the glyphs collide. **The overlap is
the estimate-layout / real-render gap.** Only `render_text`
(`src/frameforge/rendering/application/renderer.py:276`) — which computes
`widest`, `top`, `total_h`, anchor with wrap and real metrics — can see it. The
estimate constant is `src/frameforge/rendering/domain/services/text_fitter.py:36`.

---

## Options Inventory

**P0 is a prerequisite, not an alternative.** The enforcement options (O1/O2/O4/O7)
all sit on top of it.

| # | Option | Kind | Mechanism | Adopt / Abandon |
|---|---|---|---|---|
| **P0** | Add `overlap: allowed` to the model | **prerequisite** | new element attribute (default false, mutually required); schema semver bump + grammar/docs regen. This *is* the authoring mechanism (absorbs rev 1's O3). | S / M · schema change |
| **O1** | Render-time detector, **advisory** | canonical (**recommended first move**) | in `render_text`, per layer, flag same-layer **ink** overlaps where not all parties declare `overlap: allowed`; surface a `collisions` count in `--check-overflow` under `--real-metrics`. Advisory. | M / S · reversible |
| **O2** | Render-time detector, **hard-fail in container** | canonical | same detector, build-failing — deterministic only inside the `frameforge` image; bare-host `make check` skips it. | M / S · couples Docker |
| **O4** | **Two-mode tiered** detector | hybrid | run under *both* estimate and real metrics. **Hard-fail** on same-layer ink overlaps present under the estimate layout (deterministic, env-independent). **Advise** on real-only overlaps (the estimate↔real gap). | M/L / S |
| **O7** | **Vendor a pinned metrics table** | orthogonal | ship vetted glyph advances for the fixture faces (or one canonical metrics font), making real ink reproducible off-Docker. **Dissolves B3**, promoting O1's advisory count to a deterministic hard-fail everywhere. | L / S · enables O2 / O4-hard |
| **O6** | Defer enforcement; ship P0 + fixture fix only | deferred | land the model + fix the proxy now, defer the automated gate until O7 is decided. Weaker now that the model is settled — the gate is the only thing being deferred. | XS / — |
| **O5** | **P0 ⊕ O1 ⊕ fixture fix** | composition | the recommended combination (see Recommendations). | — |

The proxy is an **accidental** same-layer overlap, so its fix is a **geometry
correction** (separate the header boxes) + re-pinned golden — *not* an
`overlap: allowed` flag (nothing about it was intended).

---

## Implication Map (enables / degrades / blocks)

- **P0** — *enables* every other option, and makes intentional overlaps
  first-class (authored, not fought). *Degrades* nothing. *Costs* a schema bump +
  the regen chain. Existing intentional **same-layer** overlaps must be flagged;
  cross-layer effects need nothing (exempt).
- **O1** — *enables* immediate visibility of accidental overlaps and a clean path
  to O7-hard. *Degrades* enforcement (an ignored advisory count is fatigue, S1).
  *Blocks* nothing; fully reversible.
- **O2** — *enables* real enforcement now. *Degrades* local↔CI parity (bare-host
  green, container red). *Blocks* a Docker-free contributor loop.
- **O7** — *enables* deterministic hard-fail collision *and* overflow gates
  everywhere; removes the estimate↔real blind spot from all gates. *Degrades*
  nothing structurally; adds a vetted-metrics maintenance surface. Highest payoff,
  highest unknown-risk surface.

---

## Composition Analysis

P0, O1, and O7 **compose** as layers: P0 gives the vocabulary, O1 enforces it
advisorily, O7 makes the enforcement deterministic and off-Docker.

- **Composes:** P0 → (O1 | O2 | O4) · O7 → O1-hard · O7 → O4-hard.
- **Conflicts:** O2-alone (hard-fail without O7 ⇒ local/CI divergence) ·
  O6 (defer ⇒ tension with fix-root-causes, now that the model is settled).
- **Orthogonal:** the `tabular-box-model` WARN (a complementary authoring nudge)
  to all of the above.

---

## Risk Landscape

- **P0 — the retrofit is the cost.** Default-false means every *intentional
  same-layer* overlap in existing docs must be flagged or it reads as a collision.
  Cross-layer effects are exempt, so the burden is smaller than rev 1 implied — but
  the corpus still has hundreds of same-layer ink overlaps (concentrated in the
  auto-traced `docusign` fixture and the proxy). Triage them: accident → fix;
  effect → flag.
- **O7 — highest unknown-risk, highest payoff.** A wrong metrics table
  re-introduces the estimate↔real gap it closes. Does a pinned advance table match
  Chromium's shaping (kerning, ligatures, fallback chains)? Must be **vetted
  against real renders**. Failure mode: silent wrong verdicts.
- **O2 — brick wall for bare-host contributors.** Unknown: font-resolution drift
  across base-image updates silently changing verdicts.
- **O1 — speed bump only.** Misses stay misses; it never false-fails a build.
- **O4 — complexity.** Two layout passes and a two-tier verdict; unknown whether
  estimate-mode same-layer overlaps are common enough to justify it.

---

## Recommendations

Not a single pick — a decision function.

### Primary: **P0 + O1 now, O7 as the funded follow-up**

1. **P0** — add `overlap: allowed` to the model (default false, mutual); bump the
   schema, regen grammar/docs.
2. **O1** — a render-time, per-layer, ink-based detector that flags same-layer
   overlaps lacking unanimous `overlap: allowed`, as an advisory `--check-overflow`
   count under `--real-metrics`.
3. **Fix the proxy** by geometry (separate the header boxes) and re-pin the golden
   — it is an accident, not an effect.

Nothing here can false-fail the build. Then schedule **O7**: vendor a vetted
metrics table (gated on the Follow-Up below); once real ink is reproducible
off-Docker, flip O1's advisory count to a hard-fail — full enforcement, no
container coupling. This is the path **O2 wishes it were.**

### If your priorities differ

- **Ship now with zero build-blocking risk** → P0 + O1 + fix *(the recommendation)*.
- **One deterministic hard-fail everywhere, will fund the metrics work** → P0 + O7,
  then O1-hard / O4-hard. Highest rigor; vet the table first.
- **Land the model but not the gate yet** → P0 + fixture fix (O6). Acceptable only
  if O7 (or O1) is actually scheduled — otherwise the accident class stays undetected.
- **`make check` already runs in-container for other gates** → O2 becomes cheap;
  its coupling cost is already paid.

### Avoid

- **O2 alone** — Docker-coupled hard-fail ⇒ local/CI split.
- **A gate before P0** — with no `overlap: allowed`, every intentional same-layer
  overlap is a false positive.

---

## Follow-Up Questions

1. **Fixes the model's crux — is `z`-slab = layer container?** The definition maps
   "same layer" to the same `page.layers[]` container. Confirm that (vs. a
   continuous per-object `z`), since it decides what counts as a same-layer
   intersection. This is the one open question in the definition doc.
2. **Gates O7 — is a vendored table faithful?** Render one fixture in-container
   (real metrics) vs. a candidate pinned table and diff the collision verdicts.
   Disagreement ⇒ O7 not yet safe.
3. **Sizes the P0 retrofit — how many *same-layer ink* overlaps survive in the
   corpus?** Re-run the scan with the ink refinement and cross-layer exemption to
   get the true count of docs needing `overlap: allowed` (rev 1's 617 is an
   estimate-mode upper bound).
4. **Scopes the detector — top-level layer objects only?** Confirm it excludes
   Table/flow cells (their engines lay out without overlap). A one-line guard in
   `render_text`'s caller.

### Deep-dives available on request

- Spec the `overlap: allowed` model field (schema shape, mutual-declaration semantics).
- Stress-test O7 against Chromium fallback-chain shaping.
- Map the O1 → O1-hard migration once O7 lands.
- Triage the corpus's same-layer ink overlaps into accident-vs-effect.
