#!/usr/bin/env python3
"""RED — unified point-spec grammar across overlay/construct/score/map tools.

The discriminated point dict already accepted by ``mark_points``/``workspace``
(``resolve_point_spec`` in ``framegraph.vision.domain.coordinates``) must become
accepted — ADDITIVELY, with every legacy shape byte-identical — in:

1. ``overlay_images`` landmark pairs (``_to_pairs``): ``{"px": ..}`` / ``{"norm": ..}``
   dict entries per side, resolved against THAT side's image size; dict entries are
   self-describing (pair-level ``"norm"`` flag ignored for them); session-scoped
   forms (cs/landmark/viewport_px) raise ValueError naming the supported forms.
2. ``construct_vectors`` / ``score_reconstruction`` shape ``points``: legacy
   ``[x, y]``, ``{"px": ..}``, ``{"norm": ..}`` (resolved against the source dims),
   or ``{"landmark": id, "dx"?, "dy"?}`` via the same anchors map as ``pins``.
3. ``map_coordinates``: ``{"px": ..}`` anywhere in ``pairs``/2D ``points``;
   ``{"norm": ..}`` only when dims are resolvable, else a structured error dict.

Every test imports the surface under test lazily so each fails individually
(missing feature), never at collection.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

import pytest  # noqa: E402

BASE_SIZE = (100, 200)
OVERLAY_SIZE = (50, 60)


def _write_test_png(tmp_path, name="source.png", size=(60, 40)):
    """A tiny deterministic raster with real edges (a rectangle outline)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, size[0] - 10, size[1] - 10], outline="black", width=2)
    path = tmp_path / name
    img.save(path)
    return str(path)


# ─────────────────────────────────────────────────────────────
# 1. overlay_images pair parsing (_to_pairs)
# ─────────────────────────────────────────────────────────────
def test_overlay_px_dict_equals_legacy_list():
    from framegraph.vision.infrastructure.overlay_align import _to_pairs

    legacy = _to_pairs([{"base": [10, 20], "overlay": [3, 4]}], BASE_SIZE, OVERLAY_SIZE)
    dicts = _to_pairs([{"base": {"px": [10, 20]}, "overlay": {"px": [3, 4]}}],
                      BASE_SIZE, OVERLAY_SIZE)
    assert dicts == legacy


def test_overlay_norm_dict_resolves_against_own_sides_dims():
    from framegraph.vision.infrastructure.overlay_align import _to_pairs

    pairs = _to_pairs(
        [{"base": {"norm": [0.5, 0.5]}, "overlay": {"norm": [0.5, 0.5]}}],
        BASE_SIZE, OVERLAY_SIZE)
    (b, o), = pairs
    assert b == (50.0, 100.0)   # 0.5 of base (100, 200)
    assert o == (25.0, 30.0)    # 0.5 of overlay (50, 60) — NOT base dims


def test_overlay_mixed_dict_and_legacy_with_pair_level_norm_flag():
    from framegraph.vision.infrastructure.overlay_align import _to_pairs

    # dict entries are self-describing: the pair-level "norm" flag must apply
    # to the legacy list side only and be ignored for the dict side.
    pairs = _to_pairs(
        [{"base": {"px": [10, 20]}, "overlay": [0.5, 0.5], "norm": True}],
        BASE_SIZE, OVERLAY_SIZE)
    (b, o), = pairs
    assert b == (10.0, 20.0)
    assert o == (25.0, 30.0)


def test_overlay_session_scoped_dict_forms_raise_naming_supported_forms():
    from framegraph.vision.infrastructure.overlay_align import _to_pairs

    for bad in ({"cs": [1, 2]}, {"landmark": "A1"}, {"viewport_px": [5, 5]}):
        with pytest.raises(ValueError) as exc_info:
            _to_pairs([{"base": bad, "overlay": [3, 4]}], BASE_SIZE, OVERLAY_SIZE)
        msg = str(exc_info.value)
        assert "px" in msg and "norm" in msg, (
            f"error for {bad!r} must name the supported forms (px, norm), got: {msg}")


# ─────────────────────────────────────────────────────────────
# 2. construct_vectors / score_reconstruction shape points
# ─────────────────────────────────────────────────────────────
def _construct_yaml(tmp_path, session_id, points):
    from framegraph.mcp import usecases

    res = usecases.construct_vectors(
        shapes=[{"kind": "line", "points": points}],
        width=100, height=200, raster_png=False,
        session_root=tmp_path, session_id=session_id)
    assert res.get("ok") is True, f"construct_vectors failed: {res.get('error')}"
    yaml_path = tmp_path / session_id / "generated.fg.yaml"
    assert yaml_path.is_file(), "no generated.fg.yaml was written"
    return yaml_path.read_text(encoding="utf-8")


def test_construct_vectors_px_and_norm_dicts_match_legacy_yaml(tmp_path):
    legacy = _construct_yaml(tmp_path, "legacy", [[10, 20], [50, 100]])
    # norm resolves against the explicit width/height (100, 200) → (50, 100)
    unified = _construct_yaml(tmp_path, "unified",
                              [{"px": [10, 20]}, {"norm": [0.5, 0.5]}])
    assert unified == legacy


def test_construct_vectors_landmark_dict_resolves_via_pin_anchors(tmp_path):
    from framegraph.vision.infrastructure import workspace as ws

    ws_dir = tmp_path / "anchors"
    ws_dir.mkdir()
    state = ws.WorkspaceState(image_ref="unused.png", width=100, height=200,
                              pins=[ws.Pin("P1", 10.0, 20.0)])
    ws.save_state(ws_dir, state)

    from framegraph.mcp import usecases

    def build(session_id, points):
        res = usecases.construct_vectors(
            shapes=[{"kind": "line", "points": points}],
            from_workspace="anchors", width=100, height=200, raster_png=False,
            session_root=tmp_path, session_id=session_id)
        assert res.get("ok") is True, f"construct_vectors failed: {res.get('error')}"
        return (tmp_path / session_id / "generated.fg.yaml").read_text(encoding="utf-8")

    # P1+(5,-5) → (15, 15); structural landmark A9 (centre of 100×200) → (50, 100)
    legacy = build("lm-legacy", [[15, 15], [50, 100]])
    unified = build("lm-unified",
                    [{"landmark": "P1", "dx": 5, "dy": -5}, {"landmark": "A9"}])
    assert unified == legacy


def test_construct_vectors_unknown_dict_key_names_accepted_forms(tmp_path):
    from framegraph.mcp import usecases

    res = usecases.construct_vectors(
        shapes=[{"kind": "line", "points": [{"bogus": [1, 2]}, [3, 4]]}],
        width=100, height=200, raster_png=False,
        session_root=tmp_path, session_id="badkey")
    assert res.get("ok") is False
    msg = str(res.get("error", ""))
    assert "px" in msg and "norm" in msg and "landmark" in msg, (
        f"error must name the accepted point forms, got: {msg}")


def test_score_reconstruction_accepts_dict_point_grammar(tmp_path):
    from framegraph.mcp import usecases

    image = _write_test_png(tmp_path, size=(60, 40))
    legacy = usecases.score_reconstruction(
        image, [{"kind": "rect", "points": [[10, 10], [50, 30]]}],
        session_root=tmp_path, session_id="score-legacy")
    assert legacy.get("ok") is True, f"legacy scoring failed: {legacy.get('error')}"

    # norm resolves against the image dims (60, 40) → (50, 30)
    unified = usecases.score_reconstruction(
        image, [{"kind": "rect",
                 "points": [{"px": [10, 10]}, {"norm": [50 / 60, 30 / 40]}]}],
        session_root=tmp_path, session_id="score-unified")
    assert unified.get("ok") is True, f"dict points rejected: {unified.get('error')}"
    for key in ("on_edge_frac", "mean_dist"):
        assert unified["score"][key] == legacy["score"][key]


# ─────────────────────────────────────────────────────────────
# 3. map_coordinates pairs / points
# ─────────────────────────────────────────────────────────────
_HOMOGRAPHY_PAIRS = [
    ([0, 0], [0, 0]),
    ([100, 0], [200, 0]),
    ([100, 100], [200, 200]),
    ([0, 100], [0, 200]),
]


def test_map_homography_px_dicts_equal_bare_lists(tmp_path):
    from framegraph.mcp import usecases

    legacy = usecases.map_coordinates(
        "homography",
        pairs=[{"src": s, "dst": d} for s, d in _HOMOGRAPHY_PAIRS],
        points=[[50, 50]],
        session_root=tmp_path, session_id="map-legacy")
    assert legacy.get("ok") is True, f"legacy homography failed: {legacy.get('error')}"

    unified = usecases.map_coordinates(
        "homography",
        pairs=[{"src": {"px": s}, "dst": {"px": d}} for s, d in _HOMOGRAPHY_PAIRS],
        points=[{"px": [50, 50]}],
        session_root=tmp_path, session_id="map-unified")
    assert unified.get("ok") is True, f"px dicts rejected: {unified.get('error')}"
    assert unified["spatial"]["matrix"] == legacy["spatial"]["matrix"]
    assert unified["spatial"]["mapped_points"] == legacy["spatial"]["mapped_points"]


def test_map_homography_norm_dicts_resolve_with_width_height(tmp_path):
    from framegraph.mcp import usecases

    legacy = usecases.map_coordinates(
        "homography",
        pairs=[{"src": s, "dst": d} for s, d in _HOMOGRAPHY_PAIRS],
        points=[[50, 50]],
        session_root=tmp_path, session_id="map-legacy-wh")
    assert legacy.get("ok") is True, f"legacy homography failed: {legacy.get('error')}"

    # with width=100, height=100 given: norm [1, 1] → px [100, 100], etc.
    unified = usecases.map_coordinates(
        "homography",
        pairs=[
            {"src": {"norm": [0, 0]}, "dst": {"px": [0, 0]}},
            {"src": {"norm": [1, 0]}, "dst": {"px": [200, 0]}},
            {"src": {"norm": [1, 1]}, "dst": {"px": [200, 200]}},
            {"src": {"norm": [0, 1]}, "dst": {"px": [0, 200]}},
        ],
        points=[{"norm": [0.5, 0.5]}],
        width=100, height=100,
        session_root=tmp_path, session_id="map-unified-wh")
    assert unified.get("ok") is True, f"norm dicts rejected: {unified.get('error')}"
    assert unified["spatial"]["matrix"] == legacy["spatial"]["matrix"]
    assert unified["spatial"]["mapped_points"] == legacy["spatial"]["mapped_points"]


def test_map_homography_norm_without_dims_is_structured_error(tmp_path):
    from framegraph.mcp import usecases

    res = usecases.map_coordinates(
        "homography",
        pairs=[{"src": {"norm": [0, 0]}, "dst": [0, 0]},
               {"src": {"norm": [1, 0]}, "dst": [200, 0]},
               {"src": {"norm": [1, 1]}, "dst": [200, 200]},
               {"src": {"norm": [0, 1]}, "dst": [0, 200]}],
        session_root=tmp_path, session_id="map-norm-nodims")
    assert isinstance(res, dict), "must return a structured error dict, not raise"
    assert res.get("ok") is False
    msg = str(res.get("error", "")).lower()
    assert "norm" in msg and "dim" in msg, (
        f"error must explain that norm needs dims, got: {msg}")


def test_map_warp_norm_dst_resolves_against_out_size(tmp_path):
    """A warp pair's ``dst`` lives in the OUTPUT canvas: ``{"norm": ..}`` on the dst
    side must resolve against ``out_size``, not the source image dims."""
    from framegraph.mcp import usecases

    image = _write_test_png(tmp_path, size=(100, 50))
    res = usecases.map_coordinates(
        "warp",
        image=image,
        out_size=[200, 100],
        pairs=[
            {"src": {"px": [0, 0]}, "dst": {"norm": [0, 0]}},
            {"src": {"px": [100, 0]}, "dst": {"norm": [1, 0]}},
            {"src": {"px": [100, 50]}, "dst": {"norm": [1, 1]}},
            {"src": {"px": [0, 50]}, "dst": {"norm": [0, 1]}},
        ],
        session_root=tmp_path, session_id="warp-norm-dst")
    assert res.get("ok") is True, f"warp rejected norm dst: {res.get('error')}"
    matrix = res["spatial"]["matrix"]
    # Image corners → out_size corners is a pure 2x scale. With the dst side
    # wrongly resolved against the image dims, the fit collapses to identity.
    assert matrix[0][0] == pytest.approx(2.0, abs=1e-6), matrix
    assert matrix[1][1] == pytest.approx(2.0, abs=1e-6), matrix
    assert matrix[0][1] == pytest.approx(0.0, abs=1e-6), matrix
    assert matrix[1][0] == pytest.approx(0.0, abs=1e-6), matrix
