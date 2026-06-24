---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code (conceptual-codebase-analysis skill)"
  date: "2026-06-23"
provenance:
  method: "Boundaries-first static analysis. No runtime/profiler data. Output is hypothesis, not theorem."
  scope: "framegraph/ (sdk, rendering, mcp), models/, schema/, grammar/, spec/, tooling/, tests/ (~30K py-LOC). viewer/ (JS) sampled via parity test only."
  confidence_legend: "High = 3+ converging sources; Medium = 1–2 files; Low = naming/single path."
---

# FrameGraph v2 — Conceptual Analysis

> Companion visual: [architecture-map.svg](architecture-map.svg)

## 1. System Thesis

FrameGraph v2 is a **document/graphics DSL whose entire architecture is organized around one act of governance: a single Pydantic model (`models/framegraph.py`) is declared the source of truth, and every other artifact — JSON Schema, EBNF grammar, prose spec, docs site, fixture-status table, the JS viewer's type list — is either *generated from* it or *checked against* it by a wall of CI gates.** The model describes two parallel worlds that never mix: **`VisualObject`** (absolute-positioned, layered graphics; CSS/SVG semantics) and **`Flowable`** (reflowable story content; print/CSS-paged semantics). The Python SDK is a convenience layer that *lowers* into the model and validates there; the renderer turns a validated model into SVG (then optionally PNG via Chromium, or `.tex` via LaTeX). If you internalize one thing to predict behavior: **the model is closed (`extra="forbid"`) and authoritative — anything not in it is a hard error at parse time, and anything that drifts from it fails `make check`.** Novel behavior is almost always explained by "what does the model permit, and which gate guards this edge?"

*(Evidence: `models/framegraph.py:1–28` self-describes as "single source of truth"; `schema/build_schema.py:28–36` generates schema from `Document.model_json_schema()`; `Makefile:37` wires 10 gates; `framegraph/sdk/__init__.py` docstring: "builders and helpers lower into the model and validate there." Confidence: high.)*

---

## 2. Concept Atlas

| Concept | Class | Purpose | Where | Stability |
|---|---|---|---|---|
| **`Document`** | control | Root; declares `dsl`, semver `version`, `profile`, `defs`, `pages[]` | `models/framegraph.py:1059` | Stable (semver-gated) |
| **`VisualObject`** (union) | domain | Absolute graphics: rect/ellipse/line/path/text/image/icon/table/group… discriminated by `type` | `models/framegraph.py:721` | Stable core; aliases deprecating |
| **`Flowable`** (union) | domain | Reflowable story: paragraph/heading/list/figure/table/math/toc… discriminated by `type` | `models/framegraph.py:895` | Stable |
| **`Style`** | domain | ~90-field closed CSS-parity bag; `TextStyle`/`StrokeStyle` are *aliases* of it | `models/framegraph.py:232,352` | High-churn surface |
| **`Paint`** | domain | `color │ gradient │ pattern │ url-image`; the fill/stroke value type | `models/framegraph.py:127` | Stable |
| **Page (`mode:"page"`)** | domain | Layered absolute canvas; `reading_order`, `RenderingContract` | `models/framegraph.py:982` | Stable |
| **FlowSection (`mode:"flow"`)** | domain | `story[]` of Flowables on a master; paginated | `models/framegraph.py:996` | Stable |
| **`Defs.tokens`** | control | Named colors/fonts/styles/stroke_styles/glyph_map — the indirection layer styles resolve through | `models/framegraph.py:1021` | Stable |
| **DocumentBuilder / PageBuilder** | domain | Fluent SDK that emits model dicts | `framegraph/sdk/author.py` | Stable API |
| **Renderer** | platform | Orchestrates Document→SVG (object dispatch, layout, text-fit) | `tooling/render_fixtures.py:99` | **Mislocated** (see §6.1) |
| **domain resolvers + `ScenePainter`** | platform | Backend-agnostic paint/stroke/text/canvas/effect/layout services behind a port | `framegraph/rendering/domain/` | Newer, clean |
| **Static rules** | control | ~14 `rule_id` semantic checks beyond Pydantic | `tooling/validate.py:137–321` | Stable |
| **Gates (`make check`)** | control | schema/grammar/spec/a11y/status/golden/docs/validate/overflow | `Makefile:37` | Stable |
| **codemod** | control | Migrates legacy docs to HEAD (P3 stroke, size→sizing, alias→canonical) | `tooling/codemod.py:62–144` | Stable |
| **MCP server** | integration | run/edit SDK clients → validate → render SVG/PNG (the feedback loop) | `framegraph/mcp/server.py:392` | Newer |

**Absent / under-reified concepts** (revealing): there is **no retained-mode Scene / value-object document** separate from the Pydantic dicts — the renderer consumes normalized dicts, not a typed scene; **no plugin/registry** for object types (the unions are closed and edited by hand); **no single "render facade"** (each backend is a separate CLI script). *(Confidence: high — searched; no dispatcher/registry exists.)*

**Compression check:** 16 core concepts + 4 tensions + 6 flows/contracts ≈ 26 items (≤40 target — adequately compressed).

---

## 3. Capability Map

1. **Author a document** — SDK builders (`DocumentBuilder.page().layer().rect(...)`) → `build()`/`expand()` → validated `Document` → `serialize()` to YAML/JSON. Entry: `framegraph/sdk/author.py`. Failure path: validation raises with actionable messages (e.g. P3 stroke error points at the codemod, `models/framegraph.py:545`).
2. **Validate** — `tooling/validate.py`: Pydantic structural pass + static rules; out-of-profile types degrade to **warnings** (§8.5), not errors (`validate.py:99–111`).
3. **Render** — `Renderer.render_page()` → SVG; `render_chromium.py`→PNG; `render_latex.py`→`.tex` (flow only). Decision point: `page.mode` selects absolute vs flow path.
4. **Govern / prevent drift** — `make check` regenerates derived artifacts and diffs, or checks enum/membership parity for hand-maintained views.
5. **Migrate** — `codemod.py` upgrades old documents to HEAD.
6. **AI feedback loop** — MCP server runs SDK code in a subprocess, validates, renders, returns SVG/PNG + diagnostics (`framegraph/mcp/server.py`).

---

## 4. Flow Narratives

**4.1 Authoring → validated document (the happy path).**
A builder call tree produces plain dicts; `expand()` calls `validate_document()` which runs `Document.model_validate()` — so the SDK has *no independent schema*, it borrows the model's. Forward refs (recursive `Group`, footnotes-in-spans) are resolved via `model_rebuild()` at import (`models/framegraph.py:1074`). *(Evidence: `sdk/expand.py:49`, `sdk/model.py:28`. Confidence: high.)*

**4.2 Validated document → SVG.** `Renderer` (`tooling/render_fixtures.py:99`) wires domain resolvers (`ColorResolver`, `TextStyleResolver`, `StrokeResolver`, `CanvasResolver`, `EffectResolver`, `LayoutEngine`) imported from `framegraph/rendering/domain/services/`, then dispatches each object by `type` (`obj()` ~L520), lowering gradients into `<defs>` and emitting via the `SvgPainter` adapter (`framegraph/rendering/infrastructure/painters/svg.py`). **Page-mode** renders layers in z-order to a fixed canvas; **flow-mode** (`_render_flow` ~L1936) does naive vertical word-wrap and emits one SVG per page. *(Evidence: imports at `render_fixtures.py:55–80`; Explore trace. Confidence: high for structure, medium for exact line numbers in the 2.4K-LOC file.)*

**4.3 Model change → schema/grammar/spec sync (the governance flow).** Editing the model and committing without regenerating fails CI: `build_schema.py --check` does byte-equality on the JSON Schema; `check_grammar_sync.py` parses the EBNF tolerantly and compares discriminator literals + named-`Literal` enum value-sets against model introspection; `check_spec_sync.py` asserts every `type`/`kind` discriminator is *named* in the spec prose. *(Evidence: `Makefile:39–46`; agent trace of the three checkers. Confidence: high.)*

**4.4 Render change → golden lock.** `render_golden.py` renders the `fixtures/b1/*` oracle set, SHA-256s each page's SVG, and diffs against `tests/golden/oracle.lock.json`. Any layout/paint/text change shows as a hash drift; intentional changes require `make golden` to re-pin. Relies on the renderer being deterministic (no clock/RNG). *(Evidence: `Makefile:101–105`; agent trace. Confidence: high.)*

**4.5 MCP feedback loop.** `run_sdk_code` writes the snippet + a harness into a per-session temp dir, execs it in a subprocess, derives a `Document` (from `OUTPUT_YAML_PATH`, a `doc/document/builder` global, or a `build*()` function), validates, renders, and returns content blocks + resource URIs. A reused `session_id` will **not** re-derive if `generated.fg.yaml` already exists. *(Evidence: `framegraph/mcp/server.py:707–744`; observed directly this session. Confidence: high.)*

---

## 5. Boundary Contracts (drift map)

| Derived artifact | Source | Gate | Comparison | Tightness |
|---|---|---|---|---|
| `schema/framegraph-v2.schema.json` | model | `schema-check` | regenerate + **byte-equal** | Tight |
| `FIXTURE-STATUS.md` | validator over fixtures | `status-check` | regenerate + byte-equal | Tight |
| `docs/*` (reference, sdk, sdk-api…) | schema + SDK docstrings | `docs-check`, `test_generated_docs_fresh` | regenerate + byte-equal | Tight |
| `tests/golden/oracle.lock.json` | b1 renders | `golden-check` | SHA-256 per page | Tight (deterministic) |
| `grammar/*.ebnf` | model (hand view) | `grammar-check` | discriminator + enum **parity** | **Looser** |
| `spec/…spec.md` | model (hand view) | `spec-check` | type/kind **named in prose** | **Loosest** |
| `viewer/` type sets | model | `test_viewer_schema_parity` | set membership | Medium |

**Key seam:** the boundary splits into *generated* artifacts (byte-equal, cannot drift silently) and *hand-maintained views* (grammar, spec) guarded only by membership/enum parity. A change to a field's *semantics or shape* (not its enum set or name) can pass grammar/spec gates while the prose silently lies. *(Evidence: agent trace of `check_grammar_sync.py` / `check_spec_sync.py`; the spec check is word-boundary substring presence. Confidence: high.)*

---

## 6. Tension Report

**6.1 — The canonical renderer lives in `tooling/`, and the library depends *up* into it.** `Renderer` is a 2,395-line class in `tooling/render_fixtures.py`, yet `framegraph/sdk/conform.py:8` does `from tooling.render_fixtures import Renderer, normalize_doc` — and the MCP server's render path goes through `sdk.conform`. So a *script directory* holds core library code that the *package* imports. Meanwhile the clean parts (resolvers, `ScenePainter` port, SVG/LaTeX/browser adapters) were already extracted into a hexagonal `framegraph/rendering/` package. **Diagnosis: historical accretion + incomplete refactor.** The extraction stopped before moving the orchestrator. *(Evidence: `tooling/render_fixtures.py:99`, `framegraph/sdk/conform.py:8`, `framegraph/rendering/domain/ports.py:22`. Confidence: high.)* This is the single highest-leverage cleanup.

**6.2 — Drift surface on hand-maintained views.** Grammar and spec are "views, not the source" (`models/framegraph.py:11`) and the gates that hold them honest are looser than byte-equality (§5). **Diagnosis: conflicting requirements** — human-readable EBNF/prose vs machine-exact sync. The project knowingly accepts this (the docstring calls EBNF "a view"); it is a *design bet*, not an oversight, but it is the most probable source of a future "the spec says X, the model does Y" bug. *(Confidence: high.)*

**6.3 — `Style` is a ~90-property closed CSS bag, aliased three ways.** `TextStyle = Style` and `StrokeStyle = Style` (`models/framegraph.py:352–353`), so a "text style" structurally accepts `stroke_miterlimit` and a "stroke style" accepts `font_kerning`. The closed model forbids *unknown* keys but not *semantically-irrelevant known* keys. **Diagnosis: leaky/over-broad abstraction** — CSS-parity ambition pushed into one type. Renderers implement a subset; the gap between "validates" and "renders" is invisible at the model layer. *(Evidence: `models/framegraph.py:232–353`. Confidence: high.)*

**6.4 — Two computational models for layout.** Page-mode is a **retained absolute** model (layers, z-order, `Group.layout` flexbox/grid); flow-mode is a **streaming pagination** model with admittedly naive word-wrap. They share resolvers but not a layout engine. **Diagnosis: paradigm boundary.** Mixed documents (`profile:"mixed"`) straddle both; flow is the weaker engine and the likelier source of layout surprises. *(Evidence: `models/framegraph.py:982/996`; renderer has distinct `render_page` vs `_render_flow` paths. Confidence: high.)*

**6.5 — Deprecated aliases + visible patch accretion (P1–P4, gap#1).** `Circle`/`Polygon`/`Curve` exist only as renderer shortcuts, marked deprecated, normalized by codemod (`models/framegraph.py:572,598,613`); the module header narrates a patch series. **Diagnosis: managed historical accretion** — well-documented, codemod-backed, but it means three ways to draw a circle and a model that carries its own changelog. *(Confidence: high.)*

---

## 7. Onboarding Path (read in this order)

1. `models/framegraph.py` — **the** file; the whole system is a satellite of it. Read the header comment (patch series) then the two unions.
2. `tooling/validate.py` — what "valid" means beyond types (static rules, §8.5 profile warnings).
3. `Makefile` — the governance contract; `check` is the system's spine.
4. `framegraph/sdk/__init__.py` + `sdk/author.py` — how documents are authored; `sdk/expand.py` for lowering.
5. `tooling/render_fixtures.py` (skim) + `framegraph/rendering/domain/` — how a document becomes SVG; note the location tension (§6.1).
6. `schema/build_schema.py`, `tooling/check_grammar_sync.py`, `check_spec_sync.py` — the drift gates.
7. `examples/ai_mobile_app_wireframe.py` / `examples/food_tracking_ai_app.py` — end-to-end SDK usage.
8. `framegraph/mcp/server.py` — the AI feedback loop.

---

## 8. Change Impact Guide

**8.1 — "Add a new visual object type (e.g. `qrcode`)."** Touch points, in order: add the model class + put it in the `VisualObject` union (`models/framegraph.py:721`) and `CORE_OBJECT_TYPES` (`validate.py:40`); `make schema` (schema-check would else fail); add it to the EBNF grammar and name it in the spec prose (grammar-check/spec-check); add it to the viewer type set (parity test); implement rendering in `Renderer.obj()` dispatch + `SvgPainter`; add a fixture (and it will enter golden + status). **Five gates will fail until all mirrors are updated** — by design. Propagation: model → schema → grammar → spec → viewer → renderer → fixtures/golden/status.

**8.2 — "Change how text wraps / a default font metric."** Self-contained in the renderer (`render_fixtures.py` text-fit + `framegraph/rendering/infrastructure/font_metrics.py`), but **golden-check will fail for every fixture** with text. Required: `make golden` to re-pin, and review the diff to confirm the change is intended. No model/schema impact. *(This is the canonical "what breaks" surprise — a cosmetic render tweak trips the deterministic hash lock.)*

**8.3 — "Rename a `Style` property or tighten an enum."** Model edit → `make schema` (byte diff) → update EBNF enum (grammar-check enum-parity) → spec prose if the name was cited → **possible silent gap** if the property is only loosely referenced in prose. Plus: any committed fixture or golden render using the old name now fails validation/golden. Provide a `codemod.py` migration (the project's established expectation for breaking changes).

---

## 9. Notes & Limits

- Confidence is **high** on the model, governance, and boundary contracts (multiple converging sources, gates that encode the contracts explicitly). It is **medium** on exact line numbers inside `render_fixtures.py` (2.4K LOC, traced by sub-agent, not line-verified end-to-end) and on the `viewer/` (90 JS files, examined only via the parity test, not read).
- No runtime evidence: hot paths, Chromium launch behavior, and real font resolution were not executed/profiled.
- The repo contains prior agent artifacts at root (`drift-risk-map.md`, `doc-hygiene-report.md`, `codebase-standards.md`) that overlap this analysis; I did **not** treat them as evidence (they may be stale) — all claims here are grounded in live files cited inline.
