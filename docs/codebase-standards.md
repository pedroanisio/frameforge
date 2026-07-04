---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code"
  date: "2026-07-02"
---

# codebase-standards

## Disclaimer

This document follows the project's own **"don't overclaim"** ethos
([README.md](../README.md), *Honest limits*): the parts you can run are the parts to
trust, and every claim here is either backed by a real config value or explicitly
marked as not-yet-enforced.

> No statement or premise not backed by a real logical definition or verifiable
> reference should be taken for granted.

---

## What this document is

This is the **elevated standard** for the **framegraph** repository — the bar we hold
ourselves to and are deliberately moving toward. It is **not** a cold snapshot of the
current config. Some standards here are gated by tooling today; others are commitments
we have not yet wired into the gate. To keep the aspiration honest, **every rule carries
a status tag**:

| Tag | Meaning |
|---|---|
| **`[Enforced]`** | Gated by config *today*. A violation fails `make check` or CI. Citation given. |
| **`[Adopted]`** | Practiced and expected today, but not mechanically gated. Reviewers uphold it. |
| **`[Target]`** | Committed direction. **Not yet in place.** A real gap we own — see §16. |

Rules of reading:

- A **`[Target]`** is a destination, not a license to ignore. New code should move
  *toward* it, never further away.
- Where this file and any other prose disagree, **the enforced config value wins** for
  `[Enforced]` items; `[Target]` items are governed by this document until the config
  catches up.
- The status tags are the only thing that may legitimately "lie about the present" —
  and they do so openly, by naming the gap.

### Source of truth per topic

| Topic | Source of truth | Status |
|---|---|---|
| Toolchain, deps, version, packaging | [pyproject.toml](../pyproject.toml) | exists |
| The quality gate (what must pass) | [Makefile](../Makefile) (`make check`), mirrored by [ci.yml](../.github/workflows/ci.yml) | exists |
| Format / conformance (the data model) | [docs/models/framegraph.py](./models/framegraph.py) (Pydantic v2, **source of truth**) | exists |
| Generated JSON schema | [docs/schema/build_schema.py](./schema/build_schema.py) (`--check` fails on drift) | exists |
| Normative prose & grammar | [docs/spec/](./spec/), [docs/grammar/](./grammar/) (grammar ⇄ models gated by [check_grammar_sync.py](../tooling/check_grammar_sync.py)) | exists |
| Status, scope, honest limits | [README.md](../README.md), [CHANGELOG.md](../CHANGELOG.md) | exists |
| Mission / non-goals, CLI contracts, process, disclaimer | [PURPOSE.md](../PURPOSE.md), [AGENTS.md](../AGENTS.md), [CLAUDE.md](../CLAUDE.md), [DISCLAIMER.md](../DISCLAIMER.md) | exists |

> The governance row is closed: all four files exist. [AGENTS.md](../AGENTS.md) (the
> programmatic CLI/tooling reference, landed 2026-07-01) owns the make-target and
> script-invocation surface; `CLAUDE.md` owns process. Earlier revisions of this document
> tracked `AGENTS.md` as a §16 gap — that row is retired.

---

## 1. Language and runtime

- **`[Enforced]`** Source language is Python. Minimum runtime **3.10**
  (`requires-python = ">=3.10"`, [pyproject.toml:6](../pyproject.toml#L6)).
- **`[Adopted]`** New code is Python. The "TypeScript over JavaScript" default applies
  only to the standalone [viewer/](../viewer/) (a separate JS bundle), not the core.
- **`[Adopted]`** The core SVG proxy renderer is **dependency-free** at its core
  ([README.md](../README.md), *Run it*) — pure-Python rendering is load-bearing (§13).
- **`[Target]`** Declared `classifiers` for 3.10/3.11/3.12 and a CI matrix across them.
  Today only 3.10 is named, and CI runs a single runner ([ci.yml](../.github/workflows/ci.yml)).
- **`[Target]`** Shipped `py.typed` + fully annotated public surface. **Not applicable
  today** — the project is a *virtual* (non-installed) tree, see §2.

## 2. Dependencies and packaging

- **`[Enforced]`** Runtime deps are minimal, pinned by floor: `pydantic>=2`, `pyyaml>=6`
  ([pyproject.toml:11-12](../pyproject.toml#L11-L12)).
- **`[Enforced]`** Optional capability sets are **PEP 735 dependency-groups**, not PEP
  621 extras ([pyproject.toml:40-68](../pyproject.toml#L40-L68)): `dev` (`hypothesis>=6` +
  `pytest>=8`, installed by default on `uv sync`), `render` (matplotlib proxy renderer),
  `browser` (Headless-Chromium raster), `pdf` (PyMuPDF — PDF **input** transpiler),
  `pdfout` (cairosvg + pypdf — PDF **output** from solved SVG pages), `metrics`
  (fonttools, real font-advance metrics), `mcp` (`mcp[cli]>=1.27,<2` + cairosvg as the
  browser-free raster fallback), and `vision` (opencv-python-headless + pillow +
  pytesseract — image→draft proposers and the measurement layer). Install per-capability
  with `uv sync --group <name>` or one-off with `uv run --group <name>`.
- **`[Enforced]`** The LaTeX/TikZ renderer (`tooling/render_latex.py`) adds **no** Python
  dependency: it shells out to a system TeX engine (lualatex preferred, pdflatex fallback)
  plus poppler's `pdftoppm` for `--png` ([pyproject.toml:30-39](../pyproject.toml#L30-L39)).
- **`[Enforced]`** Two console scripts are declared — `framegraph-render` and
  `fg-font` ([pyproject.toml:25-26](../pyproject.toml#L25-L26)) — but inert while the
  project stays virtual; they resolve as commands only where the package is
  installed (e.g. an external consumer or image). In this tree run the
  self-bootstrapping launchers: `uv run python tooling/framegraph_render.py`
  (PYTHONPATH-free; issue #35) or `python -m framegraph.cli` where `src`/`docs`
  are already on the path, and `uv run python tooling/fg_font.py` (thin
  launcher over `framegraph.fontpack`; also `make font-list` / `font-check`).
- **`[Enforced]`** This is a **virtual project**: `package = false`
  ([pyproject.toml:81](../pyproject.toml#L81)). The tree runs via `sys.path`-rooted scripts;
  it is deliberately **not** built or installed (an installed `framegraph` distribution
  would shadow the [docs/models/framegraph.py](./models/framegraph.py) module the tooling imports).
- **`[Enforced]`** Lock state lives in [uv.lock](../uv.lock). Do not hand-edit it; CI syncs
  from the lock with `uv sync --locked --group pdf` — the `pdf` group only lets the PDF
  transpiler's `importorskip`-gated e2e test run ([ci.yml:25](../.github/workflows/ci.yml#L25)).
- **`[Enforced — workaround]`** `[tool.uv] override-dependencies = ["starlette<1"]`
  ([pyproject.toml:82](../pyproject.toml#L82)) pins around a corrupt `starlette==1.3.1` on
  this environment's package index (it breaks the FastMCP import chain). The rationale is
  documented in-file; remove once the index stops serving the broken build.
- **`[Adopted]`** No new runtime dependency without justification. Do not pull a
  browser/GUI/graphics stack into the core (§13).
- **`[Adopted]`** `make live` is a stdlib local web adapter over the existing MCP/session
  functions. It must not add a browser or web-framework dependency to the core runtime.
- **`[Target]`** Floor on `pydantic>=2.7` (today the floor is `>=2`). Tighten only with a
  documented reason (a feature actually used).

## 3. The quality gate

The gate is the contract for "done." It has **one definition**, run two places.

- **`[Enforced]`** `make check` runs **twelve** gates ([Makefile:45](../Makefile#L45)):
  `schema-check grammar-check spec-check a11y-check status-check test validate overflow
  golden-check docs-check docs-linkcheck disclaimer-check`.
  A change is not done until it passes.
  - `schema-check` — `uv run python docs/schema/build_schema.py --check`: fails if the committed
    [docs/schema/framegraph-v2.schema.json](./schema/framegraph-v2.schema.json) drifted from the
    models ([Makefile:47-48](../Makefile#L47-L48)).
  - `grammar-check` — `uv run python tooling/check_grammar_sync.py`: fails if the EBNF grammar
    drifted from the models on the **core profile** (a mismatched object/flow `type` or a
    divergent enum). Out-of-profile grammar (charts, the UML zoo, connectors) is a non-blocking
    warning; `--strict` demands full parity ([Makefile:50-51](../Makefile#L50-L51)).
  - `spec-check` — `uv run python tooling/check_spec_sync.py --quiet`: fails if the spec prose
    drops a model type, flow discriminator, or inline discriminator ([Makefile:53-54](../Makefile#L53-L54)).
  - `a11y-check` — `uv run python tooling/check_accessibility.py $(FIXTURES_YAML) --quiet`:
    fails if a page's `reading_order` references a missing or duplicate id (a broken/ambiguous
    structure tree); missing image `alt` and pages without a `reading_order` are advisory
    warnings that `--strict` promotes ([Makefile:56-57](../Makefile#L56-L57)).
  - `test` — `uv run pytest -q` ([Makefile:59-60](../Makefile#L59-L60)). The suite is itself a
    battery of sync gates — docs drift, executable examples, generated-snapshot freshness,
    capability manifest, viewer contract, CI ⇄ make wiring, package boundary — see §6 and §8.
  - `validate` — `uv run python tooling/validate.py $(FIXTURES_YAML)`: structural +
    geometric rules ([Makefile:62-63](../Makefile#L62-L63)).
  - `overflow` — `uv run python tooling/render_fixtures.py --all --check-overflow`: asserts
    no text spills its box ([Makefile:65-66](../Makefile#L65-L66)).
  - `status-check` — `uv run python tooling/gen_status.py --check`: fails if
    [docs/FIXTURE-STATUS.md](./FIXTURE-STATUS.md) drifted from the validator ([Makefile:84-85](../Makefile#L84-L85)).
  - `golden-check` — `uv run python tooling/render_golden.py`: fails if the b1/ oracle's per-page
    SVG renders drift from the committed hash lock (`tests/golden/oracle.lock.json`); re-pin an
    intentional render change with `make golden` ([Makefile:133-134](../Makefile#L133-L134)).
  - `docs-check` — `uv run python tooling/gen_docs.py --check`: regenerates the docs pages,
    asserts every `mkdocs.yml` nav entry resolves **and** that the committed generated
    snapshots are fresh ([Makefile:95-96](../Makefile#L95-L96)).
  - `docs-linkcheck` — `uv run python tooling/check_doc_links.py`: fails if a tracked Markdown
    file has a broken relative link ([Makefile:110-111](../Makefile#L110-L111)).
  - `disclaimer-check` — `uv run python tooling/check_disclaimers.py`: fails if a tracked
    agent-authored Markdown doc is missing the rule-5 disclaimer frontmatter
    ([Makefile:113-114](../Makefile#L113-L114)).
- **`[Removed — justified]`** `brand-check` and `brand-logo-check` (added in the 2.3.0 pass)
  were **removed with the 2026-07-02 folder refactor**, per the rule of motion's
  written-justification requirement: the operator directed that non-core content — the
  `brand/` asset directory (tokens + generated logo masters) among it — stays **out of the
  codebase tree**. With their comparison inputs untracked, both gates had nothing to gate.
  The logo *generator* remains in-tree
  ([static/examples/framegraph_logo.py](../static/examples/framegraph_logo.py)); it now
  writes masters out of tree (`_tmp/brand/`).
- **`[Enforced]`** **CI runs `make check` verbatim.** The `python` job syncs from the lock
  (`uv sync --locked --group pdf`) and executes the Makefile target as a single step
  ([ci.yml:28](../.github/workflows/ci.yml#L28)), so the workflow *cannot* hand-mirror-and-drift.
  The wiring itself is pinned: [tests/test_ci_make_check_sync.py](../tests/test_ci_make_check_sync.py)
  fails if the literal `run: make check` leaves the workflow. (Earlier revisions of this
  document asked for make/CI lockstep by discipline; it is now enforced by test.)
- **`[Enforced]`** Two further **blocking** CI jobs sit outside `make check`: `docs` re-runs
  `gen_docs.py --check` and builds the site with `mkdocs build --strict`
  ([ci.yml:34-47](../.github/workflows/ci.yml#L34-L47)); `viewer-contract` runs the Node twin of
  the viewer ⇄ model type contract ([ci.yml:83-94](../.github/workflows/ci.yml#L83-L94), §8).
- **`[Adopted]`** `manifest-check` (capability-manifest drift, [Makefile:104-105](../Makefile#L104-L105))
  is a make target but not a `make check` dependency; the same freshness is blocking anyway via
  [tests/test_capability_manifest.py](../tests/test_capability_manifest.py) in the `test` gate.
- **`[Target]`** Fold `lint` and `typecheck` (§4, §5) into the gate once they are green
  (see §16). Today they are **not** in `make check`.

## 4. Code style (ruff)

- **`[Enforced — non-gating]`** `ruff` is the linter, fetched ephemerally via `uvx`. It is
  deliberately **non-blocking** today: `make lint` runs `-uvx ruff check .` (leading `-`
  ignores failure, [Makefile:116-117](../Makefile#L116-L117)) and CI runs it with
  `continue-on-error: true` ([ci.yml:30-32](../.github/workflows/ci.yml#L30-L32)). Lint
  output is advisory; a lint failure does **not** fail the build.
- **`[Target]`** A committed, gating ruff configuration. When adopted, the intended shape is:
  line length **100**; rule families `E, F, W, I, UP, B, C4, SIM, RET, D`; ignore `E501`
  (the formatter owns line length), `D203`, `D213`; **Google** docstring convention; per-file
  `D` exemptions for tests and dev/maintenance scripts (docstring rigor reserved for the
  public surface). **None of this is in [pyproject.toml](../pyproject.toml) today** — there is
  no `[tool.ruff]` section. Until there is, treat the ruleset above as the target, not a rule.
- **`[Target]`** `ruff format` as the formatter, with no formatter diffs allowed to land,
  and a `make fix` (`ruff check --fix . && ruff format .`) autofix path.

## 5. Type checking (mypy)

- **`[Target]`** `mypy --strict` over [docs/models/](./models/) and [src/framegraph/](../src/framegraph/),
  with the `pydantic.mypy` plugin, wired into the gate as `make typecheck`. **Nothing exists
  today** — there is no `[tool.mypy]` config, no `typecheck` target, and CI does not type-check.
  This is one of the larger gaps (§16); new code should be written annotated and strict-clean
  so adoption is cheap when it lands.

## 6. Testing

- **`[Enforced]`** `pytest>=8` + `hypothesis>=6` are the framework, in the default `dev`
  group ([pyproject.toml:40-44](../pyproject.toml#L40-L44)); test discovery is
  `testpaths = ["tests"]` ([pyproject.toml:84-85](../pyproject.toml#L84-L85)); the suite runs
  in the gate (§3).
- **`[Adopted]`** [tests/test_head.py](../tests/test_head.py) is the **HEAD oracle**: it pins
  the models to **2.3.0**, asserts schema-in-sync, the style-module surface, the P3 stroke
  single-form rejection, and that every authoritative fixture validates (directly, or after
  the codemod). It is runnable two ways — standalone (`python tests/test_head.py`) and under
  pytest — and both must stay green.
- **`[Adopted]`** The suite is no longer a single module: ~130 test files cover the models,
  SDK, the SVG/LaTeX/PDF/Chromium render paths, MCP tools, the vision layer, and the
  doc/CI sync gates (§8). Property-based tests exist
  ([tests/test_elements.py](../tests/test_elements.py),
  [tests/test_element_render.py](../tests/test_element_render.py) — hypothesis), but they are
  practice, not yet a mechanical requirement on new code.
- **`[Adopted]`** Tests are deterministic, isolated, and assert against the authoritative
  fixtures (the oracle), not against incidental output.
- **`[Target]`** TDD as the default loop (Red → Green → Refactor) and `tests/unit` +
  `tests/integration` trees. Today the tree is flat `tests/`; the hypothesis half of the
  original target has landed. No code ships without a test that exercises it.

## 7. Coverage

- **`[Target]`** Branch coverage measured on the core, gated at a published threshold (the
  standing target is **90% branch**), via `pytest-cov` and `--cov-fail-under`. **No coverage
  is measured or gated today** — there is no `pytest-cov`, no `[tool.coverage]`, and no
  `--cov-*` in `addopts`. Do not cite a coverage number as enforced; it is a destination.

## 8. The sync guarantee and regression

The project's central invariant is that **the models are the source of truth and everything
else is generated from or checked against them** ([README.md](../README.md), *The sync guarantee*).

- **`[Enforced]`** **Schema ⇄ models.** The schema is `Document.model_json_schema()`;
  `build_schema.py --check` is non-zero on drift (§3).
- **`[Enforced]`** **Validator ⇄ models.** [tooling/validate.py](../tooling/validate.py)
  validates against the same `Document` model, then layers the §3.3 / §3.6 / §9.6 rules; the
  gate runs it over the curated fixtures.
- **`[Enforced]`** **Text-fit.** The overflow gate asserts no text overflows its box (§3).
- **`[Enforced]`** **Docs ⇄ tooling.** [tests/test_docs_in_sync.py](../tests/test_docs_in_sync.py)
  asserts the README's `$defs` count, every `N/N green` test count, `pyproject` version ==
  `HEAD_VERSION`, and that every path in the README Layout map exists; `gen_status.py --check`
  keeps [docs/FIXTURE-STATUS.md](./FIXTURE-STATUS.md) in sync with the validator;
  [tests/test_doc_examples.py](../tests/test_doc_examples.py) validates every complete FrameGraph
  example shown in the prose; [tests/test_generated_docs_fresh.py](../tests/test_generated_docs_fresh.py)
  asserts the committed `docs/sdk.md`/`docs/sdk-api.md` snapshots equal a fresh build; and
  [tests/test_capability_manifest.py](../tests/test_capability_manifest.py) asserts
  `docs/capability-manifest.json` matches a fresh build and `docs/examples.md` lists exactly
  the tracked `examples/*.py`. Documentation cannot silently drift from the code (the
  `status-check` and `docs-check` gates plus the pytest suite, §3).
- **`[Enforced]`** **Site ⇄ source.** [tooling/gen_docs.py](../tooling/gen_docs.py) generates
  the site's content pages — schema reference from the schema, fixture gallery from the
  renderer, spec/grammar/changelog verbatim (transient build artifacts) — and the repo keeps
  four **committed generated snapshots**: `docs/sdk.md` + `docs/sdk-api.md` (SDK guide/API),
  `docs/examples.md` ([tooling/gen_examples_index.py](../tooling/gen_examples_index.py)), and
  `docs/capability-manifest.json` ([tooling/gen_capability_manifest.py](../tooling/gen_capability_manifest.py)).
  Snapshot freshness is gated twice — `docs-check` and the pytest suite (above).
- **`[Adopted]`** **Hand-written pages are now in nav.** Beyond `docs/index.md`, the
  `mkdocs.yml` nav carries `error-codes.md` and a *Design records* section
  (`architecture.md`, `output-space.md`, `roadmap.md`, the ADRs,
  `illustration-protocol.md`, `framegraph-vector-recreation-improvements.md`, `BRAND.md`) —
  all committed, hand-written pages. Everything else under `docs/` is a `make docs` build
  artifact. (Earlier revisions stated `index.md` was the only hand-written nav page; the
  nav has since grown.)
- **`[Adopted]`** **Codemod ⇄ validator.** [tooling/codemod.py](../tooling/codemod.py)'s
  migrations are exactly the breaking/renamed forms the validator rejects — running it makes a
  legacy document pass.
- **`[Enforced]`** **Grammar ⇄ models.** The grammar is a *view*;
  [tooling/check_grammar_sync.py](../tooling/check_grammar_sync.py) (the `grammar-check` gate, §3)
  introspects the models and diffs the EBNF, failing on **core-profile** drift (a mismatched
  object/flow `type` or a divergent enum). Out-of-profile grammar (charts, the UML zoo,
  connectors) is a non-blocking warning; `--strict` demands full parity. The models are the
  authority if the two disagree.
- **`[Enforced]`** **Accessibility conformance.** [tooling/check_accessibility.py](../tooling/check_accessibility.py)
  (the `a11y-check` gate, §3) fails if a page's `reading_order` references a missing or duplicate id
  (a broken structure tree); missing image `alt` and pages without a `reading_order` are advisory.
  It keeps the accessibility vocabulary (`decorative`, `alt`/`actual_text`, `reading_order`) coherent
  for a future tagged export (roadmap item 2).
- **`[Enforced]`** **Golden renders.** [tooling/render_golden.py](../tooling/render_golden.py)
  (the `golden-check` gate, §3) pins each b1/ oracle fixture's per-page SVG output by SHA-256 in
  `tests/golden/oracle.lock.json`; any change in rendered output fails the gate until re-pinned
  with `make golden`. This catches output regressions the validate/overflow gates cannot.
- **`[Removed — justified]`** **Brand ⇄ tokens.** The `brand-check` / `brand-logo-check`
  couplings were retired with the 2026-07-02 folder refactor: brand assets are non-core and
  live out of tree by operator direction, so there is no tracked comparison input left (§3).
  [docs/BRAND.md](./BRAND.md) remains as un-gated guideline prose.
- **`[Enforced]`** **Links.** `docs-linkcheck` ([tooling/check_doc_links.py](../tooling/check_doc_links.py))
  fails if any tracked Markdown file carries a broken relative link (§3).
- **`[Enforced]`** **Disclaimers.** `disclaimer-check` ([tooling/check_disclaimers.py](../tooling/check_disclaimers.py))
  fails if a tracked agent-authored `.md` is missing the rule-5 frontmatter (§12); exemptions
  are an explicit named set in the checker, not a heuristic.
- **`[Enforced]`** **Viewer ⇄ model.** The JS viewer hand-mirrors the document model, so its
  declared type surface (`viewer/dev/type-registry.json`) must stay reconciled with the model's
  discriminators: [tests/test_viewer_schema_contract.py](../tests/test_viewer_schema_contract.py)
  in the blocking pytest gate, plus its Node twin in the blocking `viewer-contract` CI job (§3).
- **`[Enforced]`** **CI ⇄ Makefile.** [tests/test_ci_make_check_sync.py](../tests/test_ci_make_check_sync.py)
  asserts the workflow delegates to `make check` (§3), so a Makefile-only gate cannot silently
  stop blocking pull requests.
- **`[Adopted]`** **Curated fixture gate.** `FIXTURES_YAML` is resolved from tracked
  **top-level** `tests/fixtures/*.fg.yaml` / `*.framegraph.yml` paths via `git ls-files`
  ([Makefile:9](../Makefile#L9)), so scratch/untracked fixture experiments do not silently
  change `make check`. Add a fixture to git before expecting the gate to validate it.
- **`[Target]`** An explicit **drift tolerance** (rasterized pixel diff) so a cosmetically-trivial
  change need not force a re-pin. Today the lock is exact (hash) over the deterministic SVG; there
  is no tolerance band yet.

## 9. Versioning and backward compatibility

The **bump procedure** — the four hand-edited version sites, the regeneration
chain, and the gate that proves each invariant — is formalised in
[RELEASE.md](../RELEASE.md) (run `make bump VERSION=X.Y.Z`; pre-flight with
`make bump-check`).

- **`[Enforced]`** Single source of truth for the package version: `[project] version`
  in [pyproject.toml:3](../pyproject.toml#L3) (`2.3.0`). [tests/test_head.py](../tests/test_head.py)
  asserts the models report this version and that the schema is generated in sync.
- **`[Adopted]`** Semantic versioning. The format is **PROPOSED / partially-implemented**
  ([CHANGELOG.md](../CHANGELOG.md)); breaking changes (e.g. the 2.1.0 stroke single-form, the
  `size → sizing` rename) are documented there with their migration.
- **`[Adopted]`** **Migration is provided, not assumed.** Backward compatibility for legacy
  documents is delivered by the codemod (`codemod.py --in-place --bump`) and by accepting legacy
  shorthand as sugar — not by freezing the schema. [CHANGELOG.md](../CHANGELOG.md) is updated every
  release.
- **`[Enforced]`** Runtime `framegraph.__version__`
  ([src/framegraph/__init__.py](../src/framegraph/__init__.py)) is a fifth version literal that `make bump`
  moves in lockstep and [tests/test_docs_in_sync.py](../tests/test_docs_in_sync.py) gates against
  `[project] version` — so the package can report its own version and it can never drift.
  A plain literal, not `importlib.metadata`, because this is a virtual (uninstalled) project (§2).
- **`[Enforced]`** `make release VERSION=X.Y.Z` runs the full recipe end to end: bump every
  site → regenerate schema / manifest / SDK snapshots / status / examples-index → `make check`
  (see RELEASE.md). *Residual* (still `[Target]`): the git tag and CI-publish steps stay by
  hand — the target prints them as the remaining checklist.
- **`[Adopted]`** The distance to that target is **measurable**: `make package-check`
  ([tooling/check_package_readiness.py](../tooling/check_package_readiness.py)) asserts
  package-emit readiness, separating hard build/install blockers from advisory `[Target]`
  gaps. It is advisory — deliberately **not** in `make check` — and reports **NOT READY**
  today (3 blockers, 3 gaps; FrameGraph is a virtual project by design, §2). See §16.

## 10. Pre-commit and CI

- **`[Enforced]`** CI is the gate ([.github/workflows/ci.yml](../.github/workflows/ci.yml)):
  the `python` job runs `make check` itself — all fourteen gates in one step, drift-proof by
  test (§3) — plus non-blocking ruff; a `docs` job runs `gen_docs.py --check` + `mkdocs build
  --strict`, and on pushes to `main` a `docs-deploy` job publishes versioned docs to GitHub
  Pages via `mike`; the `viewer-contract` job is **blocking** (viewer ⇄ model type surface,
  §8); the `viewer` smoke build stays **non-blocking** (`continue-on-error: true`).
- **`[Target]`** A `.pre-commit-config.yaml` that runs the same lint/format/type checks at
  commit time — "the same gate, earlier." **No pre-commit config exists today;** earlier drafts
  described hooks and tool pins that are not present. Do not rely on commit-time hooks until this
  lands.

## 11. Commit and workflow conventions

- **`[Adopted]`** Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`,
  `release:`. (This is the practiced set — the last 200 commits use exactly these types;
  extend it only when practice does.)
- **`[Adopted]`** AI-generated artifacts are labeled with their source model/tool (in
  frontmatter, metadata, or a commit trailer) — as this document's own frontmatter does.
- **`[Adopted]`** **Trunk-based branching.** Work driven by a GitHub issue branches from
  `main` as `<type>/<issue#>-<slug>`, with `<type>` from the conventional set above —
  e.g. `feat/28-pattern-catalog`, `fix/35-render-cli-models`. Tracking/umbrella issues
  get no branch. Direct pushes to `main` remain the operator's prerogative; agent-driven
  work goes through a branch and PR.
- **`[Enforced]`** **Every PR is gated.** CI triggers on `pull_request` and runs
  `make check` verbatim ([ci.yml](../.github/workflows/ci.yml), §3), so a PR cannot merge
  green without passing the full gate.
- **`[Enforced — settings]`** **Squash-merge only.** The repository accepts only squash
  merges for PRs and deletes head branches on merge (GitHub repository settings, set
  2026-07-02). `main` history therefore stays 1:1 with conventional commits: the squashed
  PR title must itself be a valid conventional-commit line.
- **`[Adopted]`** **PR ⇄ issue linkage.** A PR that completes an issue carries
  `Closes #N` in its body; partial work references the issue without closing it.
- **`[Adopted]`** **Definition of Ready (DoR).** An issue is ready to start when its
  blocking dependencies are closed, any gating decision (ADR) it names is ratified by the
  operator, and it states scope plus acceptance criteria. Starting a not-ready issue
  requires the operator's explicit direction.
- **`[Adopted]`** **Definition of Done (DoD).** §3's contract, applied per issue: the
  full gate (`make check`) is green, every acceptance-criteria box is checked, commits
  follow the conventions above, and user-visible changes carry a [CHANGELOG.md](../CHANGELOG.md)
  entry. Sub-gate mentions inside an issue (e.g. `make validate overflow`) are floor
  requirements, not a substitute for the full gate.

## 12. Documentation standards

- **`[Adopted]`** Default prose format is Markdown (`.md`); default language English (EN-US).
  PT-BR only on request or for a PT-BR audience; when both appear, English is primary.
- **`[Adopted]`** The **honest-limits** discipline ([README.md](../README.md)): state scope and
  caveats plainly; never present a proxy/sanity-check as a fidelity guarantee.
- **`[Enforced]`** Markdown produced by an AI agent carries the disclaimer YAML frontmatter
  (`disclaimer.notice`, `generated_by`, `date` as `YYYY-MM-DD`) — as this file does. Gated:
  `disclaimer-check` ([tooling/check_disclaimers.py](../tooling/check_disclaimers.py)) fails
  `make check` for any tracked `.md` outside the checker's explicit exempt set (READMEs,
  `CHANGELOG.md`, `CLAUDE.md`, generated snapshots).
- **`[Adopted]`** No wall-clock estimates (hours/days/weeks). Use a complexity scale:
  XS / S / M / L / XL.
- **`[Adopted]`** A root [DISCLAIMER.md](../DISCLAIMER.md) holds the repository-level
  methodological caveats. Per `CLAUDE.md`, product READMEs **may** link to it when they make
  methodological claims; there is deliberately **no** blanket every-README requirement.
  (An earlier revision targeted a mandatory depth-matched link from every README — that
  requirement was dropped when the governance docs landed.)

## 13. Architecture and purpose commitments

These are the load-bearing commitments of the project; treat them as **`[Adopted]`** and
non-negotiable absent an explicit, documented decision.

- **Core commitments.** YAML/JSON is the authoring surface; the Pydantic models are the source
  of truth; SVG is the primary output; **pure-Python, dependency-free core rendering** stays
  first-class; the schema/validator/codemod/grammar stay **in sync** with the models (§8).
- **Output surface.** SVG stays primary; the matplotlib proxy, headless-Chromium raster,
  LaTeX/TikZ (system TeX, no Python deps, §2), and PDF-out (`pdfout` group) paths are optional
  render backends behind the [src/framegraph/cli.py](../src/framegraph/cli.py) front door
  (`framegraph-render`; `--list` shows live availability). None of them is conformant
  (honest scope, below).
- **MCP boundary.** [src/framegraph/mcp/](../src/framegraph/mcp/) is an optional adapter for AI coding
  feedback loops: Python SDK code runs in a per-session subprocess, emits FrameGraph YAML, and
  the existing validator/SVG proxy renderer produce artifacts for inspection. MCP dependencies
  stay in the optional `mcp` group; do not import them from the core SDK or renderer path.
- **Live-session boundary.** [src/framegraph/live/](../src/framegraph/live/) is a local HTTP UI over the
  same MCP/session functions. It may serve browser chrome, session metadata, diagnostics, and
  rendered artifacts, but it must not become a separate renderer or introduce core web deps.
- **Vision boundary.** [src/framegraph/vision/](../src/framegraph/vision/) (image→draft proposers and
  the coordinate measurement layer) sits behind the optional `vision` dependency group and is
  lazily imported — the classical detectors and OCR load only when a propose tool runs. All
  CV/LLM proposals are UNVERIFIED drafts (§14) and must round-trip through the
  validator/renderer.
- **Honest scope.** FrameGraph v2 is a **proposed** format. No renderer is conformant; the
  matplotlib and SVG proxies are sanity checks, not fidelity guarantees. Font pinning gives
  deterministic *layout* only up to a stated tolerance, not pixel-exact identity (§9.6).
- **In-progress restructuring.** A DDD split is underway. The package now hosts several
  bounded contexts — [src/framegraph/rendering](../src/framegraph/rendering/) (render orchestrator +
  `normalize_doc` under `rendering/application/`, re-exported by `tooling/render_fixtures.py`
  for its CLI), [src/framegraph/sdk](../src/framegraph/sdk/), [src/framegraph/cli.py](../src/framegraph/cli.py),
  [src/framegraph/mcp](../src/framegraph/mcp/), [src/framegraph/live](../src/framegraph/live/),
  [src/framegraph/vision](../src/framegraph/vision/), [src/framegraph/coach](../src/framegraph/coach/),
  [src/framegraph/patterns](../src/framegraph/patterns/) (the #28/#29 slide-template catalog),
  [src/framegraph/library](../src/framegraph/library/) (the #32 themes/symbols/generators content
  library), and [src/framegraph/fontpack.py](../src/framegraph/fontpack.py) (ADR-0004 font packs;
  the `fg-font` console script) —
  while the conformance/schema context still lives in [docs/models/](./models/),
  [docs/schema/](./schema/), and [tooling/](../tooling/) and migrates in later steps
  ([src/framegraph/__init__.py](../src/framegraph/__init__.py)). Do not justify a decision by the
  *current* mid-migration shape; move toward the target structure. **The package no longer
  imports up into `tooling/`** — [tests/test_package_boundary.py](../tests/test_package_boundary.py)
  pins this in the gate, and `make package-check` re-asserts it.
- **Non-goals (do not build):** a WYSIWYG editor; a browser-only rendering stack in the core;
  an interactive presentation runtime; a general-purpose scientific-charting replacement; a
  constraint-solver layout engine for every diagram class.
- Document significant architecture decisions with rationale and trade-offs. Fix root causes,
  not symptoms. **Production-ready code only** — no placeholders, stubs, or "implement later."
- [PURPOSE.md](../PURPOSE.md) exists and makes the mission/non-goals authoritative on their
  own; this section defers to it where they overlap. (Formerly a `[Target]` here.)

## 14. LLM-output verification (PALS's Law)

- **`[Adopted — principle]`** LLMs statistically produce errors: omissions, hallucinations,
  partial completions, schema violations, silent failures. Any pipeline or agent consuming LLM
  output MUST treat that output as **untrusted, incomplete, and unverified** by default. Absence
  of an explicit verification layer is an architectural defect, not a downstream bug —
  regardless of how correct the output looks.
- This document is itself an instance: its predecessor asserted an entire enforcement regime
  (mypy, coverage gate, pre-commit, golden harness, four governance files) that **did not exist
  in the repo.** The fix was verification against real config — the status tags above are that
  verification layer made permanent.
- **`[Enforced]`** Rule 5's disclaimer frontmatter is now mechanically verified
  (`disclaimer-check`, §3/§12) — one PALS verification layer moved from prose to gate.
- **`[Target]`** A written contract banner on every function that calls an LLM.

## 15. Agent behavioral constraints (ranked)

Ranked; higher rank wins on conflict. **`[Adopted]`**.

1. **Unbiased over flattering** — state flaws directly; no hedging or agreeableness padding.
2. **Verify, don't fabricate** — concrete, correct claims with provenance; never invent
   references, theorems, API signatures, config values, or file paths. "I cannot verify this"
   is always acceptable, and preferred over a confident guess.
3. **English over Portuguese** (see §12).
4. **Markdown over DOCX**; Python is the core language (the JS viewer is the exception, §1).
5. **Mandatory disclaimer frontmatter** in agent-authored Markdown (see §12; gated by
   `disclaimer-check`).
6. **Feedback is a claim, not a source of truth** — accept sound parts and explain, refute
   unsound parts and explain; never silently comply with feedback that breaks a standard here.
7. **Skill assertion gate** — if a Claude Code skill matches the request, invoke it.
8. **Execution discipline** — when a task is clear, execute it. No planning theatre, no
   approval-seeking on obvious subtasks. **No deferrals** without operator authorization.

## 16. Roadmap — closing the gap (the `[Target]` ledger)

The elevated bar above commits us to standards not yet gated. Tracked here so the gap is
explicit and shrinking, never silently assumed-met. Complexity scale per §12.

| # | Target | Today | Section | Complexity |
|---|---|---|---|---|
| 1 | Gating ruff config (`[tool.ruff]`, ruleset, format) | non-gating `uvx ruff check .` | §4 | S |
| 2 | `mypy --strict` + `pydantic.mypy`, in the gate | absent entirely | §5 | M |
| 3 | Coverage measured + gated (target 90% branch) | not measured | §7 | M |
| 4 | TDD loop + `unit`/`integration` trees | flat `tests/` (~130 modules; hypothesis landed) | §6 | M |
| 5 | Golden-render **drift tolerance** (rasterized) | exact hash lock (`render_golden.py`) | §8 | M |
| 6 | `.pre-commit-config.yaml` mirroring CI | none | §10 | S |
| 8 | Multi-version CI matrix (3.10–3.12) + `classifiers` | 3.10 named, single runner | §1 | S |

**Closed since the 2026-06-24 revision** (per the rule of motion, their rows are removed):
the governance docs — `AGENTS.md`, `PURPOSE.md`, and `DISCLAIMER.md` all exist (source-of-truth
table, §12, §13); two gates entered `make check` (`docs-linkcheck`, `disclaimer-check`, §3);
CI ⇄ make lockstep moved from discipline to a pinned test (§3); and hypothesis property tests
landed (§6, shrinking row 4). **2026-07-04:** row 7 (runtime `__version__` + a
release recipe) closed — `framegraph.__version__` is a fifth gated version literal and
`make release` runs the full bump→regenerate→check recipe (§9; RELEASE.md); only the
git-tag/CI-publish steps remain by hand.

**The 2026-07-02 folder refactor** (operator-directed) moved the tree to a src layout —
package in `src/framegraph/`, reference sources under `docs/` (`models/`, `schema/`, `spec/`,
`grammar/`), the fixture corpus in `tests/fixtures/`, runnable clients in `static/examples/` —
and evicted all non-core content (`brand/`, `demo/`, `recipe/`, POC notes, scratch scripts)
from the tree. Two gates (`brand-check`, `brand-logo-check`) were retired with written
justification (§3, §8): their comparison inputs are no longer tracked.

**Package-emit readiness** spans row 8 (`classifiers`) and the §1 `py.typed` target, plus
the §2 `package = false` decision (row 7's runtime `__version__` + release recipe landed
2026-07-04). That
composite gap is measurable: `make package-check`
([tooling/check_package_readiness.py](../tooling/check_package_readiness.py)) asserts it and
reports **NOT READY** today (3 blockers, 3 gaps). It is advisory — not part of `make check` —
and shrinks as these rows close. The remaining blockers are the deliberate virtual-project
decisions: no `[build-system]` table, `[tool.uv] package = false`, and the `framegraph` dist
name shadowing `docs/models/framegraph.py` (§2). The former fourth blocker — `framegraph/`
importing the top-level `tooling` package (the inverted dependency, tension #1 in
`conceptual-analysis.md`) — has been **cleared**: the orchestrator + `normalize_doc` moved into
the package (§13), and [tests/test_package_boundary.py](../tests/test_package_boundary.py) keeps
it from regressing.

**Rule of motion:** adding to the gate (`[Target]` → `[Enforced]`) is a `feat:`/`refactor:`
that updates the relevant section's tag and removes its row here. Removing a gate, or letting
the config fall behind a stated `[Enforced]` value, is a regression to be justified in writing.

---

[↑ Back to root README](../README.md)
