---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code"
  date: "2026-07-01"
---

# Validation error codes

Every finding code the FrameGraph validators can emit, with meaning and fix.
There are two validation surfaces:

1. **The tooling validator** — `tooling/validate.py` (the `make validate` gate):
   structural model validation plus the static/semantic/geometric rules a JSON
   Schema cannot express. Severity is `ERROR` or `WARN`; `--strict` upgrades
   every `WARN` to `ERROR`. Exit codes: `0` no errors (warnings allowed), `1`
   any error, `2` load failure.
2. **The SDK validator** — `framegraph.sdk.validate.validate_static_rules()`:
   runs the tooling validator on the lowered document (re-surfacing every code
   below under `Issue.rule_id`, severities lower-cased) and layers SDK-only
   referential checks on top.

This page is kept honest by `tests/test_capability_manifest.py`, which extracts
the code strings from both validator sources and fails if any code is missing
here. The same enumeration ships machine-readably in
[`capability-manifest.json`](capability-manifest.json) under `validator`.

## Tooling validator codes (`tooling/validate.py`)

### Errors

| Code | Meaning | How to fix |
|---|---|---|
| `load` | The document file could not be parsed as YAML/JSON at all. | Fix the syntax error reported in the message; the path in the finding is the file itself. |
| `structure` | The document does not validate against the core Pydantic models (wrong field, wrong type, missing required key). | Follow the Pydantic message at the reported path; the models (`docs/models/framegraph.py`) are the source of truth. |
| `stroke-single-form` | Inline-geometry `stroke` (a dict carrying `width`/`dash`/`linecap`/`linejoin`) was removed in P3. | Put paint in `stroke` and geometry in `stroke_style`; `tooling/codemod.py` migrates this automatically. |
| `size-renamed` | Legacy `size` on a non-icon object collides with `IconObject.size`. | Rename the content-sizing key to `sizing` (the codemod does this). |
| `hug-on-shape` | `sizing: hug` on a pure shape (`rect`, `ellipse`, `line`, …) — shapes have no intrinsic content to hug. | Use a fixed dimension or `fill`. |
| `fill-under-free` | `sizing: fill` under a `free` (or absent) layout — there is no main axis to fill. | Give the parent group a `row`/`column`/`grid`/`wrap` layout, or use a fixed size. |
| `fr-under-free` | An `fr` box dimension outside a layout container. | `fr` units are only valid inside `row`/`column`/`grid` layouts; use absolute units under `free`. |
| `boxless-under-layout` | A box-less primitive (`line`, `ellipse`, `polyline`, `path`, …) is a direct child of a `row`/`column`/`grid`/`wrap` layout, so the layout has no extent to advance by. | Wrap it in a group with a `box`, or give the primitive a `box`. |
| `unpinned-font` | Content-sized text (`hug`/`fill`) references no pinned font, so its metrics are not deterministic (§9.6/P4). | Reference a `tokens.fonts` entry that has both `src` and `hash`. |
| `dangling-ref` | A reference points at nothing on its page/master scope: a connector/line/dimension `from`/`to` anchor id, a `use` symbol not in `defs.symbols`, or a master region `next` naming no region (§3.1/§3.3 referential integrity). | Declare the referenced id/symbol/region, or fix the typo — the finding message lists nearby declared candidates. |
| `unknown-master` | A page `master` (or a master's continuation `next`) is not declared in `defs.masters`. | Declare the master or correct the name. |
| `unknown-token` | A `style`/`stroke_style`/`text_style`/`class` token reference is not declared in the corresponding `defs.tokens` namespace — the renderer would silently apply no style. (The colour-valued and icon-font variants of this code are warnings, below.) | Declare the token or fix the reference. |

### Warnings

| Code | Meaning | How to fix |
|---|---|---|
| `out-of-profile` | An object/flow `type` (or a `defs.symbols`/`components`/`ontology` block) is outside the HEAD core profile; it is accepted but only loosely validated (§8.5 conformance). | Nothing, if the extension is intentional; `--strict` rejects it. |
| `grid_span-parent` | `grid_span` on an object whose parent layout is not `grid`. | Move the object under a `grid` layout or drop `grid_span`. |
| `deprecated-alias` | `circle`/`polygon`/`curve`/`bezier` are renderer-shortcut aliases. | Keep authoring them if convenient; the codemod normalises to `ellipse`/closed `polyline`/`path`. |
| `non-conformant-3d` | `style.perspective` is declared but no render target applies 3D perspective — it passes through inert. | Author 3D via the SDK `Scene3D` 2D projection (spec Appendix A.5). |
| `containment` | An object's box extends outside the page canvas (beyond a 1-unit tolerance) and is not marked `decorative`. | Move/resize the object, or set `decorative: true` for intentional bleed. |
| `overlap` | Two boxed, non-decorative siblings overlap significantly inside a no-overlap scope (a `free`-layout group or a `meta.no_overlap: true` cluster). Global/layer overlap stays legal (z-order). | Separate the boxes, or drop the `no_overlap` marker if stacking is intentional. |
| `tabular-box-model` | ≥6 absolutely-positioned text objects form a regular grid — a hand-built table. | Author it as a `row`/`column`/`grid` group or a `table` object (§3.3). |
| `text_contract-placement` | Top-level `text_contract` is a renderer convenience; the normative home is a master/page `RenderingContract.text`. | Move the contract into the master or page. |
| `canvas-unresolved` | A page's `canvas` does not resolve to a known preset or explicit size, so the containment audit is skipped for that page. | Use a `PagePreset` name or a `{size: [w, h]}` canvas object. |
| `unknown-adjustment-target` | A target's `adjustments.hide` names an id no object declares — hiding nothing is inert. | Fix the id or drop the entry. |
| `unknown-token` (warning variants) | A colour-valued key (`fill`/`stroke`/`color`/…) is neither a colour literal nor a declared `tokens.colors`/`fill_styles` key (it would pass through as an invalid SVG colour), or an `icon.font` is not declared in `tokens.fonts` (§3.5). | Declare the token, use a literal colour, or fix the reference. |

## SDK rule ids (`src/framegraph/sdk/validate.py`)

`validate_static_rules()` re-emits every tooling code above as `Issue.rule_id`
(severity `error`/`warning`), plus these SDK-only checks (all severity `error`):

| Rule id | Meaning | How to fix |
|---|---|---|
| `structure` | The built document failed model validation before any rule ran (same meaning as the tooling code; the SDK reports it per Pydantic error with a JSON-pointer path). | Fix the field named by the pointer. |
| `reference` | A dangling reference: a page `master`, `reading_order` id, image asset ref, master-region `next`, or a target-adjustment `hide` id that resolves to nothing. | Define the referenced master/asset/object id, or fix the typo. |
| `reference-cycle` | A master's region `next` chain loops back on itself, so flow content would never terminate. | Break the cycle; region chains must be linear. |
| `path-data` | A `path` object's `d` string is not parseable SVG path data (unknown command or wrong arity). | Fix the path data, or author it via `framegraph.sdk.Path` (use `object(structured=True)` for the typed G-1 segment form). |
| `target` | A target name passed to `validate_static_rules(targets=[...])` is not defined in the document's `targets`. | Add the target to the document or drop it from the call. |
| `target-adjustment` | A requested target's `adjustments.hide` hides an object that a page `reading_order` entry or a `from`/`to` anchor still references — the reference would dangle in that target's output. | Un-hide the object for that target, or remove the reading-order entry / re-anchor the connector. |

[↑ Back to root README](../README.md)
