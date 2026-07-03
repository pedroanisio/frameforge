---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-02"
---

# ADR 0003 — Backend-neutral flow layout (Knuth–Plass + hyphenation)

## Status

Accepted. Slice 1 (the flow-mode prose column) is implemented and gated. The
page-mode text-box wrap path and the LaTeX painter wiring are staged (below).

## Context

[ADR 0001](adr-0001-backend-neutral-rendering.md) made **drawing** backend-neutral
(the `ScenePainter` port: `Stroke`, `Markers`, transform ops, fills) but left
**layout** inside each backend. The flow pager (`renderer.py::_render_flow_pages`)
proved the cost:

- a **hard-coded symmetric `margin = 56`**, ignoring the master's `regions`/`margin`
  — so the flowed body never honoured the authored geometry and never mirrored
  recto/verso (while the running-header furniture, drawn from the master, did:
  headers flipped sides, the body did not);
- **estimated, greedy, left-aligned** wrapping (`cpl = usable / (size*0.52)`),
  which cascades one bad break into loose lines and cannot hyphenate.

The result was lopsided margins and, when justified, rivers. Two backends running
two layout algorithms means **one document has two layouts** — the defect the
operator refused to accept.

Hand-placing each word to justify does not fix it: positions computed from one
metric, painted by a rasterizer that shapes with another, drift into uneven gaps.
You cannot out-position a shaper you do not control.

## Decision

Introduce a **pure, backend-neutral flow layout engine**
(`rendering/domain/services/flow_layout.py`) that owns the two decisions a
rasterizer cannot make for you, and delegates the one it makes better:

1. **Line breaking — Knuth & Plass total-fit** (*Breaking Paragraphs into Lines*,
   Software: Practice and Experience 11(11):1119–1184, 1981): minimise the sum of
   squared line badness over the whole paragraph, so no single break cascades.
2. **Hyphenation — Liang patterns** via `pyphen` (F. M. Liang, *Word Hy-phen-a-tion
   by Com-put-er*, Stanford, 1983): absorb slack by breaking a long word instead
   of opening a river. Absent `pyphen` the engine still runs, unhyphenated.
3. **Geometry — `content_box`**: the column resolves from the master in priority
   order **explicit region box → master margin → the Johnston canon**
   (inner 1½ / top 2 / outer 3 / foot 4, mirrored recto/verso).
4. **Intra-line spacing — delegated to the shaper.** The engine emits a positioned
   IR of `LaidLine`s (text + indent + advance + width + `justify`); the painter
   renders **one text element per line** and justifies via SVG
   `textLength`+`lengthAdjust="spacing"`, so a real shaper distributes the slack
   with its *own* metrics. **Own the breaks, delegate the spacing.**

Line and hyphenation breaks are the backend-neutral, pagination-determining
decision and are identical across backends; only sub-pixel intra-line spacing
differs by backend — the correct boundary.

## Consequences

- Flow-mode prose now: honours the master's column and **mirrors recto/verso**;
  breaks optimally; **hyphenates**; sets **flush-justified on browser/PDF** and
  **tight, hyphenated ragged on the cairosvg proxy** (which ignores `textLength`).
  A first-line indent and zero inter-paragraph gap give the book column.
- **Cross-backend proof:** the `neutron-stars` fixture's IR renders with identical
  breaks through cairosvg (rag) and Chromium (flush) — verified by screenshot.
- **`pyphen`** added as a runtime dependency (pure-Python, bundles dictionaries,
  deterministic → golden stays reproducible).
- **Golden re-pinned** for the four flow fixtures (`ieee-reference-guide`,
  `neutron-stars`, `spectral-methods`, `chroma-styling-showcase`) — a deliberate,
  reviewed output change per ADR-0001's re-pin budget; the four page-mode decks
  are byte-unchanged.
- **Font caveat (honest limit):** tight *flush* justification needs the layout
  metric and the render font to be the **same** face — pin the body font (a
  `FontDef` with `src`+`hash`) so `measure` and the shaper agree. Unpinned, flush
  over-stretches (uniformly airy, not rivers); the cairosvg tight-rag is the safe
  universal default.

## Staged (not in slice 1)

- **Page-mode text boxes** (`{"type":"text","box":…,"wrap":true}`) still use the
  renderer's own box wrapping — this is the path hand-paginated books
  (`build_interior.py`-style) use, so they do **not** yet get KP/hyphenation.
  Unifying it through this engine is correct but has a large golden blast radius
  (~1077 wrapped boxes across the corpus re-pin), so it is a dedicated slice.
- Full KP **fitness classes** and optical-margin refinement.
- **LaTeX painter** wiring (toolchain-gated, as in ADR-0001 §3b-5).

[↑ Back to root README](../README.md)
