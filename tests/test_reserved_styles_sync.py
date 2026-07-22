#!/usr/bin/env python3
"""Reserved style names: ONE constant, every surface agrees.

Drift-risk-map CRITICAL #2: the flow renderer consumed five reserved style
names (`body`, `caption`, `code`, `toc`, `toc_title`) as inline string
literals, while the spec, the MCP guide, and `describe_capabilities`
documented only two — five hand-written copies, no constant, no equality
test. Pinned here:

  * `RESERVED_STYLES` (rendering domain) is the single source of truth;
  * every reserved-style literal in the renderer source is a key of it
    (grep-based, like the existing doc-drift guards) — and vice versa;
  * `describe_capabilities("style")` exports exactly its keys;
  * the spec source (§5.2.2) and the MCP guide name every key.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.domain.services.text_style_resolver import (  # noqa: E402
    RESERVED_STYLES,
)

RENDERER = os.path.join(ROOT, "src", "frameforge", "rendering", "application", "renderer.py")
RESOLVER = os.path.join(ROOT, "src", "frameforge", "rendering", "domain", "services",
                        "text_style_resolver.py")
SPEC_SRC = os.path.join(ROOT, "docs", "spec", "frameforge-v2-spec.md")
GUIDE = os.path.join(ROOT, "src", "frameforge", "mcp", "guide.py")

EXPECTED = {"body", "caption", "code", "toc", "toc_title"}


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def test_constant_carries_the_five_known_names_with_roles():
    assert set(RESERVED_STYLES) == EXPECTED
    for name, role in RESERVED_STYLES.items():
        assert isinstance(role, str) and len(role) > 10, f"{name} needs a real role line"


def test_every_renderer_reserved_literal_is_in_the_constant():
    """Grep the style-resolution helpers' call sites: styled('x'), named('x'),
    defined('x'), text_style('x') — every literal must be a documented key."""
    src = _read(RENDERER)
    used = set()
    for helper in ("styled", "named", "defined", "text_style"):
        used |= set(re.findall(rf'\b{helper}\(\s*"([a-z_]+)"', src))
    assert used, "the grep matched nothing — helper names changed? update this test"
    unknown = used - set(RESERVED_STYLES)
    assert not unknown, (
        f"renderer consumes reserved style name(s) {sorted(unknown)} that are "
        "not in RESERVED_STYLES — add them (with a role) so the spec/guide/"
        "discovery mirrors update too")


def test_every_constant_key_is_actually_consumed():
    src = _read(RENDERER) + _read(RESOLVER)
    for name in RESERVED_STYLES:
        assert f'"{name}"' in src, (
            f"RESERVED_STYLES documents {name!r} but no renderer/resolver site "
            "consumes it — stale entry?")


def test_discovery_exports_exactly_the_constant():
    from frameforge.mcp.discovery import describe_capabilities
    result = describe_capabilities("style")
    reserved = result.get("reserved_styles")
    assert isinstance(reserved, dict), "style topic must export reserved_styles"
    exported = {k for k in reserved if k != "note"}
    assert exported == set(RESERVED_STYLES), (
        f"describe_capabilities('style') exports {sorted(exported)}; "
        f"RESERVED_STYLES defines {sorted(RESERVED_STYLES)}")


def test_spec_section_names_every_reserved_style():
    spec = _read(SPEC_SRC)
    m = re.search(r"### 5\.2\.2.*?(?=\n### )", spec, re.S)
    assert m, "spec §5.2.2 heading moved — update this test"
    section = m.group(0)
    for name in RESERVED_STYLES:
        assert f"`{name}`" in section, f"spec §5.2.2 does not name reserved style `{name}`"


def test_guide_names_every_reserved_style():
    guide = _read(GUIDE)
    m = re.search(r"## Flow defaults & reserved styles.*?(?=\n## )", guide, re.S)
    assert m, "guide reserved-styles section moved — update this test"
    section = m.group(0)
    for name in RESERVED_STYLES:
        assert f"`{name}`" in section, f"MCP guide does not name reserved style `{name}`"
