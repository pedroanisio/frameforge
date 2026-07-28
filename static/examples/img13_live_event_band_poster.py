#!/usr/bin/env python3
"""Compose ``img13_live_event_band_poster`` — a psychedelic vintage-style gig
poster — from its Orthogonal-Dimension-Framework profile.

PROVENANCE AND EPISTEMIC STATUS
-------------------------------
The input is an *assessment profile*, not a graphic model. It scores 22 of the
84 registry dimensions (completion ratio 0.2619) for a source image that is NOT
in this repository. This client is therefore a **specified reconstruction**: the
22 scored dimensions are the whole brief, and everything the profile does not
score (band name, venue, dates, ticket price, exact proportions) is INVENTED
placeholder content. The profile's own label — "LIVE EVENT / BAND" — is treated
as the literal headline, which is how the source reads as a template.

  profile   _tmp/temp_model.json → profiles.img13_live_event_band_poster
            (identical to the copy previously held in _tmp/set-02.json)
  registry  _tmp/orthogonal-dimension-framework-rev2.md
            sha256 3966b0501e0ffb8005565c5bd291f8b7204c4ff76a69cb82ba32779e045b5bcd
            — verified against the sha256 the profile file itself records.

Nothing below claims to reproduce the source pixels; there are no source pixels
to compare against. What it does claim is that every construction discharges a
named, scored dimension, and that the numeric claims (contrast, angular period,
measure) are MEASURED at build time and printed, not asserted.

THE 22 SCORED DIMENSIONS AND WHAT DISCHARGES EACH
-------------------------------------------------
  A1  perceptual complexity   4  §4 ray field + §8 arched flank type
  A2  spatial rhythm          4  §4 ONE angular period drives halo and beam
  A5  cultural coding         3  psychedelic / vintage rock-poster idiom
  A6  emotional valence       3  §5 radiant eye, converging rays (hypnotic)
  A8  typographic texture     3  §8 concentric arched bands down both flanks
  C2  information topology    3  §6-§7 one event, layered supporting detail
  C3  layout topology         4  §4 radial burst + downward triangular beam
  C4  salience distribution   4  §5 eye and §6 BAND are the only two focals
  C5  information density     3  sparse core message, dense small flavour text
  C18 typeface construction   3  Roboto Slab (slab) vs Fira Sans Cond (grotesque)
  C20 type weight             4  §6 mass from stroke, not from a missing weight
  C26 role differentiation    4  §2 seven typographic roles, each distinct
  C27 alignment model         3  §2 one centred axis + §8 curved baselines
  C28 hue                     4  §1 cream + ink duotone, ONE polychrome accent
  C29 lightness               4  §1 light ground, dark rays
  C30 chroma                  3  §5 the iris is the only chromatic element
  C31 relational contrast     5  §1 MEASURED, printed as COLOUR PROOF
  C32 abstraction level       4  §5 flat schematic eye, no rendered volume
  C33 ornamentation           4  §4 rays, §9 corner stars, §2 rules
  C34 formality               3  vernacular gig-poster register
  C35 expressive intensity    4  theatrical scale contrast
  C36 mode of reference       3  radiant all-seeing eye: iconic + symbolic

Run from the repository root::

    uv run python static/examples/img13_live_event_band_poster.py

which writes ``_tmp/img13-live-event-poster/img13-live-event-band-poster.fg.yaml``
and prints the measured proofs. Render it with::

    uv run python tooling/frameforge_render.py \\
        _tmp/img13-live-event-poster/img13-live-event-band-poster.fg.yaml \\
        --to svg --out _tmp/img13-live-event-poster
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import DocumentBuilder                      # noqa: E402
from frameforge.sdk.chevreul import contrast_ratio              # noqa: E402
from frameforge.sdk.clip import clip_polygon                    # noqa: E402
from frameforge.sdk.metrics import measure_text                 # noqa: E402
from frameforge.sdk.paint import stroke                         # noqa: E402
from frameforge.sdk.pathtext import path_length, text_on_path   # noqa: E402

REGISTRY_SHA256 = "3966b0501e0ffb8005565c5bd291f8b7204c4ff76a69cb82ba32779e045b5bcd"

# --------------------------------------------------------------------------- #
# §0 · Sheet, palette, faces
# --------------------------------------------------------------------------- #
# 12 x 18 in at 100 px/in — the classic screen-printed gig-poster format.
W, H = 1200, 1800

# C28 hue · C29 lightness · C30 chroma.
# Near-duotone: a warm paper cream and a warm screen-printing ink, plus exactly
# ONE polychrome element (the iris). Nothing else in the poster is chromatic.
CREAM = "#F2E6CB"
INK = "#141110"
#
# The iris is drawn as twelve real pie sectors, NOT as a conic gradient: the
# renderer reports `gradient_conic_fallback` (no native SVG conic primitive, so
# a conic is approximated by a radial) and the ramp collapses to a single hue —
# which would silently delete the one thing C30/C28 score. Flat sectors also sit
# better with C32 "simplified / schematic" (scored 4).
IRIS_WHEEL = [
    "#D8322C", "#E2542A", "#EE8A21", "#F2B024", "#F0C92C", "#C9C932",
    "#8FBB3E", "#3E9F55", "#2E8C7E", "#2E63AE", "#4A4CA0", "#6F3C9B",
]

# C18 typeface construction. Two constructions, deliberately opposed:
#   SLAB  — Roboto Slab, the display voice (bracketed slab serifs).
#   GROT  — Fira Sans Condensed, the grotesque voice for the information block.
# HONEST LIMIT: the resolvable Roboto Slab family ships Thin/Light/Regular/Bold
# only, so C20 "heavy / black display" (scored 4) cannot come from a 900 weight —
# a synthesized one would be a lie about the face. §6 buys the mass with a real
# outline stroke instead, which is also what the profile actually observed
# ("chunky OUTLINED display letterforms").
SLAB = "Roboto Slab"
GROT = "Fira Sans Condensed"
GROT_HEAVY = "Fira Sans Condensed Heavy"

# C26 role differentiation (scored 4) needs distinct roles, not distinct sizes.
# Seven roles ride a SIX-step scale; the renderer's design census enforces the
# budget, and every near-duplicate size was collapsed onto the step below.
S_META = 20.0     # address, small print, flank flavour
S_LABEL = 26.0    # presenter, lineup, doors
S_LEDE = 32.0     # CTA, venue
S_KICK = 54.0     # the arched kicker
S_DATE = 84.0     # the date — the second-loudest voice
S_FLAVOUR = S_META

# --------------------------------------------------------------------------- #
# §0.1 · The one angular rhythm (A2) and the beam it cuts (C3)
# --------------------------------------------------------------------------- #
EX, EY = 600.0, 470.0          # the eye: origin of every ray in the poster
RAYS = 44                      # A2: ONE period, shared by halo and beam
PERIOD = 360.0 / RAYS
DUTY = 0.46                    # black fraction of each period
HALO_R0, HALO_R1 = 148.0, 286.0
IRIS_R = 86.0
BEAM_HALF = 34.0               # half-angle of the triangular beam
BEAM_R = 2600.0                # rays overshoot; the clip cuts the triangle
SOLID_Y = 960.0                # below this row the rays close into a solid field

# The beam triangle: apex at the eye, sides at +/- BEAM_HALF, running off the
# bottom edge so the black bleeds into the two bottom corners.
_dx = (H - EY) * math.tan(math.radians(BEAM_HALF))
BEAM_TRI = [(EX, EY), (EX - _dx, float(H)), (EX + _dx, float(H))]

# §6 keep-out: the display's ink footprint, which the §8 flank bands must not
# cross. Derived from the measured type, not guessed — see build().
DISPLAY_TOP = 960.0
DISPLAY_TRACK = 18.0
DISPLAY_MARGIN = 26.0          # clear cream either side of the set word
# DISPLAY_SIZE is not a constant: it is FITTED to the solid field below, once
# the copy and the real bold metrics are both known.
# An INLINE, not an outline: with SVG's default paint order the stroke lands on
# top of the fill, so half its width eats into the cream letter and half falls
# outside onto matching ink — a dark keyline hugging the letterform's inner
# edge, which is the "chunky outlined display letterform" the profile observed.
DISPLAY_STROKE = 16.0
FLANK_INSET = 26.0


def polar(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    """Point at ``deg`` on the circle (0 deg = +x, clockwise in y-down space)."""
    rad = math.radians(deg)
    return (cx + r * math.cos(rad), cy + r * math.sin(rad))


def beam_half_width(y: float) -> float:
    """Half-width of the beam at page row ``y`` — the cream flank starts here."""
    return max(0.0, (y - EY)) * math.tan(math.radians(BEAM_HALF))


def _display_fits(size: float) -> bool:
    """Does ``DISPLAY`` set at ``size`` clear the solid field it sits in?

    The binding row is the TOP of the glyph band (the field is a trapezoid, so
    it is narrowest there) — and that row itself moves down as the size grows,
    since the box top is pinned. Both sides are measured, never estimated.
    """
    top = DISPLAY_TOP + size * (1.62 / 2.0 - 0.355)
    run = (measure_text(DISPLAY, font_family=SLAB, font_size=size)
           + DISPLAY_TRACK * (len(DISPLAY) - 1))
    return run <= 2.0 * beam_half_width(top) - 2.0 * DISPLAY_MARGIN


def fit_display_size(lo: float = 120.0, hi: float = 460.0) -> float:
    """Largest size at which the display still clears the field, by bisection.

    The set width grows about 2.5 px per px of size while the field grows only
    ~0.61 px per px, so the predicate is monotone and bisection is sound. Fitting
    rather than hard-coding means the poster stays correct when the copy, the
    face or BEAM_HALF changes — a hand-picked size silently overflows instead.
    """
    if not _display_fits(lo):
        raise ValueError(
            f"the solid field cannot hold {DISPLAY!r} even at {lo:.0f} px; "
            f"widen BEAM_HALF or lower DISPLAY_TOP"
        )
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if _display_fits(mid):
            lo = mid
        else:
            hi = mid
    return round(lo, 1)


def _uncramped(objs: list[dict]) -> list[dict]:
    """Re-centre arc-set glyph boxes on a 1.6 em height.

    ``text_on_path`` emits each glyph in a box 1.35 em tall, just under the
    1.40 em floor below which the renderer reports the text as clipped — so a
    sheet of arc-set type returns hundreds of `clipped` signals with no ink
    actually lost, and a REAL clip elsewhere would be buried in the noise. The
    glyph centre is preserved exactly; only the box grows.
    """
    out = []
    for o in objs:
        size = float(o["style"]["font_size"])
        x, y, w, h = o["box"]
        out.append({**o, "box": [x, y + h / 2.0 - size * 0.8, w, size * 1.6]})
    return out


def _fit_phrase(text: str, avail: float, size: float, family: str,
                track: float) -> str:
    """Longest whole-word prefix of ``text`` that fits ``avail`` arc length."""
    while text and _arc_run(text, size, family, track) > avail:
        text = text[:-1]
    cut = max(text.rfind(" "), text.rfind("·"))
    if cut > 0:
        text = text[:cut]
    return text.strip(" ·")


def _flank_ok(p: tuple[float, float]) -> bool:
    """Is ``p`` inside the cream flank field the §8 bands are allowed to use?

    Ink-on-cream flavour text is invisible the moment it crosses onto the §7
    solid field, and it would fight the §2 presenter line above — so the band
    is bounded on both sides rather than trimmed after the fact.
    """
    x, y = p
    if not (FLANK_INSET <= x <= W - FLANK_INSET and FLANK_INSET <= y <= H - FLANK_INSET):
        return False
    return 152.0 <= y <= SOLID_Y - 18.0


def wedge(r0: float, r1: float, a0: float, a1: float, **fields):
    """An annular sector (r0..r1, a0..a1 degrees) about the eye, as a path dict."""
    x0, y0 = polar(EX, EY, r1, a0)
    x1, y1 = polar(EX, EY, r1, a1)
    x2, y2 = polar(EX, EY, r0, a1)
    x3, y3 = polar(EX, EY, r0, a0)
    large = 1 if abs(a1 - a0) > 180 else 0
    d = (f"M {x0:.2f} {y0:.2f} A {r1:.2f} {r1:.2f} 0 {large} 1 {x1:.2f} {y1:.2f} "
         f"L {x2:.2f} {y2:.2f} A {r0:.2f} {r0:.2f} 0 {large} 0 {x3:.2f} {y3:.2f} Z")
    return {"type": "path", "d": d, "decorative": True, **fields}


def ray_angles(lo: float, hi: float) -> list[tuple[float, float]]:
    """Wedge (start, end) pairs on the ONE period, covering [lo, hi] degrees.

    The grid is PHASE-LOCKED so a wedge is centred on the vertical axis (90 deg,
    straight down). An arbitrary phase puts a wedge *edge* on the axis instead,
    and the beam is then not bilaterally symmetric — which C3 (scored 4, radial
    / symmetrical) fails on inspection even though the spacing is still even.
    360 / RAYS divides 90 exactly, so the halo stays locked too.
    """
    half = PERIOD * DUTY / 2.0
    out: list[tuple[float, float]] = []
    n = math.floor((lo - 90.0) / PERIOD) - 1
    while 90.0 + n * PERIOD - half <= hi:
        centre = 90.0 + n * PERIOD
        a0, a1 = centre - half, centre + half
        if a1 >= lo and a0 <= hi:
            out.append((max(a0, lo), min(a1, hi)))
        n += 1
    return out


# --------------------------------------------------------------------------- #
# §0.2 · Placeholder copy (INVENTED — the profile scores form, not content)
# --------------------------------------------------------------------------- #
PRESENTER = "THE ORPHEUM SOCIETY PRESENTS"
KICKER = "LIVE EVENT"
DISPLAY = "BAND"
LINEUP = "WITH THE VELVET TIDE  ·  MOTHER CIRCUIT  ·  SLOW LANTERN"
DATE = "SAT 18 OCT"
DOORS = "DOORS 8 PM   ·   MUSIC 9 PM   ·   18+"
CTA = "TICKETS AT THE DOOR — $18"
VENUE = "THE ORPHEUM BALLROOM"
ADDRESS = "214 CANAL STREET  ·  NEW ORLEANS, LOUISIANA"
SMALLPRINT = "NO REFUNDS  ·  NO ENCORES  ·  ONE NIGHT ONLY"

# C5: the density is carried here — a sparse core message swimming in repeated
# small flavour text, exactly as the profile scores it.
FLAVOUR = [
    "AN EVENING OF LOUD AND HYPNOTIC MUSIC · ",
    "THE SOUND WILL FIND YOU WHEREVER YOU STAND · ",
    "ALL SEEING · ALL HEARING · ALL NIGHT · ",
    "BRING YOUR OWN LIGHT AND LEAVE IT BURNING · ",
    "ONE NIGHT ONLY · NO REFUNDS · NO ENCORES · ",
    "TURN THE HOUSE LIGHTS DOWN AND LOOK UP · ",
    "WE PLAY UNTIL THE ROOM AGREES · ",
    "EVERY EYE IN THE ROOM POINTS THE SAME WAY · ",
]

# Fitted here, not above: the fit needs both the copy and the real bold metrics.
DISPLAY_SIZE = fit_display_size()


def _arc_run(text: str, size: float, family: str, track: float) -> float:
    """Arc length ``text_on_path`` will consume for ``text`` — the same walk it
    does internally, so §3/§8 can centre and truncate against real metrics."""
    total = 0.0
    for ch in text:
        if ch == " ":
            total += size * 0.32 + track
        else:
            total += measure_text(ch, font_family=family, font_size=size) + track
    return total


def build():
    doc = DocumentBuilder(title="LIVE EVENT / BAND — gig poster", profile="mixed")

    page = doc.page(
        "poster",
        canvas={"size": [W, H], "units": "px", "background": CREAM},
        coordinate_mode="absolute",
        meta={
            "source_profile": "img13_live_event_band_poster",
            "registry_sha256": REGISTRY_SHA256,
            "epistemic_status": (
                "Specified reconstruction from a 22-dimension assessment profile; "
                "no source image is available to compare against. All copy is "
                "invented placeholder content."
            ),
        },
        # Raster-stage screen-print grain. Deterministic seed; the SVG/PDF
        # targets are byte-unaffected and the renderer says so (PALS).
        post={"grain": {"amount": 0.022, "seed": 1968, "monochrome": True}},
    )

    # ----------------------------------------------------------------------- #
    # §1 · Ground — C29 lightness (light key), C31 contrast (measured below)
    # ----------------------------------------------------------------------- #
    ground = page.layer("ground")
    ground.rect([0, 0, W, H], fill=CREAM)

    # ----------------------------------------------------------------------- #
    # §4 · The sunburst — C3 layout topology, A2 spatial rhythm, C33 ornament
    #      One angular period; the halo rings the eye, the beam falls from it.
    # ----------------------------------------------------------------------- #
    burst = page.layer("burst")
    with burst.bleed():
        # 4a · halo: short spikes all the way round, so the eye reads as radiant.
        burst.extend([
            wedge(HALO_R0, HALO_R1, a0, a1, fill=INK)
            for a0, a1 in ray_angles(0.0, 360.0)
        ])
        # 4b · beam: the same period, run long and cut to the triangle. The clip
        # sits on a STATIC group (no transform), so it cannot ride along.
        burst.group(
            [wedge(HALO_R0, BEAM_R, a0, a1, fill=INK)
             for a0, a1 in ray_angles(90.0 - BEAM_HALF - PERIOD, 90.0 + BEAM_HALF + PERIOD)],
            clip=clip_polygon(BEAM_TRI),
            decorative=True,
        )
        # 4c · the beam's own edges, drawn crisp so the triangle reads as a beam
        # and not as a ragged fan. They stop at the triangle's base corners —
        # a ray run to BEAM_R would streak unclipped across the whole sheet.
        for corner in BEAM_TRI[1:]:
            burst.line([EX, EY], list(corner), **stroke(3.0, color=INK))
        # 4d · below SOLID_Y the rays close up into one solid field, so §7's
        # reversed type has an unbroken ground. Cream type over the striped beam
        # would sit half on cream and vanish.
        hw_top = beam_half_width(SOLID_Y)
        burst.polygon([[EX - hw_top, SOLID_Y], [EX + hw_top, SOLID_Y],
                       BEAM_TRI[2], BEAM_TRI[1]], fill=INK)

    # ----------------------------------------------------------------------- #
    # §5 · The eye — C32 abstraction (flat, schematic), C36 iconic + symbolic,
    #      C30 chroma (the iris is the ONLY saturated element in the poster).
    # ----------------------------------------------------------------------- #
    eye = page.layer("eye")
    LID_W, LID_H = 208.0, 122.0
    almond = (f"M {EX - LID_W:.1f} {EY:.1f} "
              f"Q {EX:.1f} {EY - LID_H * 2.0:.1f} {EX + LID_W:.1f} {EY:.1f} "
              f"Q {EX:.1f} {EY + LID_H * 2.0:.1f} {EX - LID_W:.1f} {EY:.1f} Z")
    with eye.bleed():
        # Lashes first, so the lid overlaps their roots.
        for i in range(-3, 4):
            if i == 0:
                continue
            a = -90.0 + i * 13.0
            p0 = polar(EX, EY + 6.0, LID_W * 0.80, a)
            p1 = polar(EX, EY + 6.0, LID_W * 1.12, a)
            eye.line(list(p0), list(p1), **stroke(11.0, color=INK, cap="round"))
        eye.path(almond, fill=CREAM, style={"stroke": INK, "stroke_width": 13.0,
                                            "stroke_linejoin": "round"})
        # C30 · the only chromatic element on the sheet: twelve real sectors.
        step = 360.0 / len(IRIS_WHEEL)
        for i, hue in enumerate(IRIS_WHEEL):
            eye.sector([EX, EY], IRIS_R, -90.0 + i * step, -90.0 + (i + 1) * step,
                       fill=hue)
        eye.circle([EX, EY], IRIS_R, fill="none",
                   style={"stroke": INK, "stroke_width": 9.0})
        eye.circle([EX, EY], 38.0, fill=INK)
        eye.circle([EX - 27.0, EY - 30.0], 15.0, fill=CREAM)
        eye.circle([EX + 20.0, EY + 22.0], 7.0, fill=CREAM, opacity=0.85)

    # ----------------------------------------------------------------------- #
    # §2 · Presenter line + rules — C26 role differentiation, C27 centred axis
    # ----------------------------------------------------------------------- #
    head = page.layer("head")
    head.text([W / 2 - 460, 74, 920, S_LABEL * 1.6], PRESENTER, id="presenter",
              style={"font_family": [GROT], "font_size": S_LABEL, "font_weight": 600,
                     "letter_spacing": 7.4, "color": INK, "align": "center"})
    for i, y in enumerate((116.0, 124.0)):
        half = 300.0 if i == 0 else 240.0
        head.line([W / 2 - half, y], [W / 2 + half, y],
                  **stroke(4.0 if i == 0 else 2.0, color=INK))

    # ----------------------------------------------------------------------- #
    # §3 · Arched kicker — C27 curved baselines, on the profile's own label
    # ----------------------------------------------------------------------- #
    KICK_R = 322.0
    kick_pts = [polar(EX, EY, KICK_R, a) for a in range(232, 309, 2)]
    with head.bleed(), head.lettering():
        head.extend(_uncramped(text_on_path(
            kick_pts, KICKER, size=S_KICK, family=SLAB, weight=700, color=INK,
            offset=-6.0, track=9.0,
            s0=(path_length(kick_pts) - _arc_run(KICKER, S_KICK, SLAB, 9.0)) / 2.0,
        )))
        # Two stars closing the arch, on the same circle.
        for a in (228.0, 312.0):
            cx, cy = polar(EX, EY, KICK_R, a)
            head.star([cx, cy], 20.0, 8.0, 8, fill=INK)

    # ----------------------------------------------------------------------- #
    # §8 · Flank flavour bands — A8 typographic texture, A1 complexity, C5
    #      Concentric arcs about the eye, hugging the beam edges, running off
    #      the sheet. Each arc is truncated to the copy that actually fits.
    # ----------------------------------------------------------------------- #
    flank = page.layer("flank")
    with flank.bleed(), flank.lettering():
        band = 0
        for r in range(430, 1400, 62):
            for side, (a_start, step) in (
                ("R", (90.0 - BEAM_HALF - 4.0, -1.0)),   # right flank, sweeping up
                ("L", (90.0 + BEAM_HALF + 4.0, 1.0)),    # left flank, mirrored
            ):
                pts: list[tuple[float, float]] = []
                a = a_start
                while abs(a - a_start) <= 104.0:
                    p = polar(EX, EY, float(r), a)
                    if _flank_ok(p):
                        pts.append(p)
                    elif pts:
                        break            # first exit ends the band, never re-enters
                    a += step
                if len(pts) < 14:
                    continue
                # Repeat the phrase, then cut it to what the arc actually holds,
                # measured with the same walk text_on_path performs, and backed
                # off to a word boundary so no band ends mid-word.
                text = _fit_phrase(FLAVOUR[band % len(FLAVOUR)] * 4,
                                   path_length(pts), S_FLAVOUR, GROT, 1.6)
                if len(text) < 12:
                    continue
                flank.extend(_uncramped(text_on_path(
                    pts, text, size=S_FLAVOUR, family=GROT, weight=500,
                    color=INK, offset=-4.0 if side == "L" else 4.0, track=1.6,
                )))
                band += 1

    # ----------------------------------------------------------------------- #
    # §6 · The display — C4 salience, C20 weight, C18 slab construction
    #      Cream letterforms with a heavy ink outline, drawn stroke-behind-fill
    #      so the outline adds mass instead of eating the counters.
    # ----------------------------------------------------------------------- #
    # The display sits wholly inside the solid field, on ONE uniform ground.
    # Straddling the striped beam was tried and cut: a cream letter reads solid
    # over the black rays and hollow over the cream flank, so the beam's slanted
    # edge slices each glyph into two unrelated shapes and the word stops being
    # a word. C4 (scored 4, strong focal) cannot survive that.
    #
    # No offset shadow either: over the rays it doubles the word into a second
    # competing silhouette, and C32 (scored 4, "simplified / schematic, low
    # retained detail") argues against the depth cue regardless.
    #
    # C20 (scored 4, heavy / black): Roboto Slab tops out at Bold, so the mass
    # is bought with size on maximum contrast rather than with a synthesized 900
    # that would misreport the face.
    disp = page.layer("display")
    box = [0.0, DISPLAY_TOP, float(W), DISPLAY_SIZE * 1.62]
    disp.text(box, DISPLAY, id="display",
              style={"font_family": [SLAB], "font_size": DISPLAY_SIZE,
                     "font_weight": 700, "align": "center",
                     "letter_spacing": DISPLAY_TRACK, "color": CREAM,
                     "stroke": INK, "stroke_width": DISPLAY_STROKE,
                     "stroke_linejoin": "round"})

    # ----------------------------------------------------------------------- #
    # §7 · The information block — C2 layered detail, C26 seven roles,
    #      all reversed out of the beam (C31 extreme contrast, both directions).
    # ----------------------------------------------------------------------- #
    info = page.layer("info")

    def centred(y: float, w: float) -> list[float]:
        """A centred box of width ``w`` at row ``y``, asserted to fit the field.

        The solid field is a trapezoid, so a box that fits at the bottom can
        still hang off the sides higher up — this refuses to place type that
        would spill onto the cream flank rather than letting it happen quietly.
        """
        limit = 2.0 * beam_half_width(y) - 24.0
        if w > limit:
            raise ValueError(
                f"info box {w:.0f}px wide at y={y:.0f} exceeds the solid field "
                f"({limit:.0f}px); move it down or set it smaller"
            )
        return [EX - w / 2.0, y, w, 0.0]

    # A cream stage rule on the ray/solid seam, spanning the field at that row.
    seam = beam_half_width(SOLID_Y + 24.0) - 26.0
    info.line([EX - seam, SOLID_Y + 24.0], [EX + seam, SOLID_Y + 24.0],
              **stroke(3.0, color=CREAM))

    info.text(centred(1312.0, 700.0)[:3] + [S_LABEL * 1.6], LINEUP, id="lineup",
              style={"font_family": [GROT], "font_size": S_LABEL, "font_weight": 600,
                     "letter_spacing": 2.4, "color": CREAM, "align": "center"})
    info.text(centred(1370.0, 800.0)[:3] + [S_DATE * 1.55], DATE, id="date",
              style={"font_family": [SLAB], "font_size": S_DATE, "font_weight": 700,
                     "letter_spacing": 3.0, "color": CREAM, "align": "center"})
    info.text(centred(1512.0, 820.0)[:3] + [S_LABEL * 1.6], DOORS, id="doors",
              style={"font_family": [GROT], "font_size": S_LABEL, "font_weight": 500,
                     "letter_spacing": 4.6, "color": CREAM, "align": "center"})

    # CTA — the one cream slab in the black half; the poster's second inversion.
    CTA_W, CTA_H, CTA_Y = 726.0, 92.0, 1566.0
    info.rect(centred(CTA_Y, CTA_W)[:3] + [CTA_H], fill=CREAM,
              style={"border_radius": 6})
    info.text([EX - CTA_W / 2, CTA_Y + 21, CTA_W, S_LEDE * 1.6], CTA, id="cta",
              style={"font_family": [GROT_HEAVY], "font_size": S_LEDE,
                     "font_weight": 800, "letter_spacing": 3.4, "color": INK,
                     "align": "center"})

    info.text(centred(1676.0, 900.0)[:3] + [S_LEDE * 1.6], VENUE, id="venue",
              style={"font_family": [SLAB], "font_size": S_LEDE, "font_weight": 700,
                     "letter_spacing": 3.8, "color": CREAM, "align": "center"})
    info.text(centred(1722.0, 940.0)[:3] + [S_META * 1.6], ADDRESS, id="address",
              style={"font_family": [GROT], "font_size": S_META, "font_weight": 500,
                     "letter_spacing": 3.0, "color": CREAM, "align": "center"})
    info.text(centred(1758.0, 940.0)[:3] + [S_META * 1.6], SMALLPRINT, id="smallprint",
              style={"font_family": [GROT], "font_size": S_META, "font_weight": 500,
                     "letter_spacing": 4.2, "color": CREAM, "align": "center"},
              opacity=0.88)

    # ----------------------------------------------------------------------- #
    # §9 · Corner ornament — C33 ornamentation, kept in the cream field only
    # ----------------------------------------------------------------------- #
    orn = page.layer("ornament")
    with orn.bleed():
        # Ink in the cream field at the top, cream in the solid field at the
        # bottom — the same ornament, reversed, closing the A2 rhythm.
        for cx, cy, tone in ((92.0, 92.0, INK), (W - 92.0, 92.0, INK),
                             (92.0, 1706.0, CREAM), (W - 92.0, 1706.0, CREAM)):
            orn.star([cx, cy], 30.0, 11.4, 8, fill=tone)
            orn.circle([cx, cy], 48.6, fill="none", **stroke(3.0, color=tone))

    return doc


# --------------------------------------------------------------------------- #
# Measured proofs — printed, never asserted (CLAUDE.md constraint 2)
# --------------------------------------------------------------------------- #
def proofs() -> list[str]:
    disp_w = (measure_text(DISPLAY, font_family=SLAB, font_size=DISPLAY_SIZE)
              + DISPLAY_TRACK * (len(DISPLAY) - 1))
    disp_mid = DISPLAY_TOP + DISPLAY_SIZE * 1.62 / 2.0
    field_w = 2.0 * beam_half_width(disp_mid - DISPLAY_SIZE * 0.355)
    iris_area = math.pi * IRIS_R ** 2
    return [
        f"C31 relational contrast (scored 5, 'extreme'): ink {INK} on cream "
        f"{CREAM} = {contrast_ratio(INK, CREAM):.2f}:1 — WCAG AAA large-text "
        f"floor is 4.5:1 and the body floor 7:1, so both directions clear it "
        f"(the poster reverses ground and figure twice)",
        f"A2 spatial rhythm (scored 4, 'radial / periodic'): {RAYS} wedges, one "
        f"period = {PERIOD:.4f} deg at duty {DUTY:.2f}; halo and beam share it, "
        f"phase-locked with a wedge centred on the vertical axis "
        f"(90 / {PERIOD:.4f} = {90.0 / PERIOD:.1f} periods, integral => symmetric)",
        f"C3 layout topology: beam half-angle {BEAM_HALF:.0f} deg from apex "
        f"({EX:.0f}, {EY:.0f}); half-width {beam_half_width(SOLID_Y):.0f} px at the "
        f"y={SOLID_Y:.0f} seam and {_dx:.0f} px at y={H}, so the field bleeds off "
        f"both bottom corners",
        f"C30 chroma: {len(IRIS_WHEEL)} chromatic paints, all inside the iris disc "
        f"(r={IRIS_R:.0f} px = {iris_area / (W * H) * 100:.2f}% of the sheet); every "
        f"other paint on the poster is cream or ink",
        f"C4 salience: display '{DISPLAY}' sets {disp_w:.0f} px wide at "
        f"{DISPLAY_SIZE:.0f} px ({disp_w / W * 100:.0f}% of the {W} px sheet) inside a "
        f"{field_w:.0f} px solid field — {(field_w - disp_w) / 2.0:.0f} px clear each side",
    ]


if __name__ == "__main__":
    out_dir = os.path.join(ROOT, "_tmp", "img13-live-event-poster")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "img13-live-event-band-poster.fg.yaml")
    report = build().write(out, fail_on_error=True)
    print(f"wrote {out}")
    if report is not None:
        print(f"validation ok={report.ok} issues={len(report.issues)}")
        for issue in report.issues[:12]:
            print(f"  - {issue}")
    print("\nMEASURED PROOFS")
    for line in proofs():
        print(f"  {line}")
