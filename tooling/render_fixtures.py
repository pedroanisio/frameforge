#!/usr/bin/env python3
"""
render_fixtures.py — a dependency-free SVG proxy renderer for FrameGraph v2 docs.

Renders ALL or ANY document under fixtures/ (or any path you pass) to SVG, one
file per page, plus a browsable index.html contact sheet. Unlike the matplotlib
proxy in render_fg_doc.py, this needs only the standard library + PyYAML, so it
runs in a bare environment, and it tolerates the full fixture variety:

  * canvas from explicit `size`, a `preset`, or inherited from a master
  * `page` layers AND `flow` sections (naive vertical text flow, paginated)
  * the core object set: rect / ellipse / circle / line / polyline / polygon /
    path / text / bullet_list / icon / image / table / group
  * HEAD stroke single-form (paint in `stroke`, geometry in `stroke_style`)
  * token colour deref, CSS-named *and* legacy shorthand text styles,
    linear/radial gradient fills (conic ≈ first stop)

This is a SANITY-CHECK proxy, not a conformant renderer: no real text shaping or
line-breaking metrics, fonts are the browser's generic families, out-of-profile
objects and missing image assets become labelled placeholders. Geometry,
positions, colours and z-order are honoured.

Usage:
    python3 tooling/render_fixtures.py                       # render every fixture -> out/render/
    python3 tooling/render_fixtures.py --all
    python3 tooling/render_fixtures.py fixtures/b1/mckinsey-7s.fg.json
    python3 tooling/render_fixtures.py 'fixtures/*.fg.yaml'  # globs ok (quote them)
    python3 tooling/render_fixtures.py fixtures/b1 --out /tmp/r --max-pages 3
    python3 tooling/render_fixtures.py --list                # just list discoverable docs

Open out/render/index.html in a browser to see the contact sheet.
"""
from __future__ import annotations

import argparse
import glob
import html
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
FIXTURES = os.path.join(ROOT, "fixtures")

PRESETS = {
    "A3": (842, 1191), "A4": (595, 842), "A5": (419.5, 595.3), "Letter": (612, 792),
    "Legal": (612, 1008), "Tabloid": (792, 1224), "deck-16x9": (1920, 1080),
    "deck-4x3": (1024, 768), "square": (1080, 1080), "phone": (390, 844),
    "tablet": (834, 1112), "web": (1280, 800),
}
DEFAULT_WH = (1280, 800)
FONT_MAP = {"sans": "sans-serif", "serif": "serif", "mono": "monospace",
            "monospace": "monospace", "sans-serif": "sans-serif"}


# --------------------------------------------------------------------------- #
#  small helpers                                                              #
# --------------------------------------------------------------------------- #
def num(v, default=None):
    """Coerce a Length-ish value to a float (pt/px treated 1:1; %/fr give default)."""
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s.endswith(("%", "fr")):
            return default
        for u in ("px", "pt", "pc", "mm", "cm", "in", "em", "rem", "deg"):
            if s.endswith(u):
                s = s[: -len(u)]
                break
        try:
            return float(s)
        except ValueError:
            return default
    return default


def fnum(x):
    """Compact float formatting for SVG attributes."""
    f = float(x)
    return str(int(f)) if f == int(f) else f"{f:.3f}".rstrip("0").rstrip(".")


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def is_point(v):
    return isinstance(v, (list, tuple)) and len(v) == 2 and all(
        isinstance(c, (int, float)) and not isinstance(c, bool) for c in v
    )


# --------------------------------------------------------------------------- #
#  the renderer                                                               #
# --------------------------------------------------------------------------- #
class Renderer:
    def __init__(self, doc, base_dir):
        self.doc = doc if isinstance(doc, dict) else {}
        self.base_dir = base_dir
        defs = self.doc.get("defs") or {}
        tok = defs.get("tokens") or {}
        self.colors = tok.get("colors") or {}
        self.text_styles = tok.get("text_styles") or {}
        self.styles = tok.get("styles") or {}
        self.stroke_styles = tok.get("stroke_styles") or {}
        self.assets = defs.get("assets") or {}
        self.masters = defs.get("masters") or {}
        self._gid = 0
        self._defs = []          # per-page <defs> entries (gradients)
        self.skipped = 0

    # ---- colour / paint ---------------------------------------------------- #
    def color(self, c, depth=0):
        if c is None or depth > 8:
            return None
        if isinstance(c, dict):                      # a paint object (gradient/pattern)
            stops = c.get("stops")
            if stops:
                return self.color(stops[0].get("color"), depth + 1)
            return self.color(c.get("background"), depth + 1)
        if isinstance(c, str):
            s = c.strip()
            if s in self.colors:
                return self.color(self.colors[s], depth + 1)
            low = s.lower()
            if low in ("none", "transparent"):
                return "none"
            if low == "currentcolor":
                return "#222"
            return s                                  # hex / rgb()/rgba() / css name
        return None

    def paint(self, p, depth=0):
        """Return an SVG fill/stroke value: a colour, 'none', or url(#grad)."""
        if isinstance(p, dict) and p.get("stops") and p.get("kind") in ("linear", "radial", "conic"):
            return self._gradient(p)
        return self.color(p, depth)

    def _gradient(self, g):
        self._gid += 1
        gid = f"g{self._gid}"
        kind = g.get("kind")
        stops = []
        n = max(1, len(g.get("stops", [])))
        for i, st in enumerate(g.get("stops", [])):
            off = st.get("position")
            o = num(off)
            if o is None and isinstance(off, str) and off.strip().endswith("%"):
                o = num(off.strip()[:-1])
            if o is None:
                o = i / (n - 1) * 100 if n > 1 else 0
            col = self.color(st.get("color")) or "#000"
            stops.append(f'<stop offset="{fnum(o)}%" stop-color="{esc(col)}"/>')
        body = "".join(stops)
        if kind == "radial" or kind == "conic":     # conic ≈ radial fallback
            self._defs.append(f'<radialGradient id="{gid}">{body}</radialGradient>')
        else:
            self._defs.append(f'<linearGradient id="{gid}">{body}</linearGradient>')
        return f"url(#{gid})"

    # ---- stroke (HEAD P3: paint in `stroke`, geometry in `stroke_style`) --- #
    def stroke(self, o):
        ssv = o.get("stroke_style")
        bundle = self.stroke_styles.get(ssv, {}) if isinstance(ssv, str) else (ssv or {})
        if not isinstance(bundle, dict):
            bundle = {}
        sv = o.get("stroke")
        col = self.paint(sv) if sv is not None else None
        if col is None or col == "none":
            col = self.color(bundle.get("stroke") or bundle.get("color"))
        width = num(bundle.get("stroke_width", bundle.get("width")), None)
        dash = bundle.get("stroke_dasharray") or bundle.get("dash")
        dash = " ".join(fnum(num(d, 0)) for d in dash) if isinstance(dash, list) else None
        if col is None or col == "none":
            return ""
        if width is None:
            width = 1.0
        out = f' stroke="{esc(col)}" stroke-width="{fnum(width)}"'
        if dash:
            out += f' stroke-dasharray="{esc(dash)}"'
        cap = bundle.get("stroke_linecap"); join = bundle.get("stroke_linejoin")
        if cap:
            out += f' stroke-linecap="{esc(cap)}"'
        if join:
            out += f' stroke-linejoin="{esc(join)}"'
        return out

    # ---- text style resolution -------------------------------------------- #
    def text_style(self, ref):
        st = {}
        if isinstance(ref, str):
            st = self.text_styles.get(ref) or self.styles.get(ref) or {}
        elif isinstance(ref, dict):
            st = ref
        cls = st.get("class") or st.get("class_")
        merged = {}
        for name in ([cls] if isinstance(cls, str) else (cls or [])):
            merged.update(self.text_styles.get(name) or self.styles.get(name) or {})
        merged.update(st)
        fam = merged.get("font_family") or merged.get("font") or "sans"
        if isinstance(fam, list):
            fam = fam[0] if fam else "sans"
        return {
            "family": FONT_MAP.get(str(fam), str(fam)),
            "size": num(merged.get("font_size") or merged.get("size"), 14) or 14,
            "weight": merged.get("font_weight") or merged.get("weight") or "normal",
            "italic": bool(merged.get("italic")) or merged.get("font_style") == "italic",
            "color": self.color(merged.get("color")) or "#1c1c1c",
            "align": merged.get("text_align") or merged.get("align") or "left",
            "lh": num(merged.get("line_height"), None) or 1.25,
        }

    @staticmethod
    def anchor(align):
        return {"center": "middle", "right": "end", "end": "middle"}.get(align, "start")

    def text_tag(self, x, y, w, h, content, st, vcenter=None):
        if content is None or content == "":
            return ""
        a = self.anchor(st["align"])
        tx = x + (w / 2 if a == "middle" else (w if a == "end" else 0))
        if vcenter is None:
            vcenter = h <= st["size"] * 2.4            # heuristic: small box ⇒ centre
        if vcenter:
            ty = y + h / 2
            baseline = ' dominant-baseline="central"'
        else:
            ty = y + st["size"] * 0.92
            baseline = ""
        style = f'font-family:{esc(st["family"])};font-size:{fnum(st["size"])}px;fill:{esc(st["color"])}'
        if str(st["weight"]) not in ("normal", "400"):
            style += f';font-weight:{esc(st["weight"])}'
        if st["italic"]:
            style += ";font-style:italic"
        return (f'<text x="{fnum(tx)}" y="{fnum(ty)}" text-anchor="{a}"{baseline} '
                f'style="{style}">{esc(content)}</text>')

    # ---- per-object dispatch ---------------------------------------------- #
    def obj(self, o):
        if not isinstance(o, dict):
            return ""
        try:
            return self._obj(o)
        except Exception:                              # never let one object kill a page
            self.skipped += 1
            return ""

    def _obj(self, o):
        t = o.get("type")
        box = o.get("box")
        fill = self.paint(o.get("fill")) if "fill" in o else None
        fa = "" if fill is None else f' fill="{esc(fill)}"'
        if fill is None:
            fa = ' fill="none"'

        if t == "rect" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            r = num(o.get("radius") or o.get("rx"), 0) or 0
            rr = f' rx="{fnum(r)}"' if r else ""
            return f'<rect x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}"{rr}{fa}{self.stroke(o)}/>'

        if t == "ellipse":
            c = o.get("center") or [0, 0]
            cx, cy = num(c[0], 0), num(c[1], 0)
            rx, ry = num(o.get("rx"), 0), num(o.get("ry"), 0)
            if not rx and box:
                cx, cy, rx, ry = box[0] + box[2] / 2, box[1] + box[3] / 2, box[2] / 2, box[3] / 2
            return f'<ellipse cx="{fnum(cx)}" cy="{fnum(cy)}" rx="{fnum(rx)}" ry="{fnum(ry)}"{fa}{self.stroke(o)}/>'

        if t == "circle":
            c = o.get("center") or [0, 0]
            r = num(o.get("r"), 0)
            return f'<circle cx="{fnum(num(c[0],0))}" cy="{fnum(num(c[1],0))}" r="{fnum(r)}"{fa}{self.stroke(o)}/>'

        if t == "line":
            fr, to = o.get("from"), o.get("to")
            if is_point(fr) and is_point(to):
                stk = self.stroke(o) or ' stroke="#000" stroke-width="1"'
                return (f'<line x1="{fnum(fr[0])}" y1="{fnum(fr[1])}" '
                        f'x2="{fnum(to[0])}" y2="{fnum(to[1])}"{stk}/>')
            return ""

        if t in ("polyline", "polygon"):
            pts = o.get("points") or []
            ptstr = " ".join(f"{fnum(num(p[0],0))},{fnum(num(p[1],0))}" for p in pts if is_point(p))
            if not ptstr:
                return ""
            closed = t == "polygon" or o.get("closed")
            tag = "polygon" if closed else "polyline"
            ff = fa if (closed and fill not in (None,)) else ' fill="none"' if not closed else fa
            return f'<{tag} points="{ptstr}"{ff}{self.stroke(o)}/>'

        if t == "path":
            d = o.get("d")
            if isinstance(d, list):
                d = " ".join(str(seg[0]) + " " + " ".join(fnum(num(n, 0)) for n in seg[1:])
                             if isinstance(seg, list) else str(seg) for seg in d)
            if not isinstance(d, str) or not d.strip():
                return ""
            return f'<path d="{esc(d)}"{fa}{self.stroke(o)}/>'

        if t == "text" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            st = self.text_style(o.get("style"))
            content = o.get("text")
            if content is None and o.get("spans"):
                content = "".join(s if isinstance(s, str) else s.get("text", "")
                                  for s in o["spans"])
            return self.text_tag(x, y, w, h, content, st)

        if t == "bullet_list" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            st = self.text_style(o.get("style"))
            marker = o.get("marker", "•")
            gap = num(o.get("gap"), None) or st["size"] * 1.5
            mc = self.color(o.get("marker_color")) or st["color"]
            out = []
            cy = y + st["size"]
            for it in o.get("items", []):
                txt = it if isinstance(it, str) else (it.get("text", "") if isinstance(it, dict) else str(it))
                out.append(self.text_tag(x, cy - st["size"], st["size"] + 4, st["size"] + 4,
                                         marker, {**st, "color": mc}, vcenter=False))
                out.append(self.text_tag(x + st["size"] * 1.1, cy - st["size"], w, st["size"] + 4,
                                         txt, st, vcenter=False))
                cy += gap
            return "".join(out)

        if t == "icon" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            col = self.color(o.get("color")) or "#444"
            sz = num(o.get("size"), None) or min(w, h) * 0.8
            st = {"family": "sans-serif", "size": sz, "weight": "normal",
                  "italic": False, "color": col, "align": "center", "lh": 1.2}
            return self.text_tag(x, y, w, h, o.get("glyph", "▢"), st, vcenter=True)

        if t == "image" and box:
            return self._image(o, box)

        if t == "table" and box:
            return self._table(o, box)

        if t == "group":
            inner = "".join(self.obj(ch) for ch in (o.get("children") or []))
            bx = o.get("box")
            if is_point(bx[:2]) if isinstance(bx, list) and len(bx) >= 2 else False:
                # only translate when the group declares an origin box (P1 nesting)
                return f'<g transform="translate({fnum(num(bx[0],0))},{fnum(num(bx[1],0))})">{inner}</g>'
            return f"<g>{inner}</g>"

        # unknown / out-of-profile object → labelled placeholder iff it has a box
        if box and all(isinstance(v, (int, float)) for v in box[:4]):
            x, y, w, h = box[:4]
            st = {"family": "monospace", "size": 11, "weight": "normal",
                  "italic": True, "color": "#999", "align": "center", "lh": 1.2}
            return (f'<rect x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}" '
                    f'fill="#f3f3f3" stroke="#ccc" stroke-dasharray="3 3"/>'
                    + self.text_tag(x, y, w, h, f"?{t}", st, vcenter=True))
        self.skipped += 1
        return ""

    def _image(self, o, box):
        x, y, w, h = (num(v, 0) for v in box[:4])
        src = o.get("src", "")
        asset = self.assets.get(src)
        path = asset.get("src") if isinstance(asset, dict) else src
        if path and not os.path.isabs(path):
            path = os.path.normpath(os.path.join(self.base_dir, path))
        if path and os.path.exists(path):
            href = "file://" + path
            return (f'<image x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}" '
                    f'href="{esc(href)}" preserveAspectRatio="xMidYMid meet"/>')
        label = o.get("label") or os.path.basename(str(src)) or "image"
        st = {"family": "sans-serif", "size": 11, "weight": "normal", "italic": False,
              "color": "#888", "align": "center", "lh": 1.2}
        return (f'<rect x="{fnum(x)}" y="{fnum(y)}" width="{fnum(w)}" height="{fnum(h)}" '
                f'fill="#eee" stroke="#bbb"/>'
                f'<line x1="{fnum(x)}" y1="{fnum(y)}" x2="{fnum(x+w)}" y2="{fnum(y+h)}" stroke="#ccc"/>'
                f'<line x1="{fnum(x+w)}" y1="{fnum(y)}" x2="{fnum(x)}" y2="{fnum(y+h)}" stroke="#ccc"/>'
                + self.text_tag(x, y + h / 2 - 8, w, 16, "▣ " + str(label), st, vcenter=True))

    def _table(self, o, box):
        x0, y0, w, h = (num(v, 0) for v in box[:4])
        cols = o.get("columns") or []
        header = o.get("header")
        rows = o.get("rows") or []
        visual = ([("h", header)] if header else []) + [("b", r) for r in rows]
        nrow = max(1, len(visual))
        ncol = max(1, len(cols) or (max((len(r) for _, r in visual), default=1)))
        cw = [num(c.get("width"), None) if isinstance(c, dict) else None for c in cols]
        cw += [None] * (ncol - len(cw))
        known = sum(v for v in cw if v)
        free = [i for i, v in enumerate(cw) if not v]
        each = (w - known) / len(free) if free else 0
        for i in free:
            cw[i] = each
        colx = [x0 + sum(cw[:k]) for k in range(ncol)]
        rh = h / nrow
        out = [f'<rect x="{fnum(x0)}" y="{fnum(y0)}" width="{fnum(w)}" height="{fnum(h)}" fill="white" stroke="#bbb"/>']
        st_h = {"family": "sans-serif", "size": min(13, rh * 0.5), "weight": "bold",
                "italic": False, "color": "#fff", "align": "left", "lh": 1.2}
        st_c = {**st_h, "weight": "normal", "color": "#222"}
        for ri, (kind, row) in enumerate(visual):
            ry = y0 + ri * rh
            if kind == "h":
                out.append(f'<rect x="{fnum(x0)}" y="{fnum(ry)}" width="{fnum(w)}" height="{fnum(rh)}" fill="#3b6ea5"/>')
            elif o.get("zebra") and (ri % 2):
                out.append(f'<rect x="{fnum(x0)}" y="{fnum(ry)}" width="{fnum(w)}" height="{fnum(rh)}" fill="#f4f6f9"/>')
            st = st_h if kind == "h" else st_c
            for ci in range(ncol):
                cell = row[ci] if ci < len(row) else ""
                txt = cell.get("content", "") if isinstance(cell, dict) else ("" if cell is None else str(cell))
                out.append(self.text_tag(colx[ci] + 4, ry, cw[ci] - 6, rh, txt, st, vcenter=True))
            out.append(f'<line x1="{fnum(x0)}" y1="{fnum(ry)}" x2="{fnum(x0+w)}" y2="{fnum(ry)}" stroke="#ddd"/>')
        for cx in colx[1:]:
            out.append(f'<line x1="{fnum(cx)}" y1="{fnum(y0)}" x2="{fnum(cx)}" y2="{fnum(y0+h)}" stroke="#eee"/>')
        return "".join(out)

    # ---- page / flow ------------------------------------------------------- #
    def canvas_wh(self, page):
        c = page.get("canvas")
        if c is None and page.get("master"):
            c = (self.masters.get(page["master"]) or {}).get("canvas")
        if isinstance(c, str):
            return PRESETS.get(c, DEFAULT_WH)
        if isinstance(c, dict):
            if is_point(c.get("size")):
                return tuple(c["size"][:2])
            if c.get("preset"):
                return PRESETS.get(c["preset"], DEFAULT_WH)
        return DEFAULT_WH

    def _svg(self, w, h, body):
        defs = f"<defs>{''.join(self._defs)}</defs>" if self._defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{fnum(w)}" height="{fnum(h)}" '
                f'viewBox="0 0 {fnum(w)} {fnum(h)}">'
                f'<rect width="100%" height="100%" fill="white"/>{defs}{body}</svg>\n')

    def render_page(self, page):
        """Return a list of SVG strings (1 for page-mode, N for paginated flow)."""
        self._defs = []
        w, h = self.canvas_wh(page)
        if page.get("mode") == "flow":
            return self._render_flow(page, w, h)
        body = []
        for layer in sorted(page.get("layers") or [], key=lambda L: L.get("z", 0)):
            lo = layer.get("opacity")
            inner = "".join(self.obj(o) for o in (layer.get("objects") or []))
            body.append(f'<g opacity="{fnum(lo)}">{inner}</g>' if lo not in (None, 1) else inner)
        return [self._svg(w, h, "".join(body))]

    def _render_flow(self, page, w, h):
        margin = 56
        x, top, bottom = margin, margin, h - margin
        usable = w - 2 * margin
        pages, body, cy = [], [], top

        def flush():
            if body:
                pages.append(self._svg(w, h, "".join(body)))

        def newpage():
            nonlocal body, cy
            flush()
            self._defs = []
            body, cy = [], top

        def wrap(text, size):
            cpl = max(8, int(usable / (size * 0.52)))
            words, lines, cur = str(text).split(), [], ""
            for word in words:
                if cur and len(cur) + 1 + len(word) > cpl:
                    lines.append(cur); cur = word
                else:
                    cur = (cur + " " + word).strip()
            if cur:
                lines.append(cur)
            return lines or [""]

        def emit(text, st, indent=0, gap_after=6):
            nonlocal cy
            for ln in wrap(text, st["size"]):
                if cy + st["size"] > bottom:
                    newpage()
                body.append(self.text_tag(x + indent, cy, usable - indent, st["size"] * st["lh"],
                                          ln, st, vcenter=False))
                cy += st["size"] * st["lh"]
            cy += gap_after

        base = {"family": "serif", "size": 12, "weight": "normal", "italic": False,
                "color": "#1c1c1c", "align": "left", "lh": 1.4}
        for fl in page.get("story") or []:
            if not isinstance(fl, dict):
                continue
            ft = fl.get("type")
            stref = self.text_style(fl.get("style")) if fl.get("style") else None
            if ft == "heading":
                sz = max(15, 30 - 3 * (fl.get("level", 1) - 1))
                emit(fl.get("text", ""), {**base, "size": sz, "weight": "bold",
                                          **({"color": stref["color"]} if stref else {})}, gap_after=10)
            elif ft == "paragraph":
                txt = fl.get("text")
                if txt is None and fl.get("spans"):
                    txt = "".join(s if isinstance(s, str) else s.get("text", "") for s in fl["spans"])
                emit(txt or "", stref or base)
            elif ft == "list":
                for it in fl.get("items", []):
                    txt = it if isinstance(it, str) else (it.get("text", "") if isinstance(it, dict) else str(it))
                    emit("• " + str(txt), base, indent=16, gap_after=2)
                cy += 6
            elif ft == "spacer":
                cy += num(fl.get("height"), 12) or 12
            elif ft in ("page_break", "column_break"):
                newpage()
            else:                                      # table/figure/image/code/math/toc/...
                if cy + 26 > bottom:
                    newpage()
                ph = {**base, "family": "monospace", "size": 11, "italic": True, "color": "#999"}
                body.append(f'<rect x="{fnum(x)}" y="{fnum(cy)}" width="{fnum(usable)}" height="22" '
                            f'fill="#f5f5f5" stroke="#ddd" stroke-dasharray="3 3"/>')
                body.append(self.text_tag(x + 6, cy, usable, 22, f"[{ft}]", ph, vcenter=True))
                cy += 30
        flush()
        return pages or [self._svg(w, h, "")]


# --------------------------------------------------------------------------- #
#  driver                                                                     #
# --------------------------------------------------------------------------- #
def discover(paths):
    """Expand args (files / dirs / globs) into a sorted list of FrameGraph docs."""
    exts = (".json", ".yaml", ".yml")
    out = []
    if not paths:
        paths = [FIXTURES]
    for p in paths:
        cand = glob.glob(p, recursive=True) or ([p] if os.path.exists(p) else [])
        for c in cand:
            if os.path.isdir(c):
                for root, _, files in os.walk(c):
                    out += [os.path.join(root, f) for f in files if f.endswith(exts)]
            elif c.endswith(exts):
                out.append(c)
    seen, docs = set(), []
    for f in sorted(set(out)):
        try:
            d = yaml.safe_load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("dsl") == "FrameGraph" and d.get("pages"):
            rp = os.path.relpath(f, ROOT)
            if rp not in seen:
                seen.add(rp); docs.append((f, d))
    return docs


def stem_of(path):
    # keep the extension so docusign.fg.json and docusign.fg.yaml stay distinct
    rel = os.path.relpath(path, FIXTURES) if path.startswith(FIXTURES) else os.path.basename(path)
    return rel.replace(os.sep, "_")


def write_index(out_dir, entries, title, page_links=False):
    cards = []
    for name, link, thumbs in entries:
        if page_links:
            imgs = "".join(
                f'<a href="{esc(t)}"><img src="{esc(t)}" loading="lazy" '
                f'style="width:200px;border:1px solid #ccc;margin:4px;background:#fff"></a>'
                for t in thumbs)
            cards.append(f'<section><h2>{esc(name)} '
                         f'<small style="color:#888">({len(thumbs)} page(s))</small></h2>{imgs}</section>')
        else:
            first = f'<img src="{esc(thumbs[0])}" loading="lazy" style="width:240px;border:1px solid #ccc;background:#fff">' if thumbs else ""
            cards.append(f'<a href="{esc(link)}" style="text-decoration:none;color:inherit">'
                         f'<figure style="display:inline-block;margin:8px;vertical-align:top">'
                         f'{first}<figcaption style="font:13px sans-serif;max-width:240px">{esc(name)} '
                         f'<span style="color:#888">({len(thumbs)}p)</span></figcaption></figure></a>')
    body = "".join(cards)
    doc = (f'<!doctype html><meta charset="utf-8"><title>{esc(title)}</title>'
           f'<body style="font:14px sans-serif;margin:24px;background:#fafafa">'
           f'<h1>{esc(title)}</h1>{body}</body>')
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(doc)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="files / dirs / globs (default: all fixtures/)")
    ap.add_argument("--all", action="store_true", help="render every fixture under fixtures/")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "render"), help="output dir")
    ap.add_argument("--max-pages", type=int, default=0, help="cap pages rendered per doc (0 = all)")
    ap.add_argument("--list", action="store_true", help="list discoverable docs and exit")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    docs = discover([] if args.all else args.paths)
    if args.list:
        for f, _ in docs:
            print(os.path.relpath(f, ROOT))
        print(f"\n{len(docs)} document(s).")
        return 0
    if not docs:
        print("No FrameGraph documents found. Try: render_fixtures.py --all", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    index_entries, total_pages = [], 0
    for f, doc in docs:
        stem = stem_of(f)
        doc_dir = os.path.join(args.out, stem)
        os.makedirs(doc_dir, exist_ok=True)
        r = Renderer(doc, os.path.dirname(os.path.abspath(f)))
        svgs, thumbs = [], []
        for page in doc.get("pages", []):
            if not isinstance(page, dict):
                continue
            for s in r.render_page(page):
                svgs.append(s)
                if args.max_pages and len(svgs) >= args.max_pages:
                    break
            if args.max_pages and len(svgs) >= args.max_pages:
                break
        for i, s in enumerate(svgs, 1):
            fn = f"p{i:03d}.svg"
            with open(os.path.join(doc_dir, fn), "w", encoding="utf-8") as fh:
                fh.write(s)
            thumbs.append(f"{stem}/{fn}")
        write_index(doc_dir, [(stem, "", [f"p{i:03d}.svg" for i in range(1, len(svgs) + 1)])],
                    f"FrameGraph proxy — {stem}", page_links=True)
        index_entries.append((stem, f"{stem}/index.html", thumbs))
        total_pages += len(svgs)
        if not args.quiet:
            note = f" ({r.skipped} skipped)" if r.skipped else ""
            print(f"  {stem}: {len(svgs)} page(s){note}")

    write_index(args.out, index_entries, "FrameGraph fixtures — SVG proxy contact sheet")
    print(f"\nRendered {len(docs)} document(s), {total_pages} page(s) -> {args.out}")
    print(f"Open {os.path.join(args.out, 'index.html')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
