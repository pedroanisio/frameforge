---
disclaimer: >
  No information within this document should be taken for granted. Verify all
  commands against your environment before relying on them.
last_verified: 2026-08-01
tool_versions:
  - tool: frameforge
    version: 2.8.2
---

# How to align author-time and render-time font metrics

## Overview

Use this guide when SDK-sized boxes wrap or truncate differently during
rendering. The end state uses one strict `.fp` closure provider across SDK
measurement, static validation, SVG/HTML rendering, reports, and goldens.

## Prerequisites

1. Install the repository groups: `uv sync --group metrics`.
2. Export a `.fp` containing every family/weight used by the document.
3. Record concrete replacements for any CSS generic-only family.

## Steps

### Step 1: Create the provider

```python
from frameforge_sdk import closure_metrics

provider = closure_metrics(
    "book.fp",
    store_root=".frameforge-font-store",
    strict=True,
    generics={"sans-serif": "Inter"},
)
```

### Step 2: Reuse it during composition and validation

```python
from frameforge_sdk import fit_width, validate_static_rules

width = fit_width(
    copy, font_family="Inter", font_size=12,
    metrics_provider=provider)
report = validate_static_rules(doc, metrics_provider=provider)
assert report.ok
```

### Step 3: Reuse it at every render entry point

```python
from frameforge.conform import page_hashes, render_html, render_pages_with_stats

svgs, stats, diagnostics = render_pages_with_stats(
    doc, metrics_provider=provider, diagnostics=True)
html = render_html(doc, metrics_provider=provider)
hashes = page_hashes(doc, metrics_provider=provider)
assert diagnostics["metrics_mode"] == "closure"
```

## Verification

Repeat the render using a second empty `store_root`. The page hashes must match
and strict closure loading must select the same face SHA-256 values.

## Troubleshooting

- `closure_metrics() requires the metrics extra`: run
  `uv sync --group metrics` or install `frameforge-sdk[metrics]`.
- `no face in the closure satisfies ...`: add that face/weight or fix the
  generic map; do not switch a golden/CI run to permissive mode.
- `ModuleNotFoundError: frameforge_render`: sync the updated core dependencies
  or install `frameforge-render>=1.0,<2`.
