"""frameforge.library — consulting themes, symbol packs, generators (issue #32).

The absorbed content library: 7 consulting token packs translated to v2
`defs.tokens` fragments, the general-purpose symbol packs (cover, agenda
pane, insight box, hex cells …) expandable through `sdk.expand`, and the two
data-driven generators (honeycomb capability map, radial module hub) that
reproduce full pages from committed example data. Acceptance gates from the
issue: every theme loads/validates/renders; every symbol expands with zero
uncontained text; generators reproduce from their example data.

Runs under pytest or standalone (``uv run python tests/test_library.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from frameforge.library import (  # noqa: E402
    EXAMPLES_DIR,
    honeycomb_capability_map,
    list_symbols,
    list_themes,
    load_example,
    load_symbols,
    load_theme,
    module_hub_radial,
    support_text_styles,
)
from frameforge.sdk import render_pages_with_stats  # noqa: E402
from frameforge.sdk.model import HEAD_VERSION, validate_document  # noqa: E402

THEMES = ("bain", "bcg", "deloitte", "ey", "kpmg", "mckinsey", "pwc")
V01_STYLE_KEYS = {"font", "size", "weight", "v_align", "wrap"}


def _walk(objs):
    for obj in objs:
        yield obj
        yield from _walk(obj.get("children") or [])


def _objects(doc):
    for page in doc["pages"]:
        for layer in page["layers"]:
            yield from _walk(layer["objects"])


def _texts(doc):
    out = []
    for obj in _objects(doc):
        if obj.get("type") == "text":
            out.append(str(obj.get("text", "")))
        if obj.get("type") == "bullet_list":
            out.extend(str(i) for i in obj.get("items", []))
    return "\n".join(out)


def _assert_contained(doc):
    svgs, stats = render_pages_with_stats(doc, base_dir=str(ROOT))
    assert svgs, "document rendered no pages"
    assert stats.get("uncontained", 0) == 0, (
        f"{stats.get('uncontained')} uncontained text object(s)")


# ── Themes ──────────────────────────────────────────────────────────────


def test_all_seven_consulting_themes_are_listed():
    assert tuple(list_themes()) == THEMES


def test_theme_is_a_v2_tokens_fragment_not_a_v01_pack():
    for name in THEMES:
        theme = load_theme(name)
        assert theme["colors"], name
        assert theme["text_styles"], name
        for sname, style in theme["text_styles"].items():
            leaked = V01_STYLE_KEYS & set(style)
            assert not leaked, f"{name}.{sname} leaks v0.1 keys {leaked}"
            fam = style.get("font_family")
            assert fam is None or isinstance(fam, list), f"{name}.{sname}"


def test_every_theme_validates_and_renders_a_probe_page():
    """The issue's theme gate: each theme's tokens drive a real document —
    one text object per text style, one line per stroke style — that
    validates and renders with zero uncontained text."""
    for name in THEMES:
        theme = load_theme(name)
        objects, y = [], 20.0
        for sname in sorted(theme["text_styles"]):
            objects.append({"type": "text", "box": [40, y, 880, 34],
                            "text": f"{name} · {sname}", "style": sname})
            y += 40
        for sname in sorted(theme.get("stroke_styles") or {}):
            objects.append({"type": "line", "from": [40, y], "to": [400, y],
                            "stroke": "text", "stroke_style": sname})
            y += 16
        doc = {"dsl": "FrameForge", "version": HEAD_VERSION,
               "title": f"theme probe · {name}", "profile": "deck",
               "defs": {"tokens": theme},
               "pages": [{"mode": "page", "id": f"probe-{name}",
                          "canvas": {"size": [960, max(540.0, y + 20)],
                                     "units": "px"},
                          "rendering": {"coordinate_mode": "absolute"},
                          "layers": [{"id": "main", "objects": objects}]}]}
        validate_document(doc)
        _assert_contained(doc)


def test_unknown_theme_raises_keyerror():
    with pytest.raises(KeyError):
        load_theme("accenture")


# ── Symbol packs ────────────────────────────────────────────────────────


def test_symbol_packs_enumerate_the_absorbed_set():
    packs = list_symbols()
    assert set(packs) == {"covers", "sections", "shared", "hex"}
    assert "cover_minimal_sidebar" in packs["covers"]
    assert "agenda_left_pane" in packs["sections"]
    assert {"insight_box", "kpi_card", "two_by_two", "s_node"} <= set(packs["shared"])
    assert {"hex_header", "hex_leaf_solid", "hex_leaf_dashed",
            "hex_node_plain", "hex_node_warning", "hex_node_excel",
            "hex_node_money"} <= set(packs["hex"])


def test_load_symbols_merges_packs_for_defs():
    symbols = load_symbols("covers", "shared")
    assert "cover_minimal_sidebar" in symbols and "insight_box" in symbols
    assert "hex_header" not in symbols
    everything = load_symbols()
    assert len(everything) == sum(len(v) for v in list_symbols().values())
    for sym in everything.values():
        assert sym["box"] and sym["objects"]


def test_cover_symbol_expands_and_renders_contained():
    from frameforge.sdk import expand
    doc = {"dsl": "FrameForge", "version": HEAD_VERSION,
           "title": "cover probe", "profile": "deck",
           "defs": {"tokens": {**load_theme("mckinsey"),
                               "text_styles": {**load_theme("mckinsey")["text_styles"],
                                               **support_text_styles("covers")}},
                    "symbols": load_symbols("covers")},
           "pages": [{"mode": "page", "id": "cover",
                      "canvas": {"size": [960, 540], "units": "px"},
                      "rendering": {"coordinate_mode": "absolute"},
                      "layers": [{"id": "main", "objects": [
                          {"type": "use", "symbol": "cover_minimal_sidebar",
                           "box": [0, 0, 960, 540],
                           "params": {"title": "FrameForge Library",
                                      "subtitle": "Issue #32 absorption probe",
                                      "page_number": "01",
                                      "bg_color": "#FFFFFF",
                                      "accent_color": "accent",
                                      "right_pane_color": "primary"}}]}]}]}
    expanded = expand(doc).document.model_dump(by_alias=True, exclude_none=True)
    assert all(o.get("type") != "use" for o in _objects(expanded))
    assert "FrameForge Library" in _texts(expanded)
    _assert_contained(expanded)


# ── Generators ──────────────────────────────────────────────────────────


def test_honeycomb_generator_reproduces_the_committed_example():
    data = load_example("honeycomb")
    doc = honeycomb_capability_map(data)
    validate_document(doc)
    assert all(o.get("type") != "use" for o in _objects(doc)), \
        "generator must return an expanded, render-ready document"
    text = _texts(doc)
    assert data["title"] in text
    for col in data["columns"]:
        assert col["header"] in text
        for item in col["items"]:
            assert item["label"] in text
    _assert_contained(doc)


def test_module_hub_generator_reproduces_the_committed_example():
    data = load_example("module_hub")
    doc = module_hub_radial(data)
    validate_document(doc)
    assert all(o.get("type") != "use" for o in _objects(doc))
    text = _texts(doc)
    assert data["hub"]["label"] in text
    for sat in data["satellites"]:
        assert sat["label"] in text
    for bullet in data["hub"]["detail"]["bullets"]:
        assert bullet in text
    lines = [o for o in _objects(doc) if o.get("type") == "line"]
    assert len(lines) >= len(data.get("edges") or []), "edges must be drawn"
    _assert_contained(doc)


def test_generators_are_deterministic():
    data = load_example("honeycomb")
    assert honeycomb_capability_map(data) == honeycomb_capability_map(data)
    data = load_example("module_hub")
    assert module_hub_radial(data) == module_hub_radial(data)


def test_example_data_is_committed_not_referenced():
    assert (EXAMPLES_DIR / "honeycomb.yml").is_file()
    assert (EXAMPLES_DIR / "module_hub.yml").is_file()
    assert ROOT in EXAMPLES_DIR.resolve().parents


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
