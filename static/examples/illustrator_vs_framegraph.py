#!/usr/bin/env python3
"""CAPABILITY TEARDOWN — Adobe Illustrator ⇄ FrameGraph v2.

A granular, feature-by-feature teardown: every Illustrator tool, panel, and
capability the source book documents, set against FrameGraph v2's coverage, with
a per-feature verdict glyph (● has · ◐ partial · ○ none · ◆ inverts).

This document deliberately does NOT reuse the "typeface book" house style (warm
paper, serif, plates). Its subject is a technical face-off between an interactive
GUI editor and a declarative format, so it wears a *datasheet* identity: a cool
near-white ground, sans + monospace only (no serif), a strict modular grid, and
a coverage-dot visual language. The declarative side even shows in the styling —
the comparison of a structured format is itself a structured, gridded artifact.

Provenance / epistemic contract (CLAUDE.md rules 1 & 2):
  * Illustrator features are mined from "Master Adobe Illustrator 2025"
    (Dana J. Bailey, 159 pp, 1,875 sentences) in the doc-ray corpus, queried over
    its GraphQL API. Each row cites the source *sentence ordinal* [n].
  * FrameGraph coverage quotes docs/capability-manifest.json (generated from the
    live tree, gated by tests/test_capability_manifest.py) and the SDK surface.
  * Verdicts are unbiased. Where FrameGraph has no answer (an explicit non-goal),
    the glyph is a hollow ○, not spin.

Build (from the frameforge root, src-layout):
    PYTHONPATH=src:docs python static/examples/illustrator_vs_framegraph.py [--out FILE]
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, serialize, stroke  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas & identity — a datasheet, not a book                                 #
# --------------------------------------------------------------------------- #
W, H = 794, 1123
CANVAS = {"size": [W, H], "units": "px"}
M = 56
CW = W - 2 * M
TITLE = "CAPABILITY TEARDOWN"
_page_no = 0

# Cool technical palette. Illustrator = its own brand amber; FrameGraph = cyan.
COLORS = {
    "bg":      "#f5f7f9",   # cool near-white ground
    "ink":     "#161a20",   # near-black
    "sub":     "#5c6672",   # muted slate
    "faint":   "#8b95a2",   # metadata grey
    "hair":    "#dde2e8",   # hairline
    "band":    "#eef1f4",   # zebra band
    "ai":      "#dd7a1f",   # Adobe amber (Illustrator)
    "aitint":  "#f6e7d4",   # amber wash
    "fg":      "#0f7d88",   # FrameGraph teal-cyan
    "fgtint":  "#d8eaec",   # cyan wash
    "part":    "#8fb9be",   # partial glyph (pale cyan)
    "none":    "#b7bfc9",   # none glyph (grey ring)
    "invert":  "#8a63c8",   # inverts-the-axis (violet)
    "night":   "#12161c",   # dark cover ground
    "nightink":"#eef1f4",   # text on night
    "nightsub":"#9aa4b1",
}

STYLES = {
    "run":    {"font_family": ["Fira Mono", "monospace"], "font_size": 8.5,
               "color": "faint", "letter_spacing": 1.5},
    "runR":   {"font_family": ["Fira Mono", "monospace"], "font_size": 8.5,
               "color": "faint", "letter_spacing": 1.5, "align": "right"},
    "folio":  {"font_family": ["Fira Mono", "monospace"], "font_size": 9,
               "color": "faint", "align": "center", "letter_spacing": 1},
    "kick":   {"font_family": ["Fira Mono", "monospace"], "font_size": 10,
               "color": "fg", "letter_spacing": 3, "text_transform": "uppercase"},
    "h2":     {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 27,
               "color": "ink", "font_weight": 600, "letter_spacing": -0.3},
    "lead":   {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 12,
               "color": "sub", "line_height": 1.5},
    "gid":    {"font_family": ["Fira Mono", "monospace"], "font_size": 9,
               "color": "ai", "letter_spacing": 0.5},
    "feat":   {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 12,
               "color": "ink", "font_weight": 600},
    "aiev":   {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 9.5,
               "color": "sub", "line_height": 1.35},
    "ord":    {"font_family": ["Fira Mono", "monospace"], "font_size": 8.5,
               "color": "ai"},
    "covlbl": {"font_family": ["Fira Mono", "monospace"], "font_size": 8.5,
               "color": "fg", "letter_spacing": 1, "text_transform": "uppercase"},
    "fgev":   {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 9.5,
               "color": "ink", "line_height": 1.35},
    "grouphd":{"font_family": ["Fira Mono", "monospace"], "font_size": 10,
               "color": "ink", "letter_spacing": 2, "text_transform": "uppercase"},
    "colhd":  {"font_family": ["Fira Mono", "monospace"], "font_size": 8.5,
               "color": "faint", "letter_spacing": 1.5, "text_transform": "uppercase"},
    "verdict":{"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 11,
               "color": "sub", "line_height": 1.5, "italic": True},
    # cover / night
    "ncode":  {"font_family": ["Fira Mono", "monospace"], "font_size": 11,
               "color": "fg", "letter_spacing": 3, "text_transform": "uppercase"},
    "ntitle": {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 52,
               "color": "nightink", "font_weight": 700, "letter_spacing": -1},
    "nsub":   {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 15,
               "color": "nightsub", "line_height": 1.5},
    "nmeta":  {"font_family": ["Fira Mono", "monospace"], "font_size": 9,
               "color": "nightsub", "letter_spacing": 1.5},
    "nlegend":{"font_family": ["Fira Mono", "monospace"], "font_size": 10,
               "color": "nightink", "letter_spacing": 0.5},
    # legend page
    "big":    {"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 30,
               "color": "ink", "font_weight": 700, "align": "center"},
    "biglbl": {"font_family": ["Fira Mono", "monospace"], "font_size": 8,
               "color": "faint", "align": "center", "letter_spacing": 1.5,
               "text_transform": "uppercase"},
    "legname":{"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 12,
               "color": "ink", "font_weight": 600},
    "legdesc":{"font_family": ["Inter", "Arial", "sans-serif"], "font_size": 10.5,
               "color": "sub", "line_height": 1.4},
}

_SF = {"font_family", "font_size", "font_weight", "color", "italic", "align",
       "letter_spacing", "line_height", "text_transform"}


def _styled(p):
    orig = p.text

    def text(box, txt, **fields):
        style = fields.pop("style", None)
        sf = {k: fields.pop(k) for k in list(fields) if k in _SF}
        if sf:
            style = {"class": style, **sf} if isinstance(style, str) else {**(style or {}), **sf}
        return orig(box, txt, style=style, **fields) if style is not None else orig(box, txt, **fields)

    p.text = text
    return p


def page(b, pid, *, tab="", night=False):
    global _page_no
    _page_no += 1
    p = _styled(b.page(pid, canvas=CANVAS, coordinate_mode="absolute"))
    p.layer("bg")
    p.rect([0, 0, W, H], fill="night" if night else "bg")
    p.layer("main")
    if not night:
        p.text([M, 34, 300, 11], TITLE, style="run")
        if tab:
            p.text([W - M - 320, 34, 320, 11], tab, style="runR")
        p.rect([M, 50, CW, 1], fill="hair")
        p.rect([M, H - 54, CW, 1], fill="hair")
        p.text([0, H - 44, W, 12], f"{_page_no:02d}", style="folio")
    return p


def head(p, y, kick, title):
    p.text([M, y, CW, 12], kick, style="kick")
    p.text([M, y + 18, CW, 40], title, style="h2")
    p.rect([M, y + 56, 44, 3], fill="fg")
    return y + 80


# --------------------------------------------------------------------------- #
# Coverage glyph — the visual through-line                                     #
# --------------------------------------------------------------------------- #
# cov: "has" ● · "part" ◐ · "none" ○ · "invert" ◆
def glyph(p, cx, cy, cov, r=8, ground="bg"):
    if cov == "has":
        p.circle([cx, cy], r, fill="fg")
    elif cov == "part":
        p.circle([cx, cy], r, fill="fg")
        p.rect([cx, cy - r, r + 1, 2 * r], fill=ground)     # blank the right half → ◐
        p.circle([cx, cy], r, fill="none", **stroke(1.4, color="fg"))
    elif cov == "none":
        p.circle([cx, cy], r, fill="none", **stroke(1.4, color="none"))
    elif cov == "invert":
        p.polygon([[cx, cy - r], [cx + r, cy], [cx, cy + r], [cx - r, cy]],
                  fill="invert")


# "reframed" = the capability exists in BOTH tools, but FrameGraph reaches it by
# naming or a tool call instead of a cursor gesture (its most interesting verdict).
COVLBL = {"has": "HAS", "part": "PARTIAL", "none": "NONE", "invert": "REFRAMED"}
COVCOL = {"has": "fg", "part": "part", "none": "none", "invert": "invert"}

# Row geometry
ID_X = M
FE_X, FE_W = M + 48, 300         # feature + AI evidence
GL_X = M + 372                    # glyph centre
CV_X, CV_W = M + 392, 46          # coverage label
FV_X, FV_W = M + 448, CW - (448 - M)   # FG evidence

ROWH = 62


def col_headers(p, y):
    p.text([ID_X, y, 44, 10], "ID", style="colhd")
    p.text([FE_X, y, FE_W, 10], "ILLUSTRATOR FEATURE  ·  EVIDENCE [ORDINAL]", style="colhd")
    p.text([GL_X - 8, y, 60, 10], "FG", style="colhd")
    p.text([FV_X, y, FV_W, 10], "FRAMEGRAPH COVERAGE", style="colhd")
    p.rect([M, y + 16, CW, 1.4], fill="ink")
    return y + 26


def row(p, y, i, fid, feat, ai, ordn, cov, fg):
    if i % 2 == 1:
        p.rect([M - 6, y - 6, CW + 12, ROWH], fill="band")
    p.text([ID_X, y, 44, 10], fid, style="gid")
    p.text([FE_X, y - 1, FE_W, 14], feat, style="feat")
    p.text([FE_X, y + 16, FE_W, 32], ai, style="aiev")
    if ordn:
        p.text([FE_X, y + ROWH - 22, FE_W, 10], ordn, style="ord")
    glyph(p, GL_X + 8, y + 14, cov, r=8, ground=("band" if i % 2 == 1 else "bg"))
    p.text([CV_X, y + 28, CV_W + 40, 10], COVLBL[cov], style="covlbl",
           color=COVCOL[cov])
    p.text([FV_X, y + 2, FV_W, 44], fg, style="fgev")
    p.rect([M, y + ROWH - 6, CW, 0.6], fill="hair")
    return y + ROWH


# --------------------------------------------------------------------------- #
# The feature inventory — granular, grounded, grouped by the book's chapters   #
# (id, group, feature, ai-evidence, [ordinal], coverage, fg-evidence)          #
# --------------------------------------------------------------------------- #
GROUPS = [
    ("A · SELECT & EDIT PATHS", "sel-edit", [
        ("AI-01", "Object selection",
         "Selection Tool picks a whole object to move or transform.", "[64]",
         "invert", "REFRAMED: you NAME an object by id and act on it — "
         "declaration replaces the point-and-click selection."),
        ("AI-02", "Anchor-point editing",
         "Direct Selection edits specific anchor points & paths in an object.", "[198]",
         "part", "path / bezier / curve points authored as coordinates."),
        ("AI-03", "Isolation mode",
         "Double-click into a group to edit its contents in place.", "[281]",
         "has", "nested group + per-page layer scoping."),
        ("AI-04", "Compound paths",
         "Combine paths so one cuts a hole in another.", "[296]",
         "has", "path fill_rule even-odd; polygon holes."),
        ("AI-05", "Shape Builder",
         "Drag across shapes to merge/subtract them interactively.", "[59]",
         "none", "no boolean / interactive shape merge."),
        ("AI-06", "Scissors & Knife",
         "Cut a path at a point, or slice across objects.", "[365][381]",
         "none", "no interactive path surgery."),
    ]),
    ("B · DRAW & PRIMITIVES", "draw", [
        ("AI-07", "Shape primitives",
         "Rectangle, Ellipse, Polygon, Star, Line, Arc tools.", "[47][211]",
         "has", "rect, ellipse, circle, polygon, line, polyline (17 object_types)."),
        ("AI-08", "Pen tool (Bézier)",
         "Draw free-form Bézier paths by hand, point by point.", "[95]",
         "part", "bezier / curve objects, authored by coordinate not by hand."),
        ("AI-09", "Curvature tool",
         "Rubber-band free-form curves as you click & release.", "[696]",
         "part", "curve object + smooth polyline; no live rubber-band."),
        ("AI-10", "Pencil / freehand",
         "Sketch a path freehand; Illustrator fits the curve.", "[740]",
         "none", "no freehand pointer input (declarative only)."),
        ("AI-11", "Stroke controls",
         "Weight, dashes, caps, joins on the Stroke panel.", "[93]",
         "has", "stroke_style: width / dasharray / cap / join (P3 split)."),
    ]),
    ("C · COLOUR SYSTEM", "colour", [
        ("AI-12", "Colour picker",
         "Pick colour on the Color panel; many input modes.", "[66]",
         "has", "hex / rgb colour values on any paintable field."),
        ("AI-13", "Swatches",
         "Save & reuse named colour swatches.", "[85]",
         "has", "defs.tokens.colors — a named, reusable palette."),
        ("AI-14", "Global colours",
         "Edit a global swatch once; every use updates.", "[958]",
         "has", "named colour tokens are global by construction."),
        ("AI-15", "CMYK / RGB modes",
         "Document colour mode selectable CMYK or RGB.", "[326]",
         "part", "RGB / hex only — no CMYK, no separations."),
        ("AI-16", "Eyedropper sampling",
         "Sample colour from any object or image.", "[989]",
         "none", "no interactive sampling (vision tools measure, not paint)."),
        ("AI-17", "Live Paint",
         "Fill regions bounded by overlapping paths interactively.", "[1000]",
         "part", "region toolkit: select_in / place_region / region_grade."),
        ("AI-18", "Patterns",
         "Tile a swatch as a repeating pattern fill.", "[22]",
         "has", "pattern fills on any object."),
    ]),
    ("D · TYPE & TEXT", "type", [
        ("AI-19", "Point & area type",
         "Type tool sets point text or text inside a shape.", "[1015]",
         "has", "text objects + flow paragraph / heading / list."),
        ("AI-20", "Character formatting",
         "Font, size, weight on the Character panel.", "[1015]",
         "has", "font_family / size / weight among 106 style props."),
        ("AI-21", "Paragraph controls",
         "Alignment, spacing, indents on the Paragraph panel.", "[1029]",
         "has", "paragraph flow: align, line_height, spacing, columns."),
        ("AI-22", "Threaded text",
         "Flow overset text between linked frames.", "[1029]",
         "has", "flow model: column_break / page_break / keep_together."),
        ("AI-23", "Type on a path",
         "Set text running along a curved path.", "[1099]",
         "none", "no text-on-path (explicit scope limit)."),
        ("AI-24", "Kerning & leading",
         "Fine letter/line spacing per the Character panel.", "[1054]",
         "part", "letter_spacing / line_height; no pair-kerning table."),
        ("AI-25", "Envelope distort",
         "Warp text into an arbitrary envelope shape.", "[1104]",
         "none", "non-goal — text stays on its baseline grid."),
    ]),
    ("E · GRADIENT · EFFECT · STYLE", "appearance", [
        ("AI-26", "Linear gradient",
         "Two+ colour stops along a linear axis.", "[1180]",
         "has", "linear_gradient paint on fill or stroke."),
        ("AI-27", "Radial gradient",
         "Concentric colour stops with handle control.", "[1214]",
         "has", "radial_gradient paint."),
        ("AI-28", "Freeform gradient",
         "Colour stops placed freely across the object.", "[1240]",
         "none", "no freeform gradient."),
        ("AI-29", "Gradient mesh",
         "A mesh of colour points for painterly blends.", "[653]",
         "none", "no mesh — the biggest single gap."),
        ("AI-30", "Blending modes",
         "Multiply, screen, etc. per object/layer.", "[1197]",
         "part", "opacity + a limited blend-mode set."),
        ("AI-31", "Live effects",
         "Drop shadow, distort — non-destructive effects.", "[154][1608]",
         "part", "SVG filter effects (shadow / blur), not a live stack."),
        ("AI-32", "Graphic styles",
         "Save an appearance and reapply it by name.", "[270]",
         "has", "named styles / text_styles / stroke_styles tokens."),
        ("AI-33", "Appearance stack",
         "Stack multiple fills/strokes/effects per object.", "[1526]",
         "part", "one style per object; no multi-fill appearance stack."),
    ]),
    ("F · LAYER · TRANSFORM · PAGE", "layout", [
        ("AI-34", "Layers",
         "Organise artwork in a Layers-panel hierarchy.", "[282]",
         "has", "ordered layers per page, z-index."),
        ("AI-35", "Lock / hide",
         "Lock or hide layers and objects on the canvas.", "[282]",
         "part", "visibility flag; no interactive lock state."),
        ("AI-36", "Transform tools",
         "Rotate, Scale, Reflect, Shear an object.", "[548][369]",
         "has", "transform: Mat3 rotate / scale / translate / shear."),
        ("AI-37", "Align & distribute",
         "Align/distribute selected objects on the Align panel.", "[93]",
         "has", "layout groups: row / column / grid, align."),
        ("AI-38", "Artboards",
         "Multiple artboards — “similar to pages in InDesign”.", "[423]",
         "has", "multi-page flow doc: TOC, tables, bibliography."),
    ]),
    ("G · IMAGE & OUTPUT", "output", [
        ("AI-39", "Embed / link raster",
         "Embed a raster image, or link it externally.", "[1727][1625]",
         "has", "image object: embedded or src-referenced."),
        ("AI-40", "Image trace",
         "Convert a raster image into editable vectors.", "[1641]",
         "invert", "REFRAMED: same raster→vector, but via the vectorize_image "
         "MCP tool call, not a canvas menu command."),
        ("AI-41", "Pixel grid",
         "Snap vector edges to the pixel grid for crisp export.", "[1844]",
         "none", "pure vector coordinates; no pixel snapping."),
        ("AI-42", "Export formats",
         "EPS, PSD, TIFF, GIF, JPEG, SWF, SVG, DWG/DXF.", "[20]",
         "part", "SVG / PNG / PDF / LaTeX (6 renderers); no PSD / EPS / DWG."),
        ("AI-43", "PDF export",
         "Save the document as a PDF.", "[1818]",
         "has", "PDF renderer (solved SVG → vector PDF)."),
        ("AI-44", "Package",
         "Collect linked assets & fonts into one folder.", "[1808]",
         "none", "no asset-collection packaging step."),
    ]),
]


def coverage_tally():
    from collections import Counter
    c = Counter()
    for _, _, rows in GROUPS:
        for r in rows:
            c[r[4]] += 1          # r[4] is the coverage verdict (has/part/none/invert)
    return c


def build():
    b = DocumentBuilder(
        title="Capability Teardown — Illustrator vs FrameGraph",
        profile="report",
        lang="en",
    )
    for k, v in COLORS.items():
        b.define_color(k, v)
    for k, v in STYLES.items():
        b.define_text_style(k, **v)
    tally = coverage_tally()
    total = sum(tally.values())
    b.meta(
        provenance=(
            f"{total} Illustrator features torn down. Illustrator claims cite "
            "sentence ordinals in 'Master Adobe Illustrator 2025' (doc-ray corpus, "
            "GraphQL). FrameGraph coverage quotes docs/capability-manifest.json."
        ),
        generated_by="Claude Fable 5 via Claude Code",
    )

    # -- 1. COVER (dark datasheet) --------------------------------------- #
    p = page(b, "cover", night=True)
    p.layer("main")
    # header rule + brand line
    p.rect([M, 70, CW, 1], fill="nightsub")
    p.text([M, 84, CW, 12], "ADOBE ILLUSTRATOR 2025   vs   FRAMEGRAPH v2 · 2.3.0",
           style="nmeta")
    p.text([M, 250, CW, 14], "// FEATURE-BY-FEATURE", style="ncode")
    p.text([M, 278, CW, 62], "Capability", style="ntitle")
    p.text([M, 336, CW, 62], "Teardown", style="ntitle")
    p.rect([M, 410, 120, 3], fill="fg")
    p.text([M, 436, CW - 30, 80],
           f"An interactive vector editor, torn down feature by feature against a "
           f"declarative document format. {total} capabilities, one verdict each.",
           style="nsub")
    # coverage legend key on the cover
    ly = 610
    p.text([M, ly, CW, 12], "// VERDICT KEY", style="ncode")
    keys = [("has", "HAS", "a direct equivalent"),
            ("part", "PARTIAL", "a narrower / different form"),
            ("none", "NONE", "no equivalent (often a non-goal)"),
            ("invert", "REFRAMED", "exists in both — but reached by code, not cursor")]
    for i, (cov, lbl, desc) in enumerate(keys):
        ky = ly + 34 + i * 40
        glyph(p, M + 10, ky, cov, r=8, ground="night")
        p.text([M + 30, ky - 6, 90, 12], lbl, style="nlegend")
        p.text([M + 140, ky - 6, CW - 140, 12], desc, style="nmeta")
    p.rect([M, H - 96, CW, 1], fill="nightsub")
    p.text([M, H - 82, CW, 12],
           "SOURCE: doc-ray GraphQL · MANIFEST: docs/capability-manifest.json",
           style="nmeta")

    # -- 2. METHOD + COVERAGE SUMMARY ------------------------------------ #
    p = page(b, "summary", tab="METHOD · SCORECARD")
    y = head(p, 74, "// how this was measured", "Method & scorecard")
    p.text([M, y, CW, 68],
           "Illustrator's surface was enumerated from its own manual and reduced to "
           f"{total} discrete capabilities. Each was checked against FrameGraph's "
           "generated capability manifest and SDK. The bar below is the raw tally — "
           "no weighting, no spin.", style="lead")
    # stacked coverage bar
    by = y + 84
    p.text([M, by, CW, 10], "COVERAGE ACROSS " + str(total) + " FEATURES", style="colhd")
    bar_y, bar_h = by + 18, 34
    order = [("has", "fg"), ("part", "part"), ("invert", "invert"), ("none", "none")]
    x = M
    for cov, col in order:
        w = CW * tally[cov] / total
        p.rect([x, bar_y, w, bar_h], fill=col)
        if w > 30:
            p.text([x + 6, bar_y + 11, w - 8, 12], str(tally[cov]),
                   style="folio", color="bg", align="start")
        x += w
    # legend under the bar
    lx = M
    for cov, col in order:
        p.rect([lx, bar_y + bar_h + 14, 12, 12], fill=col)
        p.text([lx + 18, bar_y + bar_h + 14, 120, 12],
               f"{COVLBL[cov]} · {tally[cov]}", style="folio", align="start")
        lx += 150
    # headline stat cards
    sy = bar_y + bar_h + 60
    has_pct = round(100 * (tally["has"]) / total)
    somepct = round(100 * (tally["has"] + tally["part"]) / total)
    cards = [(str(total), "FEATURES TORN DOWN"),
             (f"{has_pct}%", "FULL EQUIVALENT"),
             (f"{somepct}%", "FULL OR PARTIAL"),
             (str(tally["none"]), "GENUINE GAPS")]
    cwc = (CW - 3 * 14) / 4
    for i, (num, lbl) in enumerate(cards):
        cx = M + i * (cwc + 14)
        p.rect([cx, sy, cwc, 78], fill="band")
        p.rect([cx, sy, cwc, 3], fill="fg")
        p.text([cx, sy + 20, cwc, 30], num, style="big")
        p.text([cx, sy + 58, cwc, 10], lbl, style="biglbl")
    # what the glyphs mean, restated as a table
    gy = sy + 110
    p.text([M, gy, CW, 10], "READING A ROW", style="colhd")
    p.rect([M, gy + 16, CW, 1], fill="hair")
    demo = [("gid", "AI-nn", "monospace feature id (chapter-ordered)"),
            ("feat", "Feature", "the Illustrator capability, named"),
            ("ord", "[1234]", "source sentence ordinal — round-trips to the book"),
            ("covlbl", "● HAS", "FrameGraph verdict glyph + label"),
            ("fgev", "evidence", "the FrameGraph capability that backs the verdict")]
    for i, (st, k, desc) in enumerate(demo):
        yy = gy + 28 + i * 22
        p.text([M, yy, 90, 12], k, style=st)
        p.text([M + 110, yy, CW - 110, 12], desc, style="legdesc")

    # dedicated explainer: the one verdict that needs it — REFRAMED
    ry = gy + 28 + len(demo) * 22 + 22
    p.rect([M, ry, CW, 120], fill="band")
    glyph(p, M + 22, ry + 24, "invert", r=8, ground="band")
    p.text([M + 44, ry + 18, CW - 60, 12], "WHAT “REFRAMED” MEANS", style="grouphd")
    p.text([M + 44, ry + 40, CW - 88, 30],
           "The capability exists in BOTH tools — but FrameGraph reaches it by "
           "naming or a tool call, not a cursor gesture. It is neither a gap nor a "
           "look-alike; it is the same end down the opposite (declarative) road.",
           style="legdesc")
    p.text([M + 44, ry + 84, CW - 88, 12],
           "AI-01  Illustrator SELECTS an object with the pointer   →   "
           "FrameGraph NAMES it by id.", style="folio", color="sub", align="start")
    p.text([M + 44, ry + 100, CW - 88, 12],
           "AI-40  Illustrator TRACES a raster from a menu   →   "
           "FrameGraph calls the vectorize_image tool.", style="folio",
           color="sub", align="start")

    # -- 3..N. GRANULAR MATRIX PAGES ------------------------------------- #
    # Two groups per page where they fit; else one. Lay out by measured height.
    pending = list(GROUPS)
    page_idx = 0
    while pending:
        page_idx += 1
        p = page(b, f"matrix-{page_idx}", tab="TEARDOWN · " + str(page_idx))
        y = 74 if page_idx > 1 else 74
        if page_idx == 1:
            y = head(p, 74, "// the teardown", "Feature-by-feature")
        else:
            y = head(p, 74, "// the teardown, cont.", "Feature-by-feature")
        # fit as many groups as remain within the page
        budget_bottom = H - 90
        while pending:
            grp_title, _, rows = pending[0]
            needed = 20 + 26 + len(rows) * ROWH + 14
            if y + needed > budget_bottom:
                break
            p.text([M, y, CW, 12], grp_title, style="grouphd")
            p.rect([M, y + 16, CW, 1], fill="ink")
            y = col_headers(p, y + 22)
            for i, r in enumerate(rows):
                y = row(p, y, i, *r)
            y += 18
            pending.pop(0)

    # -- FINAL. VERDICT + PROVENANCE ------------------------------------- #
    p = page(b, "verdict", tab="VERDICT")
    y = head(p, 74, "// what the tally means", "Two machines, one honest score")
    p.text([M, y, CW, 92],
           f"Of {total} Illustrator capabilities, FrameGraph has a full equivalent "
           f"for {tally['has']} and a partial one for {tally['part']}. The {tally['none']} "
           f"genuine gaps cluster where Illustrator is a painting instrument — gradient "
           f"mesh, freeform gradient, the Pencil, envelope distort, type on a path, "
           f"pixel snapping, packaging. The {tally['invert']} REFRAMED rows are the "
           f"most telling: object selection and image trace exist in both tools, but "
           f"FrameGraph reaches them by naming and a tool call — not a cursor.",
           style="lead")
    # the split thesis
    ty = y + 108
    p.rect([M, ty, CW, 150], fill="ink")
    p.text([M + 26, ty + 26, CW - 52, 34], "Illustrator is a hand.",
           style="h2", color="bg")
    p.text([M + 26, ty + 60, CW - 52, 34], "FrameGraph is a grammar.",
           style="h2", color="fg")
    p.text([M + 26, ty + 104, CW - 52, 22],
           "The gaps are the price of being declarative and machine-authored;",
           style="lead", color="nightsub")
    p.text([M + 26, ty + 124, CW - 52, 22],
           "the overlaps are where a format can meet an editor.",
           style="lead", color="nightsub")
    # honest scope band
    hy = ty + 180
    p.rect([M, hy, CW, 104], fill="aitint")
    p.text([M + 20, hy + 18, CW - 40, 12], "// HONEST SCOPE", style="kick", color="ai")
    p.text([M + 20, hy + 36, CW - 40, 60],
           "FrameGraph v2 is a PROPOSED format: no renderer is conformant, the SVG "
           "and matplotlib backends are sanity checks, not fidelity guarantees. "
           "Illustrator is a mature product. This is a comparison of feature surface "
           "and design intent, not of production maturity.", style="legdesc")
    # provenance footer
    py = hy + 124
    p.text([M, py, CW, 10], "// PROVENANCE", style="kick")
    p.rect([M, py + 16, CW, 1], fill="hair")
    p.text([M, py + 26, CW, 64],
           "Illustrator features mined from “Master Adobe Illustrator 2025” "
           "(Dana J. Bailey, 159 pp, 1,875 sentences), doc-ray corpus, GraphQL. Each "
           "[n] is a source sentence ordinal — searchSentences(documentId, term) "
           "round-trips it. FrameGraph coverage quotes docs/capability-manifest.json, "
           "gated by tests/test_capability_manifest.py.", style="legdesc")
    p.text([M, py + 92, CW, 12],
           "Composed by Claude (Fable 5), 2026 · a declarative teardown of a "
           "declarative format.", style="legdesc", color="faint")

    return b.build()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__) or ".",
                                                  "illustrator_vs_framegraph.fg.yaml"))
    args = ap.parse_args()
    doc = build()
    report = validate_static_rules(doc)
    errs = [i for i in report.issues if i.severity == "error"]
    print(f"pages={len(doc.pages)} features={sum(coverage_tally().values())} "
          f"ok={report.ok} errors={len(errs)} warnings={len(report.issues) - len(errs)}")
    for i in report.issues[:20]:
        print(f"  [{i.severity}] {i.rule_id} {i.path}: {i.message}")
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
