"""Font resolution must be browser-faithful, and a substitution must SCREAM.

The root defect these guard (ADR-0004): layout measures with `font_metrics`
(fontTools + fc-match) while the rasterizer resolves the family itself. fc-match
fuzzy-returns *some* face for any name, so an uninstalled family silently
measured a different font than gets drawn. Resolution now walks the chain like a
browser (rejecting fuzzy fallbacks), and a genuine substitution warns loudly.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from framegraph.rendering.infrastructure import font_metrics as fmmod  # noqa: E402
from tooling.render_fixtures import Renderer  # noqa: E402


def test_is_real_match_rejects_fontconfig_fuzzy_fallback():
    assert fmmod._is_real_match("Charter", "Noto Sans") is False        # unrelated fuzzy face
    assert fmmod._is_real_match("Bitstream Charter", "Bitstream Charter") is True
    assert fmmod._is_real_match("Charter", "Bitstream Charter") is True  # tokens ⊆ resolved
    assert fmmod._is_real_match("Helvetica", "Nimbus Sans") is False
    assert fmmod._is_real_match("Anything", None) is False


def test_resolve_report_flags_missing_concrete_font():
    resolved, matched, requested = fmmod.resolve_report("ZzzNoSuchFace, YyyAlsoNone, serif")
    assert requested == "ZzzNoSuchFace"
    assert matched is False                          # every concrete family missing → hazard
    _, matched_generic, req_generic = fmmod.resolve_report("serif")
    assert matched_generic is True and req_generic is None    # generic-only: default by design


def test_renderer_screams_on_font_substitution(capsys):
    doc = {"pages": [{
        "mode": "page", "id": "p", "canvas": {"size": [300, 120], "units": "px"},
        "layers": [{"id": "l", "objects": [
            {"type": "text", "box": [10, 10, 280, 40], "text": "hello world",
             "style": {"font_family": ["ZzzNoSuchFace", "serif"], "font_size": 12}}]}],
    }]}
    r = Renderer(doc, ".", real_metrics=True)
    r.render_page(doc["pages"][0])
    err = capsys.readouterr().err
    assert "FONT SUBSTITUTION" in err                # loud, on stderr — cannot be missed
    assert any(w["kind"] == "font_substitution" for w in r.diagnostics["warnings"])


def test_estimate_mode_does_not_warn(capsys):
    # real_metrics off (golden/proxy estimate mode) → font_metrics is not consulted,
    # so there is nothing to substitute and nothing to warn about.
    doc = {"pages": [{
        "mode": "page", "id": "p", "canvas": {"size": [300, 120], "units": "px"},
        "layers": [{"id": "l", "objects": [
            {"type": "text", "box": [10, 10, 280, 40], "text": "hello world",
             "style": {"font_family": ["ZzzNoSuchFace", "serif"], "font_size": 12}}]}],
    }]}
    Renderer(doc, ".", real_metrics=False).render_page(doc["pages"][0])
    assert "FONT SUBSTITUTION" not in capsys.readouterr().err
