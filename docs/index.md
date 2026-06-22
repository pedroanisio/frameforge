# FrameGraph v2 — HEAD

A single, internally-consistent cut of **FrameGraph v2**: a *proposed,
not-yet-conformantly-implemented* document/graphics DSL for decks, diagrams,
books, and letters.

!!! note "What to trust"
    The Pydantic **models are the source of truth**. The JSON Schema, the
    validator, the codemod, and **this whole site** are generated from or checked
    against them — so the docs can't silently drift. The prose and grammar are
    design targets to verify.

## This site

| Page | What it is | Source |
|---|---|---|
| [Specification](spec.md) | the normative reference prose | `spec/framegraph-v2-spec.md` |
| [Schema reference](reference.md) | every model & property | **generated** from `schema/framegraph-v2.schema.json` |
| [Grammar](grammar.md) | the consolidated EBNF (a hand-kept *view*) | `grammar/*.ebnf` |
| [Fixture gallery](fixtures.md) | every fixture rendered to SVG + validator status | **generated** by `tooling/render_fixtures.py` + `tooling/gen_status.py` |
| [Changelog](changelog.md) | version history & rationale | `CHANGELOG.md` |

All pages except this one are **generated** by `tooling/gen_docs.py`; build the
site with `make docs` (it runs the generator first).

## The guarantee

```
models/framegraph.py  ──model_json_schema()──►  schema/framegraph-v2.schema.json
        │                                                │
        │ validate.py / pytest                           │ build_schema.py --check
        ▼                                                ▼
   the fixtures (oracle)                          generated reference + gallery
```

`make check` enforces it: schema in sync, the assertion suite, fixture validation,
the text-fit overflow proxy, the fixture-status table, and the **documentation
drift gate** (doc numbers/paths must match the tooling).
