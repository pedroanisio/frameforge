#!/usr/bin/env python3
"""test_model_no_name_collisions.py — the source-of-truth model must not bind one
name to two different meanings.

`docs/models/frameforge.py` once defined ``Image = Union[Gradient, UrlImage, str]``
(a paint-value type alias) and later ``class Image(ObjBase)`` (the image *object*).
With ``from __future__ import annotations`` field annotations resolve lazily against
the module namespace, so which ``Image`` a field binds to depends on *definition
order* — the three fields annotated ``Image`` happened to resolve to the alias only
because their classes are defined before the class rebinds the name. A field added
after the class would silently bind to the OBJECT instead. That is a latent
correctness hazard (ruff flags it F811); this gate forbids the collision at the
source so it cannot return.

Dependency-free (AST only), so it runs in the base suite with no ruff/tomli.
"""
import ast
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MODEL = os.path.join(ROOT, "docs", "models", "frameforge.py")


def _module_level_bindings(path):
    """Return (class_names, alias_names) bound at module top level."""
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    classes, aliases = set(), set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    aliases.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            aliases.add(node.target.id)
    return classes, aliases


def test_no_module_level_class_shadows_a_type_alias():
    classes, aliases = _module_level_bindings(MODEL)
    collisions = classes & aliases
    assert collisions == set(), (
        "these names are bound to BOTH a module-level class and a top-level "
        f"assignment in docs/models/frameforge.py: {sorted(collisions)}. A model "
        "class must not share its name with a type alias — under lazy annotations "
        "the meaning a field binds to becomes definition-order dependent (the "
        "`Image` alias/class hazard).")
