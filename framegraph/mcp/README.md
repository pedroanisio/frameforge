# FrameGraph MCP server

An optional [Model Context Protocol](https://modelcontextprotocol.io) adapter for
AI authoring feedback loops: a model writes Python that uses `framegraph.sdk`, the
server **validates and renders** the generated FrameGraph document, and returns the
artifacts (validation issues, SVG, and a PNG the model can actually *see*) so the
output can be verified — never trusted blind (PALS's Law).

> The MCP boundary is optional. The core SDK and renderers never import it unless
> `framegraph.mcp.create_server()` is called; its dependencies live in the `mcp`
> dependency group. See [codebase-standards.md](../../codebase-standards.md) §13.

## Run it

```bash
uv sync --group mcp                       # installs mcp[cli] + cairosvg (raster fallback)
uv run --group mcp python -m framegraph.mcp
# or:
make mcp                                  # same, over the default FastMCP transport
make live                                 # local web UI over the same session functions
```

## Tools & resources

Forward (author → render):

- `run_sdk_code` / `run_sdk_client` — run Python that builds a document, then validate + render it.
- `render_framegraph_yaml` — validate + render caller-supplied YAML directly (no Python).
- `write_sdk_client` / `read_sdk_client` / `list_sdk_clients` — edit whitelisted SDK client files.

Inverse (image / PDF → draft), needs the `vision` group:

- `propose_from_image` / `propose_from_document` — propose a **draft** document from a
  screenshot or rasterized PDF page, then round-trip it through validate + render. The
  proposal is unverified CV/VLM output; treat it as a starting point.

Sessions:

- `get_session_resource`, `list_sessions`, `cleanup_sessions`.
- Resources: `framegraph://session/{id}/document.yaml`, `…/page/{n}.svg`, `…/page/{n}.png`,
  `…/diagnostics.json`.

The `framegraph_guide` prompt returns a model-facing capability guide for the SDK.

## Visual verification (how a render is *seen*)

A vision model can only see a raster (PNG), not SVG, so the render tools rasterize to
PNG by default (`raster_png=True`) and attach it as an image content block; the SVG
stays a resource link. Rasterization uses the first backend that can run:

| Order | Backend | Group | Notes |
|---|---|---|---|
| 1 | Headless Chromium | `browser` (+ `playwright install chromium`) | Highest CSS fidelity (filters, blend modes, masks). |
| 2 | CairoSVG | `mcp` / `pdfout` | Browser-free; faithful for the vector/text/gradient core. |

Each render reports the `backend` it used. Only when **neither** backend is available
does the result carry a `render_warning` and ship SVG/diagnostics text alone — read the
warning, install a backend, and re-render.

## Failure feedback (one round-trip)

- A non-zero build puts a bounded `stderr_tail` in the model-facing summary, so the
  traceback is visible without a second fetch of the diagnostics resource.
- A schema-invalid document returns structured `validation.issues`
  (`{rule_id, severity, path, message}`) — the harness lowers the Pydantic errors into
  a `build_error.json` sidecar that the result is enriched from.

## Operational note — restart after code changes

The SDK **client** runs in a fresh per-call subprocess, but the **validate/render
pipeline runs in the long-lived MCP server process**. Edits to `framegraph/mcp/*`,
`framegraph/rendering/*`, or the models therefore **do not take effect until the server
restarts** — the running process keeps the modules it imported at start. After changing
that code, restart `make mcp` (and `make live`, which shares the same functions) to pick
it up. Use a fresh interpreter to verify pipeline changes during development rather than
the running server.

## Configuration (environment variables)

| Variable | Effect |
|---|---|
| `FRAMEGRAPH_MCP_SESSION_ROOT` | Where per-session scratch dirs/artifacts live (default: temp dir). |
| `FRAMEGRAPH_MCP_EDIT_ROOTS` | `os.pathsep`-joined roots the client-file tools may read/write (default: `examples`). |
| `FRAMEGRAPH_MCP_INPUT_ROOTS` | Confine `propose_*` inputs to these roots (unset = any readable path). |
| `FRAMEGRAPH_MCP_KEEP_ENV` | Truthy keeps secret-looking env vars in the code subprocess (default: stripped). |
| `FRAMEGRAPH_MCP_STRUCT_LOG_PATH` | Path for the JSONL structured tool log (default: under the session root). |
| `FRAMEGRAPH_MCP_RENDER_TIMEOUT` | Soft per-render wall-clock budget, seconds. |
| `FRAMEGRAPH_MCP_RENDER_MAX_PAGES` | Hard page ceiling refused before the in-process render starts. |
| `FRAMEGRAPH_MCP_RENDER_MAX_OBJECTS` | Hard object ceiling refused before rendering. |
| `FRAMEGRAPH_MCP_RASTER_MAX_PAGES` | Max pages rasterized to PNG per call. |
| `FRAMEGRAPH_MCP_RASTER_TIMEOUT` | Soft wall-clock budget for the rasterization loop, seconds. |
| `FRAMEGRAPH_MCP_MAX_INLINE_IMAGES` | Max PNGs inlined as image blocks (rest stay resource links). |

## Security posture — trusted-operator only

`run_sdk_code` / `run_sdk_client` execute caller-supplied Python in a **subprocess** with
secret-looking env vars stripped, a wall-clock timeout, and hard input ceilings. This is
**process isolation, not a security sandbox**: the code still runs with the server user's
filesystem and network access. Run the server only for local, trusted use — do not expose
it to untrusted callers.

---

[↑ Back to the project README](../../README.md)
