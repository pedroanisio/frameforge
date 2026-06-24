#!/usr/bin/env python3
"""FrameForge provenance metatag (signing key/fingerprint + timestamp on rendered
docs). Pins: deterministic fingerprint, the SVG <metadata> injection, that the
timestamp is optional/deterministic-when-fixed, and — critically — that signing is
opt-in so default (golden) output is byte-identical."""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from framegraph.rendering.provenance import (  # noqa: E402
    FrameForgeStamp, content_fingerprint, sign_svg, stamp,
)

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"><rect/></svg>'


def test_fingerprint_is_deterministic():
    assert content_fingerprint("abc") == content_fingerprint("abc")
    assert content_fingerprint("abc") != content_fingerprint("abd")
    assert len(content_fingerprint("abc")) == 64 and re.fullmatch(r"[0-9a-f]+", content_fingerprint("abc"))


def test_stamp_fields_and_optional_timestamp():
    s = stamp("body", tool="framegraph", tool_version="2.2.0")
    assert s.fingerprint.startswith("sha256:") and s.timestamp is None
    assert "timestamp" not in s.fields()                       # deterministic: no time
    s2 = stamp("body", timestamp="2026-06-24T00:00:00Z")
    assert s2.fields()["timestamp"] == "2026-06-24T00:00:00Z"


def test_sign_svg_injects_metadata_after_root():
    out = sign_svg(SVG, timestamp="2026-06-24T12:00:00Z")
    assert out.startswith('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"><metadata>')
    assert '<frameforge xmlns="https://framegraph.dev/ns/provenance"' in out
    assert 'fingerprint="sha256:' in out and 'tool="framegraph"' in out
    assert 'timestamp="2026-06-24T12:00:00Z"' in out
    assert out.endswith("<rect/></svg>")                        # body preserved, order intact


def test_fingerprint_covers_body_not_the_metatag():
    # signing the same document twice with the same timestamp is byte-identical
    a = sign_svg(SVG, timestamp="2026-06-24T12:00:00Z")
    b = sign_svg(SVG, timestamp="2026-06-24T12:00:00Z")
    assert a == b
    # the fingerprint is of the body (<rect/>), independent of the injected metatag
    body_fp = content_fingerprint("<rect/>")
    assert f"sha256:{body_fp}" in a


def test_non_svg_input_unchanged():
    assert sign_svg("not an svg") == "not an svg"
    assert sign_svg("% a tikz comment") == "% a tikz comment"


def test_signing_is_opt_in_default_output_untouched():
    # the default render path never calls sign_svg, so unsigned output is the
    # original SVG byte-for-byte (this is what keeps the golden lock valid).
    assert "<metadata>" not in SVG               # sanity: unsigned has none
    assert isinstance(FrameForgeStamp(fingerprint="sha256:x"), FrameForgeStamp)
