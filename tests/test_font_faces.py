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
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RENDER = os.path.join(ROOT, "tooling", "render_fixtures.py")
RENDER_LATEX = os.path.join(ROOT, "tooling", "render_latex.py")


def _fixture_path(name):
    root_path = os.path.join(ROOT, "fixtures", name)
    if os.path.exists(root_path):
        return root_path
    return os.path.join(ROOT, "examples", "fixtures", name)


def _render_fixture(name):
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, RENDER, _fixture_path(name), "--out", out, "--quiet"],
                       check=True, cwd=ROOT)
        svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
        assert svgs, "renderer produced no SVG"
        with open(svgs[0], encoding="utf-8") as fh:
            return fh.read()


def _render_all_pages(name):
    """Every page's SVG concatenated, for flow docs that paginate."""
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, RENDER, _fixture_path(name), "--out", out, "--quiet"],
                       check=True, cwd=ROOT)
        svgs = sorted(glob.glob(os.path.join(out, "**", "p*.svg"), recursive=True))
        assert svgs, "renderer produced no SVG"
        return "\n".join(open(p, encoding="utf-8").read() for p in svgs)


def _transpile_latex(name):
    """Transpile a fixture to LaTeX source via the CLI (subprocess: same
    name-clash dodge as the SVG path)."""
    with tempfile.TemporaryDirectory() as out:
        subprocess.run([sys.executable, RENDER_LATEX, _fixture_path(name), "--out", out, "--tex-only", "--quiet"],
                       check=True, cwd=ROOT)
        tex = glob.glob(os.path.join(out, "*.tex"))
        assert tex, "transpiler produced no .tex"
        with open(tex[0], encoding="utf-8") as fh:
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


# --- the multi-face capacity proof: support >= 100 font faces --------------- #
# font-faces-100.fg.yaml declares 100 distinct faces in defs.tokens.fonts and
# renders one paragraph per face. These two tests are the regression gate that
# both render paths carry an arbitrary number of faces with no cap/truncation.

def test_hundred_faces_render_distinct_font_families_svg():
    svg = _render_all_pages("font-faces-100.fg.yaml")
    families = set(re.findall(r"font-family:([^;\"]+)", svg))
    # 100 declared faces each emit their own font-family (plus the page-number's
    # generic sans), so the SVG proxy carries >= 100 distinct families.
    assert len(families) >= 100, f"only {len(families)} distinct font-family in SVG"


def test_hundred_faces_map_to_distinct_latex_font_families():
    tex = _transpile_latex("font-faces-100.fg.yaml")
    # one guarded \newfontfamily per declared face: no cap, no collision.
    assert tex.count(r"\newfontfamily") == 100
    assert tex.count(r"\IfFontExistsTF") == 100
    # each face is actually *selected* by its paragraph, not just declared.
    selections = set(re.findall(r"\\fgff[a-z]+\\fontsize", tex))
    assert len(selections) >= 100, f"only {len(selections)} faces selected in LaTeX"
    # the declaration degrades gracefully on hosts missing a face (still compiles).
    assert r"{\newcommand\fgffa{}}" in tex
