"""Typeset-PDF output backend — the `DocumentRenderer` port over LaTeX/TikZ.

Transpiles a FrameGraph document to native LaTeX (TeX owns pagination,
justification, hyphenation, and real math) and compiles it to a PDF by invoking
an external TeX engine. The engine call is the adapter's own driven dependency
(`…latex.compile`); the CLI reaches this backend through the port, not by
subprocessing a script in `tooling/`.
"""
from __future__ import annotations

from framegraph.rendering.domain.ports import RenderedArtifact


class PdfTexDocumentRenderer:
    """Compile a FrameGraph document to a typeset PDF via LaTeX/TikZ.

    `options["engine"]` selects the TeX engine (``auto`` | ``lualatex`` |
    ``pdflatex``); ``auto`` prefers lualatex when luaotfload is present, else
    pdflatex. `available()` reports whether any usable engine is on PATH.
    """

    target = "pdf-tex"
    kind = "typeset"
    blurb = "typeset PDF via LaTeX/TikZ (TeX owns pagination + math)"

    def available(self) -> "str | None":
        from framegraph.rendering.infrastructure.latex.compile import engine_available
        return None if engine_available("auto") else "needs lualatex/pdflatex on PATH"

    def render(self, document, *, base_dir=None, options=None) -> RenderedArtifact:
        from framegraph.rendering.infrastructure.latex.compile import compile_document
        engine = (options or {}).get("engine", "auto")
        pdf = compile_document(document, engine=engine, asset_base=base_dir)
        return RenderedArtifact(
            pages=[pdf],
            media_type="application/pdf",
            extension="pdf",
            one_file_per_page=False,
        )
