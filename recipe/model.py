"""recipe.model — the data structure for a reversible change recipe.

A *recipe* describes how to move a system from an as-is state to a desired
to-be state as a set of **linked, individually reversible steps**. It is plain
data (load it from YAML/JSON), validated by :mod:`recipe.parse`, analysed by
:mod:`recipe.analysis`, and rendered by :mod:`recipe.report`. No third-party
dependency: the model is stdlib dataclasses so it travels anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Command:
    """One state-changing command, scoped to a file/folder, with its inverse.

    ``mutate`` is the forward command; ``reverse`` undoes it. ``reverse is None``
    (or blank) marks the command as *irreversible* — a one-way door surfaced
    loudly by the reversibility audit.
    """

    target: str                    # the file or folder this command acts on
    mutate: str                    # forward, state-changing command
    reverse: str | None = None     # command that reverses ``mutate`` (None = irreversible)
    note: str | None = None

    @property
    def reversible(self) -> bool:
        return bool(self.reverse and self.reverse.strip())


@dataclass
class Step:
    """One as-is → to-be transition: a bundle of commands plus its links.

    ``depends_on`` lists the ids of steps that must complete first (this is the
    "mapping … linked" relation). ``independent`` is the author's *declared*
    claim that the step can run standalone / in parallel; the analyser checks it.
    """

    id: str
    goal: str = ""                                       # what this step achieves
    as_is: str = ""                                      # state before this step
    to_be: str = ""                                      # state after this step
    commands: list[Command] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)  # ids that must precede this
    independent: bool = False                            # declared parallel-safe

    @property
    def reversible(self) -> bool:
        return all(c.reversible for c in self.commands)

    @property
    def targets(self) -> list[str]:
        """Distinct file/folder targets this step touches, in first-seen order."""
        seen: dict[str, None] = {}
        for c in self.commands:
            seen.setdefault(c.target, None)
        return list(seen)


@dataclass
class Recipe:
    """A complete reversible plan: goal, preconditions, desired state, steps.

    ``id`` names the recipe so other recipes can depend on it; ``depends_on``
    lists the ids of recipes that must complete first (the recipe-level analogue
    of :attr:`Step.depends_on`). Both are optional for a standalone recipe and
    required/resolved when the recipe lives in a :class:`RecipeBook`.
    """

    goal: str
    preconditions: list[str] = field(default_factory=list)   # assumed pre-conditions
    desired_state: str = ""                                   # overall to-be state
    steps: list[Step] = field(default_factory=list)
    id: str = ""                                              # recipe identifier
    depends_on: list[str] = field(default_factory=list)      # ids of recipes that must precede

    def step(self, step_id: str) -> Step | None:
        return next((s for s in self.steps if s.id == step_id), None)

    @property
    def ids(self) -> list[str]:
        return [s.id for s in self.steps]

    @property
    def targets(self) -> list[str]:
        """Distinct file/folder targets this recipe touches, across all steps."""
        seen: dict[str, None] = {}
        for s in self.steps:
            for t in s.targets:
                seen.setdefault(t, None)
        return list(seen)


@dataclass
class RecipeBook:
    """An ordered collection of recipes linked by recipe-level ``depends_on``."""

    recipes: list[Recipe] = field(default_factory=list)

    def recipe(self, recipe_id: str) -> Recipe | None:
        return next((r for r in self.recipes if r.id == recipe_id), None)

    @property
    def ids(self) -> list[str]:
        return [r.id for r in self.recipes]
