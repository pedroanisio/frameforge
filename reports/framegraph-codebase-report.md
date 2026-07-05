---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude (Anthropic) via Claude Code"
  date: "2026-07-05"
---

# FrameGraph v2 — Codebase Report

**Version at time of writing:** `2.4.1` (HEAD) · **Schema:** 85 `$defs` ·
**Status:** PROPOSED / partially-implemented format (the project's own stance).

This report describes the repository as it stands after syncing `origin/main`.
It is an architectural map produced by reading the live tree — the source of
truth is always the code, tests, and generated artifacts, not this summary.

---

## 1. What FrameGraph is

FrameGraph v2 is a document/graphics DSL for decks, diagrams, books, letters,
and fixed/reflowable visual documents. Its organizing conviction (see
`PURPOSE.md`) is **truth before appearance**: a document must be structured,
inspectable, checkable, and reproducible — the rendered picture is not the only
source of truth.

The **Pydantic model at `docs/models/framegraph.py` is the single source of
truth.** Schema, grammar, spec prose, validator, SDK, and most site pages are
generated from — or gated against — that model. This "everything downstream of
the models" rule is formalized in `docs/adr-0002-sdk-lags-core-delivery.md`.

---

## 2. Repository topology

```
docs/models/framegraph.py     SOURCE OF TRUTH (Pydantic v2)
docs/schema/                  GENERATED JSON schema (+ build_schema.py, --check gate)
docs/grammar/                 EBNF views of the models (core + CSS style module)
docs/spec/                    normative prose (gated against the models)
src/framegraph/               the Python package (strictly downstream of the models)
  ├── sdk/          authoring: builders + geometry/paint/widgets that lower into the models
  ├── rendering/    forward renderer (DDD split): doc → layout → paint → output
  ├── vision/       inverse lane: pixels → UNVERIFIED FrameGraph drafts
  ├── coach/        Vector Construction Coach: process scaffolding over the SDK
  ├── live/         local web UI for MCP feedback sessions
  ├── mcp/          MCP server: author→render→verify loop
  ├── patterns/     375-pattern slide-layout catalog + fills
  ├── library/      consulting themes, symbol packs, page generators
  ├── cli.py        `framegraph-render` front door (multi-backend)
  └── fontpack.py   `fg-font` — font gate/pack/install (measure-time == render-time)
static/examples/              105 runnable SDK clients (the cookbook), indexed in docs/examples.md
tooling/                      27 scripts: generators, validators/gates, renderers, converters
tests/                        179 test files; the b1/ oracle + golden lock
Dockerfile + docker/          font-rich SDK/MCP/render runtime image
Makefile + .github/workflows/ `make check` = the local gate; CI mirrors it
```

Note: the layered package (`sdk` / `rendering` / `vision` / `coach` / `live`)
follows a hexagonal / DDD style — pure, stdlib-only domain cores with heavy
backends isolated behind ports and imported lazily.

---

## 3. The sync guarantee (why the tree stays honest)

Nearly every gate is a drift check against the models:

- **Schema ⇄ models** — `docs/schema/build_schema.py --check` fails if the
  committed schema differs from a fresh `Document.model_json_schema()`.
- **Validator ⇄ models** — `tooling/validate.py` validates against the same
  `Document`, then layers static/geometric rules the schema can't express.
- **Codemod ⇄ validator** — `tooling/codemod.py` migrations are exactly the
  forms the validator rejects (incl. `--from-v01`).
- **Grammar ⇄ models** — `tooling/check_grammar_sync.py` diffs the EBNF against
  the models; `--strict` demands full parity.
- **Spec ⇄ models** — `tooling/check_spec_sync.py` asserts the prose still names
  every model type / flow / inline discriminator.
- **Docs / examples / capability manifest** — all generated and drift-gated.
- **Viewer ⇄ models** — a JS twin (`viewer/dev/schema-contract.mjs`) keeps the
  standalone viewer's type registry reconciled with the model discriminators
  (a BLOCKING CI job).

---

## 4. The SDK (`src/framegraph/sdk/`, 32 modules, ~12k LoC)

A hand-written Python binding **over** the model. Its doctrine (§A.0, repeated in
module docstrings): **the SDK computes; the document receives plain objects.**
Every helper lowers to grammar-native primitives (`path`, `polyline`, `group`,
`table`, …) — none extend the schema.

**Authoring & document structure**
- `author` — `DocumentBuilder` / `PageBuilder` / `MasterBuilder` / `StackBuilder`
  / `Handle` (typed references).
- `flow` — `FlowBuilder`: typed helpers for every Flowable (headings, lists,
  tables, code, math, TOC, bibliography, breaks).
- `book` — `BookBuilder` / `ChapterBuilder`: numbered chapters → one `mode: flow`
  document with computed numbering.
- `markdown` — `from_markdown` → validated flow page.
- `figure` — import live docs / PDF / EPUB images as placed, provenance-tagged
  figures.

**Model lifecycle / IO / validation**
- `model` (access shim), `io` (`parse` / `serialize` / `svg_to_objects`),
  `expand` (deterministic reuse/symbol/component resolution + asset/font pinning),
  `humanize` (seeded, bounded imperfection pass), `validate`
  (`validate_static_rules` → `ValidationReport`), `conform` (golden-render harness).

**Layout & typography**
- `layout` (`row`/`column`/`grid`/`inset` box math), `canon` (Johnston
  typographic canon, modular scale, margins), `metrics` (author-time text
  measurement, kerning; real font advances via fontTools when available).

**Color science**
- `chevreul` — a real color-science module: 12-station wheel, harmonies, WCAG
  contrast, tone scales, greyscale simulation, `color_guide`.
- `recolor` — one-call whole-document palette remap (tokens, literals, gradient
  stops).
- `paint` — gradients, patterns/hatch/dots, strokes, text styles, shadow/glow/
  neon effects.

**Geometry / math kernels**
- `geometry` — `Vec2/Vec3/Mat3/Mat4/Path/CubicBezier/Camera/ViewingPipeline`,
  hulls, intersections, `point_in_polygon`, OBB/AABB, surface curvature.
- `planar` (advanced) — a self-contained polygon-clipping kernel: boolean ops
  (`union`/`intersect`/`subtract`/`divide`), `offset_polygon`, path surgery
  (`split_at`/`cut_along`/`fill_regions`), all in Python → `path` objects.
- `outline` (advanced) — Illustrator-class stroke expansion: `stroke_outline`
  with variable width profiles, caps, a calligraphic pen, and `repeat_along_path`
  pattern brushes.

**Generative / procedural**
- `chart` (`Chart` over a `Frame`: line/bar/scatter/area/pie/donut), `draw`
  (`Frame`, `Scene3D`, function/polar plots, `multiview`), `fields`
  (`VectorField` / `ScalarField` with marching-squares contours), `fractal`
  (deterministic L-systems + turtle), `lattices` (2D/3D crystal lattices),
  `manifold` (parametric surfaces + Bézier/B-spline patches), `topology`
  (node-link graphs with layout + camera projection), `region` (region ops over
  object lists), `macros` (theme/md/cite/sparkline/greeble/lorem…).

**UI widgets**
- `widgets` — a full UI vocabulary (`card`/`kpi`/`badge`/`button`/`field`/
  `toggle`/`tabs`/`table`/…) that each lower to a single `group`.

---

## 5. Rendering (`src/framegraph/rendering/`, ~12.2k LoC)

The forward renderer, in a strict 3-layer DDD split:

- **domain/** — pure, stdlib-only: geometry primitives, the hexagonal ports
  (`RenderContext`, `ScenePainter`, `DocumentRenderer`), and the resolver /
  layout services (`layout_engine`, `flow_layout` — backend-neutral line-breaking
  + Liang hyphenation per `adr-0003`, `table_layout`, `text_fitter`, plus color /
  paint / stroke / effect / text-style / canvas resolvers).
- **application/** — `Renderer` (the doc→output orchestrator, z-order walk) and
  sub-renderers (`TableRenderer`, `UmlRenderer`, `DimensionRenderer`) plus
  `normalize_doc`.
- **infrastructure/** — adapters:
  - `painters/` — `SvgPainter` (primary), `TikzPainter` (per-primitive scene
    painters over the same Renderer).
  - `backends/` — coarse `DocumentRenderer` output ports resolved by the CLI's
    `--to` name: `html`, `pdf_tex`.
  - `latex/` — a first-class LaTeX/TikZ lane (TeX owns pagination / justification
    / hyphenation / math), compiled in-process via `lualatex`/`pdflatex`.
  - rasterization / measurement: `browser` (headless Chromium via Playwright),
    `cairo` (CairoSVG, browser-free PNG), `font_metrics` (fontTools + fontconfig),
    `math_svg` (MathJax via Node, deterministic fallback).

**Output backends:** SVG (primary), TikZ + LaTeX→PDF, HTML, and PNG raster (from
SVG via Chromium or CairoSVG). Everything heavy is optional and degrades
gracefully; the domain core needs only the stdlib.

---

## 6. Vision (`src/framegraph/vision/`, ~6.3k LoC)

The inverse renderer: proposes FrameGraph objects **from pixels**. Its cardinal
rule is explicit (PALS's Law): all output is UNVERIFIED CV/VLM draft and callers
MUST round-trip through the forward validate+render pipeline.

- **domain/** — value objects (`Bbox`, `Observation`, `Proposal`, …), detector /
  source / VLM ports, and the `Proposer` service.
- **application/** — the two public entry points `propose_from_image` /
  `propose_from_document`, `default_detectors()` (color → shape → line → text →
  VLM), and the observation mapper.
- **infrastructure/** — detectors (OpenCV, Tesseract OCR, an OpenAI-compatible
  VLM client), sources (Pillow, PyMuPDF), and the coordinate-reconstruction
  toolkit that backs the MCP tools: `measure`, `regions`, `vectorize`
  (k-means / potrace), `construct`, `matchscore`, `image_compare`,
  `overlay_align`, `edgesnap`, `mapping3d`, `svg_import`, `workspace`.

All heavy backends are lazily imported and gated behind `available()`.

---

## 7. Coach & Live

- **coach/** (~1.4k LoC) — the Vector Construction Coach (POC). It does **not**
  draw; it provides deterministic scaffolding to help a model produce better
  vector art: intent parsing, style-as-grammar (`StyleProfile`), layer-order
  discipline ("no detail before structure"), a silhouette readability gate,
  contour cleanup (RDP simplify / denoise / smooth), and human-figure proportion
  analysis. Imports only `framegraph.sdk` + stdlib (OpenCV lazily in `ingest`).
- **live/** (~0.7k LoC) — a dependency-free local web UI (`http.server`,
  default `127.0.0.1:8789`) that reuses the MCP server in-process so a browser
  can submit a prompt / SDK code / YAML and see validation, generated YAML, and
  page artifacts. No second render path.

---

## 8. MCP server (`src/framegraph/mcp/`, ~6.3k LoC)

A FastMCP server (official MCP Python SDK) that closes the authoring loop:
author with the SDK → validate + render to PNG/SVG → visually QA and reconstruct
against pixels. Entry: `create_server()` in `mcp/server.py`; runnable as
`python -m framegraph.mcp`. The tool wrappers live in `server.py` (~1.6k lines);
the logic sits in `usecases.py` (~1.7k) and `pipeline.py` (~0.6k).

Tools, by category:
- **Author → render:** `run_sdk_code`, `run_sdk_client`, `render_framegraph_yaml`,
  `list/read/write_sdk_client`.
- **Image → draft (unverified):** `propose_from_image` / `_document` / `_svg`.
- **Visual QA:** `compare_images` (NCC/RMSE/MAE + optional phase-align).
- **Coordinate-aware reconstruction:** `measure_image`, `mark_points`,
  `overlay_images`, `workspace` (a stateful pin-board "AI mouse"),
  `construct_vectors`, `score_reconstruction`, `map_coordinates`,
  `vectorize_image`, `detect_regions`.
- **Sessions / meta:** `get_guide`, `describe_capabilities`, `list_fonts`,
  `get_session_resource`, `list/cleanup_sessions`, plus session resources
  (`framegraph://session/{id}/…`) and a guide prompt.

Sandboxed execution (`execution.py` / `security.py`) guards arbitrary SDK code
behind safe-root checks.

---

## 9. Patterns & Library (absorbed content)

- **patterns/** (~0.6k LoC + data) — a fixed catalog of **375 typed slide-layout
  patterns** (one YAML, calibrated 1920×1080 boxes) plus **17 fill sidecars**.
  Public API: `compose(pattern_id, fill, …) -> validated document`, with a
  strict `{role: content}` fill contract (Pydantic-validated).
- **library/** (~0.6k LoC + data) — **7 consulting themes** (bain, bcg, deloitte,
  ey, kpmg, mckinsey, pwc as `defs.tokens` fragments), **4 symbol packs**
  (covers / sections / hex / shared), and data-driven generators
  (`honeycomb_capability_map`, `module_hub_radial`).

Neither touches the document schema; both lower to grammar-native forms.

---

## 10. CLIs

- **`framegraph-render`** (`cli.py`) — one front door dispatching a document to a
  `TARGETS` registry: `svg` (dependency-free, primary), `png` (Chromium), `pdf`
  (CairoSVG), `pdf-tex` (LaTeX/TikZ), `tex` (source only), `html` (legacy).
  `--list` reports each target's optional dependency and current availability.
- **`fg-font`** (`fontpack.py`) — inspect / gate / pack the fonts a document
  needs so measure-time font equals render-time font (`adr-0004`): `--list`,
  `--check`, `--pack` (optionally `--fetch` from the google/fonts corpus),
  `--install`.

---

## 11. Tooling, tests, and gates

**Tooling (27 scripts)** falls into generators (`gen_docs`, `gen_status`,
`gen_examples_index`, `gen_capability_manifest`, `bump_version`, `build_schema`),
validators/gates (`validate`, `check_grammar_sync`, `check_spec_sync`,
`check_accessibility`, `check_disclaimers`, `check_doc_links`, `render_golden`),
renderers (`render_fixtures`, `render_latex`, `render_chromium`, `render_pdf`),
and converters/ingest (`pdf_to_framegraph_yml`, `vectorize_image`, `codemod`),
plus font/corpus utilities.

**`make check` runs 13 gates in order:** `schema-check`, `grammar-check`,
`spec-check`, `a11y-check`, `status-check`, `ruff-check`, `test`, `validate`,
`overflow`, `golden-check`, `docs-check`, `docs-linkcheck`, `disclaimer-check`.
CI mirrors this across Python 3.10/3.11/3.12, adds a strict MkDocs build,
main-only versioned docs deploy (mike), and the blocking viewer-contract job.

**Tests (179 files)** — the largest areas are the LaTeX/TikZ backend (~25),
the SDK (~30: planar, outline, chevreul, book, flow, canon, topology, fields,
markdown, figure, …), rendering/SVG semantics, geometry/3D, vision/MCP (~30),
and the drift-sync gates. The `b1/` oracle set + `tests/golden/oracle.lock.json`
pin renderer output.

---

## 12. Examples cookbook (`static/examples/`, 105 clients)

Regenerated into `docs/examples.md` by `gen_examples_index.py`. The range is
broad: decks (`architecture_deck`, `naval_engineering_deck`, `framegraph_seed_deck`),
wireframes/UI (`cs_suite_wireframe`, `vscode_frameforge_ide`, `widgets_gallery`),
brand/landing (`brand_book`, `saas_hero_headers`, `visual_identities`, logos),
illustration/game (`marina_whale`, `starlight_fox`, the Tron set,
`atlantis_adventure_game`), engineering/3D (`patent_fighter_jet_mechanisms_3d`,
`trebuchet_drawings`, `sdk_3d_scene`), books (`book_builder_demo`,
`world_cup_book`), SDK-feature showcases (`planar_kernel_showcase`,
`stroke_outline_showcase`, `sdk_symbol_instancing`, `library_showcase`,
`pattern_compose_deck`), and the vision/coach POC pipeline
(`poc2`…`poc9`, `coach_pipeline`, `vectorization_workflow`, `humanize_hand`).

---

## 13. Dependency posture

Runtime core is deliberately tiny: `pydantic>=2`, `pyyaml>=6`, `pyphen` (flow
hyphenation). Everything else is an **optional group** and degrades gracefully:
matplotlib/pillow (render), pymupdf (pdf), fonttools (metrics), plus
Chromium/Playwright, CairoSVG, OpenCV, Tesseract, potrace, Node/MathJax, and a
LaTeX toolchain for the richer backends. The `Dockerfile` bakes a font-rich
runtime (full google/fonts + broad Debian coverage, TeX Live, Chromium,
Tesseract) so `font_family`-by-name resolution and every backend work in one
image; `test_docker_contract.py` guards that contract.

---

## 14. Assessment (honest)

**Strengths**
- Rigorous source-of-truth discipline: 13 local gates + CI + drift tests make
  silent divergence between model, schema, grammar, spec, docs, and viewer very
  hard.
- Clean hexagonal separation: pure stdlib domain cores with heavy backends behind
  ports and lazy imports — the SVG path runs with almost no dependencies.
- Unusual breadth done tastefully: the SDK now spans generative geometry
  (planar booleans, stroke outlining, fractals, lattices, manifolds), real color
  science, and full document structure (book/flow/figure) — all lowering to
  grammar-native primitives rather than extending the schema.
- The PALS's-Law posture is enforced structurally, not just documented: the
  vision lane's output is explicitly unverified and must round-trip through
  validation.

**Risks & things to watch**
- **Proposed, not conformant.** No renderer is a conformance oracle; the SVG /
  matplotlib renderers are sanity checks, not fidelity guarantees. Treat rendered
  pixels as verification input, not proof.
- **Large optional-dependency surface.** Full fidelity depends on Chromium,
  LaTeX, OpenCV, Tesseract, potrace, and Node/MathJax. Reproducibility hinges on
  the Docker image or a carefully provisioned environment; bare checkouts get the
  degraded (still-useful) path.
- **MCP logic concentration.** Most server behavior lives in a few large modules
  (`server.py` / `usecases.py` / `pipeline.py`); worth watching for further
  decomposition as tools grow.
- **Local checkout hygiene.** This working tree carries an untracked top-level
  `framegraph/` directory (stale build artifacts / an old package copy); the real,
  tracked package is `src/framegraph/`. It is harmless but can mislead casual
  inspection — `conftest.py` explicitly manages the `framegraph`-module shadow so
  imports resolve to `docs/models/framegraph.py`.

---

## 15. Provenance & method

This report was assembled by reading the live tree after syncing `origin/main`
into the working branch: repository docs (`README.md`, `PURPOSE.md`,
`CHANGELOG.md`, the ADRs), the `Makefile` / CI workflows, and a fan-out survey of
`src/framegraph/**`, `tooling/`, `tests/`, and `static/examples/`. Figures
(85 `$defs`, 32 SDK modules, 179 test files, 105 example clients, 375 patterns,
7 themes, 13 gates, version 2.4.1) were read from the tree at generation time and
may drift as the code evolves — re-derive from source before relying on any
number here. Per rule 2 of `CLAUDE.md`, claims are grounded in files present in
the repository; where a detail could not be verified it was omitted rather than
guessed.
