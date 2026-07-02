"""Style `transform` — TransformFn list → SVG `<g transform>` wrapper.

Backs the reused transform renderer (`_with_transform` / `_svg_transform` in
tooling/render_fixtures.py) under the standing fixture rule: the feature is
demonstrated by a checked-in oracle, not only synthetic in-process dicts.
fixtures/transforms.fg.yaml is that oracle — a Y-axis-leaning gallery
(translate_y / scale_y / skew_y / rotate) that also pins the FrameGraph default
`transform_origin` (box centre) against an explicit corner origin and a
two-function composition.

Subprocess render (not an in-process import) to avoid the framegraph-package vs
models-module name clash in the shared pytest process — same shape as
tests/test_text_spans.py.
"""
import glob
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RENDER = os.path.join(ROOT, "tooling", "render_fixtures.py")


def _render_fixture(name):
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, RENDER, os.path.join(ROOT, "tests", "fixtures", name),
                        "--out", out, "--quiet"], check=True, cwd=ROOT)
        svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
        assert svgs, "renderer produced no SVG"
        with open(svgs[0], encoding="utf-8") as fh:
            return fh.read()


def test_y_axis_transforms_wrap_in_transform_groups():
    svg = _render_fixture("transforms.fg.yaml")
    # translate_y → a pure vertical translate (no origin bookkeeping needed)
    assert '<g transform="translate(0 22)">' in svg
    # scale_y / skew_y pivot about the box centre via the origin sandwich
    assert '<g transform="translate(201 91) scale(1 1.6) translate(-201 -91)">' in svg
    assert '<g transform="translate(325 91) skewY(18) translate(-325 -91)">' in svg


def test_rotate_default_origin_is_box_centre_vs_explicit_corner():
    svg = _render_fixture("transforms.fg.yaml")
    # default transform_origin: the [420,64,58,54] box centre → (449, 91)
    assert '<g transform="rotate(20 449 91)">' in svg
    # explicit transform_origin: [544, 64] (the box's top-left corner)
    assert '<g transform="rotate(20 544 64)">' in svg


def test_transform_list_composes_in_order():
    svg = _render_fixture("transforms.fg.yaml")
    # a translate_y then a rotate, emitted left-to-right in declaration order
    assert '<g transform="translate(0 14) rotate(16 697 91)">' in svg
