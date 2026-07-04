#!/usr/bin/env python3
"""BookBuilder — a capability tour as a real book (roadmap item 8).

Eight chapters, 32+ A5 pages, every plate COMPUTED by the SDK it
demonstrates: flow typography and the margin canon; the stroke-outline
engine (profiles, calligraphic pen, scatter brushes); the planar kernel
(booleans, holes, divide, offsets, Live-Paint faces); the Chevreul colour
canon (colour guide, closed palette, recolor); style richness (appearance
passes, effect stacks, humanize); charts and tables; Scene3D extrusion and
revolution with multiview; and the book layer itself, self-described.
Build-time numbering throughout — chapters, sections, `Figure N.K`
captions — with a chapters-only TOC and figures kept with their captions.

Writes ``_tmp/book-builder/`` (YAML + SVGs). The MCP run contract is
``build()``; the canonical fixture ``tests/fixtures/book-composition.fg.yaml``
is this document verbatim.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import (  # noqa: E402
    BookBuilder,
    Camera,
    Chart,
    Frame,
    chevreul,
    canon,
    kerned_spans,
    multiview,
    planar,
    recolor,
    render_page_svgs,
    repeat_along_path,
    serialize,
    stroke_outline,
)
from framegraph.sdk.draw import Scene3D  # noqa: E402

TEAL, RUST, VIOLET, INK, PAPER = ("#0f7d88", "#b5642c", "#7c3aed",
                                  "#1d1e22", "#fcfbf8")

# token fragments harvested from embedded plate documents (the SWOT page,
# the honeycomb page); build() merges them into the book's defs so the
# plates' colour/text-style references resolve inside the book
_PLATE_TOKENS: list = []


def _group(children):
    return {"type": "group", "children": children}


def _swatch_row(colors, y=0, w=34, h=20, gap=6):
    return [{"type": "rect", "box": [i * (w + gap), y, w, h], "fill": c,
             "radius": 3, "decorative": True} for i, c in enumerate(colors)]




def _scaled(objects, s, text_styles=None):
    """Scale plate objects numerically — backend-proof (no transforms):
    boxes, radii, font sizes; token text styles resolved inline from the
    plate's own tokens then scaled. Children are marked decorative — the
    figure's alt text speaks for the plate as a whole."""
    import copy
    out = []
    for obj in objects:
        o = copy.deepcopy(obj)
        if isinstance(o.get("box"), list):
            o["box"] = [v * s for v in o["box"]]
        for key in ("radius",):
            if isinstance(o.get(key), (int, float)):
                o[key] = o[key] * s
        if isinstance(o.get("center"), list):
            o["center"] = [v * s for v in o["center"]]
            for key in ("rx", "ry"):
                if isinstance(o.get(key), (int, float)):
                    o[key] = o[key] * s
        for key in ("from", "to"):
            if isinstance(o.get(key), list):
                o[key] = [v * s for v in o[key]]
        if isinstance(o.get("d"), list):
            o["d"] = [[seg[0], *[v * s for v in seg[1:]]] for seg in o["d"]]
        elif isinstance(o.get("d"), str):
            # expand bakes symbol paths as ABSOLUTE string data (M/L/Z);
            # scale every numeric token — the silent giant-hex trap
            import re
            o["d"] = re.sub(r"-?\d+(?:\.\d+)?",
                            lambda mt: f"{float(mt.group(0)) * s:g}",
                            o["d"])
        style = o.get("style")
        if isinstance(style, str) and text_styles and style in text_styles:
            style = dict(text_styles[style])
        if isinstance(style, dict):
            style = dict(style)
            for key in ("font_size", "letter_spacing", "line_height"):
                # scale truly — a clamp would break the text/box ratio and
                # re-introduce clipping the home document does not have.
                # line_height scales only in its ABSOLUTE-px form (>2);
                # unit ratios are scale-free
                v = style.get(key)
                if isinstance(v, (int, float)) and (key != "line_height"
                                                    or v > 2):
                    style[key] = v * s
            o["style"] = style
        ss = o.get("stroke_style")
        if isinstance(ss, dict) and isinstance(ss.get("stroke_width"),
                                               (int, float)):
            o["stroke_style"] = {**ss, "stroke_width": ss["stroke_width"] * s}
        if o.get("type") == "group" and o.get("children"):
            o["children"] = _scaled(o["children"], s, text_styles)
        else:
            o.setdefault("decorative", True)
        out.append(o)
    return out


# ── chapter bodies ──────────────────────────────────────────────────────


def _ch_column(book):
    ch = book.chapter("The Column")
    ch.para("A page begins as a negotiation between text and silence. The "
            "column takes what it needs to carry a comfortable line — "
            "forty-five to seventy-five characters — and returns the rest "
            "to the margins, where the eye rests between thoughts.")
    ch.para("FrameGraph settles this negotiation deterministically. A flow "
            "section names a master; the master names a canvas; the margins "
            "resolve through an explicit region, a declared margin, or the "
            "Johnston canon — inner one-and-a-half, top two, outer three, "
            "foot four. Nothing is eyeballed, so nothing drifts.")
    ch.section("Measure and rhythm")
    ch.para("The Knuth–Plass engine breaks each paragraph as a whole, "
            "trading tightness across lines instead of committing greedily "
            "to the first fit. Hyphenation follows Liang patterns. The "
            "result is the even grey a book page owes its reader.")
    steps = [round(v, 1) for v in canon.modular_scale(
        11, 1.25, names=["xs", "s", "m", "l", "xl", "xxl"]).values()]
    ch.figure(_group([{"type": "rect",
                       "box": [0, i * 16, s * 6, 12], "fill": TEAL,
                       "decorative": True}
                      for i, s in enumerate(steps)]),
              caption=f"A modular scale (base 11, ratio 1.25): {steps}",
              alt="six bars growing by a constant ratio")
    ch.para("Sizes drawn from one modular scale agree with each other the "
            "way notes of one chord do; the bars above are the scale made "
            "visible, each length six times its font size.")
    ch.para("The proof of a paginator is what it refuses to do: it will "
            "not orphan a heading at a page foot, will not split a kept "
            "figure from its caption, and will not stretch a last line "
            "into a river because the paragraph ended inconveniently. "
            "Refusals are design; the engine's cost function makes them "
            "cheap enough to be invisible.")
    ch.section("Lists and continuation")
    ch.bullet(["The column carries prose.",
               "Lists interrupt it with rhythm, not with noise.",
               "A continuation line hangs beneath its marker."])
    ch.para("Everything on this page is a flowable: paragraphs, headings, "
            "lists, figures. The engine decides where pages end; the "
            "author decides only what must not be separated.")
    ch.section("The canon, briefly")
    ch.para("Edward Johnston taught letterers to divide the page before "
            "touching it: the inner margin one and a half units, the head "
            "two, the outer three, the foot four. The asymmetry is not "
            "decoration — facing pages share their inner silence, and the "
            "thumb needs the outer edge. FrameGraph mirrors the canon "
            "recto and verso, so a spread reads as one object.")
    ch.para("A measure that runs too long tires the return sweep of the "
            "eye; one that runs too short chops the phrase. The forty-five "
            "to seventy-five character band is not taste but physiology, "
            "and the validator can be asked to check it the way it checks "
            "contrast: before ink, not after complaints.")
    ch.para("None of this requires an operator watching a preview. The "
            "same YAML paginates identically on every machine, because "
            "the breaks are chosen by an algorithm with a cost function, "
            "not by a rendering accident. Determinism is what lets a "
            "book carry a test suite.")
    ch.para("What follows is a tour: each chapter takes one capability "
            "family, states what it is for, and proves it with plates "
            "computed by the very functions under discussion. Nothing "
            "was drawn by hand; everything can be re-derived.")
    ch.section("Reading a spread")
    ch.para("Hold two facing pages and the design either resolves or it "
            "does not. The inner margins pool into one channel of "
            "quiet; the outer edges hold the thumbs; the running text "
            "aligns across the gutter because both pages answer to the "
            "same master. A book that only works one page at a time is "
            "a stack of leaflets.")
    ch.para("The verso and recto masters mirror each other, and the "
            "engine tracks the document-global page parity — so a "
            "chapter that opens mid-book still knows which margin is "
            "inner. These are the kinds of facts a template cannot "
            "carry and a layout engine must.")
    return ch


def _ch_line(book):
    ch = book.chapter("The Line")
    ch.para("A stroke is a promise about a pen. The outline engine keeps "
            "that promise in geometry: the centre-line and a width become "
            "a closed filled path, so every backend paints the same body "
            "without knowing anything about pens.")
    ch.figure(stroke_outline([(0, 45), (70, 12), (150, 52), (230, 18),
                              (300, 42)],
                             width=14, join="round", cap="round", fill=TEAL),
              caption="A constant-width stroke, outlined",
              alt="thick teal zigzag as a filled shape")
    ch.section("Width as a voice")
    ch.para("Give the width a profile and the line starts to speak: full "
            "at the attack, tapering to silence. This is the Width tool "
            "as a function of arc length, not a gesture.")
    ch.figure(stroke_outline([(0, 30), (300, 12)], width=22,
                             profile=lambda t: 1.0 - 0.92 * t, fill=RUST),
              caption="A tapered profile, width 22 falling to nothing",
              alt="rust wedge tapering to a point")
    ch.para("Hold a broad nib at thirty degrees and the same machinery "
            "yields calligraphy — thick where the tangent crosses the pen, "
            "thin where it runs along it.")
    ch.figure(stroke_outline([(0, 55), (80, 18), (180, 62), (300, 22)],
                             width=18, pen_angle=30, pen_thin=0.18,
                             smooth=True, join="round", cap="round",
                             fill=INK),
              caption="A calligraphic swash: pen at 30°, thin ratio 0.18",
              alt="black calligraphic swash")
    ch.section("The brush that repeats")
    ch.para("Scatter and pattern brushes are placements, not paint: stamps "
            "laid down by arc length with the tangent's rotation. The dots "
            "below are one ellipse, repeated by rule.")
    ch.figure(_group(repeat_along_path(
        [(0, 40), (100, 10), (200, 55), (300, 20)], spacing=22, smooth=True,
        stamp={"type": "ellipse", "center": [0, 0], "rx": 4, "ry": 4,
               "fill": TEAL, "decorative": True})),
        caption="A scatter brush: one stamp, arc-length spacing",
        alt="teal dots along a curve")
    ch.para("Profiles compose with smoothing: run the centre-line "
            "through the Catmull-Rom interpolator first and the width "
            "function rides the curve, not the polyline. The swash on "
            "the previous plate is exactly that — four knots, one pen "
            "angle, and no hand-tuning anywhere.")
    ch.section("Corners, honestly")
    ch.para("A join is a small theory of what a corner means: miter "
            "insists the two edges meet where they were headed, bevel "
            "concedes the point, round admits a pen was involved. The "
            "engine implements all three and caps to match — and routes "
            "the round cap explicitly through the outward direction, "
            "because at a stroke's end the shorter arc is ambiguous and "
            "the wrong choice bites into the body.")
    ch.para("The deeper point is architectural. Because outlining happens "
            "at author time, the document that leaves the builder contains "
            "only closed filled paths. A PDF engine, a browser, a plotter "
            "— none of them is asked to agree about pens, because the pen "
            "is already gone.")
    ch.figure(stroke_outline([(0, 15), (70, 15), (70, 62), (150, 62),
                              (150, 15), (220, 15)],
                             width=12, join="miter", fill=VIOLET),
              caption="Miter joins keep the promise of the corner",
              alt="violet square-wave stroke with sharp corners")
    return ch


def _ch_plane(book):
    sq = [(0, 0), (70, 0), (70, 70), (0, 70)]
    sq2 = [(35, 35), (105, 35), (105, 105), (35, 105)]
    inner = [(20, 20), (50, 20), (50, 50), (20, 50)]
    ch = book.chapter("The Plane")
    ch.para("Shapes argue; the planar kernel arbitrates. Union, "
            "intersection, difference and division are computed on the "
            "flattened rings and returned as plain even-odd paths — holes "
            "included, no renderer contract touched.")
    ch.figure(planar.to_path(planar.union([sq], [sq2]), fill=TEAL),
              caption="Union: two squares, one body",
              alt="teal union blob")
    ch.figure(planar.to_path(planar.subtract([sq], [inner]), fill=TEAL),
              caption="Difference with a hole — even-odd, natively",
              alt="teal square with a square hole")
    ch.section("Divide and conquer")
    pieces = planar.divide([sq], [sq2])
    ch.figure(_group([planar.to_path(p, fill=c) for p, c in
                      zip(pieces, (TEAL, RUST, VIOLET))]),
              caption="Pathfinder divide: three pieces, three colours",
              alt="three coloured boolean pieces")
    ch.para("Division is the honest version of visual overlap: rather "
            "than stacking translucent shapes and hoping, the kernel "
            "hands you the actual pieces — each one addressable, "
            "fillable, and countable. The atlas of pieces is what makes "
            "Live-Paint style colouring possible downstream.")
    ch.section("Offsets and regions")
    ch.para("An offset grows or shrinks a polygon with miter-true corners "
            "and refuses to lie about collapse. Region filling is the "
            "same boolean algebra pointed inward: every bounded region of "
            "an overlay becomes its own fillable face.")
    base = [(12, 12), (88, 12), (88, 88), (12, 88)]
    ch.figure(_group([planar.to_path(planar.offset_polygon(base, 14),
                                     fill="#d7e6e8"),
                      planar.to_path([base], fill=TEAL),
                      planar.to_path(planar.offset_polygon(base, -14),
                                     fill=PAPER)]),
              caption="Offset rings at ±14, miter corners exact",
              alt="nested offset squares")
    ch.figure(_group([planar.to_path(f, fill=c, stroke=PAPER,
                                     stroke_style={"stroke_width": 1})
                      for f, c in zip(planar.fill_regions([sq, sq2]),
                                      (TEAL, VIOLET, RUST))]),
              caption="Live Paint: each bounded region its own colour",
              alt="three region faces")
    ch.section("Scissors and the knife")
    ch.para("Surgery completes the kit. The scissors split an open path "
            "at an arc-length fraction, exact over corners; the knife is "
            "a boolean in disguise, intersecting the shape with each "
            "half-plane of the cutting line. Both return plain geometry, "
            "and both are deterministic to the digit.")
    halves = planar.cut_along([(0, 0), (90, 0), (90, 66), (0, 66)],
                              (0, 10), (90, 56))
    shifted = [[(x + 8, y + 6) for x, y in ring] for ring in halves[1]]
    ch.figure(_group([planar.to_path(halves[0], fill=TEAL),
                      planar.to_path(shifted, fill=RUST)]),
              caption="The knife: one rectangle, two pieces, pulled apart",
              alt="two knife-cut halves separated")
    ch.para("Degenerate inputs — shared edges, touching corners — are the "
            "graveyard of geometry code. The kernel answers them with a "
            "deterministic nudge that prefers the engaged result, and the "
            "test suite pins the areas it must conserve.")
    return ch


def _ch_colour(book):
    ch = book.chapter("Colour")
    ch.para("Chevreul's law of simultaneous contrast is older than any "
            "screen and still decides whether a page feels calm. The "
            "colour canon encodes it: harmonies computed from the wheel, "
            "palettes closed over duties, contrast checked before ink.")
    guide = chevreul.color_guide(TEAL)
    ch.figure(_group(_swatch_row(guide["scale"], y=0)
                     + _swatch_row(guide["hues"], y=28)
                     + _swatch_row(guide["contrast_of_colours"], y=56)),
              caption="The colour guide for one teal: scale, hues, "
                      "contrast of colours",
              alt="three rows of related swatches")
    ch.section("A palette with duties")
    pal = chevreul.closed_palette(ground=PAPER, ink=INK, accent=RUST).tokens()
    duties = [pal["ground"], pal["ink"], pal["accent"]]
    ch.figure(_group([{"type": "rect", "box": [0, 0, 186, 24],
                       "fill": duties[0], "decorative": True,
                       "stroke": "#d9d3c7",
                       "stroke_style": {"stroke_width": 1}},
                      {"type": "rect", "box": [0, 30, 90, 24],
                       "fill": duties[1], "decorative": True},
                      {"type": "rect", "box": [0, 60, 24, 24],
                       "fill": duties[2], "decorative": True}]),
              caption="Ground, ink, accent — dosed roughly 62 · 30 · 8",
              alt="three duty swatches at decreasing area")
    ch.para("The guide's six rows are not swatch inspiration; they are "
            "functions of one input. Feed the same teal tomorrow and the "
            "same six families return — which is what lets a palette "
            "decision live in version control instead of in somebody's "
            "memory of a Tuesday.")
    ch.section("Recolouring a page")
    ch.para("Recolor is one call over the whole document: token values, "
            "paint literals, gradient stops. The pair below is the same "
            "plate, remapped from rust to violet without touching text.")
    before = [{"type": "rect", "box": [0, 0, 86, 44], "fill": RUST,
               "radius": 5},
              {"type": "rect", "box": [0, 50, 86, 18],
               "fill": {"kind": "linear", "stops": [
                   {"color": RUST, "position": "0%"},
                   {"color": PAPER, "position": "100%"}]}}]
    probe = {"dsl": "FrameGraph", "version": "2.4.1", "title": "p",
             "pages": [{"mode": "page", "id": "p",
                        "layers": [{"id": "m", "objects": before}]}]}
    after = recolor(probe, {RUST: VIOLET})["pages"][0]["layers"][0]["objects"]
    for obj in after:
        obj["box"] = [obj["box"][0] + 110, *obj["box"][1:]]
    ch.figure(_group(before + after),
              caption="recolor({rust → violet}): literals and gradient stops",
              alt="before and after swatch pairs")
    ch.section("Naming the palette")
    ch.para("A colour that reaches the document does so as a token: a "
            "name in one table, referenced everywhere it is used. The "
            "name is the design decision; the hex is an implementation "
            "detail the recolour pass may change wholesale. Plates in "
            "this chapter write literals only because they demonstrate "
            "the machinery beneath the names.")
    ch.para("Tokens also carry the audit trail. When the grey test or "
            "the contrast floor rejects a palette, the finding names a "
            "token, not a coordinate on some page — and fixing the "
            "token fixes every use at once.")
    ch.section("Tone before hue")
    ch.para("Chevreul's sternest test ignores colour entirely: print the "
            "page grey and see whether the hierarchy survives. A palette "
            "that only works in hue collapses for a fifth of readers and "
            "every photocopier. The tone scale below is one teal walked "
            "from paper to ink; any two neighbours are a legible step.")
    ch.figure(_group(_swatch_row(chevreul.tone_scale(TEAL, 8))),
              caption="A tone scale: one hue, eight measured steps",
              alt="eight swatches from light to dark teal")
    ratio = chevreul.contrast_ratio(INK, PAPER)
    ch.para(f"Contrast is arithmetic, not opinion: ink on paper here "
            f"measures {ratio:.1f}:1 against the WCAG floor of 4.5:1 for "
            f"body text. The builder can refuse a palette before a single "
            f"page is set — the cheapest possible accessibility review.")
    return ch


def _ch_style(book):
    ch = book.chapter("Style")
    ch.para("An object's paint need not be a single decision. The "
            "appearance stack paints one geometry several times — fill, "
            "outer stroke, inner stroke — bottom to top, each pass "
            "declaring only what it owns.")
    ch.figure({"type": "rect", "box": [0, 0, 200, 90], "radius": 10,
               "appearance": [{"fill": "#dbeafe"},
                              {"stroke": "#1d4ed8",
                               "stroke_style": {"stroke_width": 8}},
                              {"stroke": "#ffffff",
                               "stroke_style": {"stroke_width": 3}}]},
              caption="Three appearance passes on one rectangle",
              alt="card with double stroke")
    ch.section("Ordered effects")
    ch.para("Effects stack in author order and kinds may repeat: a warm "
            "shadow below, a glow around, a violet counter-shadow above. "
            "The SVG carries the filter chain; browser targets composite "
            "it, the dependency-free proxy declares it faithfully.")
    ch.figure({"type": "rect", "box": [0, 0, 200, 90], "radius": 10,
               "fill": "#dbeafe",
               "effects": [{"kind": "shadow", "dx": 6, "dy": 6, "blur": 8,
                            "opacity": 0.35},
                           {"kind": "glow", "color": "#00b8a9", "blur": 12},
                           {"kind": "shadow", "dx": -3, "dy": -3, "blur": 3,
                            "color": VIOLET, "opacity": 0.4}]},
              caption="An ordered effect stack: shadow, glow, shadow",
              alt="card carrying a filter chain")
    ch.section("The imperfect hand")
    ch.para("Perfection reads as machine; a seeded wobble reads as care. "
            "Humanize perturbs rotation, opacity and stroke weight from "
            "one seed — the same seed always draws the same page.")
    ch.figure(_group([{"type": "rect", "box": [0, 0, 90, 60], "fill": "none",
                       "stroke": INK, "stroke_style": {"stroke_width": 2}},
                      {"type": "rect", "box": [110, 0, 90, 60],
                       "fill": "none", "stroke": INK,
                       "stroke_style": {"stroke_width": 2},
                       "humanize": {"seed": 7, "drift_deg": 2.0,
                                    "weight": 0.35, "opacity": 0.15}}]),
              caption="The same rectangle, clean and humanized (seed 7)",
              alt="a clean and a wobbled rectangle")
    ch.para("Because the wobble is seeded, imperfection becomes a "
            "reviewable property: change the seed and the hand changes; "
            "keep it and every rebuild of this book draws the same "
            "tremor. The golden gate treats humanized pages like any "
            "other — byte-identical until someone means to change them.")
    return ch


def _ch_data(book):
    ch = book.chapter("Data")
    ch.para("A chart is a claim drawn to scale. The chart helpers lower "
            "series onto a frame — domain to box — and emit the same "
            "primitives as everything else, so a figure of data obeys the "
            "same book rules as a figure of ink.")
    frame = Frame(domain=[0, 0, 6, 12], box=[0, 0, 300, 110])
    bars = Chart(frame).bars([(1, 4), (2, 7), (3, 5), (4, 11), (5, 8)],
                             fill=TEAL).axes(x_ticks=range(0, 7, 2),
                                             y_ticks=(0, 6, 12)).objects()
    ch.figure(_group(bars), caption="Bars on a framed domain",
              alt="five teal bars with axes")
    line = Chart(frame).line([(0, 2), (1, 5), (2, 4), (3, 8), (4, 7),
                              (5, 10), (6, 9)], stroke=RUST, width=2,
                             smooth=True).axes(x_ticks=(0, 3, 6),
                                               y_ticks=(0, 6, 12)).objects()
    ch.figure(_group(line), caption="A line series over the same frame",
              alt="rust line chart")
    ch.para("Series compose on one frame the way flowables compose in "
            "one story: the bars and the line above share axes, domain "
            "and box, so their claims can be compared without squinting "
            "at two different rulers.")
    ch.section("Tables in flow")
    ch.para("Tables are flowables: columns, rows, and the engine's box "
            "model. The one below states what each chapter of this book "
            "demonstrates.")
    ch.table(["Chapter", "Capability"],
             [["The Line", "stroke_outline · repeat_along_path"],
              ["The Plane", "planar booleans · offsets · regions"],
              ["Colour", "color_guide · closed_palette · recolor"],
              ["Style", "appearance · effects · humanize"],
              ["Space", "Scene3D extrude · revolve · multiview"]])
    ch.para("Nothing in the table is an image; resize the master and the "
            "columns re-solve like every other line on the page.")
    ch.section("Parts of a whole")
    donut = Chart(Frame(domain=[0, 0, 1, 1], box=[0, 0, 150, 150])).donut(
        [42, 33, 25], colors=[TEAL, RUST, VIOLET],
        labels=["flow", "pages", "plates"])
    ch.figure(_group(donut.objects()),
              caption="A donut of this book's own page budget",
              alt="three-segment donut chart")
    area = Chart(frame).area([(0, 1), (1, 4), (2, 3), (3, 7), (4, 6),
                              (5, 9), (6, 8)], fill="#d7e6e8",
                             stroke=TEAL).axes(x_ticks=(0, 3, 6),
                                               y_ticks=(0, 6, 12)).objects()
    ch.figure(_group(area), caption="An area series: the line, filled",
              alt="teal area chart")
    ch.para("Every mark above shares the coordinate discipline of the "
            "rest of the book: a domain, a box, a deterministic mapping. "
            "A chart that cannot say where its zero sits has no business "
            "on a page that can.")
    return ch


def _ch_space(book):
    ch = book.chapter("Space")
    ch.para("Three dimensions enter the book only as honest projection: a "
            "scene of faces, a camera, and a painter's sort. Extrusion "
            "pulls a polygon into a prism; revolution spins a profile "
            "into a vessel.")
    cam = Camera(eye=(4.0, 3.0, 5.0))
    prism = Scene3D().extrude([(0, 0), (1.4, 0), (1.4, 0.9), (0.7, 1.3),
                               (0, 0.9)], depth=0.8)
    ch.figure(prism.render(camera=cam, box=[0, 0, 240, 150],
                           fill="#d7e6e8", stroke=INK, shading="lambert"),
              caption="An extruded prism, painter-sorted",
              alt="wireframe prism projection")
    vase = Scene3D().revolve([(0.18, 0), (0.5, 0.15), (0.32, 0.7),
                              (0.42, 1.05), (0.25, 1.25)], segments=20)
    ch.figure(vase.render(camera=cam, box=[0, 0, 240, 170],
                          fill="#efe7dc", stroke="#7a6f63",
                          shading="lambert"),
              caption="A profile revolved into a vessel (20 segments)",
              alt="lathe-revolved vase")
    ch.para("Materials shade the faces without pretending to ray-trace: "
            "a Lambert term against a declared light, ambient floor "
            "beneath it, painter-sorted. The vase's roundness is twenty "
            "flat quadrilaterals telling one coordinated lie — which is "
            "all drawing has ever been.")
    ch.section("Every view at once")
    ch.para("Engineering asks for agreement between views. Multiview "
            "renders front, top, side and isometric panels of one scene "
            "in a single grid — four claims, one geometry, no chance for "
            "the views to drift apart because they are projections of "
            "the same faces.")
    ch.figure(multiview(prism, box=[0, 0, 300, 220]),
              caption="Multiview of the prism: front, top, side, isometric",
              alt="four orthographic panels of one prism")
    ch.para("The painter's algorithm sorts faces by depth per view; the "
            "projection is honest about being a drawing, not a model. "
            "For the cases where a true kernel is needed, the roadmap "
            "keeps its non-goals written down.")
    return ch


def _ch_letter(book):
    ch = book.chapter("The Letter")
    ch.para("Typography's smallest unit is a pair. The space between A "
            "and V is not the space between A and B, and a page set "
            "without kerning quietly announces that nobody looked. The "
            "metrics module reads the resolved font's kern table when "
            "fontTools is present, and accepts explicit pairs when it "
            "is not — both paths emit grammar-native spans.")
    ch.figure({"type": "group", "children": [
        {"type": "text", "box": [0, 0, 300, 34], "text": "WAVY TAVERN",
         "style": {"font_family": ["DejaVu Sans"], "font_size": 26,
                   "font_weight": 700, "color": "#9aa0a8",
                   "white_space": "nowrap"}},
        {"type": "text", "box": [0, 40, 300, 34],
         "style": {"font_family": ["DejaVu Sans"], "font_size": 26,
                   "font_weight": 700, "color": INK,
                   "white_space": "nowrap"},
         "spans": kerned_spans("WAVY TAVERN",
                               pairs={("W", "A"): -3.0, ("A", "V"): -2.6,
                                      ("V", "Y"): -2.2, ("V", "E"): -1.4})},
    ]}, caption="Untouched above, pair-kerned below",
        alt="the same words with and without kerning")
    ch.section("Measure before ink")
    ch.para("The same module answers the question every absolute layout "
            "asks eventually: how wide is this string, and how tall will "
            "it stand once wrapped? Boxes sized by measurement instead of "
            "guesswork are what keep the containment gates green across "
            "this entire corpus.")
    ch.para("Where the measuring engine and the drawing engine disagree — "
            "different font, different host — the layout must scream, and "
            "it does: silent substitution is banned by decision record, "
            "and the font-pack tooling pins the faces so measure equals "
            "render on any machine.")
    ch.para("The pipeline runs both directions. A portable font pack "
            "carries the exact faces with their fingerprints; the "
            "renderer installs it before the first glyph is measured; "
            "and a face the pack cannot supply is a loud build error "
            "carrying the pack digest — never a lookalike substituted "
            "in silence.")
    ch.para("Typography at this altitude is bookkeeping, and that is "
            "praise: kerning tables, advance widths, wrap points and "
            "line boxes are all just numbers, and numbers can be "
            "gated. The craft is deciding which numbers matter; the "
            "machine holds them steady afterwards.")
    return ch


def _ch_pattern(book):
    ch = book.chapter("The Pattern")
    ch.para("Most slides are not designed; they are re-derived. The "
            "pattern catalog absorbs that truth: three hundred and "
            "seventy-five typed layouts, each declaring its zones, its "
            "size vocabulary and the shape of content it accepts. A fill "
            "is validated before any geometry is computed — layout never "
            "runs on unchecked content.")
    from framegraph.patterns import compose
    swot = compose(10, {
        "strengths": ["Deterministic", "Typed model"],
        "weaknesses": ["Proxy fonts"],
        "opportunities": ["Corpus growth"],
        "threats": ["Silent loss"]})
    _PLATE_TOKENS.append(swot["defs"]["tokens"])
    plate = _group(_scaled([o for layer in swot["pages"][0]["layers"]
                            for o in layer["objects"]], 0.15))
    ch.figure(plate,
              caption="Pattern 010, the SWOT quadrant, composed and "
                      "scaled onto this page",
              alt="miniature SWOT slide")
    ch.section("A library with opinions")
    ch.para("Above the catalog sits the content library: seven consulting "
            "house styles as ready token fragments, symbol packs for "
            "covers and agendas, and two data-driven generators. The "
            "honeycomb below is a generator's whole output — one data "
            "dict in, one page out — reduced to a plate.")
    from framegraph.library import honeycomb_capability_map
    honey = honeycomb_capability_map({
        "title": "A pocket honeycomb", "columns": [
            {"header": "Flow", "items": [
                {"label": "Pages"}, {"label": "Breaks"}]},
            {"header": "Plates", "items": [
                {"label": "Booleans"}, {"label": "Outlines",
                                        "variant": "extended"}]},
            {"header": "Colour", "items": [
                {"label": "Harmonies"}, {"label": "Recolor",
                                         "variant": "future"}]},
        ]})
    _PLATE_TOKENS.append({"colors": honey["defs"]["tokens"]["colors"]})
    honey_styles = honey["defs"]["tokens"].get("text_styles") or {}
    ch.figure(_group(_scaled([o for layer in honey["pages"][0]["layers"]
                              for o in layer["objects"]], 0.42,
                             honey_styles)),
              caption="The honeycomb generator, fed three columns",
              alt="miniature honeycomb capability map")
    ch.para("Both plates obey the book's figure discipline: numbered, "
            "captioned, kept with their captions, and sized from their "
            "declared geometry. A generator's page is just another "
            "object once it is in the story.")
    ch.section("A hub and its satellites")
    from framegraph.library import module_hub_radial
    hub = module_hub_radial({
        "title": "A pocket module map",
        "hub": {"id": "core", "label": "Core", "position": [400, 420],
                "size": 110, "icon": "none",
                "outline_color": "#7c3aed"},
        "satellites": [
            {"id": "a", "label": "Flow", "position": [180, 260],
             "size": 60, "icon": "none", "label_anchor": "above"},
            {"id": "b", "label": "Plates", "position": [640, 250],
             "size": 60, "icon": "none", "label_anchor": "above"},
            {"id": "c", "label": "Colour", "position": [620, 610],
             "size": 60, "icon": "none", "label_anchor": "below"},
            {"id": "d", "label": "Gates", "position": [190, 600],
             "size": 60, "icon": "none", "label_anchor": "below"}],
        "edges": [{"from": "core", "to": t} for t in "abcd"]})
    _PLATE_TOKENS.append({"colors": hub["defs"]["tokens"]["colors"]})
    hub_styles = hub["defs"]["tokens"].get("text_styles") or {}
    ch.figure(_group(_scaled([o for layer in hub["pages"][0]["layers"]
                              for o in layer["objects"]], 0.26,
                             hub_styles)),
              caption="The radial module generator: one hub, four "
                      "satellites, edges beneath",
              alt="miniature hub-and-spoke module map")
    ch.para("Three generators, three grammars of arrangement — grid, "
            "tessellation, radial — and none of them asked the author "
            "for a single coordinate.")
    ch.para("Each plate is the generator's own output, rescaled by "
            "plain arithmetic — symbol frames, path data and text "
            "styles all multiplied by one factor, so what this book "
            "embeds is exactly what the generator computed, smaller.")
    return ch


def _ch_corpus(book):
    ch = book.chapter("The Corpus")
    ch.para("A format earns trust by carrying other people's documents. "
            "The migration path lifts the predecessor dialect in one "
            "command, and the corners it learned are recorded as a "
            "mapping table — each one found by migrating a real "
            "production deck, not by speculation.")
    ch.table(["v0.1 dialect", "v2 lift"],
             [["scene / visual envelope", "one page + defs.tokens"],
              ["deck / slides envelope", "defs + one page per slide"],
              ["text styles (font, size, wrap)", "font_family, font_size, "
               "white_space"],
              ["chip_row component", "a group of pills, baked"],
              ["gradient fill tokens", "v2 Gradient paints that render"]])
    ch.section("What the oracle taught")
    ch.para("The strongest lesson came from the golden corpus itself: a "
            "deck cover had rendered near-black since the day it was "
            "pinned, because a declared gradient token was never "
            "dereferenced by the renderer. The migration work found the "
            "silent failure, the fix lit the cover purple, and the "
            "golden lock was re-pinned with open eyes.")
    ch.para("Every migrated deck is verified page-by-page against the "
            "predecessor's own renderer — content identical, wrap points "
            "and font faces honestly different, and a hard rule enforced "
            "throughout: nothing is ever silently truncated. Overflow "
            "must be explicit policy or it is a build error.")
    ch.para("The corpus now holds thirty-eight fixtures, every one "
            "validating clean, every one rendered by the gate on every "
            "commit. A book like this joins them the moment it is "
            "committed: the page you are reading is a test asset.")
    ch.para("Two decks remain outside, waiting on a dependency the "
            "checklist names honestly: their diagrams speak the UML "
            "dialect, and the composers that understand it have not yet "
            "crossed over from the predecessor. When they do, the same "
            "one-command lift is already waiting.")
    return ch


def _ch_gate(book):
    ch = book.chapter("The Gate")
    ch.para("Everything in this volume is claimed twice: once by the "
            "prose, once by a test. The gate runs twelve checks on every "
            "commit — schema against model, grammar against schema, "
            "fixtures against the validator, renders against a golden "
            "lock — and a chapter that breaks any of them does not ship.")
    ch.para("The discipline has a name in this repository: no output is "
            "trusted until it is checked against a real gate. Rendered "
            "pixels outrank YAML; a numbered caption is not delivered "
            "until it is seen on a page; a silent truncation is a build "
            "error, not a style choice.")
    ch.section("The grey test")
    ch.para("The oldest gate is Chevreul's: drain the hue and see if the "
            "page still speaks. Below, one working palette and its grey "
            "shadow — the hierarchy must survive the crossing or the "
            "palette is leaning on colour it does not own.")
    palette = [TEAL, RUST, VIOLET, INK]
    ch.figure(_group(_swatch_row(palette, y=0)
                     + _swatch_row([chevreul.to_grey(c) for c in palette],
                                   y=28)),
              caption="A palette and its grey test, computed",
              alt="colour swatches above their grey equivalents")
    ch.para("A book is a promise held over hundreds of decisions. The "
            "gates keep the promise cheap: nobody re-reads every page "
            "after every change, because the machine already has.")
    ch.section("What a gate cannot see")
    ch.para("Honesty requires the inverse list. A gate cannot tell you "
            "whether a sentence is worth reading, whether a plate earns "
            "its page, or whether the tone of a chapter matches its "
            "subject. It can only hold the ground so those judgements "
            "are made once, by a person, and never silently unmade by "
            "a regression.")
    ch.para("So the division of labour stands: the machine guards "
            "measure, contrast, containment, determinism and provenance; "
            "the author owns meaning. Neither can do the other's job, "
            "and the book is better because neither tries.")
    return ch


def _ch_book(book):
    ch = book.chapter("The Book")
    ch.para("This volume assembled itself. Chapters numbered their own "
            "headings, figures counted themselves per chapter and folded "
            "their labels into captions, and the contents page resolved "
            "its numbers from the paginated result.")
    ch.section("The whole surface in one builder")
    ch.code("""book = BookBuilder(title="On Composition", author="…")
ch = book.chapter("The Line")
ch.para("A stroke is a promise about a pen…")
ch.figure(stroke_outline(pts, width=18, pen_angle=30),
          caption="A calligraphic swash")     # -> Figure 2.3
doc = book.build()                            # validated flow document""",
            language="python")
    ch.numbered(["Front matter carries identity, never a chapter number.",
                 "A figure without a box still reserves its true height.",
                 "The book never lists itself in its own contents."])
    ch.section("From builder to shelf")
    ch.para("The path from these calls to a bound object is short and "
            "entirely inspectable. The builder returns a document; the "
            "document validates against the model; the flow engine "
            "paginates it; the SVG pages assemble into a vector PDF or "
            "transpile to LaTeX for a press that prefers TeX. Each stage "
            "is a function with a test, not a menu with a mood.")
    ch.para("Nothing in that chain is exotic. The same builders that "
            "made this book make slide decks, diagrams, letters and "
            "posters; the book layer is only an opinion about numbering "
            "and front matter expressed over the common flowables.")
    ch.bullet(["One source, every artifact derived.",
               "One paginator, every backend downstream.",
               "One test suite, every page accounted for."])
    ch.para("If a page of this volume ever renders differently on your "
            "machine, that difference is a bug with a reproduction — "
            "the book itself is the test case.")
    ch.section("What the reader never sees")
    ch.para("Under every page: a validated document, a deterministic "
            "paginator, margins from a hundred-year-old canon, and a "
            "test suite that reads the pixels. The craft is old; the "
            "guarantees are new.")
    ch.para("The same surface is reachable over MCP: an agent connects, "
            "reads the capability guide, and authors through the identical "
            "builders — with coverage gates that fail the build if a new "
            "capability ever ships without appearing in that guide.")
    ch.para("Colophon: composed by framegraph.sdk.book on an A5 master, "
            "set with the ADR-0003 flow engine, every plate computed by "
            "the capability it depicts.")
    return ch


def build():
    """MCP contract: the eight-chapter capability-tour book."""
    book = BookBuilder(title="On Composition",
                       author="FrameGraph Press", lang="en")
    _PLATE_TOKENS.clear()
    for builder in (_ch_column, _ch_line, _ch_plane, _ch_colour,
                    _ch_style, _ch_data, _ch_space, _ch_letter,
                    _ch_pattern, _ch_corpus, _ch_gate, _ch_book):
        builder(book)
    doc = book.build()
    tokens = doc.setdefault("defs", {}).setdefault("tokens", {})
    for fragment in _PLATE_TOKENS:
        for section, entries in fragment.items():
            tokens.setdefault(section, {}).update(
                {k: v for k, v in entries.items()
                 if k not in tokens.get(section, {})})
    from framegraph.sdk.model import validate_document
    validate_document(doc)
    return doc


def main() -> int:
    out = os.path.join(ROOT, "_tmp", "book-builder")
    os.makedirs(out, exist_ok=True)
    doc = build()
    with open(os.path.join(out, "book.fg.yaml"), "w", encoding="utf-8") as fh:
        fh.write(serialize(doc))
    svgs = render_page_svgs(doc, base_dir=out)
    for i, svg in enumerate(svgs, 1):
        with open(os.path.join(out, f"page-{i:02d}.svg"), "w",
                  encoding="utf-8") as fh:
            fh.write(svg)
    print(f"Wrote the {len(svgs)}-page book to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
