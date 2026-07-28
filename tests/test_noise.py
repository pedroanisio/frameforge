"""Contract tests for sampleable coherent SDK noise (#91)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from frameforge.sdk import (
    DocumentBuilder,
    Noise,
    ScalarField,
    domain_warp,
    fbm,
    perlin_2d,
    remap,
    render_page_svgs,
    simplex_2d,
    to_unit,
    validate_static_rules,
    value_noise_2d,
)
from frameforge.sdk.noise import _fade, _permutation
from frameforge.sdk.paint import turbulence

ROOT = Path(__file__).resolve().parent.parent


def _load_noise_example():
    path = ROOT / "static/examples/sampleable_noise_field.py"
    spec = importlib.util.spec_from_file_location("sampleable_noise_field", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quintic_fade_matches_perlin_reference_values():
    expected = {
        0.0: 0.0,
        0.25: 0.103515625,
        0.5: 0.5,
        0.75: 0.896484375,
        1.0: 1.0,
    }
    assert {value: _fade(value) for value in expected} == expected


@pytest.mark.parametrize(
    ("x", "y", "seed", "expected"),
    [
        (0.125, 0.25, 0, 0.30386790767103422),
        (1.25, -0.75, 7, -0.49870358607233589),
        (-2.5, 3.125, 18497, 0.18314486886620968),
    ],
)
def test_simplex_matches_independently_calculated_gustavson_reference_values(
    x: float, y: float, seed: int, expected: float
):
    assert simplex_2d(x, y, seed=seed) == pytest.approx(expected, abs=1e-15)


@pytest.mark.parametrize("seed", [0, 1, 18497])
def test_perlin_is_zero_at_integer_lattice_points(seed: int):
    values = [
        perlin_2d(float(x), float(y), seed=seed)
        for x in range(-4, 5)
        for y in range(-4, 5)
    ]
    assert max(abs(value) for value in values) < 1e-9


def test_primitives_are_seeded_deterministic_and_distinct():
    point = (1.2345, -6.789)
    for basis in (value_noise_2d, perlin_2d, simplex_2d):
        assert basis(*point, seed=7) == basis(*point, seed=7)
        assert basis(*point, seed=7) != basis(*point, seed=8)


def test_noise_sample_grid_hash_is_reproducible_across_fresh_processes():
    code = (
        "import hashlib,json; "
        "from frameforge.sdk import perlin_2d,simplex_2d,value_noise_2d,fbm; "
        "fs=(value_noise_2d,perlin_2d,simplex_2d,fbm); "
        "v=[[f(x/7,y/11,seed=18497) for y in range(-5,6)] "
        "for f in fs for x in range(-7,8)]; "
        "b=json.dumps(v,separators=(',',':')).encode(); "
        "print(hashlib.sha256(b).hexdigest())"
    )
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    digests = [
        subprocess.check_output(
            [sys.executable, "-c", code], cwd=ROOT, env=env, text=True
        ).strip()
        for _ in range(2)
    ]
    assert digests[0] == digests[1]


@pytest.mark.parametrize(
    ("basis", "lo", "hi"),
    [
        (value_noise_2d, 0.0, 1.0),
        (perlin_2d, -1.0, 1.0),
        (simplex_2d, -1.0, 1.0),
    ],
)
def test_primitive_ranges_hold_over_ten_thousand_points(basis, lo: float, hi: float):
    values = [
        basis((index % 100 - 50) / 7.0, (index // 100 - 50) / 9.0, seed=31)
        for index in range(10_000)
    ]
    assert min(values) >= lo
    assert max(values) <= hi
    assert min(values) < max(values)


@pytest.mark.parametrize("basis", [value_noise_2d, perlin_2d, simplex_2d])
@settings(max_examples=1000, deadline=None)
@given(
    x=st.floats(-100, 100, allow_nan=False, allow_infinity=False),
    y=st.floats(-100, 100, allow_nan=False, allow_infinity=False),
)
def test_primitives_are_numerically_continuous(basis, x: float, y: float):
    delta = 1e-4
    before = basis(x, y, seed=23)
    after = basis(x + delta, y, seed=23)
    assert abs(after - before) < 50 * delta


@pytest.mark.parametrize(
    ("basis", "expected"),
    [
        (lambda _x, _y, *, seed: 1.0, 1.0),
        (lambda _x, _y, *, seed: -1.0, -1.0),
        (lambda _x, _y, *, seed: 0.25, 0.25),
    ],
)
@pytest.mark.parametrize("octaves", [1, 4, 8])
def test_fbm_normalises_summed_amplitude(basis, expected: float, octaves: int):
    assert fbm(1.25, -3.5, seed=7, octaves=octaves, basis=basis) == pytest.approx(expected)


@pytest.mark.parametrize("basis", [value_noise_2d, perlin_2d, simplex_2d])
@pytest.mark.parametrize("octaves", [1, 4, 8])
def test_fbm_stays_within_its_basis_range(basis, octaves: int):
    values = [
        fbm(index / 17, -index / 23, seed=91, octaves=octaves, basis=basis)
        for index in range(500)
    ]
    lo = 0.0 if basis is value_noise_2d else -1.0
    assert min(values) >= lo
    assert max(values) <= 1.0


def test_domain_warp_is_seeded_and_strength_zero_is_identity():
    point = (3.25, -1.75)
    assert domain_warp(*point, seed=7, strength=0) == point
    assert domain_warp(*point, seed=7) == domain_warp(*point, seed=7)
    assert domain_warp(*point, seed=7) != domain_warp(*point, seed=8)


def test_noise_binds_basis_frequency_and_order_stable_derived_streams():
    root = Noise("document", frequency=0.125, basis="simplex")
    labels_first = root.derive("labels")
    dots_second = root.derive("dots")
    dots_first = Noise("document", frequency=0.125, basis="simplex").derive("dots")
    labels_second = Noise("document", frequency=0.125, basis="simplex").derive("labels")

    assert labels_first.at(3, 4) == labels_second.at(3, 4)
    assert dots_first.at(3, 4) == dots_second.at(3, 4)
    assert labels_first.at(3, 4) != dots_first.at(3, 4)
    assert root.at(3, 4) == simplex_2d(3 * 0.125, 4 * 0.125, seed=root.seed)
    assert root.field()(3, 4) == root.at(3, 4)
    assert root.fbm_at(3, 4, octaves=6) == fbm(
        3 * 0.125,
        4 * 0.125,
        seed=root.seed,
        octaves=6,
        basis=simplex_2d,
    )


def test_noise_value_mapping_helpers_do_not_silently_clamp():
    assert to_unit(-1) == 0
    assert to_unit(0) == 0.5
    assert to_unit(1) == 1
    assert remap(-1, 20, 40) == 20
    assert remap(0, 20, 40) == 30
    assert remap(1, 20, 40) == 40
    assert to_unit(2) == 1.5


@pytest.mark.parametrize(
    ("call", "parameter"),
    [
        (lambda: fbm(0, 0, octaves=0), "octaves"),
        (lambda: fbm(0, 0, lacunarity=0), "lacunarity"),
        (lambda: fbm(0, 0, gain=0), "gain"),
        (lambda: domain_warp(0, 0, strength=math.inf), "strength"),
        (lambda: Noise(0, frequency=0), "frequency"),
        (lambda: Noise(0, basis="worley"), "basis"),
    ],
)
def test_noise_guards_name_offending_parameter(call, parameter: str):
    with pytest.raises(ValueError, match=parameter):
        call()


def test_permutation_cache_is_bounded_and_reuses_tables():
    first = _permutation(7)
    second = _permutation(7)
    assert first is second
    assert len(first) == 512
    assert sorted(first[:256]) == list(range(256))
    assert _permutation.cache_info().maxsize == 64


def test_perlin_throughput_exceeds_two_hundred_thousand_samples_per_second():
    sample_count = 250_000
    perlin_2d(0.25, 0.75, seed=7)
    started = time.perf_counter()
    checksum = sum(
        perlin_2d(index * 0.001, index * -0.0013, seed=7)
        for index in range(sample_count)
    )
    elapsed = time.perf_counter() - started
    throughput = sample_count / elapsed

    assert math.isfinite(checksum)
    assert throughput >= 200_000, f"perlin throughput={throughput:,.0f} samples/s"


def test_scalar_field_consumes_noise_field_without_fields_or_renderer_changes():
    builder = DocumentBuilder(title="Noise field integration", profile="diagram")
    page = builder.page(
        "noise",
        canvas={"size": [640, 360], "units": "px"},
        coordinate_mode="absolute",
    ).layer("main")
    field = ScalarField(Noise(7, frequency=0.35, basis="simplex").field(), domain=(0, 0, 8, 5))
    heatmap = field.heatmap(
        box=[32, 32, 576, 296], steps_x=32, steps_y=20, low="#102a43", high="#f6c453"
    )
    contours = field.contours(
        box=[32, 32, 576, 296], steps_x=42, steps_y=28, levels=7, color="#ffffff"
    )
    heatmap["children"].extend(contours["children"])
    page.add(heatmap)

    document = builder.build()
    report = validate_static_rules(document)
    assert report.ok is True
    assert render_page_svgs(document)[0].count("<rect") >= 600


def test_paint_turbulence_output_is_byte_identical_to_pre_noise_contract():
    value = turbulence(
        base_frequency=(0.03, 0.08),
        num_octaves=3,
        seed=7,
        stitch_tiles="stitch",
        type="fractalNoise",
        opacity=0.35,
        mode="multiply",
    )
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(payload.encode()).hexdigest() == (
        "88b7db0c765b109317622ab3dfbcd89f4ffe021ff22edf0737fae603efef9590"
    )
    assert "frameforge.sdk.noise" in (turbulence.__doc__ or "")


def test_sampleable_noise_example_builds_valid_deterministic_svg():
    module = _load_noise_example()
    first = module.build()
    second = module.build()
    assert first == second
    assert validate_static_rules(first).ok is True
    first_svg = render_page_svgs(first)
    assert first_svg == render_page_svgs(second)
    assert len(first_svg) == 1
    assert first_svg[0].count("<rect") >= 900


def test_generated_sdk_docs_include_noise_signatures_and_usage():
    api = (ROOT / "docs/sdk-api.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs/sdk.md").read_text(encoding="utf-8")
    api_fragments = (
        "## `frameforge.sdk.noise`",
        "### `Noise`",
        "### `value_noise_2d`",
        "### `perlin_2d`",
        "### `simplex_2d`",
        "### `fbm`",
        "### `domain_warp`",
        "### `to_unit`",
        "### `remap`",
    )
    guide_fragments = (
        "## Sampleable coherent noise",
        "ScalarField(source.field()",
        "paint.turbulence",
        "author-time",
        "not cryptographic",
    )
    assert not [fragment for fragment in api_fragments if fragment not in api]
    assert not [fragment for fragment in guide_fragments if fragment not in guide]
    noise_api = api.split("## `frameforge.sdk.noise`", 1)[1].split("\n## `", 1)[0]
    assert " at 0x" not in noise_api
    assert "basis: 'NoiseBasis' = perlin_2d" in noise_api
    assert "basis: 'NoiseBasis' = fbm" in noise_api
