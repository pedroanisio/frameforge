"""Vision context: propose FrameForge documents from images and documents.

The inverse of the renderer — instead of FrameForge → pixels, this proposes
FrameForge objects *from* pixels. Classical OpenCV/numpy detectors and an
optional VLM lane each implement one :class:`Detector` port; the proposer lowers
their observations into a draft document via the SDK authoring API.

⚠ PALS's LAW: every proposal is unverified CV/VLM output. Callers must run it
through the forward validate+render pipeline (the MCP ``propose_*`` tools do this
automatically) before trusting it.
"""
from __future__ import annotations

from .application import (
    DefaultObservationMapper,
    build_default_proposer,
    default_detectors,
    propose_from_document,
    propose_from_image,
)
from .domain import (
    Detector,
    DocumentSource,
    ImageSource,
    Observation,
    ObservationMapper,
    Proposal,
    Proposer,
    RasterImage,
    SkippedDetector,
    VlmClient,
)

__all__ = [
    # value objects
    "Observation",
    "RasterImage",
    "Proposal",
    "SkippedDetector",
    # ports
    "Detector",
    "ImageSource",
    "DocumentSource",
    "VlmClient",
    "ObservationMapper",
    # services / composition
    "Proposer",
    "DefaultObservationMapper",
    "default_detectors",
    "build_default_proposer",
    "propose_from_image",
    "propose_from_document",
]
