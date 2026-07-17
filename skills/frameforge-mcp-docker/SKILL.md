---
name: frameforge-mcp-docker
description: >-
  Wire any codebase to the dockerized FrameForge MCP server (SDK authoring,
  rendering, visual QA, raster→vector reconstruction) with full file exchange.
  Use when a project wants to author or render FrameForge documents via MCP,
  when frameforge tools fail with file-not-found on project paths, when
  rendered output is missing fonts, or when the frameforge tool list looks
  incomplete (stale image). Covers image build, client config, the /workspace
  path convention, artifact retrieval, persistent SDK clients, and the
  version/freshness handshake.
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code"
  date: "2026-07-02"
---

# FrameForge over Docker MCP — consumption guide

The `frameforge` image is the canonical FrameForge runtime: the full SDK and
MCP toolchain, every render lane (SVG/cairo, Chromium PNG, PDF, LaTeX/TikZ),
and thousands of font families. The MCP server speaks stdio; your client
spawns one container per session. This skill makes a *foreign* codebase a
first-class consumer.

## 1. Get the image

```bash
git clone https://github.com/pedroanisio/frameforge && cd frameforge
docker build -t frameforge .          # or: make docker-build (wires the version label)
```

## 2. Wire your MCP client

Copy `docker/mcp.docker.json` into your project's MCP config (for Claude Code:
merge into `.mcp.json`). The wiring that matters:

```json
"args": [
  "run", "--rm", "-i",
  "-v", "frameforge-work:/work",
  "-v", "${PWD}:/workspace:ro",
  "-e", "FRAMEFORGE_MCP_INPUT_ROOTS=/workspace:/work:/app",
  "frameforge"
]
```

- `frameforge-work:/work` — named volume; sessions and written SDK clients
  persist across container runs.
- `${PWD}:/workspace:ro` — **your project**, read-only. Claude Code expands
  `${PWD}`; other clients: substitute the absolute project path.
- `FRAMEFORGE_MCP_INPUT_ROOTS` confines file-reading tools to the mounted
  roots (defense against confused-deputy reads).

## 3. Path convention — the one rule that prevents every file-not-found

Host paths do not exist inside the container. Reference project files as
`/workspace/<path-relative-to-your-project-root>` in every tool call that
takes a path (`propose_from_image`, `propose_from_document`,
`propose_from_svg`, `vectorize_image`, `measure_image`, `compare_images`, …):

```
propose_from_image  path=/workspace/design/mockup.png
```

## 4. Getting artifacts out

Rendered pages, YAML, and diagnostics live in the session, not on your disk.
Retrieve them MCP-natively — `get_session_resource` with a
`frameforge://session/<id>/...` URI (e.g. `page/1.svg`, `document.yaml`,
`diagnostics.json`) returns the content inline. Bulk export without MCP:

```bash
docker run --rm -v frameforge-work:/work -v "$PWD:/out" frameforge \
  bash -c 'cp -r /work/sessions/<session-id> /out/'
```

## 5. Persistent SDK clients

`write_sdk_client` with a bare filename (e.g. `poster.py`) creates the file
under `/work/clients` on the named volume — it survives container restarts
and is listed by `list_sdk_clients` in later sessions. The in-repo cookbook
(`static/examples/…`) remains readable and editable by explicit path; edits
to it do not persist across runs (the container layer is ephemeral).

## 6. Freshness handshake — do this when anything looks off

The image bakes the repo at build time; a stale image silently serves an old
toolchain (symptom: tools like `describe_capabilities` missing from the tool
list, or version skew in validation).

```bash
docker run --rm frameforge version
# package 2.3.0 / models HEAD_VERSION 2.3.0 / built 2026-07-02T...
```

Compare against your frameforge checkout; on skew, rebuild
(`make docker-build`) and restart the MCP client. Once connected, prefer the
`describe_capabilities` tool for the same check without leaving MCP.

## 7. Troubleshooting

| Symptom | Cause → fix |
|---|---|
| `file not found` on a path that exists on your host | Host path used instead of `/workspace/...` (§3) |
| `input path is outside the allowed FRAMEFORGE_MCP_INPUT_ROOTS` | File lies outside the mounts — move it into the project or extend the mount |
| Fonts collapse to a generic sans in PNG | Image built with `INSTALL_BROWSER=0`, or family missing — `docker run --rm frameforge fonts \| grep -i <family>` |
| Tool list smaller than the docs claim | Stale image (§6) |
| Client file written last session is gone | It was written by explicit repo path, not a bare name (§5) |
