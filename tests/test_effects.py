"""Shadow / glow filter rendering for objects.

Backs the ported shadow/glow component (codebase-standards §6/§16 + the standing
rule: a reused component is backed by a checked-in fixture, not only synthetic
docs). v2 `shadow`/`glow` are Effect = bool | preset-string | EffectObject; each
renders as an SVG `<filter>` and the object is wrapped in `<g filter="url(#fx…)">`.

Subprocess (not an in-process import): the rendering package is named
`framegraph`, which would shadow the `framegraph` models module that
tests/test_head.py imports in a shared pytest process.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RENDER = os.path.join(ROOT, "tooling", "render_fixtures.py")

_RECT = {"type": "rect", "box": [40, 40, 120, 80], "fill": "#fff", "stroke": "#111",
         "stroke_style": {"stroke_width": 1}}


def _read_first_svg(out):
    svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
    assert svgs, "renderer produced no SVG"
    with open(svgs[0], encoding="utf-8") as fh:
        return fh.read()


def _render_obj(obj):
    doc = {"dsl": "FrameGraph", "version": "2.2.0", "defs": {},
           "pages": [{"mode": "page", "id": "p", "canvas": {"size": [200, 200]},
                      "layers": [{"id": "l", "objects": [obj]}]}]}
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "doc.fg.json")
        out = os.path.join(td, "out")
        with open(src, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        subprocess.run([sys.executable, RENDER, src, "--out", out, "--quiet"],
                       check=True, cwd=ROOT)
        return _read_first_svg(out)


def _render_fixture(name):
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, RENDER, os.path.join(ROOT, "fixtures", name),
                        "--out", out, "--quiet"], check=True, cwd=ROOT)
        return _read_first_svg(out)


def test_shadow_bool_emits_drop_shadow_filter():
    svg = _render_obj({**_RECT, "shadow": True})
    assert '<filter id="fx1"' in svg and 'filter="url(#fx1)"' in svg
    assert "feOffset" in svg and "feGaussianBlur" in svg


def test_glow_bool_emits_filter_without_offset():
    svg = _render_obj({**_RECT, "glow": True})
    assert '<filter id="fx1"' in svg and 'filter="url(#fx1)"' in svg
    assert "feOffset" not in svg                       # a glow is not offset


def test_shadow_effect_object_params_flow_through():
    svg = _render_obj({**_RECT, "shadow": {"color": "#ff0000", "blur": 6, "dy": 3, "opacity": 0.3}})
    assert 'flood-color="#ff0000"' in svg and 'flood-opacity="0.3"' in svg
    assert 'dy="3"' in svg


def test_no_effect_emits_no_filter():
    svg = _render_obj(dict(_RECT))
    assert "<filter" not in svg and "filter=" not in svg   # additive: untouched


def test_both_effects_nest_two_filters():
    svg = _render_obj({**_RECT, "shadow": "small", "glow": {"color": "#00ff00", "blur": 5}})
    assert svg.count("<filter ") == 2
    assert svg.count('<g filter="url(#fx') == 2           # glow inner, shadow outer


def test_css_string_box_shadow_renders_a_filter():
    """A CSS-string `box_shadow` must render, not vanish.

    Regression: `EffectResolver._box_shadow` skipped string items, so a
    model-valid `box_shadow: "<css>"` (ShadowVal = Union[str, Shadow]) validated
    but silently produced no shadow — a silent failure the project's honest-limits
    ethos forbids.
    """
    svg = _render_obj({**_RECT, "style": {"box_shadow": "0px 4px 12px rgba(0,0,0,0.35)"}})
    assert "<filter" in svg and 'filter="url(#fx1)"' in svg
    assert "feGaussianBlur" in svg and "feFlood" in svg
    assert 'flood-opacity="0.35"' in svg          # alpha lifted out of the rgba()
    assert "feOffset" in svg                       # offset_y = 4 from the string


def test_css_string_box_shadow_matches_the_dict_form():
    """The string and structured forms both produce a drop-shadow filter."""
    as_string = _render_obj({**_RECT, "style": {"box_shadow": "0 3px 6px #000000"}})
    as_dict = _render_obj(
        {**_RECT, "style": {"box_shadow": [{"offset_x": 0, "offset_y": 3, "blur": 6, "color": "#000000"}]}}
    )
    assert "feGaussianBlur" in as_string and "feGaussianBlur" in as_dict


def test_effects_fixture_is_the_oracle():
    """fixtures/effects.fg.yaml is the checked-in oracle — it flows through
    validate + overflow in `make check`; here we assert it renders the filters."""
    svg = _render_fixture("effects.fg.yaml")
    assert svg.count("<filter ") == 7                     # 4 shadow + 3 glow, deduped
    assert svg.count("feOffset") == 4                     # only the shadows are offset
    assert svg.count('<g filter="url(#fx') == 7           # one wrap per effect application
    assert "feFlood" in svg and "feComposite" in svg


# ---- Style.mask lowering (Image/Gradient values -> generated <mask> defs) ---- #
def test_gradient_mask_lowers_to_a_mask_def():
    """A Gradient mask value must generate a real `<mask>` def (luminance mask),
    not be silently ignored because it isn't a string."""
    svg = _render_obj({**_RECT, "style": {"mask": {
        "kind": "linear", "angle": 90,
        "stops": [{"color": "#ffffff", "position": "0%"},
                  {"color": "#000000", "position": "100%"}]}}})
    assert "<mask id=" in svg
    assert "mask:url(#" in svg                             # the wrapper references it
    assert "<linearGradient" in svg                        # gradient def backs the mask


def test_url_image_mask_lowers_to_a_mask_def():
    svg = _render_obj({**_RECT, "style": {"mask": {"url": "data:image/png;base64,AAAA"}}})
    assert "<mask id=" in svg
    assert "<image" in svg


def test_string_mask_keeps_passthrough():
    svg = _render_obj({**_RECT, "style": {"mask": "url(#hand-authored)"}})
    assert "mask:url(#hand-authored)" in svg
