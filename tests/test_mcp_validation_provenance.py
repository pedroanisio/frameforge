#!/usr/bin/env python3
"""Author-site provenance and grouped MCP validation feedback (GitHub #77)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "docs")]

from frameforge_mcp.guide import FRAMEFORGE_GUIDE  # noqa: E402
from frameforge_mcp.usecases import run_sdk_client  # noqa: E402
from frameforge_sdk import DocumentBuilder  # noqa: E402
from frameforge_sdk.io import serialize  # noqa: E402
from frameforge_sdk.paint import linear_gradient  # noqa: E402


def _valid_builder(*, capture_provenance: bool) -> DocumentBuilder:
    builder = DocumentBuilder(
        title="Provenance parity",
        profile="diagram",
        capture_provenance=capture_provenance,
    )
    layer = builder.page(
        "p1",
        canvas={"size": [160, 90], "units": "px"},
        coordinate_mode="absolute",
    ).layer("main")
    layer.rect(
        [10, 10, 80, 40],
        fill=linear_gradient([("#111111", 0), ("#eeeeee", 1)], angle=90),
    )
    return builder


def test_provenance_is_sidecar_only_and_can_be_disabled():
    enabled = _valid_builder(capture_provenance=True)
    disabled = _valid_builder(capture_provenance=False)

    assert enabled.provenance_map()
    assert disabled.provenance_map() == {}
    assert serialize(enabled.build(), format="json") == serialize(disabled.build(), format="json")
    assert "provenance" not in serialize(enabled.build(), format="json")


def test_run_sdk_client_groups_gradient_union_noise_at_author_site(tmp_path):
    examples = tmp_path / "static" / "examples"
    examples.mkdir(parents=True)
    client = examples / "gradient_error.py"
    client.write_text(
        """\
from frameforge_sdk import DocumentBuilder, linear_gradient

def broken_gradient():
    return linear_gradient([
        {"color": "#111111", "position": 0},
        {"color": "#eeeeee", "position": 1},
    ], angle=90)

def hero(page):
    for index in range(12):
        page.rect([index * 10, 10, 8, 30], fill=broken_gradient())

doc = DocumentBuilder(title="Broken gradient", profile="diagram")
layer = doc.page(
    "p1",
    canvas={"size": [160, 90], "units": "px"},
    coordinate_mode="absolute",
).layer("main")
hero(layer)
""",
        encoding="utf-8",
    )

    result = run_sdk_client(
        "static/examples/gradient_error.py",
        session_id="provenance",
        session_root=tmp_path / "sessions",
        repo_root=tmp_path,
        raster_png=False,
    )

    assert result["ok"] is False
    assert result["issues_total"] > len(result["validation"]["issues"])
    assert result["groups_total"] == 1
    assert len(result["error_groups"]) == 1
    group = result["error_groups"][0]
    assert group["count"] == result["issues_total"]
    assert "gradient_error.py:11 in hero()" in group["site"]
    assert "via sdk.paint.linear_gradient" in group["site"]
    assert "/fill/Gradient/stops/" in group["sample_path"]
    assert "gradient stop color is not a string" in group["message"]
    assert "(color, position) tuples or bare colors" in group["hint"]


def test_guide_explains_grouped_author_site_validation_feedback():
    assert "error_groups" in FRAMEFORGE_GUIDE
    assert "issues_total" in FRAMEFORGE_GUIDE
    assert "authoring file, line, and function" in FRAMEFORGE_GUIDE
