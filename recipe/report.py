"""recipe.report — render a Recipe (+ analysis) into a report.

Modular by design: :func:`render` dispatches on a format name, and a new
reporter is just a class with a ``render() -> str`` method registered below.
Ships one reporter (Markdown); add HTML/JSON/etc. without touching the model.
"""
from __future__ import annotations

from datetime import datetime

from recipe.analysis import BookAnalysis, RecipeAnalysis, analyze, analyze_book
from recipe.model import Recipe, RecipeBook
from recipe.sign import RunSignature, sign, sign_book


def render(recipe: Recipe, fmt: str = "md", *, analysis: RecipeAnalysis | None = None,
           frontmatter: bool = False, signature: bool = True,
           generated_at: datetime | str | None = None) -> str:
    """Render ``recipe`` to ``fmt`` (default ``md``). Reuses ``analysis`` if given.

    A run signature (recipe digest + order fingerprint + metrics) is appended by
    default; ``generated_at`` adds the run timestamp (omitted → deterministic
    output). Pass ``signature=False`` to suppress it."""
    analysis = analysis or analyze(recipe)
    reporter = _REPORTERS.get(fmt)
    if reporter is None:
        raise ValueError(f"unknown report format {fmt!r}; have: {', '.join(sorted(_REPORTERS))}")
    sig = sign(recipe, analysis=analysis, generated_at=generated_at) if signature else None
    return reporter(recipe, analysis, frontmatter=frontmatter, signature=sig).render()


class MarkdownReporter:
    """Render the recipe as a Markdown report: goal → preconditions → desired
    state → as-is/to-be mapping → per-step commands by target → analysis →
    run signature."""

    def __init__(self, recipe: Recipe, analysis: RecipeAnalysis, *,
                 frontmatter: bool = False, signature: RunSignature | None = None,
                 level: int = 1):
        self.r = recipe
        self.a = analysis
        self.frontmatter = frontmatter
        self.signature = signature
        self.level = level

    def render(self) -> str:
        h1, h2, h3 = ("#" * (self.level + n) + " " for n in (0, 1, 2))
        out: list[str] = []
        if self.frontmatter:
            out += [
                "---",
                "disclaimer: >-",
                "  Generated from a recipe data structure. Verify every command "
                "and its reverse before running anything.",
                'generated_by: "recipe.report (MarkdownReporter)"',
                "---",
                "",
            ]
        r, a = self.r, self.a

        name = f"Recipe `{r.id}`" if r.id else "Recipe"
        out += [f"{h1}{name} — {r.goal}", ""]

        out += [f"{h2}Assumed pre-conditions", ""]
        out += [f"- {p}" for p in r.preconditions] or ["- _(none stated)_"]
        out += [""]

        out += [f"{h2}Desired state", "", r.desired_state or "_(not stated)_", ""]

        out += [f"{h2}As-is → to-be mapping (in apply order)", "",
                "| # | Step | As-is → To-be | Independent | Depends on |",
                "|---|------|---------------|:-----------:|------------|"]
        for i, sid in enumerate(a.apply_order, 1):
            s = r.step(sid)
            assert s is not None
            ind = "✅" if s.independent else "—"
            dep = ", ".join(f"`{d}`" for d in s.depends_on) or "—"
            out.append(f"| {i} | `{s.id}` — {s.goal} | {_cell(s.as_is)} → {_cell(s.to_be)} | {ind} | {dep} |")
        out += [""]

        out += [f"{h2}Steps — mutating commands and their reverse (by target)"]
        for sid in a.apply_order:
            s = r.step(sid)
            assert s is not None
            out += ["", f"{h3}`{s.id}` — {s.goal}"]
            if s.commands:
                out += ["", "| Target (file/folder) | Mutate | Reverse |",
                        "|----------------------|--------|---------|"]
                for c in s.commands:
                    rev = f"`{c.reverse}`" if c.reversible else "⚠ **irreversible**"
                    out.append(f"| `{c.target}` | `{c.mutate}` | {rev} |")
            else:
                out += ["", "_(no commands)_"]
        out += [""]

        out += [f"{h2}Analysis", "",
                f"- **Apply order (roll-forward):** {_chain(a.apply_order)}",
                f"- **Rollback order (roll-back):** {_chain(a.rollback_order)}",
                f"- **Independently runnable (parallelisable):** "
                f"{', '.join(f'`{x}`' for x in a.parallelizable) or '_none_'}",
                f"- **Reversibility:** {a.reversible_commands}/{a.total_commands} commands "
                f"reversible ({a.reversibility_pct:.0f}%)", ""]

        if a.discrepancies:
            out += [f"{h3}⚠ Independence-flag discrepancies", ""]
            for f in a.discrepancies:
                detail = f" ({'; '.join(f.reasons)})" if f.reasons else ""
                out.append(f"- `{f.step_id}`: {f.discrepancy}{detail}")
            out += [""]

        if a.couplings:
            out += [f"{h3}Shared targets (steps coupled by file/folder)", ""]
            for c in a.couplings:
                out.append(f"- `{c.target}` — touched by {', '.join(f'`{x}`' for x in c.step_ids)}")
            out += [""]

        if a.irreversible:
            out += [f"{h3}⚠ Irreversible commands (block a clean rollback)", ""]
            for sid, target, mutate in a.irreversible:
                out.append(f"- `{sid}` @ `{target}`: `{mutate}`")
            out += [""]

        if self.signature is not None:
            out += ["---", "", self.signature.line(), ""]

        return "\n".join(out).rstrip() + "\n"


def render_book(book: RecipeBook, fmt: str = "md", *, analysis: BookAnalysis | None = None,
                frontmatter: bool = False, signature: bool = True,
                generated_at: datetime | str | None = None) -> str:
    """Render a whole :class:`RecipeBook`: recipe dependency order, each recipe's
    report nested under it, and a book-level run signature."""
    analysis = analysis or analyze_book(book)
    reporter = _BOOK_REPORTERS.get(fmt)
    if reporter is None:
        raise ValueError(f"unknown report format {fmt!r}; have: {', '.join(sorted(_BOOK_REPORTERS))}")
    sig = sign_book(book, analysis=analysis, generated_at=generated_at) if signature else None
    return reporter(book, analysis, frontmatter=frontmatter, signature=sig).render()


class BookMarkdownReporter:
    """Render a book: dependency order + summary table, the recipe-level analysis,
    then each recipe's full report nested at heading level 2."""

    def __init__(self, book: RecipeBook, analysis: BookAnalysis, *,
                 frontmatter: bool = False, signature: RunSignature | None = None):
        self.b = book
        self.a = analysis
        self.frontmatter = frontmatter
        self.signature = signature

    def render(self) -> str:
        b, a = self.b, self.a
        out: list[str] = []
        if self.frontmatter:
            out += ["---", "disclaimer: >-",
                    "  Generated from a recipe book. Verify every command and its "
                    "reverse before running anything.",
                    'generated_by: "recipe.report (BookMarkdownReporter)"', "---", ""]

        out += ["# Recipe book", ""]
        out += ["## Recipe dependency order", "",
                "| # | Recipe | Goal | Depends on | Steps | Reversible |",
                "|---|--------|------|------------|------:|-----------:|"]
        for i, rid in enumerate(a.apply_order, 1):
            r = b.recipe(rid)
            assert r is not None
            dep = ", ".join(f"`{d}`" for d in r.depends_on) or "—"
            out.append(f"| {i} | `{rid}` | {r.goal} | {dep} | {len(r.steps)} "
                       f"| {a.recipes[rid].reversibility_pct:.0f}% |")
        out += [""]

        out += [f"- **Apply order (roll-forward):** {_chain(a.apply_order)}",
                f"- **Rollback order (roll-back):** {_chain(a.rollback_order)}",
                f"- **Independent recipes (parallelisable):** "
                f"{', '.join(f'`{x}`' for x in a.parallelizable) or '_none_'}",
                f"- **Reversibility (whole book):** {a.reversible_commands}/{a.total_commands} "
                f"commands reversible ({a.reversibility_pct:.0f}%)", ""]

        if a.couplings:
            out += ["### Shared targets (recipes coupled by file/folder)", ""]
            for c in a.couplings:
                out.append(f"- `{c.target}` — touched by {', '.join(f'`{x}`' for x in c.step_ids)}")
            out += [""]

        for rid in a.apply_order:
            r = b.recipe(rid)
            assert r is not None
            out += ["---", ""]
            out.append(MarkdownReporter(r, a.recipes[rid], level=2, signature=None).render().rstrip())
            out += [""]

        if self.signature is not None:
            out += ["---", "", self.signature.line(), ""]

        return "\n".join(out).rstrip() + "\n"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ") if text else "?"


def _chain(ids: list[str]) -> str:
    return " → ".join(f"`{x}`" for x in ids) or "_empty_"


_REPORTERS = {"md": MarkdownReporter, "markdown": MarkdownReporter}
_BOOK_REPORTERS = {"md": BookMarkdownReporter, "markdown": BookMarkdownReporter}
