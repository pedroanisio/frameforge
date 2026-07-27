---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code; resolution record by OpenAI Codex (GPT-5)"
  date: "2026-07-27"
title: FrameForge 2.6.0 — issue drafts from a 20-page authoring session
author: drafted by Claude, reviewed and resolved locally by OpenAI Codex
frameforge_version: 2.6.0
session_scope: two documents, 28 pages total, 1280×880 px canvases, SVG/PDF/PNG lanes
status: implemented and regression-tested locally; upstream publication/deployment pending
---

# Issue drafts

## Resolution record — 2026-07-27

The observations below are retained as the original session report. They were
verified against the live tree and corrected where the proposed explanation was
incomplete. All seven outcomes are implemented test-first in this workspace:

| Draft | Resolution |
|---|---|
| Metric divergence | Shared SDK/renderer mode + full family stack; `fit_width()` and MCP `fit_text` added. |
| Shallow/decorative containment | Deep group-local audit; `decorative` decoupled; `containment: allowed` and `bleed()` consent added. |
| Opt-in text fit | CLI and SDK validation now run text fit by default, with explicit opt-outs. |
| Whitespace collapse | `pre`, `pre-wrap`, `pre-line`, and `break-spaces` layout semantics implemented. |
| Dash strings | SVG whitespace/comma strings and `dash` shorthand normalize to canonical lists. |
| Tabular false positives | 85% density requirement plus annotation/furniture/lettering role exemptions. |
| Ambiguous `needed` | Semantics documented; additive, backward-compatible `unwrapped_width` added. |

The authoritative migration notes are
[`docs/migration-2.7-authoring-feedback.md`](docs/migration-2.7-authoring-feedback.md).
This record does not claim deployment: external issue/backlog state should be updated
only after the changes are published by an authorized maintainer.

Ordered by how much time each cost me, worst first.

---

## 1. `measure_text`, the line-breaker and the renderer use three different metric sources

**Severity:** high — it is the difference between "boxes are tight" and "boxes collide".

**What happened.** Authoring absolutely-positioned per-token text (an annotated
reading view, one text object per word), I need each box wide enough that the
line-breaker will not split the word, and narrow enough that adjacent boxes do
not overlap. Those two constraints are only simultaneously satisfiable if my
width prediction matches the breaker's. It does not.

Three stages measure independently:

| Stage | Source | Observed |
|---|---|---|
| `measure_text()` | built-in metric table | baseline |
| line-breaker (`overflow_report` / `--text-fit`) | real font metrics | needs **up to 1.35×** the `measure_text` width |
| renderer | whatever fontconfig resolves | **0.88×** the `measure_text` width |

Measured on this machine, font-size 13, binary-searching the minimum box width
that avoids a split:

| Font stack | Max slack the breaker demanded | Rendered ink / `measure_text` |
|---|---|---|
| `("Inter","Helvetica","Arial","sans-serif")` — **the SDK default theme** | not usable; the three stages diverged ~12% | 0.878 |
| `("Carlito","sans-serif")` — installed, renders fine | **1.35×** | 0.975 |
| `("DejaVu Sans","sans-serif")` — installed | **1.09×** | 0.972 |

**The sting:** `default_theme().font` is `("Inter", "Helvetica", "Arial",
"sans-serif")`, and none of those resolve in this environment. So the shipped
default is the worst case, and an author who never touches the theme gets the
maximum divergence. Carlito renders correctly but the *breaker* appears to fall
back on it — a font can be right for the renderer and wrong for the breaker.

**Cost to me:** ~10 tool calls of probes and binary searches before settling on
`SLACK = 1.20` over DejaVu Sans.

**Proposals, cheapest first:**
1. Document the three-stage divergence in the text-authoring notes. Even just
   "name a font all three can resolve" would have saved the whole detour.
2. Ship a default theme font stack that resolves on common Linux containers
   (prepend `DejaVu Sans`), or resolve the stack at build time and warn when
   nothing in it is available.
3. Export a `fit_width(text, size, family) -> float` helper that returns a box
   width the breaker is guaranteed to accept. Every author of positioned text
   needs this and every one of them will re-derive my constant badly.
4. Longer term: have the breaker and `measure_text` read one metric source.

---

## 2. `decorative=True` silently disables the containment audit, and group children escape it entirely

**Severity:** high — this shipped a broken page past a clean validator.

**What happened.** A background panel drawn with the widgets' own `_bg()`
convention (`decorative=True`) at `[x, 296, w, 640]` on an 880 px canvas
extends to y=936 — 56 px off-canvas, 100 px past my intended viewport.
`validate_static_rules` returned `ok=True, 0 issues`. `--text-fit` passed.

Two compounding causes, from `tooling/validate.py`:

- `_geometric_audit` skips `o.get("decorative")` for the containment check.
  Reasonable for a11y reading order; wrong for geometry, since backgrounds are
  exactly the objects most likely to be oversized.
- The same function iterates `layer.get("objects")` only. It does not recurse
  into `type: "group"` children. Since the SDK's own widgets and the
  `local()` / `group()` idiom put nearly everything inside groups, **most
  objects in a well-structured document are exempt from containment.**

I only caught it by writing an independent bounding-box sweep that walks group
children. That sweep later caught a second instance (a text column running to
x=1400 on a 1280 canvas, also inside a group, also clean per the validator).

**Proposals:**
1. Recurse into group children for the containment rule, or add
   `--containment-deep`.
2. Decouple the two meanings of `decorative`: keep it excluding objects from
   reading order and from the scoped-overlap audit, but still check containment.
   A decorative object off-canvas is a bug in every case I can construct.
3. If (1) and (2) are both unwanted, at minimum document that containment is
   top-level-and-non-decorative only, so authors know to build their own sweep.

---

## 3. `--text-fit` finds silent content loss and is opt-in

**Severity:** medium-high.

`tooling/validate.py --text-fit` was the only check that caught:
- a single trailing comma dropped from `skill,` (box 36.3 px, one word);
- a two-line footer note whose box fit one line, silently discarding the second.

Neither is visible in the SVG, and in a print-bound PDF nobody notices until
it is printed. `validate_static_rules` (the SDK-facing API) does not run it,
so an author using the Python SDK never sees it unless they know to shell out
to `tooling/validate.py`.

**Proposal:** run the text-fit pass inside `validate_static_rules` by default,
or expose `validate_static_rules(text_fit=True)`. The docstring for §3.7 calls
this "SILENT content loss" — an opt-in check for silent data loss is the wrong
default.

---

## 4. Runs of whitespace collapse inside a text object, undocumented

**Severity:** medium — silent, and the workaround is non-obvious.

`"Advanced   SQL   Implementing"` and `"Advanced SQL Implementing"` render to
byte-identical ink extents (measured: both 268.5 px at size 15). The renderer
inherits SVG's default `xml:space` collapsing.

This matters because padding tokens with extra spaces is the obvious way to
leave room for inline decorations, and it fails silently — the author sees
correct spacing in their source string and wrong spacing on the page. The
working alternative (one text object per token, positioned) is materially more
expensive and interacts with issues 1 and 2 above.

**Proposal:** document it in the text notes, and/or support
`style={"white_space": "preserve"}` lowering to `xml:space="preserve"`.

---

## 5. `stroke_dasharray` rejects the SVG string form, and the error is hard to read

**Severity:** low, but it is a first-five-minutes papercut.

```python
stroke_style={"stroke_width": 1.0, "dash": [4, 4]}            # rejected: unknown field
stroke_style={"stroke_width": 1.0, "stroke_dasharray": "4 4"} # rejected: not a list
stroke_style={"stroke_width": 1.0, "stroke_dasharray": [4, 4]}# accepted
```

The middle form is the one every SVG author will try first. The rejection is a
three-branch pydantic union dump (`literal['none']` / `list[union[...]]` /
`str`) that takes a moment to decode.

**Proposal:** accept a whitespace- or comma-separated string and normalise it.
Optionally accept `dash=` as an alias.

---

## 6. `tabular-box-model` false-positives on incidental alignment

**Severity:** low-medium — it cost a real detour and the fix was a workaround,
not a correction.

The rule (`tooling/validate.py` ~line 698) fires on ≥6 boxed text objects when
≥2 x-values are shared by ≥2 objects, ≥3 y-values are shared by ≥2 objects, and
≥6 objects sit on that intersection.

It fired on a page whose "grid" was: three region tags sharing one y, plus a
caption-strip pair sharing another y, plus a footer pair sharing a third — six
objects, no table anywhere. All the page's genuine label:value data was already
in first-class `table` objects.

The workaround was to wrap the annotation furniture in a `local()` group, since
the rule does not recurse. That works, but it means the sanctioned fix for a
false positive is "hide the objects from the rule".

**Proposals:**
1. Require the detected grid to be near-complete: `cells >= 0.7 * len(cols) *
   len(rows)`, so a sparse coincidence does not qualify.
2. Or exempt objects carrying a `meta.role` of `annotation` / `furniture`, the
   way `lettering` is already exempted.

---

## 7. `OverflowSignal.needed` semantics are unclear

`needed` is sometimes **smaller** than the box width while overflow is still
reported:

```
box=(20.0, 380.0, 88.57, 21.0)  needed=(87.88, 36.4)  detail=','
```

Box width 88.57 > needed width 87.88, yet the object is reported as wrapping to
two lines (needed height 36.4 = 2 × line-height). My reading is that `needed[0]`
is the widest line *after* breaking rather than the width required to avoid
breaking — which makes it unusable for the obvious purpose of computing a
corrected box width. UNVERIFIED; I did not read the diagnostics producer.

**Proposal:** document what `needed` measures, and if it is post-wrap, add the
pre-wrap required width. That number is what an author actually wants.

---

## What is good, and worth not regressing

Stated because bug lists distort:

- The **widget vocabulary** (`table`, `card`, `pill`, `segmented`, `field`,
  `image_placeholder`, `sparkline`, `kpi`, `badge`) made a 28-page set feasible.
  `image_placeholder` in particular is exactly right for wireframing.
- **`table()` lowering to a first-class `TableObject` that silences
  `tabular-box-model`** is good design: the rule points at a better primitive
  instead of just complaining.
- The `_bg()` / `decorative` convention is the right *idea* — see issue 2 for
  where its scope is too broad.
- **`page_hashes()`** gave the deliverable a stable identity I could quote in a
  provenance record. Underrated.
- `read_document_outline`-style honesty in messages — e.g. `search_sentences`
  distinguishing "exhaustive scan, genuinely absent" from "flooded, try a rarer
  term" — is a pattern the validator messages already partly share and should
  keep.

---

## Environment

```
frameforge 2.6.0 (installed -e from git clone)
pydantic 2.13.4 · cairosvg 2.9.0 · pyphen 0.17.2
render lanes reported available: svg, png (headless Chromium), pdf (CairoSVG),
                                pdf-tex, tex, html
fonts present: DejaVu Sans/Serif/Mono, Carlito, Caladea, FreeSans/Serif/Mono,
               Bitstream Charter, GFS families, IPA Gothic
fonts absent:  Inter, Helvetica, Arial  ← all three named in default_theme().font
```
