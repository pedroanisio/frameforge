"""recipe.parse — turn an untrusted data structure into a validated Recipe.

The incoming structure is treated as untrusted: every problem is collected and
reported together (not just the first), and :func:`parse` raises
:class:`RecipeError` rather than ever returning a half-valid object.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from recipe.graph import find_cycle
from recipe.model import Command, Recipe, RecipeBook, Step


class RecipeError(ValueError):
    """Raised when a data structure is not a valid recipe. Carries all issues."""

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        body = "\n  - ".join(self.errors)
        super().__init__(f"invalid recipe ({len(self.errors)} issue(s)):\n  - {body}")


def parse(data: Any) -> Recipe:
    """Validate ``data`` (a mapping) and return a :class:`Recipe`, else raise."""
    errors: list[str] = []
    recipe = _parse_recipe(data, errors)
    if errors or recipe is None:
        raise RecipeError(errors or ["could not parse recipe"])
    return recipe


def parse_book(data: Any) -> RecipeBook:
    """Validate a collection of recipes linked by recipe-level ``depends_on``.

    ``data`` is a list of recipes, or a mapping with a ``recipes:`` list. Within
    a book every recipe needs a unique ``id``; ``depends_on`` must reference
    existing recipes and form no cycle.
    """
    if isinstance(data, dict) and "recipes" in data:
        raw = data.get("recipes")
    elif isinstance(data, list):
        raw = data
    else:
        raise RecipeError(["a recipe book must be a list of recipes or a mapping "
                           "with a `recipes:` list"])
    if not isinstance(raw, list):
        raise RecipeError(["`recipes` must be a list"])

    errors: list[str] = []
    recipes: list[Recipe] = []
    seen: set[str] = set()
    for i, rd in enumerate(raw):
        sub: list[str] = []
        r = _parse_recipe(rd, sub)
        label = r.id if (r is not None and r.id) else f"recipes[{i}]"
        errors += [f"{label}: {e}" for e in sub]
        if r is None:
            continue
        if not r.id:
            errors.append(f"recipes[{i}]: `id` is required for every recipe in a book")
        elif r.id in seen:
            errors.append(f"recipe {r.id!r}: duplicate recipe id")
        else:
            seen.add(r.id)
        recipes.append(r)

    book = RecipeBook(recipes=recipes)
    rids = set(book.ids)
    for r in recipes:
        for dep in r.depends_on:
            if dep == r.id:
                errors.append(f"recipe {r.id!r}: depends_on lists itself")
            elif dep not in rids:
                errors.append(f"recipe {r.id!r}: depends_on references unknown recipe {dep!r}")
    cycle = find_cycle(book.ids, {r.id: r.depends_on for r in recipes})
    if cycle:
        errors.append("recipe dependency cycle: " + " -> ".join(cycle))

    if errors:
        raise RecipeError(errors)
    return book


def load(path: str | Path) -> Recipe:
    """Load and validate a single recipe from a ``.yaml`` / ``.yml`` / ``.json`` file."""
    return parse(_read(Path(path)))


def load_book(path: str | Path) -> RecipeBook:
    """Load and validate a book (a file holding a ``recipes:`` list)."""
    return parse_book(_read(Path(path)))


def load_many(paths: list[str | Path]) -> RecipeBook:
    """Assemble a book from several single-recipe files (one recipe per file)."""
    return parse_book([_read(Path(p)) for p in paths])


def load_any(paths: list[str | Path]) -> Recipe | RecipeBook:
    """Load one path as a recipe-or-book, or several paths as a book."""
    if len(paths) != 1:
        return load_many(paths)
    data = _read(Path(paths[0]))
    if isinstance(data, list) or (isinstance(data, dict) and "recipes" in data):
        return parse_book(data)
    return parse(data)


def _read(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RecipeError([f"cannot read {path.suffix} without PyYAML; "
                           "install pyyaml or use a .json file"]) from exc
    return yaml.safe_load(text)


def _parse_recipe(data: Any, errors: list[str]) -> Recipe | None:
    """Parse one recipe, appending problems to ``errors``. Recipe-level
    ``depends_on`` (cross-recipe links) is recorded but resolved by the book."""
    if not isinstance(data, dict):
        errors.append(f"recipe must be a mapping, got {type(data).__name__}")
        return None

    goal = data.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        errors.append("`goal` is required and must be a non-empty string")
        goal = goal if isinstance(goal, str) else ""

    rid = data.get("id", "")
    if not isinstance(rid, str):
        errors.append("`id` must be a string")
        rid = ""

    recipe_deps = _as_str_list(data.get("depends_on", []), "depends_on", errors)
    preconditions = _as_str_list(data.get("preconditions", []), "preconditions", errors)

    desired_state = data.get("desired_state", "")
    if not isinstance(desired_state, str):
        errors.append("`desired_state` must be a string")
        desired_state = ""

    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list):
        errors.append("`steps` must be a list")
        raw_steps = []

    steps: list[Step] = []
    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_steps):
        step = _parse_step(raw, i, seen_ids, errors)
        if step is not None:
            steps.append(step)

    recipe = Recipe(goal=goal or "", preconditions=preconditions,
                    desired_state=desired_state, steps=steps,
                    id=rid, depends_on=recipe_deps)

    # cross-step validation (within this recipe)
    ids = set(recipe.ids)
    for s in steps:
        for dep in s.depends_on:
            if dep == s.id:
                errors.append(f"step {s.id!r}: depends_on lists itself")
            elif dep not in ids:
                errors.append(f"step {s.id!r}: depends_on references unknown step {dep!r}")
        if s.independent and s.depends_on:
            errors.append(f"step {s.id!r}: marked independent but declares depends_on {s.depends_on}")

    cycle = find_cycle(recipe.ids, {s.id: s.depends_on for s in steps})
    if cycle:
        errors.append("step dependency cycle: " + " -> ".join(cycle))

    return recipe


# --------------------------------------------------------------------------- #
#  internals
# --------------------------------------------------------------------------- #
def _as_str_list(value: Any, field_name: str, errors: list[str]) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        errors.append(f"`{field_name}` must be a list of strings")
        return []
    return list(value)


def _parse_step(raw: Any, index: int, seen_ids: set[str], errors: list[str]) -> Step | None:
    where = f"steps[{index}]"
    if not isinstance(raw, dict):
        errors.append(f"{where}: must be a mapping")
        return None

    sid = raw.get("id")
    if not isinstance(sid, str) or not sid.strip():
        errors.append(f"{where}: `id` is required and must be a non-empty string")
        return None
    if sid in seen_ids:
        errors.append(f"{where}: duplicate step id {sid!r}")
        return None
    seen_ids.add(sid)

    for key in ("goal", "as_is", "to_be"):
        if key in raw and not isinstance(raw[key], str):
            errors.append(f"step {sid!r}: `{key}` must be a string")

    independent = raw.get("independent", False)
    if not isinstance(independent, bool):
        errors.append(f"step {sid!r}: `independent` must be true/false")
        independent = False

    depends_on = _as_str_list(raw.get("depends_on", []), f"step {sid!r}.depends_on", errors)

    raw_cmds = raw.get("commands", [])
    if not isinstance(raw_cmds, list):
        errors.append(f"step {sid!r}: `commands` must be a list")
        raw_cmds = []
    commands: list[Command] = []
    for j, rc in enumerate(raw_cmds):
        cmd = _parse_command(rc, sid, j, errors)
        if cmd is not None:
            commands.append(cmd)

    return Step(
        id=sid,
        goal=str(raw.get("goal", "")),
        as_is=str(raw.get("as_is", "")),
        to_be=str(raw.get("to_be", "")),
        commands=commands,
        depends_on=depends_on,
        independent=independent,
    )


def _parse_command(raw: Any, sid: str, index: int, errors: list[str]) -> Command | None:
    where = f"step {sid!r} commands[{index}]"
    if not isinstance(raw, dict):
        errors.append(f"{where}: must be a mapping")
        return None

    target, mutate = raw.get("target"), raw.get("mutate")
    ok = True
    if not isinstance(target, str) or not target.strip():
        errors.append(f"{where}: `target` (file/folder) is required")
        ok = False
    if not isinstance(mutate, str) or not mutate.strip():
        errors.append(f"{where}: `mutate` command is required")
        ok = False
    reverse = raw.get("reverse")
    if reverse is not None and not isinstance(reverse, str):
        errors.append(f"{where}: `reverse` must be a string or omitted")
        ok = False
    note = raw.get("note")
    if note is not None and not isinstance(note, str):
        errors.append(f"{where}: `note` must be a string or omitted")
        ok = False
    if not ok:
        return None
    return Command(target=target, mutate=mutate, reverse=reverse, note=note)
