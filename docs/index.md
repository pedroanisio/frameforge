---
disclaimer:
  notice: >-
    No information within this document should be taken for granted. Any
    statement or premise not backed by a real logical definition or a
    verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-24"
---

# FrameGraph v2 — HEAD

A single, internally-consistent cut of **FrameGraph v2**: a *proposed,
not-yet-conformantly-implemented* document/graphics DSL for decks, diagrams,
books, and letters.

!!! note "What to trust"
    The Pydantic **models are the source of truth**. The JSON Schema, the
    validator, the codemod, and **this whole site** are generated from or checked
    against them — so the docs can't silently drift. The prose and grammar are
    design targets to verify.

## A minimal document

A complete FrameGraph document is `dsl` + `version` + at least one page. This
example is **validated in CI** (`tests/test_doc_examples.py` parses every complete
example in these docs and checks it against the models) — so it can't drift:

```yaml
dsl: FrameGraph
version: "2.2.0"
title: Minimal document
pages:
  - mode: page
    id: hello
    canvas: { size: [320, 200], units: px }
    layers:
      - id: main
        objects:
          - type: rect
            box: [0, 0, 320, 200]
            fill: "#0d9648"
          - type: text
            box: [24, 84, 272, 40]
            text: "Hello, FrameGraph"
            style: { color: "#ffffff", font_size: 24, text_align: center }
```

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
