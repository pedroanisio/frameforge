---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-07-03"
---

# RELEASE.md — the FrameForge HEAD version-bump procedure

The package version is one *logical* source of truth — `[project] version` in
[pyproject.toml](pyproject.toml) — that, by necessity, lives in ten hand-edited
literals plus one human-authored CHANGELOG entry. The gates cross-check the
literals so a **half-bump can never ship**: `make check` fails on the smallest
divergence. This document formalises the invariants, the ordered procedure, and
the one-command automation (`make bump`).

Companion policy: [`docs/codebase-standards.md` §9](docs/codebase-standards.md).
Coupling inventory: `docs/drift-risk-map.md` (generated skill report; regenerate
via the drift-risk-map skill when stale).

---

## 1 · Invariants — what `make check` enforces

A correct release is exactly the state in which all of these hold. Each is
machine-checked; the "Gate" column is where a violation surfaces.

| # | Invariant | Sites | Gate |
|---|---|---|---|
| **I1** | declared version == the CONTRACT revision this engine is built against | [pyproject.toml:3](pyproject.toml#L3) == [`frameforge_api.model.HEAD_VERSION`](https://github.com/pedroanisio/frameforge-api) | `tests/test_docs_in_sync.py` |
| **I2** | the contract's version == the pinned test literal | `frameforge_api.model.HEAD_VERSION` == [test_head.py](tests/test_head.py) | `tests/test_head.py::test_version_is_head` |
| **I2b** | declared version == the package runtime `__version__` | [pyproject.toml:3](pyproject.toml#L3) == [frameforge/__init__.py `__version__`](src/frameforge/__init__.py) | `tests/test_docs_in_sync.py::test_package_runtime_version_matches_pyproject` |
| **I3** | the committed schema is generated-in-sync **and** its title carries the version | models → `docs/schema/frameforge-v2.schema.json` | `schema-check` + `test_head.py::test_schema_in_sync_with_models` + `test_docs_in_sync.py` |
| **I4** | the capability manifest reflects the live tree | `docs/capability-manifest.json` | `tests/test_capability_manifest.py::test_committed_manifest_matches_fresh_build` (the `manifest-check` target is the same contract, but it is **not** on `check:` — the test is what runs) |
| **I5** | README's honest counts + paths match reality | `README.md` (`$defs` count, `N/N green`, Layout paths) | `tests/test_docs_in_sync.py` |
| **I6** | every generated nav page exists and is fresh | `docs/*.md` (reference/spec/grammar/…) | `docs-check` |
| **I7** | the plugin surface pins the package version | plugin manifest, marketplace manifest, the runtime image tag, the launcher's `FRAMEFORGE_IMAGE` fallback | `tests/test_plugin_contract.py` (§1 version parity; the `plugin-check` target additionally runs `claude plugin validate`, and is **not** on `check:`) |
| **I8** | the version *prose* restatements agree with `HEAD_VERSION` | `CHANGELOG.md` top block, [docs/spec/frameforge-v2-spec.md](docs/spec/frameforge-v2-spec.md) front-matter, `Document.version` field description | `tests/test_version_prose_sync.py` |

Every invariant above is reached by `make check` — directly through a gate on the
`check:` target in [Makefile](Makefile), or through the `test` target, which runs
the whole pytest suite and therefore includes the contract tests named above.
**"`make check` is green" is a proof that the bump is complete** — with one
documented exception: the README version headline is moved by `make bump` but
gated by nothing (§7).

---

## 2 · Source of truth vs. derived

**Authored on a bump (hand-edited — `make bump` moves the ten literals):**

| Artifact | Literal |
|---|---|
| [pyproject.toml:3](pyproject.toml#L3) | `version = "X.Y.Z"` — the declared package version |
| [tests/test_head.py](tests/test_head.py) | `HEAD_VERSION == "X.Y.Z"` — the contract pin |
| [README.md](README.md) | `**FrameForge v2** (\`X.Y.Z\`)` — the human headline (**ungated**, §7) |
| [src/frameforge/__init__.py](src/frameforge/__init__.py) | `__version__ = "X.Y.Z"` — the package runtime version |
| [plugin/.claude-plugin/plugin.json](plugin/.claude-plugin/plugin.json) | `"version"` — what an installed plugin re-fetches on |
| [plugin/.claude-plugin/plugin.json](plugin/.claude-plugin/plugin.json) | `ghcr.io/pedroanisio/frameforge:X.Y.Z` — the runtime image the plugin launches |
| [plugin/bin/frameforge-mcp](plugin/bin/frameforge-mcp) | `FRAMEFORGE_IMAGE:-…:X.Y.Z` — the launcher's standalone fallback |
| [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json) | `"version"` — the marketplace entry |
| [CHANGELOG.md](CHANGELOG.md) | `**Version:** \`X.Y.Z\`` — the top block's declared version (gated by I8) |
| [docs/spec/frameforge-v2-spec.md](docs/spec/frameforge-v2-spec.md) | `version: X.Y.Z` — the spec front-matter (gated by I8) |
| [CHANGELOG.md](CHANGELOG.md) | the `## X.Y.Z` entry (+ migration if breaking) — **human judgement, not automated** |

**Generated (never hand-edit — regenerate):** schema (`make schema`),
capability manifest (`make manifest`), examples index (`make examples-index`),
site pages (`make docs`), `FIXTURE-STATUS.md` (`make status`). The Pydantic
models are the DSL source of truth; the schema/site are downstream of them.

---

## 3 · Procedure

Each step names the gate that verifies it.

0. **Preconditions.** Clean working tree; `CHANGELOG.md` not mid-merge; choose
   the bump type (§4).
1. **Move the ten literals** → `make bump VERSION=X.Y.Z` (the raw mover,
   `python tooling/bump_version.py X.Y.Z`, moves the literals only — no regen
   chain; see §6); or collapse steps 1, 2, and 4 in one shot with
   `make release VERSION=X.Y.Z`, which also regenerates every derived artifact
   and runs the gate. *Verify:* `make bump-check`.
2. **Regenerate derived artifacts.** `make bump` already runs
   `schema manifest examples-index`; for the full nav check run `make docs-check`
   (or `make docs` for the site). *Verify:* `schema-check`, `manifest-check`,
   `docs-check`.
3. **CHANGELOG.md.** Add the `## X.Y.Z` entry; for a breaking change document the
   migration and confirm `codemod.py --bump` covers it (§5).
4. **Gate.** `make check` — all gates green **proves** §1.
5. **Runtime.** `make docker-build` — rebakes `BUILD_VERSION`
   ([Makefile](Makefile), `docker-build` target); the image `version` verb detects skew
   ([AGENTS.md](AGENTS.md)).
6. **Ship.** Commit `release: X.Y.Z` on a `<type>/<issue#>-<slug>` branch; open a
   PR (CI reruns `make check`); squash-merge (§11 of codebase-standards).

---

## 4 · Semantic versioning — the practiced convention

Honest caveat: semver here is **PROPOSED / partially-implemented**
([CHANGELOG.md](CHANGELOG.md), §9). What the history actually does, within the
`v2` line:

- **MAJOR** (`2 → 3`) — a new DSL line. Not yet done.
- **MINOR** (`2.x`) — features / additive surface (**2.3.0** typed Connector),
  *and* breaking changes that ship **with a codemod** (**2.1.0** stroke
  single-form; **2.2.0** P3 stroke collapse). This deliberately deviates from
  strict semver: a breaking-change-with-migration is a *minor* here, not a major.
- **PATCH** (`2.x.y`) — fixes with no schema/DSL contract change.

Rule of thumb: if the schema `$defs` or any field contract changes → at least
**MINOR** + a CHANGELOG migration note. If a document authored on the prior
version no longer validates → provide `codemod.py --bump` coverage.

**Since 2.11.0 the contract sets the clock.** The models are the `frameforge-api`
distribution, which versions the *format* on its own schedule; this repo declares
which revision of that contract it is built and gated against, and I1/I2 hold the
two equal. So a bump here is normally "adopt contract X.Y.Z", and the semver
question above is answered by what the CONTRACT changed, not by what this
repository changed. Engine-only work that adopts no new contract still moves the
patch digit — but it may not silently redefine what `X.Y.Z` means, because the
number is shared with a package that publishes its own.

---

## 5 · Breaking changes

Backward compatibility is **delivered, not assumed** (§9): migrate, don't freeze.

- `codemod.py --in-place --bump` migrates legacy documents; legacy shorthand is
  accepted as sugar.
- The CHANGELOG entry states the break and the migration command.
- The enforced pattern: the old form is *rejected with a message that points at
  the codemod* — see `tests/test_head.py::test_p3_inline_geometry_stroke_rejected`.

---

## 6 · Automation

- **`make bump VERSION=X.Y.Z`** → [tooling/bump_version.py](tooling/bump_version.py)
  rewrites the ten literals, then regenerates schema + manifest + examples-index,
  then prints the remaining human steps.
- **`make bump-check`** → assert the ten sites agree (a fast pre-flight;
  `test_head` + `test_docs_in_sync` remain the authoritative gates).
- **`python tooling/bump_version.py X.Y.Z --dry-run`** → show the edits, write
  nothing.

---

## 7 · Known gaps (honest)

- **Nine hand-edited version sites.** Five in the package proper, four in the
  Claude Code plugin surface (the plugin manifest, the runtime image tag it
  launches, the launcher's standalone `FRAMEFORGE_IMAGE` fallback, and the
  marketplace manifest). Cross-checked by the gates (a divergence
  can't ship) and moved together by `make bump` — but not DRY. A single generated
  source would remove the footgun entirely; it remains unbuilt — `make release`
  (§9 `[Enforced]`) wraps bump → regenerate → gate, but the version literals stay
  hand-maintained.
- **The README version headline is ungated.** `make bump` moves it, but no test
  asserts it: `test_docs_in_sync.py`'s README assertions cover the `$defs` count,
  the `N/N green` claims, and the Layout paths — never `**FrameForge v2** (\`X.Y.Z\`)`.
  A hand-edit that drifts it ships green. The other eight sites are all pinned
  (§1 I1/I2/I2b/I7).
- **Ungated cosmetic staleness.** Prose and shipped commands that hardcode a
  version are reported by the bump's cosmetic sweep
  ([bump_version.py `COSMETIC_GLOBS`](tooling/bump_version.py)) but never rewritten —
  review by hand on every bump. The consequential ones are the `docker pull
  ghcr.io/pedroanisio/frameforge:X.Y.Z` commands in
  [docs/plugin-windows-setup.md](docs/plugin-windows-setup.md),
  [docs/desktop-cowork-setup.md](docs/desktop-cowork-setup.md), and
  [plugin/skills/frameforge-runtime/SKILL.md](plugin/skills/frameforge-runtime/SKILL.md):
  a reader who follows them pulls the *previous* release while the plugin manifest
  asks for the current one.
- **A gated site the mover does not move: `docs/index.md`.** The minimal-document
  example's `version:` literal is **not** cosmetic —
  `tests/test_doc_drift_guards.py::test_index_example_version_is_head` fails the
  bump until it matches `HEAD_VERSION`. It is reported by the cosmetic sweep but
  rewritten by nobody, so a bump that stops at `make bump` leaves `make check` red.
  Edit it by hand (or teach [bump_version.py](tooling/bump_version.py) a twelfth
  site — the honest fix, still unbuilt).
  Genuinely cosmetic-only: the landing demo (repo `frameforge-example`), and sample console output in
  `skills/frameforge-mcp-docker/SKILL.md`. The landing demo additionally carries a
  self-verifying `FACTS` table — run
  `python examples/frameforge_landing.py --verify` in the sibling `frameforge-example`
  repo on a bump; it re-derives
  every count and reports drift, and it is **not** on `check:`.
- **CI docs-deploy probe — RESOLVED (2.5.0).** The `docs-deploy` job no longer
  hardcodes a `docs/models` path; it derives the version from
  `frameforge_api.model.HEAD_VERSION` (ci.yml), which the pre-merge gates already
  exercise.
- **Tag + publish remain manual.** `make release VERSION=X.Y.Z`
  ([Makefile](Makefile), `release` target) bumps every site, regenerates every
  derived artifact, and runs the full gate; the by-hand tail is what it prints
  as its remaining checklist — the CHANGELOG entry, `git tag vX.Y.Z`,
  `make docker-build` (§9 `[Enforced]`, residual `[Target]`).

---

## Quick reference

```sh
make bump VERSION=X.Y.Z    # 1. rewrite the 11 version sites + regenerate
#                            2. edit CHANGELOG.md (+ migration if breaking)
make check                 # 3. all gates green == every §1 invariant holds
make docker-build          # 4. rebake the runtime version stamp
git commit -m "release: X.Y.Z"   # 5. on a branch → PR → squash-merge
```
