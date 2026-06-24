"""recipe — a modular, dependency-free parser and reporter for reversible
change recipes.

A recipe is plain data: a **goal**, **assumed pre-conditions**, a **desired
state**, and a **mapping** of as-is → to-be **steps**. Each step is *linked*
(``depends_on``), carries **mutating commands paired with their reverse, by
file/folder target**, and a **flag for whether it is independent**.

    from recipe import load, analyze, render
    plan = load("recipe/examples/packaging.yaml")
    print(render(plan))            # Markdown report (mapping + reversal + analysis)

The four stages are separable (parse → model → analyse → report), so each can be
swapped or reused on its own.
"""
__version__ = "0.1.0"

from recipe.analysis import (
    BookAnalysis,
    Coupling,
    IndependenceFinding,
    RecipeAnalysis,
    analyze,
    analyze_book,
)
from recipe.model import Command, Recipe, RecipeBook, Step
from recipe.parse import (
    RecipeError,
    load,
    load_any,
    load_book,
    load_many,
    parse,
    parse_book,
)
from recipe.report import render, render_book
from recipe.sign import RunSignature, book_digest, recipe_digest, sign, sign_book

__all__ = [
    "__version__",
    # model
    "Command",
    "Step",
    "Recipe",
    "RecipeBook",
    # parse
    "RecipeError",
    "load",
    "parse",
    "load_book",
    "parse_book",
    "load_many",
    "load_any",
    # analysis
    "analyze",
    "analyze_book",
    "Coupling",
    "IndependenceFinding",
    "RecipeAnalysis",
    "BookAnalysis",
    # report
    "render",
    "render_book",
    # sign
    "sign",
    "sign_book",
    "RunSignature",
    "recipe_digest",
    "book_digest",
]
