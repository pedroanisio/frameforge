# FrameGraph v2 — HEAD release

A single, internally-consistent cut of **FrameGraph v2** (`2.3.0`) in which the
documents, grammar, schema, prose, and Python code are kept in sync — the Pydantic
models are the source of truth and everything else is generated from or checked
against them.

> **Status (unchanged from the project's own stance):** FrameGraph v2 is a **proposed,
> not-yet-conformantly-implemented** format. The prose and grammar are design targets to
> verify. The parts you can actually *run* — the models, the generated schema, the
> validator, and the codemod — are the parts to trust.

## Layout

```
src/framegraph/               ← the Python package (strictly downstream of the models — ADR-0002):
  rendering/                  ← renderer (DDD split): domain + application (the Renderer) + infrastructure.
  sdk/                        ← authoring SDK: builders/geometry/paint/widgets that lower into the models.
  mcp/                        ← MCP server: author→render loop + the coordinate/measurement tool layer.
  vision/                     ← raster→vector lane: measure/compare/vectorize/propose (optional deps).
  coach/                      ← Vector Construction Coach: style-grammar, layer order, silhouette gate.
  live/                       ← local web UI for live MCP feedback sessions (`make live`).
docs/models/framegraph.py     ← SOURCE OF TRUTH (Pydantic v2). Core conformance profile + all patches.
docs/schema/
  framegraph-v2.schema.json   ← GENERATED from the models (82 $defs). Do not hand-edit.
  build_schema.py             ← regenerates the schema; `--check` fails if it drifts.
docs/grammar/
  framegraph-v2.ebnf          ← the consolidated CORE grammar (base + P1–P4); styling deferred to the module.
  framegraph-v2-style.ebnf    ← the AUTHORITATIVE CSS style module (adopted verbatim at 2.2.0).
docs/spec/framegraph-v2-spec.md ← the normative prose (folds P1–P4 + the style module + cascade + corrections).
static/examples/              ← runnable SDK clients — indexed in docs/examples.md (GENERATED).
  framegraph_logo.py          ← the BRAND LOGO source of truth → generates the (out-of-tree) logo masters.
  framegraph_seed_deck.py     ← the canonical seed pitch deck (imports the mark + wordmark from above).
tooling/
  validate.py                 ← structural (models) + static/geometric rules the schema can't express.
  codemod.py                  ← migrates a document to HEAD (stroke split, size→sizing, gradient, aliases).
  render_fixtures.py          ← SVG render CLI driver (re-exports the Renderer; `--check-overflow` text-fit gate).
  render_chromium.py          ← optional Headless-Chromium SVG→PNG raster renderer (CSS-fidelity path).
  render_fg_doc.py            ← the matplotlib PROXY renderer, patched to HEAD (sanity check only).
  pdf_to_framegraph_yml.py    ← optional PyMuPDF PDF → fixed-layout FrameGraph YAML extractor.
  framegraph_to_html.py       ← FrameGraph → semantic HTML exporter (contract-tested).
  gen_status.py               ← GENERATES docs/FIXTURE-STATUS.md from the validator (`--check` gates drift).
  gen_docs.py                 ← GENERATES the docs-site pages (reference/gallery/spec/grammar plus SDK docs).
  gen_capability_manifest.py  ← GENERATES docs/capability-manifest.json (core/SDK/MCP status per capability).
  gen_examples_index.py       ← GENERATES docs/examples.md (the examples cookbook index).
  check_grammar_sync.py       ← GATES grammar ⇄ models drift (core profile); `--strict` for full parity.
  check_accessibility.py      ← GATES page reading_order integrity; warns on missing image alt (a11y).
  render_golden.py            ← GATES b1/ oracle SVG output against a pinned hash lock (golden).
tests/fixtures/               ← the original fixtures, migrated to 2.2.0.
  b1/                         ← the 8 AUTHORITATIVE fixtures (the oracle the tests assert against).
conftest.py                   ← shared pytest bootstrap (sys.path + the framegraph shadow-module rule).
tests/
  test_head.py                ← assertions: authoritative fixtures validate, schema in sync, style surface, P3.
  test_docs_in_sync.py        ← doc drift gate: numbers, Layout paths, generated-doc policy, fixture status.
  test_doc_examples.py        ← validates every complete FrameGraph example shown in the prose.
docs/ + mkdocs.yml            ← the MkDocs site: `index.md` is hand-written, `sdk*.md` are committed generated snapshots, transient generated pages are ignored, and non-site sources (models/schema/spec/grammar) are `exclude_docs`.
docs/capability-manifest.json ← GENERATED machine-readable capability status {core, sdk, mcp} (ADR-0002).
docs/error-codes.md           ← every validator finding code + SDK rule_id: meaning and fix (sync-tested).
docs/output-space.md          ← what FrameGraph can generate: the verified-today backends + the conceptual output space (anchor drift-gated by tests/test_output_space_doc.py).
docs/BRAND.md                 ← the brand guideline (proposal); §3 governs the generated logo.
docs/FIXTURE-STATUS.md        ← GENERATED validator status for the delivered fixtures (gen_status.py).
docs/codebase-standards.md    ← the elevated engineering bar, status-tagged (Enforced / Adopted / Target).
AGENTS.md                     ← programmatic CLI/tooling reference (make targets, tooling flags, workflows).
Dockerfile + docker/          ← the font-rich SDK/MCP runtime image (`make docker-build`).
CHANGELOG.md                  ← version, the breaking change + migration, conformance classes, rec. resolution.
pyproject.toml + uv.lock      ← the uv virtual project (deps; dev/render/browser/pdf groups; `package = false`).
Makefile + .github/workflows/ ← `make check` = the local gate; CI mirrors it (+ a docs build/deploy job).
```

## The sync guarantee (what "in sync" means here, concretely)

1. **Schema ⇄ models.** `docs/schema/framegraph-v2.schema.json` is produced by
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

The project is managed with [uv](https://docs.astral.sh/uv/). `uv sync` once to
create `.venv` with the runtime deps (`pydantic>=2`, `pyyaml`) plus the `dev`
group (`pytest`); prefix commands with `uv run`.

```bash
uv sync                                    # create/populate .venv

# schema is generated and in sync
uv run python docs/schema/build_schema.py --check

# validate the delivered tracked fixtures — 30/30 zero errors in docs/FIXTURE-STATUS.md
make validate

# migrate a legacy v2 document to HEAD
uv run python tooling/codemod.py path/to/legacy.fg.json --in-place --bump

# run the assertions (13/13 green), either runner
uv run python tests/test_head.py
uv run pytest

# SVG proxy renderer (dependency-free core) -> out/render/index.html
uv run python tooling/render_fixtures.py --all

# optional browser-fidelity raster renderer (install Playwright + Chromium first)
uv sync --group browser
uv run playwright install chromium
uv run python tooling/render_chromium.py tests/fixtures/filters.fg.yaml --out out/chromium

# optional PDF text/layout extractor (install PyMuPDF first)
uv sync --group pdf
uv run python tooling/pdf_to_framegraph_yml.py input.pdf output.framegraph.yml

# optional MCP server for AI feedback loops:
# Python SDK code -> generated FrameGraph YAML -> validation + rendered SVG/PNG,
# plus the coordinate-aware measurement layer (see "Subsystems" below)
uv sync --group mcp
uv run --group mcp python -m framegraph.mcp
# or: make mcp

# optional local web UI over the same MCP feedback functions
make live                                  # http://127.0.0.1:8789
# choose a port when needed: make live LIVE_PORT=8790

# the whole local gate (schema · grammar · a11y · tests · validate · overflow · golden · fixture-status · docs nav)
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

- **MCP measurement layer** (`framegraph/mcp/` + `framegraph/vision/`). Besides
  the author→render loop, the MCP server exposes a coordinate-aware
  raster→vector reconstruction toolset: `measure_image` (grids/rulers/regions/
  landmarks/zoom crops), `mark_points`, `overlay_images`, a stateful `workspace`
  pin board, `construct_vectors`, `vectorize_image` (region/outline/potrace/
  layers tracing), `score_reconstruction` (numeric edge-match convergence), and
  `map_coordinates` (homography/warp). The live tool registry is enumerated in
  [docs/capability-manifest.json](docs/capability-manifest.json); it needs the
  `vision` dependency group.
- **Vector Construction Coach** (`src/framegraph/coach/`). A staged construction
  loop over the SDK — style-grammar checks, layer-order rules, a silhouette
  gate, SVG ingest/cleaning, and figure-proportion helpers. It coaches
  *construction* discipline; it is not a curve-drawing engine. Demos:
  `static/examples/coach_demo.py` and the other `coach_*` examples.
- **Docker runtime** (`Dockerfile` + `docker/`). The font-rich canonical
  SDK/MCP runtime (thousands of font families baked in) for font-faithful
  raster verification: `make docker-build` / `docker-mcp` / `docker-shell` /
  `docker-fonts`; client wiring in `docker/mcp.docker.json`.
- **Live UI** (`framegraph/live/`). A local web view over the same MCP feedback
  functions for humans watching/driving a session: `make live`
  (`http://127.0.0.1:8789`, port via `LIVE_PORT`).

Programmatic entry points for all of the above — every make target and tooling
CLI with flags — are catalogued in [AGENTS.md](AGENTS.md); the examples
cookbook is generated at [docs/examples.md](docs/examples.md).

## What changed vs the pre-HEAD bundle (one-line summary)

At 2.2.0 the **authoritative CSS style module** is adopted verbatim (`Style` is the
~80-property bag; `TextStyle`/`StrokeStyle` are projections of it; `fill`/`stroke` are
`Paint`; gradient stops use `position`; `class` + `css` escape). 2.1.0 folded Patches
1–4, made the **stroke single-form breaking**, renamed `size → sizing`, generated the
schema from Pydantic, and added the validator + codemod. Full detail in `CHANGELOG.md`.

## Provenance (how the earlier documents relate)

These predecessor documents are **not included in this HEAD bundle** — their content is
folded into the artifacts above; they are listed only for historical context:

- `FrameGraph-2.0.0-Specification.md` — the spec reverse-engineered from the renderer,
  superseded by `docs/spec/framegraph-v2-spec.md`.
- `FrameGraph-2.0.0-Specification-Complement.md` — the reconciliation that produced the
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
  at this snapshot **30/30** have zero errors. Advisory warnings, when present, are
  recorded there instead of summarized by hand here.
- What FrameGraph can — and deliberately will not — generate is mapped in
  [docs/output-space.md](docs/output-space.md): the backends wired today (whose
  entry points are drift-gated) plus the conceptual output space the IR admits.
- How FrameGraph presents itself — name, voice, colour, type, and the logo — is the
  [docs/BRAND.md](docs/BRAND.md) guideline (a proposal). The logo is *generated*: the
  mark/wordmark source of truth is
  [static/examples/framegraph_logo.py](static/examples/framegraph_logo.py), which writes
  the masters out of tree (`_tmp/brand/`) — brand assets are non-core and are not
  tracked in this repository.
