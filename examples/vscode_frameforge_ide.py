#!/usr/bin/env python3
"""Recreate the FrameForge VSCode IDE screenshot with the FrameGraph SDK.

This authors the whole window — title/menu bar, activity bar, Explorer side
bar, a two-up editor split (an AI chat panel on the left, the rendered
``FIXTURE-STATUS.md`` markdown table on the right), the integrated terminal
panel, and the blue status bar — out of core SDK primitives (``rect``/``text``/
``line``/``ellipse``/``polygon``) plus the layout-native ``local`` groups and a
couple of ``widgets``. It lowers to a single absolute-coordinate page sized to
the displayed screenshot (2000×1145) so coordinates map straight from the image.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framegraph.sdk import DocumentBuilder, stroke  # noqa: E402
from framegraph.sdk.metrics import measure_text, wrap_text  # noqa: E402

OUT = ROOT / "examples" / "fixtures" / "vscode-frameforge-ide.fg.yaml"

W, H = 2000, 1145

# ---- VSCode "Light+" palette ------------------------------------------------ #
C = {
    "title_bg": "#e8e8e8",
    "activity_bg": "#f3f3f3",
    "sidebar_bg": "#f3f3f3",
    "editor_bg": "#ffffff",
    "tab_inactive": "#ececec",
    "tab_active": "#ffffff",
    "panel_bg": "#ffffff",
    "status_bg": "#007acc",
    "border": "#e0e0e0",
    "border_strong": "#cecece",
    "ink": "#333333",
    "sub": "#616161",
    "muted": "#8a8a8a",
    "icon": "#5a5a5a",
    "accent": "#007acc",
    "sel_bg": "#e4e6f1",
    "code_bg": "#f3f3f3",
    "code_red": "#a31515",
    "folder": "#c09553",
    "md_blue": "#4a7ebb",
    "git_mod": "#9a6700",
    "white": "#ffffff",
    "term_green": "#1a8a1a",
    "term_red": "#cd3131",
    "term_blue": "#2472c8",
    "term_yellow": "#b58900",
    "rec_red": "#e51400",
}

MONO = ["SFMono-Regular", "Menlo", "Consolas", "monospace"]
SANS = ["Segoe UI", "Inter", "Helvetica", "Arial", "sans-serif"]


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameForge IDE — screenshot recreation", profile="deck")

    page = b.page(
        "ide",
        canvas={"size": [W, H], "units": "px"},
        coordinate_mode="absolute",
    ).layer("chrome")

    # ---- helpers ---------------------------------------------------------- #
    def txt(x, y, w, h, s, *, size=13, color=C["ink"], weight=400, family=SANS,
            align="left", valign="middle", nowrap=True, **extra):
        st = {
            "font_family": family, "font_size": size, "font_weight": weight,
            "color": color, "align": align, "vertical_align": valign,
            "overflow": "clip",
        }
        if nowrap:
            st["white_space"] = "nowrap"
        st.update(extra)
        page.text([x, y, w, h], s, style=st)

    def mono(x, y, w, h, s, **kw):
        kw.setdefault("family", MONO)
        kw.setdefault("size", 12.5)
        txt(x, y, w, h, s, **kw)

    def box(x, y, w, h, **kw):
        page.rect([x, y, w, h], decorative=True, **kw)

    sw = lambda px, color: stroke(px, color=color)  # noqa: E731

    # ===================================================================== #
    #  1. TITLE / MENU BAR
    # ===================================================================== #
    box(0, 0, W, 30, fill=C["title_bg"])
    page.line([0, 30], [W, 30], **sw(1, C["border_strong"]))

    # VSCode ribbon logo (simplified blue mark)
    page.polygon([[14, 8], [25, 4], [29, 7], [20, 15], [29, 23], [25, 26], [14, 22],
                  [10, 18], [10, 12]], fill="#0a6cba")
    page.polygon([[20, 15], [14, 8], [14, 22]], fill="#1f8ad6")

    mx = 42
    for label in ("File", "Edit", "Selection", "View", "Go", "Run", "Terminal", "Help"):
        mw = measure_text(label, font_family=SANS, font_size=12.5)
        txt(mx, 0, mw + 8, 30, label, size=12.5, color=C["sub"])
        mx += mw + 26   # measured advance + inter-menu gap (no magic per-item x)

    # nav arrows
    txt(640, 0, 20, 30, "←", size=15, color=C["muted"], align="center")
    txt(666, 0, 20, 30, "→", size=15, color=C["muted"], align="center")

    # centred command bar
    box(700, 5, 640, 20, fill=C["white"], radius=4, **sw(1, C["border_strong"]))
    page.ellipse([714, 15], 4, 4, fill=C["rec_red"])
    txt(700, 5, 640, 20, "frameforge [SSH: 192.168.199.25]", size=12, color=C["sub"],
        align="center")
    # right-of-bar badges
    page.ellipse([1286, 15], 6, 6, fill=C["rec_red"])
    txt(1281, 5, 12, 20, "13", size=9, color=C["white"], align="center", family=MONO)
    txt(1305, 5, 24, 20, "\U0001f5e9", size=12, color=C["muted"], align="center")
    txt(1330, 6, 14, 18, "⌄", size=14, color=C["muted"], align="center")

    # right side: editor-layout toggles + window controls (close near the corner)
    for gx in (1772, 1802, 1832):
        box(gx, 9, 18, 13, fill="none", **sw(1.3, C["icon"]), radius=2)
    page.line([1778, 9], [1778, 22], **sw(1.3, C["icon"]))  # sidebar-toggle divider
    txt(1866, 0, 24, 30, "—", size=12, color=C["icon"], align="center")
    box(1906, 9, 12, 12, fill="none", **sw(1.3, C["icon"]), radius=1)
    txt(1948, 0, 24, 30, "✕", size=13, color=C["icon"], align="center")

    # ===================================================================== #
    #  2. ACTIVITY BAR  (x 0..48)
    # ===================================================================== #
    box(0, 30, 48, H - 30 - 25, fill=C["activity_bg"])
    page.line([48, 30], [48, H - 25], **sw(1, C["border"]))
    activity_bar(page, C, sw, txt)

    # ===================================================================== #
    #  3. SIDE BAR / EXPLORER  (x 48..345)
    # ===================================================================== #
    box(48, 30, 297, H - 30 - 25, fill=C["sidebar_bg"])
    page.line([345, 30], [345, H - 25], **sw(1, C["border"]))
    explorer(page, C, sw, txt, MONO)

    # ===================================================================== #
    #  4. EDITOR + TERMINAL REGION  (x 345..2000)
    # ===================================================================== #
    EDIT_X0, EDIT_X1 = 345, W
    SPLIT_X = 1178
    EDIT_TOP, EDIT_BOT = 30, 812

    # editor background bands — strip sits lighter than the inactive tab chips
    box(EDIT_X0, EDIT_TOP, EDIT_X1 - EDIT_X0, 42, fill=C["sidebar_bg"])  # tab strip
    box(EDIT_X0, EDIT_TOP + 42, SPLIT_X - EDIT_X0, EDIT_BOT - EDIT_TOP - 42, fill=C["editor_bg"])
    box(SPLIT_X, EDIT_TOP + 42, EDIT_X1 - SPLIT_X, EDIT_BOT - EDIT_TOP - 42, fill=C["editor_bg"])
    page.line([SPLIT_X, EDIT_TOP], [SPLIT_X, EDIT_BOT], **sw(1, C["border"]))
    page.line([EDIT_X0, EDIT_TOP + 42], [EDIT_X1, EDIT_TOP + 42], **sw(1, C["border"]))

    left_editor(page, C, sw, txt, mono, box, SANS, MONO)
    right_editor(page, C, sw, txt, mono, box, SPLIT_X, MONO)

    # ===================================================================== #
    #  5. TERMINAL PANEL  (x 345..2000, y 812..1120)
    # ===================================================================== #
    terminal(page, C, sw, txt, mono, box, EDIT_X0, EDIT_X1, MONO)

    # ===================================================================== #
    #  6. STATUS BAR  (blue)
    # ===================================================================== #
    status_bar(page, C, txt, W, H)

    return b


# ------------------------------------------------------------------------- #
#  region builders
# ------------------------------------------------------------------------- #
def activity_icon(page, x, y, kind, color, sw):
    """Draw a simplified 24px activity-bar glyph centred at (x, y)."""
    if kind == "files":
        page.rect([x - 7, y - 9, 10, 18], fill="none", **sw(1.6, color), radius=1)
        page.rect([x - 3, y - 6, 10, 18], fill="none", **sw(1.6, color), radius=1)
    elif kind == "search":
        page.ellipse([x - 2, y - 2], 6, 6, fill="none", **sw(1.6, color))
        page.line([x + 3, y + 3], [x + 8, y + 8], **sw(1.8, color))
    elif kind == "scm":
        page.ellipse([x - 5, y - 6], 3, 3, fill="none", **sw(1.6, color))
        page.ellipse([x - 5, y + 7], 3, 3, fill="none", **sw(1.6, color))
        page.ellipse([x + 6, y - 1], 3, 3, fill="none", **sw(1.6, color))
        page.line([x - 5, y - 3], [x - 5, y + 4], **sw(1.6, color))
        page.path(f"M {x-5} {y-1} C {x-5} {y+3} {x+6} {y-1} {x+6} {y+2}",
                  fill="none", **sw(1.6, color))
    elif kind == "debug":
        page.ellipse([x, y], 6, 7, fill="none", **sw(1.6, color))
        page.line([x - 9, y], [x - 6, y], **sw(1.6, color))
        page.line([x + 6, y], [x + 9, y], **sw(1.6, color))
        page.line([x - 8, y - 6], [x - 5, y - 4], **sw(1.6, color))
        page.line([x + 8, y - 6], [x + 5, y - 4], **sw(1.6, color))
    elif kind == "extensions":
        for dx, dy in ((-8, -8), (1, -8), (-8, 1)):
            page.rect([x + dx, y + dy, 7, 7], fill="none", **sw(1.5, color))
        page.rect([x + 1, y + 1, 7, 7], fill=color)
    elif kind == "sparkle":
        page.polygon([[x, y - 9], [x + 2, y - 2], [x + 9, y], [x + 2, y + 2],
                      [x, y + 9], [x - 2, y + 2], [x - 9, y], [x - 2, y - 2]],
                     fill="none", **sw(1.5, color))
    elif kind == "robot":
        page.rect([x - 8, y - 5, 16, 12], fill="none", **sw(1.6, color), radius=3)
        page.ellipse([x - 3, y + 1], 1.6, 1.6, fill=color)
        page.ellipse([x + 3, y + 1], 1.6, 1.6, fill=color)
        page.line([x, y - 5], [x, y - 9], **sw(1.6, color))
        page.ellipse([x, y - 10], 1.8, 1.8, fill=color)
    elif kind == "account":
        page.ellipse([x, y - 3], 5, 5, fill="none", **sw(1.6, color))
        page.path(f"M {x-8} {y+9} C {x-8} {y+1} {x+8} {y+1} {x+8} {y+9}",
                  fill="none", **sw(1.6, color))
    elif kind == "gear":
        page.ellipse([x, y], 4, 4, fill="none", **sw(1.6, color))
        for ang in range(0, 360, 45):
            import math
            rad = math.radians(ang)
            page.line([x + 5 * math.cos(rad), y + 5 * math.sin(rad)],
                      [x + 9 * math.cos(rad), y + 9 * math.sin(rad)], **sw(1.6, color))


def activity_bar(page, C, sw, txt):
    items = [(64, "files", True), (118, "search", False), (172, "scm", False),
             (226, "debug", False), (280, "sparkle", False), (334, "robot", False),
             (388, "extensions", False)]
    for cy, kind, active in items:
        if active:
            page.rect([0, cy - 24, 2, 48], fill=C["accent"], decorative=True)
        activity_icon(page, 24, cy, kind, C["ink"] if active else C["icon"], sw)
    # source-control badge "2"
    page.ellipse([34, 162], 8, 8, fill=C["accent"])
    txt(26, 154, 16, 16, "2", size=10, color=C["white"], align="center", weight=700)
    # bottom group
    activity_icon(page, 24, 1010, "account", C["icon"], sw)
    activity_icon(page, 24, 1062, "gear", C["icon"], sw)


def file_icon(page, x, y, color, sw):
    """A small page glyph with a folded corner."""
    page.polygon([[x, y], [x + 8, y], [x + 12, y + 4], [x + 12, y + 15], [x, y + 15]],
                 fill="none", **sw(1.4, color))
    page.polyline([[x + 8, y], [x + 8, y + 4], [x + 12, y + 4]], **sw(1.4, color))


def folder_icon(page, x, y, color):
    page.polygon([[x, y + 2], [x + 5, y + 2], [x + 7, y + 5], [x + 14, y + 5],
                  [x + 14, y + 14], [x, y + 14]], fill=color)


def explorer(page, C, sw, txt, MONO):
    # headers
    txt(64, 42, 200, 18, "EXPLORER", size=11, color=C["sub"], weight=600, letter_spacing=0.4)
    txt(322, 42, 18, 18, "⋯", size=14, color=C["sub"], align="center")
    txt(58, 70, 16, 18, "⌄", size=13, color=C["ink"], align="center")
    txt(74, 70, 260, 18, "FRAMEFORGE [SSH: 192.168.199.25]", size=11, color=C["ink"],
        weight=700)

    folders = [".agent-tasks", ".github", ".repo", ".venv", "docs", "examples",
               "fixtures", "framegraph", "grammar", "models", "schema", "spec",
               "tests", "tooling", "viewer"]
    files = [("CHANGELOG.md", None, C["md_blue"]),
             ("CLAUDE.md", None, C["md_blue"]),
             ("codebase-standards.md", None, C["md_blue"]),
             ("DISCLAIMER.md", None, C["md_blue"]),
             ("FIXTURE-STATUS.md", "M", C["md_blue"]),  # selected row
             ("Makefile", "M", C["icon"]),
             ("mkdocs.yml", "!", "#d18616"),
             ("pyproject.toml", None, C["icon"]),
             ("README.md", None, C["md_blue"]),
             ("uv.lock", None, C["icon"])]

    y = 92
    rh = 22
    for name in folders:
        txt(58, y, 14, rh, "›", size=13, color=C["sub"], align="center")
        folder_icon(page, 74, y + 3, C["folder"])
        txt(92, y, 230, rh, name, size=13, color=C["ink"])
        y += rh
    # .gitignore is the first "file" but sits right after viewer with M marker
    git_files = [(".gitignore", "M", C["icon"])] + files
    for name, marker, icon_color in git_files:
        selected = name == "FIXTURE-STATUS.md"
        if selected:
            page.rect([48, y, 297, rh], fill=C["sel_bg"], decorative=True)
            page.rect([48, y, 2, rh], fill=C["accent"], decorative=True)
        file_icon(page, 76, y + 3, icon_color, sw)
        txt(92, y, 215, rh, name, size=13, color=C["ink"])  # selection isn't bolded
        if marker:
            mcolor = C["git_mod"] if marker == "M" else "#d18616"
            txt(318, y, 16, rh, marker, size=12, color=mcolor, align="center", weight=700)
        y += rh


def left_editor(page, C, sw, txt, mono, box, SANS, MONO):
    # ---- tab strip ---- #
    box(345, 30, 255, 42, fill=C["tab_inactive"])
    txt(360, 30, 20, 42, "✳", size=12, color="#c8862a", align="center")
    txt(378, 30, 210, 42, "Drift risk map developme…", size=12.5, color=C["sub"])
    page.line([600, 30], [600, 72], **sw(1, C["border"]))
    box(600, 30, 222, 42, fill=C["tab_active"])  # Light+ active tab: white, no top accent
    txt(615, 30, 20, 42, "✳", size=12, color="#c8862a", align="center")
    txt(633, 30, 165, 42, "Fix calendar-3day.fg.yam…", size=12.5, color=C["ink"])
    txt(798, 30, 18, 42, "✕", size=12, color=C["sub"], align="center")
    # tab-bar action icons (sparkle, openai, split, lock, …)
    txt(1048, 30, 20, 42, "✳", size=13, color=C["muted"], align="center")
    page.ellipse([1078, 51], 8, 8, fill="none", **sw(1.4, C["muted"]))
    box(1108, 42, 16, 16, fill="none", **sw(1.4, C["muted"]), radius=2)
    page.line([1116, 42], [1116, 58], **sw(1.4, C["muted"]))
    # lock (this AI tab is locked, per the title bar lock glyph)
    page.rect([1134, 47, 12, 9], fill="none", **sw(1.3, C["icon"]), radius=1)
    page.path("M 1137 47 C 1137 42 1143 42 1143 47", fill="none", **sw(1.3, C["icon"]))
    txt(1152, 30, 18, 42, "⋯", size=14, color=C["muted"], align="center")

    # ---- chat content ---- #
    txt(365, 78, 600, 22, "Fix calendar-3day.fg.yaml fixture", size=15, color=C["ink"],
        weight=600)

    # prompt input box
    box(382, 126, 790, 30, fill=C["white"], radius=6, **sw(1, C["border_strong"]))
    txt(400, 126, 760, 30, "fix this fixture calendar-3day.fg.yaml", size=13, color=C["ink"])

    # "OUT IDENTICAL" result row
    box(415, 176, 720, 26, fill=C["white"], radius=4, **sw(1, C["border"]))
    mono(432, 176, 40, 26, "OUT", color=C["muted"], size=11.5)
    mono(478, 176, 200, 26, "IDENTICAL", color=C["sub"], size=12.5)

    # Thinking
    page.ellipse([398, 240], 4, 4, fill=C["muted"])
    txt(414, 230, 200, 20, "Thinking", size=13, color=C["sub"])

    # paragraph — wrapped at the real renderer metric, not hand-split
    para = ("Both copies are identical. The status file shows 0 errors but 4 warnings "
            "(containment, tabular-box-model). Let me run the validator to see the "
            "actual diagnostics.")
    for i, ln in enumerate(wrap_text(para, width=722, font_family=SANS, font_size=13)):
        txt(418, 262 + i * 22, 730, 20, ln, size=13, color=C["ink"])

    # Bash block #1
    txt(418, 330, 60, 20, "Bash", size=13, color=C["ink"], weight=700)
    txt(466, 330, 400, 20, "Run the validator on the fixture", size=13, color=C["sub"])
    box(415, 356, 735, 96, fill=C["code_bg"], radius=6, **sw(1, C["border"]))
    mono(432, 360, 30, 22, "IN", color=C["muted"], size=11)
    mono(470, 360, 680, 22,
         'ls tooling/ && echo "---" && python tooling/validate.py fixtures/calenda…',
         color=C["ink"])
    mono(432, 396, 30, 22, "OUT", color=C["muted"], size=11)
    for i, line in enumerate(("check_accessibility.py", "check_grammar_sync.py", "codemod.py")):
        mono(470, 392 + i * 18, 400, 18, line, color=C["sub"])

    # Bash block #2
    txt(418, 500, 60, 20, "Bash", size=13, color=C["ink"], weight=700)
    txt(466, 500, 400, 20, "Run validator with python3", size=13, color=C["sub"])
    box(415, 526, 735, 86, fill=C["code_bg"], radius=6, **sw(1, C["border"]))
    mono(432, 530, 30, 22, "IN", color=C["muted"], size=11)
    mono(470, 530, 680, 22,
         "python3 tooling/validate.py fixtures/calendar-3day.fg.yaml 2>&1 | head -80",
         color=C["ink"])
    mono(432, 566, 36, 22, "OUT", color=C["muted"], size=11)
    mono(470, 562, 600, 18, "WARN  calendar-3day.fg.yaml  (0 error(s), 4 warning(s))",
         color=C["sub"])
    mono(486, 580, 660, 18,
         "[WARN] containment @ pages[0].layers[1].objects[0]: object box extends outside the 412×1040 canv…",
         color=C["sub"], size=11)
    mono(486, 596, 660, 18,
         "[WARN] containment @ pages[0].layers[2].objects[20]: object box extends outside the 412×1040 can…",
         color=C["sub"], size=11)

    # Actualizing…
    page.ellipse([398, 672], 4, 4, fill=C["muted"])
    txt(414, 662, 200, 20, "Actualizing…", size=13, color=C["sub"])

    # bottom "Queue another message…" composer
    box(382, 706, 790, 92, fill=C["white"], radius=8, **sw(1, C["border_strong"]))
    txt(400, 716, 740, 22, "Queue another message…", size=13, color=C["muted"])
    page.ellipse([412, 776], 9, 9, fill="none", **sw(1.4, C["icon"]))
    page.line([412, 772], [412, 780], **sw(1.4, C["icon"]))
    page.line([408, 776], [416, 776], **sw(1.4, C["icon"]))
    box(434, 768, 18, 16, fill="none", **sw(1.3, C["icon"]), radius=3)
    txt(950, 766, 140, 20, "</> Edit automatically", size=12, color=C["sub"], align="right")
    box(1126, 766, 22, 22, fill="#3b3b3b", radius=4)
    page.rect([1132, 772, 10, 10], fill=C["white"], decorative=True)

    # scrollbar thumb (content scrolled near the top)
    box(1168, 80, 4, 300, fill="#c8c8c8", radius=2)


def right_editor(page, C, sw, txt, mono, box, SPLIT_X, MONO):
    x0 = SPLIT_X
    # tab strip
    box(x0, 30, 132, 42, fill=C["tab_inactive"])
    file_icon(page, x0 + 12, 43, C["icon"], sw)
    txt(x0 + 30, 30, 74, 42, ".gitignore", size=12.5, color=C["sub"])
    txt(x0 + 106, 30, 16, 42, "M", size=11, color=C["git_mod"], align="center", weight=700)
    page.line([x0 + 132, 30], [x0 + 132, 72], **sw(1, C["border"]))
    box(x0 + 132, 30, 220, 42, fill=C["tab_active"])
    file_icon(page, x0 + 144, 43, C["md_blue"], sw)
    txt(x0 + 162, 30, 150, 42, "FIXTURE-STATUS.md", size=12.5, color=C["ink"], font_style="italic")
    txt(x0 + 300, 30, 16, 42, "M", size=11, color=C["git_mod"], align="center", weight=700)
    txt(x0 + 320, 30, 18, 42, "✕", size=12, color=C["sub"], align="center")
    txt(W - 24, 30, 18, 42, "⋯", size=14, color=C["muted"], align="center")

    # breadcrumb
    file_icon(page, x0 + 16, 78, C["md_blue"], sw)
    txt(x0 + 34, 74, 200, 26, "FIXTURE-STATUS.md", size=13, color=C["sub"])

    # rendered markdown table (scrolled — first visible row is effects.fg.yaml)
    # (filename, errors, warnings, notes) — the real FIXTURE-STATUS.md rows.
    # Notes wrap on metrics; only the one long filename keeps a manual break,
    # since wrap_text would hard-break a space-less token mid-character.
    rows = [
        ("effects.fg.yaml", "0", "0", "clean"),
        ("group-layout.fg.yaml", "0", "0", "clean"),
        ("myfiles-internal.fg.yaml", "0", "19", "advisory warnings only (containment, overlap)"),
        ("nyt-mideast-live.fg.yaml", "0", "1", "advisory warnings only (tabular-box-model)"),
        ("pdf_table_extraction.fg.yaml", "0", "1", "advisory warnings only (out-of-profile)"),
        ("sdk-ergonomics-\nshowcase.fg.yaml", "0", "1", "advisory warnings only (out-of-profile)"),
        ("sdk-geometry-patterns.fg.yaml", "0", "0", "clean"),
        ("standard-model.fg.yaml", "0", "17", "advisory warnings only (out-of-profile)"),
        ("table-rows.fg.yaml", "0", "0", "clean"),
        ("tables.fg.yaml", "0", "0", "clean"),
        ("text-spans.fg.yaml", "0", "0", "clean"),
        ("topology-perspective.fg.yaml", "0", "0", "clean"),
        ("transform-scene.fg.yaml", "0", "0", "clean"),
        ("transforms-affine.fg.yaml", "0", "0", "clean"),
        ("transforms.fg.yaml", "0", "0", "clean"),
        ("wordle-how-to-play.fg.yaml", "0", "15", "advisory warnings only (overlap)"),
    ]
    name_x = x0 + 18
    n1_x, n2_x = x0 + 372, x0 + 470
    status_x = x0 + 508
    note_w = 240
    y = 112
    for name, n1, n2, note in rows:
        name_lines = name.split("\n")
        note_lines = wrap_text(note, width=note_w, font_family=SANS, font_size=13)
        rh = 34 if max(len(name_lines), len(note_lines)) == 1 else 56
        for i, ln in enumerate(name_lines):       # filename — markdown inline-code red mono
            mono(name_x, y + 4 + i * 22, 350, 22, ln, color=C["code_red"], size=13)
        txt(n1_x, y + 4, 40, 22, n1, size=13, color=C["ink"], valign="top")
        txt(n2_x, y + 4, 40, 22, n2, size=13, color=C["ink"], valign="top")
        for i, ln in enumerate(note_lines):
            txt(status_x, y + 4 + i * 22, 300, 22, ln, size=13, color=C["ink"], valign="top")
        page.line([x0 + 12, y + rh], [W - 14, y + rh], **sw(1, "#eeeeee"))
        y += rh

    # scrollbar thumb (table is scrolled — header row is above the viewport)
    box(W - 10, 210, 4, 380, fill="#c8c8c8", radius=2)


def terminal(page, C, sw, txt, mono, box, x0, x1, MONO):
    PT = 812      # panel top
    TAB_H = 34
    box(x0, PT, x1 - x0, 1120 - PT, fill=C["panel_bg"])
    page.line([x0, PT], [x1, PT], **sw(1, C["border_strong"]))

    tabs = [("PROBLEMS", x0 + 20), ("OUTPUT", x0 + 128), ("DEBUG CONSOLE", x0 + 210),
            ("TERMINAL", x0 + 350), ("PORTS", x0 + 452)]
    for label, tx in tabs:
        active = label == "TERMINAL"
        txt(tx, PT, 130, TAB_H, label, size=11.5,
            color=C["ink"] if active else C["muted"], weight=600,
            letter_spacing=0.3)
        if active:
            page.rect([tx, PT + TAB_H - 2, 70, 2], fill=C["accent"], decorative=True)
    # right-side panel controls
    for i, ic in enumerate(("+", "⌄", "⯆", "✕")):
        txt(x1 - 200 + i * 34, PT, 20, TAB_H, ic, size=12, color=C["icon"], align="center")

    # terminal text
    ty = PT + TAB_H + 14
    lh = 24
    px = x0 + 18

    def prompt(row_y, dot_filled):
        """Lay the colored zsh prompt segments left-to-right by measured advance."""
        if dot_filled:
            page.ellipse([px, row_y + 9], 3.5, 3.5, fill=C["term_blue"])
        else:
            page.ellipse([px, row_y + 9], 3.5, 3.5, fill="none", **sw(1.2, C["muted"]))
        cx = px + 12
        segs = [("→ ", C["term_green"], 400), ("frameforge ", C["term_green"], 700),
                ("git:(", C["term_blue"], 400), ("main", C["term_red"], 400),
                (")", C["term_blue"], 400), (" ✗ ", C["term_yellow"], 400)]
        for s, color, weight in segs:
            adv = measure_text(s, font_family=MONO, font_size=13, bold=weight >= 700)
            mono(cx, row_y, adv + 6, lh, s, color=color, size=13, weight=weight)
            cx += adv
        return cx

    # line 1 — prompt + command
    cx = prompt(ty, True)
    mono(cx, ty, 500, lh, "python3 tooling/gen_status.py", color=C["ink"], size=13)
    # line 2 — output
    mono(px, ty + lh, 1200, lh,
         "Wrote /home/admin/github-mirror/_framework/frameforge/FIXTURE-STATUS.md",
         color=C["ink"], size=13)
    # line 3 — fresh prompt with cursor
    ty3 = ty + 2 * lh
    cx = prompt(ty3, False)
    page.rect([cx + 2, ty3 + 3, 8, 16], fill=C["ink"], decorative=True)  # cursor

    # right-hand terminal tab list
    lx = x1 - 180
    page.line([lx, PT + TAB_H], [lx, 1120], **sw(1, C["border"]))
    box(lx, PT + TAB_H + 28, 180, 24, fill=C["sel_bg"])  # zsh selected
    txt(lx + 16, PT + TAB_H + 4, 120, 22, "node", size=12.5, color=C["sub"])
    txt(lx + 150, PT + TAB_H + 4, 16, 22, "⯆", size=11, color=C["muted"], align="center")
    txt(lx + 16, PT + TAB_H + 28, 120, 24, "zsh", size=12.5, color=C["ink"], weight=600)


def status_bar(page, C, txt, W, H):
    sy = H - 25
    page.rect([0, sy, W, 25], fill=C["status_bg"], decorative=True)
    # left cluster
    txt(8, sy, 24, 25, "〈»", size=12, color=C["white"], align="center")
    txt(28, sy, 170, 25, "SSH: 192.168.199.25", size=12, color=C["white"])
    txt(206, sy, 16, 25, "⎇", size=12, color=C["white"], align="center")
    txt(222, sy, 70, 25, "main*", size=12, color=C["white"])
    txt(280, sy, 16, 25, "↻", size=12, color=C["white"], align="center")
    txt(316, sy, 18, 25, "⊘", size=12, color=C["white"], align="center")
    txt(330, sy, 24, 25, "0", size=12, color=C["white"])
    txt(352, sy, 18, 25, "⚠", size=11, color=C["white"], align="center")
    txt(368, sy, 24, 25, "0", size=12, color=C["white"])
    txt(404, sy, 18, 25, "⏻", size=12, color=C["white"], align="center")
    txt(420, sy, 24, 25, "0", size=12, color=C["white"])
    # right cluster
    txt(W - 220, sy, 40, 25, "OVR", size=12, color=C["white"], align="center")
    txt(W - 170, sy, 18, 25, "⊘", size=12, color=C["white"], align="center")
    txt(W - 150, sy, 70, 25, "Sign In", size=12, color=C["white"])
    txt(W - 40, sy, 24, 25, "\U0001f514", size=12, color=C["white"], align="center")


def main() -> None:
    report = build().write(OUT, fail_on_error=False)
    if report is not None:
        errs = [i for i in report.issues if i.severity == "error"]
        warns = [i for i in report.issues if i.severity == "warning"]
        print(f"{OUT.relative_to(ROOT)}  ({len(errs)} error(s), {len(warns)} warning(s))")
        for i in errs[:10]:
            print("  ERROR", i.path, i.message)
    else:
        print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
