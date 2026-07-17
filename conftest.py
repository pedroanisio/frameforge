"""Root pytest bootstrap for the FrameForge test suite.

Centralizes the ``sys.path`` setup that every test file used to hand-copy, so
new test files need zero boilerplate for the common imports:

- ``src/``          → ``import frameforge`` resolves the package
                      (``src/frameforge/`` — model, rendering, sdk, mcp, vision,
                      coach, live)
- ``tooling/``      → ``import validate``, ``import codemod``, ``import gen_status``, …
- ``docs/schema/``  → ``import build_schema``

The shadow-module rule (history, and the invariant that replaced it)
--------------------------------------------------------------------
Until 2.5.0 the repository had BOTH a package named ``frameforge``
(``src/frameforge/``) and the authoritative Pydantic model module at
``docs/models/frameforge.py`` — two owners for one ``sys.modules`` name, which
forced every consumer into order-dependent "shadow dance" bootstraps. 2.5.0
moved the model INTO the package as ``frameforge.model``, so the name now has
exactly one owner and no dance exists in either direction. The invariant that
replaces the rule: nothing may ever register a module other than the package
under ``sys.modules["frameforge"]`` (gated by
``tests/test_module_shadow_regression.py`` and the package-readiness checker).

Tests that need the authoritative model module use the ``models_fg`` fixture
below (or call ``frameforge.sdk.model.model_module()`` directly).
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))

# Insert in reverse priority so the final order is:
# ROOT (the `tooling` namespace pkg), src/, tooling/, docs/schema/.
for _rel in ("docs/schema", "tooling", "src", ""):
    _path = os.path.join(ROOT, *_rel.split("/")) if _rel else ROOT
    if _path not in sys.path:
        sys.path.insert(0, _path)


@pytest.fixture(scope="session")
def repo_root() -> str:
    """Absolute path of the repository root."""
    return ROOT


@pytest.fixture(scope="session")
def models_fg():
    """The authoritative model module (``frameforge.model``), via the SDK's
    accessor."""
    from frameforge.sdk.model import model_module

    return model_module()
