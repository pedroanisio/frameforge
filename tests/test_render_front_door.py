#!/usr/bin/env python3
"""The package render front-door (`framegraph.cli`).

`framegraph.cli` is the single CLI over every render path; it is referenced from
pyproject's `[project.scripts]` as `framegraph-render`. This pins its target
registry, the `--list` path, and the two always-available, dependency-free
targets (svg, tex) end to end — the optional ones (png/pdf/pdf-tex/html) are
guarded by availability checks and not exercised here.

Package-side import — the `framegraph` PACKAGE must win over a models-module
shadow (mirror of test_render_cli.py / test_head.py).
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):   # the models module
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph import cli  # noqa: E402

DOC = """\
dsl: FrameGraph
version: 2.2.0
pages:
  - mode: page
    id: p1
    canvas: {size: [200, 120], units: px}
    layers:
      - id: main
        objects:
          - {type: rect, box: [10, 10, 180, 100], fill: "#cccccc"}
          - {type: text, box: [20, 40, 160, 30], text: "hi"}
"""


def _doc(tmp_path):
    p = tmp_path / "mini.fg.yaml"
    p.write_text(DOC, encoding="utf-8")
    return str(p)


def test_registry_covers_every_advertised_target():
    assert set(cli.TARGETS) == {"svg", "png", "pdf", "pdf-tex", "tex", "html"}
    # every target carries a kind, a blurb, an availability check and a render fn
    for t in cli.TARGETS.values():
        assert t.kind and t.blurb and callable(t.check) and callable(t.fn)


def test_list_exits_clean(capsys):
    assert cli.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "render targets" in out and "svg" in out and "available" in out


def test_to_without_input_is_a_usage_error():
    assert cli.main(["--to", "svg"]) == 2


def test_render_svg_is_always_available(tmp_path):
    out = tmp_path / "o"
    rc = cli.main([_doc(tmp_path), "--to", "svg", "--out", str(out)])
    assert rc == 0
    svg = out / "mini.fg-1.svg"
    assert svg.exists() and "<svg" in svg.read_text(encoding="utf-8")


def test_render_tex_is_always_available(tmp_path):
    out = tmp_path / "o"
    rc = cli.main([_doc(tmp_path), "--to", "tex", "--out", str(out)])
    assert rc == 0
    tex = out / "mini.fg.tex"
    assert tex.exists()
    body = tex.read_text(encoding="utf-8")
    assert "\\documentclass" in body and "tikzpicture" in body
