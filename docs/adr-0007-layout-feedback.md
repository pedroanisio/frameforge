---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-22"
---

# ADR 0007 — Layout feedback closes its own loop: a separation solver for what the audit flags, typed signals for what the measure pass proves

## Status

Accepted (2026-07-22). Extends the issue-#44 truncation-diagnostics contract and
gives the §3.3 scoped non-overlap audit its missing counterpart.

## Context

Two detect-without-act gaps existed in the layout feedback loop:

1. **Overlap was detected but never solved.** The static audit
   (`tooling/validate.py` `_free_group_overlap`) WARNs (`overlap`) when
   box-bearing children of a free-layout group or a `meta.no_overlap: true`
   cluster overlap by more than 10 % of the smaller box AND more than 100 px².
   Nothing in the tree could *fix* the finding — authors and agents nudged
   boxes by hand, iterating render-inspect-move.
2. **Overflow was priced but only partially reported.** The truncation records
   named content the containment net *discarded*, but two classes of provable
   does-not-fit stayed invisible per object: `overflow: visible` spill (only
   the aggregate `tstats["visible_overflow"]` counter) and flow-mode lines the
   Knuth–Plass engine emitted wider than their column
   (`flow_layout.py` admits an unbreakable box at badness `1e5 + (L − target)`
   — legal, internal, unreported).

Prior art shaping the decision: the truncation-diagnostics contract (records
ride `diagnostics`, never alter SVG bytes), `sdk.humanize` (dict-in/dict-out,
deterministic, identity-when-absent doc transforms), and the boxwood layout
engine's design review (2026-07-22), which surfaced both gaps.

## Decision

### 1. `sdk.separate` — an audit-scoped separation solver

- `separate_rects(rects, *, world, gap, movable, max_passes)` — a pure,
  deterministic AABB kernel: iterative pairwise relaxation along the axis of
  minimum penetration; wall-aware push redistribution (a partner flush against
  the world wall hands its share to the other mover, so chains resolve exactly
  rather than converging geometrically); **feasibility-aware axis choice** (a
  wall-blocked cheaper axis falls back to the axis that can actually resolve
  the pair — a room-blind rule burns passes on zero-progress pushes); world
  clamping; passes terminate on zero measured progress, and bounded
  `max_passes` means over-constrained input returns with residual overlap
  instead of hanging.
- `apply_separation(data, *, gap, max_passes)` — moves ONLY what the audit
  flags: box-bearing, non-decorative children of free-layout groups /
  `meta.no_overlap` clusters containing at least one audit-level overlap.
  Solving a flagged cluster resolves *all* positive overlaps in it (plus
  `gap`), clamped to the group's own box (`[0, 0, gw, gh]`, parent-local).
  Global/layer overlap is z-order layering (§3.3) and is never touched.
  Sub-threshold overlaps are a design idiom the audit tolerates — the solver
  tolerates them too. Absence is identity: a clean document returns the same
  object.

### 2. Typed layout-overflow signals — `diagnostics["overflow"]`

- A frozen dataclass `OverflowSignal`
  (`rendering/domain/services/overflow.py`): `id`, `page`, `source`
  (`text` | `flow`), `kind` (`width` | `height` | `lines`), `policy`, `box`,
  `needed`, `acknowledged`, `detail`. Wire form is `to_dict()`; `from_dict`
  restores the typed value.
- The renderer emits signals at measure time, before any pixels: contained
  clips (alongside their existing truncation record, unchanged), visible
  spill (per object, previously counter-only), and flow overwide lines
  (per line, natural width re-measured because `LaidLine.width` is the
  justify target). keep_together trial layouts are skipped; the flow
  dry/real double pass needs no guard — `_render_flow` already rolls the dry
  pass's diagnostics back.
- Propagation reuses the existing chain unchanged: renderer →
  `render_pages_with_stats(diagnostics=True)` → MCP result
  `diagnostics.overflow` + session `diagnostics.json`. Additions:
  `sdk.overflow_report(model)` returns typed signals; the MCP
  `render_warning` names *unacknowledged* signals only (an authored
  `overflow: visible` stays a record, not a nag); `validate.py --text-fit`
  surfaces the non-truncation signals as advisory `layout-overflow` WARNs.

## Consequences

- The authoring loop closes without pixels: audit flags → `apply_separation`
  fixes → audit goes quiet; measure proves → signal names the object, the
  needed extent, and whether the author opted in.
- Golden fixtures cannot move: signals never alter rendered bytes; the solver
  runs only when explicitly called.
- The solver is local relaxation, not global optimisation: it does not
  minimise total displacement, and label-to-anchor leader-line aesthetics are
  out of scope for this record. `emit()`-path flow furniture (headings, list
  items) uses the legacy char-count wrap and does not yet signal — the KP
  paragraph path does.
- New surfaces are gated: `layout-overflow` documented in
  [error-codes](error-codes.md), exports docstring-gated, capability manifest
  regenerated, example client
  (`static/examples/declutter_and_overflow.py`) in the cookbook.

## Verification

`tests/test_sdk_separate.py` (21 tests: kernel identity/determinism/purity,
minimum-penetration axis, immovable rects, gap clearance, world clamping,
over-constrained termination; doc-level audit convergence, decorative/global
exemptions, nested groups, model round-trip) and
`tests/test_overflow_signals.py` (12 tests: dataclass contract, all three
signal classes, channel-always-exists, truncation/tstats regression guards,
SDK/MCP/CLI propagation tiers).
