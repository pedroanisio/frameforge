"""sdk.chevreul — Chevreul colour canon (wheel, harmonies, tone, grey test).

Sources the tests hold the module to:
- M. E. Chevreul, *De la loi du contraste simultané des couleurs* (1839):
  the 12-station painter's wheel, the six harmonies, tone scales.
- WCAG 2.1 §relative luminance / contrast ratio (https://www.w3.org/TR/WCAG21/)
  for the two numeric formulas — checked against published reference values.

Runs under pytest or standalone (``uv run python tests/test_sdk_chevreul.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from framegraph.sdk import chevreul as ch  # noqa: E402
from framegraph.sdk.model import validate_document  # noqa: E402


# ── the wheel ─────────────────────────────────────────────────────────────


def test_wheel_has_twelve_named_stations() -> None:
    assert len(ch.WHEEL) == 12
    for name in ("red", "red-orange", "yellow", "green", "blue", "violet"):
        assert name in ch.WHEEL
    for value in ch.WHEEL.values():
        assert value.startswith("#") and len(value) == 7


def test_complement_is_six_stations_away_and_involutive() -> None:
    assert ch.complement("red") == ch.WHEEL["green"]
    assert ch.complement("orange") == ch.WHEEL["blue"]
    assert ch.complement("yellow") == ch.WHEEL["violet"]
    names = list(ch.WHEEL)
    for name in names:
        partner = ch.complement_name(name)
        assert ch.complement_name(partner) == name
        assert (names.index(partner) - names.index(name)) % 12 == 6


def test_nearest_station_maps_hexes_onto_the_wheel() -> None:
    assert ch.nearest_station(ch.WHEEL["blue"]) == "blue"
    assert ch.nearest_station("#d92b2b") == "red"


# ── tone (WCAG-checked numerics) ─────────────────────────────────────────


def test_relative_luminance_reference_values() -> None:
    assert ch.relative_luminance("#ffffff") == pytest.approx(1.0)
    assert ch.relative_luminance("#000000") == pytest.approx(0.0)
    # WCAG coefficients: pure channels contribute exactly their weight
    assert ch.relative_luminance("#ff0000") == pytest.approx(0.2126)
    assert ch.relative_luminance("#00ff00") == pytest.approx(0.7152)
    assert ch.relative_luminance("#0000ff") == pytest.approx(0.0722)


def test_contrast_ratio_reference_values() -> None:
    assert ch.contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert ch.contrast_ratio("#ffffff", "#ffffff") == pytest.approx(1.0)
    # symmetric regardless of argument order
    a, b = "#33689c", "#fbf8f1"
    assert ch.contrast_ratio(a, b) == ch.contrast_ratio(b, a)


def test_tone_scale_runs_light_to_dark_through_the_colour() -> None:
    scale = ch.tone_scale("#33689c", steps=9)
    assert len(scale) == 9
    assert scale[4] == "#33689c"  # the normal tone sits mid-ladder
    lums = [ch.relative_luminance(tone) for tone in scale]
    assert all(x > y for x, y in zip(lums, lums[1:]))  # strictly darker rightward


def test_to_grey_preserves_luminance() -> None:
    grey = ch.to_grey("#d7332f")
    assert grey[1:3] == grey[3:5] == grey[5:7]  # r == g == b
    assert ch.relative_luminance(grey) == pytest.approx(
        ch.relative_luminance("#d7332f"), abs=5e-3
    )


# ── the six harmonies ────────────────────────────────────────────────────


def test_harmony_of_scale_is_tones_of_one_colour() -> None:
    colours = ch.harmony_of_scale("#33689c", n=5)
    assert len(colours) == 5
    assert set(colours) <= set(ch.tone_scale("#33689c", steps=5))  # picks from ONE ladder
    lums = [ch.relative_luminance(c) for c in colours]
    assert all(x > y for x, y in zip(lums, lums[1:]))  # read in order, light to dark


def test_harmony_of_hues_walks_neighbouring_stations() -> None:
    colours = ch.harmony_of_hues("green", n=3)
    assert len(colours) == 3
    assert ch.WHEEL["green"] in colours
    names = list(ch.WHEEL)
    picked = sorted(names.index(ch.nearest_station(c)) for c in colours)
    assert picked[-1] - picked[0] <= 2  # adjacent walk, no wheel-crossing


def test_dominant_light_pulls_every_colour_toward_the_tint() -> None:
    base = [ch.WHEEL["red"], ch.WHEEL["blue"], ch.WHEEL["green"]]
    tinted = ch.dominant_light(base, tint="#f0b32e", strength=0.5)
    for before, after in zip(base, tinted):
        d_before = ch._rgb_distance(before, "#f0b32e")
        d_after = ch._rgb_distance(after, "#f0b32e")
        assert d_after < d_before


def test_contrast_harmonies() -> None:
    light, dark = ch.contrast_of_scale("#33689c")
    assert ch.contrast_ratio(light, dark) > 3.0  # "two very distant tones"
    a, b = ch.contrast_of_hues("green")
    assert ch.nearest_station(a) != ch.nearest_station(b)
    pair = ch.contrast_of_colours("red")
    assert pair == (ch.WHEEL["red"], ch.WHEEL["green"])


# ── the closed palette (duties + tokens fragment) ────────────────────────


def test_closed_palette_duties_and_area_guide() -> None:
    palette = ch.closed_palette(ground="#fbf8f1", ink="#1d1e22", accent="#b5402c")
    assert set(palette.duties) >= {"ground", "ink", "accent"}
    assert len(palette.quiet_steps) >= 2  # greys from the ink's own scale
    assert sum(ch.AREA_GUIDE.values()) == pytest.approx(1.0)
    # the accent must actually read against the ground (the book's plate 37 rule)
    assert ch.contrast_ratio(palette.duties["accent"], palette.duties["ground"]) > 3.0


def test_closed_palette_tokens_fragment_validates_in_a_document() -> None:
    palette = ch.closed_palette(ground="#fbf8f1", ink="#1d1e22", accent="#b5402c")
    doc = {
        "dsl": "FrameGraph",
        "version": "2.3.0",
        "title": "palette smoke",
        "defs": {"tokens": {"colors": palette.tokens()}},
        "pages": [{"mode": "page", "id": "p1",
                   "canvas": {"size": [100, 100], "units": "px"},
                   "layers": [{"id": "l1", "objects": [
            {"type": "rect", "box": [0, 0, 100, 100], "fill": "ground"},
            {"type": "text", "box": [0, 0, 100, 20], "text": "hi",
             "style": {"color": "ink"}},
        ]}]}],
    }
    validate_document(doc)  # must not raise


# ── the grey test (plate 36) ─────────────────────────────────────────────


def test_grey_document_strips_hue_everywhere_and_still_validates() -> None:
    doc = {
        "dsl": "FrameGraph",
        "version": "2.3.0",
        "title": "grey test",
        "defs": {"tokens": {"colors": {"accent": "#b5402c"}}},
        "pages": [{"mode": "page", "id": "p1",
                   "canvas": {"size": [100, 100], "units": "px"},
                   "layers": [{"id": "l1", "objects": [
            {"type": "rect", "box": [0, 0, 100, 50], "fill": "#33689c"},
            {"type": "rect", "box": [0, 50, 100, 50],
             "fill": {"kind": "linear", "stops": [
                 {"color": "#d7332f", "position": 0},
                 {"color": "#f0b32e", "position": 1}]}},
            {"type": "text", "box": [0, 0, 100, 20], "text": "hi",
             "style": {"color": "accent"}},
        ]}]}],
    }
    grey = ch.grey_document(doc)
    validate_document(grey)
    flat = str(grey)
    for hue in ("#33689c", "#d7332f", "#f0b32e", "#b5402c"):
        assert hue not in flat
    # source document untouched
    assert doc["pages"][0]["layers"][0]["objects"][0]["fill"] == "#33689c"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
