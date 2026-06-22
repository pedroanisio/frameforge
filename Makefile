# FrameGraph v2 — developer entrypoints (uv-based). Run `make` (or `make help`).
#
# Dependency + venv management is owned by pyproject.toml + uv.lock (uv is the
# source of truth). These targets only wrap the project's build/check commands so
# nobody has to remember the individual invocations. `make check` is exactly what
# CI runs (.github/workflows/ci.yml).

UV ?= uv
FIXTURES_YAML := fixtures/*.fg.yaml

.DEFAULT_GOAL := help
.PHONY: help sync schema render pdf check schema-check test validate overflow status status-check docs docs-serve docs-check lint clean viewer-build viewer-test

help:  ## list targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-13s\033[0m %s\n",$$1,$$2}'

sync:  ## create/refresh the venv from uv.lock
	$(UV) sync

schema:  ## regenerate schema/framegraph-v2.schema.json from the models
	$(UV) run python schema/build_schema.py

render:  ## render every fixture to out/render/ (+ contact sheet)
	$(UV) run python tooling/render_fixtures.py --all

pdf:  ## transpile a PDF -> FrameGraph YAML (pulls the `pdf` group): make pdf PDF=paper.pdf [OUT=...] [ARGS='--text-mode spans']
	@test -n "$(PDF)" || { echo "usage: make pdf PDF=<input.pdf> [OUT=<out.fg.yaml>] [ARGS='--text-mode spans']"; exit 2; }
	$(UV) run --group pdf python tooling/pdf_to_framegraph_yml.py "$(PDF)" "$(if $(OUT),$(OUT),$(PDF:.pdf=.fg.yaml))" $(ARGS)

check: schema-check test validate overflow status-check docs-check  ## run every local gate

schema-check:  ## fail if the committed schema drifted from the models
	$(UV) run python schema/build_schema.py --check

test:  ## HEAD assertion suite
	$(UV) run pytest -q

validate:  ## structurally validate the curated (passing) fixtures
	$(UV) run python tooling/validate.py $(FIXTURES_YAML)

overflow:  ## assert no text overflows its box (SVG proxy)
	$(UV) run python tooling/render_fixtures.py --all --check-overflow

status:  ## regenerate FIXTURE-STATUS.md from the validator
	$(UV) run python tooling/gen_status.py

status-check:  ## fail if FIXTURE-STATUS.md drifted from the validator
	$(UV) run python tooling/gen_status.py --check

docs:  ## generate pages + build the static site into site/ (theme fetched ephemerally)
	$(UV) run python tooling/gen_docs.py
	$(UV) run --with mkdocs-material mkdocs build --strict

docs-serve:  ## generate pages + serve with live reload (http://127.0.0.1:8000)
	$(UV) run python tooling/gen_docs.py
	$(UV) run --with mkdocs-material mkdocs serve

docs-check:  ## generate pages + assert every mkdocs.yml nav page exists (no full build)
	$(UV) run python tooling/gen_docs.py --check

lint:  ## ruff (non-gating; fetched ephemerally)
	-$(UV)x ruff check .

clean:  ## remove generated output + caches
	rm -rf out site docs/assets .ruff_cache .pytest_cache
	rm -f docs/reference.md docs/grammar.md docs/spec.md docs/fixtures.md docs/changelog.md
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

viewer-build:  ## build the JS viewer bundle
	npm --prefix viewer ci && npm --prefix viewer run build

viewer-test:  ## viewer node coverage check
	npm --prefix viewer test
