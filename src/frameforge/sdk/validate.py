"""Validation API for the Python SDK."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from pydantic import ValidationError

from frameforge.sdk.model import validate_document


@dataclass(frozen=True)
class Issue:
    """One validation issue reported by the SDK."""

    rule_id: str
    severity: str
    path: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """Validation result for a FrameForge document."""

    ok: bool
    issues: tuple[Issue, ...]


class StaticValidationError(ValueError):
    """Static validation failed; carries the full :class:`ValidationReport`.

    Raised by :meth:`DocumentBuilder.write(fail_on_error=True)
    <frameforge.sdk.DocumentBuilder.write>`. The message lists every
    error-severity issue with its JSON-pointer path so callers (human or agent)
    can fix all of them in one pass; ``report`` holds the complete report
    (warnings included) and ``errors`` the error-severity issues.
    """

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        self.errors = tuple(issue for issue in report.issues if issue.severity == "error")
        if self.errors:
            lines = "\n".join(
                f"  [{issue.rule_id}] {issue.path or '/'}: {issue.message}"
                for issue in self.errors
            )
            message = f"static validation failed with {len(self.errors)} error(s):\n{lines}"
        else:
            message = "static validation failed"
        super().__init__(message)


def validate_static_rules(model: Any, targets: list[str] | None = None) -> ValidationReport:
    """Validate model structure plus the repository's static rule catalogue.

    ``targets`` names render targets to additionally validate: each requested
    name must be defined under ``/targets``, and each requested target's
    ``adjustments`` are applied to the reference graph — an object hidden by
    the target may not be referenced by a page ``reading_order`` entry or by a
    ``from``/``to`` anchor (id or ``{ref, port}``), since the reference would
    dangle in that target's output (rule id ``target-adjustment``). Rendering
    adjustments that cannot break references (``font_scale``,
    ``padding_delta``) need no per-target re-check.
    """
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
    issues.extend(_sdk_issues(raw, targets or []))
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
    # tooling/validate.py imports the model package-qualified (frameforge.model,
    # inside the package since 2.5.0), so it loads without any sys.modules
    # manipulation — the historical model/package swap dance is gone for good.
    import importlib.util

    root = Path(__file__).resolve().parents[3]
    path = root / "tooling" / "validate.py"
    name = "_frameforge_sdk_tooling_validate"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load tooling validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sdk_issues(raw: dict[str, Any], requested_targets: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    defs = raw.get("defs") if isinstance(raw.get("defs"), dict) else {}
    masters = defs.get("masters") if isinstance(defs.get("masters"), dict) else {}
    assets = defs.get("assets") if isinstance(defs.get("assets"), dict) else {}
    targets = raw.get("targets") if isinstance(raw.get("targets"), list) else []
    target_names = {
        target.get("name")
        for target in targets
        if isinstance(target, dict) and isinstance(target.get("name"), str)
    }

    for name in requested_targets:
        if name not in target_names:
            issues.append(_error("target", "/targets", f"requested target {name!r} is not defined"))

    for page_index, page in enumerate(raw.get("pages") or []):
        if not isinstance(page, dict):
            continue
        base = f"/pages/{page_index}"
        master = page.get("master")
        if isinstance(master, str) and master not in masters:
            issues.append(_error("reference", f"{base}/master", f"master {master!r} is not defined"))

        object_ids = _page_object_ids(page)
        for order_index, object_id in enumerate(page.get("reading_order") or []):
            if isinstance(object_id, str) and object_id not in object_ids:
                issues.append(
                    _error(
                        "reference",
                        f"{base}/reading_order/{order_index}",
                        f"reading_order id {object_id!r} does not resolve to a page object",
                    )
                )

        for path, obj in _walk_objects(page, base):
            kind = obj.get("type")
            if kind == "path" and "d" in obj and not _path_is_parseable(obj.get("d")):
                issues.append(_error("path-data", f"{path}/d", "path data is not parseable"))
            if kind == "image":
                src = obj.get("src")
                if _looks_like_asset_ref(src) and src not in assets:
                    issues.append(_error("reference", f"{path}/src", f"asset {src!r} is not defined"))

    issues.extend(_master_region_issues(masters))
    issues.extend(_target_adjustment_issues(targets, raw))
    issues.extend(_requested_target_issues(targets, raw, requested_targets))
    return issues


def _master_region_issues(masters: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for master_name, master in masters.items():
        if not isinstance(master, dict):
            continue
        regions = master.get("regions") if isinstance(master.get("regions"), list) else []
        region_ids = {
            region.get("id")
            for region in regions
            if isinstance(region, dict) and isinstance(region.get("id"), str)
        }
        edges: dict[str, str] = {}
        for index, region in enumerate(regions):
            if not isinstance(region, dict):
                continue
            region_id = region.get("id")
            next_id = region.get("next")
            if not isinstance(next_id, str):
                continue
            path = f"/defs/masters/{_ptr(master_name)}/regions/{index}/next"
            if next_id not in region_ids:
                issues.append(_error("reference", path, f"region {next_id!r} is not defined"))
            elif isinstance(region_id, str):
                edges[region_id] = next_id
        seen: set[str] = set()
        for start in edges:
            if start in seen:
                continue
            trail: set[str] = set()
            node = start
            while node in edges:
                if node in trail:
                    issues.append(
                        _error(
                            "reference-cycle",
                            f"/defs/masters/{_ptr(master_name)}/regions",
                            f"region flow contains a cycle at {node!r}",
                        )
                    )
                    break
                trail.add(node)
                seen.add(node)
                node = edges[node]
    return issues


def _target_adjustment_issues(targets: list[Any], raw: dict[str, Any]) -> list[Issue]:
    ids = _document_object_ids(raw)
    issues: list[Issue] = []
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            continue
        adjustments = target.get("adjustments")
        if not isinstance(adjustments, dict):
            continue
        hidden = adjustments.get("hide")
        if not isinstance(hidden, list):
            continue
        for hide_index, object_id in enumerate(hidden):
            if isinstance(object_id, str) and object_id not in ids:
                issues.append(
                    _error(
                        "reference",
                        f"/targets/{index}/adjustments/hide/{hide_index}",
                        f"target hide id {object_id!r} does not resolve to an object",
                    )
                )
    return issues


def _requested_target_issues(
    targets: list[Any], raw: dict[str, Any], requested_targets: list[str]
) -> list[Issue]:
    """Per-target integrity: applying a requested target's adjustments must
    leave every reference the document touches resolvable."""
    by_name = {
        target.get("name"): target
        for target in targets
        if isinstance(target, dict) and isinstance(target.get("name"), str)
    }
    issues: list[Issue] = []
    for name in requested_targets:
        target = by_name.get(name)
        if target is None:
            continue  # undefined targets are already reported above
        adjustments = target.get("adjustments")
        if not isinstance(adjustments, dict):
            continue
        hidden = {
            object_id
            for object_id in (adjustments.get("hide") or [])
            if isinstance(object_id, str)
        }
        if not hidden:
            continue
        for page_index, page in enumerate(raw.get("pages") or []):
            if not isinstance(page, dict):
                continue
            base = f"/pages/{page_index}"
            for order_index, object_id in enumerate(page.get("reading_order") or []):
                if object_id in hidden:
                    issues.append(
                        _error(
                            "target-adjustment",
                            f"{base}/reading_order/{order_index}",
                            f"target {name!r} hides {object_id!r}, which reading_order references",
                        )
                    )
            for path, obj in _walk_objects(page, base):
                for field in ("from", "to"):
                    ref = _anchor_ref(obj.get(field))
                    if ref is not None and ref in hidden:
                        issues.append(
                            _error(
                                "target-adjustment",
                                f"{path}/{field}",
                                f"target {name!r} hides {ref!r}, which a "
                                f"{obj.get('type')} anchor references",
                            )
                        )
    return issues


def _anchor_ref(value: Any) -> str | None:
    """The object id an ``Anchor`` references, if any (point anchors return None)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("ref"), str):
        return value["ref"]
    return None


def _walk_objects(root: dict[str, Any], base: str):
    for layer_index, layer in enumerate(root.get("layers") or []):
        if isinstance(layer, dict):
            for object_index, obj in enumerate(layer.get("objects") or []):
                yield from _walk_object(obj, f"{base}/layers/{layer_index}/objects/{object_index}")
    for story_index, flow in enumerate(root.get("story") or []):
        if isinstance(flow, dict) and isinstance(flow.get("object"), dict):
            yield from _walk_object(flow["object"], f"{base}/story/{story_index}/object")


def _walk_object(obj: Any, path: str):
    if not isinstance(obj, dict):
        return
    yield path, obj
    for child_index, child in enumerate(obj.get("children") or []):
        yield from _walk_object(child, f"{path}/children/{child_index}")


def _page_object_ids(page: dict[str, Any]) -> set[str]:
    return {
        obj["id"]
        for _path, obj in _walk_objects(page, "")
        if isinstance(obj.get("id"), str)
    }


def _document_object_ids(raw: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for page in raw.get("pages") or []:
        if isinstance(page, dict):
            ids.update(_page_object_ids(page))
    return ids


def _path_is_parseable(value: Any) -> bool:
    if isinstance(value, list):
        return bool(value)
    if not isinstance(value, str):
        return False
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", value)
    if not tokens:
        return False
    i = 0
    command = ""
    arity = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
    saw_command = False
    while i < len(tokens):
        token = tokens[i]
        if re.fullmatch(r"[A-Za-z]", token):
            command = token.upper()
            if command not in arity:
                return False
            saw_command = True
            i += 1
            if arity[command] == 0:
                continue
        if not command or command not in arity:
            return False
        needed = arity[command]
        if needed == 0:
            return False
        if i + needed > len(tokens):
            return False
        for part in tokens[i : i + needed]:
            if re.fullmatch(r"[A-Za-z]", part):
                return False
        i += needed
    return saw_command


def _looks_like_asset_ref(value: Any) -> bool:
    if not isinstance(value, str) or _is_remote_or_data(value):
        return False
    return "/" not in value and "\\" not in value and not value.startswith(".") and "." not in value


def _is_remote_or_data(src: str) -> bool:
    return src.strip().lower().startswith(("http://", "https://", "data:", "url("))


def _error(rule_id: str, path: str, message: str) -> Issue:
    return Issue(rule_id=rule_id, severity="error", path=path, message=message)


def _ptr(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


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


__all__ = ["Issue", "StaticValidationError", "ValidationReport", "validate_static_rules"]
