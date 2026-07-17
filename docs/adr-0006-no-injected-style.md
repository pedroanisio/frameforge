---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-17"
---

# ADR 0006 — The flow renderer injects no undefined style; text defaults resolve from reserved document styles

## Status

Accepted — operator-directed (2026-07-17). Amends the flow-render path introduced
under [ADR-0003](adr-0003-backend-neutral-flow-layout.md) and the backend-neutral
rendering commitment of [ADR-0001](adr-0001-backend-neutral-rendering.md).

## Context

The `mode: flow` renderer (`src/frameforge/rendering/application/renderer.py`,
`_render_flow_pages`) resolved styles correctly for **paragraphs** but, for every
other flow element, discarded the resolved style and fell back to **scattered
hardcoded literals**:

- headings, lists, and TOC entries kept only `color` and inherited a hardcoded
  `base = {family: "serif", color: "#1c1c1c", size: 12, …}` — so a document set
  in Inter rendered serif headings;
- the generated TOC title used a hardcoded `size: 18`;
- tables painted a hardcoded grey chrome (`#f1f3f5` header, `#fafafa` zebra,
  `#d8d8d8` grid, `#222` header text) and a heuristic cell size (`8`/`6.5`),
  ignoring the table's own `style`;
- figure/table captions used a hardcoded `#666` at size `8.5`/`10`.

These literals were **undocumented, unoverridable, and inconsistent**. Two
failures follow. First, **design-system sprawl**: one document rendered 15
distinct font sizes and 11 colours, most of them injected by the engine rather
than authored. Second, and more fundamentally, the rendered output **did not
trace to the document** — you could not audit "what design tokens does this
document use?" because the answer mixed authored values with engine defaults.

This violates the project's stance that output must be a faithful function of the
document (PALS's Law's cousin: an artifact you cannot audit against its source is
a design defect, not a convenience).

## Decision

**The flow renderer renders only what the document defines. It holds no font,
size, or colour literal beyond a single documented fallback.**

1. **The flow default text style (`base`) is document-defined.** It is the
   document's reserved **`body`** style (resolved through the normal token
   cascade, spec §5.2.1). Only when the document defines no `body` style does a
   single documented engine constant apply.
2. **Reserved style names are resolved from the document** via `named(name)`.
   `caption` styles figure and table captions; headings/lists/TOC resolve their
   own `style`. A reserved name absent from the document falls back to `base`.
3. **Tables read all chrome from their `style`**: `header_fill`, `header_text`,
   `cell_text`, `zebra_fill`, `grid_color`, `cell_size`. Chrome the document did
   not define is **not drawn** (no injected borders or fills).
4. **`text_indent` is honored** by the paragraph engine: an explicit
   `text_indent` (including `0`) overrides the positional first-line-indent
   default, so a document can select the modern space-between paragraph style.

No other text/colour/size literal exists in the flow renderer.

## Consequences

- **Auditability is now real.** Because every visual value traces to the
  document, the `--to audit` render target's token census (fonts, sizes,
  weights, colours, features — read off the emitted SVG plus a generic model
  walk; `src/frameforge/rendering/application/audit.py`) is a faithful inventory,
  and its design-system health checks (type-scale-sprawl, palette-sprawl,
  mixed-weight-encoding) are **normative**, not advisory.
- **Reserved-style contract.** Authors define `body` to set the flow default and
  `caption` to style captions (spec §5.2.2). This is now part of the flow
  contract, not an implementation detail.
- **Minimal-by-default.** A document that does not define table chrome renders a
  borderless, fill-less table — the faithful result, not a bug. Chrome is opt-in.
- **Golden oracle re-pinned.** Fixtures that relied on injected chrome/defaults
  re-rendered; `tests/golden/oracle.lock.json` was updated (`make golden`).
  Fixtures without a `body` style are unaffected (they keep the documented
  fallback).
- **Enforcement.** `tests/test_audit.py` plus the `--to audit` health flags guard
  against regression. Any future flow-renderer feature MUST route its defaults
  through the document (a reserved style or an element `style`), never a literal;
  a hardcoded token is an ADR-0006 violation and will surface in the audit.

## Alternatives considered

- **Keep the engine defaults, add a linter.** Rejected: it treats the symptom.
  The defaults are the defect; a document must be able to fully determine its
  output.
- **Put the default in `text_contract`.** Rejected: the `TextContract` model is a
  fitting/overflow contract (`min_font_size`, `overflow`, …) and forbids extra
  fields; the reserved `body` style is the natural, already-cascading home.
