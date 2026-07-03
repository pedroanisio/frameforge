---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code"
  date: "2026-07-03"
---

# Migrating v0.1 documents — the deck-corpus conversion path

The predecessor project's dialect (issue #33) converts to v2 mechanically:

```bash
uv run python tooling/codemod.py old-doc.yml --from-v01        # writes old-doc.head.yml
uv run python tooling/validate.py old-doc.head.yml             # then verify
```

`--from-v01` lifts the envelope, then the standard HEAD rules (P3 stroke
split, `stroke_styles` Style projection, gradient stops) run as usual.
Conversion proof: the genai-ecosystem production diagram —
`tests/data/v01/genai-ecosystem.yml` (committed v0.1 source) →
`tests/fixtures/genai-ecosystem.fg.yaml` (0 errors, 0 warnings), rendered
output 98.8 % pixel-identical to the v0.1 reference render (RMSE 14.7/255;
the delta is one label's wrap point plus antialiasing). Regression-gated by
`tests/test_codemod_v01.py`.

## What the lift does

| v0.1 | v2 |
|---|---|
| `version: 1.5` (float) | `version: "2.3.0"` (HEAD semver) |
| `kind:` | `meta.kind` (+ `profile:` inferred: `*diagram*` → `diagram`, `*deck*`/`*presentation*` → `deck`) |
| `scene.name` / `scene.description` | `title` / `description` |
| `scene.id`, `scene.canvas` | the single page's `id`, `canvas` |
| `scene.rendering_contract` | `page.rendering` (shape is 1:1 — `text.min_font_size`, `overflow: shrink_to_fit`, `semantics`, `preserve_manual_line_breaks` all exist in v2) |
| `semantic:` (ontology/nodes/edges) | `page.semantic` (loose dict; object `bind` refs survive as-is) |
| `visual.tokens` / `visual.layers` | `defs.tokens` / `page.layers` |
| `deck.canvas`, `deck.tokens`, `deck.component_defs` | per-page `canvas`, `defs.tokens`, `defs.components` |
| `slides[]` (`slide`, `id`, `title`, `notes`, `visual.layers`) | `pages[]` (`meta.slide`, `id`, `meta.title`, `notes`, `layers`) |
| unknown top-level keys (e.g. `disclaimer:`) | `meta.<key>` (the v2 envelope forbids extras) |

Two **semantic traps** the lift fixes (silently wrong if merely carried,
because the old keys validate as unrelated CSS properties):

- text styles: `font` → `font_family` **list** (resolved through the pack's
  `fonts` map), `size`/`weight` → `font_size`/`font_weight`, `v_align` →
  `vertical_align`, `wrap` dropped (v2 wraps by default); `fonts` CSS
  strings become `{family: …}` defs;
- stroke bundles: `{color, width, dash}` → `{stroke, stroke_width,
  stroke_dasharray}` — both as `tokens.stroke_styles` values and inline on
  objects (the P3 split).

## Corpus status

Migrated: **genai-ecosystem** (the conversion proof). Remaining decks are
tracked as a checklist on
[#33](https://github.com/pedroanisio/frameforge/issues/33) and migrate on
demand through the same command; the deck/slides form is already handled by
the lift, so PALS EN/PT-BR, GTDS, faz-ai and code-base-mapper are expected
to be mechanical, with per-deck hand-fixes only where a deck exercises a
dialect corner the corpus has not hit yet.

Back to the [roadmap](roadmap.md) (absorption programme) ·
[patterns & fills](patterns-fills.md) · [library](library.md).
