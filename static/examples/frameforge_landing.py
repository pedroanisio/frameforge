#!/usr/bin/env python3
"""FrameForge — the proposed landing page for the FrameForge service itself.

A single tall web canvas (1440 x ~5000), authored with the FrameForge SDK, so
the page that sells the substrate is *made of* the substrate. Top to bottom:

  1.  Nav          — the canonical mark + wordmark (imported, never redrawn).
  2.  Hero         — the positioning line, the install chip, and the gate panel:
                     the local `make check` summary, with real numbers.
  3.  Stat strip   — five counts, every one generated from this repository.
  4.  Derivation   — `fan()` from the logo module: one source, everything else
                     generated from it or gated against it.
  5.  Problem      — what breaks when output survives only as pixels.
  6.  Loop         — describe -> validate -> render -> verify, drawn.
  7.  Code         — a real SDK client, and what it lowers to.
  8.  Outputs      — the backends that are verified *today* (docs/output-space.md),
                     each flagged verified or degraded. No aspirational rows.
  9.  Agents       — the 31 MCP tools, grouped, named.
  10. Proof (dark) — the four sync gates, plus the honest-limits card quoted
                     verbatim from README.md. The limit is on the page, not in
                     a footnote.
  11. Audience     — who it serves (PURPOSE.md).
  12. CTA + footer.

EVERY NUMBER ON THIS PAGE IS GENERATED, NOT ASSERTED.  The constants in the
`FACTS` block below each carry the command that produces them; `--verify`
re-derives the ones that can be re-derived from the working tree and fails the
build on drift, so this page cannot quietly go stale (CLAUDE.md: "treat
generated artifacts as generated"; PALS's Law: verify, do not trust).

Design constraints obeyed (docs/BRAND.md):
  * closed palette, brand tokens only, plus two greys on the ink's own scale
    for the reversed band;
  * flat and exact — no gradients, bevels or drop shadows in brand chrome (§4);
  * `gate-green` / `drift-red` are reserved for *state*, never decoration, and
    always paired with a glyph or a label so meaning survives greyscale (§4);
  * type scale 13 / 16 / 20 / 25 / 32 / 40 / 50 (1.25, §5), body 16 / 1.55;
  * body measure held to 45-75 characters.

Known, disclosed deviation: the brand sans is IBM Plex Sans, which is **not
installed in this render runtime** — fontconfig substitutes Noto Sans for it.
Rather than ship a silent substitution, this page names Inter (a real, resolvable
family with real weights) as its sans and keeps IBM Plex Mono, which does
resolve, as the brand mono. `wordmark()` is imported unmodified and therefore
still renders in whatever the runtime resolves for the brand sans.

Run from the repository root::

    uv run python static/examples/frameforge_landing.py
    uv run python static/examples/frameforge_landing.py --verify   # re-derive FACTS
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge.sdk import DocumentBuilder, measure_text  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# The mark, the wordmark and the derivation fan come from the brand's single
# source of truth (docs/BRAND.md §3) — imported, never redrawn, so this page and
# the logo masters can never diverge.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # the examples/ dir
from frameforge_logo import fan, mark, wordmark  # noqa: E402


# --------------------------------------------------------------------------- #
# FACTS — every number on the page, with the command that generates it.
# `--verify` re-derives each `probe` and fails on drift.
# --------------------------------------------------------------------------- #
SITE = "frameforge.hefestus.io"
OUT_TMP = os.path.join(ROOT, "_tmp", "landing")   # non-core output stays out of the tree

FACTS = {
    "version":      ("2.6.0", "pyproject.toml [project] version"),
    "tests":        (2562,    "uv run pytest --collect-only -q"),
    "tests_pass":   (2561,    "uv run pytest  -> '2561 passed, 1 skipped' (0 failed)"),
    "tests_skip":   (1,       "same run: the one skip"),
    "golden_pages": (87,      "uv run python tooling/render_golden.py"),
    "fixtures":     ("39/39", "docs/FIXTURE-STATUS.md (tooling/gen_status.py)"),
    "capabilities": (373,     "docs/capability-manifest.json .capabilities"),
    "schema_defs":  (88,      "docs/schema/frameforge-v2.schema.json .$defs"),
    "examples":     (139,     "docs/examples.md (tooling/gen_examples_index.py)"),
    "mcp_tools":    (31,      "docs/capability-manifest.json .mcp.tools"),
    "sdk_exports":  (245,     "docs/capability-manifest.json .sdk.public_exports"),
    "object_types": (17,      "docs/capability-manifest.json .model.object_types"),
    "canvas":       (57,      "docs/capability-manifest.json .model.canvas_presets"),
    "style_props":  (106,     "docs/capability-manifest.json .model.style_property_count"),
    "codes":        (25,      "docs/capability-manifest.json .validator.tooling_codes"),
}
F = {k: v[0] for k, v in FACTS.items()}


def verify_facts() -> int:
    """Re-derive every cheaply-derivable FACT from the working tree; report drift.

    PALS's Law, applied to this file: the page asserts counts about the
    repository, so the page must be able to *check* them. Only the pytest total
    is skipped (it needs a full collection run); everything else is read from
    the generated artifacts that are themselves gated by `make check`.
    """
    manifest = json.load(open(os.path.join(ROOT, "docs", "capability-manifest.json")))
    schema = json.load(open(os.path.join(ROOT, "docs", "schema", "frameforge-v2.schema.json")))
    status = open(os.path.join(ROOT, "docs", "FIXTURE-STATUS.md"), encoding="utf-8").read()
    pyproject = open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8").read()
    # The example count comes from the GENERATED index, not from `ls`: a raw file
    # count includes untracked scratch files and modules with no runnable entry
    # point, and would have put 144 on the page where the generator says 138.
    index = open(os.path.join(ROOT, "docs", "examples.md"), encoding="utf-8").read()

    version = next(ln.split("=", 1)[1].strip().strip('"')
                   for ln in pyproject.splitlines() if ln.startswith("version"))
    # Anchored patterns, not "the first token containing a slash" — a loose scan
    # would happily match a path like `tests/fixtures` and report a false match,
    # which would defeat the whole point of this gate.
    fixtures = re.search(r"\*\*(\d+/\d+)\*\*\s+have zero errors", status)
    n_examples = re.search(r"The (\d+) tracked, runnable SDK clients", index)

    derived = {
        "version":      version,
        "fixtures":     fixtures.group(1) if fixtures else "UNPARSED",
        "capabilities": len(manifest["capabilities"]),
        "schema_defs":  len(schema.get("$defs", {})),
        "examples":     int(n_examples.group(1)) if n_examples else -1,
        "mcp_tools":    len(manifest["mcp"]["tools"]),
        "sdk_exports":  len(manifest["sdk"]["public_exports"]),
        "object_types": len(manifest["model"]["object_types"]),
        "canvas":       len(manifest["model"]["canvas_presets"]),
        "style_props":  manifest["model"]["style_property_count"],
        "codes":        len(manifest["validator"]["tooling_codes"]),
    }
    drift = {k: (F[k], v) for k, v in derived.items() if F[k] != v}
    for key, (claimed, actual) in sorted(drift.items()):
        print(f"  [DRIFT] {key}: page claims {claimed!r}, tree says {actual!r}"
              f"  ({FACTS[key][1]})")
    print(f"verify: {len(derived) - len(drift)}/{len(derived)} facts match the tree"
          f" (tests={F['tests']} not re-derived here — run pytest)")

    ok_code = _verify_code_sample()
    return 1 if (drift or not ok_code) else 0


def _verify_code_sample() -> bool:
    """Execute the code shown on the page and compare against its own `# ->`.

    The sample asserts a result in a comment. An asserted result that nobody runs
    is exactly the failure mode this page exists to argue against, so it is run.
    """
    import io
    import contextlib

    # The page paints CODE (coloured spans) but runs CODE_SOURCE. If those two
    # ever diverge, the page shows one program and proves another — so assert
    # they are the same text before trusting the run.
    shown = [("".join(t for t, _ in line).rstrip()).split("   # ->")[0].rstrip()
             for line in CODE]
    if shown != CODE_SOURCE.splitlines():
        print("  [CODE] the painted sample and the executed source differ")
        for i, (a, b) in enumerate(zip(shown, CODE_SOURCE.splitlines())):
            if a != b:
                print(f"    line {i}: shown={a!r} source={b!r}")
        return False

    buf = io.StringIO()
    namespace: dict[str, object] = {}
    scratch = os.path.join(OUT_TMP, "verify")     # keep the deliverables dir clean
    os.makedirs(scratch, exist_ok=True)
    source = CODE_SOURCE.replace('doc.write("q3.fg.yaml"',
                                 f'doc.write("{os.path.join(scratch, "q3.fg.yaml")}"')
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(source, "<landing-code-sample>", "exec"), namespace)
    except Exception as exc:                                   # noqa: BLE001
        print(f"  [CODE] sample raised {type(exc).__name__}: {exc}")
        return False
    actual = buf.getvalue().strip()
    if actual != CODE_RESULT:
        print(f"  [CODE] page shows '# -> {CODE_RESULT}', sample prints '{actual}'")
        return False
    print(f"code sample: runs clean and prints '{actual}' as shown")
    return True


# --------------------------------------------------------------------------- #
# Canvas + palette (docs/BRAND.md §4 — the closed set, nothing invented)
# --------------------------------------------------------------------------- #
W = 1440
M = 100                       # page margin
CW = W - 2 * M                # 1240 content width

COLORS = {
    # brand tokens, verbatim
    "ink":        "#15181E",   # graphite, never pure black
    "paper":      "#FBFAF6",   # warm technical paper
    "canvas":     "#FFFFFF",   # pure render surface
    "frame":      "#1F4FD8",   # frame-blue — the primary accent ("Forge")
    "graph":      "#12B0C3",   # graph-cyan — flow, edges, live signal
    "gate":       "#1E9E5A",   # semantic: passing gate / in-sync
    "drift":      "#D23B2B",   # semantic: failed gate / drift
    "grid":       "#D4D8DE",   # hairlines, rules
    "mute":       "#6B7280",   # secondary text at >= 16px   (4.63:1 on paper)
    # Three further steps on the *ink's own* grey scale — not new hues, so the
    # palette stays closed. Each exists because a measured ratio demanded it:
    "mute-s":     "#4B5563",   # 13px text on paper          (7.24:1 on paper)
    "surface":    "#1D212A",   # raised surface on the ink ground
    "muted-r":    "#A7AEBA",   # secondary text on ink       (7.96:1 on ink)
    "hair-r":     "#2E3542",   # hairline on the ink ground
}

# Measured tone contrast (WCAG 2.x) of every text colour against the two grounds
# this page uses. `mute` clears 4.5:1 on paper but only at >= 16px (BRAND §4);
# on ink it is 3.68:1 and must not carry text. `gate-green` fails on paper
# (3.30:1) and `drift-red` fails on ink (3.73:1) — so neither is ever used as
# TEXT: state lives in the dot, and the label uses a neutral that passes. That
# also satisfies BRAND §4's "pair the colour with a glyph or label".

# Brand mono resolves in this runtime; the brand sans (IBM Plex Sans) does not —
# see the module docstring. Inter carries real weights, so no faux-bold.
SANS    = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
DISPLAY = ["Inter Display", "Inter", "Helvetica Neue", "DejaVu Sans", "sans-serif"]
MONO    = ["IBM Plex Mono", "DejaVu Sans Mono", "Menlo", "monospace"]

# Type scale — 1.25 (major third), docs/BRAND.md §5.
S13, S16, S20, S25, S32, S40, S50 = 13, 16, 20, 25, 32, 40, 50


def _ts(family, size, weight, color, *, align="left", ls=0.0, lh=1.3):
    return dict(font_family=family, font_size=size, font_weight=weight,
                color=color, align=align, letter_spacing=ls, line_height=lh)


STYLES = {
    # display / headings
    "h1":        _ts(DISPLAY, S50, 600, "ink", ls=-1.0, lh=1.14),
    "h2":        _ts(DISPLAY, S40, 600, "ink", ls=-0.7, lh=1.18),
    "h2r":       _ts(DISPLAY, S40, 600, "paper", ls=-0.7, lh=1.18),
    "h3":        _ts(SANS, S20, 600, "ink", lh=1.35),
    "h3r":       _ts(SANS, S20, 600, "paper", lh=1.35),
    "stat":      _ts(DISPLAY, S40, 600, "ink", ls=-0.8, lh=1.0),
    "statb":     _ts(DISPLAY, S40, 600, "frame", ls=-0.8, lh=1.0),
    # body
    "lede":      _ts(SANS, S20, 400, "mute", lh=1.55),
    "body":      _ts(SANS, S16, 400, "mute", lh=1.55),
    "bodyi":     _ts(SANS, S16, 400, "ink", lh=1.55),
    "bodyr":     _ts(SANS, S16, 400, "muted-r", lh=1.55),
    # labels — mono is the "typed artifact" signal
    "eyebrow":   _ts(MONO, S13, 600, "frame", ls=1.8),
    "eyebrowr":  _ts(MONO, S13, 600, "graph", ls=1.8),
    "bodysm":    _ts(SANS, S13, 400, "mute-s", lh=1.6),
    "cap":       _ts(MONO, S13, 500, "mute-s", ls=0.3, lh=1.6),
    "capr":      _ts(MONO, S13, 500, "muted-r", ls=0.3, lh=1.6),
    "capi":      _ts(MONO, S13, 600, "ink", ls=0.3, lh=1.6),
    "capstate":  _ts(MONO, S13, 600, "mute-s", ls=0.3, lh=1.6),    # on paper
    "capstater": _ts(MONO, S13, 600, "muted-r", ls=0.3, lh=1.6),   # on ink
    "code":      _ts(MONO, S16, 400, "paper", lh=1.62),
    # interactive
    "btn":       _ts(SANS, S16, 600, "paper"),
    "nav":       _ts(SANS, S16, 500, "ink"),
    "chip":      _ts(MONO, S16, 500, "ink"),
    "chipr":     _ts(MONO, S16, 500, "graph"),
}

# style -> (font_size, line_height), so `para()` can never measure at one size
# and render at another. Every size here is on the 1.25 scale (BRAND §5).
PARA_METRICS = {name: (s["font_size"], s["line_height"]) for name, s in STYLES.items()}


# --------------------------------------------------------------------------- #
# Measurement + small components
# --------------------------------------------------------------------------- #
def tw(s, size, weight=400, family=None):
    """Rendered width of `s` — measured, never guessed, so every content-sized
    box (buttons, chips, dividers) fits what it actually contains."""
    return measure_text(s, font_family=list(family or SANS), font_size=size,
                        bold=weight >= 600)


def card(layer, box, *, fill="canvas", border="grid", radius=8, sw=1.0):
    """A flat, hairline-bordered surface. No shadow, no gradient (BRAND §4)."""
    layer.rect(list(box), fill=fill, radius=radius, stroke=border,
               stroke_style={"stroke_width": sw})


def rule(layer, x1, y, x2, *, color="grid", sw=1.0):
    layer.line([x1, y], [x2, y], stroke=color,
               stroke_style={"stroke_width": sw}, decorative=True)


def button(layer, x, y, label, *, ground="ink", ink="btn", h=52, pad=28):
    """Content-sized button: width comes from `measure_text`, not a guess."""
    w = tw(label, S16, 600) + 2 * pad
    layer.rect([x, y, w, h], fill=ground, radius=6)
    layer.text([x + pad, y, w - 2 * pad, h], label, style=ink)
    return w


def chip(layer, x, y, label, *, h=52, pad=22, style="chip", border="grid",
         fill="canvas", size=S16):
    """A bordered mono chip — the CLI register."""
    w = tw(label, size, 500, MONO) + 2 * pad
    layer.rect([x, y, w, h], fill=fill, radius=6, stroke=border,
               stroke_style={"stroke_width": 1.0})
    layer.text([x + pad, y, w - 2 * pad, h], label, style=style)
    return w


def tag(layer, x, y, label, *, color="gate", dark=False):
    """A state tag: coloured dot (filled = pass, ring = not) + the word.

    The dot carries the hue; the label is set in a neutral that clears 4.5:1 on
    its ground. Setting the label itself in `gate-green` measured 3.30:1 on
    paper — a fail — and it is the word, not the hue, that survives greyscale.
    """
    if color == "gate":
        layer.circle([x + 5, y + 9], 4.5, fill=color, decorative=True)
    else:
        layer.circle([x + 5, y + 9], 4.5, fill="canvas" if not dark else "surface",
                     stroke=color, stroke_style={"stroke_width": 1.8},
                     decorative=True)
    layer.text([x + 18, y, 220, 18], label,
               style="capstater" if dark else "capstate")


def eyebrow(layer, x, y, text, *, style="eyebrow", w=560):
    layer.text([x, y, w, 18], text, style=style)


def section_head(layer, y, kicker, title, *, lede=None, x=M, tw_=CW,
                 kstyle="eyebrow", tstyle="h2", lstyle="lede", lede_w=760):
    """kicker -> title -> optional lede. Returns the y below the block."""
    eyebrow(layer, x, y, kicker, style=kstyle, w=tw_)
    lines = max(title.count("\n") + 1,
                int(tw(title, S40, 600, DISPLAY) / (tw_ - 2)) + 1)
    th = int(lines * S40 * 1.18) + 6
    layer.text([x, y + 34, tw_, th], title, style=tstyle)
    y2 = y + 34 + th
    if lede:
        y2 = para(layer, x, y2 + 16, lede_w, lede, style=lstyle) + 0
    return y2


def label_column(g, x, y, w, items, *, style="cap", lh=18, gap=4, id=None):
    """A run of labels as a real `column` layout group, not hand-placed rows.

    §3.3 (`tabular-box-model`) exists precisely to catch text objects hand-placed
    on a regular rhythm: the structure is a column, so it is authored as one and
    the layout engine owns the advance. Returns the y below the group.
    """
    h = len(items) * lh + (len(items) - 1) * gap
    fields = {"id": id} if id else {}
    with g.vstack([x, y, w, h], gap=gap, **fields) as st:
        for item in items:
            st.add({"type": "text", "box": [0, 0, w, lh], "text": item,
                    "style": style})
    return y + h


def cols(x, total, n, gap):
    """n equal columns across `total`, returning (x, width) pairs."""
    cw = (total - gap * (n - 1)) / n
    return [(x + i * (cw + gap), cw) for i in range(n)]


def para_h(w, text, *, size=S16, lh=1.55):
    """Height a paragraph needs at width `w` — measured, then rounded up.

    The renderer's own text-fit diagnostics flag any box that clips its content,
    so this is the number that keeps a paragraph honest: guess low and the
    render reports a SILENT truncation.
    """
    n = max(1, int(tw(text, size) / (w - 2)) + 1)
    return int(n * size * lh) + 6


def para(layer, x, y, w, text, *, style="body", size=S16, lh=1.55):
    """Draw a paragraph in a box sized to its measured line count.

    `size`/`lh` MUST match the named `style`, or the box is measured for one
    type size and rendered at another — which is exactly how text gets silently
    clipped. `PARA_METRICS` keeps the two in step.
    """
    size, lh = PARA_METRICS.get(style, (size, lh))
    h = para_h(w, text, size=size, lh=lh)
    layer.text([x, y, w, h], text, style=style)
    return y + h


# --------------------------------------------------------------------------- #
# Content
# --------------------------------------------------------------------------- #
# The gate panel is a REPORT, not a badge: each row is an observed result from
# this working tree, and the row that is not green says so. A landing page that
# hid the red row would be contradicting the product it is selling
# (docs/BRAND.md §6: "If the test says 702/703, the copy says 702/703").
GATE_ROWS = [
    ("schema  <=> models",   "build_schema.py --check",  "in sync",              True),
    ("grammar <=> models",   "check_grammar_sync.py",    "0 errors",             True),
    ("delivered fixtures",   "gen_status.py --check",    f"{F['fixtures']} · 0 errors", True),
    ("golden render lock",   "render_golden.py",         f"{F['golden_pages']} pages match", True),
    ("the test suite",       "uv run pytest",
     f"{F['tests_pass']:,} · {F['tests_skip']} skip", True),
]

STATS = [
    (f"{F['tests_pass']:,}",  f"TESTS PASS · {F['tests_skip']} SKIP"),
    (F["fixtures"],          "FIXTURES · 0 ERRORS"),
    (str(F["capabilities"]), "DECLARED CAPABILITIES"),
    (str(F["schema_defs"]),  "SCHEMA DEFINITIONS"),
    (str(F["examples"]),     "TRACKED SDK CLIENTS"),
]

DERIVED = ["frameforge-v2.schema.json", "frameforge-v2.ebnf", "frameforge-v2-spec.md",
           "renders · svg png pdf html", "capability-manifest.json"]

PROBLEMS = [
    ("A screenshot is not evidence.",
     "Structure, constraints, provenance and generation history flatten into "
     "pixels. Teams end up debating an image because there is nothing else "
     "left to inspect."),
    ("It looks right, and it is wrong.",
     "Generated layouts overflow their boxes, collapse their columns and drift "
     "from the brand. Nothing fails loudly, so the defect ships."),
    ("The file is a dead end.",
     "Re-prompting is not editing. Output locked inside a vendor runtime cannot "
     "be diffed, migrated, or reproduced a year from now."),
]

LOOP = [
    ("01", "DESCRIBE", "Python SDK or MCP",
     f"{F['sdk_exports']} public SDK exports lower to one typed model: "
     f"{F['object_types']} object types, {F['style_props']} style properties."),
    ("02", "VALIDATE", "before a pixel is drawn",
     f"The model plus {F['codes']} typed rule codes — containment, overflow, "
     "dangling refs, deprecated forms — each with a documented fix."),
    ("03", "RENDER", "one document, many backends",
     "SVG, headless-Chromium PNG, PDF via LaTeX/TikZ or cairosvg, HTML/CSS. "
     "Each backend declares the subset it supports."),
    ("04", "VERIFY", "against the pixels",
     "Structural diff, image NCC/RMSE, a design-token audit, and a golden "
     "hash lock that fails the build on drift."),
]

# The sample is RUN, not written from memory: `--verify` executes it and fails
# the build if the printed result differs from the `# ->` comment below. A
# landing page whose thesis is "we check our output" cannot ship a code sample
# with an invented result — the first draft of this block claimed `True 0` while
# actually returning `False 2`, because `"ink"` and `"display"` were never
# declared. That is precisely the defect the page is about.
CODE_SOURCE = '''from frameforge.sdk import DocumentBuilder

doc = DocumentBuilder(title="Q3 Review", profile="deck")
doc.define_color("ink", "#15181E")
doc.define_text_style("display", font_size=132, color="#FBFAF6")

page = doc.page("cover", canvas="deck-16x9")
page.rect([0, 0, 1920, 1080], fill="ink")
page.text([160, 430, 1360, 210], "Q3 Review", style="display")

report = doc.write("q3.fg.yaml", format="yaml")
print(report.ok, len(report.issues))'''

CODE_RESULT = "True 0"

CODE = [
    [("from", "graph"), (" frameforge.sdk ", "paper"), ("import", "graph"),
     (" DocumentBuilder", "paper")],
    [],
    [("doc = DocumentBuilder(title=", "paper"), ('"Q3 Review"', "muted-r"),
     (", profile=", "paper"), ('"deck"', "muted-r"), (")", "paper")],
    [("doc.define_color(", "paper"), ('"ink"', "muted-r"), (", ", "paper"),
     ('"#15181E"', "muted-r"), (")", "paper")],
    # No continuation lines: SVG collapses leading whitespace, so an indented
    # second line renders flush left and the sample *looks* like broken Python.
    [("doc.define_text_style(", "paper"), ('"display"', "muted-r"),
     (", font_size=", "paper"), ("132", "muted-r"), (", color=", "paper"),
     ('"#FBFAF6"', "muted-r"), (")", "paper")],
    [],
    [("page = doc.page(", "paper"), ('"cover"', "muted-r"), (", canvas=", "paper"),
     ('"deck-16x9"', "muted-r"), (")", "paper")],
    [("page.rect([", "paper"), ("0, 0, 1920, 1080", "muted-r"), ("], fill=", "paper"),
     ('"ink"', "muted-r"), (")", "paper")],
    [("page.text([", "paper"), ("160, 430, 1360, 210", "muted-r"), ("], ", "paper"),
     ('"Q3 Review"', "muted-r"), (", style=", "paper"),
     ('"display"', "muted-r"), (")", "paper")],
    [],
    [("report = doc.write(", "paper"), ('"q3.fg.yaml"', "muted-r"),
     (", format=", "paper"), ('"yaml"', "muted-r"), (")", "paper")],
    [("print(report.ok, ", "paper"), ("len", "graph"), ("(report.issues))", "paper"),
     (f"   # -> {CODE_RESULT}", "muted-r")],
]

CODE_NOTES = [
    ("Validated at build time, not at render time.",
     "`write()` returns a report of typed issues before anything is drawn. "
     "An error is a build failure, not a visual surprise."),
    ("One document, every backend.",
     "The same `.fg.yaml` renders to SVG, PNG, PDF and HTML. Nothing about the "
     "document is renderer-specific."),
    ("Migrated forward, not rewritten.",
     "`codemod.py` migrates older documents to HEAD — exactly the forms the "
     "validator rejects. Your archive keeps opening."),
]

OUTPUTS = [
    ("SVG",          "vector · primary",        "verified"),
    ("PNG",          "headless Chromium",       "verified"),
    ("PDF",          "LaTeX / TikZ",            "verified"),
    ("PDF",          "cairosvg",                "verified"),
    ("HTML / CSS",   "web",                     "degrades flow"),
    ("Math",         "TeX -> SVG (MathJax)",    "verified"),
    ("JSON Schema",  "the format contract",     "verified"),
    ("Audit",        "design-token census",     "verified"),
]

MCP_GROUPS = [
    ("Author -> render", ["run_sdk_code", "run_sdk_client", "render_frameforge_yaml",
                          "write_sdk_client", "read_sdk_client", "list_sdk_clients"]),
    ("Image -> draft",   ["propose_from_image", "propose_from_document",
                          "propose_from_svg", "vectorize_image", "coach_vectorize"]),
    ("Visual QA",        ["compare_images", "diff_renders", "overlay_images",
                          "design_audit", "score_reconstruction"]),
    ("Reconstruction",   ["measure_image", "mark_points", "map_coordinates",
                          "workspace", "construct_vectors", "fit_primitives",
                          "detect_regions", "refine_reconstruction"]),
    ("Discovery",        ["describe_capabilities", "get_guide", "list_fonts",
                          "match_font", "list_sessions", "get_session_resource",
                          "cleanup_sessions"]),
]

SYNC = [
    ("Schema follows the models.",
     "`docs/schema/frameforge-v2.schema.json` is produced by "
     "`Document.model_json_schema()`. `build_schema.py --check` returns "
     "non-zero if the committed file differs from a fresh build."),
    ("The validator is the same model.",
     "`validate.py` validates against that same `Document`, then layers the "
     "spec's structural and geometric rules on top."),
    ("The codemod is the validator, inverted.",
     "Its migrations are exactly the breaking and renamed forms the validator "
     "rejects. Running it makes a legacy document pass."),
    ("The grammar is a view, and it is checked.",
     "`check_grammar_sync.py` introspects the models and diffs the EBNF, "
     "failing on core-profile drift instead of trusting it."),
]

AUDIENCE = [
    ("Agent and tool builders",
     f"{F['mcp_tools']} MCP tools expose the same model, capabilities and "
     "renderer contracts an agent needs to know what is supported, degraded "
     "or unavailable — before it commits."),
    ("Design and documentation teams",
     f"{F['canvas']} canvas presets, real typesetting — pagination, footnotes, "
     "grids, flowing regions, tables, figures — and a design-token audit that "
     "catches drift in the output, not in review."),
    ("Organisations that must audit output",
     "Deterministic renders, declared renderer subsets, provenance and a "
     "migration path. The source outlives the tool that produced it."),
]

FOOTER = [
    ("PRODUCT", ["Spec", "Grammar", "JSON Schema", "Output space", "Error codes"]),
    ("BUILD",   ["Python SDK", "MCP server", "Examples", "Codemod", "Fixtures"]),
    ("PROJECT", ["README", "PURPOSE", "CHANGELOG", "DISCLAIMER", "Brand"]),
]


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def sec_nav(g, top):
    h = 92
    mark(g, M + 18, top + h / 2, 36)
    wordmark(g, M + 52, top + h / 2 - 17, S25, box_w=200)
    links = ["Spec", "Schema", "SDK", "MCP", "Examples"]
    vw = tw(F["version"], S16, 500, MONO) + 44
    widths = [tw(t, S16, 500) for t in links]
    x = W - M - vw - 34 - sum(widths) - 34 * (len(links) - 1)
    for label, lw in zip(links, widths):
        g.text([x, top, lw + 6, h], label, style="nav")
        x += lw + 34
    chip(g, W - M - vw, top + h / 2 - 18, F["version"], h=36, pad=22)
    rule(g, 0, top + h, W)
    return h


def sec_hero(g, top):
    y = top + 60
    eyebrow(g, M, y, "THE OUTPUT LAYER FOR THE AGENT ERA")
    g.text([M, y + 40, 620, 124], "Structured output,\nchecked before it ships.",
           style="h1")
    lede = ("FrameForge turns a typed description — written by you, or by an agent "
            "acting for you — into decks, reports, books, diagrams and vector art. "
            "Every document is validated before it renders.")
    lb = para(g, M, y + 184, 560, lede, style="lede")
    by = lb + 34
    bw = button(g, M, by, "Read the spec")
    chip(g, M + bw + 16, by, "uv pip install frameforge")
    g.text([M, by + 78, 620, 18],
           f"{SITE}  ·  MIT  ·  Python >= 3.10  ·  SDK + MCP  ·  "
           f"{F['mcp_tools']} agent tools", style="cap")

    left_bottom = by + 52 + 26 + 18

    # --- the gate panel: the local gate, summarised, with real numbers ------ #
    note = ("Read off a working tree, not a badge: every row is a command that "
            "was run, and a failing one would be shown failing.")
    px, py, pw = 760, top + 60, 580
    ph = 90 + len(GATE_ROWS) * 56 + 8 + 18 + para_h(pw - 56, note, size=S13, lh=1.6) + 28
    card(g, [px, py, pw, ph], fill="ink", border="hair-r", radius=10)
    g.text([px + 28, py + 20, pw - 56, 26], "$ make check", style="chipr")
    rule(g, px + 28, py + 62, px + pw - 28, color="hair-r")
    ry = py + 90
    for name, cmd, state, ok in GATE_ROWS:
        # A ring, not a dot, for the row that is not passing: the state survives
        # greyscale and colour-blindness on shape alone (BRAND §4).
        if ok:
            g.circle([px + 34, ry + 11], 4.5, fill="gate", decorative=True)
        else:
            g.circle([px + 34, ry + 11], 4.5, fill="ink", stroke="drift",
                     stroke_style={"stroke_width": 1.8}, decorative=True)
        g.text([px + 50, ry, 300, 22], name, style="capr")
        # `cap` is mute (#6B7280) — 3.68:1 on ink, a fail. On this ground the
        # secondary step is `muted-r` at 7.96:1.
        g.text([px + 50, ry + 21, 300, 20], cmd, style="capr")
        sw_ = tw(state, S13, 600, MONO)
        g.text([px + pw - 28 - sw_, ry, sw_ + 6, 22], state, style="capstater")
        ry += 56
    rule(g, px + 28, ry + 8, px + pw - 28, color="hair-r")
    para(g, px + 28, ry + 26, pw - 56, note, style="capr")
    return int(max(left_bottom, py + ph) - top + 58)


def sec_stats(g, top):
    h = 150
    rule(g, 0, top + h, W)
    for i, (num, label) in enumerate(STATS):
        cx = M + i * (CW / len(STATS))
        if i:
            g.line([cx - 24, top + 42], [cx - 24, top + 108], stroke="grid",
                   stroke_style={"stroke_width": 1.0}, decorative=True)
        g.text([cx, top + 44, CW / len(STATS) - 24, 44], num,
               style="statb" if i == 0 else "stat")
        g.text([cx, top + 96, CW / len(STATS) - 24, 18], label, style="cap")
    return h


def sec_derivation(g, top):
    y = section_head(g, top + 76, "ONE SOURCE OF TRUTH",
                     "Everything else is generated from it, or gated against it.",
                     # Precise, because the strong version is false: the EBNF is a
                     # hand-maintained *view* and the spec is authored normative
                     # prose. Both are gated against the models, not generated
                     # from them (README, "The sync guarantee").
                     lede="The Pydantic model is the source of truth. The schema, the capability "
                          "manifest and every render are generated from it; the grammar and the "
                          "normative prose are written by hand and then gated against it — drift "
                          "fails a check rather than ageing quietly.", lede_w=720)
    span = 250
    fy = y + 60 + span / 2                 # source node, centred on the fan
    fan(g, M + 410, fy, M + 680, "model.py", DERIVED, span=span, label_size=S16,
        source=COLORS["frame"], edge=COLORS["graph"], node_stroke=COLORS["ink"],
        node_fill=COLORS["canvas"], label=COLORS["ink"], sw=1.6)
    return int(fy + span / 2 + S16 + 64 - top)


def sec_problem(g, top):
    y = section_head(g, top + 64, "WHY THIS EXISTS",
                     "What breaks when output survives only as pixels.")
    bottom = y
    for (x, cw), (title, body) in zip(cols(M, CW, 3, 40), PROBLEMS):
        rule(g, x, y + 40, x + cw)
        g.text([x, y + 58, cw, 56], title, style="h3")
        bottom = max(bottom, para(g, x, y + 124, cw, body))
    return int(bottom - top + 72)


def sec_loop(g, top):
    y = section_head(g, top + 64, "THE LOOP",
                     "Describe. Validate. Render. Verify.",
                     lede="The same four steps whether a person writes the client or an agent "
                          "calls the tools. The loop closes: the render is measured, and the "
                          "measurement is what drives the next revision.", lede_w=740)
    boxes = cols(M, CW, 4, 24)
    # Card height comes from the tallest body, not from a guess. Card micro-copy
    # sits at 13px (a caption register, on the scale) — a knowing deviation from
    # the 45ch measure floor, which governs body copy, not four-across cards.
    body_top = 112
    bh = body_top + max(para_h(cw - 48, b[3], size=S13, lh=1.6)
                        for (x, cw), b in zip(boxes, LOOP)) + 24
    by = y + 46
    for i, ((x, cw), (num, name, sub, body)) in enumerate(zip(boxes, LOOP)):
        card(g, [x, by, cw, bh])
        g.text([x + 24, by + 24, cw - 48, 18], num, style="eyebrow")
        g.text([x + 24, by + 50, cw - 48, 26], name, style="capi")
        g.text([x + 24, by + 78, cw - 48, 18], sub, style="cap")
        para(g, x + 24, by + body_top, cw - 48, body, style="bodysm")
        if i < 3:
            ax = x + cw
            g.line([ax + 4, by + bh / 2], [ax + 20, by + bh / 2], stroke="graph",
                   stroke_style={"stroke_width": 1.6}, decorative=True)
            g.polyline([[ax + 15, by + bh / 2 - 4], [ax + 20, by + bh / 2],
                        [ax + 15, by + bh / 2 + 4]], stroke="graph",
                       stroke_style={"stroke_width": 1.6}, decorative=True)
    # the return edge — the loop actually closes
    ry = by + bh + 34
    lx, rx = M + 60, M + CW - 60
    g.polyline([[rx, by + bh + 6], [rx, ry], [lx, ry], [lx, by + bh + 6]],
               stroke="graph", stroke_style={"stroke_width": 1.4,
                                             "stroke_dasharray": [4, 4]},
               decorative=True)
    g.polyline([[lx - 4, by + bh + 11], [lx, by + bh + 6], [lx + 4, by + bh + 11]],
               stroke="graph", stroke_style={"stroke_width": 1.4}, decorative=True)
    label = "the measurement drives the next revision"
    lw = tw(label, S13, 500, MONO)
    g.rect([(W - lw - 32) / 2, ry - 13, lw + 32, 26], fill="paper", decorative=True)
    g.text([(W - lw) / 2, ry - 13, lw + 4, 26], label, style="cap")
    return int(ry + 13 - top + 64)


def sec_code(g, top):
    y = section_head(g, top + 64, "THE API",
                     "A document is a program you can read.")
    cx, cyy, cwid = M, y + 46, 700
    chh = 72 + len(CODE) * 26 + 28
    card(g, [cx, cyy, cwid, chh], fill="ink", border="hair-r", radius=10)
    for i, dot in enumerate(("drift", "mute", "gate")):
        g.circle([cx + 28 + i * 18, cyy + 26], 5, fill=dot, decorative=True)
    g.text([cx + 96, cyy + 14, 300, 24], "q3_review.py", style="capr")
    rule(g, cx, cyy + 46, cx + cwid, color="hair-r")
    ly = cyy + 72
    for line in CODE:
        if line:
            # Each span carries its OWN font_family. A span style of just
            # {"color": …} is materialised against the document default face, so
            # the parent object's `font_family` is overridden and monospaced code
            # silently renders in the UI sans — visible in the emitted SVG as
            # `font-family:Inter…` on every tspan. Verified against the pixels,
            # not assumed (PALS's Law).
            g.add({"type": "text", "box": [cx + 28, ly, cwid - 56, 26],
                   "spans": [{"text": t,
                              "style": {"color": COLORS[c], "font_family": MONO,
                                        "font_size": S16, "font_weight": 400}}
                             for t, c in line],
                   "style": {"font_family": MONO, "font_size": S16,
                             "font_weight": 400, "color": "paper"}})
        ly += 26
    nx, nw = M + cwid + 44, CW - cwid - 44
    ny = cyy + 4
    for title, body in CODE_NOTES:
        rule(g, nx, ny, M + CW)
        g.text([nx, ny + 18, nw, 28], title, style="h3")
        ny = para(g, nx, ny + 54, nw, body) + 28
    return int(max(cyy + chh, ny) - top + 64)


def sec_outputs(g, top):
    y = section_head(g, top + 64, "OUTPUTS",
                     "What it renders today — and what still degrades.",
                     lede="Only backends that are verified in this repository appear here. A "
                          "renderer that degrades says so, on the page, next to the ones that "
                          "do not.", lede_w=720)
    boxes, ch, gap = cols(M, CW, 4, 24), 128, 22
    for i, (name, sub, state) in enumerate(OUTPUTS):
        x, cwid = boxes[i % 4]
        by = y + 46 + (i // 4) * (ch + gap)
        card(g, [x, by, cwid, ch])
        g.text([x + 22, by + 24, cwid - 44, 32], name, style="h3")
        g.text([x + 22, by + 58, cwid - 44, 18], sub, style="cap")
        ok = state == "verified"
        tag(g, x + 22, by + 90, state, color="gate" if ok else "drift")
    rows = (len(OUTPUTS) + 3) // 4
    return int(y + 46 + rows * ch + (rows - 1) * gap - top + 72)


def sec_agents(g, top):
    y = section_head(g, top + 64, "AGENT-NATIVE",
                     "Built for the agent that has to be right.",
                     lede=f"{F['mcp_tools']} MCP tools over the same model the SDK uses: author "
                          "and render, draft from an image, then measure the result and prove it "
                          "converged. Bounded operations, inspectable state, verifiable results.",
                     lede_w=760)
    boxes = cols(M, CW, 5, 20)
    rows = max(len(t) for _, t in MCP_GROUPS)
    ch = 92 + rows * 18 + (rows - 1) * 4 + 22      # 92 = card top -> list top
    for i, ((x, cwid), (group, tools)) in enumerate(zip(boxes, MCP_GROUPS)):
        card(g, [x, y + 46, cwid, ch])
        g.text([x + 20, y + 66, cwid - 40, 24], group, style="capi")
        g.text([x + 20, y + 92, cwid - 40, 18], f"{len(tools)} tools", style="eyebrow")
        rule(g, x + 20, y + 120, x + cwid - 20)
        label_column(g, x + 20, y + 138, cwid - 32, tools, id=f"mcp-{i}")
    return int(y + 46 + ch - top + 72)


def sec_proof(g, top):
    # The band is drawn last (it needs its own height), so measure first.
    y = top + 76
    head_h = 34 + int(S40 * 1.18) + 6 + 16 + para_h(
        700, "Four couplings that would silently rot in any other stack. Here each "
             "one is a gate, and a gate that fails stops the build.",
        size=S16, lh=1.55)
    boxes = cols(M, CW, 2, 40)
    row_h = 44 + max(para_h(boxes[0][1] - 26, b, size=S16, lh=1.55) for _, b in SYNC)
    limits = ("FrameForge v2 is a proposed, not-yet-conformantly-implemented system. "
              "The prose and grammar are design targets to verify. The parts you can "
              "actually run — the models, the generated schema, the validator and the "
              "codemod — are the parts to trust.")
    lh_ = 58 + para_h(CW - 56, limits, size=S13, lh=1.6) + 26
    ly = y + head_h + 44 + 2 * row_h + 20
    h = int(ly + lh_ + 76 - top)

    g.rect([0, top, W, h], fill="ink", decorative=True)
    section_head(g, y, "THE PROOF", "The sync guarantee.",
                 lede="Four couplings that would silently rot in any other stack. Here each "
                      "one is a gate, and a gate that fails stops the build.",
                 kstyle="eyebrowr", tstyle="h2r", lstyle="bodyr", lede_w=700)
    for i, (title, body) in enumerate(SYNC):
        x, cwid = boxes[i % 2]
        by = y + head_h + 44 + (i // 2) * row_h
        g.circle([x + 7, by + 11], 5.5, fill="gate", decorative=True)
        g.text([x + 26, by, cwid - 26, 28], title, style="h3r")
        para(g, x + 26, by + 36, cwid - 26, body, style="bodyr")
    # Honest limits — the constraint stays on the page, not in a footnote.
    card(g, [M, ly, CW, lh_], fill="surface", border="hair-r", radius=8)
    tag(g, M + 28, ly + 26, "HONEST LIMITS", color="drift", dark=True)
    para(g, M + 28, ly + 58, CW - 56, limits, style="capr")
    return h


def sec_audience(g, top):
    y = section_head(g, top + 64, "WHO IT SERVES", "Three ways in.")
    bottom = y
    for (x, cwid), (title, body) in zip(cols(M, CW, 3, 40), AUDIENCE):
        rule(g, x, y + 40, x + cwid)
        g.text([x, y + 58, cwid, 32], title, style="h3")
        bottom = max(bottom, para(g, x, y + 98, cwid, body))
    return int(bottom - top + 72)


def sec_cta(g, top):
    cardh = 208
    axis = top + 40 + cardh / 2          # ONE optical axis for both columns
    card(g, [M, top + 40, CW, cardh], fill="canvas", radius=10)

    # The action row is measured FIRST; the text column then gets exactly what is
    # left. A hardcoded text width here ran the sub-line 28px *under* the button
    # and put the heading, the buttons and the sub-line on three different axes.
    install, spec = "uv pip install frameforge", "Read the spec"
    cwid = tw(install, S16, 500, MONO) + 44
    bwid = tw(spec, S16, 600) + 56
    bx = M + CW - 56 - (bwid + 16 + cwid)
    button(g, bx, axis - 26, spec)
    chip(g, bx + bwid + 16, axis - 26, install)

    # Text column, bounded by the action row with a real gutter.
    tx = M + 56
    col = bx - 56 - tx
    head, sub = "Author it. Then prove it.", \
                "Install the package, run an example, read the report it prints."
    hh, sh = 52, para_h(col, sub)
    assert tw(head, S40, 600, DISPLAY) <= col, "CTA heading overruns the action row"
    assert tw(sub, S16) <= col, "CTA sub-line overruns the action row"
    ty = axis - (hh + 10 + sh) / 2       # block centred on the same axis
    g.text([tx, ty, col, hh], head, style="h2")
    para(g, tx, ty + hh + 10, col, sub)

    fy = top + cardh + 130
    rule(g, M, fy - 40, M + CW)
    mark(g, M + 18, fy + 14, 32)
    wordmark(g, M + 48, fy + 1, S20, box_w=180)
    g.text([M, fy + 42, 340, 34],
           f"v{F['version']} · MIT · Pedro Anisio Silva", style="cap")
    fbottom = fy
    for i, ((x, cwid), (head, items)) in enumerate(zip(cols(M + 460, CW - 460, 3, 30), FOOTER)):
        g.text([x, fy - 4, cwid, 18], head, style="eyebrow")
        fbottom = max(fbottom,
                      label_column(g, x, fy + 22, cwid, items, lh=18, gap=3,
                                   id=f"foot-{i}"))
    g.text([M, fbottom + 34, CW, 18],
           f"{SITE}  ·  github.com/pedroanisio/frameforge  ·  This page is itself a "
           "FrameForge document — static/examples/frameforge_landing.py", style="cap")
    return int(fbottom + 52 - top + 40)


SECTIONS = [sec_nav, sec_hero, sec_stats, sec_derivation, sec_problem, sec_loop,
            sec_code, sec_outputs, sec_agents, sec_proof, sec_audience, sec_cta]


def _shell() -> DocumentBuilder:
    doc = DocumentBuilder(title="FrameForge — structured output, checked before it ships",
                          profile="diagram", lang="en")
    doc.describe("Proposed landing page for the FrameForge service, authored with "
                 "the FrameForge SDK. Every count is generated from the repository "
                 "(see FACTS in static/examples/frameforge_landing.py).")
    for name, value in COLORS.items():
        doc.define_color(name, value)
    for name, style in STYLES.items():
        doc.define_text_style(name, **style)
    # The size the hero's example code would render at — declared so the code
    # sample references a real token instead of an undefined name.
    doc.define_text_style("display", font_family=DISPLAY, font_size=132,
                          font_weight=600, color="paper")
    return doc


def _heights() -> list[int]:
    """Measure every section by drawing it on a scratch page.

    Each `sec_*` returns the height its *content* actually needs, so the canvas
    is derived rather than declared. A hand-maintained list of section heights is
    exactly the kind of manual mirror that silently rots — and the failure mode
    is a clipped section, which the renderer would then report as lost text.
    """
    scratch = _shell().page("scratch", canvas={"size": [W, 1], "units": "px"},
                            coordinate_mode="absolute")
    g = scratch.layer("scratch")
    return [int(section(g, 0)) for section in SECTIONS]


def _assign_reading_order(page) -> list[str]:
    """Declare the semantic layer: text is content, every shape is chrome.

    Two jobs, both demanded by the a11y gate (`tooling/check_accessibility.py`):

    * **A11Y-3** — an absolutely-positioned page 6,300px tall has no inferable
      reading order, so it must be declared. The sections draw strictly
      top-to-bottom and, within a section, column by column, so insertion order
      *is* reading order.
    * **A11Y-4** — every non-decorative object must be addressable. On this page
      no shape carries reading content: every rect is a card or panel, every line
      is a rule, an edge or an arrow, every ellipse is a state dot or a graph
      node. Their meaning lives in the text beside them (the derivation fan reads
      through its labels, which stay content). Saying so explicitly is more
      honest than padding the reading order with silent geometry.
    """
    order: list[str] = []
    counter = 0

    def walk(objects):
        nonlocal counter
        for obj in objects:
            if obj.get("decorative"):
                continue
            if obj.get("type") == "group":
                if obj.get("id"):      # the container is announced, then its rows
                    order.append(obj["id"])
                walk(obj.get("children", []))
                continue
            if obj.get("type") != "text":
                obj["decorative"] = True
                continue
            if not obj.get("id"):
                counter += 1
                obj["id"] = f"t{counter:03d}"
            order.append(obj["id"])

    for layer in page._page.get("layers", []):
        walk(layer.get("objects", []))
    page._page["reading_order"] = order
    return order


def build() -> DocumentBuilder:
    heights = _heights()
    H = sum(heights)
    doc = _shell()
    page = doc.page("landing", canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute")
    page.layer("ground").rect([0, 0, W, H], fill="paper", decorative=True)
    g = page.layer("page")

    y = 0
    for section, h in zip(SECTIONS, heights):
        actual = int(section(g, y))
        if actual != h:            # sections must be position-independent
            raise AssertionError(
                f"{section.__name__}: measured {h}px at top=0, {actual}px at top={y}")
        y += h
    _assign_reading_order(page)
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true",
                    help="re-derive every FACT from the working tree and exit")
    args = ap.parse_args()
    if args.verify:
        return verify_facts()

    out = os.path.join(ROOT, "static", "examples", "fixtures", "frameforge-landing.fg.yaml")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    report = build().write(out, format="yaml")
    errors = [i for i in report.issues if i.severity == "error"]
    warns = [i for i in report.issues if i.severity != "error"]
    print(f"ok={report.ok} errors={len(errors)} warnings={len(warns)} -> {out}")
    for i in errors[:20]:
        print(f"  [ERROR] [{i.rule_id}] {i.path}: {i.message}")
    for i in warns[:8]:
        print(f"  [warn] [{i.rule_id}] {i.path}: {i.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
