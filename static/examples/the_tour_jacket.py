#!/usr/bin/env python3
"""Recreate ``img5_the_tour_jacket`` — a full book jacket flat (back / spine /
front with an ISBN barcode) — from its orthogonal-dimension profile in
``_tmp/temp_model.json``.

The profile is an *assessment*, not a graphic model: the source image is not in
this repository, so this client is a reconstruction driven only by the 10 scored
dimensions. Each construction names the dimension it discharges:

  A2  Modular grid       a visible 4x8 module grid on the front; TOUR is broken
                         TO / UR onto it, each pair filling the measure
  C20 Heavy/black display Archivo at wght 900 / wdth 125 — a real variable-font
                         instance, not a faux-bold stroke
  C24 Conventional cols  back-cover body at a 66-character measure
  C26 Role differentiation title / subtitle / author / spine / back copy / colophon
  C27 Flush-left         every text block hangs on its panel's left safe edge
  C28 Yellow + black     exactly two ink values across all three panels
  C31 Extreme contrast   #000 on #FEDD00 = 15.56:1 (verified, see COLOUR_PROOF)
  C32 Simplified         line-art mountain: ridges, hatching, a switchback road
  C33 Restrained         no ornament that is not the illustration or the grid
  O16 Print-constrained  real trim/bleed/spine geometry, fold + crop marks, and a
                         spec-conformant EAN-13 + EAN-5 symbol (not drawn bars)

PLACEHOLDER CONTENT. The title, author, imprint, jacket copy and ISBN are
invented for this mock. 978-1-234567-89-7 is the conventional dummy ISBN; its
check digit is computed, not asserted (see ``ean13_modules``).

Run from the repository root::

    uv run python static/examples/the_tour_jacket.py
    DOC=_tmp/the-tour-jacket/the-tour-jacket.fg.yaml
    uv run python tooling/frameforge_render.py $DOC --to svg --out _tmp/the-tour-jacket
    uv run --group pdfout python tooling/render_pdf.py $DOC --out _tmp/the-tour-jacket
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder  # noqa: E402
from frameforge.sdk.geometry import Mat3  # noqa: E402
from frameforge.sdk.paint import stroke  # noqa: E402

# --------------------------------------------------------------------------- #
# §1 · Print geometry (O16) — everything downstream derives from these
# --------------------------------------------------------------------------- #
# The canvas is authored at 96 px/in, so 1 px == 1 CSS inch/96 and every
# dimension below is a real press dimension rather than a screen guess.
PPI = 96.0


def inches(v: float) -> float:
    return v * PPI


TRIM_W, TRIM_H = 6.00, 9.00        # in — a standard US trade hardcover
SPINE_IN = 0.875                   # in — ~320pp on 50lb uncoated + boards
BLEED_IN = 0.125                   # in — press bleed on all four sides
SAFE_IN = 0.375                    # in — keep live matter off the folds

BLEED = inches(BLEED_IN)
SAFE = inches(SAFE_IN)
PANEL_W = inches(TRIM_W)
PANEL_H = inches(TRIM_H)
SPINE_W = inches(SPINE_IN)

W = BLEED * 2 + PANEL_W * 2 + SPINE_W      # 1260 px == 13.125 in
H = BLEED * 2 + PANEL_H                    # 888 px  ==  9.25 in

BACK_X = BLEED                             # back panel left edge (at trim)
SPINE_X = BACK_X + PANEL_W                 # first fold
FRONT_X = SPINE_X + SPINE_W                # second fold
TRIM_T, TRIM_B = BLEED, BLEED + PANEL_H

# per-panel live areas
FRONT_L, FRONT_R = FRONT_X + SAFE, FRONT_X + PANEL_W - SAFE
BACK_L, BACK_R = BACK_X + SAFE, BACK_X + PANEL_W - SAFE
LIVE_T, LIVE_B = TRIM_T + SAFE, TRIM_B - SAFE
LIVE_W = FRONT_R - FRONT_L                 # 504 px
LIVE_H = LIVE_B - LIVE_T                   # 792 px

# A2 — the visible modular grid: 4 columns x 8 rows over the front live area
COLS, ROWS = 4, 8
MOD_W, MOD_H = LIVE_W / COLS, LIVE_H / ROWS        # 126 x 99


def row_y(i: float) -> float:
    return LIVE_T + i * MOD_H


def col_x(i: float) -> float:
    return FRONT_L + i * MOD_W


# --------------------------------------------------------------------------- #
# §2 · Ink (C28/C31) — a two-value system, nothing else is permitted
# --------------------------------------------------------------------------- #
YELLOW = "#FEDD00"        # process yellow; Pantone Yellow C is the press match
BLACK = "#000000"
COLOUR_PROOF = 15.56      # WCAG contrast, black on YELLOW (see __main__)

# One family, one variable font. Roles separate by weight / width / size / case
# rather than by adding faces (C26 under C33's restraint).
# NOTE the chain must carry a generic fallback: font_metrics returns None for a
# single-family chain, which silently drops author-time measurement onto the
# per-character estimate.
GROTESK = ["Archivo", "Helvetica Neue", "Arial", "sans-serif"]

# C33 — one modular scale, ratio 1.2 from an 11 px base, so every role's size is
# derived rather than chosen. The display size is the one exception: it is
# solved from the measure in §5 and therefore cannot sit on the scale.
SCALE_BASE, SCALE_RATIO = 11.0, 1.2


def step(n: int) -> float:
    return round(SCALE_BASE * SCALE_RATIO ** n, 2)


S_MICRO = step(0)      # 11.00 — colophon, barcode HRI, ISBN caption
S_BODY = step(1)       # 13.20 — back-cover body
S_SMALL = step(2)      # 15.84 — subtitle, spine author, back imprint
S_HOOK = step(4)       # 22.81 — back-cover hook
S_AUTHOR = step(6)     # 32.85 — front author
S_SPINE = step(7)      # 39.42 — spine title
S_KICKER = step(9)     # 56.76 — the "THE" kicker
BODY_LH = 1.62         # back-cover leading
BLACK_EXP = "'wght' 900, 'wdth' 125"      # the display instance (C20)
BLACK_NORM = "'wght' 900, 'wdth' 100"
BOLD_NORM = "'wght' 700, 'wdth' 100"
BOOK_NORM = "'wght' 400, 'wdth' 100"
MED_NORM = "'wght' 500, 'wdth' 100"

# Real advances read from Archivo[wdth,wght].ttf at the display instance
# (fontTools varLib instancer; upm 1000, sCapHeight 686). The display size is
# solved from these, not eyeballed — see §5.
ADV_EXP = {"T": 0.8770, "O": 1.0080, "U": 0.9890, "R": 0.9430}
CAP_EM = 0.686

# --------------------------------------------------------------------------- #
# §3 · EAN-13 + EAN-5 (O16) — GS1 General Specifications / ISO-IEC 15420
# --------------------------------------------------------------------------- #
# Left-hand odd-parity ("A"/L) set. The even-parity ("B"/G) and right-hand ("C"/R)
# sets are DERIVED from it — R is the bitwise complement, G is R reversed — so
# there is one table to get wrong instead of three.
_L = {
    "0": "0001101", "1": "0011001", "2": "0010011", "3": "0111101", "4": "0100011",
    "5": "0110001", "6": "0101111", "7": "0111011", "8": "0110111", "9": "0001011",
}
_R = {d: "".join("1" if b == "0" else "0" for b in p) for d, p in _L.items()}
_G = {d: p[::-1] for d, p in _R.items()}

# Which of the six left-hand digits use the even-parity set, keyed by digit 1.
_PARITY13 = {
    "0": "LLLLLL", "1": "LLGLGG", "2": "LLGGLG", "3": "LLGGGL", "4": "LGLLGG",
    "5": "LGGLLG", "6": "LGGGLL", "7": "LGLGLG", "8": "LGLGGL", "9": "LGGLGL",
}
# EAN-5 parity, keyed by its own weighted checksum.
_PARITY5 = {
    0: "GGLLL", 1: "GLGLL", 2: "GLLGL", 3: "GLLLG", 4: "LGGLL",
    5: "LLGGL", 6: "LLLGG", 7: "LGLGL", 8: "LGLLG", 9: "LLGLG",
}


def ean13_check_digit(first12: str) -> str:
    """Modulo-10 check digit: odd positions x1, even positions x3."""
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(first12))
    return str((10 - total % 10) % 10)


def ean13_modules(first12: str) -> tuple[str, str]:
    """Return (module string, full 13-digit code). '1' is a bar, '0' a space."""
    if len(first12) != 12 or not first12.isdigit():
        raise ValueError("EAN-13 takes exactly 12 digits; the 13th is computed")
    code = first12 + ean13_check_digit(first12)
    parity = _PARITY13[code[0]]
    left = "".join((_L if p == "L" else _G)[d] for p, d in zip(parity, code[1:7]))
    right = "".join(_R[d] for d in code[7:])
    return "101" + left + "01010" + right + "101", code


def ean5_modules(digits: str) -> str:
    """Return the 48-module add-on string (price/currency block)."""
    if len(digits) != 5 or not digits.isdigit():
        raise ValueError("EAN-5 takes exactly 5 digits")
    checksum = (3 * sum(int(digits[i]) for i in (0, 2, 4))
                + 9 * sum(int(digits[i]) for i in (1, 3))) % 10
    parity = _PARITY5[checksum]
    parts = [(_L if p == "L" else _G)[d] for p, d in zip(parity, digits)]
    return "01011" + "01".join(parts)


def decode_ean13(modules: str) -> str:
    """Read a module string back to digits — the verification counterpart of
    :func:`ean13_modules`. An encoder nobody decodes is an unverified claim."""
    if len(modules) != 95 or modules[:3] != "101" or modules[-3:] != "101":
        raise ValueError("not a 95-module EAN-13 frame")
    if modules[45:50] != "01010":
        raise ValueError("centre guard missing")
    inv_l = {v: k for k, v in _L.items()}
    inv_g = {v: k for k, v in _G.items()}
    inv_r = {v: k for k, v in _R.items()}
    parity, left = "", ""
    for i in range(6):
        chunk = modules[3 + i * 7: 10 + i * 7]
        if chunk in inv_l:
            parity += "L"
            left += inv_l[chunk]
        elif chunk in inv_g:
            parity += "G"
            left += inv_g[chunk]
        else:
            raise ValueError(f"undecodable left chunk {chunk}")
    right = "".join(inv_r[modules[50 + i * 7: 57 + i * 7]] for i in range(6))
    first = next(d for d, p in _PARITY13.items() if p == parity)
    return first + left + right


ISBN12 = "978123456789"                     # the conventional publishing dummy
PRICE5 = "52995"                            # EAN-5: US$29.95
BAR_MODULE = 1.7                            # px per module (~129% magnification)
BAR_H = 60 * BAR_MODULE
GUARD_EXTRA = 5 * BAR_MODULE                # guards run below the digit line

# --------------------------------------------------------------------------- #
# §4 · Copy (placeholder — see the module docstring)
# --------------------------------------------------------------------------- #
TITLE_PAIRS = ("TO", "UR")
KICKER = "THE"
SUBTITLE = "TWENTY-ONE DAYS IN THE HIGH MOUNTAINS"
AUTHOR = "H. J. ANSELM"
IMPRINT = "MERIDIAN & CO."

BACK_HOOK = ("Three weeks. Twenty-one stages.\nOne climb that decides all of it.")
BACK_BODY = [
    "Every July the race goes up. For nineteen days the road is flat enough to "
    "argue about, and then it tilts, and the argument ends. What happens on "
    "those four or five afternoons in the high mountains is the only part of "
    "the Tour anyone remembers a decade later.",
    "H. J. Anselm spent a season inside the convoy — in team cars on the "
    "Galibier, in feed zones at six in the morning, in hotel corridors where "
    "the day's loser sat on the floor and could not speak. The result is a "
    "book about altitude and arithmetic: how a race is won by riders who have "
    "already calculated, to the watt, exactly how much they are prepared to "
    "lose.",
    "Clear-eyed, unsentimental and very fast, The Tour is the account of "
    "professional cycling's hardest three weeks that the sport has been "
    "waiting for.",
]
COLOPHON = "Cover design by Meridian Studio.  Printed in Great Britain."


def build():
    d = DocumentBuilder(title="The Tour — full jacket flat")
    d.describe(
        "Book jacket flat (back / spine / front) in a two-value yellow-and-black "
        "system: a heavy grotesque title broken TO / UR on a visible modular "
        "grid, line-art mountain illustration, conventional back-cover measure, "
        "and a spec-conformant EAN-13 + EAN-5 ISBN symbol.")
    d.meta(reconstruction={
        "source_profile": "img5_the_tour_jacket",
        "source_model": "_tmp/temp_model.json",
        "basis": "10 scored orthogonal dimensions; the reference image is NOT in "
                 "this repository — geometry and copy are inferred, not measured",
        "placeholder": "title, author, imprint, jacket copy and ISBN are invented",
    }, print_spec={
        "trim_in": [TRIM_W, TRIM_H], "spine_in": SPINE_IN,
        "bleed_in": BLEED_IN, "safe_in": SAFE_IN, "ppi": PPI,
        "flat_in": [round(W / PPI, 4), round(H / PPI, 4)],
        "inks": 2, "contrast_black_on_yellow": COLOUR_PROOF,
    })

    d.define_color("yellow", YELLOW)
    d.define_color("black", BLACK)

    def ts(name, *, size, var=BOOK_NORM, tracking=None, lh=None, align=None):
        d.define_text_style(
            name, font_family=GROTESK, font_size=size, color="black",
            font_variation_settings=var,
            **({"letter_spacing": tracking} if tracking is not None else {}),
            **({"line_height": lh} if lh is not None else {}),
            **({"align": align} if align is not None else {}))

    # C26 — the differentiated roles, all from one family and one scale
    DISPLAY = round(LIVE_W / (ADV_EXP["U"] + ADV_EXP["R"]), 1)   # solved, §5
    ts("display", size=DISPLAY, var=BLACK_EXP, lh=1.0)
    ts("kicker", size=S_KICKER, var=BLACK_EXP, tracking=1)
    ts("subtitle", size=S_SMALL, var=BOLD_NORM, tracking=3.4)
    ts("author", size=S_AUTHOR, var=BLACK_NORM, tracking=0.4)
    ts("spineTitle", size=S_SPINE, var=BLACK_NORM, tracking=0.5)
    ts("spineAuthor", size=S_SMALL, var=BOLD_NORM, tracking=2.2)
    ts("spineImprint", size=S_MICRO, var=BOLD_NORM, tracking=2.4, align="right")
    ts("hook", size=S_HOOK, var=BLACK_NORM, lh=1.22)
    ts("body", size=S_BODY, var=BOOK_NORM, lh=BODY_LH)
    ts("imprint", size=S_SMALL, var=BLACK_NORM, tracking=1.6)
    ts("colophon", size=S_MICRO, var=MED_NORM, tracking=0.6)
    ts("isbnText", size=S_MICRO, var=BOLD_NORM, tracking=1.2)
    # Barcode human-readable interpretation. Alignment lives in the style
    # because `align` is a Style property, not an object field. The tracking is
    # what spreads six digits across their 42-module half — interleaving spaces
    # into the string instead made the run wider than its box, so the renderer
    # clipped it and the halves collided.
    ts("hriLead", size=S_MICRO, var=MED_NORM, tracking=0.5, align="right")
    ts("hri", size=S_MICRO, var=MED_NORM, tracking=4.4, align="center")
    ts("hriSmall", size=S_MICRO, var=MED_NORM, tracking=4.4, align="center")

    pg = d.page(
        "jacket",
        canvas={"size": [W, H], "units": "px"},
        # A11Y-4: every non-decorative object carries an id and appears here,
        # in the order a reader meets the jacket — front, spine, then back.
        reading_order=["front-kicker", "front-title-1", "front-title-2",
                       "front-subtitle", "front-author", "spine",
                       "back-hook", "back-body-0", "back-body-1", "back-body-2",
                       "back-isbn", "hri-lead", "hri-left", "hri-right",
                       "hri-addon", "back-imprint", "back-colophon"],
    )

    # ------------------------------------------------------------------ #
    # §5 · The stock: one flood of yellow across the whole bleed
    # ------------------------------------------------------------------ #
    pg.layer("stock")
    pg.rect([0, 0, W, H], fill="yellow", decorative=True)

    # ------------------------------------------------------------------ #
    # §6 · The visible modular grid (A2) — front panel only. The evidence for
    #      A2 is the title's construction, so the grid is exposed where the
    #      title sits and stays latent (but obeyed) on the back.
    # ------------------------------------------------------------------ #
    pg.layer("grid")
    HAIR = 0.75
    for c in range(COLS + 1):
        pg.rect([col_x(c) - HAIR / 2, LIVE_T, HAIR, LIVE_H],
                fill="black", decorative=True)
    for r in range(ROWS + 1):
        pg.rect([FRONT_L, row_y(r) - HAIR / 2, LIVE_W, HAIR],
                fill="black", decorative=True)

    # ------------------------------------------------------------------ #
    # §7 · Front panel type (C20/C27/C26)
    # ------------------------------------------------------------------ #
    pg.layer("front-type")

    # A text box is centre-anchored and silently clips below ~1.40x the font
    # size, so each display line gets a box taller than its module band and is
    # positioned by the band's centre; consecutive boxes therefore overlap by
    # construction, hence the explicit consent.
    def band(text, oid, style, r0, r1, *, size, x=None, w=None, extra=0.0):
        cy = (row_y(r0) + row_y(r1)) / 2 + extra
        h = max(size * 1.55, (r1 - r0) * MOD_H)
        pg.text([x if x is not None else FRONT_L, cy - h / 2,
                 w if w is not None else LIVE_W, h],
                text, id=oid, style=style, overlap="allowed")

    band(KICKER, "front-kicker", "kicker", 0, 1, size=54)
    # TOUR broken across two module bands. DISPLAY is solved so the wider pair
    # (U+R = 1.932 em) exactly fills the 504 px measure; TO then runs 12 px
    # short, which is the honest flush-left rag, not a fitting error.
    band(TITLE_PAIRS[0], "front-title-1", "display", 1, 3, size=DISPLAY)
    band(TITLE_PAIRS[1], "front-title-2", "display", 3, 5, size=DISPLAY)

    # ------------------------------------------------------------------ #
    # §8 · Line-art mountain (C32/C33) — rows 5-6 of the module grid
    # ------------------------------------------------------------------ #
    pg.layer("illustration")
    ILL_T, ILL_B = row_y(5) + 14, row_y(7) - 22
    ill_h = ILL_B - ILL_T

    def ill(fx, fy):
        """Map illustration-local (0..1 across, 0..1 up from the base) to px."""
        return [FRONT_L + fx * LIVE_W, ILL_B - fy * ill_h]

    def ridge_at(profile, fx):
        """Height of a piecewise-linear ridge at fx (for occlusion below)."""
        for (x0, y0), (x1, y1) in zip(profile, profile[1:]):
            if x0 <= fx <= x1:
                t = 0.0 if x1 == x0 else (fx - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return profile[0][1] if fx < profile[0][0] else profile[-1][1]

    SUMMIT_X = 0.46
    NEAR = ((0.00, 0.06), (0.09, 0.30), (0.17, 0.24), (0.28, 0.52),
            (0.37, 0.68), (SUMMIT_X, 1.00), (0.55, 0.62), (0.63, 0.70),
            (0.74, 0.34), (0.85, 0.44), (1.00, 0.10))
    FAR = ((0.52, 0.22), (0.62, 0.46), (0.71, 0.38), (0.80, 0.74),
           (0.89, 0.52), (1.00, 0.66))

    # The far ridge is emitted ONLY where it stands above the near ridge —
    # line art has no fill to hide behind, so the occlusion has to be computed
    # or the two profiles read as one crossing squiggle.
    seg, visible = [], []
    for i in range(121):
        fx = FAR[0][0] + (1.0 - FAR[0][0]) * i / 120
        fy = ridge_at(FAR, fx)
        if fy > ridge_at(NEAR, fx):
            seg.append((fx, fy))
        elif seg:
            visible.append(seg)
            seg = []
    if seg:
        visible.append(seg)
    for run in visible:
        if len(run) > 1:
            pg.polyline([ill(x, y) for x, y in run], fill="none",
                        decorative=True, **stroke(1.6, color="black",
                                                  join="round"))

    # the near ridge — the subject
    pg.polyline([ill(x, y) for x, y in NEAR], fill="none", decorative=True,
                **stroke(3.4, color="black", join="round", cap="round"))

    # Shading, held to two gestures because C32 scores this "Simplified" and
    # C33 "Restrained". An earlier pass drew a switchback road up the west
    # flank; as a polyline it read as a bar chart standing on the mountain, and
    # nothing in the profile evidences it — so the illustration is ridges,
    # hatch and ground line only.
    #
    # East face: fine strokes parallel to the summit->base chord, each one
    # dropped to the ground line so the face reads as a plane, not as ticks.
    EAST = (0.74, 0.34)
    for i in range(1, 11):
        t = i / 11.0
        x0 = SUMMIT_X + t * (EAST[0] - SUMMIT_X)
        # start on the summit->base chord, but never ABOVE the real ridge: the
        # east profile dips below the chord around fx 0.55, so an unclamped
        # stroke floats off the mountain and crosses the ridge line it is
        # supposed to be shading
        y0 = min(1.00 + t * (EAST[1] - 1.00), ridge_at(NEAR, x0))
        drop = 0.30 + 0.22 * t
        pg.line(ill(x0, y0), ill(x0 + 0.055, max(0.0, y0 - drop)),
                decorative=True, **stroke(1.3, color="black", cap="round"))

    # West face: three long contours parallel to the ascending ridge — the same
    # mark at a different rhythm, so the two faces read as one drawing.
    for i in range(1, 4):
        off = 0.16 * i
        pg.polyline([ill(x, max(0.0, y - off)) for x, y in NEAR
                     if x <= SUMMIT_X and y - off > 0.02],
                    fill="none", decorative=True,
                    **stroke(1.3, color="black", join="round", cap="round"))

    # the ground line the whole illustration stands on
    pg.rect([FRONT_L, ILL_B, LIVE_W, 3.4], fill="black", decorative=True)

    # ------------------------------------------------------------------ #
    # §9 · Front foot: subtitle over author, both flush-left (C26/C27)
    # ------------------------------------------------------------------ #
    pg.text([FRONT_L, row_y(7) + 6, LIVE_W, 26], SUBTITLE,
            id="front-subtitle", style="subtitle", overlap="allowed")
    pg.text([FRONT_L, row_y(7) + 34, LIVE_W, 56], AUTHOR,
            id="front-author", style="author", overlap="allowed")

    # ------------------------------------------------------------------ #
    # §10 · Spine (C26) — reads top-to-bottom, the Anglo-American convention.
    #       ObjBase.rotation is ignored by the SVG renderer, so the rotation
    #       has to come from a transformed frame.
    # ------------------------------------------------------------------ #
    pg.layer("spine")
    spine_cx = SPINE_X + SPINE_W / 2
    # `frame()` would build the same transform but takes no object fields, so
    # its group could not carry an id and tripped A11Y-4. `grouped()` is the
    # same lowering with the fields exposed.
    spine_tf = Mat3.translate(spine_cx, TRIM_T + SAFE) @ Mat3.rotate(90)
    with pg.grouped(transform=spine_tf, id="spine") as sp:
        run = PANEL_H - 2 * SAFE
        # local +x runs DOWN the spine, local +y runs LEFT across its width.
        # The three runs get explicit non-overlapping bands: sizing them as
        # fractions of `run` let the author band collide with the imprint.
        sp.text([0, -SPINE_W / 2, 330, SPINE_W], "THE TOUR",
                id="spine-title", style="spineTitle")
        sp.text([356, -SPINE_W / 2, 250, SPINE_W], AUTHOR,
                id="spine-author", style="spineAuthor")
        sp.text([run - 140, -SPINE_W / 2, 140, SPINE_W], IMPRINT,
                id="spine-imprint", style="spineImprint")

    # ------------------------------------------------------------------ #
    # §11 · Back panel (C24/C26/C27)
    # ------------------------------------------------------------------ #
    pg.layer("back")
    from frameforge.sdk.metrics import wrap_text

    MEASURE = 430.0                    # px -> ~65 characters at 13.2 px Archivo
    LEAD = S_BODY * BODY_LH
    y = LIVE_T

    pg.text([BACK_L, y, LIVE_W, 84], BACK_HOOK, id="back-hook", style="hook")
    y += 96
    pg.rect([BACK_L, y, LIVE_W, 2.4], fill="black", decorative=True)
    y += 30

    # Author-time measurement and the rasterizer do NOT agree to the line here:
    # fc-match resolves Archivo's DEFAULT variable instance (wght 600) while the
    # renderer draws the wght-400 instance this style asks for. Handing whole
    # paragraphs to the renderer therefore gives a line count this client cannot
    # predict — which first LOST a line of copy and then ate the paragraph gaps.
    # A press file cannot be host-dependent (O16), so the wrap is resolved here:
    # break to BREAK_W, set each line in its own box at BOX_W, and the 13 %
    # safety band means no line can re-wrap however the rasterizer measures it.
    BREAK_W, BOX_W = 405.0, 460.0
    for i, para in enumerate(BACK_BODY):
        lines = wrap_text(para, width=BREAK_W, font_family=GROTESK,
                          font_size=S_BODY, variation_settings=BOOK_NORM)
        with pg.grouped(id=f"back-body-{i}") as para_group:
            for n, ln in enumerate(lines):
                # consecutive lines of set copy overlap in ink extent by
                # design; the audit's remedy for intentional overlap is the
                # explicit consent, not extra leading
                para_group.text([BACK_L, y + n * LEAD, BOX_W, LEAD], ln,
                                style="body", overlap="allowed")
        y += len(lines) * LEAD + 16

    # Foot of the back panel, stacked bottom-up so nothing has to be guessed:
    # colophon on the trim-safe line, imprint above it, and the ISBN symbol
    # above BOTH. Sitting the barcode beside them instead put the full-measure
    # colophon underneath the digits — a real collision, not a false positive.
    COLOPHON_Y = LIVE_B - 16
    IMPRINT_Y = COLOPHON_Y - 30
    HRI_BOTTOM = IMPRINT_Y - 6

    # ------------------------------------------------------------------ #
    # §12 · The ISBN symbol (O16) — bars emitted from the encoders in §3.
    #       Black on yellow scans: red-illumination scanners see yellow as a
    #       light substrate, so the two-value system survives the barcode.
    # ------------------------------------------------------------------ #
    modules, code13 = ean13_modules(ISBN12)
    if decode_ean13(modules) != code13:                 # PALS: verify, don't trust
        raise AssertionError("EAN-13 encode/decode round trip failed")
    addon = ean5_modules(PRICE5)

    sym_w = len(modules) * BAR_MODULE
    gap = 10 * BAR_MODULE
    total_w = sym_w + gap + len(addon) * BAR_MODULE
    bx = BACK_R - total_w
    HRI_BOX_H = 18
    by = HRI_BOTTOM - HRI_BOX_H + 4 - BAR_H - GUARD_EXTRA

    isbn_pretty = (f"ISBN {code13[:3]}-{code13[3]}-{code13[4:10]}-"
                   f"{code13[10:12]}-{code13[12]}")
    pg.text([bx, by - 30, total_w, 20], isbn_pretty, id="back-isbn",
            style="isbnText")

    def bars(mstring, x0, y0, height, *, long_at=()):
        """Emit one rect per run of '1' modules; `long_at` names module indices
        whose bars extend below the digit line (guards)."""
        i = 0
        while i < len(mstring):
            if mstring[i] == "0":
                i += 1
                continue
            j = i
            while j < len(mstring) and mstring[j] == "1":
                j += 1
            extra = GUARD_EXTRA if any(i <= k < j for k in long_at) else 0.0
            # the guards run PAST the digit line by design — that descender is
            # part of the symbol, so its overlap with the HRI is declared
            pg.rect([x0 + i * BAR_MODULE, y0, (j - i) * BAR_MODULE,
                     height + extra], fill="black", decorative=True,
                    overlap="allowed")
            i = j

    guards = tuple(range(0, 3)) + tuple(range(45, 50)) + tuple(range(92, 95))
    bars(modules, bx, by, BAR_H, long_at=guards)

    # human-readable interpretation: lead digit outside, then 6 + 6 under halves
    hri_y = by + BAR_H + GUARD_EXTRA - 4
    pg.text([bx - 15 * BAR_MODULE, hri_y, 13 * BAR_MODULE, HRI_BOX_H],
            code13[0], id="hri-lead", style="hriLead", overlap="allowed")
    pg.text([bx + 3 * BAR_MODULE, hri_y, 42 * BAR_MODULE, HRI_BOX_H],
            code13[1:7], id="hri-left", style="hri", overlap="allowed")
    pg.text([bx + 50 * BAR_MODULE, hri_y, 42 * BAR_MODULE, HRI_BOX_H],
            code13[7:], id="hri-right", style="hri", overlap="allowed")

    # the foot lines, now clear of the symbol above them
    pg.text([BACK_L, IMPRINT_Y, 320, 28], IMPRINT,
            id="back-imprint", style="imprint")
    pg.text([BACK_L, COLOPHON_Y, 430, 16], COLOPHON,
            id="back-colophon", style="colophon")

    # the EAN-5 add-on: shorter bars, digits ABOVE the symbol
    ax = bx + sym_w + gap
    add_h = BAR_H * 0.76
    add_y = by + (BAR_H - add_h)
    bars(addon, ax, add_y, add_h)
    pg.text([ax, add_y - 19, len(addon) * BAR_MODULE, 16], PRICE5,
            id="hri-addon", style="hriSmall")

    # ------------------------------------------------------------------ #
    # §13 · Press marks (O16) — fold ticks at the two spine folds and crop
    #       ticks at the trim corners, all drawn inside the bleed so they are
    #       cut away on the guillotine.
    # ------------------------------------------------------------------ #
    pg.layer("marks")
    TICK, MW = 8.0, 0.6
    for fold in (SPINE_X, FRONT_X):
        for y0 in (BLEED - TICK - 1, TRIM_B + 1):
            pg.rect([fold - MW / 2, y0, MW, TICK], fill="black", decorative=True)
    for x0 in (BACK_X, BACK_X + PANEL_W * 2 + SPINE_W):
        for y0 in (TRIM_T, TRIM_B):
            pg.rect([x0 - (TICK if x0 > W / 2 else 0), y0 - MW / 2, TICK, MW],
                    fill="black", decorative=True)
    for y0 in (TRIM_T, TRIM_B):
        for x0 in (BACK_X, BACK_X + PANEL_W * 2 + SPINE_W):
            pg.rect([x0 - MW / 2, y0 - (TICK if y0 > H / 2 else 0), MW, TICK],
                    fill="black", decorative=True)

    return d


if __name__ == "__main__":
    from frameforge.sdk.chevreul import contrast_ratio
    from frameforge.sdk.validate import validate_static_rules

    ratio = contrast_ratio(BLACK, YELLOW)
    print(f"C31 proof: {BLACK} on {YELLOW} = {ratio:.2f}:1 "
          f"(max possible 21.00:1)")
    mods, code = ean13_modules(ISBN12)
    print(f"O16 proof: EAN-13 {code} -> {len(mods)} modules, "
          f"decoded back as {decode_ean13(mods)}")

    out = os.path.join(ROOT, "_tmp", "the-tour-jacket")
    os.makedirs(out, exist_ok=True)
    doc = build()
    report = validate_static_rules(doc.build_dict())
    for issue in report.issues:
        print(f"{issue.severity:8} {issue.rule_id}: {issue.message}")
    print(f"static rules: {'ok' if report.ok else 'FAILED'} "
          f"({len(report.issues)} issue(s))")
    path = os.path.join(out, "the-tour-jacket.fg.yaml")
    doc.write(path)
    print(f"wrote {path}")
