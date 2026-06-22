"""document — transpile a FrameGraph flow document to a compilable LaTeX string.

`transpile(doc)` walks `pages[].story` and emits native LaTeX so TeX owns
pagination, justification, hyphenation, microtype, and math; figures are emitted
as vector TikZ via `FigureTikz`. Design tokens are honoured: token text styles map
to `\\fontsize`/series/shape + colour, the canvas drives `geometry`, and a sans
face (fontspec) carries the body — "LaTeX-quality rendering OF the FrameGraph design".
"""
from __future__ import annotations

from framegraph.rendering.domain.geometry import fnum, num
from framegraph.rendering.domain.services.canvas_resolver import CanvasResolver
from framegraph.rendering.domain.services.paint_resolver import ColorResolver
from framegraph.rendering.domain.services.text_style_resolver import TextStyleResolver

from .tikz import FigureTikz, _parse_hex, color_expr, ltx_escape, ltx_url_escape

# Symbol (`use`) expansion is shared with the SVG engine so a figure's object
# graph is already groups by the time we walk it.
try:
    from tooling.render_fixtures import normalize_doc
except Exception:                                    # pragma: no cover - import fallback
    def normalize_doc(doc):
        return doc

MARGIN_PT = 56.0                                     # matches the SVG proxy's flow column


class _ColorBook:
    """Allocates `\\definecolor`s for the resolved colours used in flowing text."""

    def __init__(self):
        self._by_rgb = {}
        self.defs = []

    def name(self, resolved):
        """resolved hex/name/None → (latex colour name | None)."""
        if resolved is None or resolved == "none":
            return None
        rgb = _parse_hex(resolved)
        if not rgb:
            return str(resolved)                     # assume a bare xcolor name
        r, g, b, _a = rgb
        key = (r, g, b)
        if key not in self._by_rgb:
            nm = f"fgc{len(self._by_rgb)}"
            self._by_rgb[key] = nm
            self.defs.append(f"\\definecolor{{{nm}}}{{RGB}}{{{r},{g},{b}}}")
        return self._by_rgb[key]


class _Transpiler:
    def __init__(self, doc):
        self.doc = normalize_doc(doc) if isinstance(doc, dict) else {}
        defs = self.doc.get("defs") or {}
        tok = defs.get("tokens") or {}
        self._color = ColorResolver(tok.get("colors") or {})
        self._ts = TextStyleResolver(tok.get("text_styles") or {}, tok.get("styles") or {}, self._color)
        self._canvas = CanvasResolver(defs.get("masters") or {})
        self._figtikz = FigureTikz(self._color, self._ts, tok.get("stroke_styles") or {})
        self._book = _ColorBook()
        self.skipped = 0

    # -- style → LaTeX font run ------------------------------------------- #
    def _font(self, st):
        size = st.get("size", 12) or 12
        lh = st.get("lh", 1.25) or 1.25
        out = f"\\fontsize{{{fnum(size)}}}{{{fnum(size * lh)}}}\\selectfont"
        if st.get("bold"):
            out += "\\bfseries"
        if st.get("italic"):
            out += "\\itshape"
        name = self._book.name(st.get("color"))
        if name:
            out += f"\\color{{{name}}}"
        return out

    def _styled(self, st, latex_body, gap="6pt"):
        return "{" + self._font(st) + " " + latex_body + "\\par}\n" + (f"\\addvspace{{{gap}}}\n" if gap else "")

    # -- inline ------------------------------------------------------------ #
    @staticmethod
    def _inline_text(value):
        if value is None:
            return ""
        if isinstance(value, (str, int, float)):
            return ltx_escape(value)
        if isinstance(value, list):
            return "".join(_Transpiler._inline_text(v) for v in value)
        if not isinstance(value, dict):
            return ltx_escape(value)
        if value.get("kind") == "link" and value.get("href"):
            inner = _Transpiler._inline_text(value.get("content"))
            return f"\\href{{{ltx_url_escape(value['href'])}}}{{{inner}}}"
        if value.get("kind") == "math":
            tex = value.get("tex") or value.get("latex")
            if tex:
                return f"\\({tex}\\)"
            return ltx_escape(value.get("alt") or "math expression")
        if value.get("text") is not None:
            return ltx_escape(value["text"])
        if isinstance(value.get("content"), list):
            return _Transpiler._inline_text(value["content"])
        return ""

    def _para_body(self, fl):
        if isinstance(fl.get("spans"), list):
            return "".join(self._inline_text(s) for s in fl["spans"])
        return ltx_escape(fl.get("text"))

    # -- block emitters ---------------------------------------------------- #
    def _emit(self, fl, out):
        t = fl.get("type")
        getattr(self, f"_emit_{t}", self._emit_unknown)(fl, out)

    def _emit_unknown(self, fl, out):
        txt = self._inline_text(fl.get("text"))
        if txt:
            out.append(self._styled(self._ts.resolve(fl.get("style") or "body"), txt))
        else:
            self.skipped += 1

    def _emit_heading(self, fl, out):
        st = self._ts.resolve(fl.get("style") or f"h{fl.get('level', 1)}")
        out.append("\\addvspace{10pt}\n" + self._styled(st, ltx_escape(fl.get("text")), gap="4pt"))

    def _emit_paragraph(self, fl, out):
        out.append(self._styled(self._ts.resolve(fl.get("style") or "body"), self._para_body(fl)))

    def _emit_list(self, fl, out):
        env = "enumerate" if fl.get("ordered") else "itemize"
        st = self._ts.resolve(fl.get("style") or "body")
        items = "".join("\\item " + self._inline_text(it) + "\n" for it in (fl.get("items") or []))
        out.append("{" + self._font(st) + f"\n\\begin{{{env}}}[leftmargin=2.2em,topsep=2pt,itemsep=1pt]\n"
                   + items + f"\\end{{{env}}}\\par}}\n\\addvspace{{6pt}}\n")

    def _emit_block(self, fl, out):
        for child in (fl.get("children") or []):
            if isinstance(child, dict):
                self._emit(child, out)

    def _emit_math(self, fl, out):
        tex = fl.get("tex") or fl.get("latex")
        if not tex:
            self.skipped += 1
            return
        out.append("\\[\n" + str(tex) + "\n\\]\n")

    def _emit_code(self, fl, out):
        code = fl.get("code") or fl.get("source") or ""
        out.append("\\begin{verbatim}\n" + str(code) + "\n\\end{verbatim}\n")

    def _emit_table(self, fl, out):
        header = fl.get("header") if isinstance(fl.get("header"), list) else []
        rows = [r for r in (fl.get("rows") or []) if isinstance(r, list)]
        if not header and not rows:
            return
        ncol = max([len(header)] + [len(r) for r in rows] + [1])
        cap = fl.get("caption")
        if isinstance(cap, dict):
            cap = cap.get("text")
        if cap:
            out.append(self._styled(self._ts.resolve("caption"), "\\textbf{" + ltx_escape(cap) + "}", gap="3pt"))

        def cells(row, bold=False):
            xs = [ltx_escape(row[i]) if i < len(row) and row[i] is not None else "" for i in range(ncol)]
            if bold:
                xs = [("\\textbf{" + c + "}" if c else "") for c in xs]
            return " & ".join(xs) + " \\\\\n"

        size = 7 if ncol >= 7 else (8 if ncol >= 5 else 9)
        lines = [f"\\begin{{tabular}}{{{'l' * ncol}}}\n\\toprule\n"]
        if header:
            lines.append(cells(header, bold=True) + "\\midrule\n")
        lines += [cells(r) for r in rows]
        lines.append("\\bottomrule\n\\end{tabular}")
        table = "".join(lines)
        inkname = self._book.name(self._color.resolve("ink")) or "black"
        if ncol >= 6:
            table = f"\\resizebox{{\\textwidth}}{{!}}{{{table}}}"
        else:
            table = f"{{\\fontsize{{{size}}}{{{fnum(size * 1.2)}}}\\selectfont {table}}}"
        out.append(f"\\begin{{center}}\\color{{{inkname}}}{table}\\end{{center}}\n\\addvspace{{8pt}}\n")

    def _emit_figure(self, fl, out):
        ob = fl.get("object")
        if not isinstance(ob, dict):
            self.skipped += 1
            return
        size = fl.get("size") if isinstance(fl.get("size"), list) else None
        obox = ob.get("box") if isinstance(ob.get("box"), list) else None
        figw = (num(size[0], 0) if size and len(size) >= 2
                else num(obox[2], 0) if obox and len(obox) >= 4 else 0)
        body = self._figtikz.render(ob)
        pic = "\\begin{tikzpicture}[x=1pt,y=-1pt]\n" + body + "\\end{tikzpicture}"
        tw = self._textwidth
        if figw and figw > tw:
            pic = f"\\resizebox{{\\textwidth}}{{!}}{{{pic}}}"
        out.append("\\begin{center}\n" + pic + "\n\\end{center}\n")
        cap = fl.get("caption")
        if isinstance(cap, dict):
            cap = cap.get("text")
        if cap:
            out.append("{\\centering" + self._font(self._ts.resolve("fig_caption"))
                       + "\\itshape " + ltx_escape(cap) + "\\par}\n")
        out.append("\\addvspace{12pt}\n")

    # -- assembly ---------------------------------------------------------- #
    def build(self):
        pages = [p for p in (self.doc.get("pages") or []) if isinstance(p, dict)]
        flow = next((p for p in pages if p.get("mode") == "flow"), pages[0] if pages else {})
        w, h = self._canvas.resolve(flow)
        self._textwidth = w - 2 * MARGIN_PT

        out = []
        for fl in (flow.get("story") or []):
            if isinstance(fl, dict):
                self._emit(fl, out)
        body = "".join(out)
        return self._preamble(w, h) + "\\begin{document}\n" + body + "\\end{document}\n"

    def _preamble(self, w, h):
        title = ltx_escape(self.doc.get("title") or "")
        # Touch a few token colours up front so they exist even if unused in body.
        for key in ("ink", "paper", "rule"):
            self._book.name(self._color.resolve(key))
        colordefs = "\n".join(self._book.defs)
        return (
            "\\documentclass[11pt]{article}\n"
            "\\usepackage{fontspec}\n"
            f"\\usepackage[paperwidth={fnum(w)}pt,paperheight={fnum(h)}pt,"
            f"margin={fnum(MARGIN_PT)}pt]{{geometry}}\n"
            "\\usepackage{microtype}\n"
            "\\usepackage{amsmath}\n"
            "\\usepackage{amssymb}\n"
            "\\usepackage{slashed}\n"
            "\\usepackage{xcolor}\n"
            "\\usepackage{booktabs}\n"
            "\\usepackage{array}\n"
            "\\usepackage{enumitem}\n"
            "\\usepackage{graphicx}\n"
            "\\usepackage[hidelinks]{hyperref}\n"
            "\\usepackage{tikz}\n"
            "\\usetikzlibrary{arrows.meta}\n"
            "\\setmainfont{DejaVu Sans}\n"
            f"{colordefs}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\setlength{\\parskip}{0pt}\n"
            "\\frenchspacing\n"
            f"\\title{{{title}}}\n"
            "\\pagestyle{plain}\n"
        )


def transpile(doc) -> str:
    return _Transpiler(doc).build()
