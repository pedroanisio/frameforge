#!/usr/bin/env python3
"""Recreate ``img13_live_event_band_poster`` — a psychedelic vintage-style gig
poster — from its orthogonal-dimension profile in ``_tmp/temp_model.json``.

The profile is an *assessment*, not a graphic model: the source image is not in
this repository, so this client is a reconstruction driven only by the 22 scored
dimensions. Each construction names the dimension it discharges:

  A1  Intricate        dense ray field + curved type throughout
  A2  Radial/periodic  N evenly spaced wedges set one angular rhythm
  A5  Idiom-coded      psychedelic / vintage rock-poster idiom
  A6  Energetic        motion-suggestive rays converging on the eye
  A8  Curved stripes   arched text bands weaving down both flanks
  C2  Focal hierarchy  one event, layered supporting detail
  C3  Radial/symmetric black sunburst from a top eye, widening downward
  C4  Strong focal     the eye and the outlined BAND dominate
  C5  Moderate density sparse core message amid repeated small flavour text
  C18 Slab display     Roboto Slab Bold, drawn as real outlines
  C20 Heavy/black      the display anchors the centre
  C26 Layered roles    title / display / subtitle / CTA / footer / flavour
  C27 Centred + curved symmetrical axis, arched baselines on the flanks
  C28 Near-duotone     cream + ink, ONE polychrome accent (the iris)
  C29 Light/dark       cream field, black rays
  C30 One vivid accent the iris is the only saturated element in the poster
  C31 Extreme contrast measured, see COLOUR_PROOF
  C32 Simplified       flat graphic sunburst, stylised eye
  C33 Ornamented       rays and arched type are decorative devices
  C34 Vernacular       gig-poster register
  C35 Theatrical       loud, hypnotic
  C36 Iconic+symbolic  the radiant all-seeing eye

PLACEHOLDER CONTENT. Band name, venue, date and ticket copy are invented; the
profile's own label ("LIVE EVENT / BAND") is treated as the literal headline,
which is how the source reads as a template.

Run from the repository root::

    uv run python static/examples/live_event_band_poster.py
    DOC=_tmp/live-event-poster/live-event-band-poster.fg.yaml
    uv run python tooling/frameforge_render.py $DOC --to svg --out _tmp/live-event-poster
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.rendering.infrastructure.font_metrics import get_font_metrics  # noqa: E402
from frameforge.sdk import DocumentBuilder  # noqa: E402
from frameforge.sdk.paint import radial_gradient, stroke  # noqa: E402
from frameforge.sdk.pathtext import text_on_path  # noqa: E402

# --------------------------------------------------------------------------- #
# §1 · Sheet — an 18 x 24 in poster authored at 72 px/in
# --------------------------------------------------------------------------- #
PPI = 72.0
W, H = int(18 * PPI), int(24 * PPI)        # 1296 x 1728
MX = 84                                     # side margin for the type stack

EYE_X, EYE_Y = W / 2, 470                   # the apex everything radiates from
RAY_R = 2400                                # past the far corner (1415 px away)

# --------------------------------------------------------------------------- #
# §2 · Ink — two values plus exactly one polychrome accent (C28/C30/C31)
# --------------------------------------------------------------------------- #
CREAM = "#F2E7CE"
INK = "#12100C"
COLOUR_PROOF = 15.47                        # ink-on-cream, measured in __main__

# The iris is the ONLY saturated element on the sheet (C30). A conic sweep
# lowers to a radial approximation in the SVG proxy, so the iris is authored as
# a real radial ramp: concentric bands are what an iris looks like anyway.
IRIS = [("#E23B2E", 0.0), ("#EE8B21", 0.18), ("#F2C300", 0.36),
        ("#3FA34D", 0.55), ("#2C7FB8", 0.74), ("#6A3FA0", 0.90),
        ("#6A3FA0", 1.0)]

SLAB = ["Roboto Slab", "Georgia", "serif"]
SLAB_CHAIN = "Roboto Slab, Georgia, serif"

# Flavour text repeated down the flanks — the "curved striped texture" (A8/C5).
# Held at several lengths because the usable arc shrinks as the rings grow: the
# longest phrase that fits each band is chosen at build time (`fit_phrase`).
FLAVOUR = [
    "ALL SEEING · ALL HEARING · ALL NIGHT",
    "TURN IT UP UNTIL THE WALLS COMPLAIN",
    "ONE NIGHT ONLY · NO ENCORES PROMISED",
    "BRING EARPLUGS · THEN IGNORE THEM",
    "LOUD · LOUDER · LOUDEST",
    "NO ENCORES PROMISED",
    "ONE NIGHT ONLY",
    "ALL SEEING",
]

TITLE = "LIVE EVENT"
DISPLAY = "BAND"
SUBTITLE = "AN EVENING OF AMPLIFIED SOUND"
CTA = "TICKETS ON SALE NOW"
FOOT_1 = "SAT 27 SEPT · THE ELECTRIC HALL"
FOOT_2 = "DOORS 8 PM · SUPPORT: THE LESSER LIGHTS · STRICTLY 18+"


# --------------------------------------------------------------------------- #
# §3 · Outlined display type (C18/C20)
# --------------------------------------------------------------------------- #
# The SVG text painter emits `font-family;font-size;fill` and nothing else — no
# stroke, no paint-order — so a *stroked* text object silently loses its
# outline. Chunky outlined letterforms therefore have to be real geometry: the
# glyphs are pulled as outlines from the SAME font file fc-match resolves for
# the rasterizer (FontMetrics.source_path), so they cannot drift from type set
# in that family elsewhere on the sheet.
def _glyph_source():
    metrics = get_font_metrics(SLAB_CHAIN, bold=True)
    path = getattr(metrics, "source_path", None)
    if not path:
        raise RuntimeError(f"cannot resolve a font file for {SLAB_CHAIN!r}")
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    font = TTFont(path)
    return font, font.getGlyphSet(), font.getBestCmap(), \
        font["head"].unitsPerEm, font["hmtx"], SVGPathPen, TransformPen


def outlined_word(text, *, size, cx, baseline, tracking=0.0):
    """Return (path-d list, total width) for `text` set as filled outlines,
    horizontally centred on `cx` and sitting on `baseline`."""
    _font, glyphs, cmap, upm, hmtx, SVGPathPen, TransformPen = _glyph_source()
    scale = size / upm
    names = [cmap[ord(ch)] for ch in text if ord(ch) in cmap]
    advances = [hmtx[n][0] * scale for n in names]
    total = sum(advances) + tracking * max(0, len(names) - 1)

    ds, pen_x = [], cx - total / 2.0
    for name, adv in zip(names, advances):
        pen = SVGPathPen(glyphs)
        # (xx, xy, yx, yy, dx, dy) — the y flip takes font units (y up) to
        # page coordinates (y down); baking the transform into the path data
        # keeps the stroke width in page px instead of scaling with the glyph
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, pen_x, baseline)))
        d = pen.getCommands()
        if d.strip():
            ds.append(d)
        pen_x += adv + tracking
    return ds, total


# --------------------------------------------------------------------------- #
# §4 · Geometry helpers
# --------------------------------------------------------------------------- #
def polar(cx, cy, r, deg):
    """Screen-space polar: 0 deg = +x, 90 deg = straight DOWN (+y)."""
    a = math.radians(deg)
    return [cx + r * math.cos(a), cy + r * math.sin(a)]


def arc_points(cx, cy, r, a0, a1, steps=64):
    return [polar(cx, cy, r, a0 + (a1 - a0) * i / steps) for i in range(steps + 1)]


def arc_band_d(cx, cy, r_in, r_out, a0, a1, steps=64):
    """Annulus-sector path: out along the outer arc, back along the inner."""
    outer = arc_points(cx, cy, r_out, a0, a1, steps)
    inner = arc_points(cx, cy, r_in, a1, a0, steps)
    pts = outer + inner
    head = f"M{pts[0][0]:.2f},{pts[0][1]:.2f}"
    body = "".join(f"L{x:.2f},{y:.2f}" for x, y in pts[1:])
    return head + body + "Z"


def band_window(r, *, x_limit, y_limit, a_max, keep_out):
    """Angular window (deg) in which a ring of radius `r` is usable.

    Three constraints, all derived rather than eyeballed:
      * `x_limit`  — the ring is off the sheet until ``acos(x_limit / r)``;
      * `y_limit`  — it must stop before the subtitle bar;
      * `keep_out` — ``(half_width, dy_top, dy_bottom)`` of the display block.
        A ring enters that block once it is BOTH low enough and near enough to
        the axis, so the window closes at the first angle where both hold.

    Without these every ring got the same range: the big ones ran off the right
    edge with their type sliced mid-word, and the small ones swept straight
    through BAND, leaving fragments of flavour text inside its counters.
    Returns ``None`` when nothing usable is left, so a ring is skipped rather
    than emitted broken."""
    a0, a1 = 4.0, a_max
    if r > x_limit:                          # ring is wider than the half-sheet
        a0 = max(a0, math.degrees(math.acos(min(1.0, x_limit / r))))
    if r > y_limit:                          # ring reaches below the type stack
        a1 = min(a1, math.degrees(math.asin(min(1.0, y_limit / r))))

    half, dy_top, dy_bot = keep_out
    if r > dy_top:
        low = math.degrees(math.asin(min(1.0, dy_top / r)))          # low enough
        near = math.degrees(math.acos(min(1.0, half / r))) if r > half else 0.0
        enter = max(low, near)
        leaves = (math.degrees(math.asin(min(1.0, dy_bot / r)))
                  if r > dy_bot else 90.0)
        if enter <= leaves:
            a1 = min(a1, enter)

    return (a0, a1) if a1 - a0 >= 12.0 else None


def phrase_width(phrase, *, size, track):
    """Set width of `phrase` the way ``text_on_path`` will actually lay it."""
    from frameforge.sdk.metrics import measure_text
    return (measure_text(phrase, font_family=SLAB_CHAIN, font_size=size)
            + track * len(phrase))


def fit_phrase(candidates, arc_px, *, size, track):
    """First candidate (in the caller's order) whose set width fits `arc_px`,
    or ``None`` when even the shortest overruns the arc.

    First-fit, not longest-fit: the caller rotates the phrase list per band so
    the flanks vary, and picking the globally longest phrase would silently
    discard that rotation and repeat one line all over the sheet. Returning
    ``None`` rather than the shortest candidate matters too — falling back to a
    phrase that does not fit is what put half-words ("ALL SEEIN") on the short
    outer bands."""
    for phrase in candidates:
        if phrase_width(phrase, size=size, track=track) <= arc_px:
            return phrase
    return None


def build():
    d = DocumentBuilder(title="LIVE EVENT / BAND — gig poster")
    d.describe(
        "Psychedelic vintage gig poster: a black sunburst radiating from a "
        "radiant all-seeing eye down a widening beam, arched flavour-text "
        "bands weaving down both flanks, and an outlined slab display at the "
        "centre. Two ink values plus a single rainbow iris.")
    d.meta(reconstruction={
        "source_profile": "img13_live_event_band_poster",
        "source_model": "_tmp/temp_model.json",
        "basis": "22 scored orthogonal dimensions; the reference image is NOT "
                 "in this repository — geometry and copy are inferred",
        "placeholder": "band name, venue, date and ticket copy are invented",
    }, sheet={"size_in": [18, 24], "ppi": PPI,
              "inks": 2, "accent": "single radial rainbow iris",
              "contrast_ink_on_cream": COLOUR_PROOF})

    d.define_color("cream", CREAM)
    d.define_color("ink", INK)

    def ts(name, **style):
        d.define_text_style(name, font_family=SLAB, **style)

    # C26 — the layered roles
    ts("subtitle", font_size=34, font_weight=700, color="cream",
       letter_spacing=5.5, align="center")
    ts("cta", font_size=41, font_weight=700, color="ink",
       letter_spacing=3.4, align="center")
    ts("footA", font_size=30, font_weight=700, color="cream",
       letter_spacing=4.0, align="center")
    ts("footB", font_size=19, font_weight=400, color="cream",
       letter_spacing=2.6, align="center")

    pg = d.page(
        "poster",
        canvas={"size": [W, H], "units": "px"},
        reading_order=["title", "display", "subtitle", "cta", "foot-a", "foot-b"],
    )

    # ---------------------------------------------------------------- #
    # §5 · Ground + sunburst (C3/C29/A2/C32)
    # ---------------------------------------------------------------- #
    pg.layer("ground")
    pg.rect([0, 0, W, H], fill="cream", decorative=True)

    pg.layer("rays")
    # One angular rhythm: N wedges of equal width, equally spaced, over a
    # downward fan. The apex sits high and the wedges run past the corners, so
    # the black mass reads as a triangular beam widening toward the foot.
    N_RAYS, A0, A1, DUTY = 23, 3.0, 177.0, 0.46
    pitch = (A1 - A0) / N_RAYS
    for i in range(N_RAYS):
        a = A0 + i * pitch
        half = pitch * DUTY / 2.0
        pg.polygon([[EYE_X, EYE_Y],
                    polar(EYE_X, EYE_Y, RAY_R, a - half),
                    polar(EYE_X, EYE_Y, RAY_R, a + half)],
                   fill="ink", decorative=True, overlap="allowed")

    # ---------------------------------------------------------------- #
    # §6 · Arched flavour bands down both flanks (A8/C27/C33/C5)
    # ---------------------------------------------------------------- #
    pg.layer("flanks")
    BAND_T = 52                                   # band thickness
    RADII = [520, 650, 780, 910]
    X_LIMIT = W / 2 - 26                          # keep the ring on the sheet
    Y_LIMIT = 1104 - EYE_Y                        # and clear of the subtitle bar
    KEEP_OUT = (500.0, 815 - EYE_Y, 1104 - EYE_Y)  # the BAND block to avoid
    TRACK, FLAVOUR_SIZE = 2.2, 22.0

    for ring, r in enumerate(RADII):
        window = band_window(r, x_limit=X_LIMIT, y_limit=Y_LIMIT, a_max=66.0,
                             keep_out=KEEP_OUT)
        if window is None:
            continue
        wa0, wa1 = window
        # the outer rings get a shorter usable arc, so they step the type down
        # a notch rather than being dropped
        size = FLAVOUR_SIZE - 1.6 * ring
        for flank in (0, 1):
            # flank 1 is the mirror of flank 0 about the vertical axis
            fa0, fa1 = (wa0, wa1) if flank == 0 else (180.0 - wa1, 180.0 - wa0)

            # the left flank is walked backwards so its glyphs stay upright
            a_start, a_end = (fa0 + 2, fa1 - 2) if flank == 0 else (fa1 - 2, fa0 + 2)
            arc_px = r * math.radians(abs(a_end - a_start))
            rot = (ring + flank) % len(FLAVOUR)
            phrase = fit_phrase(FLAVOUR[rot:] + FLAVOUR[:rot], arc_px,
                                size=size, track=TRACK)
            if phrase is None:
                continue          # no phrase fits: emit no band either

            r_in, r_out = r - BAND_T / 2, r + BAND_T / 2
            # cream band knocked out of the black rays; the text then reads in
            # ink whatever the ray field underneath happens to be doing
            pg.path(arc_band_d(EYE_X, EYE_Y, r_in, r_out, fa0, fa1),
                    fill="cream", decorative=True, overlap="allowed",
                    **stroke(3.0, color=INK, join="round"))

            # centre the run in the band instead of starting hard at its lip
            s0 = max(0.0, (arc_px - phrase_width(phrase, size=size,
                                                 track=TRACK)) / 2.0)
            pts = arc_points(EYE_X, EYE_Y, r, a_start, a_end, 96)
            glyphs = text_on_path(pts, phrase, size=size, family=SLAB,
                                  weight=700, color=INK, track=TRACK,
                                  offset=0.0, s0=s0, overlap="allowed",
                                  decorative=True)
            # text_on_path sizes each glyph box at 1.35x the font size, just
            # under the renderer's ~1.40x silent-clip floor, so glyphs drop out
            # at random. Grow every box clear of the floor before emitting.
            for g in glyphs:
                gx, gy, gw, gh = g["box"]
                grow = size * 0.30
                g["box"] = [gx, gy - grow / 2, gw, gh + grow]
            with pg.lettering():
                pg.extend(glyphs)

    # ---------------------------------------------------------------- #
    # §7 · The radiant eye (C36/C4/C30/C32)
    # ---------------------------------------------------------------- #
    pg.layer("eye")
    EW, EH = 214, 116                              # almond half-width / half-height
    # a cream almond knocked out of the rays, drawn as two symmetric arcs
    lid = (f"M{EYE_X - EW:.1f},{EYE_Y:.1f} "
           f"Q{EYE_X:.1f},{EYE_Y - EH * 2:.1f} {EYE_X + EW:.1f},{EYE_Y:.1f} "
           f"Q{EYE_X:.1f},{EYE_Y + EH * 2:.1f} {EYE_X - EW:.1f},{EYE_Y:.1f} Z")
    pg.path(lid, fill="cream", decorative=True, overlap="allowed",
            **stroke(11, color=INK, join="round"))

    IRIS_R = 84
    pg.circle([EYE_X, EYE_Y], IRIS_R, decorative=True, overlap="allowed",
              fill=radial_gradient(IRIS, at="50% 50%", shape="circle"))
    pg.circle([EYE_X, EYE_Y], IRIS_R, fill="none", decorative=True,
              overlap="allowed", **stroke(7, color=INK))
    pg.circle([EYE_X, EYE_Y], 34, fill="ink", decorative=True, overlap="allowed")

    # short lashes: the eye radiates too, at the same angular rhythm as the rays
    for i in range(19):
        a = 186.0 + i * (168.0 / 18)
        p0 = polar(EYE_X, EYE_Y, EW * 0.62, a)
        p1 = polar(EYE_X, EYE_Y, EW * 0.62 + 46, a)
        pg.line([p0[0], EYE_Y - (EYE_Y - p0[1]) * 0.55],
                [p1[0], EYE_Y - (EYE_Y - p1[1]) * 0.95],
                decorative=True, overlap="allowed",
                **stroke(7, color=INK, cap="round"))

    # ---------------------------------------------------------------- #
    # §8 · The centred type stack (C2/C4/C20/C26/C27)
    # ---------------------------------------------------------------- #
    pg.layer("type")

    def outlined(text, *, size, baseline, tracking, oid, weight=17):
        ds, total = outlined_word(text, size=size, cx=W / 2,
                                  baseline=baseline, tracking=tracking)
        for n, dd in enumerate(ds):
            pg.path(dd, fill="cream", id=(oid if n == 0 else None),
                    overlap="allowed", decorative=(n != 0),
                    **stroke(weight, color=INK, join="round"))
        return total

    # The outline weight has to stay well under the stem width or it closes the
    # counters: at 104 px a 15 px stroke turned LIVE EVENT into a black slug,
    # because half of it grows inward. These are ~7 % of the cap height.
    outlined(TITLE, size=112, baseline=776, tracking=7, oid="title", weight=8)
    outlined(DISPLAY, size=316, baseline=1062, tracking=10, oid="display",
             weight=16)

    # subtitle sits on its own ink bar so it reads over the ray field
    pg.rect([0, 1124, W, 74], fill="ink", decorative=True, overlap="allowed")
    pg.text([MX, 1136, W - 2 * MX, 52], SUBTITLE, id="subtitle", style="subtitle")

    # CTA — a cream plate with a heavy rule, the one affordance on the sheet
    cta_box = [W / 2 - 330, 1268, 660, 96]
    pg.rect(cta_box, fill="cream", decorative=True, overlap="allowed",
            **stroke(9, color=INK, join="round"))
    pg.text([cta_box[0], cta_box[1] + 20, cta_box[2], 58], CTA,
            id="cta", style="cta", overlap="allowed")

    # ---------------------------------------------------------------- #
    # §9 · Footer (C26) — a full-bleed ink bar closing the sheet
    # ---------------------------------------------------------------- #
    pg.layer("footer")
    pg.rect([0, 1536, W, H - 1536], fill="ink", decorative=True,
            overlap="allowed")
    pg.rect([MX, 1560, W - 2 * MX, 4], fill="cream", decorative=True,
            overlap="allowed")
    pg.text([MX, 1594, W - 2 * MX, 50], FOOT_1, id="foot-a", style="footA")
    pg.text([MX, 1654, W - 2 * MX, 34], FOOT_2, id="foot-b", style="footB")

    return d


if __name__ == "__main__":
    from frameforge.sdk.chevreul import contrast_ratio
    from frameforge.sdk.validate import validate_static_rules

    print(f"C31 proof: {INK} on {CREAM} = {contrast_ratio(INK, CREAM):.2f}:1 "
          f"(max possible 21.00:1)")
    m = get_font_metrics(SLAB_CHAIN, bold=True)
    print(f"C18 proof: display outlines drawn from {m.source_path}")

    out = os.path.join(ROOT, "_tmp", "live-event-poster")
    os.makedirs(out, exist_ok=True)
    doc = build()
    report = validate_static_rules(doc.build_dict())
    for issue in report.issues:
        print(f"{issue.severity:8} {issue.rule_id}: {issue.message}")
    print(f"static rules: {'ok' if report.ok else 'FAILED'} "
          f"({len(report.issues)} issue(s))")
    path = os.path.join(out, "live-event-band-poster.fg.yaml")
    doc.write(path)
    print(f"wrote {path}")
