"""sdk.canon — Johnston's typographic canon (scale, margins, measure).

Source: Edward Johnston, *Writing & Illuminating, & Lettering* (1906) —
the margin proportions ("inner 1½, top 2, outer 3, foot 4 … proportions
common in early MSS", ch. VI) and the measure/leading guidance; the modular
scale is the standard ratio-power construction.

Runs under pytest or standalone (``uv run python tests/test_sdk_canon.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "docs")]

from frameforge.sdk import canon  # noqa: E402


def test_modular_scale_is_exact_ratio_powers() -> None:
    sizes = canon.modular_scale(base=11.5, ratio=1.25)
    assert sizes["caption"] == pytest.approx(11.5)
    assert sizes["body"] == pytest.approx(11.5 * 1.25)
    assert sizes["lead"] == pytest.approx(11.5 * 1.25**2)
    assert list(sizes) == ["caption", "body", "lead", "h3", "h2", "h1", "display", "cover"]
    values = list(sizes.values())
    assert all(y / x == pytest.approx(1.25) for x, y in zip(values, values[1:]))


def test_modular_scale_custom_names() -> None:
    sizes = canon.modular_scale(base=10, ratio=1.5, names=["s", "m", "l"])
    assert sizes == {"s": pytest.approx(10), "m": pytest.approx(15), "l": pytest.approx(22.5)}


def test_johnston_margins_hold_the_canonical_proportions() -> None:
    margins = canon.johnston_margins(unit=40)
    assert margins == {"inner": 60.0, "top": 80.0, "outer": 120.0, "foot": 160.0}
    ratio = [margins["inner"], margins["top"], margins["outer"], margins["foot"]]
    assert [r / ratio[0] for r in ratio] == pytest.approx([1.0, 4 / 3, 2.0, 8 / 3])


def test_content_box_mirrors_across_the_opening() -> None:
    recto = canon.content_box(794, 1123, unit=40, side="recto")
    verso = canon.content_box(794, 1123, unit=40, side="verso")
    # recto: inner margin on the left; verso: inner margin on the right
    assert recto[0] == 60 and verso[0] == 120
    assert recto[2] == verso[2] == 794 - 60 - 120  # same content width
    assert recto[1] == verso[1] == 80
    assert recto[3] == verso[3] == 1123 - 80 - 160


def test_content_box_rejects_unknown_side() -> None:
    with pytest.raises(ValueError):
        canon.content_box(794, 1123, unit=40, side="middle")


def test_measure_bounds_are_johnstons_45_to_75() -> None:
    assert canon.MEASURE_MIN == 45 and canon.MEASURE_MAX == 75
    assert canon.measure_fits(60)
    assert not canon.measure_fits(30)
    assert not canon.measure_fits(90)


def test_caps_tracking_scales_with_size_and_rejects_negatives() -> None:
    assert canon.caps_tracking(20) == pytest.approx(20 * 0.06)
    assert canon.caps_tracking(20, percent=10) == pytest.approx(2.0)
    with pytest.raises(ValueError):
        canon.caps_tracking(-4)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
