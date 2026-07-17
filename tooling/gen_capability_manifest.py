#!/usr/bin/env python3
"""
gen_capability_manifest.py — generate docs/capability-manifest.json from the LIVE tree.

ADR-0002 ("the SDK is a downstream consumer of the committed core") mandates that
status tracking distinguish "in core" from "in SDK" as separate milestones per
capability. This tool emits that tracking machine-readably, built **purely by
introspection** — zero hand-maintained capability lists — so it stays correct as
the model/SDK/MCP surfaces grow:

- model unions (``VisualObject``/``Flowable``/``Inline`` discriminators, canvas
  presets, ``Style`` property count) from the authoritative model module, loaded
  read-only via the SDK's non-shadowing loader (``docs/models/frameforge.py`` stays
  the single source of truth, exactly as ``schema/build_schema.py`` treats it);
- SDK public exports from ``frameforge.sdk.__all__`` and builder-method coverage
  from the classes defined in ``frameforge.sdk.author``;
- MCP tool/prompt/resource names from the live registry (``create_server`` is
  instantiated against a recording stub, so the enumeration is the real
  ``@server.tool()`` surface, not a parallel list);
- renderer entry points from ``tooling/render_*.py`` on disk;
- validator finding codes / SDK rule_ids extracted from the validator sources.

Status semantics per capability (documented in the emitted ``semantics`` block):

- ``core``  — the model admits it (enumerated from the discriminated unions).
- ``sdk``   — a same-named public builder method exists on a class defined in
  ``frameforge.sdk.author`` (direct authoring ergonomics; raw-dict authoring is
  always possible and deliberately does not count), or the capability *is* an
  SDK export.
- ``mcp``   — reachable through the MCP surface: model capabilities are MCP-
  reachable when the registry exposes an author→render tool; MCP tools are the
  registry itself.

Usage:
    python tooling/gen_capability_manifest.py            # (re)write docs/capability-manifest.json
    python tooling/gen_capability_manifest.py --check    # exit 1 if the committed file is stale
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys
import tempfile
import typing

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "docs", "capability-manifest.json")

_AUTHOR_RENDER_TOOLS = ("run_sdk_code", "run_sdk_client", "render_frameforge_yaml")


def _ensure_package_importable() -> None:
    """Make ``import frameforge`` resolve the package (not the models module)."""
    if ROOT not in sys.path:
        sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
    shadow = sys.modules.get("frameforge")
    if shadow is not None and not hasattr(shadow, "__path__"):
        del sys.modules["frameforge"]


def _models():
    _ensure_package_importable()
    from frameforge.sdk.model import model_module

    return model_module()


# --------------------------------------------------------------------------- #
#  Model introspection                                                        #
# --------------------------------------------------------------------------- #
def _union_members(annotated):
    """Members of ``Annotated[Union[...], ...]`` or a plain ``Union``."""
    args = typing.get_args(annotated)
    if args and typing.get_origin(args[0]) is typing.Union:
        return typing.get_args(args[0])
    if typing.get_origin(annotated) is typing.Union:
        return args
    return args


def _literal_values(cls, field: str) -> list[str]:
    model_fields = getattr(cls, "model_fields", {})
    if field not in model_fields:
        return []
    annotation = model_fields[field].annotation
    return [v for v in typing.get_args(annotation) if isinstance(v, str)]


def _discriminators(union, field: str = "type") -> list[str]:
    values: list[str] = []
    for member in _union_members(union):
        for value in _literal_values(member, field):
            if value not in values:
                values.append(value)
    return values


def model_object_types() -> list[str]:
    return _discriminators(_models().VisualObject, "type")


def model_flow_types() -> list[str]:
    return _discriminators(_models().Flowable, "type")


def model_inline_kinds() -> list[str]:
    """Inline union members: typed kinds via their ``kind`` literal; structural
    members (``str``, ``Span``) via their conventional names."""
    fg = _models()
    kinds: list[str] = []
    for member in _union_members(fg.Inline):
        if member is str:
            value = "text"
        else:
            literals = _literal_values(member, "kind")
            value = literals[0] if literals else member.__name__.lower()
        if value not in kinds:
            kinds.append(value)
    return kinds


def model_canvas_presets() -> list[str]:
    return [v for v in typing.get_args(_models().PagePreset) if isinstance(v, str)]


def style_property_count() -> int:
    return len(_models().Style.model_fields)


# --------------------------------------------------------------------------- #
#  SDK introspection                                                          #
# --------------------------------------------------------------------------- #
def sdk_public_exports() -> list[str]:
    _ensure_package_importable()
    import frameforge.sdk as sdk

    return list(sdk.__all__)


def sdk_builder_methods() -> set[str]:
    """Public callables on every class *defined in* ``frameforge.sdk.author``."""
    _ensure_package_importable()
    import frameforge.sdk.author as author

    methods: set[str] = set()
    for _name, cls in inspect.getmembers(author, inspect.isclass):
        if cls.__module__ != author.__name__:
            continue
        for attr, value in vars(cls).items():
            if not attr.startswith("_") and callable(value):
                methods.add(attr)
    return methods


# --------------------------------------------------------------------------- #
#  MCP introspection (the live registry, via a recording FastMCP stand-in)    #
# --------------------------------------------------------------------------- #
class _RecordingMCP:
    """Duck-typed FastMCP stand-in: records what ``create_server`` registers."""

    def __init__(self, name: str, *args, **kwargs):
        self.name = name
        self.tools: list[str] = []
        self.prompts: list[str] = []
        self.resources: list[str] = []

    def tool(self, *args, **kwargs):
        def decorate(fn):
            self.tools.append(fn.__name__)
            return fn

        return decorate

    def prompt(self, *args, **kwargs):
        def decorate(fn):
            self.prompts.append(fn.__name__)
            return fn

        return decorate

    def resource(self, uri: str, *args, **kwargs):
        def decorate(fn):
            self.resources.append(uri)
            return fn

        return decorate


def _mcp_registry() -> _RecordingMCP:
    _ensure_package_importable()
    from frameforge.mcp.server import create_server

    with tempfile.TemporaryDirectory(prefix="fg-manifest-") as tmp:
        return create_server(
            session_root=tmp,
            structured_log_path=os.path.join(tmp, "log.jsonl"),
            fastmcp_cls=_RecordingMCP,
        )


def mcp_tool_names() -> list[str]:
    return list(_mcp_registry().tools)


# --------------------------------------------------------------------------- #
#  Renderer entry points + validator codes                                    #
# --------------------------------------------------------------------------- #
def renderer_entry_points() -> list[dict[str, str]]:
    entries = []
    for name in sorted(os.listdir(os.path.join(ROOT, "tooling"))):
        if not (name.startswith("render_") and name.endswith(".py")):
            continue
        path = os.path.join(ROOT, "tooling", name)
        summary = ""
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        match = re.search(r'"""(.*?)"""', source, re.S)
        if match:
            summary = next(
                (line.strip() for line in match.group(1).splitlines() if line.strip()), ""
            )
        entries.append({"entry_point": f"tooling/{name}", "summary": summary})
    return entries


def tooling_finding_codes() -> set[str]:
    """Every finding code the tooling validator can emit, from its source: both
    direct ``Finding("ERROR"|"WARN", "code", …)`` constructions and the local
    ``err("code", …)`` emit helpers rules define around them."""
    with open(os.path.join(ROOT, "tooling", "validate.py"), encoding="utf-8") as fh:
        source = fh.read()
    codes = set(re.findall(r'Finding\(\s*"(?:ERROR|WARN)"\s*,\s*"([^"]+)"', source))
    codes.update(re.findall(r'\berr\(\s*"([^"]+)"', source))
    return codes


def sdk_rule_ids() -> set[str]:
    """Every SDK ``rule_id`` from ``frameforge/sdk/validate.py`` (its own ids;
    tooling codes it re-surfaces via ``rule_id=f.code`` are covered above)."""
    path = os.path.join(ROOT, "src", "frameforge", "sdk", "validate.py")
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    ids = set(re.findall(r'_error\(\s*"([^"]+)"', source))
    ids.update(re.findall(r'rule_id\s*=\s*"([^"]+)"', source))
    return ids


# --------------------------------------------------------------------------- #
#  Manifest assembly                                                          #
# --------------------------------------------------------------------------- #
def build() -> dict:
    fg = _models()
    builder_methods = sdk_builder_methods()
    exports = sdk_public_exports()
    registry = _mcp_registry()
    tools = registry.tools
    render_reachable = any(t in tools for t in _AUTHOR_RENDER_TOOLS)
    code_lane = "run_sdk_code" in tools

    def cap(name: str, kind: str, core: bool, sdk: bool, mcp: bool) -> dict:
        return {"name": name, "kind": kind, "core": core, "sdk": sdk, "mcp": mcp}

    capabilities = []
    for t in model_object_types():
        capabilities.append(cap(t, "object_type", True, t in builder_methods, render_reachable))
    for t in model_flow_types():
        capabilities.append(cap(t, "flow_type", True, t in builder_methods, render_reachable))
    for k in model_inline_kinds():
        capabilities.append(cap(k, "inline_kind", True, k in builder_methods, render_reachable))
    for p in model_canvas_presets():
        # Canvas strings pass through DocumentBuilder.page(canvas=...) unmodified,
        # so SDK/MCP reachability tracks the author→render lane, not a per-preset helper.
        capabilities.append(cap(p, "canvas_preset", True, render_reachable, render_reachable))
    for e in sorted(exports):
        capabilities.append(cap(e, "sdk_export", False, True, code_lane))
    for t in sorted(tools):
        capabilities.append(cap(t, "mcp_tool", False, False, True))

    return {
        "$comment": (
            "GENERATED by tooling/gen_capability_manifest.py — do not hand-edit; "
            "run `make manifest`. Gated by tests/test_capability_manifest.py."
        ),
        "version": fg.HEAD_VERSION,
        "semantics": {
            "core": "the authoritative model (docs/models/frameforge.py) admits the capability",
            "sdk": (
                "a same-named public builder method exists on a frameforge.sdk.author "
                "class (raw-dict authoring always works and does not count), or the "
                "capability is itself a frameforge.sdk export"
            ),
            "mcp": (
                "reachable through the live MCP registry: model capabilities via an "
                "author→render tool, SDK exports via run_sdk_code, tools directly"
            ),
        },
        "model": {
            "object_types": model_object_types(),
            "flow_types": model_flow_types(),
            "inline_kinds": model_inline_kinds(),
            "canvas_presets": model_canvas_presets(),
            "style_property_count": style_property_count(),
        },
        "sdk": {"public_exports": sorted(exports)},
        "mcp": {
            "tools": sorted(tools),
            "prompts": sorted(registry.prompts),
            "resources": sorted(registry.resources),
        },
        "renderers": renderer_entry_points(),
        "validator": {
            "tooling_codes": sorted(tooling_finding_codes()),
            "sdk_rule_ids": sorted(sdk_rule_ids()),
        },
        "capabilities": capabilities,
    }


def render() -> str:
    return json.dumps(build(), indent=2, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail if docs/capability-manifest.json is stale")
    args = ap.parse_args(argv)

    text = render()
    if args.check:
        on_disk = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if on_disk != text:
            print("STALE: docs/capability-manifest.json differs from a fresh build. "
                  "Run `make manifest` and commit the result.")
            return 1
        print("OK: capability manifest is in sync with the live tree.")
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    manifest = json.loads(text)
    print(f"Wrote {os.path.relpath(OUT, ROOT)}  "
          f"({len(manifest['capabilities'])} capabilities, "
          f"{len(manifest['mcp']['tools'])} MCP tools, "
          f"{len(manifest['sdk']['public_exports'])} SDK exports)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
