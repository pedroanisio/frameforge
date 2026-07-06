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
    # a cached framegraph.sdk is not re-attached to a re-imported parent —
    # take the submodule from sys.modules, never as a parent attribute
    return sys.modules["framegraph.sdk"]

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
    # v0.1 deck text was painted past its box, never truncated — the lift
    # pins that semantics explicitly (v2 defaults to wrap-then-clip)
    assert cover["rendering"] == {"text": {"overflow": "visible"}}


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


# ── chip_row lowering (the PALS dialect corner) ─────────────────────────


V01_CHIP_DECK = {
    "dsl": "FrameGraph",
    "version": 1.5,
    "kind": "presentation-deck",
    "deck": {
        "canvas": {"size": [1920, 1080], "units": "px"},
        "component_defs": {
            "chip": {"fill": "brand_s", "text_style": "tag_bc",
                     "geometry": {"radius": 6}}},
        "tokens": {"colors": {"brand_s": "#DBEAFE"}},
    },
    "slides": [
        {"slide": 1, "id": "chips",
         "visual": {"layers": [{"id": "main", "objects": [
             {"type": "chip_row", "id": "err_chips",
              "origin": [80, 208], "gap": 20, "height": 36,
              "items": [{"text": "ERR_HALLUCINATION", "width": 176},
                        {"text": "ERR_OMISSION", "width": 176},
                        "PLAIN"]}]}]}},
    ],
}


def test_chip_row_lowers_to_a_core_group():
    """v0.1's compositional `chip_row` has no v2 counterpart — the lift
    lowers it to a group of pill rects + centered texts using the chip
    component def (fill, text_style, corner radius), left-to-right with
    the declared gap; string items auto-size like the v0.1 renderer
    (max(20, len*6+12))."""
    out, _ = _lift(V01_CHIP_DECK)
    objs = out["pages"][0]["layers"][0]["objects"]
    assert len(objs) == 1
    row = objs[0]
    assert row["type"] == "group" and row["id"] == "err_chips"
    kids = row["children"]
    assert len(kids) == 6                       # rect+text per item
    r1, t1, r2, t2, r3, t3 = kids
    assert r1 == {"type": "rect", "box": [80, 208, 176, 36],
                  "fill": "brand_s", "radius": 6, "decorative": True}
    assert t1 == {"type": "text", "box": [80, 208, 176, 36],
                  "text": "ERR_HALLUCINATION", "style": "tag_bc"}
    assert r2["box"] == [80 + 176 + 20, 208, 176, 36]      # cursor + gap
    auto_w = max(20, len("PLAIN") * 6 + 12)
    assert r3["box"] == [80 + 2 * (176 + 20), 208, auto_w, 36]
    assert t3["text"] == "PLAIN"


def test_chip_row_consumed_component_defs_are_dropped():
    """chip_row was the only consumer: once lowered, defs.components would
    be dead weight (and out-of-profile) — the lift drops it unless real
    `component` objects remain."""
    out, _ = _lift(V01_CHIP_DECK)
    assert "components" not in (out.get("defs") or {})


def test_chip_row_lowered_deck_validates():
    out, _ = _lift(V01_CHIP_DECK)
    _sdk().model.validate_document(out)


def test_v01_flat_stroke_width_moves_to_stroke_style():
    """v0.1 allowed `stroke_width` flat on an object next to `stroke`; in
    v2 stroke geometry lives in stroke_style (P3)."""
    doc = copy.deepcopy(V01_SCENE)
    doc["visual"]["layers"][0]["objects"].append(
        {"type": "rect", "id": "outline", "box": [5, 5, 50, 50],
         "fill": "none", "stroke": "ink", "stroke_width": 0.5, "radius": 8})
    out, _ = _lift(doc)
    rect = out["pages"][0]["layers"][0]["objects"][-1]
    assert "stroke_width" not in rect
    assert rect["stroke"] == "ink"
    assert rect["stroke_style"] == {"stroke_width": 0.5}
    _sdk().model.validate_document(out)


def test_v01_flat_span_styles_are_nested():
    """v0.1 spans carry style keys flat on the span ({text, weight, color});
    v2 Span allows only text/style/lang — the extras become a translated
    inline style."""
    doc = copy.deepcopy(V01_SCENE)
    doc["visual"]["layers"][0]["objects"].append(
        {"type": "text", "id": "eq", "box": [10, 160, 200, 30],
         "style": "title",
         "spans": [{"text": "bold bit", "weight": 700, "color": "ink"},
                   {"text": "plain bit", "size": 14}]})
    out, _ = _lift(doc)
    spans = out["pages"][0]["layers"][0]["objects"][-1]["spans"]
    assert spans[0] == {"text": "bold bit",
                        "style": {"font_weight": 700, "color": "ink"}}
    assert spans[1] == {"text": "plain bit", "style": {"font_size": 14}}
    _sdk().model.validate_document(out)


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


def test_v01_gradient_fill_styles_translate_to_v2_paints():
    """PT-BR corner: v0.1 `tokens.fill_styles` gradient defs
    ({type: linear_gradient, from/to points, stops with offset+opacity})
    become v2 Gradient paints — kind/angle/position, stop opacity folded
    into an 8-digit hex against the deck palette (v2 stops carry no
    opacity field)."""
    doc = copy.deepcopy(V01_DECK)
    doc["deck"]["tokens"]["colors"]["white"] = "#ffffff"
    doc["deck"]["tokens"]["fill_styles"] = {
        "bg_soft": {"type": "linear_gradient", "from": [0, 0], "to": [0, 1],
                    "stops": [{"offset": 0, "color": "ink"},
                              {"offset": 1, "color": "white",
                               "opacity": 0.85}]}}
    out, _ = _lift(doc)
    grad = out["defs"]["tokens"]["fill_styles"]["bg_soft"]
    assert grad["kind"] == "linear"
    assert grad["angle"] == 180                     # (0,0)→(0,1) = to bottom
    assert "from" not in grad and "to" not in grad and "type" not in grad
    s0, s1 = grad["stops"]
    assert s0 == {"color": "ink", "position": "0%"}
    assert s1["position"] == "100%"
    assert s1["color"].lower() == "#ffffffd9"       # alpha 0.85 folded
    _sdk().model.validate_document(out)


def test_fill_style_tokens_render_as_gradients():
    """Renderer gap found by this corner: Tokens.fill_styles exists in the
    model but the renderer never dereferenced it — `fill: bg_soft` silently
    emitted an invalid SVG paint. A string fill naming a fill_styles key
    must resolve to its gradient."""
    sdk = _sdk()
    doc = {"dsl": "FrameGraph", "version": C.HEAD_VERSION, "title": "g",
           "profile": "diagram",
           "defs": {"tokens": {
               "colors": {"ink": "#1d1e22"},
               "fill_styles": {"fade": {"kind": "linear", "angle": 180,
                                        "stops": [
                                            {"color": "#ffffff",
                                             "position": "0%"},
                                            {"color": "#1d1e22",
                                             "position": "100%"}]}}}},
           "pages": [{"mode": "page", "id": "p",
                      "canvas": {"size": [200, 100], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "m", "objects": [
                          {"type": "rect", "box": [10, 10, 180, 80],
                           "fill": "fade"}]}]}]}
    svgs, _ = sdk.render_pages_with_stats(doc, base_dir=str(ROOT))
    assert "linearGradient" in svgs[0]
    assert 'fill="url(#' in svgs[0]


PTBR = HERE / "data" / "v01" / "pals-genai-arch-deck-pt-br.yml"


def test_pals_ptbr_deck_migrates_end_to_end():
    """#33 checklist: the 15-slide PT-BR deck — gradient fill tokens, one
    chip_row, 383 rects — lifts, validates, and renders with no silent
    content loss."""
    sdk = _sdk()
    doc = yaml.safe_load(PTBR.read_text(encoding="utf-8"))
    stats = C.Stats()
    out = C.lift_v01(doc, stats)
    assert stats.v01 == 1
    sdk.model.validate_document(out)
    assert len(out["pages"]) == 15
    fills = out["defs"]["tokens"]["fill_styles"]
    assert all(g.get("kind") == "linear" for g in fills.values())

    svgs, rstats = sdk.render_pages_with_stats(out, base_dir=str(ROOT))
    assert len(svgs) == 15
    assert rstats.get("clipped", 0) == 0
    assert rstats.get("uncontained", 0) == rstats.get("visible_overflow", 0)
    joined = "\n".join(svgs)
    assert "linearGradient" in joined, "gradient tokens must actually paint"


PALS = HERE / "data" / "v01" / "pals-genai-architecture-deck.yml"


def test_pals_en_deck_migrates_end_to_end():
    """#33 checklist: the 8-slide PALS EN production deck lifts through the
    deck/slides form, validates, and renders every page — chip_row lowered,
    disclaimer frontmatter preserved in meta."""
    sdk = _sdk()
    doc = yaml.safe_load(PALS.read_text(encoding="utf-8"))
    stats = C.Stats()
    out = C.lift_v01(doc, stats)
    assert stats.v01 == 1
    sdk.model.validate_document(out)

    assert len(out["pages"]) == 8
    assert out["profile"] == "deck"
    assert "disclaimer" in out["meta"], "provenance must ride in meta"

    def walk(objs):
        for o in objs:
            yield o
            yield from walk(o.get("children") or [])

    texts = [str(o.get("text", "")) for p in out["pages"]
             for layer in p["layers"] for o in walk(layer["objects"])
             if o.get("type") == "text"]
    joined = "\n".join(texts)
    assert "ERR_HALLUCINATION" in joined      # the lowered chip_row
    assert all(o.get("type") != "chip_row"
               for p in out["pages"] for layer in p["layers"]
               for o in walk(layer["objects"]))

    svgs, rstats = sdk.render_pages_with_stats(out, base_dir=str(ROOT))
    assert len(svgs) == 8
    # v0.1 semantics: content may spill its authoring box (explicit
    # overflow:visible — permitted by the corpus gate) but must NEVER be
    # silently truncated: no contained-policy spill, nothing clipped.
    assert rstats.get("clipped", 0) == 0
    assert rstats.get("uncontained", 0) == rstats.get("visible_overflow", 0)
    # the regression that motivated the policy: the slide-3 consequence
    # sentence was silently truncated mid-word under the v2 clip default —
    # the RENDERED svg must carry it to the last glyph
    assert "structural ones." in svgs[2]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
