---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code"
  date: "2026-07-01"
---

# AGENTS.md — programmatic CLI / tooling reference

The reference CLAUDE.md's priority-reading order points at: every `make`
target and `tooling/` entry point, with exact invocations. Facts here are
derived from the live `Makefile`, `pyproject.toml`, and script argparse
surfaces; when in doubt, `make help` and `<script> --help` are authoritative.

## Runtime

- Managed by [uv](https://docs.astral.sh/uv/); the tree is a **virtual project**
  (`[tool.uv] package = false`) — never `pip install` it; prefix everything with
  `uv run`.
- `uv sync` creates `.venv` with runtime deps + the `dev` group (pytest,
  hypothesis).
- Optional dependency groups (`uv sync --group <name>`, or one-off
  `uv run --group <name> python ...`):

| Group | Enables |
|---|---|
| `render` | matplotlib proxy renderer (`tooling/render_fg_doc.py`) |
| `browser` | headless-Chromium SVG→PNG raster (`tooling/render_chromium.py`) |
| `pdf` | PDF **input** transpiler (`tooling/pdf_to_framegraph_yml.py`, PyMuPDF) |
| `pdfout` | PDF **output** (`tooling/render_pdf.py`, cairosvg + pypdf) |
| `metrics` | real font-advance metrics (`--real-metrics`, `sdk.measure_text`) |
| `mcp` | the MCP server + cairosvg raster fallback |
| `vision` | image→draft proposers + the measurement layer (opencv, PIL, pytesseract) |

## Make targets

`make help` lists these live. `make check` is exactly what CI runs.

| Target | What it runs |
|---|---|
| `check` | every local gate: schema/grammar/spec/a11y/status + tests + validate + overflow + golden + docs nav/links + disclaimers |
| `test` | `uv run pytest -q` (the HEAD assertion suite) |
| `validate` | `tooling/validate.py` over the tracked top-level fixtures |
| `overflow` | `tooling/render_fixtures.py --all --check-overflow` (text-fit gate) |
| `schema` / `schema-check` | regenerate / drift-gate `docs/schema/framegraph-v2.schema.json` |
| `grammar-check` | `tooling/check_grammar_sync.py` (EBNF ⇄ models, core profile) |
| `spec-check` | `tooling/check_spec_sync.py --quiet` (spec prose ⇄ model discriminators) |
| `a11y-check` | `tooling/check_accessibility.py <fixtures> --quiet` (reading-order integrity) |
| `status` / `status-check` | regenerate / drift-gate `FIXTURE-STATUS.md` (`tooling/gen_status.py`) |
| `golden` / `golden-check` | re-pin / drift-gate the b1/ oracle SVG hash lock (`tooling/render_golden.py`) |
| `manifest` / `manifest-check` | regenerate / drift-gate `docs/capability-manifest.json` (`tooling/gen_capability_manifest.py`) |
| `examples-index` | regenerate `docs/examples.md` (`tooling/gen_examples_index.py`) |
| `render` | render every fixture to `out/render/` + contact sheet |
| `render-latex` | flow fixtures → LaTeX/TikZ + PDF via lualatex (`out/latex/`) |
| `pdf PDF=in.pdf [OUT=…]` | PDF → FrameGraph YAML transpile (pulls the `pdf` group) |
| `docs` / `docs-serve` / `docs-check` | generate site pages (+ manifest + examples index) and build/serve/nav-check |
| `docs-sdk` | regenerate ONLY the committed `docs/sdk.md` / `docs/sdk-api.md` snapshots (fast) |
| `docs-linkcheck` | `tooling/check_doc_links.py` — broken relative links in tracked Markdown |

| `disclaimer-check` | `tooling/check_disclaimers.py` — rule-5 frontmatter on AI-authored docs |
| `package-check` | `tooling/check_package_readiness.py` (advisory; NOT in `check`) |
| `mcp` / `live` | run the MCP server / the local live-session web UI (`make live LIVE_PORT=8790`) |
| `corpus` / `corpus-check` / `corpus-ui` | fetch / verify / re-render the expressiveness corpus |
| `viewer-build` / `viewer-test` | JS viewer bundle build / node coverage |
| `docker-build` / `docker-mcp` / `docker-shell` / `docker-fonts` | font-rich runtime image (below) |
| `sync` / `lint` / `clean` | uv venv refresh / ruff (non-gating) / remove generated output |

## Tooling entry points (direct invocation)

All are `uv run python tooling/<script>.py …`. Gate convention: exit `0` on
pass, non-zero on failure; generators pair a write mode with `--check`
(fail-if-stale, write nothing).

| Script | Invocation / notes |
|---|---|
| `validate.py` | `validate.py doc.fg.yaml [...] [--strict] [--quiet]` — exit 0 no errors, 1 errors, 2 load failure. Codes: [docs/error-codes.md](docs/error-codes.md) |
| `codemod.py` | `codemod.py doc.fg.json --in-place [--normalize-aliases] [--bump]` — migrate legacy docs to HEAD |
| `render_fixtures.py` | `[paths|--all] [--out DIR] [--max-pages N] [--check-overflow] [--real-metrics] [--list]` — dependency-free SVG proxy |
| `render_chromium.py` | SVG→PNG raster via Playwright Chromium (`--group browser`) |
| `render_pdf.py` | `[paths|--all|--single FILE] [--out DIR] [--real-metrics]` — SVG pages → one vector PDF (`--group pdfout`) |
| `render_latex.py` | `--all` — FrameGraph → LaTeX/TikZ (+ PDF when lualatex exists) |
| `render_fg_doc.py` | `render_fg_doc.py <yml> <asset_dir> <outdir> <montage.png>` — matplotlib sanity proxy (`--group render`) |
| `render_golden.py` | `[--update] [--tolerance F] [--strict]` — b1/ oracle golden lock |
| `pdf_to_framegraph_yml.py` | `input.pdf output.fg.yaml [--text-mode spans]` (`--group pdf`) |
| `vectorize_image.py` | raster → traced FrameGraph objects (CLI over `framegraph.vision`) |
| `build_schema.py` (in `docs/schema/`) | `[--check] [doc-to-validate]` — models → JSON schema |
| `gen_status.py` | `[--check]` — validator → `FIXTURE-STATUS.md` |
| `gen_docs.py` | `[--check] [--sdk]` — docs-site pages + committed SDK snapshots |
| `gen_capability_manifest.py` | `[--check]` — live-tree introspection → `docs/capability-manifest.json` (core/sdk/mcp status per capability) |
| `gen_examples_index.py` | `[--check]` — tracked `static/examples/*.py` docstrings → `docs/examples.md` |
| `check_grammar_sync.py` | `[--strict] [--quiet]` — EBNF ⇄ models drift |
| `check_spec_sync.py` | `[--quiet]` — spec prose ⇄ model discriminators |
| `check_accessibility.py` | `<docs…> [--quiet]` — page `reading_order` integrity, alt warnings |
| `check_doc_links.py` / `check_disclaimers.py` | docs gates (no args) |
| `check_package_readiness.py` | package-emit readiness report (advisory) |
| `fetch_corpus.py` / `fetch_book_corpus.py` | `[--check]` — corpus download/verify |
| `install_fonts.py` | font provisioning used by the Docker image |

## Tests

```bash
uv run pytest -q                       # full suite (testpaths = tests/)
uv run pytest tests/test_head.py -q    # focused file
```

- The root `conftest.py` puts the repo root, `src/`, `docs/`, `tooling/`, and `docs/schema/` on
  `sys.path` — new test files need no bootstrap. `import framegraph` resolves
  the **package**; for the authoritative model module use the `models_fg`
  fixture (see `conftest.py` for the shadow-module rule).
- Vision/raster tests `importorskip` their optional deps and skip cleanly in a
  base venv.

## MCP server

```bash
uv sync --group mcp
uv run --group mcp python -m framegraph.mcp     # or: make mcp   (stdio transport)
make live                                       # web UI over the same functions
```

Tool surface, prompts, and session resources are enumerated live in
[docs/capability-manifest.json](docs/capability-manifest.json) (`mcp` section);
usage guidance is the `framegraph_guide` prompt. Session artifacts:
`framegraph://session/<id>/{document.yaml,page/<n>.svg,page/<n>.png,diagnostics.json,workspace.json}`.

## Docker runtime (fonts + full toolchain)

The canonical SDK/MCP runtime for font-faithful rendering (~5k font families):

```bash
make docker-build          # ARGS='--build-arg FONTS_APT_WILDCARD=1' for the full set
make docker-mcp            # MCP server (stdio) from the container
make docker-shell          # interactive toolchain shell
make docker-fonts          # list baked-in font families
docker run --rm frameforge version   # freshness: package + models HEAD_VERSION + build stamp
```

The image bakes the tree at build time — **rebuild after updating the repo**
(`make docker-build`), and use the `version` verb to detect skew. A stale image
silently serves an old toolchain (missing tools, old schema).

`docker/mcp.docker.json` is the client wiring for *any* codebase: the consuming
project mounts read-only at `/workspace` (reference its files as
`/workspace/<path>` in tool calls), session artifacts persist on the
`framegraph-work` volume, and SDK clients written with a bare name land in
`/work/clients` (persistent). Full guide: `skills/framegraph-mcp-docker/`.
`FRAMEGRAPH_CHROMIUM_NO_SANDBOX=1` is needed for in-container Chromium raster
(baked into the image).

## Fixture workflow

1. Author `tests/fixtures/<name>.fg.yaml` (HEAD-conformant; legacy docs go through
   `codemod.py` first).
2. Reference it from a test or gate — `tests/fixtures/README.md` rule: if no test
   references it, it does not belong.
3. `make validate overflow` (structure + text-fit), then `make status` to
   regenerate `FIXTURE-STATUS.md` and commit both.
4. `tests/fixtures/b1/` is the frozen pre-codemod oracle — never edit; its renders
   are pinned by `make golden-check` (re-pin intentional changes with
   `make golden`).

## Generated-artifact rule

Never hand-edit generated outputs (`docs/schema/framegraph-v2.schema.json`,
`FIXTURE-STATUS.md`, `docs/sdk*.md`, `docs/capability-manifest.json`,
`docs/examples.md`): edit the source or generator,
rerun the paired make target, and commit the refreshed output. Check any file
for `__file_meta__` / FLAM frontmatter before editing (see CLAUDE.md).

[↑ Back to root README](README.md)
