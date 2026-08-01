"""`conform.render_html` — the HTML target reachable from the SDK, not just the CLI.

Every other output the project ships has an in-process SDK entry point
(`render_page_svgs`, `page_hashes`, `overflow_report`…). HTML had none: it was
reachable only through `ff-render --to html`, so an agent or application building
a document in memory had to write it to disk and shell out to get HTML. That is
the gap this closes, and these gates hold the surface to the same contract as its
siblings — a validated model in, a string out, `real_metrics` threaded the same
way.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]


def _doc():
    from frameforge_sdk import DocumentBuilder
    b = DocumentBuilder(title="SDK HTML")
    page = b.page("p1", canvas={"size": [400, 300], "units": "px"})
    page.rect([10, 10, 100, 50], id="r", fill="#3366cc")
    page.text([10, 80, 300, 24], "hello", id="t")
    return b.build()


def test_render_html_is_exported_from_the_engine_not_the_sdk():
    """`render_html` lives in `frameforge.conform`, deliberately.

    The 2026-08-01 split put COMPOSITION in `frameforge-sdk` (a leaf over the
    contract) and VERIFICATION in the engine, because rendering needs real
    pixels. `render_html` renders, so it stayed. Asserting the old home would
    quietly pull the whole engine back into the SDK's dependency set — the exact
    coupling the split removed.
    """
    from frameforge import conform
    assert hasattr(conform, "render_html")
    assert "render_html" in conform.__all__

    import frameforge_sdk as sdk
    assert not hasattr(sdk, "render_html"), (
        "render_html reappeared on the SDK — the leaf now depends on a renderer")


def test_render_html_returns_a_whole_document():
    from frameforge.conform import render_html
    out = render_html(_doc())
    assert isinstance(out, str)
    assert out.startswith("<!DOCTYPE html>")
    assert "</html>" in out
    assert "<title>SDK HTML</title>" in out


def test_render_html_paints_the_documents_objects():
    from frameforge.conform import render_html
    out = render_html(_doc())
    assert 'id="r"' in out and 'id="t"' in out
    assert 'fill="#3366cc"' in out
    assert "hello" in out


def test_render_html_accepts_a_plain_dict_too():
    """Parity with `render_pages_with_stats`, which validates whatever it is given."""
    from frameforge.conform import render_html
    out = render_html(_doc().model_dump(by_alias=True, exclude_none=True))
    assert out.startswith("<!DOCTYPE html>")


def test_render_html_rejects_an_invalid_document():
    """A validated entry point must not silently render nonsense."""
    from frameforge.conform import render_html
    with pytest.raises(Exception):
        render_html({"not": "a document"})


def test_render_html_threads_real_metrics_like_its_siblings():
    from frameforge.conform import render_html
    estimate = render_html(_doc(), real_metrics=False)
    assert estimate.startswith("<!DOCTYPE html>")
    # An explicit False must win over the environment, so the output is stable
    # regardless of FRAMEFORGE_REAL_METRICS — the property the golden lock needs.
    assert render_html(_doc(), real_metrics=False) == estimate


def test_render_html_is_deterministic():
    from frameforge.conform import render_html
    assert render_html(_doc()) == render_html(_doc())


def test_render_html_matches_the_cli_backend():
    """One implementation: the SDK entry point must not become a third renderer."""
    from frameforge.rendering.infrastructure.backends import get_backend
    from frameforge.conform import render_html
    from frameforge.conform import validate_document

    model = _doc()
    data = validate_document(model).model_dump(by_alias=True, exclude_none=True)
    assert render_html(model) == get_backend("html").render(data).pages[0]
