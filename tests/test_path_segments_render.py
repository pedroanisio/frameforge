"""G-1 (render half): a structured ``d`` renders identically to its string form.

The structured segment list is the authored source; the SVG path-data string is
its compiled view. The renderer must treat the two as the same geometry, so a
path authored with typed segments produces byte-identical output to the same path
authored as a ``d`` string. Uses the tooling ``Renderer`` (no model-package
shadowing) the way the accessibility render tests do.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
# Prefer the repo root so the `framegraph` *package* outranks `models/` on sys.path,
# and evict a models-*module* shadow (no __path__) left by a model-only test in the
# shared pytest process, so `framegraph.rendering` resolves to the package. The
# opposite direction of the eviction in test_elements.py / test_head.py.
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
sys.path.insert(0, os.path.join(ROOT, "tooling"))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # models module shadowing the package
    del sys.modules["framegraph"]

from render_fixtures import Renderer  # noqa: E402


def _doc(d):
    return {
        "dsl": "FrameGraph",
        "version": "2.2.0",
        "pages": [{
            "mode": "page",
            "id": "p1",
            "canvas": {"size": [100, 100]},
            "layers": [{"id": "main", "objects": [{"type": "path", "d": d}]}],
        }],
    }


def test_structured_and_string_d_render_identically():
    string_d = "M 0 0 L 10 0 L 10 10 Z"
    seg_d = [["M", 0, 0], ["L", 10, 0], ["L", 10, 10], ["Z"]]

    def render(d):
        return Renderer(_doc(d), ".").render_page(_doc(d)["pages"][0])

    assert render(seg_d) == render(string_d)
