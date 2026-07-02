---
title: FrameGraph v2 — Specification (HEAD)
version: 2.3.0
status: PROPOSED / partially-implemented
source_of_truth: docs/models/framegraph.py (Pydantic) → schema generated; this prose is the normative reference
supersedes: FrameGraph-2.0.0-Specification.md (reverse-engineered) and the four standalone patch docs (P1–P4); style subsystem defers to framegraph-v2-style.ebnf (authoritative)
date: 2026-07-01
disclaimer: >
  FrameGraph v2 is a proposed, not-yet-conformantly-implemented format. Normative
  statements below ("MUST"/"SHOULD") describe the design target. Claims inherited
  from the patch series carry their original [JUDGMENT]/[EXTERNAL] character. The
  machine-checkable parts (models, generated schema, validator, codemod) are the
  parts you can actually run; the prose is the reference they implement.
---

# FrameGraph v2 — Specification (HEAD)

FrameGraph is a declarative JSON/YAML language describing a paginated or continuous
document — decks, books, reports, diagrams — rendered to vector output. This is the
**HEAD** specification: the consolidation of the base grammar with Patches 1–4 and
the (now drafted) CSS style module. It is the normative companion to
`docs/grammar/framegraph-v2.ebnf` and `docs/models/framegraph.py`.

This document records only the **rules**; for the descriptive walk-through of the
format see the reverse-engineered spec (provenance). Section numbers match the
references used throughout the grammar and the patch series.

## 1. Document model

A document is a single JSON/YAML object:

```yaml
dsl: FrameGraph          # required, literal
version: "2.3.0"         # required, semver string (NOT a number)
profile: report          # advisory only: deck|book|letter|report|diagram|mixed — never changes parsing
title: …                 # optional metadata
defs: { … }              # optional shared definitions (§8)
targets: [ … ]           # optional multi-target adaptation
pages: [ … ]             # required, ≥1 PageProducer (Page or FlowSection)
meta: { … }              # optional
```

- The model is **closed**: unknown keys are errors (`additionalProperties:false`).
- A document has exactly **one root** (`pages`); there is no alternative top-level form.
- `profile` is **advisory** — tooling may use it, but it is not a discriminant and
  MUST NOT change how the body is parsed.

### 1.1 Pages vs flow

`pages[]` mixes two producers, discriminated by `mode`:

- **`mode: page`** — a fixed canvas with `layers[]` of absolutely-placed
  `VisualObject`s (the deck/diagram end).
- **`mode: flow`** — a `story[]` of `Flowable`s poured through a `master` (the
  book/report end), `media: paged` (default) or `continuous` (§3.9).

## 2. Value types & units

| Type | Form |
|---|---|
| `Length` | a number (points) or a string `<n>("pt"\|"px"\|"pc"\|"mm"\|"cm"\|"in"\|"em"\|"rem"\|"%"\|"fr")` |
| `Color` | hex `#rgb[a]`/`#rrggbb[aa]`, a CSS colour name, or a `tokens.colors` key |
| `Point` | `[x, y]` |
| `Box` | `[x, y, w, h]`, top-left origin, **+y down** (§3.4) |
| `unit-interval` | a number in `0.0 .. 1.0` |
| `semver` | `<major>.<minor>.<patch>[-pre][+build]` |

`%` and `fr` are **relative** and resolve only in defined contexts (§3.4, §3.6g). The
unit set is the one the toolchain resolves (renderer `geometry.num` + the relative
contexts) and is **pattern-enforced** by the models at schema time — a malformed unit
(`12ptx`) is a validation error, not a silent default. The style module's earlier
`q/ex/ch/vw/vh/vmin/vmax` extras were never resolved by any render target and are
dropped from the conformant set (reconciled at HEAD).

## 3. Geometry, layout, text, and audit

### 3.1–3.2 Identity & references

Objects may carry `id`; references (`bind`, `Anchor` `ref`, `ref`/`cite`/dimension
`from`/`to`) MUST resolve to a declared id/key (referential integrity, checked in
the §3.3 static pass).

### 3.3 Static validation pass (no constraint solver)

A document is checked by cheap, order-independent static rules — schema validity is
necessary but **not** sufficient. In addition to cardinality/reference checks, the
pass includes the **geometric audit** (P3):

- **Containment (SHOULD).** Every object's resolved page-space box SHOULD lie within
  its canvas (plus declared `bleed`). Outside ⇒ warning, unless `decorative` or under
  `overflow: clip`/bleed.
- **Scoped non-overlap (SHOULD).** Sibling boxes within a `free`-layout `GroupObject`,
  or any cluster marked `meta.no_overlap: true`, SHOULD NOT overlap. Global/layer
  overlap stays **legal** (z-order is intentional) — the check is scoped, not blanket.
- **Tabular regions MUST use the box-model.** Aligned tabular content (title blocks,
  key/value stacks, legends, cells) MUST be a `row`/`column`/`grid` `GroupObject` or a
  `TableObject`, not a flat list of absolutely-placed `text`. A validator SHOULD warn
  when ≥ 6 absolutely-positioned text objects in one layer form an approximately
  regular grid (the title-block-collision signature).

These are enforced by `tooling/validate.py`.

### 3.4 Coordinate system & relative lengths

Page space is top-left origin, +y down (matches CSS/document authoring). Inside a
`GroupObject`/`SymbolDef`/`ComponentDef`, a child box's `(x, y)` is resolved in the
**parent-local** system (origin at the parent box top-left), not page space (§3.6).

- `%` on a child box dimension resolves against the **container content-box** on the
  same axis (Pass 2, §3.6g); under `free` or at page root, against the parent/canvas.
- `fr` is a free-space share, valid **only** inside a layout container (grid track
  sizing, or row/column fill weight where `1fr ≡ fill grow:1`). Elsewhere it is a
  validation error.

### 3.5 Token resolution & the single stroke form

`style`/`stroke`/`stroke_style`/`text_style`/`src`/`glyph`/`font` resolve against
`defs.tokens` and `defs.assets`:

- **`stroke` → paint only:** `tokens.colors` or a hex/CSS-name literal. It never
  carries width/dash. *(P3, BREAKING — the inline `stroke:{geometry}` form is removed.)*
- **`stroke_style` → geometry bundle:** `tokens.stroke_styles` (a named `StrokeStyle`)
  or an inline `StrokeStyle`. The single home for `width`/`dash`/`linecap`/`linejoin`/
  `arrow_*`/`opacity`. A bundle's `color` is a default, overridden by the object's
  `stroke`. *(End-state: both fold into the CSS-named `stroke*` properties on `Style`.)*
- **`src` (image/icon):** a literal path **or** a `defs.assets` key (a pinned
  `AssetDef`). An unpinned external URL fetched at render is **non-conformant** (§9.6).
- **`IconObject.font`** → `tokens.fonts` (a pinned font); **`glyph`** → `tokens.glyph_map`.

### 3.6 Nested coordinates & the layout box model (P1, P2, P3)

**(a) Local coordinate systems.** A container establishes a local system (origin at
its box top-left, +x right/+y down). A child's page-space position composes the
box-origin translations and transforms from the root down (SVG transform-stack model).

**(b) Transforms.** A container's `rotation`/`transform` applies to its whole subtree,
innermost last; `transform_origin` defaults to the box centre (CSS `50% 50%`).

**(c) Clip.** `overflow: clip` (via `style`) or an explicit `ClipSpec` clips children
to the container box; `overflow: visible` (default) lets them paint outside.

**(d) Group opacity.** A container's `opacity` composites the **subtree as one unit**
(render → flatten → apply), so overlapping children in a half-opaque group do not
double-darken (SVG group-opacity). Per-object `opacity` still applies before flattening.

**(e) Placement per `Layout.kind`** (after insetting by `padding`; `gx = column_gap ??
gap ?? 0`, `gy = row_gap ?? gap ?? 0`):

- **`free`** (also the **default** when `layout` is absent) — each child at its own
  box `(x, y)`. The only kind that reads child `(x, y)`.
- **`row`** — packed left-to-right by child width + `gx`; cross-axis by `align`.
- **`column`** — packed top-to-bottom by child height + `gy`; cross-axis by `align`.
- **`grid`** — row-major into `columns`; column width = max child width per column,
  row height = max child height per row. A child may carry `grid_span: [cs, rs]`
  (default `[1,1]`) with **sparse** auto-placement (skipped cells not back-filled;
  `cs > columns` is an error).

`align ∈ {start, center, end, stretch}` (default `start`). There is **no automatic
line wrapping** in row/column.

**(f) Box requirement.** Under `row`/`column`/`grid`, box-based children
(`rect`/`text`/`image`/`icon`/`group`/`table`/…) MUST supply width+height via `box`
(computed `x,y` replace authored ones). **Box-less primitives** (`line`/`ellipse`/
`polyline`/`path` by intrinsic coords) are allowed under `free` with no box, but are a
**validation error** as direct `row`/`column`/`grid` children (no extent to advance
by) — wrap in a group or give a box. Cyclic instancing is an error.

**(g) Content sizing & the measure–arrange pass (P4).** Each object has a per-axis size
mode `sizing: {width,height: fixed|hug|fill, grow, min, max}` (default `fixed`/`fixed`).

- **Pass 1 MEASURE (bottom-up):** text `max-content`/`min-content`; image natural;
  icon glyph box; group ⇒ children bbox + padding. `hug` is **invalid on**
  `rect`/`ellipse`/`line`/`polyline`/`path` (no intrinsic content) — error.
- **Pass 2 ARRANGE (top-down), main axis first:** content box = box − padding;
  partition `fixed`/`hug`/`fill`; `free_main` split across `fill` children by `grow`
  (clamped to `min`/`max`); cross axis stretch/align; **then** wrap text to the
  resolved width and compute `hug` height + the §3.7 chain; recurse; pack.
- Resolution order **main → cross → wrap/height → recurse** removes circularity.
- `fill`/`fr` are undefined under `free` (no container main axis) — error.

### 3.7 Text fitting & truncation (P1)

For a run with target width `W` (and height `H` in a fixed box):

1. **Shape & wrap** at the style `size`; if `wrap` (default true in flow), break to
   `W`, else single line (or manual breaks under `preserve_manual_line_breaks`).
2. **`line_clamp = n`** keeps the first `n` lines — applies in **both** flow and
   fixed-box (a max-lines cap, not a height test).
3. **Height test** (fixed-box only): if it fits `H`, stop. In flow the box grows;
   only step 2 truncates there.
4. **Overflow** (fixed-box, still exceeds `H`): `visible` paints past the box; `clip`
   clips to `H`; `shrink_to_fit` reduces `size` monotonically to a floor of
   `min_font_size` (object → `TextContract` → engine default), then falls through to
   `clip`.
5. **Marker:** at the truncation point, `text_overflow: ellipsis` replaces the visible
   end of the last kept line with `…`; `clip` (default) cuts with no marker.

`shrink_to_fit` is a declared FrameGraph fit mode a target MAY mark unsupported (§8.5).
The shrink search MUST be a pure function of `(text, W, H, size, min_font_size,
step/tolerance)`; each target publishes its step/tolerance.


Truncation MUST be diagnosable: a conforming renderer reports every text
object that materially loses content to containment (identity, lines
dropped, the head of the dropped text, and whether the clip was explicitly
authored) — a bare aggregate count is not a diagnostic.

### 3.8 Pattern fills (P2)

`Fill = Color | Gradient | Pattern`. A `Pattern` tiles a closed shape's interior and
is **clipped to that geometry**: `hatch` (parallel lines at `angle`, default 45°,
spaced by `spacing`), `cross_hatch`, `dots`, `grid`. Line paint/weight come from
`stroke`; optional `background` paints behind. A target that cannot tile paints
`background` (or nothing) and emits a "pattern unsupported" diagnostic — never a
silent blank (§8.5).

### 3.9 Continuous vs paged flow (P2)

`FlowSection.media` defaults to `paged`. `continuous` lays the story into a **single
region whose height grows to fit** (CSS continuous media): no page breaks generated
(`break_*: page` degrades to `column` or is ignored), `page`/`pages` counters are
undefined, a running header/footer renders once or is omitted, and the uniform-page-size
rule does not apply.

### 3.10 Dimensions (P3)

A `DimensionObject` is one anchored unit — value + witness lines + dimension line +
arrowheads. `from`/`to` are `Anchor`s and MUST resolve. With `value: auto` (default
intent), the measurement is computed in a **measure pass**: `linear`/`aligned` ⇒
distance; `angular` ⇒ angle at the shared vertex; `radial`/`diameter` ⇒ radius/diameter
(`to` is the centre). `prefix`/`suffix` (`Ø`, `R`, `mm`) and `text` form the label;
`arrows`/`offset`/`stroke_style`/`text_style` control rendering. A renderer that cannot
draw it MAY decompose to lines+text but MUST keep the computed value attached.

### 3.11 Connectors (typed at HEAD)

A `connector` is an anchored line/polyline between two endpoints. Each endpoint is
an explicit `[x, y]` point or an object attachment `{ref, port?, side?, offset?}`
(the legacy `object` key is accepted for `ref` and normalised): `port` picks a named
port of the target; otherwise `side` (`north|south|east|west`, or a side-named port)
picks the box-edge midpoint, slid by `offset` along that edge; with neither, the
endpoint is the target's box centre. An endpoint `point` short-circuits to fixed
page coordinates and takes precedence over `ref`. Endpoint `ref`s MUST resolve to an
object id on the same page (§3.1). An optional `route` carries intermediate
`points`; the drawn geometry is always the chain start → points… → end (`route.kind`
— legacy key `type` — is an advisory hint: `straight|orthogonal|curved`). An optional
boxed `label` (`{text, box, style?}`) is drawn at its own box. Paint comes from
`stroke` and geometry/arrowheads from `stroke_style` (`arrow_start`/`arrow_end`),
exactly as for other open shapes (§3.5).

## 4. Canvas & presets

`CanvasSpec` is a preset string or a `CanvasObject` (`preset` **xor** `size`+`units`,
plus `orientation`/`bleed`/`margin`). Presets:

| Print (pt) | Deck (px) | Screen (px, P2) |
|---|---|---|
| A3, A4, A5, Letter, Legal, Tabloid | deck-16x9, deck-4x3, square | phone 390×844, tablet 834×1112, web 1280×800 |

Social-media canvases (px) and aspect-ratio aliases are also presets: `instagram-square`
1080×1080, `instagram-portrait` 1080×1350, `instagram-landscape` 1080×566, `instagram-story`
1080×1920, `facebook-post` 1200×630, `facebook-cover` 820×312, `facebook-story` 1080×1920,
`twitter-post` 1600×900, `twitter-header` 1500×500, `linkedin-post` 1200×627, `linkedin-cover`
1584×396, `youtube-thumbnail` 1280×720, `youtube-banner` 2560×1440, `tiktok-video` 1080×1920,
`pinterest-pin` 1000×1500, `snapchat` 1080×1920, `story` 1080×1920; ratio aliases `1x1`, `4x5`,
`5x4`, `9x16`, `16x9`, `2x3`, `3x2`, `1.91x1`, `3x1`. These are platform creator-guideline
conventions (subject to change); the renderer's `CanvasResolver.PRESETS` is their pixel source.

Book **trim sizes** (the final page size after cutting) are presets too, given in
**points @ 72 dpi** (like the print presets, so `--to pdf`/`pdf-tex` come out physically
correct): `book-pocket` 4×6 in, `book-mass-market` 4.25×6.87 in, `book-trade` 5×8 in,
`book-novel` 5.25×8 in, `book-digest` 5.5×8.5 in, `book-6x9` 6×9 in (nonfiction / hardcover
fiction), `book-7x10` 7×10 in (magazine-like), `book-8x10` 8×10 in (illustrated),
`book-textbook` 8.5×11 in, `book-square-8` 8×8 in, `book-picture` 8.5×8.5 in, `book-square-10`
10×10 in, `book-coffee-table` 9×12 in, `book-art-10x12` 10×12 in, `book-art-11x14` 11×14 in.

## 5. Styling, reuse, value types

### 5.1 Tokens

`defs.tokens`: `colors`, `fonts` (`FontDef`), `text_styles` (`Style`), `styles`
(`Style`), `stroke_styles` (`StrokeStyle`), `fill_styles` (`Fill`), `glyph_map`.

### 5.2 The style module — `Style` (authoritative; see `framegraph-v2-style.ebnf`)

The CSS-parity style module is a **separate authoritative file** adopted verbatim. `Style`
is a closed bag of ~80 CSS-mapped properties (snake_case ↔ CSS kebab-case, 1:1) across
six groups — **text/font**, **box/border/overflow**, **background** (multi-layer),
**paint** (fill/stroke), **effects** (`box_shadow`/`filter`/`backdrop_filter`/
`mix_blend_mode`/`clip_path`/`mask`), and **transforms** — plus **`class`** (compose
named token styles) and a bounded **`css`** raw-CSS escape (so there is no hard gap).

- `TextStyle` and `StrokeStyle` are **projections of `Style`** (`TextStyle = StrokeStyle
  = Style`). `tokens.text_styles`/`styles`/`stroke_styles`/`fill_styles` hold the
  corresponding values; `stroke_styles` entries use CSS-named `stroke_width`/
  `stroke_dasharray`/… .
- `fill`/`stroke` are **`Paint`** (`none | currentColor | Color | Image`, where `Image`
  covers gradients/patterns/url). Gradient stops use **`position`**; gradients add
  `conic`/`repeating`/`from`/`at`/`shape` and an `Angle` type.
- **Out of scope by design:** layout (FG owns it via `box`/`Layout`/`FlowRegion`) and
  CSS cascade/selectors/interaction/animation. The `css` escape covers the long tail.
- Legacy shorthand (`font`/`size`/`weight`/`italic`/`align`/`v_align`/`radius`/`wrap`) is
  accepted as **sugar** for the canonical names.

A badge is one `text`/`rect` with `background_color`+`border_radius`+`padding`; an
underlined link is `text_decoration` — no rect-behind-text workaround.

### 5.2.1 Cascade (explicit, not CSS's — spec §8.4)

Resolution order, lowest → highest: **(1)** target/theme defaults; **(2)** named token
styles in `style.class`, in order; **(3)** inline `style` properties; **(4)** the `css`
escape; **(5)** per-object convenience fields (`fill`/`stroke`/`radius`/`color`), which
desugar and **win on conflict**. No specificity, no selectors. Inheritance is limited to
inheritable text properties and flows only along `group`/flow nesting.

### 5.3 Fonts & pinning

`FontDef` = a family name or `{family, src?, hash?, fallback?, weight?, style?}`. A font
is **pinned** when it has both `src` and `hash` (content hash). Pinning is required for
deterministic text-derived sizing (§9.6).

### 5.4 Strokes

`StrokeStyle` = the geometry bundle (`color?`, `width?`, `dash?`, `arrow_start?`,
`arrow_end?`, `linecap?`, `linejoin?`, `opacity?`). See §3.5 for the single-form rule.

## 6. Flow vocabulary

`Flowable` ∈ `paragraph`, `heading`, `list`, `table`, `image`, `figure`, `block`,
`spacer`, `keep_together`, `page_break`, `column_break`, `code`, `math`, `toc`,
`bibliography` (+ index/glossary/endnotes, extended). `image`/`figure`/`table` carry
rich `caption` (`Caption` = string or inline runs) and a separate `credit` (P2). Inline
content (`Inline`) covers plain runs, `Span`, `ref`, `cite`, `footnote`, `math`, `code`.

## 7. Fixed vocabulary

`VisualObject` core: `rect`, `ellipse`, `line`, `polyline`, `path`, `dimension`,
`connector` (§3.11), `text`, `image`, `icon`, `bullet_list`, `table`, `group`.
(`circle`/`polygon`/`curve` are **deprecated** renderer shortcuts → `ellipse`/closed
`polyline`/`path`.) Charts, components/use/symbols, and the UML family are
**extended** (out of the core profile; §8.5).

## 8. Conformance

### 8.5 Classes & negotiation

A target declares the **core profile** plus whichever **optional** features it
supports; **out-of-profile** content is reported (warning), never silently dropped. See
`CHANGELOG.md` for the exact lists. Validation has two layers: structural (against the
models / generated schema) and the §3.3 static + geometric rules
(`tooling/validate.py`).

## 9. Reproducibility

### 9.3 Hermetic expansion

All imports/assets/fonts resolve at **expansion** and are content-hashed; nothing is
fetched at render. Expansion is acyclic.

### 9.6 Determinism precondition for content sizing (P4)

Any object whose size derives from text measurement (a non-`fixed` text leaf, or a
`hug` group containing such text) **MUST** reference only **pinned** fonts (`src` +
`hash`); a validator **MUST** error otherwise (`unpinned-font`), because the measure
pass would otherwise differ across machines. Content-sizing auto-layout and font pinning
are the **same** commitment.

**Honest limit.** Pinning the font *file* is necessary but **not sufficient** for
byte-identical layout. A defined shaping model is also required: shape with the font's
GSUB/GPOS under the object's `lang`, integer-round advances at the target DPI, and
exclude hinting from advance computation. Residual cross-engine variance bounded by
rounding is a stated **conformance tolerance** — not exact identity. Claiming
pixel-exact reproducibility from pinning alone would be false.

---

*This HEAD spec consolidates the base grammar and Patches 1–4 with the drafted style
module. It is a proposed design; the runnable artifacts (models, generated schema,
validator, codemod) are the parts to trust. (The former `RENDERER-PATCH.md`
companion was retired; renderer gaps are tracked in `docs/roadmap-draft.md` and
the renderer's own structured diagnostics.)*
