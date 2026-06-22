---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-22"
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
| Normative prose & grammar | [spec/](./spec/), [grammar/](./grammar/) | exists |
| Status, scope, honest limits | [README.md](./README.md), [CHANGELOG.md](./CHANGELOG.md) | exists |
| Mission / non-goals, CLI contracts, process, disclaimer | `PURPOSE.md`, `AGENTS.md`, `CLAUDE.md`, `DISCLAIMER.md` | **`[Target]` — do not exist yet** |

> The four governance files in the last row are **planned, not present.** Earlier drafts
> of this document cited them as live sources of truth; they are not. Until they land,
> their topics are governed here. See §16.

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
  621 extras: `dev = ["pytest>=8"]` and `render = ["matplotlib>=3.7", "pillow>=10"]`
  ([pyproject.toml:18-20](./pyproject.toml#L18-L20)). `uv sync` installs `dev` by default;
  `uv sync --group render` adds the matplotlib proxy renderer's deps.
- **`[Enforced]`** This is a **virtual project**: `package = false`
  ([pyproject.toml:27](./pyproject.toml#L27)). The tree runs via `sys.path`-rooted scripts;
  it is deliberately **not** built or installed (an installed `framegraph` distribution
  would shadow the [models/framegraph.py](./models/framegraph.py) module the tooling imports).
- **`[Enforced]`** Lock state lives in [uv.lock](./uv.lock). Do not hand-edit it; CI syncs
  with `uv sync --locked` ([ci.yml:25](./.github/workflows/ci.yml#L25)).
- **`[Adopted]`** No new runtime dependency without justification. Do not pull a
  browser/GUI/graphics stack into the core (§13).
- **`[Target]`** Floor on `pydantic>=2.7` (today the floor is `>=2`). Tighten only with a
  documented reason (a feature actually used).

## 3. The quality gate

The gate is the contract for "done." It has **one definition**, run two places.

- **`[Enforced]`** `make check = schema-check + test + validate + overflow`
  ([Makefile:27](./Makefile#L27)). A change is not done until it passes.
  - `schema-check` — `uv run python schema/build_schema.py --check`: fails if the committed
    [schema/framegraph-v2.schema.json](./schema/framegraph-v2.schema.json) drifted from the
    models ([Makefile:29-30](./Makefile#L29-L30)).
  - `test` — `uv run pytest -q` ([Makefile:32-33](./Makefile#L32-L33)).
  - `validate` — `uv run python tooling/validate.py fixtures/*.fg.yaml`: structural +
    geometric rules ([Makefile:35-36](./Makefile#L35-L36)).
  - `overflow` — `uv run python tooling/render_fixtures.py --all --check-overflow`: asserts
    no text spills its box ([Makefile:38-39](./Makefile#L38-L39)).
- **`[Enforced]`** **CI mirrors `make check`.** [ci.yml:27-38](./.github/workflows/ci.yml#L27-L38)
  runs the same four gates as separate steps after `uv sync --locked`. The Makefile header
  and CI both state CI runs exactly what `make check` runs — keep them in lockstep; if they
  must diverge, document why here.
- **`[Target]`** Fold `lint` and `typecheck` (§4, §5) into the gate once they are green
  (see §16). Today they are **not** in `make check`.

## 4. Code style (ruff)

- **`[Enforced — non-gating]`** `ruff` is the linter, fetched ephemerally via `uvx`. It is
  deliberately **non-blocking** today: `make lint` runs `-uvx ruff check .` (leading `-`
  ignores failure, [Makefile:41-42](./Makefile#L41-L42)) and CI runs it with
  `continue-on-error: true` ([ci.yml:40-42](./.github/workflows/ci.yml#L40-L42)). Lint
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
- **`[Adopted]`** **Codemod ⇄ validator.** [tooling/codemod.py](./tooling/codemod.py)'s
  migrations are exactly the breaking/renamed forms the validator rejects — running it makes a
  legacy document pass. **Grammar ⇄ models** is kept consistent by hand; the grammar is a *view*,
  the models are the authority if the two disagree.
- **`[Target]`** A formal golden-snapshot harness with an explicit drift tolerance, so that a
  change pushing prior v1.x/v2.x output outside tolerance is flagged automatically as breaking.
  Today regression is covered by the fixture-validation + overflow gates and the HEAD oracle,
  not a tolerance-configured snapshot diff.

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

## 10. Pre-commit and CI

- **`[Enforced]`** CI is the gate ([.github/workflows/ci.yml](./.github/workflows/ci.yml)):
  the `python` job runs the four `make check` gates; the `viewer` job is a **non-blocking**
  smoke build of the JS bundle (`continue-on-error: true`).
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
| 5 | Golden-snapshot harness + drift tolerance | fixture-validate + overflow only | §8 | M |
| 6 | `.pre-commit-config.yaml` mirroring CI | none | §10 | S |
| 7 | Governance docs: `PURPOSE.md`, `AGENTS.md`, `CLAUDE.md`, `DISCLAIMER.md` | none | table, §12, §13 | S–M |
| 8 | Runtime `__version__` + `make release` | single literal, no recipe | §9 | S |
| 9 | Multi-version CI matrix (3.10–3.12) + `classifiers` | 3.10 named, single runner | §1 | S |

**Rule of motion:** adding to the gate (`[Target]` → `[Enforced]`) is a `feat:`/`refactor:`
that updates the relevant section's tag and removes its row here. Removing a gate, or letting
the config fall behind a stated `[Enforced]` value, is a regression to be justified in writing.

---

[↑ Back to root README](./README.md)
