# Contributing to FrameForge

FrameForge is a Python project managed with `uv`. The source package lives in
`src/frameforge`, and generated artifacts are committed only through their
paired generators.

## Development Setup

1. Install `uv`.
2. Run `uv sync` from the repository root.
3. Use `uv run ...` for local commands.

Common commands:

```bash
uv run pytest -q
make check
make docs-sdk
make manifest
```

`make check` is the full local gate used by CI. For a focused change, run the
smallest relevant test first, then run the broader gate that covers the changed
surface.

## Generated Files

Do not hand-edit generated outputs. Change the source or generator, then rerun
the matching target.

Generated outputs include:

- `docs/schema/frameforge-v2.schema.json`
- `FIXTURE-STATUS.md`
- `docs/sdk.md`
- `docs/sdk-api.md`
- `docs/capability-manifest.json`
- `docs/examples.md`

## Pull Requests

Keep pull requests focused. Include:

- what changed and why
- the tests or checks you ran
- any generated targets you refreshed
- any known limitations or follow-up work

If your change alters the model, SDK, MCP surface, renderer behavior, or docs
truth surfaces, add or update regression tests with the change.

## Fixtures

Fixtures under `tests/fixtures/` should be referenced by tests or gates. If a
fixture is only exploratory output, keep it out of the tracked fixture set.

The frozen `tests/fixtures/b1/` oracle is intentionally pinned. Do not edit it
unless the golden baseline is being updated deliberately.
