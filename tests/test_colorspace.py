"""Perceptual colour-space conversions, interpolation, and SDK integration."""
from __future__ import annotations

import math
import importlib.util
import json
from pathlib import Path
import time

import pytest
from hypothesis import given, settings, strategies as st

from frameforge.sdk import (
    delta_e,
    from_lab,
    from_lch,
    from_oklab,
    from_oklch,
    from_xyz,
    linear_to_srgb,
    mix,
    ramp,
    srgb_to_linear,
    to_lab,
    to_lch,
    to_oklab,
    to_oklch,
    to_xyz,
)
from frameforge.sdk import chevreul

ROOT = Path(__file__).resolve().parents[1]


def _channels(color: str) -> tuple[int, int, int]:
    value = color.removeprefix("#")
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _hue_distance(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def test_srgb_transfer_reference_values() -> None:
    assert srgb_to_linear(0.0) == 0.0
    assert srgb_to_linear(1.0) == 1.0
    assert srgb_to_linear(0.04045) == pytest.approx(0.0031308049535603713)
    assert linear_to_srgb(0.0031308) == pytest.approx(0.040449936)
    for value in (0.0, 0.003, 0.04045, 0.18, 0.5, 1.0):
        # IEC's rounded forward/inverse breakpoints leave a ~3e-8 seam.
        assert linear_to_srgb(srgb_to_linear(value)) == pytest.approx(value, abs=4e-8)


def test_xyz_and_cielab_d65_published_anchors() -> None:
    # The high-precision CSS Color 4 sRGB matrix sums to this D65 white.
    d65 = (0.95045592705167, 1.0, 1.0890577507598784)
    assert to_xyz("#ffffff") == pytest.approx(d65, abs=1e-12)
    assert from_xyz(d65) == "#ffffff"
    assert to_lab("#ffffff") == pytest.approx((100.0, 0.0, 0.0), abs=0.01)
    assert to_lab("#ff0000") == pytest.approx((53.2408, 80.0925, 67.2032), abs=0.01)
    _, grey_a, grey_b = to_lab("#808080")
    assert grey_a == pytest.approx(0.0, abs=0.01)
    assert grey_b == pytest.approx(0.0, abs=0.01)


def test_lch_is_the_cylindrical_form_of_cielab() -> None:
    lab = to_lab("#ff0000")
    lch = to_lch("#ff0000")
    assert lch == pytest.approx(
        (lab[0], math.hypot(lab[1], lab[2]), math.degrees(math.atan2(lab[2], lab[1]))),
        abs=1e-10,
    )
    assert from_lch(lch) == "#ff0000"


def test_oklab_and_oklch_published_anchors() -> None:
    assert to_oklab("#ffffff") == pytest.approx((1.0, 0.0, 0.0), abs=0.001)
    assert to_oklab("#ff0000") == pytest.approx(
        (0.62795536, 0.22486306, 0.12584630), abs=1e-7,
    )
    lab = to_oklab("#33689c")
    lch = to_oklch("#33689c")
    assert lch[0] == pytest.approx(lab[0])
    assert lch[1] == pytest.approx(math.hypot(lab[1], lab[2]))
    assert _hue_distance(lch[2], math.degrees(math.atan2(lab[2], lab[1]))) < 1e-10
    assert from_oklch(lch) == "#33689c"


def test_stratified_round_trips_cover_more_than_twenty_thousand_srgb_triples() -> None:
    levels = tuple(round(index * 255 / 27) for index in range(28))
    samples = {(r, g, b) for r in levels for g in levels for b in levels}
    samples.update((value, value, value) for value in range(256))
    samples.update((r, g, b) for r in (0, 255) for g in (0, 255) for b in (0, 255))
    assert len(samples) >= 20_000
    for rgb in samples:
        color = "#" + "".join(f"{channel:02x}" for channel in rgb)
        for restored in (from_lab(to_lab(color)), from_oklab(to_oklab(color))):
            assert all(
                abs(actual - expected) <= 1
                for actual, expected in zip(_channels(restored), rgb)
            )


@settings(max_examples=500, deadline=None)
@given(
    red=st.integers(min_value=0, max_value=255),
    green=st.integers(min_value=0, max_value=255),
    blue=st.integers(min_value=0, max_value=255),
)
def test_arbitrary_srgb_round_trips(red: int, green: int, blue: int) -> None:
    color = f"#{red:02x}{green:02x}{blue:02x}"
    for restored in (
        from_xyz(to_xyz(color)),
        from_lab(to_lab(color)),
        from_lch(to_lch(color)),
        from_oklab(to_oklab(color)),
        from_oklch(to_oklch(color)),
    ):
        assert all(
            abs(actual - expected) <= 1
            for actual, expected in zip(_channels(restored), (red, green, blue))
        )


def test_mix_defaults_to_oklab_and_preserves_exact_endpoints() -> None:
    assert mix("#000", "#fff", 0.0) == "#000"
    assert mix("#000", "#fff", 1.0) == "#fff"
    assert mix("#000000", "#ffffff", 0.5, space="srgb") == "#808080"
    midpoint = mix("#000000", "#ffffff", 0.5)
    assert midpoint != "#808080"
    assert to_oklab(midpoint)[0] == pytest.approx(0.5, abs=0.02)


@pytest.mark.parametrize("space", ["lch", "oklch"])
def test_cylindrical_mix_uses_the_shorter_hue_arc(space: str) -> None:
    if space == "lch":
        a = from_lch((65.0, 20.0, 350.0))
        b = from_lch((65.0, 20.0, 10.0))
        midpoint_hue = to_lch(mix(a, b, 0.5, space=space))[2]
    else:
        a = from_oklch((0.7, 0.05, 350.0))
        b = from_oklch((0.7, 0.05, 10.0))
        midpoint_hue = to_oklch(mix(a, b, 0.5, space=space))[2]
    assert _hue_distance(midpoint_hue, 0.0) < 5.0
    assert _hue_distance(midpoint_hue, 180.0) > 170.0


def test_ramp_is_even_across_two_or_more_stops() -> None:
    colors = ramp(["#000000", "#ff0000", "#ffffff"], 5, space="oklab")
    assert len(colors) == 5
    assert colors[0] == "#000000"
    assert colors[2] == "#ff0000"
    assert colors[-1] == "#ffffff"
    assert ramp(["#123456", "#abcdef"], 2) == ["#123456", "#abcdef"]


def test_delta_e_is_symmetric_and_supports_both_metrics() -> None:
    for method in ("oklab", "cie76"):
        assert delta_e("#123456", "#123456", method=method) == pytest.approx(0.0)
        forward = delta_e("#d7332f", "#33689c", method=method)
        assert forward > 0.0
        assert forward == pytest.approx(
            delta_e("#33689c", "#d7332f", method=method), abs=1e-12,
        )


def test_wcag_luminance_uses_exactly_the_same_srgb_linearisation() -> None:
    for color in ("#000000", "#ffffff", "#33689c", "#d7332f", "#808080"):
        red, green, blue = (channel / 255.0 for channel in _channels(color))
        expected = (
            0.2126 * srgb_to_linear(red)
            + 0.7152 * srgb_to_linear(green)
            + 0.0722 * srgb_to_linear(blue)
        )
        assert chevreul.relative_luminance(color) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize(
    ("call", "parameter"),
    [
        (lambda: to_lab("not-a-colour"), "color"),
        (lambda: to_oklab("#12xz89"), "color"),
        (lambda: mix("#000", "#fff", -0.01), "t"),
        (lambda: mix("#000", "#fff", 1.01), "t"),
        (lambda: mix("#000", "#fff", 0.5, space="hsl"), "space"),
        (lambda: ramp(["#000", "#fff"], 3, space="hsv"), "space"),
        (lambda: ramp(["#000"], 3), "stops"),
        (lambda: ramp(["#000", "#fff"], 1), "n"),
        (lambda: delta_e("#000", "#fff", method="cie2000"), "method"),
    ],
)
def test_invalid_inputs_name_the_parameter(call, parameter: str) -> None:
    with pytest.raises(ValueError, match=parameter):
        call()


def test_out_of_gamut_conversion_clips_to_srgb() -> None:
    color = from_oklab((0.8, 0.5, 0.5))
    assert color.startswith("#") and len(color) == 7
    assert all(0 <= channel <= 255 for channel in _channels(color))
    assert "clip" in (from_oklab.__doc__ or "").lower()


def test_conversion_throughput_floor() -> None:
    samples = 150_000
    started = time.perf_counter()
    checksum = 0.0
    for index in range(samples):
        checksum += to_oklab(f"#{index & 0xFFFFFF:06x}")[0]
    elapsed = time.perf_counter() - started
    assert checksum > 0.0
    assert samples / elapsed >= 100_000, f"{samples / elapsed:,.0f} conversions/s"


def test_runnable_example_uses_the_public_api_deterministically(capsys) -> None:
    path = ROOT / "static/examples/perceptual_color_ramp.py"
    spec = importlib.util.spec_from_file_location("perceptual_color_ramp", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected = {
        "delta_e_oklab": 0.597438,
        "legacy_midpoint": "#857a58",
        "oklab_ramp": [
            "#172a46", "#4e3744", "#813f3c", "#b5402c",
            "#cc703f", "#e19c54", "#f3c969",
        ],
        "perceptual_midpoint": "#7e7761",
    }
    assert module.build_payload() == expected
    assert module.build_payload() == expected
    assert module.main() == 0
    assert json.loads(capsys.readouterr().out) == expected


def test_generated_sdk_docs_and_manifest_expose_colorspace() -> None:
    sdk_guide = (ROOT / "docs/sdk.md").read_text(encoding="utf-8")
    sdk_api = (ROOT / "docs/sdk-api.md").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "docs/capability-manifest.json").read_text(encoding="utf-8"))
    assert "perceptual" in sdk_guide.lower()
    assert "mix(..., space=\"oklab\")" in sdk_guide
    assert "## `frameforge.sdk.colorspace`" in sdk_api
    assert "mix(a: 'Color', b: 'Color', t: 'float', *, space: 'str' = 'oklab')" in sdk_api
    assert {"mix", "ramp", "delta_e", "to_oklab", "from_oklab"} <= set(
        manifest["sdk"]["public_exports"]
    )
