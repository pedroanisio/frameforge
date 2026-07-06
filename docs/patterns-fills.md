---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Fable 5 via Claude Code"
  date: "2026-07-02"
---

# Patterns & fills — the declarative slide-template catalog

`framegraph.patterns` ships **375 typed layout patterns** and **17 fill
sidecars** as committed data (absorbed from the predecessor project, issue
#28; guidance adapted from its `AGENTS.md` / `AUTHORING-FILLS.md`). A pattern
declares *zones* — role, a controlled size vocabulary, placement, and a
`content_type`; a **fill** is the `{role: content}` payload that populates
one pattern. Validation is strict at both ends: the loader rejects a
malformed catalog, `load_fill` rejects a malformed payload.

Rendering is live (#29): `compose(pattern_id, fill)` returns a full,
validated document realizing the pattern on a 1920×1080 deck page — zone
boxes computed deterministically from the placement vocabulary (column
bands, quadrant grids, the BMC's mixed columns), enterprise-layout
treatments applied (cards, accent bars, label slots), content emitted per
`content_type` as plain core objects. Runnable sample:
`static/examples/pattern_compose_deck.py`.

```python
from framegraph.patterns import compose, load_sidecars
doc = compose(10, load_sidecars()[10].example_fill)   # SWOT, ready to render
```

## Loading and inspecting

```python
from framegraph.patterns import load_catalog, load_sidecars, load_fill

catalog = load_catalog()          # strict; the test gate locks the count at 375
swot = catalog.get(10)            # SlidePattern: name, category, zones
[z.role for z in swot.zones]      # ['strengths', 'weaknesses', 'opportunities', 'threats']
```

## The fill contract — default shape per `content_type`

| `content_type` | Payload shape |
|---|---|
| `title_body` | `{title: str, body?: str}` |
| `metric` | `{label: str, value: str, trend?: str}` |
| `list_items` | `list[str]` |
| `key_value` | `dict[str, str]` |
| `comparison` | `{left: str, right: str}` |
| `chart_data` | `{type: str, series: list[dict]}` |
| `table_data` | `{headers: list[str], rows: list[list[str]]}` |
| `image` | `{src: str, alt?: str}` |
| `axis_label` | `{title: str, units?: str}` |
| `decorative` | nothing — the zone takes no content |

```python
fill = load_fill(10, {
    "strengths": ["…"], "weaknesses": ["…"],
    "opportunities": ["…"], "threats": ["…"],
})
```

Unknown roles are rejected; every non-decorative content zone is required.
The error is a plain `pydantic.ValidationError` naming the zone.

## Sidecars — richer item shapes per pattern

A sidecar (`src/framegraph/patterns/data/fills/<id>-<slug>.yml`) overrides
zones with typed item shapes and carries a committed `example_fill` that the
test gate round-trips. The Business Model Canvas (44) is the proof:

```yaml
pattern_id: 44
zones:
  revenue_streams:
    item_kind: object
    item_fields:
      label:  {type: string, required: true}
      metric: {type: string, required: true}
example_fill:
  revenue_streams: [{label: "SaaS subscriptions", metric: "ARR $12m"}]
```

With the sidecar in place, `load_fill(44, …)` **enforces** the object shape —
plain strings for that zone fail validation. Authoring rules carried over
from the predecessor:

- do not hand-roll slide templates that a catalog pattern already covers;
- a fill is content, a sidecar is contract — never mix the two files;
- reach patterns through `framegraph.patterns` (the public surface), not by
  parsing the YAML yourself;
- when a zone lacks `content_type`, the fill accepts anything — prefer
  adding a sidecar override to silently freeform content.

Back to the [roadmap](roadmap.md) (item 10 / W-cross-links) and the
absorption programme (#28 → #29).
