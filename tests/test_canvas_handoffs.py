"""Track B canvas-resolution handoffs (pixel-perfect campaign, C2 stage).

HANDOFF-warn     — the Renderer wires its structured `warn` sink into
                   CanvasResolver, so an unknown preset lands in
                   `diagnostics["warnings"]` instead of a loose UserWarning.
HANDOFF-html     — backends/html.py `canvas_size` delegates to the canonical
                   CanvasResolver (ONE implementation): orientation and
                   physical units are honoured, exactly like the SVG lane.
HANDOFF-validate — tooling/validate.py `_canvas_wh` mirrors the resolver's
                   orientation/units handling (keeping its None-on-unknown
                   contract for the canvas-unresolved audit).
"""
import warnings

import pytest

from frameforge.rendering.application.renderer import Renderer
from frameforge.rendering.domain.services.canvas_resolver import DEFAULT_WH
from frameforge.rendering.infrastructure.backends.html import canvas_size

import validate as V

MM = 96 / 25.4  # CSS mm → px (CSS Values 4 §6.2)


# --------------------------------------------------------------------------- #
# HANDOFF-warn — unknown preset reaches renderer diagnostics                   #
# --------------------------------------------------------------------------- #

def test_unknown_preset_lands_in_renderer_diagnostics():
    doc = {"dsl": "FrameForge", "version": "2.5.0",
           "pages": [{"mode": "page", "id": "p", "canvas": "definitely-not-a-preset",
                      "layers": []}]}
    r = Renderer(doc, ".")
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # wired sink means NO stdlib UserWarning
        svg = r.render_page(doc["pages"][0])[0]
    assert f'width="{DEFAULT_WH[0]}"' in svg
    kinds = [w["kind"] for w in r.diagnostics["warnings"]]
    assert "canvas_preset_unknown" in kinds
    event = next(w for w in r.diagnostics["warnings"]
                 if w["kind"] == "canvas_preset_unknown")
    assert event["preset"] == "definitely-not-a-preset"


# --------------------------------------------------------------------------- #
# HANDOFF-html — canvas_size == CanvasResolver semantics                       #
# --------------------------------------------------------------------------- #

def test_html_canvas_size_honours_orientation():
    assert canvas_size({"canvas": {"preset": "A4", "orientation": "landscape"}}) == (842, 595)
    assert canvas_size({"canvas": {"preset": "16x9", "orientation": "portrait"}}) == (1080, 1920)
    # identity when the preset already points the requested way
    assert canvas_size({"canvas": {"preset": "A4", "orientation": "portrait"}}) == (595, 842)


def test_html_canvas_size_honours_physical_units():
    w, h = canvas_size({"canvas": {"size": [297, 210], "units": "mm"}})
    assert w == pytest.approx(297 * MM)
    assert h == pytest.approx(210 * MM)
    # pt/px (and absent) stay 1:1 per the documented renderer convention
    assert canvas_size({"canvas": {"size": [595, 842], "units": "pt"}}) == (595, 842)
    assert canvas_size({"canvas": {"size": [640, 480]}}) == (640, 480)


def test_html_canvas_size_preset_and_default_paths_unchanged():
    assert canvas_size({"canvas": "deck-16x9"}) == (1920, 1080)
    assert canvas_size({}) == DEFAULT_WH
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # unknown preset is loud (resolver policy)
        assert canvas_size({"canvas": "no-such-preset"}) == DEFAULT_WH


# --------------------------------------------------------------------------- #
# HANDOFF-validate — _canvas_wh mirrors orientation/units                      #
# --------------------------------------------------------------------------- #

def test_validate_canvas_wh_honours_orientation():
    assert V._canvas_wh({"preset": "A4", "orientation": "landscape"}) == (842, 595)
    assert V._canvas_wh({"preset": "16x9", "orientation": "portrait"}) == (1080, 1920)
    assert V._canvas_wh({"preset": "A4"}) == (595, 842)


def test_validate_canvas_wh_honours_physical_units():
    w, h = V._canvas_wh({"size": [297, 210], "units": "mm"})
    assert w == pytest.approx(297 * MM)
    assert h == pytest.approx(210 * MM)
    assert V._canvas_wh({"size": [595, 842], "units": "pt"}) == (595, 842)


def test_validate_canvas_wh_keeps_none_on_unknown():
    # None-on-unknown feeds the canvas-unresolved audit — must NOT become a
    # silent DEFAULT_WH fallback here.
    assert V._canvas_wh({"preset": "no-such-preset"}) is None
    assert V._canvas_wh("no-such-preset") is None


# --------------------------------------------------------------------------- #
#  Lockstep pins — the validator's mirrors may never drift from the resolver   #
# --------------------------------------------------------------------------- #
def test_validate_unit_table_is_lockstep_with_the_resolver():
    """tooling/validate.py mirrors CanvasResolver._UNIT_TO_PX by copy (it cannot
    delegate: resolve() returns DEFAULT_WH on unknowns, the validator needs
    None). A copy without a pin is silent-drift waiting to happen — this gate
    makes divergence loud."""
    import importlib

    from frameforge.rendering.domain.services.canvas_resolver import _UNIT_TO_PX as _CR_UNITS

    validate = importlib.import_module("validate")
    assert validate._UNIT_TO_PX == _CR_UNITS


def test_validate_orientation_matches_resolver_for_samples():
    """Same document → same geometry in both lanes, for the orientation and
    physical-unit paths the C2 handoffs added."""
    import importlib

    from frameforge.rendering.domain.services.canvas_resolver import CanvasResolver

    validate = importlib.import_module("validate")
    samples = [
        {"preset": "A4", "orientation": "landscape"},
        {"preset": "4k", "orientation": "portrait"},
        {"size": [297, 210], "units": "mm"},
        {"size": [10, 5], "units": "in", "orientation": "landscape"},
    ]
    resolver = CanvasResolver({})
    for canvas in samples:
        assert validate._canvas_wh(canvas) == resolver.resolve({"canvas": canvas}), canvas
