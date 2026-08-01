---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-03"
  last_revised: "2026-07-27"
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
   render resolve the identical file. This is operationalised by **`fg-font`** (the
   `fg-font` console script, `frameforge.fontpack:main` in `src/frameforge/fontpack.py`;
   `tooling/fg_font.py` is a thin launcher): `--list` the runtime's resolvable families, `--check DOC`
   as a determinism gate (non-zero exit if any content font substitutes), and
   `--pack DOC --out P.fp` — a portable font pack (zip of the exact TTFs + a
   `manifest.json` of family→file→sha256) that an *external* renderer points both
   its rasterizer and `font_metrics` at, so measure == render on any host without
   the 9 GB image. `--pack --fetch` closes the last gap: a family the *authoring*
   host lacks is provisioned from the open `google/fonts` corpus and stamped
   `source: "google-fonts:<slug>"` in the manifest, so a pack is reproducible from
   a thin machine, not only the font-rich image. This makes the model's existing
   pinned-`FontDef` (src+hash, §9.6) enforceable rather than aspirational.

4. **Author-time and proxy-layout measurement select one mode.** The SDK
   `measure_text`/`fit_width`, renderer, validator, and MCP pipeline must resolve the
   same `real_metrics` choice and full CSS family stack. Estimate mode is the
   deterministic default for SDK/CLI authoring; explicit real mode (or the shared
   environment opt-in) is threaded through validation and rendering. `fit_width`
   is the positioned-box contract: measured advance plus the renderer's published
   fit tolerance. MCP `fit_text` exposes both values before geometry is authored.

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
- Optional fontTools installation no longer changes only one side of the authoring
  contract: author-time measurement and proxy line breaking always select the same
  provider/mode. This prevents avoidable box drift without claiming cross-rasterizer
  fidelity.
- This amends the SVG-primary core commitment **for flow fidelity only**; SVG
  stays primary for fixed page-mode vector output where measure≠render does not
  arise (absolute-positioned text is not re-flowed).

## Progress

**Done — the HTML backend renders flow.** It was a standalone transform that
drew 13 of the model's 34 object types and replaced a `mode: flow` page with a
labelled "profile not rendered" note. It is now driven by the shared `Renderer`
through `HtmlPainter`
(`src/frameforge/rendering/infrastructure/painters/html.py`), with
`…/backends/html.py` reduced to the document shell. Consequences for this ADR:

- Flow documents typeset in HTML: page masters, running heads, tables and TOC all
  arrive from the shared builder, because HTML no longer has an opinion about
  them. Object-type parity with SVG is now *structural* and gated
  (`tests/test_html_backend_parity.py`).
- The measure≠render problem this ADR names is **unchanged**. HTML output is
  still measured with `font_metrics` and rasterised by a browser, so it remains a
  proxy in exactly the sense described above. Sharing a builder removed the
  *backend* divergence, not the *engine* divergence.

## Not yet done (the real project this ADR names)

- CSS paged-media output → Chromium PDF, so the engine that measures is the
  engine that paginates.
- Route `run`/`--to pdf` for flow documents through the single engine, leaving SVG
  as the explicit `--to svg` proxy.

[↑ Back to root README](../README.md)
