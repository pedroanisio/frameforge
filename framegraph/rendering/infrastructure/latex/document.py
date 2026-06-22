"""document — transpile a FrameGraph flow document to a compilable LaTeX string.

`transpile(doc)` walks `pages[].story` and emits native LaTeX so TeX owns
pagination, justification, hyphenation, microtype, and math; figures are emitted
as vector TikZ via `FigureTikz`. Design tokens are honoured: token text styles map
to `\\fontsize`/series/shape + colour, the canvas drives `geometry`, and a sans
face (fontspec) carries the body — "LaTeX-quality rendering OF the FrameGraph design".
"""
from __future__ import annotations

import os

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


def _latex_label(value) -> str:
    raw = str(value or "")
    return "fg:" + "".join(ch if ch.isalnum() or ch in ".:-" else "-" for ch in raw)


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
    def __init__(self, doc, asset_base=None):
        self.doc = normalize_doc(doc) if isinstance(doc, dict) else {}
        defs = self.doc.get("defs") or {}
        self._assets = defs.get("assets") or {}
        self._asset_base = asset_base
        tok = defs.get("tokens") or {}
        self._color = ColorResolver(tok.get("colors") or {})
        self._ts = TextStyleResolver(tok.get("text_styles") or {}, tok.get("styles") or {}, self._color)
        self._canvas = CanvasResolver(defs.get("masters") or {})
        self._figtikz = FigureTikz(self._color, self._ts, tok.get("stroke_styles") or {})
        self._book = _ColorBook()
        self._gloss_terms = []
        self._endnotes = []
        self._use_endnotes = False
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
    def _index_entry(term, sort=None, see=None):
        shown = ltx_escape(term)
        prefix = f"{ltx_escape(sort)}@" if sort else ""
        suffix = f"|see{{{ltx_escape(see)}}}" if see else ""
        return f"\\index{{{prefix}{shown}{suffix}}}"

    def _inline_text(self, value):
        if value is None:
            return ""
        if isinstance(value, (str, int, float)):
            return ltx_escape(value)
        if isinstance(value, list):
            return "".join(self._inline_text(v) for v in value)
        if not isinstance(value, dict):
            return ltx_escape(value)
        if value.get("kind") == "link" and value.get("href"):
            inner = self._inline_text(value.get("content"))
            return f"\\href{{{ltx_url_escape(value['href'])}}}{{{inner}}}"
        if value.get("kind") == "ref" and value.get("target"):
            target = _latex_label(value.get("target"))
            if value.get("show") == "page":
                return f"\\pageref{{{target}}}"
            if value.get("show") == "title":
                return f"\\nameref{{{target}}}"
            return f"\\ref{{{target}}}"
        if value.get("kind") == "cite" and value.get("key"):
            keys = value.get("key")
            key_text = ",".join(str(k) for k in keys) if isinstance(keys, list) else str(keys)
            note = ", ".join(str(x) for x in (value.get("prefix"), value.get("locator")) if x)
            return f"\\cite{f'[{ltx_escape(note)}]' if note else ''}{{{ltx_escape(key_text)}}}"
        if value.get("kind") == "footnote":
            content = "".join(self._flow_text_content(fl) for fl in (value.get("content") or []))
            content = content or ltx_escape(value.get("id") or "")
            if self._use_endnotes:
                self._endnotes.append(content)
                return f"\\textsuperscript{{{len(self._endnotes)}}}"
            return "\\footnote{" + content + "}"
        if value.get("kind") == "math":
            tex = value.get("tex") or value.get("latex")
            if tex:
                return f"\\({tex}\\)"
            return ltx_escape(value.get("alt") or "math expression")
        if value.get("kind") == "code":
            return f"\\texttt{{{ltx_escape(value.get('text') or '')}}}"
        if value.get("kind") == "index" and value.get("term"):
            return self._index_entry(value.get("term"), value.get("sort"), value.get("see"))
        if value.get("kind") == "gloss" and value.get("term"):
            term = str(value.get("term"))
            if term not in self._gloss_terms:
                self._gloss_terms.append(term)
            return ltx_escape(term) + self._index_entry(term)
        if value.get("kind") == "margin_note":
            content = "".join(self._flow_text_content(fl) for fl in (value.get("content") or []))
            return "\\marginpar{\\footnotesize " + content + "}"
        if value.get("text") is not None:
            return ltx_escape(value["text"])
        if isinstance(value.get("spans"), list):
            return self._inline_text(value["spans"])
        if isinstance(value.get("content"), list):
            return self._inline_text(value["content"])
        return ""

    def _flow_text_content(self, fl):
        if isinstance(fl, str):
            return ltx_escape(fl)
        if isinstance(fl, list):
            return "".join(self._flow_text_content(item) for item in fl)
        if not isinstance(fl, dict):
            return ltx_escape(fl)
        if isinstance(fl.get("spans"), list):
            return "".join(self._inline_text(s) for s in fl["spans"])
        if fl.get("text") is not None:
            return ltx_escape(fl.get("text"))
        if fl.get("type") == "math" and fl.get("tex"):
            return f"\\({fl.get('tex')}\\)"
        if fl.get("type") == "code":
            return f"\\texttt{{{ltx_escape(fl.get('source') or fl.get('code') or '')}}}"
        if isinstance(fl.get("children"), list):
            return "".join(self._flow_text_content(child) for child in fl["children"])
        return ""

    def _caption_text(self, value):
        if isinstance(value, list):
            return self._inline_text(value)
        if isinstance(value, dict):
            if isinstance(value.get("spans"), list):
                return self._inline_text(value.get("spans"))
            return self._inline_text(value.get("text") or value.get("content"))
        return ltx_escape(value)

    def _asset_src(self, src):
        asset = self._assets.get(src)
        if isinstance(asset, dict):
            return asset.get("data") or asset.get("src") or asset.get("path") or src
        if isinstance(asset, str):
            return asset
        return src

    def _asset_path(self, src):
        resolved = self._asset_src(src)
        if not isinstance(resolved, str) or not resolved.strip():
            return None
        if resolved.startswith("data:"):
            return None
        if os.path.isabs(resolved) or not self._asset_base:
            return os.path.normpath(resolved)
        return os.path.normpath(os.path.join(self._asset_base, resolved))

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
        label = f"\\label{{{_latex_label(fl.get('id'))}}}" if fl.get("id") else ""
        out.append("\\addvspace{10pt}\n" + self._styled(st, ltx_escape(fl.get("text")) + label, gap="4pt"))

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

    def _emit_keep_together(self, fl, out):
        inner = []
        for child in (fl.get("children") or []):
            if isinstance(child, dict):
                self._emit(child, inner)
        out.append("\\begin{samepage}\n" + "".join(inner) + "\\end{samepage}\n")

    def _emit_spacer(self, fl, out):
        out.append(f"\\vspace{{{fnum(num(fl.get('height'), 12) or 12)}pt}}\n")

    def _emit_page_break(self, _fl, out):
        out.append("\\clearpage\n")

    def _emit_column_break(self, _fl, out):
        out.append("\\newpage\n")

    def _emit_math(self, fl, out):
        tex = fl.get("tex") or fl.get("latex")
        if not tex:
            self.skipped += 1
            return
        label = f"\\label{{{_latex_label(fl.get('id'))}}}" if fl.get("id") else ""
        out.append("\\[\n" + str(tex) + label + "\n\\]\n")

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
        if cap:
            out.append(self._styled(self._ts.resolve("caption"), "\\textbf{" + self._caption_text(cap) + "}", gap="3pt"))

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
        if fl.get("id"):
            table += f"\n\\label{{{_latex_label(fl.get('id'))}}}"
        inkname = self._book.name(self._color.resolve("ink")) or "black"
        if ncol >= 6:
            table = f"\\resizebox{{\\textwidth}}{{!}}{{{table}}}"
        else:
            table = f"{{\\fontsize{{{size}}}{{{fnum(size * 1.2)}}}\\selectfont {table}}}"
        out.append(f"\\begin{{center}}\\color{{{inkname}}}{table}\\end{{center}}\n\\addvspace{{8pt}}\n")

    def _image_graphics_options(self, fl):
        width = num(fl.get("width"), None)
        height = num(fl.get("height"), None)
        opts = []
        if width is not None and width > 0:
            opts.append("width=\\textwidth" if width > self._textwidth else f"width={fnum(width)}pt")
        elif height is None:
            opts.append("width=\\textwidth")
        if height is not None and height > 0:
            opts.append(f"height={fnum(height)}pt")
        if fl.get("preserve_aspect_ratio") is not False:
            opts.append("keepaspectratio")
        return ",".join(opts)

    def _image_placeholder(self, fl):
        label = fl.get("alt") or fl.get("actual_text") or fl.get("caption") or fl.get("src") or "image"
        return (
            "\\fbox{\\begin{minipage}{0.9\\textwidth}\\centering "
            + self._font(self._ts.resolve("caption"))
            + ltx_escape(label)
            + "\\end{minipage}}\n"
        )

    def _emit_image(self, fl, out):
        path = self._asset_path(fl.get("src"))
        if path:
            opts = self._image_graphics_options(fl)
            out.append("\\begin{center}\n")
            out.append(f"\\includegraphics[{opts}]{{\\detokenize{{{path}}}}}\n")
            out.append("\\end{center}\n")
        else:
            self.skipped += 1
            out.append("\\begin{center}\n" + self._image_placeholder(fl) + "\\end{center}\n")
        cap = fl.get("caption")
        if cap:
            out.append("{\\centering" + self._font(self._ts.resolve("fig_caption"))
                       + "\\itshape " + self._caption_text(cap) + "\\par}\n")
        credit = fl.get("credit")
        if credit:
            out.append("{\\centering" + self._font(self._ts.resolve("caption"))
                       + self._caption_text(credit) + "\\par}\n")
        out.append("\\addvspace{12pt}\n")

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
        if cap:
            out.append("{\\centering" + self._font(self._ts.resolve("fig_caption"))
                       + "\\itshape " + self._caption_text(cap)
                       + (f"\\label{{{_latex_label(fl.get('id'))}}}" if fl.get("id") else "")
                       + "\\par}\n")
        out.append("\\addvspace{12pt}\n")

    def _emit_toc(self, fl, out):
        title = fl.get("title")
        if title:
            out.append(self._styled(self._ts.resolve(fl.get("style") or "h2"), ltx_escape(title), gap="4pt"))
        out.append("\\tableofcontents\n\\addvspace{8pt}\n")

    def _emit_bibliography(self, fl, out):
        title = fl.get("title")
        entries = fl.get("entries") if isinstance(fl.get("entries"), list) else []
        if title:
            out.append(self._styled(self._ts.resolve("h2"), ltx_escape(title), gap="4pt"))
        out.append("\\begin{thebibliography}{99}\n")
        for idx, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue
            key = entry.get("id") or entry.get("key") or str(idx)
            text = entry.get("text") or entry.get("title") or entry.get("citation") or key
            out.append(f"\\bibitem{{{ltx_escape(key)}}}{ltx_escape(text)}\n")
        out.append("\\end{thebibliography}\n")

    def _emit_index(self, fl, out):
        title = fl.get("title")
        if title:
            out.append(f"\\renewcommand{{\\indexname}}{{{ltx_escape(title)}}}\n")
        out.append("\\printindex\n")

    def _glossary_entries(self, source=None):
        defs = self.doc.get("defs") if isinstance(self.doc.get("defs"), dict) else {}
        candidates = []
        if source and isinstance(defs.get(source), (dict, list)):
            candidates.append(defs.get(source))
        if isinstance(defs.get("glossary"), (dict, list)):
            candidates.append(defs.get("glossary"))
        if isinstance(defs.get("glossaries"), dict):
            if source and isinstance(defs["glossaries"].get(source), (dict, list)):
                candidates.append(defs["glossaries"][source])
            candidates += [v for v in defs["glossaries"].values() if isinstance(v, (dict, list))]
        for candidate in candidates:
            if isinstance(candidate, dict):
                for term, body in candidate.items():
                    if isinstance(body, dict):
                        yield str(body.get("term") or term), body.get("definition") or body.get("text") or body.get("long") or body.get("short") or ""
                    else:
                        yield str(term), body
            elif isinstance(candidate, list):
                for item in candidate:
                    if isinstance(item, dict):
                        term = item.get("term") or item.get("id")
                        if term:
                            yield str(term), item.get("definition") or item.get("text") or item.get("long") or item.get("short") or ""
                    elif item:
                        yield str(item), ""

    def _emit_glossary(self, fl, out):
        title = fl.get("title")
        if title:
            out.append(self._styled(self._ts.resolve(fl.get("style") or "h2"), ltx_escape(title), gap="4pt"))
        entries = list(self._glossary_entries(fl.get("source")))
        known = {term for term, _ in entries}
        entries += [(term, "") for term in self._gloss_terms if term not in known]
        if not entries:
            self.skipped += 1
            return
        out.append("\\begin{description}[leftmargin=2.2em,style=nextline]\n")
        for term, definition in entries:
            out.append(f"\\item[{ltx_escape(term)}] {self._inline_text(definition)}\n")
        out.append("\\end{description}\n\\addvspace{8pt}\n")

    def _emit_endnotes(self, fl, out):
        title = fl.get("title")
        if title:
            out.append(self._styled(self._ts.resolve(fl.get("style") or "h2"), ltx_escape(title), gap="4pt"))
        if not self._endnotes:
            self.skipped += 1
            return
        out.append("\\begin{enumerate}[leftmargin=2.2em,topsep=2pt,itemsep=1pt]\n")
        for note in self._endnotes:
            out.append("\\item " + note + "\n")
        out.append("\\end{enumerate}\n\\addvspace{8pt}\n")

    # -- assembly ---------------------------------------------------------- #
    def build(self):
        pages = [p for p in (self.doc.get("pages") or []) if isinstance(p, dict)]
        flow = next((p for p in pages if p.get("mode") == "flow"), pages[0] if pages else {})
        w, h = self._canvas.resolve(flow)
        self._textwidth = w - 2 * MARGIN_PT

        story = flow.get("story") or []
        self._use_endnotes = any(isinstance(fl, dict) and fl.get("type") == "endnotes" for fl in story)
        out = []
        for fl in story:
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
            "\\usepackage{makeidx}\n"
            "\\usepackage[hidelinks]{hyperref}\n"
            "\\usepackage{nameref}\n"
            "\\usepackage{tikz}\n"
            "\\usetikzlibrary{arrows.meta}\n"
            "\\setmainfont{DejaVu Sans}\n"
            "\\makeindex\n"
            f"{colordefs}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\setlength{\\parskip}{0pt}\n"
            "\\frenchspacing\n"
            f"\\title{{{title}}}\n"
            "\\pagestyle{plain}\n"
        )


def transpile(doc, asset_base=None) -> str:
    return _Transpiler(doc, asset_base=asset_base).build()
