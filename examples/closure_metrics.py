"""Render a one-page probe with one portable metrics provider."""
from __future__ import annotations

import argparse
import json

from frameforge_sdk import DocumentBuilder, closure_metrics, fit_width

from frameforge.conform import page_hashes, render_pages_with_stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("closure")
    parser.add_argument("family")
    parser.add_argument("--generic", default="sans-serif")
    args = parser.parse_args()

    provider = closure_metrics(
        args.closure,
        strict=True,
        generics={args.generic: args.family},
    )
    text = "Portable measurement"
    width = fit_width(
        text, font_family=args.family, font_size=18,
        metrics_provider=provider)
    builder = DocumentBuilder(title="closure probe", profile="diagram")
    layer = builder.page(
        "p1", canvas={"size": [320, 120], "units": "px"},
        coordinate_mode="absolute").layer("content")
    layer.text(
        [20, 30, width, 30], text,
        style={"font_family": args.family, "font_size": 18})
    document = builder.build()
    _svgs, stats, diagnostics = render_pages_with_stats(
        document, metrics_provider=provider, diagnostics=True)
    print(json.dumps({
        "metrics_mode": diagnostics["metrics_mode"],
        "hashes": page_hashes(document, metrics_provider=provider),
        "text_fit": stats,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
