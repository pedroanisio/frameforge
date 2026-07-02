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
import datetime
import json
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
    "sub":     "#5c6672",   # muted slate  (5.4:1 on ground)
    "faint":   "#667079",   # metadata grey (4.7:1 — was #8b95a2 @ 2.8, below floor)
    "hair":    "#dde2e8",   # hairline
    "band":    "#eef1f4",   # zebra band
    "ai":      "#a85510",   # Adobe amber, darkened for text legibility (4.9:1)
    "aitint":  "#f6e7d4",   # amber wash
    "fg":      "#0f7d88",   # FrameGraph teal-cyan (4.5:1)
    "fgtint":  "#d8eaec",   # cyan wash
    "part":    "#4f9098",   # partial mid-teal (bar/glyph fill; carries white counts)
    "partlbl": "#38757c",   # PARTIAL label text (4.9:1)
    "none":    "#7c8590",   # none glyph ring (3.5:1 non-text floor; was #b7bfc9 @ 1.6)
    "invert":  "#8a63c8",   # REFRAMED glyph violet
    "invertlbl":"#6a3fa6",  # REFRAMED label text (6.8:1)
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
    "cite":   {"font_family": ["Fira Mono", "monospace"], "font_size": 8.5,
               "color": "sub"},
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
# Label TEXT colours are legibility-first (glyphs keep the lighter tokens): the
# shape already carries the verdict, so the word must clear the contrast floor.
COVCOL = {"has": "fg", "part": "partlbl", "none": "sub", "invert": "invertlbl"}

# Row geometry
ID_X = M
FE_X, FE_W = M + 48, 300         # feature + AI evidence
GL_X = M + 372                    # glyph centre
CV_X, CV_W = M + 392, 46          # coverage label
FV_X = M + 448
FV_W = W - M - FV_X                     # FG evidence — ends at the right margin

ROWH = 62


def col_headers(p, y):
    p.text([ID_X, y, 44, 10], "ID", style="colhd")
    p.text([FE_X, y, FE_W, 10], "ILLUSTRATOR FEATURE  ·  EVIDENCE [SRC·ORDINAL]", style="colhd")
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
        p.text([FE_X, y + ROWH - 22, FE_W, 10], f"[{ordn}]", style="ord")
    glyph(p, GL_X + 8, y + 14, cov, r=8, ground=("band" if i % 2 == 1 else "bg"))
    # label carries confidence on every non-HAS row, plus the equivalence
    # dimension (F/W/D) on the PARTIAL & REFRAMED verdicts; gap-type under NONE.
    m = row_meta(fid, cov)
    if cov == "has":
        lbl = COVLBL[cov]
    elif cov in ("part", "invert"):
        lbl = f"{COVLBL[cov]} ·{m['confidence']} ·{m['dimension']}"
    else:  # none
        lbl = f"{COVLBL[cov]} ·{m['confidence']}"
    p.text([CV_X, y + 28, CV_W + 44, 10], lbl, style="covlbl", color=COVCOL[cov])
    if cov == "none" and m["gap_type"]:
        chip = {"non_goal": "non-goal", "arch": "architectural", "maturity": "maturity"}[m["gap_type"]]
        p.text([CV_X, y + 40, CV_W + 44, 10], chip, style="cite", color="faint",
               align="start")
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
         "Selection Tool picks a whole object to move or transform.", "25·64",
         "invert", "REFRAMED: you NAME an object by id — declaration "
         "replaces cursor selection."),
        ("AI-02", "Anchor-point editing",
         "Direct Selection edits specific anchor points & paths.", "25·198",
         "part", "path / bezier / curve points authored as coordinates."),
        ("AI-03", "Isolation mode",
         "Double-click into a group to edit its contents in place.", "25·281",
         "part", "structural nesting (group + layers) — no in-place isolated edit."),
        ("AI-04", "Compound paths / Pathfinder",
         "Combine paths (Pathfinder) so one cuts a hole in another.", "24·1488",
         "part", "path fill_rule even-odd + holes; no live Pathfinder ops."),
        ("AI-05", "Shape Builder",
         "Drag across shapes to merge / subtract them interactively.", "24·523",
         "none", "no boolean / interactive shape merge."),
        ("AI-06", "Scissors & Knife",
         "Cut a path at a point, or slice across objects.", "25·365",
         "none", "no interactive path surgery."),
        ("AI-47", "Offset path",
         "Object > Path > Offset expands a path outward / inward.", "26·3298",
         "none", "no offset-path operation."),
        ("AI-48", "Outline stroke",
         "Object > Path > Outline Stroke converts a stroke to a filled path.", "26·771",
         "none", "no stroke→outline conversion."),
    ]),
    ("B · DRAW & PRIMITIVES", "draw", [
        ("AI-07", "Shape primitives",
         "Rectangle, Ellipse, Polygon, Star, Line, Arc tools.", "25·47",
         "has", "rect, ellipse, circle, polygon, line, polyline (17 object_types)."),
        ("AI-08", "Pen tool (Bézier)",
         "Set Bézier anchor points and handles by hand.", "24·612",
         "part", "bezier / Path / CubicBezier objects, authored by coordinate."),
        ("AI-09", "Curvature tool",
         "Rubber-band free-form curves as you click & release.", "24·1964",
         "part", "curve object + parametric_curve; no live rubber-band."),
        ("AI-10", "Pencil / freehand",
         "Sketch a path freehand; Illustrator fits the curve.", "24·747",
         "none", "no freehand pointer input (declarative only)."),
        ("AI-11", "Stroke controls",
         "Weight, dashes, caps, joins, arrowheads on the Stroke panel.", "25·93",
         "has", "stroke_style: width / dasharray / cap / join + connector markers."),
        ("AI-12", "Variable-width (Width Tool)",
         "Vary stroke width along a path for a calligraphic look.", "24·666",
         "none", "stroke width is uniform — no width profile."),
        ("AI-49", "Brushes",
         "Calligraphic, Scatter, Art, Pattern, Blob brushes paint along a path.", "26·937",
         "none", "no brush engine; nearest is hatch_fill / pattern."),
    ]),
    ("C · COLOUR SYSTEM", "colour", [
        ("AI-13", "Colour picker & swatches",
         "Pick colour; save reusable named swatches.", "25·85",
         "has", "hex / rgba values + defs.tokens.colors named palette."),
        ("AI-14", "Global colours",
         "Edit a global swatch once; every use updates.", "25·958",
         "has", "named colour tokens are global by construction."),
        ("AI-15", "CMYK / RGB modes",
         "Document colour mode selectable CMYK or RGB.", "25·326",
         "part", "RGB / hex only — no CMYK, no separations."),
        ("AI-16", "Recolor Artwork",
         "Remap a whole palette via the Recolor command / Color Guide.", "24·684",
         "part", "gradient_map + closed_palette + token swap (declarative recolor)."),
        ("AI-17", "Live Paint",
         "Fill regions bounded by overlapping paths interactively.", "24·319",
         "part", "region toolkit: select_in / place_region / region_grade."),
        ("AI-18", "Colour science",
         "Colour groups & harmony via the Color Guide panel.", "24·684",
         "part", "Chevreul harmony + WCAG contrast tools — not a Color-Guide workflow."),
        ("AI-19", "Patterns",
         "Tile a swatch as a repeating pattern fill.", "24·695",
         "has", "pattern, grid_pattern, dots, hatch_fill fills."),
    ]),
    ("D · TYPE & TEXT", "type", [
        ("AI-20", "Point & area type",
         "Type tool sets point text or text inside a shape.", "25·1015",
         "has", "text objects + flow paragraph / heading / list."),
        ("AI-21", "Character & paragraph",
         "Font, size, weight, alignment, spacing, indents.", "25·1029",
         "has", "font_family / size / weight + paragraph flow (106 style props)."),
        ("AI-22", "Threaded text",
         "Flow overset text between linked frames.", "25·1029",
         "part", "flow auto-pagination continues overset; no interactive frame linking."),
        ("AI-23", "Type on a path",
         "Set text running along a curved path.", "25·1099",
         "none", "no text-on-path (explicit scope limit)."),
        ("AI-24", "Kerning & tracking",
         "Fine letter / line spacing on the Character panel.", "25·1054",
         "part", "letter_spacing / line_height; no pair-kerning table."),
        ("AI-25", "Envelope distort",
         "Warp text into an arbitrary envelope shape.", "25·715",
         "none", "non-goal — text stays on its baseline grid."),
    ]),
    ("E · GRADIENT · EFFECT · STYLE", "appearance", [
        ("AI-26", "Linear / radial gradient",
         "Colour stops along a linear or radial axis.", "24·844",
         "has", "linear_gradient / radial_gradient paint."),
        ("AI-27", "Freeform gradient",
         "Colour stops placed freely across the object.", "24·857",
         "none", "no freeform gradient."),
        ("AI-28", "Gradient mesh",
         "A mesh of colour points for painterly blends.", "24·1079",
         "none", "no mesh — the single biggest gap."),
        ("AI-29", "Blend tool",
         "Interpolate shape & colour between two objects.", "24·1160",
         "none", "no shape-to-shape blend / interpolation."),
        ("AI-30", "Live effects",
         "Drop shadow, glow, blur — non-destructive effects.", "25·1496",
         "part", "effects set: glow / neon / shadow / soft_shadow / hatch."),
        ("AI-31", "Graphic styles",
         "Save an appearance and reapply it by name.", "24·1823",
         "has", "named styles / text_styles / stroke_styles tokens."),
        ("AI-32", "Appearance stack",
         "Stack multiple fills / strokes / effects per object.", "24·1092",
         "part", "one style per object; no multi-fill appearance stack."),
    ]),
    ("F · LAYER · TRANSFORM · PAGE", "layout", [
        ("AI-33", "Layers",
         "Organise artwork in a Layers-panel hierarchy.", "24·547",
         "has", "ordered layers per page, z-index."),
        ("AI-34", "Transform tools",
         "Rotate, Scale, Reflect, Shear an object.", "24·700",
         "has", "transform: Mat3 rotate / scale / translate / shear."),
        ("AI-35", "Align & distribute",
         "Align / distribute objects on the Align panel.", "24·542",
         "has", "layout groups: row / column / grid, align."),
        ("AI-36", "Artboards",
         "Multiple artboards — “similar to pages in InDesign”.", "25·423",
         "part", "multi-page flow doc (TOC, bibliography); no free spatial canvas."),
        ("AI-37", "Perspective grid",
         "Draw & place objects on a simulated perspective grid.", "24·762",
         "none", "no perspective grid (flat page space)."),
        ("AI-50", "Guides, rulers & snap",
         "Rulers, guides and Snap-to-Grid align artwork by eye.", "26·572",
         "part", "grid_pattern + exact coordinates; no interactive guides / snap."),
    ]),
    ("G · IMAGE · 3D · OUTPUT", "output", [
        ("AI-38", "Embed / link raster",
         "Embed a raster image, or link it externally.", "25·1727",
         "has", "image object: embedded or src-referenced."),
        ("AI-39", "Image trace",
         "Object > Image Trace: raster into editable vectors.", "24·1394",
         "invert", "REFRAMED: same raster→vector via the vectorize_image tool call."),
        ("AI-40", "3D & Materials",
         "Effect > 3D: extrude, bevel, revolve with materials.", "24·767",
         "part", "Scene3D + Material + Camera scene — not vector extrusion."),
        ("AI-41", "Export formats",
         "EPS, PSD, TIFF, GIF, JPEG, SWF, SVG, DWG/DXF, PDF.", "25·20",
         "part", "SVG / PNG / PDF / LaTeX (6 renderers); no PSD / EPS / DWG."),
        ("AI-42", "Package",
         "Collect linked assets & fonts into one folder.", "24·2204",
         "none", "no asset-collection packaging step."),
        ("AI-51", "Graph tool",
         "Graph tools plot data as bar / pie / line charts.", "26·405",
         "has", "Chart / sparkline / function_plot / polar_plot / kpi (data-bound)."),
    ]),
    ("H · GENERATIVE / AI  (Illustrator 2024)", "genai", [
        ("AI-43", "Text to Vector Graphic",
         "Describe art in words; generative AI makes the vectors.", "24·105",
         "invert", "REFRAMED: propose_from_image / run_sdk_code author→render loop."),
        ("AI-44", "Generative Recolor",
         "Recolour artwork with a text prompt via generative AI.", "24·678",
         "invert", "REFRAMED: swap a palette token / gradient_map, re-render."),
        ("AI-45", "Retype",
         "Identify & match fonts found in existing artwork.", "24·73",
         "none", "list_fonts resolves families, but no visual font ID."),
        ("AI-46", "Mockup",
         "Wrap flat vector art onto a 3D object mockup.", "24·41",
         "none", "no mockup / surface-wrap of art onto an object."),
    ]),
]

# --------------------------------------------------------------------------- #
# Per-row audit metadata (addresses the review: confidence, gap taxonomy,      #
# equivalence dimension, rationale). Defaults applied for any id not listed:   #
#   confidence H · dimension by verdict · gap type only for NONE rows.         #
# --------------------------------------------------------------------------- #
# equivalence dimension: F = functional (same user outcome), W = workflow
# (same task, different steps), D = data-model (structural analogue only).
# gap type: non_goal (explicit scope choice), arch (architectural — declarative
# model precludes it), maturity (plausible, not yet built).
META = {
    "AI-01": {"conf": "H", "dim": "D", "why": "Naming replaces pointing; no cursor selection exists."},
    "AI-02": {"conf": "M", "dim": "W", "why": "Points are authored as coordinates, not hand-dragged."},
    "AI-03": {"conf": "M", "dim": "D", "why": "Structural nesting only; no interactive in-place isolation."},
    "AI-04": {"conf": "M", "dim": "W", "why": "even-odd holes yes; live Pathfinder booleans no."},
    "AI-05": {"conf": "H", "dim": "F", "gap": "arch", "why": "No interactive boolean shape building."},
    "AI-06": {"conf": "H", "dim": "F", "gap": "arch", "why": "No interactive path cutting."},
    "AI-08": {"conf": "M", "dim": "W", "why": "Bézier by coordinate, not by-hand handle dragging."},
    "AI-09": {"conf": "M", "dim": "W", "why": "curve/parametric_curve; no live rubber-band."},
    "AI-10": {"conf": "H", "dim": "F", "gap": "non_goal", "why": "Freehand pointer input is out of scope."},
    "AI-12": {"conf": "H", "dim": "F", "gap": "arch", "why": "Stroke width is uniform; no width profile."},
    "AI-15": {"conf": "H", "dim": "F", "why": "RGB/hex only; no CMYK or separations."},
    "AI-16": {"conf": "M", "dim": "W", "why": "Declarative palette/gradient_map remap, not a Recolor dialog."},
    "AI-17": {"conf": "M", "dim": "W", "why": "region toolkit places/grades regions declaratively; no interactive bounded-region painting."},
    "AI-36": {"conf": "M", "dim": "D", "why": "Document pages, not Illustrator's free spatial canvas / per-artboard export regions."},
    "AI-22": {"conf": "M", "dim": "F", "why": "Flow auto-pagination continues overset; no interactive linked-frame semantics."},
    "AI-18": {"conf": "M", "dim": "W", "why": "Harmony/contrast tools overlap Color Guide, not a 1:1 workflow."},
    "AI-23": {"conf": "H", "dim": "F", "gap": "non_goal", "why": "Text-on-path is an explicit scope limit."},
    "AI-24": {"conf": "M", "dim": "F", "why": "letter_spacing/line_height; no pair-kerning table."},
    "AI-25": {"conf": "H", "dim": "F", "gap": "non_goal", "why": "Envelope warp is a non-goal."},
    "AI-27": {"conf": "H", "dim": "F", "gap": "arch", "why": "No freeform gradient model."},
    "AI-28": {"conf": "H", "dim": "F", "gap": "arch", "why": "No mesh — the single biggest gap."},
    "AI-29": {"conf": "H", "dim": "F", "gap": "arch", "why": "No shape-to-shape interpolation."},
    "AI-30": {"conf": "M", "dim": "F", "why": "Static effect set; not a live non-destructive stack."},
    "AI-32": {"conf": "M", "dim": "F", "why": "One style per object; no appearance stack."},
    "AI-37": {"conf": "H", "dim": "F", "gap": "non_goal", "why": "Flat page space; no perspective grid."},
    "AI-39": {"conf": "H", "dim": "F", "why": "Same raster→vector outcome, via a tool call not a menu."},
    "AI-40": {"conf": "M", "dim": "D", "why": "Scene3D is a 3D scene, not vector extrude/bevel."},
    "AI-41": {"conf": "M", "dim": "F", "why": "SVG/PNG/PDF/LaTeX only; no PSD/EPS/DWG; renderers non-conformant."},
    "AI-42": {"conf": "H", "dim": "F", "gap": "non_goal", "why": "No asset-collection packaging step."},
    "AI-43": {"conf": "L", "dim": "W", "why": "No natural-language→vector path; nearest analogue is authoring by SDK code (run_sdk_code) or an image-input propose — a loose reframe, flagged."},
    "AI-44": {"conf": "L", "dim": "W", "why": "Deterministic token/gradient_map recolor with NO natural-language prompt interpretation — not generative-AI recolor."},
    "AI-45": {"conf": "H", "dim": "F", "gap": "arch", "why": "list_fonts resolves families; no visual font ID."},
    "AI-46": {"conf": "H", "dim": "F", "gap": "non_goal", "why": "No surface-wrap of art onto an object."},
    "AI-47": {"conf": "H", "dim": "F", "gap": "maturity", "why": "No offset-path op — a deterministic geometry the model could express; unbuilt."},
    "AI-48": {"conf": "H", "dim": "F", "gap": "maturity", "why": "No stroke→outline conversion — derivable geometry, not paradigm-precluded; unbuilt."},
    "AI-49": {"conf": "H", "dim": "F", "gap": "maturity", "why": "No brush engine — a brush-along-path is declarable in principle; unbuilt (hatch/pattern are the nearest static fills)."},
    "AI-50": {"conf": "M", "dim": "W", "why": "Coordinates are exact by construction; a grid_pattern draws lines, but there is no interactive guide/snap UI."},
    "AI-51": {"conf": "M", "dim": "W", "why": "Both plot data as charts; FG charts are declarative & data-bound, IL graphs are static objects you restyle."},
}
DIM_DEFAULT = {"has": "F", "part": "F", "none": "F", "invert": "W"}


def row_meta(fid, cov):
    m = META.get(fid, {})
    return {
        "confidence": m.get("conf", "H"),
        "dimension": m.get("dim", DIM_DEFAULT[cov]),
        "gap_type": m.get("gap", "non_goal" if cov == "none" else None),
        "rationale": m.get("why", ""),
    }


def coverage_tally():
    from collections import Counter
    c = Counter()
    for _, _, rows in GROUPS:
        for r in rows:
            c[r[4]] += 1          # r[4] is the coverage verdict (has/part/none/invert)
    return c


# Full-title bibliography for the two sources (addresses the citation review).
SOURCES = {
    "24": {"title": "Adobe Illustrator 2024 User's Guide", "pages": 231, "sentences": 2283,
           "doc_id": "586533f6-5893-446d-a3e5-55210477f24d"},
    "25": {"title": "Master Adobe Illustrator 2025", "author": "Dana J. Bailey",
           "pages": 159, "sentences": 1875, "doc_id": "56d6727a-23a3-43d2-b920-df53c8b1f8b0"},
    "26": {"title": "BMG 106: Computer Graphics Part II — Adobe Illustrator",
           "publisher": "Y. C. M. Open University", "pages": 257, "sentences": 3340,
           "doc_id": "649e47a5-cbf2-4d92-b7ab-f4d710d6351a"},
}


def manifest_identity():
    """Reproducibility identity for the FrameGraph side: sha256 + version + count."""
    import hashlib
    path = os.path.join(ROOT, "docs", "capability-manifest.json")
    raw = open(path, "rb").read()
    data = json.loads(raw)
    return {
        "manifest_path": "docs/capability-manifest.json",
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "framegraph_version": data.get("version", "?"),
        "manifest_capabilities": len(data.get("capabilities", [])),
    }


def source_identity():
    """Source-code version: the frameforge git commit that built this document.
    A dirty flag marks a render from uncommitted code so the stamp cannot lie."""
    import subprocess

    def g(*args):
        try:
            return subprocess.run(["git", "-C", ROOT, *args],
                                  capture_output=True, text=True).stdout.strip()
        except OSError:
            return ""
    sha = g("rev-parse", "HEAD")
    return {
        "repo": "frameforge",
        "git_commit": sha or "unknown",
        "git_short": (sha[:10] or "unknown"),
        "git_branch": g("rev-parse", "--abbrev-ref", "HEAD") or "?",
        "git_dirty": bool(g("status", "--porcelain")),
        "builder": "static/examples/illustrator_vs_framegraph.py",
    }


def corpus_identity():
    """External-corpus version: the exact doc-ray documents the claims cite."""
    return [{"src": k, "title": v["title"], "document_id": v["doc_id"],
             "pages": v.get("pages"), "sentences": v.get("sentences")}
            for k, v in sorted(SOURCES.items())]


def gap_split():
    """Three-way split of the NONE tally: non-goal (scope), architectural
    (paradigm precludes it), maturity (declarable in principle, unbuilt)."""
    from collections import Counter
    c = Counter()
    for _, _, rows in GROUPS:
        for r in rows:
            if r[4] == "none":
                c[row_meta(r[0], r[4])["gap_type"] or "arch"] += 1
    return c["non_goal"], c["arch"], c["maturity"]


def _manifest_names():
    """Every capability name in the manifest, for symmetric FG-side citation."""
    path = os.path.join(ROOT, "docs", "capability-manifest.json")
    data = json.loads(open(path, encoding="utf-8").read())
    return sorted({c["name"] for c in data.get("capabilities", [])}, key=len, reverse=True)


def audit_rows():
    """The full machine-readable audit matrix — one record per feature.

    Each row carries symmetric evidence: the Illustrator source ordinal AND the
    FrameGraph manifest capability names its coverage prose references (IFG-004).
    """
    import re
    names = _manifest_names()
    out = []
    for grp_title, grp_key, rows in GROUPS:
        for fid, feat, ai, ordn, cov, fg in rows:
            src, _, ordinal = ordn.partition("·")
            m = row_meta(fid, cov)
            # word-boundary match so 'line' does not match inside 'linear_gradient'
            refs = [n for n in names
                    if re.search(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9_])", fg)]
            out.append({
                "id": fid, "group": grp_title, "feature": feat,
                "illustrator_evidence": ai,
                "source": {"book": src, "ordinal": int(ordinal),
                           "title": SOURCES[src]["title"], "document_id": SOURCES[src]["doc_id"]},
                "verdict": cov, "verdict_label": COVLBL[cov],
                "framegraph_coverage": fg,
                "framegraph_manifest_refs": refs,
                "confidence": m["confidence"], "equivalence_dimension": m["dimension"],
                "gap_type": m["gap_type"], "rationale": m["rationale"],
            })
    return out


def category_subtotals():
    """Per-section (A–H) coverage counts (IFG-018)."""
    out = []
    for grp_title, _, rows in GROUPS:
        from collections import Counter
        c = Counter(r[4] for r in rows)
        out.append({"group": grp_title, "n": len(rows),
                    "counts": {k: c.get(k, 0) for k in ("has", "part", "invert", "none")}})
    return out


def score_block():
    t = coverage_tally()
    total = sum(t.values())
    ng, arch, mat = gap_split()
    return {
        "total_features": total,
        "counts": {k: t[k] for k in ("has", "part", "invert", "none")},
        "gap_breakdown": {"declared_non_goal": ng, "architectural": arch,
                          "maturity_unbuilt": mat, "true_gap": arch + mat},
        "scores": {
            "full_equivalent_pct": round(100 * t["has"] / total, 1),
            "full_or_partial_pct": round(100 * (t["has"] + t["part"]) / total, 1),
            "any_route_pct": round(100 * (t["has"] + t["part"] + t["invert"]) / total, 1),
        },
        "score_formulas": {
            "full_equivalent": f"has/total = {t['has']}/{total}",
            "full_or_partial": f"(has+part)/total = {t['has']+t['part']}/{total}  (REFRAMED & NONE excluded)",
            "any_route": f"(has+part+reframed)/total = {t['has']+t['part']+t['invert']}/{total}  (REFRAMED counted as reachable)",
        },
    }


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
    p.text([M, 84, CW, 12], "ADOBE ILLUSTRATOR 2024 · 2025 · BMG106   vs   FRAMEGRAPH v2.3.0",
           style="nmeta")
    p.text([M, 250, CW, 14], "// FEATURE-BY-FEATURE", style="ncode")
    p.text([M, 278, CW, 62], "Capability", style="ntitle")
    p.text([M, 336, CW, 62], "Teardown", style="ntitle")
    p.rect([M, 410, 120, 3], fill="fg")
    p.text([M, 436, CW - 30, 80],
           f"An interactive vector editor, mapped feature by feature against a "
           f"declarative document format. {total} capabilities, one verdict each — a "
           f"feature-surface comparison, not a maturity benchmark.",
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
    p.text([M, y, 452, 116],
           "Illustrator's surface was enumerated from three manuals (2024 User's Guide, "
           f"2025 book, BMG 106) and reduced to {total} discrete capabilities, each checked "
           "against FrameGraph's capability manifest. Evidence cites SRC·ORDINAL. This is a "
           "feature-surface comparison, not a maturity benchmark: FrameGraph is a PROPOSED "
           "format with no conformant renderer.", style="lead")
    # stacked coverage bar
    by = y + 128
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
    # explicit score math + coverage/reachability + 3-way gap split + audit pointer
    ng, arch, mat = gap_split()
    anyroute = round(100 * (tally["has"] + tally["part"] + tally["invert"]) / total)
    p.text([M, sy + 90, CW, 10],
           f"coverage {somepct}% = (HAS+PARTIAL)/{total}   ·   reachability {anyroute}% "
           f"= +REFRAMED   ·   {tally['none']} NONE = {arch} architectural + {mat} maturity "
           f"+ {ng} non-goal   ·   unweighted (subtotals are descriptive) → p.03",
           style="cite", color="faint", align="start")
    # what the glyphs mean, restated as a table
    gy = sy + 122
    p.text([M, gy, CW, 10], "READING A ROW", style="colhd")
    p.rect([M, gy + 16, CW, 1], fill="hair")
    demo = [("gid", "AI-nn", "monospace feature id (chapter-ordered)"),
            ("feat", "Feature", "the Illustrator capability, named"),
            ("ord", "[26·405]", "source book (24 / 25 / 26) · sentence ordinal — round-trips"),
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

    # -- 3. RUBRIC · SOURCES · AUDIT IDENTITY ---------------------------- #
    p = page(b, "rubric", tab="RUBRIC · SOURCES · IDENTITY")
    y = head(p, 74, "// how a verdict is decided",
             "Rubric, sources & audit identity")
    # verdict rubric with the exact threshold for each label
    p.text([M, y, CW, 10], "VERDICT RUBRIC — THE THRESHOLD FOR EACH LABEL", style="colhd")
    p.rect([M, y + 16, CW, 1], fill="ink")
    rub = [("has", "HAS", "A direct FUNCTIONAL equivalent: the same user outcome is "
            "expressible, even if authored declaratively."),
           ("part", "PARTIAL", "Narrower or different: missing interactivity, missing "
            "output fidelity, or a workflow-only (not functional) match."),
           ("invert", "REFRAMED", "Exists in both, but reached by NAMING / a tool call / "
            "an author→render loop — not a cursor. Not a gap; a different road."),
           ("none", "NONE", "No equivalent. Tagged by gap_type: non_goal (scope choice) · "
            "arch (declarative model precludes it) · maturity (plausible, unbuilt).")]
    yy = y + 26
    for cov, lbl, desc in rub:
        glyph(p, M + 10, yy + 10, cov, r=8, ground="bg")
        p.text([M + 30, yy, 90, 12], lbl, style="legname", color=COVCOL[cov])
        p.text([M + 130, yy - 1, CW - 130, 30], desc, style="legdesc")
        yy += 40
    # confidence + equivalence-dimension legends, side by side
    yy += 4
    colw = (CW - 20) / 2
    p.text([M, yy, colw, 10], "CONFIDENCE (SHOWN ON M / L ROWS)", style="colhd")
    p.text([M + colw + 20, yy, colw, 10], "EQUIVALENCE DIMENSION", style="colhd")
    p.rect([M, yy + 14, colw, 1], fill="hair")
    p.rect([M + colw + 20, yy + 14, colw, 1], fill="hair")
    conf_l = [("H", "high — direct, well-evidenced"),
              ("M", "medium — interpretive mapping"),
              ("L", "low — loose equivalence, flagged for review")]
    dim_l = [("F", "functional — same user outcome"),
             ("W", "workflow — same task, different steps"),
             ("D", "data-model — structural analogue only")]
    for i, (k, d) in enumerate(conf_l):
        p.text([M, yy + 24 + i * 18, 24, 12], k, style="gid", color="ai")
        p.text([M + 24, yy + 24 + i * 18, colw - 24, 12], d, style="legdesc")
    for i, (k, d) in enumerate(dim_l):
        p.text([M + colw + 20, yy + 24 + i * 18, 24, 12], k, style="gid", color="fg")
        p.text([M + colw + 44, yy + 24 + i * 18, colw - 44, 12], d, style="legdesc")
    # score math
    sy2 = yy + 90
    sb = score_block()
    p.text([M, sy2, CW, 10], "SCORE MATH (NO WEIGHTING)", style="colhd")
    p.rect([M, sy2 + 14, CW, 1], fill="hair")
    for i, (k, txt) in enumerate([
            ("Full equivalent", sb["score_formulas"]["full_equivalent"]),
            ("Full or partial", sb["score_formulas"]["full_or_partial"]),
            ("Reachable by any route", sb["score_formulas"]["any_route"])]):
        p.text([M, sy2 + 24 + i * 18, 180, 12], k, style="legname")
        p.text([M + 190, sy2 + 24 + i * 18, CW - 190, 12], txt, style="cite", color="sub")
    # sources (bibliography) + audit identity, side by side
    by2 = sy2 + 92
    p.text([M, by2, colw, 10], "SOURCES (doc-ray corpus · GraphQL)", style="colhd")
    p.text([M + colw + 20, by2, colw, 10], "AUDIT IDENTITY", style="colhd")
    p.rect([M, by2 + 14, colw, 1], fill="hair")
    p.rect([M + colw + 20, by2 + 14, colw, 1], fill="hair")
    # each source rendered from corpus_identity() with full pp + sentences + doc-id
    short = {"24": "Adobe Illustrator 2024 User's Guide",
             "25": "Master Adobe Illustrator 2025",
             "26": "BMG 106: Computer Graphics II"}
    for i, s in enumerate(corpus_identity()):
        p.text([M, by2 + 24 + i * 24, colw, 12],
               f"[{s['src']}] {short[s['src']]}", style="legdesc")
        p.text([M + 14, by2 + 38 + i * 24, colw - 14, 12],
               f"{s['pages']} pp · {s['sentences']:,} sentences · doc {s['document_id'][:8]}…",
               style="cite", color="faint", align="start")
    ident = manifest_identity()
    src = source_identity()
    idlines = [("FrameGraph", f"v{ident['framegraph_version']} · {ident['manifest_capabilities']} caps"),
               ("Manifest sha256", ident["manifest_sha256"][:20] + "…"),
               ("Source code", f"frameforge @{src['git_short']}"
                + (" (dirty)" if src["git_dirty"] else "")),
               ("Corpus", "[24][25][26] doc-ray · IDs at left"),
               ("Full audit", "…_vs_framegraph.audit.json"),
               ("Gate", "test_capability_manifest.py")]
    for i, (k, v) in enumerate(idlines):
        p.text([M + colw + 20, by2 + 24 + i * 20, 120, 12], k, style="legdesc")
        p.text([M + colw + 128, by2 + 24 + i * 20, colw - 128, 12], v,
               style="cite", color="sub", align="start")
    # trademark / independence
    ty2 = by2 + 150
    p.rect([M, ty2, CW, 40], fill="band")
    p.text([M + 16, ty2 + 15, CW - 32, 24],
           "Adobe and Adobe Illustrator are trademarks of Adobe Inc. This is an "
           "independent comparison, not affiliated with or endorsed by Adobe; source "
           "manuals are cited for factual feature claims only.", style="cite", color="sub")

    # -- 4..N. GRANULAR MATRIX PAGES ------------------------------------- #
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

    # -- EXAMPLES: Illustrator action → FrameGraph source ---------------- #
    p = page(b, "examples", tab="EVIDENCE · WORKED EXAMPLES")
    y = head(p, 74, "// show, don't assert",
             "Every verdict, in source")
    p.text([M, y, 452, 56],
           "So the verdicts are not just labels: here is the same intent, as an "
           "Illustrator gesture on the left and as the FrameGraph source the SDK emits "
           "on the right.", style="lead")
    ex = [
        ("AI-07 · HAS", "has", "Draw a rectangle",
         "Rectangle Tool → drag on the artboard.",
         "page.rect([40, 40, 220, 120],\n          fill=\"#1f9ec4\",\n          "
         "**stroke(2, color=\"ink\"))"),
        ("AI-01 · REFRAMED", "invert", "Act on one object",
         "Selection Tool → click the object → move.",
         "# no cursor — name it, then act\ncard = page.rect([...], id=\"hero\")\n"
         "page.move(\"hero\", dx=12, dy=0)"),
        ("AI-26 · HAS", "has", "Linear gradient fill",
         "Gradient panel → set stops → drag.",
         "page.rect([40, 40, 300, 80], fill=linear_gradient(\n    stops=[(0, "
         "\"#0f7d88\"), (1, \"#f5f7f9\")], angle=0))"),
        ("AI-02 · PARTIAL ·M", "part", "Edit an anchor point",
         "Direct Selection → drag a point by hand.",
         "# authored by coordinate, not dragged\npage.path([[40,40],[120,20],"
         "[200,60]])\n# to 'edit' AI-02: change the numbers"),
        ("AI-28 · NONE (arch)", "none", "Gradient mesh",
         "Mesh Tool → add colour points → blend.",
         "# no mesh primitive in the model —\n# nearest: a linear/radial "
         "gradient,\n# which cannot vary in two axes."),
    ]
    ey = y + 78
    boxw = CW
    for tag, cov, title, ai_do, fg_code in ex:
        p.rect([M, ey, boxw, 118], fill="band")
        p.rect([M, ey, 4, 118], fill=COVCOL[cov])
        p.text([M + 18, ey + 16, 200, 12], tag, style="gid", color=COVCOL[cov])
        p.text([M + 18, ey + 34, CW - 40, 14], title, style="feat")
        # left: Illustrator action
        half = (boxw - 40) / 2
        p.text([M + 18, ey + 58, half - 10, 12], "ILLUSTRATOR", style="colhd", color="ai")
        p.text([M + 18, ey + 74, half - 10, 36], ai_do, style="aiev")
        # right: FrameGraph source
        rx = M + 18 + half
        p.text([rx, ey + 58, half, 12], "FRAMEGRAPH SDK", style="colhd", color="fg")
        for j, ln in enumerate(fg_code.split("\n")):
            p.text([rx, ey + 74 + j * 13, half, 12], ln, style="cite", color="ink",
                   align="start")
        ey += 130

    # -- REVERSE GAPS: what FrameGraph has that Illustrator doesn't ------- #
    p = page(b, "reverse", tab="THE OTHER DIRECTION")
    y = head(p, 74, "// the comparison runs both ways",
             "What FrameGraph has that Illustrator lacks")
    p.text([M, y, 452, 96],
           "A comparison that only lists an editor's features would be rigged. These are "
           "manifest capabilities a vector editor has no NATIVE, declarative answer for — "
           "the price Illustrator pays for being a canvas, not a document engine. "
           "(Illustrator can still embed such artwork by hand, via scripts or plugins; it "
           "just is not native.)", style="lead")
    rev = [
        ("Long-form documents",
         "flow model: TOC, bibliography, footnotes, code & math blocks, keep_together "
         "— a book, not an artboard."),
        ("Structural validation",
         "a schema + validator + golden-render lock prove the document before a pixel "
         "is drawn; Illustrator has no correctness gate."),
        ("Reproducible source of truth",
         "plain-text YAML, diffable & version-controlled, with byte-stable renders — "
         "not a binary .ai project."),
        ("Parametric geometry",
         "parametric_curve, Lattice, manifolds (Klein bottle, Möbius) — equation-driven "
         "geometry Illustrator has no tool for. (Charts it does have: AI-51.)"),
        ("UI component library",
         "navbar, button, card, tabs, badge, avatar, breadcrumb, slider — a whole "
         "interface kit with no Illustrator equivalent."),
        ("Colour science",
         "Chevreul harmony + WCAG contrast_ratio + tone_scale — measured colour, not "
         "just swatches."),
        ("Machine authoring",
         "25 MCP tools: an AI author→render→verify loop. The document is built and "
         "checked by code, end to end."),
    ]
    ry = y + 112
    for i, (name, desc) in enumerate(rev):
        if i % 2 == 1:
            p.rect([M - 6, ry - 6, CW + 12, 58], fill="band")
        p.polygon([[M + 8, ry + 6], [M + 16, ry + 14], [M + 8, ry + 22], [M, ry + 14]],
                  fill="fg")
        p.text([M + 30, ry, CW - 40, 14], name, style="feat")
        p.text([M + 30, ry + 18, CW - 60, 32], desc, style="fgev", color="sub")
        p.rect([M, ry + 50, CW, 0.6], fill="hair")
        ry += 58

    # -- FINAL. VERDICT + PROVENANCE ------------------------------------- #
    p = page(b, "verdict", tab="VERDICT")
    y = head(p, 74, "// what the tally means", "Two machines, one honest score")
    p.text([M, y, 452, 148],
           f"Across {total} Illustrator capabilities from three manuals, FrameGraph has a "
           f"full equivalent for {tally['has']} and a partial one for {tally['part']}. The "
           f"{tally['none']} genuine gaps cluster where Illustrator is a painting instrument "
           f"— gradient mesh, freeform gradient, blends, the Pencil, variable-width "
           f"strokes, perspective, envelope distort, mockup. The {tally['invert']} REFRAMED "
           f"rows are the most telling: selection, image trace, and the new 2024 "
           f"generative-AI features exist in both — but FrameGraph reaches them by "
           f"naming, a tool call, and an author→render loop, not a cursor.",
           style="lead")
    # the split thesis
    ty = y + 164
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
    p.text([M, py + 26, CW, 90],
           "Illustrator features mined from THREE doc-ray corpus sources over GraphQL: "
           "[24] Adobe Illustrator 2024 User's Guide (231 pp), [25] Master Adobe "
           "Illustrator 2025 (Dana J. Bailey, 159 pp), and [26] BMG 106: Computer "
           "Graphics II (257 pp). Each SRC·ORDINAL round-trips via searchSentences(). "
           "FrameGraph coverage quotes docs/capability-manifest.json (278 capabilities, "
           "tri-state core/SDK/MCP), gated by tests/test_capability_manifest.py.",
           style="legdesc")
    # version stamp — the artifact is pinned to the code + corpus that built it
    _src = source_identity()
    _mid = manifest_identity()
    p.rect([M, py + 108, CW, 1], fill="hair")
    p.text([M, py + 120, CW, 12],
           f"VERSION · code frameforge@{_src['git_short']}"
           + ("+dirty" if _src["git_dirty"] else "")
           + f" · manifest {_mid['manifest_sha256'][:12]} (v{_mid['framegraph_version']})"
           + " · corpus doc-ray [24 586533f6][25 56d6727a][26 649e47a5]"
           + f" · built {datetime.date.today().isoformat()}",
           style="cite", color="faint", align="start")
    p.text([M, py + 138, CW, 12],
           "Composed by Claude (Fable 5) · a declarative teardown of a declarative format.",
           style="legdesc", color="faint")

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

    # Machine-readable audit sidecar (reproducibility: the PDF summarises, the
    # JSON proves). One record per feature + rubric + score math + build identity.
    audit = {
        "artifact": "illustrator_vs_framegraph capability teardown",
        "generated_at": datetime.date.today().isoformat(),
        # Version identity — this artifact is pinned to the code that built it and
        # the exact external corpus documents its claims cite.
        "version": {
            "generated_at": datetime.date.today().isoformat(),
            "source_code": source_identity(),
            "framegraph_manifest": manifest_identity(),
            "external_corpus": corpus_identity(),
        },
        "framegraph": manifest_identity(),
        "sources": SOURCES,
        "rubric": {
            "has": "a direct functional equivalent exists",
            "part": "narrower / different form, or missing interactivity or fidelity",
            "invert": "REFRAMED — exists in both, reached by naming/tool/loop not a cursor",
            "none": "no equivalent (see gap_type: non_goal | arch | maturity)",
            "confidence": "H high · M interpretive · L loose equivalence, review",
            "equivalence_dimension": "F functional · W workflow · D data-model only",
        },
        "score": score_block(),
        "category_subtotals": category_subtotals(),
        "features": audit_rows(),
    }
    audit_path = os.path.splitext(args.out)[0].replace(".fg", "") + ".audit.json"
    with open(audit_path, "w", encoding="utf-8") as fh:
        json.dump(audit, fh, indent=2, ensure_ascii=False)
    sb = audit["score"]
    vc = audit["version"]["source_code"]
    print(f"wrote {audit_path}  ({len(audit['features'])} rows · "
          f"code frameforge@{vc['git_short']}{'+dirty' if vc['git_dirty'] else ''} · "
          f"manifest {audit['framegraph']['manifest_sha256'][:12]} · "
          f"corpus {len(audit['version']['external_corpus'])} docs · "
          f"full={sb['scores']['full_equivalent_pct']}% · "
          f"gaps {sb['gap_breakdown']['architectural']}arch+"
          f"{sb['gap_breakdown']['maturity_unbuilt']}mat+"
          f"{sb['gap_breakdown']['declared_non_goal']}non-goal)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
