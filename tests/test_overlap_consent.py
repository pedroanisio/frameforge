"""`overlap: allowed` — the consent field for intentional same-layer overlap.

Design of record: ``docs/decisions/collision-gate/collision-gate-decision.md``
(rev 2). A *collision* is an UNINTENDED same-layer overlap. Overlap itself is a
first-class effect — a watermark over a paragraph, a caption over an image,
double-exposure display type. The system never judges aesthetics; it flags only
overlaps that were not stacked on purpose.

This is P0: the model needs a place to record that consent, so the render-time
detector (O1) can tell an accident from an effect. Default is false — silence is
not consent — and the flag is read by the collision detector, never by the
renderer's geometry (it changes nothing about how the object draws).
"""

from __future__ import annotations

import sys

_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

import frameforge.model as fg  # noqa: E402


def _rect(**extra):
    return {"type": "rect", "box": [0, 0, 10, 10], **extra}


def test_overlap_allowed_is_accepted_on_an_object():
    obj = fg.Rect.model_validate(_rect(overlap="allowed"))
    assert obj.overlap == "allowed"


def test_overlap_defaults_to_none_meaning_not_consented():
    obj = fg.Rect.model_validate(_rect())
    assert obj.overlap is None, "absence of the field must mean 'no consent'"


def test_overlap_only_accepts_the_allowed_literal():
    import pydantic
    for bad in ("yes", "true", "ok", True, 1):
        try:
            fg.Rect.model_validate(_rect(overlap=bad))
        except pydantic.ValidationError:
            continue
        raise AssertionError(f"overlap accepted an invalid value: {bad!r}")


def test_overlap_is_available_on_text_and_group_too():
    """Consent is a property of any placed object, not just rects."""
    t = fg.Text.model_validate(
        {"type": "text", "box": [0, 0, 10, 10], "text": "x", "overlap": "allowed"})
    assert t.overlap == "allowed"
    g = fg.Group.model_validate(
        {"type": "group", "box": [0, 0, 10, 10], "children": [], "overlap": "allowed"})
    assert g.overlap == "allowed"


def test_overlap_field_is_in_the_generated_schema():
    schema = fg.Document.model_json_schema()
    # every object $def that carries `decorative` must also carry `overlap`
    carriers = [name for name, d in schema.get("$defs", {}).items()
                if isinstance(d, dict) and "decorative" in (d.get("properties") or {})]
    assert carriers, "expected objects with a decorative property"
    for name in carriers:
        props = schema["$defs"][name]["properties"]
        assert "overlap" in props, f"{name} has decorative but not overlap"


def test_sdk_builder_passes_overlap_through():
    """The authoring surface: any object accepts `overlap` and it survives build."""
    from frameforge.sdk import DocumentBuilder
    b = DocumentBuilder(title="t", profile="diagram")
    page = b.page("p", canvas={"size": [100, 100], "units": "px"},
                  coordinate_mode="absolute")
    page.rect([0, 0, 50, 50], fill="#123456", overlap="allowed")
    page.text([0, 0, 50, 20], "watermark", overlap="allowed")
    doc = b.build_dict()
    objs = doc["pages"][0]["layers"][0]["objects"]
    assert all(o.get("overlap") == "allowed" for o in objs)
    # and it validates
    fg.Document.model_validate(doc)


def test_collision_detector_reads_the_authored_consent_end_to_end():
    """SDK-authored consent must actually suppress the render-time collision."""
    from frameforge.sdk import DocumentBuilder, collision_report
    b = DocumentBuilder(title="t", profile="diagram")
    page = b.page("p", canvas={"size": [400, 200], "units": "px"},
                  coordinate_mode="absolute")
    big = {"font_family": ["DejaVu Sans", "sans-serif"], "font_size": 20}
    page.text([10, 40, 380, 30], "WIDE WATERMARK TEXT", style=big, overlap="allowed")
    page.text([200, 40, 190, 30], "OVER THE TOP LABEL", style=big, overlap="allowed")
    assert collision_report(b.build_dict()) == [], "authored consent must suppress"
