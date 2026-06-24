"""Tests for the `recipe` package: parse/validate, analyse, report.

Runnable under pytest (``pytest recipe/tests``) or standalone
(``python recipe/tests/test_recipe.py``). Bumps the repo root onto sys.path so
``import recipe`` resolves when run either way.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest  # noqa: E402

from datetime import datetime, timezone  # noqa: E402

from recipe import (  # noqa: E402
    RecipeError,
    analyze,
    analyze_book,
    book_digest,
    load,
    load_book,
    parse,
    parse_book,
    recipe_digest,
    render,
    render_book,
    sign,
    sign_book,
)

EXAMPLE = os.path.join(_ROOT, "recipe", "examples", "packaging.yaml")
BOOK = os.path.join(_ROOT, "recipe", "examples", "book.yaml")


def _min(**over):
    """A minimal valid recipe dict, overridable per test."""
    data = {
        "goal": "g",
        "preconditions": ["p1"],
        "desired_state": "done",
        "steps": [
            {"id": "a", "goal": "first", "as_is": "x", "to_be": "y",
             "commands": [{"target": "f", "mutate": "do", "reverse": "undo"}]},
            {"id": "b", "goal": "second", "depends_on": ["a"],
             "commands": [{"target": "g", "mutate": "do2", "reverse": "undo2"}]},
        ],
    }
    data.update(over)
    return data


# ---- parse / validation -------------------------------------------------- #
def test_parse_minimal_ok():
    r = parse(_min())
    assert r.goal == "g" and r.ids == ["a", "b"]
    assert r.step("b").depends_on == ["a"]


def test_missing_goal_is_error():
    with pytest.raises(RecipeError) as ei:
        parse({"steps": []})
    assert any("goal" in e for e in ei.value.errors)


def test_duplicate_id_is_error():
    data = _min()
    data["steps"][1]["id"] = "a"
    with pytest.raises(RecipeError) as ei:
        parse(data)
    assert any("duplicate step id 'a'" in e for e in ei.value.errors)


def test_dangling_dependency_is_error():
    data = _min()
    data["steps"][1]["depends_on"] = ["nope"]
    with pytest.raises(RecipeError) as ei:
        parse(data)
    assert any("unknown step 'nope'" in e for e in ei.value.errors)


def test_self_dependency_is_error():
    data = _min()
    data["steps"][0]["depends_on"] = ["a"]
    with pytest.raises(RecipeError) as ei:
        parse(data)
    assert any("lists itself" in e for e in ei.value.errors)


def test_cycle_is_error():
    data = _min()
    data["steps"][0]["depends_on"] = ["b"]  # a<->b
    with pytest.raises(RecipeError) as ei:
        parse(data)
    assert any("cycle" in e for e in ei.value.errors)


def test_independent_with_depends_on_is_error():
    data = _min()
    data["steps"][1]["independent"] = True  # b depends on a -> contradiction
    with pytest.raises(RecipeError) as ei:
        parse(data)
    assert any("independent but declares depends_on" in e for e in ei.value.errors)


def test_command_requires_target_and_mutate():
    data = _min()
    data["steps"][0]["commands"] = [{"reverse": "undo"}]
    with pytest.raises(RecipeError) as ei:
        parse(data)
    joined = " ".join(ei.value.errors)
    assert "`target`" in joined and "`mutate`" in joined


def test_all_errors_collected_not_just_first():
    with pytest.raises(RecipeError) as ei:
        parse({"steps": [{"id": "a"}, {"id": "a"}]})  # no goal + dup id
    assert len(ei.value.errors) >= 2


# ---- analysis ------------------------------------------------------------ #
def test_apply_and_rollback_order_respect_dependencies():
    a = analyze(parse(_min()))
    assert a.apply_order == ["a", "b"]
    assert a.rollback_order == ["b", "a"]


def test_reversibility_full_and_partial():
    a = analyze(parse(_min()))
    assert a.total_commands == 2 and a.reversible_commands == 2
    assert a.reversibility_pct == 100.0

    data = _min()
    data["steps"][0]["commands"] = [{"target": "f", "mutate": "rm -rf x"}]  # no reverse
    a2 = analyze(parse(data))
    assert a2.reversible_commands == 1 and a2.reversibility_pct == 50.0
    assert a2.irreversible == [("a", "f", "rm -rf x")]


def test_structural_independence_and_under_claim():
    # a single isolated step, NOT declared independent -> under-claimed
    data = {"goal": "g", "steps": [
        {"id": "solo", "commands": [{"target": "f", "mutate": "do", "reverse": "undo"}]}
    ]}
    a = analyze(parse(data))
    assert a.parallelizable == ["solo"]
    disc = {f.step_id: f.discrepancy for f in a.discrepancies}
    assert "under-claimed" in disc["solo"]


def test_shared_target_coupling_and_over_claim():
    # two steps touch the same file; one wrongly claims independence -> over-claim
    data = {"goal": "g", "steps": [
        {"id": "x", "independent": True,
         "commands": [{"target": "same", "mutate": "a", "reverse": "ra"}]},
        {"id": "y",
         "commands": [{"target": "same", "mutate": "b", "reverse": "rb"}]},
    ]}
    a = analyze(parse(data))
    assert a.couplings and a.couplings[0].target == "same"
    assert set(a.couplings[0].step_ids) == {"x", "y"}
    over = [f for f in a.discrepancies if f.step_id == "x"]
    assert over and "over-claimed" in over[0].discrepancy


# ---- report -------------------------------------------------------------- #
def test_render_contains_all_sections():
    md = render(parse(_min()))
    for needle in ("## Assumed pre-conditions", "## Desired state",
                   "As-is → to-be mapping", "Reverse", "## Analysis",
                   "Reversibility", "roll-forward", "roll-back"):
        assert needle in md, f"missing {needle!r} in report"


def test_render_frontmatter_and_unknown_format():
    assert render(parse(_min()), frontmatter=True).startswith("---")
    with pytest.raises(ValueError):
        render(parse(_min()), fmt="pdf")


# ---- run signature ------------------------------------------------------- #
def test_digest_is_deterministic_and_content_sensitive():
    r1, r2 = parse(_min()), parse(_min())
    assert recipe_digest(r1) == recipe_digest(r2)          # same content → same digest
    changed = _min()
    changed["goal"] = "different"
    assert recipe_digest(parse(changed)) != recipe_digest(r1)


def test_signature_fields_and_fingerprint_stability():
    r = parse(_min())
    s1 = sign(r)
    assert s1.tool == "recipe" and s1.version
    assert s1.steps == 2 and s1.commands == 2 and s1.reversible_pct == 100.0
    assert s1.generated_at is None                          # deterministic by default
    assert sign(r).order_fingerprint == s1.order_fingerprint


def test_report_carries_signature_by_default_deterministically():
    r = parse(_min())
    md = render(r)
    assert "**Run signature**" in md and f"sha256:{recipe_digest(r)}" in md
    assert render(r) == md                                  # no timestamp → reproducible
    assert "**Run signature**" not in render(r, signature=False)


def test_signature_timestamp_is_included_when_supplied():
    r = parse(_min())
    when = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)
    md = render(r, generated_at=when)
    assert "generated 2026-06-24T12:00:00Z" in md


# ---- the worked example -------------------------------------------------- #
def test_packaging_example_parses_validates_and_renders():
    r = load(EXAMPLE)
    assert r.goal.startswith("Make FrameGraph")
    a = analyze(r)
    # the chain is correctly ordered: move-model first, packaging-metadata last-ish
    assert a.apply_order[0] == "move-model"
    assert a.apply_order.index("move-model") < a.apply_order.index("move-tooling")
    assert a.apply_order.index("move-tooling") < a.apply_order.index("packaging-metadata")
    # the doc-only step is genuinely independent
    assert "document-install" in a.parallelizable
    # every command in the proposal is reversible
    assert a.reversibility_pct == 100.0
    md = render(r)
    assert "move-model" in md and "git mv" in md


# ---- recipe-level dependencies (a book) ---------------------------------- #
def _book(**over):
    book = {"recipes": [
        {"id": "base", "goal": "first recipe",
         "steps": [{"id": "s", "commands": [{"target": "f", "mutate": "do", "reverse": "undo"}]}]},
        {"id": "next", "goal": "second recipe", "depends_on": ["base"],
         "steps": [{"id": "s", "commands": [{"target": "g", "mutate": "do2", "reverse": "undo2"}]}]},
    ]}
    book.update(over)
    return book


def test_parse_book_orders_recipes_by_dependency():
    b = parse_book(_book())
    assert b.ids == ["base", "next"]
    a = analyze_book(b)
    assert a.apply_order == ["base", "next"]
    assert a.rollback_order == ["next", "base"]
    # neither is parallelisable: base is required by next, next depends on base
    assert a.parallelizable == []


def test_book_requires_recipe_ids():
    data = _book()
    del data["recipes"][0]["id"]
    with pytest.raises(RecipeError) as ei:
        parse_book(data)
    assert any("`id` is required" in e for e in ei.value.errors)


def test_book_duplicate_recipe_id_is_error():
    data = _book()
    data["recipes"][1]["id"] = "base"
    with pytest.raises(RecipeError) as ei:
        parse_book(data)
    assert any("duplicate recipe id" in e for e in ei.value.errors)


def test_book_dangling_recipe_dependency_is_error():
    data = _book()
    data["recipes"][1]["depends_on"] = ["ghost"]
    with pytest.raises(RecipeError) as ei:
        parse_book(data)
    assert any("unknown recipe 'ghost'" in e for e in ei.value.errors)


def test_book_recipe_cycle_is_error():
    data = _book()
    data["recipes"][0]["depends_on"] = ["next"]  # base <-> next
    with pytest.raises(RecipeError) as ei:
        parse_book(data)
    assert any("recipe dependency cycle" in e for e in ei.value.errors)


def test_book_list_form_and_per_recipe_errors_prefixed():
    # top-level list form, and a malformed inner recipe is reported under its label
    with pytest.raises(RecipeError) as ei:
        parse_book([{"id": "ok", "goal": "g", "steps": []}, {"id": "bad"}])
    assert any("bad:" in e and "goal" in e for e in ei.value.errors)


def test_book_analysis_totals_and_reversibility():
    b = load_book(BOOK)
    a = analyze_book(b)
    assert a.apply_order == ["package", "publish"]      # publish depends on package
    assert a.total_steps == 4 and a.total_commands == 4
    # the `twine upload` command in `publish` has no reverse -> not 100%
    assert a.reversible_commands == 3
    assert a.reversibility_pct == 75.0


def test_render_book_and_signature():
    b = load_book(BOOK)
    md = render_book(b)
    assert "# Recipe book" in md
    assert "Recipe dependency order" in md
    assert "`package`" in md and "`publish`" in md
    assert "## Recipe `package`" in md          # recipes nested at level 2
    assert "**Run signature**" in md and "2 recipes" in md
    assert f"sha256:{book_digest(b)}" in md
    # deterministic without a timestamp
    assert render_book(b) == md


def test_sign_book_is_deterministic_and_distinct_from_recipe():
    b = parse_book(_book())
    s = sign_book(b)
    assert s.recipes == 2 and s.generated_at is None
    assert sign_book(b).digest == s.digest
    # a recipe digest and a book digest are different objects/spaces
    assert book_digest(b) != recipe_digest(b.recipes[0])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
