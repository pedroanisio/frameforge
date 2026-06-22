# FrameGraph v2 — CHANGELOG (HEAD)

**Version:** `2.2.0` · **Status:** PROPOSED / partially-implemented · **Date:** 2026-06-22

---

## 2.2.0 — adopt the authoritative style module (gap #1, for real)

A later batch supplied the two artifacts that were missing when 2.1.0 was cut: the
**authoritative CSS style module** (`framegraph-v2-style.ebnf`) and the **base spec**
(`framegraph-v2-spec.md`). 2.1.0 had *drafted* the style module by harvesting the
renderer; this release **replaces that draft with the real module**, which is richer
and differs in specifics. The architecture did not move — only the styling subsystem.

**What moved (style subsystem only):**
- **`Style` is the authoritative ~80-property bag** (text / box / background / paint /
  effect / transform groups) with **`class`** (named-style composition) and a **`css`**
  raw-CSS escape. New surface now accepted: `box_shadow`, `filter`, `backdrop_filter`,
  `mix_blend_mode`, `clip_path`, `mask`, multi-layer `background`, typed
  `transform`/`FilterFn`, `hyphens`, `white_space`, `word_break`, `writing_mode`,
  `font_stretch`/`font_variant_*`/`font_feature_settings`, `vertical_align`, etc.
- **`TextStyle` and `StrokeStyle` are now projections of `Style`** (`TextStyle =
  StrokeStyle = Style`). `tokens.stroke_styles` entries are Styles using **CSS-named**
  `stroke_width`/`stroke_dasharray`/… (not the old `{width,dash}` bundle).
- **`fill`/`stroke` are `Paint`** (`= none | currentColor | Color | Image`, where
  `Image` covers gradients/patterns/url). `Fill = Paint`.
- **Gradient stops canonicalise on `position`** (was `offset` in 2.1.0 — flipped to
  match the module + the fixtures; `conic`/`repeating`/`from`/`at`/`shape` added;
  `angle`/`from` accept an `Angle` like `"135deg"`).
- **Explicit cascade (spec §8.4):** theme → `style.class` → inline `style` → `css` →
  per-object convenience fields (`fill`/`stroke`/`radius`/`color`), which win on conflict.
- Legacy shorthand (`font`/`size`/`weight`/`italic`/`align`/`v_align`/`radius`/`wrap`) is
  **accepted as sugar** for the canonical CSS names, so existing styles keep validating.
- **Text-fit reconciliation (P2 Part C):** the delivered CSS module mirrored
  `line_clamp`/`text_overflow`/`max_lines` but dropped the two non-CSS FrameGraph
  autofit extensions. HEAD restores them on `Style`: `overflow` also accepts
  **`shrink_to_fit`** (beyond the CSS box values), and **`min_font_size`** (the autofit
  floor) is added back. These are the only HEAD additions to the authoritative module;
  without them the deck fixtures (which use `shrink_to_fit`) would not validate.
- Minor flow gaps closed from the authoritative fixtures: `toc.of`, `figure.align`,
  `block.role`/`block.stroke_style`, `bibliography.title`, image
  `preserve_aspect_ratio` (SVG string) and `clip` (shorthand).

**Migration:** additive for authors (richer styling; existing docs validate once the
model matches the module). The codemod gained: gradient `offset → position`, inline
stroke geometry → **CSS-named** `stroke_width`/`stroke_dasharray` in a `stroke_style`
Style, and `tokens.stroke_styles` bundle rewrite. Run:
```bash
python3 tooling/codemod.py your-doc.fg.json --in-place --bump
```

**Verification (asserted by `tests/test_head.py`, 12/12 green):** all **nine
authoritative fixtures validate at 2.2.0** — directly for those without legacy strokes
(`ieee`, `neutron-stars`, `spectral-methods`, `mckinsey-7s`), and after the codemod for
those that carry legacy inline strokes (`amazon-proxy`, `chroma-styling-showcase`,
`wireframing-guide`, `docusign-deck-v2` — **544 strokes migrated**). The schema is
generated-in-sync, and the P3 inline-geometry `stroke` is still rejected.

**Two source contradictions adjudicated** (flagged, not hidden): the base core grammar's
`GradientStop` uses `offset` while the authoritative style module uses `position` — the
module wins; and the base grammar still carried `Stroke = string | StrokeStyle` while
base-spec §3.5 says paint-only — already resolved (Stroke = Paint).

---

## 2.1.0 — fold the patch series (P1–P4) + draft gap #1

> Superseded by 2.2.0's adoption of the authoritative style module, but the rest of the
> 2.1.0 record stands.


> Honesty note (unchanged from the bundle's own stance): FrameGraph v2 is a
> **proposed, not-yet-conformantly-implemented** format. Everything here is a
> design target to verify, not a shipped standard. What *is* verifiable in this
> release: the schema is generated from the Pydantic models, and the validator +
> codemod run on the real fixtures (see "Verification" below).

---

## What HEAD is

A single, internally-consistent cut of FrameGraph v2 that folds the whole patch
series (P1–P4) and resolves the open gaps the complement identified:

- **Models are the source of truth** (`models/framegraph.py`). The **JSON Schema is
  generated** from them (`schema/build_schema.py`), so the two cannot drift.
- The **grammar** (`grammar/framegraph-v2.ebnf`) is one consolidated file =
  base + P1 + P2 + P3 + P4 + the inlined CSS style module. The earlier
  `framegraph-v2-revised.ebnf` (base+P1+P2) and the stray "v2.1" `framegraph-v2.ebnf`
  are **superseded**.
- The **validator** (`tooling/validate.py`) enforces the rules a schema can't
  express; the **codemod** (`tooling/codemod.py`) migrates documents to HEAD.

### Versioning rationale (read this)

The P3 stroke collapse is technically a **breaking** change. Strict semver would
make that a major bump. Because v2 was never released or conformantly implemented,
HEAD folds it into the v2 line as **2.1.0** with a mechanical codemod, rather than
inventing a "3.0.0". This is a deliberate, documented call — not an oversight. If
you have external consumers pinned to a pre-HEAD v2, treat 2.1.0 as breaking for
them and run the codemod.

---

## Breaking changes

### 1. Stroke has a single normative form (P3) — **BREAKING**

- `stroke` is now **paint only** (a `Color`). Stroke **geometry**
  (`width`/`dash`/`linecap`/`linejoin`/`arrow_*`/`opacity`) lives **only** in
  `stroke_style` (a token **or** an inline `StrokeStyle`).
- The inline `stroke: { width, dash, … }` form is **removed**.
- A `stroke_style` bundle's `color` is a default, overridden by an object's `stroke`.

**Migration (automated):**
```bash
python3 tooling/codemod.py your-doc.fg.yaml --in-place
```
The codemod splits each legacy inline `stroke`: `color → stroke` (paint),
geometry → `stroke_style` (inline). A `stroke` that was already a colour string is
unchanged. On the bundled fixtures this rewrote **17 inline strokes** (NYT ×5,
Wordle ×12); afterwards all five core fixtures validate with **0 errors**.

---

## Additive / non-breaking changes

| Change | Patch | Notes |
|---|---|---|
| Nested coordinates + layout box-model (`Layout.align`/`row_gap`/`column_gap`); group opacity composites the subtree as one unit | P1 | §3.6 |
| Text fit/truncation (`overflow:shrink_to_fit`, `min_font_size`, `line_clamp`, `text_overflow`) | P1 | §3.7 |
| `defs.assets` (content-addressed, hashed media); `src` may name an asset key | P2 | §3.5/§9.6 |
| Screen presets `phone`/`tablet`/`web` | P2 | §4 |
| `FlowSection.media: paged \| continuous` | P2 | §3.9 |
| `Pattern` fills (`hatch`/`cross_hatch`/`dots`/`grid`), region-clipped | P2 | §3.8 |
| Rich `Caption` (string or inline runs) + `credit` on image/figure/table | P2 | — |
| `grid_span` + sparse auto-placement; absent `layout` ⇒ `free` | P2 | §3.6e |
| `DimensionObject` (composite anchored dimension + measure pass) | P3 | §3.10 |
| Box-less primitives allowed under `free` (defined) | P3 | §3.6f |
| Geometric audit: containment, scoped non-overlap, tabular-box mandate | P3 | §3.3 |
| Content sizing `sizing: {width,height: fixed\|hug\|fill, grow, min, max}` | P4 | §3.6g |
| `fr`/`%` resolution defined (`1fr ≡ fill grow:1`) | P4 | §3.4 |

## Renames & resolutions

- **`size` → `sizing`** (P4). The content-sizing key collided with `IconObject.size`;
  it is renamed to `sizing` everywhere. `size` on an `icon` (numeric font size) is
  unchanged. The codemod renames content-sizing `size` objects to `sizing`.
- **gap #1 resolved.** The CSS style module is drafted as `Style` (+ `BorderSide`)
  and **inlined into the grammar**. `Style` supersedes the old `TextStyle` for
  `tokens.text_styles` and backs `tokens.styles`. Property names harvested from the
  reference renderer. The grammar has **no remaining dangling references**.
- **Gradient stops** canonicalise on `offset` (was `position` in the renderer);
  `position` is accepted as a deprecated alias and normalised by the codemod.

## Deprecated (accepted, normalised by the codemod)

- Renderer-shortcut primitives `circle` / `polygon` / `curve`(`bezier`) — normative
  forms are `ellipse` / closed `polyline` / `path`. Run
  `codemod.py --normalize-aliases` to rewrite them.
- Top-level `text_contract` — the normative home is a master/page
  `RenderingContract.text`.

---

## Conformance classes (the §8.5 mechanism)

HEAD defines a **core profile** (what the models validate and the schema covers)
and an **extended set** (grammar-allowed, out of the deep profile). A target
declares which it supports; out-of-profile content is a *warning*, never a silent
failure.

- **Core (REQUIRED):** the document envelope; `defs.tokens` (colors, fonts,
  `text_styles`/`styles` via `Style`, `stroke_styles`, `fill_styles`, `glyph_map`),
  `defs.assets`, `defs.masters`; fixed pages with `rect`/`ellipse`/`line`/`polyline`/
  `path`/`text`/`image`/`icon`/`bullet_list`/`dimension`/`table`/`group`; flow
  sections with the `Flowable` set; the box-model, text-fit, sizing, pattern, and
  stroke rules above.
- **OPTIONAL (declarable unsupported):** `media: continuous`, `Pattern` tiling,
  `shrink_to_fit`, the `dimension` measure pass, rich captions/credit, `grid_span`
  spanning, group-opacity isolation. A target that can't do one emits a diagnostic
  and degrades per the spec, never a blank.
- **Out-of-profile (extended):** the UML object family, `bar_chart`/`line_chart`/
  `legend`, `component`/`use`/`symbol`, `connector`, `ontology`/`semantic`. Accepted
  by the grammar; reported by the validator as `out-of-profile`; not modelled at HEAD.

---

## Verification (what actually runs in this release)

```bash
# 1. schema is generated from the models and in sync
python3 schema/build_schema.py --check          # -> "OK: schema is in sync with the models."

# 2. validate the migrated fixtures (core profile)
python3 tooling/validate.py fixtures/*.fg.yaml  # -> 0 errors (advisory warnings only)

# 3. migrate a legacy document to HEAD
python3 tooling/codemod.py legacy.fg.yaml --in-place
```

**Fixture status after migration (in this repo):**

| Fixture | Errors | Note |
|---|---|---|
| calendar-3day, edst1-flange, myfiles-internal, nyt-mideast-live, wordle-how-to-play | **0** | core profile; advisory warnings only (overlap/tabular/containment/alias) |
| anthropic_claude_deck_improved, esfera_improved | **0** | out-of-profile warnings only |
| coopera_polished, coopera_tables | **2 each** | genuine non-conformance: an `image` carries a `stroke` (images have no stroke in the grammar). Not a tooling gap — fix the source (remove the stroke or use a bordered rect / `Style.border`). |

---

## How the three prior documents relate

- `FrameGraph-2.0.0-Specification.md` — the reverse-engineered spec (from the
  renderer). **Provenance**; superseded by `spec/framegraph-v2-spec.md` at HEAD.
- `FrameGraph-2.0.0-Specification-Complement.md` — the reconciliation that produced
  these recommendations. **Provenance**; its §8 actions are resolved below.
- This release implements those recommendations.

## Recommendation resolution (from the Complement §8)

| # | Recommendation | Resolution at HEAD |
|---|---|---|
| 1 | Draft/promote the CSS style module (gap #1) | **Done.** `Style` + `BorderSide` drafted (harvested from the renderer) and inlined into the grammar + modelled in Pydantic. |
| 2 | One canonical grammar; discard the stray | **Done.** `grammar/framegraph-v2.ebnf` is the single consolidated grammar; revised + stray superseded. |
| 3 | Generate the schema from Pydantic; extend to P3/P4 types | **Done.** Schema generated from the models (`Dimension`, `AssetDef`, `Caption`, `Sizing`, `Style` all present); `build_schema.py --check` enforces sync. |
| 4 | Fold P3 + P4 into the grammar; run the stroke codemod | **Done.** Grammar carries P3/P4; codemod run on fixtures (17 strokes split). |
| 5 | Rename `size` → `sizing` everywhere | **Done.** Models/schema/grammar use `sizing`; codemod renames legacy `size` objects. |
| 6 | Enforce stroke single-form | **Done.** Models reject inline-geometry `stroke` with an actionable message; validator rule `stroke-single-form`. |
| 7 | Font-pinning precondition + defined shaping tolerance | **Done (validator) / specified (shaping).** `FontDef.hash` added; validator errors on content-sized text using an unpinned font (`unpinned-font`). Shaping model + rounding tolerance specified in the spec §9.6 (stated as a tolerance, not pixel-exact). |
| 8 | Pick an implementation of record or mark features OPTIONAL | **Specified.** Conformance classes above; `RENDERER-PATCH.md` specifies the ReportLab renderer's HEAD changes; the proxy renderer is patched in `tooling/render_fg_doc.py`. |
| 9 | Coopera unconverted regions; validate against ReportLab not proxy | **Tracked.** 61 borderless regions remain intentionally unconverted; the 2 residual coopera errors above are real (image+stroke), surfaced by the validator, to fix at source. |
