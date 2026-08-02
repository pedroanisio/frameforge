"""Suite-wide configuration.

The input-root declaration below is not a workaround: it is the same
configuration step a real deployment has to perform since `frameforge-mcp` 2.0.0,
made explicit in one place instead of scattered through every test that feeds a
tool a fixture written under pytest's temp directory.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _declare_test_input_roots(tmp_path_factory):
    """Let the suite read the fixtures it writes under pytest's temp directory.

    Since `frameforge-mcp` 2.0.0 the propose/measure/font-closure tools are
    confined to the input roots (the session root, the working directory, and the
    repository) unless ``FRAMEFORGE_MCP_INPUT_ROOTS`` says otherwise — the
    confused-deputy fix, where an agent steered by a poisoned document could
    previously ask a propose tool for `~/.ssh/id_rsa`. Test fixtures live under
    pytest's ``tmp_path`` base, which is none of those roots, so the suite
    declares it exactly as a deployment declares the directory its source images
    live in.

    Kept deliberately narrow: the temp base plus the working directory, never
    ``*``. A suite that opted out of confinement entirely could not notice if the
    confinement broke — and this repo has its own posture gate
    (`tests/test_mcp_security_posture.py`) that overrides this to exercise the
    real default.
    """
    roots = [str(tmp_path_factory.getbasetemp()), os.getcwd()]
    previous = os.environ.get("FRAMEFORGE_MCP_INPUT_ROOTS")
    os.environ["FRAMEFORGE_MCP_INPUT_ROOTS"] = os.pathsep.join(roots)
    yield
    if previous is None:
        os.environ.pop("FRAMEFORGE_MCP_INPUT_ROOTS", None)
    else:
        os.environ["FRAMEFORGE_MCP_INPUT_ROOTS"] = previous
