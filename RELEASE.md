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
[pyproject.toml](pyproject.toml) — that, by necessity, lives in five hand-edited
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
| **I1** | declared version == the models' reported version | [pyproject.toml:3](pyproject.toml#L3) == [model.py:41 `HEAD_VERSION`](src/frameforge/model.py#L41) | `tests/test_docs_in_sync.py` |
| **I2** | the models' version == the pinned test literal | `HEAD_VERSION` == [test_head.py:73](tests/test_head.py#L73) | `tests/test_head.py::test_version_is_head` |
| **I2b** | declared version == the package runtime `__version__` | [pyproject.toml:3](pyproject.toml#L3) == [frameforge/__init__.py `__version__`](src/frameforge/__init__.py) | `tests/test_docs_in_sync.py::test_package_runtime_version_matches_pyproject` |
| **I3** | the committed schema is generated-in-sync **and** its title carries the version | models → `docs/schema/frameforge-v2.schema.json` | `schema-check` + `test_head.py::test_schema_in_sync_with_models` + `test_docs_in_sync.py` |
| **I4** | the capability manifest reflects the live tree | `docs/capability-manifest.json` | `manifest-check` |
| **I5** | README's honest counts + paths match reality | `README.md` (`$defs` count, `N/N green`, Layout paths) | `tests/test_docs_in_sync.py` |
| **I6** | every generated nav page exists and is fresh | `docs/*.md` (reference/spec/grammar/…) | `docs-check` |

Because every invariant is inside `make check` (every gate listed on the `check:`
target in [Makefile](Makefile)),
**"`make check` is green" is a proof that the bump is complete.**

---

## 2 · Source of truth vs. derived

**Authored on a bump (hand-edited — `make bump` moves the five literals):**

| Artifact | Literal |
|---|---|
| [pyproject.toml:3](pyproject.toml#L3) | `version = "X.Y.Z"` — the declared package version |
| [src/frameforge/model.py:41](src/frameforge/model.py#L41) | `HEAD_VERSION = "X.Y.Z"` — the models' report |
| [tests/test_head.py:73](tests/test_head.py#L73) | `HEAD_VERSION == "X.Y.Z"` — the version pin |
| [README.md](README.md) | `**FrameForge v2** (\`X.Y.Z\`)` — the human headline |
| [src/frameforge/__init__.py](src/frameforge/__init__.py) | `__version__ = "X.Y.Z"` — the package runtime version |
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
1. **Move the five literals** → `make bump VERSION=X.Y.Z` (the raw mover,
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
  rewrites the five literals, then regenerates schema + manifest + examples-index,
  then prints the remaining human steps.
- **`make bump-check`** → assert the five sites agree (a fast pre-flight;
  `test_head` + `test_docs_in_sync` remain the authoritative gates).
- **`python tooling/bump_version.py X.Y.Z --dry-run`** → show the edits, write
  nothing.

---

## 7 · Known gaps (honest)

- **Five hand-edited version sites.** Cross-checked by the gates (a divergence
  can't ship) and moved together by `make bump` — but not DRY. A single generated
  source would remove the footgun entirely; it remains unbuilt — `make release`
  (§9 `[Enforced]`) wraps bump → regenerate → gate, but the version literals stay
  hand-maintained.
- **Ungated cosmetic staleness.** `static/examples/illustrator_vs_frameforge.py`,
  `static/examples/zen_libficar.py`, and `skills/frameforge-mcp-docker/SKILL.md`
  hardcode `v2.3.0` in prose/comments, and the `docs/index.md` minimal-document
  example carries a `version:` literal (`test_doc_examples.py` checks it
  *validates*, not that it is current) — **not gated**; grep-sweep on a bump.
- **CI docs-deploy probe — RESOLVED (2.5.0).** The `docs-deploy` job no longer
  hardcodes a `docs/models` path; it derives the version from
  `frameforge.model.HEAD_VERSION` (ci.yml), which the pre-merge gates already
  exercise.
- **Tag + publish remain manual.** `make release VERSION=X.Y.Z`
  ([Makefile](Makefile), `release` target) bumps every site, regenerates every
  derived artifact, and runs the full gate; the by-hand tail is what it prints
  as its remaining checklist — the CHANGELOG entry, `git tag vX.Y.Z`,
  `make docker-build` (§9 `[Enforced]`, residual `[Target]`).

---

## Quick reference

```sh
make bump VERSION=X.Y.Z    # 1. rewrite the 5 version sites + regenerate
#                            2. edit CHANGELOG.md (+ migration if breaking)
make check                 # 3. all gates green == every §1 invariant holds
make docker-build          # 4. rebake the runtime version stamp
git commit -m "release: X.Y.Z"   # 5. on a branch → PR → squash-merge
```
