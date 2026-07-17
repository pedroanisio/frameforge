"""Table column-width resolution (pure).

Ported from the legacy renderer's `_resolve_widths` (frameforge/renderers/table.py)
and extended for the v2 `ColumnSpec.width` Length, which is `number | "<n>%" |
"<n>fr" | "auto"` (models L661; Length = float | int | str). The current proxy
`_table` resolved only numeric px widths — `num("30%")` returns None, so percent /
fr / auto columns silently collapsed to an equal free-split. This resolver makes
the width hints first-class.

Distribution:
  * a positive number          → fixed px
  * "<n>%"                      → that fraction of the table width
  * "<n>fr"                     → a flexible weight (default 1 if bare/0)
  * None / 0 / "auto" / other   → a flexible weight of 1
Flexible columns share the width left after the fixed + percent columns, in
proportion to their weights. With only numeric / auto columns this reduces to the
previous behaviour (fixed px, else equal split), so existing fixtures are
unchanged.
"""
from __future__ import annotations


def resolve_column_widths(cols, ncol: int, total: float) -> list[float]:
    cols = list(cols or [])
    cols += [None] * (ncol - len(cols))
    cols = cols[:ncol]

    widths: list[float | None] = [None] * ncol
    weights: list[float] = [0.0] * ncol     # flexible (fr / auto) share weights
    consumed = 0.0
    for i, c in enumerate(cols):
        spec = c.get("width") if isinstance(c, dict) else c
        if isinstance(spec, (int, float)) and not isinstance(spec, bool) and spec > 0:
            widths[i] = float(spec)
            consumed += widths[i]
        elif isinstance(spec, str) and spec.strip().endswith("%"):
            try:
                w = total * float(spec.strip()[:-1]) / 100.0
            except ValueError:
                w = 0.0
            widths[i] = w
            consumed += w
        elif isinstance(spec, str) and spec.strip().endswith("fr"):
            try:
                weights[i] = float(spec.strip()[:-2])
            except ValueError:
                weights[i] = 1.0
            if weights[i] <= 0:
                weights[i] = 1.0
        else:                               # None / 0 / "auto" / unrecognised → 1fr
            weights[i] = 1.0

    remaining = max(0.0, total - consumed)
    wtotal = sum(weights)
    if wtotal > 0:
        for i in range(ncol):
            if widths[i] is None:
                widths[i] = remaining * weights[i] / wtotal
    return [w if w is not None else 0.0 for w in widths]
