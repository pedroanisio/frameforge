"""Regression tests for tooling/pdf_to_frameforge_yml.py (the PDF -> FrameForge
transpiler).

Two layers:

  * Pure-helper / shape tests (no PyMuPDF): the token store, object scaffolding,
    semantic registration, and the assembled document are all fitz-free, so we
    drive them directly and assert the output is a canonical, model-valid
    FrameForge v2 document. These run everywhere (incl. CI, which has no
    PyMuPDF).

  * One end-to-end test gated on `fitz`: builds a tiny PDF in-memory, transpiles
    it, and validates the result. Skipped automatically when PyMuPDF is absent.

Guarded regressions:
  - emitted tokens are HEAD-canonical `Style` projections (no legacy/dup keys, no
    `meta` inside a Style) — Style is `extra="forbid"`, so a non-canonical token
    silently breaks validation.
  - the page text contract is `shrink_to_fit`, NOT `clip`: a re-rendering font is
    usually wider than the PDF's, so `clip` dropped the tail of every tight line
    (the reported rendering flaw). `shrink_to_fit` preserves all text.
  - whole-line/span text is carried verbatim into the object (no extraction-time
    truncation).

Like tests/test_head.py, the `frameforge` name resolves to the *models module*
(models/frameforge.py), not the rendering package — evicted + re-imported here so
both this module and the tool agree.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "tooling"))

# Evict any cached `frameforge` (a rendering-package import from another test) so
# this module — and the tool's internal `import frameforge as fg` — both bind the
# models module that lives on the models/ path inserted above.

import frameforge.model as fg  # noqa: E402
import pdf_to_frameforge_yml as tool  # noqa: E402

from pathlib import Path  # noqa: E402


def _converter(tmp_path, **opts_kw):
    opts = tool.ExtractionOptions(
        asset_dir=tmp_path / "assets",
        output_file=tmp_path / "out.fg.yaml",
        **opts_kw,
    )
    return tool.PDFToFrameForge(tmp_path / "sample.pdf", opts)


# --------------------------------------------------------------------------- #
#  Fakes — a minimal duck-typed PyMuPDF page so the fitz-free path is testable #
# --------------------------------------------------------------------------- #
class _FakeRect:
    def __init__(self, bbox):
        x0, y0, x1, y1 = bbox
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.width, self.height = x1 - x0, y1 - y0

    @property
    def is_empty(self):
        return self.width <= 0 or self.height <= 0


class _FakeFitz:
    TEXTFLAGS_DICT = 0

    @staticmethod
    def Rect(bbox):
        return bbox if isinstance(bbox, _FakeRect) else _FakeRect(bbox)


class _FakePageRect:
    width, height = 612, 792


class _FakePage:
    """One text block with three spans (incl. a mono chip), plus a non-text
    block that must be skipped. No drawings/images."""

    rect = _FakePageRect()
    rotation = 0
    mediabox = [0, 0, 612, 792]
    cropbox = [0, 0, 612, 792]

    LINE = [78, 72, 504, 85]

    def get_text(self, kind, flags=0):
        return {"blocks": [
            {"type": 1, "bbox": [0, 0, 10, 10]},  # image block -> skipped
            {"type": 0, "bbox": self.LINE, "lines": [
                {"bbox": self.LINE, "spans": [
                    {"text": "System ", "bbox": [78, 72, 120, 85],
                     "font": "Helvetica", "size": 11, "color": 0, "flags": 0},
                    {"text": "S", "bbox": [120, 72, 133, 85],
                     "font": "Courier", "size": 11, "color": 0, "flags": 0},
                    {"text": " is reducible", "bbox": [133, 72, 504, 85],
                     "font": "Helvetica-Bold", "size": 11, "color": 0, "flags": 0},
                ]},
            ]},
        ]}

    def get_drawings(self):
        return []

    def get_image_info(self, xrefs=False):
        return []


class _FakeTableRow:
    def __init__(self, cells):
        self.cells = cells


class _FakeTable:
    bbox = [0, 0, 150, 40]

    def __init__(self):
        # Real PyMuPDF exposes row geometry through rows[*].cells. The flat
        # cells list is not safe for idx % ncol because its ordering can differ.
        self.rows = [
            _FakeTableRow([[0, 0, 40, 20], [40, 0, 150, 20]]),
            _FakeTableRow([[0, 20, 40, 40], [40, 20, 150, 40]]),
        ]
        self.cells = [
            [0, 0, 40, 20],
            [0, 20, 40, 40],
            [40, 0, 150, 20],
            [40, 20, 150, 40],
        ]

    def extract(self):
        return [["Name", "Description"], ["A", "Wide cell"]]


def _fake_page_doc(tmp_path, **opts_kw):
    conv = _converter(tmp_path, **opts_kw)
    conv.fitz = _FakeFitz()
    conv.add_sem_node("doc", "document", "sample.pdf", pages=1)
    page = conv._page(_FakePage(), 0)
    return conv, page


# --------------------------------------------------------------------------- #
#  Scalar helpers                                                              #
# --------------------------------------------------------------------------- #
def test_rgb_hex_helpers():
    assert tool.int_rgb_to_hex(0x112233) == "#112233"
    assert tool.int_rgb_to_hex(None, "#abcdef") == "#abcdef"
    assert tool.float_rgb_to_hex((1.0, 0.0, 0.0)) == "#FF0000"
    assert tool.float_rgb_to_hex(0x00FF00) == "#00FF00"   # int passthrough
    assert tool.float_rgb_to_hex(None, "#000000") == "#000000"
    assert tool.float_rgb_to_hex((2.0, -1.0, 0.5)) == "#FF007F"  # clamped


def test_safe_text_strips_nul_and_newlines():
    assert tool.safe_text("a\u0000b\n") == "ab"
    assert tool.safe_text("\nkeep spaces\n") == "keep spaces"  # spaces untouched


def test_slug_and_font_classes():
    assert tool.slug("Page 1!") == "page_1"
    assert tool.slug("") == "item"
    assert tool.family_class("CourierNew") == "mono"
    assert tool.family_class("Times-Roman") == "serif"
    assert tool.family_class("Helvetica") == "sans"
    assert tool.is_bold_font("Arial-Black") and tool.is_italic_font("Arial-Oblique")


# --------------------------------------------------------------------------- #
#  TokenStore — canonical Style projections (validate against the model)       #
# --------------------------------------------------------------------------- #
def test_text_style_is_canonical_and_model_valid():
    ts = tool.TokenStore()
    key = ts.add_text_style(font="Helvetica-BoldOblique", size=12.0, color="#112233")
    style = ts.text_styles[key]
    assert set(style) == {"font_family", "font_size", "font_weight", "font_style",
                          "color", "text_align", "line_height"}
    # no legacy/duplicate sugar keys, and crucially no `meta` (Style forbids extra)
    for forbidden in ("meta", "font", "size", "weight", "align"):
        assert forbidden not in style
    assert style["font_weight"] == 700          # "Bold" detected
    assert style["font_style"] == "italic"      # "Oblique" detected
    fg.Style.model_validate(style)              # the source of truth accepts it


def test_text_style_dedupes_and_records_provenance():
    ts = tool.TokenStore()
    a = ts.add_text_style(font="Helvetica", size=10.0, color="#000000")
    b = ts.add_text_style(font="Arial", size=10.0, color="#000000")  # same class/size/etc
    assert a == b                                # deduped to one token
    assert sorted(ts.font_provenance[a]) == ["Arial", "Helvetica"]


def test_stroke_style_is_canonical_single_form():
    ts = tool.TokenStore()
    key = ts.add_stroke_style(color="#FF0000", width=2.0, opacity=0.5)
    style = ts.stroke_styles[key]
    assert set(style) == {"stroke", "stroke_width", "opacity"}
    assert "color" not in style and "width" not in style  # no legacy bundle keys
    fg.Style.model_validate(style)


def test_default_text_style_is_valid():
    ts = tool.TokenStore()
    assert ts.default_text_style() == "ts_default"
    fg.Style.model_validate(ts.text_styles["ts_default"])


# --------------------------------------------------------------------------- #
#  Object scaffolding + semantic registration (the de-duplicated helpers)      #
# --------------------------------------------------------------------------- #
def test_new_object_scaffold(tmp_path):
    conv = _converter(tmp_path)
    obj = conv._new_object("oid1", "rect", {"k": "v"}, box=[0, 0, 1, 1])
    assert obj == {"type": "rect", "id": "oid1", "box": [0, 0, 1, 1],
                   "bind": "oid1", "meta": {"k": "v"}}


def test_register_adds_node_and_derived_edge(tmp_path):
    conv = _converter(tmp_path)
    conv._register("page_1", "page_1_text_0", "text", "hi", pdf_block_index=0)
    assert conv.semantic_nodes[-1] == {"id": "page_1_text_0", "type": "text",
                                       "label": "hi", "meta": {"pdf_block_index": 0}}
    assert conv.semantic_edges[-1] == {"id": "page_1_page_1_text_0_derived",
                                       "type": "derived_from", "from": "page_1",
                                       "to": "page_1_text_0"}


def test_fill_ref_and_apply_paint(tmp_path):
    conv = _converter(tmp_path)
    assert conv._fill_ref(None) == "none"
    ref = conv._fill_ref("#00FF00")
    assert conv.tokens.colors[ref] == "#00FF00"

    obj = {"type": "rect"}
    conv._apply_paint(obj, None, None)
    assert obj["fill"] == "none" and "stroke_style" not in obj
    obj2 = {"type": "rect"}
    conv._apply_paint(obj2, "#00FF00", "stroke_x")
    assert obj2["fill"] == ref and obj2["stroke_style"] == "stroke_x"


def test_unique_id_disambiguates(tmp_path):
    conv = _converter(tmp_path)
    assert conv.unique_id("Box") == "box"
    assert conv.unique_id("Box") == "box_2"
    assert conv.unique_id("Box") == "box_3"


# --------------------------------------------------------------------------- #
#  Text extraction modes (the unified _text_units driver)                      #
# --------------------------------------------------------------------------- #
def test_lines_mode_joins_spans_into_one_object(tmp_path):
    _, page = _fake_page_doc(tmp_path, text_mode="lines")
    texts = [o for L in page["layers"] if L["id"] == "text" for o in L["objects"]]
    assert len(texts) == 1
    assert texts[0]["text"] == "System S is reducible"   # full line, nothing dropped
    assert texts[0]["meta"]["extract_mode"] == "line"


def test_spans_mode_emits_one_object_per_span(tmp_path):
    _, page = _fake_page_doc(tmp_path, text_mode="spans")
    texts = [o for L in page["layers"] if L["id"] == "text" for o in L["objects"]]
    # one object per span, intra-line spaces preserved verbatim (faithful layout;
    # safe_text strips only NUL/newlines, not spaces)
    assert [t["text"] for t in texts] == ["System ", "S", " is reducible"]
    assert all(t["meta"]["extract_mode"] == "span" for t in texts)


# --------------------------------------------------------------------------- #
#  THE flaw guard: text-fit contract + whole document validity                 #
# --------------------------------------------------------------------------- #
def test_page_uses_shrink_to_fit_not_clip(tmp_path):
    """A re-rendering font runs wider than the PDF's, so a `clip` contract
    silently dropped the tail of every tight line. The fix is shrink_to_fit."""
    _, page = _fake_page_doc(tmp_path)
    assert page["rendering"]["text"]["overflow"] == "shrink_to_fit"
    assert page["rendering"]["text"]["overflow"] != "clip"
    assert page["rendering"]["text"]["min_font_size"] == 3


def test_assembled_document_is_model_valid(tmp_path):
    conv, page = _fake_page_doc(tmp_path)
    doc = conv._assemble([page], [612.0, 792.0])
    fg.Document.model_validate(doc)             # validates against the source of truth
    assert doc["version"] == fg.HEAD_VERSION
    assert doc["dsl"] == "FrameForge"
    assert doc["pages"][0]["rendering"]["text"]["overflow"] == "shrink_to_fit"
    # provenance surfaced in document meta (kept out of the Style tokens)
    assert doc["meta"]["pdf_fonts"]


def test_background_layer_toggle(tmp_path):
    _, with_bg = _fake_page_doc(tmp_path, include_background=True)
    _, without = _fake_page_doc(tmp_path, include_background=False)
    assert any(L["id"] == "background" for L in with_bg["layers"])
    assert not any(L["id"] == "background" for L in without["layers"])


def test_table_column_widths_use_row_geometry(tmp_path):
    conv = _converter(tmp_path)
    conv.fitz = _FakeFitz()

    assert conv._column_widths(_FakeTable(), 2) == [40, 110]


# --------------------------------------------------------------------------- #
#  End-to-end with real PyMuPDF (skipped where it isn't installed, e.g. CI)    #
# --------------------------------------------------------------------------- #
def test_end_to_end_real_pdf(tmp_path):
    fitz = pytest.importorskip("fitz", reason="PyMuPDF not installed")
    pdf = fitz.open()
    page = pdf.new_page(width=612, height=792)
    # Keep the line within the page width: insert_text clips off-page glyphs at
    # creation time, which would truncate the PDF text layer itself.
    line = "System S is reducible relative to language L when decomposition is sufficient"
    page.insert_text((72, 72), line, fontsize=11)
    pdf_path = tmp_path / "sample.pdf"
    pdf.save(str(pdf_path))
    pdf.close()

    opts = tool.ExtractionOptions(asset_dir=tmp_path / "assets",
                                  output_file=tmp_path / "out.fg.yaml")
    doc = tool.PDFToFrameForge(pdf_path, opts).transpile()

    fg.Document.model_validate(doc)
    assert doc["version"] == fg.HEAD_VERSION
    page0 = doc["pages"][0]
    assert page0["rendering"]["text"]["overflow"] == "shrink_to_fit"
    text = " ".join(o["text"] for L in page0["layers"]
                     for o in (L.get("objects") or []) if o.get("type") == "text")
    # the trailing words that `clip` used to drop must be present in the data
    assert "reducible" in text and "sufficient" in text
