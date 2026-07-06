"""libfy_letter.py — "Libfy": a one-page US-Letter broadside.

A visual concept of *libfy* — the extract -> curate -> compound flywheel — set
above a polished typesetting of the complete definition.

Primitives only: rect / circle / line / polyline / polygon / text. No symbols,
widgets, components, charts, or library helpers — the vocabulary of a document
about reuse is, deliberately, the bare shapes.

Craft (after *The Letter & the Hue*):
  - closed palette, one duty each: warm paper, warm ink, one grey, one rubric.
  - one Garalde serif (EB Garamond, + its true small-caps) carries the prose and
    hero; one grotesque (Inter) carries the machine-voice tags. Both resolve
    exactly in the frameforge font runtime — no silent substitution.
  - sizes on a 1.333 modular scale; body measure ~62ch; hierarchy in tone first.

Drawn by Claude Opus 4.8 via Claude Code.
"""
from __future__ import annotations

import math

from framegraph.sdk import DocumentBuilder, paint
from framegraph.sdk.macros import span

# ---------------------------------------------------------------- palette ----
# One paper, one ink, one quiet grey, one rubric accent. Every hue has a duty;
# a stranger would show. Contrast on paper (WCAG): ink 14.8:1, grey 4.9:1,
# rubric 5.2:1 — all clear the 4.5:1 body floor.
PAPER = "#F3EEE4"   # warm ground (~62% of the field)
INK = "#211C16"     # warm near-black — never pure #000
GREY = "#6E6656"    # the second rank: labels, dek, colophon
HAIR = "#CDC5B4"    # faint rules, rests
RUBRIC = "#A6442E"  # the one accent — the loop, and one word of emphasis

# ----------------------------------------------------------- type + scale ----
GAR = "EB Garamond"
SC = "EB Garamond SC"   # true small caps, not a faux transform
INTER = "Inter"

BASE, RATIO = 15.5, 1.333
def s(step: int) -> float:            # modular scale
    return round(BASE * (RATIO ** step), 1)

HERO = s(5)     # 65.2  — the title, the single darkest+largest mass
DEK = s(1)      # 20.7  — the standfirst, and the coda
BODY = s(0)     # 15.5  — prose, node words
SMALL = s(-1)   # 11.6  — kicker, descriptors, arc label, center caption
MICRO = 9.5     # colophon (the one sub-scale micro line)

ts = paint.text_style

# ------------------------------------------------------------- geometry ----
W, H = 816, 1056                      # US Letter @ 96dpi
ML, MR = 84, 732                      # content margins (side)
CX, CY, R, NR = 408, 464, 132, 48     # flywheel centre / ring radius / node radius


def arc_points(a0: float, a1: float, n: int = 24) -> list[list[float]]:
    """Sample a ring arc (degrees) into a polyline of n+1 points."""
    out = []
    for i in range(n + 1):
        t = math.radians(a0 + (a1 - a0) * i / n)
        out.append([round(CX + R * math.cos(t), 2), round(CY + R * math.sin(t), 2)])
    return out


def arrow_head(a_end: float, length: float = 12.0, half: float = 5.6) -> list[list[float]]:
    """A filled triangle at the arc's arriving end, aimed along clockwise travel."""
    t = math.radians(a_end)
    tip = (CX + R * math.cos(t), CY + R * math.sin(t))
    d = (-math.sin(t), math.cos(t))                # clockwise tangent (increasing angle)
    base = (tip[0] - d[0] * length, tip[1] - d[1] * length)
    perp = (-d[1], d[0])
    c1 = (base[0] + perp[0] * half, base[1] + perp[1] * half)
    c2 = (base[0] - perp[0] * half, base[1] - perp[1] * half)
    return [[round(x, 2), round(y, 2)] for x, y in (tip, c1, c2)]


def node_xy(angle: float) -> tuple[float, float]:
    t = math.radians(angle)
    return CX + R * math.cos(t), CY + R * math.sin(t)


# node angle, ring colour+weight, word colour, word, one-line descriptor, side
NODES = [
    (-90, INK, 1.6, INK, "Construct", "finished or ongoing work", "above"),
    (30, RUBRIC, 2.0, RUBRIC, "Libfy", "extract reusable capability", "below"),
    (150, INK, 1.6, INK, "Library", "curated parts + know-how", "below"),
]
GAP = 24  # angular clearance so an arc starts/ends just off a node

# --------------------------------------------------------------- document ----
doc = DocumentBuilder(title="Libfy — a definition", profile="letter")
page = doc.page("broadside", canvas={"size": [W, H], "units": "px"},
                coordinate_mode="absolute")

# --- ground -----------------------------------------------------------------
page.layer("paper")
page.rect([0, 0, W, H], fill=PAPER)

# --- the flywheel arcs (below the nodes) ------------------------------------
page.layer("arcs")
stroke_arc = paint.stroke(2.4, color=RUBRIC, cap="round", join="round")
# each arc runs clockwise from just past one node to just before the next
for start_ang in (-90, 30, 150):
    page.polyline(arc_points(start_ang + GAP, start_ang + 120 - GAP), **stroke_arc)
    page.polygon(arrow_head(start_ang + 120 - GAP), fill=RUBRIC)

# --- node disks (cover the arc ends) ----------------------------------------
page.layer("shapes")
for angle, ring, rw, _wc, *_ in NODES:
    nx, ny = node_xy(angle)
    page.circle([round(nx, 2), round(ny, 2)], NR, fill=PAPER,
                **paint.stroke(rw, color=ring))

# --- all type + rules (top) -------------------------------------------------
page.layer("ink")

# masthead
page.text([ML, 86, 560, 18], "A Definition — the compounding of capability",
          style=ts(SMALL, family=SC, color=GREY, letter_spacing=1.4))
page.text([ML, 108, 460, 86], "Libfy",
          style=ts(HERO, family=GAR, weight=700, color=INK))
page.text([ML, 200, 560, 28],
          "What you build once, made ready to build with again.",
          style=ts(DEK, family=GAR, italic=True, color=GREY, line_height=1.2))
page.line([ML, 250], [MR, 250], **paint.stroke(1.1, color=GREY))

# flywheel labels
for angle, _ring, _rw, wcol, word, desc, side in NODES:
    nx, ny = node_xy(angle)
    page.text([round(nx - 62), round(ny - 11), 124, 22], word,
              style=ts(BODY, family=SC, color=wcol, align="center", letter_spacing=0.4))
    dy = ny - NR - 26 if side == "above" else ny + NR + 10
    page.text([round(nx - 96), round(dy), 192, 14], desc,
              style=ts(SMALL, family=INTER, color=GREY, align="center", letter_spacing=0.2))

# the payoff, at the hub
page.text([CX - 92, 450, 184, 16], "Capability",
          style=ts(SMALL, family=SC, color=RUBRIC, align="center", letter_spacing=1.8))
page.text([CX - 92, 469, 184, 16], "compounds",
          style=ts(SMALL, family=SC, color=RUBRIC, align="center", letter_spacing=1.8))

# the return arc, named
page.text([150, 386, 118, 16], "accelerates",
          style=ts(SMALL, family=GAR, italic=True, color=RUBRIC, align="right"))

# --- the polished definition -------------------------------------------------
page.line([ML, 616], [MR, 616], **paint.stroke(1.0, color=HAIR))
COL_X, COL_W = 168, 460   # measure ~62 ch

page.text([COL_X, 640, COL_W, 54],
          [span("Libfy", font=SC, color=RUBRIC, letter_spacing=0.3),
           span(" is the practice of extracting reusable capability from constructive "
                "work — whether finished or still under way.", font=GAR, color=INK)],
          style=ts(BODY, family=GAR, color=INK, line_height=1.5))

page.text([COL_X, 702, COL_W, 88],
          "Its output is a library: a curated, annotated system of reusable elements, "
          "ranged from concrete parts — components, aggregates, assets — to know-how: "
          "patterns, rules, methods, and checklists.",
          style=ts(BODY, family=GAR, color=INK, line_height=1.5))

page.text([COL_X, 804, COL_W, 80],
          [span("A library accelerates every future construction; and because whatever "
                "is built from a library inherits its structure, that work is, in turn, "
                "easier to ", font=GAR, color=INK),
           span("libfy", font=GAR, italic=True, color=INK),
           span(".", font=GAR, color=INK)],
          style=ts(BODY, family=GAR, color=INK, line_height=1.5))

page.text([COL_X, 900, COL_W, 30], "So capability compounds.",
          style=ts(DEK, family=GAR, italic=True, color=RUBRIC, align="center"))

# --- colophon ----------------------------------------------------------------
page.line([ML, 986], [MR, 986], **paint.stroke(1.0, color=HAIR))
page.text([ML, 994, 320, 14], "FrameGraph v2  ·  docs/spec/libfy.md",
          style=ts(MICRO, family=INTER, color=GREY, letter_spacing=0.3))
page.text([MR - 380, 994, 380, 14],
          "EB Garamond & Inter  ·  primitives only  ·  drawn by Claude Opus 4.8",
          style=ts(MICRO, family=INTER, color=GREY, align="right", letter_spacing=0.3))


def build():
    return doc


if __name__ == "__main__":
    import os
    out = os.environ.get("OUTPUT_YAML_PATH", "libfy_letter.fg.yaml")
    doc.write(out, fail_on_error=True)
    print("wrote", out)
