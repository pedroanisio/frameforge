#!/usr/bin/env python3
"""Five documents with nothing visually in common.

The critique: everything I produced was the same costume — navy #0b1020, the
same four accents, Inter + Charter, rounded corners, gradients. That is one
house style applied five ways, not range.

This builds FIVE page sections that share an identical content skeleton (a
label, a headline, a type specimen, three shapes, a footer) so the ONLY thing
that changes is the visual identity:

  A. Swiss      — white, black, one red; grotesque; hard grid; no radius, no gradient
  B. Editorial  — cream paper, sepia ink, terracotta; serif display; classic
  C. Brutalist  — near-black, bone, acid yellow; monospace; heavy borders; raw
  D. Pastel     — mint paper, blush/sky/lilac; rounded sans; soft, light, friendly
  E. Noir-lux   — aubergine, gold; serif; thin gold rules; dark but NOT navy

Each identity is a dict of tokens (palette, fonts, shape language). One render
function consumes the identity — so the divergence is data, not five rewrites.

Run from the repository root::

    uv run python examples/visual_identities.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, serialize  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1000, 720
CANVAS = {"size": [W, H], "units": "px"}

# Stacks lead with families this environment actually has installed (verified
# via fc-list), then fall back to web-safe names and the CSS generic, so the
# type difference renders in previews instead of collapsing to one sans.
GROTESQUE = ["DejaVu Sans", "Helvetica Neue", "Arial", "sans-serif"]
SERIF = ["Bitstream Charter", "Noto Serif", "DejaVu Serif", "Georgia", "serif"]
MONO = ["DejaVu Sans Mono", "Fira Mono", "Courier New", "monospace"]
ROUNDED = ["Fira Sans", "Nunito", "Verdana", "sans-serif"]

# Each identity: palette + fonts + a shape language (radius / gradient / borders).
IDENTITIES = [
    {
        "key": "swiss", "label": "A · International Typographic",
        "headline": "Order before\nornament.",
        "bg": "#ffffff", "fg": "#111111", "muted": "#7a7a7a", "accent": "#e3261f",
        "panel": "#f0f0f0", "border": "#111111",
        "head_font": GROTESQUE, "body_font": GROTESQUE, "spec_font": GROTESQUE,
        "head_size": 78, "tracking": -2, "radius": 0, "use_gradient": False,
        "border_w": 0, "accent_kind": "bar",
    },
    {
        "key": "editorial", "label": "B · Editorial / Magazine",
        "headline": "A quiet\nconfidence.",
        "bg": "#f3ead9", "fg": "#2c2118", "muted": "#8a7a64", "accent": "#bf5a36",
        "panel": "#e8dcc4", "border": "#cdbfa3",
        "head_font": SERIF, "body_font": SERIF, "spec_font": SERIF,
        "head_size": 72, "tracking": -1, "radius": 2, "use_gradient": False,
        "border_w": 1, "accent_kind": "rule",
    },
    {
        "key": "brutalist", "label": "C // BRUTALIST.SYS",
        "headline": "RAW\nMATERIAL.",
        "bg": "#141410", "fg": "#ECEAD7", "muted": "#8f8d77", "accent": "#E8FF1A",
        "panel": "#1f1f18", "border": "#ECEAD7",
        "head_font": MONO, "body_font": MONO, "spec_font": MONO,
        "head_size": 70, "tracking": 1, "radius": 0, "use_gradient": False,
        "border_w": 2, "accent_kind": "box",
    },
    {
        "key": "pastel", "label": "D · Soft Pop",
        "headline": "Gentle, but\nnot shy.",
        "bg": "#eaf6ef", "fg": "#33424a", "muted": "#7d94a0", "accent": "#ff8fab",
        "panel": "#ffffff", "border": "#d6e7dd",
        "head_font": ROUNDED, "body_font": ROUNDED, "spec_font": ROUNDED,
        "head_size": 70, "tracking": -1, "radius": 28, "use_gradient": True,
        "grad": ["#bde0c8", "#f6c9d4", "#c9d6f6"],
        "border_w": 0, "accent_kind": "round",
    },
    {
        "key": "noir", "label": "E · Noir Luxe",
        "headline": "After hours.",
        "bg": "#1c1230", "fg": "#f2e9d8", "muted": "#a193b4", "accent": "#e8b04b",
        "panel": "#261a3d", "border": "#e8b04b",
        "head_font": SERIF, "body_font": SERIF, "spec_font": SERIF,
        "head_size": 76, "tracking": 0, "radius": 4, "use_gradient": True,
        "grad": ["#2a1c44", "#1c1230"],
        "border_w": 1, "accent_kind": "rule",
    },
]


def render_identity(b: DocumentBuilder, idn: dict) -> None:
    k = idn["key"]

    def sc(name):  # scoped style name so identities don't collide
        return f"{k}_{name}"

    b.define_color(sc("bg"), idn["bg"])
    b.define_color(sc("fg"), idn["fg"])
    b.define_color(sc("muted"), idn["muted"])
    b.define_color(sc("accent"), idn["accent"])
    b.define_color(sc("panel"), idn["panel"])
    b.define_color(sc("border"), idn["border"])

    b.define_text_style(sc("label"), font_family=idn["body_font"], font_size=15,
                        font_weight=700, color=sc("muted"), letter_spacing=2,
                        text_transform="uppercase")
    b.define_text_style(sc("head"), font_family=idn["head_font"],
                        font_size=idn["head_size"], font_weight=800, color=sc("fg"),
                        letter_spacing=idn["tracking"], line_height=0.98)
    b.define_text_style(sc("spec"), font_family=idn["spec_font"], font_size=64,
                        font_weight=700, color=sc("accent"))
    b.define_text_style(sc("body"), font_family=idn["body_font"], font_size=16,
                        color=sc("fg"), line_height=1.5)
    b.define_text_style(sc("foot"), font_family=idn["body_font"], font_size=13,
                        color=sc("muted"), letter_spacing=1)
    b.define_text_style(sc("chip"), font_family=idn["body_font"], font_size=14,
                        font_weight=700, color=sc("bg"), align="center")

    r = idn["radius"]
    page = b.page(f"id-{k}", canvas=CANVAS, coordinate_mode="absolute")

    # background
    page.layer("bg")
    if idn["use_gradient"] and idn.get("grad"):
        stops = idn["grad"]
        n = len(stops)
        page.rect([0, 0, W, H], fill={
            "kind": "linear", "angle": 135,
            "stops": [{"color": c, "position": f"{int(i*100/(n-1))}%"}
                      for i, c in enumerate(stops)]})
    else:
        page.rect([0, 0, W, H], fill=sc("bg"))

    page.layer("frame")
    # editorial/brutalist get an outer keyline; swiss gets a top hairline rule
    if idn["border_w"]:
        page.rect([40, 40, W - 80, H - 80], fill=None,
                  stroke=sc("border"), stroke_style={"width": idn["border_w"]},
                  radius=r)
    else:
        page.rect([72, 96, W - 144, 2], fill=sc("fg"))

    # label
    page.text([72, 64, W - 144, 20], idn["label"], style=sc("label"))

    # headline (two lines, authored explicitly so wrapping never reflows the mood)
    lines = idn["headline"].split("\n")
    page.text([72, 150, W - 200, 90], lines[0], style=sc("head"))
    if len(lines) > 1:
        page.text([72, 150 + idn["head_size"] + 6, W - 200, 90], lines[1],
                  style=sc("head"))

    # accent device — different per identity (bar / rule / box / round / rule)
    ak = idn["accent_kind"]
    ay = 150 + idn["head_size"] * 2 + 24
    if ak == "bar":
        page.rect([72, ay, 220, 16], fill=sc("accent"))
    elif ak == "rule":
        page.rect([72, ay, 320, 3], fill=sc("accent"))
    elif ak == "box":
        page.rect([72, ay, 220, 40], fill=sc("accent"))
        page.text([72, ay + 11, 220, 20], "[ NO STYLE ]", style=sc("chip"))
    elif ak == "round":
        page.rect([72, ay, 160, 40], radius=20, fill=sc("accent"))
        page.text([72, ay + 11, 160, 20], "hello", style=sc("chip"))

    # type specimen + three shape chips (radius/gradient differ by identity)
    page.text([72, 470, 500, 80], "Aa Gg 123", style=sc("spec"))
    chips = ["accent", "panel", "fg"]
    for i, tok in enumerate(chips):
        x = 560 + i * 150
        page.rect([x, 470, 130, 130], radius=r, fill=sc(tok),
                  stroke=(sc("border") if idn["border_w"] else None),
                  stroke_style=({"width": idn["border_w"]} if idn["border_w"] else None))

    # footer
    page.text([72, H - 70, W - 144, 18],
              "Same skeleton · different identity · FrameGraph SDK", style=sc("foot"))


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Five Visual Identities", profile="deck", lang="en")
    for idn in IDENTITIES:
        render_identity(b, idn)
    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} identities — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:25]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")
    out = os.path.join(ROOT, "fixtures", "visual-identities.fg.yaml")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
