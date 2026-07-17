"""Design-audit service: token census off the SVG + generic model walk.

The audit must (a) count every distinct visual token from the emitted SVG,
(b) surface features generically from the model (so new node types need no new
code — the drift-proof property), and (c) flag design-system sprawl.
"""
from frameforge.rendering.application.audit import (
    audit_document, render_markdown, summary_line)

# A tiny two-element SVG page: one Inter heading, one serif body line, plus a
# stroked rect — enough to exercise every extractor.
_SVG = [
    '<svg xmlns="http://www.w3.org/2000/svg">'
    '<text style="font-family:Inter;font-size:20px;font-weight:700;fill:#111827">H</text>'
    '<text style="font-family:serif;font-size:10px;fill:#374151">body</text>'
    '<rect x="0" y="0" width="9" height="9" fill="#6B7B47" '
    'stroke="#E5E7EB" stroke-width="1"/>'
    '<rect x="0" y="0" width="9" height="9" fill="#F9FAFB"/>'
    '</svg>'
]
_DOC = {
    "pages": [
        {"mode": "flow", "id": "s", "master": "m", "story": [
            {"type": "heading", "level": 1, "text": "H"},
            {"type": "paragraph", "text": "body"},
            {"type": "table", "rows": [["a"]]},
        ]},
    ],
    "defs": {"masters": {"m": {"regions": [{"id": "r", "columns": 2}]}},
             "tokens": {"colors": {"x": "#111827"}, "styles": {"body": {}}}},
}


def test_svg_token_census_counts_distinct_values():
    r = audit_document(_DOC, _SVG)["svg"]
    assert r["font_family"]["n_distinct"] == 2          # Inter + serif
    assert set(r["font_size_px"]["distinct"]) == {"20", "10"}
    assert r["font_weight"]["distinct"] == ["700"]
    assert "#111827" in r["text_color"]["distinct"]
    assert "#6B7B47" in r["shape_fill"]["distinct"]
    assert "#E5E7EB" in r["stroke_color"]["distinct"]


def test_model_walk_is_generic_over_types():
    m = audit_document(_DOC, _SVG)["model"]
    # object/flow types come from `type` discriminators — no hardcoded list, so a
    # new node type would appear here automatically (the anti-drift guarantee)
    assert set(m["object_and_flow_types"]) == {"heading", "paragraph", "table"}
    assert m["structural"]["flow_sections"] == 1
    assert m["structural"]["multicolumn_regions"] is True
    assert m["structural"]["colors_defined"] == 1


def test_health_flags_sprawl_and_mixed_weights():
    # 9 distinct sizes (> budget 6) + a keyword/number weight clash
    svg = ['<svg>' + "".join(
        f'<text style="font-size:{s}px;font-weight:{w};fill:#111">x</text>'
        for s, w in zip(range(10, 19), ["bold", "700"] + ["400"] * 7)) + '</svg>']
    codes = {f["code"] for f in audit_document({"pages": []}, svg)["health"]}
    assert "type-scale-sprawl" in codes
    assert "mixed-weight-encoding" in codes


def test_clean_document_passes_and_renders():
    report = audit_document(_DOC, _SVG)
    assert [f for f in report["health"] if f["level"] == "warn"] == []  # no sprawl
    assert isinstance(summary_line(report), str)
    md = render_markdown(report, title="t")
    assert "Design audit" in md and "Visual tokens" in md
