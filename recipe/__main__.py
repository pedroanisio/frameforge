"""python -m recipe <file> — parse, validate, analyse, and report a recipe.

    python -m recipe recipe/examples/packaging.yaml
    python -m recipe plan.json --frontmatter > plan-report.md

Exit status: 0 = valid (report on stdout); 1 = invalid (issues on stderr);
2 = usage error (argparse).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from recipe.model import RecipeBook
from recipe.parse import RecipeError, load_any
from recipe.report import render, render_book
from recipe.sign import book_digest, recipe_digest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="recipe",
        description="Parse and report reversible change recipes "
                    "(goal → preconditions → desired state → linked reversible steps). "
                    "Pass several files, or one file holding a `recipes:` list, to "
                    "report a book of recipes linked by recipe-level depends_on.",
    )
    ap.add_argument("file", nargs="+",
                    help="recipe/book file(s) (.yaml / .yml / .json)")
    ap.add_argument("--format", default="md", help="report format (default: md)")
    ap.add_argument("--frontmatter", action="store_true",
                    help="emit YAML frontmatter at the top of the report")
    ap.add_argument("--no-signature", action="store_true",
                    help="omit the run-signature footer")
    ap.add_argument("--digest", action="store_true",
                    help="print only the content digest and exit")
    args = ap.parse_args(argv)

    try:
        obj = load_any(args.file)
    except FileNotFoundError as exc:
        print(f"recipe: no such file: {exc.filename}", file=sys.stderr)
        return 1
    except RecipeError as exc:
        print(f"recipe: {exc}", file=sys.stderr)
        return 1

    is_book = isinstance(obj, RecipeBook)

    if args.digest:
        print(f"sha256:{book_digest(obj) if is_book else recipe_digest(obj)}")
        return 0

    try:
        renderer = render_book if is_book else render
        print(renderer(
            obj, args.format,
            frontmatter=args.frontmatter,
            signature=not args.no_signature,
            generated_at=datetime.now(timezone.utc),   # stamp the actual run
        ))
    except ValueError as exc:
        print(f"recipe: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
