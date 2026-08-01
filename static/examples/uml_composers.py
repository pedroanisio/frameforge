#!/usr/bin/env python3
"""UML 2.5.1 composer atlas — typed semantics to valid FrameForge v2 pages.

The fourteen pages exercise every absorbed UML composer. Hierarchical kinds use
the full four-stage Sugiyama layout; sequence, timing, communication, and
composite-structure kinds use their notation-specific deterministic layouts.

Writes ``_tmp/uml-composers/`` (YAML + SVG pages). The MCP run contract is
``build()``; ``--update-fixtures`` derives fourteen minimal single-page
conformance fixtures from that one typed source.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]

from frameforge_sdk import (
    # noqa: E402     HEAD_VERSION,
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
    serialize,
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
from frameforge.conform import render_page_svgs

_CANVAS = (640.0, 480.0)


def _cases():
    return [
        (
            "class",
            validate_class_diagram,
            compose_class_diagram,
            {
                "classes": [
                    {"id": "entity", "name": "Entity", "attributes": [{"name": "id", "type": "UUID"}]},
                    {"id": "order", "name": "Order", "operations": [{"name": "total", "return_type": "Money"}]},
                ],
                "generalizations": [{"id": "inherits", "from": "order", "to": "entity"}],
            },
        ),
        (
            "package",
            validate_package_diagram,
            compose_package_diagram,
            {
                "packages": [{"id": "domain", "name": "domain"}, {"id": "api", "name": "api"}],
                "dependencies": [{"id": "uses", "from": "api", "to": "domain"}],
            },
        ),
        (
            "use-case",
            validate_use_case_diagram,
            compose_use_case_diagram,
            {
                "actors": [{"id": "operator", "name": "Operator"}],
                "use_cases": [{"id": "publish", "name": "Publish"}],
                "relations": [{"id": "performs", "from": "operator", "to": "publish"}],
            },
        ),
        (
            "component",
            validate_component_diagram,
            compose_component_diagram,
            {
                "components": [{"id": "web", "name": "Web"}, {"id": "api", "name": "API"}],
                "connectors": [{"id": "calls", "from": "web", "to": "api"}],
            },
        ),
        (
            "deployment",
            validate_deployment_diagram,
            compose_deployment_diagram,
            {
                "nodes": [{"id": "edge", "name": "Edge"}, {"id": "worker", "name": "Worker"}],
                "relations": [{"id": "network", "from": "edge", "to": "worker"}],
            },
        ),
        (
            "activity",
            validate_activity_diagram,
            compose_activity_diagram,
            {
                "nodes": [{"id": "start", "kind": "initial"}, {"id": "work", "kind": "action", "name": "Validate"}, {"id": "end", "kind": "final"}],
                "edges": [{"id": "e1", "from": "start", "to": "work"}, {"id": "e2", "from": "work", "to": "end"}],
            },
        ),
        (
            "state-machine",
            validate_state_machine,
            compose_state_machine,
            {
                "states": [{"id": "ready", "name": "Ready"}, {"id": "done", "name": "Done"}],
                "transitions": [{"id": "finish", "from": "ready", "to": "done", "trigger": "complete"}],
            },
        ),
        (
            "sequence",
            validate_sequence_diagram,
            compose_sequence_diagram,
            {
                "lifelines": [{"id": "client", "name": "Client"}, {"id": "service", "name": "Service"}],
                "messages": [{"id": "request", "from": "client", "to": "service", "step": 1, "name": "request()"}],
            },
        ),
        (
            "timing",
            validate_timing_diagram,
            compose_timing_diagram,
            {
                "lifelines": [{"id": "clock", "name": "Clock", "states": ["low", "high"]}],
                "changes": [{"id": "rise", "lifeline": "clock", "state": "high", "at": 1.0}, {"id": "fall", "lifeline": "clock", "state": "low", "at": 2.0}],
            },
        ),
        (
            "communication",
            validate_communication_diagram,
            compose_communication_diagram,
            {
                "lifelines": [{"id": "client", "name": "Client"}, {"id": "service", "name": "Service"}],
                "messages": [{"id": "request", "from": "client", "to": "service", "sequence": "1", "name": "request()"}],
            },
        ),
        (
            "interaction-overview",
            validate_interaction_overview,
            compose_interaction_overview,
            {
                "nodes": [{"id": "start", "kind": "initial"}, {"id": "login", "kind": "interaction_use", "name": "Login"}, {"id": "end", "kind": "final"}],
                "edges": [{"id": "e1", "from": "start", "to": "login"}, {"id": "e2", "from": "login", "to": "end"}],
            },
        ),
        (
            "profile",
            validate_profile_diagram,
            compose_profile_diagram,
            {
                "stereotypes": [{"id": "service", "name": "Service"}],
                "metaclasses": [{"id": "component", "name": "Component"}],
                "extensions": [{"id": "extends", "from": "service", "to": "component"}],
            },
        ),
        (
            "composite-structure",
            validate_composite_structure,
            compose_composite_structure,
            {
                "classifier_id": "system",
                "classifier_name": "System",
                "parts": [{"id": "frontend", "name": "Frontend"}, {"id": "backend", "name": "Backend"}],
                "connectors": [{"id": "link", "from": "frontend", "to": "backend"}],
            },
        ),
        (
            "object",
            validate_object_diagram,
            compose_object_diagram,
            {
                "instances": [{"id": "alice", "name": "alice", "type_name": "User"}, {"id": "order", "type_name": "Order"}],
                "links": [{"id": "placed", "from": "alice", "to": "order", "name": "placed"}],
            },
        ),
    ]


def build():
    """MCP contract: return the deterministic fourteen-page UML atlas."""
    pages = []
    for page_id, validator, composer, payload in _cases():
        composed = composer(validator(payload), canvas_size=_CANVAS)
        pages.append(composed.to_page(page_id=page_id, canvas_size=_CANVAS))
    return {
        "dsl": "FrameForge",
        "version": HEAD_VERSION,
        "profile": "diagram",
        "title": "UML 2.5.1 composer atlas",
        "pages": pages,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-fixture",
        "--update-fixtures",
        dest="update_fixture",
        action="store_true",
        help="regenerate the fourteen tests/fixtures/uml-*.fg.yaml files from build()",
    )
    args = parser.parse_args(argv)
    out = os.path.join(ROOT, "_tmp", "uml-composers")
    os.makedirs(out, exist_ok=True)
    document = build()
    with open(os.path.join(out, "uml-composers.fg.yaml"), "w", encoding="utf-8") as stream:
        stream.write(serialize(document))
    for page, svg in zip(document["pages"], render_page_svgs(document), strict=True):
        with open(os.path.join(out, f"{page['id']}.svg"), "w", encoding="utf-8") as stream:
            stream.write(svg)
    if args.update_fixture:
        fixture_dir = os.path.join(ROOT, "tests", "fixtures")
        for page in document["pages"]:
            single = {
                **document,
                "title": f"UML 2.5.1 {page['id']} composer fixture",
                "pages": [page],
            }
            single_path = os.path.join(fixture_dir, f"uml-{page['id']}.fg.yaml")
            single_header = (
                f"# Canonical UML 2.5.1 {page['id']} composer fixture.\n"
                "# GENERATED by static/examples/uml_composers.py --update-fixtures;\n"
                "# edit the typed input in that example, never this file.\n"
            )
            with open(single_path, "w", encoding="utf-8") as stream:
                stream.write(single_header + serialize(single))
        print(f"Updated fourteen UML fixtures in {fixture_dir}")
    print(f"Wrote the UML composer atlas to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
