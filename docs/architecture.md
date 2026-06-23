# Framegraph Architecture

> How an input document becomes rendered output (SVG, LaTeX/PDF), and the
> intermediate representation that sits between the two.

## TL;DR

Framegraph **does** generate an intermediate representation. Input files
(`*.fg.json` / `*.fg.yaml`) are parsed and validated into a structured,
backend-neutral **Pydantic `Document` tree** — the IR. Every backend renders
from that same IR, so SVG and LaTeX never re-parse the source format.

There are really two layers of "intermediate":

1. **Structural IR** — the validated `Document` model tree (the durable,
   serializable representation of a deck/figure).
2. **Display list** — a transient, immediate-mode stream of primitive calls
   that a builder emits while walking the IR, consumed by a backend *painter*.

```
*.fg.json / *.fg.yaml
        │
        │  parse + validate            framegraph/sdk/model.py  (validate_document)
        ▼
   Document IR  ───────────────────────  models/framegraph.py  (class Document)
   (Pydantic model tree)
        │
        │  resolve + walk in z-order    framegraph/rendering/domain/services/
        ▼
   primitive display-list calls  ──────  framegraph/rendering/domain/ports.py  (ScenePainter)
        │
   ┌────┴───────────────┐
   ▼                    ▼
 SvgPainter          FigureTikz / _Transpiler
 (SVG fragments)     (LaTeX + TikZ)
   │                    │
   ▼                    ▼
  .svg               .tex → lualatex → .pdf
```

## The IR: the `Document` model tree

The IR is the Pydantic model hierarchy rooted at `Document`, defined in
[models/framegraph.py:1033](../models/framegraph.py#L1033). It is produced by
validating the input file via
[`validate_document()`](../framegraph/sdk/model.py#L26) in
`framegraph/sdk/model.py`.

Because it is a Pydantic tree, the IR is:

- **Validated** — structural and type guarantees before any rendering runs.
- **Backend-neutral** — it describes *what* to draw, not *how* a given backend
  draws it.
- **Serializable** — it round-trips to/from JSON and YAML.

### IR structure (top to bottom)

| Level | Type | Role |
|-------|------|------|
| Root | `Document` | The whole deck/figure |
| Defs | `Defs`, `Tokens`, `Style` | Design tokens, masters, assets, CSS-like style module |
| Container | `Page` / `FlowSection` (`PageProducer`) | A page (page-mode) or a flow section (flow-mode) |
| Stack | `Layer` | Z-ordered band of objects on a page |
| Content | `VisualObject` | Union: `Rect`, `Ellipse`, `Circle`, `Line`, `Polyline`, `Polygon`, `Path`, `Curve`, `Text`, `Image`, `Icon`, `BulletList`, `Dimension`, `TableObject`, `Group` |
| Grouping | `Group` | Nestable container with an optional `Layout` |

Styling is centralized in a CSS-like **style module** (`Tokens` → `Style`,
adopted at 2.2.0). `TextStyle` and `StrokeStyle` are projections of the
authoritative `Style` property bag, so text and stroke styling stay consistent
across backends.

## Pipeline stages

### 1. Parse → IR

`validate_document()` ([framegraph/sdk/model.py:26](../framegraph/sdk/model.py#L26))
loads JSON/YAML and validates it into a `Document` instance. The SDK
(`framegraph/sdk/`) also provides authoring, conform, expand, draw, and IO
helpers around this model.

### 2. Resolve + walk → display-list calls

A **builder** walks the IR in z-order and, for each primitive, calls a method on
a `ScenePainter`. Along the way it uses pure **domain resolvers** to normalize
the IR's abstract values (tokens, styles, layout) into concrete numbers and
colors. The resolvers live in
[framegraph/rendering/domain/services/](../framegraph/rendering/domain/services/):

| Resolver | Responsibility |
|----------|----------------|
| `ColorResolver` | Color token refs → resolved hex/paint values |
| `PaintResolver` | Paint (solid color / gradient) resolution |
| `TextStyleResolver` | Text style tokens → normalized style dicts |
| `StrokeResolver` | Stroke properties |
| `CanvasResolver` | Master references → canvas specs |
| `EffectResolver` | Shadow / glow effects |
| `LayoutEngine` | Arrange group children (row / column / grid) |
| `table_layout` | Table sizing and cell placement |
| `geometry` | Shared geometric math |

For the SVG path, the builder is the `Renderer` class in
[tooling/render_fixtures.py:93](../tooling/render_fixtures.py#L93). It wires up
the resolvers and an `SvgPainter`, then emits primitives page by page
(`render_page`, `render_text`, …).

### 3. Paint → backend output

The seam between the builder and a backend is the **`ScenePainter` port**, an
*immediate-mode display list* defined in
[framegraph/rendering/domain/ports.py:22](../framegraph/rendering/domain/ports.py#L22).
The builder calls methods like `rect()`, `ellipse()`, `path()`, `text_block()`,
`group()`, `document()`; each returns the backend's representation of that
primitive and manages per-page backend resources (gradient/clip id counters, the
`<defs>` registry).

Backends are infrastructure adapters under
[framegraph/rendering/infrastructure/](../framegraph/rendering/infrastructure/):

- **SVG** — `SvgPainter`
  ([painters/svg.py](../framegraph/rendering/infrastructure/painters/svg.py))
  implements `ScenePainter`, returning SVG string fragments and assembling a full
  page in `document()`.
- **LaTeX / TikZ** — driven by `render_latex.py`
  ([tooling/render_latex.py](../tooling/render_latex.py)), which transpiles the
  IR via `_Transpiler`
  ([latex/document.py:72](../framegraph/rendering/infrastructure/latex/document.py#L72))
  and renders vector figures through `FigureTikz`
  ([latex/tikz.py:118](../framegraph/rendering/infrastructure/latex/tikz.py#L118)).
  The emitted `.tex` is compiled to PDF with `lualatex`.

## Design notes

- **Hexagonal / DDD layout.** The `domain/` layer (resolvers, ports, geometry)
  is pure and dependency-free; the `infrastructure/` layer holds the
  format-specific adapters. The domain depends on the `ScenePainter` *abstraction*,
  not on any concrete backend.
- **One IR, many backends.** Both SVG and LaTeX consume the same `Document` IR
  and the same resolver normalization. Adding a backend means implementing the
  `ScenePainter` surface (the port docstring names a future `MatplotlibPainter`
  as the motivating example).
- **Immediate-mode today, retained-mode possible.** The current display list is
  immediate-mode: the builder calls painter methods as it walks. The `ScenePainter`
  docstring notes a possible future **retained-mode `Scene`** — a materialized
  list of primitive value objects on the same seam — which would turn the
  transient display list into a second, inspectable IR.

## File map

| Concern | Location |
|---------|----------|
| IR models | [models/framegraph.py](../models/framegraph.py) |
| Parse/validate + SDK | [framegraph/sdk/](../framegraph/sdk/) (`model.py`, `validate.py`, `io.py`, …) |
| Domain resolvers | [framegraph/rendering/domain/services/](../framegraph/rendering/domain/services/) |
| Painter port (seam) | [framegraph/rendering/domain/ports.py](../framegraph/rendering/domain/ports.py) |
| SVG backend | [framegraph/rendering/infrastructure/painters/svg.py](../framegraph/rendering/infrastructure/painters/svg.py) |
| LaTeX/TikZ backend | [framegraph/rendering/infrastructure/latex/](../framegraph/rendering/infrastructure/latex/) |
| SVG render CLI / builder | [tooling/render_fixtures.py](../tooling/render_fixtures.py) |
| LaTeX render CLI | [tooling/render_latex.py](../tooling/render_latex.py) |
