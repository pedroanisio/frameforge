---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code"
  date: "2026-07-03"
---

# Library — themes, symbol packs, generators

`framegraph.library` is the content library absorbed from the predecessor
project (issue #32): **7 consulting token packs** as ready v2 `defs.tokens`
fragments, **4 symbol packs** instantiable through grammar-level `use`, and
**2 data-driven page generators**. Everything is committed data under
`src/framegraph/library/data/` — translated once from the v0.1 sources
(field renames, the P3 stroke split, `ellipse` center/rx/ry), now owned
here. Runnable sample: `static/examples/library_showcase.py`; canonical
fixture: `tests/fixtures/library-honeycomb.fg.yaml`.

## Themes

House-style *homages* (per the packs' own metadata): `bain`, `bcg`,
`deloitte`, `ey`, `kpmg`, `mckinsey`, `pwc`. Each carries `colors`,
`fonts`, `text_styles` (`font_family` lists, `font_size`/`font_weight`,
`vertical_align`), `stroke_styles` (Style-bag props: `stroke`,
`stroke_width`, `stroke_dasharray`), plus `fill_styles`/`glyph_map` where
the pack ships them.

```python
from framegraph.library import list_themes, load_theme
doc = {..., "defs": {"tokens": load_theme("mckinsey")}, ...}
```

The test gate (`tests/test_library.py`) renders a probe page per theme —
every text style and stroke style exercised, zero uncontained text.

## Symbol packs

| Pack | Symbols | Notes |
|---|---|---|
| `covers` | `cover_minimal_sidebar` | 960×540 title slide, right accent pane |
| `sections` | `agenda_left_pane` | numbered agenda (7 slots), left pane |
| `shared` | `insight_box`, `kpi_card`, `two_by_two`, `s_node` | rely on theme styles (`body`, `callout`, `exhibit_*`) |
| `hex` | `hex_header`, `hex_leaf_solid/dashed`, `hex_node_plain/warning/excel/money` | cells consumed by the generators |

Symbols are `defs.symbols` bodies with `$param` slots, lowered by
`framegraph.sdk.expand`. The cover/agenda/hex packs reference pack-scoped
text styles the consumer must supply — merge `support_text_styles(...)`
into `defs.tokens.text_styles` next to a theme:

```python
from framegraph.library import load_symbols, load_theme, support_text_styles
from framegraph.sdk import expand

theme = load_theme("mckinsey")
theme["text_styles"] |= support_text_styles("covers", "sections")
doc = {..., "defs": {"tokens": theme, "symbols": load_symbols("covers")},
       "pages": [{... {"type": "use", "symbol": "cover_minimal_sidebar",
                       "box": [0, 0, 960, 540], "params": {...}} ...}]}
page_ready = expand(doc).document
```

## Generators

Faithful geometry ports of the two v0.1 build scripts — same input data
contract, committed examples under `data/examples/`:

```python
from framegraph.library import (honeycomb_capability_map, load_example,
                                module_hub_radial)
doc = honeycomb_capability_map(load_example("honeycomb"))
doc = module_hub_radial(load_example("module_hub"))
```

- `honeycomb_capability_map(data)` — columns of flat-top hex cells
  (`title`, `columns[].header`, `columns[].items[].{label, variant}`;
  variant `core`/`extended`/`future`, future = dashed). Odd columns drop by
  the tessellation offset.
- `module_hub_radial(data)` — hub + satellites at explicit positions
  (`hub`, `satellites[]`, optional `edges[]` drawn beneath the hexes),
  per-node icon/outline/label colors, optional hub detail block.

Both return **expanded, validated, render-ready** documents — plain core
primitives, no `use`, no `defs.symbols`. Two deliberate departures from
v0.1, both visible in the committed example renders: the honeycomb canvas
grows to fit instead of clipping a shifted six-row column (pin
`geometry.canvas_h` to restore the fixed height), and the module hub's
detail block paints above the node layer instead of beneath a neighbouring
hex. Per-node colors pass through as literals instead of v0.1's
`hash()`-derived tokens, so output is deterministic.

Back to the [roadmap](roadmap.md) (absorption programme #32; #28/#29 are
the sibling [patterns & fills](patterns-fills.md) context).
