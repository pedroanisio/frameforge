"""Cross-backend fidelity floor — SVG and HTML must not silently diverge (GH #86).

Two backends rendering the SAME document should look the same. Nothing in the
repo asserted that: HTML vs SVG on a real page measured NCC 0.878, and that number
was unowned — it could have drifted to 0.4 with every gate green. Backend
divergence was only ever found by a human comparing screenshots.

This pins a per-fixture NCC floor between the SVG proxy raster and the HTML
backend raster of each oracle fixture (page 1), so a change that pulls the two
renderers apart fails a gate instead of shipping. It is dependency-gated
(CairoSVG for SVG→PNG, a headless browser for HTML→PNG): skipped, never failed,
when a dependency is absent — the dependency-free core stays runnable.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for p in (ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs"),
          os.path.join(ROOT, "tooling")):
    if p not in sys.path:
        sys.path.insert(0, p)

_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

fidelity = pytest.importorskip("cross_backend_fidelity",
                               reason="fidelity harness import")


def _deps_present() -> bool:
    return fidelity.deps_available()


requires_raster = pytest.mark.skipif(
    not _deps_present(), reason="raster deps (cairosvg + browser + numpy/PIL) absent")


@requires_raster
def test_svg_and_html_agree_within_the_floor():
    """Every oracle fixture's SVG and HTML page-1 raster must clear its floor."""
    floors = fidelity.load_floors()
    assert floors, "no fidelity floors pinned — run the harness with --update"
    failures = []
    for fixture, floor in floors.items():
        ncc = fidelity.cross_backend_ncc(fixture)
        if ncc is None:
            continue
        if ncc < floor - fidelity.EPS:
            failures.append(f"{fixture}: NCC {ncc:.3f} < floor {floor:.3f}")
    assert not failures, "cross-backend fidelity regressed:\n  " + "\n  ".join(failures)


@requires_raster
def test_identical_backends_score_perfectly():
    """Sanity: the same raster against itself is NCC 1.0 (the metric is sound)."""
    from frameforge.vision.infrastructure.image_compare import image_metrics, load_rgb
    png = fidelity.render_svg_png(fidelity.oracle_fixtures()[0])
    img = load_rgb(png)
    assert image_metrics(img, img)["ncc"] >= 0.999


def test_floors_are_pinned_and_reasonable():
    """The floor file must exist and hold sane values (no deps needed to check)."""
    floors = fidelity.load_floors()
    assert floors, "fidelity floors must be pinned"
    for fixture, floor in floors.items():
        assert 0.0 <= floor <= 1.0, f"{fixture}: floor {floor} out of range"


def test_every_oracle_fixture_is_guarded_or_explicitly_excluded():
    """No silent omission: each fixture is either floored or documented-excluded.

    A fixture the HTML backend degrades (flow content → placeholders) is excluded
    WITH its measured score and a reason — never dropped quietly. So the set of
    (floors ∪ excluded) must be exactly the oracle.
    """
    covered = set(fidelity.load_floors()) | set(fidelity.load_excluded())
    fixtures = {os.path.relpath(p, ROOT) for p in fidelity.oracle_fixtures()}
    missing = fixtures - covered
    assert not missing, f"fixtures neither floored nor excluded: {sorted(missing)}"


def test_pinned_floors_are_meaningful():
    """A pinned floor must actually assert agreement — no near-zero theater."""
    for fixture, floor in fidelity.load_floors().items():
        assert floor >= fidelity._MEANINGFUL - fidelity.EPS, (
            f"{fixture}: floor {floor} is below the meaningful threshold — "
            "it should be an explicit exclusion, not a floor")


def test_exclusions_carry_a_reason():
    """Every exclusion documents why the backends legitimately diverge."""
    for fixture, rec in fidelity.load_excluded().items():
        assert rec.get("reason"), f"{fixture} excluded with no reason"
        assert "ncc" in rec, f"{fixture} excluded without its measured score"
