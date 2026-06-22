# FrameGraph v2 — HEAD release

A single, internally-consistent cut of **FrameGraph v2** (`2.2.0`) in which the
documents, grammar, schema, prose, and Python code are kept in sync — the Pydantic
models are the source of truth and everything else is generated from or checked
against them.

> **Status (unchanged from the project's own stance):** FrameGraph v2 is a **proposed,
> not-yet-conformantly-implemented** format. The prose and grammar are design targets to
> verify. The parts you can actually *run* — the models, the generated schema, the
> validator, and the codemod — are the parts to trust.

## Layout

```
models/framegraph.py          ← SOURCE OF TRUTH (Pydantic v2). Core conformance profile + all patches.
framegraph/                   ← rendering package (DDD split, in progress): the SVG proxy's domain/infra.
schema/
  framegraph-v2.schema.json   ← GENERATED from the models (77 $defs). Do not hand-edit.
  build_schema.py             ← regenerates the schema; `--check` fails if it drifts.
grammar/
  framegraph-v2.ebnf          ← the consolidated CORE grammar (base + P1–P4); styling deferred to the module.
  framegraph-v2-style.ebnf    ← the AUTHORITATIVE CSS style module (adopted verbatim at 2.2.0).
spec/framegraph-v2-spec.md    ← the normative prose (folds P1–P4 + the style module + cascade + corrections).
tooling/
  validate.py                 ← structural (models) + static/geometric rules the schema can't express.
  codemod.py                  ← migrates a document to HEAD (stroke split, size→sizing, gradient, aliases).
  render_fixtures.py          ← dependency-free SVG proxy renderer (+ `--check-overflow` text-fit gate).
  render_fg_doc.py            ← the matplotlib PROXY renderer, patched to HEAD (sanity check only).
  gen_status.py               ← GENERATES FIXTURE-STATUS.md from the validator (`--check` gates drift).
  gen_docs.py                 ← GENERATES the docs-site pages (schema reference, gallery, spec, grammar).
fixtures/                     ← the original fixtures, migrated to 2.2.0.
  b1/                         ← the 8 AUTHORITATIVE fixtures (the oracle the tests assert against).
tests/
  test_head.py                ← assertions: authoritative fixtures validate, schema in sync, style surface, P3.
  test_docs_in_sync.py        ← doc drift gate: README/CHANGELOG numbers + Layout paths match the tooling.
  test_doc_examples.py        ← validates every complete FrameGraph example shown in the prose.
docs/ + mkdocs.yml            ← the GENERATED MkDocs site (only docs/index.md is committed; `make docs`).
FIXTURE-STATUS.md             ← GENERATED validator status for the delivered fixtures (gen_status.py).
CHANGELOG.md                  ← version, the breaking change + migration, conformance classes, rec. resolution.
codebase-standards.md         ← the elevated engineering bar, status-tagged (Enforced / Adopted / Target).
pyproject.toml + uv.lock      ← the uv virtual project (deps; dev/render groups; `package = false`).
Makefile + .github/workflows/ ← `make check` = the local gate; CI mirrors it (+ a docs build/deploy job).
```

## The sync guarantee (what "in sync" means here, concretely)

1. **Schema ⇄ models.** `schema/framegraph-v2.schema.json` is produced by
   `Document.model_json_schema()`. `build_schema.py --check` returns non-zero if the
   committed file differs from a fresh build — so they cannot silently drift.
2. **Validator ⇄ models.** `validate.py` validates against the same `Document` model,
   then layers the §3.3/§3.6/§9.6 rules.
3. **Codemod ⇄ validator.** The codemod's migrations are exactly the breaking/renamed
   forms the validator rejects; running it makes a legacy document pass.
4. **Grammar ⇄ models.** The EBNF is kept consistent by hand (the grammar is a *view*;
   the models are the source). Every production the models add — `Style`, `BorderSide`,
   `Sizing`/`SizeMode`, `DimensionObject`, `sizing`, `Stroke = Color` — is present in
   the grammar, and the grammar has no remaining dangling references.

## Run it

The project is managed with [uv](https://docs.astral.sh/uv/). `uv sync` once to
create `.venv` with the runtime deps (`pydantic>=2`, `pyyaml`) plus the `dev`
group (`pytest`); prefix commands with `uv run`.

```bash
uv sync                                    # create/populate .venv

# schema is generated and in sync
uv run python schema/build_schema.py --check

# validate the (migrated) fixtures — 0 errors on the core profile
uv run python tooling/validate.py fixtures/*.fg.yaml

# migrate a legacy v2 document to HEAD
uv run python tooling/codemod.py path/to/legacy.fg.json --in-place --bump

# run the assertions (13/13 green), either runner
uv run python tests/test_head.py
uv run pytest

# SVG proxy renderer (dependency-free core) -> out/render/index.html
uv run python tooling/render_fixtures.py --all

# the whole local gate (schema · tests · validate · overflow · fixture-status · docs nav)
make check

# build & browse the generated documentation site (Material theme, live reload)
make docs-serve
```

The matplotlib proxy renderer (`tooling/render_fg_doc.py`) needs the extra
`render` dependency group:

```bash
uv sync --group render                     # adds matplotlib + pillow
```

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
  superseded by `spec/framegraph-v2-spec.md`.
- `FrameGraph-2.0.0-Specification-Complement.md` — the reconciliation that produced the
  recommendations this release implements; its §8 actions are resolved in `CHANGELOG.md`.
- The four standalone patch documents (P1–P4) are folded into the grammar, the spec, and
  the models here; they remain useful as rationale.

## Honest limits (don't overclaim)

- This is a **proposed** format. No renderer is conformant; the proxy renderer uses
  DejaVu stand-in fonts and is a sanity check, not a fidelity guarantee.
- The grammar is consolidated and paren-balanced but is a **view** kept in sync by hand;
  the models are the authority if the two ever disagree.
- Font pinning enables deterministic *layout* only up to a stated rounding **tolerance**
  (a defined shaping model is also required) — not pixel-exact identity (§9.6).
- Two of the nine fixtures (Coopera) retain **2 genuine errors each** (an `image` with a
  `stroke`, which images don't have) — surfaced by the validator, to be fixed at source.
