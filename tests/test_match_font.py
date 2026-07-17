#!/usr/bin/env python3
"""match_font — evidence-based typeface choice for reconstruction (recon gap F6a).

Choosing a stand-in face from priors is guesswork; this ranks the runtime's
resolvable families by shape similarity against a reference crop. Ground truth
here: a sample rendered in a known family must out-rank other families of the
same library when matched against itself.
"""
from __future__ import annotations

import base64
import io
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path[:0] = [ROOT, os.path.join(ROOT, "src")]

PIL = pytest.importorskip("PIL.Image")
from PIL import ImageDraw, ImageFont  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("fc-match") is None,
                                reason="fontconfig unavailable")

SAMPLE = "ORCHIES 197"


def _font_file(family):
    out = subprocess.run(["fc-match", "-f", "%{file}\\n%{family}", family],
                         capture_output=True, text=True)
    file, resolved = (out.stdout.split("\n") + [""])[:2]
    if not file or family.lower() not in resolved.lower():
        pytest.skip(f"{family} not resolvable in this environment")
    return file


def _reference_data_uri(family, size=64):
    font = ImageFont.truetype(_font_file(family), size)
    img = PIL.new("L", (size * len(SAMPLE), size * 2), 255)
    ImageDraw.Draw(img).text((20, 20), SAMPLE, font=font, fill=0)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_self_family_wins_the_ranking(tmp_path):
    from frameforge.mcp.usecases import match_font
    ref = _reference_data_uri("DejaVu Sans")
    out = match_font(
        reference=ref, text=SAMPLE,
        candidates=["DejaVu Serif", "DejaVu Sans", "DejaVu Sans Mono"],
        session_id="fm", session_root=str(tmp_path))
    assert out["ok"] is True
    ranking = out["ranking"]
    assert ranking[0]["family"] == "DejaVu Sans"
    scores = [r["score"] for r in ranking]
    assert scores == sorted(scores, reverse=True)
    assert all(set(r) >= {"family", "score", "ncc", "aspect_delta"} for r in ranking)


def test_serif_reference_prefers_serif(tmp_path):
    from frameforge.mcp.usecases import match_font
    ref = _reference_data_uri("DejaVu Serif")
    out = match_font(
        reference=ref, text=SAMPLE,
        candidates=["DejaVu Sans", "DejaVu Serif"],
        session_id="fm2", session_root=str(tmp_path))
    assert out["ok"] is True
    assert out["ranking"][0]["family"] == "DejaVu Serif"


def test_no_resolvable_candidates_is_structured(tmp_path):
    from frameforge.mcp.usecases import match_font
    ref = _reference_data_uri("DejaVu Sans")
    out = match_font(reference=ref, text=SAMPLE,
                     candidates=["No Such Face 9000"],
                     session_id="fm3", session_root=str(tmp_path))
    assert out["ok"] is False
    assert "resolv" in out["error"]


def test_server_registers_match_font(tmp_path):
    from frameforge.mcp.server import create_server

    class _Fake:
        def __init__(self, name, **kw):
            self.tools, self.resources, self.prompts = {}, {}, {}

        def tool(self, **_kw):
            def dec(fn):
                self.tools[fn.__name__] = fn
                return fn
            return dec

        def resource(self, uri, **_kw):
            def dec(fn):
                self.resources[uri] = fn
                return fn
            return dec

        def prompt(self, **_kw):
            def dec(fn):
                self.prompts[fn.__name__] = fn
                return fn
            return dec

    server = create_server(session_root=tmp_path, fastmcp_cls=_Fake)
    assert "match_font" in server.tools
