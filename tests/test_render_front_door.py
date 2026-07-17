#!/usr/bin/env python3
"""The package render front-door (`frameforge.cli`).

`frameforge.cli` is the single CLI over every render path; it is referenced from
pyproject's `[project.scripts]` as `frameforge-render`. This pins its target
registry, the `--list` path, and the two always-available, dependency-free
targets (svg, tex) end to end — the optional ones (png/pdf/pdf-tex/html) are
guarded by availability checks and not exercised here.

Package-side import — the `frameforge` PACKAGE must win over a models-module
shadow (mirror of test_render_cli.py / test_head.py).
"""
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):   # the models module
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge import cli  # noqa: E402


@pytest.fixture(autouse=True)
def _ensure_frameforge_package():
    """A models-module test collected *after* this file can leave the models
    module (``docs/models/frameforge.py``) owning ``sys.modules["frameforge"]``
    AND ``docs/models`` first on ``sys.path``. These tests call ``cli.main``
    which lazily imports ``frameforge.sdk`` / ``frameforge.rendering`` at RUN
    time, so re-assert the package here — a collection-time preamble alone is
    order-dependent (audit finding #11). Everything is saved and restored, so
    this isolation never leaks to the next test."""
    models_path = os.path.normpath(os.path.join(ROOT, "docs", "models"))
    saved_path, saved_mod = list(sys.path), sys.modules.get("frameforge")
    # drop docs/models from the path and evict a non-package shadow so a fresh
    # `import frameforge` resolves the package (src is on the path); submodules
    # are left intact (other modules hold live references to them).
    sys.path[:] = [p for p in sys.path
                   if os.path.normpath(p or os.getcwd()) != models_path]
    if saved_mod is not None and not hasattr(saved_mod, "__path__"):
        del sys.modules["frameforge"]
    try:
        yield
    finally:
        sys.path[:] = saved_path
        if saved_mod is not None:
            sys.modules["frameforge"] = saved_mod
        elif not hasattr(sys.modules.get("frameforge"), "__path__"):
            sys.modules.pop("frameforge", None)

DOC = """\
dsl: FrameForge
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
    assert set(cli.TARGETS) == {"svg", "png", "pdf", "pdf-tex", "tex", "html", "audit"}
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


# A flow doc with a TOC: its entries must become clickable PDF link annotations
# (the "dead TOC" regression — 0 hyperlinks in the stitched PDF).
FLOW_TOC = """\
dsl: FrameForge
version: 2.2.0
profile: book
title: toc links
pages:
  - mode: flow
    id: s
    story:
      - {type: toc, levels: [1]}
      - {type: heading, level: 1, text: Alpha, id: a}
      - {type: page_break}
      - {type: heading, level: 1, text: Beta, id: b}
"""


def test_pdf_toc_entries_become_clickable_links(tmp_path):
    import pytest
    if not cli._can_import("cairosvg", "pypdf"):
        pytest.skip("pdf target unavailable (needs cairosvg + pypdf)")
    src = tmp_path / "toc.fg.yaml"
    src.write_text(FLOW_TOC, encoding="utf-8")
    out = tmp_path / "out"
    assert cli.main([str(src), "--to", "pdf", "--out", str(out)]) == 0
    from pypdf import PdfReader
    pdfs = list(out.glob("*.pdf"))
    assert pdfs, "no PDF written"
    reader = PdfReader(str(pdfs[0]))
    links = []
    for pg in reader.pages:
        for a in (pg.get("/Annots") or []):
            obj = a.get_object()
            if obj.get("/Subtype") == "/Link":
                links.append(obj)
    assert len(links) >= 2, "TOC entries did not become PDF link annotations"
    # each link targets a real page in the document (internal GoTo)
    for lk in links:
        dest = lk.get("/Dest") or (lk.get("/A") or {}).get("/D")
        assert dest is not None and int(dest[0]) < len(reader.pages)
