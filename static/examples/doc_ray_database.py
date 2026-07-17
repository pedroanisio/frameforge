#!/usr/bin/env python3
"""FrameForge v2 — doc-ray Database Architecture (SDK client).

A frameforge-v2 rendering of the doc-ray ERD / data dictionary (docs/DATABASE.md):
object store -> first-class 4NF document entity + append-only provenance ->
shared span/annotation backbone -> the 20-layer NLP annotation band ->
document-level RBAC enforced by row-level security as the cross-cutting gate.

Authored through the FrameForge v2 SDK (models are the source of truth), then
rendered by the repo's SVG proxy and stitched to PDF by tooling/render_pdf.py.

Run from the repository root::

    uv run python examples/doc_ray_database.py                    # -> .svg + .fg.yaml
    uv run --group pdfout python tooling/render_pdf.py \
        doc-ray-database.fg.yaml --out out/pdf                    # -> out/pdf/*.pdf
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder, render_page_svgs, serialize  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1600, 960
CANVAS = {"size": [W, H], "units": "px"}
SANS = ["Inter", "Helvetica", "Arial", "sans-serif"]

# palette (mirrors the v1 representation)
PAGE = "#FFFFFF"
INK = "#0F172A"
MUTE = "#475569"
BRAND = "#2563EB"
BRAND_SOFT = "#EBF1FE"
PANEL = "#F8FAFC"
CARD = "#FFFFFF"
CARD_STROKE = "#D6DBE0"
CHIP_STROKE = "#CBD5E1"
LAYER = "#0E7490"
LAYER_SOFT = "#E6F6F9"
RBAC = "#7C3AED"
RBAC_SOFT = "#F2ECFE"
STORE = "#475569"
CONN = "#C4CBD4"


def ts(size, color, *, weight=None, align=None, spacing=None, lh=None):
    s = {"font_family": SANS, "font_size": size, "color": color}
    if weight is not None:
        s["font_weight"] = weight
    if align is not None:
        s["align"] = align
    if spacing is not None:
        s["letter_spacing"] = spacing
    if lh is not None:
        s["line_height"] = lh
    return s


def panel(page, box, *, fill, stroke, sw=1.0, accent=None):
    x, y, w, h = box
    page.rect([x, y, w, h], radius=8, fill=fill, stroke=stroke,
              stroke_style={"stroke_width": sw})
    if accent:
        page.rect([x, y, w, 6], radius=2, fill=accent)


def head(page, x, y, w, text, *, color=INK, size=15, weight=700, align=None):
    page.text([x, y, w, size + 6], text, style=ts(size, color, weight=weight, align=align))


def chip(page, box, text, *, fill=CARD, stroke=CHIP_STROKE, tcolor=INK,
         weight=None, size=12, sw=1.0):
    x, y, w, h = box
    page.rect([x, y, w, h], radius=6, fill=fill, stroke=stroke,
              stroke_style={"stroke_width": sw})
    page.text([x, y + (h - size) / 2 - 1, w, size + 4], text,
              style=ts(size, tcolor, weight=weight, align="center"))


def ctext(page, x, y, w, text, *, color=INK, size=12, weight=None):
    page.text([x, y, w, size + 4], text, style=ts(size, color, weight=weight, align="center"))


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="doc-ray — Database Architecture",
                        profile="diagram", lang="en")
    page = b.page("doc-ray-database", canvas=CANVAS, coordinate_mode="absolute")

    # ── background + title ────────────────────────────────────────────────
    page.layer("bg")
    page.rect([0, 0, W, H], fill=PAGE)

    # ── flow connectors (behind panels) ───────────────────────────────────
    page.layer("connectors")
    flow = {"stroke_width": 1.4, "stroke_dasharray": [5, 4]}
    gate = {"stroke_width": 1.3, "stroke_dasharray": [2, 4]}
    page.line([250, 255], [300, 255], stroke=CONN, stroke_style=flow)
    page.line([1020, 255], [1050, 255], stroke=CONN, stroke_style=flow)
    page.line([650, 330], [650, 360], stroke=CONN, stroke_style=flow)
    for cx in (198, 494, 790, 1086, 1382):
        page.line([cx, 480], [cx, 520], stroke=CONN, stroke_style=flow)   # backbone → cards
        page.line([cx, 700], [cx, 740], stroke=RBAC, stroke_style=gate)   # RBAC gate ↑

    # ── title ─────────────────────────────────────────────────────────────
    page.layer("title")
    head(page, 60, 40, 1200, "doc-ray — Database Architecture", size=30, weight=800)
    page.rect([60, 96, 64, 4], radius=2, fill=BRAND)
    page.text([60, 108, 1300, 22],
              "PostgreSQL 16 + pgvector · 43 tables · 4NF · stand-off spans · document-level RLS",
              style=ts(14, MUTE))

    # ── object store ──────────────────────────────────────────────────────
    page.layer("store")
    panel(page, [60, 180, 190, 150], fill=STORE, stroke=STORE, sw=1.0)
    head(page, 70, 198, 170, "Object store", color="#FFFFFF", size=14, align="center")
    chip(page, [78, 236, 154, 40], "MinIO / S3", fill="#FFFFFF", stroke=CARD_STROKE)
    ctext(page, 70, 288, 170, "blobs by sha256", color="#E2E8F0", size=11)
    ctext(page, 70, 304, 170, "(s3:// pointer only)", color="#E2E8F0", size=11)

    # ── document entity (4NF) ─────────────────────────────────────────────
    page.layer("doc_core")
    panel(page, [300, 180, 720, 150], fill=PANEL, stroke=CARD_STROKE, sw=1.0, accent=BRAND)
    head(page, 316, 196, 690, "Document entity · 4NF")
    chip(page, [316, 228, 200, 40], "documents", fill=BRAND_SOFT, stroke=BRAND,
         tcolor=BRAND, weight=700, sw=1.25)
    chip(page, [528, 228, 220, 40], "document_content (+FTS)")
    chip(page, [760, 228, 244, 40], "derived_from → documents")
    chip(page, [316, 278, 220, 34], "authors ▸ document_authors")
    chip(page, [548, 278, 190, 34], "tags ▸ document_tags")
    chip(page, [750, 278, 254, 34], "document_identifiers · document_metadata")

    # ── provenance ────────────────────────────────────────────────────────
    page.layer("provenance")
    panel(page, [1050, 180, 490, 150], fill=PANEL, stroke=CARD_STROKE, sw=1.0, accent=STORE)
    head(page, 1066, 196, 460, "Provenance · append-only")
    chip(page, [1066, 228, 300, 40], "document_provenance")
    chip(page, [1066, 278, 300, 34], "provenance_params (key,value)")
    page.text([1382, 232, 150, 14], "actor → principals", style=ts(11, MUTE))
    page.text([1382, 248, 150, 14], "(audit FK)", style=ts(11, MUTE))

    # ── span & annotation backbone ────────────────────────────────────────
    page.layer("backbone")
    panel(page, [60, 360, 1480, 120], fill=BRAND_SOFT, stroke=BRAND, sw=1.25, accent=BRAND)
    head(page, 76, 374, 900, "Span registry & annotation backbone — stand-off over shared spans")
    chip(page, [76, 406, 150, 44], "spans", fill="#FFFFFF", stroke=BRAND, tcolor=BRAND,
         weight=700, sw=1.25)
    chip(page, [242, 406, 150, 44], "sentences", fill="#FFFFFF")
    chip(page, [408, 406, 180, 44], "annotations", fill="#FFFFFF", stroke=BRAND, tcolor=BRAND,
         weight=700, sw=1.25)
    chip(page, [604, 406, 150, 44], "lexemes", fill="#FFFFFF")
    chip(page, [770, 406, 220, 44], "lexeme_occurrences", fill="#FFFFFF")
    page.text([1010, 418, 512, 32],
              "every layer binds a span_id · a run = (document, layer, tool) · ULID identity",
              style=ts(11, MUTE, lh=1.3))

    # ── NLP annotation band (layers 3–20) ─────────────────────────────────
    page.layer("nlp")
    cards = [
        (60,   "Tokens & Morphology · L3–7",
         ["tokens", "token_feature (UD FEATS)", "subword"]),
        (356,  "Syntax · L8–10",
         ["chunk", "constituent (tree)", "dependency"]),
        (652,  "Entities & Reference · L11–13",
         ["entity_mention", "entity_link (KB id)", "coref_chain · coref_mention"]),
        (948,  "Meaning & Discourse · L14–19",
         ["srl_predicate · srl_argument", "word_sense · amr_node/edge",
          "discourse_relation", "timex · event · tlink · sentiment"]),
        (1244, "Embeddings · L20",
         ["embedding", "vector(768)", "pgvector HNSW (cosine)"]),
    ]
    for x, title, rows in cards:
        panel(page, [x, 520, 276, 180], fill=LAYER_SOFT, stroke=LAYER, sw=1.0, accent=LAYER)
        head(page, x + 16, 536, 244, title, size=14)
        step = 26 if len(rows) <= 3 else 22
        y0 = 566 if len(rows) <= 3 else 564
        for i, r in enumerate(rows):
            ctext(page, x, y0 + i * step, 276, r, size=12)

    # ── access control — RBAC + RLS (cross-cutting) ───────────────────────
    page.layer("rbac")
    panel(page, [60, 740, 1480, 120], fill=RBAC_SOFT, stroke=RBAC, sw=1.25, accent=RBAC)
    page.rect([76, 758, 20, 20], radius=4, fill=RBAC)
    head(page, 108, 756, 760, "Row-Level Security · document-level RBAC")
    chip(page, [76, 792, 150, 34], "principals")
    chip(page, [236, 792, 90, 34], "roles")
    chip(page, [336, 792, 150, 34], "permissions")
    chip(page, [496, 792, 190, 34], "role_permissions")
    chip(page, [696, 792, 180, 34], "principal_roles")
    chip(page, [886, 792, 170, 34], "document_acl", fill="#FFFFFF", stroke=RBAC,
         tcolor=RBAC, weight=700, sw=1.25)
    page.text([1076, 794, 452, 40],
              "gates all 33 document-scoped tables\nvia docray_client + app.principal_id",
              style=ts(11, MUTE, lh=1.35))

    # ── footer ────────────────────────────────────────────────────────────
    page.layer("footer")
    page.text([60, 900, 1480, 24],
              "ULID + uuid identity · language-aware full-text search · full FK-cascade "
              "delete graph · generated from docs/DATABASE.md",
              style=ts(12, MUTE))
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:30]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    svg = render_page_svgs(doc)[0]
    with open(os.path.join(ROOT, "doc-ray-database.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg)
    with open(os.path.join(ROOT, "doc-ray-database.fg.yaml"), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print("Wrote doc-ray-database.svg + doc-ray-database.fg.yaml")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
