---
disclaimer:
  notice: >-
    No information within this document should be taken for granted. This is a
    hand-written design record, listed in the MkDocs nav under Design records but
    not gated for prose freshness — verify any claim against the live tree before
    relying on it.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-24"
  last_revised: "2026-08-01"
---

# FrameForge Architecture

> How an input document becomes rendered output (SVG, LaTeX/PDF), and the
> intermediate representation that sits between the two.

## TL;DR

FrameForge **does** generate an intermediate representation. Input files
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
        │  parse + validate            frameforge_api + frameforge_sdk
        ▼
   Document IR  ───────────────────────  frameforge_api.model.Document
   (Pydantic model tree)
        │
        │  resolve + walk in z-order    frameforge_render/domain/services/
        ▼
   primitive display-list calls  ──────  frameforge_render/domain/ports.py  (ScenePainter)
        │
   ┌────┴───────────────┐
   ▼                    ▼
 SvgPainter          FigureTikz / _Transpiler
 (SVG fragments)     (LaTeX + TikZ)
   │                    │
   ▼                    ▼
  .svg               .tex → lualatex/pdflatex → .pdf
```

## The IR: the `Document` model tree

The IR is the Pydantic model hierarchy rooted at `Document`, defined in
[`frameforge_api.model`](https://github.com/pedroanisio/frameforge-api/tree/main/src/frameforge_api/model).
It is produced by validating the input file via `validate_document()` in
[`src/frameforge_sdk/model.py`](https://github.com/pedroanisio/frameforge-sdk/blob/main/src/frameforge_sdk/model.py).

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
| Content | `VisualObject` | Union: `Rect`, `Ellipse`, `Circle`, `Line`, `Polyline`, `Polygon`, `Path`, `Curve`, `Text`, `Image`, `Icon`, `BulletList`, `Dimension`, `Connector`, `TableObject`, `Group` |
| Grouping | `Group` | Nestable container with an optional `Layout` |

Styling is centralized in a CSS-like **style module** (`Tokens` → `Style`,
adopted at 2.2.0). `TextStyle` and `StrokeStyle` are projections of the
authoritative `Style` property bag, so text and stroke styling stay consistent
across backends.

## Pipeline stages

### 1. Parse → IR

`validate_document()` ([src/frameforge_sdk/model.py](https://github.com/pedroanisio/frameforge-sdk/blob/main/src/frameforge_sdk/model.py))
loads JSON/YAML and validates it into a `Document` instance. The SDK
(`src/frameforge_sdk/`) provides authoring, validation, expand, draw, and IO
helpers around this model. Pixel-dependent conformance helpers remain in
`frameforge.conform` and delegate to the standalone render engine.

### 2. Resolve + walk → display-list calls

A **builder** walks the IR in z-order and, for each primitive, calls a method on
a `ScenePainter`. Along the way it uses pure **domain resolvers** to normalize
the IR's abstract values (tokens, styles, layout) into concrete numbers and
colors. The resolvers live in
[src/frameforge_render/domain/services/](https://github.com/pedroanisio/frameforge-render/tree/main/src/frameforge_render/domain/services):

| Resolver | Responsibility |
|----------|----------------|
| `ColorResolver` (`paint_resolver.py`) | Color/paint token dereference — gradients proxy to the first stop's color; gradient emission stays in the painter |
| `TextStyleResolver` | Text style tokens → normalized style dicts |
| `StrokeResolver` | Stroke properties |
| `CanvasResolver` | Master references → canvas specs |
| `EffectResolver` | Shadow / glow effects |
| `LayoutEngine` | Arrange group children (row / column / grid) |
| `flow_layout` | Backend-neutral prose layout: Knuth–Plass line breaking, hyphenation, span-aware justification (ADR-0003) |
| `table_layout` | Table sizing and cell placement |
| `TextFitter` (`text_fitter.py`) | Measure / wrap / ellipsize text to a pixel width (injected font-metrics provider) |
| `StyleValues` (`style_values.py`) | CSS/SVG value builders: filter / shadow / transform / length |
| `math_text` | Dependency-free TeX→Unicode display fallback |

Shared geometric math lives one level up, in
`src/frameforge_render/domain/geometry.py` (not a service). The
`flow_layout` engine emits the `LaidLine`/`LaidParagraph` IR and the
recto/verso `content_box`.

For the SVG path, the builder is the `Renderer` class in
[`src/frameforge_render/application/renderer.py`](https://github.com/pedroanisio/frameforge-render/blob/main/src/frameforge_render/application/renderer.py),
the rendering bounded context's **application layer**. It wires up the resolvers
and an `SvgPainter`, then emits primitives page by page (`render_page`,
`render_text`, …). [`tooling/render_fixtures.py`](https://github.com/pedroanisio/frameforge/blob/main/tooling/render_fixtures.py)
is the thin CLI driver (discovery, contact sheet, `--check-overflow`) and
re-exports `Renderer` for backward compatibility.

### 3. Paint → backend output

The seam between the builder and a backend is the **`ScenePainter` port**, an
*immediate-mode display list* defined in
[`src/frameforge_render/domain/ports.py`](https://github.com/pedroanisio/frameforge-render/blob/main/src/frameforge_render/domain/ports.py).
The builder calls methods like `rect()`, `ellipse()`, `path()`, `text_block()`,
`group()`, `document()`; each returns the backend's representation of that
primitive and manages per-page backend resources (gradient/clip id counters, the
`<defs>` registry).

Backends are infrastructure adapters under
[src/frameforge_render/infrastructure/](https://github.com/pedroanisio/frameforge-render/tree/main/src/frameforge_render/infrastructure):

- **SVG** — `SvgPainter`
  ([painters/svg.py](https://github.com/pedroanisio/frameforge-render/blob/main/src/frameforge_render/infrastructure/painters/svg.py))
  implements `ScenePainter`, returning SVG string fragments and assembling a full
  page in `document()`.
- **LaTeX / TikZ** — driven by `render_latex.py`
  ([tooling/render_latex.py](https://github.com/pedroanisio/frameforge/blob/main/tooling/render_latex.py)), which transpiles the
  IR via `_Transpiler`
  ([latex/document.py](https://github.com/pedroanisio/frameforge-render/blob/main/src/frameforge_render/infrastructure/latex/document.py))
  and renders vector figures through `FigureTikz`
  ([latex/tikz.py](https://github.com/pedroanisio/frameforge-render/blob/main/src/frameforge_render/infrastructure/latex/tikz.py)).
  The emitted `.tex` is compiled to PDF with `lualatex` when `luaotfload` is
  available, else `pdflatex` (`--engine auto`).
- **TikZ painter (in progress)** — `TikzPainter`
  ([painters/tikz.py](https://github.com/pedroanisio/frameforge-render/blob/main/src/frameforge_render/infrastructure/painters/tikz.py))
  is a second `ScenePainter` adapter, test-gated (`test_tikz_painter.py` /
  `test_tikz_wiring.py` / `test_tikz_fidelity.py`) and covering the port
  except `text_block`/`text_runs` — intentionally not yet wired into the
  render path (the `latex/` fork above still owns LaTeX output).

## Design notes

- **Hexagonal / DDD layout.** The `domain/` layer (resolvers, ports, geometry)
  is pure and dependency-free; the `application/` layer holds the `Renderer`
  orchestration use-case; the `infrastructure/` layer holds the format-specific
  adapters. The domain depends on the `ScenePainter` *abstraction*, not on any
  concrete backend. *In progress* (codebase-standards.md §13): the application
  `Renderer` still constructs `SvgPainter` directly and the large class is
  being decomposed; `TikzPainter` exists as a second port adapter but is
  intentionally not yet wired into the render path (the `latex/` fork still
  owns LaTeX output), so the shipping LaTeX and Chromium paths remain separate
  drivers rather than adapters behind the one port.
- **One IR, many backends.** Both SVG and LaTeX consume the same `Document` IR
  and the same resolver normalization. Adding a backend means implementing the
  `ScenePainter` surface (the port docstring names a future `MatplotlibPainter`
  as the motivating example).
- **Immediate-mode today, retained-mode possible.** The current display list is
  immediate-mode: the builder calls painter methods as it walks. The `ScenePainter`
  docstring notes a possible future **retained-mode `Scene`** — a materialized
  list of primitive value objects on the same seam — which would turn the
  transient display list into a second, inspectable IR.
- **Measure-time font must equal render-time font.** The strongest mode is a
  `frameforge-fonts` closure provider: HarfBuzz shapes SHA-256-pinned bytes and
  the same callable is injected into SDK measurement, static validation,
  `frameforge.conform`, SVG/HTML rendering, reports, and MCP tools. The renderer
  reports `metrics_mode: closure`; strict mode raises for an unpinned family.
- **Metric evidence has three explicit strengths.** `closure` is portable and
  byte-pinned; host-bound `real` uses the file local fontconfig resolves;
  `estimate` is deterministic arithmetic. A supplied `metrics_provider` always
  outranks `real_metrics` / `FRAMEFORGE_REAL_METRICS`. MCP accepts
  `font_closure` plus `font_generics`, confines the path with
  `FRAMEFORGE_MCP_INPUT_ROOTS`, and reports the closure digest.
- **Generative sampling is author-side computation, not IR state.**
  `frameforge_sdk.rand` provides process-stable `Rand` streams plus Halton,
  Poisson-disk, and jittered-grid sampling. They compute ordinary `Vec2` values
  in Y-down page space, which authors lower into existing objects before model
  validation. Named `Rand.derive(...)` streams isolate document regions from
  call-order changes. No seed, RNG state, sampler object, model field, renderer
  branch, or configuration knob enters the durable IR; reproducibility is proved
  at the SDK/example boundary and the resulting ordinary geometry continues
  through the unchanged parse → IR → painter pipeline.
- **Validation may invoke layout, but painting remains optional.** Structural and
  referential rules run first. Default validation then runs the application
  renderer's measurement pass and discards the SVG, surfacing typed
  truncation/overflow feedback. `--no-text-fit` / `text_fit=False` is the explicit
  structure-only lane. Geometric containment independently descends through
  group-local arranged boxes; `containment: allowed` is the only bleed consent,
  separate from `decorative` accessibility intent.

## File map

| Concern | Location |
|---------|----------|
| IR models | [frameforge_api/model](https://github.com/pedroanisio/frameforge-api/tree/main/src/frameforge_api/model) |
| Parse/validate + SDK | [src/frameforge_sdk/](https://github.com/pedroanisio/frameforge-sdk) (`model.py`, `validate.py`, `io.py`, …) |
| Deterministic sampling | [src/frameforge_sdk/rand.py](https://github.com/pedroanisio/frameforge-sdk/blob/main/src/frameforge_sdk/rand.py) (`Rand`, `halton`, `poisson_disk`, `jittered_grid`) |
| Domain resolvers | [frameforge_render/domain/services](https://github.com/pedroanisio/frameforge-render/tree/main/src/frameforge_render/domain/services) |
| Painter port (seam) | [frameforge_render/domain/ports.py](https://github.com/pedroanisio/frameforge-render/blob/main/src/frameforge_render/domain/ports.py) |
| Render orchestrator (application) | [frameforge_render/application/renderer.py](https://github.com/pedroanisio/frameforge-render/blob/main/src/frameforge_render/application/renderer.py) |
| SVG backend | [frameforge_render/infrastructure/painters/svg.py](https://github.com/pedroanisio/frameforge-render/blob/main/src/frameforge_render/infrastructure/painters/svg.py) |
| LaTeX/TikZ backend | [frameforge_render/infrastructure/latex](https://github.com/pedroanisio/frameforge-render/tree/main/src/frameforge_render/infrastructure/latex) |
| Portable metrics owner | [frameforge_fonts/metrics.py](https://github.com/pedroanisio/frameforge-fonts/blob/main/src/frameforge_fonts/metrics.py) |
| Conformance adapter | [src/frameforge/conform.py](https://github.com/pedroanisio/frameforge/blob/main/src/frameforge/conform.py) |
| SVG render CLI driver | [tooling/render_fixtures.py](https://github.com/pedroanisio/frameforge/blob/main/tooling/render_fixtures.py) |
| LaTeX render CLI | [tooling/render_latex.py](https://github.com/pedroanisio/frameforge/blob/main/tooling/render_latex.py) |
