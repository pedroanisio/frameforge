#!/usr/bin/env python3
"""FrameGraph v2 — doc-ray Database Reference (A4, ERD + full data dictionary).

A multi-page A4 print reference for the doc-ray PostgreSQL schema, authored
through the FrameGraph v2 SDK: a cover, a one-page ERD (the layered
architecture), then the complete data dictionary — every table's columns
(type · null · key · notes), keys/constraints/index counts, and RLS path —
grouped by NLP layer and paginated across A4 pages.

The schema facts are pulled from the LIVE catalog by a companion extractor
(scratchpad/dbdict_extract.py, which reuses scripts/gen_data_dictionary.py) into
a JSON side-file, so this renderer stays pure layout and never drifts.

Run from the repository root (JSON path via env or arg)::

    DBDICT=/path/dbdict.json uv run python examples/doc_ray_a4_reference.py
    uv run --group pdfout python tooling/render_pdf.py doc-ray-database-a4.fg.yaml --out out/pdf
"""
from __future__ import annotations

import json
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, serialize  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

DBDICT = os.environ.get("DBDICT") or (sys.argv[1] if len(sys.argv) > 1 else "dbdict.json")

# A4 @ 96 dpi
PW, PH = 794, 1123                 # portrait
LW, LH = 1123, 794                 # landscape (ERD)
MX = 56
CW = PW - 2 * MX                   # 682
TOP = 138
BOTTOM = PH - 58                   # 1065

SANS = ["Inter", "Helvetica", "Arial", "sans-serif"]
MONO = ["JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"]

PAPER = "#FFFFFF"
INK = "#0F172A"
MUTE = "#475569"
MUTE2 = "#94A3B8"
LINE = "#E8EDF2"
BRAND, BRAND_SOFT = "#2563EB", "#EBF1FE"
LAYER, LAYER_SOFT = "#0E7490", "#E6F6F9"
RBAC, RBAC_SOFT = "#7C3AED", "#F2ECFE"
STORE = "#475569"
PANEL = "#F8FAFC"
HEADBG = "#F1F5F9"
CHIP_STROKE = "#CBD5E1"
CARD_STROKE = "#D6DBE0"

# group index → (accent, soft) for section bands + table accents
GROUP_ACCENT = {
    0: (BRAND, BRAND_SOFT), 1: (STORE, "#EEF2F6"), 2: (BRAND, BRAND_SOFT),
    3: (BRAND, BRAND_SOFT), 4: (LAYER, LAYER_SOFT), 5: (LAYER, LAYER_SOFT),
    6: (LAYER, LAYER_SOFT), 7: (LAYER, LAYER_SOFT), 8: (LAYER, LAYER_SOFT),
    9: (RBAC, RBAC_SOFT), 10: (MUTE, "#EEF2F6"),
}

FOOTER = "doc-ray · Database ERD & Data Dictionary"


# ── primitives ─────────────────────────────────────────────────────────────
def T(x, y, w, h, s, *, size=11, color=INK, weight=None, align="left", font=None,
      track=None, lh=None, upper=False):
    st = {"font_size": size, "color": color, "overflow": "shrink_to_fit",
          "font_family": font or SANS}
    if weight:
        st["font_weight"] = weight
    if align != "left":
        st["text_align"] = align
    if track is not None:
        st["letter_spacing"] = track
    if lh is not None:
        st["line_height"] = lh
    if upper:
        st["text_transform"] = "uppercase"
    return {"type": "text", "box": [x, y, w, h], "text": s, "style": st, "decorative": True}


def R(x, y, w, h, **f):
    return {"type": "rect", "box": [x, y, w, h], "decorative": True, **f}


def LN(x1, y1, x2, y2, *, color=LINE, width=1.0, dash=None):
    ss = {"stroke_width": width}
    if dash:
        ss["stroke_dasharray"] = list(dash)
    return {"type": "line", "from": [x1, y1], "to": [x2, y2], "stroke": color,
            "stroke_style": ss, "decorative": True}


def ELP(cx, cy, r, **f):
    return {"type": "ellipse", "center": [cx, cy], "rx": r, "ry": r, "decorative": True, **f}


def ARR(x1, y1, x2, y2, *, color=INK, width=1.3, head=4.0):
    """A directional arrow composed from a line + a polyline arrowhead (primitives)."""
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1.0
    ux, uy = dx / ln, dy / ln
    px, py = -uy, ux
    hx, hy = x2 - ux * head, y2 - uy * head
    return [
        {"type": "line", "from": [x1, y1], "to": [x2, y2], "stroke": color,
         "stroke_style": {"stroke_width": width}, "decorative": True},
        {"type": "polyline", "fill": "none", "stroke": color,
         "stroke_style": {"stroke_width": width}, "decorative": True,
         "points": [[hx + px * head * 0.55, hy + py * head * 0.55], [x2, y2],
                    [hx - px * head * 0.55, hy - py * head * 0.55]]},
    ]


def chip(x, y, w, h, text, *, fill=PAPER, stroke=CHIP_STROKE, tcolor=INK, weight=None,
         size=11, sw=1.0, font=None):
    return [R(x, y, w, h, fill=fill, stroke=stroke, stroke_style={"stroke_width": sw}, radius=6),
            T(x, y + (h - size) / 2 - 1, w, size + 4, text, size=size, color=tcolor,
              weight=weight, align="center", font=font)]


def panel(x, y, w, h, *, fill=PANEL, stroke=CARD_STROKE, sw=1.0, accent=None):
    out = [R(x, y, w, h, fill=fill, stroke=stroke, stroke_style={"stroke_width": sw}, radius=8)]
    if accent:
        out.append(R(x, y, w, 6, fill=accent, radius=2))
    return out


class Report:
    def __init__(self, b, data):
        self.b = b
        self.data = data
        self.version = data.get("version", "0.0.0")
        self.pageno = 0
        self.section = ""
        self.L = None
        self.y = 0

    # -- full custom pages ---------------------------------------------------
    def cover(self):
        self.pageno += 1
        page = self.b.page("cover", canvas={"size": [PW, PH], "units": "px"},
                           coordinate_mode="absolute")
        L = page.layer("main")
        for o in [R(0, 0, PW, PH, fill=PAPER),
                  R(0, 0, PW, 250, fill=INK),
                  R(MX, 250 - 6, 96, 6, fill=BRAND)]:
            L.add(o)
        L.add(T(MX, 92, CW, 20, "POSTGRESQL SCHEMA REFERENCE", size=12, color="#93C5FD",
                weight=700, upper=True, track=2))
        L.add(T(MX, 120, CW, 56, "doc-ray", size=52, color="#FFFFFF", weight=800))
        L.add(T(MX, 188, CW, 30, "Database — ERD & Data Dictionary", size=20,
                color="#CBD5E1", weight=500))
        # SemVer badge (top-right on the dark header): dot + label, even padding
        vb = f"SCHEMA v{self.version}"
        tw = len(vb) * 6.2
        pad, dotr, gap, bh = 15, 3, 8, 28
        bw = pad + dotr * 2 + gap + tw + pad
        bx, by = PW - MX - bw, 94
        L.add(R(bx, by, bw, bh, fill="#1D4ED8", stroke="#3B82F6",
                stroke_style={"stroke_width": 1}, radius=bh / 2))
        L.add(ELP(bx + pad + dotr, by + bh / 2, dotr, fill="#93C5FD"))
        L.add(T(bx + pad + dotr * 2 + gap, by + (bh - 12) / 2, tw + 6, 13, vb,
                size=10.5, color="#FFFFFF", weight=700))
        ntab = len(self.data["tables"])
        ncol = sum(len(t["columns"]) for t in self.data["tables"].values())
        L.add(T(MX, 292, CW, 60,
                "A first-class, 4NF document entity feeding a shared span/annotation "
                "backbone, the 20-layer NLP annotation stack, and document-level "
                "row-level security. Generated from the live catalog.",
                size=13, color=INK, lh=1.55))
        facts = [("43", "tables"), (str(ncol), "columns"), ("PG 16", "+ pgvector"),
                 ("4NF", "normalized"), ("RLS", "33 tables")]
        fx, fw = MX, (CW - 4 * 14) / 5
        for i, (v, lab) in enumerate(facts):
            x = fx + i * (fw + 14)
            for o in panel(x, 372, fw, 74, fill=PANEL, accent=BRAND):
                L.add(o)
            L.add(T(x + 14, 388, fw - 20, 30, v, size=22, color=INK, weight=800))
            L.add(T(x + 14, 420, fw - 20, 16, lab, size=10, color=MUTE))
        # contents
        L.add(T(MX, 486, CW, 18, "CONTENTS", size=11, color=MUTE, weight=700, track=1.5))
        yy = 512
        toc = [("Entity-relationship diagram", "the layered architecture, one page")]
        toc += [(g["title"], f"{len(g['tables'])} table" + ("s" if len(g["tables"]) != 1 else ""))
                for g in self.data["groups"]]
        for t, d in toc:
            L.add(LN(MX, yy + 26, MX + CW, yy + 26))
            L.add(T(MX, yy + 4, CW - 120, 18, t, size=12.5, color=INK, weight=600))
            L.add(T(MX + CW - 120, yy + 4, 120, 18, d, size=10.5, color=MUTE, align="right"))
            yy += 30
        L.add(T(MX, PH - 48, CW, 16,
                "Generated by examples/doc_ray_a4_reference.py from the live PostgreSQL "
                "catalog · figures reflect the applied migration set.",
                size=9.5, color=MUTE2))

    def erd(self):
        self.pageno += 1
        page = self.b.page("erd", canvas={"size": [PW, PH], "units": "px"},
                           coordinate_mode="absolute")
        L = page.layer("main")
        L.add(R(0, 0, PW, PH, fill=PAPER))
        L.add(T(MX, 54, CW, 20, "doc-ray · Database Reference", size=10.5, color=MUTE,
                weight=700, upper=True, track=1.5))
        L.add(T(MX, 74, CW, 30, "Entity-Relationship Diagram", size=22, color=INK, weight=800))
        L.add(LN(MX, 112, MX + CW, 112))

        def add(objs):
            for o in objs:
                L.add(o)

        # connectors (behind the panels) — dashed flow + violet RBAC gate
        FLOW = "#C4CBD4"
        add([LN(MX + 150, 231, MX + 166, 231, color=FLOW, dash=[5, 4]),   # store → document
             LN(MX + 326, 306, MX + 326, 344, color=FLOW, dash=[5, 4])])  # document → backbone
        for cx in (MX + 109, MX + 341, MX + 573):
            add([LN(cx, 452, cx, 486, color=FLOW, dash=[5, 4])])          # backbone -> NLP band
        for cx in (MX + 109, MX + 341):                                   # gate under the row-2 cards
            add([LN(cx, 736, cx, 748, color=RBAC, dash=[2, 4])])

        # Row 1 — store · document · provenance
        add(panel(MX, 156, 150, 150, fill=STORE, stroke=STORE))
        add([T(MX, 174, 150, 18, "Object store", size=12, color="#FFFFFF", weight=700, align="center")])
        add(chip(MX + 18, 210, 114, 34, "MinIO / S3", fill="#FFFFFF"))
        add([T(MX, 258, 150, 30, "blobs by sha256\n(s3:// pointer)", size=9.5,
               color="#E2E8F0", align="center", lh=1.3)])

        dx = MX + 166
        add(panel(dx, 156, 320, 150, accent=BRAND))
        add([T(dx + 14, 170, 300, 18, "Document entity · 4NF", size=13, color=INK, weight=700)])
        add(chip(dx + 14, 200, 140, 32, "documents", fill=BRAND_SOFT, stroke=BRAND,
                 tcolor=BRAND, weight=700, font=MONO, size=10.5))
        add(chip(dx + 162, 200, 144, 32, "document_content", fill="#FFFFFF", font=MONO, size=10))
        add(chip(dx + 14, 238, 292, 28, "authors · tags · identifiers · metadata (4NF satellites)",
                 fill="#FFFFFF", size=9.5))
        add(chip(dx + 14, 270, 292, 26, "derived_from -> documents  ·  document_content(+FTS)",
                 fill="#FFFFFF", size=9.5))

        px = MX + 502
        add(panel(px, 156, 180, 150, accent=STORE))
        add([T(px + 14, 170, 160, 16, "Provenance", size=12, color=INK, weight=700)])
        add(chip(px + 14, 198, 152, 30, "document_provenance", fill="#FFFFFF", font=MONO, size=9))
        add(chip(px + 14, 232, 152, 28, "provenance_params", fill="#FFFFFF", font=MONO, size=9))
        add([T(px + 14, 266, 152, 28, "append-only · actor -> principals", size=9, color=MUTE, lh=1.3)])

        # Row 2 — backbone
        add(panel(MX, 344, CW, 108, fill=BRAND_SOFT, stroke=BRAND, sw=1.25, accent=BRAND))
        add([T(MX + 14, 356, CW - 28, 18,
               "Span registry & annotation backbone — stand-off over shared spans",
               size=12.5, color=INK, weight=700)])
        bchips = [("spans", 112, True), ("sentences", 108, False), ("annotations", 126, True),
                  ("lexemes", 96, False), ("lexeme_occurrences", 164, False)]
        bx = MX + 14
        for name, w, key in bchips:
            add(chip(bx, 386, w, 40, name, fill="#FFFFFF",
                     stroke=BRAND if key else CHIP_STROKE, tcolor=BRAND if key else INK,
                     weight=700 if key else None, font=MONO, size=10, sw=1.25 if key else 1.0))
            bx += w + 8

        # Row 3 — NLP band (grid of 5)
        add([T(MX, 494, CW, 16, "NLP ANNOTATION STACK · LAYERS 3–20", size=10,
               color=LAYER, weight=700, track=1.2)])
        cards = [
            ("Tokens & Morphology · L3–7", ["tokens", "token_feature", "subword"]),
            ("Syntax · L8–10", ["chunk", "constituent", "dependency"]),
            ("Reference · L11–13", ["entity_mention", "entity_link", "coref_chain/mention"]),
            ("Meaning · L14–19", ["srl · word_sense · amr", "discourse · timex", "event · tlink · sentiment"]),
            ("Embeddings · L20", ["embedding", "vector(768)", "pgvector HNSW"]),
        ]
        cw3 = (CW - 2 * 14) / 3
        for i, (title, rows) in enumerate(cards):
            r, c = divmod(i, 3)
            x = MX + c * (cw3 + 14)
            y = 514 + r * 118
            add(panel(x, y, cw3, 104, fill=LAYER_SOFT, stroke=LAYER, accent=LAYER))
            add([T(x + 12, y + 12, cw3 - 20, 16, title, size=11, color=INK, weight=700)])
            for j, rr in enumerate(rows):
                add([T(x + 12, y + 40 + j * 18, cw3 - 20, 16, rr, size=9.5, color=MUTE, font=MONO)])

        # Row 4 — RBAC
        add(panel(MX, 748, CW, 96, fill=RBAC_SOFT, stroke=RBAC, sw=1.25, accent=RBAC))
        add([R(MX + 14, 764, 16, 16, fill=RBAC, radius=4),
             T(MX + 38, 762, CW - 60, 18, "Row-Level Security · document-level RBAC",
               size=12.5, color=INK, weight=700)])
        rchips = ["principals", "roles", "permissions", "role_permissions", "principal_roles", "document_acl"]
        rx = MX + 14
        for name in rchips:
            w = 20 + len(name) * 6.4
            key = name == "document_acl"
            add(chip(rx, 796, w, 32, name, fill="#FFFFFF",
                     stroke=RBAC if key else CHIP_STROKE, tcolor=RBAC if key else INK,
                     weight=700 if key else None, font=MONO, size=9.5, sw=1.25 if key else 1.0))
            rx += w + 10
        add([T(MX, 858, CW, 16,
               "RLS gates all 33 document-scoped tables · reads = SELECT policy, writes = "
               "INSERT/UPDATE/DELETE · enforced via SET ROLE docray_client + app.principal_id",
               size=9.5, color=MUTE, lh=1.35)])
        self._chrome_footer(L)

    # -- dictionary pages (paginated) ---------------------------------------
    def _chrome_footer(self, L):
        L.add(LN(MX, PH - 44, MX + CW, PH - 44))
        L.add(T(MX, PH - 36, 500, 14, f"{FOOTER}  ·  schema v{self.version}", size=9, color=MUTE))
        L.add(T(MX + CW - 80, PH - 36, 80, 14, f"{self.pageno}", size=9, color=MUTE,
                align="right", weight=700))

    def _new_dict_page(self):
        self.pageno += 1
        page = self.b.page(f"dd{self.pageno:02d}", canvas={"size": [PW, PH], "units": "px"},
                           coordinate_mode="absolute")
        L = page.layer("main")
        L.add(R(0, 0, PW, PH, fill=PAPER))
        L.add(T(MX, 54, CW - 200, 16, "doc-ray · Data Dictionary", size=10, color=MUTE,
                weight=700, upper=True, track=1.5))
        L.add(T(MX + CW - 260, 54, 260, 16, self.section, size=10, color=MUTE, align="right"))
        L.add(LN(MX, 74, MX + CW, 74, color=LINE))
        self._chrome_footer(L)
        self.L = L
        self.y = 82

    def _ensure(self, h):
        if self.L is None or self.y + h > BOTTOM:
            self._new_dict_page()

    def section_header(self, gi, group):
        accent, soft = GROUP_ACCENT[gi]
        first_h = self._table_height(group["tables"][0])
        self._ensure(66 + min(first_h, 180))
        y = self.y
        desc = group["desc"].replace("`", "")
        for o in [R(MX, y, CW, 58, fill=accent, radius=8),
                  T(MX + 18, y + 10, CW - 36, 18, f"{gi + 1:02d} · {group['title']}",
                    size=14.5, color="#FFFFFF", weight=800),
                  T(MX + 18, y + 32, CW - 36, 22, desc, size=8.5, color="#EAF1FC", lh=1.28)]:
            self.L.add(o)
        self.y += 66

    def _row_h(self, note):
        lines = min(3, max(1, math.ceil(len(note) / 46))) if note else 1
        return 4 + lines * 11.5

    def _table_height(self, tname):
        t = self.data["tables"][tname]
        return 30 + 18 + sum(self._row_h(c["note"]) for c in t["columns"]) + 16

    def _render_key(self, L, x, y, keystr, accent):
        """Compose the KEY cell from primitives: PK/UQ tags + FK (label + drawn arrow + ref)."""
        cxx = x
        for p in [s.strip() for s in keystr.split(",") if s.strip()]:
            if p.startswith("FK"):
                ref = p.split("→", 1)[1] if "→" in p else p[2:].lstrip("→ ")
                L.add(T(cxx, y + 2, 15, 12, "FK", size=8.5, color=accent, weight=700))
                cxx += 15
                for o in ARR(cxx, y + 7.5, cxx + 8, y + 7.5, color=accent, width=1.0, head=2.6):
                    L.add(o)
                cxx += 11
                wref = min(len(ref) * 5.4 + 4, max(20, (x + 118) - cxx))
                L.add(T(cxx, y + 2, wref, 12, ref, size=8.5, color=accent, weight=600, font=MONO))
                cxx += wref + 6
            else:
                col = BRAND if p.startswith("PK") else MUTE
                L.add(T(cxx, y + 2, 34, 12, p, size=8.5, color=col, weight=700))
                cxx += len(p) * 5.6 + 8

    def table(self, gi, tname):
        accent, soft = GROUP_ACCENT[gi]
        t = self.data["tables"][tname]
        cols = t["columns"]
        th = self._table_height(tname)
        self._ensure(th)
        L, y = self.L, self.y
        # title bar
        L.add(R(MX, y, CW, 28, fill=soft, radius=6))
        L.add(R(MX, y, 4, 28, fill=accent, radius=2))
        L.add(T(MX + 14, y + 7, 300, 16, tname, size=12.5, color=INK, weight=700, font=MONO))
        meta = []
        if t["pk"]:
            meta.append("PK " + t["pk"])
        if t["fk_count"]:
            meta.append(f"{t['fk_count']} FK")
        if t["check_count"]:
            meta.append(f"{t['check_count']} CHECK")
        if t["index_count"]:
            meta.append(f"{t['index_count']} idx")
        if t["rls"] == "yes":
            meta.append("RLS: " + (t["rls_path"] or "yes").replace("→", "->"))
        L.add(T(MX + 300, y + 9, CW - 314, 14, "  ·  ".join(meta), size=8.5, color=MUTE,
                align="right"))
        y += 30
        # column header
        cx = [MX + 8, MX + 168, MX + 300, MX + 344, MX + 468]
        cw_note = CW - (468 - MX) - 8
        L.add(R(MX, y, CW, 18, fill=HEADBG))
        for label, x, w, al in [("COLUMN", cx[0], 156, "left"), ("TYPE", cx[1], 128, "left"),
                                ("NULL", cx[2], 40, "center"), ("KEY", cx[3], 120, "left"),
                                ("NOTES", cx[4], cw_note, "left")]:
            L.add(T(x, y + 3, w, 12, label, size=8, color=MUTE, weight=700, track=0.5, align=al))
        y += 18
        # rows
        for i, c in enumerate(cols):
            rh = self._row_h(c["note"])
            if i % 2 == 1:
                L.add(R(MX, y, CW, rh, fill="#FBFCFE"))
            L.add(T(cx[0], y + 2, 156, 12, c["name"], size=9.5, color=INK, font=MONO))
            L.add(T(cx[1], y + 2, 128, 12, c["type"], size=9, color=MUTE, font=MONO))
            # NULL as a primitive: filled disc = NOT NULL, open ring = nullable
            ncx = cx[2] + 20
            if c["null"]:
                L.add(ELP(ncx, y + 7, 3.1, fill="none", stroke=MUTE2,
                          stroke_style={"stroke_width": 1.2}))
            else:
                L.add(ELP(ncx, y + 7, 3.1, fill=accent))
            if c["key"]:
                self._render_key(L, cx[3], y, c["key"], accent)
            if c["note"]:
                L.add(T(cx[4], y + 1, cw_note, rh, c["note"], size=8.5, color=MUTE, lh=1.25))
            L.add(LN(MX, y + rh, MX + CW, y + rh, color="#EEF2F6", width=0.75))
            y += rh
        self.y = y + 16


def build() -> DocumentBuilder:
    data = json.load(open(DBDICT, encoding="utf-8"))
    b = DocumentBuilder(title="doc-ray — Database ERD & Data Dictionary",
                        profile="report", lang="en")
    rep = Report(b, data)
    rep.cover()
    rep.erd()
    for gi, group in enumerate(data["groups"]):
        rep.section = group["title"]
        rep.section_header(gi, group)
        for tname in group["tables"]:
            rep.table(gi, tname)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} A4 pages — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in errors[:20]:
        print(f"  [error] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "doc-ray-database-a4.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
