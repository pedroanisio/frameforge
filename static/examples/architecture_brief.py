#!/usr/bin/env python3
"""FrameGraph — *how this system thinks*: a conceptual architecture map, authored
and rendered **by FrameGraph itself** (the dogfood).

This is the visual output of a conceptual-codebase-analysis of FrameGraph v2:
the System Thesis, the author→validate→render→verify pipeline (Lens 2), the
"model is the single source of truth" spine (Lens 3 invariants), the core
concepts colour-coded by classification (Lens 1), and the design tensions
(Lens 6). Two landscape-A4 pages.

Run from the repo root::

    uv run python examples/architecture_brief.py    # -> out/arch/*.fg.yaml (+ render via MCP/tooling)
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
sys.path.insert(0, os.path.join(ROOT, "static", "examples"))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, serialize  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402
from framegraph_logo import mark, wordmark  # noqa: E402  — the canonical FrameGraph logo

# --- brand tokens (docs/BRAND.md §4) ---------------------------------------- #
INK, PAPER, CANVAS = "#15181E", "#FBFAF6", "#FFFFFF"
FRAME, CYAN = "#1F4FD8", "#12B0C3"          # frame-blue · graph-cyan
GREEN, RED = "#1E9E5A", "#D23B2B"           # gate-green · drift-red
GRID, MUTE = "#D4D8DE", "#6B7280"
MONO = ["IBM Plex Mono", "DejaVu Sans Mono", "monospace"]
SANS = ["IBM Plex Sans", "DejaVu Sans", "Helvetica", "Arial", "sans-serif"]

# classification → colour (Lens 1)
DOMAIN, CONTROL, PLATFORM, INTEGRATION = FRAME, CYAN, MUTE, GREEN

SW, SH = 842, 595        # A4 landscape (pt)
MX = 30


def ts(size, color, *, weight=None, align=None, spacing=None, lh=None, family=None, transform=None):
    s = {"font_family": family or SANS, "font_size": size, "color": color}
    if weight is not None:
        s["font_weight"] = weight
    if align is not None:
        s["align"] = align
    if spacing is not None:
        s["letter_spacing"] = spacing
    if lh is not None:
        s["line_height"] = lh
    if transform is not None:
        s["text_transform"] = transform
    return s


def crop(page, color=INK, *, m=16, arm=14, sw=1.3):
    for dx in (1, -1):
        for dy in (1, -1):
            x, y = (m if dx > 0 else SW - m), (m if dy > 0 else SH - m)
            page.line([x, y], [x + dx * arm, y], stroke=color, stroke_style={"stroke_width": sw})
            page.line([x, y], [x, y + dy * arm], stroke=color, stroke_style={"stroke_width": sw})


def _page(b, sid):
    p = b.page(sid, canvas={"size": [SW, SH], "units": "pt"}, coordinate_mode="absolute")
    p.layer("bg")
    p.rect([0, 0, SW, SH], fill=PAPER)
    crop(p)
    p.layer("body")
    return p


def _topbar(page, kicker, title):
    mark(page, MX + 13, 34, 26, frame=INK, graph=FRAME, node_fill=CANVAS)
    wordmark(page, MX + 32, 24, 18, frame_color=INK, graph_color=FRAME, box_w=120)
    page.text([MX + 168, 22, 480, 14], kicker,
              style=ts(9.5, CYAN, weight=700, family=MONO, spacing=2, transform="uppercase"))
    page.text([MX + 168, 36, 560, 18], title, style=ts(15, INK, weight=700))
    page.line([MX, 58], [SW - MX, 58], stroke=GRID, stroke_style={"stroke_width": 1})


def _foot(page, n):
    page.line([MX, SH - 30], [SW - MX, SH - 30], stroke=GRID, stroke_style={"stroke_width": 1})
    page.text([MX, SH - 24, 560, 12],
              "authored & rendered by FrameGraph — this map is a .fg document; `make check` gates its claims",
              style=ts(8, MUTE, family=MONO, spacing=0.5))
    page.text([SW - MX - 60, SH - 24, 60, 12], f"{n:02d} / 02",
              style=ts(8, MUTE, family=MONO, align="right"))


def _arrow(page, x1, y, x2, *, color=INK, sw=1.6):
    """A horizontal flow arrow from x1 to x2 at height y."""
    page.line([x1, y], [x2 - 7, y], stroke=color, stroke_style={"stroke_width": sw})
    page.polygon([[x2, y], [x2 - 8, y - 4], [x2 - 8, y + 4]], fill=color, stroke=color,
                 stroke_style={"stroke_width": 0.5})


def _stage(page, x, y, w, h, accent, name, bullets, foot):
    """A pipeline-stage card: classification top-bar + name + concept bullets + a footnote."""
    page.rect([x, y, w, h], radius=7, fill=CANVAS, stroke=GRID, stroke_style={"stroke_width": 1.2})
    page.rect([x, y, w, 5], radius=2.5, fill=accent)
    page.text([x + 11, y + 15, w - 22, 16], name,
              style=ts(12.5, INK, weight=700, family=MONO, spacing=1))
    yy = y + 40
    for b in bullets:
        page.circle([x + 15, yy + 5, ], 1.7, fill=accent, stroke=accent)
        page.text([x + 24, yy, w - 34, 14], b, style=ts(9, INK, lh=1.25))
        yy += 17
    page.text([x + 11, y + h - 20, w - 22, 14], foot, style=ts(8, MUTE, family=MONO))


def _tension(page, x, y, w, label, detail):
    page.rect([x, y, w, 56], radius=6, fill=CANVAS, stroke=RED, stroke_style={"stroke_width": 1.3})
    page.rect([x, y, 5, 56], fill=RED)
    page.text([x + 14, y + 8, w - 20, 13], label, style=ts(9.5, RED, weight=700))
    page.text([x + 14, y + 24, w - 22, 28], detail, style=ts(8, MUTE, lh=1.25))


def _legend_chip(page, x, y, color, label):
    page.rect([x, y, 11, 11], radius=2.5, fill=color)
    page.text([x + 16, y - 1, 110, 13], label, style=ts(8.5, INK))


# --------------------------------------------------------------------------- #
def build_map(b):
    p = _page(b, "arch-map")
    _topbar(p, "conceptual codebase analysis", "FrameGraph — how this system thinks")

    # thesis strip
    p.rect([MX, 66, SW - 2 * MX, 40], radius=5, fill=INK)
    p.text([MX + 14, 74, SW - 2 * MX - 28, 26],
           "One closed model is the single source of truth; everything else is generated from it or "
           "gated against it. Author → validate → render → verify — and LLM output is untrusted until "
           "proven (PALS's Law).",
           style=ts(8.8, PAPER, lh=1.3, family=MONO))

    # the pipeline (Lens 2): 5 stages, left → right
    sy, sh, sw = 120, 150, 142
    xs = [MX + i * (sw + 11) for i in range(5)]
    _stage(p, xs[0], sy, sw, sh, CONTROL, "AUTHOR",
           ["DocumentBuilder · PageBuilder", "widgets · paint · figures", "MCP — 11 tools",
            "SDK — 123 exports"], "control + integration")
    _stage(p, xs[1], sy, sw, sh, DOMAIN, "MODEL",
           ["Document · Page", "Object — 30 closed types", "Style · paint · tokens",
            "extra = forbid (×7)"], "domain · source of truth")
    _stage(p, xs[2], sy, sw, sh, CONTROL, "RESOLVE",
           ["canvas · paint · stroke", "text-style · effect", "layout · text-fitter",
            "= the membranes"], "control · 11 resolvers")
    _stage(p, xs[3], sy, sw, sh, PLATFORM, "PAINT",
           ["ScenePainter — the port", "→ SVG adapter", "→ TikZ adapter", "backend-neutral"],
           "platform · hexagonal seam")
    _stage(p, xs[4], sy, sw, sh, INTEGRATION, "VERIFY",
           ["golden lock — SHA-256", "overflow · a11y", "validate · static rules",
            "make check (14 gates)"], "integration · the spine")
    for i in range(4):
        _arrow(p, xs[i] + sw, sy + sh / 2, xs[i + 1])

    # the truth-spine (Lens 3): MODEL generates the mirrored artifacts, each gated
    spy = sy + sh + 26
    p.line([xs[1] + sw / 2, sy + sh], [xs[1] + sw / 2, spy], stroke=FRAME, stroke_style={"stroke_width": 1.6})
    p.polygon([[xs[1] + sw / 2, spy], [xs[1] + sw / 2 - 4, spy - 8], [xs[1] + sw / 2 + 4, spy - 8]],
              fill=FRAME, stroke=FRAME, stroke_style={"stroke_width": 0.5})
    spx, spw = xs[1], xs[4] + sw - xs[1]
    p.rect([spx, spy, spw, 52], radius=6, fill=CANVAS, stroke=FRAME, stroke_style={"stroke_width": 1.3})
    p.text([spx + 14, spy + 9, spw - 28, 14], "GENERATED FROM THE MODEL",
           style=ts(9.5, FRAME, weight=700, family=MONO, spacing=1.5))
    p.text([spx + 14, spy + 27, spw - 28, 16],
           "schema · grammar · spec · docs · fixture-status — each mirror is gated by its *-check "
           "(drift = build failure). The model never lies because nothing is allowed to disagree with it.",
           style=ts(8.3, INK, lh=1.25))

    # legend
    ly = spy + 66
    p.text([MX, ly, 90, 12], "classification:", style=ts(8.5, MUTE, weight=700, family=MONO))
    _legend_chip(p, MX + 92, ly, DOMAIN, "domain")
    _legend_chip(p, MX + 188, ly, CONTROL, "control")
    _legend_chip(p, MX + 284, ly, PLATFORM, "platform")
    _legend_chip(p, MX + 386, ly, INTEGRATION, "integration")
    p.rect([MX + 506, ly, 11, 11], radius=2.5, fill=CANVAS, stroke=RED, stroke_style={"stroke_width": 1.3})
    p.text([MX + 522, ly - 1, 200, 13], "design tension (see page 2)", style=ts(8.5, INK))

    _foot(p, 1)


def build_atlas(b):
    p = _page(b, "arch-atlas")
    _topbar(p, "concept atlas · design tensions", "What it believes exists — and where it strains")

    # Concept Atlas (Lens 1) — left column
    ax, aw = MX, 392
    p.text([ax, 70, aw, 14], "CONCEPT ATLAS — the core ontology",
           style=ts(10, INK, weight=700, family=MONO, spacing=1))
    rows = [
        (DOMAIN, "Document / Page / Object", "the closed visual IR — 30 discriminated types"),
        (DOMAIN, "Style · paint · tokens", "presentation vocabulary, today co-located on objects"),
        (CONTROL, "DocumentBuilder / Page", "the authoring machine (SDK · 123 exports)"),
        (CONTROL, "Domain resolvers (×11)", "membranes: tokens → normalized display list"),
        (PLATFORM, "ScenePainter port", "the backend seam → SVG · TikZ adapters"),
        (INTEGRATION, "Golden lock + gates", "the verification spine (make check ×14)"),
        (INTEGRATION, "MCP server (11 tools)", "the agent-facing author+render loop"),
    ]
    yy = 90
    for accent, name, desc in rows:
        p.rect([ax, yy, aw, 40], radius=5, fill=CANVAS, stroke=GRID, stroke_style={"stroke_width": 1})
        p.rect([ax, yy, 5, 40], fill=accent)
        p.text([ax + 14, yy + 7, aw - 22, 14], name, style=ts(10, INK, weight=700))
        p.text([ax + 14, yy + 23, aw - 22, 13], desc, style=ts(8.3, MUTE, lh=1.15))
        yy += 46

    # Absent concepts callout
    p.rect([ax, yy + 2, aw, 50], radius=5, fill=INK)
    p.text([ax + 12, yy + 11, aw - 24, 12], "ABSENT BY DESIGN (the revealing gaps)",
           style=ts(8.5, CYAN, weight=700, family=MONO, spacing=1))
    p.text([ax + 12, yy + 27, aw - 24, 26],
           "no data/temporal axis · no native PDF backend · no animation · "
           "content/presentation not yet split (v2.3)",
           style=ts(8, PAPER, lh=1.25))

    # Design Tensions (Lens 6) — right column
    tx, tw = MX + 414, SW - 2 * MX - 414
    p.text([tx, 70, tw, 14], "DESIGN TENSIONS — where it strains",
           style=ts(10, INK, weight=700, family=MONO, spacing=1))
    tensions = [
        ("Closed model ↔ expressiveness", "extra=forbid + a 30-type closed union: every new visual "
         "idea needs a model change + 4-artifact propagation. Bet: determinism over velocity."),
        ("Style co-located ↔ retarget", "presentation is mixed into the content tree, which blocks "
         "one-source→many-surfaces. The v2.3 split is the scheduled paydown."),
        ("Backend-neutral ↔ no PDF painter", "ScenePainter abstracts backends, but PDF is a "
         "SVG→cairo proxy — so PDF/UA a11y is gated on a backend that doesn't exist yet."),
        ("Model-as-truth ↔ N mirrors", "the more artifacts generated from the model, the more "
         "potential lies. Answer: gate every mirror (*-check). Discipline becomes CI."),
        ("MCP cache ↔ disk model", "the long-running MCP snapshots the model at startup; new "
         "presets reject until the server restarts. An invisible operational edge."),
    ]
    ty = 90
    for label, detail in tensions:
        _tension(p, tx, ty, tw, label, detail)
        ty += 64

    _foot(p, 2)


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameGraph — Architecture Brief", profile="report", lang="en")
    build_map(b)
    build_atlas(b)
    return b


def _write(b, name):
    doc = b.build()
    report = validate_static_rules(doc)
    errs = [i for i in report.issues if i.severity == "error"]
    out_dir = os.path.join(ROOT, "out", "arch")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"  {name}: {len(doc.pages)} page(s) ok={report.ok} errors={len(errs)} -> out/arch/{name}")
    return len(errs)


def main() -> int:
    e = _write(build(), "architecture-brief.fg.yaml")
    print("Render: `uv run --group browser python tooling/render_chromium.py "
          "out/arch/architecture-brief.fg.yaml --out out/arch/png`")
    return 1 if e else 0


if __name__ == "__main__":
    raise SystemExit(main())
