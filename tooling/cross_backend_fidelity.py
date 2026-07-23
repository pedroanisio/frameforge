#!/usr/bin/env python3
"""Cross-backend fidelity floor — SVG proxy vs HTML backend (GH #86).

Two backends rendering the SAME document should look the same. The SVG golden
lock and the HTML lock each pin their own backend exactly, so any regression in
either is caught — but neither asserts that the two AGREE. This harness rasterises
page 1 of every oracle fixture through both backends, scores them with NCC (the
shared `image_metrics`, phase-aligned), and pins a per-fixture floor. A change
that pulls the renderers apart drops below the floor and fails; the floor is
re-pinned only deliberately, like the golden lock.

Dependency-gated: SVG→PNG needs CairoSVG, HTML→PNG needs a headless browser
(Playwright/Chromium), scoring needs numpy+PIL. When any is absent the gate is
SKIPPED, never failed — the dependency-free core stays runnable
(`deps_available()` is the single source of truth the tests import).

    python tooling/cross_backend_fidelity.py            # check against the floors
    python tooling/cross_backend_fidelity.py --update   # re-pin the floors
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for _p in (ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import render_golden as RG  # noqa: E402

FLOORS = os.path.join(ROOT, "tests", "golden", "cross-backend-fidelity.json")
# Regression band: a drop of more than this below the pinned floor fails. Small
# enough to catch a real divergence, wide enough to absorb sub-pixel raster
# jitter across machines/browser builds.
EPS = 0.02
# The raster comparison size (square); NCC is scale-normalised anyway.
_RASTER = 512
# A floor is only MEANINGFUL where the two backends actually agree. Below this,
# the HTML backend is DEGRADING (it lowers flow content — paragraphs, tables,
# TOC — to labelled placeholders by design; see docs/output-space.md, GH #73),
# so a low NCC is correct behaviour, not a regression, and pinning it as a floor
# would assert nothing. Such fixtures are EXCLUDED explicitly (with their score),
# never silently — the gate guards only the pages the backends render alike.
_MEANINGFUL = 0.5


def oracle_fixtures() -> list[str]:
    return RG.oracle_fixtures()


def deps_available() -> bool:
    """Every dependency the raster comparison needs is importable/usable."""
    try:
        import cairosvg  # noqa: F401
        import numpy  # noqa: F401
        from PIL import Image  # noqa: F401
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        return False
    return True


def _load_doc(path: str) -> dict:
    return RG._load_doc(path)


def render_svg_png(fixture: str) -> bytes:
    """Page 1 of a fixture, SVG proxy → PNG (CairoSVG), at the canvas aspect ratio.

    Rendered at the SVG's NATURAL size, not forced square: the HTML page
    screenshot preserves the canvas aspect, so forcing the SVG to a square would
    distort one backend relative to the other and tank NCC on any non-square
    page. `image_metrics` resizes both to its comparison square identically, so
    matching input aspect ratios is what keeps the comparison honest.
    """
    import cairosvg
    from frameforge.rendering.application.renderer import Renderer
    doc = _load_doc(fixture)
    svg = Renderer(doc, os.path.dirname(fixture)).render_page(doc["pages"][0])[0]
    return cairosvg.svg2png(bytestring=svg.encode("utf-8"))


def render_html_png(fixture: str) -> bytes | None:
    """Page 1 of a fixture, HTML backend → PNG (headless Chromium).

    Screenshots the `.frameforge-page` element, not the whole document — the
    figure/caption shell (GH #73) is chrome, not the rendered page, so isolating
    the page box is the apples-to-apples comparison with the SVG canvas.
    """
    import tempfile
    from pathlib import Path
    from playwright.sync_api import sync_playwright
    from frameforge.rendering.infrastructure.backends.html import render_document
    html = render_document(_load_doc(fixture))
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "doc.html"
        p.write_text(html, encoding="utf-8")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox"])
            try:
                page = browser.new_page()
                page.goto(p.resolve().as_uri())
                page.wait_for_timeout(300)
                el = page.query_selector(".frameforge-page")
                if el is None:
                    return None
                return el.screenshot()
            finally:
                browser.close()


def cross_backend_ncc(fixture: str) -> float | None:
    """Phase-aligned NCC between the SVG and HTML page-1 rasters (None if either
    backend produced nothing to compare)."""
    from frameforge.vision.infrastructure.image_compare import image_metrics, load_rgb
    html_png = render_html_png(fixture)
    if html_png is None:
        return None
    svg_img = load_rgb(render_svg_png(fixture))
    html_img = load_rgb(html_png)
    return image_metrics(svg_img, html_img, size=_RASTER, align=True)["ncc"]


def _read_floors_file() -> dict:
    if not os.path.exists(FLOORS):
        return {"floors": {}, "excluded": {}}
    with open(FLOORS, encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("floors", {})
    data.setdefault("excluded", {})
    return data


def load_floors() -> dict[str, float]:
    """The pinned floors — fixtures the backends render alike (the guarded set)."""
    return _read_floors_file()["floors"]


def load_excluded() -> dict[str, dict]:
    """Fixtures excluded from the floor, each with {ncc, reason} — the HTML
    backend degrades flow content, so these two backends legitimately disagree."""
    return _read_floors_file()["excluded"]


def build_floors() -> dict:
    """Measure every oracle fixture; split into guarded floors vs documented
    exclusions at `_MEANINGFUL`. A pinned floor is always a real assertion; an
    exclusion is always explicit (never a silent omission)."""
    floors: dict[str, float] = {}
    excluded: dict[str, dict] = {}
    for path in oracle_fixtures():
        ncc = cross_backend_ncc(path)
        if ncc is None:
            continue
        rel = os.path.relpath(path, ROOT)
        if ncc >= _MEANINGFUL:
            floors[rel] = round(ncc, 3)
        else:
            excluded[rel] = {
                "ncc": round(ncc, 3),
                "reason": "HTML backend degrades flow content to placeholders "
                          "(docs/output-space.md); the two backends legitimately "
                          "diverge, so no fidelity floor is meaningful here",
            }
    return {"floors": floors, "excluded": excluded}


def write_floors(data: dict) -> None:
    os.makedirs(os.path.dirname(FLOORS), exist_ok=True)
    with open(FLOORS, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true", help="re-pin the fidelity floors")
    args = ap.parse_args(argv)
    if not deps_available():
        print("cross_backend_fidelity: raster deps absent (cairosvg + browser + "
              "numpy/PIL); nothing to do", file=sys.stderr)
        return 0
    if args.update:
        data = build_floors()
        write_floors(data)
        print(f"cross_backend_fidelity: pinned {len(data['floors'])} floor(s), "
              f"excluded {len(data['excluded'])} flow-degraded -> "
              f"{os.path.relpath(FLOORS, ROOT)}")
        for k, v in sorted(data["floors"].items()):
            print(f"  guard  {k}: {v}")
        for k, v in sorted(data["excluded"].items()):
            print(f"  skip   {k}: {v['ncc']} (flow-degraded)")
        return 0
    floors = load_floors()
    if not floors:
        print("cross_backend_fidelity: no floors pinned; run with --update",
              file=sys.stderr)
        return 1
    failures = []
    for fixture, floor in sorted(floors.items()):
        ncc = cross_backend_ncc(os.path.join(ROOT, fixture))
        if ncc is None:
            continue
        status = "OK" if ncc >= floor - EPS else "DRIFT"
        print(f"  [{status}] {fixture}: NCC {ncc:.3f} (floor {floor:.3f})")
        if ncc < floor - EPS:
            failures.append(fixture)
    if failures:
        print(f"cross_backend_fidelity: {len(failures)} fixture(s) drifted below "
              "the floor; review, then --update if intentional")
        return 1
    print(f"cross_backend_fidelity: OK — {len(floors)} fixture(s) within the floor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
