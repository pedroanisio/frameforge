#!/usr/bin/env python3
"""Recreate the Sublime Text (.ttl) desktop screenshot with the FrameGraph SDK.

Authors the whole frame out of core primitives (rect / text / line / ellipse /
polygon): the XFCE-style top panel, the Sublime window (title bar, menu bar, tab
strip, dark code editor with a line-number gutter, syntax-toned Turtle/RDF text,
current-line highlight, caret, and minimap), the status bar, and the bottom dock.
Lowers to a single absolute-coordinate page sized to the displayed screenshot
(2000x1250) so coordinates map straight from the image.

AI-generated (Claude Opus 4.8) screenshot recreation; coordinates are [APPROX].

    uv run python examples/sublime_ttl_screenshot.py
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder  # noqa: E402
from framegraph.sdk.io import serialize  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

OUT = ROOT / "examples" / "fixtures" / "sublime-ttl-screenshot.fg.yaml"
W, H = 2000, 1250

SANS = ["DejaVu Sans", "Arial", "sans-serif"]
MONO = ["DejaVu Sans Mono", "Fira Mono", "monospace"]

CO = {
    "panel": "#2f343f",
    "panel_text": "#cfd4de",
    "panel_dim": "#9aa0ac",
    "title_bg": "#d7dbe2",
    "ink": "#3b3f46",
    "menu_bg": "#d9dde3",
    "tabbar": "#3a3f49",
    "tab_inactive": "#33373f",
    "tab_hover": "#444a55",
    "tab_text": "#c6cad2",
    "tab_dim": "#9aa0ac",
    "editor": "#2b2f38",
    "gutter_num": "#6b7079",
    "gutter_active": "#cfd4de",
    "code": "#c5c8c6",
    "code_kw": "#9fb3c9",
    "code_str": "#b6c08a",
    "code_uri": "#86b9c4",
    "cur_line": "#343a45",
    "caret": "#e8e8e8",
    "status_bg": "#262a32",
    "status_text": "#9aa0ac",
    "minimap": "#343a45",
    "minimap_code": "#525a66",
    "dock": "#2b303b",
    "white": "#ffffff",
    "red": "#e0564b",
    "amber": "#f2b134",
    "green": "#5bb85b",
    "blue": "#4a78c8",
    "teal": "#1aa0a0",
    "violet": "#8e7cc3",
    "slate": "#5a626e",
}

TEXT = {
    "ui": dict(font_family=SANS, font_size=16, color="panel_text"),
    "ui_dim": dict(font_family=SANS, font_size=15, color="panel_dim"),
    "menu": dict(font_family=SANS, font_size=16, color="ink"),
    "title": dict(font_family=SANS, font_size=16, color="ink", align="center"),
    "tab": dict(font_family=SANS, font_size=15, color="tab_text"),
    "tab_dim": dict(font_family=SANS, font_size=15, color="tab_dim"),
    "mono": dict(font_family=MONO, font_size=15, color="code"),
    "uri": dict(font_family=MONO, font_size=15, color="code_uri"),
    "num": dict(font_family=MONO, font_size=15, color="gutter_num", align="right"),
    "num_on": dict(font_family=MONO, font_size=15, color="gutter_active", align="right"),
    "status": dict(font_family=MONO, font_size=14, color="status_text"),
    "icon": dict(font_family=SANS, font_size=18, color="white", align="center", v_align="middle"),
}

# --- editor content: (lineno|None, text). Continuation rows carry None. ------ #
B = "\\\""  # a literal backslash-quote as it appears in the screenshot
ROWS = [
    (548, 'cbm:language "go" ;'),
    (549, 'cbm:path "binding/protobuf.go" ;'),
    (550, 'cbm:sizeBytes 923 ;'),
    (551, 'cbm:type cbmt:source_code .'),
    (552, ''),
    (553, '<https://codebase-mapper.example.org/cbm/instance#file/binding%2Fquery.go> a cbm:File ;'),
    (554, f'cbm:astSummary "{{{B}imports{B}: [{{{B}kind{B}: {B}import{B}, {B}lineno{B}: 7, {B}source{B}: {B}net/http{B}}}], {B}language{B}: {B}go{B}, {B}top_level_classes{B}: [{B}queryBinding{B}], {B}top_level_functions{B}: [{B}Bind{B},'),
    (None, f'{B}Name{B}]}}" ;'),
    (555, 'cbm:contentSha256 "65e8a3f81069398c364049951aae37e0316598b0601967a4f44efaeced9e26be"^^xsd:hexBinary ;'),
    (556, 'cbm:gitBlobSha "c958b88bda02d59fdb59db94b5218c4013c77ac6" ;'),
    (557, 'cbm:hasPhase cbmp:runtime ;'),
    (558, 'cbm:language "go" ;'),
    (559, 'cbm:path "binding/query.go" ;'),
    (560, 'cbm:sizeBytes 460 ;'),
    (561, 'cbm:type cbmt:source_code .'),
    (562, ''),
    (563, '<https://codebase-mapper.example.org/cbm/instance#file/binding%2Ftoml.go> a cbm:File ;'),
    (564, f'cbm:astSummary "{{{B}imports{B}: [{{{B}kind{B}: {B}import{B}, {B}lineno{B}: 8, {B}source{B}: {B}bytes{B}}}, {{{B}kind{B}: {B}import{B}, {B}lineno{B}: 9, {B}source{B}: {B}io{B}}}, {{{B}kind{B}: {B}import{B}, {B}lineno{B}: 10, {B}source{B}:'),
    (None, f'{B}net/http{B}}}, {{{B}kind{B}: {B}import{B}, {B}lineno{B}: 12, {B}source{B}: {B}github.com/pelletier/go-toml/v2{B}}}], {B}language{B}: {B}go{B}, {B}top_level_classes{B}: [{B}tomlBinding{B}], {B}top_level_functions{B}: [{B}Bind{B},'),
    (None, f'{B}BindBody{B}, {B}Name{B}, {B}decodeToml{B}]}}" ;'),
    (565, 'cbm:contentSha256 "ce9f395d0c2d62da942cc9f9a8a576cb81b4cacc9934fa6f3d3f19881a82790"^^xsd:hexBinary ;'),
    (566, 'cbm:gitBlobSha "2681231d9d7ba3e649b2596e2ad00398b89e2348" ;'),
    (567, 'cbm:hasPhase cbmp:runtime ;'),
    (568, 'cbm:language "go" ;'),
    (569, 'cbm:path "binding/toml.go" ;'),
    (570, 'cbm:sizeBytes 698 ;'),
    (571, 'cbm:type cbmt:source_code .'),
    (572, ''),
    (573, '<https://codebase-mapper.example.org/cbm/instance#file/binding%2Ftoml_test.go> a cbm:File ;'),
    (574, f'cbm:astSummary "{{{B}imports{B}: [{{{B}kind{B}: {B}import{B}, {B}lineno{B}: 8, {B}source{B}: {B}testing{B}}}, {{{B}kind{B}: {B}import{B}, {B}lineno{B}: 10, {B}source{B}: {B}github.com/stretchr/testify/assert{B}}}, {{{B}kind{B}:'),
    (None, f'{B}import{B}, {B}lineno{B}: 11, {B}source{B}: {B}github.com/stretchr/testify/require{B}}}], {B}language{B}: {B}go{B}, {B}top_level_classes{B}: [], {B}top_level_functions{B}: [{B}TestTOMLBindingBindBody{B}]}}" ;'),
    (575, 'cbm:contentSha256 "f3bd4fbc65f0fc675acab2728ed633260526c60f5f366a8af36d5e4951123fd7"^^xsd:hexBinary ;'),
    (576, 'cbm:gitBlobSha "2bc0e3a47e2214a2ac0cd4904a1340b2edbf5e08" ;'),
    (577, 'cbm:hasPhase cbmp:runtime ;'),
    (578, 'cbm:importsExternal <https://codebase-mapper.example.org/cbm/instance#pkg/github.com%2Fstretchr%2Ftestify> ;'),
    (579, 'cbm:language "go" ;'),
    (580, 'cbm:path "binding/toml_test.go" ;'),
    (581, 'cbm:sizeBytes 503 ;'),
    (582, 'cbm:type cbmt:source_code .'),
    (583, ''),
    (584, '<https://codebase-mapper.example.org/cbm/instance#file/binding%2Furi.go> a cbm:File ;'),
    (585, f'cbm:astSummary "{{{B}imports{B}: [], {B}language{B}: {B}go{B}, {B}top_level_classes{B}: [{B}uriBinding{B}], {B}top_level_functions{B}: [{B}BindUri{B}, {B}Name{B}]}}" ;'),
    (586, 'cbm:contentSha256 "ef9e498347257b91f2679af03c3b07a09794e2cff7d02e16475b9e6939daf87c"^^xsd:hexBinary ;'),
    (587, 'cbm:gitBlobSha "29151064a985455f42c219ab1e933571cc8d8cc8" ;'),
    (588, 'cbm:hasPhase cbmp:runtime ;'),
    (589, 'cbm:language "go" ;'),
    (590, 'cbm:path "binding/uri.go" ;'),
    (591, 'cbm:sizeBytes 399 ;'),
    (592, 'cbm:type cbmt:source_code .'),
    (593, ''),
    (594, '<https://codebase-mapper.example.org/cbm/instance#file/binding%2Fvalidate_test.go> a cbm:File ;'),
    (595, f'cbm:astSummary "{{{B}imports{B}: [{{{B}kind{B}: {B}import{B}, {B}lineno{B}: 8, {B}source{B}: {B}bytes{B}}}, {{{B}kind{B}: {B}import{B}, {B}lineno{B}: 9, {B}source{B}: {B}testing{B}}}, {{{B}kind{B}: {B}import{B}, {B}lineno{B}: 10,'),
    (None, f'{B}source{B}: {B}time{B}}}, {{{B}kind{B}: {B}import{B}, {B}lineno{B}: 12, {B}source{B}: {B}github.com/go-playground/validator/v10{B}}}, {{{B}kind{B}: {B}import{B}, {B}lineno{B}: 13, {B}source{B}: {B}github.com/stretchr/testify/'),
    (None, f'assert{B}}}, {{{B}kind{B}: {B}import{B}, {B}lineno{B}: 14, {B}source{B}: {B}github.com/stretchr/testify/require{B}}}], {B}language{B}: {B}go{B}, {B}top_level_classes{B}: [{B}Object{B}, {B}mapNoValidationSub{B},'),
    (None, f'{B}structCustomValidation{B}, {B}structModifyValidation{B}, {B}structNoValidationPointer{B}, {B}structNoValidationValues{B}, {B}substructNoValidation{B}, {B}testInterface{B}], {B}top_level_functions{B}:'),
    (None, f'[{B}TestValidateAndModifyStruct{B}, {B}TestValidateNoValidationPointers{B}, {B}TestValidateNoValidationValues{B}, {B}TestValidatePrimitives{B}, {B}TestValidatorEngine{B}, {B}createNoValidationValues{B}, {B}notOne{B},'),
    (None, f'{B}toZero{B}]}}" ;'),
    (596, 'cbm:contentSha256 "e0120c977f4e49cdaf8b5945dcaa7de1b2571aa029d133d87ab301c22fd76e4"^^xsd:hexBinary ;'),
]

MENU = ["File", "Edit", "Selection", "Find", "View", "Goto", "Tools", "Project", "Preferences", "Help"]
# (label, width, state) state: "active" | "hover" | "plain"
TABS = [
    ("/adv-planning to implement {FC-CSR} following all", 250, "plain"),
    ("Here are 5 distinct logo styles derived from the N", 292, "plain"),
    ("traveling on the go", 150, "hover"),
    ("---", 70, "plain"),
    ("pse-genai-discovery-v3.md", 208, "plain"),
    ("10. No cross-field coherence checks", 268, "plain"),
    ("gin__inventory.ttl", 172, "active"),
    ("untitled", 112, "plain"),
    ("vscode.yml", 120, "plain"),
    ("ninja.yml", 110, "plain"),
]
DOCK = [
    ("blue", "search"), ("teal", "tiles"), ("amber", "apps"), ("teal", "files"),
    ("ink", "term"), ("teal", "get"), ("blue", "code"), ("green", "web"),
    ("amber", "subl"), ("slate", "set"),
]

ED_TOP, ED_BOT = 127, 1163
LINE_H = 16.6
GUTTER_W, CODE_X = 60, 74
MAP_X = 1900


def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="Sublime Text TTL screenshot", profile="diagram", lang="en")
    for name, value in CO.items():
        doc.define_color(name, value)
    for name, style in TEXT.items():
        doc.define_text_style(name, **style)
    page = doc.page("desktop", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute").layer("ui")

    page.rect([0, 0, W, H], fill="editor")
    _editor(page)
    _top_panel(page)
    _title_bar(page)
    _menu_bar(page)
    _tab_strip(page)
    _status_bar(page)
    _dock(page)
    return doc


def _t(page, box, value, style):
    page.text(box, value, style=style)


def _editor(page):
    page.rect([0, ED_TOP, W, ED_BOT - ED_TOP], fill="editor")
    cur_y = None
    for i, (num, _text) in enumerate(ROWS):
        y = ED_TOP + 6 + i * LINE_H
        if num == 589:
            cur_y = y
    if cur_y is not None:
        page.rect([GUTTER_W, cur_y - 2, MAP_X - GUTTER_W, LINE_H], fill="cur_line")

    for i, (num, text) in enumerate(ROWS):
        y = ED_TOP + 6 + i * LINE_H
        if num is not None:
            _t(page, [0, y, GUTTER_W - 12, LINE_H], str(num), "num_on" if num == 589 else "num")
        if text:
            style = "uri" if text.startswith("<http") else "mono"
            page.text([CODE_X, y, MAP_X - CODE_X - 6, LINE_H], text, style=style)
        if num == 589:
            cx = CODE_X + len("cbm:language \"go\" ;") * 9.05 + 6
            page.line([cx, y + 1], [cx, y + LINE_H - 2], stroke="caret", stroke_style={"stroke_width": 2})

    # minimap
    page.rect([MAP_X, ED_TOP, W - MAP_X, ED_BOT - ED_TOP], fill="editor")
    for i, (num, text) in enumerate(ROWS):
        if not text:
            continue
        my = ED_TOP + 8 + i * 6.4
        ln = min(94, 8 + len(text) * 0.42)
        page.rect([MAP_X + 4, my, ln, 2.4], fill="minimap_code")
    page.rect([MAP_X, ED_TOP + 250, W - MAP_X, 150], fill="minimap", opacity=0.5)


def _top_panel(page):
    page.rect([0, 0, W, 30], fill="panel")
    _t(page, [14, 5, 120, 22], "Workspaces", "ui")
    _t(page, [120, 5, 130, 22], "Applications", "ui")
    page.rect([238, 9, 13, 13], fill="panel_dim", radius=2)
    _t(page, [W / 2 - 120, 5, 240, 22], "Jun 23, 14:00", "ui")
    _t(page, [1560, 5, 170, 22], "us (intl-unicode)", "ui_dim")
    gx = 1748
    for col in ("blue", "panel_text", "panel_text", "panel_text", "panel_text", "panel_dim", "red"):
        page.ellipse([gx, 15], 8, 8, fill=col)
        gx += 36


def _title_bar(page):
    page.rect([0, 30, W, 33], fill="title_bg")
    _t(page, [W / 2 - 420, 38, 840, 22], "~/Downloads/gin__inventory.ttl - Sublime Text (UNREGISTERED)", "title")
    for i, glyph in enumerate(("—", "□", "✕")):
        page.text([1892 + i * 36, 36, 26, 24], glyph, style={"font_family": SANS, "font_size": 17, "color": "ink", "align": "center"})


def _menu_bar(page):
    page.rect([0, 63, W, 30], fill="menu_bg")
    x = 14
    for label in MENU:
        _t(page, [x, 68, len(label) * 9 + 24, 22], label, "menu")
        x += len(label) * 9 + 26


def _tab_strip(page):
    page.rect([0, 93, W, 34], fill="tabbar")
    x = 0
    for label, w, state in TABS:
        fill = {"active": "editor", "hover": "tab_hover", "plain": "tab_inactive"}[state]
        page.rect([x + 1, 95, w - 2, 32], fill=fill)
        page.line([x + w, 97, ], [x + w, 123], stroke="panel", stroke_style={"stroke_width": 1, "opacity": 0.5})
        max_chars = int((w - 40) / 8.2)
        shown = label if len(label) <= max_chars else label[: max_chars - 1] + "…"
        _t(page, [x + 14, 100, w - 36, 22], shown, "tab" if state == "active" else "tab_dim")
        page.text([x + w - 22, 100, 16, 22], "✕", style={"font_family": SANS, "font_size": 13, "color": "tab_dim", "align": "center"})
        if state == "active":
            page.rect([x + 1, 95, w - 2, 2], fill="amber")
        x += w
    page.text([x + 12, 100, 22, 22], "+", style={"font_family": SANS, "font_size": 17, "color": "tab_dim", "align": "center"})


def _status_bar(page):
    page.rect([0, ED_BOT, W, 24], fill="status_bg")
    _t(page, [14, ED_BOT + 4, 320, 18], "Line 589, Column 24", "status")
    _t(page, [1790, ED_BOT + 4, 110, 18], "Spaces: 4", "status")
    _t(page, [1906, ED_BOT + 4, 90, 18], "Plain Text", "status")


def _dock(page):
    n = len(DOCK)
    size, gap = 52, 18
    total = n * size + (n - 1) * gap
    x0 = (W - total) / 2
    y = 1196
    page.rect([x0 - 22, y - 8, total + 44, size + 16], fill="dock", radius=14, opacity=0.92)
    for i, (col, glyph) in enumerate(DOCK):
        x = x0 + i * (size + gap)
        page.rect([x, y, size, size], fill=col, radius=12)
        mark = {"search": "⌕", "tiles": "▦", "apps": "⋮⋮", "files": "▰",
                "term": ">_", "get": "⤓", "code": "</>", "web": "●", "subl": "S", "set": "⚙"}[glyph]
        page.text([x, y + size / 2 - 12, size, 24], mark, style="icon")


def main() -> int:
    doc = build()
    document = doc.build()
    report = validate_static_rules(document)
    errors = [i for i in report.issues if i.severity == "error"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(serialize(document, format="yaml"), encoding="utf-8")
    print(f"Wrote {OUT} - ok={report.ok} errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for issue in report.issues[:20]:
        print(f"  [{issue.severity}] [{issue.rule_id}] {issue.path}: {issue.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
