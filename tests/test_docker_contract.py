"""Docker/MCP consumption contract — regression gate.

Pins the container contract that lets a *foreign* codebase fully interact with
FrameForge over MCP (2026-07-02 audit findings):

1. freshness is detectable — a ``version`` entrypoint verb, an OCI version
   label wired through ``make docker-build``, and a build stamp;
2. the client wiring mounts the consuming project read-only at ``/workspace``
   and confines propose inputs to the mounted roots;
3. SDK clients written over MCP persist on the ``/work`` volume
   (``FRAMEFORGE_MCP_EDIT_ROOTS`` puts ``/work/clients`` first);
4. the installable skill documenting all of this exists and is complete.

Pure text/JSON/YAML assertions — no docker daemon required, so the gate runs
everywhere ``make check`` runs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
ENTRYPOINT = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
MCP_JSON = json.loads((ROOT / "docker" / "mcp.docker.json").read_text(encoding="utf-8"))
COMPOSE_TEXT = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
SKILL_PATH = ROOT / "skills" / "frameforge-mcp-docker" / "SKILL.md"


# ── 1. freshness ──────────────────────────────────────────────────────────


def test_dockerfile_carries_version_label_and_build_stamp() -> None:
    assert "ARG BUILD_VERSION" in DOCKERFILE
    assert "org.opencontainers.image.version" in DOCKERFILE
    assert ".build-stamp" in DOCKERFILE


def test_make_docker_build_wires_the_version_arg() -> None:
    assert "BUILD_VERSION" in MAKEFILE, "docker-build must pass the pyproject version as BUILD_VERSION"


def test_entrypoint_has_version_verb() -> None:
    assert "version)" in ENTRYPOINT
    assert "HEAD_VERSION" in ENTRYPOINT


# ── 2. foreign-codebase wiring ────────────────────────────────────────────


def _mcp_args() -> list[str]:
    return MCP_JSON["mcpServers"]["frameforge"]["args"]


def test_mcp_config_mounts_workspace_read_only() -> None:
    args = _mcp_args()
    assert any(a.endswith(":/workspace:ro") for a in args), "consuming project must mount at /workspace (ro)"
    assert "frameforge-work:/work" in args, "session volume must persist across runs"


def test_mcp_config_confines_input_roots() -> None:
    env_args = [a for a in _mcp_args() if a.startswith("FRAMEFORGE_MCP_INPUT_ROOTS=")]
    assert env_args, "propose inputs must be confined in the hardened docker wiring"
    roots = env_args[0].split("=", 1)[1].split(":")
    assert "/workspace" in roots and "/work" in roots and "/app" in roots


def test_compose_documents_the_workspace_convention() -> None:
    compose = yaml.safe_load(COMPOSE_TEXT)
    assert compose["services"]["frameforge"]["image"] == "frameforge"
    assert "/workspace" in COMPOSE_TEXT


# ── 3. persistent SDK clients ─────────────────────────────────────────────


def test_dockerfile_persists_sdk_clients_on_the_work_volume() -> None:
    assert "FRAMEFORGE_MCP_EDIT_ROOTS=/work/clients:/app/static/examples" in DOCKERFILE
    assert "mkdir -p /work/clients" in DOCKERFILE


# ── 4. the skill ──────────────────────────────────────────────────────────


def _skill_parts() -> tuple[dict, str]:
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md must open with YAML frontmatter"
    front, body = text[4:].split("\n---\n", 1)
    return yaml.safe_load(front), body


def test_skill_exists_with_complete_frontmatter() -> None:
    assert SKILL_PATH.is_file(), "skills/frameforge-mcp-docker/SKILL.md must exist"
    front, _ = _skill_parts()
    assert front["name"] == "frameforge-mcp-docker"
    assert "MCP" in front["description"]
    disclaimer = front["disclaimer"]
    assert disclaimer["notice"] and disclaimer["generated_by"] and disclaimer["date"]


def test_skill_covers_the_full_consumption_contract() -> None:
    _, body = _skill_parts()
    for needle in (
        "/workspace",          # path convention for the consuming codebase
        "get_session_resource",  # artifact retrieval without host paths
        "/work/clients",       # persistent SDK clients
        "docker build -t frameforge",  # image build
        "version",             # freshness handshake
    ):
        assert needle in body, f"skill must document {needle!r}"


# ── docs stay in step ─────────────────────────────────────────────────────


def test_agents_md_documents_freshness_and_version_verb() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "docker run --rm frameforge version" in agents
    assert "rebuild" in agents.lower()


def test_docker_readme_documents_foreign_codebase_use() -> None:
    readme = (ROOT / "docker" / "README.md").read_text(encoding="utf-8")
    assert "/workspace" in readme
    assert "get_session_resource" in readme
    assert "/work/clients" in readme


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
