"""Contract tests for deterministic SDK randomness and point sampling (#90)."""
from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from frameforge_sdk import Rand, halton, jittered_grid, poisson_disk
from frameforge_sdk._seed import stable_seed
from frameforge_sdk.geometry import Vec2
from frameforge_sdk.humanize import _stable_seed

ROOT = Path(__file__).resolve().parent.parent


def _tuples(points: list[Vec2]) -> list[tuple[float, float]]:
    return [point.tuple() for point in points]


def _minimum_distance(points: list[Vec2]) -> float:
    return min(
        math.hypot(a.x - b.x, a.y - b.y)
        for i, a in enumerate(points)
        for b in points[i + 1 :]
    )


def test_stable_seed_shared_helper_preserves_humanize_contract():
    cases = [(), (0,), ("document",), (42, "object-7"), (("nested", 3), "x")]
    for parts in cases:
        assert _stable_seed(*parts) == stable_seed(*parts)


def test_rand_same_seed_reproduces_every_public_sequence_operation():
    def draw(seed: object) -> tuple[object, ...]:
        rand = Rand(seed)
        source = ["a", "b", "c", "d", "e"]
        return (
            [rand.uniform(-4.0, 9.0) for _ in range(5)],
            [rand.randint(2, 5) for _ in range(12)],
            [rand.gauss(3.0, 0.75) for _ in range(5)],
            rand.choice(source),
            rand.sample(source, 3),
            rand.shuffled(source),
        )

    assert draw("same") == draw("same")
    assert draw("same") != draw("different")


def test_rand_seed_accepts_string_integer_and_tuple():
    assert Rand("42").uniform() == Rand("42").uniform()
    assert Rand(42).uniform() == Rand(42).uniform()
    assert Rand(("document", 42)).uniform() == Rand(("document", 42)).uniform()


def test_rand_derive_is_independent_and_creation_order_stable():
    first = Rand("document")
    first_labels = first.derive("labels")
    a_first = [first_labels.uniform() for _ in range(2)]
    parent_first = first.uniform()
    first_dots = first.derive("dots")
    b_second = [first_dots.uniform() for _ in range(2)]

    second = Rand("document")
    second_dots = second.derive("dots")
    b_first = [second_dots.uniform() for _ in range(2)]
    second_labels = second.derive("labels")
    a_second = [second_labels.uniform() for _ in range(2)]

    assert a_first == a_second
    assert b_first == b_second
    assert a_first != b_first
    assert parent_first == Rand("document").uniform()


def test_rand_is_reproducible_in_fresh_processes():
    code = (
        "import json; from frameforge_sdk import Rand; "
        "r=Rand(('doc', 42)); "
        "print(json.dumps([r.uniform(), r.randint(1, 9), r.gauss(), "
        "r.derive('child').uniform()]))"
    )
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    outputs = [
        subprocess.check_output(
            [sys.executable, "-c", code], cwd=ROOT, env=env, text=True
        ).strip()
        for _ in range(2)
    ]
    assert outputs[0] == outputs[1]


def test_rand_sequence_helpers_do_not_mutate_input_and_randint_is_inclusive():
    source = [1, 2, 3, 4, 5]
    original = source.copy()
    rand = Rand(9)

    shuffled = rand.shuffled(source)
    sampled = rand.sample(source, 3)
    values = {rand.randint(2, 3) for _ in range(100)}

    assert source == original
    assert shuffled is not source
    assert sampled is not source
    assert sorted(shuffled) == original
    assert set(sampled) <= set(source)
    assert values == {2, 3}


def test_rand_spatial_helpers_stay_inside_requested_regions():
    rand = Rand("spatial")
    rect_points = [rand.point_in_rect([10, 20, 30, 40]) for _ in range(500)]
    circle_points = [rand.point_in_circle(7, 11, 5) for _ in range(5000)]
    jittered = [rand.jitter(Vec2(3, 4), 2) for _ in range(500)]

    assert all(10 <= p.x <= 40 and 20 <= p.y <= 60 for p in rect_points)
    assert all(math.hypot(p.x - 7, p.y - 11) <= 5 for p in circle_points)
    assert all(math.hypot(p.x - 3, p.y - 4) <= 2 for p in jittered)
    assert rand.jitter((3, 4), 0) == Vec2(3, 4)

    mean_squared_radius = sum((p.x - 7) ** 2 + (p.y - 11) ** 2 for p in circle_points) / len(circle_points)
    assert mean_squared_radius == pytest.approx(12.5, abs=0.5)


def test_halton_matches_reference_terms_and_maps_skip_into_box():
    expected = [
        (0.5, 1 / 3),
        (0.25, 2 / 3),
        (0.75, 1 / 9),
        (0.125, 4 / 9),
        (0.625, 7 / 9),
    ]
    for actual, reference in zip(_tuples(halton(5)), expected, strict=True):
        assert actual == pytest.approx(reference, abs=1e-12)

    mapped = halton(2, box=[10, 20, 100, 60], skip=3)
    expected_mapped = [(22.5, 20 + 60 * 4 / 9), (72.5, 20 + 60 * 7 / 9)]
    for actual, reference in zip(_tuples(mapped), expected_mapped, strict=True):
        assert actual == pytest.approx(reference, abs=1e-12)


def test_jittered_grid_zero_amount_is_exact_row_major_cell_centres():
    points = jittered_grid([0, 0, 100, 100], nx=4, ny=4, amount=0)
    assert _tuples(points) == [
        (12.5, 12.5), (37.5, 12.5), (62.5, 12.5), (87.5, 12.5),
        (12.5, 37.5), (37.5, 37.5), (62.5, 37.5), (87.5, 37.5),
        (12.5, 62.5), (37.5, 62.5), (62.5, 62.5), (87.5, 62.5),
        (12.5, 87.5), (37.5, 87.5), (62.5, 87.5), (87.5, 87.5),
    ]


def test_jittered_grid_is_seeded_stratified_and_bounded():
    first = jittered_grid([10, 20, 80, 60], nx=4, ny=3, rand=Rand("grid"))
    second = jittered_grid([10, 20, 80, 60], nx=4, ny=3, rand=Rand("grid"))
    assert first == second
    assert len(first) == 12

    cell_w, cell_h = 20, 20
    for index, point in enumerate(first):
        col, row = index % 4, index // 4
        assert 10 + col * cell_w <= point.x <= 10 + (col + 1) * cell_w
        assert 20 + row * cell_h <= point.y <= 20 + (row + 1) * cell_h


def test_poisson_disk_acceptance_density_separation_and_cap():
    points = poisson_disk([0, 0, 200, 200], radius=10, rand=Rand("acceptance"))
    capped = poisson_disk([0, 0, 200, 200], radius=10, rand=Rand("acceptance"), max_points=25)

    assert len(points) >= 150
    assert _minimum_distance(points) >= 10 - 1e-9
    assert capped == points[:25]
    assert len(capped) == 25


@settings(max_examples=40, deadline=None)
@given(
    x=st.floats(-100, 100, allow_nan=False, allow_infinity=False),
    y=st.floats(-100, 100, allow_nan=False, allow_infinity=False),
    width=st.floats(8, 80, allow_nan=False, allow_infinity=False),
    height=st.floats(8, 80, allow_nan=False, allow_infinity=False),
    radius=st.floats(2, 12, allow_nan=False, allow_infinity=False),
    seed=st.integers(-1000, 1000),
)
def test_poisson_disk_property_points_are_bounded_and_separated(
    x: float, y: float, width: float, height: float, radius: float, seed: int
):
    points = poisson_disk(
        [x, y, width, height], radius=radius, rand=Rand(seed), max_points=100
    )
    assert all(x <= p.x <= x + width and y <= p.y <= y + height for p in points)
    if len(points) > 1:
        assert _minimum_distance(points) >= radius - 1e-9


def test_poisson_disk_large_case_meets_grid_acceleration_budget():
    started = time.perf_counter()
    points = poisson_disk([0, 0, 1000, 1000], radius=8, rand=Rand("performance"))
    elapsed = time.perf_counter() - started

    assert len(points) >= 8000
    assert elapsed < 5.0, f"poisson_disk took {elapsed:.3f}s for {len(points)} points"


def test_poisson_disk_cap_does_not_preallocate_theoretical_full_grid():
    tracemalloc.start()
    try:
        points = poisson_disk(
            [0, 0, 1000, 1000], radius=1, rand=Rand("bounded-memory"), max_points=2
        )
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert len(points) == 2
    assert peak < 1_000_000, f"max_points=2 allocated {peak:,} bytes"


def test_spatial_outputs_are_quantized_for_cross_machine_serialization():
    rand = Rand("quantized")
    points = [
        rand.point_in_rect([0, 0, 10, 10]),
        rand.point_in_circle(0, 0, 10),
        rand.jitter((2, 3), 1),
        *halton(5),
        *jittered_grid([0, 0, 10, 10], nx=2, ny=2, rand=rand),
        *poisson_disk([0, 0, 20, 20], radius=3, rand=rand, max_points=8),
    ]

    assert all(
        coordinate == round(coordinate, 12)
        for point in points
        for coordinate in point.tuple()
    )


@pytest.mark.parametrize(
    ("call", "parameter"),
    [
        (lambda: halton(0), "n"),
        (lambda: halton(1, base_x=1), "base_x"),
        (lambda: halton(1, base_y=1), "base_y"),
        (lambda: halton(1, skip=-1), "skip"),
        (lambda: halton(1, box=[0, 0, 1]), "box"),
        (lambda: halton(1, box=7), "box"),
        (lambda: halton(1, box=[0, 0, math.inf, 1]), "box"),
        (lambda: halton(1, box=[0, 0, 0, 1]), "box"),
        (lambda: poisson_disk([0, 0, 10, 10], radius=0), "radius"),
        (lambda: poisson_disk([0, 0, 10, 10], radius=1, k=0), "k"),
        (lambda: poisson_disk([0, 0, 10, 10], radius=1, max_points=0), "max_points"),
        (lambda: poisson_disk([0, 0, 10, 0], radius=1), "box"),
        (lambda: jittered_grid([0, 0, 10, 10], nx=0, ny=1), "nx"),
        (lambda: jittered_grid([0, 0, 10, 10], nx=1, ny=0), "ny"),
        (lambda: jittered_grid([0, 0, 10, 10], nx=1, ny=1, amount=-0.1), "amount"),
        (lambda: jittered_grid([0, 0, 10, 10], nx=1, ny=1, amount=1.1), "amount"),
        (lambda: jittered_grid([0, 0, 0, 10], nx=1, ny=1), "box"),
        (lambda: Rand(0).point_in_rect([0, 0, 0, 10]), "box"),
        (lambda: Rand(0).point_in_circle(0, 0, 0), "r"),
        (lambda: Rand(0).point_in_circle(math.inf, 0, 1), "cx"),
        (lambda: Rand(0).jitter((0, 0), -1), "radius"),
        (lambda: Rand(0).jitter((math.inf, 0), 1), "coordinates"),
    ],
)
def test_sampling_guards_name_offending_parameter(call, parameter: str):
    with pytest.raises(ValueError, match=parameter):
        call()


def test_sampling_rejects_non_rand_streams_and_honours_single_point_cap():
    with pytest.raises(TypeError, match="rand"):
        poisson_disk([0, 0, 10, 10], radius=1, rand=object())
    with pytest.raises(TypeError, match="rand"):
        jittered_grid([0, 0, 10, 10], nx=1, ny=1, rand=object())

    assert len(poisson_disk([0, 0, 10, 10], radius=1, max_points=1)) == 1


def test_sampling_does_not_perturb_global_random_state():
    random.seed(18497)
    expected = [random.random(), random.random(), random.random()]

    random.seed(18497)
    observed = [random.random()]
    rand = Rand("isolated")
    rand.uniform()
    rand.shuffled([1, 2, 3])
    halton(5)
    jittered_grid([0, 0, 10, 10], nx=2, ny=2, rand=rand)
    poisson_disk([0, 0, 20, 20], radius=3, rand=rand)
    observed.extend([random.random(), random.random()])

    assert observed == expected


def test_poisson_serialized_output_has_stable_regression_hash():
    points = poisson_disk([0, 0, 64, 48], radius=5, rand=Rand("hash-contract"))
    payload = json.dumps(_tuples(points), separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()
    assert digest == "ca03b2b43e6708dccc883a85d9938dda30ba33d1f651f1ca05395050e400024a"


# The example-parity test that lived here moved out with the cookbook;
# it now runs in frameforge-example/tests/test_example_parity.py.
def test_generated_sdk_docs_include_sampling_signatures_and_usage():
    api = (ROOT / "docs/sdk-api.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs/sdk.md").read_text(encoding="utf-8")

    api_fragments = (
        "## `frameforge_sdk.rand`",
        "### `Rand`",
        "### `halton`",
        "### `poisson_disk`",
        "### `jittered_grid`",
        "max_points",
    )
    guide_fragments = (
        "## Deterministic sampling",
        "Rand(\"document\").derive(\"dots\")",
        "poisson_disk",
        "halton",
        "jittered_grid",
        "not cryptographic",
    )

    assert not [fragment for fragment in api_fragments if fragment not in api]
    assert not [fragment for fragment in guide_fragments if fragment not in guide]
