# FrameGraph SDK / MCP — font-rich container

A Docker base image that runs the FrameGraph toolchain (SDK, renderers, and the
MCP server) with **as many fonts as we can build in**: the entire
[`google/fonts`](https://github.com/google/fonts) corpus (thousands of faces)
plus a broad Debian font set covering full Noto, CJK, Indic, Arabic, Thai,
Sinhala, Khmer, Ethiopic, and emoji.

Back to the [repo README](../README.md).

## Why fonts are the whole point

FrameGraph documents name a `font_family` as a string. Every renderer resolves
that name through the **OS font stack** — fontconfig → freetype, reached via
cairosvg/Pango and the `fc-match` metrics path in
[`font_metrics.py`](../src/framegraph/rendering/infrastructure/font_metrics.py). If a
named family is not installed, fontconfig silently substitutes a generic
serif/sans, so a deck that asks for `Fraunces` or `IBM Plex Serif` renders in
DejaVu. Render fidelity is therefore bounded by the host's installed faces. This
image removes that ceiling.

## What's inside

| Layer | Contents |
|---|---|
| Base | `python:3.13-slim-bookworm` + [uv](https://docs.astral.sh/uv/) (pinned) |
| Fonts | Full `google/fonts` corpus + Debian set from [`fonts.apt.txt`](fonts.apt.txt) |
| Render libs | libcairo2 · pango · gdk-pixbuf (cairosvg PNG lane) |
| Vision | opencv (headless) · tesseract-ocr (+ langs) for the `propose_from_*` lanes |
| Browser | Playwright Chromium (high-fidelity raster lane; cairo is the fallback) |
| Python | The full toolchain via `uv sync --all-groups` (mcp, vision, browser, render, pdf, pdfout, metrics, dev) |

## Build

```bash
docker build -t frameforge .            # or: make docker-build
```

Build args:

| Arg | Default | Effect |
|---|---|---|
| `FONTS_APT_WILDCARD` | `0` | `1` also installs **every** `fonts-*` apt package (absolute maximum; larger image) |
| `GOOGLE_FONTS_REF` | `main` | Pin the google/fonts corpus to a branch/tag/commit for a reproducible build |
| `TESSERACT_ALL` | `0` | `1` installs all tesseract OCR languages (large); default is `eng` + `osd` |
| `INSTALL_BROWSER` | `1` | `0` skips the Chromium download (cairo-only raster; smaller image) |

The build prints its font tally, e.g. `fonts: 6800 faces, 1900 families`.

## Run

The MCP server speaks **stdio**, so an MCP client spawns the container per
session:

```bash
docker run --rm -i -v framegraph-work:/work frameforge
```

Wire it into a client by replacing the `framegraph` entry in your MCP config with
[`mcp.docker.json`](mcp.docker.json). The repo's default
[`.mcp.json`](../.mcp.json) still uses the local `uv` env for development; the
container is the portable, font-complete alternative.

## Using from another codebase

Host paths do not exist inside the container, so the client wiring in
[`mcp.docker.json`](mcp.docker.json) mounts two things:

| Mount | Purpose |
|---|---|
| `framegraph-work:/work` | Named volume — session artifacts persist across runs; SDK clients written with a bare name land in `/work/clients` and survive restarts |
| `${PWD}:/workspace:ro` | **Your project**, read-only — reference its files in tool calls as `/workspace/<relative-path>` (`propose_from_image path=/workspace/design/mockup.png`) |

`FRAMEGRAPH_MCP_INPUT_ROOTS=/workspace:/work:/app` confines file-reading tools
to those roots. Retrieve rendered artifacts MCP-natively with
`get_session_resource` (`framegraph://session/<id>/page/1.svg`), or bulk-export
by mounting the volume: `docker run --rm -v framegraph-work:/work -v "$PWD:/out"
frameforge bash -c 'cp -r /work/sessions/<id> /out/'`. The installable guide for
consuming agents lives at [`skills/framegraph-mcp-docker/`](../skills/framegraph-mcp-docker/SKILL.md).

## Freshness

The image bakes the repo at build time; **rebuild after updating the repo**
(`make docker-build`). Detect skew without guessing:

```bash
docker run --rm frameforge version
# package 2.3.0 / models HEAD_VERSION 2.3.0 / built 2026-07-02T...
```

`make docker-build` stamps the OCI `org.opencontainers.image.version` label from
`pyproject.toml`; once connected over MCP, `describe_capabilities` reports the
same surface. A stale image's symptom is a shorter tool list or version skew in
validation errors.

Other entrypoint verbs (see [`entrypoint.sh`](entrypoint.sh)):

```bash
docker run --rm frameforge fonts          # list installed families
docker run --rm -it frameforge bash       # shell inside the toolchain
docker run --rm frameforge python -m framegraph.cli --list   # any command in the venv
```

## Chromium in a container

Chromium's setuid sandbox cannot initialize under the container's default
namespaces, so the image sets `FRAMEGRAPH_CHROMIUM_NO_SANDBOX=1`. The renderer
reads that (see
[`browser.py`](../src/framegraph/rendering/infrastructure/browser.py)) and launches
Chromium with `--no-sandbox --disable-dev-shm-usage`. The container boundary is
the isolation. Override the flags entirely with `FRAMEGRAPH_CHROMIUM_ARGS`
(space-separated). Locally, with neither variable set, launch behavior is
unchanged.

## Adding fonts at runtime

Bind-mount a directory of extra faces and rebuild the cache on start:

```bash
docker run --rm -i \
  -e FRAMEGRAPH_REFRESH_FONTS=1 \
  -v "$PWD/my-fonts:/usr/share/fonts/custom:ro" \
  -v framegraph-work:/work \
  frameforge
```

## Relationship to `tooling/install_fonts.py`

[`install_fonts.py`](../tooling/install_fonts.py) installs a **curated** subset of
google/fonts into a host user's font dir — the lightweight, no-Docker path. This
image is the **maximal** path: the whole corpus plus system script coverage,
baked in and cached. Use the script on a dev host; use the image for a portable,
font-complete SDK/MCP runtime.
