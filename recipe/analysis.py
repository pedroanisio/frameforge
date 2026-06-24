"""recipe.analysis — derive execution order, independence, and reversibility.

Pure functions over a validated :class:`~recipe.model.Recipe`; no I/O. The
analyser answers the three questions a reversible plan must answer:

* **order** — apply (roll-forward) and rollback (roll-back) sequences from the
  ``depends_on`` links;
* **independence** — which steps are *structurally* isolated (declared vs. real,
  including implicit coupling through a shared file/folder target);
* **reversibility** — which commands can be undone and which are one-way doors.
"""
from __future__ import annotations

from dataclasses import dataclass

from recipe.graph import topo_order
from recipe.model import Recipe, RecipeBook


@dataclass
class Coupling:
    """A file/folder touched by more than one step (implicit coupling)."""

    target: str
    step_ids: list[str]


@dataclass
class IndependenceFinding:
    step_id: str
    declared: bool                 # the step's `independent` flag
    structural: bool               # truly isolated (no deps, no dependents, no shared target)
    reasons: list[str]             # why `structural` is False

    @property
    def discrepancy(self) -> str | None:
        if self.declared and not self.structural:
            return "over-claimed: declared independent but coupled"
        if self.structural and not self.declared:
            return "under-claimed: could be parallelised"
        return None


@dataclass
class RecipeAnalysis:
    apply_order: list[str]                       # roll-forward (dependencies first)
    rollback_order: list[str]                    # roll-back (reverse of apply)
    couplings: list[Coupling]                    # targets touched by >1 step
    independence: list[IndependenceFinding]
    irreversible: list[tuple[str, str, str]]     # (step_id, target, mutate)
    total_commands: int
    reversible_commands: int

    @property
    def reversibility_pct(self) -> float:
        if self.total_commands == 0:
            return 100.0
        return 100.0 * self.reversible_commands / self.total_commands

    @property
    def parallelizable(self) -> list[str]:
        return [f.step_id for f in self.independence if f.structural]

    @property
    def discrepancies(self) -> list[IndependenceFinding]:
        return [f for f in self.independence if f.discrepancy]


def analyze(recipe: Recipe) -> RecipeAnalysis:
    order = _topo_order(recipe)
    couplings = _couplings(recipe)
    coupled_ids = {sid for c in couplings for sid in c.step_ids}

    dependents: dict[str, list[str]] = {s.id: [] for s in recipe.steps}
    for s in recipe.steps:
        for dep in s.depends_on:
            if dep in dependents:
                dependents[dep].append(s.id)

    independence: list[IndependenceFinding] = []
    for s in recipe.steps:
        reasons: list[str] = []
        if s.depends_on:
            reasons.append(f"depends on {s.depends_on}")
        if dependents[s.id]:
            reasons.append(f"required by {dependents[s.id]}")
        if s.id in coupled_ids:
            shared = sorted({c.target for c in couplings if s.id in c.step_ids})
            reasons.append(f"shares target(s) {shared}")
        independence.append(IndependenceFinding(s.id, s.independent, not reasons, reasons))

    irreversible = [(s.id, c.target, c.mutate)
                    for s in recipe.steps for c in s.commands if not c.reversible]
    total = sum(len(s.commands) for s in recipe.steps)

    return RecipeAnalysis(
        apply_order=order,
        rollback_order=list(reversed(order)),
        couplings=couplings,
        independence=independence,
        irreversible=irreversible,
        total_commands=total,
        reversible_commands=total - len(irreversible),
    )


def _couplings(recipe: Recipe) -> list[Coupling]:
    return _couplings_by_target((s.id, s.targets) for s in recipe.steps)


def _topo_order(recipe: Recipe) -> list[str]:
    return topo_order(recipe.ids, {s.id: s.depends_on for s in recipe.steps})


# --------------------------------------------------------------------------- #
#  Book-level analysis (recipes linked by recipe-level depends_on)
# --------------------------------------------------------------------------- #
@dataclass
class BookAnalysis:
    apply_order: list[str]                       # recipe ids, dependencies first
    rollback_order: list[str]                    # reverse of apply
    couplings: list[Coupling]                    # file/folder touched by >1 recipe
    parallelizable: list[str]                    # recipe ids with no deps/dependents/shared target
    recipes: dict[str, RecipeAnalysis]           # per-recipe analysis, keyed by id
    total_steps: int
    total_commands: int
    reversible_commands: int

    @property
    def reversibility_pct(self) -> float:
        if self.total_commands == 0:
            return 100.0
        return 100.0 * self.reversible_commands / self.total_commands


def analyze_book(book: RecipeBook) -> BookAnalysis:
    order = topo_order(book.ids, {r.id: r.depends_on for r in book.recipes})
    couplings = _couplings_by_target((r.id, r.targets) for r in book.recipes)
    coupled = {rid for c in couplings for rid in c.step_ids}

    dependents: dict[str, list[str]] = {r.id: [] for r in book.recipes}
    for r in book.recipes:
        for dep in r.depends_on:
            if dep in dependents:
                dependents[dep].append(r.id)

    parallelizable = [r.id for r in book.recipes
                      if not r.depends_on and not dependents[r.id] and r.id not in coupled]

    per = {r.id: analyze(r) for r in book.recipes}
    total_commands = sum(a.total_commands for a in per.values())
    reversible = sum(a.reversible_commands for a in per.values())

    return BookAnalysis(
        apply_order=order,
        rollback_order=list(reversed(order)),
        couplings=couplings,
        parallelizable=parallelizable,
        recipes=per,
        total_steps=sum(len(r.steps) for r in book.recipes),
        total_commands=total_commands,
        reversible_commands=reversible,
    )


def _couplings_by_target(owned_targets) -> list[Coupling]:
    """Group (owner_id, [targets]) pairs by shared target. ``Coupling.step_ids``
    holds step ids at recipe level and recipe ids at book level."""
    by_target: dict[str, list[str]] = {}
    for owner, targets in owned_targets:
        for t in targets:
            ids = by_target.setdefault(t, [])
            if owner not in ids:
                ids.append(owner)
    return [Coupling(t, ids) for t, ids in by_target.items() if len(ids) > 1]
