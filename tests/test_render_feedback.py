#!/usr/bin/env python3
"""
test_render_feedback.py — structured render feedback + the end of silent drops.

Covers the renderer's diagnostics surface:
* every flowable type the flow proxy drops is COUNTED by type
  (``diagnostics["skipped_flowables"]``) — never a silent pass,
* objects swallowed by the per-object safety net are recorded with type/id and
  the exception message (``diagnostics["skipped_objects"]``),
* ``font_report()`` surfaces requested->resolved font family pairs (fc-match),
  filling ``diagnostics["font_fallbacks"]`` with substituted families,
* the opt-in ``layout_report`` flag records per-object final boxes and fitted
  font sizes,
* ``FRAMEGRAPH_REAL_METRICS`` reaches the Renderer through every public entry
  point (default unchanged: estimate metrics),
* ``image`` and ``toc`` flowables now RENDER (with leader dots + computed page
  numbers for the toc) instead of dropping.

Renderer-only (no models import): evict a models-module shadow first — mirror of
the guard in test_element_render.py.
"""
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):  # a non-package (the models module)
    del sys.modules["framegraph"]
sys.path.insert(0, ROOT)

from tooling.render_fixtures import Renderer  # noqa: E402


def _flow_doc(story):
    return {"dsl": "FrameGraph", "version": "2.2.0",
            "pages": [{"mode": "flow", "id": "p", "canvas": {"size": [400, 300]},
                       "story": story}]}


def _page_doc(objects):
    return {"dsl": "FrameGraph", "version": "2.2.0",
            "pages": [{"mode": "page", "id": "p", "canvas": {"size": [300, 200]},
                       "layers": [{"id": "l", "objects": objects}]}]}


# ---- skipped flowables ------------------------------------------------------ #
def test_dropped_flowables_are_counted_by_type():
    doc = _flow_doc([{"type": "paragraph", "text": "kept"},
                     {"type": "bibliography", "entries": [{"id": "a"}]},
                     {"type": "bibliography", "entries": [{"id": "b"}]}])
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    assert r.diagnostics["skipped_flowables"] == {"bibliography": 2}


def test_supported_flowables_are_not_counted_as_skipped():
    doc = _flow_doc([{"type": "paragraph", "text": "kept"},
                     {"type": "heading", "level": 1, "text": "H"}])
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    assert r.diagnostics["skipped_flowables"] == {}


# ---- skipped objects -------------------------------------------------------- #
def test_swallowed_object_exception_is_recorded():
    # ellipse with a malformed center raises inside _obj; the safety net must
    # record WHAT died and WHY, not just bump a counter.
    doc = _page_doc([{"type": "ellipse", "id": "bad-e", "center": {"x": 1}, "rx": 5, "ry": 5}])
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    assert r.skipped == 1
    events = r.diagnostics["skipped_objects"]
    assert len(events) == 1
    assert events[0]["type"] == "ellipse"
    assert events[0]["id"] == "bad-e"
    assert events[0]["error"]


# ---- font resolution feedback ----------------------------------------------- #
def test_font_report_surfaces_substituted_families(monkeypatch):
    import framegraph.rendering.infrastructure.font_metrics as fm
    monkeypatch.setattr(fm, "resolve_family_name", lambda family: "DejaVu Sans")
    doc = _page_doc([{"type": "text", "box": [0, 0, 200, 20], "text": "hello",
                      "style": {"font_family": "Inter"}}])
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    report = r.font_report()
    inter = [e for e in report if e["requested"] == "Inter"]
    assert inter and inter[0]["resolved"] == "DejaVu Sans" and inter[0]["substituted"]
    assert any(e["requested"] == "Inter" for e in r.diagnostics["font_fallbacks"])


def test_font_report_ignores_generic_only_chains(monkeypatch):
    import framegraph.rendering.infrastructure.font_metrics as fm
    monkeypatch.setattr(fm, "resolve_family_name", lambda family: "DejaVu Sans")
    doc = _page_doc([{"type": "text", "box": [0, 0, 200, 20], "text": "hello"}])  # default "sans"
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    assert r.font_report() == []
    assert r.diagnostics["font_fallbacks"] == []


# ---- layout report (opt-in) -------------------------------------------------- #
def test_layout_report_records_boxes_and_fitted_sizes():
    doc = _page_doc([{"type": "text", "id": "t1", "box": [10, 10, 120, 40],
                      "text": "fitted", "style": {"size": 12}},
                     {"type": "rect", "id": "r1", "box": [0, 0, 50, 50], "fill": "#111"}])
    r = Renderer(doc, ".", layout_report=True)
    r.render_page(doc["pages"][0])
    by_id = {e.get("id"): e for e in r.diagnostics["layout"]}
    assert by_id["t1"]["box"] == [10, 10, 120, 40]
    assert by_id["t1"]["font_size"] == 12
    assert by_id["t1"]["lines"] >= 1
    assert by_id["r1"]["type"] == "rect" and by_id["r1"]["box"] == [0, 0, 50, 50]


def test_layout_report_is_off_by_default():
    doc = _page_doc([{"type": "text", "box": [10, 10, 120, 40], "text": "x"}])
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    assert r.diagnostics["layout"] == []


# ---- real_metrics reachability ----------------------------------------------- #
def test_real_metrics_defaults_off(monkeypatch):
    monkeypatch.delenv("FRAMEGRAPH_REAL_METRICS", raising=False)
    assert Renderer({}, ".").real_metrics is False


def test_real_metrics_env_opt_in(monkeypatch):
    monkeypatch.setenv("FRAMEGRAPH_REAL_METRICS", "1")
    assert Renderer({}, ".").real_metrics is True
    # an explicit False (e.g. the golden harness) always wins over the env
    assert Renderer({}, ".", real_metrics=False).real_metrics is False


# ---- unresolved string masks ---------------------------------------------------- #
def test_string_mask_with_unknown_ref_warns():
    doc = _page_doc([{"type": "rect", "box": [0, 0, 50, 50], "fill": "#111",
                      "style": {"mask": "url(#nothing-defines-this)"}}])
    r = Renderer(doc, ".")
    svg = r.render_page(doc["pages"][0])[0]
    assert "mask:url(#nothing-defines-this)" in svg     # pass-through preserved
    assert any(w["kind"] == "mask_unresolved_ref" for w in r.diagnostics["warnings"])


def test_generated_mask_reference_does_not_warn():
    doc = _page_doc([{"type": "rect", "box": [0, 0, 50, 50], "fill": "#111",
                      "style": {"mask": {"kind": "linear", "stops": [
                          {"color": "#fff", "position": "0%"},
                          {"color": "#000", "position": "100%"}]}}}])
    r = Renderer(doc, ".")
    svg = r.render_page(doc["pages"][0])[0]
    assert "<mask id=" in svg
    assert not any(w["kind"].startswith("mask") for w in r.diagnostics["warnings"])


# ---- image flow --------------------------------------------------------------- #
def test_image_flow_renders_and_is_not_dropped():
    doc = _flow_doc([{"type": "image", "src": "missing-file.png", "alt": "Chart",
                      "caption": "Fig. 1", "height": 60}])
    r = Renderer(doc, ".")
    svg = "".join(r.render_page(doc["pages"][0]))
    assert "skipped_flowables" in r.diagnostics and "image" not in r.diagnostics["skipped_flowables"]
    assert "Chart" in svg          # placeholder label for a missing file
    assert "Fig. 1" in svg         # caption emitted


# ---- toc flow ------------------------------------------------------------------ #
def test_toc_flow_renders_entries_with_page_numbers():
    filler = [{"type": "paragraph", "text": "lorem ipsum " * 30} for _ in range(12)]
    doc = _flow_doc([{"type": "toc", "title": "Contents"},
                     {"type": "heading", "level": 1, "text": "Alpha"},
                     *filler,
                     {"type": "heading", "level": 2, "text": "Beta"}])
    r = Renderer(doc, ".")
    svgs = r.render_page(doc["pages"][0])
    assert len(svgs) >= 2, "filler must paginate for the page-number assertion"
    first = svgs[0]
    assert "Contents" in first
    assert "Alpha" in first and "Beta" in first
    assert " . ." in first                      # leader dots
    assert 'text-anchor="end"' in first          # right-aligned page numbers
    assert "toc" not in r.diagnostics["skipped_flowables"]


def test_toc_levels_filter():
    doc = _flow_doc([{"type": "toc", "title": "Contents", "levels": [1]},
                     {"type": "heading", "level": 1, "text": "KeepMe"},
                     {"type": "heading", "level": 2, "text": "DropMe"}])
    r = Renderer(doc, ".")
    first = r.render_page(doc["pages"][0])[0]
    toc_region = first.split("KeepMe")[0] + "KeepMe"   # entries precede the body headings
    assert "KeepMe" in toc_region
    assert first.count("DropMe") == 1                  # heading body only, no toc entry


def test_toc_of_non_headings_warns_instead_of_silence():
    doc = _flow_doc([{"type": "toc", "of": "figures"},
                     {"type": "heading", "level": 1, "text": "H"}])
    r = Renderer(doc, ".")
    r.render_page(doc["pages"][0])
    assert r.diagnostics["skipped_flowables"].get("toc") == 1
    assert any(w["kind"] == "flow_toc_unsupported" for w in r.diagnostics["warnings"])


if __name__ == "__main__":
    test_dropped_flowables_are_counted_by_type()
    print("OK")
