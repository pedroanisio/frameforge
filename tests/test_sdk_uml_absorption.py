#!/usr/bin/env python3
"""Typed UML 2.5.1 ontology and all-composer v2 contract (GitHub #30)."""
from __future__ import annotations

from pathlib import Path
import json
from hashlib import sha256

import pytest
from pydantic import ValidationError

from frameforge.sdk import page_hashes, parse, render_page_svgs, validate_document
from frameforge.sdk.uml import (
    compose_activity_diagram,
    compose_class_diagram,
    compose_communication_diagram,
    compose_component_diagram,
    compose_composite_structure,
    compose_deployment_diagram,
    compose_interaction_overview,
    compose_object_diagram,
    compose_package_diagram,
    compose_profile_diagram,
    compose_sequence_diagram,
    compose_state_machine,
    compose_timing_diagram,
    compose_use_case_diagram,
)
from frameforge.sdk.uml_models import (
    UMLAssociation,
    UMLAttribute,
    UMLClass,
    UMLEnumeration,
    UMLInterface,
    UMLOperation,
    validate_activity_diagram,
    validate_class_diagram,
    validate_communication_diagram,
    validate_component_diagram,
    validate_composite_structure,
    validate_deployment_diagram,
    validate_interaction_overview,
    validate_object_diagram,
    validate_package_diagram,
    validate_profile_diagram,
    validate_sequence_diagram,
    validate_state_machine,
    validate_timing_diagram,
    validate_use_case_diagram,
)


def test_uml_and_sugiyama_are_public_sdk_capabilities():
    import frameforge.sdk as sdk

    required = {
        "SugiyamaConfig",
        "UMLClassDiagramModel",
        "compose_activity_diagram",
        "compose_class_diagram",
        "compose_communication_diagram",
        "compose_component_diagram",
        "compose_composite_structure",
        "compose_deployment_diagram",
        "compose_interaction_overview",
        "compose_object_diagram",
        "compose_package_diagram",
        "compose_profile_diagram",
        "compose_sequence_diagram",
        "compose_state_machine",
        "compose_timing_diagram",
        "compose_use_case_diagram",
        "sugiyama_layout",
        "validate_class_diagram",
    }
    assert required <= set(sdk.__all__)
    assert all(callable(getattr(sdk, name)) for name in required - {"SugiyamaConfig", "UMLClassDiagramModel"})


CASES = [
    ("class", validate_class_diagram, compose_class_diagram, {"classes": [{"id": "c", "name": "Customer"}]}),
    ("package", validate_package_diagram, compose_package_diagram, {"packages": [{"id": "p", "name": "Billing"}]}),
    ("use-case", validate_use_case_diagram, compose_use_case_diagram, {"actors": [{"id": "a", "name": "Operator"}]}),
    ("component", validate_component_diagram, compose_component_diagram, {"components": [{"id": "c", "name": "API"}]}),
    ("deployment", validate_deployment_diagram, compose_deployment_diagram, {"nodes": [{"id": "n", "name": "Worker"}]}),
    ("activity", validate_activity_diagram, compose_activity_diagram, {"nodes": [{"id": "i", "kind": "initial"}]}),
    ("state-machine", validate_state_machine, compose_state_machine, {"states": [{"id": "s", "name": "Ready"}]}),
    ("sequence", validate_sequence_diagram, compose_sequence_diagram, {"lifelines": [{"id": "l", "name": "Service"}]}),
    ("timing", validate_timing_diagram, compose_timing_diagram, {"lifelines": [{"id": "l", "name": "Clock", "states": ["low", "high"]}]}),
    ("communication", validate_communication_diagram, compose_communication_diagram, {"lifelines": [{"id": "l", "name": "Client"}]}),
    ("interaction-overview", validate_interaction_overview, compose_interaction_overview, {"nodes": [{"id": "i", "kind": "initial"}]}),
    ("profile", validate_profile_diagram, compose_profile_diagram, {"stereotypes": [{"id": "s", "name": "Service"}]}),
    ("composite-structure", validate_composite_structure, compose_composite_structure, {"classifier_id": "system", "classifier_name": "System", "parts": [{"id": "part", "name": "Part"}]}),
    ("object", validate_object_diagram, compose_object_diagram, {"instances": [{"id": "u1", "name": "alice", "type_name": "User"}]}),
]


def _objects(document: dict):
    def walk(values):
        for value in values:
            yield value
            yield from walk(value.get("children", []))

    for page in document["pages"]:
        for layer in page.get("layers", []):
            yield from walk(layer.get("objects", []))


@pytest.mark.parametrize(("kind", "validator", "composer", "raw"), CASES, ids=[case[0] for case in CASES])
def test_all_fourteen_composers_emit_model_valid_v2_documents(kind, validator, composer, raw):
    composed = composer(validator(raw), canvas_size=(640, 480))
    document = composed.to_document(title=f"UML {kind}", page_id=kind)

    validated = validate_document(document)
    assert validated.pages[0].id == kind
    assert any(page.layers for page in validated.pages)

    for obj in _objects(document):
        stroke = obj.get("stroke")
        assert not isinstance(stroke, dict) or not ({"width", "dash", "arrow_start", "arrow_end"} & stroke.keys())
        if obj.get("type") == "connector":
            assert isinstance(obj["from"], dict) or isinstance(obj["from"], list)
            assert isinstance(obj["to"], dict) or isinstance(obj["to"], list)
        if obj.get("type") == "text" and isinstance(obj.get("style"), dict):
            assert not ({"size", "wrap", "align"} & obj["style"].keys())


@pytest.mark.parametrize(
    ("validator", "payload", "message"),
    [
        (validate_class_diagram, {"classes": [{"id": "c", "name": "C", "attributes": [{"name": "x", "multiplicity": "2..1"}]}]}, "upper bound"),
        (validate_sequence_diagram, {"lifelines": [{"id": "x", "name": "X"}, {"id": "x", "name": "Y"}]}, "duplicate UML element id"),
        (validate_state_machine, {"states": [{"id": "s", "name": "S"}], "transitions": [{"id": "t", "from": "s", "to": "missing"}]}, "unknown"),
    ],
)
def test_uml_ontology_rejects_semantically_invalid_models(validator, payload, message):
    with pytest.raises(ValidationError, match=message):
        validator(payload)


@pytest.mark.parametrize("value", ["1", "0..1", "1..*", "*", "12..99"])
def test_uml_multiplicity_accepts_canonical_ranges(value):
    assert UMLAttribute(name="value", multiplicity=value).multiplicity == value


@pytest.mark.parametrize("value", ["", "..1", "1..", "-1", "5..3", "many"])
def test_uml_multiplicity_rejects_malformed_or_inverted_ranges(value):
    with pytest.raises(ValidationError):
        UMLAttribute(name="value", multiplicity=value)


def test_uml_classifier_feature_constraints_are_strict():
    with pytest.raises(ValidationError, match="abstract.*final"):
        UMLClass(id="sealed-abstract", name="Impossible", abstract=True, final=True)
    with pytest.raises(ValidationError, match="direction='return'"):
        UMLOperation(
            name="ambiguous",
            parameters=[
                {"name": "one", "direction": "return"},
                {"name": "two", "direction": "return"},
            ],
        )
    with pytest.raises(ValidationError, match="static=True and readonly=True"):
        UMLInterface(
            id="mutable-interface",
            name="MutableInterface",
            constants=[{"name": "value", "static": False, "readonly": True}],
        )
    with pytest.raises(ValidationError, match="public"):
        UMLInterface(
            id="private-interface",
            name="PrivateInterface",
            operations=[{"name": "hidden", "visibility": "private"}],
        )
    with pytest.raises(ValidationError, match="duplicate"):
        UMLEnumeration(id="color", name="Color", literals=["RED", "RED"])


def test_uml_composition_and_member_distinguishability_constraints_are_strict():
    with pytest.raises(ValidationError, match="composit"):
        UMLAssociation(
            id="owns",
            end1={"id_ref": "Whole"},
            end2={"id_ref": "Part", "multiplicity": "0..*"},
            kind="composition",
        )
    with pytest.raises(ValidationError, match="distinguishable|duplicate"):
        UMLClass(
            id="duplicate-members",
            name="DuplicateMembers",
            attributes=[{"name": "x", "type": "int"}, {"name": "x", "type": "str"}],
        )
    overloaded = UMLClass(
        id="overloaded",
        name="Overloaded",
        operations=[
            {"name": "find", "parameters": [{"name": "value", "type": "int"}]},
            {"name": "find", "parameters": [{"name": "value", "type": "str"}]},
        ],
    )
    assert len(overloaded.operations) == 2


def test_uml_generalization_graph_enforces_cycles_finality_and_classifier_kinds():
    with pytest.raises(ValidationError, match="generalization cycle"):
        validate_class_diagram(
            {
                "classes": [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
                "generalizations": [
                    {"id": "ab", "from": "a", "to": "b"},
                    {"id": "ba", "from": "b", "to": "a"},
                ],
            }
        )
    with pytest.raises(ValidationError, match="final"):
        validate_class_diagram(
            {
                "classes": [
                    {"id": "child", "name": "Child"},
                    {"id": "sealed", "name": "Sealed", "final": True},
                ],
                "generalizations": [{"id": "inherits", "from": "child", "to": "sealed"}],
            }
        )
    with pytest.raises(ValidationError, match="specialize_type|incompatible"):
        validate_class_diagram(
            {
                "classes": [{"id": "class", "name": "Class"}],
                "interfaces": [{"id": "interface", "name": "Interface"}],
                "generalizations": [{"id": "wrong", "from": "class", "to": "interface"}],
            }
        )


def test_class_sequence_and_state_machine_render_end_to_end():
    class_doc = compose_class_diagram(
        validate_class_diagram(
            {
                "classes": [{"id": "parent", "name": "Parent"}, {"id": "child", "name": "Child"}],
                "generalizations": [{"id": "inherits", "from": "child", "to": "parent"}],
            }
        ),
        canvas_size=(640, 480),
    ).to_document(title="Class", page_id="class")
    sequence_doc = compose_sequence_diagram(
        validate_sequence_diagram(
            {
                "lifelines": [{"id": "client", "name": "Client"}, {"id": "api", "name": "API"}],
                "messages": [{"id": "call", "from": "client", "to": "api", "step": 1, "name": "request()"}],
            }
        ),
        canvas_size=(640, 480),
    ).to_document(title="Sequence", page_id="sequence")
    state_doc = compose_state_machine(
        validate_state_machine(
            {
                "states": [{"id": "ready", "name": "Ready"}, {"id": "done", "name": "Done"}],
                "transitions": [{"id": "finish", "from": "ready", "to": "done"}],
            }
        ),
        canvas_size=(640, 480),
    ).to_document(title="State", page_id="state")

    assert "Parent" in render_page_svgs(class_doc)[0]
    assert "request()" in render_page_svgs(sequence_doc)[0]
    assert "Ready" in render_page_svgs(state_doc)[0]


def test_backend_specific_uml_frames_are_lowered_to_portable_v2_primitives():
    activity = compose_activity_diagram(
        validate_activity_diagram(
            {
                "nodes": [{"id": "work", "kind": "action", "name": "Review"}],
                "swimlanes": [{"id": "ops", "name": "Operations"}],
            }
        ),
        canvas_size=(640, 480),
    ).to_document(title="Activity", page_id="activity")
    overview = compose_interaction_overview(
        validate_interaction_overview(
            {"nodes": [{"id": "ref", "kind": "interaction_use", "name": "Authorize"}]}
        ),
        canvas_size=(640, 480),
    ).to_document(title="Overview", page_id="overview")
    timing = compose_timing_diagram(
        validate_timing_diagram(
            {"lifelines": [{"id": "clock", "name": "Clock", "states": ["Low", "High"]}]}
        ),
        canvas_size=(640, 480),
    ).to_document(title="Timing", page_id="timing")

    unsupported = {"uml.fragment_frame", "uml.swimlane", "uml.timing_lane"}
    for document, expected_text in (
        (activity, "Operations"),
        (overview, "Authorize"),
        (timing, "Clock"),
    ):
        assert not ({obj.get("type") for obj in _objects(document)} & unsupported)
        assert expected_text in render_page_svgs(document)[0]


def test_composer_geometry_stays_inside_small_requested_canvases():
    package = compose_package_diagram(
        validate_package_diagram(
            {"packages": [{"id": "domain", "name": "Domain"}, {"id": "api", "name": "API"}]}
        ),
        canvas_size=(640, 480),
    ).to_document(title="Package", page_id="package")
    timing = compose_timing_diagram(
        validate_timing_diagram(
            {"lifelines": [{"id": "clock", "name": "Clock", "states": ["Low", "High"]}]}
        ),
        canvas_size=(640, 480),
    ).to_document(title="Timing", page_id="timing")

    for group in (obj for obj in _objects(package) if obj.get("type") == "group"):
        width, height = group["box"][2:4]
        for child in group["children"]:
            if child.get("box"):
                x, y, child_width, child_height = child["box"]
                assert x >= 0 and y >= 0
                assert x + child_width <= width
                assert y + child_height <= height

    page_width, page_height = timing["pages"][0]["canvas"]["size"]
    for obj in _objects(timing):
        if obj.get("box"):
            x, y, width, height = obj["box"]
            if obj.get("type") == "group":
                assert x + width <= page_width
                assert y + height <= page_height


def test_uml_composer_fixture_is_reproducible_and_pins_key_diagram_goldens():
    from static.examples.uml_composers import build

    fixture_dir = Path(__file__).parents[1] / "tests" / "fixtures"
    generated = validate_document(build())

    assert [page.id for page in generated.pages] == [
        "class",
        "package",
        "use-case",
        "component",
        "deployment",
        "activity",
        "state-machine",
        "sequence",
        "timing",
        "communication",
        "interaction-overview",
        "profile",
        "composite-structure",
        "object",
    ]

    for page in generated.pages:
        single_path = fixture_dir / f"uml-{page.id}.fg.yaml"
        single = parse(single_path.read_text(encoding="utf-8"), forgiving=False)
        assert [candidate.id for candidate in single.pages] == [page.id]
        assert single.pages[0].model_dump(mode="json", exclude_none=True) == page.model_dump(
            mode="json", exclude_none=True
        )

    lock_path = Path(__file__).parents[1] / "tests" / "golden" / "uml-composers.lock.json"
    locked = json.loads(lock_path.read_text(encoding="utf-8"))
    hashes = dict(zip((page.id for page in generated.pages), page_hashes(generated), strict=True))
    assert {key: hashes[key] for key in locked} == locked


def test_omg_uml_251_xmi_reference_set_is_preserved_with_checksums():
    root = Path(__file__).parents[1] / "static" / "specs" / "uml-2.5.1"
    names = {path.name for path in root.glob("ptc-18-01-0*.xmi")}
    assert names == {
        "ptc-18-01-01.xmi",
        "ptc-18-01-02.xmi",
        "ptc-18-01-03.xmi",
        "ptc-18-01-04.xmi",
    }
    checksum_rows = (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    checksums = dict(row.split(maxsplit=1) for row in checksum_rows)
    checksums = {name: digest for digest, name in checksums.items()}
    assert set(checksums) == names
    for name, expected in checksums.items():
        assert sha256((root / name).read_bytes()).hexdigest() == expected
