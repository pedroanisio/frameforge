---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-07-03"
status: analysis
scope: what `libfy.md` means for FrameGraph, grounded in the live tree
---

# Libfy, on FrameGraph

Companion analysis to `libfy.md` (the libfy concept document; not yet committed to this repository). Every claim below is grounded in a
live file; paths are repo-relative.

## Thesis

`libfy` is **not a feature request — it is the name for a meta-loop FrameGraph
has already been running unnamed.** The word appears nowhere else in the tree,
but the *practice* is embedded throughout. Naming it does one useful thing: it
exposes the single rung of the loop that is currently manual — the **extraction
operator** that promotes a finished document into a library primitive.

## 1. FrameGraph is the textbook subject for libfy — twice over

libfy's claim: *constructive work → curated library of (parts + know-how) →
capability compounds.* FrameGraph is a construction tool, so it is a libfy
subject on two levels at once:

- **The documents users build** (decks, books, diagrams) are constructive work
  whose reusable spine can be extracted.
- **The tooling itself** (validators, codemods, the coach) is constructive work
  that has *already* been extracted into reusable methods.

The library module's own docstring records a completed libfy event in plain
language — `src/framegraph/library/__init__.py`: *"the content library absorbed
from the predecessor project."* Capability from prior work, curated, committed
under `data/`. That is libfy, done, before the word existed. Issue #33's
`--from-v01` codemod (`tooling/codemod.py`) is a second instance: an entire prior
corpus (v0.1) libfied into a reusable **migration method** rather than a pile of
one-off conversions.

## 2. libfy's parts↔know-how spectrum maps 1:1 onto the existing tree

The definition's own phrase — *"from concrete parts (components, aggregates,
assets) to know-how (patterns, rules, methods, checklists)"* — is not
aspirational for FrameGraph. It is an unusually precise description of what is
**already committed**. Every rung is populated:

| Rung (concrete → abstract) | Live artifact | Consume API |
|---|---|---|
| **Assets** | font packs `.fp` (`src/framegraph/fontpack.py`), corpus media, `FigureAsset` (imported PDF/EPUB) | `fg-font --install`, `scope_font_pack`, `place_imported_figure` |
| **Parts** | symbol packs via `use`, `components`, widgets, `Group` | `load_symbols`, `use`/`component` → `src/framegraph/sdk/expand.py` |
| **Compositions** | page masters, the **375 typed layout patterns** in `docs/patterns-fills.md`, `FigureRef` | `compose(pattern_id, fill)`, `place_figure` |
| **Rules / tokens** | 7 house-style theme token packs (`src/framegraph/library/themes.py`) | `load_theme` → merged into `defs.tokens` |
| **Methods** | the 2 data-driven generators, SDK builders, `tooling/codemod.py`, render lanes, the coach process | `honeycomb_capability_map`, `FlowBuilder`, `--from-v01` |
| **Know-how / checklists** | `skills/typeface-and-colour/` (12 measurable gates), `src/framegraph/coach/` rubrics, ADRs, the MCP `describe_capabilities` catalog, validator codes R1–R12 | Skill invocation, `get_guide`, `describe_capabilities` |
| **The oracle** | `tests/fixtures/b1/` — the frozen reference the whole thing is diffed against | golden `oracle.lock.json` |

The finding is the strong one: **libfy describes FrameGraph's existing
architecture, it doesn't propose a new one.** The library module is even *shaped*
like the spectrum in miniature — data (themes) → parts (symbols) → methods
(generators), the three-rung ladder in one package.

## 3. The compounding claim is *mechanically testable* here — not hand-wavy

libfy asserts: *"anything built from a library inherits its structure, so it is in
turn easier to libfy."* In most systems that is a slogan. In FrameGraph it is a
verifiable property:

- A doc built from a theme + symbol pack carries **named, referenced structure**
  the validator can trace (R12 referential integrity), so any future extractor
  operates on it deterministically.
- `use`/`component` instances are stamped `meta.source_symbol` /
  `meta.source_component` at lowering time (`src/framegraph/sdk/expand.py`). The
  document **retains the back-reference to its library origin.** That stamp *is*
  the literal mechanism by which "built-from-library ⇒ easier-to-libfy."
- The contrast proves it: the hand-authored one-offs — `static/examples/syrus_proposal.py`,
  the b1 oracle decks — carry no such structure, which is precisely why
  extracting reuse from them is manual today.

## 4. The gap libfy names: the extraction operator is the one missing rung

FrameGraph is **consume-complete and extract-incomplete.**

- It has rich machinery to *consume* the library: `load_theme`, `use`+`expand`,
  `render --font-pack`, `compose`, the widget registry.
- It has rich machinery to *enforce curation*: the validator, the oracle lock,
  `gen_capability_manifest --check`, the sync gates.
- It has an *inverse* direction, but only for raster→draft: `propose_from_image`
  / `propose_from_document` / `propose_from_svg`.

What it does **not** have is `finished-doc → library-primitive`. That promotion is
done by human hands every time — someone read the predecessor's build scripts and
hand-ported them into `src/framegraph/library/generators.py`; someone will
hand-lift the next recurring deck layout into a new symbol or pattern.

**That missing operator is what "libfy" would concretely become as a verb in
FrameGraph:** a `tooling/` command (and matching MCP tool) that takes one finished
client — or a set of them from `static/examples/` — diffs them against the
library, finds the repeated spine (a recurring token set, a recurring group
geometry, recurring page furniture), and emits a **candidate `defs.tokens` theme /
`defs.symbols` pack / patterns-fills entry / generator stub**, annotated with
provenance (which examples it was distilled from), then round-trips it through the
validator + a new fixture so the extraction is *verified, not asserted* (PALS's
Law). It is the exact inverse of `load_theme` / `use` / `compose`, and it closes
the loop.

## 5. Guardrail — where to push back before anyone builds it

Two constraints, both grounded in the definition's own words:

- **libfy is a practice, not a schema field.** It must never become a Pydantic
  attribute or a document keyword. It lives in `tooling/` + MCP + `docs/`, exactly
  where the codemod and capability-manifest already live. The document model
  stays clean.
- **The value is the curation gate, not the volume.** The definition stresses
  *curated, annotated* twice. The failure mode is 85 cookbook examples and a
  growing `data/` that never get distilled — accretion masquerading as a library.
  FrameGraph already has the defense (validator, oracle lock, `gen_status`
  counting only tracked fixtures, manifest `--check`), so a real libfy in this
  repo must route *through* those gates: **an extraction that doesn't produce a
  passing fixture + a manifest entry is not a libfy — it's a copy.** And not every
  rung wants an auto-extractor: a bespoke 14-page proposal is a leaf, not library
  stock. The discernment of *what deserves promotion* is the operator's, and the
  word "curated" is carrying exactly that judgment.

## In one line

libfy is the name for FrameGraph's extract→curate→compound loop; every rung of its
parts/know-how spectrum is already in the tree; the loop is consume-complete but
extract-incomplete, and making libfy first-class means building the one missing
operator — *finished doc → annotated, gate-verified library primitive.*
