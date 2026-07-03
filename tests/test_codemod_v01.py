"""codemod --from-v01 — the v0.1 dialect lift (issue #33).

The conversion proof for the production deck corpus: `tooling/codemod.py`
gains a `--from-v01` mode that lifts both v0.1 envelope forms into the v2
envelope, then the existing HEAD rules (P3 stroke split, stroke_styles
Style projection, gradient stops) finish the job.

- scene-form (`scene:` + `semantic:` + `visual:`) → one v2 page carrying
  the semantic block, rendering contract, tokens and layers;
- deck-form (`deck:` + `slides:`) → defs from the deck block, one page per
  slide;
- v0.1 text styles (`font`/`size`/`weight`/`v_align`/`wrap`) → v2 names —
  the same semantic trap the #32 library translation hit: the old keys
  VALIDATE as unrelated CSS props and silently render wrong.

The committed v0.1 source `tests/data/v01/genai-ecosystem.yml` is the
end-to-end regression: lift → validate → render with zero uncontained text
(the sibling repo the deck came from is slated for erasure — the corpus
conversion path must not depend on it).

Runs under pytest or standalone (``uv run python tests/test_codemod_v01.py``).
"""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs"), str(ROOT / "tooling")]

_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):  # the rendering package
    del sys.modules["framegraph"]

import codemod as C  # noqa: E402
import yaml  # noqa: E402


def _sdk():
    """Swap the models-module shadow back for the rendering package.

    Importing codemod puts docs/models first on sys.path and caches the
    MODEL module as `framegraph`; the SDK needs the package from src/.
    """
    mod = sys.modules.get("framegraph")
    if mod is not None and not hasattr(mod, "__path__"):
        del sys.modules["framegraph"]
    sys.path.insert(0, str(ROOT / "src"))
    import framegraph.sdk  # noqa: F401
    return sys.modules["framegraph"].sdk

V01_SCENE = {
    "dsl": "FrameGraph",
    "version": 1.5,
    "kind": "hybrid-semantic-visual-diagram",
    "scene": {
        "id": "probe",
        "name": "Probe scene",
        "description": "A one-scene v0.1 document.",
        "canvas": {"size": [640, 360], "units": "px"},
        "rendering_contract": {
            "coordinate_mode": "absolute",
            "preserve_manual_line_breaks": True,
            "text": {"min_font_size": 9, "overflow": "shrink_to_fit"},
            "semantics": {"decorative_objects_may_omit_bind": True},
        },
    },
    "semantic": {
        "ontology": {"node_types": {"hub": {"description": "hub"}}},
        "nodes": [{"id": "n1", "type": "hub"}],
        "edges": [],
    },
    "visual": {
        "tokens": {
            "colors": {"ink": "#111111", "paper": "#ffffff"},
            "fonts": {"primary": "Helvetica, Arial, sans-serif"},
            "text_styles": {
                "title": {"font": "primary", "size": 20, "weight": 700,
                          "color": "ink", "align": "left", "v_align": "top",
                          "wrap": True},
            },
            "stroke_styles": {
                "dashed": {"color": "ink", "width": 1.25, "dash": [4, 4]},
            },
        },
        "layers": [
            {"id": "main", "z": 0, "objects": [
                {"type": "rect", "id": "card", "box": [10, 10, 200, 100],
                 "fill": "paper",
                 "stroke": {"color": "ink", "width": 1.0}, "radius": 6,
                 "bind": "n1"},
                {"type": "text", "id": "t", "box": [10, 120, 200, 30],
                 "text": "hello", "style": "title"},
                {"type": "line", "id": "l", "from": [0, 0], "to": [10, 10],
                 "stroke_style": "dashed", "decorative": True},
            ]},
        ],
    },
}

V01_DECK = {
    "dsl": "FrameGraph",
    "version": 1.5,
    "kind": "presentation-deck",
    "deck": {
        "canvas": {"size": [1920, 1080], "units": "px"},
        "component_defs": {"chip": {"fill": "ink"}},
        "tokens": {"colors": {"ink": "#111111", "bg": "#ffffff"}},
    },
    "slides": [
        {"slide": 1, "id": "cover", "title": "Cover", "notes": "n",
         "visual": {"layers": [
             {"id": "bg", "z": 0, "objects": [
                 {"type": "rect", "id": "f", "box": [0, 0, 1920, 1080],
                  "fill": "bg", "decorative": True}]}]}},
        {"slide": 2, "id": "body",
         "visual": {"layers": [
             {"id": "main", "objects": [
                 {"type": "text", "id": "t", "box": [80, 80, 800, 60],
                  "text": "Body", "style": {"font_size": 30,
                                            "color": "ink"}}]}]}},
    ],
}


def _lift(doc):
    stats = C.Stats()
    out = C.lift_v01(copy.deepcopy(doc), stats)
    return out, stats


# ── scene form ──────────────────────────────────────────────────────────


def test_scene_form_lifts_to_v2_envelope():
    out, _ = _lift(V01_SCENE)
    assert out["version"] == C.HEAD_VERSION
    assert out["title"] == "Probe scene"
    assert out["description"] == "A one-scene v0.1 document."
    assert out["profile"] == "diagram"
    assert out["meta"]["kind"] == "hybrid-semantic-visual-diagram"
    assert "scene" not in out and "visual" not in out and "kind" not in out
    page = out["pages"][0]
    assert page["mode"] == "page" and page["id"] == "probe"
    assert page["canvas"] == {"size": [640, 360], "units": "px"}
    assert page["rendering"]["coordinate_mode"] == "absolute"
    assert page["rendering"]["text"] == {"min_font_size": 9,
                                         "overflow": "shrink_to_fit"}
    assert page["semantic"]["nodes"] == [{"id": "n1", "type": "hub"}]
    assert page["layers"][0]["id"] == "main"


def test_scene_form_translates_v01_text_styles():
    out, _ = _lift(V01_SCENE)
    style = out["defs"]["tokens"]["text_styles"]["title"]
    assert style["font_family"] == ["Helvetica", "Arial", "sans-serif"]
    assert style["font_size"] == 20 and style["font_weight"] == 700
    assert style["vertical_align"] == "top"
    assert not {"font", "size", "weight", "v_align", "wrap"} & set(style)


def test_scene_form_rewrites_stroke_style_bundles():
    out, _ = _lift(V01_SCENE)
    dashed = out["defs"]["tokens"]["stroke_styles"]["dashed"]
    assert dashed == {"stroke": "ink", "stroke_width": 1.25,
                      "stroke_dasharray": [4, 4]}


def test_scene_form_splits_inline_object_strokes():
    out, _ = _lift(V01_SCENE)
    card = out["pages"][0]["layers"][0]["objects"][0]
    assert card["stroke"] == "ink"
    assert card["stroke_style"] == {"stroke_width": 1.0}
    assert card["bind"] == "n1"                      # semantics preserved


def test_lifted_scene_document_validates():
    out, _ = _lift(V01_SCENE)
    _sdk().model.validate_document(out)


# ── deck form ───────────────────────────────────────────────────────────


def test_deck_form_lifts_slides_to_pages():
    out, _ = _lift(V01_DECK)
    assert out["profile"] == "deck"
    assert out["defs"]["tokens"]["colors"]["ink"] == "#111111"
    assert out["defs"]["components"] == {"chip": {"fill": "ink"}}
    assert [p["id"] for p in out["pages"]] == ["cover", "body"]
    cover = out["pages"][0]
    assert cover["mode"] == "page"
    assert cover["canvas"] == {"size": [1920, 1080], "units": "px"}
    assert cover["meta"]["title"] == "Cover" and cover["meta"]["slide"] == 1
    assert cover["notes"] == "n"
    assert "slides" not in out and "deck" not in out


def test_lifted_deck_document_validates():
    out, _ = _lift(V01_DECK)
    _sdk().model.validate_document(out)


# ── guards ──────────────────────────────────────────────────────────────


def test_v2_document_passes_through_unchanged():
    v2 = {"dsl": "FrameGraph", "version": "2.3.0", "title": "already v2",
          "pages": [{"mode": "page", "id": "p",
                     "layers": [{"id": "m", "objects": []}]}]}
    out, stats = _lift(v2)
    assert out == v2 and stats.v01 == 0


def test_lift_counts_in_stats():
    _, stats = _lift(V01_SCENE)
    assert stats.v01 == 1


# ── the committed corpus proof ──────────────────────────────────────────


GENAI = HERE / "data" / "v01" / "genai-ecosystem.yml"


def test_genai_ecosystem_migrates_end_to_end():
    """Issue #33's first acceptance criterion, as a test: the committed v0.1
    production diagram lifts, validates, and renders with zero uncontained
    text — without touching the sibling repo."""
    sdk = _sdk()
    doc = yaml.safe_load(GENAI.read_text(encoding="utf-8"))
    stats = C.Stats()
    out = C.lift_v01(doc, stats)
    assert stats.v01 == 1
    sdk.model.validate_document(out)

    page = out["pages"][0]
    assert page["semantic"]["nodes"], "semantic layer must survive the lift"
    binds = [o for layer in page["layers"] for o in layer["objects"]
             if o.get("bind")]
    assert len(binds) >= 10, "object→semantic bindings must survive"

    svgs, rstats = sdk.render_pages_with_stats(out, base_dir=str(ROOT))
    assert len(svgs) == 1
    assert rstats.get("uncontained", 0) == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
