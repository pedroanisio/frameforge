"""Root pytest bootstrap for the FrameGraph test suite.

Centralizes the ``sys.path`` setup that every test file used to hand-copy, so
new test files need zero boilerplate for the common imports:

- repo root        → ``import framegraph`` resolves the *package*
                     (``framegraph/`` — rendering, sdk, mcp, vision, coach, live)
- ``tooling/``     → ``import validate``, ``import codemod``, ``import gen_status``, …
- ``schema/``      → ``import build_schema``

The shadow-module rule (READ THIS BEFORE WRITING A NEW BOOTSTRAP)
-----------------------------------------------------------------
The repository deliberately has BOTH a package named ``framegraph`` (the
directory ``framegraph/``) and the authoritative Pydantic model module at
``models/framegraph.py``. Only one of them can own ``sys.modules["framegraph"]``
at a time, which is why older test files carry two *opposite* five-line dances:

- a test that needs the **package** deletes the cached name when it is NOT a
  package (``not hasattr(mod, "__path__")``);
- a test that needs the **models module** deletes the cached name when it IS a
  package (``hasattr(mod, "__path__")``), after putting ``models/`` first on
  ``sys.path``.

This conftest intentionally does NOT put ``models/`` on ``sys.path``: the
package is the default resolution. New tests that need the authoritative model
module should use the ``models_fg`` fixture below (or call
``framegraph.sdk.model.model_module()`` directly) — it loads
``models/framegraph.py`` under the ``models`` namespace without shadowing the
package, so no dance is required in either direction.

Existing test files keep their local bootstraps (they are additive and
idempotent next to this one); do not copy them into new files.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))

# Insert in reverse priority so the final order is: ROOT, tooling/, schema/.
for _rel in ("schema", "tooling", ""):
    _path = os.path.join(ROOT, _rel) if _rel else ROOT
    if _path not in sys.path:
        sys.path.insert(0, _path)


@pytest.fixture(scope="session")
def repo_root() -> str:
    """Absolute path of the repository root."""
    return ROOT


@pytest.fixture(scope="session")
def models_fg():
    """The authoritative model module (``models/framegraph.py``), loaded via the
    SDK's non-shadowing loader — safe to use alongside the ``framegraph`` package."""
    from framegraph.sdk.model import model_module

    return model_module()
