# Decision analysis — text-collision gate (`collision-gate/2026-07`)

Working architectural decision analysis (not a committed ADR) for **how to enforce
the collision model** in `make check`. Triggered by the visible header overlap in
`tests/fixtures/b1/amazon-proxy-2026.fg.json` (page 1), which no gate alarms on.

The **model is now settled** (`docs/spec/viewport-definition-proposal.md`):
collision = an *unintended* overlap; overlap itself is a first-class effect, gated
by consent, not legibility. This analysis (rev 2) is about enforcement placement.

**Status:** open · analysis · rev 2. **Author:** Claude Opus 4.8 via Claude Code · 2026-07-03.

## Contents

| File | What it is |
|---|---|
| [collision-gate-decision.md](collision-gate-decision.md) | the report — context, evidence, 7 options, composition, risk, recommendation, follow-ups |
| [collision-gate-decision.html](collision-gate-decision.html) | the same analysis as a self-contained visual page |
| [diagram-A-option-space.svg](diagram-A-option-space.svg) | option-space map (relationships between the 7 options) |
| [diagram-B-enables-blocks.svg](diagram-B-enables-blocks.svg) | downstream consequences (enables / degrades / blocks) |
| [diagram-C-decision-matrix.svg](diagram-C-decision-matrix.svg) | 5-option × 7-axis scoring heatmap |
| `diagram-{A,B,C}-*.png` | rasterized previews of the SVGs |

## The one-line finding

Collision = a same-layer overlap not unanimously declared `overlap: allowed`
(cross-layer overlap is an exempt effect). A static box-geometry check provably
floods — 1090 → 617 false positives across four variants — because a box is a
layout region, larger than its ink; reliable detection needs the renderer's real
wrapped, measured ink, which only exists at render time. The recommendation is
**P0 + O1** (add the `overlap: allowed` model field, plus an advisory render-time
same-layer ink detector), with a funded follow-up (**O7**, vendor a vetted metrics
table) that promotes the advisory count to a deterministic hard-fail without
coupling `make check` to Docker.
