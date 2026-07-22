#!/usr/bin/env python3
"""Variable-font axes REACH THE PIXELS in the Chromium raster lane.

The defect (found typesetting the Warrant proposal, 2026-07-22): the renderer
emits ``font-variation-settings`` into its SVG correctly, but headless
Chromium ignores the property (and ``font-stretch``) for fonts served through
fontconfig — the variable axis dies silently between the vector and the
raster. Probed, not assumed: three ``wdth`` 62/100/125 lines rendered
byte-identical.

The engine fix pinned here: the raster lane detects families used with
``font-variation-settings``, resolves each through fontconfig, and — when the
file carries an ``fvar`` table — embeds it as an ``@font-face`` data: URI in
the HTML wrapper. A document-defined face takes precedence over the system
lookup, and Chromium applies variations to web fonts. Documents without
variation settings produce byte-identical HTML (no resolver calls, no drift).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge.rendering.infrastructure import browser as B  # noqa: E402

SVG_VAR = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="120" viewBox="0 0 600 120">'
    '<text x="10" y="50" style="font-family:\'FGVarProbe\';font-size:36px;'
    "font-variation-settings:&#x27;wdth&#x27; 62\">probe</text>"
    "</svg>"
)
SVG_PLAIN = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="120" viewBox="0 0 600 120">'
    '<text x="10" y="50" style="font-family:\'FGVarProbe\';font-size:36px">probe</text>'
    "</svg>"
)


# --- unit: family detection + fvar gating --------------------------------- #
def _fake_resolver(mapping):
    def resolve(family):
        return mapping.get(family)
    return resolve


def test_detects_families_used_with_variation_settings(tmp_path, monkeypatch):
    var_font = tmp_path / "var.ttf"
    var_font.write_bytes(b"\x00\x01\x00\x00 junk fvar junk")
    monkeypatch.setattr(B, "_resolve_family_file",
                        _fake_resolver({"FGVarProbe": var_font}))
    faces = B._variable_font_faces(SVG_VAR)
    assert [f[0] for f in faces] == ["FGVarProbe"]
    assert faces[0][1] == var_font


def test_non_variable_file_is_not_embedded(tmp_path, monkeypatch):
    static_font = tmp_path / "static.ttf"
    static_font.write_bytes(b"\x00\x01\x00\x00 no variations here")
    monkeypatch.setattr(B, "_resolve_family_file",
                        _fake_resolver({"FGVarProbe": static_font}))
    assert B._variable_font_faces(SVG_VAR) == []


def test_no_variation_settings_means_no_resolution_at_all(monkeypatch):
    def explode(_family):
        raise AssertionError("resolver must not run for plain documents")
    monkeypatch.setattr(B, "_resolve_family_file", explode)
    assert B._variable_font_faces(SVG_PLAIN) == []


def test_html_embeds_face_for_variable_family(tmp_path, monkeypatch):
    var_font = tmp_path / "var.ttf"
    var_font.write_bytes(b"\x00\x01\x00\x00 fvar payload")
    monkeypatch.setattr(B, "_resolve_family_file",
                        _fake_resolver({"FGVarProbe": var_font}))
    html = B._html(SVG_VAR, base_dir=None)
    assert "@font-face" in html
    assert "FGVarProbe" in html
    assert "data:font/ttf;base64," in html


def test_html_is_byte_identical_without_variation_settings(monkeypatch):
    def explode(_family):
        raise AssertionError("resolver must not run for plain documents")
    monkeypatch.setattr(B, "_resolve_family_file", explode)
    html = B._html(SVG_PLAIN, base_dir=None)
    assert "@font-face" not in html


def test_unresolvable_family_degrades_to_no_injection(monkeypatch):
    monkeypatch.setattr(B, "_resolve_family_file", _fake_resolver({}))
    assert B._variable_font_faces(SVG_VAR) == []
    assert "@font-face" not in B._html(SVG_VAR, base_dir=None)


# --- integration: the axis is visible in the pixels ------------------------ #
def _chromium_available():
    try:
        B._load_playwright()
    except Exception:
        return False
    return True


def _variable_wdth_family():
    """A real installed family with a wdth axis, via fontconfig; None if absent."""
    if not shutil.which("fc-match"):
        return None
    for fam in ("Archivo", "Roboto Flex", "Noto Sans"):
        try:
            out = subprocess.run(["fc-match", "--format", "%{file}", fam],
                                 capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return None
        if out and os.path.exists(out) and fam.lower() in os.path.basename(out).lower():
            with open(out, "rb") as fh:
                if b"fvar" in fh.read():
                    return fam
    return None


@pytest.mark.skipif(not _chromium_available(),
                    reason="headless Chromium unavailable — variable-font raster NOT verified")
def test_wdth_axis_changes_rendered_ink_width(tmp_path):
    fam = _variable_wdth_family()
    if fam is None:
        pytest.skip("no installed variable font with a wdth axis — cannot probe the raster lane")

    def svg(wdth):
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="120" '
                'viewBox="0 0 900 120"><rect width="900" height="120" fill="#fff"/>'
                f'<text x="10" y="70" style="font-family:\'{fam}\';font-size:48px;'
                f"font-variation-settings:&#x27;wdth&#x27; {wdth}\">HHHHHHHHHH</text></svg>")

    def ink_width(png_path):
        import struct
        import zlib
        data = open(png_path, "rb").read()
        # minimal PNG scanline walk (browser group has no Pillow): find IHDR+IDAT
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        pos, w, h, ct, idat = 8, 0, 0, 6, b""
        while pos < len(data):
            ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
            body = data[pos + 8:pos + 8 + ln]
            if typ == b"IHDR":
                w, h, _bd, ct = struct.unpack(">IIBB", body[:10])
                assert ct in (2, 6), f"expected RGB/RGBA, got colour type {ct}"
            elif typ == b"IDAT":
                idat += body
            pos += 12 + ln
        raw = zlib.decompress(idat)
        bpp = 4 if ct == 6 else 3
        stride = w * bpp + 1
        # unfilter enough: chromium screenshots typically use filter 0/... — be
        # safe and unfilter fully (sub/up/avg/paeth)
        prev = bytearray(w * bpp)
        min_x, max_x = w, -1
        for row in range(h):
            line = bytearray(raw[row * stride + 1:(row + 1) * stride])
            f = raw[row * stride]
            for i in range(len(line)):
                a = line[i - bpp] if i >= bpp else 0
                b_ = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                if f == 1:
                    line[i] = (line[i] + a) & 0xFF
                elif f == 2:
                    line[i] = (line[i] + b_) & 0xFF
                elif f == 3:
                    line[i] = (line[i] + (a + b_) // 2) & 0xFF
                elif f == 4:
                    p = a + b_ - c
                    pa, pb, pc = abs(p - a), abs(p - b_), abs(p - c)
                    pr = a if (pa <= pb and pa <= pc) else (b_ if pb <= pc else c)
                    line[i] = (line[i] + pr) & 0xFF
            prev = line
            for x in range(w):
                if line[x * bpp] < 128:          # dark ink pixel
                    min_x, max_x = min(min_x, x), max(max_x, x)
        return max(0, max_x - min_x)

    w62 = ink_width(B.rasterize_svg(svg(62), tmp_path / "w62.png"))
    w125 = ink_width(B.rasterize_svg(svg(125), tmp_path / "w125.png"))
    assert w62 > 0 and w125 > 0, "probe text did not render"
    assert w125 > w62 * 1.15, (
        f"wdth 125 ink ({w125}px) is not wider than wdth 62 ink ({w62}px) — "
        "the variable axis is not reaching the raster")
