"""The `ScenePainter` port must describe what the builder actually demands.

`ScenePainter` (frameforge_render.domain.ports) is the contract a rendering
backend implements to be driven by the shared builder. Its whole value is that a
new backend author can read the Protocol and know what to implement — so a
method the builder calls but the port never declares is a *lying contract*: the
new backend passes review, then crashes at render time.

These gates are drift-proof by construction. They do not hard-code a method
list; they parse the application layer with `ast` and derive what the builder
really calls, then assert the port covers it. Adding a painter call without
declaring it in the port fails here.

Distinguishing the two kinds of call:

* **required** — `self._painter.foo(...)`; every backend must supply it.
* **optional** — `getattr(self._painter, "foo", None)`; a capability the builder
  probes for and degrades gracefully without. These still belong in the port,
  documented as optional, or a backend author cannot discover them at all.

Written for the DRY/SOLID HTML-backend work: the HTML backend is being moved off
the coarse `DocumentRenderer` port onto this one, and porting against an
incomplete contract would bake the gap in.
"""
from __future__ import annotations

import ast
import glob
import inspect
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from frameforge_render.domain.ports import (  # noqa: E402
    PainterCapabilities, ScenePainter)
from frameforge_render.infrastructure.painters.svg import SvgPainter  # noqa: E402


def _render_src():
    """Directory of the installed `frameforge_render` package source.

    The engine became its own distribution on 2026-08-01; gates that read its
    source must resolve it through the module, not a path in this repository.
    """
    import frameforge_render
    return os.path.dirname(os.path.abspath(frameforge_render.__file__))


APPLICATION = os.path.join(_render_src(), "application")

#: Attribute names that hold a painter in the application layer. `self._painter`
#: is the builder's own; `ctx.painter` / `self.painter` is how the sub-renderers
#: (UML, table, dimension) reach it through `RenderContext`.
_PAINTER_ATTRS = {"_painter", "painter"}


# --------------------------------------------------------------------------- #
# Static scan of real usage                                                    #
# --------------------------------------------------------------------------- #
def _painter_usage():
    """Parse the application layer -> (required, optional, callsites).

    `required[name]` and `optional[name]` map a painter method to the modules
    that call it. `callsites[name]` records the maximum positional arity and the
    set of keyword names any call site passes, which is what the port signature
    has to be able to accept.
    """
    required: dict[str, set[str]] = {}
    optional: dict[str, set[str]] = {}
    callsites: dict[str, dict] = {}

    for path in sorted(glob.glob(os.path.join(APPLICATION, "*.py"))):
        module = os.path.basename(path)
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            # getattr(self._painter, "name", default) -> an optional capability
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == "getattr"
                    and len(node.args) >= 2
                    and isinstance(node.args[1], ast.Constant)
                    and isinstance(node.args[0], ast.Attribute)
                    and node.args[0].attr in _PAINTER_ATTRS):
                optional.setdefault(node.args[1].value, set()).add(module)

            # self._painter.name -> a hard dependency
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Attribute)
                    and node.value.attr in _PAINTER_ATTRS):
                required.setdefault(node.attr, set()).add(module)

            # ...and how it is called, so we can check the signature accepts it
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr in _PAINTER_ATTRS):
                site = callsites.setdefault(node.func.attr, {"positional": 0, "keywords": set()})
                site["positional"] = max(site["positional"], len(node.args))
                site["keywords"] |= {k.arg for k in node.keywords if k.arg}

    # A name probed via getattr is optional even if also referenced directly.
    for name in optional:
        required.pop(name, None)
    return required, optional, callsites


def _declared(protocol) -> set[str]:
    """Every public name a Protocol declares — methods and annotated attrs."""
    members = {n for n in vars(protocol) if not n.startswith("_")}
    members |= set(getattr(protocol, "__annotations__", {}))
    return members


def _port_members() -> set[str]:
    """The whole painter contract: the required core plus optional extensions."""
    return _declared(ScenePainter) | _declared(PainterCapabilities)


def _port_method(name):
    """Look a declared member up across both halves of the contract."""
    return getattr(ScenePainter, name, None) or getattr(PainterCapabilities, name, None)


REQUIRED, OPTIONAL, CALLSITES = _painter_usage()


def test_scan_finds_the_builder_calls_at_all():
    """Guard the guard: a broken scanner must not silently pass every gate."""
    assert len(REQUIRED) >= 15, f"scanner found only {len(REQUIRED)} painter calls"
    assert "rect" in REQUIRED and "text_block" in REQUIRED
    assert OPTIONAL, "scanner found no getattr-probed capabilities"


@pytest.mark.parametrize("name", sorted(REQUIRED))
def test_port_declares_every_required_painter_method(name):
    """Every `self._painter.X(...)` must be declared on `ScenePainter`."""
    assert name in _declared(ScenePainter), (
        f"the builder requires painter.{name}() (called in "
        f"{', '.join(sorted(REQUIRED[name]))}) but ScenePainter never declares it — "
        "a backend author reading the port cannot know to implement it"
    )


@pytest.mark.parametrize("name", sorted(OPTIONAL))
def test_port_declares_every_optional_painter_capability(name):
    """Capabilities probed with `getattr` are still part of the contract."""
    assert name in _port_members(), (
        f"the builder probes painter.{name} (in {', '.join(sorted(OPTIONAL[name]))}) "
        "but neither ScenePainter nor PainterCapabilities declares it — an "
        "optional capability that is not written down is undiscoverable"
    )


@pytest.mark.parametrize("name", sorted(OPTIONAL))
def test_optional_capabilities_stay_out_of_the_required_core(name):
    """Interface segregation: an optional capability must not be mandatory.

    The builder degrades gracefully without every name in `OPTIONAL`, so putting
    it on `ScenePainter` would force every backend to implement something it can
    skip. They belong on `PainterCapabilities`.
    """
    if name in getattr(ScenePainter, "__annotations__", {}):
        pytest.skip(f"{name} is a declared capability *flag*, not a method")
    assert name not in _declared(ScenePainter), (
        f"painter.{name} is probed with getattr (optional) but is declared on the "
        "required ScenePainter core — move it to PainterCapabilities"
    )


@pytest.mark.parametrize("name", sorted(CALLSITES))
def test_port_signature_accepts_every_real_call_site(name):
    """The declared signature must accept what the builder actually passes.

    This is the gate that catches a *stale* declaration: `text_block` grew
    `justify_width`/`justifies` when justified text landed, and the port never
    learned about them. A backend implementing the port signature verbatim would
    raise TypeError on the first justified paragraph.
    """
    declared = _port_method(name)
    if declared is None or not callable(declared):
        pytest.skip(f"{name} not declared as a method — covered by another gate")

    sig = inspect.signature(declared)
    params = [p for p in sig.parameters.values() if p.name != "self"]
    names = {p.name for p in params}
    site = CALLSITES[name]

    for kw in sorted(site["keywords"]):
        assert kw in names, (
            f"builder calls painter.{name}(..., {kw}=...) but the port signature "
            f"declares only {sorted(names)}"
        )

    positional = [p for p in params
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    assert len(positional) >= site["positional"], (
        f"builder calls painter.{name}() with {site['positional']} positional "
        f"arguments but the port declares only {len(positional)}"
    )


def _other_painters():
    from frameforge_render.infrastructure.painters.html import HtmlPainter
    from frameforge_render.infrastructure.painters.tikz import TikzPainter
    return {"TikzPainter": TikzPainter, "HtmlPainter": HtmlPainter}


@pytest.mark.parametrize("backend", sorted(_other_painters()))
@pytest.mark.parametrize("name", sorted(_declared(ScenePainter)))
def test_every_backend_implements_the_required_core(name, backend):
    """Every shipped backend must satisfy the required core.

    `TikzPainter` and `HtmlPainter` are the existence proof that this port is not
    SVG-only, so they are the gate that keeps it honestly backend-neutral.
    Optional capabilities are *not* checked — TikZ implements none, which is
    exactly what `PainterCapabilities` being separate is for.
    """
    painter = _other_painters()[backend]
    assert hasattr(painter, name), (
        f"ScenePainter requires {name} but {backend} lacks it — the builder "
        "would raise AttributeError the moment this backend is driven"
    )


@pytest.mark.parametrize("name", sorted(_port_members()))
def test_svg_painter_implements_the_whole_port(name):
    """The reference backend must satisfy every declared member."""
    assert hasattr(SvgPainter, name), (
        f"ScenePainter declares {name} but the reference SvgPainter lacks it"
    )


@pytest.mark.parametrize("name", sorted(_port_members()))
def test_svg_painter_signature_is_compatible_with_the_port(name):
    """A caller written against the port must be callable on the real painter.

    Every parameter the port promises has to exist on the implementation, and
    the implementation may not demand extra *required* arguments the port never
    mentions — either would break substitutability (LSP).
    """
    declared = _port_method(name)
    impl = getattr(SvgPainter, name, None)
    if not callable(declared) or not callable(impl):
        pytest.skip(f"{name} is an attribute, not a method")

    want = inspect.signature(declared).parameters
    got = inspect.signature(impl).parameters
    got_names = set(got)

    for pname, p in want.items():
        if pname == "self" or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        assert pname in got_names, (
            f"port declares {name}({pname}=...) but SvgPainter.{name} has "
            f"{sorted(got_names)}"
        )

    extra_required = [
        p.name for p in got.values()
        if p.name not in ("self",) and p.default is p.empty
        and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
        and p.name not in want
    ]
    assert not extra_required, (
        f"SvgPainter.{name} requires {extra_required}, which the port never "
        "declares — a caller written against the port would fail"
    )
