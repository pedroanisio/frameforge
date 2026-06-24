#!/usr/bin/env python3
"""Fail if ``docs/BRAND.md``'s colour palette drifts from the canonical token file.

The brand tokens live in ``brand/framegraph.tokens.fg.yaml`` (the source of
truth). ``docs/BRAND.md`` documents the same palette in prose. This gate compares
the two as the *set* of ``#RRGGBB`` hex values (case-insensitive): every canonical
token colour must appear in BRAND.md, and BRAND.md must introduce no colour that
is not a canonical token. A token edit that is not mirrored into the brand doc —
or a rogue colour pasted into the doc — fails the gate.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKENS = ROOT / "brand" / "framegraph.tokens.fg.yaml"
BRAND = ROOT / "docs" / "BRAND.md"
HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def hex_set(path: Path) -> set[str]:
    return {h.upper() for h in HEX.findall(path.read_text(encoding="utf-8"))}


def main() -> int:
    tokens = hex_set(TOKENS)
    brand = hex_set(BRAND)
    missing = tokens - brand  # canonical token absent from BRAND.md
    rogue = brand - tokens    # colour in BRAND.md that is not a canonical token
    if missing or rogue:
        print("check_brand_sync: docs/BRAND.md palette drifted from "
              "brand/framegraph.tokens.fg.yaml")
        if missing:
            print("  token colours missing from BRAND.md:", ", ".join(sorted(missing)))
        if rogue:
            print("  non-token colours in BRAND.md:", ", ".join(sorted(rogue)))
        return 1
    print(f"check_brand_sync: OK — BRAND.md palette matches the {len(tokens)} "
          "canonical tokens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
