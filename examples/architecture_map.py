#!/usr/bin/env python3
"""FrameGraph v2 — Architecture Map (companion to ``conceptual-analysis.md``).

This map is *authored through the FrameGraph SDK* and rendered by the project's
own SVG proxy — the system drawing a portrait of itself. It is the visual
synthesis artifact (Output Section 9) of the conceptual-codebase-analysis: a
single absolute-mode page whose nodes are the core concepts (color-coded by
classification), grouped into capability regions, wired by semantic (data-flow)
and governing (generates/enforces) edges, with the four §6 tension hotspots
marked in red.

Run from the repository root::

    uv run python examples/architecture_map.py     # writes architecture-map.svg
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, render_page_svgs, serialize  # noqa: E402
from framegraph.sdk.validate import validate_static_rules  # noqa: E402

W, H = 1340, 984
CANVAS = {"size": [W, H], "units": "px"}
SANS = ["Inter", "Helvetica", "Arial", "sans-serif"]
MONO = ["JetBrains Mono", "SFMono-Regular", "Menlo", "monospace"]

# Classification palette (fill, stroke) — matches the legend + Concept Atlas.
SOT = ("#F5F3FF", "#7C3AED")   # source of truth (the model)
DOM = ("#EFF6FF", "#2563EB")   # domain (authoring / model)
GOV = ("#FEF3C7", "#B45309")   # control / governance (gates)
PLAT = ("#F1F5F9", "#475569")  # platform / rendering
INTEG = ("#ECFEFF", "#0D9488")  # integration (MCP / vision)
GEN = ("#FEF9C3", "#CA8A04")   # generated / checked view
RED = "#DC2626"

INK = "#0F172A"
MUTE = "#64748B"


def ts(size, color, *, weight=None, align=None, spacing=None, lh=None,
       transform=None, family=None):
    """An inline text Style dict (the model accepts inline Style anywhere)."""
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


def region(page, box, label, *, fill="#F8FAFC", stroke="#CBD5E1", sw=1.2,
           label_color=MUTE):
    x, y, w, h = box
    page.rect([x, y, w, h], radius=14, fill=fill, stroke=stroke,
              stroke_style={"stroke_width": sw})
    page.text([x + 18, y + 14, w - 36, 16], label,
              style=ts(12.5, label_color, weight=800, spacing=0.6,
                       transform="uppercase"))


def node(page, box, palette, title, title_color, subs, sub_color, *,
         sw=1.4, family=None):
    x, y, w, h = box
    fill, stroke = palette
    page.rect([x, y, w, h], radius=9, fill=fill, stroke=stroke,
              stroke_style={"stroke_width": sw})
    page.text([x + 14, y + 9, w - 26, 17], title,
              style=ts(13, title_color, weight=700, family=family))
    for i, line in enumerate(subs):
        page.text([x + 14, y + 30 + i * 14, w - 26, 13], line,
                  style=ts(10.5, sub_color))


def build() -> DocumentBuilder:
    b = DocumentBuilder(title="FrameGraph v2 — Architecture Map",
                        profile="diagram", lang="en")
    page = b.page("architecture-map", canvas=CANVAS, coordinate_mode="absolute")

    # ---- background ----------------------------------------------------- #
    page.layer("bg")
    page.rect([0, 0, W, H], fill="#FFFFFF")
    page.text([40, 26, 1000, 30], "FrameGraph v2 — Architecture Map",
              style=ts(24, INK, weight=800, spacing=-0.3))
    page.text([40, 58, 1260, 18],
              "A DSL + code-generation system: one closed Pydantic model is the "
              "source of truth; every other artifact is generated from it or "
              "checked against it by a wall of CI gates.",
              style=ts(12.5, MUTE, lh=1.3))

    # Cluster regions (drawn first, behind the nodes).
    region(page, [40, 214, 360, 300], "Authoring · inputs")
    region(page, [940, 92, 360, 360], "Generated / checked views")
    region(page, [410, 540, 520, 330], "Rendering · capability")
    region(page, [40, 540, 360, 330], "Governance · make check (= CI)",
           fill="#FFFBEB", stroke="#FCD34D", sw=1.5, label_color="#B45309")

    # ---- edges (behind nodes) ------------------------------------------ #
    page.layer("edges")
    # SDK -> Model : build & validate (data flow)
    page.arrow([392, 286], [560, 178], color=PLAT[1], width=1.8, head=9)
    page.text([398, 250, 150, 13], "build → validate", style=ts(10, PLAT[1], weight=600))
    # Model -> Generated views : generates / governs (dashed, amber)
    page.arrow([832, 140], [936, 150], color=GOV[1], width=2.0, head=9,
               stroke_style={"stroke_dasharray": [6, 4]})
    page.arrow([832, 150], [936, 250], color=GOV[1], width=1.3, head=7,
               stroke_style={"stroke_dasharray": [6, 4]})
    page.arrow([832, 158], [936, 360], color=GOV[1], width=1.3, head=7,
               stroke_style={"stroke_dasharray": [6, 4]})
    # Model -> Renderer : the validated document (data flow)
    page.arrow([655, 186], [655, 536], color=PLAT[1], width=1.8, head=9)
    page.text([548, 356, 100, 13], "validated doc", style=ts(10, PLAT[1], weight=600))
    # Renderer -> SDK : inverted dependency (red)
    page.arrow([430, 604], [381, 344], color=RED, width=1.8, head=9)
    page.text([430, 520, 420, 13],
              "sdk.conform imports tooling.Renderer — inverted layering",
              style=ts(10, RED, weight=700))
    # Governance -> Renderer : golden / overflow / a11y gate (dashed, amber)
    page.arrow([392, 726], [424, 748], color=GOV[1], width=1.6, head=8,
               stroke_style={"stroke_dasharray": [6, 4]})

    # ---- nodes ---------------------------------------------------------- #
    page.layer("nodes")

    # Source of truth (centered).
    page.rect([510, 92, 320, 94], radius=12, fill=SOT[0], stroke=SOT[1],
              stroke_style={"stroke_width": 2.5})
    page.text([510, 108, 320, 18], "models/framegraph.py",
              style=ts(14, "#5B21B6", weight=700, align="center", family=MONO))
    page.text([510, 130, 320, 13], "SINGLE SOURCE OF TRUTH · Document (Pydantic v2)",
              style=ts(10.5, "#6D28D9", align="center"))
    page.text([510, 146, 320, 13], "VisualObject ∪ Flowable · Style bag · HEAD 2.2.0",
              style=ts(10.5, "#6D28D9", align="center"))
    page.text([510, 163, 320, 13], 'extra="forbid" — unknown keys are hard errors',
              style=ts(10.5, "#7C3AED", align="center"))

    # Authoring region nodes.
    node(page, [60, 250, 320, 62], DOM,
         "framegraph.sdk — DocumentBuilder", "#1E40AF",
         ["PageBuilder · layout · paint · widgets · macros ·",
          "charts · geometry · 3D scenes · topology · fields"], "#1E40AF")
    node(page, [60, 320, 320, 46], DOM,
         "sdk.expand · sdk.validate", "#1E40AF",
         ["lowers builders → model; validates THERE"], "#1E40AF")
    node(page, [60, 374, 320, 60], INTEG,
         "framegraph.mcp — FastMCP server", "#0F766E",
         ["run_sdk_code · render SVG/PNG · propose_from_*",
          "the AI authoring feedback loop"], "#0F766E")
    node(page, [60, 442, 320, 58], INTEG,
         "framegraph.vision — propose_from_*", "#0F766E",
         ["OpenCV/VLM + pdf_to_framegraph_yml → proposed doc",
          "UNVERIFIED draft (PALS's Law)"], "#0F766E")

    # Generated / checked views.
    gen_rows = [
        ("schema/…schema.json", "regenerate + byte-equal", 124),
        ("grammar/*.ebnf", "hand view · discriminator/enum parity", 174),
        ("spec/…spec.md", "membership · every type named in prose", 224),
        ("docs/ (MkDocs)", "regenerate + diff · gen_docs.py", 274),
        ("FIXTURE-STATUS.md", "regenerate + byte-equal", 324),
        ("viewer/ type sets", "set-membership parity test", 374),
    ]
    for title, sub, y in gen_rows:
        node(page, [958, y, 322, 42], GEN, title, "#854D0E", [sub], "#92400E")

    # Rendering region.
    node(page, [428, 574, 484, 58], ("#FEE2E2", "#DC2626"),
         "Renderer — tooling/render_fixtures.py  (~2,400 LOC)", "#991B1B",
         ["orchestrator: type dispatch · page layout · flow pagination · text-fit"],
         "#991B1B", sw=2.0)
    node(page, [428, 642, 234, 80], PLAT,
         "rendering/domain — services", "#334155",
         ["paint · stroke · text-style · canvas",
          "effect · layout_engine · table_layout",
          "behind domain/ports (clean hexagon)"], "#334155")
    node(page, [670, 642, 242, 80], PLAT,
         "ScenePainter port → adapters", "#334155",
         ["SVG painter (canonical)",
          "Chromium/Playwright → PNG (raster)",
          "LaTeX/TikZ → .tex (flow only)"], "#334155")
    page.rect([428, 730, 484, 38], radius=9, fill=PLAT[0], stroke=PLAT[1],
              stroke_style={"stroke_width": 1.4})
    page.text([442, 744, 470, 14],
              "font_metrics (fontTools/fc-match) · golden lock = SHA-256 per page (deterministic)",
              style=ts(10.5, "#334155"))
    page.rect([428, 776, 484, 40], radius=9, fill="#FFFFFF", stroke="#94A3B8",
              stroke_style={"stroke_width": 1.2, "stroke_dasharray": [4, 3]})
    page.text([442, 786, 470, 13], "TWO layout engines (a paradigm boundary):",
              style=ts(10.5, "#475569", weight=700))
    page.text([442, 800, 470, 13],
              "page-mode (absolute layers + Group.layout)  ≠  flow-mode (naive pagination)",
              style=ts(10.5, "#475569"))

    # Governance region.
    page.rect([60, 574, 320, 36], radius=9, fill="#FEF3C7", stroke="#B45309",
              stroke_style={"stroke_width": 1.4})
    page.text([74, 586, 300, 14], "validate.py — Pydantic + ~14 static rules",
              style=ts(12.5, "#92400E", weight=700))
    gates = [
        "schema · status · docs-check  (regenerate + diff)",
        "grammar-check  (discriminator / enum parity)",
        "spec-check  (every type named in prose)",
        "golden-check  (b1 oracle render hashes)",
        "a11y-check  (reading_order · alt text)",
        "overflow  (no text escapes its box)",
        "§8.5  out-of-profile types ⇒ warn, not error",
    ]
    for i, g in enumerate(gates):
        page.text([74, 626 + i * 18, 300, 13], "•  " + g, style=ts(11, "#92400E"))
    page.rect([60, 752, 320, 48], radius=9, fill="#FEF3C7", stroke="#B45309",
              stroke_style={"stroke_width": 1.4})
    page.text([74, 762, 300, 14], "codemod.py — migrations",
              style=ts(12.5, "#92400E", weight=700))
    page.text([74, 781, 300, 13],
              "P3 stroke-split · size→sizing · alias→canonical",
              style=ts(10.5, "#92400E"))

    # ---- legend + tension hotspots (top layer) -------------------------- #
    page.layer("marks")

    # Legend box.
    page.rect([940, 470, 360, 196], radius=10, fill="#FFFFFF", stroke="#CBD5E1",
              stroke_style={"stroke_width": 1.2})
    page.text([958, 484, 320, 16], "Legend",
              style=ts(12.5, MUTE, weight=800, spacing=0.6, transform="uppercase"))
    legend_cls = [
        (SOT, "source of truth (model)"),
        (DOM, "domain (authoring / model)"),
        (GOV, "control / governance (gates)"),
        (PLAT, "platform / rendering"),
        (INTEG, "integration (MCP / vision)"),
        (GEN, "generated / checked view"),
    ]
    for i, (pal, lab) in enumerate(legend_cls):
        y = 506 + i * 24
        page.rect([958, y, 16, 16], radius=3, fill=pal[0], stroke=pal[1],
                  stroke_style={"stroke_width": 1.6})
        page.text([982, y + 1, 220, 13], lab, style=ts(10.5, "#334155"))
    # Edge styles.
    page.arrow([1138, 514], [1176, 514], color=PLAT[1], width=1.8, head=8)
    page.text([1184, 508, 110, 13], "data flow", style=ts(10.5, "#334155"))
    page.arrow([1138, 538], [1176, 538], color=GOV[1], width=1.8, head=8,
               stroke_style={"stroke_dasharray": [6, 4]})
    page.text([1184, 532, 116, 13], "generates / governs", style=ts(10.5, "#334155"))
    page.arrow([1138, 562], [1176, 562], color=RED, width=1.8, head=8)
    page.text([1184, 556, 116, 13], "inverted dependency", style=ts(10.5, "#334155"))
    page.circle([1146, 588], 8, fill=RED)
    page.text([1162, 582, 130, 13], "tension hotspot (§6)", style=ts(10.5, "#334155"))

    # Tension hotspot markers (numbered red discs at node corners).
    for cx, cy, n in [(898, 580, "1"), (1266, 180, "2"), (816, 104, "3"), (898, 782, "4")]:
        page.circle([cx, cy], 11, fill=RED)
        page.text([cx - 11, cy - 7, 22, 14], n,
                  style=ts(12, "#FFFFFF", weight=800, align="center"))

    # ---- tension report band ------------------------------------------- #
    page.rect([40, 888, 1260, 90], radius=10, fill="#FEF2F2", stroke="#FECACA",
              stroke_style={"stroke_width": 1.2})
    page.text([56, 902, 300, 16], "Tensions (§6)",
              style=ts(12, "#991B1B", weight=800))
    tensions = [
        ([56, 916, 600, 30],
         "1 · Canonical Renderer is a 2.4K-LOC monolith in tooling/ the SDK depends "
         "UP into — inverted layering; hexagonal extraction stopped at the orchestrator."),
        ([56, 948, 600, 30],
         "2 · Drift surface: grammar + spec are hand-maintained VIEWS, held only by "
         "membership/enum gates — looser than the byte-equal schema."),
        ([672, 916, 612, 30],
         "3 · Style is one ~100-field closed CSS bag; TextStyle / StrokeStyle alias "
         "it — broad surface, only partly honoured by the renderer."),
        ([672, 948, 612, 30],
         "4 · Two paradigms: absolute page-mode vs naive flow-mode pagination — "
         "separate engines, no shared layout model; flow is the weaker one."),
    ]
    for box, txt in tensions:
        page.text(box, txt, style=ts(10.5, "#7F1D1D", lh=1.35))

    return b


def main() -> int:
    b = build()
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built {len(doc.pages)} page(s) — ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:30]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    svg = render_page_svgs(doc)[0]
    out_svg = os.path.join(ROOT, "architecture-map.svg")
    with open(out_svg, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"Wrote {out_svg}")

    # Root, not fixtures/ — this is an analysis asset, not part of the gated
    # fixture corpus (a file in fixtures/ would desync FIXTURE-STATUS.md).
    out_yaml = os.path.join(ROOT, "architecture-map.fg.yaml")
    with open(out_yaml, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {out_yaml}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
