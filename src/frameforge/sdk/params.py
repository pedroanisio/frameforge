"""Document parameters — the associative core (``defs.params`` + expressions).

CAD's missing half-step: parameters as first-class document citizens. A
document declares named numbers under ``defs.params`` (values may themselves
be ``"=expr"`` strings over earlier parameters); any string field anywhere in
the document of the form ``"=expr"`` resolves to its evaluated value before
validation. Numeric positions (boxes, points, sizes) become numbers; ``text``
/ ``content`` fields become formatted strings — the driven-dimension case,
where a label shows the same number that shapes the geometry.

Evaluation is a whitelisted arithmetic AST — numbers, arithmetic operators,
parameter names, and a small math namespace. Never Python ``eval``: no calls
outside the whitelist, no attributes, no subscripts, no lambdas, no
conditionals. Unknown names are errors, not silence.
"""
from __future__ import annotations

import ast
import copy
import math
from typing import Any, Mapping

__all__ = ["eval_expr", "resolve_params"]

_FUNCS: dict[str, Any] = {
    "abs": abs, "min": min, "max": max, "round": round,
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "atan2": math.atan2, "degrees": math.degrees, "radians": math.radians,
    "floor": math.floor, "ceil": math.ceil, "hypot": math.hypot,
}
_CONSTS: dict[str, float] = {"pi": math.pi, "tau": math.tau, "e": math.e}

_BINOPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
           ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b,
           ast.FloorDiv: lambda a, b: a // b, ast.Mod: lambda a, b: a % b,
           ast.Pow: lambda a, b: a ** b}
_UNARYOPS = {ast.UAdd: lambda a: +a, ast.USub: lambda a: -a}


def eval_expr(expr: str, params: Mapping[str, float]) -> float:
    """Evaluate a whitelisted arithmetic expression over ``params``."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid parameter expression {expr!r}: {exc.msg}") from exc

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return float(node.value)
            raise ValueError(f"non-numeric constant in expression {expr!r}")
        if isinstance(node, ast.Name):
            if node.id in params:
                return float(params[node.id])
            if node.id in _CONSTS:
                return _CONSTS[node.id]
            raise ValueError(f"unknown name {node.id!r} in expression {expr!r}")
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return _BINOPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
            return _UNARYOPS[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _FUNCS \
                    and not node.keywords:
                return float(_FUNCS[node.func.id](*[ev(a) for a in node.args]))
            raise ValueError(f"call outside the whitelist in expression {expr!r}")
        raise ValueError(f"unsupported syntax in expression {expr!r}: "
                         f"{type(node).__name__}")

    return ev(tree)


def _is_expr(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("=") and len(value) > 1


def _fmt(value: float) -> str:
    return f"{value:g}"


def resolve_params(doc: Mapping[str, Any]) -> dict[str, Any]:
    """A deep copy of ``doc`` with every ``"=expr"`` string resolved.

    ``defs.params`` resolves first (iteratively, so parameters may reference
    earlier ones; a reference cycle or unknown name fails with the offending
    depth). Documents without parameters pass through untouched — and a
    string that merely *starts* with '=' but does not parse as an expression
    is left alone only when no parameters are declared; with parameters
    declared, a malformed expression is an error, not silence.
    """
    out = copy.deepcopy(dict(doc))
    raw = ((out.get("defs") or {}).get("params") or {})
    if not raw:
        return out

    params: dict[str, float] = {}
    pending = dict(raw)
    for _depth in range(len(pending) + 1):
        progressed = False
        for name, value in list(pending.items()):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                params[name] = float(value)
            elif _is_expr(value):
                try:
                    params[name] = eval_expr(value[1:], params)
                except ValueError:
                    continue
            else:
                raise ValueError(f"parameter {name!r} must be a number or '=expr'")
            del pending[name]
            progressed = True
        if not pending:
            break
        if not progressed:
            raise ValueError(
                f"could not resolve parameters at any depth: {sorted(pending)} "
                "(unknown name or reference cycle)")

    def walk(value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {k: walk(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v, key) for v in value]
        if _is_expr(value):
            resolved = eval_expr(value[1:], params)
            return _fmt(resolved) if key in ("text", "content") else resolved
        return value

    resolved_doc = {k: walk(v, k) for k, v in out.items()}
    resolved_doc.setdefault("meta", {})
    if isinstance(resolved_doc["meta"], dict):
        resolved_doc["meta"].setdefault("resolved_params", dict(params))
    return resolved_doc
