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
| `chip_row` (compositional pill row) | lowered to a core `group` of decorative pill rects + centered texts — same cursor/gap layout, chip def's fill/`text_style`/radius baked in; a consumed-and-baked `chip` component def is dropped (lossless), unconsumed defs are kept |
| flat span styles (`{text, weight, color}`) | v2 `Span` allows `text`/`style`/`lang` — extras become a translated inline style |
| flat object `stroke_width` | moved into `stroke_style` (P3) |
| gradient fill tokens (`tokens.fill_styles` `{type: linear_gradient, from/to points, stops+opacity}`) | v2 `Gradient` paints — `kind: linear`, `from`/`to` → `angle`, stop `offset` → `position`, stop `opacity` folded into an 8-digit hex against the pack palette (v2 stops carry no opacity field). The renderer now dereferences `tokens.fill_styles` keys (it never had, so named gradient fills silently emitted invalid paint) |
| implicit single-line text (v0.1 wrapped only under `wrap: true`) | styles without `wrap` pin `white_space: nowrap`; deck-form pages pin `rendering.text.overflow: visible` — v0.1 painted past the box and never truncated, v2's default is wrap-then-clip, and silent truncation is exactly what #44 bans |

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

Migrated: **genai-ecosystem** (the conversion proof; 98.8 % pixel-identical),
**PALS GenAI architecture EN** (8 slides — the first deck/slides-form
migration; fixture `pals-genai-architecture.fg.yaml`, 0 errors, one honest
advisory: slide 8's error matrix is authored as 51 absolute texts in the
source, and re-authoring it as a `TableObject` would be content surgery,
not migration), and **PALS PT-BR** (15 slides — fixture
`pals-genai-arch-ptbr.fg.yaml`; this deck closed the gradient-fill-token
corner above). Remaining decks are tracked as a checklist on
[#33](https://github.com/pedroanisio/frameforge/issues/33): **faz-ai and
code-base-mapper are gated on #30** (49 and 57 `type: uml` objects — the
unabsorbed UML composers); GTDS awaits the client token-pack decision.

Back to the [roadmap](roadmap.md) (absorption programme) ·
[patterns & fills](patterns-fills.md) · [library](library.md).
