---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-06-24"
status: proposal
---

# FrameGraph — Brand Guideline (proposal)

> **Status.** This is a *proposed* brand identity, in the same spirit as the
> format itself: a design target to verify, not a ratified standard. It is
> **derived from existing evidence in this repository**, not invented — every
> pillar below cites the source it was extracted from. Treat it as a pull
> request against the project's identity, open to revision.

This guideline governs how FrameGraph presents itself: its product definition,
name, voice, color, type, and mark. The essence and positioning in §1 are
anchored to the FrameGraph seed pitch
([`FrameGraph-Seed-Pitch.pdf`](FrameGraph-Seed-Pitch.pdf)) — the outcome-first,
agent-era framing — with the system's rigor recast as the *proof* of that
promise rather than the pitch. It inherits the project's epistemic stance from
[`DISCLAIMER.md`](../DISCLAIMER.md) and its operating constraints from
[`CLAUDE.md`](../CLAUDE.md) — the brand is the outward face of those rules, not a
separate marketing layer.

---

## 1. Essence

**FrameGraph is the output layer for the agent era.**

AI learned to *read* the world — screens, documents, images. The unclaimed half
is *output*: turning what a machine intends into a real, finished, trustworthy
artifact a business can actually send. FrameGraph is that layer. You — or your
AI — describe what you want, or point it at your data; FrameGraph assembles the
artifact, **checks it the way a meticulous proofreader would**, and renders a
real file — a slide, report, web page, chart, or image — at any quality from a
quick sketch to print-ready. The output is **correct, on-brand, and yours**: an
open file you own and can edit by hand, not a dead-end image you can only
re-prompt. *(Definition sharpened from the seed pitch —
[`FrameGraph-Seed-Pitch.pdf`](FrameGraph-Seed-Pitch.pdf).)*

> *Spell-check and a printing press — for everything AI makes that you can see.*

**Positioning (Moore template, with a namable "unlike").** *For* businesses and
the AI agents acting for them *who* need a finished visual artifact they can
trust without a human checking it, **FrameGraph is** an output layer *that* turns
intent — or data — into a correct, on-brand, editable file. *Unlike* image
generators (a dead-end you can only re-prompt) or code-it-yourself AI (output
that *looks* right but breaks — text overflows, layouts collapse), FrameGraph
hands you an open file you own and proofreads every render, so it ships
unattended, at volume.

The rigor in the pillars below is **not the pitch; it is the proof** that
"correct, on-brand, and yours" is true rather than asserted — one typed source
makes the output reproducible (same input, same file, every time, so it plugs
into real systems), and gated verification is what lets a machine produce it at
scale without a human checking each one.

The name is two halves, and the brand keeps them visible:

| Half | Meaning in the model | Brand register |
|---|---|---|
| **Frame** | the fixed page / canvas / bounding box | structure, ink, the drafting grid |
| **Graph** | the typed object & flow tree (the directed document) | signal, flow, derivation |

### Brand pillars (each grounded in a live artifact)

1. **Source of truth.** One authoritative model; everything else generated or
   checked. — *README "sync guarantee"; `Document.model_json_schema()` → `schema/`.*
2. **Provenance over assertion.** Every claim cites; nothing is taken for granted.
   — *`DISCLAIMER.md`; CLAUDE.md §2 "Formalization means research".*
3. **Honest limits.** Says "proposed," "sanity check, not a fidelity guarantee,"
   "don't overclaim." — *README "Honest limits".*
4. **Gated, not trusted.** Drift fails a gate, loudly. — *`make check`; the golden lock.*
5. **Verification is architecture.** Output is untrusted by default.
   — *CLAUDE.md "PALS's LAW".*

### Personality

A **precision instrument that ships finished work.** The brand *chrome* stays
quiet — drafting table, not billboard — but the *output* is the showroom: a
rendered FrameGraph artifact should look as finished as it is correct. Confident
because it is grounded in a working system ("not a concept — a working system"),
and honest about what is still proposed in the *format* — never hedged about the
*result* it produces.

---

## 2. Name & wordmark rules

- The product is **FrameGraph** — one word, capital `F` and capital `G`, camel-joined.
- Versioned as **FrameGraph v2** or **FrameGraph 2.2.0** (semver, per the repo).
- The file/format extensions are `.fg.yaml` and `.framegraph.yml`.
- `FG` is the internal Pydantic base class and an acceptable square-logo monogram —
  it is **not** a public short name for the product in prose.

**Never:** `Frame Graph` (two words) · `Framegraph` (lowercase g) · `frameGraph` ·
`FRAMEGRAPH` (except inside a fixed-width ASCII/CLI banner) · "the FrameGraph framework"
(it is a format + toolchain, not a framework).

---

## 3. Logo

Two assets ship in [`brand/`](../brand/):

- [`brand/framegraph-mark.svg`](../brand/framegraph-mark.svg) — the icon.
- [`brand/framegraph-wordmark.svg`](../brand/framegraph-wordmark.svg) — the horizontal lockup.

**The mark is the thesis, drawn.** Technical-drawing corner brackets (the *Frame*:
a fixed page / bounding box) enclose a small derivation graph (the *Graph*): one
filled **source node** fanning out to three outlined **derived nodes**. That is
literally the project's architecture — `models/framegraph.py` → `{schema, grammar,
spec, renders}` — turned into a glyph. The source node is the only filled,
colored element; everything generated from it is outline-only. The hierarchy of
the picture *is* the hierarchy of the system.

- **Clear space:** keep a margin of one corner-bracket length (the bracket arm)
  on all sides. Nothing intrudes.
- **Minimum size:** 24 px (icon) / 120 px wide (wordmark). Below that the
  derived nodes merge — use the monogram `FG` instead.
- **Variants:** full color (default) · all-ink monochrome (single-color print,
  embossing, favicons) · reversed (ink → paper) on dark surfaces. The accent
  node may render in `frame-blue` or, in a passing-state context, `gate-green`.
- **Production:** the shipped wordmark sets live text in a mono stack and will
  render with whatever mono face is present (honestly, DejaVu Mono is the
  in-repo proxy). For distribution, **outline the wordmark text** so it is
  font-independent.

**Misuse (do not):** stretch or skew · rotate · add gradients, bevels, or drop
shadows · recolor the brackets · fill the derived nodes · place on a busy
photographic background without the clear-space plate · re-letter the wordmark
in a non-mono face.

---

## 4. Color

The palette is an instrument panel, not a paint set. Two structural accents (the
two halves of the name) and **two semantic colors that are the gate states
themselves** — green for *in-sync / pass*, red for *drift / fail*. That pair is
not decorative; it is the project's core feedback loop, promoted to brand color.

| Token | Hex | Role |
|---|---|---|
| `ink` | `#15181E` | Primary text, lines, crop marks. Graphite, never pure black. |
| `paper` | `#FBFAF6` | Default surface. Warm technical paper. |
| `canvas` | `#FFFFFF` | Pure render surface (inside a document frame). |
| `frame-blue` | `#1F4FD8` | **Primary accent** — the *Frame* half. Links, key marks, the source node. |
| `graph-cyan` | `#12B0C3` | Secondary accent — the *Graph* half. Flow, edges, live signal. |
| `gate-green` | `#1E9E5A` | **Semantic:** passing gate · valid · in-sync. |
| `drift-red` | `#D23B2B` | **Semantic:** failed gate · drift · invalid. |
| `grid` | `#D4D8DE` | Hairlines, rules, secondary strokes. |
| `mute` | `#6B7280` | Captions, secondary text. |

**Usage rules**

- Ink on paper is the default text pairing. Reserve `gate-green` / `drift-red`
  for *state* (a check result, a validity badge, a diff) — never as decorative
  fill, or the signal stops meaning anything.
- One accent per surface. Do not put `frame-blue` and `graph-cyan` in equal
  weight competition; cyan is a supporting voice.
- No gradients in brand chrome. (The *format* supports them; the *brand* is flat
  and exact — restraint is the point.)
- **Accessibility:** body text must meet WCAG AA (≥ 4.5:1). `ink` on `paper`
  clears this comfortably; `mute` is for ≥ 16 px secondary text only; never set
  body copy in `gate-green`/`drift-red` (pair the color with a glyph or label so
  meaning survives color-blindness and grayscale).

---

## 5. Typography

One coherent superfamily across the three registers FrameGraph actually spans —
data, UI, and long-form documents — plus the deterministic proxy face already in
the repo.

- **IBM Plex Mono** — wordmark, code, YAML, schema, CLI, data labels. *Mono =
  machine-true; it signals "this is a typed artifact, not prose."*
- **IBM Plex Sans** — UI, docs body, captions, this guideline.
- **IBM Plex Serif** — long-form rendering (the books and letters FrameGraph
  targets).
- **DejaVu Sans / Mono / Serif** — the **proxy faces**. The dependency-free
  renderer ships DejaVu stand-ins (`tooling/render_fixtures.py`); the brand names
  them honestly as fallbacks rather than pretending the proxy is the brand face.

IBM Plex is chosen because it is one open superfamily (SIL OFL) covering mono +
sans + serif coherently — matching a system that spans code, UI, and books — and
it carries an engineering-drawing temperament that fits the mark.

**Scale** (1.25 / major-third, rounded): 13 · 16 · 20 · 25 · 32 · 40 · 50.
Body 16 px / line-height 1.55. Set tabular numerals on in any table that carries
measurements or gate counts.

---

## 6. Voice & tone

The voice is **CLAUDE.md, externalized**. It is not a separate copywriting style;
it is the same operating discipline pointed at the reader.

- **Unbiased over flattering.** State the limit, then the capability. No
  superlatives, no "revolutionary," no "effortless." If the test says 702/703,
  the copy says 702/703. *(CLAUDE.md §1.)*
- **Cite or qualify.** Every factual claim links its source; uncertainty is
  marked explicitly. "I cannot verify this" is acceptable; a plausible-sounding
  unverifiable claim is a critical failure. *(CLAUDE.md §2.)*
- **English-first (EN-US).** PT-BR appears only for a PT-BR audience or in
  bilingual project docs, as the translation under the English primary.
  *(CLAUDE.md §3.)*
- **Present tense, active voice, lowercase technical terms** exactly as they
  appear in code (`defs`, `flow`, `.fg.yaml`, `make check`).
- **No complexity theatre.** Say the thing and stop. *(CLAUDE.md §8.)*

**Tagline (primary):** *"The output layer for the agent era."*
**Alternates:** *"Turn intent into a finished, checked file."* · *"Spell-check
and a printing press — for everything AI makes that you can see."* · *"Anyone can
make a picture; FrameGraph makes a result you can trust."*
**Internal / architecture line** (for a maintainer audience, not the public
lead): *"The models are the source of truth · documents that can't silently
drift."*
Lead with the *output* claim — correct, on-brand, checked, yours — which is
grounded in the working system and the seed pitch. Still avoid claiming
conformance, fidelity, or completeness of the *format* itself (it remains
*proposed*); the brand must not write a check the renderer can't cash.

---

## 7. Graphic language

Reusable motifs, all drawn from the toolchain's real vocabulary:

- **Corner brackets / crop marks** — the frame motif; bound figures, cards, code blocks.
- **The derivation fan** — a source node → generated nodes; the diagram for "source of truth."
- **Hairline grid** (`grid` color) — a faint drafting grid under diagrams and contact sheets.
- **State chips** — a mono label with a leading glyph: `✓ PASS` in `gate-green`,
  `✗ DRIFT` in `drift-red`. Used for fixture status, schema-check, CI.
- **`→` arrows in mono** — for pipelines: `models → schema → docs`.

---

## 8. Design tokens (in FrameGraph's own model)

The palette and type system map 1:1 onto the native `Defs.tokens` surface
([`models/framegraph.py`](../models/framegraph.py) `class Tokens`). The brand is
therefore *consumable from FrameGraph itself* — see
[`brand/framegraph.tokens.fg.yaml`](../brand/framegraph.tokens.fg.yaml). Drop that
`defs:` block into a document and reference the tokens by name. This is the
intended dogfood: **the brand guideline should ultimately be authored as a
FrameGraph document**, rendered by the project's own renderer, gated by the
project's own checks.

---

## 9. Applications

- **README badge / CLI banner:** wordmark or `FG` monogram + a state chip
  (`✓ in sync`). ASCII-art banner may use `FRAMEGRAPH` in a fixed-width box.
- **Docs site (MkDocs Material):** ink on paper; `frame-blue` as the theme primary;
  IBM Plex Sans body, IBM Plex Mono code.
- **Fixture contact sheets / galleries:** hairline `grid` backdrop, corner-bracket
  frames around each thumbnail, `mute` captions.
- **Diagrams in the spec/docs:** the derivation-fan motif for any "source → generated"
  relationship; state chips for any pass/fail.

---

## 10. Quick reference — do / don't

| Do | Don't |
|---|---|
| Write "FrameGraph" (camel, one word) | "Frame Graph", "Framegraph", "the framework" |
| Lead with limits, then capability | Use superlatives or claim conformance/fidelity |
| Reserve green/red for real state | Use gate colors as decoration |
| Keep brand chrome flat | Add gradients, bevels, shadows to the mark |
| Outline the wordmark for distribution | Re-letter the wordmark in a non-mono face |
| Carry the disclaimer frontmatter on docs | Drop provenance to look more polished |

---

## 11. Governance

This guideline is a proposal and lives where the rest of the source of truth
lives — in the repo, under the same rules. If adopted, the right end-state is to
bind it to the sync system rather than maintain it by hand: the tokens become a
checked `defs` fragment, the guideline renders as a FrameGraph document, and a
gate fails when the brand drifts from its tokens — the same guarantee the
project already makes about its schema, grammar, and prose.

*Feedback on this proposal is processed, not blindly applied (CLAUDE.md §6):
sound objections are accepted and cited; unsound ones are refuted with reasons.*
