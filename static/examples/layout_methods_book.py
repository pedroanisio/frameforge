#!/usr/bin/env python3
"""Compose *Layout Methods — A Field Guide* as a native FrameGraph book.

This is the chapter itself — prose, code, tables, callouts and all fourteen
plates — authored end-to-end through the FrameGraph SDK and lowered to a single
multi-page ``mode: page`` document. Nothing here is rendered by an outside
Markdown/HTML pipeline: the running heads, the measured text wrapping, the
pagination, the inline monospace code, and the plates are all FrameGraph
objects.

It is, deliberately, the thesis of §10 applied to itself. The book is laid out
by a thin composer that *lowers author intent (a heading, a paragraph, a figure)
to the absolute coordinates the renderer consumes* — the same "author high,
lower to one representation, render" move the chapter argues a layout layer
should make. The fourteen plates are reused verbatim from
``layout_methods_figures.py`` (each a standalone absolute page) and embedded by a
single scale-and-translate group transform.

Run from the repository root::

    uv run python examples/layout_methods_book.py     # writes _tmp/book/*

⚠ ARCHITECTURAL CONTRACT (PALS's LAW) — the figures and prose are authored by an
LLM. They are validated here against the model (``build``) and the static rules
(``validate_static_rules``); the build fails loudly on any model error. Treat the
prose as didactic and verify the bibliographic specifics against primary sources.
"""
from __future__ import annotations

import os
import re as _re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
sys.path.insert(0, HERE)            # so the sibling plate module resolves even
                                    # when exec'd from another CWD (the MCP harness)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import (  # noqa: E402
    DocumentBuilder,
    FigureRef,
    render_page_svgs,
    serialize,
)
from framegraph.sdk.metrics import measure_text, wrap_text  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

import layout_methods_figures as plates  # noqa: E402

# --------------------------------------------------------------------------- #
# Page geometry — US Letter at 96 dpi (816 × 1056), the chapter's print target.
# --------------------------------------------------------------------------- #
PAGE_W, PAGE_H = 816, 1056
MX = 99                                  # left / right margin
CONTENT_W = PAGE_W - 2 * MX              # 618 px text measure
TOP = 132                                # first baseline region, below running head
BOTTOM = 980                             # last usable y for content
HEAD_Y = 66                              # running-head baseline

# --------------------------------------------------------------------------- #
# Type system. Body is a true book serif (Charter); chrome and headings are a
# humanist sans (Fira Sans); code is Fira Mono. All three are installed, so the
# author-time measurement matches the rasterizer's glyph advances.
# --------------------------------------------------------------------------- #
SERIF = ["Charter", "Bitstream Charter", "Georgia", "serif"]
SANS = ["Fira Sans", "Inter", "Helvetica", "Arial", "sans-serif"]
MONO = ["Fira Mono", "JetBrains Mono", "DejaVu Sans Mono", "monospace"]

# Ink ramp + one restrained accent, consistent with the plates.
PAPER = plates.PAPER
INK = plates.INK
MUTE = plates.MUTE
FAINT = plates.FAINT
LINE = plates.LINE
RULE = plates.RULE
ACCENT = plates.INDIGO[2]          # deep steel-indigo, page chrome
ACCENT_MID = plates.INDIGO[1]
PANEL = plates.PANEL
INKBG = plates.INKBG
CODE_INK = "#2C3A2F"               # inline code, a hair warmer than body ink
D_BODY = plates.D_BODY
D_FAINT = plates.D_FAINT

BODY_SIZE = 11.5
BODY_LH = 1.52                     # generous leading for a serif reading column
CODE_SIZE = 10.0
CODE_LH = 1.42


def ts(size, color, *, family=SERIF, weight=None, align=None, spacing=None,
       lh=None, style=None, transform=None):
    """Inline text-Style dict (the model accepts inline Style anywhere)."""
    s = {"font_family": family, "font_size": size, "color": color}
    if weight is not None:
        s["font_weight"] = weight
    if align is not None:
        s["align"] = align
    if spacing is not None:
        s["letter_spacing"] = spacing
    if lh is not None:
        s["line_height"] = lh
    if style is not None:
        s["font_style"] = style
    if transform is not None:
        s["text_transform"] = transform
    return s


# --------------------------------------------------------------------------- #
# Inline rich text — a tiny run model so body prose can carry true monospace
# code spans, bold and italic without losing the measured wrap.
# --------------------------------------------------------------------------- #
_INLINE_RE = _re.compile(
    r"(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))"
)


def runs(text):
    """Split a string into (text, kind) runs; kind in body/code/bold/italic/link."""
    out = []
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], "body"))
        tok = m.group(0)
        if tok.startswith("`"):
            out.append((tok[1:-1], "code"))
        elif tok.startswith("**"):
            out.append((tok[2:-2], "bold"))
        elif tok.startswith("*"):
            out.append((tok[1:-1], "italic"))
        else:                                     # [label](href) -> label, link
            label = tok[1:tok.index("](")]
            out.append((label, "link"))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], "body"))
    return out or [("", "body")]


def _atom_width(word, kind, size):
    sz = size - 0.5 if kind == "code" else size
    fam = MONO if kind == "code" else SERIF
    return measure_text(word, font_family=fam, font_size=sz, bold=(kind == "bold"))


def atoms(text):
    """Flatten a rich string to (word, kind, space_before) atoms — words keep
    their run's style; whitespace collapses into the next word's space flag."""
    out = []
    pending = False
    for seg, kind in runs(text):
        for part in _re.split(r"(\s+)", seg):
            if part == "":
                continue
            if part.isspace():
                pending = True
            else:
                out.append((part, kind, pending))
                pending = False
    return out


def wrap_atoms(text, width, size):
    """Greedy word-wrap that respects run styles; returns lines of atoms."""
    sw = measure_text(" ", font_family=SERIF, font_size=size)
    lines, cur, cw = [], [], 0.0
    for word, kind, sp in atoms(text):
        wsp = sw if (cur and sp) else 0.0
        ww = _atom_width(word, kind, size)
        if cur and cw + wsp + ww > width:
            lines.append(cur)
            cur, cw = [(word, kind, False)], ww
        else:
            cur.append((word, kind, sp))
            cw += wsp + ww
    if cur:
        lines.append(cur)
    return lines or [[]]


def nbsp(text):
    """Render runs of spaces as non-breaking spaces so SVG/HTML does not collapse
    the leading indentation and comment alignment of a code or formula line.
    Monospace fonts advance NBSP exactly like a space, so columns stay true."""
    return text.replace(" ", " ")


def _span_style(kind, size, color):
    if kind == "code":
        return ts(size - 0.5, CODE_INK, family=MONO)
    if kind == "bold":
        return ts(size, INK, weight=700)
    if kind == "italic":
        return ts(size, color, style="italic")
    if kind == "link":
        return ts(size, ACCENT_MID, weight=600)
    return ts(size, color)


def line_spans(line, size, color):
    """Turn one wrapped line of atoms into a model ``spans`` list — adjacent
    same-kind atoms merge into one span; the inter-run space rides on the left
    run (it is blank, so its style is irrelevant)."""
    spans, cur_kind, cur_text = [], None, ""
    for i, (word, kind, sp) in enumerate(line):
        sep = " " if (i > 0 and sp) else ""
        if cur_text == "":
            cur_kind, cur_text = kind, word
        elif kind == cur_kind:
            cur_text += sep + word
        else:
            spans.append({"text": cur_text + sep, "style": _span_style(cur_kind, size, color)})
            cur_kind, cur_text = kind, word
    if cur_text:
        spans.append({"text": cur_text, "style": _span_style(cur_kind, size, color)})
    return spans


# --------------------------------------------------------------------------- #
# The composer — a cursor that paginates blocks into absolute coordinates.
# --------------------------------------------------------------------------- #
class Book:
    def __init__(self, title, subtitle):
        self.b = DocumentBuilder(title=title, profile="book", lang="en")
        self.title = title
        self.subtitle = subtitle
        self.running = ""                  # running-head section label
        self.page = None
        self._seq = 0                      # unique page id counter
        self.pno = 0                       # folio (printed page number)
        self.folio = False                 # does the current page show a folio?
        self.y = TOP
        self._pages = []

    # -- page lifecycle ----------------------------------------------------- #
    def new_page(self, *, chrome=True, folio=True):
        self._seq += 1
        pid = f"p{self._seq:02d}"
        if folio:
            self.pno += 1
        self.folio = folio
        pg = self.b.page(pid, canvas={"size": [PAGE_W, PAGE_H], "units": "px"},
                         coordinate_mode="absolute")
        pg.layer("bg")
        pg.rect([0, 0, PAGE_W, PAGE_H], fill=PAPER)
        pg.layer("body")
        # All loose page text is prose / labels, never tabular data: declare the
        # whole page as lettering so the tabular-box-model heuristic does not
        # misread the reading column as a table.
        pg._lettering_depth += 1
        self.page = pg
        self.y = TOP
        if chrome:
            self._chrome()
        self._pages.append(pg)
        return pg

    def _chrome(self):
        pg = self.page
        # Running head: chapter short-title (verso/recto symmetric), folio.
        pg.rect([MX, HEAD_Y + 14, CONTENT_W, 1.0], fill=LINE)
        pg.text([MX, HEAD_Y, CONTENT_W - 60, 14],
                "LAYOUT METHODS — A FIELD GUIDE",
                style=ts(8.5, FAINT, family=SANS, weight=700, spacing=1.6,
                         transform="uppercase"))
        if self.running:
            pg.text([MX, HEAD_Y, CONTENT_W, 14], self.running,
                    style=ts(8.5, ACCENT_MID, family=SANS, weight=700, spacing=1.4,
                             align="right", transform="uppercase"))
        # Folio, bottom-centre.
        if self.folio:
            pg.text([MX, PAGE_H - 56, CONTENT_W, 14], str(self.pno),
                    style=ts(9.5, FAINT, family=SANS, align="center"))

    def ensure(self, h):
        """Guarantee ``h`` px of vertical room on the current page."""
        if self.page is None or self.y + h > BOTTOM:
            self.new_page()

    def space(self, dh):
        self.y += dh

    # -- block emitters ----------------------------------------------------- #
    def section(self, num, title, running, *, keep=96):
        """A numbered §-heading: starts a new page if the heading would be
        orphaned. ``keep`` is the room reserved for the first following block,
        so a heading is never separated from the content it introduces."""
        self.running = running
        need = 30 + 34 + 26 + keep          # heading + rule + first content block
        if self.y + need > BOTTOM:
            self.new_page()
        else:
            self.space(14)
        pg = self.page
        pg.text([MX, self.y, CONTENT_W, 16], num,
                style=ts(12, ACCENT_MID, family=SANS, weight=800, spacing=1.4))
        self.y += 20
        for ln in wrap_text(title, width=CONTENT_W, font_family=SANS,
                            font_size=23, bold=True):
            pg.text([MX, self.y, CONTENT_W, 30], ln,
                    style=ts(23, INK, family=SANS, weight=800, spacing=-0.3))
            self.y += 30
        self.y += 4
        pg.rect([MX, self.y, CONTENT_W, 2.0], fill=ACCENT)
        self.y += 18

    def subsection(self, title):
        self.ensure(26 + 22 + 70)          # keep the sub-heading with its first lines
        pg = self.page
        self.space(6)
        pg.text([MX, self.y, CONTENT_W, 20], title,
                style=ts(15, ACCENT, family=SANS, weight=800, spacing=-0.2))
        self.y += 26

    def para(self, text, *, size=BODY_SIZE, color=INK, lh=BODY_LH, gap=10,
             indent=0):
        """Flow a rich paragraph, breaking across pages line by line.

        Each wrapped line is emitted as ONE text object carrying styled
        ``spans``, so the renderer flows the bold/italic/mono runs with its own
        glyph metrics — author-side measurement only decides the wrap points,
        never the on-page advance, so inline runs never drift."""
        if self.page is None:
            self.new_page()
        base = ts(size, color)
        step = size * lh
        # Wrap a hair narrow so the renderer's metrics can never push a line
        # past the measure and force a second, clipped row inside the box.
        lines = wrap_atoms(text, (CONTENT_W - indent) * 0.985, size)
        for line in lines:
            if self.y + step > BOTTOM:
                self.new_page()
            x = MX + indent
            spans = line_spans(line, size, color)
            if spans:
                self.page.add({"type": "text", "box": [x, self.y, CONTENT_W - indent, step],
                               "spans": spans, "style": base})
            self.y += step
        self.y += gap

    def callout(self, text, *, accent=ACCENT, fill=PANEL, size=11, mono=False):
        """A tinted aside with a left accent bar (e.g. the chapter's blockquotes)."""
        fam = MONO if mono else SERIF
        inner_w = CONTENT_W - 28 - 18
        lines = wrap_text(text, width=inner_w, font_family=fam, font_size=size)
        step = size * 1.5
        box_h = step * len(lines) + 24
        self.ensure(box_h + 12)
        pg = self.page
        y0 = self.y
        pg.rect([MX, y0, CONTENT_W, box_h], radius=7, fill=fill)
        pg.rect([MX, y0, 4, box_h], radius=2, fill=accent)
        ty = y0 + 12
        for ln in lines:
            pg.text([MX + 22, ty, inner_w, step], ln,
                    style=ts(size, INK, family=fam, lh=1.5,
                             style="italic" if not mono else None))
            ty += step
        self.y = y0 + box_h + 14

    def code(self, src, *, caption=None):
        """A dark code/formula slab; splits across pages, repeating the slab."""
        raw = src.strip("\n").split("\n")
        pad = 16
        step = CODE_SIZE * CODE_LH
        inner_w = CONTENT_W - 2 * pad
        # Pre-wrap over-long code lines (rare; keeps everything inside the slab).
        lines = []
        for ln in raw:
            w = measure_text(ln, font_family=MONO, font_size=CODE_SIZE)
            if w <= inner_w or ln.strip() == "":
                lines.append(ln)
            else:
                for part in wrap_text(ln, width=inner_w, font_family=MONO,
                                      font_size=CODE_SIZE):
                    lines.append(part)
        i = 0
        while i < len(lines):
            avail = BOTTOM - self.y - 2 * pad - 6
            if avail < step * 3:                  # not enough room — new page
                self.new_page()
                avail = BOTTOM - self.y - 2 * pad - 6
            fit = max(1, int(avail // step))
            chunk = lines[i:i + fit]
            slab_h = step * len(chunk) + 2 * pad
            pg = self.page
            pg.rect([MX, self.y, CONTENT_W, slab_h], radius=8, fill=INKBG)
            ty = self.y + pad
            for ln in chunk:
                pg.text([MX + pad, ty, inner_w, step], nbsp(ln),
                        style=ts(CODE_SIZE, D_BODY, family=MONO, lh=1.0))
                ty += step
            self.y += slab_h + (6 if i + fit < len(lines) else 12)
            i += fit
        if caption:
            self.caption_line(caption)

    def caption_line(self, text):
        self.ensure(28)
        for ln in wrap_text(text, width=CONTENT_W, font_family=SANS, font_size=9.5):
            self.page.text([MX, self.y, CONTENT_W, 13], ln,
                           style=ts(9.5, MUTE, family=SANS, lh=1.3))
            self.y += 14
        self.y += 8

    def table(self, headers, rows, *, weights=None, row_height=30, header_height=34):
        """A real TableObject via the widgets table helper, themed to the book."""
        from dataclasses import replace
        from framegraph.sdk.widgets import default_theme
        n = len(headers)
        weights = weights or [1.0] * n
        tot = sum(weights)
        cols = [{"label": h, "width": f"{100 * w / tot:.3f}%"}
                for h, w in zip(headers, weights)]
        th = replace(default_theme(), font=tuple(SANS), mono=tuple(MONO),
                     ink=INK, sub=MUTE, muted=FAINT, line=LINE,
                     accent=ACCENT, accent_soft=PANEL, surface=PAPER,
                     surface_alt="#F7F8FA", fill=PANEL)
        est = header_height + row_height * len(rows)
        self.ensure(est + 16)
        self.page.table([MX, self.y, CONTENT_W, est], cols, rows,
                        zebra=True, row_height=row_height,
                        header_height=header_height, theme=th)
        self.y += est + 18

    def figure(self, fig_id, number, title, *, caption=None, fig_w=None):
        """Embed a standalone plate, scaled into the column, keep-together."""
        fn = dict(plates.FIGURES)[fig_id]
        ref = FigureRef.from_callable(fn)
        content = ref.load()
        fw = fig_w or CONTENT_W
        scaled_h = fw * content.source_box[3] / content.source_box[2]
        fx = MX + (CONTENT_W - fw) / 2
        cap_h = 0
        if caption:
            cap_h = 8 + 14 * len(wrap_text(f"Figure {number} — {caption}",
                                           width=CONTENT_W, font_family=SANS,
                                           font_size=9.5))
        block_h = 20 + scaled_h + 10 + cap_h
        # Keep the whole plate (and its caption) together on one page.
        if self.y + block_h > BOTTOM:
            self.new_page()
        pg = self.page
        pg.text([MX, self.y, CONTENT_W, 14], f"FIGURE {number}",
                style=ts(9, ACCENT_MID, family=SANS, weight=800, spacing=2.0,
                         transform="uppercase"))
        pg.text([MX + 86, self.y, CONTENT_W - 86, 14], title,
                style=ts(9.5, MUTE, family=SANS, weight=600))
        self.y += 20
        pg.figure(ref, [fx, self.y, fw, scaled_h], fit="contain", align="top-left", decorative=True)
        pg.rect([fx, self.y, fw, scaled_h], fill="none", stroke=LINE,
                stroke_style={"stroke_width": 1.0}, radius=6)
        self.y += scaled_h + 10
        if caption:
            for j, ln in enumerate(wrap_text(f"Figure {number} — {caption}",
                                             width=CONTENT_W, font_family=SANS,
                                             font_size=9.5)):
                self.page.text([MX, self.y, CONTENT_W, 13], ln,
                               style=ts(9.5, MUTE, family=SANS, lh=1.35,
                                        style="italic" if j else None))
                self.y += 14
        self.y += 14

    def bullets(self, items, *, size=BODY_SIZE, lh=BODY_LH, gap=10, ordered=False):
        """A bulleted / numbered list; each item is rich text, wraps + paginates."""
        step = size * lh
        marker_w = 26
        for k, item in enumerate(items):
            mark = f"{k + 1}." if ordered else "•"
            lines = wrap_atoms(item, (CONTENT_W - marker_w) * 0.985, size)
            for li, line in enumerate(lines):
                if self.y + step > BOTTOM:
                    self.new_page()
                if li == 0:
                    self.page.text([MX, self.y, marker_w, step], mark,
                                   style=ts(size, ACCENT_MID, family=SANS,
                                            weight=700 if ordered else 400,
                                            align="left"))
                spans = line_spans(line, size, INK)
                if spans:
                    self.page.add({"type": "text",
                                   "box": [MX + marker_w, self.y, CONTENT_W - marker_w, step],
                                   "spans": spans, "style": ts(size, INK)})
                self.y += step
            self.y += 4
        self.y += gap - 4

    def formula(self, src, *, caption=None):
        """A light, centered formula/identity slab (for the at-a-glance math)."""
        raw = src.strip("\n").split("\n")
        size = 10.5
        step = size * 1.5
        pad = 14
        slab_h = step * len(raw) + 2 * pad
        self.ensure(slab_h + 14)
        pg = self.page
        pg.rect([MX, self.y, CONTENT_W, slab_h], radius=8, fill="#F7F8FA",
                stroke=LINE, stroke_style={"stroke_width": 1.0})
        ty = self.y + pad
        for ln in raw:
            pg.text([MX + pad, ty, CONTENT_W - 2 * pad, step], nbsp(ln),
                    style=ts(size, "#33414F", family=MONO, lh=1.0))
            ty += step
        self.y += slab_h + 12
        if caption:
            self.caption_line(caption)

    def cover(self, *, kicker, title, subtitle, author, date, note, epigraph):
        """The chapter's title page — no running head, no folio."""
        self.new_page(chrome=False, folio=False)
        pg = self.page
        pg.rect([0, 0, PAGE_W, 8], fill=ACCENT)
        y = 250
        pg.rect([MX, y, 46, 3.4], fill=ACCENT)
        pg.text([MX, y + 16, CONTENT_W, 16], kicker,
                style=ts(11, ACCENT_MID, family=SANS, weight=800, spacing=3.0,
                         transform="uppercase"))
        y += 52
        for ln in wrap_text(title, width=CONTENT_W, font_family=SANS,
                            font_size=46, bold=True):
            pg.text([MX, y, CONTENT_W, 58], ln,
                    style=ts(46, INK, family=SANS, weight=800, spacing=-1.2))
            y += 56
        y += 8
        for ln in wrap_text(subtitle, width=CONTENT_W - 40, font_family=SERIF,
                            font_size=17):
            pg.text([MX, y, CONTENT_W - 40, 24], ln,
                    style=ts(17, MUTE, family=SERIF, style="italic", lh=1.4))
            y += 25
        y += 26
        pg.rect([MX, y, CONTENT_W, 1.0], fill=RULE)
        y += 16
        pg.text([MX, y, CONTENT_W, 16], author,
                style=ts(11.5, INK, family=SANS, weight=700))
        pg.text([MX, y, CONTENT_W, 16], date,
                style=ts(11.5, MUTE, family=SANS, align="right"))
        y += 40
        for ln in wrap_text(note, width=CONTENT_W, font_family=SERIF, font_size=11):
            pg.text([MX, y, CONTENT_W, 16], ln, style=ts(11, MUTE, family=SERIF, lh=1.5))
            y += 17
        # Epigraph, lower third.
        ey = 880
        pg.rect([MX, ey, 4, 70], radius=2, fill=ACCENT)
        for ln in wrap_text(epigraph, width=CONTENT_W - 30, font_family=SERIF,
                            font_size=13):
            pg.text([MX + 22, ey, CONTENT_W - 30, 20], ln,
                    style=ts(13, INK, family=SERIF, style="italic", lh=1.5))
            ey += 20
        self.y = BOTTOM + 1            # force the first section onto a fresh page

    def colophon(self, lines):
        """A closing note page carrying the disclaimer / provenance."""
        self.new_page()
        self.running = "Colophon"
        self.subsection("Colophon & disclaimer")
        for label, body in lines:
            self.ensure(20)
            self.page.text([MX, self.y, CONTENT_W, 14], label,
                           style=ts(10, ACCENT_MID, family=SANS, weight=800,
                                    spacing=1.4, transform="uppercase"))
            self.y += 18
            self.para(body, size=10.5, color=MUTE, lh=1.55, gap=14)

    # -- finalize ----------------------------------------------------------- #
    def build(self):
        return self.b.build()


# --------------------------------------------------------------------------- #
# The chapter — every section, code block, table, formula, callout and plate,
# composed as one paginated FrameGraph book.
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    bk = Book("Layout Methods — A Field Guide",
              "A book chapter, grounded in the FrameGraph architecture map")

    # ---- Title page ------------------------------------------------------- #
    bk.cover(
        kicker="FrameGraph · A Field Guide",
        title="Layout Methods",
        subtitle="A field guide, grounded in the FrameGraph architecture map — "
                 "from one hand-placed node up to the solvers, and back down.",
        author="Prepared with Claude · Opus 4.8",
        date="2026-06-24",
        note="A field guide written to one reader — the author of FrameGraph's "
             "architecture map. Fourteen plates illustrate it, each a single "
             "absolute-mode page authored through the FrameGraph SDK: the system "
             "drawing the very layout methods it is built on. This entire chapter "
             "is, in turn, one FrameGraph document — its prose, code, tables and "
             "plates lowered to absolute coordinates by a thin composer.",
        epigraph="Author intent high; lower it to a single canonical "
                 "representation; render that. The same move sdk.expand already "
                 "makes for builders, applied to coordinates.",
    )

    # ---- §0 --------------------------------------------------------------- #
    bk.section("§ 0", "Where your example actually sits", "§0 · Absolute")
    bk.para("Your map uses **absolute placement**. Every visual object is given "
            "explicit `[x, y, w, h]` pixel coordinates, and the two helpers that "
            "look like layout primitives are really just *coordinate arithmetic*:")
    bk.code(
        "def node(page, box, palette, title, ..., subs, ...):\n"
        "    x, y, w, h = box\n"
        "    page.rect([x, y, w, h], ...)                 # the box itself\n"
        "    page.text([x + 14, y + 9, w - 26, 17], title)  # padding 14/12/9\n"
        "    for i, line in enumerate(subs):\n"
        "        page.text([x + 14, y + 30 + i * 14, ...], line)  # vstack, step 14"
    )
    bk.figure("fig-00-absolute", 1, "Absolute placement, dissected",
              caption="A single hand-placed node already carries an implicit box "
                      "model (the dashed content inset) and an implicit vertical "
                      "flow (the stacked sub-lines). The padding and the line "
                      "advance are computed by hand — exactly the arithmetic every "
                      "method in this chapter eventually formalises, or lowers back "
                      "down to.")
    bk.para("Two things are worth naming precisely, because they recur all the way "
            "up the abstraction ladder:")
    bk.bullets([
        "**You already have a box model.** `x + 14` / `w - 26` are *padding*. "
        "The inner content rectangle is `[x+14, y+9, w-26, h-…]`. Every layout "
        "system above this one formalizes exactly that inset arithmetic.",
        "**You already have flow.** `y + 30 + i*14` is a vertical stack with a "
        "fixed line advance of 14px. Your `gen_rows` is a single-column grid: row "
        "height 42 + gap 8 = stride 50. These are vstacks and grids — you are just "
        "computing their offsets by hand instead of asking a primitive to do it.",
    ])
    bk.para("So the honest assessment: for a small, curated, semantically-arranged "
            "diagram like this one, absolute placement is the *correct* method, not "
            "a deficiency. Automatic graph layout (§7) would actively destroy your "
            "intentional grouping. The value of learning the other methods is (a) to "
            "compute the offsets you now hard-code, and (b) to know when curation "
            "stops paying off and a solver should take over.")
    bk.table(
        ["Property", "Absolute placement (your file)"],
        [["Control", "Total — pixel-exact"],
         ["Effort", "O(elements) of manual arithmetic"],
         ["Adapts to content size changes", "No — magic numbers go stale"],
         ["Adapts to data-driven counts", "Poorly — you re-derive every y"],
         ["Right when", "Small, fixed, hand-curated, meaning-bearing diagrams"],
         ["Wrong when", "Content length is dynamic, or N is large / unknown"]],
        weights=[1.0, 1.7],
    )

    # ---- §1 --------------------------------------------------------------- #
    bk.section("§ 1", "The layout problem, stated once", "§1 · The problem")
    bk.callout("Given a set of objects, each with an intrinsic or desired size and "
               "a set of relationships or constraints among them, assign every "
               "object a final position and size in a coordinate space such that "
               "the constraints are satisfied — or, if they cannot all be "
               "satisfied, such that a stated objective is minimized.")
    bk.para("Every method below is a different answer to two questions. *Who "
            "computes the coordinates?* You, by formula (absolute, flow, grid), or "
            "a solver, from declared relations (constraints, graph layout, "
            "force-directed). And *what is being optimized?* Nothing (you place "
            "it), a local packing rule (flow / flex / grid), a global cost "
            "(Knuth–Plass, force-directed, crossing minimization), or a feasibility "
            "region (constraints).")
    bk.figure("fig-01-ladder", 2, "The ladder of layout methods",
              caption="Climbing a rung trades manual control for the machine "
                      "inferring positions from higher-level intent. The right "
                      "panel groups the rungs by what, if anything, each one "
                      "optimises — from nothing (absolute) to a global energy "
                      "(force-directed).")
    bk.para("The methods form a ladder. Each rung trades manual control for the "
            "machine working out positions from higher-level intent. Your SDK "
            "already embodies this pattern in a different dimension — `sdk.expand` "
            "*lowers* high-level builders to the model. Layout primitives are the "
            "same move applied to coordinates: author intent high, lower to "
            "absolute, render.")

    # ---- §2 --------------------------------------------------------------- #
    bk.section("§ 2", "Box model — the first abstraction over absolute",
               "§2 · Box model")
    bk.para("The box model turns four nested rectangles into named space: "
            "`margin → border → padding → content`. For a box at outer "
            "`[x, y, w, h]` with padding `p` on all sides, "
            "`content = [x + p, y + p, w - 2p, h - 2p]`.")
    bk.figure("fig-02-box-model", 3, "The box model",
              caption="margin → border → padding → content. The content rectangle "
                      "is a single inset of the outer box; the SDK ships exactly "
                      "this as `layout.inset()`. Once `content()` exists, every "
                      "later method operates inside it.")
    bk.para("Your `node()` is a box model with asymmetric padding (left = right, "
            "top = 9). Formalizing it removes the magic numbers:")
    bk.code(
        "interface Insets { top: number; right: number; bottom: number; left: number; }\n"
        "type Box = { x: number; y: number; w: number; h: number };\n"
        "\n"
        "function content(box: Box, p: Insets): Box {\n"
        "  return {\n"
        "    x: box.x + p.left,\n"
        "    y: box.y + p.top,\n"
        "    w: box.w - p.left - p.right,\n"
        "    h: box.h - p.top - p.bottom,\n"
        "  };\n"
        "}"
    )
    bk.para("Once you have `content()`, every method below operates inside it.")

    # ---- §3 --------------------------------------------------------------- #
    bk.section("§ 3", "Flow layout — 1D document flow + line breaking",
               "§3 · Flow")
    bk.para("Flow places objects one after another along a writing axis, wrapping "
            "to a new line when the current one is full. Your subline loop is "
            "manual flow; real text flow adds *line breaking*, which has two "
            "regimes.")
    bk.para("**Greedy (first-fit).** Put as many words on a line as fit, then "
            "break. Simple, local, fast. This is what most naive wrappers — and "
            "your sublines, implicitly — do.")
    bk.code(
        "function greedyWrap(\n"
        "  words: string[], maxWidth: number,\n"
        "  measure: (s: string) => number, spaceWidth: number,\n"
        "): string[][] {\n"
        "  const lines: string[][] = [];\n"
        "  let line: string[] = []; let width = 0;\n"
        "  for (const w of words) {\n"
        "    const ww = measure(w);\n"
        "    const advance = line.length === 0 ? ww : spaceWidth + ww;\n"
        "    if (width + advance > maxWidth && line.length > 0) {\n"
        "      lines.push(line); line = [w]; width = ww;\n"
        "    } else { line.push(w); width += advance; }\n"
        "  }\n"
        "  if (line.length) lines.push(line);\n"
        "  return lines;\n"
        "}"
    )
    bk.para("**Optimal (Knuth–Plass).** Greedy makes one ugly line to spare the "
            "next; optimal breaking minimizes a *global* cost over the whole "
            "paragraph. It defines a per-line **badness** from how much the "
            "inter-word glue must stretch or shrink, then **demerits** that add "
            "penalties (hyphenation, consecutive hyphens, adjacent lines of very "
            "different tightness). The total cost is the sum of squared demerits, "
            "and the optimum is a shortest path over feasible breakpoints by "
            "dynamic programming. This is the algorithm in TeX, and it is why TeX "
            "paragraphs look more even than a browser's.")
    bk.figure("fig-03-line-breaking", 4, "Greedy vs optimal line breaking",
              caption="Greedy fills each line locally and leaves ragged, uneven "
                      "space; Knuth–Plass minimises a global cost — per-line "
                      "badness grows as roughly the cube of the stretch ratio — to "
                      "balance the whole paragraph.")
    bk.para("The shape of the cost (constants are TeX-specific; treat as "
            "illustrative):")
    bk.formula(
        "adjustment ratio r = (desired - natural) / (stretch or shrink)\n"
        "badness b          ≈ 100 · |r|³\n"
        "line demerits      ≈ (linePenalty + b)²  + penalty terms\n"
        "total              = Σ line demerits   → minimize by DP / shortest path"
    )
    bk.para("When to reach for which: greedy for labels, captions, and any "
            "single-pass UI text; Knuth–Plass when justified, multi-line typography "
            "quality matters (print, PDF). Relevant to you because the flow-mode "
            "engine your map flags as the weaker of its two paradigms is exactly "
            "this problem — naive pagination is greedy flow without the global "
            "objective.")

    # ---- §4 --------------------------------------------------------------- #
    bk.section("§ 4", "Stack / linear layout — Flexbox (1D distribution)",
               "§4 · Flexbox")
    bk.para("Flexbox is the modern formalization of “lay items along one axis "
            "and distribute the leftover space.” The **main axis** is the one "
            "items flow along; the **cross axis** is perpendicular. Each item has a "
            "`flex-basis` (its starting main size), a `flex-grow` (share of "
            "*surplus*), and a `flex-shrink` (share of *deficit*).")
    bk.formula(
        "free = containerMainSize − Σ basis\n"
        "if free ≥ 0:  itemSize = basis + (grow / Σgrow) · free\n"
        "if free < 0:  itemSize = basis + (scaledShrink / Σ scaledShrink) · free\n"
        "              where scaledShrink = shrink · basis"
    )
    bk.figure("fig-04-flexbox", 5, "Flexbox surplus distribution",
              caption="The free space after summing the bases (top row) is shared "
                      "out in proportion to each item's `flex-grow` (bottom row); "
                      "an item with grow = 0 keeps its basis. Shrink is the "
                      "symmetric rule for a deficit.")
    bk.para("The shrink factor is weighted by the basis on purpose: larger items "
            "give up more absolute space, which keeps results visually "
            "proportional.")
    bk.code(
        "interface FlexItem { basis: number; grow: number; shrink: number; }\n"
        "\n"
        "function flexMainSizes(items: FlexItem[], container: number): number[] {\n"
        "  const totalBasis = items.reduce((s, i) => s + i.basis, 0);\n"
        "  const free = container - totalBasis;\n"
        "  if (free >= 0) {\n"
        "    const totalGrow = items.reduce((s, i) => s + i.grow, 0) || 1;\n"
        "    return items.map(i => i.basis + (i.grow / totalGrow) * free);\n"
        "  }\n"
        "  const scaled = items.map(i => i.shrink * i.basis);\n"
        "  const total = scaled.reduce((a, b) => a + b, 0) || 1;\n"
        "  return items.map((i, k) => i.basis + (scaled[k] / total) * free);\n"
        "}"
    )
    bk.para("Caveat for honesty: the real algorithm also clamps each item to its "
            "min/max-content size and *freezes* clamped items, then redistributes "
            "among the rest — an iterative loop, not the single pass above. The "
            "single pass is the mental model; the loop is the spec.")
    bk.para("Tie-in: your governance gate list, legend, and tension band are all "
            "fixed-stride vstacks — a flex column with `gap` and no grow / shrink. "
            "If you wrapped that in a `vstack(items, gap)` macro, the constant "
            "`+ i*18` / `+ i*24` strides would be *computed*, and adding a gate "
            "would not require re-typing offsets.")

    # ---- §5 --------------------------------------------------------------- #
    bk.section("§ 5", "Grid / table layout (2D)", "§5 · Grid")
    bk.para("Grid generalizes flex to two axes: you define **tracks** (rows and "
            "columns), each sized as fixed px, a content-derived size, or a "
            "fraction (`fr`) of leftover space, and then place items into cells, "
            "optionally spanning several. The sizing of `fr` tracks is the same "
            "surplus-distribution idea as flex-grow, applied to each axis.")
    bk.para("Resolving track *positions* once track *sizes* are known is trivial — "
            "and it is exactly what your `gen_rows` does by hand:")
    bk.code(
        "function trackOffsets(sizes: number[], gap: number, start = 0): number[] {\n"
        "  const offsets: number[] = [];\n"
        "  let pos = start;\n"
        "  for (const s of sizes) { offsets.push(pos); pos += s + gap; }\n"
        "  return offsets;\n"
        "}"
    )
    bk.figure("fig-05-grid", 6, "Grid tracks and gen_rows offsets",
              caption="Grid tiles two axes into tracks (left). A single-column grid "
                      "is what `gen_rows` writes out by hand (right): "
                      "`trackOffsets(6 × 42, gap 8, start 124)` reproduces the "
                      "file's hard-typed y values exactly — so a seventh row would "
                      "cost no arithmetic.")
    bk.para("Your six generated-view cards: height 42, gap 8, starting at y = 124. "
            "So `trackOffsets(Array(6).fill(42), 8, 124)` returns "
            "`[124, 174, 224, 274, 324, 374]` — identical to your hand-typed "
            "values. That equality is the whole lesson: you have a 1-column grid "
            "written out longhand, and a `grid` (or even `vstack`) primitive would "
            "emit those numbers from `(count, rowHeight, gap, start)`.")
    bk.para("When grid beats flex: genuine 2D alignment, where items in different "
            "rows must share column edges (tables, dashboards, your legend "
            "swatches-and-labels). When flex beats grid: a single axis with "
            "content-driven distribution.")

    # ---- §6 --------------------------------------------------------------- #
    bk.section("§ 6", "Constraint-based layout (Cassowary)", "§6 · Constraints")
    bk.para("Instead of computing coordinates, you *declare relationships* and a "
            "solver finds positions that satisfy them. This is the model behind "
            "Apple's Auto Layout, and the Cassowary algorithm (an incremental "
            "simplex method for linear-arithmetic constraints) is its engine; "
            "Kiwi.js is a widely used port. You state things like:")
    bk.code(
        "renderer.centerX == (svcLeft.right + svcRight.left) / 2   // required\n"
        "renderer.left   >= svcLeft.right + 16                     // required gap\n"
        "legend.top      == model.bottom + 24    weight: strong    // preferred"
    )
    bk.figure("fig-06-constraints", 7, "Constraint-based layout",
              caption="Strengths order the solve: `required` must hold; "
                      "`strong` / `medium` / `weak` resolve any remaining slack or "
                      "conflict. The solver maintains the solution incrementally, so "
                      "editing one constraint re-solves cheaply.")
    bk.para("Where this would help your map: the brittle parts are the "
            "relationships you encoded as coincident magic numbers — the renderer "
            "box at `[428, 574, 484, 58]` sitting above two service boxes. A "
            "constraint engine lets you say “centered, with ≥16px gaps, "
            "services equal width” once; resize the page and it re-solves. For "
            "a static one-page export, that cost is rarely worth it — for a "
            "resizable interactive canvas, it is.")

    # ---- §7 --------------------------------------------------------------- #
    bk.section("§ 7", "Graph & diagram layout", "§7 · Graphs")
    bk.para("Your artifact *is* a node-and-edge graph: boxes wired by data-flow and "
            "governing edges. So this family deserves the most attention. The "
            "defining shift: positions are produced by an algorithm reading the "
            "**graph structure**, not by you reading a ruler.")

    bk.subsection("7a · Tree layout — Reingold–Tilford / Walker / Buchheim")
    bk.para("For data that is a tree, the classic aesthetic rules are: nodes at the "
            "same depth share a horizontal line; a parent is centered over its "
            "children; isomorphic subtrees are drawn identically; and the drawing "
            "is as narrow as those rules allow. Reingold–Tilford achieves this in "
            "linear time using **contours** — the left/right silhouettes of a "
            "subtree — shifting sibling subtrees apart only as far as their facing "
            "contours require.")
    bk.figure("fig-07a-tree", 8, "Reingold–Tilford tree layout",
              caption="Nodes at equal depth share a line and each parent is centred "
                      "over its children; the dashed contours are the subtree "
                      "silhouettes the algorithm walks to push siblings apart only "
                      "as far as they must — in linear time after "
                      "Buchheim–Jünger–Leipert.")
    bk.para("Walker generalized this to n-ary trees; his original had an accidental "
            "O(n²) case that Buchheim, Jünger and Leipert corrected back to O(n). "
            "Reach for tree layout whenever the relation is strictly hierarchical "
            "(org charts, ASTs, your SDK's `expand` lowering tree, file systems).")

    bk.subsection("7b · Layered / hierarchical layout — Sugiyama; Graphviz dot")
    bk.para("For a directed acyclic graph with a sense of “flow” — which "
            "is what your map is (authoring → model → views, left to right; model → "
            "renderer, top to bottom) — the Sugiyama framework is the standard. "
            "Four phases:")
    bk.bullets([
        "**Cycle removal.** Temporarily reverse a minimal set of edges to make the "
        "graph acyclic.",
        "**Layer assignment.** Put each node in a rank so edges point one way "
        "(longest-path is simple; network-simplex minimizes total edge length).",
        "**Crossing minimization.** Order nodes within each layer to reduce "
        "crossings. Exact minimization is NP-hard, so the median / barycenter "
        "heuristic is used.",
        "**Coordinate assignment.** Give nodes x-coordinates that keep edges "
        "straight, then route edges (splines through dummy nodes for edges that "
        "skip layers).",
    ], ordered=True)
    bk.figure("fig-07b-sugiyama", 9, "Sugiyama layered layout",
              caption="Assign nodes to ranks, then order within each rank to "
                      "minimise edge crossings, inserting dummy nodes for edges "
                      "that skip a layer. It optimises a geometric objective — not "
                      "the semantic placement a hand-curated map encodes.")
    bk.para("Graphviz `dot` is a mature implementation of a variant of this. Your "
            "map is, structurally, a hand-laid layered graph. A Sugiyama engine "
            "would assign the layers and minimize crossings for free — but it would "
            "*not* know that “governance” belongs visually bottom-left for "
            "narrative reasons. That is the crux of the curation-versus-automation "
            "tradeoff: automatic layout optimizes a geometric objective, not your "
            "semantic one.")

    bk.subsection("7c · Force-directed — Eades; Fruchterman–Reingold; Kamada–Kawai")
    bk.para("When the graph has no inherent hierarchy and you want clusters to "
            "emerge, simulate physics: nodes repel each other (like charges), edges "
            "pull their endpoints together (like springs), and the system relaxes "
            "toward low energy.")
    bk.figure("fig-07c-force", 10, "Force-directed layout",
              caption="Edges act as springs pulling endpoints together while every "
                      "node pair repels, and the system cools toward a low-energy "
                      "configuration in which clusters emerge. Barnes–Hut "
                      "approximation makes the repulsion step tractable at scale.")
    bk.para("Fruchterman–Reingold's forces, with ideal edge length "
            "`k = C·√(area / |V|)`:")
    bk.formula(
        "attractive (along edges):   f_a(d) = d² / k\n"
        "repulsive (all node pairs): f_r(d) = −k² / d\n"
        "per iteration: sum forces, move each node, cap displacement by a\n"
        "               \"temperature\" that cools over time (annealing)."
    )
    bk.para("Kamada–Kawai instead minimizes a **stress** energy using "
            "graph-theoretic (shortest-path) distances `d_ij`, so geometric "
            "distance tracks graph distance: "
            "`E = Σ (1/d_ij²)(‖p_i − p_j‖ − d_ij)²`. The naive repulsion step is "
            "O(n²) per iteration; the Barnes–Hut approximation groups distant nodes "
            "into a quadtree to reach O(n log n), which is what makes large force "
            "layouts (d3-force) tractable. Use force-directed for exploratory "
            "network views — not for a deliberately composed figure like yours.")

    bk.subsection("7d · Edge routing")
    bk.para("Independent of node placement: once nodes are positioned, edges must "
            "be drawn. Your arrows are hand-routed straight segments, which is fine "
            "for a sparse, curated figure. Automatic options are straight-line, "
            "orthogonal (Manhattan, right-angle bends — common in UML and circuit "
            "diagrams), and spline routing through obstacle-avoiding control points "
            "(what `dot` produces). The cost that automation removes here is the "
            "manual collision checking you currently do by eye.")
    bk.figure("fig-07d-edge-routing", 11, "Edge routing",
              caption="The same two endpoints can be wired straight, orthogonally "
                      "(Manhattan), or as an obstacle-avoiding spline. Automation "
                      "replaces the by-eye collision checking that hand-routed "
                      "arrows require.")

    # ---- §8 --------------------------------------------------------------- #
    bk.section("§ 8", "Space-filling layout (treemaps, packing)", "§8 · Packing")
    bk.para("When the goal is to show *quantity* by area inside a bounded region, "
            "not to show connections, use space-filling methods. **Treemaps** map a "
            "hierarchy to nested rectangles whose areas encode a value. The "
            "original *slice-and-dice* alternates split direction by depth, which "
            "produces thin slivers. **Squarified treemaps** instead greedily fill "
            "each row with the children that keep cell aspect ratios closest to 1, "
            "because near-square cells are easier to compare and label.")
    bk.figure("fig-08-treemap", 12, "Slice-and-dice vs squarified treemaps",
              caption="Slice-and-dice (left) alternates split directions and "
                      "produces hard-to-compare slivers; squarified treemaps "
                      "(right) greedily keep each cell close to square. Both panels "
                      "encode the same eight values.")
    bk.para("Not applicable to your architecture map — included so the taxonomy is "
            "complete, and so you can recognize when a problem is “show "
            "proportions in a box” rather than “show structure.”")

    # ---- §9 --------------------------------------------------------------- #
    bk.section("§ 9", "Choosing a method", "§9 · Choosing")
    bk.table(
        ["Situation", "Method", "§"],
        [["Small, fixed, meaning-bearing figure", "Absolute + box model", "2"],
         ["Wrapping label / caption text", "Greedy flow", "3"],
         ["Justified, quality multi-line text", "Knuth–Plass", "3"],
         ["Distribute items along one axis", "Flexbox", "4"],
         ["Align items across two axes", "Grid / table", "5"],
         ["Resizable canvas, relational intent", "Constraints (Cassowary)", "6"],
         ["Strict hierarchy", "Tree (Reingold–Tilford)", "7a"],
         ["Directed flow / DAG", "Layered (Sugiyama / dot)", "7b"],
         ["Network with no hierarchy", "Force-directed", "7c"],
         ["Quantity-by-area", "Treemap / packing", "8"]],
        weights=[2.0, 1.5, 0.4], row_height=27,
    )
    bk.figure("fig-09-decision", 13, "Choosing a method",
              caption="If you can name the structure — tree, DAG, network, "
                      "proportion — use the matching algorithm. If the figure's "
                      "value is human curation of grouping and emphasis, stay with "
                      "absolute placement and borrow only the cheap parts.")
    bk.para("Decision shortcut: if you can *name* the structure (tree, DAG, flow, "
            "network, proportion), use the matching structural algorithm. If the "
            "figure's value comes from *human curation* of grouping and emphasis — "
            "your case — stay with absolute placement and only borrow the cheap "
            "parts (a box model, a `vstack`, a `grid` offset helper) to delete "
            "magic numbers.")

    # ---- §10 -------------------------------------------------------------- #
    bk.section("§ 10", "One concrete rung up for FrameGraph", "§10 · The rung up")
    bk.para("You do not need a constraint solver or a Sugiyama engine. The "
            "highest-value, lowest-risk improvement is a thin layout-primitive "
            "layer that *lowers to the absolute coordinates you already emit* — "
            "mirroring how `sdk.expand` lowers builders into the model:")
    bk.code(
        "# A layout macro that compiles to the absolute calls you write today.\n"
        "def vstack(page, origin, items, gap, render_item):\n"
        "    x, y = origin\n"
        "    for it in items:\n"
        "        h = render_item(page, x, y, it)   # returns height consumed\n"
        "        y += h + gap\n"
        "\n"
        "def grid_offsets(start, count, cell, gap):\n"
        "    return [start + i * (cell + gap) for i in range(count)]"
    )
    bk.figure("fig-10-lowering", 14, "Lowering author intent to absolute",
              caption="A thin primitive layer compiles author-level intent (a "
                      "`vstack`, a `grid_offsets`) down to the absolute coordinates "
                      "the renderer already consumes — the same author-high / "
                      "lower-to-one-representation / render move `sdk.expand` "
                      "already performs.")
    bk.para("This keeps absolute mode as the compile target (so the golden "
            "SHA-256 page locks still apply deterministically), removes the brittle "
            "arithmetic, and makes content-count changes (a seventh generated view, "
            "an extra gate) free. It is the same architectural principle your "
            "codebase already trusts: author high, lower to a single canonical "
            "representation, render that.")
    bk.callout("This very book is that principle, dogfooded twice: the fourteen "
               "plates are absolute-mode FrameGraph pages, and the chapter around "
               "them is one more — its headings, paragraphs, code slabs and tables "
               "all lowered to absolute coordinates by a composer that measures, "
               "wraps, and paginates. Author high; lower to absolute; render.",
               accent=ACCENT)

    # ---- References ------------------------------------------------------- #
    bk.section("§", "References", "References")
    bk.para("*Reproduced from memory; verify bibliographic specifics against the "
            "primary source before citing. All entries are well-known canonical "
            "works.*", size=10.5, color=MUTE)
    bk.bullets([
        "W3C. *CSS Flexible Box Layout Module Level 1.*",
        "W3C. *CSS Grid Layout Module Level 1/2.*",
        "Knuth, D. E., & Plass, M. F. (1981). Breaking Paragraphs into Lines. "
        "*Software: Practice and Experience*, 11(11).",
        "Reingold, E. M., & Tilford, J. S. (1981). Tidier Drawings of Trees. "
        "*IEEE Trans. Software Engineering*, SE-7(2).",
        "Walker, J. Q. (1990). A Node-Positioning Algorithm for General Trees. "
        "*Software: Practice and Experience*, 20(7).",
        "Buchheim, C., Jünger, M., & Leipert, S. (2002). Improving Walker's "
        "Algorithm to Run in Linear Time. *Graph Drawing (GD 2002)*, LNCS 2528.",
        "Sugiyama, K., Tagawa, S., & Toda, M. (1981). Methods for Visual "
        "Understanding of Hierarchical System Structures. *IEEE Trans. SMC*, 11(2).",
        "Gansner, E. R., Koutsofios, E., North, S. C., & Vo, K.-P. (1993). A "
        "Technique for Drawing Directed Graphs. *IEEE Trans. SE*, 19(3).",
        "Eades, P. (1984). A Heuristic for Graph Drawing. *Congressus "
        "Numerantium*, 42.",
        "Fruchterman, T. M. J., & Reingold, E. M. (1991). Graph Drawing by "
        "Force-Directed Placement. *Software: Practice and Experience*, 21(11).",
        "Kamada, T., & Kawai, S. (1989). An Algorithm for Drawing General "
        "Undirected Graphs. *Information Processing Letters*, 31(1).",
        "Barnes, J., & Hut, P. (1986). A Hierarchical O(N log N) Force-Calculation "
        "Algorithm. *Nature*, 324.",
        "Shneiderman, B. (1992). Tree Visualization with Tree-Maps. *ACM Trans. "
        "Graphics*, 11(1).",
        "Bruls, M., Huizing, K., & van Wijk, J. J. (2000). Squarified Treemaps. "
        "*Proc. VisSym*.",
        "Badros, G. J., Borning, A., & Stuckey, P. J. (2001). The Cassowary Linear "
        "Arithmetic Constraint Solving Algorithm. *ACM TOCHI*, 8(4).",
        "Ye, K., et al. (2020). Penrose: From Mathematical Notation to Beautiful "
        "Diagrams. *ACM Trans. Graphics*, 39(4).",
    ], ordered=True, size=10.5, lh=1.45)

    # ---- Appendix A ------------------------------------------------------- #
    bk.section("Appendix A", "Key formulas at a glance", "Appendix A", keep=175)
    bk.formula(
        "Box content:     [x+pL, y+pT, w−pL−pR, h−pT−pB]\n"
        "Flex (surplus):  size = basis + (grow / Σgrow) · free,        free ≥ 0\n"
        "Flex (deficit):  size = basis + (shrink·basis / Σ…) · free,   free < 0\n"
        "Grid offsets:    o[i] = start + Σ_{j<i} (size[j] + gap)\n"
        "Line badness:    b ≈ 100 · |r|³,  r = (desired − natural)/stretch\n"
        "FR forces:       f_a = d²/k,  f_r = −k²/d,  k = C·√(area/|V|)\n"
        "KK stress:       E = Σ (1/d_ij²)(‖p_i − p_j‖ − d_ij)²"
    )

    # ---- Appendix B ------------------------------------------------------- #
    bk.section("Appendix B", "The plates", "Appendix B")
    bk.para("All fourteen plates are authored by `layout_methods_figures.py` and "
            "reused verbatim here. Each is a single absolute-mode FrameGraph page; "
            "the script reuses the SDK's own `inset` / `row` / `column` / `grid` "
            "helpers, so the illustrations are produced by the same box-geometry "
            "primitives §10 recommends — and this book embeds each plate by a single "
            "scale-and-translate group transform.")
    bk.code(
        "uv run python examples/layout_methods_figures.py   # writes _tmp/figures/*.svg\n"
        "uv run python examples/layout_methods_book.py      # writes _tmp/book/*"
    )

    # ---- Colophon --------------------------------------------------------- #
    bk.colophon([
        ("Disclaimer",
         "No information within this chapter should be taken for granted. Any "
         "statement, premise, formula, code sample, or reference not backed by a "
         "real logical definition or a verifiable primary source may be invalid, "
         "erroneous, or a hallucination. The bibliographic specifics in the "
         "References are reproduced from memory and should be checked against the "
         "primary sources. Treat the math and pseudocode as didactic models of the "
         "canonical algorithms, not production-grade implementations. The fourteen "
         "plates are deliberate schematics: they show the *shape* of each method, "
         "not a faithful run of its algorithm."),
        ("Generated by",
         "Claude Opus 4.8 via Claude Code — prose by the model; plates and the book "
         "itself authored through the FrameGraph SDK and rendered by the project's "
         "own SVG proxy. Date: 2026-06-24."),
        ("Provenance",
         "The connections drawn to the source file (coordinate arithmetic, helper "
         "functions, edge routing) are derived from the supplied `architecture_map`. "
         "The algorithm descriptions are standard results from the layout / "
         "graph-drawing / typography literature; see References."),
    ])
    return bk.b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(warns)}")
    for i in report.issues[:40]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    out_dir = os.path.join(ROOT, "_tmp", "book")
    os.makedirs(out_dir, exist_ok=True)
    out_yaml = os.path.join(out_dir, "layout-methods-book.fg.yaml")
    with open(out_yaml, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out_yaml}")
    svgs = render_page_svgs(doc)
    for idx, svg in enumerate(svgs, 1):
        with open(os.path.join(out_dir, f"page-{idx:02d}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
    print(f"Wrote {len(svgs)} page SVG(s) to {out_dir}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
