---
name: frameforge-runtime
description: >-
  Operate the FrameForge runtime that this plugin bundles — the containerised
  MCP server providing SDK authoring, rendering, visual QA and raster→vector
  reconstruction. Use when a frameforge tool fails with file-not-found on a
  path that exists on the host, when rendered output loses its fonts, when the
  tool list looks smaller than the documentation claims, when the server will
  not start, or when a rendered artifact has to be pulled out of the session.
  Covers the /workspace path convention, artifact retrieval, persistent SDK
  clients, the version freshness handshake, and plugin configuration.
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-23"
---

# FrameForge runtime — operating guide

The plugin ships no Python. It ships a launcher that spawns the canonical
FrameForge image, which carries the full SDK and MCP toolchain, every render
lane (SVG/cairo, Chromium PNG, PDF, LaTeX/TikZ) and thousands of font
families. One container per session, stdio JSON-RPC, torn down on exit.

The image is the runtime for a reason: renderers resolve `font_family` **by
name** through the OS font stack, so a family the host lacks silently degrades
to a generic serif or sans. Fidelity is bounded by installed faces, and the
image is how that bound gets raised.

## Tool names are plugin-scoped

Tools arrive as `mcp__plugin_frameforge_frameforge__<tool>` — plugin name,
then server name. Hook matchers and `if` conditions written against the bare
server key never fire. The scoped form is also what `server` fields want as
`plugin:frameforge:frameforge`.

## The one rule that prevents every file-not-found

Host paths do not exist inside the container. The project is mounted
read-only at `/workspace`, so reference project files as
`/workspace/<path-relative-to-project-root>` in every tool call that takes a
path — `propose_from_image`, `propose_from_document`, `propose_from_svg`,
`vectorize_image`, `measure_image`, `compare_images`, and the rest:

```
propose_from_image  path=/workspace/design/mockup.png
```

A host path such as `/home/you/project/design/mockup.png` fails, and so does
anything outside the mounted roots — the server confines path reads to
`/workspace`, `/work`, `/app` (plus a publish directory when configured) so a
prompt cannot steer it into arbitrary reads.

## Getting artifacts out

Rendered pages, YAML and diagnostics live in the session, not on your disk.
Retrieve them MCP-natively with `get_session_resource` and a
`frameforge://session/<id>/...` URI — `page/1.svg`, `document.yaml`,
`diagnostics.json` — which returns the content inline.

For durable output, set the plugin's **Publish target** option to an absolute
host path. It is mounted writable at `/publish` with
`FRAMEFORGE_MCP_PUBLISH_ROOT` pointing at it, so finished artifacts land on your
disk. Left at its default it is a Docker named volume — publishing still works,
the files just stay inside Docker.

## Two usage models

The plugin serves both a per-project and a host-wide workflow, decided by two
settings:

- **Per-project** — Shared library and Publish target stay at their default
  named volumes. The current project at `/workspace` is the input.
- **Host-wide** — Shared library points at a host folder of reusable assets
  (mounted read-only at `/library`, present in *every* project) and Publish
  target points at a host output folder. This is the setup for driving
  FrameForge as an asset generator across many contexts. `/workspace` is still
  mounted, so the shared library is additive, not a replacement.

Reference shared assets by their `/library` path — `/library/logos/mark.svg` —
exactly as project files use `/workspace`.

Bulk export without MCP:

```bash
docker run --rm -v frameforge-work:/work -v "$PWD:/out" \
  ghcr.io/pedroanisio/frameforge:2.6.0 \
  bash -c 'cp -r /work/sessions/<session-id> /out/'
```

## Persistent SDK clients

`write_sdk_client` with a bare filename (`poster.py`) writes under
`/work/clients` on the named volume — it survives container restarts and is
listed by `list_sdk_clients` in later sessions. The in-image cookbook under
`static/examples/` stays readable and editable by explicit path, but those
edits die with the container layer.

## Freshness handshake

The image bakes the toolchain at build time, so a stale tag silently serves an
old one. The symptom is a tool list shorter than the documentation describes,
or version skew in validation output.

```bash
docker run --rm ghcr.io/pedroanisio/frameforge:2.6.0 version
```

Once connected, `describe_capabilities` answers the same question without
leaving MCP. On skew, change the plugin's **Runtime image** option to the tag
you want and restart the client — the launcher pulls any tag it does not
already have locally.

## Configuration

Four options, set when the plugin is enabled and editable later through
`/plugin`:

| Option | Effect |
|---|---|
| Runtime image | The tag that runs. Point it at a locally built `frameforge` image to test an unreleased build. |
| Session volume | Named volume holding sessions and written SDK clients. Change it to isolate projects from one another. |
| Shared library | Read-only root mounted at `/library` in every project. Set it to a host path holding brand assets, logos and templates to use FrameForge host-wide instead of per-project. |
| Publish target | Mounted writable at `/publish`. A named volume by default; set an absolute host path to have finished artifacts land in your own filesystem. |

The plugin names the Docker CLI directly rather than running a wrapper script,
so the same manifest works on Windows, macOS and Linux. On Windows, see
[the Windows setup guide](https://github.com/pedroanisio/frameforge/blob/main/docs/plugin-windows-setup.md)
— path handling is the one place it differs.

## Troubleshooting

| Symptom | Cause → fix |
|---|---|
| Server never connects, no output | Docker daemon down, or the first pull is still running — the full image is several GB. Check the client's MCP logs for the launcher's stderr. |
| `file not found` on a path that exists on the host | A host path was used instead of `/workspace/...` |
| `input path is outside the allowed FRAMEFORGE_MCP_INPUT_ROOTS` | The file sits outside the mounted roots — move it into the project, or configure a publish directory |
| Fonts collapse to a generic sans | The family is not in the image. `docker run --rm <image> fonts \| grep -i <family>` to confirm, then pick a face that exists or extend the image |
| Tool list smaller than documented | Stale image tag — run the freshness handshake |
| A client written last session is gone | It was written by explicit repo path, not a bare name, so it lived in the ephemeral container layer |
