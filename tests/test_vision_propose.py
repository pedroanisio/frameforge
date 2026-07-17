#!/usr/bin/env python3
"""Tests for the vision context: image/document -> draft FrameForge proposals.

The OpenCV/OCR adapters cannot run without their backends, so the orchestration
is exercised with injected fakes (the Dependency-Inversion payoff) and the one
backend present here (numpy, via ColorRegionDetector) gets a real end-to-end
check. Every proposal is round-tripped through the model so a bad object shape
fails loudly rather than silently.
"""
from __future__ import annotations

import base64
import io
import os
import sys

import pytest
import yaml

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.sdk.conform import render_page_svgs  # noqa: E402
from frameforge.sdk.io import parse  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402
from frameforge.vision import (  # noqa: E402
    Detector,
    Observation,
    Proposer,
    RasterImage,
)
from frameforge.vision.application.mapper import DefaultObservationMapper  # noqa: E402
from frameforge.vision.infrastructure.image_source import DefaultImageSource  # noqa: E402
from frameforge.vision.infrastructure.opencv_detectors import ColorRegionDetector  # noqa: E402
from frameforge.vision.infrastructure.vlm_detector import VlmDetector  # noqa: E402


class FakeDetector:
    """A Detector whose observations and availability are fixed for the test."""

    def __init__(self, name, observations, *, available=True, reason="unavailable"):
        self.name = name
        self._observations = list(observations)
        self._available = available
        self._reason = reason

    def available(self):
        return self._available

    def unavailable_reason(self):
        return self._reason

    def detect(self, image):
        return list(self._observations)


class FakeVlmClient:
    def __init__(self, response, *, available=True):
        self._response = response
        self._available = available

    def available(self):
        return self._available

    def unavailable_reason(self):
        return "fake vlm not configured"

    def infer(self, image, prompt):
        return self._response


def _objects(document):
    objects = []
    for page in document.get("pages", []):
        for layer in page.get("layers", []):
            objects.extend(layer.get("objects", []))
    return objects


def _png_bytes(width=200, height=140):
    from PIL import Image

    image = Image.new("RGB", (width, height), (32, 33, 36))
    for x in range(20, 100):
        for y in range(20, 60):
            image.putpixel((x, y), (92, 139, 214))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
def test_mapper_lowers_every_kind_to_a_model_valid_object():
    observations = [
        Observation("fill", bbox=(0, 0, 128, 96), color="#202124"),
        Observation("rect", bbox=(10, 10, 40, 20), color="#5C8BD6"),
        Observation("ellipse", bbox=(60, 10, 30, 30), color="#A7D7C5"),
        Observation("line", points=((0, 80), (120, 80)), stroke_color="#333333", stroke_width=2.0),
        Observation("polyline", points=((0, 0), (10, 10), (20, 5)), stroke_color="#333333"),
        Observation("path", points=((0, 0), (10, 10), (20, 0)), stroke_color="#333333", meta={"closed": True}),
        Observation("text", bbox=(5, 5, 40, 16), text="hi", color="#111111"),
    ]
    proposer = Proposer([FakeDetector("fake", observations)], DefaultObservationMapper())

    proposal = proposer.propose(RasterImage(width=128, height=96), title="mapper-test")

    assert len(proposal.observations) == 7
    assert len(_objects(proposal.document)) == 7
    # build_dict already validated structure; re-validate to be explicit.
    report = validate_static_rules(parse(yaml.safe_dump(dict(proposal.document)), forgiving=False))
    assert report.ok, [(i.severity, i.rule_id, i.message) for i in report.issues]
    svgs = render_page_svgs(parse(yaml.safe_dump(dict(proposal.document)), forgiving=False))
    assert svgs and all(tag in svgs[0] for tag in ("<rect", "<ellipse", "<line", "<text"))


def test_mapper_drops_degenerate_geometry():
    mapper = DefaultObservationMapper()
    assert mapper.to_object(Observation("rect", bbox=(0, 0, 0, 50)), 0) is None  # zero width
    assert mapper.to_object(Observation("text", bbox=(0, 0, 10, 10), text="  "), 0) is None  # blank text
    assert mapper.to_object(Observation("line", points=()), 0) is None  # no endpoints


def test_proposer_records_skipped_detectors_without_failing():
    ran = FakeDetector("ran", [Observation("rect", bbox=(0, 0, 10, 10), color="#fff")])
    skipped = FakeDetector("skip", [], available=False, reason="backend missing")

    proposal = Proposer([ran, skipped], DefaultObservationMapper()).propose(RasterImage(width=20, height=20))

    assert proposal.detectors_run == ("ran",)
    assert [(s.name, s.reason) for s in proposal.detectors_skipped] == [("skip", "backend missing")]
    assert len(_objects(proposal.document)) == 1


def test_detector_names_filter_selects_a_subset():
    a = FakeDetector("a", [Observation("rect", bbox=(0, 0, 10, 10), color="#fff")])
    b = FakeDetector("b", [Observation("rect", bbox=(0, 0, 10, 10), color="#000")])

    proposal = Proposer([a, b], DefaultObservationMapper()).propose(
        RasterImage(width=20, height=20), detector_names=["b"]
    )

    assert proposal.detectors_run == ("b",)


def test_color_region_detector_runs_on_real_pixels():
    image = DefaultImageSource().load(_png_bytes(), is_base64=False)
    detector = ColorRegionDetector()

    assert detector.available() is True
    observations = list(detector.detect(image))

    assert observations, "expected at least the background fill"
    background = observations[0]
    assert background.kind == "fill"
    # background bbox spans (most of) the canvas
    assert background.bbox is not None and background.bbox[2] >= image.width * 0.8


def test_vlm_lane_parses_model_json_into_observations():
    response = (
        'Sure! {"observations": ['
        '{"kind": "rect", "bbox": [10, 10, 40, 20], "color": "#5C8BD6", "confidence": 0.9},'
        '{"kind": "text", "bbox": [5, 5, 30, 12], "text": "hi"},'
        '{"kind": "bogus", "bbox": [0, 0, 1, 1]}]}'
    )
    detector = VlmDetector(FakeVlmClient(response))

    assert detector.available() is True
    observations = list(detector.detect(RasterImage(width=100, height=60, encoded=b"x")))

    kinds = [o.kind for o in observations]
    assert kinds == ["rect", "text"]  # the unknown kind is dropped
    assert observations[0].detector == "vlm"


def test_vlm_lane_tolerates_garbage_response():
    detector = VlmDetector(FakeVlmClient("not json at all"))
    assert list(detector.detect(RasterImage(width=10, height=10, encoded=b"x"))) == []


def test_concrete_detectors_satisfy_the_detector_port():
    # runtime_checkable Protocol: structural conformance (LSP at the boundary).
    assert isinstance(ColorRegionDetector(), Detector)
    assert isinstance(VlmDetector(FakeVlmClient("{}")), Detector)
    assert isinstance(FakeDetector("x", []), Detector)


# --------------------------------------------------------------------------- #
# MCP tool surface (forward verification of the inverse proposal)
# --------------------------------------------------------------------------- #
def test_mcp_propose_from_image_validates_and_renders(tmp_path):
    from frameforge.mcp.server import propose_from_image

    image_b64 = base64.b64encode(_png_bytes()).decode("ascii")
    result = propose_from_image(
        image_base64=image_b64, session_id="vision-1", session_root=tmp_path
    )

    assert result["ok"] is True
    assert result["validation"]["ok"] is True
    assert result["renders"], "the proposal should render at least one page"
    summary = result["proposal"]
    assert "color_region" in summary["detectors_run"]
    assert summary["object_count"] >= 1
    # unavailable backends are reported, not fatal; available optional OpenCV
    # detectors may run in environments that install the vision group.
    ran_names = set(summary["detectors_run"])
    skipped_names = {s["name"] for s in summary["detectors_skipped"]}
    assert {"shape", "line", "text", "vlm"} <= (ran_names | skipped_names)
    # `text` (pytesseract) runs wherever the vision group + tesseract binary
    # exist, so it may land on either side. Only the VLM lane is deterministic
    # here: it needs explicit FRAMEFORGE_VISION_VLM_* configuration.
    assert "vlm" in skipped_names


def test_mcp_propose_from_image_requires_an_image():
    from frameforge.mcp.server import propose_from_image

    with pytest.raises(ValueError, match="image_path or image_base64"):
        propose_from_image()


def test_mcp_propose_from_document_reports_missing_backend_gracefully(tmp_path, monkeypatch):
    from frameforge.vision.infrastructure.pdf_source import PdfDocumentSource
    from frameforge.mcp.server import propose_from_document

    monkeypatch.setattr(PdfDocumentSource, "available", lambda self: False)
    result = propose_from_document("/nonexistent.pdf", session_id="vision-doc", session_root=tmp_path)

    # A missing optional backend is a clean error, not an import traceback.
    assert result["ok"] is False
    assert "PyMuPDF" in result["error"]
