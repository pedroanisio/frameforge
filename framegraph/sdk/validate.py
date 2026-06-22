"""Validation API for the Python SDK."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from pydantic import ValidationError

from framegraph.sdk.model import model_module, validate_document


@dataclass(frozen=True)
class Issue:
    """One validation issue reported by the SDK."""

    rule_id: str
    severity: str
    path: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """Validation result for a FrameGraph document."""

    ok: bool
    issues: tuple[Issue, ...]


def validate_static_rules(model: Any, targets: list[str] | None = None) -> ValidationReport:
    """Validate model structure plus the repository's static rule catalogue.

    ``targets`` is accepted for API compatibility with the proposal. Targeted
    adjustment validation is not implemented by the current validator, so the
    argument is recorded as a future extension and otherwise ignored.
    """
    _ = targets
    issues: list[Issue] = []
    try:
        validated = validate_document(model)
        raw = validated.model_dump(by_alias=True, exclude_none=True)
    except ValidationError as exc:
        for err in exc.errors():
            issues.append(
                Issue(
                    rule_id="structure",
                    severity="error",
                    path=_json_pointer(err.get("loc", ())),
                    message=str(err.get("msg", "")),
                )
            )
        return ValidationReport(ok=False, issues=tuple(issues))

    issues.extend(_tooling_issues(raw))
    ok = not any(issue.severity == "error" for issue in issues)
    return ValidationReport(ok=ok, issues=tuple(issues))


def _tooling_issues(raw: dict[str, Any]) -> list[Issue]:
    tooling_validate = _load_tooling_validate()

    fd, path = tempfile.mkstemp(suffix=".fg.json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(raw, fh)
        _, findings, _code = tooling_validate.validate_doc(path)
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    return [
        Issue(
            rule_id=f.code,
            severity="error" if f.severity == "ERROR" else "warning",
            path=_finding_path_to_pointer(f.path),
            message=f.msg,
        )
        for f in findings
    ]


def _load_tooling_validate():
    import importlib.util
    import sys

    root = Path(__file__).resolve().parents[2]
    path = root / "tooling" / "validate.py"
    name = "_framegraph_sdk_tooling_validate"
    previous = sys.modules.get("framegraph")
    sys.modules["framegraph"] = model_module()
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load tooling validator")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop("framegraph", None)
        else:
            sys.modules["framegraph"] = previous


def _json_pointer(loc: tuple[object, ...] | list[object]) -> str:
    if not loc:
        return ""
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in loc)


def _finding_path_to_pointer(path: str) -> str:
    if not path:
        return ""
    out: list[str] = []
    token = ""
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if token:
                out.append(token)
                token = ""
            i += 1
        elif ch == "[":
            if token:
                out.append(token)
                token = ""
            j = path.find("]", i)
            if j == -1:
                out.append(path[i + 1 :])
                break
            out.append(path[i + 1 : j])
            i = j + 1
        else:
            token += ch
            i += 1
    if token:
        out.append(token)
    return _json_pointer(out)


__all__ = ["Issue", "ValidationReport", "validate_static_rules"]
