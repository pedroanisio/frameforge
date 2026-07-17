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


def test_roundtrip_preserves_viewBox_case_and_paint():
    html = _render([
        {"type": "polygon", "id": f"pg{i}", "points": [[0, 0], [10, 0], [5, 10]],
         "fill": "#facc15", "stroke": "#22d3ee"} for i in range(5)
    ])
    out, _ = opt.optimize(html, quiet=True)
    assert html.count("viewBox=") == out.count("viewBox=")   # all preserved
    assert "viewbox=" not in out                              # none lowercased
    # paint still present (inline or pooled into a class rule)
    assert "fill:#facc15" in out and "stroke:#22d3ee" in out


def test_every_inline_property_still_applies_after_pooling():
    # many identical rects -> their theme set pools into a class
    html = _render([{"type": "rect", "id": f"r{i}", "box": [i, i, 20, 20],
                     "fill": "#3366cc", "radius": 4} for i in range(6)])
    out, _ = opt.optimize(html, quiet=True)
    # background got pooled out of inline styles into a .t* class rule...
    assert "fg-doc" in out
    head = out.split("</style>")[0]
    body = out.split("</style>")[1]
    # the property survives somewhere (a pooled rule or still inline)
    assert "background:#3366cc" in head or "background:#3366cc" in body
    # and at least one element references the pooled class
    assert re.search(r'class="[^"]*\bt\d+\b', body)


def test_pooling_actually_compounds_repeated_styles():
    html = _render([{"type": "rect", "id": f"r{i}", "box": [0, 0, 10, 10],
                     "fill": "#123456"} for i in range(4)])
    out, stats = opt.optimize(html, quiet=True)
    assert stats[0]["pooled_classes"] >= 1
    assert stats[0]["theme_pooled"] >= 4              # 4 repeats compounded
    assert stats[0]["bytes_after"] < stats[0]["bytes_before"]
    # the shared declaration now lives in a generated .t* rule, not 4x inline
    head = out.split("</style>")[0]
    assert re.search(r"\.t\d+\{[^}]*background:#123456", head)


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
