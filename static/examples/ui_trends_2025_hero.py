#!/usr/bin/env python3
"""Recreate ``img12_ui_trends_2025_hero`` — a dark editorial hero banner —
from its orthogonal-dimension profile in ``_tmp/temp_model.json``.

The profile is an *assessment*, not a graphic model: the source image is not in
this repository, so this client is a reconstruction driven only by the 16 scored
dimensions. Each construction below names the dimension it discharges:

  A1  Layered            grain + glow + spotlight + inset composited in z-order
  A6  Neutral/aspiration moody ground, forward-looking (no alarm colour)
  C4  Focal              spotlight cone/pool + a glowing inset card
  C18 Didone serif       GFS Didot display (a real Didot revival, not a proxy)
  C22 Upright + italic   'Trends' set in the drawn italic inside an upright title
  C23 High contrast      the face's own thick/thin modulation, set large
  C26 Display/dek/credit three typographic roles, three faces/sizes/tones
  C27 Flush-left + split flush-left title; tagline left / credit right at the base
  C28 Violet ground      near-monochrome violet field against a polychrome inset
  C29 Low-key            dark field, lit accents only
  C30 Muted/vivid        desaturated ground, saturated inset
  C31 Prominent type     white display type on near-black
  C32 Nonrepresentation  the inset is a grainy gradient bloom, no literal referent
  C34 Editorial register restrained; no decoration that is not load-bearing
  C35 Characteristic      cinematic single-source lighting
  C36 Symbolic marker    the '*' after 2025 keys the footnote tagline

Run from the repository root::

    uv run python static/examples/ui_trends_2025_hero.py
    DOC=_tmp/ui-trends-2025/ui-trends-2025-hero.fg.yaml
    uv run python tooling/frameforge_render.py $DOC --to svg --out _tmp/ui-trends-2025
    uv run --group pdfout python tooling/render_pdf.py $DOC --out _tmp/ui-trends-2025

The page declares `post` (bloom + grain). Those are RASTER-stage effects and are
applied by the MCP render pipeline only — `frameforge_render.py --to png` and the
vector targets do not carry them, which is why the grain that the composition
actually depends on is drawn as geometry rather than left to `post`.
"""
from __future__ import annotations

import math
import os
import random
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge_sdk import DocumentBuilder  # noqa: E402
from frameforge_sdk.clip import clip_path  # noqa: E402
from frameforge_sdk.paint import (  # noqa: E402
    effects,
    glow,
    linear_gradient,
    radial_gradient,
    rgba,
)

# --------------------------------------------------------------------------- #
# §1 · Canvas + the flush-left grid (C27)
# --------------------------------------------------------------------------- #
W, H = 1600, 900
MX = 96                       # side margin — the flush-left edge everything hangs on

CARD_X, CARD_Y = 1000, 112    # the inset card (C4/C30/C32)
CARD_W, CARD_H = 504, 600
CARD_R = 20                   # corner radius
CARD_CX = CARD_X + CARD_W / 2
CARD_CY = CARD_Y + CARD_H / 2

COL_W = CARD_X - 48 - MX      # display column: flush left, stops short of the card

RULE_Y = 748                  # hairline that splits the footer off the field
FOOT_Y = 782                  # footer band (tagline left, credit right)

# Three display lines, baseline-stepped. Text boxes are centre-anchored, so a
# line is placed by its centre, and the box must stay >= 1.40 * font_size or the
# renderer silently clips it — which makes consecutive line boxes overlap by
# construction, hence the `overlap="allowed"` consent on each.
DISPLAY = 166
LINE_BOX = int(DISPLAY * 1.45)
LINE_STEP = DISPLAY
L1_C = 258                    # first line centre; the stack centres on the card
LINE_C = [L1_C + i * LINE_STEP for i in range(3)]

# --------------------------------------------------------------------------- #
# §2 · Palette — near-monochrome violet ground, polychrome inset (C28/C29/C30)
# --------------------------------------------------------------------------- #
INK = "#08070C"               # near-black page ground
INK_HI = "#171126"            # lifted violet-black (top of the field)
INK_LO = "#050409"            # the floor
VIOLET = "#7C4DFF"            # the light source
VIOLET_HI = "#A78BFA"         # its hot core
WHITE = "#FFFFFF"
DEK = "#B3A8CC"               # dek / tagline tone
CREDIT = "#7B7196"            # credit tone (one step down from the dek)
RULE = "#2A2340"

# the inset's saturated hues — the only polychrome in the composition (C30)
MAGENTA = "#FF2D78"
INDIGO = "#7C3AED"
CYAN = "#22D3EE"
AMBER = "#FFB020"
EMBER = "#FF6B3D"

DIDOT = ["GFS Didot", "Didot", "Bodoni 72", "serif"]          # C18/C23
SANS = ["Inter", "Helvetica Neue", "Arial", "sans-serif"]     # C26 support roles


def rounded_rect_d(x, y, w, h, r):
    """SVG path data for a rounded rectangle.

    The object-level ``clip`` (ClipSpec ``rect`` + ``radius``) is only honoured
    on images, and the ``inset`` basic shape lowers to a square-cornered rect —
    so a rounded group clip has to be expressed as a real path."""
    return (f"M{x + r},{y} H{x + w - r} A{r},{r} 0 0 1 {x + w},{y + r} "
            f"V{y + h - r} A{r},{r} 0 0 1 {x + w - r},{y + h} "
            f"H{x + r} A{r},{r} 0 0 1 {x},{y + h - r} "
            f"V{y + r} A{r},{r} 0 0 1 {x + r},{y} Z")


def alpha_ellipse(pg, cx, cy, rx, ry, color, peak, *, mid=0.55, mid_a=0.22, **fields):
    """A soft bloom: a bbox-fitted radial ramp from `color` at `peak` alpha to the
    same hue at zero alpha. Filter-free on purpose — cairosvg drops SVG filter
    primitives, so every soft edge in this document is real gradient geometry."""
    pg.ellipse([cx, cy], rx, ry, fill=radial_gradient(
        [(color, 0.0, peak), (color, mid, mid_a), (color, 1.0, 0.0)],
        at="50% 50%", shape="ellipse"), **fields)


def scatter(pg, rng, box, n, *, r_lo, r_hi, a_lo, a_hi, colors, radial_bias=0.0):
    """Deterministic geometric grain (A1). feTurbulence rasterises far too flat
    to read as film grain here, so the noise floor is drawn as isotropic
    geometry; `radial_bias` > 0 pulls density toward the box centre."""
    x, y, w, h = box
    for _ in range(n):
        if radial_bias and rng.random() < radial_bias:
            t = rng.random() ** 0.5
            ang = rng.random() * math.tau
            px = x + w / 2 + math.cos(ang) * t * w / 2
            py = y + h / 2 + math.sin(ang) * t * h / 2
        else:
            px, py = x + rng.random() * w, y + rng.random() * h
        pg.circle([px, py], rng.uniform(r_lo, r_hi),
                  fill=rng.choice(colors), opacity=rng.uniform(a_lo, a_hi),
                  decorative=True)


def build():
    d = DocumentBuilder(title="UI Design Trends in 2025 — hero banner")
    d.describe(
        "Dark editorial hero banner: a flush-left high-contrast Didone display "
        "line with an italic word, a glowing nonrepresentational gradient inset, "
        "single-source violet lighting, and a split tagline/credit footer.")
    d.meta(reconstruction={
        "source_profile": "img12_ui_trends_2025_hero",
        "source_model": "_tmp/temp_model.json",
        "basis": "16 scored orthogonal dimensions; the reference image is NOT in "
                 "this repository — geometry and copy are inferred, not measured",
    })

    for name, value in (
        ("ink", INK), ("inkHi", INK_HI), ("inkLo", INK_LO),
        ("violet", VIOLET), ("violetHi", VIOLET_HI), ("white", WHITE),
        ("dek", DEK), ("credit", CREDIT), ("rule", RULE),
        ("magenta", MAGENTA), ("indigo", INDIGO), ("cyan", CYAN),
        ("amber", AMBER), ("ember", EMBER),
    ):
        d.define_color(name, value)

    # C26 — three typographic roles, deliberately far apart in face, size and tone
    d.define_text_style("display", font_family=DIDOT, font_size=DISPLAY,
                        color="white", letter_spacing=-1.5, line_height=1.04)
    d.define_text_style("displayItalic", font_family=DIDOT, font_size=DISPLAY,
                        color="white", italic=True, letter_spacing=-1.0,
                        line_height=1.04)
    d.define_text_style("marker", font_family=DIDOT, font_size=58,
                        color="violetHi")                       # C36 the '*'
    d.define_text_style("dek", font_family=SANS, font_size=20, font_weight=300,
                        color="dek", letter_spacing=0.2, line_height=1.4)
    d.define_text_style("credit", font_family=SANS, font_size=14, font_weight=500,
                        color="credit", letter_spacing=1.6, align="right")

    pg = d.page(
        "hero",
        canvas={"size": [W, H], "units": "px"},
        reading_order=["title1", "title2", "title3", "tagline", "credit"],
        # A3 raster post — bloom then grain over the finished raster. Vector
        # targets are byte-unaffected and the renderer says so, which is why the
        # card carries its own drawn grain below.
        post={"bloom": {"radius": 26.0, "strength": 0.34, "threshold": 0.58},
              "grain": {"amount": 0.024, "seed": 2025, "monochrome": True}},
    )

    rng = random.Random(20250712)

    # ---------------------------------------------------------------- #
    # §3 · The field: low-key violet ground (C28/C29)
    # ---------------------------------------------------------------- #
    pg.layer("field")
    pg.rect([0, 0, W, H], fill=linear_gradient(
        [(INK_HI, 0.0), (INK, 0.46), (INK_LO, 1.0)], angle=180))

    # C4/C35 — one light source, above and to the left. Built entirely from soft
    # radial ramps: a polygon shaft would carry hard lateral edges that read as
    # a drawn triangle rather than light, so the shaft is a tall narrow bloom
    # instead, layered over a broad pool and a low floor spill.
    alpha_ellipse(pg, 560, 210, 620, 500, VIOLET, 0.26, mid=0.5, mid_a=0.09,
                  decorative=True)                                  # the pool
    alpha_ellipse(pg, 545, 100, 250, 600, VIOLET, 0.22, mid=0.45, mid_a=0.07,
                  decorative=True)                                  # the shaft
    alpha_ellipse(pg, 530, 40, 200, 190, VIOLET_HI, 0.22, mid=0.5, mid_a=0.06,
                  decorative=True)                                  # the source
    alpha_ellipse(pg, 500, 660, 640, 190, VIOLET, 0.10, mid=0.5, mid_a=0.03,
                  decorative=True)                                  # floor spill

    # ---------------------------------------------------------------- #
    # §4 · The inset: a grainy nonrepresentational bloom (C30/C32)
    # ---------------------------------------------------------------- #
    pg.layer("inset")

    # spill from the card onto the field — this is what makes it read as lit
    # rather than pasted (A1 layering)
    alpha_ellipse(pg, CARD_CX, CARD_CY, CARD_W * 1.15, CARD_H * 0.95,
                  INDIGO, 0.42, mid=0.42, mid_a=0.14, decorative=True)
    alpha_ellipse(pg, CARD_CX - 60, CARD_CY - 120, CARD_W * 0.85, CARD_H * 0.5,
                  MAGENTA, 0.22, mid=0.5, mid_a=0.07, decorative=True)
    alpha_ellipse(pg, CARD_CX + 40, CARD_CY + 160, CARD_W * 0.8, CARD_H * 0.5,
                  CYAN, 0.16, mid=0.5, mid_a=0.05, decorative=True)

    pg.rect([CARD_X, CARD_Y, CARD_W, CARD_H], radius=CARD_R, fill=INK_LO,
            meta={"role": "inset-image",
                  "description": "nonrepresentational grainy gradient bloom"},
            **effects(glow=glow(blur=92, color=INDIGO, opacity=0.6)))

    # The clip rides OUTSIDE the group's box-origin translate, so its path is
    # authored in page coordinates while the children stay local to the box.
    with pg.local([CARD_X, CARD_Y, CARD_W, CARD_H],
                  clip=clip_path(rounded_rect_d(
                      CARD_X, CARD_Y, CARD_W, CARD_H, CARD_R))) as card:
        cw, ch = CARD_W, CARD_H
        card.rect([0, 0, cw, ch], decorative=True, fill=linear_gradient(
            [("#2A1748", 0.0), ("#120C22", 0.62), ("#0A0714", 1.0)], angle=155))

        # the bloom itself: overlapping saturated ramps, no literal referent.
        # Radii overrun the card so colour reaches the corners rather than
        # leaving a dead ring the vignette then doubles down on.
        alpha_ellipse(card, cw * 0.22, ch * 0.22, 270, 260, MAGENTA, 0.95,
                      mid=0.6, mid_a=0.34)
        alpha_ellipse(card, cw * 0.82, ch * 0.18, 265, 255, INDIGO, 0.98,
                      mid=0.58, mid_a=0.38)
        alpha_ellipse(card, cw * 0.86, ch * 0.72, 255, 250, CYAN, 0.85,
                      mid=0.55, mid_a=0.28)
        alpha_ellipse(card, cw * 0.16, ch * 0.78, 245, 240, AMBER, 0.78,
                      mid=0.55, mid_a=0.24)
        alpha_ellipse(card, cw * 0.52, ch * 0.50, 200, 215, EMBER, 0.55,
                      mid=0.5, mid_a=0.16)
        # the hot core the bloom radiates from
        alpha_ellipse(card, cw * 0.46, ch * 0.38, 140, 130, WHITE, 0.38,
                      mid=0.42, mid_a=0.10)

        # pull the corners back down so the card stays low-key (C29) without
        # desaturating the bloom that makes it the vivid inset (C30)
        card.rect([0, 0, cw, ch], decorative=True, fill=radial_gradient(
            [("#05040A", 0.0, 0.0), ("#05040A", 0.66, 0.05),
             ("#05040A", 1.0, 0.52)], at="50% 46%", shape="ellipse"))

        # A1 — the drawn grain floor, denser toward the lit centre. Density is
        # the whole game: at ~2.5k dots the field reads as dust, so it is set
        # near one speck per 34 px² and each speck is kept under 0.09 alpha so
        # the eye integrates texture instead of counting particles. The page
        # `post.grain` only touches the PNG — this is what the SVG and the PDF
        # carry, so it cannot be skipped.
        scatter(card, rng, [0, 0, cw, ch], 9000, r_lo=0.55, r_hi=1.45,
                a_lo=0.015, a_hi=0.085, radial_bias=0.45,
                colors=[WHITE, WHITE, "#000000", VIOLET_HI, AMBER])

        # the inset edge: a hairline lip, plus a brighter top rim where the
        # light lands (a gradient is a paint, never a stroke colour — the model
        # types stroke_style.color as a plain colour string)
        card.rect([0.5, 0.5, cw - 1, ch - 1], radius=CARD_R, fill="none",
                  stroke_style={"color": rgba(WHITE, 0.14), "width": 1})
        card.rect([CARD_R, 0.5, cw - 2 * CARD_R, 1], fill=linear_gradient(
            [(WHITE, 0.0, 0.05), (WHITE, 0.45, 0.42), (WHITE, 1.0, 0.08)],
            angle=90), decorative=True)
        # left rim: the edge that faces the page's light source (C35 coherence)
        card.rect([0.5, CARD_R, 1, ch - 2 * CARD_R], fill=linear_gradient(
            [(VIOLET_HI, 0.0, 0.30), (VIOLET_HI, 0.5, 0.12),
             (VIOLET_HI, 1.0, 0.0)], angle=180), decorative=True)

    # ---------------------------------------------------------------- #
    # §5 · Veil — the vignette sits UNDER the type so the display stays the
    #      brightest ink on the page (C31), not something the atmosphere dims.
    # ---------------------------------------------------------------- #
    pg.layer("veil")
    pg.rect([0, 0, W, H], fill=radial_gradient(
        [("#000000", 0.0, 0.0), ("#000000", 0.62, 0.06), ("#000000", 1.0, 0.48)],
        at="50% 44%", shape="ellipse"), decorative=True)

    # ---------------------------------------------------------------- #
    # §6 · The display stack (C18/C22/C23/C26/C31/C36)
    # ---------------------------------------------------------------- #
    pg.layer("type")

    def line(idx, content, oid):
        # optical left alignment: the Didone's left side bearing is pulled back
        # so the display stem, not the glyph box, sits on the flush-left edge
        pg.text([MX - 8, LINE_C[idx] - LINE_BOX / 2, COL_W, LINE_BOX], content,
                id=oid, style="display", overlap="allowed")

    line(0, "UI Design", "title1")
    # C22 — the drawn italic carries one word of the upright title
    line(1, [{"text": "Trends", "style": "displayItalic"}], "title2")
    # C36 — a superior asterisk keyed to the footnote in the footer. A smaller
    # span sits on the shared baseline, so it rides high by construction rather
    # than by a hand-tuned offset.
    line(2, [{"text": "in 2025", "style": "display"},
             {"text": "*", "style": "marker"}], "title3")

    # ---------------------------------------------------------------- #
    # §7 · The split footer (C27/C26)
    # ---------------------------------------------------------------- #
    pg.layer("footer")
    pg.rect([MX, RULE_Y, W - 2 * MX, 1], fill=linear_gradient(
        [(RULE, 0.0, 0.9), (RULE, 0.55, 0.5), (RULE, 1.0, 0.0)], angle=90),
        decorative=True)
    pg.text([MX, FOOT_Y, 760, 34],
            "*a field guide to the interfaces we'll be building next year",
            id="tagline", style="dek")
    pg.text([W - MX - 420, FOOT_Y + 3, 420, 30], "by souptikdn",
            id="credit", style="credit")

    # ---------------------------------------------------------------- #
    # §8 · The grain floor, over everything (A1)
    # ---------------------------------------------------------------- #
    pg.layer("grain")
    scatter(pg, rng, [0, 0, W, H], 9000, r_lo=0.5, r_hi=1.25,
            a_lo=0.010, a_hi=0.045, colors=[WHITE, "#000000", VIOLET_HI])

    return d


if __name__ == "__main__":
    from frameforge_sdk.validate import validate_static_rules

    out = os.path.join(ROOT, "_tmp", "ui-trends-2025")
    os.makedirs(out, exist_ok=True)
    doc = build()
    report = validate_static_rules(doc.build_dict())
    for issue in report.issues:
        print(f"{issue.severity:8} {issue.rule_id}: {issue.message}")
    print(f"static rules: {'ok' if report.ok else 'FAILED'} ({len(report.issues)} issue(s))")
    path = os.path.join(out, "ui-trends-2025-hero.fg.yaml")
    doc.write(path)
    print(f"wrote {path}")
