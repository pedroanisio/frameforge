#!/usr/bin/env python3
"""test_humanize.py — the seeded imperfection 'hand' (docs/models Humanize + sdk.humanize).

Pins the contract that lets a stochastic-looking feature live inside a deterministic
golden-fixture regime:

  * ABSENCE IS IDENTITY — a document without a ``humanize`` spec expands (and renders)
    exactly as before, so existing golden locks cannot move.
  * DETERMINISTIC — same document + same seed → byte-identical output; a different
    seed re-performs the page.
  * BOUNDED — every channel delta is provably within its declared amplitude.
  * ROUND-ROBIN — two identical objects never perturb identically.
  * CORRELATED — channels co-vary (one hand, not independent dice) — our frame.
  * TOPOLOGY-PRESERVING — an object a connector attaches to is exempt from rotation.
  * SUPPRESSIBLE — ``ExpandOptions(humanize=False)`` forces the pass off (measurement
    renders must never be perturbed).
"""
import copy
import re
import statistics

import pytest

from framegraph.sdk.conform import page_hashes
from framegraph.sdk.expand import ExpandOptions, expand
from framegraph.sdk.humanize import Hand, apply_humanize
from framegraph.sdk.model import validate_document


# --------------------------------------------------------------------------- #
#  document builders                                                          #
# --------------------------------------------------------------------------- #
def _doc(objects, humanize=None):
    doc = {
        "dsl": "FrameGraph",
        "version": "2.3.0",
        "pages": [{
            "mode": "page", "id": "pg",
            "canvas": {"size": [320, 200], "units": "px"},
            "layers": [{"id": "l1", "objects": objects}],
        }],
    }
    if humanize is not None:
        doc["humanize"] = humanize
    return doc


def _rect(rid, x, **extra):
    obj = {"type": "rect", "id": rid, "box": [x, 10, 80, 40], "fill": "#3388ff"}
    obj.update(extra)
    return obj


def _expand_objs(doc, **opts):
    """Expand and return the layer-0 object list of page 0 (as plain dicts)."""
    expanded = expand(doc, ExpandOptions(**opts)).document
    data = expanded.model_dump(by_alias=True, exclude_none=True)
    return data["pages"][0]["layers"][0]["objects"]


_ROT_RE = re.compile(r"rotate\(([-\d.]+)deg\)")


def _tilt(obj):
    """The composed pitch-drift tilt (degrees) on an object, or None if untilted."""
    style = obj.get("style")
    if not isinstance(style, dict):
        return None
    tf = style.get("transform")
    if not isinstance(tf, str):
        return None
    m = _ROT_RE.search(tf)
    return float(m.group(1)) if m else None


HZ = {"seed": 42, "drift_deg": 1.2, "opacity": 0.15, "weight": 0.12, "grain": 0.6}


# --------------------------------------------------------------------------- #
#  absence is identity                                                        #
# --------------------------------------------------------------------------- #
def test_absent_humanize_is_identity():
    doc = _doc([_rect("a", 10, stroke_style={"stroke_width": 2.0}),
                _rect("b", 120, stroke_style={"stroke_width": 2.0})])
    plain = validate_document(doc).model_dump(by_alias=True, exclude_none=True)
    expanded = expand(doc).document.model_dump(by_alias=True, exclude_none=True)
    assert plain == expanded


def test_apply_humanize_no_spec_returns_same_object():
    data = _doc([_rect("a", 10)])
    # No humanize anywhere → identity, and cheap (no copy).
    assert apply_humanize(data) is data


# --------------------------------------------------------------------------- #
#  determinism                                                                #
# --------------------------------------------------------------------------- #
def test_same_seed_is_byte_identical():
    doc = _doc([_rect("a", 10), _rect("b", 120)], humanize=HZ)
    a = _expand_objs(doc)
    b = _expand_objs(doc)
    assert a == b


def test_different_seed_reperforms():
    base = _doc([_rect("a", 10), _rect("b", 120)], humanize=HZ)
    other = _doc([_rect("a", 10), _rect("b", 120)], humanize={**HZ, "seed": 43})
    assert _expand_objs(base) != _expand_objs(other)


def test_render_hash_stable_with_humanize():
    doc = _doc([_rect("a", 10), _rect("b", 120)], humanize=HZ)
    h1 = page_hashes(expand(doc).document)
    h2 = page_hashes(expand(doc).document)
    assert h1 == h2
    # and a humanized render actually differs from the mechanical one
    plain = page_hashes(validate_document(_doc([_rect("a", 10), _rect("b", 120)])))
    assert h1 != plain


# --------------------------------------------------------------------------- #
#  round-robin                                                                #
# --------------------------------------------------------------------------- #
def test_round_robin_identical_objects_differ():
    # two geometrically identical rects (no connector) must perturb differently
    doc = _doc([_rect("a", 10, stroke_style={"stroke_width": 2.0}),
                _rect("b", 120, stroke_style={"stroke_width": 2.0})], humanize=HZ)
    a, b = _expand_objs(doc)
    assert _tilt(a) != _tilt(b)
    assert a["stroke_style"]["stroke_width"] != b["stroke_style"]["stroke_width"]


# --------------------------------------------------------------------------- #
#  bounded (property test over many seeds/keys/amplitudes)                    #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", [0, 1, 7, 99, 100000])
@pytest.mark.parametrize("amp", [0.05, 0.2, 1.0])
def test_channels_bounded_by_amplitude(seed, amp):
    hand = Hand(seed=seed, drift_deg=amp * 30, opacity=amp, weight=amp, grain=0.5)
    eps = 1e-9
    for i in range(500):
        ch = hand.channels(f"obj-{i}")
        assert abs(ch["rotation"]) <= amp * 30 + eps
        assert abs(ch["opacity"]) <= amp + eps
        assert abs(ch["weight"]) <= amp + eps


def test_opacity_clamped_to_unit_interval():
    # a large opacity band must never push rendered opacity outside 0..1
    doc = _doc([_rect(f"r{i}", 10 + i) for i in range(30)],
               humanize={"seed": 3, "opacity": 1.0})
    for obj in _expand_objs(doc):
        assert 0.0 <= obj["opacity"] <= 1.0


# --------------------------------------------------------------------------- #
#  our frame: correlated channels + tension                                   #
# --------------------------------------------------------------------------- #
def _pearson(xs, ys):
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (sx * sy) if sx and sy else 0.0


def test_channels_are_correlated_not_independent():
    # weight and opacity share the h2 latent → they must co-vary (one hand).
    hand = Hand(seed=11, weight=1.0, opacity=1.0, drift_deg=10.0, grain=0.4)
    ws, os_ = [], []
    for i in range(600):
        ch = hand.channels(f"k{i}")
        ws.append(ch["weight"]); os_.append(ch["opacity"])
    assert _pearson(ws, os_) > 0.2


def test_grain_tension_shapes_excursions():
    # looser hand (grain 0) → larger mean excursion than a tight hand (grain 1).
    def mean_abs_rot(grain):
        hand = Hand(seed=5, drift_deg=10.0, grain=grain)
        return statistics.fmean(abs(hand.channels(f"k{i}")["rotation"]) for i in range(800))
    assert mean_abs_rot(0.0) > mean_abs_rot(1.0)


# --------------------------------------------------------------------------- #
#  topology-preserving                                                        #
# --------------------------------------------------------------------------- #
def test_connector_endpoints_exempt_from_rotation():
    objs = [
        _rect("free", 10),
        _rect("anchored", 120),
        {"type": "connector", "from": {"ref": "anchored"}, "to": {"ref": "free"}},
    ]
    doc = _doc(objs, humanize={"seed": 8, "drift_deg": 2.0})
    out = {o.get("id"): o for o in _expand_objs(doc) if o.get("id")}
    # both rects are connector endpoints → neither tilts
    assert _tilt(out["free"]) is None
    assert _tilt(out["anchored"]) is None


def test_free_object_rotates_when_no_connector():
    doc = _doc([_rect("solo", 10)], humanize={"seed": 8, "drift_deg": 2.0})
    (solo,) = _expand_objs(doc)
    tilt = _tilt(solo)
    assert tilt is not None and tilt != 0.0
    assert abs(tilt) <= 2.0


# --------------------------------------------------------------------------- #
#  cascade + suppression                                                      #
# --------------------------------------------------------------------------- #
def test_object_humanize_disable_overrides_document():
    doc = _doc([
        _rect("kept", 10),
        _rect("quiet", 120, humanize={"enabled": False}),
    ], humanize={"seed": 2, "drift_deg": 2.0, "opacity": 0.2})
    out = {o.get("id"): o for o in _expand_objs(doc) if o.get("id")}
    assert _tilt(out["kept"]) not in (None, 0.0)             # doc default applied
    assert _tilt(out["quiet"]) is None                       # object opted out
    assert "opacity" not in out["quiet"]


def test_object_humanize_overrides_params():
    shared = {"seed": 2, "drift_deg": 2.0}
    doc_default = _doc([_rect("x", 10)], humanize=shared)
    doc_override = _doc([_rect("x", 10, humanize={**shared, "seed": 999})], humanize=shared)
    (a,) = _expand_objs(doc_default)
    (b,) = _expand_objs(doc_override)
    assert _tilt(a) != _tilt(b)


def test_suppression_via_expand_option():
    doc = _doc([_rect("a", 10), _rect("b", 120)], humanize=HZ)
    on = _expand_objs(doc, humanize=True)
    off = _expand_objs(doc, humanize=False)
    plain = _doc([_rect("a", 10), _rect("b", 120)])
    plain_objs = validate_document(plain).model_dump(
        by_alias=True, exclude_none=True)["pages"][0]["layers"][0]["objects"]
    assert off == plain_objs      # forced off ⇒ objects untouched
    assert on != off              # and the pass really does something


def test_apply_humanize_is_pure():
    data = _doc([_rect("a", 10)], humanize={"seed": 1, "drift_deg": 2.0})
    before = copy.deepcopy(data)
    apply_humanize(data)
    assert data == before         # input dict is not mutated


# --------------------------------------------------------------------------- #
#  roughen — geometry-level coherent wobble (ported from build_a6.py)         #
# --------------------------------------------------------------------------- #
def _line(lid, x1, y1, x2, y2):
    return {"type": "line", "id": lid, "from": [x1, y1], "to": [x2, y2],
            "stroke": "#222", "stroke_style": {"stroke_width": 2.0}}


def _roughen_doc(objs):
    return _doc(objs, humanize={"seed": 5, "roughen": 1.2})


def test_roughen_converts_primitives_to_polylines():
    objs = [
        _line("ln", 10, 10, 200, 10),
        _rect("rc", 10, stroke_style={"stroke_width": 2.0}),
        {"type": "ellipse", "id": "el", "center": [80, 150], "rx": 40, "ry": 25,
         "stroke": "#a6442e", "stroke_style": {"stroke_width": 2.0}},
    ]
    out = {o.get("id"): o for o in _expand_objs(_roughen_doc(objs)) if o.get("id")}
    assert out["ln"]["type"] == "polyline" and out["ln"].get("closed") is None
    assert out["rc"]["type"] == "polyline" and out["rc"]["closed"] is True
    assert out["el"]["type"] == "polyline" and out["el"]["closed"] is True
    assert len(out["el"]["points"]) >= 3


def test_roughen_line_endpoints_are_pinned():
    (ln,) = _expand_objs(_roughen_doc([_line("ln", 10, 10, 200, 40)]))
    assert ln["points"][0] == [10.0, 10.0]     # endpoint-anchored: ends stay exact
    assert ln["points"][-1] == [200.0, 40.0]
    assert len(ln["points"]) > 2               # interior vertices wander


def test_roughen_is_deterministic_and_round_robin():
    objs = [_rect("a", 10, stroke_style={"stroke_width": 2.0}),
            _rect("b", 120, stroke_style={"stroke_width": 2.0})]
    a1 = _expand_objs(_roughen_doc(objs))
    a2 = _expand_objs(_roughen_doc(objs))
    assert a1 == a2                             # same seed → byte-identical
    by_id = {o["id"]: o for o in a1}
    assert by_id["a"]["points"] != by_id["b"]["points"]   # identical rects differ


def test_roughen_is_reorder_stable():
    # keyed on the object id, not draw order → reversing the list keeps each wobble
    objs = [_rect("a", 10), _rect("b", 120), _rect("c", 230)]
    fwd = {o["id"]: o for o in _expand_objs(_roughen_doc(objs))}
    rev = {o["id"]: o for o in _expand_objs(_roughen_doc(list(reversed(objs))))}
    assert fwd["a"]["points"] == rev["a"]["points"]


def test_roughen_preserves_paint_and_stroke():
    (rc,) = _expand_objs(_roughen_doc([_rect("rc", 10, fill="#dbe7f3",
                                             stroke="#20324a",
                                             stroke_style={"stroke_width": 2.0})]))
    assert rc["fill"] == "#dbe7f3" and rc["stroke"] == "#20324a"
    assert rc["stroke_style"]["stroke_width"] == 2.0


def test_roughen_exempts_connector_endpoints_and_text():
    objs = [
        _rect("anchored", 10, stroke_style={"stroke_width": 2.0}),
        {"type": "text", "id": "t", "box": [10, 120, 100, 20], "text": "hi"},
        {"type": "connector", "from": {"ref": "anchored"}, "to": [200, 200]},
    ]
    out = {o.get("id"): o for o in _expand_objs(_roughen_doc(objs)) if o.get("id")}
    assert out["anchored"]["type"] == "rect"   # connector endpoint stays crisp
    assert out["t"]["type"] == "text"          # text is never roughened


def test_typographic_objects_are_left_crisp():
    # text/labels are the type gates' domain — humanize must not tilt/fade/roughen them
    doc = _doc([
        {"type": "text", "id": "t", "box": [10, 10, 100, 20], "text": "hi"},
        _rect("r", 10),
    ], humanize={"seed": 3, "drift_deg": 2.0, "opacity": 0.3, "roughen": 1.5})
    out = {o.get("id"): o for o in _expand_objs(doc) if o.get("id")}
    assert out["t"]["type"] == "text"
    assert _tilt(out["t"]) is None and "opacity" not in out["t"]
    assert out["r"]["type"] == "polyline"          # the neighbouring rect IS humanized


def test_roughen_off_by_default_leaves_geometry():
    # a humanize with only scalar channels must not convert geometry
    doc = _doc([_rect("r", 10)], humanize={"seed": 1, "drift_deg": 1.0})
    (r,) = _expand_objs(doc)
    assert r["type"] == "rect" and "box" in r


# --------------------------------------------------------------------------- #
#  golden oracle must stay mechanical (render_golden hygiene gate)            #
# --------------------------------------------------------------------------- #
def test_oracle_is_free_of_humanize_specs():
    # The b1/ oracle bypasses expand(); a humanize spec there would be silently
    # ignored, so the gate forbids it. The current oracle must be clean.
    import render_golden
    assert render_golden.oracle_humanize_violations() == []


def test_find_humanize_detects_doc_and_nested_specs():
    import render_golden
    assert render_golden._find_humanize({"dsl": "FrameGraph"}) is None
    assert render_golden._find_humanize({"humanize": {"seed": 1}}) == "doc.humanize"
    nested = _doc([_rect("a", 10, humanize={"enabled": False})])
    assert render_golden._find_humanize(nested) is not None


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
