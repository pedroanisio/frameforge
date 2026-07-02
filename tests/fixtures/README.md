# `fixtures/` — what holds here

This directory is the **gated conformance corpus**. Every full-corpus gate walks it:

| Gate | What it walks | Cost driver |
|---|---|---|
| `tooling/gen_status.py` → `FIXTURE-STATUS.md` | top-level `fixtures/*.fg.yaml` + `*.framegraph.yml` | validates every file |
| `tooling/render_fixtures.py` (default / `--all`) | **all of `fixtures/` recursively** | parses + normalizes + renders every file |
| `tests/test_head.py`, golden oracle (`tests/golden/oracle.lock.json`) | `b1/` corpus | validates + diffs every page |

Because these gates are `O(corpus)` and several run on every `make check`, **the size of this
tree is directly the speed of the test suite.** Keep it lean. (History: this corpus had grown to
~87 files / 23 MB — full of multi-slide art decks — and the suite took ~11 min, ~95% of it in six
whole-corpus tests. Trimming to the canonical set below is what keeps it fast.)

## A fixture belongs at the top level only if it is

1. **Conformant at HEAD** — `tooling/validate.py` reports zero errors, *or* a single documented
   known-error class (see `FIXTURE-STATUS.md`). It must never be silently broken.
2. **Tied to a test or gate** — it backs a specific capability/regression test, or represents a
   document *class* the renderers must keep handling. If no test references it, it does not belong.
3. **Minimal and focused** — the smallest document that demonstrates the thing. A *capability*
   fixture exercises one area (`arrows`, `effects`, `tables`, `transforms`, `text-spans`,
   `group-layout`, `topology-perspective`, …). A *representative-document* fixture
   (`calendar-3day`, `wordle-how-to-play`, `nyt-mideast-live`, `edst1-flange`) stays page-bounded.
4. **Stable / maintained** — if it breaks, the gate is catching a real regression, not bit-rot in
   disposable art.

Rule of thumb: a capability fixture is a few KB–tens of KB; a representative document is a handful
of pages. If a file is hundreds of KB or 1 MB+, it almost certainly does **not** belong here.

## What does NOT belong here

- **Large multi-slide SDK showcase / art decks** (30–40 page cinematic/neon/branded demos). The
  *builder* lives in `examples/`; the rendered deck is demo art, not a conformance gate. Checking a
  1–3 MB deck into the corpus taxes every full-corpus gate for zero extra capability coverage.
  Archive the rendered output under an ungated `../fixture_old/` directory (create it if needed)
  or just regenerate it from its `examples/*.py` builder on demand.
- **One-off experiments, scratch renders, PDFs, or raw assets.** Out of this tree entirely.

> The "a reused/ported component must be backed by a checked-in fixture" rule is satisfied by a
> **small, focused** fixture that exercises the component — not by a full art deck. Build the deck
> in `examples/`; back the *component* with a minimal fixture here.

## Subdirectories (also under the render walk — keep bounded)

- **`b1/`** — the **pre-codemod oracle** corpus (`*.fg.json`). Authored against the *old* schema and
  validated/diffed *as-is* by `tests/test_head.py` (the `AUTHORITATIVE` list) and the golden oracle;
  it is intentionally **not** codemodded and **not** part of the top-level `gen_status` glob. Add a
  file here only when introducing a new oracle document, and update `tests/golden/oracle.lock.json`.
  Do not author HEAD documents here.
- **`newset/`** — legacy-schema presentation decks that exist to exercise the
  **normalize-to-pages** path in `render_fixtures.discover()` (legacy `.yml` → 2.2.0 `pages`).
  Add a file here only to cover a legacy-normalization case; see `tests/test_render_cli.py` and
  `tests/test_newset_render_skips.py`.

## Adding a fixture — checklist

- [ ] It passes `uv run python tooling/validate.py fixtures/<name>.fg.yaml` (or its error is a known,
      documented class).
- [ ] A test references it by name (capability/regression), or it represents a needed document class.
- [ ] It is the minimal document that makes the point — not a full deck.
- [ ] Run `make status` so `FIXTURE-STATUS.md` records it.
