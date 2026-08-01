---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 5 (1M context) via Claude Code"
  date: "2026-07-31"
---

# Migrating inert stroke declarations

The 2026-07-31 paint-intent pass is schema-additive and changes no rendered
byte. It adds a validator warning and a render diagnostics channel for a defect
that previously passed every gate in silence.

## The defect

A stroke-painted shape declares its stroke inside `style` using the shape of the
**pre-P3 bundle**:

```yaml
- type: line
  from: [64, 44]
  to:   [730, 44]
  style: {color: '#d5d0c6', width: 1}     # ← reads as text colour + box width
```

This **validates**. `Style` really does carry `color`, `width` and `dash` — but
on a shape they mean CSS `color` (text), CSS `width` (box) and a dash unrelated
to `stroke_dasharray`. None of them is stroke paint, so the authored appearance
is discarded and the shape is painted by the engine's fallback instead:

| Object type | What renders |
|---|---|
| `line`, `connector` | `stroke="#000" stroke-width="1"` — wrong colour **and** wrong weight, but visible, so it survives visual review |
| `polyline`, `polygon`, `path`, `curve`, `bezier` | `fill="none"` with **no stroke** — the shape paints zero ink and is invisible while remaining in model, validation and SVG |

This is the stroke twin of the failure the v0.1 lift already handles for text
styles, where `size`/`weight` validate as unrelated CSS properties.

## Required change

Use the P3 single form — paint in `stroke`, geometry in `stroke_style`:

```yaml
- type: line
  from: [64, 44]
  to:   [730, 44]
  stroke: '#d5d0c6'
  stroke_style: {stroke_width: 1}
```

An inline `style` bag works too, as long as the keys are the stroke ones:

```yaml
  style: {stroke: '#d5d0c6', stroke_width: 1}
```

### Mechanically

```bash
uv run python tooling/codemod.py doc.fg.yaml --in-place --fix-inert-stroke
```

The migration is idempotent and scoped: it rewrites only objects where the
validator fires, so `style.color` on a `text` object — the correct way to colour
text — is left alone. An object whose `style` is a **shared token reference** is
reported but not rewritten, because editing the token would change every other
object that uses it; fix those by hand.

## Finding it

| Surface | What it reports |
|---|---|
| `validate.py` | WARN `inert-stroke-declaration`, with the exact replacement in the message. `--strict` makes it an ERROR. No render needed. |
| `diagnostics.paint` | The resolved half: `invisible-shape` (paints nothing) and `injected-stroke-default` (info: the `#000` substitution fired) |
| `sdk.paint_report(doc)` | The same signals as typed `PaintSignal` values; `signal.remedy` is copy-pasteable |
| `--to audit` | A `paint` section, plus `invisible-shape` / `inert-stroke-declaration` health flags |
| MCP render result | `design.unpainted` counts blind shapes; `render_warning` names the first one |

Only the static rule gates. Invisibility is deliberately **not** decided
statically: paint can arrive from a group style, a token, or a stroke-outline
lowering, and a static guess produced 124 false positives on the committed
fixture corpus against 0 for the static rule. See
[ADR-0006](adr-0006-no-injected-style.md#amendment-2026-07-31--the-shape-fallbacks-are-documented-and-observable).

## What did not change

The `#000` fallback still fires and the unfilled open shapes still paint
nothing. The golden corpus depends on those bytes, and substituting a different
guess would be a new injection rather than a smaller one. The change is that
both are now observable — a fallback the author cannot see is indistinguishable
from one the engine invented.

---

← Back to the [documentation index](index.md).
