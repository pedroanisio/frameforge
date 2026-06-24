---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-24"
---

# codebase-standards

## Disclaimer

This document follows the project's own **"don't overclaim"** ethos
([README.md](./README.md), *Honest limits*): the parts you can run are the parts to
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
| Toolchain, deps, version, packaging | [pyproject.toml](./pyproject.toml) | exists |
| The quality gate (what must pass) | [Makefile](./Makefile) (`make check`), mirrored by [ci.yml](./.github/workflows/ci.yml) | exists |
| Format / conformance (the data model) | [models/framegraph.py](./models/framegraph.py) (Pydantic v2, **source of truth**) | exists |
| Generated JSON schema | [schema/build_schema.py](./schema/build_schema.py) (`--check` fails on drift) | exists |
| Normative prose & grammar | [spec/](./spec/), [grammar/](./grammar/) (grammar ⇄ models gated by [check_grammar_sync.py](./tooling/check_grammar_sync.py)) | exists |
| Status, scope, honest limits | [README.md](./README.md), [CHANGELOG.md](./CHANGELOG.md) | exists |
| Mission / non-goals, CLI contracts, process, disclaimer | `PURPOSE.md`, `AGENTS.md`, `CLAUDE.md`, `DISCLAIMER.md` | partial: `AGENTS.md` is still missing |

> The governance row is only partially closed. Earlier drafts of this document cited all
> four files as live sources of truth; `AGENTS.md` is still absent, so agent/process topics
> remain governed here until that file lands. See §16.

---

## 1. Language and runtime

- **`[Enforced]`** Source language is Python. Minimum runtime **3.10**
  (`requires-python = ">=3.10"`, [pyproject.toml:6](./pyproject.toml#L6)).
- **`[Adopted]`** New code is Python. The "TypeScript over JavaScript" default applies
  only to the standalone [viewer/](./viewer/) (a separate JS bundle), not the core.
- **`[Adopted]`** The core SVG proxy renderer is **dependency-free** at its core
  ([README.md](./README.md), *Run it*) — pure-Python rendering is load-bearing (§13).
- **`[Target]`** Declared `classifiers` for 3.10/3.11/3.12 and a CI matrix across them.
  Today only 3.10 is named, and CI runs a single runner ([ci.yml](./.github/workflows/ci.yml)).
- **`[Target]`** Shipped `py.typed` + fully annotated public surface. **Not applicable
  today** — the project is a *virtual* (non-installed) tree, see §2.

## 2. Dependencies and packaging

- **`[Enforced]`** Runtime deps are minimal, pinned by floor: `pydantic>=2`, `pyyaml>=6`
  ([pyproject.toml:11-12](./pyproject.toml#L11-L12)).
- **`[Enforced]`** Optional capability sets are **PEP 735 dependency-groups**, not PEP
  621 extras: `dev` (hypothesis + pytest), `render = ["matplotlib>=3.7", "pillow>=10"]`,
  `browser = ["playwright>=1.44"]`, `pdf = ["pymupdf>=1.24"]`,
  `metrics = ["fonttools>=4"]`, and `mcp = ["mcp[cli]>=1.27,<2"]`
  ([pyproject.toml:21-34](./pyproject.toml#L21-L34)). `uv sync` installs `dev` by default;
  `uv sync --group render` adds the matplotlib proxy renderer's deps,
  `uv sync --group browser` adds the Headless-Chromium raster renderer's deps, and
  `uv sync --group pdf` adds PyMuPDF for the PDF -> FrameGraph transpiler. `uv sync
  --group mcp` installs the Model Context Protocol adapter; it is not a core dependency.
- **`[Enforced]`** This is a **virtual project**: `package = false`
  ([pyproject.toml:33](./pyproject.toml#L33)). The tree runs via `sys.path`-rooted scripts;
  it is deliberately **not** built or installed (an installed `framegraph` distribution
  would shadow the [models/framegraph.py](./models/framegraph.py) module the tooling imports).
- **`[Enforced]`** Lock state lives in [uv.lock](./uv.lock). Do not hand-edit it; CI syncs
  from the lock with `uv sync --locked` — the `python` job adds `--group pdf` so the PDF
  transpiler's `importorskip`-gated e2e test runs ([ci.yml:25](./.github/workflows/ci.yml#L25)).
- **`[Adopted]`** No new runtime dependency without justification. Do not pull a
  browser/GUI/graphics stack into the core (§13).
- **`[Adopted]`** `make live` is a stdlib local web adapter over the existing MCP/session
  functions. It must not add a browser or web-framework dependency to the core runtime.
- **`[Target]`** Floor on `pydantic>=2.7` (today the floor is `>=2`). Tighten only with a
  documented reason (a feature actually used).

## 3. The quality gate

The gate is the contract for "done." It has **one definition**, run two places.

- **`[Enforced]`** `make check = schema-check + grammar-check + spec-check + a11y-check +
  status-check + test + validate + overflow + golden-check + docs-check` ([Makefile](./Makefile)). A change is not done until it passes.
  - `schema-check` — `uv run python schema/build_schema.py --check`: fails if the committed
    [schema/framegraph-v2.schema.json](./schema/framegraph-v2.schema.json) drifted from the
    models ([Makefile:33-34](./Makefile#L33-L34)).
  - `grammar-check` — `uv run python tooling/check_grammar_sync.py`: fails if the EBNF grammar
    drifted from the models on the **core profile** (a mismatched object/flow `type` or a
    divergent enum). Out-of-profile grammar (charts, the UML zoo, connectors) is a non-blocking
    warning; `--strict` demands full parity ([Makefile:36-37](./Makefile#L36-L37)).
  - `spec-check` — `uv run python tooling/check_spec_sync.py --quiet`: fails if the spec prose
    drops a model type, flow discriminator, or inline discriminator.
  - `a11y-check` — `uv run python tooling/check_accessibility.py $(FIXTURES_YAML)`: fails if a
    page's `reading_order` references a missing or duplicate id (a broken/ambiguous structure
    tree); missing image `alt` and pages without a `reading_order` are advisory warnings that
    `--strict` promotes ([Makefile:39-40](./Makefile#L39-L40)).
  - `test` — `uv run pytest -q` ([Makefile:42-43](./Makefile#L42-L43)). The suite includes the
    documentation drift gate (`test_docs_in_sync.py`) and the executable-examples gate
    (`test_doc_examples.py`) — see §8.
  - `validate` — `uv run python tooling/validate.py $(FIXTURES_YAML)`: structural +
    geometric rules ([Makefile:45-46](./Makefile#L45-L46)).
  - `overflow` — `uv run python tooling/render_fixtures.py --all --check-overflow`: asserts
    no text spills its box ([Makefile:48-49](./Makefile#L48-L49)).
  - `golden-check` — `uv run python tooling/render_golden.py`: fails if the b1/ oracle's per-page
    SVG renders drift from the committed hash lock (`tests/golden/oracle.lock.json`); re-pin an
    intentional render change with `make golden` ([Makefile:85-86](./Makefile#L85-L86)).
  - `status-check` — `uv run python tooling/gen_status.py --check`: fails if
    [FIXTURE-STATUS.md](./FIXTURE-STATUS.md) drifted from the validator ([Makefile:54-55](./Makefile#L54-L55)).
  - `docs-check` — `uv run python tooling/gen_docs.py --check`: regenerates the docs pages and
    asserts every `mkdocs.yml` nav entry resolves ([Makefile:65-66](./Makefile#L65-L66)).
- **`[Enforced]`** **CI mirrors `make check`.** The `python` job
  ([ci.yml:28-50](./.github/workflows/ci.yml#L28-L50)) runs schema-check, grammar-check, a11y-check,
  spec-check, test, validate, overflow, golden-check, and status-check as separate steps after `uv sync --locked --group pdf` (the
  `pdf` group only lets the transpiler's gated e2e test execute; the gate *commands* still
  match `make check`); the ninth gate, `docs-check`, runs in the dedicated `docs` job
  ([ci.yml:57-69](./.github/workflows/ci.yml#L57-L69)) which also builds the site with
  `mkdocs build --strict`. Keep make and CI in lockstep; if they must diverge, document why here.
- **`[Target]`** Fold `lint` and `typecheck` (§4, §5) into the gate once they are green
  (see §16). Today they are **not** in `make check`.

## 4. Code style (ruff)

- **`[Enforced — non-gating]`** `ruff` is the linter, fetched ephemerally via `uvx`. It is
  deliberately **non-blocking** today: `make lint` runs `-uvx ruff check .` (leading `-`
  ignores failure, [Makefile:68-69](./Makefile#L68-L69)) and CI runs it with
  `continue-on-error: true` ([ci.yml:52-54](./.github/workflows/ci.yml#L52-L54)). Lint
  output is advisory; a lint failure does **not** fail the build.
- **`[Target]`** A committed, gating ruff configuration. When adopted, the intended shape is:
  line length **100**; rule families `E, F, W, I, UP, B, C4, SIM, RET, D`; ignore `E501`
  (the formatter owns line length), `D203`, `D213`; **Google** docstring convention; per-file
  `D` exemptions for tests and dev/maintenance scripts (docstring rigor reserved for the
  public surface). **None of this is in [pyproject.toml](./pyproject.toml) today** — there is
  no `[tool.ruff]` section. Until there is, treat the ruleset above as the target, not a rule.
- **`[Target]`** `ruff format` as the formatter, with no formatter diffs allowed to land,
  and a `make fix` (`ruff check --fix . && ruff format .`) autofix path.

## 5. Type checking (mypy)

- **`[Target]`** `mypy --strict` over [models/](./models/) and [framegraph/](./framegraph/),
  with the `pydantic.mypy` plugin, wired into the gate as `make typecheck`. **Nothing exists
  today** — there is no `[tool.mypy]` config, no `typecheck` target, and CI does not type-check.
  This is one of the larger gaps (§16); new code should be written annotated and strict-clean
  so adoption is cheap when it lands.

## 6. Testing

- **`[Enforced]`** `pytest>=8` is the framework ([pyproject.toml:19](./pyproject.toml#L19));
  test discovery is `testpaths = ["tests"]` ([pyproject.toml:30](./pyproject.toml#L30)); the
  suite runs in the gate (§3).
- **`[Adopted]`** [tests/test_head.py](./tests/test_head.py) is the **HEAD oracle**: it pins
  the models to 2.2.0, asserts schema-in-sync, the style-module surface, the P3 stroke
  single-form rejection, and that every authoritative fixture validates (directly, or after
  the codemod). It is runnable two ways — standalone (`python tests/test_head.py`) and under
  pytest — and both must stay green.
- **`[Adopted]`** Tests are deterministic, isolated, and assert against the authoritative
  fixtures (the oracle), not against incidental output.
- **`[Target]`** TDD as the default loop (Red → Green → Refactor), `tests/unit` +
  `tests/integration` trees, and `hypothesis` property tests. Today the suite is a single
  assertion module; no code ships without a test that exercises it.

## 7. Coverage

- **`[Target]`** Branch coverage measured on the core, gated at a published threshold (the
  standing target is **90% branch**), via `pytest-cov` and `--cov-fail-under`. **No coverage
  is measured or gated today** — there is no `pytest-cov`, no `[tool.coverage]`, and no
  `--cov-*` in `addopts`. Do not cite a coverage number as enforced; it is a destination.

## 8. The sync guarantee and regression

The project's central invariant is that **the models are the source of truth and everything
else is generated from or checked against them** ([README.md](./README.md), *The sync guarantee*).

- **`[Enforced]`** **Schema ⇄ models.** The schema is `Document.model_json_schema()`;
  `build_schema.py --check` is non-zero on drift (§3).
- **`[Enforced]`** **Validator ⇄ models.** [tooling/validate.py](./tooling/validate.py)
  validates against the same `Document` model, then layers the §3.3 / §3.6 / §9.6 rules; the
  gate runs it over the curated fixtures.
- **`[Enforced]`** **Text-fit.** The overflow gate asserts no text overflows its box (§3).
- **`[Enforced]`** **Docs ⇄ tooling.** [tests/test_docs_in_sync.py](./tests/test_docs_in_sync.py)
  asserts the README's `$defs` count, every `N/N green` test count, `pyproject` version ==
  `HEAD_VERSION`, and that every path in the README Layout map exists; `gen_status.py --check`
  keeps [FIXTURE-STATUS.md](./FIXTURE-STATUS.md) in sync with the validator; and
  [tests/test_doc_examples.py](./tests/test_doc_examples.py) validates every complete FrameGraph
  example shown in the prose. Documentation cannot silently drift from the code (the `status-check`
  and `docs-check` gates plus the pytest suite, §3).
- **`[Adopted]`** **Site ⇄ source.** The MkDocs site is generated by
  [tooling/gen_docs.py](./tooling/gen_docs.py) — schema reference from the schema, fixture
  gallery from the renderer, spec/grammar/changelog verbatim; `docs/index.md` is the only
  hand-written page, the rest are build artifacts (`make docs`).
- **`[Adopted]`** **Codemod ⇄ validator.** [tooling/codemod.py](./tooling/codemod.py)'s
  migrations are exactly the breaking/renamed forms the validator rejects — running it makes a
  legacy document pass.
- **`[Enforced]`** **Grammar ⇄ models.** The grammar is a *view*;
  [tooling/check_grammar_sync.py](./tooling/check_grammar_sync.py) (the `grammar-check` gate, §3)
  introspects the models and diffs the EBNF, failing on **core-profile** drift (a mismatched
  object/flow `type` or a divergent enum). Out-of-profile grammar (charts, the UML zoo,
  connectors) is a non-blocking warning; `--strict` demands full parity. The models are the
  authority if the two disagree.
- **`[Enforced]`** **Accessibility conformance.** [tooling/check_accessibility.py](./tooling/check_accessibility.py)
  (the `a11y-check` gate, §3) fails if a page's `reading_order` references a missing or duplicate id
  (a broken structure tree); missing image `alt` and pages without a `reading_order` are advisory.
  It keeps the accessibility vocabulary (`decorative`, `alt`/`actual_text`, `reading_order`) coherent
  for a future tagged export (roadmap item 2).
- **`[Enforced]`** **Golden renders.** [tooling/render_golden.py](./tooling/render_golden.py)
  (the `golden-check` gate, §3) pins each b1/ oracle fixture's per-page SVG output by SHA-256 in
  `tests/golden/oracle.lock.json`; any change in rendered output fails the gate until re-pinned
  with `make golden`. This catches output regressions the validate/overflow gates cannot.
- **`[Adopted]`** **Curated fixture gate.** `FIXTURES_YAML` is resolved from tracked
  `fixtures/*.fg.yaml` paths via `git ls-files`, so scratch/untracked fixture experiments do not
  silently change `make check`. Add a fixture to git before expecting the gate to validate it.
- **`[Target]`** An explicit **drift tolerance** (rasterized pixel diff) so a cosmetically-trivial
  change need not force a re-pin. Today the lock is exact (hash) over the deterministic SVG; there
  is no tolerance band yet.

## 9. Versioning and backward compatibility

- **`[Enforced]`** Single source of truth for the package version: `[project] version`
  in [pyproject.toml:3](./pyproject.toml#L3) (`2.2.0`). [tests/test_head.py](./tests/test_head.py)
  asserts the models report this version and that the schema is generated in sync.
- **`[Adopted]`** Semantic versioning. The format is **PROPOSED / partially-implemented**
  ([CHANGELOG.md](./CHANGELOG.md)); breaking changes (e.g. the 2.1.0 stroke single-form, the
  `size → sizing` rename) are documented there with their migration.
- **`[Adopted]`** **Migration is provided, not assumed.** Backward compatibility for legacy
  documents is delivered by the codemod (`codemod.py --in-place --bump`) and by accepting legacy
  shorthand as sugar — not by freezing the schema. [CHANGELOG.md](./CHANGELOG.md) is updated every
  release.
- **`[Target]`** Runtime `__version__` resolution and a release recipe (`make release
  VERSION=X.Y.Z`) that runs the full gate, builds, tags, and lets CI publish. Today
  [framegraph/__init__.py](./framegraph/__init__.py) carries **no** version logic and there is no
  release target; the single literal in `pyproject.toml` is the only version site.
- **`[Adopted]`** The distance to that target is **measurable**: `make package-check`
  ([tooling/check_package_readiness.py](./tooling/check_package_readiness.py)) asserts
  package-emit readiness, separating hard build/install blockers from advisory `[Target]`
  gaps. It is advisory — deliberately **not** in `make check` — and reports **NOT READY**
  today (4 blockers; FrameGraph is a virtual project by design, §2). See §16.

## 10. Pre-commit and CI

- **`[Enforced]`** CI is the gate ([.github/workflows/ci.yml](./.github/workflows/ci.yml)):
  the `python` job runs eight of the nine `make check` gates (schema, grammar, a11y, test, validate,
  overflow, golden, status-check); a `docs` job runs `docs-check` + `mkdocs build --strict`, and on pushes to
  `main` a `docs-deploy` job publishes versioned docs to GitHub Pages via `mike`; the `viewer`
  job is a **non-blocking** smoke build of the JS bundle (`continue-on-error: true`).
- **`[Target]`** A `.pre-commit-config.yaml` that runs the same lint/format/type checks at
  commit time — "the same gate, earlier." **No pre-commit config exists today;** earlier drafts
  described hooks and tool pins that are not present. Do not rely on commit-time hooks until this
  lands.

## 11. Commit conventions

- **`[Adopted]`** Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`,
  `release:`.
- **`[Adopted]`** AI-generated artifacts are labeled with their source model/tool (in
  frontmatter, metadata, or a commit trailer) — as this document's own frontmatter does.

## 12. Documentation standards

- **`[Adopted]`** Default prose format is Markdown (`.md`); default language English (EN-US).
  PT-BR only on request or for a PT-BR audience; when both appear, English is primary.
- **`[Adopted]`** The **honest-limits** discipline ([README.md](./README.md)): state scope and
  caveats plainly; never present a proxy/sanity-check as a fidelity guarantee.
- **`[Adopted]`** Markdown produced by an AI agent carries the disclaimer YAML frontmatter
  (`disclaimer.notice`, `generated_by`, `date` as `YYYY-MM-DD`) — as this file does.
- **`[Adopted]`** No wall-clock estimates (hours/days/weeks). Use a complexity scale:
  XS / S / M / L / XL.
- **`[Target]`** A root `DISCLAIMER.md` referenced from every `README.md` by a depth-matched
  relative path. **`DISCLAIMER.md` does not exist yet** — until it does, keep the disclaimer
  self-contained in frontmatter (as here) rather than linking to a missing file.

## 13. Architecture and purpose commitments

These are the load-bearing commitments of the project; treat them as **`[Adopted]`** and
non-negotiable absent an explicit, documented decision.

- **Core commitments.** YAML/JSON is the authoring surface; the Pydantic models are the source
  of truth; SVG is the primary output; **pure-Python, dependency-free core rendering** stays
  first-class; the schema/validator/codemod/grammar stay **in sync** with the models (§8).
- **MCP boundary.** [framegraph/mcp/](./framegraph/mcp/) is an optional adapter for AI coding
  feedback loops: Python SDK code runs in a per-session subprocess, emits FrameGraph YAML, and
  the existing validator/SVG proxy renderer produce artifacts for inspection. MCP dependencies
  stay in the optional `mcp` group; do not import them from the core SDK or renderer path.
- **Live-session boundary.** [framegraph/live/](./framegraph/live/) is a local HTTP UI over the
  same MCP/session functions. It may serve browser chrome, session metadata, diagnostics, and
  rendered artifacts, but it must not become a separate renderer or introduce core web deps.
- **Honest scope.** FrameGraph v2 is a **proposed** format. No renderer is conformant; the
  matplotlib and SVG proxies are sanity checks, not fidelity guarantees. Font pinning gives
  deterministic *layout* only up to a stated tolerance, not pixel-exact identity (§9.6).
- **In-progress restructuring.** A DDD split is underway:
  [framegraph/rendering](./framegraph/rendering/) hosts the *rendering* bounded context; the
  conformance/schema context still lives in [models/](./models/), [schema/](./schema/), and
  [tooling/](./tooling/) and is migrated in later steps
  ([framegraph/__init__.py](./framegraph/__init__.py)). Do not justify a decision by the *current*
  mid-migration shape; move toward the target structure.
- **Non-goals (do not build):** a WYSIWYG editor; a browser-only rendering stack in the core;
  an interactive presentation runtime; a general-purpose scientific-charting replacement; a
  constraint-solver layout engine for every diagram class.
- Document significant architecture decisions with rationale and trade-offs. Fix root causes,
  not symptoms. **Production-ready code only** — no placeholders, stubs, or "implement later."
- **`[Target]`** A `PURPOSE.md` that makes the above mission/non-goals authoritative on their own.

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
- **`[Target]`** A written contract banner on every function that calls an LLM.

## 15. Agent behavioral constraints (ranked)

Ranked; higher rank wins on conflict. **`[Adopted]`**.

1. **Unbiased over flattering** — state flaws directly; no hedging or agreeableness padding.
2. **Verify, don't fabricate** — concrete, correct claims with provenance; never invent
   references, theorems, API signatures, config values, or file paths. "I cannot verify this"
   is always acceptable, and preferred over a confident guess.
3. **English over Portuguese** (see §12).
4. **Markdown over DOCX**; Python is the core language (the JS viewer is the exception, §1).
5. **Mandatory disclaimer frontmatter** in agent-authored Markdown (see §12).
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
| 4 | TDD loop, `unit`/`integration` trees, hypothesis | single oracle module | §6 | M |
| 5 | Golden-render **drift tolerance** (rasterized) | exact hash lock (`render_golden.py`) | §8 | M |
| 6 | `.pre-commit-config.yaml` mirroring CI | none | §10 | S |
| 7 | Governance docs: `AGENTS.md` plus any remaining governance alignment | partial | table, §12, §13 | S–M |
| 8 | Runtime `__version__` + `make release` | single literal, no recipe | §9 | S |
| 9 | Multi-version CI matrix (3.10–3.12) + `classifiers` | 3.10 named, single runner | §1 | S |

**Package-emit readiness** spans rows 1 (`py.typed`/`classifiers`), 8 (`__version__` + `make
release`), and 9, plus the §2 `package = false` decision. That composite gap is now
measurable: `make package-check` ([tooling/check_package_readiness.py](./tooling/check_package_readiness.py))
asserts it and reports **NOT READY** today (4 blockers, 3 gaps). It is advisory — not part of
`make check` — and shrinks as these rows close. The blockers are real: no `[build-system]`
table, `[tool.uv] package = false`, the `framegraph` dist name shadowing `models/framegraph.py`
(§2), and `framegraph/` importing the top-level `tooling` package (which would not ship in a
wheel — the same coupling flagged as tension #1 in `conceptual-analysis.md`).

**Rule of motion:** adding to the gate (`[Target]` → `[Enforced]`) is a `feat:`/`refactor:`
that updates the relevant section's tag and removes its row here. Removing a gate, or letting
the config fall behind a stated `[Enforced]` value, is a regression to be justified in writing.

---

[↑ Back to root README](./README.md)
