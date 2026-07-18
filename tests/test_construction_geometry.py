#!/usr/bin/env python3
"""Construction geometry + layer roles — CAD's non-printing datum layer.

Construction objects (own flag, or membership of a `role: construction`
layer) exist for authoring — snap targets, datums, guides — and stay out of
the rendered output unless the document opts in (`meta.show_construction`).
Layer roles also give annotation/dimension layers a declared semantic.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

from frameforge.sdk import DocumentBuilder, validate_static_rules  # noqa: E402
from frameforge.sdk.conform import render_page_svgs  # noqa: E402

MARK = "#0BA51E"          # construction marker colour, greppable in SVG
KEEP = "#AA1133"          # ordinary geometry that must always render


def _doc(show=None, layer_role=None):
    b = DocumentBuilder(title="constr", profile="diagram")
    pg = b.page("p1", canvas={"size": [300, 200], "units": "px"})
    pg.layer("main")
    pg.rect([0, 0, 300, 200], fill="#FFFFFF")
    pg.rect([20, 20, 60, 40], fill=KEEP)
    pg.line([0, 100], [300, 100], stroke=MARK, stroke_style={"stroke_width": 1},
            construction=True)
    if layer_role:
        pg.layer("datums", role=layer_role)
        pg.rect([200, 50, 40, 40], fill=MARK)
    doc = b.build_dict() if hasattr(b, "build_dict") else b.build()
    if isinstance(doc, dict) and show is not None:
        doc.setdefault("meta", {})["show_construction"] = show
    elif show is not None:
        d = doc.model_dump(exclude_none=True) if hasattr(doc, "model_dump") else doc
        d.setdefault("meta", {})["show_construction"] = show
        return d
    return doc


def test_construction_fields_validate():
    report = validate_static_rules(_doc())
    assert report.ok, [i.message for i in report.issues]


def test_construction_objects_hidden_by_default():
    svg = render_page_svgs(_doc())[0]
    assert KEEP in svg
    assert MARK not in svg


def test_construction_layer_role_hides_members():
    svg = render_page_svgs(_doc(layer_role="construction"))[0]
    assert MARK not in svg


def test_show_construction_opt_in_renders_them():
    svg = render_page_svgs(_doc(show=True))[0]
    assert MARK in svg


def test_annotation_role_is_accepted_and_renders():
    svg = render_page_svgs(_doc(layer_role="annotation"))[0]
    assert svg.count(MARK) >= 1      # non-construction roles paint normally


def test_unknown_role_is_rejected():
    doc = _doc()
    d = doc if isinstance(doc, dict) else doc.model_dump(exclude_none=True)
    page = d["pages"][0].get("page") or d["pages"][0]
    page["layers"][0]["role"] = "scaffolding"
    report = validate_static_rules(d)
    assert not report.ok
