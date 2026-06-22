"""Font faces, families & OpenType features — the advanced text surface.

Backs the reused text-style renderer's advanced-typography path under the
standing fixture rule. fixtures/font-faces.fg.yaml declares four @font-face
faces across three families (a variable Inter roman + its italic companion, a
variable Source Serif 4, a static JetBrains Mono) and drives the OpenType
controls the renderer maps to CSS. Each row is one `text` whose muted label run
+ feature run render as per-run styled `<tspan>`s, so each feature lands on its
own run rather than a flattened single style.

Feature/variation settings carry literal double quotes; the painter escapes them
to `&quot;` so the SVG `style="…"` attribute stays well-formed — the assertions
match that escaped form.

Subprocess render (not an in-process import) to dodge the framegraph-package vs
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
        subprocess.run([sys.executable, RENDER, os.path.join(ROOT, "fixtures", name),
                        "--out", out, "--quiet"], check=True, cwd=ROOT)
        svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
        assert svgs, "renderer produced no SVG"
        with open(svgs[0], encoding="utf-8") as fh:
            return fh.read()


def test_multiple_families_render_distinct_font_family():
    svg = _render_fixture("font-faces.fg.yaml")
    assert "font-family:Inter" in svg
    assert "font-family:Source Serif 4" in svg
    assert "font-family:JetBrains Mono" in svg


def test_weight_axis_and_slant_select_distinct_faces():
    svg = _render_fixture("font-faces.fg.yaml")
    # the Inter weight axis: Thin / Semibold / Bold / Black instances (400 stays implicit)
    for weight in ("200", "600", "800", "900"):
        assert f"font-weight:{weight}" in svg
    # the italic companion face is selected by font-style
    assert "font-style:italic" in svg


def test_advanced_opentype_features_emit_css():
    svg = _render_fixture("font-faces.fg.yaml")
    assert "font-variant-caps:small-caps" in svg
    assert "font-variant-numeric:tabular-nums" in svg
    assert "font-variant-numeric:oldstyle-nums" in svg
    assert "font-stretch:condensed" in svg
    assert "font-stretch:expanded" in svg
    assert "letter-spacing:4px" in svg
    # feature / variation settings keep their tag-quotes, escaped for the attribute
    assert "font-feature-settings:&quot;dlig&quot; 1, &quot;liga&quot; 1, &quot;calt&quot; 1" in svg
    assert "font-feature-settings:&quot;ss01&quot; 1" in svg
    assert "font-variation-settings:&quot;wght&quot; 350, &quot;slnt&quot; -6, &quot;opsz&quot; 28" in svg


def test_features_render_per_run_not_flattened():
    svg = _render_fixture("font-faces.fg.yaml")
    # 17 text objects, but the multi-span rows expand to many styled <tspan>s —
    # proof the per-run feature styles survive (a flattened line would be 1 tspan each)
    assert svg.count("<tspan") >= 30
