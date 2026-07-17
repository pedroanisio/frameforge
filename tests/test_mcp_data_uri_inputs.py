#!/usr/bin/env python3
"""data: URI image ingestion — chat-pasted references without a filesystem stall (F5).

The vision tools accepted only filesystem paths and frameforge:// session URIs;
an agent holding a pasted reference had to excavate its own transcript to get a
file. A ``data:image/<type>;base64,`` URI is unambiguous (no collision with
paths), so the single input resolver accepts it everywhere at once.
"""
from __future__ import annotations

import base64
import io
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

PIL = pytest.importorskip("PIL.Image")

from frameforge.mcp.usecases import _resolve_image_arg, overlay_images  # noqa: E402


def _png_bytes(color, size=(16, 16)):
    buf = io.BytesIO()
    PIL.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _data_uri(raw, mime="image/png"):
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def test_resolver_accepts_png_data_uri():
    raw = _png_bytes((200, 30, 30))
    assert _resolve_image_arg(_data_uri(raw), session_root=None) == raw


def test_resolver_accepts_jpeg_data_uri():
    buf = io.BytesIO()
    PIL.new("RGB", (12, 12), (0, 128, 255)).save(buf, format="JPEG")
    raw = buf.getvalue()
    assert _resolve_image_arg(_data_uri(raw, "image/jpeg"), session_root=None) == raw


def test_resolver_rejects_non_image_or_unencoded_data_uri():
    with pytest.raises(ValueError):
        _resolve_image_arg("data:text/plain;base64,aGk=", session_root=None)
    with pytest.raises(ValueError):
        _resolve_image_arg("data:image/png,notbase64", session_root=None)
    with pytest.raises(ValueError):
        _resolve_image_arg("data:image/png;base64,@@not-base64@@", session_root=None)


def test_overlay_images_end_to_end_with_data_uris(tmp_path):
    base = _data_uri(_png_bytes((250, 250, 250)))
    over = _data_uri(_png_bytes((10, 10, 10)))
    out = overlay_images(
        base=base, overlay=over,
        landmarks=[{"base": [0, 0], "overlay": [0, 0]},
                   {"base": [16, 16], "overlay": [16, 16]}],
        session_id="datauri-test", session_root=str(tmp_path))
    assert out["ok"] is True
    assert out["spatial"]["alignment"]["scale"] == pytest.approx(1.0)
