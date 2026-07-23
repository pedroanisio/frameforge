"""Claude Code plugin/marketplace contract — regression gate.

FrameForge ships as a Claude Code plugin: ``.claude-plugin/marketplace.json`` at
the repo root catalogs it, and ``plugin/`` holds the plugin itself, fetched by
the marketplace as a ``git-subdir`` sparse checkout. This gate pins the parts
that break silently:

1. version parity — plugin manifest, marketplace manifest and the packaged
   version move together, since a stale pin means installed users never see an
   update (Claude Code only re-fetches when the pinned version string changes);
2. the plugin is self-contained — an installed plugin is copied into a cache and
   cannot read anything outside its own root, so a component path that escapes
   ``plugin/`` resolves to nothing at runtime;
3. the launcher's stdio contract — stdout carries JSON-RPC only, so every
   diagnostic must be redirected to stderr;
4. the skill mirror stays in sync with the canonical ``skills/`` copy.

Pure text/JSON assertions — no docker daemon and no network, so the gate runs
everywhere ``make check`` runs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 has no stdlib tomllib
    import tomli as tomllib  # type: ignore[no-redefine]

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugin"
PLUGIN_MANIFEST = json.loads(
    (PLUGIN_DIR / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
)
MARKETPLACE = json.loads(
    (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
)
LAUNCHER_PATH = PLUGIN_DIR / "bin" / "frameforge-mcp"
LAUNCHER = LAUNCHER_PATH.read_text(encoding="utf-8")
PLUGIN_MCP = json.loads((PLUGIN_DIR / ".mcp.json").read_text(encoding="utf-8"))
PACKAGE_VERSION = tomllib.loads(
    (ROOT / "pyproject.toml").read_text(encoding="utf-8")
)["project"]["version"]

MARKET_ENTRY = next(p for p in MARKETPLACE["plugins"] if p["name"] == "frameforge")


# ── 1. version parity ─────────────────────────────────────────────────────


def test_plugin_version_tracks_the_package() -> None:
    assert PLUGIN_MANIFEST["version"] == PACKAGE_VERSION, (
        "plugin/.claude-plugin/plugin.json version must match pyproject; an "
        "unbumped pin means installed users never receive the update"
    )


def test_marketplace_version_tracks_the_package() -> None:
    assert MARKETPLACE["version"] == PACKAGE_VERSION


def test_default_runtime_image_is_pinned_to_the_package_version() -> None:
    default = PLUGIN_MANIFEST["userConfig"]["image"]["default"]
    assert default.endswith(f":{PACKAGE_VERSION}"), (
        f"default runtime image {default!r} must pin the released tag, not a "
        "floating one — a stale image silently serves an old toolchain"
    )


# ── 2. self-containment ───────────────────────────────────────────────────


def test_marketplace_fetches_the_plugin_subdirectory() -> None:
    source = MARKET_ENTRY["source"]
    assert source["source"] == "git-subdir"
    assert source["path"] == "plugin"


def test_no_component_path_escapes_the_plugin_root() -> None:
    """An installed plugin is copied to a cache; ``../`` resolves to nothing."""
    component_fields = (
        "skills",
        "commands",
        "agents",
        "hooks",
        "mcpServers",
        "outputStyles",
        "lspServers",
    )
    for field in component_fields:
        value = PLUGIN_MANIFEST.get(field)
        paths = [value] if isinstance(value, str) else (value or [])
        for path in paths:
            if isinstance(path, str):
                assert ".." not in path, f"{field} path {path!r} escapes the plugin root"


def test_every_plugin_file_is_tracked() -> None:
    """A file present on disk but ignored by git publishes as an empty hole.

    ``.gitignore`` carries a bare ``.mcp.json`` rule for local client config,
    which also matches ``plugin/.mcp.json`` — the plugin's server declaration.
    Nothing in a working tree notices: the file is right there, every test that
    reads it passes, and the published plugin has no MCP server.
    """
    import subprocess
    import sys

    sys.path.insert(0, str(ROOT / "tooling"))
    import tracked_files

    on_disk = {
        p.relative_to(ROOT).as_posix()
        for p in PLUGIN_DIR.rglob("*")
        if p.is_file()
    }
    tracked = set(tracked_files.tracked_paths(ROOT, "plugin"))
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", *sorted(on_disk)],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout.split()
    assert not ignored, f"plugin files git would drop on publish: {ignored}"
    untracked = on_disk - tracked
    assert not untracked, f"plugin files not staged or committed: {sorted(untracked)}"


def test_plugin_tree_contains_no_symlinks() -> None:
    """A ``git-subdir`` checkout fetches only ``plugin/``, so a symlink pointing
    at a sibling directory in this repo has no target to resolve after install."""
    escaping = [
        p.relative_to(ROOT).as_posix()
        for p in PLUGIN_DIR.rglob("*")
        if p.is_symlink()
    ]
    assert not escaping, f"symlinks are unresolvable after a sparse install: {escaping}"


# ── 3. launcher stdio contract ────────────────────────────────────────────


def test_launcher_is_executable() -> None:
    assert LAUNCHER_PATH.stat().st_mode & 0o111, "launcher must be executable"


def test_launcher_keeps_stdout_clean() -> None:
    """stdout is the JSON-RPC stream; one stray line corrupts the session."""
    emitters = re.findall(r"^\s*(?:printf|echo)\b.*$", LAUNCHER, flags=re.MULTILINE)
    for line in emitters:
        assert ">&2" in line, f"launcher writes to stdout: {line.strip()!r}"
    assert "docker pull" in LAUNCHER and re.search(r"docker pull[^\n]*>&2", LAUNCHER), (
        "docker pull progress must be redirected to stderr"
    )


def test_launcher_confines_reads_to_the_mounted_roots() -> None:
    assert "FRAMEFORGE_MCP_INPUT_ROOTS" in LAUNCHER
    assert ":ro" in LAUNCHER, "the consuming project must be mounted read-only"


def test_mcp_command_is_an_executable_every_platform_can_spawn() -> None:
    """Windows cannot run a shebang script.

    Native Windows has no shebang support: an extensionless file with
    ``#!/usr/bin/env bash`` is not spawnable, and PATHEXT resolution finds
    nothing. Naming a real executable — the docker CLI, present as ``docker.exe``
    on Windows and ``docker`` elsewhere — is what makes one manifest work on
    Windows, macOS and Linux without a per-platform code path.
    """
    server = PLUGIN_MCP["mcpServers"]["frameforge"]
    assert server["type"] == "stdio"
    assert server["command"] == "docker", (
        "the MCP command must be a real cross-platform executable, not a script "
        "the host has to interpret"
    )
    assert not server["command"].startswith("${CLAUDE_PLUGIN_ROOT}")


def test_mcp_args_mount_the_project_read_only() -> None:
    args = PLUGIN_MCP["mcpServers"]["frameforge"]["args"]
    assert "${CLAUDE_PROJECT_DIR}:/workspace:ro" in args, (
        "the consuming project must be mounted read-only at /workspace"
    )


def test_mcp_args_confine_reads_to_the_mounted_roots() -> None:
    args = PLUGIN_MCP["mcpServers"]["frameforge"]["args"]
    roots = next(a for a in args if a.startswith("FRAMEFORGE_MCP_INPUT_ROOTS="))
    declared = set(roots.split("=", 1)[1].split(":"))
    mounted = {a.split(":")[-2] for a in args if a.count(":") >= 2 and a.startswith(("$", "frameforge"))}
    assert mounted <= declared | {"ro"}, (
        f"every mount must appear in the input roots; {mounted - declared} does not"
    )


def test_no_mount_argument_can_collapse_when_a_setting_is_blank() -> None:
    """A ``-v :/publish`` from an empty setting is a docker parse error.

    Every substituted mount therefore needs a non-empty default, which is why
    the publish target defaults to a named volume rather than an optional host
    directory.
    """
    for key, spec in PLUGIN_MANIFEST["userConfig"].items():
        if any(f"${{user_config.{key}}}:" in a for a in PLUGIN_MCP["mcpServers"]["frameforge"]["args"]):
            assert spec.get("default"), f"userConfig.{key} is used in a mount and needs a default"


def test_every_user_config_key_reaches_the_launcher() -> None:
    declared = set(PLUGIN_MANIFEST["userConfig"])
    referenced = set(re.findall(r"\$\{user_config\.(\w+)\}", json.dumps(PLUGIN_MCP)))
    assert declared == referenced, (
        f"userConfig keys not wired into .mcp.json: {declared ^ referenced}"
    )


# ── 4. skill mirror ───────────────────────────────────────────────────────


def test_mirrored_skill_matches_the_canonical_copy() -> None:
    canonical = ROOT / "skills" / "typeface-and-colour"
    mirrored = PLUGIN_DIR / "skills" / "typeface-and-colour"
    canonical_files = sorted(p.relative_to(canonical) for p in canonical.rglob("*") if p.is_file())
    mirrored_files = sorted(p.relative_to(mirrored) for p in mirrored.rglob("*") if p.is_file())
    assert canonical_files == mirrored_files, "run `make plugin-sync`"
    for rel in canonical_files:
        assert (canonical / rel).read_bytes() == (mirrored / rel).read_bytes(), (
            f"{rel} has drifted from skills/typeface-and-colour — run `make plugin-sync`"
        )


def test_runtime_skill_documents_the_scoped_tool_namespace() -> None:
    skill = (PLUGIN_DIR / "skills" / "frameforge-runtime" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "mcp__plugin_frameforge_frameforge__" in skill, (
        "plugin-provided tools are namespaced; hook matchers written against the "
        "bare server key never fire, so the skill must state the scoped form"
    )
