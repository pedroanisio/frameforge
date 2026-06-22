# FrameGraph v2 — developer entrypoints (uv-based). Run `make` (or `make help`).
#
# Dependency + venv management is owned by pyproject.toml + uv.lock (uv is the
# source of truth). These targets only wrap the project's build/check commands so
# nobody has to remember the individual invocations. `make check` is exactly what
# CI runs (.github/workflows/ci.yml).

UV ?= uv
FIXTURES_YAML := fixtures/*.fg.yaml

.DEFAULT_GOAL := help
.PHONY: help sync schema render check schema-check test validate overflow status status-check lint clean viewer-build viewer-test

help:  ## list targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-13s\033[0m %s\n",$$1,$$2}'

sync:  ## create/refresh the venv from uv.lock
	$(UV) sync

schema:  ## regenerate schema/framegraph-v2.schema.json from the models
	$(UV) run python schema/build_schema.py

render:  ## render every fixture to out/render/ (+ contact sheet)
	$(UV) run python tooling/render_fixtures.py --all

check: schema-check test validate overflow status-check  ## run every gate (what CI enforces)

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

lint:  ## ruff (non-gating; fetched ephemerally)
	-$(UV)x ruff check .

clean:  ## remove generated output + caches
	rm -rf out .ruff_cache .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

viewer-build:  ## build the JS viewer bundle
	npm --prefix viewer ci && npm --prefix viewer run build

viewer-test:  ## viewer node coverage check
	npm --prefix viewer test
