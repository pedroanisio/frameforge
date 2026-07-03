---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-03"
---

# ADR 0004 — Single-engine layout for fidelity output; SVG + `font_metrics` is a labeled proxy

## Status

Proposed. Amends the "SVG is the primary output" core commitment
(`docs/codebase-standards.md`) for the **flow-fidelity** case.

## Context

**There was no decision record for making `html` legacy / SVG primary.** The
choice lives only as a bare *core commitment* — `docs/codebase-standards.md`:
"SVG is the primary output; **pure-Python, dependency-free core rendering** stays
first-class" — and a label, `docs/output-space.md` / `cli.py`: "HTML/CSS
(legacy; documented flow/gradient limits)". No ADR ever weighed **single-engine**
layout (the rasterizer also measures, breaks, and justifies) against the
**two-tool** split that SVG forces. The stated motive (no browser dependency in
the core) is real — but it *structurally requires* measure-time ≠ render-time.

**Why that is the root defect.** SVG `<text>` has no native line breaking. So the
flow/text layout is computed at **measure time** by `font_metrics` (fontTools +
`fc-match`) and then rasterized at **render time** by a *different* engine
(Chromium/Pango, cairosvg, or LaTeX). Two independent font resolvers cannot be
kept in agreement:

- `fc-match "Charter"` fuzzy-returns **Noto Sans** (an unrelated face), so
  `font_metrics` measured Noto Sans; Chromium walked the CSS chain and drew
  **Bitstream Charter**. Justified lines were broken for one font and rendered in
  another → every line stretched by a different amount (the "still differs"
  spacing variation), even in Docker.

No `fc-match` patch closes this. It is a category: *if measure and render use
different engines, they will drift* — per font, per environment, forever. That is
the correct reading of the reporter's objection.

## Decision

1. **Fidelity flow output is single-engine.** Justified/hyphenated books and PDFs
   render through an engine that measures, breaks, justifies, **and** rasterizes
   with one set of metrics: HTML/CSS via Chromium (`text-align: justify;
   hyphens: auto`, a real/embedded font), or LaTeX. `font_metrics` / Knuth–Plass /
   `textLength` are **not** in the fidelity path.

2. **SVG + `font_metrics` + KP is a *labeled proxy*, not a fidelity target.** It
   is kept for what it is genuinely good at — a dependency-free preview, the
   deterministic golden lock, and pagination estimates — and it MUST **scream**
   (a `font_substitution` warning, emitted to diagnostics *and* stderr, once per
   family) whenever a requested concrete font is not installed, because at that
   point its measurement matches no rasterizer. Silent substitution is banned
   (this is PALS's Law applied to fonts: an unverified measurement is a defect).

3. **Fonts are pinned/baked, never trusted from the host.** Fidelity renders embed
   the face or run in the frameforge Docker image (baked fonts) so measure and
   render resolve the identical file.

## Consequences

- The **`html` target is promoted** from "legacy" to the fidelity path for flow;
  its documented flow/gradient limits become work to do, not a reason to prefer a
  structurally-divergent SVG path for prose.
- **ADR-0003's `flow_layout`** is correctly re-scoped: it is the SVG-**proxy**
  layout + pagination estimator, now honest because it warns on font substitution.
  Its output is *not* the book.
- The interim `font_metrics` fix (walk the chain browser-faithfully; reject
  fontconfig's fuzzy fallback; fall through to the next installed family) reduces
  proxy divergence but **does not remove it** — only single-engine does.
- This amends the SVG-primary core commitment **for flow fidelity only**; SVG
  stays primary for fixed page-mode vector output where measure≠render does not
  arise (absolute-positioned text is not re-flowed).

## Not yet done (the real project this ADR names)

- Make `tooling/framegraph_to_html.py` a first-class flow renderer (page masters,
  running heads, tables, TOC, CSS paged-media) → Chromium PDF.
- Route `run`/`--to pdf` for flow documents through the single engine, leaving SVG
  as the explicit `--to svg` proxy.

[↑ Back to root README](../README.md)
