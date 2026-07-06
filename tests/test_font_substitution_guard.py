"""drift-risk-map #7 — the font-substitution guard must keep working.

Layout is *measured* with font_metrics (fontTools + fc-match) but *rendered* by a
different engine; `fg-font --check` is the guard that flags when a document's
declared font substitutes to a different face (ADR-0004). Nothing locked that
guard's behaviour, so it could silently stop detecting substitutions. These tests
pin it: a family that resolves to itself is clean, a family fontconfig cannot
match is flagged as a substitution, and the document font-extraction that feeds
the guard works.

A full CI gate over the committed corpus is deliberately NOT added here: the b1
oracle itself substitutes 'Georgia' -> 'Noto Serif' in a bare runtime, so gating
the whole corpus would fail on font *availability* rather than on real drift. The
structural fix is single-engine rendering + font-packs (ADR-0004); this test locks
the detector so it cannot regress silently.
"""
from __future__ import annotations

import sys
from pathlib import Path

_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest  # noqa: E402
from framegraph import fontpack  # noqa: E402


def _fontconfig_ready() -> bool:
    try:
        return fontpack._resolve("DejaVu Sans", False)[0] is not None
    except Exception:
        return False


needs_fc = pytest.mark.skipif(
    not _fontconfig_ready(),
    reason="fontconfig / font_metrics not available in this runtime")


def test_referenced_families_extracts_declared_fonts():
    """The doc-walk that feeds the guard finds token + inline font families."""
    doc = {"defs": {"tokens": {"fonts": {"ui": {"family": "Inter"}}}},
           "pages": [{"layers": [{"objects": [
               {"type": "text", "text": "x", "style": {"font_family": "DejaVu Sans"}}]}]}]}
    assert {"Inter", "DejaVu Sans"} <= set(fontpack.referenced_families(doc))


@needs_fc
def test_self_resolving_family_is_clean():
    resolved, matched, _ = fontpack._resolve("DejaVu Sans", False)
    assert matched is True, "a base-installed family must match exactly (no substitution)"
    assert resolved == "DejaVu Sans"


@needs_fc
def test_unknown_family_is_detected_as_a_substitution():
    fam = "NoSuchFont_ZZZ_9999"
    resolved, matched, _ = fontpack._resolve(fam, False)
    # the guard's substitution signal: no exact match AND a different face returned
    assert matched is False, "an unknown family must not report an exact match"
    assert resolved != fam, "an unknown family must resolve to a different (substitute) face"
