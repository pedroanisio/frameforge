"""G-1 SDK exposure: the SDK can author the structured path-segment form.

The G-1 structured-segment contract (`Path.d = Union[str, list[PathSeg]]`) landed
in the core; per ADR 0002 the SDK trailed. These tests pin that the SDK `Path`
builder now exposes it: `segments()` returns typed `[cmd, *coords]` lists, the
SDK validator accepts a path authored from them, `object(structured=True)` emits
them, and the default `object()` stays the byte-identical `d` string (so golden
output is unaffected).

Package-only (imports `framegraph.sdk`, never the models module) so the
`framegraph` package is not shadowed — validation goes through the SDK's own
`validate_document`, which reaches the models internally.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from framegraph.sdk import HEAD_VERSION, validate_document  # noqa: E402
from framegraph.sdk.geometry import Path  # noqa: E402


def _built_path():
    return (
        Path()
        .move_to(0, 0)
        .line_to(10, 0)
        .cubic_to((10, 5), (5, 10), (0, 10))
        .quad_to((0, 5), (5, 5))
        .arc_to(3, 3, 0, False, True, (8, 8))
        .close()
    )


def test_segments_returns_typed_command_lists():
    segs = _built_path().segments()
    cmds = [s[0] for s in segs]
    assert cmds == ["M", "L", "C", "Q", "A", "Z"]
    # arity per command
    assert len(segs[0]) == 3 and len(segs[2]) == 7 and len(segs[4]) == 8 and len(segs[5]) == 1
    # coordinates are numbers, not strings
    assert all(isinstance(v, (int, float)) for s in segs for v in s[1:])
    # arc flags lowered to 0/1
    assert segs[4][4] in (0, 1) and segs[4][5] in (0, 1)


def test_default_object_emits_d_string_unchanged():
    """Default emission stays the `d` string — byte-identical, golden-safe."""
    obj = _built_path().object()
    assert isinstance(obj["d"], str)
    assert obj["d"].startswith("M 0 0 L 10 0")


def test_structured_object_emits_segment_list():
    obj = _built_path().object(structured=True)
    assert isinstance(obj["d"], list)
    assert obj["d"] == _built_path().segments()


def test_structured_object_validates_through_the_sdk():
    """A path authored with structured segments validates as a real Document."""
    obj = _built_path().object(structured=True)
    doc = {
        "dsl": "FrameGraph",
        "version": HEAD_VERSION,
        "pages": [{
            "mode": "page", "id": "p1", "canvas": {"size": [100, 100]},
            "layers": [{"id": "main", "objects": [obj]}],
        }],
    }
    validate_document(doc)  # raises on invalid
