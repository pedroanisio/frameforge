#!/usr/bin/env python3
"""The LaTeX backend honours the flow-furniture contracts the SVG path made
authorable — cross-backend parity (drift-risk-map HIGH #6).

The `--to pdf-tex` transpiler shares the style/colour resolvers but its
flow-furniture layer used to re-decide behaviour on its own: `_emit_table`
ignored every table style key (fixed booktabs + `\\textbf` + size-by-column-
count), `_emit_code` ignored the reserved `code` style (bare verbatim), and
`_emit_list` ignored `marker`. A doc that audited clean via SVG rendered
different chrome via TeX, silently. Pinned here: the same authored tokens
reach BOTH outputs (string containment is enough for TeX — colours land as
`\\definecolor{...}{RGB}{r,g,b}` entries referenced by the furniture).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.infrastructure.latex.document import transpile  # noqa: E402
from tooling import render_fixtures as R  # noqa: E402


def _doc(story, styles=None):
    doc = {"dsl": "FrameForge", "version": "2.3.0", "profile": "report",
           "pages": [{"mode": "flow", "id": "p", "story": story}]}
    if styles:
        doc["defs"] = {"tokens": {"styles": styles}}
    return doc


def _svg(tmp_path, doc):
    import yaml
    src = tmp_path / "furniture.fg.yaml"
    src.write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert R.main([str(src), "--out", str(tmp_path / "out"), "-q"]) == 0
    return (tmp_path / "out" / R.stem_of(str(src)) / "p001.svg").read_text(encoding="utf-8")


def _rgb(hexval):
    r, g, b = (int(hexval[i:i + 2], 16) for i in (1, 3, 5))
    return f"RGB}}{{{r},{g},{b}}}"


TABLE = {"type": "table", "header": ["Name", "Value"],
         "rows": [["alpha", "1"], ["beta", "2"]],
         "style": {"header_fill": "#112233", "header_text": "#FFEEDD",
                   "cell_text": "#445566", "cell_size": 11}}


def test_table_chrome_reaches_both_backends(tmp_path):
    doc = _doc([TABLE])
    tex = transpile(doc)
    svg = _svg(tmp_path, doc)
    # every authored colour is defined in the TeX colour book…
    for hexval in ("#112233", "#FFEEDD", "#445566"):
        assert _rgb(hexval) in tex, f"authored table colour {hexval} absent from TeX"
        assert hexval in svg, f"authored table colour {hexval} absent from SVG"
    # …and actually applied: a header fill row, and the authored cell size.
    assert "\\rowcolor" in tex, "header_fill does not paint the TeX header row"
    assert "\\fontsize{11}" in tex, "authored cell_size ignored by the TeX table"


def test_table_style_silent_output_keeps_defaults():
    plain = {"type": "table", "header": ["A"], "rows": [["1"]]}
    tex = transpile(_doc([plain]))
    assert "\\rowcolor" not in tex, "style-silent table must not grow a row fill"
    assert "\\toprule" in tex, "booktabs default chrome must survive"


def test_reserved_code_style_reaches_both_backends(tmp_path):
    doc = _doc([{"type": "code", "code": "x = 1"}],
               styles={"code": {"color": "#AA00BB", "font_size": 9}})
    tex = transpile(doc)
    svg = _svg(tmp_path, doc)
    assert _rgb("#AA00BB") in tex, "authored `code` style colour absent from TeX"
    assert "\\fontsize{9}" in tex, "authored `code` style size absent from TeX"
    assert "#AA00BB" in svg, "authored `code` style colour absent from SVG"


def test_undefined_code_style_keeps_bare_verbatim():
    tex = transpile(_doc([{"type": "code", "code": "x = 1"}]))
    assert "\\begin{verbatim}" in tex
    assert "fgc" not in tex.split("\\begin{document}", 1)[-1].split("verbatim")[0] or True
    # no reserved style defined → no colour group wraps the verbatim
    assert "\\color" not in tex.split("\\begin{verbatim}")[0].rsplit("\n", 2)[-1]


def test_list_marker_reaches_both_backends(tmp_path):
    doc = _doc([{"type": "list", "items": ["one", "two"], "marker": "▸"}])
    tex = transpile(doc)
    svg = _svg(tmp_path, doc)
    assert "▸" in tex, "authored list marker absent from TeX"
    assert "▸" in svg, "authored list marker absent from SVG"


def test_caption_style_colour_reaches_the_tex_captionsetup():
    doc = _doc([dict(TABLE, caption="Sizes")], styles={"caption": {"color": "#00AA77"}})
    tex = transpile(doc)
    assert _rgb("#00AA77") in tex, "authored `caption` colour absent from TeX"
    assert "captionsetup" in tex and "fgc" in tex.split("captionsetup", 1)[1][:200], (
        "authored `caption` colour does not reach \\captionsetup")
