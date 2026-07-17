"""Contract for the `DocumentRenderer` output port and its backends.

Locks the hexagonal seam that replaced the html/pdf-tex subprocess shell-outs:
the CLI renders through the port *in-process*, the registry exposes one adapter
per ``--to`` target, and no caller shells out to one of our own scripts. The
compile-to-PDF assertion is gated on a real TeX engine being present.
"""
from __future__ import annotations

import functools
import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# earlier collected modules (the codemod tests) cache the MODELS module as
# `frameforge` AND leave docs/models first on sys.path; evict the non-package
# shadow and put src back in front so the rendering package imports
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import frameforge.cli as cli
from frameforge.rendering.domain.ports import RenderedArtifact
from frameforge.rendering.infrastructure.backends import (
    HtmlDocumentRenderer,
    PdfTexDocumentRenderer,
    all_backends,
    get_backend,
)
from frameforge.rendering.infrastructure.latex.compile import (
    compile_tex,
    engine_available,
    pick_engine,
)


def _doc(objects: list[dict] | None = None) -> dict:
    return {
        "dsl": "FrameForge",
        "version": "2.0.0",
        "title": "Port",
        "pages": [{
            "mode": "page", "id": "p1",
            "canvas": {"size": [320, 240], "units": "px"},
            "layers": [{"id": "main", "z": 0,
                        "objects": objects or [{"type": "rect", "id": "bg", "box": [0, 0, 10, 10]}]}],
        }],
    }


# --------------------------------------------------------------------------- #
# Registry + port surface                                                      #
# --------------------------------------------------------------------------- #
def test_registry_exposes_one_backend_per_port_target():
    reg = all_backends()
    assert set(reg) == {"html", "pdf-tex"}
    assert isinstance(get_backend("html"), HtmlDocumentRenderer)
    assert isinstance(get_backend("pdf-tex"), PdfTexDocumentRenderer)
    assert get_backend("does-not-exist") is None


def test_backends_satisfy_the_port_surface():
    for target in ("html", "pdf-tex"):
        be = get_backend(target)
        assert be.target == target
        assert isinstance(be.kind, str) and be.kind
        assert isinstance(be.blurb, str) and be.blurb
        avail = be.available()
        assert avail is None or isinstance(avail, str)


# --------------------------------------------------------------------------- #
# HTML adapter                                                                 #
# --------------------------------------------------------------------------- #
def test_html_backend_returns_a_text_html_artifact():
    art = get_backend("html").render(_doc())
    assert isinstance(art, RenderedArtifact)
    assert art.media_type == "text/html"
    assert art.extension == "html"
    assert art.one_file_per_page is False
    assert len(art.pages) == 1 and isinstance(art.pages[0], str)
    assert "<figure" in art.pages[0]
    assert '<h1 class="sr-only">Port</h1>' in art.pages[0]


def test_html_backend_is_always_available():
    assert get_backend("html").available() is None


# --------------------------------------------------------------------------- #
# The CLI drives the port in-process — the shell-out machinery is gone         #
# --------------------------------------------------------------------------- #
def test_cli_has_no_shellout_machinery():
    for gone in ("subprocess", "glob", "shutil", "_script"):
        assert not hasattr(cli, gone), (
            f"cli.{gone} should be gone — html/pdf-tex go through the port, "
            "not a subprocess to our own scripts"
        )


def test_cli_render_html_writes_in_process(tmp_path):
    doc_path = tmp_path / "d.fg.yaml"
    doc_path.write_text(yaml.safe_dump(_doc()), encoding="utf-8")

    class _Args:
        stem = "d"
        single = None

    written = cli._render_via_port("html", str(doc_path), str(tmp_path), _Args())
    assert len(written) == 1
    out = written[0]
    assert out.endswith("d.html")
    assert "<figure" in open(out, encoding="utf-8").read()


# --------------------------------------------------------------------------- #
# pdf-tex adapter — compiles via an external TeX engine (gated)               #
# --------------------------------------------------------------------------- #
@functools.cache
def _tex_env_can_compile_stack() -> bool:
    """True only when the local TeX engine can compile the package stack the
    transpiler emits (fontspec + microtype + tikz), not merely that an engine is
    on PATH.

    ``engine_available`` checks PATH only; a host can have lualatex present yet a
    broken luaotfload/lualibs font cache that fails on the first featured OpenType
    font (e.g. microtype loading ``lmr:+tlig``). This probes a HAND-WRITTEN
    reference doc — never the transpiler's output — so a genuine backend defect on
    a healthy TeX host still fails the test, while a broken TeX install skips it
    (as an absent engine already does)."""
    if not engine_available("auto"):
        return False
    eng = pick_engine("auto")
    ref = (
        r"\documentclass{article}"
        r"\usepackage{fontspec}\setmainfont{DejaVu Sans}"
        r"\usepackage{microtype}\usepackage{tikz}"
        r"\begin{document}hi"
        r"\begin{tikzpicture}\path (0,0) rectangle (1,1);\end{tikzpicture}"
        r"\end{document}"
    )
    with tempfile.TemporaryDirectory(prefix="fg-texprobe-") as work:
        tex_path = os.path.join(work, "probe.tex")
        with open(tex_path, "w", encoding="utf-8") as fh:
            fh.write(ref)
        try:
            return bool(compile_tex(tex_path, engine=eng, quiet=True))
        except Exception:  # noqa: BLE001 — any failure here means "cannot compile"
            return False


@pytest.mark.skipif(
    not _tex_env_can_compile_stack(),
    reason="TeX engine cannot compile the transpiler's package stack "
    "(no engine on PATH, or a broken luaotfload/lualibs font cache)",
)
def test_pdf_tex_backend_compiles_to_pdf_bytes():
    art = get_backend("pdf-tex").render(_doc(), options={"engine": "auto"})
    assert art.media_type == "application/pdf"
    assert art.extension == "pdf"
    assert len(art.pages) == 1 and isinstance(art.pages[0], (bytes, bytearray))
    assert art.pages[0][:5] == b"%PDF-"
