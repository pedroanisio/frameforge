---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-23"
---

# FrameForge in the Claude Desktop app (and Cowork)

## Read this first — what actually works

FrameForge ships as a Claude Code *plugin*. Plugins are a Claude Code feature;
the Claude Desktop app does not load them. But the plugin is only packaging
around a container that speaks MCP over stdio — and the desktop app **can** run
a local stdio MCP server. So the same FrameForge tools are reachable in the
desktop app by registering the container directly, without the plugin.

Two honest boundaries, stated plainly:

- **Verified:** the Claude Desktop app runs local MCP servers declared in
  `claude_desktop_config.json`, and they appear in the app as Connectors with
  their tools available. This guide uses that mechanism.
- **Not independently verified:** whether the **Cowork** agent surface exposes a
  locally-registered MCP server's tools identically to a normal desktop chat.
  Cowork runs inside the desktop app and works through Connectors, so a
  local server registered here shows up in the same Connectors surface Cowork
  draws on — but confirm it appears for your Cowork sessions after Step 4 rather
  than assuming it.
- **Will not work at all:** Cowork on **web or mobile**, and **claude.ai web
  chat**. Neither can run a local Docker daemon, and web Connectors accept only
  remote (URL) MCP servers, not a local `docker run`.

If you are on Claude Code (CLI or the VS Code / JetBrains extension), use the
[plugin guide](plugin-windows-setup.md) instead — this document is only for the
desktop app.

---

## Step 0 · Prerequisites

You need the same two things the plugin needs, minus Claude Code:

1. **Docker Desktop running in Linux-container mode.** Verify:

   ```powershell
   docker version --format "{{.Server.Version}}"; docker info --format "{{.OSType}}"
   ```

   ✅ a version number, then `linux`. If not, see Steps 2–3 of the
   [plugin guide](plugin-windows-setup.md).

2. **The `frameforge:2.6.0` image present locally.** Verify:

   ```powershell
   docker image inspect frameforge:2.6.0 --format "{{.Id}}"
   ```

   ✅ a `sha256:…` digest. If missing, pull or build it per Step 4 of the
   [plugin guide](plugin-windows-setup.md).

3. **The Claude Desktop app**, updated. [claude.ai/download](https://claude.ai/download).

---

## Step 1 · Create the host folders

The desktop app is not scoped to a project the way Claude Code is, so there is
no automatic `/workspace` mount. You choose fixed folders. This is the
host-wide model by default, which is what most desktop/Cowork use is.

**Put them outside your user profile** — a OneDrive-managed or Controlled-Folder-
Access-protected profile folder is readable but not writable by Docker, and the
output mount fails with `Permission denied`. Use `C:\frameforge\...`:

```powershell
mkdir C:\frameforge\inbox   -Force
mkdir C:\frameforge\library -Force
mkdir C:\frameforge\out     -Force
```

| Folder | Mounts at | Role |
|---|---|---|
| `inbox` | `/workspace` (read-only) | drop input files here — images to trace, documents to render |
| `library` | `/library` (read-only) | reusable brand assets, logos, templates, shared across every session |
| `out` | `/publish` (writable) | finished artifacts land here |

---

## Step 2 · Open the config

In the Claude Desktop app: the **Claude menu** (menu bar, not the in-window
settings) → **Settings…** → **Developer** tab → **Edit Config**. That opens, or
creates, `claude_desktop_config.json`:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

---

## Step 3 · Add the FrameForge server

If the file already has an `mcpServers` object, add the `frameforge` key inside
it. If the file is empty, paste the whole thing.

**Windows:**

```json
{
  "mcpServers": {
    "frameforge": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "frameforge-work:/work",
        "-v", "C:\\frameforge\\inbox:/workspace:ro",
        "-v", "C:\\frameforge\\library:/library:ro",
        "-v", "C:\\frameforge\\out:/publish",
        "-e", "FRAMEFORGE_MCP_INPUT_ROOTS=/workspace:/library:/work:/app:/publish",
        "-e", "FRAMEFORGE_MCP_PUBLISH_ROOT=/publish",
        "frameforge:2.6.0"
      ]
    }
  }
}
```

**macOS:**

```json
{
  "mcpServers": {
    "frameforge": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "frameforge-work:/work",
        "-v", "/Users/you/frameforge/inbox:/workspace:ro",
        "-v", "/Users/you/frameforge/library:/library:ro",
        "-v", "/Users/you/frameforge/out:/publish",
        "-e", "FRAMEFORGE_MCP_INPUT_ROOTS=/workspace:/library:/work:/app:/publish",
        "-e", "FRAMEFORGE_MCP_PUBLISH_ROOT=/publish",
        "frameforge:2.6.0"
      ]
    }
  }
}
```

Every mount path must be **absolute** — the desktop app does not expand
variables or relative paths in this file. On Windows, backslashes must be
doubled (`C:\\frameforge\\out`) because it is JSON.

> **If you built the image under a different tag**, change the final
> `frameforge:2.6.0` argument to match. `ghcr.io/pedroanisio/frameforge:2.6.0`
> only works once that image is published; a locally built one is whatever you
> tagged it.

Save the file.

---

## Step 4 · Restart and verify

MCP servers load only at launch, so **fully quit** the desktop app (not just
close the window) and reopen it.

Then, in a conversation, open the **"Add files, connectors, and more"**
indicator at the bottom-left of the input box → **Connectors** →
**Manage connectors**. `frameforge` should be listed with its tools.

✅ **Pass:** `frameforge` appears with tools such as `run_sdk_code`,
`render_frameforge_yaml`, `vectorize_image`, and `describe_capabilities`.

Then confirm the loop end to end. Drop any PNG into `C:\frameforge\inbox`, and
ask:

> Use FrameForge to build a one-page A4 document titled "Hello Desktop" and show
> me the render.

A rendered image back means the container started, the mounts resolved, and the
render lane works.

**For Cowork specifically:** start a Cowork session and confirm `frameforge`
appears among its available connectors before relying on it — see the honest
boundary at the top of this page.

---

## Step 5 · The path rules

Same as the plugin, because it is the same container:

| To reference | Use |
|---|---|
| an input you dropped in `inbox` | `/workspace/mockup.png` |
| a shared asset | `/library/logos/mark.svg` |
| where output goes | `/publish/...` (or fetch with `get_session_resource`) |

Forward slashes inside the container, always — never a `C:\...` path in a tool
call. Anything outside the three mounted folders is refused by design.

---

## Troubleshooting

The desktop app writes per-server logs. Read them first:

- **Windows:** `%APPDATA%\Claude\logs\mcp-server-frameforge.log`
- **macOS:** `~/Library/Logs/Claude/mcp-server-frameforge.log`

| Symptom | Cause and fix |
|---|---|
| `frameforge` not in Connectors after restart | JSON syntax error (a trailing comma, an unescaped backslash), or the app was not fully quit. Validate the file and relaunch. |
| Log shows `docker: executable file not found` / `spawn docker ENOENT` | The desktop app did not inherit Docker's PATH. Replace `"command": "docker"` with the absolute path — Windows `"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe"`, macOS `"/usr/local/bin/docker"` (confirm with `where docker` / `which docker`). |
| Log shows `Cannot connect to the Docker daemon` | Docker Desktop is not running. Start it, then relaunch the app. |
| `touch: cannot touch '/publish/...': Permission denied` | The `out` folder is OneDrive- or Controlled-Folder-Access-protected. Use a path outside your profile such as `C:\frameforge\out`, or allow Docker in Windows Security → Ransomware protection → Controlled folder access. |
| `invalid mount config` / empty `/workspace` | A mount path does not exist or is not shared. Confirm the folder exists and the drive is shared under Docker Desktop → Settings → Resources → File sharing. |
| Fonts fall back to a generic sans | The family is not in the image. `docker run --rm frameforge:2.6.0 fonts` lists what is available. |

---

## How this differs from the plugin

| | Claude Code plugin | Desktop app config |
|---|---|---|
| Install | `/plugin marketplace add` | edit `claude_desktop_config.json` by hand |
| Project mount | automatic `${CLAUDE_PROJECT_DIR}` → `/workspace` | a fixed `inbox` folder you choose |
| Settings | prompted (image, library, publish) | hardcoded in the JSON |
| Updates | version-pinned via the marketplace | change the image tag and restart |
| Runs in | Claude Code CLI + IDE extensions | the Claude Desktop app |

The container, the tools, and the path conventions are identical; only the way
you register it differs.

## Related

- [Plugin on Windows](plugin-windows-setup.md) — the Claude Code path
- [`skills/frameforge-mcp-docker/`](../skills/frameforge-mcp-docker/SKILL.md) —
  the generic dockerized-MCP consumption guide
- [`docker/README.md`](../docker/README.md) — building the image
