#!/usr/bin/env python3
"""Reconstruct the ``gulf-war-2003-photobook-cover-brief`` as a real jacket.

Two source records drive this client; nothing here is retyped from them by
hand — both JSON files are read at build time and their sha256 is stamped into
the document meta, so the artifact cannot drift from the brief:

    _tmp/gulf_war_2003_cover_brief.json            direction (mood + design_direction)
    _tmp/gulf_war_2003_cover_image_selection.json  the chosen photograph + its rights

WHAT IS NOT HERE, AND WHY
-------------------------
The photograph. The selection record names a specific, copyrighted frame —
Jean-Marc Bouju / The Associated Press, 31 March 2003 — and states plainly that
images are not reproduced in it. The brief's fourth guardrail forbids "an
AI-generated or composited image presented as documentary". Both readings agree:
this client reserves the plate at its true measure and prints the licence path
into it. It does NOT draw, trace, simulate, or otherwise invent a war
photograph. The plate is a hole with a specification, which is what a cover comp
at this stage honestly is.

Everything the brief actually fixes IS executed: print geometry, the achromatic
ink system, the type system, the flush-left single block, the panel hierarchy,
the credit roles, the retail-thumbnail survival test, and the conformance record.

When the licensed file exists, one environment variable places it — the plate
takes the frame's TRUE aspect, the reservation text disappears, and nothing is
printed over the photograph:

    IRAQ2003_COVER_IMAGE=/path/to/bouju-an-najaf.tif \
        uv run python static/examples/iraq_2003_photobook_jacket.py

A file being present settles nothing about the licence; see §6b.

SLOTS. Grey bracketed text — ``[ EDITOR ]`` — is an unresolved slot, not copy.
Names that are set in bone are real and sourced from the selection record. The
ISBN is 978-1-234567-89-7, the conventional publishing dummy.

THE MEASURED GATES (printed by ``__main__``, asserted at build time)
  chroma      every declared colour is strictly achromatic (r == g == b), which
              discharges C28's "NO patriotic red/white/blue" by construction
  contrast    every live text colour clears WCAG 4.5:1 on its own ground
  thumbnail   the title's cap height is computed at each retail scale
  barcode     the EAN-13 symbol is decoded back before it is drawn

ARCHITECTURAL REQUIREMENT (PALS's LAW): LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Run from the repository root::

    uv run python static/examples/iraq_2003_photobook_jacket.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge_sdk import DocumentBuilder  # noqa: E402
from frameforge_sdk.chevreul import contrast_ratio  # noqa: E402
from frameforge_sdk.geometry import Mat3  # noqa: E402
from frameforge_sdk.metrics import measure_text, wrap_text  # noqa: E402

# The EAN-13/EAN-5 encoder + its decoder already exist in the sibling jacket
# client. A second copy of the GS1 parity tables is a second thing to get wrong,
# so this loads that module by path rather than duplicating them.
_TJ_PATH = os.path.join(HERE, "the_tour_jacket.py")
_tj_spec = importlib.util.spec_from_file_location("_ff_tour_jacket", _TJ_PATH)
_tj = importlib.util.module_from_spec(_tj_spec)
_tj_spec.loader.exec_module(_tj)
ean13_modules, ean5_modules, decode_ean13 = (
    _tj.ean13_modules, _tj.ean5_modules, _tj.decode_ean13)


# --------------------------------------------------------------------------- #
# §1 · The source records — read, hashed, never retyped
# --------------------------------------------------------------------------- #
BRIEF_PATH = os.path.join(ROOT, "_tmp", "gulf_war_2003_cover_brief.json")
IMAGE_PATH = os.path.join(ROOT, "_tmp", "gulf_war_2003_cover_image_selection.json")


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _load(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"source record missing: {path}\n"
            "This client is a reconstruction OF those records; it cannot be "
            "built without them.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


BRIEF = _load(BRIEF_PATH)
IMAGE = _load(IMAGE_PATH)
BRIEF_SHA, IMAGE_SHA = _sha256(BRIEF_PATH), _sha256(IMAGE_PATH)
PICK = IMAGE["recommended"]

# --------------------------------------------------------------------------- #
# §2 · Print geometry — a large-format photobook jacket with flaps
# --------------------------------------------------------------------------- #
# Authored at 96 px/in, so every number below is a real press dimension.
# The brief asks for a "larger photobook trim" and for a jacket carrying front,
# spine and back; the flaps come with the jacket and are load-bearing here,
# because guardrail 7 puts the photograph's honest caption on one of them.
PPI = 96.0


def inches(v: float) -> float:
    return v * PPI


TRIM_W, TRIM_H = 9.50, 11.25      # in — 241 x 286 mm, a standard monograph trim
FLAP_IN = 3.50                    # in — jacket flap
BLEED_IN = 0.125
SAFE_IN = 0.375
# Spine: 256pp on 170 gsm matt art (caliper ~0.15 mm/leaf) = 128 x 0.15 =
# 19.2 mm, plus two 3.0 mm board-and-cloth turns = 25.2 mm = 0.992 in. Rounded
# UP to the next 1/16 in, because a spine that measures short is a reprint.
SPINE_IN = 1.0

BLEED, SAFE = inches(BLEED_IN), inches(SAFE_IN)
PANEL_W, PANEL_H = inches(TRIM_W), inches(TRIM_H)
FLAP_W, SPINE_W = inches(FLAP_IN), inches(SPINE_IN)

W = 2 * BLEED + 2 * FLAP_W + 2 * PANEL_W + SPINE_W     # 2616 px == 27.25 in
H = 2 * BLEED + PANEL_H                                # 1104 px == 11.50 in

BFLAP_X = BLEED                          # back flap, at the left of the flat
BACK_X = BFLAP_X + FLAP_W                # back panel
SPINE_X = BACK_X + PANEL_W               # spine
FRONT_X = SPINE_X + SPINE_W              # front panel
FFLAP_X = FRONT_X + PANEL_W              # front flap
RIGHT_X = FFLAP_X + FLAP_W
TRIM_T, TRIM_B = BLEED, BLEED + PANEL_H
FOLDS = (BACK_X, SPINE_X, FRONT_X, FFLAP_X)

LIVE_T, LIVE_B = TRIM_T + SAFE, TRIM_B - SAFE
LIVE_W = PANEL_W - 2 * SAFE              # 840 px — the panel measure
FLAP_LIVE_W = FLAP_W - 2 * SAFE          # 264 px — the flap measure

# --------------------------------------------------------------------------- #
# §3 · Ink (C28 / C30 / C31) — achromatic by rule, verified by gate
# --------------------------------------------------------------------------- #
# The brief's colour direction is "muted, image-led; neutral type; NO patriotic
# red/white/blue coding" and "no added saturation". The strongest reading of
# both is not "low chroma" but ZERO chroma: every colour the DESIGN contributes
# is a grey, and every hue on the finished jacket therefore belongs to the
# photograph. That is checkable, and §9 checks it.
INK = "#131313"        # jacket ground — a single-ink near-black, not a rich black
BONE = "#E9E9E9"       # primary type
GREY = "#8E8E8E"       # secondary type and unresolved slots
PLATE = "#242424"      # the reserved photograph plate
RULE = "#3C3C3C"       # hairlines inside the plate
MARK = "#9B9B9B"       # production marks (construction layer only)
PAPER = "#E9E9E9"      # the retail-thumbnail sheet ground
SHEET_INK = "#1A1A1A"  # type on the specification sheets
SHEET_DIM = "#5E5E5E"

INKS = {"ink": INK, "bone": BONE, "grey": GREY, "plate": PLATE, "rule": RULE,
        "mark": MARK, "paper": PAPER, "sheetInk": SHEET_INK, "sheetDim": SHEET_DIM}

# (colour, ground, role) triples that must clear WCAG 4.5:1 — live type only.
CONTRAST_GATE = [
    (BONE, INK, "title / primary type on the jacket ground"),
    (GREY, INK, "secondary type and slots on the jacket ground"),
    (MARK, PLATE, "the plate's own specification type"),
    (SHEET_INK, PAPER, "specification-sheet body"),
    (SHEET_DIM, PAPER, "specification-sheet secondary"),
]

# --------------------------------------------------------------------------- #
# §4 · Type (C18 / C20 / C26 / C27) — one serious grotesque, one scale
# --------------------------------------------------------------------------- #
# C18 asks for "serious grotesque or restrained serif" and rules out stencil,
# military and distressed faces. Archivo is a Roman grotesque with a variable
# weight axis, so C26's four roles separate by weight, size and case inside ONE
# family rather than by adding faces — which is what C33's austerity requires.
GROTESK = ["Archivo", "Inter", "DejaVu Sans", "sans-serif"]

W_TITLE = "'wght' 500, 'wdth' 100"     # C20 — medium, not black
W_MED = "'wght' 500, 'wdth' 100"
W_BOOK = "'wght' 400, 'wdth' 100"
W_SEMI = "'wght' 600, 'wdth' 100"
CAP_EM = 0.686                          # Archivo sCapHeight / upm

SCALE_BASE, SCALE_RATIO = 11.0, 1.22


def step(n: int) -> float:
    return round(SCALE_BASE * SCALE_RATIO ** n, 2)


S_MICRO = step(0)      # 11.00 — colophon, barcode HRI
S_SMALL = step(1)      # 13.42 — flap body, back-cover body, credits
S_CREDIT = step(2)     # 16.37 — the front credit block
S_SUB = step(3)        # 19.97 — subtitle
S_SPINE = step(6)      # 36.27 — spine title
S_FLAP = 11.0          # the flap measure is 264 px; the panel scale will not fit
BODY_LH = 1.62

# The title is SOLVED from the measure, not chosen: it is set to fill 74 % of
# the panel measure, which keeps it subordinate to a plate that fills 100 % of
# it (C20) while staying large enough to survive the thumbnail ladder (§8).
TITLE = "IRAQ 2003"
TITLE_TRACK = 1.6
TITLE_FILL = 0.66

# Author-time measurement and the rasterizer do NOT agree to the pixel: fc-match
# resolves Archivo's DEFAULT variable instance while the renderer draws the
# instance each style asks for. A line wrapped to the exact measure therefore
# renders a hair wider, the renderer folds its last word onto a second line, and
# a box that is one line tall CLIPS that word away — copy silently lost, which
# is the worst failure a press file can have. Two defences, both applied:
#   1. every line is wrapped to WRAP_SAFETY of its measure, and
#   2. every style is nowrap, so a line that still overruns overhangs its box
#      visibly instead of disappearing.
WRAP_SAFETY = 0.88


def _solve_title_size() -> float:
    at100 = measure_text(TITLE, font_family=GROTESK, font_size=100.0,
                         variation_settings=W_TITLE)
    target = TITLE_FILL * LIVE_W - TITLE_TRACK * (len(TITLE) - 1)
    return round(target * 100.0 / at100, 1)


S_TITLE = _solve_title_size()

# --------------------------------------------------------------------------- #
# §5 · Copy — real credits from the record, bracketed slots for the rest
# --------------------------------------------------------------------------- #
# The brief's naming_flag is discharged here and nowhere else: the working title
# "Gulf War 2003" is REJECTED, because that name conventionally denotes 1990-91.
WORKING_TITLE = BRIEF["subject"]["working_title"]
SUBTITLE_SENTENCE = "Photographs from the invasion of Iraq, March–May 2003"
SUBTITLE = SUBTITLE_SENTENCE.upper()

PHOTOGRAPHER = PICK["photographer"]              # Jean-Marc Bouju
RIGHTS = PICK["rights_holder"]                   # The Associated Press (AP)
CREDIT_LINE = PICK["credit_line"]                # Jean-Marc Bouju / AP
PHOTO_DATE = PICK["date"]
PHOTO_PLACE = PICK["location"]
ACCOLADE = PICK["accolade"]
LICENCE_PATH = PICK["licensing_path"]

SLOT_PHOTOGRAPHERS = "[ CONTRIBUTING PHOTOGRAPHERS ]"
SLOT_EDITOR = "[ EDITOR ]"
SLOT_IMPRINT = "[ IMPRINT ]"
SLOT_DESIGNER = "[ JACKET DESIGNER ]"
SLOT_PRICE = "[ £ 00.00 ]"

FRONT_CREDIT = f"COVER PHOTOGRAPH  ·  {PHOTOGRAPHER.upper()} / AP"

# The full, honest caption. Guardrail 7 says it belongs on a flap or the back;
# it is set on the front flap, in full, uncut.
CAPTION = (
    f"Cover photograph. {PICK['description']} {PHOTO_PLACE}, {PHOTO_DATE}. "
    f"© {CREDIT_LINE.replace(' / AP', '')} / {RIGHTS}. {ACCOLADE}.")

ISBN12 = "978123456789"        # the conventional publishing dummy
PRICE5 = "59500"               # EAN-5 add-on, a placeholder price band
BAR_MODULE = 1.55
BAR_H = 60 * BAR_MODULE
GUARD_EXTRA = 5 * BAR_MODULE


# --------------------------------------------------------------------------- #
# §6 · A tiny typesetter — every text box is placed by its LINE, not its box
# --------------------------------------------------------------------------- #
# A FrameForge text box is centre-anchored and clips silently below ~1.40x the
# font size, so a naive [x, y, w, size] box loses descenders. Column places each
# line on a leading grid and gives it a box comfortably taller than its face.
# Named styles carry an ABSOLUTE font size, so a style name alone cannot draw
# the same panel at two scales. Column therefore overrides font_size (and the
# named style's tracking, which is absolute too) per object via `class`, and
# this registry is how it knows what tracking to scale. Populated by ``ts()``.
TRACKING: dict[str, float] = {}


class Column:
    """A leading grid. ``x``/``y`` are page px; ``w`` and every ``size`` are
    LOCAL units multiplied by ``k`` — so the same code draws a panel at 100 %
    and at 10 %, which is what makes the thumbnail ladder a real test."""

    def __init__(self, page, x: float, y: float, w: float, scale: float = 1.0):
        self.pg, self.x, self.y, self.w, self.k = page, x, y, w, scale

    def gap(self, dy: float) -> "Column":
        self.y += dy * self.k
        return self

    def line(self, text: str, style: str, size: float, *, lead: float | None = None,
             before: float = 0.0, oid: str | None = None,
             w: float | None = None) -> "Column":
        self.y += before * self.k
        lead_px = (lead if lead is not None else size * 1.5) * self.k
        # A text box shorter than ~1.40x its font size is SILENTLY clipped, so
        # 1.45 is the floor. Give a line a leading at or above that and its box
        # is exactly its leading — consecutive lines then do not overlap at all,
        # which is what lets a row be lowered as a free group without tripping
        # the scoped non-overlap rule.
        h = max(size * self.k * 1.45, lead_px)
        cy = self.y + lead_px / 2.0
        st: dict = {"class": style, "font_size": round(size * self.k, 3)}
        if style in TRACKING:
            st["letter_spacing"] = round(TRACKING[style] * self.k, 3)
        fields = {"style": st, "overlap": "allowed"}
        if oid:
            fields["id"] = oid
        self.pg.text([self.x, cy - h / 2.0, (w if w is not None else self.w) * self.k,
                      h], text, **fields)
        self.y += lead_px
        return self

    def para(self, text: str, style: str, size: float, *, lead: float,
             measure: float, var: str = W_BOOK, before: float = 0.0,
             oid: str | None = None) -> "Column":
        """Set a wrapped paragraph. The wrap is resolved HERE and each line is
        emitted in its own box: author-time metrics and the rasterizer do not
        agree to the line, and a press file may not be host-dependent."""
        self.y += before * self.k
        lines = wrap_text(text, width=measure * WRAP_SAFETY, font_family=GROTESK,
                          font_size=size, variation_settings=var)
        for i, ln in enumerate(lines):
            self.line(ln, style, size, lead=lead,
                      oid=f"{oid}-{i}" if oid else None)
        return self


def dashed_v(pg, x: float, y0: float, y1: float, *, seg: float = 7.0,
             gap: float = 7.0, w: float = 0.7, color: str = "mark") -> None:
    y = y0
    while y < y1:
        pg.rect([x - w / 2.0, y, w, min(seg, y1 - y)], fill=color,
                decorative=True, construction=True)
        y += seg + gap


# --------------------------------------------------------------------------- #
# §7 · The front panel, drawn parametrically so the thumbnail ladder is REAL
# --------------------------------------------------------------------------- #
# Every dimension below is panel-local (0..912 x 0..1080) and multiplied by k.
# The ladder in §8 calls this same function at retail scales, so what it proves
# about legibility is a property of this design, not of a separate mock-up.

# --------------------------------------------------------------------------- #
# §6b · The photograph, if and only if a real file is supplied
# --------------------------------------------------------------------------- #
# Point this at the LICENSED file and the plate stops being a reservation:
#
#     IRAQ2003_COVER_IMAGE=/path/to/bouju-an-najaf.tif \
#         uv run python static/examples/iraq_2003_photobook_jacket.py
#
# or drop the file at _tmp/cover-photograph.{tif,jpg,png,webp}. Absent both, the
# plate renders as the specified reservation. There is no third branch: this
# client never draws, traces, or generates a substitute for the frame.
COVER_IMAGE_CANDIDATES = [
    os.path.join(ROOT, "_tmp", f"cover-photograph{ext}")
    for ext in (".tif", ".tiff", ".jpg", ".jpeg", ".png", ".webp")]


def _find_cover_image() -> str | None:
    explicit = os.environ.get("IRAQ2003_COVER_IMAGE")
    if explicit:
        if not os.path.exists(explicit):
            raise FileNotFoundError(
                f"IRAQ2003_COVER_IMAGE is set to {explicit}, which does not "
                f"exist. Refusing to fall back to the reservation silently.")
        return explicit
    return next((p for p in COVER_IMAGE_CANDIDATES if os.path.exists(p)), None)


COVER_IMAGE = _find_cover_image()
COVER_ASSET = None          # the pinned defs.assets handle, set in build()


def _image_aspect(path: str | None) -> tuple[float, str]:
    """Return (width/height, provenance) for the plate reservation.

    A licensed frame's TRUE aspect governs the plate — the brief forbids a crop
    that changes a photograph's meaning, so the layout adapts to the frame and
    never the other way round. Without a file the reservation is a nominal 35 mm
    3:2, which is a stated assumption, not a measurement.
    """
    if path:
        try:
            from PIL import Image  # noqa: PLC0415 — optional, only needed here
            with Image.open(path) as im:
                w, h = im.size
            return w / h, f"measured from {os.path.basename(path)} ({w}×{h})"
        except Exception as exc:                    # pragma: no cover - env
            print(f"  ! could not measure {path}: {exc}; using the nominal 3:2")
    return 3.0 / 2.0, "NOMINAL 3:2 (35 mm) — no licensed file supplied"


COMP_MAX_SIDE = 2400        # comp resolution; the press file stays the original


def _cover_data_uri(path: str) -> tuple[str, dict]:
    """Embed the frame as a pinned data URI, and report what was embedded.

    The renderer resolves a filesystem path to ``file://``, which headless
    Chromium refuses to load as a sub-resource — the page renders a broken-image
    glyph and the render still reports ok. So the bytes travel INSIDE the
    document. A press-resolution TIFF is also not a web format, so the comp
    carries a downscaled PNG preview while ``meta`` keeps the original's path
    and sha256: the artifact you look at and the file that goes to press are
    both identified, and neither is mistaken for the other.
    """
    import base64                                   # noqa: PLC0415
    original_sha = _sha256(path)
    from PIL import Image                           # noqa: PLC0415
    with Image.open(path) as im:
        w, h = im.size
        im = im.convert("RGB")
        scale = min(1.0, COMP_MAX_SIDE / max(w, h))
        if scale < 1.0:
            im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                           Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
    payload = buf.getvalue()
    uri = "data:image/png;base64," + base64.b64encode(payload).decode("ascii")
    return uri, {
        "press_file": path,
        "press_file_sha256": original_sha,
        "press_file_px": [w, h],
        "comp_preview_px": [round(w * scale), round(h * scale)],
        "comp_preview_bytes": len(payload),
        "note": "the embedded preview is a downscaled PNG for the comp render; "
                "the press file is the original named above",
    }


P_SAFE = SAFE
P_LIVE_W = LIVE_W
PLATE_X, PLATE_Y = P_SAFE, 104.0
# The frame is reserved WHOLE: guardrail 7 forbids a crop that changes a
# photograph's meaning, and a landscape frame bled across a portrait cover is
# exactly such a crop. So the photograph sits as a plate inside the ink, at its
# own aspect, and the INK adapts — never the frame.
PLATE_ASPECT, PLATE_ASPECT_SOURCE = _image_aspect(COVER_IMAGE)

# The front type block: (text, style, size, leading, space-before, id-suffix).
# Its height is SUMMED, not guessed, and the block is anchored to the live
# bottom — so the imprint cannot walk off the trim as the title size changes.
FRONT_STACK = [
    (TITLE, "title", S_TITLE, S_TITLE * 1.04, 0.0, "title"),
    (SUBTITLE, "subtitle", S_SUB, S_SUB * 1.5, 16.0, "subtitle"),
    (SLOT_PHOTOGRAPHERS, "creditSlot", S_CREDIT, S_CREDIT * 1.5, 32.0,
     "photographers"),
    (f"EDITED BY {SLOT_EDITOR}", "creditSlot", S_CREDIT, S_CREDIT * 1.5, 0.0,
     "editor"),
    (FRONT_CREDIT, "credit", S_CREDIT, S_CREDIT * 1.5, 10.0, "cover-credit"),
    (SLOT_IMPRINT, "microSlot", S_MICRO, S_MICRO * 1.6, 18.0, "imprint"),
]
FRONT_STACK_H = sum(before + lead for _, _, _, lead, before, _ in FRONT_STACK)
FRONT_STACK_TOP = PANEL_H - P_SAFE - FRONT_STACK_H

# The plate is then the largest rectangle OF THE FRAME'S OWN ASPECT that fits
# the band between the head margin and the type block, flush-left on the
# measure. A wider-than-3:2 frame loses height, a portrait frame loses width;
# neither loses pixels.
PLATE_GAP_MIN = 56.0
PLATE_BAND_H = FRONT_STACK_TOP - PLATE_Y - PLATE_GAP_MIN
if PLATE_BAND_H < 200.0:
    raise AssertionError(
        f"the type block has grown into the plate: only {PLATE_BAND_H:.1f} px "
        f"of band left. Reduce TITLE_FILL.")
PLATE_W = round(min(P_LIVE_W, PLATE_BAND_H * PLATE_ASPECT), 1)
PLATE_H = round(PLATE_W / PLATE_ASPECT, 1)
PLATE_B = PLATE_Y + PLATE_H

# The plate's own specification, optically centred inside the reservation.
PLATE_SPEC = [
    ("PHOTOGRAPH RESERVED · NOT REPRODUCED", "plateHead", 14.0, 22.0, 0.0,
     "plate-head"),
    (None, "plateBody", 12.5, 19.0, 10.0, "plate-caption"),      # wrapped
    (f"© {CREDIT_LINE} · {ACCOLADE}", "plateBody", 12.5, 19.0, 8.0,
     "plate-credit"),
    ("LICENCE PENDING — CLEAR WITH AP IMAGES BEFORE PRESS", "plateHead", 11.0,
     18.0, 10.0, "plate-licence"),
]
PLATE_SPEC_INSET = 34.0
PLATE_CAPTION = f"{PICK['description']} {PHOTO_PLACE}, {PHOTO_DATE}."


def draw_front(pg, ox: float, oy: float, w: float, *, prefix: str,
               plate_spec: bool = True) -> dict:
    """Draw the front panel into ``pg`` with its top-left at (ox, oy)."""
    k = w / PANEL_W

    def X(u: float) -> float:
        return ox + u * k

    def Y(v: float) -> float:
        return oy + v * k

    pg.rect([ox, oy, w, PANEL_H * k], fill="ink", decorative=True)
    pg.rect([X(PLATE_X), Y(PLATE_Y), PLATE_W * k, PLATE_H * k],
            fill="plate", decorative=True)

    if COVER_IMAGE is not None:
        # The frame, whole, at its own aspect, with NOTHING printed over it.
        pg.image([X(PLATE_X), Y(PLATE_Y), PLATE_W * k, PLATE_H * k],
                 COVER_ASSET, id=f"{prefix}-photograph",
                 preserve_aspect_ratio=True,
                 alt=f"{PICK['description']} {PHOTO_PLACE}, {PHOTO_DATE}. "
                     f"Photograph {CREDIT_LINE}.")
        return {"type_bottom": _draw_front_type(pg, X, Y, k, prefix),
                "live_bottom": Y(PANEL_H - P_SAFE)}

    if plate_spec:
        # The reservation reads as a reservation: a hairline inside the plate
        # and its own specification set into it. Nothing here is a picture.
        pg.rect([X(PLATE_X) + 1, Y(PLATE_Y) + 1, PLATE_W * k - 2, 0.8],
                fill="rule", decorative=True)
        pg.rect([X(PLATE_X) + 1, Y(PLATE_B) - 1.8, PLATE_W * k - 2, 0.8],
                fill="rule", decorative=True)
        spec_w = PLATE_W - 2 * PLATE_SPEC_INSET
        cap_lines = wrap_text(PLATE_CAPTION, width=spec_w * WRAP_SAFETY,
                              font_family=GROTESK, font_size=12.5,
                              variation_settings=W_BOOK)
        spec_h = sum(before + (lead * len(cap_lines) if txt is None else lead)
                     for txt, _, _, lead, before, _ in PLATE_SPEC)
        spec = Column(pg, X(PLATE_X + PLATE_SPEC_INSET),
                      Y(PLATE_Y + (PLATE_H - spec_h) / 2.0), spec_w, k)
        for txt, style, size, lead, before, suffix in PLATE_SPEC:
            if txt is None:
                spec.para(PLATE_CAPTION, style, size, lead=lead, measure=spec_w,
                          before=before, oid=f"{prefix}-{suffix}")
            else:
                spec.line(txt, style, size, lead=lead, before=before,
                          oid=f"{prefix}-{suffix}")

    return {"type_bottom": _draw_front_type(pg, X, Y, k, prefix),
            "live_bottom": Y(PANEL_H - P_SAFE)}


def _draw_front_type(pg, X, Y, k: float, prefix: str) -> float:
    """The front type block: one quiet flush-left stack (C27), bottom-anchored."""
    c = Column(pg, X(P_SAFE), Y(FRONT_STACK_TOP), P_LIVE_W, k)
    for txt, style, size, lead, before, suffix in FRONT_STACK:
        c.line(txt, style, size, lead=lead, before=before,
               oid=f"{prefix}-{suffix}")
    return c.y


# --------------------------------------------------------------------------- #
# §8 · The document
# --------------------------------------------------------------------------- #
THUMB_HEIGHTS = [1080.0, 400.0, 260.0, 168.0, 108.0]

SHEET_W, SHEET_H = 1122.0, 1588.0      # A3 portrait at 96 px/in


def build():
    d = DocumentBuilder(title="Iraq 2003 — photobook jacket")
    d.describe(
        "Full jacket flat (back flap / back / spine / front / front flap) for a "
        "documentary photography monograph on the 2003 invasion of Iraq, "
        "reconstructed from a cover brief and its companion image-selection "
        "record. Achromatic ink system, one grotesque, a whole-frame plate "
        "reservation for a licensed AP photograph, and the conformance sheets "
        "that close every dimension the brief names.")

    for name, value in INKS.items():
        d.define_color(name, value)

    global COVER_ASSET
    cover_meta = None
    if COVER_IMAGE is not None:
        uri, cover_meta = _cover_data_uri(COVER_IMAGE)
        COVER_ASSET = d.define_asset(
            "cover_photograph", uri, kind="image",
            hash=cover_meta["press_file_sha256"])

    def ts(name, *, size, color="bone", var=W_BOOK, track=None, lh=None,
           family=GROTESK, align=None):
        # Every text object in this document is ONE already-resolved line, so
        # `wrap=False` is right for all of them — and it is what stops the
        # renderer from folding an overlong line into a clipped second one.
        if track is not None:
            TRACKING[name] = track
        d.define_text_style(
            name, font_family=family, font_size=size, color=color,
            font_variation_settings=var, wrap=False,
            **({"letter_spacing": track} if track is not None else {}),
            **({"line_height": lh} if lh is not None else {}),
            **({"align": align} if align is not None else {}))

    # C26 — the differentiated roles. Title / subtitle / photographer credit /
    # editor / imprint, each separated by size, weight and colour, never by a
    # second family.
    ts("title", size=S_TITLE, var=W_TITLE, track=TITLE_TRACK, lh=1.0)
    ts("subtitle", size=S_SUB, var=W_BOOK, track=1.5)
    ts("credit", size=S_CREDIT, var=W_MED, track=1.0)
    ts("creditSlot", size=S_CREDIT, color="grey", var=W_MED, track=1.0)
    ts("micro", size=S_MICRO, var=W_MED, track=1.3)
    ts("microSlot", size=S_MICRO, color="grey", var=W_MED, track=1.3)
    ts("plateHead", size=12.0, color="mark", var=W_SEMI, track=1.4)
    ts("plateBody", size=12.5, color="mark", var=W_BOOK, lh=1.5)
    ts("spineTitle", size=S_SPINE, var=W_TITLE, track=0.8)
    ts("spineCredit", size=S_SMALL, var=W_MED, track=1.8)
    ts("spineImprint", size=S_MICRO, color="grey", var=W_MED, track=1.8)
    ts("body", size=S_SMALL, var=W_BOOK, lh=BODY_LH)
    ts("bodyDim", size=S_SMALL, color="grey", var=W_BOOK, lh=BODY_LH)
    ts("label", size=S_MICRO, var=W_SEMI, track=1.8)
    ts("labelDim", size=S_MICRO, color="grey", var=W_SEMI, track=1.8)
    ts("isbnText", size=S_MICRO, var=W_MED, track=1.0)
    ts("hri", size=S_MICRO, var=W_MED, track=3.6, align="center")
    ts("mark", size=9.0, color="mark", var=W_MED, track=1.4)
    # the specification sheets
    ts("sheetTitle", size=30.0, color="sheetInk", var=W_SEMI, track=0.4)
    ts("sheetHead", size=13.0, color="sheetInk", var=W_SEMI, track=1.9)
    ts("sheetKey", size=11.5, color="sheetInk", var=W_SEMI, track=0.6)
    ts("sheetBody", size=11.5, color="sheetInk", var=W_BOOK, lh=1.5)
    ts("sheetDim", size=11.5, color="sheetDim", var=W_BOOK, lh=1.5)
    ts("sheetMicro", size=9.5, color="sheetDim", var=W_BOOK, lh=1.5)
    ts("thumbLabel", size=13.0, color="sheetInk", var=W_SEMI, track=1.4)
    ts("thumbMicro", size=10.0, color="sheetDim", var=W_BOOK, lh=1.45)

    modules, code13 = ean13_modules(ISBN12)
    if decode_ean13(modules) != code13:          # PALS: verify, do not trust
        raise AssertionError("EAN-13 encode/decode round trip failed")
    addon = ean5_modules(PRICE5)
    isbn_pretty = (f"ISBN {code13[:3]}-{code13[3]}-{code13[4:10]}-"
                   f"{code13[10:12]}-{code13[12]}")

    d.meta(
        show_construction=True,      # the comp shows its own crop/fold furniture
        reconstruction={
            "brief": os.path.relpath(BRIEF_PATH, ROOT),
            "brief_sha256": BRIEF_SHA,
            "image_selection": os.path.relpath(IMAGE_PATH, ROOT),
            "image_selection_sha256": IMAGE_SHA,
            "photograph": (f"supplied: {COVER_IMAGE}" if COVER_IMAGE else
                           "RESERVED, NOT REPRODUCED — copyrighted (AP); the "
                           "brief forbids an AI-generated or composited image "
                           "presented as documentary"),
            "plate_aspect": PLATE_ASPECT_SOURCE,
            "working_title_rejected": WORKING_TITLE,
            "unresolved_slots": [SLOT_PHOTOGRAPHERS, SLOT_EDITOR, SLOT_IMPRINT,
                                 SLOT_DESIGNER, SLOT_PRICE, "jacket copy",
                                 "contributor and editor biographies"],
            "isbn": "978-1-234567-89-7 is the conventional dummy, not a real ISBN",
        },
        print_spec={
            "trim_in": [TRIM_W, TRIM_H], "spine_in": SPINE_IN,
            "flap_in": FLAP_IN, "bleed_in": BLEED_IN, "safe_in": SAFE_IN,
            "ppi": PPI, "flat_in": [round(W / PPI, 4), round(H / PPI, 4)],
            "plate_aspect": PLATE_ASPECT_SOURCE,
            "plate_px": [PLATE_W, PLATE_H],
            "photograph_asset": cover_meta,
        },
        disclaimer=IMAGE["disclaimer"])

    # ------------------------------------------------------------------ #
    # PAGE 1 — the jacket flat
    # ------------------------------------------------------------------ #
    pg = d.page("jacket", canvas={"size": [W, H], "units": "px"},
                coordinate_mode="absolute")

    pg.layer("stock")
    pg.rect([0, 0, W, H], fill="ink", decorative=True)

    # --- front panel ---
    pg.layer("front")
    draw_front(pg, FRONT_X, TRIM_T, PANEL_W, prefix="front")

    # --- spine: reads top-to-bottom, the Anglo-American convention ---------
    # ObjBase.rotation is ignored by the SVG renderer, so the rotation has to
    # come from a transformed frame.
    pg.layer("spine")
    spine_tf = Mat3.translate(SPINE_X + SPINE_W / 2.0, LIVE_T) @ Mat3.rotate(90)
    with pg.grouped(transform=spine_tf, id="spine") as sp:
        run = PANEL_H - 2 * SAFE
        sp.text([0, -SPINE_W / 2.0, 300, SPINE_W], TITLE,
                id="spine-title", style="spineTitle")
        sp.text([330, -SPINE_W / 2.0, 300, SPINE_W], SLOT_EDITOR,
                id="spine-editor", style="spineImprint")
        sp.text([run - 150, -SPINE_W / 2.0, 150, SPINE_W], SLOT_IMPRINT,
                id="spine-imprint", style="spineImprint")

    # --- back panel -------------------------------------------------------
    # A1 asks for a quiet, single-image focus: "one authoritative frame, not a
    # montage". The brief permits a second image on the back; this design
    # declines it, so the back stays typographic and the cover keeps exactly
    # one photograph. The decision is recorded on sheet 1.
    pg.layer("back")
    BACK_L = BACK_X + SAFE
    b = Column(pg, BACK_L, LIVE_T + 26, LIVE_W)
    b.line("IRAQ 2003", "credit", S_CREDIT, lead=S_CREDIT * 1.5, oid="back-title")
    b.line(SUBTITLE, "microSlot", S_MICRO, lead=S_MICRO * 1.7, before=4.0,
           oid="back-subtitle")

    # The jacket copy is not written yet, and inventing marketing prose about a
    # real war would be the exact failure the brief's guardrails describe. What
    # IS specified is the typographic well it must fit: measure, leading, depth.
    b.gap(46)
    b.line("JACKET COPY — TO BE WRITTEN", "labelDim", S_MICRO,
           lead=S_MICRO * 1.8, oid="back-copy-label")
    well_top = b.y + 10
    WELL_LINES, WELL_LEAD = 11, S_SMALL * BODY_LH
    MEASURE_CH = 66
    for i in range(WELL_LINES):
        # each rule is one set line of the specified measure and leading
        wfrac = 1.0 if i < WELL_LINES - 1 else 0.58
        pg.rect([BACK_L, well_top + i * WELL_LEAD, LIVE_W * 0.86 * wfrac, 1.0],
                fill="rule", decorative=True)
    b.y = well_top + WELL_LINES * WELL_LEAD
    b.line(f"{MEASURE_CH} characters  ·  {S_SMALL:.1f}/{WELL_LEAD:.1f} px  "
           f"·  {WELL_LINES} lines maximum", "microSlot", S_MICRO,
           lead=S_MICRO * 1.8, before=10.0, oid="back-copy-spec")

    b.gap(44)
    b.line("PHOTOGRAPHS BY", "label", S_MICRO, lead=S_MICRO * 1.8,
           oid="back-photographers-label")
    b.line(SLOT_PHOTOGRAPHERS, "creditSlot", S_SMALL, lead=S_SMALL * 1.6,
           before=4.0, oid="back-photographers")
    b.line("EDITED BY", "label", S_MICRO, lead=S_MICRO * 1.8, before=16.0,
           oid="back-editor-label")
    b.line(SLOT_EDITOR, "creditSlot", S_SMALL, lead=S_SMALL * 1.6, before=4.0,
           oid="back-editor")
    b.line("COVER PHOTOGRAPH", "label", S_MICRO, lead=S_MICRO * 1.8, before=16.0,
           oid="back-cover-label")
    b.line(f"{CREDIT_LINE}, {PHOTO_DATE}", "body", S_SMALL, lead=S_SMALL * 1.6,
           before=4.0, oid="back-cover-credit")
    b.line("Full caption on the front flap.", "bodyDim", S_SMALL,
           lead=S_SMALL * 1.6, oid="back-cover-caption-ref")

    # --- the ISBN symbol, foot of the back panel --------------------------
    sym_w = len(modules) * BAR_MODULE
    gap_w = 10 * BAR_MODULE
    total_w = sym_w + gap_w + len(addon) * BAR_MODULE
    bx = BACK_L
    colophon_y = LIVE_B - 14
    imprint_y = colophon_y - 30
    hri_bottom = imprint_y - 16
    by = hri_bottom - 18 - BAR_H - GUARD_EXTRA

    pg.text([bx, by - 32, total_w, 20], isbn_pretty, id="back-isbn",
            style="isbnText")

    # Bars must sit on a light substrate to scan, so the symbol gets its own
    # bone panel — the one place the ink system inverts, and it inverts for a
    # machine, not for a reader.
    quiet = 9 * BAR_MODULE
    pg.rect([bx - quiet, by - 8, total_w + 2 * quiet,
             BAR_H + GUARD_EXTRA + 30], fill="bone", decorative=True)

    def bars_dark(mstring, x0, y0, height, *, long_at=()):
        i = 0
        while i < len(mstring):
            if mstring[i] == "0":
                i += 1
                continue
            j = i
            while j < len(mstring) and mstring[j] == "1":
                j += 1
            extra = GUARD_EXTRA if any(i <= q < j for q in long_at) else 0.0
            pg.rect([x0 + i * BAR_MODULE, y0, (j - i) * BAR_MODULE,
                     height + extra], fill="ink", decorative=True)
            i = j

    guards = tuple(range(0, 3)) + tuple(range(45, 50)) + tuple(range(92, 95))
    bars_dark(modules, bx, by, BAR_H, long_at=guards)
    bars_dark(addon, bx + sym_w + gap_w, by, BAR_H * 0.78)

    hri_y = by + BAR_H + GUARD_EXTRA - 2
    d.define_text_style("hriDark", font_family=GROTESK, font_size=S_MICRO,
                        color="ink", font_variation_settings=W_MED,
                        letter_spacing=3.4, align="center")
    pg.text([bx - quiet, hri_y, quiet, 16], code13[0], id="hri-lead",
            style="hriDark", overlap="allowed")
    pg.text([bx + 3 * BAR_MODULE, hri_y, 42 * BAR_MODULE, 16], code13[1:7],
            id="hri-left", style="hriDark", overlap="allowed")
    pg.text([bx + 50 * BAR_MODULE, hri_y, 42 * BAR_MODULE, 16], code13[7:],
            id="hri-right", style="hriDark", overlap="allowed")
    pg.text([bx + sym_w + gap_w, by - 16, len(addon) * BAR_MODULE, 16],
            PRICE5, id="hri-addon", style="hriDark", overlap="allowed")

    pg.text([BACK_L, imprint_y - 8, LIVE_W, 20], SLOT_IMPRINT,
            id="back-imprint", style="microSlot", overlap="allowed")
    pg.text([BACK_L, colophon_y - 8, LIVE_W, 20],
            f"Jacket design by {SLOT_DESIGNER}.  Printed in [ COUNTRY ].",
            id="back-colophon", style="microSlot", overlap="allowed")

    # --- front flap: the honest caption (guardrail 7) ----------------------
    pg.layer("front-flap")
    FF_L = FFLAP_X + SAFE
    f = Column(pg, FF_L, LIVE_T + 20, FLAP_LIVE_W)
    f.line(SLOT_PRICE, "microSlot", S_MICRO, lead=S_MICRO * 1.8,
           oid="fflap-price")
    f.gap(40)
    f.line("JACKET COPY — TO BE WRITTEN", "labelDim", S_MICRO,
           lead=S_MICRO * 1.8, oid="fflap-copy-label")
    ff_well = f.y + 8
    for i in range(14):
        wfrac = 1.0 if i != 13 else 0.62
        pg.rect([FF_L, ff_well + i * WELL_LEAD, FLAP_LIVE_W * wfrac, 1.0],
                fill="rule", decorative=True)
    f.y = ff_well + 14 * WELL_LEAD

    f.gap(40)
    f.line("COVER PHOTOGRAPH", "label", S_MICRO, lead=S_MICRO * 1.9,
           oid="fflap-caption-label")
    f.para(CAPTION, "bodyDim", 11.0, lead=17.0, measure=FLAP_LIVE_W,
           before=8.0, oid="fflap-caption")
    f.para(f"Licensing: {LICENCE_PATH}", "bodyDim", 9.5, lead=15.0,
           measure=FLAP_LIVE_W, before=14.0, oid="fflap-licence")

    # --- back flap ---------------------------------------------------------
    pg.layer("back-flap")
    BF_L = BFLAP_X + SAFE
    g = Column(pg, BF_L, LIVE_T + 20, FLAP_LIVE_W)
    g.line("THE EDITOR", "label", S_MICRO, lead=S_MICRO * 1.9,
           oid="bflap-editor-label")
    g.line(SLOT_EDITOR, "creditSlot", S_FLAP, lead=S_FLAP * 1.7, before=6.0,
           oid="bflap-editor")
    bio_top = g.y + 10
    for i in range(6):
        pg.rect([BF_L, bio_top + i * WELL_LEAD,
                 FLAP_LIVE_W * (1.0 if i < 5 else 0.5), 1.0],
                fill="rule", decorative=True)
    g.y = bio_top + 6 * WELL_LEAD

    g.gap(34)
    g.line("THE PHOTOGRAPHERS", "label", S_MICRO, lead=S_MICRO * 1.9,
           oid="bflap-photographers-label")
    g.line(SLOT_PHOTOGRAPHERS, "creditSlot", S_FLAP, lead=S_FLAP * 1.7,
           before=6.0, oid="bflap-photographers")
    bio2_top = g.y + 10
    for i in range(6):
        pg.rect([BF_L, bio2_top + i * WELL_LEAD,
                 FLAP_LIVE_W * (1.0 if i < 5 else 0.66), 1.0],
                fill="rule", decorative=True)
    g.y = bio2_top + 6 * WELL_LEAD

    g.gap(40)
    g.para(f"Cover photograph © {CREDIT_LINE.split(' / ')[0]} / {RIGHTS}. "
           f"All rights reserved.", "bodyDim", 10.0, lead=15.5,
           measure=FLAP_LIVE_W, oid="bflap-rights")
    g.para(f"Jacket design by {SLOT_DESIGNER}.", "bodyDim", 10.0, lead=15.5,
           measure=FLAP_LIVE_W, before=10.0, oid="bflap-design")
    g.para(f"{SLOT_IMPRINT}  ·  [ ADDRESS ]  ·  [ WEBSITE ]",
           "bodyDim", 10.0, lead=15.5, measure=FLAP_LIVE_W, before=10.0,
           oid="bflap-imprint")

    # --- production furniture (non-printing datum layer) -------------------
    pg.layer("marks", role="construction")
    TICK, MW = 22.0, 0.7
    for x0 in (BACK_X, RIGHT_X):
        for y0 in (TRIM_T, TRIM_B):
            pg.rect([x0 - (TICK if x0 > W / 2 else 0), y0 - MW / 2, TICK, MW],
                    fill="mark", decorative=True, construction=True)
            pg.rect([x0 - MW / 2, y0 - (TICK if y0 > H / 2 else 0), MW, TICK],
                    fill="mark", decorative=True, construction=True)
    # Fold ticks live in the bleed, which is only 12 px deep here — so they are
    # 10 px long, not 22. A mark that needs more room than the bleed has is a
    # mark that gets trimmed off.
    FOLD_TICK = 10.0
    for fold in FOLDS:
        dashed_v(pg, fold, TRIM_T, TRIM_B)
        for y0 in (1.0, TRIM_B + 1.0):
            pg.rect([fold - MW / 2, y0, MW, FOLD_TICK], fill="mark",
                    decorative=True, construction=True)
    labels = [(BFLAP_X, FLAP_W, "BACK FLAP"), (BACK_X, PANEL_W, "BACK"),
              (SPINE_X, SPINE_W, "SPINE"), (FRONT_X, PANEL_W, "FRONT"),
              (FFLAP_X, FLAP_W, "FRONT FLAP")]
    for x0, wid, name in labels:
        pg.text([x0 + 4, TRIM_T + 5, wid - 8, 13], name, style="mark",
                construction=True, overlap="allowed")
    pg.text([BLEED, 1, W - 2 * BLEED, 12],
            f"FLAT {W / PPI:.3f} × {H / PPI:.3f} in  ·  TRIM "
            f"{TRIM_W} × {TRIM_H} in  ·  SPINE {SPINE_IN} in  "
            f"·  FLAP {FLAP_IN} in  ·  BLEED {BLEED_IN} in  ·  "
            f"SAFE {SAFE_IN} in", style="mark", construction=True,
            overlap="allowed")

    # ------------------------------------------------------------------ #
    # PAGE 2 — the front cover alone, as it is met
    # ------------------------------------------------------------------ #
    cover = d.page("cover", canvas={"size": [PANEL_W, PANEL_H], "units": "px"},
                   coordinate_mode="absolute")
    draw_front(cover, 0, 0, PANEL_W, prefix="cover")

    # ------------------------------------------------------------------ #
    # PAGE 3 — the retail-thumbnail ladder (a deliverable constraint)
    # ------------------------------------------------------------------ #
    # "type and image must survive down to a retail thumbnail". This draws the
    # SAME parametric front at five real pixel heights, so the claim is tested
    # rather than asserted.
    GUT, PAD_T, PAD_B, PAD_R = 44.0, 116.0, 150.0, 130.0
    widths = [h * PANEL_W / PANEL_H for h in THUMB_HEIGHTS]
    ladder_w = sum(widths) + GUT * (len(widths) + 1) + PAD_R
    ladder_h = PAD_T + max(THUMB_HEIGHTS) + PAD_B
    tn = d.page("thumbnails",
                canvas={"size": [ladder_w, ladder_h], "units": "px"},
                coordinate_mode="absolute")
    tn.layer("sheet")
    tn.rect([0, 0, ladder_w, ladder_h], fill="paper", decorative=True)
    t = Column(tn, GUT, 34, ladder_w - 2 * GUT)
    t.line("RETAIL THUMBNAIL SURVIVAL", "sheetHead", 13.0, lead=20.0,
           oid="tn-head")
    t.line("The same parametric front panel at five real pixel heights. The "
           "title's cap height is measured, not estimated.", "sheetMicro",
           10.0, lead=16.0, before=6.0, oid="tn-sub")

    x = GUT
    for i, (hh, ww) in enumerate(zip(THUMB_HEIGHTS, widths)):
        k = ww / PANEL_W
        y = PAD_T + (max(THUMB_HEIGHTS) - hh)
        tn.layer(f"thumb-{i}")
        draw_front(tn, x, y, ww, prefix=f"tn{i}", plate_spec=(k > 0.45))
        cap = S_TITLE * k * CAP_EM
        lab = Column(tn, x, y + hh + 14, max(ww, 150.0))
        lab.line(f"{int(hh)} px tall", "thumbLabel", 13.0, lead=19.0,
                 oid=f"tn{i}-label")
        lab.line(f"{int(round(k * 100))} %  ·  title cap {cap:.1f} px",
                 "thumbMicro", 10.0, lead=15.0, oid=f"tn{i}-metric")
        lab.line("legible" if cap >= 6.0 else "title lost", "thumbMicro", 10.0,
                 lead=15.0, oid=f"tn{i}-verdict")
        x += ww + GUT

    # ------------------------------------------------------------------ #
    # PAGES 4-5 — the conformance sheets
    # ------------------------------------------------------------------ #
    _sheet_one(d)
    _sheet_two(d)
    _sheet_three(d)
    return d


# --------------------------------------------------------------------------- #
# §9 · Conformance sheets — every id the brief names, closed against the design
# --------------------------------------------------------------------------- #
COL_GUT = 46.0
SHEET_M = 64.0
COL_W = (SHEET_W - 2 * SHEET_M - COL_GUT) / 2.0


def _sheet(d, pid: str, title: str, strap: str):
    pg = d.page(pid, canvas={"size": [SHEET_W, SHEET_H], "units": "px"},
                coordinate_mode="absolute")
    pg.layer("sheet")
    pg.rect([0, 0, SHEET_W, SHEET_H], fill="paper", decorative=True)
    head = Column(pg, SHEET_M, SHEET_M, SHEET_W - 2 * SHEET_M)
    head.line(title, "sheetTitle", 30.0, lead=38.0, oid=f"{pid}-title")
    head.para(strap, "sheetMicro", 10.0, lead=15.0,
              measure=SHEET_W - 2 * SHEET_M, before=8.0, oid=f"{pid}-strap")
    pg.rect([SHEET_M, head.y + 12, SHEET_W - 2 * SHEET_M, 1.4],
            fill="sheetDim", decorative=True)
    return pg, head.y + 34


def _rows(col: Column, pg, items, *, key_w: float, pid: str, tag: str):
    """A two-column definition list: key in semibold, body wrapped beside it.

    Each row is lowered as ONE group. That is not cosmetic: a flat run of
    absolutely-positioned text on a regular grid is exactly what the static
    audit's tabular-box-model rule flags, and it is right to — these rows ARE
    table rows, so they are authored as rows.
    """
    for n, (key, body) in enumerate(items):
        with pg.grouped(id=f"{pid}-{tag}-{n}") as row:
            rc = Column(row, col.x, col.y, col.w)
            row.rect([col.x, col.y, col.w, 0.6], fill="sheetDim",
                     decorative=True)
            rc.gap(9)
            top = rc.y
            rc.line(key, "sheetKey", 11.0, lead=15.5, w=key_w,
                    oid=f"{pid}-{tag}-{n}-k")
            key_bottom = rc.y
            rc.y, rc.x, rc.w = top, col.x + key_w + 14, col.w - key_w - 14
            rc.para(body, "sheetBody", 11.0, lead=15.5, measure=rc.w,
                    oid=f"{pid}-{tag}-{n}-v")
        col.y = max(rc.y, key_bottom) + 11


def _sheet_one(d):
    pid = "sheet-conformance"
    pg, y0 = _sheet(
        d, pid, "Jacket specification",
        f"Iraq 2003 · reconstructed from {os.path.basename(BRIEF_PATH)} "
        f"(sha256 {BRIEF_SHA[:16]}…) and {os.path.basename(IMAGE_PATH)} "
        f"(sha256 {IMAGE_SHA[:16]}…). Every dimension id below is the "
        f"brief's own; the right-hand column is where the design discharges it.")

    left = Column(pg, SHEET_M, y0, COL_W)
    left.line("THE NAMING DECISION", "sheetHead", 13.0, lead=20.0,
              oid=f"{pid}-h-naming")
    left.gap(6)
    _rows(left, pg, [
        ("Working title", f"“{WORKING_TITLE}” — REJECTED. The "
         f"brief's own naming_flag: ‘Gulf War’ conventionally denotes "
         f"1990–91. A 2003 monograph under that name is a retail and "
         f"library mis-shelving waiting to happen."),
        ("Set title", f"“{TITLE}” over “{SUBTITLE_SENTENCE}”. The title "
         f"carries the year; the subtitle carries the country and the months. "
         f"Confirm with the publisher before press — the brief requires it."),
    ], key_w=104, pid=pid, tag="naming")

    left.gap(20)
    left.line("INK — ACHROMATIC BY RULE", "sheetHead", 13.0, lead=20.0,
              oid=f"{pid}-h-ink")
    left.gap(6)
    ratios = [(f"{a} on {b}", f"{contrast_ratio(a, b):.2f}:1 — {role}")
              for a, b, role in CONTRAST_GATE]
    _rows(left, pg, [
        ("Rule", "Every colour the design contributes is a grey (r = g = b). "
         "The strongest reading of C28's ‘no patriotic red/white/blue’ "
         "and C30's ‘no added saturation’ is not low chroma but zero "
         "chroma: all hue on the finished jacket belongs to the photograph. "
         "Asserted at build time, not eyeballed."),
        ("Values", "  ·  ".join(f"{n} {v}" for n, v in INKS.items())),
    ] + [("Contrast", f"{k}  =  {v}") for k, v in ratios[:2]],
        key_w=104, pid=pid, tag="ink")

    left.gap(20)
    left.line("TYPE", "sheetHead", 13.0, lead=20.0, oid=f"{pid}-h-type")
    left.gap(6)
    _rows(left, pg, [
        ("C18 face", "Archivo — a serious Roman grotesque with a variable "
         "weight axis. No stencil, no camo, no distressed face; C26's four "
         "roles separate by weight, size and colour inside ONE family, which is "
         "what C33's austerity requires."),
        ("C20 weight", f"Title set at wght 500 — medium, not black. It is "
         f"solved to fill {int(TITLE_FILL * 100)} % of the {int(LIVE_W)} px "
         f"measure ({S_TITLE:.1f} px, cap {S_TITLE * CAP_EM:.1f} px) while the "
         f"plate fills 100 % of it. The type states; it does not compete."),
        ("Scale", f"Modular, base {SCALE_BASE:.0f} ratio {SCALE_RATIO}: "
         f"{S_MICRO:.1f} / {S_SMALL:.1f} / {S_CREDIT:.1f} / {S_SUB:.1f} / "
         f"{S_SPINE:.1f} px. The display size is the one exception — it is "
         f"solved from the measure and therefore cannot sit on the scale."),
        ("C27 alignment", "Flush-left, one quiet block per panel, hanging on "
         "each panel's safe edge. No centred-symmetrical monumentality, which "
         "the brief reads as memorial-grand or propagandistic."),
    ], key_w=104, pid=pid, tag="type")

    right = Column(pg, SHEET_M + COL_W + COL_GUT, y0, COL_W)
    right.line("PRINT", "sheetHead", 13.0, lead=20.0, oid=f"{pid}-h-print")
    right.gap(6)
    _rows(right, pg, [
        ("Trim", f"{TRIM_W} × {TRIM_H} in (241 × 286 mm) — a "
         f"large-format monograph, per the brief's ‘larger photobook "
         f"trim’."),
        ("Spine", f"{SPINE_IN} in. 256 pp on 170 gsm matt art (caliper "
         f"~0.15 mm/leaf) = 19.2 mm, plus two 3.0 mm board-and-cloth turns = "
         f"25.2 mm = 0.992 in, rounded UP to the next 1/16 in. A spine that "
         f"measures short is a reprint."),
        ("Flat", f"{W / PPI:.3f} × {H / PPI:.3f} in over back flap / back "
         f"/ spine / front / front flap, {BLEED_IN} in bleed, {SAFE_IN} in "
         f"safe. Crop and fold marks are on a non-printing construction layer."),
        ("Barcode", f"{isbn_display()} — a spec-conformant EAN-13 with an "
         f"EAN-5 add-on, encoded from the GS1 parity tables and DECODED back "
         f"before it was drawn. It sits on its own bone panel: bars need a "
         f"light substrate to scan, and that is the one place the ink system "
         f"inverts."),
    ], key_w=104, pid=pid, tag="print")

    right.gap(20)
    right.line("MUST INCLUDE", "sheetHead", 13.0, lead=20.0,
               oid=f"{pid}-h-must")
    right.gap(6)
    _rows(right, pg, [
        (BRIEF["must_include"][0], "Front panel, spine, back panel. ‘IRAQ "
         "2003’ plus a subtitle naming the country and the months."),
        (BRIEF["must_include"][1], "Front panel, spine, back panel, back flap "
         "— SLOT, unresolved."),
        (BRIEF["must_include"][2], "Front panel (line 1 of the credit block), "
         "back panel, back flap — SLOT for the contributor list; the COVER "
         f"photographer is real and set: {CREDIT_LINE}."),
        (BRIEF["must_include"][3], "Front panel foot, spine foot, back panel "
         "foot, back flap — SLOT, unresolved."),
    ], key_w=170, pid=pid, tag="must")

    right.gap(20)
    right.line("DELIVERABLE CONSTRAINTS", "sheetHead", 13.0, lead=20.0,
               oid=f"{pid}-h-deliv")
    right.gap(6)
    _rows(right, pg, [
        ("Jacket", "Front, spine, back AND both flaps — the flaps are not "
         "optional here, because guardrail 7 puts the photograph's honest "
         "caption on one of them."),
        ("Second image", "DECLINED. The brief permits one on the back; A1 asks "
         "for ‘one authoritative frame, not a montage that dilutes "
         "witness’. The back stays typographic and the jacket carries "
         "exactly one photograph."),
        ("Thumbnail", "Tested, not asserted: sheet 3 draws the same parametric "
         "front panel at five real pixel heights and measures the title's cap "
         "height at each."),
        ("Press", "Single-ink near-black ground (#131313, not a four-colour "
         "rich black), no filter effects anywhere on the jacket, and the "
         "photograph's tonality to be proofed on the actual stock."),
    ], key_w=104, pid=pid, tag="deliv")


def isbn_display() -> str:
    _, code13 = ean13_modules(ISBN12)
    return (f"ISBN {code13[:3]}-{code13[3]}-{code13[4:10]}-{code13[10:12]}-"
            f"{code13[12]} (the conventional dummy, not a real ISBN)")


def _sheet_two(d):
    pid = "sheet-dimensions"
    pg, y0 = _sheet(
        d, pid, "The brief's dimensions, closed",
        "Every id the brief names, its authored value, and the construction "
        "that discharges it. Left: the mood profile. Right: the design "
        "direction, the tensions the brief asks the design to hold, and the "
        "list of things it says to avoid.")

    left = Column(pg, SHEET_M, y0, COL_W)
    left.line("MOOD — AFFECTIVE PROFILE", "sheetHead", 13.0, lead=20.0,
              oid=f"{pid}-h-mood")
    left.gap(6)
    DISCHARGE = {
        "C35": "The plate is the only event on the panel; the design performs "
               "no emotion on top of it. No scrim, no overprint, no gradient.",
        "A6": "The chosen frame humanises through paternal tenderness rather "
              "than gore (see the image record). The setting is ink and space.",
        "C34": "Grotesque, flush-left, no ornament, a caption in the reportage "
               "register — a journalistic object, not a decorative one.",
        "C33": "There is no rule, no flourish, no texture, no effect anywhere "
               "on the jacket. Hierarchy is carried by size, weight and space.",
        "C28": "Achromatic BY RULE and asserted at build time: every design "
               "colour is r = g = b, so no flag coding is representable.",
        "C29": "Deferred to the frame, as the brief asks. The ground is a "
               "low-key #131313; the plate's tonality is set by the licensed "
               "file and proofed on stock.",
        "C30": "Zero chroma from the design. No saturation is added anywhere; "
               "nothing is graded.",
        "C31": f"Bone on near-black measures "
               f"{contrast_ratio(BONE, INK):.2f}:1 and the title runs at "
               f"wght 500, not black — legible, not shouting.",
        "A1": "One plate, whole, uncropped. No second image on the back, no "
              "montage, no collage.",
        "A5": "Whole-frame plate, hard flush-left type, honest caption with "
              "date and place — the reportage monograph idiom.",
        "A7": "A conventional monograph jacket: plate over title over credits. "
              "Nothing here is trend-driven.",
        "C36": "The plate is RESERVED for a licensed documentary frame and "
               "prints its own licence path. Nothing is drawn, traced or "
               "generated into it.",
        "C32": "No stylisation is possible — the design never touches the "
               "photograph's pixels.",
        "C18": "Archivo, a serious Roman grotesque. No stencil, no grunge.",
        "C20": f"wght 500 at {S_TITLE:.1f} px, filling "
               f"{int(TITLE_FILL * 100)} % of a measure the plate fills wholly.",
        "C26": "Title / disambiguating subtitle / photographers / editor / "
               "COVER PHOTOGRAPHER / imprint — six roles, one family.",
        "C27": "Flush-left on every one of the five panels.",
    }
    mood_rows = [
        (f"{dim['id']}  {dim['name']}",
         f"{dim['value']}. → {DISCHARGE.get(dim['id'], 'not discharged')}")
        for dim in BRIEF["mood"]["affective_profile"]]
    _rows(left, pg, mood_rows, key_w=168, pid=pid, tag="mood")

    right = Column(pg, SHEET_M + COL_W + COL_GUT, y0, COL_W)
    right.line("DESIGN DIRECTION", "sheetHead", 13.0, lead=20.0,
               oid=f"{pid}-h-dir")
    right.gap(6)
    dir_rows = [
        (f"{dim['id']}  {dim['name']}",
         f"{dim['value']}. → {DISCHARGE.get(dim['id'], 'not discharged')}")
        for dim in BRIEF["design_direction"]]
    _rows(right, pg, dir_rows, key_w=168, pid=pid, tag="dir")

    right.gap(18)
    right.line("TENSIONS HELD", "sheetHead", 13.0, lead=20.0,
               oid=f"{pid}-h-tension")
    right.gap(6)
    _rows(right, pg, [(f"{i + 1}", t) for i, t
                      in enumerate(BRIEF["mood"]["tensions_to_hold"])],
          key_w=18, pid=pid, tag="tension")

    right.gap(18)
    right.line("WHAT THE BRIEF SAYS TO AVOID", "sheetHead", 13.0, lead=20.0,
               oid=f"{pid}-h-avoid")
    right.gap(6)
    _rows(right, pg, [(f"{i + 1}", a) for i, a
                      in enumerate(BRIEF["mood"]["avoid"])],
          key_w=18, pid=pid, tag="avoid")


def _sheet_three(d):
    pid = "sheet-guardrails"
    pg, y0 = _sheet(
        d, pid, "Guardrails, the photograph, and what is open",
        "The brief's seven editorial and ethical guardrails, each answered by a "
        "construction; the image-selection record that the plate reserves; and "
        "the list of everything this design does NOT decide.")

    right = Column(pg, SHEET_M, y0, COL_W)
    right.line("EDITORIAL AND ETHICAL GUARDRAILS", "sheetHead", 13.0, lead=20.0,
               oid=f"{pid}-h-guard")
    right.gap(6)
    GUARD_ANSWER = [
        "The selected frame is an act of care inside captivity, not a person's "
        "worst moment used as a hook. Reproduced whole.",
        "No grading, no filter, no effect touches it — the design cannot "
        "reach the pixels. Nothing is made beautiful.",
        "The triumphalist frames (Firdos Square, ‘shock and awe’, "
        "‘Mission Accomplished’) and the atrocity frames were both "
        "rejected in the selection record. See the image record opposite.",
        "The plate is RESERVED, never faked. Date, place, maker and rights "
        "holder are printed into the reservation and onto the flap.",
        f"{CREDIT_LINE} is set on the front panel, the back panel, the front "
        f"flap and the back flap. It is the only real name on this jacket.",
        "Achromatic by rule and asserted at build time — flag coding is "
        "not representable in this ink system.",
        "The full caption runs UNCUT on the front flap, and the frame is "
        "reserved whole: a landscape photograph bled across a portrait cover "
        "would be exactly the meaning-changing crop this forbids.",
    ]
    # The guardrail is quoted WHOLE from the brief and the answer follows it.
    # Slicing a guardrail down to a column label truncated the sentence, which
    # is the one thing a compliance record must not do.
    _rows(right, pg, [
        (str(i + 1), f"{g} → {a}") for i, (g, a)
        in enumerate(zip(BRIEF["editorial_ethical_guardrails"], GUARD_ANSWER))
    ], key_w=18, pid=pid, tag="guard")

    far = Column(pg, SHEET_M + COL_W + COL_GUT, y0, COL_W)
    far.line("THE PHOTOGRAPH", "sheetHead", 13.0, lead=20.0,
             oid=f"{pid}-h-photo")
    far.gap(6)
    _rows(far, pg, [
        ("Selected", f"{PICK['description']}"),
        ("Maker / rights", f"{PHOTOGRAPHER} · {RIGHTS} · credit line "
                           f"“{CREDIT_LINE}”"),
        ("When / where", f"{PHOTO_DATE} · {PHOTO_PLACE}"),
        ("Standing", ACCOLADE),
        ("Licence", LICENCE_PATH),
        ("The tension", PICK["one_tension"]),
        ("Alternates", "  ·  ".join(
            f"{a.get('photographer', a.get('rights_holder', '?'))}"
            for a in IMAGE["alternatives"])),
        ("Rejected", "  ·  ".join(
            f"{r['image'].split(',')[0]}" for r in IMAGE["rejected_and_why"])),
    ], key_w=104, pid=pid, tag="photo")

    far.gap(18)
    far.line("OPEN — NOT DECIDED BY THIS DESIGN", "sheetHead", 13.0,
             lead=20.0, oid=f"{pid}-h-open")
    far.gap(6)
    _rows(far, pg, [
        ("The photograph",
         (f"SUPPLIED — drawn from {os.path.basename(COVER_IMAGE)}. Licensing is "
          f"a separate question and is NOT settled by a file being present: "
          f"clear it with AP Images before press."
          if COVER_IMAGE else
          "NOT reproduced. Copyrighted (AP), and the brief forbids a generated "
          "or composited substitute. The plate is a specified reservation — set "
          "IRAQ2003_COVER_IMAGE, or drop the file at _tmp/cover-photograph.tif, "
          "and it renders whole with no further edit.")),
        ("Plate aspect", f"{PLATE_ASPECT:.4f} — {PLATE_ASPECT_SOURCE}. The "
         f"plate is the largest rectangle of THAT aspect which fits the band "
         f"above the type ({PLATE_W:.0f} × {PLATE_H:.0f} px); the ink adapts to "
         f"the frame, never the frame to the ink."),
        ("Slots", "  ·  ".join([SLOT_PHOTOGRAPHERS, SLOT_EDITOR,
                                     SLOT_IMPRINT, SLOT_DESIGNER, SLOT_PRICE,
                                     "[ JACKET COPY ]", "[ BIOGRAPHIES ]"])),
        ("ISBN / price", "Dummy symbol. Replace with the real ISBN and price "
         "band; re-run, the bars are encoded not drawn."),
        ("Provenance", f"Photo facts {IMAGE['provenance']['photo_facts']} "
         f"Re-verify with the rights holder before use. Framework ids: "
         f"{IMAGE['provenance']['framework_ids_validated_against']}."),
        ("Disclaimer", BRIEF["disclaimer"]),
    ], key_w=104, pid=pid, tag="open")


# --------------------------------------------------------------------------- #
# §10 · The gates
# --------------------------------------------------------------------------- #
def check_chroma() -> list[tuple[str, str]]:
    """Every declared colour must be strictly achromatic (r == g == b)."""
    bad = []
    for name, hexv in INKS.items():
        r, g, b = (int(hexv[i:i + 2], 16) for i in (1, 3, 5))
        if not (r == g == b):
            bad.append((name, hexv))
    return bad


def check_contrast(floor: float = 4.5) -> list[tuple[str, str, str, float]]:
    return [(a, b, role, contrast_ratio(a, b))
            for a, b, role in CONTRAST_GATE if contrast_ratio(a, b) < floor]


if __name__ == "__main__":
    from frameforge_sdk.validate import validate_static_rules

    print(f"brief  sha256 {BRIEF_SHA}")
    print(f"image  sha256 {IMAGE_SHA}")
    if COVER_IMAGE:
        print(f"photograph: {COVER_IMAGE} (sha256 {_sha256(COVER_IMAGE)[:16]}…)")
        print("  LICENSING IS NOT SETTLED BY THE FILE BEING PRESENT — clear "
              "book-cover use with AP Images before press.")
    else:
        print("photograph: NOT SUPPLIED — the plate renders as a reservation. "
              "Set IRAQ2003_COVER_IMAGE=<path> to place the licensed frame.")
    print(f"plate: {PLATE_W:.0f} × {PLATE_H:.0f} px, aspect "
          f"{PLATE_ASPECT:.4f} — {PLATE_ASPECT_SOURCE}")

    chroma_bad = check_chroma()
    print(f"chroma gate: {'PASS' if not chroma_bad else 'FAIL ' + str(chroma_bad)}"
          f" — {len(INKS)} colours, all r==g==b")
    contrast_bad = check_contrast()
    for a, b, role, ratio in [(a, b, r, contrast_ratio(a, b))
                              for a, b, r in CONTRAST_GATE]:
        print(f"  contrast {a} on {b} = {ratio:5.2f}:1  {role}")
    print(f"contrast gate: {'PASS' if not contrast_bad else 'FAIL'} (floor 4.5:1)")

    mods, code = ean13_modules(ISBN12)
    print(f"barcode gate: EAN-13 {code} -> {len(mods)} modules, decoded back as "
          f"{decode_ean13(mods)}")

    print(f"title solved: {S_TITLE:.1f} px, cap {S_TITLE * CAP_EM:.1f} px, "
          f"fills {TITLE_FILL:.0%} of the {LIVE_W:.0f} px measure")
    for hh in THUMB_HEIGHTS:
        k = hh / PANEL_H
        cap = S_TITLE * k * CAP_EM
        print(f"  thumbnail {int(hh):>4} px tall -> title cap {cap:5.2f} px "
              f"{'legible' if cap >= 6.0 else 'TITLE LOST'}")

    if chroma_bad or contrast_bad:
        raise SystemExit("design gates failed")

    out = os.path.join(ROOT, "_tmp", "iraq-2003-jacket")
    os.makedirs(out, exist_ok=True)
    doc = build()
    report = validate_static_rules(doc.build_dict())
    for issue in report.issues:
        print(f"{issue.severity:8} {issue.rule_id}: {issue.message}")
    print(f"static rules: {'ok' if report.ok else 'FAILED'} "
          f"({len(report.issues)} issue(s))")
    path = os.path.join(out, "iraq-2003-jacket.fg.yaml")
    doc.write(path)
    print(f"wrote {path}")
