# FrameForge v2

**FrameForge v2** (`2.6.0`) keeps its documents, grammar, schema, prose, and
Python code in sync — the Pydantic models are the source of truth and everything
else is generated from or checked against them.

FrameForge aims to be an **agent-native visual-authoring substrate** — one
structured, programmable foundation (SDK + MCP) for producing professional visual
assets across documents, decks, diagrams, books, and letters today, extending
toward UIs, vector graphics, logos, and design systems. See [`PURPOSE.md`](PURPOSE.md)
for the full why and scope.

> **Status:** FrameForge v2 is a **proposed,
> not-yet-conformantly-implemented** system. The prose and grammar are design targets to
> verify. The parts you can actually *run* — the models, the generated schema, the
> validator, and the codemod — are the parts to trust.

## Layout

```
src/frameforge/               ← the Python package (strictly downstream of the models — ADR-0002):
  rendering/                  ← renderer (DDD split): domain + application (the Renderer) + infrastructure.
  sdk/                        ← authoring SDK: builders/geometry/paint/widgets that lower into the models.
  mcp/                        ← MCP server: author→render loop + the coordinate/measurement tool layer.
  vision/                     ← raster→vector lane: measure/compare/vectorize/propose (optional deps).
  coach/                      ← Vector Construction Coach: style-grammar, layer order, silhouette gate.
  live/                       ← local web UI for live MCP feedback sessions (`make live`).
src/frameforge/model.py     ← SOURCE OF TRUTH (Pydantic v2). Core conformance profile + all patches.
docs/schema/
  frameforge-v2.schema.json   ← GENERATED from the models (88 $defs). Do not hand-edit.
  build_schema.py             ← regenerates the schema; `--check` fails if it drifts.
docs/grammar/
  frameforge-v2.ebnf          ← the consolidated CORE grammar (base + P1–P4); styling deferred to the module.
  frameforge-v2-style.ebnf    ← the AUTHORITATIVE CSS style module (adopted verbatim at 2.2.0).
docs/spec/frameforge-v2-spec.md ← the normative prose (folds P1–P4 + the style module + cascade + corrections).
static/examples/              ← runnable SDK clients — indexed in docs/examples.md (GENERATED).
  frameforge_logo.py          ← the BRAND LOGO source of truth → generates the (out-of-tree) logo masters.
  frameforge_seed_deck.py     ← the canonical seed pitch deck (imports the mark + wordmark from above).
tooling/
  validate.py                 ← structural (models) + static/geometric rules the schema can't express.
  codemod.py                  ← migrates a document to HEAD (stroke split, size→sizing, gradient, aliases).
  render_fixtures.py          ← SVG render CLI driver (re-exports the Renderer; `--check-overflow` text-fit gate).
  render_chromium.py          ← optional Headless-Chromium SVG→PNG raster renderer (CSS-fidelity path).
  render_fg_doc.py            ← the matplotlib PROXY renderer, patched to HEAD (sanity check only).
  pdf_to_frameforge_yml.py    ← optional PyMuPDF PDF → fixed-layout FrameForge YAML extractor.
  (HTML export moved into the package → `ff-render --to html`; the DocumentRenderer
   port at src/frameforge/rendering/infrastructure/backends/html.py — contract-tested.)
  gen_status.py               ← GENERATES docs/FIXTURE-STATUS.md from the validator (`--check` gates drift).
  gen_docs.py                 ← GENERATES the docs-site pages (reference/gallery/spec/grammar plus SDK docs).
  gen_capability_manifest.py  ← GENERATES docs/capability-manifest.json (core/SDK/MCP status per capability).
  gen_examples_index.py       ← GENERATES docs/examples.md (the examples cookbook index).
  check_grammar_sync.py       ← GATES grammar ⇄ models drift (core profile); `--strict` for full parity.
  check_accessibility.py      ← GATES page reading_order integrity; warns on missing image alt (a11y).
  render_golden.py            ← GATES b1/ oracle SVG output against a pinned hash lock (golden).
tests/fixtures/               ← the fixture corpus (declared versions span 2.0.0–2.4.x; top-level YAML gated by `make validate`, the b1/ oracle by test_head.py).
  b1/                         ← the 8 AUTHORITATIVE fixtures (the oracle the tests assert against).
conftest.py                   ← shared pytest bootstrap (sys.path + the frameforge shadow-module rule).
tests/
  test_head.py                ← assertions: authoritative fixtures validate, schema in sync, style surface, P3.
  test_docs_in_sync.py        ← doc drift gate: numbers, Layout paths, generated-doc policy, fixture status.
  test_doc_examples.py        ← validates every complete FrameForge example shown in the prose.
docs/ + mkdocs.yml            ← the MkDocs site: `index.md` is hand-written, `sdk*.md` are committed generated snapshots, transient generated pages are ignored, and non-site sources (schema/spec/grammar, plus seed/ and decisions/) are `exclude_docs`.
docs/capability-manifest.json ← GENERATED machine-readable capability status {core, sdk, mcp} (ADR-0002).
docs/error-codes.md           ← every validator finding code + SDK rule_id: meaning and fix (sync-tested).
docs/output-space.md          ← what FrameForge can generate: the verified-today backends + the conceptual output space (anchor drift-gated by tests/test_output_space_doc.py).
docs/BRAND.md                 ← the brand guideline (proposal); §3 governs the generated logo.
docs/FIXTURE-STATUS.md        ← GENERATED validator status for the delivered fixtures (gen_status.py).
docs/codebase-standards.md    ← the elevated engineering bar, status-tagged (Enforced / Adopted / Target).
AGENTS.md                     ← programmatic CLI/tooling reference (make targets, tooling flags, workflows).
Dockerfile + docker/          ← the font-rich SDK/MCP runtime image (`make docker-build`).
CHANGELOG.md                  ← version, the breaking change + migration, conformance classes, rec. resolution.
pyproject.toml + uv.lock      ← the real hatchling package since 2.5.0 (`[tool.uv] package = true`): `uv sync` installs it editable with the `ff-render`/`fg-font` console scripts; dep groups dev/render/browser/pdf/pdfout/metrics/mcp/vision.
Makefile + .github/workflows/ ← `make check` = the local gate; CI mirrors it (+ a docs build/deploy job).
```

## The sync guarantee (what "in sync" means here, concretely)

1. **Schema ⇄ models.** `docs/schema/frameforge-v2.schema.json` is produced by
   `Document.model_json_schema()`. `build_schema.py --check` returns non-zero if the
   committed file differs from a fresh build — so they cannot silently drift.
2. **Validator ⇄ models.** `validate.py` validates against the same `Document` model,
   then layers the §3.3/§3.6/§9.6 rules.
3. **Codemod ⇄ validator.** The codemod's migrations are exactly the breaking/renamed
   forms the validator rejects; running it makes a legacy document pass.
4. **Grammar ⇄ models.** The EBNF is a *view* of the models (the source). This is now
   enforced, not trusted: `tooling/check_grammar_sync.py` (the `grammar-check` gate)
   introspects the models and diffs the EBNF, failing CI on **core-profile** drift — a
   mismatched object/flow `type` discriminator or a divergent enum. Out-of-profile
   grammar (charts, the UML zoo, connectors) is reported as a non-blocking warning;
   `--strict` demands full parity.

## Run it

The project is managed with [uv](https://docs.astral.sh/uv/). `uv sync` once
creates `.venv` with the runtime deps and the `dev` group (see
`pyproject.toml`), and installs the `frameforge` package itself — putting the
`ff-render` and `fg-font` console scripts on PATH; prefix commands with `uv run`.

```bash
uv sync                                    # create/populate .venv

# schema is generated and in sync
uv run python docs/schema/build_schema.py --check

# validate the delivered tracked fixtures — 39/39 zero errors in docs/FIXTURE-STATUS.md
make validate

# migrate a legacy v2 document to HEAD
uv run python tooling/codemod.py path/to/legacy.fg.json --in-place --bump

# the HEAD assertions (13/13 green)
uv run python tests/test_head.py
# or the full pytest suite (also run by `make check`)
uv run pytest

# SVG proxy renderer (dependency-free core) -> out/render/index.html
uv run python tooling/render_fixtures.py --all

# optional browser-fidelity raster renderer (install Playwright + Chromium first)
uv sync --group browser
uv run playwright install chromium
uv run python tooling/render_chromium.py tests/fixtures/effects.fg.yaml --out out/chromium

# optional PDF text/layout extractor (install PyMuPDF first)
uv sync --group pdf
uv run python tooling/pdf_to_frameforge_yml.py input.pdf output.frameforge.yml

# optional MCP server for AI feedback loops:
# Python SDK code -> generated FrameForge YAML -> validation + rendered SVG/PNG,
# plus the coordinate-aware measurement layer (see "Subsystems" below)
uv sync --group mcp
uv run --group mcp python -m frameforge.mcp
# or: make mcp

# optional local web UI over the same MCP feedback functions
make live                                  # http://127.0.0.1:8789
# choose a port when needed: make live LIVE_PORT=8790

# the whole local gate — every gate on the Makefile `check` target
make check

# build & browse the generated documentation site (Material theme, live reload)
make docs-serve
```

The matplotlib proxy renderer (`tooling/render_fg_doc.py`) needs the extra
`render` dependency group:

```bash
uv sync --group render                     # adds matplotlib + pillow
```

## Subsystems beyond the core

- **MCP measurement layer** (`frameforge/mcp/` + `frameforge/vision/`). Besides
  the author→render loop, the MCP server exposes a coordinate-aware
  raster→vector reconstruction toolset: `measure_image` (grids/rulers/regions/
  landmarks/zoom crops), `mark_points`, `overlay_images`, a stateful `workspace`
  pin board, `construct_vectors`, `vectorize_image` (region/outline/potrace/
  layers tracing), `score_reconstruction` (numeric edge-match convergence), and
  `map_coordinates` (homography/warp). The live tool registry is enumerated in
  [docs/capability-manifest.json](docs/capability-manifest.json); it needs the
  `vision` dependency group. Every runtime knob (`FRAMEFORGE_*` env vars —
  session/publish roots, transport budgets, render ceilings, Chromium flags,
  the VLM lane) is documented with its real default in the gated table at
  [src/frameforge/mcp/README.md](src/frameforge/mcp/README.md#configuration-environment-variables);
  container-only knobs live in [docker/README.md](docker/README.md).
- **Vector Construction Coach** (`src/frameforge/coach/`). A staged construction
  loop over the SDK — style-grammar checks, layer-order rules, a silhouette
  gate, SVG ingest/cleaning, and figure-proportion helpers. It coaches
  *construction* discipline; it is not a curve-drawing engine. Demos:
  `static/examples/coach_demo.py` and the other `coach_*` examples.
- **Docker runtime** (`Dockerfile` + `docker/`). The font-rich canonical
  SDK/MCP runtime (thousands of font families baked in) for font-faithful
  raster verification: `make docker-build` / `docker-mcp` / `docker-shell` /
  `docker-fonts`; client wiring in `docker/mcp.docker.json`.
- **Live UI** (`frameforge/live/`). A local web view over the same MCP feedback
  functions for humans watching/driving a session: `make live`
  (`http://127.0.0.1:8789`, port via `LIVE_PORT`).
- **Font determinism toolchain** (`src/frameforge/fontpack.py` +
  `tooling/render_chromium.py`; [ADR-0004](docs/adr-0004-single-engine-layout.md)).
  `fg-font` — `--list` resolvable families, `--check DOC` (non-zero exit if a
  content font would substitute), `--pack DOC --out P.fp` (portable pack of the
  exact TTFs + sha256 manifest; `--fetch` provisions missing families from the
  open Google Fonts corpus so packs build on thin hosts), `--install P.fp`
  (scoped fontconfig) — and `render_chromium.py --font-pack P.fp`, which scopes
  fontconfig to the pack before Chromium launches so measure == render on any
  host. Installed as a console script since 2.5.0: `uv run fg-font …` (or the
  `make font-*` targets; `tooling/fg_font.py` remains as a direct-run shim).
  Silent font substitution is banned: layout emits a `font_substitution`
  warning to diagnostics *and* stderr whenever a requested face is missing.

Programmatic entry points for all of the above — every make target and tooling
CLI with flags — are catalogued in [AGENTS.md](AGENTS.md); the examples
cookbook is generated at [docs/examples.md](docs/examples.md).

## How the pre-HEAD (2.0.x) bundle was folded in (2.1.0–2.2.0)

At 2.2.0 the **authoritative CSS style module** is adopted verbatim (`Style` is the
~80-property bag; `TextStyle`/`StrokeStyle` are projections of it; `fill`/`stroke` are
`Paint`; gradient stops use `position`; `class` + `css` escape). 2.1.0 folded Patches
1–4, made the **stroke single-form breaking**, renamed `size → sizing`, generated the
schema from Pydantic, and added the validator + codemod. Full detail in `CHANGELOG.md`.

## Provenance (how the earlier documents relate)

These predecessor documents are **not included in this HEAD bundle** — their content is
folded into the artifacts above; they are listed only for historical context:

- `FrameForge-2.0.0-Specification.md` — the spec reverse-engineered from the renderer,
  superseded by `docs/spec/frameforge-v2-spec.md`.
- `FrameForge-2.0.0-Specification-Complement.md` — the reconciliation that produced the
  recommendations this release implements; its §8 actions are resolved in `CHANGELOG.md`.
- The four standalone patch documents (P1–P4) are folded into the grammar, the spec, and
  the models here; they remain useful as rationale.

## Honest limits (don't overclaim)

- This is a **proposed** format. No renderer is conformant; the proxy renderer uses
  DejaVu stand-in fonts and is a sanity check, not a fidelity guarantee.
- The grammar is consolidated and paren-balanced and is a **view** of the models — now
  kept honest by the `grammar-check` gate (`check_grammar_sync.py`) for the core profile;
  the models remain the authority if the two ever disagree.
- Font pinning enables deterministic *layout* only up to a stated rounding **tolerance**
  (a defined shaping model is also required) — not pixel-exact identity (§9.6).
- The current delivered top-level fixture status is generated in `FIXTURE-STATUS.md`;
  at this snapshot **39/39** have zero errors. Advisory warnings, when present, are
  recorded there instead of summarized by hand here.
- What FrameForge can — and deliberately will not — generate is mapped in
  [docs/output-space.md](docs/output-space.md): the backends wired today (whose
  entry points are drift-gated) plus the conceptual output space the IR admits.
- How FrameForge presents itself — name, voice, colour, type, and the logo — is the
  [docs/BRAND.md](docs/BRAND.md) guideline (a proposal). The logo is *generated*: the
  mark/wordmark source of truth is
  [static/examples/frameforge_logo.py](static/examples/frameforge_logo.py), which writes
  the masters out of tree (`_tmp/brand/`) — brand assets are non-core and are not
  tracked in this repository.
