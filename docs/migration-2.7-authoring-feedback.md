---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "OpenAI Codex (GPT-5)"
  date: "2026-07-27"
---

# Migrating 2.7 authoring and validation behavior

The 2026-07-27 authoring-feedback pass is schema-additive, but it deliberately
changes three defaults. Existing documents still parse. Automation that relied on
shallow containment, `decorative` as an off-canvas exemption, or structure-only SDK
validation must choose an explicit replacement.

## Required review

| Before | Now | Migration |
|---|---|---|
| `decorative: true` suppressed containment | `decorative` is accessibility/scoped-overlap intent only | Add `containment: allowed` to intentional bleed. `PageBuilder.bleed()` stamps both fields. |
| Containment inspected layer-top-level boxes | It descends through group-local children after layout arrangement | Fix escaped child boxes, clip the group, or explicitly consent to the group's bleed. |
| `validate_static_rules()` and CLI validation skipped text fit unless requested | Text-fit diagnostics run by default | Fix `text-truncated`/`layout-overflow`, or use `text_fit=False` / `--no-text-fit` for a deliberate structure-only fast path. |

`containment: allowed` changes audit policy only. It does not clip, move, or render
the object differently. On a group it applies to that group's subtree.

## Text measurement

SDK measurement and proxy layout now share the same metric-mode decision and the
full CSS family stack. The default is deterministic estimate mode. To use installed
font advances, pass `real_metrics=True` to measurement, validation, and rendering,
or set `FRAMEFORGE_REAL_METRICS=1` for their shared default.

Replace hand-tuned positioned-text slack with `fit_width()`:

```python
from frameforge.sdk import fit_width

family = ["Inter", "DejaVu Sans", "sans-serif"]
width = fit_width("positioned", font_family=family, font_size=13)
layer.text([40, 40, width, 20], "positioned",
           style={"font_family": family, "font_size": 13})
```

MCP clients should call `fit_text` with the same `real_metrics` mode used by the
render call. It returns `measured_width`, line-breaker-safe `fit_width`, tolerance,
and the resolved mode.

## Additive authoring forms

- `style.stroke_dasharray` accepts `[4, 4]`, `"4 4"`, or `"4, 4"`; string forms
  normalize to the canonical list. `dash` is an authoring shorthand, and
  `stroke(..., dash="4 4")` is supported.
- `white_space: pre|pre-wrap|pre-line|break-spaces` now has preserving layout
  semantics. Default `normal` continues to collapse whitespace.
- `OverflowSignal.unwrapped_width` is additive. Older wire payloads without it
  still deserialize. `needed` remains the post-layout extent at the authored box
  width.
- The `tabular-box-model` advisory now requires an at least 85%-complete grid and
  ignores text tagged `meta.role: annotation|furniture|lettering`.

No codemod is required because the wire schema remains backward compatible. Run
default validation and inspect every new advisory before accepting the migration:

```bash
uv run python tooling/validate.py document.fg.yaml
```

[↑ Back to root README](../README.md)
