---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 (1M context) via Claude Code"
  date: "2026-07-23"
---

# FrameForge as a Claude Code plugin on Windows

## What you are setting up

FrameForge runs as a Linux container. The plugin is a manifest that tells Claude
Code to start that container and talk to it over stdio — it installs no Python,
no Node, and no compiler on your machine. So this is a Docker setup with a
plugin install at the end:

```
Claude Code  ──spawns──>  docker run  ──>  FrameForge container
   (Windows)                                (Linux, ~10 GB image)
                                                  │
                            your project  ────────┘  mounted read-only at /workspace
```

**When you are done**, asking Claude Code to build a document returns a rendered
image in the conversation.

**Budget**: a ~10 GB download and about 20 GB of free disk.

**How to use this page**: every step ends with a command and the exact result
that means "passed". Do not move to the next step until you see it. If a step
fails, its fix is right there — you should never need the troubleshooting
section unless something is genuinely unusual.

Run everything in **PowerShell** unless a step says otherwise. Open it with
`Win`+`R` → `powershell` → Enter.

---

## Step 0 · Preflight — check what you already have

Run this whole block. It changes nothing; it only reports.

```powershell
Write-Host "1. Windows build   : $([Environment]::OSVersion.Version)"
Write-Host "2. Free space on C : $([math]::Round((Get-PSDrive C).Free / 1GB, 1)) GB"
Write-Host -NoNewline "3. Claude Code     : "; claude --version
Write-Host -NoNewline "4. Docker CLI      : "; docker --version
Write-Host -NoNewline "5. Docker daemon   : "; docker version --format "{{.Server.Version}}"
Write-Host -NoNewline "6. Container mode  : "; docker info --format "{{.OSType}}"
```

Compare each line against this table. **Every row must pass before Step 4.**

| # | Line | Passes when | If it does not |
|---|---|---|---|
| 1 | Windows build | `10.0.17763` or higher | Update Windows. Claude Code needs 1809+. |
| 2 | Free space on C | `20` or more | Free up space. The image alone is ~10 GB. |
| 3 | Claude Code | prints a version number | → **Step 1** |
| 4 | Docker CLI | prints a version number | → **Step 2** |
| 5 | Docker daemon | prints a version number | Docker Desktop is not running → **Step 3** |
| 6 | Container mode | exactly `linux` | You are in Windows-container mode → **Step 3** |

Rows 5 and 6 are the two that actually bite. An error on row 5 — anything
mentioning *"cannot find the file specified"* or *"the docker daemon is not
running"* — means the CLI is installed but Docker Desktop is not started. Row 6
printing `windows` instead of `linux` means Docker Desktop is switched to
Windows containers, and a Linux image cannot run at all.

If every row passed, **skip to Step 4**.

---

## Step 1 · Install Claude Code

Only if row 3 failed.

```powershell
irm https://claude.ai/install.ps1 | iex
```

Close PowerShell, open a new one, then verify:

```powershell
claude --version
```

✅ **Pass**: prints a version such as `2.1.211 (Claude Code)`.

Git for Windows is *not* required for this plugin. The plugin runs `docker`
directly rather than a shell script, so no Bash interpreter needs to exist.

---

## Step 2 · Install Docker Desktop

Only if row 4 failed.

Download and install from
[docs.docker.com/desktop/install/windows-install](https://docs.docker.com/desktop/install/windows-install/).
Accept the WSL 2 backend when the installer offers it. Reboot if asked.

Open a new PowerShell and verify:

```powershell
docker --version
```

✅ **Pass**: prints a version such as `Docker version 27.x.x`.

---

## Step 3 · Start Docker and put it in Linux-container mode

Only if row 5 or row 6 failed.

1. Launch **Docker Desktop** from the Start menu.
2. Wait for the whale icon in the system tray to stop animating and the app to
   read **Engine running**. This takes 30–60 seconds on a cold start.
3. If row 6 printed `windows`: right-click the tray whale → **Switch to Linux
   containers…**, and wait for the restart.

Verify both at once:

```powershell
docker version --format "{{.Server.Version}}"; docker info --format "{{.OSType}}"
```

✅ **Pass**: a version number, then `linux`.

❌ If the daemon still will not start, run `wsl --status` — if it reports WSL is
not installed, run `wsl --install` from an **Administrator** PowerShell, reboot,
and start Docker Desktop again.

---

## Step 4 · Get the runtime image

Two ways. Try 4A first — it takes minutes instead of an hour. If it is not
published yet, 4B always works.

### 4A · Pull the published image

```powershell
docker pull ghcr.io/pedroanisio/frameforge:2.6.0
```

Do it now, explicitly, rather than letting the plugin trigger it later — Claude
Code shows no progress bar and a first-run pull just looks like a frozen
session.

✅ **Pass**: the pull completes. Go to the verification below.

❌ `error from registry: denied` — **the image has not been published yet.**
This is not a permissions problem on your machine and logging into GHCR will not
fix it; the registry answers `denied` rather than `not found` for a package that
does not exist. Use 4B.

❌ `no space left on device`: free space, or raise the disk limit in Docker
Desktop → **Settings → Resources → Advanced**, then re-run.

### 4B · Build the image yourself

Needs [Git for Windows](https://git-scm.com/downloads/win). Expect 30–60
minutes; it is a large build.

```powershell
git clone https://github.com/pedroanisio/frameforge
cd frameforge
docker build -t frameforge:2.6.0 .
```

For a build that finishes in roughly a third of the time, skip the
google/fonts corpus:

```powershell
docker build -t frameforge:2.6.0 --build-arg INSTALL_GOOGLE_FONTS=0 .
```

You keep every render lane — SVG, PNG, PDF, LaTeX — and the full Debian font
set, but lose thousands of Google faces. A document naming one of those falls
back to a generic sans. Fine to start with; rebuild without the flag later if
you need the range.

**If you build, set the plugin's Runtime image to `frameforge:2.6.0`** in Step 7
— the default points at the registry copy you do not have.

### Verify (either path)

```powershell
docker image inspect frameforge:2.6.0 --format "{{.Id}}"
```

Use `ghcr.io/pedroanisio/frameforge:2.6.0` as the name instead if you pulled.

✅ **Pass**: prints a `sha256:…` digest.

---

## Step 5 · Prove the container works — before Claude Code is involved

This isolates Docker problems from plugin problems. If Step 5 passes and things
break later, the fault is in the plugin wiring, not in Docker.

**5a — the runtime answers:**

```powershell
docker run --rm frameforge:2.6.0 version
```

Use `ghcr.io/pedroanisio/frameforge:2.6.0` throughout this step instead if you
pulled in 4A.

✅ **Pass**: prints the package version, the model `HEAD_VERSION`, and a build
stamp. The version should read `2.6.0`.

**5b — your project mounts correctly.** Replace the path with a real project
folder of yours:

```powershell
cd C:\Users\you\my-project
docker run --rm -v "${PWD}:/workspace:ro" frameforge:2.6.0 bash -c "ls /workspace"
```

✅ **Pass**: lists **your project's files**. That proves the exact mount the
plugin will use.

❌ Empty output, or an error mentioning `invalid mount config`: open Docker
Desktop → **Settings → Resources → File sharing** and confirm the drive is
shared, then retry.

> **Choose this folder deliberately.** Whatever folder you start Claude Code in
> becomes the read-only mount. Do **not** use your home folder
> (`C:\Users\you`) — that would expose `.ssh`, `.docker`, `.config`, and
> `AppData` to the container. Use one project directory.

---

## Step 6 · Install the plugin

```
/plugin marketplace add pedroanisio/frameforge
/plugin install frameforge@frameforge
```

Type these **inside a Claude Code session**, not in PowerShell.

✅ **Pass**: `/plugin` lists `frameforge` as installed and enabled.

❌ *marketplace not found* / *no marketplace.json*: the marketplace has not been
published to the repository's default branch yet. Nothing on your machine is
wrong — this step cannot succeed until it is. Confirm with:

```powershell
curl.exe -s -o NUL -w "%{http_code}`n" https://raw.githubusercontent.com/pedroanisio/frameforge/main/.claude-plugin/marketplace.json
```

`200` means published and you can retry. `404` means it is not published yet.

---

## Step 7 · Configure

Enabling the plugin prompts for three values. **Accept all three defaults** —
then come back and change the third only if you want files on your own disk.

| Setting | Default | Change it when |
|---|---|---|
| Runtime image | `ghcr.io/pedroanisio/frameforge:2.6.0` | **you built it yourself in 4B — set `frameforge:2.6.0`** |
| Session volume | `frameforge-work` | never, unless isolating projects from each other |
| Publish target | `frameforge-publish` | you want finished files in a Windows folder |

For the third, an absolute Windows path such as `C:\Users\you\frameforge-out`
makes finished artifacts appear there directly. Left as-is, output stays inside
Docker and you retrieve it with the `get_session_resource` tool.

Changing any setting later: `/plugin`, edit, then restart Claude Code.

---

## Step 8 · Prove the whole loop

Start Claude Code **in your project folder** (the one from Step 5b) and ask:

> Use FrameForge to build a one-page A4 document with the title
> "Hello Windows" and show me the render.

✅ **Pass**: a rendered image comes back in the conversation.

That single result proves the container started, the mount resolved, the fonts
loaded, and the raster lane works — every moving part at once. **Setup is
complete.**

---

## Step 9 · The one rule you need from here on

**Windows paths do not exist inside the container.** Your project is at
`/workspace`, so every tool call that takes a path uses a `/workspace` path:

| Instead of | Write |
|---|---|
| `C:\Users\you\my-project\design\mockup.png` | `/workspace/design/mockup.png` |
| `.\assets\logo.svg` | `/workspace/assets/logo.svg` |
| `\\server\share\brief.pdf` | copy it into the project first |

Forward slashes, always — a backslash is never correct inside the container,
even though you are on Windows. This applies to `propose_from_image`,
`propose_from_document`, `propose_from_svg`, `vectorize_image`, `measure_image`,
`compare_images`, and every other path-taking tool.

Files outside the project are refused rather than read: the server confines path
reads to the mounted roots, so a prompt cannot steer it into the rest of your
machine.

---

## Troubleshooting, keyed to the step that failed

| Symptom | Step | Cause and fix |
|---|---|---|
| `docker` not recognised | 0 row 4 | Docker Desktop not installed → Step 2 |
| `cannot find the file specified` from any docker command | 0 row 5 | Docker Desktop not running → Step 3 |
| Container mode prints `windows` | 0 row 6 | Right-click tray whale → Switch to Linux containers |
| `no space left on device` | 4 | Free space or raise the Docker disk limit; `docker system prune -a` reclaims old images |
| `error from registry: denied` on pull | 4A | The image is not published yet. Not a login problem — build it with 4B. |
| Container starts but the plugin cannot find the image | 7 | You built locally but left the Runtime image at the `ghcr.io/...` default. Set it to `frameforge:2.6.0`. |
| `ls /workspace` shows nothing | 5b | Drive not shared → Docker Desktop → Settings → Resources → File sharing |
| Version prints something older than `2.6.0` | 5a | Stale local image: `docker pull` again |
| marketplace not found | 6 | Not published yet — check the 404/200 command in Step 6 |
| Claude Code hangs on the first FrameForge request | 8 | The image is still downloading. You skipped Step 4 — run it and wait. |
| File-not-found on a path that exists | 9 | A Windows path was used instead of `/workspace/...` |
| `input path is outside the allowed FRAMEFORGE_MCP_INPUT_ROOTS` | 9 | The file is outside the project folder. Copy it in. |
| Fonts fall back to a generic sans | — | That family is not in the image. List what is: `docker run --rm frameforge:2.6.0 fonts` |
| Tool list shorter than documented | — | Stale image. Re-pull, restart Claude Code. |

---

## Appendix A · WSL instead of native Windows

Everything above assumes native Windows. If you already work inside WSL, run
Claude Code there instead — the plugin is identical, since Docker Desktop runs
the same Linux VM either way. Two differences:

1. **Enable the integration.** Docker Desktop → **Settings → Resources → WSL
   Integration** → enable your distribution. Then, *inside the WSL terminal*:

   ```bash
   docker info --format '{{.OSType}}'
   ```

   ✅ **Pass**: `linux`. If `docker` is not found, the integration is off.

2. **Keep your project on the WSL filesystem** (`/home/you/project`), not on
   `/mnt/c/...`. Files under `/mnt/c` cross the Windows/Linux boundary twice —
   once for WSL, once for the bind mount — and rendering gets noticeably slower.

Paths in Step 5b and Step 7 become Linux paths (`/home/you/project`,
`/home/you/frameforge-out`).

## Appendix B · What the plugin actually runs

The manifest resolves to one `docker run`:

```json
{
  "command": "docker",
  "args": [
    "run", "--rm", "-i",
    "-v", "${user_config.work_volume}:/work",
    "-v", "${CLAUDE_PROJECT_DIR}:/workspace:ro",
    "-v", "${user_config.publish_target}:/publish",
    "-e", "FRAMEFORGE_MCP_INPUT_ROOTS=/workspace:/work:/app:/publish",
    "-e", "FRAMEFORGE_MCP_PUBLISH_ROOT=/publish",
    "${user_config.image}"
  ]
}
```

`docker` is named directly rather than through a wrapper script because native
Windows has no shebang support: an extensionless file starting with
`#!/usr/bin/env bash` cannot be spawned there. Naming the Docker CLI —
`docker.exe` on Windows, `docker` elsewhere — is what lets one manifest serve
Windows, macOS, and Linux with no per-platform code path.

## Appendix C · Related

- [`skills/frameforge-mcp-docker/`](../skills/frameforge-mcp-docker/SKILL.md) —
  wiring the dockerized server into a project without the plugin
- [`docker/README.md`](../docker/README.md) — building the image yourself
