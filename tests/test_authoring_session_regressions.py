"""End-to-end regressions from the 2.6.0 long-form authoring session.

The tests deliberately cover the public boundary for every reported failure:
SDK metrics and fit diagnostics, deep geometric validation, whitespace and dash
model semantics, the tabular heuristic, and the MCP authoring surface.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import frameforge_sdk as sdk
from frameforge import conform
from frameforge.model import Style
from frameforge.rendering.application.renderer import Renderer
from frameforge.rendering.domain.services.overflow import OverflowSignal
from frameforge.rendering.infrastructure import font_metrics as fmmod
from frameforge.conform import render_pages_with_stats
from frameforge_sdk.validate import validate_static_rules
import validate as tooling_validate


def _page_doc(objects: list[dict], *, size: tuple[int, int] = (200, 160)) -> dict:
    return {
        "dsl": "FrameForge",
        "version": "2.6.0",
        "title": "regression",
        "pages": [{
            "mode": "page",
            "id": "p1",
            "canvas": {"size": list(size), "units": "px"},
            "layers": [{"id": "main", "objects": objects}],
        }],
    }


def _tooling_findings(tmp_path: Path, doc: dict, **kwargs):
    path = tmp_path / "probe.fg.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return tooling_validate.validate_doc(str(path), **kwargs)[1]


# Metric source alignment + fit-width API -------------------------------------


def test_sdk_measurement_defaults_to_the_renderers_deterministic_estimate(monkeypatch):
    """Optional fontTools must not silently change only the author-time result."""
    monkeypatch.setattr(
        fmmod,
        "measure_text",
        lambda *_a, **_k: pytest.fail("default measurement unexpectedly used real metrics"),
    )

    measured = sdk.measure_text(
        "token", font_family=["Inter", "sans-serif"], font_size=13
    )
    renderer = Renderer({}, ".", real_metrics=False)

    assert measured == renderer.measure("token", 13, 0.52)


def test_real_metric_measurement_and_breaker_resolve_the_same_full_font_stack(monkeypatch):
    seen: list[str] = []

    class SyntheticMetrics:
        def width(self, text: str, size: float) -> float:
            return len(text) * size * 0.61

    metrics = SyntheticMetrics()

    def resolve(family: str, _bold: bool):
        seen.append(family)
        return metrics

    monkeypatch.setattr(fmmod, "get_font_metrics", resolve)
    monkeypatch.setattr(
        fmmod,
        "measure_text",
        lambda text, family, size, bold: resolve(family, bold).width(text, size),
    )

    family = ["Missing Primary", "Carlito", "sans-serif"]
    measured = sdk.measure_text(
        "unbroken", font_family=family, font_size=13, real_metrics=True
    )
    width = sdk.fit_width(
        "unbroken", font_family=family, font_size=13, real_metrics=True
    )
    doc = _page_doc([{
        "id": "word",
        "type": "text",
        "box": [10, 10, width, 20],
        "text": "unbroken",
        "style": {"font_family": family, "font_size": 13},
    }])

    assert width >= measured
    assert conform.overflow_report(doc, real_metrics=True) == []
    assert seen and set(seen) == {"Missing Primary, Carlito, sans-serif"}


# Deep containment + explicit bleed intent -----------------------------------


def test_containment_recurses_through_parent_local_group_coordinates(tmp_path):
    doc = _page_doc([{
        "type": "group",
        "box": [50, 20, 100, 100],
        "children": [{"type": "rect", "box": [120, 0, 60, 20]}],
    }])

    findings = _tooling_findings(tmp_path, doc, text_fit=False)

    deep = [f for f in findings if f.code == "containment"]
    assert len(deep) == 1
    assert deep[0].path.endswith("objects[0].children[0]")


def test_decorative_no_longer_disables_containment(tmp_path):
    doc = _page_doc([
        {"type": "rect", "box": [0, 0, 250, 20], "decorative": True},
    ])

    assert "containment" in {
        f.code for f in _tooling_findings(tmp_path, doc, text_fit=False)
    }


def test_explicit_containment_consent_exempts_an_intentional_bleed(tmp_path):
    doc = _page_doc([{
        "type": "rect",
        "box": [-20, 0, 240, 20],
        "decorative": True,
        "containment": "allowed",
    }])

    assert "containment" not in {
        f.code for f in _tooling_findings(tmp_path, doc, text_fit=False)
    }
    # The same field must be admitted by the authoritative model.
    assert sdk.validate_document(doc).pages[0].layers[0].objects[0].containment == "allowed"


def test_pagebuilder_bleed_stamps_accessibility_and_geometry_intent():
    builder = sdk.DocumentBuilder(title="bleed", profile="diagram")
    layer = builder.page(
        "p", canvas={"size": [100, 100], "units": "px"}
    ).layer("main")
    with layer.bleed():
        layer.rect([-10, 0, 120, 20], fill="#000")

    obj = builder.build_dict()["pages"][0]["layers"][0]["objects"][0]
    assert obj["decorative"] is True
    assert obj["containment"] == "allowed"


# Text fit is a default validation capability --------------------------------


def _truncated_doc() -> dict:
    return _page_doc([{
        "id": "loss",
        "type": "text",
        "box": [10, 10, 35, 12],
        "text": "content that cannot fit",
        "style": {"font_size": 14},
    }])


def test_sdk_validation_reports_text_loss_by_default_and_can_be_disabled():
    default = validate_static_rules(_truncated_doc(), real_metrics=False)
    structural_only = validate_static_rules(
        _truncated_doc(), text_fit=False, real_metrics=False
    )

    assert "text-truncated" in {issue.rule_id for issue in default.issues}
    assert "text-truncated" not in {issue.rule_id for issue in structural_only.issues}


def test_cli_validator_runs_text_fit_by_default_and_has_an_explicit_opt_out(tmp_path):
    default = _tooling_findings(tmp_path, _truncated_doc())
    opted_out = _tooling_findings(tmp_path, _truncated_doc(), text_fit=False)

    assert "text-truncated" in {finding.code for finding in default}
    assert "text-truncated" not in {finding.code for finding in opted_out}


# Authored whitespace survives layout ----------------------------------------


@pytest.mark.parametrize("mode", ["pre", "pre-wrap", "break-spaces"])
def test_svg_preserves_repeated_spaces_for_preserving_white_space_modes(mode):
    doc = _page_doc([{
        "type": "text",
        "box": [10, 10, 220, 30],
        "text": "Advanced   SQL   Implementing",
        "style": {"font_size": 12, "white_space": mode},
    }], size=(260, 100))

    svgs, _stats = render_pages_with_stats(doc, real_metrics=False)

    assert "Advanced   SQL   Implementing" in svgs[0]
    assert f"white-space:{mode}" in svgs[0]


def test_pre_line_preserves_newlines_but_collapses_repeated_spaces():
    doc = _page_doc([{
        "type": "text",
        "box": [10, 10, 180, 60],
        "text": "A  B\nC",
        "style": {"font_size": 12, "white_space": "pre-line"},
    }], size=(240, 100))

    svgs, _stats = render_pages_with_stats(doc, real_metrics=False)

    assert "A B" in svgs[0]
    assert "A  B" not in svgs[0]
    assert ">C</tspan>" in svgs[0]


# SVG-compatible dash authoring ----------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("4 4", [4.0, 4.0]),
        ("4, 4", [4.0, 4.0]),
        ("4px, 2pt", ["4px", "2pt"]),
    ],
)
def test_stroke_dasharray_accepts_and_normalizes_svg_strings(value, expected):
    style = Style(stroke_dasharray=value).model_dump(exclude_none=True)
    assert style["stroke_dasharray"] == expected


def test_dash_shorthand_normalizes_to_the_canonical_field():
    style = Style(dash="3 2").model_dump(exclude_none=True)
    assert style == {"stroke_dasharray": [3.0, 2.0]}


def test_sdk_stroke_helper_accepts_the_svg_string_form_end_to_end():
    doc = _page_doc([{
        "type": "line",
        "from": [10, 10],
        "to": [100, 10],
        **sdk.stroke(1, color="#000", dash="4 4"),
    }])

    dumped = sdk.validate_document(doc).model_dump(exclude_none=True)
    style = dumped["pages"][0]["layers"][0]["objects"][0]["stroke_style"]
    assert style["stroke_dasharray"] == [4.0, 4.0]


@pytest.mark.parametrize("value", ["", "4,,2", "four two"])
def test_invalid_dash_strings_are_rejected(value):
    with pytest.raises(ValueError):
        Style(stroke_dasharray=value)


# Sparse incidental alignment is not a table ---------------------------------


def _text_at(x: int, y: int, *, role: str | None = None) -> dict:
    obj = {"type": "text", "box": [x, y, 80, 20], "text": "x"}
    if role:
        obj["meta"] = {"role": role}
    return obj


def test_sparse_seven_of_nine_incidental_alignment_is_not_tabular(tmp_path):
    objects = [
        _text_at(10, 10), _text_at(110, 10), _text_at(210, 10),
        _text_at(10, 50), _text_at(110, 50),
        _text_at(10, 90), _text_at(210, 90),
    ]

    assert "tabular-box-model" not in {
        f.code for f in _tooling_findings(tmp_path, _page_doc(objects, size=(320, 140)), text_fit=False)
    }


def test_complete_two_by_three_alignment_remains_tabular(tmp_path):
    objects = [_text_at(x, y) for y in (10, 50, 90) for x in (10, 110)]

    assert "tabular-box-model" in {
        f.code for f in _tooling_findings(tmp_path, _page_doc(objects), text_fit=False)
    }


@pytest.mark.parametrize("role", ["annotation", "furniture", "lettering"])
def test_declared_non_tabular_text_roles_are_exempt(role, tmp_path):
    objects = [_text_at(x, y, role=role) for y in (10, 50, 90) for x in (10, 110)]

    assert "tabular-box-model" not in {
        f.code for f in _tooling_findings(tmp_path, _page_doc(objects), text_fit=False)
    }


# OverflowSignal reports both laid-out and unwrapped requirements ------------


def test_overflow_signal_round_trips_unwrapped_width_and_old_payloads():
    signal = OverflowSignal(
        id="x",
        page="p1",
        source="text",
        kind="lines",
        policy="clip",
        box=(0, 0, 50, 12),
        needed=(42, 24),
        unwrapped_width=96,
        acknowledged=False,
    )

    assert OverflowSignal.from_dict(signal.to_dict()) == signal
    old = signal.to_dict()
    old.pop("unwrapped_width")
    assert OverflowSignal.from_dict(old).unwrapped_width is None
    positional = OverflowSignal(
        "x", "p1", "text", "width", "clip", (0, 0, 1, 1), (2, 1), False,
        "legacy detail",
    )
    assert positional.detail == "legacy detail"
    assert positional.unwrapped_width is None


def test_wrapped_overflow_distinguishes_laid_out_extent_from_unwrapped_width():
    doc = _page_doc([{
        "id": "wrapped",
        "type": "text",
        "box": [10, 10, 50, 12],
        "text": "alpha beta gamma",
        "style": {"font_size": 10, "line_height": 1.2},
    }])

    signal = conform.overflow_report(doc, real_metrics=False)[0]

    assert signal.needed[0] <= signal.box[2]
    assert signal.unwrapped_width is not None
    assert signal.unwrapped_width > signal.box[2]


# MCP exposes measurement before authors commit geometry ---------------------


class _FakeFastMCP:
    def __init__(self, _name: str, **_kwargs):
        self.tools: dict[str, object] = {}
        self.prompts: dict[str, object] = {}
        self.resources: dict[str, object] = {}

    def tool(self, **_kwargs):
        def decorate(func):
            self.tools[func.__name__] = func
            return func
        return decorate

    def prompt(self, **_kwargs):
        def decorate(func):
            self.prompts[func.__name__] = func
            return func
        return decorate

    def resource(self, uri: str, **_kwargs):
        def decorate(func):
            self.resources[uri] = func
            return func
        return decorate


def test_mcp_fit_text_exposes_the_same_metric_mode_and_safe_width(tmp_path):
    from frameforge.mcp.server import create_server

    server = create_server(session_root=tmp_path, fastmcp_cls=_FakeFastMCP)

    assert "fit_text" in server.tools
    result = server.tools["fit_text"](
        "positioned", ["Inter", "sans-serif"], 13, False, False
    )
    payload = getattr(result, "structuredContent", result)
    assert payload["ok"] is True
    assert payload["real_metrics"] is False
    assert payload["fit_width"] >= payload["measured_width"] > 0
