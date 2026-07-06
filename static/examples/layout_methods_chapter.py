#!/usr/bin/env python3
"""*Layout Methods — A Field Guide* as a native FrameGraph ``mode: flow`` book.

This is the typesetting-parity probe: instead of hand-rolling LaTeX, the whole
chapter is authored as ONE FrameGraph flow document — headings, rich paragraphs,
lists, real display **math**, code, tables, a bibliography, and the fourteen
plates as ``figure`` flowables — then lowered to LaTeX by the project's own
backend (``framegraph.rendering.infrastructure.latex``), where **TeX owns
pagination, hyphenation, microtype, float placement and math**. The plates are
not external images: each is a FrameGraph object graph that the backend emits as
native vector **TikZ**.

    uv run python _tmp/render_chapter_native.py     # transpile + compile

The module exposes ``build() -> DocumentBuilder`` (the MCP/run contract) and the
``DOC``/``story`` for the renderer to transpile.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
sys.path.insert(0, HERE)
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

from framegraph.sdk import DocumentBuilder, cite, ref  # noqa: E402
import layout_methods_figures as plates     # noqa: E402

INK = "#1F2530"
ACCENT = "#3F4168"
MUTE = "#5B6573"

# --------------------------------------------------------------------------- #
# Flowable constructors (plain model dicts — the SDK validates them on build).
# --------------------------------------------------------------------------- #
_INLINE = re.compile(
    r"(`[^`]+`|\$[^$]+\$|\*\*[^*]+\*\*|\*[^*]+\*"
    r"|\{(?:ref|pageref|nameref|cite):[^}]+\})")
_REF_SHOW = {"ref": None, "pageref": "page", "nameref": "title"}


def _spans(text):
    """Lower inline `code`, $math$, **bold**, *italic*, and the cross-reference /
    citation extension ({ref:id} {pageref:id} {nameref:id} {cite:key}) to model
    inline values. Emphasis rides a Span style (→ \\textbf / \\textit); the refs
    and cite are built with the SDK helpers and resolve to \\ref / \\pageref /
    \\nameref / \\cite."""
    parts = []
    for tok in _INLINE.split(text):
        if tok == "":
            continue
        if tok.startswith("`"):
            parts.append({"kind": "code", "text": tok[1:-1]})
        elif tok.startswith("$"):
            parts.append({"kind": "math", "tex": tok[1:-1]})
        elif tok.startswith("{"):
            kind, _, target = tok[1:-1].partition(":")
            parts.append(cite(target) if kind == "cite"
                         else ref(target, show=_REF_SHOW[kind]))
        elif tok.startswith("**"):
            parts.append({"text": tok[2:-2], "style": {"font_weight": 700}})
        elif tok.startswith("*"):
            parts.append({"text": tok[1:-1], "style": {"font_style": "italic"}})
        else:
            parts.append(tok)
    return parts


def P(text, *, style=None):
    spans = _spans(text)
    if len(spans) == 1 and isinstance(spans[0], str):
        fl = {"type": "paragraph", "text": spans[0]}
    else:
        fl = {"type": "paragraph", "spans": spans}
    if style:
        fl["style"] = style
    return fl


def H(level, text, *, id=None):
    fl = {"type": "heading", "level": level, "text": text}
    if id:
        fl["id"] = id
    return fl


def LIST(items, *, ordered=False):
    return {"type": "list", "ordered": ordered,
            "items": [{"spans": _spans(it)} for it in items]}


def CODE(src):
    return {"type": "code", "source": src.strip("\n")}


def MATH(tex, *, number=None, id=None):
    fl = {"type": "math", "tex": tex}
    if number:
        fl["number"] = number
    if id:
        fl["id"] = id
    return fl


def TABLE(header, rows, *, caption=None):
    fl = {"type": "table", "header": header, "rows": rows}
    if caption:
        fl["caption"] = caption
    return fl


def SP(h=8):
    return {"type": "spacer", "height": h}


PAGE_BREAK = {"type": "page_break"}


def FIG(fig_id, number, caption, *, id=None):
    """Embed a standalone plate as a figure flowable → native TikZ."""
    fn = dict(plates.FIGURES)[fig_id]
    tmp = DocumentBuilder()
    h = fn(tmp)
    page = tmp._doc["pages"][-1]
    objs = [{**o, "decorative": True}
            for layer in page.get("layers", [])
            for o in layer.get("objects", [])]
    group = {"type": "group", "box": [0, 0, plates.W, h], "children": objs}
    # The LaTeX backend now numbers figures via \caption ("Figure N:"), so the
    # caption carries only the descriptive text — no hand-typed "Figure N —".
    return {"type": "figure", "object": group, "size": [plates.W, h],
            "align": "center", "caption": caption,
            **({"id": id} if id else {})}


# --------------------------------------------------------------------------- #
# The chapter story.
# --------------------------------------------------------------------------- #
def story():
    s = []

    s += [
        H(1, "Layout Methods — A Field Guide"),
        P("A field guide written to one reader — the author of FrameGraph's "
          "architecture map. Fourteen plates illustrate it; each is a single "
          "FrameGraph page, and so is the book around them. This edition is itself "
          "a FrameGraph flow document, lowered to LaTeX so that TeX owns the "
          "pagination, line-breaking, float placement and math."),
        {"type": "toc", "leader": "."},
        SP(10),
        {"type": "toc", "of": "figures"},      # a real list of (numbered) figures
        PAGE_BREAK,
    ]

    # §0
    s += [
        H(2, "0. Where your example actually sits", id="sec-absolute"),
        P("Your map uses **absolute placement**. Every visual object is given "
          "explicit `[x, y, w, h]` pixel coordinates, and the two helpers that "
          "look like layout primitives are really just *coordinate arithmetic*:"),
        CODE(
            "def node(page, box, palette, title, ..., subs, ...):\n"
            "    x, y, w, h = box\n"
            "    page.rect([x, y, w, h], ...)                 # the box itself\n"
            "    page.text([x + 14, y + 9, w - 26, 17], title)  # padding\n"
            "    for i, line in enumerate(subs):\n"
            "        page.text([x + 14, y + 30 + i * 14, ...], line)  # vstack"),
        FIG("fig-00-absolute", 1, "Absolute placement, dissected. A single "
            "hand-placed node already carries an implicit box model and an "
            "implicit vertical flow.", id="fig-absolute"),
        P("Two things recur all the way up the abstraction ladder:"),
        LIST([
            "You already have a box model. `x + 14` / `w - 26` are padding; the "
            "inner content rectangle is `[x+14, y+9, w-26, h-...]`.",
            "You already have flow. `y + 30 + i*14` is a vertical stack with a "
            "fixed line advance of 14px. These are vstacks and grids — you compute "
            "their offsets by hand.",
        ]),
        P("For a small, curated, semantically-arranged diagram, absolute placement "
          "is the correct method, not a deficiency. Automatic graph layout "
          "({nameref:sec-graph}) would "
          "actively destroy your intentional grouping. The value of the other "
          "methods is to compute the offsets you now hard-code, and to know when "
          "curation stops paying off and a solver should take over."),
        TABLE(
            ["Property", "Absolute placement (your file)"],
            [["Control", "Total — pixel-exact"],
             ["Effort", "O(elements) of manual arithmetic"],
             ["Adapts to size", "No — magic numbers go stale"],
             ["Right when", "Small, fixed, hand-curated diagrams"],
             ["Wrong when", "Content or count is dynamic"]],
            caption="When absolute placement is the right tool."),
    ]

    # §1
    s += [
        H(2, "1. The layout problem, stated once", id="sec-problem"),
        P("Given a set of objects, each with a desired size and a set of relations "
          "among them, assign every object a final position and size such that the "
          "constraints are satisfied — or, if they cannot all be satisfied, such "
          "that a stated objective is minimized."),
        FIG("fig-01-ladder", 2, "The ladder of layout methods. Climbing a rung "
            "trades manual control for the machine inferring positions from "
            "higher-level intent.", id="fig-ladder"),
        P("Every method is a different answer to two questions. Who computes the "
          "coordinates — you, by formula, or a solver, from declared relations? "
          "And what is optimized — nothing, a local packing rule, a global cost, "
          "or a feasibility region? Your SDK already embodies this: `sdk.expand` "
          "lowers high-level builders to the model. Layout primitives are the same "
          "move applied to coordinates."),
    ]

    # §2
    s += [
        H(2, "2. Box model — the first abstraction over absolute", id="sec-box"),
        P("The box model turns four nested rectangles — margin, border, padding, "
          "content — into named space. For a box at outer `[x, y, w, h]` with "
          "padding `p`:"),
        MATH(r"\mathrm{content} = [\,x+p,\; y+p,\; w-2p,\; h-2p\,]"),
        FIG("fig-02-box-model", 3, "margin → border → padding → content. The "
            "content rectangle is a single inset of the outer box; the SDK ships "
            "it as `layout.inset()`.", id="fig-box"),
        P("Your `node()` is a box model with asymmetric padding. Formalizing it "
          "removes the magic numbers:"),
        CODE(
            "function content(box: Box, p: Insets): Box {\n"
            "  return {\n"
            "    x: box.x + p.left,\n"
            "    y: box.y + p.top,\n"
            "    w: box.w - p.left - p.right,\n"
            "    h: box.h - p.top - p.bottom,\n"
            "  };\n"
            "}"),
    ]

    # §3
    s += [
        H(2, "3. Flow layout — 1D document flow + line breaking", id="sec-flow"),
        P("Flow places objects one after another along a writing axis, wrapping "
          "when the line is full. Real text flow adds line breaking, in two "
          "regimes. **Greedy (first-fit)** puts as many words on a line as fit, "
          "then breaks — simple, local, fast."),
        CODE(
            "function greedyWrap(words, maxWidth, measure, spaceWidth) {\n"
            "  const lines = []; let line = []; let width = 0;\n"
            "  for (const w of words) {\n"
            "    const ww = measure(w);\n"
            "    const advance = line.length === 0 ? ww : spaceWidth + ww;\n"
            "    if (width + advance > maxWidth && line.length > 0) {\n"
            "      lines.push(line); line = [w]; width = ww;\n"
            "    } else { line.push(w); width += advance; }\n"
            "  }\n"
            "  if (line.length) lines.push(line);\n"
            "  return lines;\n"
            "}"),
        P("**Optimal (Knuth–Plass)** {cite:knuth1981} minimizes a global cost over the whole paragraph: "
          "a per-line badness from how far the glue must stretch, plus demerits, "
          "solved as a shortest path by dynamic programming. This is the algorithm "
          "in TeX — and it is laying out this very paragraph."),
        FIG("fig-03-line-breaking", 4, "Greedy fills each line locally and leaves "
            "ragged space; Knuth–Plass minimises a global cost to balance the "
            "whole paragraph.", id="fig-linebreak"),
        P("The shape of the cost (constants are TeX-specific):"),
        MATH(r"r = \frac{\mathrm{desired}-\mathrm{natural}}{\mathrm{stretch\ or\ "
             r"shrink}}, \qquad b \approx 100\,|r|^{3}, \qquad "
             r"\text{total} = \sum (\,\ell + b\,)^{2}\ \xrightarrow{\ \mathrm{DP}\ }\ \min"),
        P("Greedy is right for labels, captions and single-pass UI text; "
          "Knuth–Plass when justified, print-quality multi-line typography "
          "matters — print, PDF, and the flow-mode pagination your map flags as "
          "its weaker paradigm. Naive pagination is greedy flow without the global "
          "objective."),
    ]

    # §4
    s += [
        H(2, "4. Stack / linear layout — Flexbox", id="sec-flex"),
        P("Flexbox distributes leftover space along one axis. Each item has a "
          "`flex-basis`, a `flex-grow` (share of surplus) and a `flex-shrink` "
          "(share of deficit):"),
        MATH(r"\mathrm{free} = C - \sum_i b_i, \qquad "
             r"s_i = b_i + \frac{g_i}{\sum_j g_j}\,\mathrm{free}\ \ (\mathrm{free}\ge 0)"),
        FIG("fig-04-flexbox", 5, "The free space after summing the bases is shared "
            "out in proportion to each item's grow; shrink is the symmetric rule "
            "for a deficit.", id="fig-flex"),
        P("The shrink factor is weighted by the basis so larger items give up more "
          "absolute space. The single pass is the mental model; the real algorithm "
          "clamps to min/max-content and freezes clamped items, then "
          "redistributes — an iterative loop. Your gate list, legend and tension "
          "band are all fixed-stride vstacks: a flex column with gap and no grow."),
    ]

    # §5
    s += [
        H(2, "5. Grid / table layout (2D)", id="sec-grid"),
        P("Grid generalizes flex to two axes: tracks sized as fixed px, content, "
          "or a fraction of leftover space. Resolving track positions once sizes "
          "are known is exactly what your `gen_rows` does by hand:"),
        MATH(r"o_i = \mathrm{start} + \sum_{j<i} (\,s_j + \mathrm{gap}\,)"),
        FIG("fig-05-grid", 6, "A single-column grid is what `gen_rows` writes out "
            "by hand: trackOffsets(6 × 42, gap 8, start 124) reproduces the "
            "hard-typed y values exactly.", id="fig-grid"),
        P("Your six cards — height 42, gap 8, start 124 — give "
          "`[124, 174, 224, 274, 324, 374]`, identical to your hand-typed values. "
          "A grid primitive would emit those from (count, rowHeight, gap, start), "
          "and a seventh view would cost zero arithmetic."),
    ]

    # §6
    s += [
        H(2, "6. Constraint-based layout (Cassowary)", id="sec-constraints"),
        P("Instead of computing coordinates, you declare relationships and a "
          "solver finds positions that satisfy them — the model behind Apple's "
          "Auto Layout. Constraints carry strengths: required must hold; "
          "strong / medium / weak resolve remaining slack. The solver maintains "
          "the solution incrementally, so editing one constraint re-solves "
          "cheaply."),
        FIG("fig-06-constraints", 7, "Strengths order the solve; the solver "
            "maintains the solution incrementally.", id="fig-constraints"),
        P("Where it helps your map: the brittle parts are relationships encoded as "
          "coincident magic numbers. A constraint engine lets you say “centered, "
          "≥16px gaps, equal width” once; resize the page and it re-solves. For a "
          "static export that cost is rarely worth it — for a resizable canvas, it "
          "is."),
    ]

    # §7
    s += [
        H(2, "7. Graph & diagram layout", id="sec-graph"),
        P("Your artifact is a node-and-edge graph, so this family deserves the "
          "most attention. The defining shift: positions are produced by an "
          "algorithm reading the graph structure, not by you reading a ruler."),
        H(3, "7a. Tree layout — Reingold–Tilford / Walker / Buchheim"),
        P("For a tree: nodes at equal depth share a line; a parent is centered "
          "over its children; isomorphic subtrees are drawn identically. "
          "Reingold–Tilford achieves this in linear time using contours, shifting "
          "siblings apart only as far as their facing silhouettes require."),
        FIG("fig-07a-tree", 8, "Each parent is centred over its children; the "
            "dashed contours are the subtree silhouettes the algorithm walks.",
            id="fig-tree"),
        H(3, "7b. Layered / hierarchical layout — Sugiyama; Graphviz dot"),
        P("For a directed acyclic graph with a sense of flow — which is what your "
          "map is — the Sugiyama framework is standard:"),
        LIST([
            "Cycle removal — reverse a minimal set of edges to make the graph acyclic.",
            "Layer assignment — rank nodes so edges point one way.",
            "Crossing minimization — order within layers (median / barycenter heuristic).",
            "Coordinate assignment — straighten edges, route through dummy nodes.",
        ], ordered=True),
        FIG("fig-07b-sugiyama", 9, "Assign nodes to ranks, then order within each "
            "rank to minimise crossings. It optimises a geometric objective — not "
            "the semantic placement a hand-curated map encodes.", id="fig-sugiyama"),
        H(3, "7c. Force-directed — Eades; Fruchterman–Reingold; Kamada–Kawai"),
        P("When the graph has no hierarchy, simulate physics: nodes repel, edges "
          "pull like springs, the system relaxes toward low energy. "
          "Fruchterman–Reingold {cite:fr1991}, with ideal edge length `k`:"),
        MATH(r"f_a(d) = \frac{d^{2}}{k}, \qquad f_r(d) = -\frac{k^{2}}{d}, "
             r"\qquad k = C\sqrt{\tfrac{\mathrm{area}}{|V|}}"),
        P("Kamada–Kawai {cite:kk1989} instead minimizes a stress energy over graph-theoretic "
          "distances, so geometric distance tracks graph distance:"),
        MATH(r"E = \sum_{i<j} \frac{1}{d_{ij}^{2}}\,\bigl(\lVert p_i - p_j\rVert - "
             r"d_{ij}\bigr)^{2}"),
        FIG("fig-07c-force", 10, "Edges act as springs while every node pair "
            "repels; Barnes–Hut makes the repulsion step tractable at scale.",
            id="fig-force"),
        H(3, "7d. Edge routing"),
        P("Independent of node placement: edges can be straight, orthogonal "
          "(Manhattan), or splines through obstacle-avoiding control points (what "
          "`dot` produces). Automation removes the manual collision checking you "
          "do by eye."),
        FIG("fig-07d-edge-routing", 11, "The same two endpoints can be wired "
            "straight, orthogonally, or as an obstacle-avoiding spline.",
            id="fig-edges"),
    ]

    # §8
    s += [
        H(2, "8. Space-filling layout (treemaps, packing)", id="sec-space"),
        P("To show quantity by area inside a bounded region, use space-filling "
          "methods. **Treemaps** map a hierarchy to nested rectangles whose areas "
          "encode a value; *squarified* treemaps {cite:bruls2000} greedily keep each cell close to "
          "square, because near-square cells are easier to compare."),
        FIG("fig-08-treemap", 12, "Slice-and-dice produces hard-to-compare "
            "slivers; squarified treemaps keep each cell close to square. Both "
            "encode the same eight values.", id="fig-treemap"),
    ]

    # §9
    s += [
        H(2, "9. Choosing a method", id="sec-choose"),
        TABLE(
            ["Situation", "Method", "§"],
            [["Small, fixed figure", "Absolute + box model", "2"],
             ["Wrapping caption text", "Greedy flow", "3"],
             ["Justified quality text", "Knuth–Plass", "3"],
             ["Distribute on one axis", "Flexbox", "4"],
             ["Align across two axes", "Grid / table", "5"],
             ["Resizable, relational", "Constraints", "6"],
             ["Strict hierarchy", "Tree (Reingold–Tilford)", "7a"],
             ["Directed flow / DAG", "Layered (Sugiyama)", "7b"],
             ["Network, no hierarchy", "Force-directed", "7c"],
             ["Quantity by area", "Treemap / packing", "8"]],
            caption="Name the structure, pick the algorithm."),
        FIG("fig-09-decision", 13, "If you can name the structure, use the matching "
            "algorithm; if the value is human curation, stay absolute and borrow "
            "the cheap parts.", id="fig-decision"),
    ]

    # §10
    s += [
        H(2, "10. One concrete rung up for FrameGraph", id="sec-rung"),
        P("You do not need a constraint solver or a Sugiyama engine. The "
          "highest-value, lowest-risk improvement is a thin layout-primitive layer "
          "that lowers to the absolute coordinates you already emit — mirroring "
          "how `sdk.expand` lowers builders into the model:"),
        CODE(
            "def vstack(page, origin, items, gap, render_item):\n"
            "    x, y = origin\n"
            "    for it in items:\n"
            "        h = render_item(page, x, y, it)   # height consumed\n"
            "        y += h + gap\n"
            "\n"
            "def grid_offsets(start, count, cell, gap):\n"
            "    return [start + i * (cell + gap) for i in range(count)]"),
        FIG("fig-10-lowering", 14, "A thin primitive layer compiles author-level "
            "intent down to the absolute coordinates the renderer already "
            "consumes.", id="fig-lowering"),
        P("This keeps absolute mode as the compile target — so the golden SHA-256 "
          "page locks still hold — removes the brittle arithmetic, and makes "
          "content-count changes free (Figure {ref:fig-lowering}, p. {pageref:fig-lowering}). Author high, "
          "lower to a single canonical representation, render that."),
    ]

    # References
    s += [
        {"type": "bibliography", "title": "References", "entries": [
            {"id": "knuth1981", "text": "Knuth, D. E., & Plass, M. F. (1981). "
             "Breaking Paragraphs into Lines. Software: Practice and Experience, 11(11)."},
            {"id": "rt1981", "text": "Reingold, E. M., & Tilford, J. S. (1981). "
             "Tidier Drawings of Trees. IEEE Trans. Software Engineering, SE-7(2)."},
            {"id": "buchheim2002", "text": "Buchheim, C., Junger, M., & Leipert, S. "
             "(2002). Improving Walker's Algorithm to Run in Linear Time. GD 2002."},
            {"id": "sugiyama1981", "text": "Sugiyama, K., Tagawa, S., & Toda, M. "
             "(1981). Methods for Visual Understanding of Hierarchical System "
             "Structures. IEEE Trans. SMC, 11(2)."},
            {"id": "fr1991", "text": "Fruchterman, T. M. J., & Reingold, E. M. "
             "(1991). Graph Drawing by Force-Directed Placement. Software: "
             "Practice and Experience, 21(11)."},
            {"id": "kk1989", "text": "Kamada, T., & Kawai, S. (1989). An Algorithm "
             "for Drawing General Undirected Graphs. Information Processing "
             "Letters, 31(1)."},
            {"id": "bruls2000", "text": "Bruls, M., Huizing, K., & van Wijk, J. J. "
             "(2000). Squarified Treemaps. Proc. VisSym."},
            {"id": "badros2001", "text": "Badros, G. J., Borning, A., & Stuckey, P. "
             "J. (2001). The Cassowary Linear Arithmetic Constraint Solving "
             "Algorithm. ACM TOCHI, 8(4)."},
        ]},
    ]

    return s


# --------------------------------------------------------------------------- #
def build() -> DocumentBuilder:
    b = DocumentBuilder(title="Layout Methods — A Field Guide",
                        profile="book", lang="en")
    b.define_text_style("h1", font_family=["Helvetica"], font_size=23,
                        font_weight=800, color=INK, line_height=1.15)
    b.define_text_style("h2", font_family=["Helvetica"], font_size=16,
                        font_weight=800, color=ACCENT, line_height=1.2)
    b.define_text_style("h3", font_family=["Helvetica"], font_size=12.5,
                        font_weight=700, color=ACCENT, line_height=1.2)
    b.define_text_style("body", font_size=11, color=INK, line_height=1.4)
    b.define_text_style("caption", font_size=9, color=MUTE, line_height=1.3)
    b.define_text_style("fig_caption", font_size=9, color=MUTE, font_style="italic",
                        line_height=1.3)
    b.define_text_style("running_head", font_size=9, color=MUTE)
    b.define_color("ink", INK)
    b.define_color("paper", "#FFFFFF")
    b.define_color("rule", "#C6CBD3")
    b.define_master("main", {
        "canvas": {"size": [612, 792], "units": "pt"},        # US Letter
        "regions": [{"id": "col", "box": [56, 64, 500, 664]}],
    })
    b.flow("chapter", master="main", story=story())
    return b


if __name__ == "__main__":
    doc = build().build(expand_reuse=False)
    print(f"built flow doc — pages={len(doc.pages)}")
