#!/usr/bin/env python3
# render_fg_doc.py <yml> <base_dir_for_assets> <outdir> <montage.png>
# Generalized proxy: rect/line/text/image/table (+defs.assets). Sanity check, NOT a conformant renderer.
# HEAD-patched: stroke is PAINT-ONLY (P3); stroke geometry comes from stroke_style (token or inline);
# `size` content-sizing reads from `sizing` (P4). DejaVu stand-in fonts.
import sys, os, re, yaml
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from PIL import Image, ImageDraw

YML, BASE, OUTDIR, MONT = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
os.makedirs(OUTDIR, exist_ok=True)
SCALE, DPI = 1.6, 100; PT = 0.72 * SCALE
doc = yaml.safe_load(open(YML))
T = doc["defs"]["tokens"]; COLORS = T["colors"]; TS = T["text_styles"]; SS = T["stroke_styles"]
ASSETS = doc["defs"].get("assets", {})
FAMILY = {"sans": "DejaVu Sans", "serif": "DejaVu Serif", "mono": "DejaVu Sans Mono"}

def rc(c, dep=0):
    if c is None or dep > 5: return None
    if isinstance(c, str):
        if c in COLORS: return rc(COLORS[c], dep + 1)
        s = c.strip()
        if s.lower() in ("none", "transparent"): return None
        m = re.match(r"rgba?\(([^)]+)\)", s)
        if m:
            v = [x.strip() for x in m.group(1).split(",")]; r, g, b = [int(float(x))/255 for x in v[:3]]
            a = float(v[3]) if len(v) > 3 else 1.0; return None if a == 0 else (r, g, b, a)
        if s.startswith("#") or re.match(r"^[A-Za-z]+$", s): return s
    return None

def resolve_asset(src):
    if src in ASSETS: src = ASSETS[src].get("src", src)
    return src if os.path.isabs(src) else os.path.normpath(os.path.join(BASE, src))

def stroke_paint_width(o, default_w=1.0):
    # HEAD P3: paint from `stroke` (a colour); geometry from `stroke_style` (token or inline).
    ssv = o.get("stroke_style")
    bundle = SS.get(ssv, {}) if isinstance(ssv, str) else (ssv or {})
    paint = rc(o.get("stroke")) if isinstance(o.get("stroke"), str) else rc(bundle.get("color"))
    width = bundle.get("width", default_w) * SCALE * 0.6
    return paint, width

def render(p, i):
    W, H = p["canvas"]["size"]
    fig = plt.figure(figsize=(W/DPI*SCALE, H/DPI*SCALE), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    for L in sorted(p.get("layers", []), key=lambda l: l.get("z", 0)):
        for o in L.get("objects", []):
            t = o.get("type"); box = o.get("box")
            if t == "rect" and box:
                x, y, w, h = box; ec, lw = stroke_paint_width(o, 1.0)
                ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=rc(o.get("fill")) or "none",
                             edgecolor=ec or "none", linewidth=lw if ec else 0, zorder=L.get("z", 0)))
            elif t == "image" and box and o.get("src"):
                x, y, w, h = box; ap = resolve_asset(o["src"])
                if os.path.exists(ap):
                    ax.imshow(Image.open(ap).convert("RGBA"), extent=[x, x+w, y+h, y],
                              zorder=L.get("z", 0)+0.1, aspect="auto")
            elif t == "table" and box:
                x0, y0, w, h = box
                cols = o.get("columns") or [{"width": 1}]
                ncol = len(cols)
                widths = [c.get("width", w / ncol) for c in cols]
                tot = sum(widths) or 1; widths = [wd / tot * w for wd in widths]
                colx = [x0 + sum(widths[:k]) for k in range(ncol)]
                sty = o.get("style") or {}
                hdr_fill = rc(sty.get("header_fill", "brand")) or "#0d9648"
                zeb = rc(sty.get("zebra_fill", "#f4f8f5")) or "#f4f8f5"
                bord = rc(sty.get("border", "hairline")) or "#c2cac4"
                hstyle = TS.get(sty.get("header_text", "tbl_header"), {"size": 10, "weight": 700})
                cstyle = TS.get(sty.get("cell_text", "tbl_cell"), {"size": 10, "weight": 400})
                header = o.get("header"); body = o.get("rows") or []
                visual = ([("h", header)] if header else []) + [("b", r) for r in body]
                rh = h / max(1, len(visual)); z = L.get("z", 0)
                for ri, (kind, row) in enumerate(visual):
                    ry = y0 + ri * rh
                    if kind == "h":
                        ax.add_patch(plt.Rectangle((x0, ry), w, rh, facecolor=hdr_fill, edgecolor="none", zorder=z))
                        st = hstyle; tc = rc(st.get("color", "on_brand")) or "#fff"
                    else:
                        if (ri % 2) == (1 if header else 0):
                            ax.add_patch(plt.Rectangle((x0, ry), w, rh, facecolor=zeb, edgecolor="none", zorder=z))
                        st = cstyle; tc = rc(st.get("color", "ink")) or "#1c1c1c"
                    fs = st.get("size", 10) * PT
                    wt = "bold" if str(st.get("weight", 400)) in ("700", "800", "900", "bold") else "normal"
                    prop = FontProperties(family="DejaVu Sans", weight=wt)
                    for ci in range(ncol):
                        cell = row[ci] if ci < len(row) else ""
                        txt = cell.get("content", "") if isinstance(cell, dict) else str(cell)
                        if txt:
                            ax.text(colx[ci] + 4, ry + rh / 2, txt, fontproperties=prop, fontsize=fs,
                                    color=tc, ha="left", va="center", zorder=z + 0.3, clip_on=True)
                # grid lines (hairline)
                for ri in range(len(visual) + 1):
                    ax.plot([x0, x0 + w], [y0 + ri * rh] * 2, color=bord, linewidth=0.8, zorder=z + 0.2)
                for cx in colx + [x0 + w]:
                    ax.plot([cx, cx], [y0, y0 + h], color=bord, linewidth=0.8, zorder=z + 0.2)
            elif t == "line":
                fr, to = o.get("from"), o.get("to")
                col, lw = stroke_paint_width(o, 1.0); col = col or "#000"
                if fr and to: ax.plot([fr[0], to[0]], [fr[1], to[1]], color=col, linewidth=lw, zorder=L.get("z", 0))
            elif t == "text" and box:
                x, y, w, h = box; st = TS.get(o.get("style"), {})
                fam = FAMILY.get(st.get("font", "sans"), "DejaVu Sans")
                wt = "bold" if str(st.get("weight", 400)) in ("700","800","900","bold") else "normal"
                prop = FontProperties(family=fam, weight=wt, style="italic" if st.get("italic") else "normal")
                col = rc(st.get("color", "#000")) or "#000"
                base = st.get("size", 12); wrap = st.get("wrap"); ovf = st.get("overflow")
                # HEAD P4: a content-sizing hint lives in `sizing` (not `size`)
                _sz = o.get("sizing") or {}
                lh = st.get("line_height", 1.2); minfs = st.get("min_font_size", base * 0.45)
                ha = st.get("align", "left"); s = o.get("text", "")
                def meas(txt, sz):
                    if not txt: return 0.0
                    return TextPath((0, 0), txt, size=sz, prop=prop).get_extents().width
                def wrap_to(words, sz):
                    lines, cur = [], ""
                    for wd in words:
                        trial = (cur + " " + wd).strip()
                        if cur and meas(trial, sz) > w: lines.append(cur); cur = wd
                        else: cur = trial
                    if cur: lines.append(cur)
                    return lines or [""]
                sz = base
                if wrap:
                    lines = wrap_to(s.split(), sz)
                    if ovf == "shrink_to_fit":
                        while sz > minfs and (len(lines) * lh * sz > h + 1 or any(meas(ln, sz) > w + 1 for ln in lines)):
                            sz -= 1; lines = wrap_to(s.split(), sz)
                else:
                    lines = [s]
                    if ovf == "shrink_to_fit":
                        while sz > minfs and meas(s, sz) > w + 1: sz -= 1
                fs = sz * PT; tx = x + (w / 2 if ha == "center" else (w if ha == "right" else 0))
                hav = ha if ha in ("left", "center", "right") else "left"
                clip = ovf in ("clip", "shrink_to_fit")
                for li, ln in enumerate(lines):
                    ax.text(tx, y + li * lh * sz + sz * 0.12, ln, fontproperties=prop, fontsize=fs,
                            color=col, ha=hav, va="top", zorder=L.get("z", 0) + 0.2, clip_on=clip)
    out = os.path.join(OUTDIR, f"page_{i+1:02d}.png"); fig.savefig(out, dpi=DPI); plt.close(fig); return out

paths = [render(p, i) for i, p in enumerate(doc["pages"])]
cols, rows = 5, 7; tw = 230; pad = 10; lbl = 16
ts0 = Image.open(paths[0]); th = int(tw*ts0.height/ts0.width); cw, ch = tw+pad, th+pad+lbl
sheet = Image.new("RGB", (cols*cw+pad, rows*ch+pad), "#ededed"); dr = ImageDraw.Draw(sheet)
for i, pth in enumerate(paths):
    r, c = divmod(i, cols); x = pad+c*cw; y = pad+r*ch
    sheet.paste(Image.open(pth).convert("RGB").resize((tw, th)), (x, y+lbl)); dr.text((x+2, y+2), f"p{i+1}", fill="#222")
sheet.save(MONT); print("rendered", len(paths), "-> contact sheet", MONT, sheet.size)
