#!/usr/bin/env python3
"""Recreate the NewsPulse nine-screen mobile news-app UI kit with the FrameForge SDK.

The reference is a UI-kit product board: nine phone screens on a pale artboard —
onboarding, subscription picker, interest chips, a scrolling home feed, two long
article pages, saved articles, newsletter picker, and a confirmation screen.
Every screen is rebuilt as vector artwork: device frames, serif/sans editorial
type (Source Serif 4 + Inter), chips, radio and checkbox rows, bottom
navigation, and flat-illustration stand-ins for the photography.

Run from the repository root::

    uv run python static/examples/newspulse_ui_kit.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

import copy  # noqa: E402

from frameforge.sdk import DocumentBuilder, Mat3, serialize  # noqa: E402
from frameforge.sdk.clip import clip_path  # noqa: E402
from frameforge.sdk.metrics import measure_text, wrap_text  # noqa: E402
from frameforge.sdk.paint import effects, linear_gradient, shadow, stroke  # noqa: E402
from frameforge.sdk.params import resolve_params  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

OUT_DIR = os.path.join(ROOT, "out", "newspulse-ui")
OUT = os.path.join(OUT_DIR, "newspulse-ui.fg.yaml")
OUT_FLOW = os.path.join(OUT_DIR, "newspulse-ui-flow.fg.yaml")
OUT_RESOLVED = os.path.join(OUT_DIR, "newspulse-ui-flow.resolved.fg.yaml")
OUT_DATUM = os.path.join(OUT_DIR, "newspulse-ui-flow.datum.fg.yaml")

# The associative core (defs.params): one set of numbers; '=expr' string fields
# anywhere in the document resolve against them before validation, so the
# subscription-price labels below are DRIVEN values, not typed literals.
PARAMS = {
    "monthly_price": 45,
    "annual_price": "=monthly_price*11 + 5",
    "two_year_price": "=annual_price*2 - 100",
}
PRICE_VALUES = {"monthly_price": 45, "annual_price": 500, "two_year_price": 900}

CW = 390          # screen content width
BP = 14           # bezel padding around the screen
MARGIN = 64       # artboard margin
GAP = 52          # gap between phones
SP = 26           # in-screen side padding
RIGHT = CW - SP

SERIF = ["Source Serif 4", "PT Serif", "DejaVu Serif", "serif"]
SANS = ["Inter", "DejaVu Sans", "sans-serif"]

COLORS = {
    "stage": "#F2F1EE",
    "paper": "#FFFFFF",
    "ink": "#211E1B",
    "body": "#3B3733",
    "muted": "#8F8A84",
    "faint": "#B8B3AD",
    "line": "#ECE9E5",
    "border": "#E4E1DC",
    "soft": "#F6F4F1",
    "btn": "#232019",
    "accent": "#EC6640",
    "accent_soft": "#FBEEE7",
    "accent_border": "#F3D3C2",
}


def _ts(family, size, weight=400, color="ink", align="left", lh=1.25, italic=False, tracking=0):
    st = {
        "font_family": family,
        "font_size": size,
        "font_weight": weight,
        "color": color,
        "align": align,
        "line_height": lh,
        "letter_spacing": tracking,
    }
    if italic:
        st["italic"] = True
    return st


STYLES = {
    "wordmark": _ts(SERIF, 19, 700, "ink", "center"),
    "wordmark_lg": _ts(SERIF, 42, 700, "ink", "center", 1.15),
    "welcome_sub": _ts(SANS, 14, 400, "muted", "center", 1.55),
    "h_screen": _ts(SANS, 17, 600, "ink"),
    "skip": _ts(SANS, 12, 500, "faint", "right"),
    "opt_label": _ts(SANS, 15, 600, "ink"),
    "opt_sub": _ts(SANS, 11.5, 400, "muted"),
    "price": _ts(SANS, 20, 700, "ink", "right"),
    "price_unit": _ts(SANS, 11, 400, "muted"),
    "chip": _ts(SANS, 13, 500, "body", "center"),
    "chip_on": _ts(SANS, 13, 500, "paper", "center"),
    "tab": _ts(SANS, 13.5, 500, "muted", "center"),
    "tab_on": _ts(SANS, 13.5, 600, "accent", "center"),
    "headline": _ts(SERIF, 25, 700, "ink", "left", 1.26),
    "headline_md": _ts(SERIF, 19, 700, "ink", "left", 1.32),
    "body_txt": _ts(SERIF, 15, 400, "body", "left", 1.6),
    "body_sm": _ts(SERIF, 13.5, 400, "body", "left", 1.5),
    "quote": _ts(SERIF, 14.5, 400, "body", "left", 1.5, italic=True),
    "quote_lg": _ts(SERIF, 16, 400, "ink", "left", 1.5, italic=True),
    "caption": _ts(SERIF, 11.5, 400, "muted", "center", 1.3, italic=True),
    "meta": _ts(SANS, 11.5, 400, "muted"),
    "meta_r": _ts(SANS, 11.5, 400, "muted", "right"),
    "section": _ts(SANS, 13, 700, "ink"),
    "list_title": _ts(SERIF, 15, 600, "ink", "left", 1.3),
    "saved_title": _ts(SERIF, 14.5, 600, "ink", "left", 1.3),
    "read_more": _ts(SANS, 13, 600, "accent"),
    "btn_label": _ts(SANS, 15, 600, "paper", "center"),
    "input_ph": _ts(SANS, 13.5, 400, "faint"),
    "news_sub": _ts(SANS, 12.5, 400, "muted", "left", 1.5),
    "nav_on": _ts(SANS, 9.5, 500, "accent", "center"),
    "nav_off": _ts(SANS, 9.5, 500, "faint", "center"),
    "badge": _ts(SANS, 9, 700, "paper", "center", tracking=0.8),
    "cat_label": _ts(SANS, 13.5, 600, "ink"),
    "check_label": _ts(SANS, 14.5, 500, "ink"),
    "big_title": _ts(SERIF, 34, 700, "ink", "center", 1.25),
    # flow-map annotation styles
    "flow_title": _ts(SERIF, 30, 700, "ink"),
    "flow_sub": _ts(SANS, 13, 400, "muted", "left", 1.5),
    "flow_label": _ts(SANS, 10.5, 500, "body", "center"),
    "screen_name": _ts(SANS, 12, 600, "ink"),
    "step_num": _ts(SANS, 11, 700, "paper", "center"),
    "legend_txt": _ts(SANS, 12, 400, "muted"),
    "legend_num": _ts(SANS, 12, 700, "accent"),
    "link_run": _ts(SANS, 12, 600, "accent"),
    "idx_sep": _ts(SANS, 12, 400, "faint"),
    "datum_txt": _ts(SANS, 10, 500, "#3AA6B8"),
}


def measure(text, style):
    st = STYLES[style]
    return measure_text(text, font_family=st["font_family"], font_size=st["font_size"],
                        bold=st["font_weight"] >= 600)


def rr_d(x, y, w, h, r):
    """Rounded-rectangle path (for rounded clips on photo blocks)."""
    return (
        f"M {x + r} {y} L {x + w - r} {y} Q {x + w} {y} {x + w} {y + r} "
        f"L {x + w} {y + h - r} Q {x + w} {y + h} {x + w - r} {y + h} "
        f"L {x + r} {y + h} Q {x} {y + h} {x} {y + h - r} "
        f"L {x} {y + r} Q {x} {y} {x + r} {y} Z"
    )


class S:
    """Deferred screen canvas: collect draw ops, replay them into a phone group.

    Screen builders measure as they lay out, so total height is known before the
    device frame (which must render underneath) is drawn.
    """

    def __init__(self):
        self.ops = []

    def add(self, fn):
        self.ops.append(fn)

    def rect(self, box, **kw):
        self.add(lambda g, box=list(box), kw=kw: g.rect(box, **kw))

    def text(self, box, s, **kw):
        # Align-aware slack: the emitter clips to the box with its own metrics,
        # so give every text box breathing room that preserves its anchor edge.
        x, y, w, h = box
        st = STYLES.get(kw.get("style"))
        if st is not None:
            pad = 14
            align = st.get("align", "left")
            if align == "center":
                x -= pad / 2
            elif align == "right":
                x -= pad
            w += pad
            h += st["font_size"] * st["line_height"] * 0.65
        self.add(lambda g, box=[x, y, w, h], s=s, kw=kw: g.text(box, s, **kw))

    def line(self, a, b, **kw):
        self.add(lambda g, a=list(a), b=list(b), kw=kw: g.line(a, b, **kw))

    def path(self, d, **kw):
        self.add(lambda g, d=d, kw=kw: g.path(d, **kw))

    def ellipse(self, c, rx, ry, **kw):
        self.add(lambda g, c=list(c), rx=rx, ry=ry, kw=kw: g.ellipse(c, rx, ry, **kw))

    def polygon(self, pts, **kw):
        self.add(lambda g, pts=[list(p) for p in pts], kw=kw: g.polygon(pts, **kw))

    def para(self, x, y, w, text, style):
        """Wrap ``text`` to ``w`` px with real metrics; returns the drawn height."""
        st = STYLES[style]
        lines = wrap_text(text, width=w - 2, font_family=st["font_family"],
                          font_size=st["font_size"], bold=st["font_weight"] >= 600)
        h = len(lines) * st["font_size"] * st["line_height"]
        self.text([x, y, w, h + 2], "\n".join(lines), style=style)
        return h

    def shift(self, dx, dy):
        """Wrap everything drawn so far in a translate group."""
        ops, self.ops = self.ops, []

        def run(g, ops=ops, dx=dx, dy=dy):
            with g.grouped(transform=Mat3.translate(dx, dy)) as gg:
                for op in ops:
                    op(gg)

        self.add(run)

    def photo(self, box, kind, r=10):
        self.add(lambda g, box=list(box), kind=kind, r=r: draw_photo(g, box, kind, r))

    def icon(self, fn, *a, **kw):
        self.add(lambda g, fn=fn, a=a, kw=kw: fn(g, *a, **kw))


# --------------------------------------------------------------------------- icons

def icon_back(g, cx, cy, color="ink"):
    g.path(f"M {cx + 4} {cy - 6} L {cx - 3} {cy} L {cx + 4} {cy + 6}",
           fill="none", **stroke(2.0, color=color, cap="round", join="round"))


def icon_bookmark(g, cx, cy, s=1.0, color="ink", filled=False):
    d = (f"M {cx - 5.5 * s} {cy - 7.5 * s} L {cx + 5.5 * s} {cy - 7.5 * s} "
         f"L {cx + 5.5 * s} {cy + 7.5 * s} L {cx} {cy + 3.2 * s} L {cx - 5.5 * s} {cy + 7.5 * s} Z")
    if filled:
        g.path(d, fill=color)
    else:
        g.path(d, fill="none", **stroke(1.7 * s, color=color, join="round"))


def icon_share(g, cx, cy, color="ink"):
    g.path(f"M {cx - 6} {cy - 1} L {cx - 6} {cy + 7} L {cx + 6} {cy + 7} L {cx + 6} {cy - 1}",
           fill="none", **stroke(1.7, color=color, cap="round", join="round"))
    g.line([cx, cy - 8.5], [cx, cy + 2.5], **stroke(1.7, color=color, cap="round"))
    g.path(f"M {cx - 3.5} {cy - 5.2} L {cx} {cy - 8.8} L {cx + 3.5} {cy - 5.2}",
           fill="none", **stroke(1.7, color=color, cap="round", join="round"))


def icon_search(g, cx, cy, color="ink", s=1.0):
    g.ellipse([cx - 1.5 * s, cy - 1.5 * s], 6 * s, 6 * s, fill="none",
              **stroke(1.9 * s, color=color))
    g.line([cx + 3.4 * s, cy + 3.4 * s], [cx + 7.5 * s, cy + 7.5 * s],
           **stroke(1.9 * s, color=color, cap="round"))


def icon_home(g, cx, cy, color="ink"):
    g.path(f"M {cx - 8} {cy - 1} L {cx} {cy - 8} L {cx + 8} {cy - 1} L {cx + 8} {cy + 8} "
           f"L {cx - 8} {cy + 8} Z", fill="none",
           **stroke(1.9, color=color, cap="round", join="round"))
    g.line([cx, cy + 8], [cx, cy + 2.5], **stroke(1.9, color=color, cap="round"))


def icon_profile(g, cx, cy, color="ink"):
    g.ellipse([cx, cy - 3.5], 3.6, 3.6, fill="none", **stroke(1.9, color=color))
    g.path(f"M {cx - 7} {cy + 8.5} C {cx - 6} {cy + 2} {cx + 6} {cy + 2} {cx + 7} {cy + 8.5}",
           fill="none", **stroke(1.9, color=color, cap="round"))


def icon_check(g, cx, cy, s=1.0, color="paper", w=2.2):
    g.path(f"M {cx - 4 * s} {cy} L {cx - 1 * s} {cy + 3.2 * s} L {cx + 4.5 * s} {cy - 3.4 * s}",
           fill="none", **stroke(w, color=color, cap="round", join="round"))


def icon_arrow_r(g, cx, cy, color="accent"):
    g.line([cx - 5, cy], [cx + 5, cy], **stroke(1.8, color=color, cap="round"))
    g.path(f"M {cx + 1.5} {cy - 3.5} L {cx + 5} {cy} L {cx + 1.5} {cy + 3.5}",
           fill="none", **stroke(1.8, color=color, cap="round", join="round"))


def icon_chev(g, cx, cy, direction=1, color="faint"):
    g.path(f"M {cx - 2.5 * direction} {cy - 5} L {cx + 2.5 * direction} {cy} "
           f"L {cx - 2.5 * direction} {cy + 5}",
           fill="none", **stroke(1.9, color=color, cap="round", join="round"))


def icon_mic(g, cx, cy, color="accent"):
    g.rect([cx - 3, cy - 8, 6, 10], fill=color, radius=3)
    g.path(f"M {cx - 5.5} {cy - 1} C {cx - 5.5} {cy + 6} {cx + 5.5} {cy + 6} {cx + 5.5} {cy - 1}",
           fill="none", **stroke(1.6, color=color, cap="round"))
    g.line([cx, cy + 4.5], [cx, cy + 8], **stroke(1.6, color=color, cap="round"))


def icon_ball(g, cx, cy, color="#6B6660"):
    g.ellipse([cx, cy], 7, 7, fill="none", **stroke(1.6, color=color))
    g.path(f"M {cx - 6} {cy - 3.5} C {cx - 1} {cy - 1} {cx + 1} {cy + 1} {cx + 6} {cy + 3.5}",
           fill="none", **stroke(1.4, color=color))
    g.path(f"M {cx - 3.5} {cy + 6} C {cx - 1.5} {cy + 1} {cx - 1} {cy - 2} {cx + 1} {cy - 6.8}",
           fill="none", **stroke(1.4, color=color))


def icon_mail(g, cx, cy, color="accent"):
    g.rect([cx - 7.5, cy - 5.5, 15, 11], fill="none", radius=2, **stroke(1.6, color=color))
    g.path(f"M {cx - 7} {cy - 4.5} L {cx} {cy + 1} L {cx + 7} {cy - 4.5}",
           fill="none", **stroke(1.6, color=color, join="round"))


def icon_palette(g, cx, cy, color="#6B6660"):
    g.path(f"M {cx + 6.5} {cy + 2} C {cx + 6.5} {cy - 5} {cx + 1} {cy - 7.5} {cx - 1.5} {cy - 7} "
           f"C {cx - 7} {cy - 6} {cx - 8} {cy - 1} {cx - 6.5} {cy + 3} "
           f"C {cx - 5} {cy + 7} {cx + 1} {cy + 8.5} {cx + 3} {cy + 6} "
           f"C {cx + 4.5} {cy + 4} {cx + 3} {cy + 2.5} {cx + 6.5} {cy + 2} Z",
           fill="none", **stroke(1.6, color=color, join="round"))
    for dx, dy in [(-3.5, -3.5), (0.5, -4.5), (-4.5, 0.5)]:
        g.ellipse([cx + dx, cy + dy], 1.2, 1.2, fill=color)


def icon_chart(g, cx, cy, color="#6B6660"):
    for i, (dx, h) in enumerate([(-6, 6), (-1, 10), (4, 8)]):
        g.rect([cx + dx, cy + 7 - h, 4, h], fill=color, radius=1)


def icon_monitor(g, cx, cy, color="#6B6660"):
    g.rect([cx - 8, cy - 6.5, 16, 11], fill="none", radius=2, **stroke(1.6, color=color))
    g.line([cx - 3.5, cy + 7.5], [cx + 3.5, cy + 7.5], **stroke(1.6, color=color, cap="round"))
    g.line([cx, cy + 4.5], [cx, cy + 7.5], **stroke(1.6, color=color))


def _nav_bookmark(g, cx, cy, color="ink"):
    icon_bookmark(g, cx, cy, 1.05, color)


NAV_ICONS = {"home": icon_home, "search": icon_search, "saved": _nav_bookmark,
             "profile": icon_profile}


# --------------------------------------------------------------------------- photos

def draw_photo(g, box, kind, r=10):
    x, y, w, h = box
    with g.grouped(clip=clip_path(rr_d(x, y, w, h, r))) as p:
        PHOTOS[kind](p, x, y, w, h)


def _rider(p, cx, cy, s=1.0, tilt=0.35):
    """Iconic mid-air snowboarder silhouette."""
    bx, by = 26 * s, 9 * s * tilt
    p.path(f"M {cx - bx} {cy + 12 * s + by} Q {cx} {cy + 16 * s} {cx + bx} {cy + 12 * s - by} "
           f"L {cx + bx} {cy + 16 * s - by} Q {cx} {cy + 20 * s} {cx - bx} {cy + 16 * s + by} Z",
           fill="#22262C")
    p.line([cx - 8 * s, cy + 13 * s], [cx - 5 * s, cy + 2 * s], **stroke(5.5 * s, color="#2A2F36", cap="round"))
    p.line([cx + 9 * s, cy + 11 * s], [cx + 5 * s, cy + 2 * s], **stroke(5.5 * s, color="#2A2F36", cap="round"))
    p.path(f"M {cx - 7 * s} {cy + 3 * s} Q {cx - 3 * s} {cy - 12 * s} {cx + 7 * s} {cy - 8 * s} "
           f"L {cx + 8 * s} {cy + 1 * s} Q {cx} {cy + 6 * s} {cx - 7 * s} {cy + 3 * s} Z",
           fill="#343B44")
    p.line([cx - 6 * s, cy - 6 * s], [cx - 15 * s, cy - 13 * s], **stroke(4 * s, color="#343B44", cap="round"))
    p.line([cx + 6 * s, cy - 5 * s], [cx + 14 * s, cy + 2 * s], **stroke(4 * s, color="#343B44", cap="round"))
    p.ellipse([cx + 2 * s, cy - 15 * s], 6 * s, 6 * s, fill="#2E333B")
    p.line([cx - 3 * s, cy - 16 * s], [cx + 6.5 * s, cy - 14 * s], **stroke(2.6 * s, color="#EC6640", cap="round"))


def photo_snow_hero(p, x, y, w, h):
    p.rect([x, y, w, h], fill=linear_gradient([("#D8E1E7", 0), ("#EEF2F4", 1)], angle=90))
    p.polygon([[x, y + h * 0.52], [x + w * 0.34, y + h * 0.18], [x + w * 0.62, y + h * 0.52]],
              fill="#C4CFD6")
    p.polygon([[x + w * 0.4, y + h * 0.55], [x + w * 0.78, y + h * 0.1], [x + w * 1.05, y + h * 0.55]],
              fill="#AFBDC6")
    p.path(f"M {x} {y + h} L {x} {y + h * 0.62} Q {x + w * 0.5} {y + h * 0.4} {x + w} {y + h * 0.72} "
           f"L {x + w} {y + h} Z", fill="#F6F8FA")
    for dx, dy, rr in [(0.30, 0.62, 14), (0.36, 0.70, 20), (0.26, 0.72, 12), (0.42, 0.78, 16),
                       (0.33, 0.83, 22), (0.22, 0.66, 8)]:
        p.ellipse([x + w * dx, y + h * dy], rr, rr * 0.8, fill="#FFFFFF", opacity=0.85)
    for dx, dy in [(0.18, 0.35), (0.62, 0.25), (0.72, 0.45), (0.5, 0.15), (0.85, 0.3)]:
        p.ellipse([x + w * dx, y + h * dy], 1.6, 1.6, fill="#FFFFFF", opacity=0.9)
    _rider(p, x + w * 0.52, y + h * 0.42, 1.5)


def photo_snow_action(p, x, y, w, h):
    p.rect([x, y, w, h], fill=linear_gradient([("#CBD6DD", 0), ("#E9EEF1", 1)], angle=90))
    p.polygon([[x, y + h * 0.4], [x + w * 0.3, y + h * 0.08], [x + w * 0.58, y + h * 0.4]],
              fill="#B7C4CC")
    p.path(f"M {x} {y + h} L {x} {y + h * 0.5} Q {x + w * 0.55} {y + h * 0.34} {x + w} {y + h * 0.6} "
           f"L {x + w} {y + h} Z", fill="#F4F7F9")
    for dx, dy, rr in [(0.56, 0.6, 26), (0.46, 0.68, 18), (0.64, 0.72, 22), (0.52, 0.8, 30),
                       (0.4, 0.78, 14), (0.68, 0.56, 12)]:
        p.ellipse([x + w * dx, y + h * dy], rr, rr * 0.75, fill="#FFFFFF", opacity=0.9)
    _rider(p, x + w * 0.62, y + h * 0.38, 1.7, tilt=0.5)


def photo_goggles(p, x, y, w, h):
    p.rect([x, y, w, h], fill=linear_gradient([("#C9D5DC", 0), ("#E4EAED", 1)], angle=115))
    for dx, dy, rr in [(0.15, 0.25, 22), (0.85, 0.2, 18), (0.75, 0.7, 26)]:
        p.ellipse([x + w * dx, y + h * dy], rr, rr, fill="#FFFFFF", opacity=0.35)
    cx, cy = x + w * 0.42, y + h * 0.52
    p.path(f"M {cx - 52} {y + h} Q {cx - 40} {cy + 18} {cx - 20} {cy + 16} "
           f"L {cx + 22} {cy + 16} Q {cx + 44} {cy + 20} {cx + 54} {y + h} Z", fill="#2E3238")
    p.ellipse([cx, cy - 10], 30, 34, fill="#E6B48F")
    p.path(f"M {cx - 30} {cy - 22} Q {cx - 32} {cy - 52} {cx} {cy - 50} "
           f"Q {cx + 34} {cy - 52} {cx + 31} {cy - 20} L {cx + 26} {cy - 26} "
           f"L {cx - 26} {cy - 26} Z", fill="#33383F")
    p.rect([cx - 27, cy - 27, 54, 17], fill="#1F2327", radius=8)
    p.rect([cx - 24, cy - 24, 48, 11], fill="#8FB4C6", radius=6, opacity=0.9)
    p.line([cx - 27, cy - 19], [cx - 38, cy - 16], **stroke(4, color="#EC6640", cap="round"))
    p.path(f"M {cx - 8} {cy + 10} Q {cx} {cy + 14} {cx + 8} {cy + 10}",
           fill="none", **stroke(2, color="#B98963", cap="round"))


def photo_hug(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#E8D9CB")
    p.ellipse([x + w * 0.35, y + h * 0.38], w * 0.17, w * 0.17, fill="#6E4F3D")
    p.path(f"M {x + w * 0.08} {y + h} Q {x + w * 0.32} {y + h * 0.44} {x + w * 0.62} {y + h} Z",
           fill="#8A6450")
    p.ellipse([x + w * 0.66, y + h * 0.5], w * 0.13, w * 0.13, fill="#D19A6F")
    p.path(f"M {x + w * 0.42} {y + h} Q {x + w * 0.66} {y + h * 0.58} {x + w * 0.92} {y + h} Z",
           fill="#C08B62")
    p.path(f"M {x + w * 0.3} {y + h * 0.72} Q {x + w * 0.55} {y + h * 0.58} {x + w * 0.78} {y + h * 0.72}",
           fill="none", **stroke(5, color="#8A6450", cap="round"))


def _cyclist(p, cx, cy, s, jersey):
    p.ellipse([cx - 11 * s, cy + 10 * s], 8 * s, 8 * s, fill="none", **stroke(2.4 * s, color="#23262B"))
    p.ellipse([cx + 11 * s, cy + 10 * s], 8 * s, 8 * s, fill="none", **stroke(2.4 * s, color="#23262B"))
    p.path(f"M {cx - 11 * s} {cy + 10 * s} L {cx - 2 * s} {cy + 2 * s} L {cx + 6 * s} {cy + 10 * s} "
           f"M {cx - 2 * s} {cy + 2 * s} L {cx + 11 * s} {cy + 10 * s}",
           fill="none", **stroke(2 * s, color="#3C4148"))
    p.path(f"M {cx - 2 * s} {cy + 2 * s} L {cx + 1 * s} {cy + 8 * s}",
           fill="none", **stroke(3 * s, color="#2A2F36", cap="round"))
    p.path(f"M {cx - 2 * s} {cy + 3 * s} Q {cx + 2 * s} {cy - 8 * s} {cx + 12 * s} {cy - 4 * s}",
           fill="none", **stroke(5 * s, color=jersey, cap="round"))
    p.ellipse([cx + 14 * s, cy - 7 * s], 3.6 * s, 3.6 * s, fill="#E6B48F")
    p.path(f"M {cx + 10.5 * s} {cy - 9 * s} Q {cx + 14 * s} {cy - 13 * s} {cx + 17.5 * s} {cy - 8.5 * s}",
           fill="none", **stroke(2.6 * s, color="#23262B", cap="round"))


def photo_cycling(p, x, y, w, h):
    p.rect([x, y, w, h], fill=linear_gradient([("#DEE4E0", 0), ("#EDF0EC", 1)], angle=90))
    for dx, rr in [(0.08, 26), (0.2, 20), (0.86, 30), (0.7, 18)]:
        p.ellipse([x + w * dx, y + h * 0.3], rr, rr * 0.85, fill="#7B9468", opacity=0.85)
        p.ellipse([x + w * dx + 8, y + h * 0.36], rr * 0.7, rr * 0.6, fill="#5F7A4E", opacity=0.85)
    p.polygon([[x, y + h], [x + w * 0.16, y + h * 0.44], [x + w * 0.9, y + h * 0.44], [x + w, y + h]],
              fill="#B3B8BD")
    p.line([x + w * 0.42, y + h * 0.95], [x + w * 0.5, y + h * 0.48],
           **stroke(3, color="#E9ECEE", cap="round", dash=[10, 12]))
    _cyclist(p, x + w * 0.28, y + h * 0.6, 1.55, "#D8A93E")
    _cyclist(p, x + w * 0.55, y + h * 0.55, 1.35, "#4E7AA8")
    _cyclist(p, x + w * 0.78, y + h * 0.62, 1.7, "#C24E3A")


def photo_canal(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#E4DED3")
    bx = x
    for bw, bh, col in [(0.16, 0.52, "#7C6652"), (0.13, 0.62, "#8F7863"), (0.18, 0.48, "#655749"),
                        (0.15, 0.66, "#93705A"), (0.2, 0.5, "#5C5044"), (0.18, 0.6, "#7C6652")]:
        p.rect([bx, y + h * (0.66 - bh), w * bw, h * bh], fill=col)
        for wy in range(2):
            for wx in range(2):
                p.rect([bx + w * bw * (0.22 + wx * 0.4), y + h * (0.72 - bh + wy * 0.16),
                        w * bw * 0.16, h * 0.07], fill="#EFE7D8", opacity=0.85)
        bx += w * bw
    p.rect([x, y + h * 0.66, w, h * 0.34], fill="#77878D")
    for dx in [0.1, 0.3, 0.52, 0.74, 0.9]:
        p.rect([x + w * dx, y + h * 0.68, w * 0.06, h * 0.3], fill="#5F7076", opacity=0.5)
    for dx, rr in [(0.06, 24), (0.94, 28), (0.5, 16)]:
        p.ellipse([x + w * dx, y + h * 0.6], rr, rr * 0.9, fill="#C8763B", opacity=0.9)
        p.ellipse([x + w * dx - 8, y + h * 0.64], rr * 0.6, rr * 0.5, fill="#B5652F", opacity=0.9)


def photo_gallery1(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#DCE2DC")
    p.polygon([[x, y + h], [x + w * 0.2, y + h * 0.4], [x + w, y + h * 0.55], [x + w, y + h]],
              fill="#AEB4B9")
    _cyclist(p, x + w * 0.48, y + h * 0.5, 0.85, "#D8A93E")


def photo_gallery2(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#D8DEE2")
    p.polygon([[x, y + h], [x, y + h * 0.5], [x + w * 0.85, y + h * 0.42], [x + w, y + h]],
              fill="#B3B8BD")
    _cyclist(p, x + w * 0.4, y + h * 0.48, 0.8, "#C24E3A")
    _cyclist(p, x + w * 0.68, y + h * 0.55, 0.9, "#4E7AA8")


def photo_stadium(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#8A9298")
    p.rect([x, y + h * 0.4, w, h * 0.6], fill="#5C8A52")
    p.rect([x + w * 0.18, y + h * 0.52, w * 0.64, h * 0.36], fill="none",
           **stroke(1.4, color="#EDF2EA"))
    p.line([x + w * 0.5, y + h * 0.52], [x + w * 0.5, y + h * 0.88], **stroke(1.4, color="#EDF2EA"))
    for dx, dy, col in [(0.3, 0.62, "#C24E3A"), (0.62, 0.7, "#3D5C8C"), (0.48, 0.8, "#C24E3A")]:
        p.ellipse([x + w * dx, y + h * dy], 2.2, 2.2, fill=col)


def photo_football(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#5F8F56")
    p.line([x, y + h * 0.78], [x + w, y + h * 0.72], **stroke(1.6, color="#EDF2EA"))
    cx, cy = x + w * 0.5, y + h * 0.42
    p.ellipse([cx, cy - 8], 5, 5, fill="#E6B48F")
    p.path(f"M {cx - 6} {cy + 10} Q {cx} {cy - 4} {cx + 6} {cy + 10} Z", fill="#C24E3A")
    p.line([cx - 2, cy + 10], [cx - 4, cy + 20], **stroke(3, color="#2A2F36", cap="round"))
    p.line([cx + 2, cy + 10], [cx + 6, cy + 18], **stroke(3, color="#2A2F36", cap="round"))
    p.ellipse([cx + 10, cy + 21], 3.4, 3.4, fill="#F4F2EE")


def photo_tennis(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#4C7A63")
    p.rect([x + w * 0.12, y + h * 0.18, w * 0.76, h * 0.64], fill="none",
           **stroke(1.5, color="#E8EDE7"))
    p.line([x + w * 0.12, y + h * 0.5], [x + w * 0.88, y + h * 0.5], **stroke(1.5, color="#E8EDE7"))
    p.ellipse([x + w * 0.68, y + h * 0.34], 3.2, 3.2, fill="#DCE94A")


def photo_elections(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#EDE9E2")
    p.rect([x + w * 0.22, y + h * 0.42, w * 0.56, h * 0.38], fill="#2A2E35", radius=3)
    p.rect([x + w * 0.34, y + h * 0.4, w * 0.32, h * 0.05], fill="#EC6640", radius=1)
    p.polygon([[x + w * 0.38, y + h * 0.4], [x + w * 0.44, y + h * 0.16],
               [x + w * 0.66, y + h * 0.2], [x + w * 0.62, y + h * 0.4]], fill="#FDFCFA")
    p.line([x + w * 0.47, y + h * 0.26], [x + w * 0.6, y + h * 0.28],
           **stroke(1.4, color="#B8B3AD"))


def photo_movies(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#B3271E")
    p.polygon([[x + w * 0.4, y + h * 0.3], [x + w * 0.7, y + h * 0.5], [x + w * 0.4, y + h * 0.7]],
              fill="#FFFFFF")


def photo_pm(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#C7D3DC")
    cx = x + w * 0.5
    p.path(f"M {x + w * 0.14} {y + h} Q {cx} {y + h * 0.52} {x + w * 0.86} {y + h} Z", fill="#2E3238")
    p.line([cx, y + h * 0.72], [cx, y + h], **stroke(2.4, color="#B23A3A"))
    p.ellipse([cx, y + h * 0.42], w * 0.18, w * 0.2, fill="#E6B48F")
    p.path(f"M {cx - w * 0.2} {y + h * 0.34} Q {cx} {y + h * 0.1} {cx + w * 0.2} {y + h * 0.34} "
           f"Q {cx} {y + h * 0.26} {cx - w * 0.2} {y + h * 0.34} Z", fill="#E8E4DA")


def photo_digest(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#17181A")
    cx, cy = x + w * 0.5, y + h * 0.5
    for a, b in [((-7, -7), (7, 7)), ((7, -7), (-7, 7)), ((0, -9), (0, 9))]:
        p.line([cx + a[0], cy + a[1]], [cx + b[0], cy + b[1]],
               **stroke(2.2, color="#F4F2EE", cap="round"))


def photo_coach(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#CDD2D5")
    cx, cy = x + w * 0.46, y + h * 0.46
    p.path(f"M {x + w * 0.08} {y + h} Q {cx} {cy + h * 0.16} {x + w * 0.9} {y + h} Z", fill="#2E3338")
    p.ellipse([cx, cy - h * 0.08], w * 0.15, w * 0.17, fill="#D9A87E")
    p.path(f"M {cx - w * 0.17} {cy - h * 0.14} Q {cx} {cy - h * 0.36} {cx + w * 0.17} {cy - h * 0.14} "
           f"L {cx + w * 0.22} {cy - h * 0.11} L {cx + w * 0.17} {cy - h * 0.09} Z", fill="#23262B")
    p.rect([x + w * 0.62, y + h * 0.55, w * 0.07, h * 0.2], fill="#3C4148", radius=3)
    p.ellipse([x + w * 0.655, y + h * 0.52], w * 0.05, w * 0.05, fill="#23262B")


def photo_interview(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#5F8F56")
    p.ellipse([x + w * 0.2, y + h * 0.2], 16, 16, fill="#6FA362", opacity=0.7)
    cx = x + w * 0.5
    p.path(f"M {x + w * 0.2} {y + h} Q {cx} {y + h * 0.5} {x + w * 0.8} {y + h} Z", fill="#C24E3A")
    p.ellipse([cx, y + h * 0.4], w * 0.13, w * 0.15, fill="#E6B48F")
    p.path(f"M {cx - w * 0.14} {y + h * 0.32} Q {cx} {y + h * 0.14} {cx + w * 0.14} {y + h * 0.32} "
           f"Q {cx} {y + h * 0.24} {cx - w * 0.14} {y + h * 0.32} Z", fill="#2A2622")


def photo_mountains(p, x, y, w, h):
    p.rect([x, y, w, h], fill=linear_gradient([("#DCE4E9", 0), ("#EFF2F4", 1)], angle=90))
    p.polygon([[x, y + h], [x + w * 0.32, y + h * 0.3], [x + w * 0.6, y + h]], fill="#6E8291")
    p.polygon([[x + w * 0.35, y + h], [x + w * 0.7, y + h * 0.18], [x + w * 1.05, y + h]],
              fill="#8FA3B0")
    p.polygon([[x + w * 0.62, y + h * 0.34], [x + w * 0.7, y + h * 0.18],
               [x + w * 0.78, y + h * 0.34], [x + w * 0.7, y + h * 0.3]], fill="#F4F7F8")


def photo_city(p, x, y, w, h):
    p.rect([x, y, w, h], fill=linear_gradient([("#E5CFA9", 0), ("#D9B98E", 1)], angle=90))
    p.ellipse([x + w * 0.72, y + h * 0.3], 9, 9, fill="#F2E2C4")
    for dx, bw, bh in [(0.04, 0.14, 0.5), (0.2, 0.1, 0.66), (0.32, 0.16, 0.42),
                       (0.5, 0.12, 0.72), (0.64, 0.14, 0.5), (0.8, 0.16, 0.6)]:
        p.rect([x + w * dx, y + h * (1 - bh), w * bw, h * bh], fill="#4A4440")


def photo_portrait(p, x, y, w, h):
    p.rect([x, y, w, h], fill="#DCD4C8")
    cx = x + w * 0.5
    p.path(f"M {x + w * 0.16} {y + h} Q {cx} {y + h * 0.55} {x + w * 0.84} {y + h} Z", fill="#8A6450")
    p.ellipse([cx, y + h * 0.42], w * 0.14, w * 0.17, fill="#D9A87E")
    p.path(f"M {cx - w * 0.15} {y + h * 0.34} Q {cx} {y + h * 0.12} {cx + w * 0.15} {y + h * 0.34} "
           f"Q {cx} {y + h * 0.22} {cx - w * 0.15} {y + h * 0.34} Z", fill="#3A2E24")


PHOTOS = {
    "snow_hero": photo_snow_hero, "snow_action": photo_snow_action, "goggles": photo_goggles,
    "hug": photo_hug, "cycling": photo_cycling, "canal": photo_canal,
    "gallery1": photo_gallery1, "gallery2": photo_gallery2, "stadium": photo_stadium,
    "football": photo_football, "tennis": photo_tennis, "elections": photo_elections,
    "movies": photo_movies, "pm": photo_pm, "digest": photo_digest, "coach": photo_coach,
    "interview": photo_interview, "mountains": photo_mountains, "city": photo_city,
    "portrait": photo_portrait,
}


# --------------------------------------------------------------------------- shared parts

def frame(g, w, h):
    g.rect([-BP, -BP, w + 2 * BP, h + 2 * BP], fill="paper", radius=30,
           **stroke(1.2, color="border"),
           **effects(shadow=shadow(dy=10, blur=26, color="#8D8983", opacity=0.28)))


def header(s, back=True, share=False, bookmark=False, skip=False):
    if back:
        s.icon(icon_back, SP + 4, 37)
    s.text([0, 27, CW, 22], "NewsPulse", style="wordmark")
    ix = RIGHT - 6
    if bookmark:
        s.icon(icon_bookmark, ix, 37, 1.0, "ink")
        ix -= 28
    if share:
        s.icon(icon_share, ix, 34)
    if skip:
        s.text([RIGHT - 48, 31, 48, 14], "skip", style="skip")
    return 72


def button(s, y, label, h=48):
    s.rect([SP, y, CW - 2 * SP, h], fill="btn", radius=h / 2)
    s.text([SP, y + (h - 18) / 2, CW - 2 * SP, 20], label, style="btn_label")


def bottom_nav(s, y, active):
    s.line([0, y], [CW, y], **stroke(1.2, color="line"))
    step = CW / 4
    for i, (key, label) in enumerate([("home", "Home"), ("search", "Search"),
                                      ("saved", "Saved"), ("profile", "Profile")]):
        cx = step * i + step / 2
        color = "accent" if key == active else "faint"
        s.icon(NAV_ICONS[key], cx, y + 22, color)
        s.text([cx - 32, y + 36, 64, 12], label, style="nav_on" if key == active else "nav_off")
    return y + 56


def article_row(s, y, thumb, title, minutes, thumb_size=56):
    s.photo([SP, y, thumb_size, thumb_size], thumb, r=10)
    tx = SP + thumb_size + 16
    th = s.para(tx, y + 2, RIGHT - 30 - tx, title, "list_title")
    s.text([tx, y + th + 8, 90, 13], f"{minutes} min read", style="meta")
    s.icon(icon_bookmark, RIGHT - 8, y + 12, 0.9, "faint")
    return max(thumb_size + 4, th + 24)


# --------------------------------------------------------------------------- screens

def screen_welcome():
    s = S()
    cx = CW / 2
    s.ellipse([cx, 330], 118, 12, fill="#E6E3DE")
    # the open magazine
    s.path(f"M {cx - 92} 196 L {cx - 4} 172 L {cx - 4} 306 L {cx - 92} 322 Z", fill="#FBFAF7",
           **stroke(1.4, color="#DFDBD4", join="round"))
    s.path(f"M {cx - 4} 172 L {cx + 84} 196 L {cx + 84} 322 L {cx - 4} 306 Z", fill="#F3F0EA",
           **stroke(1.4, color="#DFDBD4", join="round"))
    s.path(f"M {cx - 92} 322 L {cx - 4} 306 L {cx + 84} 322 L {cx + 80} 330 L {cx - 4} 315 "
           f"L {cx - 88} 330 Z", fill="#DCD7CF")
    s.line([cx - 4, 172], [cx - 4, 306], **stroke(1.6, color="#D3CEC6"))
    # left page: photo block + text lines
    s.rect([cx - 78, 208, 56, 40], fill="#9FB0BC", radius=3)
    s.polygon([[cx - 74, 244], [cx - 58, 222], [cx - 42, 244]], fill="#7C919F")
    s.polygon([[cx - 56, 244], [cx - 42, 230], [cx - 28, 244]], fill="#8DA0AC")
    for i in range(4):
        s.rect([cx - 78, 258 + i * 11, 58 - (i % 2) * 14, 4], fill="#D8D3CB", radius=2)
    # right page: headline block + accent photo
    s.rect([cx + 8, 204, 48, 6], fill="#C9C3BA", radius=3)
    s.rect([cx + 8, 216, 34, 6], fill="#C9C3BA", radius=3)
    s.rect([cx + 8, 232, 62, 44], fill="#E4B08E", radius=3)
    s.ellipse([cx + 26, 252, ], 8, 8, fill="#D08752")
    for i in range(3):
        s.rect([cx + 8, 286 + i * 10, 60 - (i % 2) * 18, 4], fill="#D8D3CB", radius=2)
    # the reader, leaning on the right edge
    s.ellipse([cx + 106, 190], 11, 11, fill="#E9B58D")
    s.ellipse([cx + 114, 181], 7, 7, fill="#33221B")
    s.path(f"M {cx + 96} 204 Q {cx + 92} 232 {cx + 98} 252 L {cx + 122} 252 "
           f"Q 	{cx + 126} 226 {cx + 118} 202 Q {cx + 106} 196 {cx + 96} 204 Z", fill="#E4713F")
    s.line([cx + 100, 212], [cx + 84, 226], **stroke(7, color="#E4713F", cap="round"))
    s.line([cx + 84, 226], [cx + 82, 240], **stroke(6, color="#E9B58D", cap="round"))
    s.line([cx + 118, 214], [cx + 130, 236], **stroke(7, color="#E4713F", cap="round"))
    s.rect([cx + 97, 252, 10, 62], fill="#26221F", radius=4)
    s.rect([cx + 113, 252, 10, 62], fill="#26221F", radius=4)
    s.rect([cx + 92, 312, 18, 8], fill="#33221B", radius=3)
    s.rect([cx + 110, 312, 18, 8], fill="#33221B", radius=3)

    s.text([0, 372, CW, 50], "NewsPulse", style="wordmark_lg")
    s.para(60, 436, CW - 120, "Choose one of our subscriptions and stay informed wherever you are.",
           "welcome_sub")
    s.shift(0, 54)
    button(s, 700 - 74, "Subscribe")
    return s, 700


def screen_subscription():
    s = S()
    header(s, back=True)
    s.text([SP, 92, 300, 22], "Choose your subscription", style="h_screen")
    y = 134
    plans = [("Monthly", "Pay monthly, cancel anytime", "monthly_price", "/m", True),
             ("Annual", "Pay for a year upfront", "annual_price", "/y", False),
             ("Two years", "Pay once, our best value", "two_year_price", "/2y", False)]
    for label, sub, param, unit, active in plans:
        s.rect([SP, y, CW - 2 * SP, 76], fill="paper", radius=14,
               **stroke(1.4, color="accent_border" if active else "border"))
        cx, cy = SP + 28, y + 38
        if active:
            s.ellipse([cx, cy], 9.5, 9.5, fill="none", **stroke(2, color="accent"))
            s.ellipse([cx, cy], 4.8, 4.8, fill="accent")
        else:
            s.ellipse([cx, cy], 9.5, 9.5, fill="none", **stroke(1.8, color="#C9C5BF"))
        s.text([SP + 50, y + 18, 160, 18], label, style="opt_label")
        s.text([SP + 50, y + 42, 220, 14], sub, style="opt_sub")
        # Driven labels: the number is '=param', resolved from defs.params. The
        # static '$' is positioned from the same Python constant that seeds the
        # parameter, so document and layout share one source of numbers.
        uw = measure(unit, "price_unit")
        num_w = measure(str(PRICE_VALUES[param]), "price")
        s.text([RIGHT - 16 - uw - num_w - 6, y + 24, num_w + 6, 24],
               f"={param}", style="price")
        dw = measure("$", "price")
        s.text([RIGHT - 16 - uw - num_w - 6 - dw - 1, y + 24, dw + 1, 24],
               "$", style="price")
        s.text([RIGHT - 16 - uw, y + 33, uw + 2, 14], unit, style="price_unit")
        y += 90
    button(s, 700 - 74, "Proceed")
    return s, 700


def screen_interests():
    s = S()
    header(s, back=True, skip=True)
    s.text([SP, 92, 300, 22], "Select your interests:", style="h_screen")
    rows = [
        [("News", False), ("Culture", False), ("Technology", False)],
        [("World news", True), ("Elections", False), ("Film", False)],
        [("Foreign affairs", False), ("Commentary", False), ("Art", False)],
        [("Politics", True), ("Sports", False), ("Science", False)],
        [("Business", False), ("Climate news", False)],
    ]
    y = 132
    for row in rows:
        x = SP
        for label, active in row:
            w = measure(label, "chip") + 34
            s.rect([x, y, w, 34], fill="btn" if active else "paper", radius=17,
                   **({} if active else stroke(1.3, color="#D9D5D0")))
            s.text([x, y + 9, w, 16], label, style="chip_on" if active else "chip")
            x += w + 10
        y += 46
    button(s, 700 - 74, "Continue")
    return s, 700


def screen_feed():
    s = S()
    header(s, back=False)
    tabs = [("News", False), ("Sports", True), ("World news", False),
            ("Business", False), ("Politics", False)]
    x = SP
    for label, active in tabs:
        w = measure(label, "tab")
        s.text([x, 64, w + 2, 17], label, style="tab_on" if active else "tab")
        if active:
            s.rect([x, 86, w, 2.5], fill="accent", radius=1.2)
        x += w + 21
    s.line([0, 94], [CW, 94], **stroke(1.2, color="line"))

    y = 110
    s.photo([SP, y, CW - 2 * SP, 204], "snow_hero", r=12)
    y += 204 + 16
    s.text([SP, y, 140, 14], "Oct 4, 2022", style="meta")
    s.text([SP + measure("Oct 4, 2022", "meta") + 14, y, 90, 14], "3 min read", style="meta")
    s.icon(icon_share, RIGHT - 36, y + 3)
    s.icon(icon_bookmark, RIGHT - 8, y + 6, 1.0, "ink")
    y += 30
    y += s.para(SP, y, CW - 2 * SP, "Famous snowboarder wins Grand Prix", "headline") + 14
    y += s.para(SP, y, CW - 2 * SP,
                "The new champion explained her success as the result of a strict training "
                "regimen instituted by her coach. The youngster is also her manager and has "
                "reportedly arranged sponsorship deals which will dwarf her one million dollar "
                "prize fund.", "body_txt") + 14
    s.text([SP, y, 90, 16], "Read more", style="read_more")
    s.icon(icon_arrow_r, SP + measure("Read more", "read_more") + 14, y + 8)
    y += 34
    s.line([SP, y], [RIGHT, y], **stroke(1.2, color="line"))
    y += 22
    s.text([SP, y, 200, 16], "More articles", style="section")
    y += 28
    for thumb, title, minutes in [("cycling", "French Cycling Tour is postponed", 5),
                                  ("football", "Footballer leaves British FC", 2),
                                  ("tennis", "Young tennis player wins WTC", 2)]:
        y += article_row(s, y, thumb, title, minutes) + 18
    y += 4
    s.line([SP, y], [RIGHT, y], **stroke(1.2, color="line"))
    y += 24
    y += s.para(SP, y, CW - 2 * SP,
                'Long read: "You can be champion in anything", says world-class coach.',
                "headline_md") + 16
    s.photo([SP, y, 100, 100], "coach", r=10)
    tx = SP + 116
    th = s.para(tx, y + 2, RIGHT - tx,
                "Long awaited extensive interview with number one football coach, who moved "
                "from South America to lead British team to the victory.", "body_sm")
    s.text([tx, y + th + 10, 90, 14], "20 min read", style="meta")
    y += max(100, th + 28) + 26

    card_h = 208
    s.rect([SP - 6, y, CW - 2 * SP + 12, card_h], fill="soft", radius=14)
    pad = SP + 14
    cy = y + 22
    s.text([pad, cy, 240, 24], "Sign up for newsletter", style="headline_md")
    cy += 32
    cy += s.para(pad, cy, CW - 2 * pad - 4,
                 "Subscribe to our newsletter and receive the freshest news from all around "
                 "the world.", "news_sub") + 12
    s.rect([pad, cy, CW - 2 * pad, 42], fill="paper", radius=21, **stroke(1.3, color="border"))
    s.text([pad + 18, cy + 13, 160, 16], "Email address", style="input_ph")
    cy += 52
    s.rect([pad, cy, CW - 2 * pad, 42], fill="btn", radius=21)
    s.text([pad, cy + 12, CW - 2 * pad, 18], "Subscribe", style="btn_label")
    y += card_h + 24
    h = bottom_nav(s, y, "home")
    return s, h


def screen_article_snow():
    s = S()
    header(s, back=True, share=True, bookmark=True)
    y = 80
    y += s.para(SP, y, CW - 2 * SP, "Famous snowboarder wins Grand Prix", "headline") + 10
    s.text([SP, y, 180, 14], "November 13, 2022", style="meta")
    s.text([RIGHT - 90, y, 90, 14], "2 min read", style="meta_r")
    y += 28
    s.photo([SP, y, CW - 2 * SP, 214], "snow_action", r=12)
    y += 214 + 20
    y += s.para(SP, y, CW - 2 * SP,
                "CALIFORNIA – The young and famous snowboarder wins his second grand prix "
                "this year. His tricks are still new to the world and he's quickly winning "
                "every competition he enters.", "body_txt") + 16
    y += s.para(SP, y, CW - 2 * SP,
                "Everyone knows young, 18 year old snowboarder Jenna Shae. She's been labeled "
                "a rebel for years, but this girl just can't stop winning. She started "
                "snowboarding at age 7, and now wins grand prix races with ease. At age 18 "
                "she is still going strong, and will hopefully keep that hot streak alive "
                "well into adulthood.", "body_txt") + 20
    s.photo([SP, y, CW - 2 * SP, 190], "goggles", r=12)
    y += 190 + 20
    s.photo([SP, y, 74, 74], "hug", r=10)
    qx = SP + 92
    qh = s.para(qx, y, RIGHT - qx,
                '"This is a great story. My daughter started snowboarding when she was '
                '7 years old and now at 16, I am so excited to hear about her latest win."',
                "quote")
    y += max(74, qh) + 22
    y += s.para(SP, y, CW - 2 * SP,
                "She is a trained athlete who competed in various countries and became a "
                "number one. Her coach is super proud of her results and thinks that she can "
                "win Olympics for sure. The sport of snowboarding has been around since the "
                "1960s, but it wasn't until the 1998 Winter Olympics that it made its Olympic "
                "debut at the Nagano Games. Men and women both take their turns on giant "
                "slalom and halfpipe courses, earning points based on style and course "
                "completion. In 2002, snowboardcross made its debut as a full-on medal sport, "
                "with men and women racing against each other in one course.", "body_txt") + 22
    s.line([SP, y], [RIGHT, y], **stroke(1.2, color="line"))
    y += 20
    s.text([SP, y, 220, 16], "More from the author", style="section")
    y += 26
    tw = (CW - 2 * SP - 24) / 3
    for i, kind in enumerate(["mountains", "city", "portrait"]):
        s.photo([SP + i * (tw + 12), y, tw, 78], kind, r=10)
    y += 78 + 30
    return s, y


def screen_article_cycling():
    s = S()
    header(s, back=True, bookmark=True)
    y = 80
    y += s.para(SP, y, CW - 2 * SP, "French Cycling Tour is postponed", "headline") + 10
    s.text([SP, y, 180, 14], "November 13, 2022", style="meta")
    s.text([RIGHT - 90, y, 90, 14], "2 min read", style="meta_r")
    y += 28
    s.photo([SP, y, CW - 2 * SP, 206], "cycling", r=12)
    y += 206 + 20
    y += s.para(SP, y, CW - 2 * SP,
                "PARIS – The famous tour happening since 1935 is being postponed for the "
                "first time in the history due to lack of resources and partnerships.",
                "body_txt") + 16
    y += s.para(SP, y, CW - 2 * SP,
                "The organizators tried to find the way to make ends meet but unfortunately "
                "had no luck. The tour is postponed for next year and it will take the same "
                "route as was originally planned.", "body_txt") + 18
    s.rect([SP, y + 4, 3, 66], fill="accent", radius=1.5)
    qh = s.para(SP + 18, y, RIGHT - SP - 18,
                '"It is a big misfortune", said one of the racers who was expected to snatch '
                "this year's trophy.", "quote_lg")
    y += qh + 22
    s.photo([SP, y, CW - 2 * SP, 176], "canal", r=12)
    y += 176 + 12
    s.text([0, y, CW, 14], "Tour route in 2020 went through The Netherlands.", style="caption")
    y += 28
    y += s.para(SP, y, CW - 2 * SP,
                "Take a look in our gallery, where we prepared the digest of the best moments "
                "from previous years.", "body_txt") + 20
    gw, gh = 128, 92
    gx = CW / 2 - gw - 8
    s.icon(icon_chev, SP + 4, y + gh / 2, -1)
    s.photo([gx, y, gw, gh], "gallery1", r=10)
    s.photo([gx + gw + 16, y, gw, gh], "gallery2", r=10)
    s.icon(icon_chev, RIGHT - 4, y + gh / 2, 1)
    y += gh + 26
    s.line([SP, y], [RIGHT, y], **stroke(1.2, color="line"))
    y += 20
    s.text([SP, y, 200, 16], "More articles", style="section")
    y += 26
    for thumb, title, minutes in [("stadium", "Hometown wins 5:1 in Cup", 4),
                                  ("football", "Footballer leaves British FC", 2)]:
        y += article_row(s, y, thumb, title, minutes, thumb_size=52) + 16
    y += 6
    s.text([SP, y, 220, 16], "More from the author", style="section")
    y += 26
    s.photo([SP, y, 126, 92], "interview", r=10)
    tx = SP + 142
    th = s.para(tx, y + 4, RIGHT - tx, "Interview with footballer", "list_title")
    s.text([tx, y + th + 12, 90, 14], "10 min read", style="meta")
    bw = measure("FEATURED", "badge") + 20
    s.rect([tx, y + th + 34, bw, 20], fill="accent", radius=5)
    s.text([tx, y + th + 39, bw, 12], "FEATURED", style="badge")
    y += 92 + 30
    return s, y


def screen_saved():
    s = S()
    header(s, back=False)
    y = 88
    s.text([SP, y, 220, 18], "My Saved Articles", style="section")
    y += 28
    for thumb, title, minutes in [("elections", "Elections predictions", 5),
                                  ("movies", "New blockbusters you must see", 2),
                                  ("pm", "Who will be new PM?", 4),
                                  ("digest", "Weekly digest: The most important news", 7)]:
        s.photo([SP, y, 52, 52], thumb, r=10)
        tx = SP + 68
        th = s.para(tx, y + 1, RIGHT - 30 - tx, title, "saved_title")
        s.text([tx, y + th + 7, 90, 13], f"{minutes} min read", style="meta")
        s.icon(icon_bookmark, RIGHT - 8, y + 12, 0.9, "accent", filled=True)
        y += max(52, th + 20) + 20
    y += 10
    s.text([SP, y, 260, 18], "My favorite categories", style="section")
    y += 28
    cats = [("Politics", icon_mic, True), ("Sports", icon_ball, False),
            ("World news", icon_mail, True), ("Culture", icon_palette, False),
            ("Business", icon_chart, False), ("Technology", icon_monitor, False)]
    tile_w = (CW - 2 * SP - 12) / 2
    for i, (label, ic, hot) in enumerate(cats):
        tx = SP + (i % 2) * (tile_w + 12)
        ty = y + (i // 2) * 70
        s.rect([tx, ty, tile_w, 58], fill="paper", radius=12, **stroke(1.3, color="border"))
        s.rect([tx + 12, ty + 12, 34, 34], fill="accent_soft" if hot else "soft", radius=9)
        s.icon(ic, tx + 29, ty + 29, "accent" if hot else "#6B6660")
        s.text([tx + 58, ty + 21, tile_w - 62, 16], label, style="cat_label")
    y += 3 * 70 + 14
    h = bottom_nav(s, y, "saved")
    return s, h


def screen_newsletter():
    s = S()
    header(s, back=True)
    s.text([SP, 92, 300, 22], "Choose your newsletter", style="h_screen")
    y = 134
    items = [("Daily news", True), ("Weekly digest", False), ("Sports commentary", False),
             ("Business predictions", True), ("Culture tips", False)]
    for label, checked in items:
        s.rect([SP, y, CW - 2 * SP, 52], fill="accent_soft" if checked else "paper", radius=12,
               **stroke(1.4, color="accent_border" if checked else "border"))
        bx, by = SP + 18, y + 17
        if checked:
            s.rect([bx, by, 18, 18], fill="accent", radius=5)
            s.icon(icon_check, bx + 9, by + 9, 0.9)
        else:
            s.rect([bx, by, 18, 18], fill="paper", radius=5, **stroke(1.6, color="#C9C5BF"))
        s.text([bx + 32, y + 18, 220, 17], label, style="check_label")
        y += 64
    button(s, 700 - 74, "Confirm subscription")
    return s, 700


def screen_subscribed():
    s = S()
    s.text([75, 205, 240, 96], "You are now subscribed!", style="big_title")
    s.ellipse([CW / 2, 400], 34, 34, fill="accent")
    s.ellipse([CW / 2, 400], 34, 34, fill="none", **stroke(6, color="#F6C0AC"))
    s.icon(icon_check, CW / 2, 400, 2.4, "paper", 4.5)
    button(s, 700 - 74, "Back Home")
    return s, 700


# --------------------------------------------------------------------------- document

SCREEN_META = [
    ("screen-onboarding", "Onboarding"),
    ("screen-plans", "Choose subscription"),
    ("screen-interests", "Pick interests"),
    ("screen-feed", "Home feed"),
    ("screen-article-a", "Snowboard article"),
    ("screen-article-b", "Cycling article"),
    ("screen-saved", "Saved & categories"),
    ("screen-newsletter", "Choose newsletter"),
    ("screen-done", "Subscribed"),
]
# Navigation graph: (from, to, label). Adjacent edges run through the gap at a
# shared datum height; lane edges drop below the board; the back edge returns.
EDGES_ADJ = [(0, 1, "Subscribe"), (1, 2, "Proceed"), (2, 3, "Continue"),
             (3, 4, "Read more"), (7, 8, "Confirm")]
EDGES_LANE = [(3, 5, "More articles", 1), (3, 6, "Saved tab", 2), (3, 7, "Sign up", 3)]
EDGE_BACK = (8, 3, "Back Home", 4)

TOP = 196          # header band above the board
FLOW_Y = 340       # shared datum height for the adjacent-arrow chain (content y)


def _flow_header(page, canvas_w):
    page.text([MARGIN, 42, 900, 38], "NewsPulse — composite flow map", style="flow_title")
    page.text([MARGIN, 90, 1400, 20],
              "One document, nine linked views. defs.tokens close the palette and type for "
              "every screen; defs.params drive the plan prices; the annotation layer below "
              "carries the navigation graph.", style="flow_sub")
    lx = MARGIN
    legend = [("defs.params   monthly", "legend_txt", "monthly"),
              ("=monthly_price", "legend_num", "45"),
              ("·  annual = monthly×11 + 5  →", "legend_txt", None),
              ("=annual_price", "legend_num", "500"),
              ("·  two-year = annual×2 − 100  →", "legend_txt", None),
              ("=two_year_price", "legend_num", "900")]
    for txt, st, resolved in legend:
        shown = resolved if txt.startswith("=") else txt
        w = measure(shown, st) + 4
        page.text([lx, 120, w, 16], txt, style=st)
        lx += w + 8
    # Navigation index: LinkInline runs — internal #ids plus one external URL.
    spans = []
    for i, (slug, name) in enumerate(SCREEN_META):
        spans.append({"kind": "link", "href": f"#{slug}",
                      "content": [{"text": f"{i + 1:02d} {name}", "style": "link_run"}]})
        spans.append({"text": " · ", "style": "idx_sep"})
    spans.append({"kind": "link", "href": "https://example.com/newspulse-spec",
                  "content": [{"text": "spec ↗", "style": "link_run"}]})
    page.text([MARGIN, 150, canvas_w - 2 * MARGIN, 18], spans, style="idx_sep")


def build_document(show_construction: bool = False):
    doc = DocumentBuilder(title="NewsPulse mobile UI kit — composite flow map")
    if show_construction:
        doc.meta(show_construction=True)
    for name, color in COLORS.items():
        doc.define_color(name, color)
    for name, st in STYLES.items():
        doc.define_text_style(name, **st)

    screens = [screen_welcome(), screen_subscription(), screen_interests(), screen_feed(),
               screen_article_snow(), screen_article_cycling(), screen_saved(),
               screen_newsletter(), screen_subscribed()]
    ow = CW + 2 * BP
    max_outer = max(h for _, h in screens) + 2 * BP
    bottom = TOP + max_outer

    def lane_y(k):
        return bottom + 58 + (k - 1) * 30

    canvas_w = 2 * MARGIN + 9 * ow + 8 * GAP
    canvas_h = lane_y(4) + 70
    xs = [MARGIN + i * (ow + GAP) for i in range(9)]
    outers = [h + 2 * BP for _, h in screens]

    page = doc.page("newspulse-ui-kit", canvas={"size": [canvas_w, canvas_h], "units": "px"},
                    coordinate_mode="absolute")
    page.layer("stage")
    page.rect([0, 0, canvas_w, canvas_h], fill="stage")
    _flow_header(page, canvas_w)

    page.layer("screens")
    for i, (s, h) in enumerate(screens):
        with page.grouped(transform=Mat3.translate(xs[i] + BP, TOP + BP)) as g:
            frame(g, CW, h)
            for op in s.ops:
                op(g)

    # ---- the navigation graph: an annotation-role layer over the board -------
    page.layer("flow", role="annotation")
    for i, (slug, name) in enumerate(SCREEN_META):
        page.rect([xs[i] - 8, TOP - 8, ow + 16, outers[i] + 16], id=slug, fill="none",
                  radius=36, **stroke(1.1, color="#C9C2BA", dash=[7, 5]))
        by = TOP + outers[i] + 24
        page.ellipse([xs[i] + 12, by, ], 10, 10, fill="accent")
        page.text([xs[i] + 2, by - 6, 20, 13], str(i + 1), style="step_num")
        page.text([xs[i] + 30, by - 7, ow - 30, 15], name, style="screen_name")

    for a, b, label in EDGES_ADJ:
        gap_cx = xs[a] + ow + 8 + (GAP - 16) / 2
        y = TOP + BP + FLOW_Y
        page.rect([gap_cx - 44, y - 30, 88, 16], fill="stage", radius=8)
        page.connector({"ref": SCREEN_META[a][0], "side": "east",
                        "offset": y - (TOP - 8 + (outers[a] + 16) / 2)},
                       {"ref": SCREEN_META[b][0], "side": "west",
                        "offset": y - (TOP - 8 + (outers[b] + 16) / 2)},
                       label=label, label_box=[gap_cx - 44, y - 29, 88, 14],
                       label_style="flow_label", arrow_end=True,
                       **stroke(1.6, color="ink", cap="round"))
    # Spread the feed's three departures (and the back-edge arrival) along its
    # south side so the lane drops do not superpose on one vertical.
    for (a, b, label, k), off in zip(EDGES_LANE, (-70, 0, 70)):
        ly = lane_y(k)
        ca, cb = xs[a] + ow / 2 + off, xs[b] + ow / 2
        mx = (ca + cb) / 2
        page.connector({"ref": SCREEN_META[a][0], "side": "south", "offset": off},
                       {"ref": SCREEN_META[b][0], "side": "south"},
                       route=[[ca, ly], [cb, ly]], route_kind="orthogonal",
                       label=label, label_box=[mx - 52, ly - 21, 104, 13],
                       label_style="flow_label", arrow_end=True,
                       **stroke(1.6, color="ink", cap="round"))
    a, b, label, k = EDGE_BACK
    ly = lane_y(k)
    ca, cb = xs[a] + ow / 2, xs[b] + ow / 2 + 140
    mx = (ca + cb) / 2
    page.connector({"ref": SCREEN_META[a][0], "side": "south"},
                   {"ref": SCREEN_META[b][0], "side": "south", "offset": 140},
                   route=[[ca, ly], [cb, ly]], route_kind="orthogonal",
                   label=f"{label}  (returns to feed)",
                   label_box=[mx - 92, ly - 21, 184, 13], label_style="flow_label",
                   arrow_end=True, **stroke(1.6, color="accent", dash=[6, 5], cap="round"))

    # ---- CAD-style datum layer: hidden unless meta.show_construction ---------
    page.layer("datum", role="construction")
    for i in range(9):
        cx = xs[i] + ow / 2
        page.line([cx, TOP - 26], [cx, bottom + 18], **stroke(1, color="#3AA6B8", dash=[4, 4]))
    page.line([MARGIN - 30, TOP], [canvas_w - MARGIN + 30, TOP],
              **stroke(1, color="#3AA6B8", dash=[4, 4]))
    page.line([MARGIN - 30, TOP + BP + FLOW_Y], [canvas_w - MARGIN + 30, TOP + BP + FLOW_Y],
              **stroke(1, color="#3AA6B8", dash=[4, 4]))
    page.text([MARGIN - 30, TOP - 16, 220, 13], f"top datum  y={TOP}", style="datum_txt")
    page.text([MARGIN - 30, TOP + BP + FLOW_Y - 16, 260, 13],
              f"flow datum  y={TOP + BP + FLOW_Y}", style="datum_txt")
    return doc


def build():
    return build_document()


def _write(path: str, doc: object) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(path)


def main() -> None:
    builder = build_document()
    report = validate_static_rules(builder.build())
    if not report.ok:
        for issue in report.issues:
            print(issue)
        raise SystemExit(1)
    os.makedirs(OUT_DIR, exist_ok=True)

    # The associative source: defs.params + unresolved '=expr' driven labels.
    doc = builder.build_dict()
    doc.setdefault("defs", {})["params"] = dict(PARAMS)
    _write(OUT_FLOW, doc)

    # Resolved for the CLI render path (the MCP pipeline resolves params itself;
    # frameforge.cli does not yet, so the client resolves at its own boundary).
    resolved = resolve_params(doc)
    _write(OUT_RESOLVED, resolved)

    # Same document with the construction datum layer opted in.
    datum = copy.deepcopy(resolved)
    datum.setdefault("meta", {})["show_construction"] = True
    _write(OUT_DATUM, datum)


if __name__ == "__main__":
    main()
