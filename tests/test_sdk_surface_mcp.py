#!/usr/bin/env python3
"""SDK-surface discoverability on the MCP (gap-closure gates).

Three guarantees, drift-proof by construction:

G1 — the ENTIRE public SDK surface (``frameforge.sdk.__all__``) is enumerable
     from inside the MCP via ``describe_capabilities(topic="sdk")``, each entry
     carrying kind, signature (callables), and a one-line explanation.
G2 — every export FrameForge itself defines carries a docstring; typing aliases
     and third-party re-exports carry generated explanations instead. A new
     undocumented export fails CI by name.
G3 — (see test_mcp_guide_authority.py) the guide's tool claims are checked
     bidirectionally against the live registry.
"""
from __future__ import annotations

import inspect
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import frameforge.sdk as sdk  # noqa: E402
from frameforge.mcp.server import describe_capabilities  # noqa: E402


# --------------------------------------------------------------------------- #
#  G1 — the sdk topic enumerates the full surface, live                        #
# --------------------------------------------------------------------------- #
def test_sdk_topic_matches_package_all_exactly():
    cap = describe_capabilities(topic="sdk")
    assert cap["ok"] is True and cap["topic"] == "sdk"
    listed = {e["name"] for e in cap["exports"]}
    assert listed == set(sdk.__all__), (
        f"sdk topic drifted from __all__ — missing: {sorted(set(sdk.__all__) - listed)}; "
        f"phantom: {sorted(listed - set(sdk.__all__))}"
    )


def test_sdk_topic_entries_are_explained():
    # The sdk topic is a COMPACT index (progressive disclosure): name + kind +
    # a one-line summary. Full signatures are in docs/sdk-api.md (its own gate),
    # and every export's source docstring is guaranteed by
    # test_every_frameforge_export_has_a_docstring below. The full-signature dump
    # was 60KB — over the MCP result ceiling.
    cap = describe_capabilities(topic="sdk")
    for e in cap["exports"]:
        assert e["kind"] in {"function", "class", "module", "type_alias", "constant", "re-export"}, e
        assert isinstance(e.get("summary"), str) and e["summary"].strip(), (
            f"export {e['name']!r} has no one-line explanation on the MCP surface"
        )
    assert "docs/sdk-api.md" in cap["note"], "sdk topic must point at the full signature reference"


def test_capability_index_advertises_the_sdk_topic():
    idx = describe_capabilities()
    assert "sdk" in idx["topics"]
    assert idx["sdk_exports"] == len(sdk.__all__)


# --------------------------------------------------------------------------- #
#  G2 — every frameforge-defined export is documented at the source            #
# --------------------------------------------------------------------------- #
def test_every_frameforge_export_has_a_docstring():
    undocumented = []
    for name in sdk.__all__:
        obj = getattr(sdk, name)
        module = getattr(obj, "__module__", "") or ""
        if not (inspect.isfunction(obj) or inspect.isclass(obj) or inspect.ismodule(obj)):
            continue                      # typing aliases / instances: G1 covers them
        if inspect.ismodule(obj):
            ours = obj.__name__.startswith("frameforge")
        else:
            # frameforge.model (docs/models) is the repo's own source of truth
            ours = module.startswith("frameforge") or module == "frameforge.model"
        if not ours:
            continue                      # third-party re-exports: explained as such
        doc = inspect.getdoc(obj)
        if not doc or not doc.strip():
            undocumented.append(name)
    assert not undocumented, (
        "public SDK exports without docstrings (add one — the MCP sdk topic and "
        f"CI both surface it): {undocumented}"
    )
