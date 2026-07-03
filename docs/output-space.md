---
disclaimer:
  notice: >-
    No information within this document should be taken for granted. This is a
    hand-written conceptual design record, listed in the MkDocs nav under Design
    records but not gated for prose freshness. Its
    "Generated today" anchor — the concrete entry points — is pinned by
    tests/test_output_space_doc.py and fails the gate on drift. The conceptual
    families and the boundaries are NOT machine-verifiable; verify them against
    the live tree before relying on them.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-24"
---

# FrameGraph output space

*What FrameGraph can generate — both concretely (what is wired today) and
conceptually (what the architecture admits).* Cross-referenced from
[the README](../README.md); see also [architecture.md](architecture.md).

## The generating principle

FrameGraph is not a renderer; it is a **verifiable intermediate representation
(IR) for visual documents**. One pipeline defines the entire output space:

```
authoring (YAML / SDK)  →  Document model (the source of truth)
   →  Renderer resolves + walks in z-order  →  primitive display-list (ScenePainter port)
      →  a backend adapter emits the target
```

So an output is *possible* **iff** (a) the model can express the needed
semantics **and** (b) a `ScenePainter` (or model-walking) adapter maps the
display-list to that target. Everything below is a corollary of that — the
constraint is IR expressiveness and the existence of an adapter, never the
architecture.

## Generated today (verified)

These are wired and exercised in the repo. Each names its entry point; the paths
here are pinned by `tests/test_output_space_doc.py` (drift → gate failure).

The shared core is the port + renderer:
`src/framegraph/rendering/domain/ports.py` (the `ScenePainter` port) and
`src/framegraph/rendering/application/renderer.py` (the model-walking `Renderer`).

| Output | Kind | Entry point |
|---|---|---|
| **SVG** | vector (primary) | `src/framegraph/rendering/infrastructure/painters/svg.py`, driven by `tooling/render_fixtures.py` |
| **PNG** (headless Chromium) | raster, CSS-fidelity; `--font-pack P.fp` scopes fonts so measure == render (ADR-0004) | `tooling/render_chromium.py` |
| **Raster** (matplotlib proxy) | raster, sanity check | `tooling/render_fg_doc.py` |
| **PDF** via LaTeX/TikZ (lualatex *or* pdflatex) | print/typeset | `tooling/render_latex.py`, `src/framegraph/rendering/infrastructure/latex/document.py` |
| **PDF** via cairosvg (SVG → PDF) | vector PDF | `tooling/render_pdf.py` |
| **HTML/CSS** (ADR-0004 promotes this to the intended flow-fidelity path; the current implementation still degrades flow — documented flow/gradient limits) | web | `tooling/framegraph_to_html.py` |
| **Math** TeX → SVG (MathJax) | embedded glyphs | `tooling/mathjax_tex_to_svg.mjs` |
| **JSON Schema** | format contract | `docs/schema/build_schema.py` |
| **Docs site** (reference/gallery/SDK/spec) | documentation | `tooling/gen_docs.py` |
| **Golden hashes** (per-page SHA-256 of SVG) | regression lock | `tooling/render_golden.py` |

The second-painter migration (`src/framegraph/rendering/infrastructure/painters/tikz.py`,
`TikzPainter`) is in progress — when wired it routes the LaTeX/TikZ output through
the same port, collapsing the `FigureTikz` fork.

**Import — the hub's other half** (any-format → FrameGraph):
`tooling/pdf_to_framegraph_yml.py` (PDF → fixed-layout FrameGraph), plus vision
`propose_from_image` / `propose_from_document` in the MCP server.

> Honest scope: no renderer is conformant; the SVG/matplotlib proxies are sanity
> checks, not fidelity guarantees, and fidelity degrades where a target cannot
> hold an IR feature (gradients flatten in TikZ; flow degrades in the HTML path).
>
> Text determinism is enforced separately by `fg-font` (`src/framegraph/fontpack.py`,
> a console script): `--check DOC` gates a document (non-zero exit if a content font
> would substitute), `--pack DOC --out P.fp` bundles the exact faces plus a
> `family → file → sha256` manifest, and a substituted content font now **screams**
> (a `font_substitution` warning to diagnostics *and* stderr). A `.fp` pack fed to
> `render_chromium.py --font-pack` makes measure == render on any host
> ([ADR-0004](adr-0004-single-engine-layout.md)).

## What it could generate (conceptual)

Three families fall out of the generating principle, plus a hub.

### A. Renditions — the laid-out document *drawn* (any `ScenePainter` adapter)
- More vector: EPS/PostScript, Typst, ConTeXt; print-grade PDF/X and archival PDF/A.
- More raster: JPEG/WebP/TIFF at any DPI, sprite sheets, thumbnails.
- Web-native: Canvas/WebGL, React/Web-Component output, MJML (email-safe HTML).
- Print production: CMYK colour separations, imposition/signatures, crop/bleed marks.

### B. Hand-offs — re-expressed in a format whose *own* engine owns final layout
- Typesetting: LaTeX, Typst, Beamer (it already drives TeX).
- Office & DTP: DOCX, PPTX, ODT, **InDesign IDML/ICML**, Scribus SLA.
- Ebook: EPUB 3, MOBI/KF8 (the flow / TOC / figure semantics map cleanly).
- Markup: Markdown, AsciiDoc, HTML.

### C. Derivatives — computed *from the structured model, not the pixels*
This is the part most renderers cannot do, and where the "verifiable IR" thesis pays off.
- **Accessibility**: tagged **PDF/UA**, an accessibility/ARIA tree, reading-order
  plain-text linearization, SSML/audio narration, Braille/BRF — the model already
  carries `reading_order` / `alt` / `actual_text` / `decorative` *for a future
  tagged export* (a gated roadmap item, not yet emitted).
- **Structure**: TOC, list-of-figures, index, bibliography (model-level,
  backend-agnostic).
- **Knowledge**: a search index / embeddings of the semantic content; a
  content/visual **diff** between two documents.
- **Contracts from the model**: TypeScript/Zod/Protobuf types, JSON Schema, the
  EBNF grammar (the schema is already auto-derived — the trick generalizes).
- **Geometry / 3D interchange**: Graphviz DOT, Mermaid, draw.io XML, DXF,
  pen-plotter G-code/HPGL; and from `Scene3D` / manifolds / lattices, glTF/OBJ/STL/USD.

### The hub — any → FrameGraph → any
Because the import side exists (PDF/image → FG), FrameGraph can be a
*Pandoc/Babel for visual documents*: every (importer × exporter) pair. This is
arguably the largest latent output.

## Boundaries (deliberate non-goals)

Conceptually possible, but explicitly **not** pursued (codebase-standards §13):
a WYSIWYG editor; a browser-only rendering core; an interactive presentation
*runtime*; a general constraint-solver layout engine for every diagram class; a
general scientific-charting replacement. And anything needing semantics the IR
does not model — e.g. **time/animation** (Lottie, SMIL, video) is not expressible
until the model grows a temporal axis.

## The one-line answer

FrameGraph can generate *any artifact that is a pure function of a laid-out,
accessibility-annotated visual-document model* — every rendition a painter can
draw, every format another engine can typeset from, and every semantic
derivative the structured tree affords — bounded only by IR expressiveness and
the existence of an adapter, not by the architecture.

---

*This record protects only its concrete anchor (the "Generated today" entry
points, gated by `tests/test_output_space_doc.py`). The conceptual families are
direction, not promises — treat them with the project's "don't overclaim" ethos.*
