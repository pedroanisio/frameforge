"""Correctness + render-preservation contract for ``examples/fg_css_optimize.py``.

The optimizer promises to shrink HTML from ``frameforge_to_html.py`` *without
changing how it renders*. These tests pin that promise on real generator output
(viewBox/paint survive), and lock down the two bugs the review found: the crash
on a missing ``<style>`` block and the corruption of ``@media`` at-rules.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


opt = _load("fg_css_optimize", ROOT / "static" / "examples" / "fg_css_optimize.py")
# The HTML renderer moved into the package (the DocumentRenderer port); import it
# there rather than from the retired tooling/ script. Evict a cached non-package
# `frameforge` shadow first (conftest.py's shadow-module rule).
import sys  # noqa: E402

_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
from frameforge.rendering.infrastructure.backends import html as fgh  # noqa: E402


def _render(objects: list[dict], *, defs: dict | None = None) -> str:
    doc = {
        "dsl": "FrameForge", "version": "2.0.0", "title": "Opt",
        "pages": [{"mode": "page", "id": "p1",
                   "canvas": {"size": [600, 400], "units": "px"},
                   "layers": [{"id": "main", "z": 0, "objects": objects}]}],
    }
    if defs:
        doc["defs"] = defs
    return fgh.render_document(doc)


# --------------------------------------------------------------------------- #
# Bug fixes                                                                    #
# --------------------------------------------------------------------------- #


def test_no_style_block_does_not_crash():
    src = '<!doctype html><div style="left:1px;top:2px">x</div>'
    out, stats = opt.optimize(src, quiet=True)
    assert out == src                      # nothing to pool against -> unchanged
    assert stats[0]["pooled_classes"] == 0


def test_at_rule_is_preserved_not_flattened():
    src = ('<style>@media print{body{color:#000}}\n'
           '.a{color:#fff}</style><div class="a" style="left:0">x</div>')
    out, _ = opt.optimize(src, quiet=True)
    assert "@media print{body{color:#000}}" in out      # wrapper intact
    # the print-only rule must NOT have leaked to an always-on top-level rule
    assert not re.search(r"(?<!\{)\bbody\{color:#000\}", out.split("</style>")[0]
                         .replace("@media print{body{color:#000}}", ""))


def test_keyframes_block_survives():
    src = ('<style>@keyframes spin{from{transform:rotate(0)}to{transform:rotate(360deg)}}'
           '.b{left:0}</style><div class="b" style="left:0">x</div>')
    out, _ = opt.optimize(src, quiet=True)
    assert "@keyframes spin{" in out
    assert "rotate(360deg)" in out


# --------------------------------------------------------------------------- #
# Render preservation on real frameforge_to_html output                       #
# --------------------------------------------------------------------------- #


# NOTE ON FIXTURES
# Shapes used to be `<div style="background:…">`, so any repeated rect gave the
# optimizer something to pool. The HTML backend now emits inline SVG, where
# geometry paint travels in *presentation attributes* (`fill="#123456"`) that no
# CSS pass may touch. What still repeats — and so is still worth pooling — is the
# inline `style` on `<text>` elements whose style is anonymous (a named style is
# already hoisted to `.fg-ts-*` by the painter). These fixtures use text for that
# reason; the tool's guarantees are unchanged.
def _text_rows(n: int, **style) -> list[dict]:
    return [{"type": "text", "id": f"t{i}", "box": [0, i * 30, 200, 20],
             "text": f"row {i}", "style": dict(style)} for i in range(n)]


def test_roundtrip_preserves_viewBox_case_and_paint():
    html = _render([
        {"type": "polygon", "id": f"pg{i}", "points": [[0, 0], [10, 0], [5, 10]],
         "fill": "#facc15", "stroke": "#22d3ee"} for i in range(5)
    ])
    out, _ = opt.optimize(html, quiet=True)
    assert html.count("viewBox=") == out.count("viewBox=")   # all preserved
    assert "viewbox=" not in out                              # none lowercased
    # Paint survives untouched. It is a presentation attribute now, which is the
    # stronger guarantee: the optimizer rewrites only `style`/`class` values, so
    # geometry paint is not even reachable by a pooling bug.
    assert out.count('fill="#facc15"') == html.count('fill="#facc15"')
    assert out.count('stroke="#22d3ee"') == html.count('stroke="#22d3ee"')


def test_every_inline_property_still_applies_after_pooling():
    html = _render(_text_rows(6, font_size=14, color="#3366cc"))
    out, _ = opt.optimize(html, quiet=True)
    assert "fg-doc" in out
    head, body = out.split("</style>")[0], out.split("</style>")[1]
    # the property survives somewhere (a pooled rule or still inline)
    assert "fill:#3366cc" in head or "fill:#3366cc" in body
    # and at least one element references the pooled class
    assert re.search(r'class="[^"]*\bt\d+\b', body)


def test_pooling_actually_compounds_repeated_styles():
    html = _render(_text_rows(4, font_size=14, color="#123456"))
    out, stats = opt.optimize(html, quiet=True)
    assert stats[0]["pooled_classes"] >= 1
    assert stats[0]["theme_pooled"] >= 4              # 4 repeats compounded
    assert stats[0]["bytes_after"] < stats[0]["bytes_before"]
    # the shared declaration now lives in a generated .t* rule, not 4x inline
    head = out.split("</style>")[0]
    assert re.search(r"\.t\d+\{[^}]*fill:#123456", head)


def test_named_styles_are_already_pooled_by_the_backend():
    """The optimizer's job shrank because the backend does part of it natively.

    A *named* text style is hoisted to a `.fg-ts-<name>` class by the painter, so
    there is no repeated inline theme left for the optimizer to compound. This is
    the intended division of labour, not a regression in the tool.
    """
    doc_objects = [{"type": "text", "id": f"t{i}", "box": [0, i * 30, 200, 20],
                    "text": f"row {i}", "style": "body"} for i in range(5)]
    html = _render(doc_objects,
                   defs={"tokens": {"styles": {"body": {"font_size": 14}}}})
    assert html.count('class="fg-ts-body"') == 5
    assert ".fg-ts-body {" in html


def test_idempotent():
    html = _render([{"type": "rect", "id": f"r{i}", "box": [0, 0, 10, 10],
                     "fill": "#222"} for i in range(5)])
    once, _ = opt.optimize(html, quiet=True)
    twice, _ = opt.optimize(once, quiet=True)
    assert once == twice


def test_minify_keeps_at_rules_valid():
    src = ('<style>@media print{.x{color:#000}}\n.x{left:0}</style>'
           '<div class="x" style="left:0">y</div>')
    out, _ = opt.optimize(src, do_minify=True, quiet=True)
    assert "@media print{.x{color:#000}}" in out


# --------------------------------------------------------------------------- #
# Specificity guard                                                           #
# --------------------------------------------------------------------------- #


def test_risky_properties_empty_for_frameforge_output():
    html = _render([{"type": "rect", "id": "r", "box": [0, 0, 10, 10], "fill": "#111"}])
    css = re.search(r"<style[^>]*>(.*?)</style>", html, re.S).group(1)
    items = opt.split_stylesheet(css)
    # frameforge_to_html's only multi-token selectors end in a *type* (span/code),
    # so nothing a pooled class could collide with:
    assert opt.risky_properties(items) == set()


def test_specificity_guard_keeps_colliding_property_inline():
    # `.panel .label` out-specifies a single appended class AND keys on a class,
    # so `color` must NOT be pooled even when it repeats.
    src = (
        "<style>.panel .label{color:red}</style>"
        '<div class="panel"><span class="label" style="color:#00f;top:0">a</span>'
        '<span class="label" style="color:#00f;top:1">b</span></div>'
    )
    items = opt.split_stylesheet(
        re.search(r"<style>(.*?)</style>", src, re.S).group(1))
    assert "color" in opt.risky_properties(items)
    out, stats = opt.optimize(src, quiet=True)
    assert stats[0]["pooled_classes"] == 0      # color stayed inline
    assert out.count("color:#00f") == 2         # both still carry it inline


def test_split_stylesheet_roundtrips_plain_rules():
    css = ":root{--a:1}\n.x{color:#fff}\nbody{margin:0}"
    items = opt.split_stylesheet(css)
    kinds = [it[0] for it in items]
    assert kinds == ["rule", "rule", "rule"]
    assert ("rule", ".x", "color:#fff") in items
