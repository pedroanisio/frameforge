"""recipe.sign — a provenance signature for a recipe run.

The signature binds four things so a report can be traced back to its source:

* the **input** — a content digest (sha256) of the canonicalised recipe;
* the **computed result** — a fingerprint of the apply order + summary metrics;
* the **tool** — name and version;
* the **run** — an optional UTC timestamp.

It is a tamper-evident *fingerprint*, not a keyed cryptographic signature: the
same recipe always yields the same digest, so two reports of the same plan are
comparable and a changed plan is detectable. (Swap ``_sha`` for an HMAC if a
keyed signature is ever needed.)
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from recipe.analysis import BookAnalysis, RecipeAnalysis, analyze, analyze_book
from recipe.model import Recipe, RecipeBook


def canonical_bytes(obj: Recipe | RecipeBook) -> bytes:
    """Deterministic JSON encoding of a recipe or book (stable key order,
    semantic list order preserved)."""
    return json.dumps(
        dataclasses.asdict(obj), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha(data: bytes, length: int = 16) -> str:
    return hashlib.sha256(data).hexdigest()[:length]


def recipe_digest(recipe: Recipe, length: int = 16) -> str:
    """Short sha256 of the recipe's canonical content."""
    return _sha(canonical_bytes(recipe), length)


def book_digest(book: RecipeBook, length: int = 16) -> str:
    """Short sha256 of the whole book's canonical content."""
    return _sha(canonical_bytes(book), length)


@dataclass(frozen=True)
class RunSignature:
    tool: str
    version: str
    digest: str                  # short sha256 of the canonical recipe (the input)
    steps: int
    commands: int
    reversible_pct: float
    order_fingerprint: str       # short sha256 of the computed apply order
    generated_at: str | None     # ISO-8601 UTC, or None in deterministic mode
    recipes: int | None = None   # set for a book; None for a single recipe

    def line(self) -> str:
        """One-line Markdown signature footer."""
        scope = "book" if self.recipes is not None else "recipe"
        bits = [
            f"`{self.tool} {self.version}`",
            f"{scope} `sha256:{self.digest}`",
        ]
        if self.recipes is not None:
            bits.append(f"{self.recipes} recipes")
        bits += [
            f"{self.steps} steps",
            f"{self.commands} commands",
            f"{self.reversible_pct:.0f}% reversible",
            f"order `{self.order_fingerprint}`",
        ]
        if self.generated_at:
            bits.append(f"generated {self.generated_at}")
        return "> **Run signature** · " + " · ".join(bits)

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def sign(recipe: Recipe, *, analysis: RecipeAnalysis | None = None,
         generated_at: datetime | str | None = None,
         tool: str = "recipe", version: str = "") -> RunSignature:
    """Compute the run signature. ``generated_at`` is omitted (deterministic)
    unless given; the CLI passes the real UTC time of the run."""
    a = analysis or analyze(recipe)
    if not version:
        from recipe import __version__
        version = __version__
    return RunSignature(
        tool=tool,
        version=version,
        digest=recipe_digest(recipe),
        steps=len(recipe.steps),
        commands=a.total_commands,
        reversible_pct=a.reversibility_pct,
        order_fingerprint=_sha("\n".join(a.apply_order).encode("utf-8"), 8),
        generated_at=_iso(generated_at),
    )


def sign_book(book: RecipeBook, *, analysis: BookAnalysis | None = None,
              generated_at: datetime | str | None = None,
              tool: str = "recipe", version: str = "") -> RunSignature:
    """Compute the run signature for a whole book (digest over all recipes,
    fingerprint over the recipe apply order, totals across recipes)."""
    a = analysis or analyze_book(book)
    if not version:
        from recipe import __version__
        version = __version__
    return RunSignature(
        tool=tool,
        version=version,
        digest=book_digest(book),
        steps=a.total_steps,
        commands=a.total_commands,
        reversible_pct=a.reversibility_pct,
        order_fingerprint=_sha("\n".join(a.apply_order).encode("utf-8"), 8),
        generated_at=_iso(generated_at),
        recipes=len(book.recipes),
    )


def _iso(value: datetime | str | None) -> str | None:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise TypeError(f"generated_at must be datetime|str|None, got {type(value).__name__}")
