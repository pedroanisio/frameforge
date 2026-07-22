#!/usr/bin/env python3
"""Canvas preset DIMENSIONS stated in the spec prose match the engine.

Drift-risk-map HIGH #5: the preset *keys* are lockstep-pinned across seven
sites, but the `W×H` numbers hand-typed in the spec's §4 prose had no reader —
change a preset dimension and the spec keeps teaching the old numbers under a
green `make check`. This gate parses every `name W×H` pair the spec source
states and compares it against `CanvasResolver` `PRESETS` (docs/spec.md is
generated from this source, so one gate covers both rendered copies).
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.domain.services.canvas_resolver import PRESETS  # noqa: E402

SPEC_SRC = os.path.join(ROOT, "docs", "spec", "frameforge-v2-spec.md")

# `name W×H` — the name may be backticked and separated from its dims by
# whitespace (including a line break inside a flowed paragraph).
_PAIR = re.compile(r"`?([a-z0-9][a-z0-9-]*)`?\s+(\d+)\s*[×x]\s*(\d+)")


def _stated_pairs():
    with open(SPEC_SRC, encoding="utf-8") as fh:
        spec = fh.read()
    m = re.search(r"## 4\. Canvas & presets.*?(?=\n## )", spec, re.S)
    assert m, "spec '## 4. Canvas & presets' section moved — update this test"
    return [(name, int(w), int(h)) for name, w, h in _PAIR.findall(m.group(0))
            if name in PRESETS]


def test_the_parser_actually_finds_stated_dims():
    pairs = _stated_pairs()
    assert len(pairs) >= 15, (
        f"only {len(pairs)} preset dims parsed from the spec — the prose "
        "format changed; update _PAIR so the gate keeps reading them")


def test_every_stated_preset_dimension_matches_the_engine():
    wrong = []
    for name, w, h in _stated_pairs():
        actual = tuple(PRESETS[name])
        # Book trims are stated in inches (`book-6x9` 6×9); the engine stores
        # pt — accept the exact ×72 equivalence alongside literal dims.
        if (w, h) != actual and (w * 72, h * 72) != actual:
            wrong.append(f"spec says {name} {w}×{h}; PRESETS has "
                         f"{actual[0]}×{actual[1]}")
    assert not wrong, "spec §4 states stale preset dimensions:\n" + "\n".join(wrong)
