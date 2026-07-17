---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 (1M context) via Claude Code"
  date: "2026-07-17"
---

# BHAG — Pixel-perfect composition on a 4K canvas

Operator-directed (2026-07-17). Grounded in PURPOSE.md: *Determinism Over
Accidental Output*, *Validation Over Optimism* — "rendering should be
reproducible, testable, and suitable for automated comparison." The rendered
artifact is the visible result; the **numerically proven** pipeline behind it is
the product. "Pixel-perfect" here is a measured property, never a visual
impression.

Canvas of record: **4K UHD, 3840 × 2160 px** (plus its scale ladder: 1×, 2×).

## The goals (each is a gate, not a hope)

| # | BHAG | Measured by | Target |
|---|------|-------------|--------|
| B1 | **Sub-pixel geometry.** Every authored coordinate lands where authored on a 4K render. | `score_reconstruction` mean edge distance on a calibration probe; `fit_edge` corner recovery | mean_dist ≤ 0.5 px (AA-corrected); corner recovery ≤ 0.1 px |
| B2 | **Seamless composition.** Adjacent/abutting elements (tiles, connector endpoints, clip boundaries, stacked layout children) show no gap or overlap. | seam-probe fixture + pixel scan at 4K | no unintended seam > 0.5 px; connector endpoints touch their anchors |
| B3 | **Determinism.** Same document → same output. | byte-compare SVG across runs; `compare_images` NCC across repeated rasters | SVG byte-identical; NCC ≥ 0.9999 |
| B4 | **Documented precision budget.** Quantization is measured at every stage: float → `fnum` (3-dec) → SVG → Chromium `device_scale_factor` → PNG. | per-stage error measurement in the gate | each stage < 0.1 px at 3840×2160; budget documented, not assumed |
| B5 | **Agent-provable.** An MCP agent can *prove* B1–B3 without a human: render → measure → score, in one loop. | a `pixel gate` runnable via MCP tools / pytest | gate green in CI; failures name the offending object ids |

## Non-goals (Explicit Limits, per PURPOSE)

- Cross-rasterizer bit-identical pixels (Chromium vs cairosvg AA differs; the
  gate scores geometry, not AA fringe).
- Font-glyph pixel identity across hosts (governed by ADR-0004 / font packs —
  text *layout* is in scope, glyph rasterization is not).
- Print (pt) canvases — this BHAG is the px screen ladder; print fidelity is the
  pdf-tex lane.

## Status

- [x] Pass 1 — precision-chain census + defect hunt (2026-07-17; 46-agent
      workflow, every major finding adversarially verified). **Baseline: the
      simple path is already exact at 4K** — 0.0 px authored→SVG delta across
      324 probe attributes, byte-deterministic SVG+PNG, zero grey seams at 1×/2×,
      hairline centroids recovered to 0.0000 px. **42 confirmed defects**
      (5 critical / 27 major / 10 minor; 1 claim refuted) — full evidence in
      [pixel-perfect-pass1.json](pixel-perfect-pass1.json). Gate methodology
      facts banked: CLI `--scale` defaults to 2.0 (a "4K" PNG is 7680×4320 unless
      `--scale 1`), and sub-pixel proof requires coverage-weighted measurement
      (strict color masks see nothing at 50 % AA coverage).
- [ ] Pass 2 — fixes landed (each with a red-first test)
- [ ] Pass 3 — the 4K pixel gate exists and is green (probe fixture + numeric
      assertions)
- [ ] Pass 4 — refine loop rerun until no new confirmed defects (loop-until-dry)
