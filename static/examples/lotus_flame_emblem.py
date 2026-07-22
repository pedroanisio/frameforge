"""Lotus flame emblem — authored from FrameForge primitives (clone-task v2).

The trace pipeline (vectorize + shading + refine) reproduces the reference
pixel-faithfully but yields ~900 traced objects. This client is the OTHER
discipline: the same emblem authored as a SEMANTIC document — ~40 deliberate
objects in named layers (wings, core, star), every petal a parametric
calligraphic stroke (``sdk.outline.stroke_outline`` over a cubic S-spine with
a flame width profile), painted with exact user-space gradients (A1 ``line``
form), rim-shaded by self-clipped inner strokes (the A2 idiom, authored by
hand), glossed by feathered opacity-stop highlights. Bilateral symmetry is
structural: the right wing IS the mirrored left wing with the pink palette.

Anchor coordinates and colour families were MEASURED from the reference
(connected-component tips/bases + sampled hues); the geometry between the
anchors is authored, not traced.

Run: ``uv run python static/examples/lotus_flame_emblem.py``
(writes to ``_tmp/lotus-flame-emblem/clone-v2*``).
"""
from __future__ import annotations

import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk import DocumentBuilder
from frameforge.sdk.outline import stroke_outline
from frameforge.sdk.paint import linear_gradient, radial_gradient

W = H = 1254
AX = 627.0                      # bilateral mirror axis

# ---- measured anchor + palette table (left wing; right = mirror + pink) ----
# S-spines: base → c1 (pulls up along the V) → c2 (throws the belly outward)
# → tip (hooks back up-inward) — the serpentine flame the reference draws.
PETALS = [
    # id     base            c1              c2              tip            w    peak
    ("p1", (590, 1000), (490, 700), (348, 280), (420, 112), 128, 0.38),
    ("p2", (608, 1085), (470, 850), (268, 450), (345, 240), 138, 0.40),
    ("p3", (620, 1130), (490, 1015), (208, 735), (172, 528), 132, 0.38),
    ("p4", (626, 1158), (515, 1110), (252, 900), (126, 702), 118, 0.38),
]
BLUE = {
    "p1": ("#aee8fa", "#1b9cf9", "#1b23c8"),
    "p2": ("#c3f0fb", "#2ab5f9", "#2a1ed0"),
    "p3": ("#a9e9f9", "#0b9df6", "#2f2fd0"),
    "p4": ("#93dff6", "#0e84f2", "#4520cc"),
}
PINK = {
    "p1": ("#f6c3e0", "#f042f2", "#4a10a0"),
    "p2": ("#fbd2e8", "#f25cf0", "#6a14b8"),
    "p3": ("#f9c0e2", "#f236d2", "#8812d0"),
    "p4": ("#f4aad4", "#ea28b8", "#9a18dc"),
}
RIM = {"L": "#0c1668", "R": "#40086e", "C": "#2c0d72"}
LAVENDER = ("#efeafb", "#c3b4ea", "#5b21a0")
SPEAR = ("#d8cdf3", "#9a7ce6", "#5c19cc")


def _cubic(b, c1, c2, t, n=64):
    """Sample a cubic Bézier base→tip into a point list."""
    pts = []
    for i in range(n + 1):
        s = i / n
        u = 1.0 - s
        pts.append((
            u**3 * b[0] + 3 * u * u * s * c1[0] + 3 * u * s * s * c2[0] + s**3 * t[0],
            u**3 * b[1] + 3 * u * u * s * c1[1] + 3 * u * s * s * c2[1] + s**3 * t[1],
        ))
    return pts


def _flame(peak):
    """Asymmetric flame profile: fat below ``peak``, a long thin neck above.

    Rising side eases in fast (sin^0.6 — mass in the lower third); the falling
    side decays slowly-then-sharply (cos-ramp^1.35) so the upper half is the
    reference's whip-thin neck rather than a symmetric leaf."""
    def profile(t):
        if t <= peak:
            x = min(max(t / peak, 0.0), 1.0)
            return math.sin(x * math.pi / 2.0) ** 0.6
        x = min(max((t - peak) / (1.0 - peak), 0.0), 1.0)
        return math.cos(x * math.pi / 2.0) ** 0.9
    return profile


def _mirror(p):
    return (2.0 * AX - p[0], p[1])


def _offset_spine(pts, frac):
    """Shift a spine perpendicular by ``frac`` px (for the gloss ridge)."""
    out = []
    for i, (x, y) in enumerate(pts):
        j = min(i + 1, len(pts) - 1)
        k = max(i - 1, 0)
        dx, dy = pts[j][0] - pts[k][0], pts[j][1] - pts[k][1]
        n = math.hypot(dx, dy) or 1.0
        out.append((x - dy / n * frac, y + dx / n * frac))
    return out


def _mix(a, b, t):
    """Blend two hex colours (the deep-body stop between mid and base)."""
    av = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    bv = [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(av, bv))


def _petal(layer, pid, spine_pts, w, peak, tip_col, mid_col, base_col, rim_col,
           gloss_side):
    """One petal: body + self-clipped rim stroke + edge-hugging gloss ridge."""
    tip, base = spine_pts[-1], spine_pts[0]
    body = stroke_outline(
        spine_pts, w, profile=_flame(peak), cap="round", join="round",
        id=pid,
        fill=linear_gradient(
            [(tip_col, "0%"), (mid_col, "38%"),
             (_mix(mid_col, base_col, 0.55), "72%"), (base_col, "100%")],
            line=[list(tip), list(base)]),
    )
    layer.add(body)
    layer.add({
        "type": "path", "d": body["d"], "decorative": True,
        "stroke": rim_col, "stroke_style": {"stroke_width": 9},
        "style": {"clip_path": {"shape": "path", "args": {"d": body["d"]}}},
    })
    # gloss: a crisp rim light hugging the inner edge of the UPPER half —
    # offset scales with the LOCAL width and the ridge is self-clipped to the
    # body so it can never escape the thin neck
    n = len(spine_pts)
    lo, hi = int(n * 0.38), int(n * 0.95)
    prof = _flame(peak)
    gloss_pts = []
    for i in range(lo, hi):
        t = i / (n - 1)
        local = _offset_spine(spine_pts[max(0, i - 1):i + 2],
                              gloss_side * w * prof(t) * 0.26)
        gloss_pts.append(local[1] if len(local) > 1 else local[0])
    gloss = stroke_outline(
        gloss_pts, w * 0.10, profile=_flame(0.5), cap="round", join="round",
        decorative=True,
        fill=linear_gradient(
            [("#ffffff", "0%", 0.0), ("#ffffff", "30%", 1.0),
             ("#ffffff", "75%", 0.65), ("#ffffff", "100%", 0.0)],
            line=[list(gloss_pts[0]), list(gloss_pts[-1])]),
    )
    gloss["style"] = {"clip_path": {"shape": "path", "args": {"d": body["d"]}}}
    layer.add(gloss)


def _star(layer):
    """The 4-point sparkle: concave-edged vertical diamond + inner rim."""
    cx, cy = 626.0, 176.0
    ry_t, ry_b, rx = 128.0, 120.0, 78.0
    pinch = 0.30                                    # concavity of the edges
    top, bot = (cx, cy - ry_t), (cx, cy + ry_b)
    left, right = (cx - rx, cy + 6), (cx + rx, cy + 6)
    q = lambda p: (cx + (p[0] - cx) * pinch, cy + (p[1] - cy) * pinch)  # noqa: E731
    d = (f"M {top[0]:.1f} {top[1]:.1f} "
         f"Q {q(((cx + rx * .5), cy - ry_t * .5))[0]:.1f} {q(((cx + rx * .5), cy - ry_t * .5))[1]:.1f} "
         f"{right[0]:.1f} {right[1]:.1f} "
         f"Q {q(((cx + rx * .5), cy + ry_b * .5))[0]:.1f} {q(((cx + rx * .5), cy + ry_b * .5))[1]:.1f} "
         f"{bot[0]:.1f} {bot[1]:.1f} "
         f"Q {q(((cx - rx * .5), cy + ry_b * .5))[0]:.1f} {q(((cx - rx * .5), cy + ry_b * .5))[1]:.1f} "
         f"{left[0]:.1f} {left[1]:.1f} "
         f"Q {q(((cx - rx * .5), cy - ry_t * .5))[0]:.1f} {q(((cx - rx * .5), cy - ry_t * .5))[1]:.1f} "
         f"{top[0]:.1f} {top[1]:.1f} Z")
    layer.add({
        "type": "path", "d": d, "id": "star",
        "fill": radial_gradient(
            [("#f3eafc", "0%"), ("#c08bf8", "40%"), ("#8434f2", "100%")],
            at=[cx, cy - 16], radius=118, focal=[cx - 16, cy - 38]),
        "glow": {"blur": 12, "color": "#a05df3"},
    })
    layer.add({
        "type": "path", "d": d, "decorative": True,
        "stroke": "#5b1cae", "stroke_style": {"stroke_width": 6},
        "style": {"clip_path": {"shape": "path", "args": {"d": d}}},
    })


def build():
    doc = DocumentBuilder(title="Lotus flame emblem — authored primitives", lang="en")
    page = doc.page("emblem", canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute")
    page.layer("bg").rect([0, 0, W, H], fill="#000000")

    # wings first: their bases tuck BEHIND the centre column
    for side, palette, sgn in (("L", BLUE, 1.0), ("R", PINK, -1.0)):
        wing = page.layer(f"wing-{side}")
        for pid, base, c1, c2, tip, w, peak in PETALS:
            pts = _cubic(base, c1, c2, tip)
            if side == "R":
                pts = [_mirror(p) for p in pts]
            tip_c, mid_c, base_c = palette[pid]
            _petal(wing, f"{side}-{pid}", pts, w, peak, tip_c, mid_c, base_c,
                   RIM[side], gloss_side=sgn)

    core = page.layer("core")
    # the two lavender inner petals: S-flames — bellies out, thin necks, tips
    # hooking back in to converge over the black diamond void
    lav_spine = _cubic((622, 1110), (552, 930), (497, 545), (597, 312))
    for side, sgn in (("L", 1.0), ("R", -1.0)):
        pts = lav_spine if side == "L" else [_mirror(p) for p in lav_spine]
        _petal(core, f"lavender-{side}", pts, 112, 0.40,
               *LAVENDER, RIM["C"], gloss_side=sgn)
    # the central spear in TWO lobes with the void between them: the body
    # flares from the V to a point under the void; the peak is the small
    # flame between the converging lavender tips.
    body_spine = _cubic((625, 1160), (626, 1000), (627, 800), (627, 640))
    _petal(core, "spear-body", body_spine, 88, 0.32, *SPEAR, RIM["C"],
           gloss_side=1.0)
    peak_spine = _cubic((627, 455), (627, 408), (627, 358), (627, 300))
    core.add(stroke_outline(
        peak_spine, 46, profile=_flame(0.5), cap="round", join="round",
        id="spear-peak",
        fill=linear_gradient([(SPEAR[0], "0%"), (SPEAR[1], "60%"),
                              (SPEAR[2], "100%")],
                             line=[[627, 300], [627, 455]]),
    ))

    _star(page.layer("star"))
    return doc.build()


if __name__ == "__main__":
    import pathlib

    from frameforge.sdk.io import serialize

    out = pathlib.Path(ROOT) / "_tmp" / "lotus-flame-emblem"
    out.mkdir(parents=True, exist_ok=True)
    (out / "clone-v2.fg.yaml").write_text(serialize(build(), format="yaml"),
                                          encoding="utf-8")
    print(f"wrote {out / 'clone-v2.fg.yaml'}")
