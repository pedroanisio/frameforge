#!/usr/bin/env python3
"""Typeset & publish *Brand, From Products to Source Code* as a native FrameGraph
book.

This is the publishing pipeline for ``demo/brand-book.md``: a thin composer
*lowers author intent* (a cover, a heading, a paragraph, an evidence tag, a
figure) to the absolute coordinates the FrameGraph renderer consumes, and emits
one multi-page ``mode: page`` document — cover, front matter, two chapters, the
four redrawn plates, back matter and colophon. Nothing here is rendered by an
outside Markdown/HTML pipeline: the cover, the running heads, the measured text
wrapping, the pagination, the colour-coded evidence tags and the figures are all
FrameGraph objects.

The book shares one *imprint identity* with its plates — the seal mark and the
ripple texture come from :mod:`brand_book_figures`, so cover, running heads and
figures read as a single published object. It is its own proof: every figure and
page is real FrameGraph output.

Run from the repository root::

    uv run python examples/brand_book.py     # writes _tmp/brand-book/*

⚠ ARCHITECTURAL CONTRACT (PALS's LAW): the prose is reconciled from LLM-authored
source documents; the figures are LLM-authored. They are validated here against
the model (``build``) and the static rules (``validate_static_rules``); the build
fails loudly on any model error. The book's own evidence tags — SOURCED /
SYNTHESIS / ILLUSTRATIVE / RESEARCH-REQUIRED — mark exactly which claims a reader
must still verify; treat them as load-bearing, not decoration.
"""
from __future__ import annotations

import os
import re as _re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
sys.path.insert(0, HERE)            # so the sibling figures module resolves even
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

import brand_book_figures as plates  # noqa: E402
from brand_book_figures import (  # noqa: E402
    AMBER, BAR, BLUE, CARD, CREAM, EMER, FAINT, GOLD, INDIGO, INK, INKBG,
    LINE, MONO, MUTE, PANEL, PAPER, ROSE, RULE, SANS, SERIF, SLATE, TEAL,
    VIOLET, brand_mark, ripple_field, ts,
)

# --------------------------------------------------------------------------- #
# Page geometry — US Letter at 96 dpi (816 × 1056), the print target.
# --------------------------------------------------------------------------- #
PAGE_W, PAGE_H = 816, 1056
MX = 96                                  # left / right margin
CONTENT_W = PAGE_W - 2 * MX              # 624 px text measure
TOP = 140                                # first baseline region, below running head
BOTTOM = 980                             # last usable y for content
HEAD_Y = 70                              # running-head baseline

BODY_SIZE = 11.5
BODY_LH = 1.52
ACCENT = INDIGO[2]
ACCENT_MID = INDIGO[1]
CODE_INK = "#3A3327"

# Evidence-weight text colours — the book's epistemic colour code, applied both
# in the front-matter legend and inline wherever a tag appears.
TAG_STYLE = {
    "tag_sourced": EMER[2],
    "tag_synth": INDIGO[2],
    "tag_illus": AMBER[2],
    "tag_research": ROSE[2],
}
TAG_KIND = {
    "SOURCED": "tag_sourced",
    "SYNTHESIS": "tag_synth",
    "ILLUSTRATIVE": "tag_illus",
    "RESEARCH-REQUIRED": "tag_research",
}

# --------------------------------------------------------------------------- #
# Inline rich text — a tiny run model so body prose carries true monospace code,
# bold, italic, links and the colour-coded evidence tags without losing the
# measured wrap. Each wrapped line is emitted as ONE text object carrying styled
# ``spans``, so the renderer flows the runs with its own glyph metrics — author
# measurement decides only the wrap points, never the on-page advance.
# --------------------------------------------------------------------------- #
_TAG_RE = r"\[(?:SOURCED|SYNTHESIS|ILLUSTRATIVE|RESEARCH-REQUIRED)[^\]]*\]"
_INLINE_RE = _re.compile(
    rf"({_TAG_RE}|`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))"
)


def _tag_kind(tok):
    inner = tok[1:].lstrip()
    for key, kind in TAG_KIND.items():
        if inner.startswith(key):
            return kind
    return "tag_sourced"


def runs(text):
    """Split a string into (text, kind) runs; kind in body/code/bold/italic/link
    or one of the four tag_* evidence weights."""
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
        elif _re.match(_TAG_RE, tok):
            out.append((tok, _tag_kind(tok)))
        else:                                     # [label](href) -> label, link
            label = tok[1:tok.index("](")]
            out.append((label, "link"))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], "body"))
    return out or [("", "body")]


def _atom_width(word, kind, size):
    if kind == "code":
        return measure_text(word, font_family=MONO, font_size=size - 0.5)
    if kind.startswith("tag"):
        return measure_text(word, font_family=SANS, font_size=size - 0.5, bold=True)
    return measure_text(word, font_family=SERIF, font_size=size,
                        bold=(kind == "bold"))


def atoms(text):
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


_PUNCT = set(".,;:!?)]}’”")


def wrap_atoms(text, width, size):
    sw = measure_text(" ", font_family=SERIF, font_size=size)
    lines, cur, cw = [], [], 0.0
    for word, kind, sp in atoms(text):
        wsp = sw if (cur and sp) else 0.0
        ww = _atom_width(word, kind, size)
        # Trailing punctuation never starts a line — glue it to the current line
        # even if it overflows by a hair, so a period after an evidence tag does
        # not dangle alone at the left margin.
        if cur and not sp and all(c in _PUNCT for c in word):
            cur.append((word, kind, sp))
            cw += ww
            continue
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
    return text.replace(" ", " ")


def _span_style(kind, size, color):
    if kind == "code":
        return ts(size - 0.5, CODE_INK, family=MONO)
    if kind == "bold":
        return ts(size, INK, weight=700)
    if kind == "italic":
        return ts(size, color, style="italic")
    if kind == "link":
        return ts(size, ACCENT_MID, weight=600)
    if kind in TAG_STYLE:
        return ts(size - 0.5, TAG_STYLE[kind], family=SANS, weight=700, spacing=0.2)
    return ts(size, color)


def line_spans(line, size, color):
    spans, cur_kind, cur_text = [], None, ""
    for i, (word, kind, sp) in enumerate(line):
        sep = " " if (i > 0 and sp) else ""
        if cur_text == "":
            cur_kind, cur_text = kind, word
        elif kind == cur_kind:
            cur_text += sep + word
        else:
            spans.append({"text": cur_text + sep,
                          "style": _span_style(cur_kind, size, color)})
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
        self.running = ""
        self.page = None
        self._seq = 0
        self.pno = 0
        self.folio = False
        self.y = TOP
        self._pages = []

    # -- page lifecycle ----------------------------------------------------- #
    def new_page(self, *, chrome=True, folio=True, ground=PAPER):
        self._seq += 1
        pid = f"p{self._seq:02d}"
        if folio:
            self.pno += 1
        self.folio = folio
        pg = self.b.page(pid, canvas={"size": [PAGE_W, PAGE_H], "units": "px"},
                         coordinate_mode="absolute")
        pg.layer("bg")
        pg.rect([0, 0, PAGE_W, PAGE_H], fill=ground)
        pg.layer("body")
        pg._lettering_depth += 1
        self.page = pg
        self.y = TOP
        if chrome:
            self._chrome()
        self._pages.append(pg)
        return pg

    def _chrome(self):
        pg = self.page
        brand_mark(pg, MX + 7, HEAD_Y - 3, 8)
        pg.rect([MX, HEAD_Y + 16, CONTENT_W, 1.0], fill=LINE)
        pg.text([MX + 22, HEAD_Y - 6, CONTENT_W - 60, 14],
                "BRAND — FROM PRODUCTS TO SOURCE CODE",
                style=ts(8.0, FAINT, family=SANS, weight=700, spacing=1.5,
                         transform="uppercase"))
        if self.running:
            pg.text([MX, HEAD_Y - 6, CONTENT_W, 14], self.running,
                    style=ts(8.5, ACCENT_MID, family=SANS, weight=700, spacing=1.2,
                             align="right", transform="uppercase"))
        if self.folio:
            pg.text([MX, PAGE_H - 52, CONTENT_W, 14], str(self.pno),
                    style=ts(9.5, FAINT, family=SANS, align="center"))

    def ensure(self, h):
        if self.page is None or self.y + h > BOTTOM:
            self.new_page()

    def space(self, dh):
        self.y += dh

    # -- block emitters ----------------------------------------------------- #
    def section(self, num, title, running, *, keep=110):
        """A numbered §-heading. The section number is a run-in in a left gutter,
        baseline-aligned with the title's first line — so the number and title
        read as one line, never split across a break. An empty ``num`` renders the
        title alone (used for un-numbered back-matter headings)."""
        self.running = running
        need = 24 + 30 + keep
        if self.y + need > BOTTOM:
            self.new_page()
        else:
            self.space(16)
        pg = self.page
        gutter = 0
        if num:
            gutter = measure_text(num, font_family=SANS, font_size=13,
                                  bold=True) + 14
            pg.text([MX, self.y + 7, gutter, 16], num,
                    style=ts(13, ACCENT_MID, family=SANS, weight=800, spacing=0.4))
        y0 = self.y
        for ln in wrap_text(title, width=CONTENT_W - gutter, font_family=SANS,
                            font_size=22, bold=True):
            pg.text([MX + gutter, y0, CONTENT_W - gutter, 30], ln,
                    style=ts(22, INK, family=SANS, weight=800, spacing=-0.3))
            y0 += 29
        self.y = y0 + 5
        pg.rect([MX, self.y, CONTENT_W, 2.0], fill=GOLD)
        self.y += 18

    def subsection(self, title):
        self.ensure(24 + 22 + 70)
        pg = self.page
        self.space(6)
        pg.text([MX, self.y, CONTENT_W, 20], title,
                style=ts(14.5, ACCENT, family=SANS, weight=800, spacing=-0.2))
        self.y += 25

    def label(self, text):
        """A small uppercase run-in label (Snapshot · Diagnosis · …)."""
        self.ensure(22)
        self.page.text([MX, self.y, CONTENT_W, 14], text,
                       style=ts(9.5, GOLD, family=SANS, weight=800, spacing=1.6,
                                transform="uppercase"))
        self.y += 17

    def para(self, text, *, size=BODY_SIZE, color=INK, lh=BODY_LH, gap=10,
             indent=0):
        if self.page is None:
            self.new_page()
        base = ts(size, color)
        step = size * lh
        lines = wrap_atoms(text, (CONTENT_W - indent) * 0.985, size)
        for line in lines:
            if self.y + step > BOTTOM:
                self.new_page()
            x = MX + indent
            spans = line_spans(line, size, color)
            if spans:
                self.page.add({"type": "text",
                               "box": [x, self.y, CONTENT_W - indent, step],
                               "spans": spans, "style": base})
            self.y += step
        self.y += gap

    def callout(self, text, *, accent=GOLD, fill=PANEL, size=12, lead=None,
                italic=True):
        """A tinted aside with a left accent bar — positioning statements,
        definitions, the book's blockquotes."""
        inner_w = CONTENT_W - 30 - 18
        lines = wrap_atoms(text, inner_w, size)
        step = size * 1.5
        head_h = 20 if lead else 0
        box_h = step * len(lines) + 26 + head_h
        self.ensure(box_h + 12)
        pg = self.page
        y0 = self.y
        pg.rect([MX, y0, CONTENT_W, box_h], radius=8, fill=fill)
        pg.rect([MX, y0, 4, box_h], radius=2, fill=accent)
        ty = y0 + 13
        if lead:
            pg.text([MX + 24, ty, inner_w, 16], lead,
                    style=ts(9.5, accent, family=SANS, weight=800, spacing=1.6,
                             transform="uppercase"))
            ty += head_h
        for line in lines:
            spans = line_spans(line, size, INK)
            if spans:
                for sp in spans:
                    if italic and sp["style"].get("font_style") is None and \
                            sp["style"]["font_family"] == SERIF:
                        sp["style"]["font_style"] = "italic"
                pg.add({"type": "text", "box": [MX + 24, ty, inner_w, step],
                        "spans": spans, "style": ts(size, INK, lh=1.5)})
            ty += step
        self.y = y0 + box_h + 14

    def caption_line(self, text):
        self.ensure(28)
        for ln in wrap_text(text, width=CONTENT_W, font_family=SANS, font_size=9.5):
            self.page.text([MX, self.y, CONTENT_W, 13], ln,
                           style=ts(9.5, MUTE, family=SANS, lh=1.3))
            self.y += 14
        self.y += 8

    def table(self, headers, rows, *, weights=None, row_height=30,
              header_height=34):
        """A real TableObject, restyled to the warm editorial palette. The table
        widget bakes no colours (the renderer otherwise defaults to a saturated
        blue header), so we inject a ``style`` dict directly: an ink header with
        cream labels and warm hairline rules."""
        from framegraph.sdk.widgets import table as _wtable
        n = len(headers)
        weights = weights or [1.0] * n
        tot = sum(weights)
        cols = [{"label": h, "width": f"{100 * w / tot:.3f}%"}
                for h, w in zip(headers, weights)]
        est = header_height + row_height * len(rows)
        self.ensure(est + 16)
        obj = _wtable([MX, self.y, CONTENT_W, est], cols, rows, zebra=True,
                      row_height=row_height, header_height=header_height)
        obj["style"] = {
            "header_fill": INK,
            "header_text": {"color": "#FBFAF6", "font_weight": 700,
                            "font_family": SANS},
            "cell_text": {"color": INK, "font_family": SANS},
        }
        self.page.add(obj)
        self.y += est + 18

    def bullets(self, items, *, size=BODY_SIZE, lh=BODY_LH, gap=10,
                ordered=False):
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
                                   style=ts(size, GOLD if not ordered else ACCENT_MID,
                                            family=SANS,
                                            weight=800 if ordered else 700,
                                            align="left"))
                spans = line_spans(line, size, INK)
                if spans:
                    self.page.add({"type": "text",
                                   "box": [MX + marker_w, self.y,
                                           CONTENT_W - marker_w, step],
                                   "spans": spans, "style": ts(size, INK)})
                self.y += step
            self.y += 4
        self.y += gap - 4

    # -- figures ------------------------------------------------------------ #
    def _fig_ref(self, fig_id):
        fn = dict(plates.FIGURES)[fig_id]
        ref = FigureRef.from_callable(fn)
        return ref, ref.load()

    def figure(self, fig_id, number, title, *, caption=None, fig_w=None):
        """Embed a plate inline, scaled into the column, keep-together."""
        ref, content = self._fig_ref(fig_id)
        fw = fig_w or CONTENT_W
        scaled_h = fw * content.source_box[3] / content.source_box[2]
        fx = MX + (CONTENT_W - fw) / 2
        cap_h = 0
        if caption:
            cap_h = 8 + 14 * len(wrap_text(f"Figure {number} — {caption}",
                                           width=CONTENT_W, font_family=SANS,
                                           font_size=9.5))
        block_h = 22 + scaled_h + 10 + cap_h
        if self.y + block_h > BOTTOM:
            self.new_page()
        pg = self.page
        pg.text([MX, self.y, CONTENT_W, 14], f"FIGURE {number}",
                style=ts(9, GOLD, family=SANS, weight=800, spacing=2.0,
                         transform="uppercase"))
        pg.text([MX + 86, self.y, CONTENT_W - 86, 14], title,
                style=ts(9.5, MUTE, family=SANS, weight=600))
        self.y += 20
        pg.figure(ref, [fx, self.y, fw, scaled_h], fit="contain",
                  align="top-left", decorative=True)
        pg.rect([fx, self.y, fw, scaled_h], fill="none", stroke=LINE,
                stroke_style={"stroke_width": 1.0}, radius=6)
        self.y += scaled_h + 10
        if caption:
            self._caption(number, caption)
        self.y += 12

    def plate_page(self, fig_id, number, title, *, caption=None, running=None):
        """Devote a full page to a tall plate (the gated-process flow), scaled to
        fit the content box by height, centred."""
        if running:
            self.running = running
        self.new_page()
        ref, content = self._fig_ref(fig_id)
        pg = self.page
        pg.text([MX, self.y, CONTENT_W, 14], f"FIGURE {number}",
                style=ts(9, GOLD, family=SANS, weight=800, spacing=2.0,
                         transform="uppercase"))
        pg.text([MX + 86, self.y, CONTENT_W - 86, 14], title,
                style=ts(9.5, MUTE, family=SANS, weight=600))
        self.y += 22
        cap_reserve = 46 if caption else 8
        avail_h = BOTTOM - self.y - cap_reserve
        sw, sh = content.source_box[2], content.source_box[3]
        scale = min(CONTENT_W / sw, avail_h / sh)
        fw, fh = sw * scale, sh * scale
        fx = MX + (CONTENT_W - fw) / 2
        pg.figure(ref, [fx, self.y, fw, fh], fit="contain", align="top-left",
                  decorative=True)
        pg.rect([fx, self.y, fw, fh], fill="none", stroke=LINE,
                stroke_style={"stroke_width": 1.0}, radius=6)
        self.y += fh + 10
        if caption:
            self._caption(number, caption)

    def _caption(self, number, caption):
        for j, ln in enumerate(wrap_text(f"Figure {number} — {caption}",
                                         width=CONTENT_W, font_family=SANS,
                                         font_size=9.5)):
            self.page.text([MX, self.y, CONTENT_W, 13], ln,
                           style=ts(9.5, MUTE, family=SANS, lh=1.35,
                                    style="italic" if j else None))
            self.y += 14

    # -- special pages ------------------------------------------------------ #
    def cover(self, *, imprint, kicker, title_lines, subtitle, thesis,
              meta_line, footer):
        """The composed cover — the book's own thesis as hero art.

        A struck seal in the lower right is the literal *mark* (the word *brand*
        is a burn); from it the five layers radiate outward as concentric rings —
        mark, sign, signal, memory, feeling — the concept stack of §1.1 made
        visible. Radial spokes carry the burn out to a fanned layer index. The
        display title is set over the warm ground; a dark imprint band anchors the
        foot and states the dogfooding claim."""
        import math
        self.new_page(chrome=False, folio=False, ground=CREAM)
        pg = self.page

        # ---- Hero motif: the five-layer stack as rings radiating from the mark.
        scx, scy = 516, 650
        # Faint outer ripple texture (the burn spreading), kept inside the canvas.
        for i in range(7):
            r = 270 - i * 38
            pg.circle([scx, scy], r, fill="none", stroke=LINE,
                      stroke_style={"stroke_width": 1.0})
        # The five layers, inner→outer = mark→feeling, each a tinted ring with a
        # fanned, spoked index label on the open right side.
        layers = [
            (SLATE, "a mark", 92, 56, 70),
            (BLUE, "a sign", 126, 32, 70),
            (TEAL, "a signal", 162, 7, 84),
            (VIOLET, "in memory", 200, -19, 84),
            (INDIGO, "a feeling", 236, -45, 84),
        ]
        for pal, label, r, ang, lw in layers:
            pg.circle([scx, scy], r, fill="none", stroke=pal[1],
                      stroke_style={"stroke_width": 1.6})
            a = math.radians(ang)
            dx, dy = math.cos(a), math.sin(a)
            px, py = scx + r * dx, scy + r * dy
            pg.line([scx + 30 * dx, scy + 30 * dy], [px, py], stroke=pal[0],
                    stroke_style={"stroke_width": 1.2})           # the spoke
            pg.circle([px, py], 5.5, fill=pal[1])                  # the layer node
            pg.text([px + 12, py - 8, lw, 16], label,
                    style=ts(11, pal[2], family=SANS, weight=700, spacing=0.4))
        brand_mark(pg, scx, scy, 26)                              # the struck seal

        # ---- Top imprint band.
        pg.rect([0, 0, PAGE_W, 9], fill=GOLD)
        brand_mark(pg, MX + 12, 96, 17)
        pg.text([MX + 40, 80, 360, 16], imprint,
                style=ts(11, INK, family=SANS, weight=800, spacing=2.6))
        pg.text([MX + 40, 98, 360, 14], "an imprint that typesets itself",
                style=ts(9.5, MUTE, family=SANS, style="italic"))
        pg.text([PAGE_W - MX - 220, 84, 220, 14], "EDITION 1.0 · TWO CHAPTERS",
                style=ts(9.5, FAINT, family=SANS, weight=700, spacing=1.4,
                         align="right"))
        pg.rect([MX, 122, CONTENT_W, 1.0], fill=RULE)

        # ---- Hero title block (upper-left, clear of the lower-right motif).
        y = 232
        pg.rect([MX, y - 34, 54, 4], fill=GOLD)
        pg.text([MX, y - 22, CONTENT_W, 16], kicker,
                style=ts(11.5, ACCENT_MID, family=SANS, weight=800, spacing=3.0,
                         transform="uppercase"))
        sizes = [80, 48, 48]
        for ln, sz in zip(title_lines, sizes):
            pg.text([MX - 2, y, CONTENT_W, sz + 8], ln,
                    style=ts(sz, INK, family=SANS, weight=800, spacing=-1.6))
            y += sz + 4
        y += 12
        for ln in wrap_text(subtitle, width=CONTENT_W - 150, font_family=SERIF,
                            font_size=18):
            pg.text([MX, y, CONTENT_W - 150, 26], ln,
                    style=ts(18, MUTE, family=SERIF, style="italic", lh=1.4))
            y += 25
        y += 22
        # Thesis epigraph.
        pg.rect([MX, y, 4, 62], radius=2, fill=GOLD)
        for ln in wrap_text(thesis, width=CONTENT_W - 190, font_family=SERIF,
                            font_size=15):
            pg.text([MX + 20, y, CONTENT_W - 190, 22], ln,
                    style=ts(15, INK, family=SERIF, style="italic", lh=1.5))
            y += 22

        # ---- Dark imprint band at the foot (the dogfooding claim, reversed out).
        by = 928
        pg.rect([0, by, PAGE_W, PAGE_H - by], fill=INKBG)
        pg.rect([0, by, PAGE_W, 4], fill=GOLD)
        pg.text([MX, by + 26, CONTENT_W, 16], meta_line,
                style=ts(10.5, "#D9D6CE", family=SANS, weight=700, spacing=0.6))
        for j, ln in enumerate(wrap_text(footer, width=CONTENT_W,
                                         font_family=SERIF, font_size=10.5)):
            pg.text([MX, by + 50 + j * 15, CONTENT_W, 16], ln,
                    style=ts(10.5, "#A7A294", family=SERIF, style="italic", lh=1.4))
        self.y = BOTTOM + 1

    def front_matter(self, *, disclaimer, legend, method):
        """The legend spread — disclaimer, the four-weight evidence colour code
        (which teaches the inline colour used throughout), and the method note."""
        self.running = "Front matter"
        self.new_page(ground=CREAM)
        pg = self.page
        pg.text([MX, self.y, CONTENT_W, 26], "Before you begin",
                style=ts(24, INK, family=SANS, weight=800, spacing=-0.4))
        self.y += 36
        pg.rect([MX, self.y, CONTENT_W, 2.0], fill=GOLD)
        self.y += 20

        self.label("Disclaimer")
        self.para(disclaimer, size=11, color=MUTE, lh=1.55, gap=16)

        self.label("The evidence tags — a four-weight colour code")
        self.para("Every claim in this book carries one of four tags. They are "
                  "colour-coded here and wherever they appear inline, so the "
                  "weight a sentence can bear is legible at a glance.", size=11,
                  color=MUTE, gap=12)
        for tag, kind, defn in legend:
            self.ensure(40)
            y0 = self.y
            col = TAG_STYLE[kind]
            pg = self.page
            pg.rect([MX, y0, CONTENT_W, 34], radius=7, fill=PANEL)
            pg.rect([MX, y0, 4, 34], radius=2, fill=col)
            pg.text([MX + 18, y0 + 9, 150, 16], tag,
                    style=ts(11, col, family=SANS, weight=800, spacing=0.6))
            for ln in wrap_text(defn, width=CONTENT_W - 190, font_family=SERIF,
                                font_size=10.5)[:2]:
                pg.text([MX + 172, y0 + 9, CONTENT_W - 190, 15], ln,
                        style=ts(10.5, INK, family=SERIF, lh=1.3))
                y0 += 14
            self.y += 40

        self.space(6)
        self.label("Method note")
        self.para(method, size=11, color=MUTE, lh=1.55, gap=14)

    def part_divider(self, *, number, title, blurb, contents):
        """A chapter-opening page — big numeral, title, a ripple motif, and the
        chapter's contents."""
        self.running = title
        self.new_page(folio=True, ground=CREAM)
        pg = self.page
        ripple_field(pg, 690, 250, n=7, r0=48, dr=40, color=LINE, width=1.0,
                     max_r=150)
        y = 250
        pg.rect([MX, y, 60, 4], fill=GOLD)
        pg.text([MX, y + 14, CONTENT_W, 18], number,
                style=ts(13, ACCENT_MID, family=SANS, weight=800, spacing=3.0,
                         transform="uppercase"))
        y += 48
        for ln in wrap_text(title, width=CONTENT_W, font_family=SANS,
                            font_size=40, bold=True):
            pg.text([MX, y, CONTENT_W, 50], ln,
                    style=ts(40, INK, family=SANS, weight=800, spacing=-1.0))
            y += 48
        y += 10
        for ln in wrap_text(blurb, width=CONTENT_W - 40, font_family=SERIF,
                            font_size=14):
            pg.text([MX, y, CONTENT_W - 40, 22], ln,
                    style=ts(14, MUTE, family=SERIF, style="italic", lh=1.5))
            y += 22
        y += 30
        pg.rect([MX, y, CONTENT_W, 1.0], fill=RULE)
        y += 18
        pg.text([MX, y, CONTENT_W, 14], "IN THIS CHAPTER",
                style=ts(9.5, GOLD, family=SANS, weight=800, spacing=2.0))
        y += 24
        for item in contents:
            pg.text([MX, y, 40, 16], "—", style=ts(12, ACCENT_MID, family=SANS))
            for ln in wrap_text(item, width=CONTENT_W - 30, font_family=SERIF,
                                font_size=12.5)[:1]:
                pg.text([MX + 26, y, CONTENT_W - 26, 16], ln,
                        style=ts(12.5, INK, family=SERIF, lh=1.3))
            y += 22
        self.y = BOTTOM + 1

    def colophon(self, lines):
        self.new_page()
        self.running = "Colophon"
        self.subsection("Colophon & disclaimer")
        for label, body in lines:
            self.ensure(20)
            self.page.text([MX, self.y, CONTENT_W, 14], label,
                           style=ts(10, GOLD, family=SANS, weight=800,
                                    spacing=1.4, transform="uppercase"))
            self.y += 18
            self.para(body, size=10.5, color=MUTE, lh=1.55, gap=14)

    def build(self):
        return self.b.build()


# --------------------------------------------------------------------------- #
# The book — every section, table, callout, list and plate, composed as one
# paginated FrameGraph document. Prose reconciled from demo/brand-book.md.
# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    bk = Book("Brand, From Products to Source Code",
              "A Framework, a Method, and Field Studies")

    # ===================== COVER ====================== #
    bk.cover(
        imprint="FRAMEGRAPH PRESS",
        kicker="Branding · Framework — Method — Field Studies",
        title_lines=["Brand,", "from Products", "to Source Code"],
        subtitle="A Framework, a Method, and Field Studies — reconciling five "
                 "working documents into two chapters.",
        thesis="Define the thing, build a method to study it, then use the method "
               "in the open.",
        meta_line="VERSION 1.0 (CONSOLIDATED)   ·   2026-06-24   ·   DRAFT FOR REVIEW",
        footer="Every figure and page in this book is real FrameGraph output: the "
               "prose, the running heads, the evidence tags and the four plates are "
               "all lowered to absolute coordinates by a composer that measures, "
               "wraps and paginates. The imprint typesets itself.",
    )

    # ===================== FRONT MATTER ====================== #
    bk.front_matter(
        disclaimer="Nothing in this book should be taken for granted. Any statement "
                   "or premise not backed by an explicit logical definition or a "
                   "verifiable, cited reference may be invalid, erroneous, or a "
                   "hallucination, and should be independently checked before being "
                   "relied upon. Branding is a practitioner discipline, not a "
                   "science; much of what follows is a reasoned structuring of "
                   "common practice, labeled as such. Figures (valuations, revenue, "
                   "users, downloads, losses) move quickly and were occasionally "
                   "reported inconsistently across sources as of June 2026; "
                   "re-verify before use.",
        legend=[
            ("SOURCED", "tag_sourced",
             "Traceable to a named, verifiable reference (see Sources & Provenance)."),
            ("SYNTHESIS", "tag_synth",
             "An analyst's reading or a model with no single authoritative origin — "
             "reasonable structuring, not established fact."),
            ("ILLUSTRATIVE", "tag_illus",
             "A stylized example or generalization."),
            ("RESEARCH-REQUIRED", "tag_research",
             "A claim a full study would settle through primary research that was "
             "NOT conducted for this book; treat as an open question."),
        ],
        method="The field studies in Chapter 2 are desk research against public "
               "sources as of June 2026. No primary audience research (surveys, "
               "interviews, tracking) was conducted, so every perception, "
               "awareness, or preference claim is a hypothesis flagged "
               "RESEARCH-REQUIRED. The Claude study was authored by an Anthropic "
               "product about Anthropic's own product; that conflict of interest is "
               "countered by citing only public sources and stating risks as "
               "plainly as strengths.",
    )

    # ===================== PREFACE ====================== #
    bk.section("Preface", "How to read this book", "Preface", keep=120)
    bk.para("This book makes one argument in three moves: **define the thing, "
            "build a method to study it, then use the method in the open.**")
    bk.para("The word *brand* is used constantly and examined rarely. Chapter 1 "
            "starts by refusing the usual shorthand and building the concept from "
            "its literal root up; it then turns that concept into a working method "
            "— how a marketing agency actually runs a brand study, from engagement "
            "to deliverables to the decisions in between. Chapter 2 puts the method "
            "to work on four real subjects and lets the results, flattering or not, "
            "stand.")
    bk.para("A through-line connects every case: the **trust-and-ownership axis**. "
            "On one end sit products that monetize attention or data; on the other, "
            "products that win by giving people control. Claude positions on "
            "staying ad-free; Meta's business runs on advertising; Obsidian and "
            "Ollama win on “your files, your hardware, yours.” Watching where each "
            "subject sits on that axis — and what it costs them to stay there — is "
            "the recurring lesson.")
    bk.para("Two habits run throughout. First, **every claim is tagged** for how "
            "much weight it can bear (the four-weight legend is in the front "
            "matter, colour-coded). Second, **feedback and received wisdom are "
            "processed, not obeyed**: where a common framing is wrong or "
            "overstated, it is corrected rather than repeated. The aim is "
            "calibration — neither flattery nor reflexive skepticism.")

    # ===================== CHAPTER 1 DIVIDER ====================== #
    bk.part_divider(
        number="Chapter 1",
        title="Foundations",
        blurb="What a brand is, and how to study one — building the concept from "
              "its literal root up, then turning it into a working method.",
        contents=[
            "1.1  What a brand is: the five-layer stack",
            "1.2  The domain-general loop",
            "1.3  Building a business brand",
            "1.4  Macro and micro: people and nations",
            "1.5  Technical branding: source code and foundations",
            "1.6  The brand-study method (the playbook)",
        ],
    )

    # ---- 1.1 ---- #
    bk.section("1.1", "What a brand is: the five-layer stack", "§1.1 · The stack")
    bk.para("“Brand” is not one idea but a stack of them, accumulated over roughly "
            "four millennia, running from a literal mark to a feeling in someone's "
            "head. Treating any single layer as *the* definition — as the "
            "practitioner shorthand “gut feeling” does — collapses the stack. Each "
            "layer below is [SOURCED]; the ordering is [SYNTHESIS], and the "
            "historical and analytical sequences happen to align.")
    bk.bullets([
        "**Layer 1 — A mark (ownership and origin).** The word is literally a "
        "burn: from Old Norse *brandr*, “to burn.” The sense of a mark seared with "
        "a hot iron — onto livestock, then casks and goods — is recorded from the "
        "1550s; “a particular make of goods” only by 1854 [SOURCED: Etymonline]. "
        "*Whose is this, and who made it?*",
        "**Layer 2 — A distinguishing sign (the trademark).** Once a mark "
        "identifies a maker, it separates that maker's goods from everyone else's. "
        "The American Marketing Association defines a brand as an identifying name, "
        "term, design, or symbol; the legal term is *trademark* [SOURCED: AMA]. "
        "*Which of these competing options is which?*",
        "**Layer 3 — A quality signal (reputation under uncertainty).** A buyer "
        "who cannot inspect quality leans on the mark as a proxy. Erdem and Swait "
        "treat brand equity as the value of a brand as a *credible signal* that "
        "raises perceived quality and lowers perceived risk and information costs "
        "[SOURCED: Erdem & Swait 1998]. *Can I trust this without checking?*",
        "**Layer 4 — A structure in memory (associations).** The signal works "
        "because it is stored. Keller models a brand as *brand knowledge*: an "
        "associative memory network of awareness plus image [SOURCED: Keller 1993]. "
        "*What comes to mind, and how strongly?*",
        "**Layer 5 — A felt impression (the practitioner shorthand).** The "
        "affective summary of the layers beneath is Neumeier's “a person's gut "
        "feeling about a product, service, or organization” [SOURCED: Neumeier "
        "2003]. Useful because it locates the brand in perception — but it is a "
        "*summary of* the stack, not a substitute for it.",
    ])
    bk.figure("fig-stack", 1, "The five-layer brand stack",
              caption="Treating any single layer as the definition collapses the "
                      "stack. Diagnosis works down it — what does the felt "
                      "impression rest on? — while strategy and expression build "
                      "back up it. Each rung is sourced; the ordering is a synthesis.")
    bk.para("Each later part of this book manages a different layer for a different "
            "entity: a trademark dispute lives at Layer 2; a “Made in [Country]” "
            "premium is a Layer 3 signal; a personal brand is Layers 4–5 attached "
            "to a person.")

    # ---- 1.2 ---- #
    bk.section("1.2", "The domain-general loop", "§1.2 · The loop")
    bk.para("Strip the corporate vocabulary off “building a brand” and the same "
            "loop appears for any entity. It is a [SYNTHESIS] — a generalization, "
            "not a cited universal — but it has a recognized neighbor in Keller's "
            "brand-resonance pyramid (salience → meaning → response → resonance), "
            "which climbs the same ladder as the stack above.")
    bk.table(
        ["Phase", "Company", "Person", "Nation", "Software project"],
        [["Define core", "Purpose, vision, values", "Strengths, niche, values",
          "Audit of what it does", "Mission, design philosophy"],
         ["Position", "vs. competitors", "vs. peers", "vs. other states",
          "vs. rival tools"],
         ["Express", "Name, identity, voice", "Portfolio, voice",
          "Symbols, exports", "Name, API, docs, voice"],
         ["Distribute", "Digital / content", "Talks, writing, conduct",
          "Tourism, diplomacy", "Docs, releases, community"],
         ["Steward", "Audits, refresh", "Reputation mgmt", "NBI tracking, policy",
          "Governance, versioning"]],
        weights=[0.7, 1.1, 1.0, 1.0, 1.1], row_height=40, header_height=30)
    bk.para("The **irreducible subset** beneath all of it: a persistent "
            "distinguishing identifier (Layer 2) plus consistency over time — "
            "repetition is the only mechanism that turns a sign into a reputation. "
            "Everything else is optional scaffolding that scales with resources. "
            "The single variable that explains why the same loop looks so different "
            "across columns is the **ratio of projected to earned reputation** — "
            "high control for a company, lowest for a nation (see 1.4).")
    bk.figure("fig-loop", 2, "The domain-general loop",
              caption="Discover → Position → Express → Distribute → Steward, with a "
                      "dashed loop-back: the loop runs for a company, a person, a "
                      "nation, or a software project. Its irreducible core is a "
                      "persistent distinguishing sign plus consistency over time.")

    # ---- 1.3 ---- #
    bk.section("1.3", "Building a business brand", "§1.3 · The business")
    bk.para("The corporate process is a five-step [SYNTHESIS] — common agency "
            "practice, not a single author's sequence. Jumping to visual design "
            "before settling strategy tends to produce a forgettable result.")
    bk.bullets([
        "**Define brand strategy** — purpose, vision, values. The internal, "
        "aspirational construct is Aaker's *brand identity* [SOURCED: Aaker "
        "1995/1996].",
        "**Research audience and competitors → position** — occupy a distinct "
        "place in the prospect's mind [SOURCED: Ries & Trout 1981].",
        "**Develop identity** — name, visual system, voice.",
        "**Build touchpoints** — digital, physical, content surfaces.",
        "**Manage and evolve** — guidelines, audits, refresh. A brand is a "
        "maintained activity, not a finished artifact [SOURCED: Neumeier 2003].",
    ], ordered=True)

    # ---- 1.4 ---- #
    bk.section("1.4", "Macro and micro: people and nations", "§1.4 · People & nations")
    bk.para("Because a brand is a reputation construct (Layers 3–4), any entity "
            "with a reputation can be branded.")
    bk.para("**Personal branding.** A personal brand is Layers 4–5 attached to a "
            "person — roughly what people say when you leave the room — managed or "
            "not. Tom Peters *popularized* the idea in 1997's “The Brand Called "
            "You” (“Me Inc.”) [SOURCED: Peters 1997]; “popularized,” not strictly "
            "“coined,” is the defensible claim.")
    bk.para("**Nation branding — sourced but contested.** Simon Anholt coined "
            "“nation brand” in 1996 and founded the index now called the "
            "Anholt-Ipsos Nation Brands Index [SOURCED: Anholt 2009/2010]. But "
            "Anholt himself rejects the marketing reading: national reputation is "
            "earned through conduct and policy, not projected through PR — his "
            "“Competitive Identity.” Treat the associations below as [ILLUSTRATIVE], "
            "not measured equity.")
    bk.table(
        ["Country", "Common association [ILLUSTRATIVE]", "Note"],
        [["Switzerland", "Precision, neutrality", "Premium in watches, finance"],
         ["Germany", "Engineering, reliability",
          "Led the index six years until Japan took first in 2023"],
         ["France", "Heritage luxury, gastronomy", "Couture, cosmetics, tourism"],
         ["Costa Rica", "Eco-sustainability, Pura Vida", "A positioning, not a rank"]],
        weights=[0.7, 1.3, 1.4], row_height=34)
    bk.para("South Korea's multi-decade *Hallyu* repositioning — state-supported "
            "exports of electronics, K-pop, and cinema — is the most documented "
            "deliberate national rebrand [SOURCED: Hong 2014; Nye 2004 for the "
            "soft-power mechanism].")

    # ---- 1.5 ---- #
    bk.section("1.5", "Technical branding: source code and foundations",
               "§1.5 · Source code")
    bk.para("In software, reputation governs adoption as it does for consumer "
            "goods; the audience shifts to developers and enterprise buyers. A "
            "project's standing is a Layer-3 signal (will this be maintained, will "
            "it break my stack?) held in place by Layer-4 associations.")
    bk.para("Key touchpoints: **developer experience** (documentation clarity, "
            "time-to-first-success — the subject of Bacon's *The Art of Community* "
            "[SOURCED: Bacon 2009]); **community culture** (adoption tracks "
            "community health; Rust is a common [ILLUSTRATIVE] example); and "
            "**project philosophy**. The argument that modern open source is "
            "reputation- and maintainer-driven is Eghbal's *Working in Public* "
            "[SOURCED: Eghbal 2020, published by Stripe Press — not “funded by "
            "Stripe”].")
    bk.para("If a codebase is the product, a **foundation** is the neutral "
            "steward, selling trust, governance, and vendor neutrality: the Apache "
            "Software Foundation (“Community Over Code”), the Linux Foundation (host "
            "of Kubernetes via the CNCF), the Mozilla Foundation (Firefox, MDN). "
            "[SOURCED + ILLUSTRATIVE for the one-line brand summaries.]")

    # ---- 1.6 ---- #
    bk.section("1.6", "The brand-study method (the playbook)", "§1.6 · The playbook")
    bk.para("A **brand study** runs the loop of 1.2 once, intensively, as a paid "
            "engagement, and hands the client the means to keep running it. "
            "Diagnosis works *down* the stack (what does the felt impression rest "
            "on?); strategy and expression build back *up* it.")

    bk.subsection("1.6.1 · Engagement and decision rights")
    bk.para("The most common failure is governance, not analysis. Two roles must "
            "be separated from day one: **the agency recommends; a named client "
            "sponsor decides.** A RACI assignment (Responsible / Accountable / "
            "Consulted / Informed — a standard project convention) fixes one "
            "accountable decision-maker per artifact, which is what prevents "
            "design-by-committee.")

    bk.subsection("1.6.2 · The gated phases")
    bk.para("Each phase ends in a sponsor-owned *go / iterate / stop* gate; the "
            "structure is a [SYNTHESIS] of convergent agency practice.")
    bk.bullets([
        "**Phase 0 — Scope & contract.** Objectives, KPIs, scope, budget. *Gate:* "
        "signed brief.",
        "**Phase 1 — Discovery (internal).** Stakeholder interviews; asset review; "
        "internal audit across internal branding, external branding, and customer "
        "experience [SOURCED: agency methodologies]. *Gate:* problem alignment.",
        "**Phase 2 — Research & diagnosis (external).** Qualitative and "
        "quantitative; competitive audit; brand-health measurement. Deliverable: a "
        "**Brand Audit Report** with a gap analysis (intended vs. perceived), "
        "SWOT, and prioritized findings [SOURCED]. *Gate:* diagnosis accepted "
        "(go/no-go). Caution: an established brand that rebrands risks ~15–20% "
        "temporary customer confusion [SOURCED, agency-sourced — verify].",
        "**Phase 3 — Strategy.** Positioning, captured in Moore's template; brand "
        "platform (Kapferer's six-facet prism a common scaffold). *Gate:* "
        "**sponsor sign-off — the pivotal decision.**",
        "**Phase 4 — Expression.** Verbal and visual identity; validate with the "
        "target audience, not internal taste. *Gate:* select a direction "
        "*on-strategy*.",
        "**Phase 5 — Codification & activation.** Brand book, rollout, governance. "
        "*Gate:* launch readiness.",
        "**Phase 6 — Measurement & evolution.** Tracking against Phase-0 KPIs; "
        "periodic re-audit. *Gate:* a standing review rhythm.",
    ])
    bk.plate_page("fig-process", 3, "The brand-study process flow with gates",
                  running="§1.6.2 · The gated phases",
                  caption="The seven phases redrawn from the source Mermaid as "
                          "vector artwork, following the book's shape grammar: "
                          "rounded rectangle = step, diamond = gate, pill = "
                          "terminal, dashed = loop-back. Each gate is a sponsor-owned "
                          "go / iterate / stop; Phase 2 can halt the engagement and "
                          "Phase 3's sponsor sign-off is the pivotal decision.")

    bk.subsection("1.6.3 · The decision process")
    bk.para("Three rules. (a) Gate decisions are explicit, owned, and recorded. "
            "(b) Subjective choices are judged *on-strategy* first — “does this "
            "express the signed positioning?” — with validation data, not "
            "seniority, breaking ties. (c) A positioning is ready when the target "
            "is specific, the “unlike” names a real alternative, the benefit is an "
            "outcome, and the claim is provable.")

    bk.subsection("1.6.4 · Deliverables map")
    bk.table(
        ["Phase", "Deliverable", "Decision it informs"],
        [["0", "Signed brief", "Whether / how to proceed"],
         ["1", "Discovery readout", "Problem alignment"],
         ["2", "Brand Audit Report (+gap, SWOT)", "Go / no-go on direction"],
         ["3", "Brand Platform + Positioning", "Strategic commitment"],
         ["4", "Identity concepts + validation", "Choice of direction"],
         ["5", "Brand Book + rollout", "Launch readiness"],
         ["6", "Tracking dashboard", "Ongoing evolution"]],
        weights=[0.5, 1.6, 1.4], row_height=29)

    bk.subsection("1.6.5 · Methods and models (the evidence base)")
    bk.para("*Research:* qualitative (the “why”; not projectable), quantitative "
            "(sizes awareness/preference; measures perception, not truth), NPS (one "
            "loyalty signal), social listening (skewed to the vocal). *Equity & "
            "identity models:* Keller CBBE / resonance pyramid; Aaker (internal "
            "identity, equity components); Young & Rubicam's **BrandAsset "
            "Valuator** — Differentiation + Relevance (strength, leading) and "
            "Esteem + Knowledge (stature, lagging), on a Power Grid; Kapferer's "
            "prism; Ries & Trout (positioning); Moore (the positioning-statement "
            "template). None substitutes for judgment. [All SOURCED.]")

    # ===================== CHAPTER 2 DIVIDER ====================== #
    bk.part_divider(
        number="Chapter 2",
        title="Field studies",
        blurb="The method applied to four real subjects — desk research as of June "
              "2026, with every perception claim flagged as an open question.",
        contents=[
            "2.1  Claude (Anthropic)",
            "2.2  Meta: the rebrand that changed the sign, not the reputation",
            "2.3  Obsidian — live audit",
            "2.4  Ollama — live audit",
            "2.5  Cross-case synthesis: the trust-and-ownership axis",
            "2.6  What primary research would add",
        ],
    )
    bk.para("*These four studies apply Chapter 1's method to real subjects. They "
            "are desk research as of June 2026; no primary perception research was "
            "run, so awareness and preference claims are [RESEARCH-REQUIRED] (see "
            "2.6). The Claude study carries a conflict of interest noted in the "
            "front matter and is written to state risks as plainly as strengths.*",
            color=MUTE)

    # ---- 2.1 Claude ---- #
    bk.section("2.1", "Claude (Anthropic)", "§2.1 · Claude")
    bk.label("Snapshot")
    bk.para("Claude is the AI-assistant family from Anthropic, a Public Benefit "
            "Corporation whose stated purpose is “the responsible development and "
            "maintenance of advanced AI for the long-term benefit of humanity” "
            "[SOURCED]. A Long-Term Benefit Trust holds special voting rights "
            "intended to protect the mission from investor pressure — structural "
            "backing for the safety claim, not just messaging.")
    bk.label("Through the stack")
    bk.para("*Mark:* “Claude,” a human first name (an homage to Claude Shannon). "
            "*Sign:* the poetry-form model tiers — Haiku, Sonnet, Opus, with a "
            "higher Mythos tier — which name by craft where rivals name by spec. "
            "*Signal:* trust under uncertainty. *Associations:* AI safety, "
            "Constitutional AI, enterprise trust, strong coding — and, as a double "
            "edge, caution some read as over-refusal. *Felt impression:* a calm "
            "“space to think.” [SOURCED + SYNTHESIS]")
    bk.label("Reconstructed positioning [SYNTHESIS]")
    bk.callout("For people and organizations who need a capable AI assistant they "
               "can trust with consequential work, Claude is an assistant that "
               "pairs frontier capability with safety-first design; unlike "
               "ad-supported, engagement-optimized assistants, it is built by a "
               "public-benefit company that keeps the product ad-free and declines "
               "uses it judges harmful.", lead="Positioning · Moore template",
               accent=BLUE[1], fill=BLUE[0])
    bk.para("The “unlike” is real: Anthropic has said Claude will stay ad-free as "
            "OpenAI introduced ads to free ChatGPT, and dramatized the contrast in "
            "a 2026 Super Bowl campaign [SOURCED].")
    bk.label("Diagnosis")
    bk.para("*Strengths:* a differentiated safety identity with structural "
            "backing; authenticity from costly signals (it refused U.S. Department "
            "of Defense demands to drop restrictions on surveillance and autonomous "
            "weapons, and was labeled a “supply chain risk” for it); strong "
            "developer/enterprise standing [SOURCED]. *Risks (plainly):* a "
            "consumer-mindshare gap behind ChatGPT; the “caution paradox” where "
            "safety reads as restrictive; brand-safety tensions (a reported "
            "state-sponsored misuse incident; a US$1.5B copyright settlement); "
            "IPO/valuation pressure straining “safety over speed”; and erosion as "
            "every rival now claims “safety,” so the edge depends on making safety "
            "*provable* [SOURCED + SYNTHESIS]. *Gap hypothesis "
            "[RESEARCH-REQUIRED]:* intended “frontier-capable, genuinely helpful, "
            "trustworthy” vs. a plausible perceived “capable but cautious/"
            "corporate.”")

    # ---- 2.2 Meta ---- #
    bk.section("2.2", "Meta: the rebrand that changed the sign, not the reputation",
               "§2.2 · Meta")
    bk.label("Background")
    bk.para("Facebook (2004) grew into a family of apps, then hit sustained "
            "reputation strain — Cambridge Analytica, misinformation, and in autumn "
            "2021 the Frances Haugen disclosures [SOURCED].")
    bk.label("The rebrand")
    bk.para("On October 28, 2021, the *parent company only* was renamed Meta, to "
            "signal a metaverse pivot (“metaverse-first, not Facebook-first”); the "
            "apps kept their names; reporting split into Family of Apps and Reality "
            "Labs; the ticker ultimately became META in mid-2022 [SOURCED].")
    bk.label("Through the lenses")
    bk.para("The rename changed the *sign* (Layer 2) but not the *reputation* "
            "(Layers 3–4): the Facebook app kept its name and its controversies. A "
            "survey found 51% of U.S. adults saw the move as distancing from bad "
            "press; Meta denied it [SOURCED, the survey ILLUSTRATIVE]. The branding "
            "lesson is 1.4's earned-not-projected point: a rename cannot repair "
            "conduct-based reputation. The architecture logic was sound — but the "
            "comparison to Alphabet exposes the mistake: Alphabet is a deliberately "
            "empty name that fits any future, while **Meta hard-coded one bet — the "
            "metaverse — into the corporate identity.**")
    bk.label("What happened next")
    bk.para("Reality Labs lost roughly $6.6B (2020), $10.2B, $13.7B, $16.1B, "
            "$17.7B, and $19.2B (2025) — about **$83.6B cumulative** against "
            "negligible revenue [SOURCED]. After a 2022 collapse and a 2023 “Year "
            "of Efficiency” (~21,000 jobs cut, strong stock recovery), the real "
            "future turned out to be AI: open Llama models, then — after Llama 4 "
            "disappointed — a $14.3B Scale AI deal, Meta Superintelligence Labs, a "
            "retreat from full open-source, the proprietary Muse Spark model (April "
            "2026), and 2026 AI capex guided to $115–135B [SOURCED]. A company "
            "named for the metaverse is now an AI-and-advertising company.")
    bk.label("Assessment by criterion [SYNTHESIS]")
    bk.table(
        ["Criterion", "Verdict"],
        [["Corporate-brand separation", "Achieved"],
         ["Signaling the future", "Failed (bet on the wrong future)"],
         ["Reputation repair", "Not achieved (and contested as a goal)"],
         ["Business outcome", "Strong (recovery, ~$200B+ 2025 revenue)"]],
        weights=[1.0, 1.6], row_height=30)
    bk.para("The instructive tension: **the company succeeded while the rebrand's "
            "central premise did not.** Score the business and the brand "
            "separately.")

    # ---- 2.3 Obsidian ---- #
    bk.section("2.3", "Obsidian — live audit", "§2.3 · Obsidian")
    bk.label("Snapshot")
    bk.para("A local-first, Markdown PKM app: notes are plain `.md` files on your "
            "device, no account, no cloud dependency [SOURCED]. Created by Shida Li "
            "and Erica Xu (the Dynalist creators; Steph Ango joined as CEO in "
            "2023). The company (Dynalist Inc.) is **bootstrapped, 100% "
            "user-supported, zero VC, deliberately tiny** [SOURCED; reported ~1.5M "
            "users / ~$25M ARR are secondary estimates — RESEARCH-REQUIRED].")
    bk.label("Positioning [SYNTHESIS]")
    bk.callout("For individuals who want a fast, private knowledge base they fully "
               "own, Obsidian is a local-first Markdown app that keeps everything "
               "as plain files; unlike cloud note tools, it needs no account, locks "
               "in no data, and is funded by users rather than ads or investors.",
               lead="Positioning · Moore template", accent=TEAL[1], fill=TEAL[0])
    bk.para("**Competitive.** Notion (cloud team OS, ~100M users, VC-backed) is the "
            "mainstream opposite; Logseq is the closest *open-source* philosophical "
            "match; the live 2026 threat is “AI second brain” tools reframing the "
            "category. [SOURCED]")
    bk.label("Diagnosis")
    bk.para("*Strengths:* independence as brand infrastructure — a user-funded, "
            "no-ads, no-investor structure that *proves* the data-respect claim the "
            "way the Anthropic PBC backs a safety claim; a deep plugin ecosystem "
            "and intensely engaged community (“the product is the marketing”); "
            "plain-text permanence [SOURCED + SYNTHESIS]. *Risks:* single-player by "
            "design (weak collaboration); a power-user reputation; proprietary, not "
            "open-source (Logseq's opening); small-team limits; the AI-era category "
            "shift [SOURCED + SYNTHESIS]. *Gap hypothesis [RESEARCH-REQUIRED]:* "
            "intended “fast, private, permanent, extensible” vs. perceived "
            "“intimidating / teams-weak.”")

    # ---- 2.4 Ollama ---- #
    bk.section("2.4", "Ollama — live audit", "§2.4 · Ollama")
    bk.label("Snapshot")
    bk.para("An open-source (MIT) runtime that runs LLMs locally in one command "
            "(`ollama run llama3`), with a Dockerfile-like Modelfile and an "
            "OpenAI-compatible API; widely the **de facto standard** (100M+ "
            "downloads, 110k+ GitHub stars reported by April 2026) [SOURCED]. "
            "Founded 2023 by Jeffrey Morgan and Michael Chiang; small, lightly "
            "funded team [SOURCED; HQ reported inconsistently — RESEARCH-REQUIRED].")
    bk.label("Positioning [SYNTHESIS]")
    bk.callout("For developers who want to run AI models on their own hardware, "
               "Ollama is a local runtime that makes models as easy to pull and run "
               "as containers; unlike cloud APIs, it keeps data on your machine, "
               "costs nothing per token, and works offline.",
               lead="Positioning · Moore template", accent=EMER[1], fill=EMER[0])
    bk.para("**Competitive.** LM Studio (proprietary GUI) wins on no-terminal UX; "
            "llama.cpp is the open upstream Ollama builds on; Jan out-opens it on "
            "auditability; cloud APIs are the macro alternative. [SOURCED]")
    bk.label("Diagnosis")
    bk.para("*Strengths:* category leadership and ecosystem gravity (tools default "
            "to it as a backend); a superb ownable metaphor (“Docker for LLMs”); "
            "textbook developer experience; authentic alignment with "
            "data-sovereignty [SOURCED]. *Risks:* a **namesake dependency** — "
            "“Ollama” rides on “Llama,” whose owner Meta is moving to closed models "
            "(see 2.2); thin technical differentiation (shared llama.cpp); an "
            "upstream-attribution question; and the central tension of "
            "commercializing via **Ollama Cloud** without appearing to drift from "
            "the local-first, no-account brand that won the audience [SOURCED + "
            "SYNTHESIS]. *Gap hypothesis [RESEARCH-REQUIRED]:* intended “the easy, "
            "standard, open way to run models locally” vs. perceived “a llama.cpp "
            "wrapper — will it stay open as it commercializes?”")

    # ---- 2.5 Cross-case synthesis ---- #
    bk.section("2.5", "Cross-case synthesis: the trust-and-ownership axis",
               "§2.5 · The axis")
    bk.para("Place the four on one axis — how much each asks users to *trust it "
            "with* versus *hand control to them*.")
    bk.bullets([
        "**Meta** monetizes attention and data through advertising — the far "
        "attention-monetizing end.",
        "**Claude** positions deliberately against that end: ad-free, a “space to "
        "think,” limits on use.",
        "**Obsidian and Ollama** sit at the ownership end: your files, your "
        "hardware, yours.",
    ])
    bk.figure("fig-axis", 4, "The trust-and-ownership axis",
              caption="The four subjects placed from attention-monetizing (Meta) to "
                      "ownership (Obsidian, Ollama), with Claude positioned "
                      "deliberately against the monetizing end. Structure — a PBC, "
                      "a bootstrapped no-ads model — is what makes a claim credible.")
    bk.para("Three patterns fall out.")
    bk.bullets([
        "**Structure is the proof (earned, not projected).** The brands whose "
        "*structure* matches their claim are the credible ones: Anthropic's PBC and "
        "trust behind “safety”; Obsidian's bootstrapped, user-funded model behind "
        "“we respect your data.” Meta is the counter-example — a *rename* could not "
        "project a reputation the *conduct* had not earned.",
        "**For ownership-brands, the monetization path is the brand strategy.** "
        "Obsidian and Ollama both give the core away and charge at the edges "
        "(Sync/Publish; Cloud). The shared test is to monetize the periphery "
        "without appearing to compromise the core that won the audience.",
        "**Names are bets, and dependencies are constraints.** “Meta” bet the "
        "corporate identity on one future and aged poorly; “Ollama” inherited "
        "“Llama's” trajectory, useful in 2023 and a liability as Meta closes its "
        "models. Abstract names (Alphabet) preserve optionality; thematic and "
        "dependent names spend it.",
    ], ordered=True)
    bk.para("A fourth, quieter lesson runs through all four: when technical or "
            "feature differentiation is thin, the contest moves to **brand, "
            "developer experience, and community** — exactly the touchpoints "
            "Chapter 1 names.")

    # ---- 2.6 ---- #
    bk.section("2.6", "What primary research would add", "§2.6 · Research")
    bk.para("Every perception line above is a hypothesis until tested "
            "[RESEARCH-REQUIRED]. A real study would run the Phase-2 research from "
            "1.6.2 for each subject: brand tracking on awareness, consideration, "
            "and preference against the named alternatives; targeted qualitative "
            "work on the specific gap hypothesis (Claude's “cautious/corporate”; "
            "Obsidian's “intimidating/teams-weak”; Ollama's “wrapper” and “will it "
            "stay open”); equity measurement (CBBE, BAV) versus rivals; and, for "
            "the commercial subjects, lost-deal or lost-use analysis. Until then, "
            "treat 2.1–2.4's diagnoses as structured hypotheses, not findings.")

    # ===================== BACK MATTER ====================== #
    bk.part_divider(
        number="Back matter",
        title="Provenance & flags",
        blurb="The figures realized as vector plates, the consolidated sources, and "
              "an honest register of what remains unverified.",
        contents=[
            "Appendix A — Figures (realized as FrameGraph plates)",
            "Sources & Provenance",
            "Epistemic flags (unverified / synthesized / research-required)",
        ],
    )

    bk.section("Appendix A", "Figures", "Appendix A · Figures")
    bk.para("These illustrate the method (1.6) and the concept (1.1). The source "
            "book shipped them as Mermaid starting points; this edition realizes "
            "the four core figures as vector plates, authored through the "
            "FrameGraph SDK and kept grayscale-safe (shape + label, not colour "
            "alone), using the shape grammar: rounded rectangle = step, diamond = "
            "gate, pill = terminal, dashed = loop-back.")
    bk.bullets([
        "**Figure 1 — The five-layer concept stack** (1.1), with diagnose-down / "
        "build-up rails.",
        "**Figure 2 — The domain-general loop** (1.2), as a closed cycle with a "
        "dashed loop-back.",
        "**Figure 3 — The brand-study process flow with decision gates** (1.6.2), "
        "redrawn from the source Mermaid.",
        "**Figure 4 — The trust-and-ownership axis** (2.5), placing the four "
        "subjects.",
    ])
    bk.para("The model diagrams the source recommends — the Keller resonance "
            "pyramid, the BrandAsset Valuator Power Grid, and the Kapferer prism — "
            "reproduce published frameworks and must be redrawn with “after "
            "[author]” attribution rather than copied; they are left as future "
            "plates in the same house style.")

    bk.section("", "Sources & Provenance", "Sources & Provenance")
    bk.para("Checked June 2026. Official and primary sources and reference "
            "encyclopedias are strong; pricing aggregators, trade blogs, and "
            "profile sites are weak and used only where they corroborate. Estimates "
            "(valuations, revenue, users, downloads, losses) are flagged in the "
            "text and below.")
    bk.label("Chapter 1 — foundations")
    bk.para("*Etymology / definition:* Etymonline; American Marketing Association "
            "(via the Open University). *Equity & cognition:* Keller, “Customer-"
            "Based Brand Equity,” *Journal of Marketing* 57(1), 1993; resonance "
            "pyramid in *Strategic Brand Management* (2001). Erdem & Swait, “Brand "
            "Equity as a Signaling Phenomenon,” *J. Consumer Psychology* 7(2), "
            "1998. *Strategy:* Aaker, *Building Strong Brands* (1995/©1996); Ries & "
            "Trout, *Positioning* (1981); Neumeier, *The Brand Gap* (2003). "
            "*People/nations:* Peters, “The Brand Called You,” *Fast Company* "
            "(1997); Anholt, *Places* (Palgrave, 2009/2010) + Anholt-Ipsos NBI; "
            "Nye, *Soft Power* (2004); Hong, *The Birth of Korean Cool* (2014). "
            "*Open source:* Eghbal, *Working in Public* (Stripe Press, 2020); "
            "Bacon, *The Art of Community* (O'Reilly, 2009). *Method:* Young & "
            "Rubicam BrandAsset Valuator; Kapferer, Brand Identity Prism; Moore, "
            "*Crossing the Chasm*; plus convergent agency brand-audit methodologies "
            "(Frontify, MaRS, others). RACI is a general project convention.",
            size=10.5, lh=1.5)
    bk.label("Chapter 2 — field studies")
    bk.para("*Claude:* Anthropic company and news pages; Wikipedia and Britannica "
            "(Constitutional AI, Claude/Shannon, the DoD dispute, the misuse "
            "incident); the Super Bowl campaign; the model lineup from Anthropic "
            "product information. Valuation/IPO figures reported inconsistently — "
            "excluded or flagged. *Meta:* TechCrunch and CNBC (Oct 2021 "
            "announcement); Deadline (the META ticker); Tronvig (parent-only scope, "
            "the 51% survey, Meta's denial); SEC 8-K filings and Game Developer/CNBC "
            "(Reality Labs losses, ~$83.6B cumulative); CNBC/Bloomberg/VentureBeat/"
            "TechCrunch and Wikipedia (the AI pivot). *Obsidian:* obsidian.md; "
            "Wikipedia (founders, CEO, free for personal and commercial use); "
            "versaedits/36Kr/taskade/nesslabs (bootstrapped, zero-VC; user/ARR "
            "estimates secondary). *Ollama:* ollama.com (one-command UX, Modelfile, "
            "library, Cloud); Tracxn/startupintros (founders, 2023, funding — HQ "
            "inconsistent); daily.dev/contabo/dev.to/grandlinux (MIT license, "
            "llama.cpp foundation, “Docker for LLMs,” comparisons, estimates).",
            size=10.5, lh=1.5)

    bk.section("", "Epistemic flags", "Epistemic flags")
    bk.para("Treat as open, not established:", gap=6)
    bk.bullets([
        "all **perception, awareness, and preference** claims in Chapter 2 — no "
        "primary research was run;",
        "all **reconstructed positioning** statements and the **score-by-criterion** "
        "and **axis** readings — SYNTHESIS;",
        "**intent attributions** (e.g., why Meta rebranded — disputed);",
        "the **estimated figures** — Anthropic valuation; Meta Reality Labs "
        "cumulative loss (cited variously ~$73B / ~$80B / ~$83.6B by window); "
        "Obsidian users/ARR; Ollama downloads/stars/HQ/team size;",
        "specific open dates — Obsidian's commercial-license-became-optional date "
        "(~early 2025) and the degree of llama.cpp-attribution friction for Ollama;",
        "the **structural models** themselves — the five-layer stack, the "
        "domain-general loop, and the gated phase sequence are organizing "
        "syntheses, each rung sourced but the ladders authored.",
    ])

    # ===================== COLOPHON ====================== #
    bk.colophon([
        ("Disclaimer",
         "No information within this book should be taken for granted. Any "
         "statement, premise, figure, or reference not backed by a real logical "
         "definition or a verifiable primary source may be invalid, erroneous, or a "
         "hallucination. Branding is a practitioner discipline, not a science; much "
         "of this is a reasoned structuring of common practice, labeled as such. "
         "Re-verify all figures before relying on them."),
        ("Generated by",
         "Claude Opus 4.8 via Claude Code — prose reconciled from five LLM-authored "
         "working documents; the four plates and the book itself authored through "
         "the FrameGraph SDK and rendered by the project's own SVG proxy. Date: "
         "2026-06-24."),
        ("Provenance & method",
         "This book is its own proof: a thin composer measures, wraps and "
         "paginates the prose, colour-codes the evidence tags, and embeds the "
         "plates — all lowered to absolute coordinates the FrameGraph renderer "
         "consumes. The imprint typesets itself."),
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
    for i in report.issues[:50]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    out_dir = os.path.join(ROOT, "_tmp", "brand-book")
    os.makedirs(out_dir, exist_ok=True)
    out_yaml = os.path.join(out_dir, "brand-book.fg.yaml")
    with open(out_yaml, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out_yaml}")
    svgs = render_page_svgs(doc)
    for idx, svg in enumerate(svgs, 1):
        with open(os.path.join(out_dir, f"page-{idx:02d}.svg"), "w",
                  encoding="utf-8") as fh:
            fh.write(svg)
    print(f"Wrote {len(svgs)} page SVG(s) to {out_dir}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
