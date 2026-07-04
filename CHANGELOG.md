# FrameGraph v2 — CHANGELOG (HEAD)

**Version:** `2.4.1` · **Status:** PROPOSED / partially-implemented · **Date:** 2026-07-03

---

## Unreleased — chore: runtime `framegraph.__version__` + `make release` (§16 row 7, 2026-07-04)

Closes the runtime-version half of the package-emit gap. `framegraph.__version__`
is now a real attribute on the package — a fifth version literal that `make bump`
moves in lockstep and `tests/test_docs_in_sync.py` gates against `[project]
version`, so the package can report its own version and it can never drift. A
plain literal (not `importlib.metadata`) because this is a virtual, uninstalled
project. New `make release VERSION=X.Y.Z` runs the whole recipe end to end — bump
every site → regenerate schema/manifest/SDK-snapshots/status/examples-index →
`make check` — leaving only the git-tag and CI-publish steps by hand (it prints
them). RELEASE.md updated to five literals + the `I2b` invariant; codebase-standards
§9/§16 row 7 marked done.

## Unreleased — item 1: declarative graph auto-layout (the render-time bridge, 2026-07-04)

`sdk.topology.Graph` already computed node placements from declared edges,
but only author-side (call a layout method, bake the coordinates). This
wires it as a DECLARATIVE, expansion-tier form (roadmap item 1 — the
missing render-time bridge; the placement math was already done):

- A grammar-level `type: graph` object (`nodes` + `edges` + `algorithm`) is
  lowered by `sdk.expand` into a positioned core `group` — the SDK computes,
  the document receives plain `ellipse`/`polyline`/`text` geometry (§A.0).
  `algorithm: auto` infers grid/radial/layered/spring from structure; a
  node's `pos` OVERRIDES the computed position. **No schema change**: `graph`
  is a pre-expansion authoring type, exactly like `use`/`component`, and
  never reaches the validated document.
- `Graph.to_object(box=…, algorithm=…)` emits that declarative form fluently
  (positions NOT baked — the same declaration always lays out the same way).
- The `expand` early-return now also detects self-contained `graph` objects,
  so a document with no `defs.symbols`/`components` still lowers them; a
  document with no expansion form is byte-identical through `expand` (golden
  stability preserved).

13 red-first tests (`tests/test_sdk_graph_expand.py`); fixture
`graph-autolayout.fg.yaml` (four graphs: auto→layered/radial/spring + an
explicit circular override), pixel-verified 0 clipped/0 uncontained;
runnable `static/examples/graph_autolayout_demo.py`; MCP guide bullet
(drift-gated). Roadmap item 1 → **DONE** (residual: optional ELK binding).

## Unreleased — fix(pdf-tex): transforms reach text; effect + appearance stacks render (2026-07-04, issue #53)

Three silent-fidelity gaps on the `--to pdf-tex` path (the
`latex.tikz.FigureTikz` transpiler), all operator-reported from the book
PDF and verified in rasterized pixels:

- **`style.transform` now reaches text.** A TikZ scope transform moves
  `\node` ANCHORS but leaves glyphs unscaled/unrotated — a 0.5-scaled
  group painted full-size text over shrunken geometry. The transform scope
  now carries `transform shape`, so text obeys it (repro: scaled "SCALED?"
  text ended at x≈331 of 400 before, x≈175 after). Fixed in both the
  transpiler and the injectable `TikzPainter`; the painter's `raw`
  transform branch also now parses SVG-syntax `scale(0.5)` into valid TikZ
  `xscale/yscale` (it was emitting invalid `scale(0.5)` the TeX engine
  ignored).
- **The 2.4.0 `effects` stack renders.** The ordered stack was dropped
  silently — only the legacy `shadow`/`glow` fields got the flat
  approximation. Stack entries now get the same shadow/spread-glow
  approximation (blur is approximated, never silent).
- **The 2.4.0 `appearance` stack renders.** Multiple paint passes were
  collapsed to the bare geometry; each pass now paints its own path,
  bottom→top, mirroring the Renderer's `_appearance_stack`.

The `TikzPainter` ScenePainter port (no filter primitive at all) declares
`supports_filters = False` and the Renderer warns per dropped effect
rather than losing it silently (#44). 12 red-first tests
(`tests/test_tikz_fidelity.py`); the pinned latex-scope assertions that
encoded the old bug were corrected. SVG output is byte-identical (goldens
unmoved).

## Unreleased — item 8: the Book composition API (2026-07-03)

`framegraph.sdk.book` — the semantic authoring layer above pages
(roadmap implementation-sequence step 5; zero grammar change):
`BookBuilder(title=, author=)` composes front matter and
chapters/sections into ONE validated flow document, lowered through
`FlowBuilder` and paginated by the ADR-0003 engine. Numbering is computed
at build time (§A.0 — the renderer has no counter engine): chapters `1`,
sections `1.1`, per-chapter figure labels folded into captions
(`Figure 2.1 — …`). Chapters open on fresh pages; `keep_with_caption`
holds a figure and its caption together (`break_inside: avoid`). Two
defects caught by pixel verification and fixed in the design: the book no
longer lists ITSELF in its own Contents (the title is front-matter
display, not a heading), and a BOXLESS figure object (e.g. a computed
`stroke_outline` path) gets its size derived from the geometry instead of
silently reserving zero flow height and painting over the next block.
10 red-first tests (`tests/test_sdk_book.py`, incl. the render gate:
clipped == 0, numbered captions reach the pixels); fixture
`book-composition.fg.yaml` (corpus 37→38, 0/0); runnable
`static/examples/book_builder_demo.py`; MCP guide bullet (drift-gated).

## Unreleased — PALS PT-BR migrated; gradient fill tokens now lift AND paint (2026-07-03, issue #33)

Third corpus deck: the 15-slide PALS PT-BR deck lands as
`tests/fixtures/pals-genai-arch-ptbr.fg.yaml` (corpus 36→37; 0 errors, two
honest tabular advisories on the hand-positioned math appendix). One new
dialect corner, closed in two layers:

- **Lift** (`codemod.py --from-v01`): v0.1 gradient fill tokens
  (`tokens.fill_styles` `{type: linear_gradient, from/to points, stops
  with offset+opacity}`) become v2 `Gradient` paints — from/to vector →
  CSS `angle`, `offset` → `position`, stop `opacity` folded into an
  8-digit hex against the pack palette (v2 stops carry no opacity field).
- **Renderer**: `Tokens.fill_styles` was model-declared but NEVER read —
  a string fill naming a fill-styles key silently emitted invalid SVG
  paint. `paint()` now dereferences `tokens.fill_styles` first, so named
  gradient/pattern fills actually paint (regression-tested).

Verified page-by-page against the sibling's own renderer (15/15 pages;
deltas are the known cross-renderer font face + in-box wrapping, no
content loss — `clipped == 0`, spill only via the explicit v0.1 policy).
3 new red-first tests (19 total). Checklist honesty: **faz-ai and
code-base-mapper are #30-gated** (49/57 `type: uml` objects — the
unabsorbed UML composers); GTDS awaits the token-pack decision.

## 2.4.1 — parity W1: the planar geometry kernel + the DocumentRenderer port (2026-07-03, issue #45)

Also in this patch: the **`DocumentRenderer` output port** (hexagonal seam)
— the CLI's html / pdf-tex targets render through in-process backends
(`rendering/infrastructure/backends/`) instead of shelling out to our own
scripts; one registry adapter per `--to` target
(`tests/test_document_backends.py` locks the contract).

`framegraph.sdk.planar` — one expansion-tier kernel closes five rows, zero
schema change (§A.0: the SDK computes, documents receive even-odd `path`
objects): **booleans** `union`/`intersect`/`subtract`/`divide`
(Greiner–Hormann on flattened rings; degenerate touching/shared-edge inputs
resolved by a deterministic direction-cycling perturbation that prefers the
ENGAGED answer; holes emitted natively as multi-ring even-odd paths —
AI-04 PARTIAL→HAS, AI-05 NONE→REFRAMED), **path surgery** `split_at`
(arc-length scissors) + `cut_along` (knife via half-plane booleans —
AI-06 NONE→HAS), **`offset_polygon`** (closed, miter-exact corners,
collapse detected by edge-direction reversal, not just area sign — a
double-inverted shrink traces a *positively*-oriented ring — AI-47
NONE→HAS), and **`fill_regions`** (Live-Paint decomposition as boolean
atoms, authoring scope ≤8 shapes — AI-17 PARTIAL→HAS). Stdlib-only, pure,
deterministic. 18 property tests (areas, ring counts, membership, length
conservation); fixture `planar-kernel.fg.yaml` (corpus 35→36, 0/0)
pixel-verified — holes punch through, divide partitions, nested offset
rings, knife halves, region faces each their own colour. Teardown + audit
regenerated: **25 HAS / 5 PARTIAL / 11 REFRAMED / 10 NONE** (full 49 %,
reachable 80 %) — **the maturity-gap pool is now empty**.

## 2.4.0 — parity W4: style & colour richness (2026-07-03, issue #48)

**Schema minor bump 2.3.0 → 2.4.0** — two ADDITIVE model fields on ObjBase,
both outside the deep-core profile (§8.5, charts precedent; grammar core
untouched, schema regenerated to 85 $defs):

- **`effects`** (AI-30 PARTIAL→HAS): an ORDERED effect stack — entries
  `{kind: shadow|glow, preset?, color/blur/dx/dy/opacity?}` apply
  first→last and a kind may repeat (the single `shadow`/`glow` fields
  cannot); presets seed params, explicit keys override. Absence is
  identity (effect-free renders are byte-identical; golden gate green).
- **`appearance`** (AI-32 PARTIAL→HAS): multiple paint passes over one
  geometry — each pass paints only what it declares (fill / stroke /
  stroke_style / opacity), bottom→top; clones drop ids/binds so identity
  appears once; object-level effects and opacity wrap the whole stack.
- **`sdk.recolor(doc, mapping)`** (AI-16 PARTIAL→HAS): one-call palette
  remap — `defs.tokens.colors` by name or value, paint literals under
  paint keys only (a hex inside text content is never rewritten), and
  gradient stops; case-insensitive, input never mutated.
- **`chevreul.color_guide(base)`** (AI-18 PARTIAL→HAS): the six Chevreul
  harmonies for any base colour (snapped to its nearest wheel station),
  ready to feed `closed_palette` / `recolor`.

13 red-first tests (`tests/test_style_richness.py`); fixture
`style-richness.fg.yaml` (corpus 34→35, 0/0 — the effect filters are
structurally verified in the SVG; the cairosvg proxy ignores filter
primitives, browsers render them); runnable
`static/examples/style_richness_showcase.py`. Teardown + audit
regenerated: **21 HAS / 7 PARTIAL / 10 REFRAMED / 13 NONE** (full 41 %,
reachable 75 %).

## Unreleased — parity W2: the stroke-outline engine + curve/type finesse (2026-07-03, issue #46)

`framegraph.sdk.outline` — one shared filled-outline emitter closes three
verdicts and two finesse rows, all at author time (nothing new enters the
schema): `stroke_outline(points, width, …)` lowers a stroke centre-line to
a CLOSED filled `path` — constant width is Outline Stroke (AI-48 NONE→HAS),
a `profile(t)` callable is the Width tool (AI-12 NONE→HAS), a calligraphic
pen (`pen_angle`/`pen_thin`: width `w·√(cos²Δ+thin²·sin²Δ)` vs the tangent)
is the calligraphic brush, and `repeat_along_path` (arc-length placements
with tangent rotation, `stamp=` for direct object copies) is the
scatter/pattern half (AI-49 NONE→PARTIAL — art-brush stretch and Blob stay
honest gaps). Caps butt/square/round (round routed explicitly through the
outward direction — the shorter-sweep arc is ambiguous at π), joins
miter/bevel/round. `Path.through()` (Catmull-Rom) verified + tested as the
declarative curvature tool (AI-09 PARTIAL→REFRAMED). Kerning (AI-24
PARTIAL→HAS): `kerned_spans` (explicit pairs as grammar-native span
styles) + `font_kern_pairs` (the resolved font's kern table via fontTools;
degrades to `{}`). **Renderer fix found by pixel-verifying this feature**:
structured-`d` segments arrive as TUPLES from a pydantic model dump and
all three painters (SVG + both TikZ sites) only lowered lists — every
structured path silently rendered as a stringified Python tuple (garbage
that also hangs cairosvg). 16 red-first tests (`tests/test_sdk_outline.py`)
incl. the round-trip regression; fixture `stroke-outline.fg.yaml` (0/0),
runnable `static/examples/stroke_outline_showcase.py`. Teardown + audit
regenerated: **17 HAS / 11 PARTIAL / 10 REFRAMED / 13 NONE** (full 33 %,
reachable 75 %).

## Unreleased — parity W6: six teardown verdicts corrected by documentation (2026-07-03, issue #50)

The cheapest scoreboard movement, delivered exactly as scoped: zero schema
change, every claim verified against live code before any doc moved (PALS).
Five rows re-verdicted **PARTIAL → REFRAMED ·H** — anchor editing (restate
the coordinate: MCP `workspace` pin/nudge/snap + `construct_vectors`),
isolation mode (name the nested id; the cursor hazard has no declarative
analogue), the Bézier pen (coordinates are the pen; `construct_vectors` +
coach are the assistive half), artboards (pages + per-page canvas + render
targets, by design), guides/rulers/snap (exactness by construction +
`canon.content_box` grids + `workspace` snap). AI-40 verified in code:
`Scene3D.extrude`/`.revolve`/`Material` are real and project to 2D vector
faces — evidence corrected, verdict honestly stays **PARTIAL ·H** (no
bevel). Bonus: the REFRAMED narrative example mislabeled Image Trace as
AI-40 (it is AI-39) — fixed. Teardown deck + git-stamped audit regenerated:
**14 HAS / 12 PARTIAL / 9 REFRAMED / 16 NONE**; reachable-by-any-route
stays 69 % (W6 adds no capability, by design). Roadmap Appendix B + the
workstream table re-verdicted to match.

## Unreleased — PALS EN deck migrated; the v0.1 lift learns the deck dialect (2026-07-03, issue #33)

Second corpus deck: the 8-slide PALS GenAI architecture deck (EN) lands as
`tests/fixtures/pals-genai-architecture.fg.yaml` (corpus 32→33; 0 errors,
one honest tabular-box-model advisory on the hand-positioned slide-8
matrix). Four dialect corners closed in `codemod.py --from-v01`, red-first:

- **`chip_row`** (v0.1 compositional pill row) lowers to a core `group` of
  decorative pill rects + centered texts — same cursor/gap layout, the
  `chip` component def's fill/text_style/radius baked in; a consumed def is
  dropped (lossless), unconsumed defs are kept.
- **Flat span styles** (`{text, weight, color}`) nest into a translated
  inline `style` (v2 `Span` allows text/style/lang only).
- **Flat object `stroke_width`** moves into `stroke_style` (P3).
- **v0.1 wrap semantics pinned**: text wrapped only under `wrap: true`, and
  overflow painted past the box — styles without `wrap` now get
  `white_space: nowrap` and deck-form pages get
  `rendering.text.overflow: visible`. Found the hard way: under v2's
  wrap-then-clip default, slide 3's consequence sentence was silently
  truncated mid-word — exactly the #44 failure class; the gate now asserts
  `clipped == 0` and spill only via the explicit policy, and the genai
  fixture regenerated under the same rules moved *closer* to its v0.1
  reference (RMSE 14.7 → 13.3). PALS renders verified page-by-page against
  the sibling's own renderer (mean RMSE 18.4/255, differences are font
  rasterization and tighter in-card wrapping, no content loss). 6 new
  red-first tests (16 total in `tests/test_codemod_v01.py`).

## Unreleased — font determinism end to end (ADR-0004, 2026-07-03)

The measure==render loop is closed, host-independently
([ADR-0004](docs/adr-0004-single-engine-layout.md)):

- **Browser-faithful font resolution** in the layout metric, and a
  **screaming `font_substitution` warning** (diagnostics + stderr, once per
  family) whenever a requested content font is not installed — silent
  substitution is banned (PALS's Law applied to fonts: an unverified
  measurement is a defect).
- **`fg-font` is a real console command**: implementation moved in-package
  (`framegraph.fontpack`), registered under `[project.scripts]` — resolves
  after install (this tree stays a virtual project, where the
  `tooling/fg_font.py` launcher and `make font-*` targets keep working).
  `--list` resolvable families · `--check DOC` determinism gate · `--pack
  DOC --out P.fp` portable font pack (exact TTFs + sha256 manifest).
- **`fg-font --pack --fetch` — a Google Fonts proxy**: families the authoring
  host lacks are provisioned from the open `google/fonts` corpus and stamped
  `source: "google-fonts:<slug>"` in the manifest, so a reproducible pack can be
  built from a thin machine (no font-rich image needed) and `--check --fetch`
  becomes self-healing.
- **`render_chromium.py --font-pack P.fp`** consumes a pack: fontconfig is
  scoped to the pack (real metrics forced) before Chromium launches, so the
  layout metric and the browser resolve the identical faces — produce →
  consume → render in one flag.
- Justified flow lines no longer get cavernous letterspacing when a line is
  lone or underfull (follow-up fix to the Knuth–Plass batch below).

## Unreleased — v0.1 deck-corpus conversion path (2026-07-03, issue #33)

`tooling/codemod.py --from-v01` lifts both v0.1 envelope forms to v2 —
scene-form (`scene:`/`semantic:`/`visual:` → one page carrying the semantic
block and rendering contract) and deck-form (`deck:`/`slides:` → defs +
one page per slide) — then the standard HEAD rules finish (P3 stroke split,
`stroke_styles` Style projection). The lift also fixes the two silent
semantic traps: v0.1 text-style keys (`font`/`size`/`weight`/`v_align`)
and stroke bundles validate in v2 as unrelated CSS props and must be
renamed, not carried. Unknown top-level keys ride in `meta`. Conversion
proof per the issue's own AC: the genai-ecosystem production diagram —
committed v0.1 source (`tests/data/v01/`) → fixture
`genai-ecosystem.fg.yaml` (corpus 31→32, 0 errors 0 warnings), rendered
98.8 % pixel-identical to the v0.1 reference (RMSE 14.7/255; one label
wrap point). 10 red-first tests (`tests/test_codemod_v01.py`); recipe at
`docs/migration-v01.md`; remaining decks tracked on #33 as on-demand.

## Unreleased — content library: themes, symbol packs, generators (2026-07-03, issue #32)

`framegraph.library` — the predecessor project's content library absorbed
as committed v2 data (§13 bounded context). 7 consulting token packs
(`bain`/`bcg`/`deloitte`/`ey`/`kpmg`/`mckinsey`/`pwc`) translated to
`defs.tokens` fragments; 4 symbol packs (`covers`, `sections`, `shared`,
`hex` — 13 symbols) lowered through `sdk.expand`; the two data-driven
generators (`honeycomb_capability_map`, `module_hub_radial`) ported with
their geometry and committed example data. Translation notes: v0.1 style
field renames (`font`→`font_family` lists, `size`/`weight`→`font_*`,
`v_align`→`vertical_align`), P3 stroke split with Style-bag names
(`stroke`/`stroke_width`/`stroke_dasharray`), `ellipse` → center/rx/ry;
generators drop v0.1's `hash()`-derived color tokens (nondeterministic)
for literal pass-through, auto-grow the honeycomb canvas instead of
clipping, and paint the hub detail block above the node layer. Gates:
`tests/test_library.py` (7 theme render probes, symbol expansion, both
generators reproduce their examples, zero uncontained text everywhere);
fixture `library-honeycomb.fg.yaml` (corpus 30→31, 0 errors 0 warnings);
runnable `static/examples/library_showcase.py`. Docs: `docs/library.md`.

## Unreleased — backend-neutral flow layout · Knuth–Plass + hyphenation (2026-07-02)

Flow-mode prose gets a single backend-neutral layout engine
(`framegraph.rendering.domain.services.flow_layout`); see
[ADR-0003](docs/adr-0003-backend-neutral-flow-layout.md). *Own the breaks, delegate
the spacing.*

- **Line breaking** is Knuth–Plass total-fit (1981); **hyphenation** is Liang
  patterns via `pyphen` (new runtime dependency) — replacing greedy,
  estimate-based, left-aligned wrapping that produced rivers and lopsided margins.
- **Column geometry** resolves from the page master (explicit region → margin →
  the Johnston canon, **mirrored recto/verso**) instead of a hard-coded symmetric
  `margin = 56`; the flowed body finally honours authored geometry and mirrors the
  way the running header already did.
- Each line is emitted as **one text element**, justified to its column via SVG
  `textLength` — **flush on browser/PDF, tight hyphenated ragged on the cairosvg
  proxy** (which ignores it). First-line indent + no inter-paragraph gap.
- **Page mode too.** `render_text` (page-mode `wrap:true` boxes) also routes
  `align:"justify"` through the engine — it previously mapped justify → the
  `start` anchor and could not justify at all. Justification now exists
  document-wide (flow + page mode), including **span-aware** justification:
  inline bold/italic survive a justified wrapped block (runs are re-sliced onto
  each line by char offset).
- **Render change (golden re-pin)**: the four flow fixtures + one page-mode deck
  (`amazon-proxy-2026`, which uses justified prose) re-pinned; all other decks
  byte-unchanged.
- **Adversarial multi-agent review** fixed six confirmed defects in the new code:
  justify+`shrink_to_fit` over-shrink; the justification params crashing the TikZ
  backend; `content_box` not coercing `Length` margins, not clamping non-positive
  area, and not mirroring an asymmetric master margin; recto/verso parity using a
  section-local instead of document-global page number; and a single unbreakable
  token (a URL) dropping the whole paragraph to greedy.
- *Limit:* tight **flush** justification needs a **pinned body font** (layout
  metric = render font); unpinned, flush over-stretches (uniformly airy, not
  rivers) — tight ragged is the safe default.

## Unreleased — pattern compose: filled patterns become pages (2026-07-02, issue #29)

`framegraph.patterns.compose(pattern_id, fill)` bridges the #28 catalog to
rendered output: payload validated through the fill contract first (layout
never runs on unvalidated content), zone boxes computed deterministically
from the anchor vocabulary (column bands / quadrant grids / mixed BMC
columns; regions and relative placements stack in declaration order as a
documented approximation), enterprise-layout treatments applied (card
fill/stroke/corner, accent bars, label slots with slot typography), and
content emitted per content_type as plain core objects — nothing new enters
the schema, and the returned document is pre-validated. Acceptance gate as a
test: all 17 sidecared example fills compose, validate, and render with zero
uncontained text; SWOT/BMC/Diagnostic verified against rendered pixels.
Sample: `static/examples/pattern_compose_deck.py`. 6 red-first tests.

## Unreleased — pattern catalog + fill contract absorbed as data (2026-07-02, issue #28)

New bounded context `framegraph.patterns`: the predecessor's 375-pattern
slide-template catalog and 17 fill sidecars land as committed data with a
strict Pydantic contract — controlled vocabularies for zone size / placement /
content_type, `load_fill` deriving a typed `{role: content}` payload model per
pattern (sidecar overrides enforced: the BMC's object items reject plain
strings), and every committed `example_fill` round-tripped by the test gate.
The catalog count is LOCKED at 375 — truncation is a failing test, not a
smaller number. Rendering a filled pattern into v2 pages is the #29 bridge,
deliberately not part of this change. Docs: `docs/patterns-fills.md` (adapted
from the predecessor's AGENTS.md / AUTHORING-FILLS.md guidance). 11 red-first
tests.
## Unreleased — from-markdown: whole documents in, flow documents out (2026-07-02, issue #31)

`sdk.from_markdown(text)` converts a CommonMark/GFM-subset document into a
validated `mode: flow` page — pagination, text fitting and list/table layout
come from the flow engine, and inline forms reuse the existing `md()`
lowering (one inline parser, not two). Hand-rolled line parser, no new
dependency. Covered: headings, paragraphs, lists (model has no nested list —
sub-items fold into the parent as marked continuation lines), GFM tables,
fenced code, blockquotes (`block` with `role: blockquote`), image paragraphs,
thematic breaks → page breaks, YAML front-matter; the ```framegraph pattern
directive degrades to a structured warning until the fill/render bridge
(#29). Output is schema-validated before it is returned (PALS). The CLI
front door accepts `.md` inputs directly and writes the intermediate
`.fg.yaml` next to the render output. 11 red-first tests.
## Unreleased — render front door works PYTHONPATH-free (2026-07-02, issue #35)

Three src-layout refactor casualties in the CLI path, fixed at root:

- `framegraph.sdk.model` falls back to deriving `<repo>/docs` from its own
  location when `models` is not importable (callers with PYTHONPATH win; the
  fallback only appends) — the `ModuleNotFoundError: models` crash is gone
- `framegraph.cli` derives ROOT for the src layout, so default output goes to
  `<repo>/out/render-cli`, not `src/out/`
- new `tooling/framegraph_render.py` launcher: the working front door for the
  virtual project (`uv run python tooling/framegraph_render.py doc --to svg`),
  self-bootstrapping, any CWD, no PYTHONPATH; delegates to `framegraph.cli`.
  The `[project.scripts]` entry stays inert by the §2 packaging decision (the
  session's earlier "working" console script was a stale pre-refactor venv
  artifact). The docker entrypoint's `framegraph-render` verb now maps to the
  module form (the image sets PYTHONPATH)
- pyproject/AGENTS/codebase-standards §2 advice updated; 4 red-first tests

## Unreleased — design-canon SDK modules (2026-07-02)

Two pure-helper modules codify working design rules for document authors
(human or agent), sourced from Chevreul (1839) and Johnston (1906); no schema
change. Surfaced in the SDK guide/API snapshots, the capability manifest, and
the MCP guide's module catalog.

- `framegraph.sdk.chevreul` — the 12-station painter's wheel + `complement`,
  Chevreul tone scales, the six harmonies, WCAG 2.1 `relative_luminance` /
  `contrast_ratio` (the numeric primitives for text-on-ground legibility and
  the #44 diagnostics work), `grey_document` (the tone audit), and
  `closed_palette` with duties + the 62/30/8 area guide emitting a
  `defs.tokens.colors` fragment.
- `framegraph.sdk.canon` — `modular_scale`, Johnston's margin canon
  (`johnston_margins` / recto-verso `content_box`), the 45–75 measure band,
  `caps_tracking`.
- **Canonical fixtures** `tests/fixtures/chevreul-harmonies.fg.yaml` and
  `canon-typography.fg.yaml` — generated from the modules' own output, so a
  regression in either module shows up as a fixture diff.
- **Renderer bugfix (render change)**: `reading_order` no longer reorders SVG
  emission. The old path hoisted listed objects to the *front* of the paint
  stack, so any unlisted background painted over every listed text (found by
  rasterizing the new fixtures). Paint order is now always layer/z/document
  order; the authored order rides on the page group as `data-reading-order`
  for a future tagged export. Pages using `reading_order` with overlapping
  content render differently (correctly) from 2.3.x snapshots; the b1 golden
  corpus is unaffected (no `reading_order` usage).

## Unreleased — per-object truncation diagnostics (2026-07-02, issue #44)

Silent content loss is over: the text-fit containment now NAMES every text
object that materially loses content (id, page, lines kept/dropped, the head
of the dropped text, and whether the clip was explicitly authored).

- renderer: `diagnostics["truncations"]` records material loss only (dropped
  lines; glyph runs cut beyond rounding tolerance; >½ line clipped) — a
  sub-pixel descender trim keeps the clip-path and the aggregate count but is
  not content loss
- `render_fixtures --check-overflow` prints the named listing (capped at 20 in
  default runs); new `--strict-content` fails on any SILENT loss
- MCP render results: records ride `diagnostics.truncations` (and
  `diagnostics.json`); the render warning quotes the first silent ids
- `validate.py --text-fit` (opt-in): advisory `text-truncated` WARN per object
- spec §3.7 gains the diagnosability sentence; `docs/error-codes.md` documents
  the code
- **known state**: the curated fixture corpus currently carries 211 silent
  material losses, now visible in every overflow run — remediation
  (fix boxes vs acknowledge explicitly) is operator-directed follow-up, which
  is why `--strict-content` is not yet wired into `make check`

## Unreleased — dockerized MCP for foreign codebases (2026-07-02)

The container contract now lets any codebase fully interact with the SDK and
MCP surface (2026-07-02 audit findings: stale image, invisible host paths,
ephemeral SDK clients). Gated by `tests/test_docker_contract.py` and
`tests/test_mcp_edit_roots.py`.

- **Edit roots may leave the repo** (behavior change): explicitly configured
  absolute `FRAMEGRAPH_MCP_EDIT_ROOTS` entries are honored literally — the
  image sets `/work/clients:/app/static/examples`, so `write_sdk_client` with
  a **bare filename** creates on the persistent volume and survives `--rm`.
  Bare names are searched across roots (a miss is now `FileNotFoundError`,
  not a confinement error); relative paths *with* directories keep the strict
  repo-relative rejection. Out-of-repo paths are reported absolute.
- **Foreign-codebase wiring** (`docker/mcp.docker.json`): the consuming
  project mounts read-only at `/workspace` (tool calls reference
  `/workspace/<path>`), with `FRAMEGRAPH_MCP_INPUT_ROOTS=/workspace:/work:/app`
  confining propose inputs.
- **Freshness is detectable**: a `version` entrypoint verb (package +
  `HEAD_VERSION` + build stamp), an OCI version label wired by
  `make docker-build`, and `PYTHONPATH=/app/src:/app/docs` fixing the
  post-refactor in-image imports.
- **Installable consumption skill**: `skills/framegraph-mcp-docker/SKILL.md`.

## Unreleased — src-layout folder refactor (2026-07-02, complete)

Repository reorganisation; rendered output verified byte-identical (the golden
lock's 87 page hashes are unchanged — only its fixture-path keys re-rooted).
Path mapping (older CHANGELOG entries below keep their original paths — read
them through this table):

| Old | New |
|---|---|
| `framegraph/` | `src/framegraph/` |
| `models/`, `schema/`, `grammar/`, `spec/` | `docs/models/`, `docs/schema/`, `docs/grammar/`, `docs/spec/` |
| `fixtures/` | `tests/fixtures/` |
| `examples/` | `static/examples/` |
| `framegraph_to_html.py`, root reports (`FIXTURE-STATUS.md`, `codebase-standards.md`, `request.md`, `architecture-map.*`) | `tooling/`, `docs/` |
| `brand/`, `demo/`, `recipe/`, `POC-*.md` | retired from the tracked tree (regenerate brand assets via `static/examples/framegraph_logo.py`) |

Completion notes (refactor finished 2026-07-02):

- Every path reference rewired: `conftest.py` + per-file test/tooling
  bootstraps (`src/` for the package, `docs/` for the `models` namespace),
  package-internal repo-root derivations (`parents[3]`), MCP subprocess
  `PYTHONPATH`, MCP editable-client roots (`static/examples`), Makefile
  (`FIXTURES_YAML`, schema paths, `PYTHONPATH` for `-m` targets), CI
  version probe, mkdocs (`exclude_docs` for the in-`docs/` sources),
  viewer dev scripts, `.gitignore`, `.mcp.json`.
- **Gates:** `make check` is 12 gates and green. `brand-check` and
  `brand-logo-check` were retired with written justification
  (`docs/codebase-standards.md` §3): brand assets are non-core and stay out
  of the tree by operator direction, so their comparison inputs are no
  longer tracked. The logo generator remains
  (`static/examples/framegraph_logo.py`, now writing to `_tmp/brand/`).
- **Golden determinism fix:** golden renders now pin
  `FRAMEGRAPH_MATH_SVG=fallback` (scoped, restored) so lock hashes no longer
  depend on whether the optional node + `viewer/node_modules` MathJax
  toolchain resolves on the machine running the gate.
- mkdocs strict build made meaningful again: repo-file deep links from site
  pages are validated by `docs-linkcheck` (every tracked Markdown file), so
  mkdocs' own not-found warning is downgraded to info.
(Refactor completion generated by Claude Fable 5 via Claude Code.)

## 2.3.0 — full improvement pass, batches A–F + integration (2026-07-01)

One coordinated pass over the whole tree, executed as six parallel batches.
(Generated by Claude Fable 5 via Claude Code.) One line per batch:

- **A — MCP tool surface:** error-envelope consistency, capability/font
  discovery, session ergonomics, and richer tool parameters.
- **B — core model:** typed reuse, schema field descriptions, referential
  integrity in the validator, and tighter value types.
- **C — rendering:** paint/gradient fidelity in the SVG backend, metrics and
  per-object render feedback, export-lane work.
- **D — SDK authoring:** flow/story builders, icon/bullet_list/dimension
  builders, masters/targets/spans ergonomics, target-adjustment validation.
- **E — docs/manifest/hygiene:** generated capability manifest
  (`docs/capability-manifest.json`, ADR-0002 tracking) + error-code reference +
  examples cookbook, `AGENTS.md`, root `conftest.py`, README/CHANGELOG/nav
  refresh, brand-logo regeneration.
- **F — vision/region toolkit:** region-analysis consolidation from root
  scripts into the package, vectorizer routing, SVG round-trip coverage.

## 2.2.0 — MCP measurement layer, coach, region toolkit, Docker runtime (2026-06-25 → 2026-07-01)

Additive `framegraph/mcp/`, `framegraph/vision/`, `framegraph/coach/`, SDK, and
runtime changes; no model or schema change. Retro-documents the feature commits
between 2026-06-25 and 2026-07-01 that previously had no CHANGELOG entry.
(Entry generated by Claude Fable 5 via Claude Code.)

**Coordinate-aware measurement layer (raster → precise vectors), the headline:**
- New MCP tools `measure_image` (grid + rulers + coordinate system + regions +
  landmarks + zoom crops), `mark_points`, `overlay_images`, `workspace` (a
  stateful pin board: pin/nudge/move/snap/transform/pan/zoom/checkpoint+revert,
  persisted per session as `workspace.json`), `construct_vectors`,
  `score_reconstruction` (numeric edge-match convergence: `on_edge_frac` /
  `mean_dist`), and `map_coordinates` (homography / 2D↔3D / warp rectification)
  — commits `091c64b`, `9528faa`, `7e1e8f8`, `77b4a0b`, `a8e04b0`.
- `vectorize_image` auto-trace: `region` (k-means colour → polygons), `outline`
  (edges → polylines), `trace` (potrace Bézier, `d4337b2`), and `layers`
  (AA-aware flat-logo tracer, `9528faa`).
- `compare_images` gains real NCC/RMSE/MAE metrics + zoomed diff panels.

**Image/SVG → draft lane:**
- `propose_from_svg` — ingest an existing SVG (with optional region grade) and
  round-trip it through render (`9f65e8e`, exported at `2e6f6d1`); SVG import
  resolves `url()` gradients and carries `data-*` into `meta` (`792fe17`).

**SDK:**
- Region toolkit: `select_in` / `place_region` / `region_grade` /
  `extract_objects` / `object_bbox` / `gradient_map` (`29f8f71`).

**Coach (`framegraph.coach`):**
- Vector Construction Coach package: style-grammar, layer-order rules,
  silhouette gate (+ MCP flag), SVG ingest/clean, figure-proportion helpers
  (`bc8c3b8`, `a5a39d1`, `991da7e`, `24bde8b`).

**Runtime:**
- Font-rich Docker SDK/MCP runtime image (`Dockerfile` + `docker/`,
  `make docker-*` targets) for font-faithful raster verification (`c25fe38`).

## 2.2.0 — rendering boundary cleanup + MCP render hardening (2026-06-24)

Additive refactor + MCP changes; no model, schema, or core-renderer behaviour change
(golden lock unchanged). (Generated by Claude Opus 4.8 via Claude Code.)

**Rendering boundary (the inverted dependency, tension #1):**
- `normalize_doc` + its legacy-`use`/deck helpers moved verbatim from
  `tooling/render_fixtures.py` to `framegraph/rendering/application/normalize.py`;
  `tooling` re-exports `normalize_doc` for its CLI. With the `Renderer` already relocated
  to `framegraph/rendering/application/renderer.py`, `framegraph/sdk/conform.py` and
  `rendering/infrastructure/latex/document.py` now import from the package, so
  **`framegraph/` no longer imports up into `tooling/`.** `tests/test_package_boundary.py`
  pins it; `make package-check` drops from 4 blockers to 3 (the rest are the deliberate
  virtual-project decisions, §2).

**MCP render hardening:**
- `conform.render_pages_with_stats()` returns page SVGs + the renderer's text-fit
  telemetry; `render_page_svgs()` delegates to it. The MCP render result now carries a
  `text_fit` block and, when text was **clipped** (truncated to its box), an advisory
  `render_warning` — previously that truncation was invisible (`ok:true`, no signal).
- `_render_size_guard` refuses an obviously-oversized document before the in-process
  render thread starts (generous, env-overridable page/object caps), bounding the work
  the un-killable daemon thread can do.
- `FRAMEGRAPH_GUIDE` now names the `figure` import lane and `text_style()`; a new test
  pins that the guide names the SDK's headline capabilities so it can't silently drift.

## 2.2.0 — SDK `text_style()` + package-readiness check (2026-06-24)

Additive SDK and tooling changes; no model, schema, or core-renderer change.
(Generated by Claude Opus 4.8 via Claude Code.)

**SDK ergonomics:**
- New `framegraph.sdk.text_style()` constructor — names the ~12 text-relevant fields
  of the ~100-field `Style` bag under ergonomic kwargs and emits the *canonical* CSS
  field for each (`size`→`font_size`, `align`→`text_align`, `italic`→`font_style`),
  mirroring `stroke()`. Splats onto a text primitive or feeds `define_text_style()` /
  `theme()`. Re-exported from `framegraph.sdk` and documented in `docs/sdk-api.md`.

**Tooling:**
- New `tooling/check_package_readiness.py` + `make package-check` — asserts whether the
  tree is ready to emit (build/publish) a package, split into hard *blockers* (a wheel
  would fail to build or import-break) and advisory *gaps* (the §16 `[Target]` ledger).
  Advisory only — deliberately **not** part of `make check`. Verdict today: **NOT READY**
  (FrameGraph is a virtual project by design, `[tool.uv] package = false`) — 4 blockers,
  including `framegraph/` importing the top-level `tooling` package, which would not ship
  in a `framegraph` wheel.

**Analysis assets:**
- `architecture-map.svg` (companion to `conceptual-analysis.md`) is now *authored through
  the FrameGraph SDK* and rendered by the project's own SVG proxy, replacing the
  hand-written SVG; `examples/architecture_map.py` is the reproducible source.

## 2.2.0 — MCP feedback loop: close the visual-verification gap + hardening

The MCP adapter advertised "rendered artifacts for visual feedback," but a vision
model never actually received a viewable image: SVG was emitted as an `image/svg+xml`
content block (not a vision-decodable media type), PNG rasterization defaulted **off**,
and when it was on but the browser backend was absent it failed **silently**. The loop
was effectively blind. This release closes that gap and hardens the adapter. No model,
schema, or core-renderer change — `framegraph/mcp/` and `framegraph/live/` only.
(Generated by Claude Opus 4.8 via Claude Code.)

**Visual verification (the headline):**
- `mcp_content_blocks` now ships **only raster mimes** (`png`/`jpeg`/`gif`/`webp`) as
  image blocks; SVG stays a resource link / text artifact.
- Render tools default to `raster_png=True`, and `.mcp.json` launches with the
  `vision` + `browser` groups so the advertised surface is functional out of the box.
- When raster is unavailable the result carries an explicit **`render_warning`**
  (naming the missing backend + the `playwright install chromium` fix) instead of a
  silent empty render — the loop tells you it could not be visually verified.

**Correctness & robustness:**
- Rendering is wrapped in a structured guard: a renderer crash returns
  `ok:false` + `error` (validation still reported) rather than a raw traceback, and a
  soft **render timeout** (`FRAMEGRAPH_MCP_RENDER_TIMEOUT`, default 30s) bounds response
  latency on pathological documents.
- `propose_from_image` / `propose_from_document` degrade gracefully when the `vision`
  group is absent (friendly `ok:false`, not `ImportError`), and honor an **opt-in**
  `FRAMEGRAPH_MCP_INPUT_ROOTS` confinement for hardened deployments.
- `max_pages=0` now explicitly means **all pages** (documented), not "none".
- The code-execution subprocess **strips likely-secret env vars** (`*KEY*`, `*TOKEN*`,
  `*SECRET*`, …) unless `FRAMEGRAPH_MCP_KEEP_ENV` is set.
- The `run_sdk_client` fallback that locates a client's output YAML now diffs by
  **content hash**, not mtime, so a fixture merely `touch`-ed by another process is no
  longer mistaken for this run's output.
- The structured JSONL log **rotates** past a size ceiling and **clamps** oversized
  instruction/response strings.

**Ergonomics:** new `list_sessions` / `cleanup_sessions` tools to enumerate and prune
per-session scratch directories (cleanup is a no-op without an explicit selector).

**Verification:** `tests/test_mcp_server.py` gains coverage for SVG-never-an-image-block,
PNG-is, `render_warning` on missing backend, structured render-failure, `max_pages=0`,
env scrubbing, content-hash fallback, log truncation, opt-in input confinement,
missing-vision-group degradation, and session list/cleanup.

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

**Verification (asserted by `tests/test_head.py`, 13/13 green):** all **eight
authoritative fixtures validate at 2.2.0** — directly for those without legacy strokes
(`ieee`, `neutron-stars`, `spectral-methods`, `mckinsey-7s`), and after the codemod for
those that carry legacy inline strokes (`amazon-proxy`, `chroma-styling-showcase`,
`wireframing-guide`, `docusign-deck-v2` — **544 strokes migrated**). The schema is
generated-in-sync, and the P3 inline-geometry `stroke` is still rejected.

**Grammar ⇄ models is now gated.** A new `grammar-check` gate
(`tooling/check_grammar_sync.py`, wired into `make check` and CI) introspects the models
and diffs the EBNF, failing on **core-profile** drift — a mismatched object/flow `type`
discriminator or a divergent enum. The out-of-profile superset (charts, the UML zoo,
connectors) is reported as a non-blocking warning (`--strict` demands full parity). It
immediately caught and fixed two real grammar omissions against the models: `Units` was
missing `cm`, and `ImageObject` lacked the `alt`/`actual_text` accessibility fields.

**Two source contradictions adjudicated** (flagged, not hidden): the base core grammar's
`GradientStop` uses `offset` while the authoritative style module uses `position` — the
module wins; and the base grammar still carried `Stroke = string | StrokeStyle` while
base-spec §3.5 says paint-only — already resolved (Stroke = Paint).

### SDK — topology, perspective, fields, lattices & manifolds (additive)

Five solver modules join the Python SDK, each lowering to a single core-model `group`
(so the geometric audit, which does not recurse into groups, stays silent) and each
fully deterministic:

- **`framegraph.sdk.topology`** — `Graph` node-link networks with `circular_layout`,
  `radial_layout`, `layered_layout` (DAG), `grid_layout`, and a seeded
  `spring_layout` (Fruchterman–Reingold). `render()` emits fitted edges, arrowheads
  and labels.
- **`framegraph.sdk.geometry.Camera`** — a `look_at` + field-of-view perspective camera
  composing a view/projection `Mat4` (plus `Mat4.look_at`/`perspective_fov`/`rotate_*`
  and `Camera.orbit`). `Scene3D.render()` now accepts a `Camera` and sorts faces by
  perspective-divided depth.
- **`framegraph.sdk.draw.Material` + Scene3D lighting** — translucent material/style
  fields (`opacity`, blend mode, filters) stay model-native, while optional
  `shading="lambert"` or `"gouraud"` bakes pure-Python light intensity into each
  face's emitted 2D fill.
- **`framegraph.sdk.fields`** — `VectorField` (arrow grids) and `ScalarField`
  (`heatmap` + marching-squares `contours`).
- **`framegraph.sdk.lattices`** — `lattice(kind, …)` for 2D (square/triangular/
  honeycomb) and 3D (cubic/bcc/fcc) crystals with nearest-neighbour bonds, rendered
  through the topology engine.
- **`framegraph.sdk.manifold`** — perspective-ready parametric `Scene3D` surfaces:
  `sphere`, `torus`, `mobius`, `klein_bottle`, `saddle`, and the `wave` interference
  heightfield.
- **`tooling/render_chromium.py`** — optional Headless-Chromium raster path: reuse the
  SVG proxy output, then let browser-native rendering produce PNGs for CSS filters,
  blend/backdrop modes, masks and SVG filter fidelity (`uv sync --group browser`;
  `uv run playwright install chromium`).
- **Filter shader-lite primitives** — typed `FilterFn` now covers SVG procedural and
  lighting primitives (`turbulence`, `displacement_map`, `diffuse_lighting`,
  `specular_lighting`) with a new `filter-lighting.fg.yaml` fixture rendered by the
  Chromium path.

Two demo fixtures cover the surface: `topology-perspective.fg.yaml` (six layout/camera
panels) and `fields-lattices-manifolds.fg.yaml` (eight field/lattice/manifold panels),
both at 0 errors / 0 warnings and passing `--check-overflow`. The generated SDK API and
guide docs (`tooling/gen_docs.py`) now cover all five modules.

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
