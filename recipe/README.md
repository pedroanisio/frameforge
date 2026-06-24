---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
  generated_by: "Claude Opus 4.8 via Claude Code"
  date: "2026-06-24"
---

# `recipe` — a reversible-change recipe parser & reporter

A small, **dependency-free** (stdlib only) Python package that takes a *recipe*
data structure and renders a report. A recipe describes how to move a system
from an **as-is** state to a **desired** state as a set of **linked, individually
reversible steps**.

It answers the questions a migration plan must answer: *in what order do I apply
this, how do I roll it back, which steps are truly independent, and which
commands are one-way doors?*

## The data structure

```yaml
id:             <string>            # recipe id — needed only if other recipes depend on it
depends_on:     [<id>, ...]         # recipe-level links: ids of recipes that must run first
goal:           <string>            # what the whole recipe achieves
preconditions:  [<string>, ...]     # assumed pre-conditions (must hold before step 1)
desired_state:  <string>            # the overall to-be state
steps:                              # the as-is → to-be mapping
  - id:          <string>           # unique
    goal:        <string>
    as_is:       <string>           # state this step starts from
    to_be:       <string>           # state after this step
    depends_on:  [<id>, ...]        # links: steps that must complete first
    independent: <bool>             # declared: can run standalone / in parallel
    commands:                       # mutations, each paired with its reverse, by target
      - target:  <file-or-folder>   # what the command acts on
        mutate:  <string>           # the forward, state-changing command
        reverse: <string>           # the command that undoes it (omit = irreversible)
```

Every field maps to one part of the brief: **goal**, **assumed pre-conditions**,
**desired state**, the **as-is→to-be mapping** *linked* by `depends_on`, the
**mutating commands each with a reverse, by file/folder** (`target`), and the
**independent flag**.

## Use it

```bash
python -m recipe recipe/examples/packaging.yaml          # Markdown report → stdout
python -m recipe plan.json --frontmatter > report.md     # with YAML frontmatter
python -m recipe recipe/examples/book.yaml               # a book (recipes with deps)
python -m recipe a.yaml b.yaml c.yaml                    # several files → one book
```

```python
from recipe import load, parse, analyze, render

plan = load("plan.yaml")          # parse + validate a file (.yaml/.yml/.json)
plan = parse(some_dict)           # …or validate a data structure directly
a    = analyze(plan)              # apply/rollback order, independence, reversibility
print(render(plan, analysis=a))   # Markdown report
```

## What you get

The four stages are **separable and reusable** — swap any one:

| Stage | Module | Output |
|---|---|---|
| Parse / validate | `recipe.parse` | typed `Recipe`, or `RecipeError` listing **every** problem |
| Model | `recipe.model` | `Recipe` / `Step` / `Command` dataclasses |
| Analyse | `recipe.analysis` | apply & rollback order, parallelisable steps, reversibility %, shared-target couplings, independence-flag discrepancies |
| Report | `recipe.report` | a Markdown report (add a reporter by registering a class) |

### Checks the analyser performs

- **Apply order** (roll-forward) and **rollback order** (roll-back), topologically from `depends_on`.
- **Independence reconciliation** — flags a step that *declares* `independent` but is coupled (shares a `target` with, or is required by, another step), or one that *could* be parallelised but isn't declared.
- **Reversibility audit** — every command without a `reverse` is reported as a one-way door that blocks a clean rollback.
- **Validation** — collects all errors at once: missing `goal`, duplicate/dangling/self/cyclic `depends_on`, `independent` contradicting `depends_on`, malformed commands.

## Recipe books — recipe-level dependencies

A **book** is a collection of recipes linked by recipe-level `depends_on`, where
**one recipe may depend on a previous one** (the higher-level analogue of step
links). Put a `recipes:` list in one file, or pass several single-recipe files:

```python
from recipe import load_book, analyze_book, render_book
book = load_book("recipe/examples/book.yaml")   # or load_many(["a.yaml", "b.yaml"])
print(render_book(book))                          # ordered report + per-recipe sections
```

Within a book every recipe needs a unique `id`; `depends_on` must reference
existing recipes and form no cycle (all validated together). `analyze_book`
computes the **recipe** apply/rollback order, which recipes are independent, and
the reversibility across the whole book; the report nests each recipe under the
dependency order. See [`examples/book.yaml`](examples/book.yaml).

### Run signature

Every report ends with a **run signature** that makes it traceable and
tamper-evident — it binds the input, the computed plan, the tool, and the run:

```
> **Run signature** · `recipe 0.1.0` · recipe `sha256:…` · 5 steps · 7 commands · 100% reversible · order `…` · generated 2026-06-24T14:21:43Z
```

(A book signature reads `book sha256:… · 2 recipes · …` instead.)

- `recipe sha256:…` / `book sha256:…` — content digest (same input → same digest; a changed plan is detectable). Get it alone with `python -m recipe plan.yaml --digest`.
- `order …` — fingerprint of the computed apply order.
- `generated …` — the run timestamp (added by the CLI; **omitted** for `render()` calls so library output stays reproducible — pass `generated_at=` to include it).
- Suppress the footer with `--no-signature` (CLI) or `render(..., signature=False)`.

It is a fingerprint, not a keyed signature; swap the digest for an HMAC if you need a secret-keyed one.

## Tests

```bash
pytest recipe/tests                 # 29 tests
python recipe/tests/test_recipe.py  # or standalone
```

See [`examples/packaging.yaml`](examples/packaging.yaml) for a worked recipe
(the FrameGraph "installable package" migration, encoded as reversible steps).

---

← Back to the [project README](../README.md).
