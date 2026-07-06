# FrameGraph v2 — developer entrypoints (uv-based). Run `make` (or `make help`).
#
# Dependency + venv management is owned by pyproject.toml + uv.lock (uv is the
# source of truth). These targets only wrap the project's build/check commands so
# nobody has to remember the individual invocations. `make check` is exactly what
# CI runs (.github/workflows/ci.yml).

UV ?= uv
FIXTURES_YAML := $(shell git ls-files tests/fixtures 2>/dev/null | grep -E '^tests/fixtures/[^/]+\.(fg\.yaml|framegraph\.yml)$$' || echo 'tests/fixtures/*.fg.yaml')
LIVE_HOST ?= 127.0.0.1
LIVE_PORT ?= 8789

.DEFAULT_GOAL := help
.PHONY: help sync schema bump bump-check release render render-latex pdf mcp live check schema-check grammar-check spec-check a11y-check ruff-check hooks golden golden-check test validate overflow status status-check docs docs-serve docs-check docs-sdk manifest manifest-check examples-index lint clean viewer-build viewer-test corpus corpus-check corpus-ui package-check docker-build docker-mcp docker-shell docker-fonts

DOCKER ?= docker
IMAGE ?= frameforge

help:  ## list targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-13s\033[0m %s\n",$$1,$$2}'

sync:  ## create/refresh the venv from uv.lock
	$(UV) sync

schema:  ## regenerate docs/schema/framegraph-v2.schema.json from the models
	$(UV) run python docs/schema/build_schema.py

bump:  ## bump the HEAD version at every site + regen derived artifacts (VERSION=X.Y.Z); see RELEASE.md
	@test -n "$(VERSION)" || { echo "usage: make bump VERSION=X.Y.Z"; exit 2; }
	$(UV) run python tooling/bump_version.py $(VERSION)
	$(MAKE) schema manifest examples-index
	@echo ""
	@echo "  bumped to $(VERSION). remaining (RELEASE.md): 1) CHANGELOG.md entry  2) make check  3) make docker-build"

bump-check:  ## assert every hand-edited version site agrees (no edit)
	$(UV) run python tooling/bump_version.py --check

release:  ## full release: bump VERSION, regenerate every derived artifact, run the gate (RELEASE.md §16-7)
	@test -n "$(VERSION)" || { echo "usage: make release VERSION=X.Y.Z"; exit 2; }
	$(UV) run python tooling/bump_version.py $(VERSION)
	$(MAKE) schema manifest docs-sdk status examples-index
	$(MAKE) check
	@echo ""
	@echo "  released $(VERSION): all sites bumped, artifacts regenerated, make check green."
	@echo "  remaining by hand (RELEASE.md): 1) CHANGELOG.md entry  2) git tag v$(VERSION)  3) make docker-build"

render:  ## render every fixture to out/render/ (+ contact sheet)
	$(UV) run python tooling/render_fixtures.py --all

render-latex:  ## render flow fixtures to LaTeX/TikZ + PDF via lualatex (out/latex/)
	$(UV) run python tooling/render_latex.py --all

pdf:  ## transpile a PDF -> FrameGraph YAML (pulls the `pdf` group): make pdf PDF=paper.pdf [OUT=...] [ARGS='--text-mode spans']
	@test -n "$(PDF)" || { echo "usage: make pdf PDF=<input.pdf> [OUT=<out.fg.yaml>] [ARGS='--text-mode spans']"; exit 2; }
	$(UV) run --group pdf python tooling/pdf_to_framegraph_yml.py "$(PDF)" "$(if $(OUT),$(OUT),$(PDF:.pdf=.fg.yaml))" $(ARGS)

mcp:  ## run the optional MCP server for SDK-code -> YAML -> render feedback loops
	PYTHONPATH=src:docs $(UV) run --group mcp python -m framegraph.mcp

live:  ## run the local FrameGraph MCP live-session web UI
	PYTHONPATH=src:docs $(UV) run python -m framegraph.live --host "$(LIVE_HOST)" --port "$(LIVE_PORT)"

check: schema-check grammar-check spec-check a11y-check status-check ruff-check test validate overflow golden-check docs-check docs-linkcheck disclaimer-check  ## run every local gate

ruff-check:  ## GATE the ruff rules the tree keeps clean (F811 redefinition; §16 row 1)
	$(UV)x ruff check --select F811 --output-format concise .

hooks:  ## install the git pre-commit / pre-push hooks (.pre-commit-config.yaml)
	$(UV)x pre-commit install --install-hooks

schema-check:  ## fail if the committed schema drifted from the models
	$(UV) run python docs/schema/build_schema.py --check

grammar-check:  ## fail if the EBNF grammar drifted from the models (core profile)
	$(UV) run python tooling/check_grammar_sync.py

spec-check:  ## fail if the spec prose drops a model type/flow/inline discriminator
	$(UV) run python tooling/check_spec_sync.py --quiet

a11y-check:  ## fail if a page reading_order is broken (a11y lint; warns on missing alt)
	$(UV) run python tooling/check_accessibility.py $(FIXTURES_YAML) --quiet

test:  ## HEAD assertion suite
	$(UV) run pytest -q

validate:  ## structurally validate the curated (passing) fixtures
	$(UV) run python tooling/validate.py $(FIXTURES_YAML)

overflow:  ## assert no text overflows its box (SVG proxy)
	$(UV) run python tooling/render_fixtures.py --all --check-overflow

corpus:  ## download + archive the public-domain expressiveness corpus
	$(UV) run python tooling/fetch_corpus.py

corpus-check:  ## offline: verify archived corpus files match the lockfile
	$(UV) run python tooling/fetch_corpus.py --check

package-check:  ## assert package-emit readiness (advisory; NOT in `make check` — see §2/§16)
	$(UV) run python tooling/check_package_readiness.py

corpus-ui:  ## render the CC0 UI mockups to high-def PNG (needs playwright+chromium)
	node viewer/dev/render-ui-corpus.cjs
	$(UV) run python tooling/fetch_corpus.py

status:  ## regenerate FIXTURE-STATUS.md from the validator
	$(UV) run python tooling/gen_status.py

status-check:  ## fail if FIXTURE-STATUS.md drifted from the validator
	$(UV) run python tooling/gen_status.py --check

docs: manifest examples-index  ## generate pages + build the static site into site/ (theme fetched ephemerally)
	$(UV) run python tooling/gen_docs.py
	$(UV) run --with mkdocs-material mkdocs build --strict

docs-serve: manifest examples-index  ## generate pages + serve with live reload (http://127.0.0.1:8000)
	$(UV) run python tooling/gen_docs.py
	$(UV) run --with mkdocs-material mkdocs serve

docs-check:  ## generate pages + assert every mkdocs.yml nav page exists (no full build)
	$(UV) run python tooling/gen_docs.py --check

docs-sdk:  ## regenerate ONLY the committed SDK snapshots (sdk.md/sdk-api.md) — fast
	$(UV) run python tooling/gen_docs.py --sdk

manifest:  ## regenerate docs/capability-manifest.json from the live tree (ADR-0002 tracking)
	$(UV) run python tooling/gen_capability_manifest.py

manifest-check:  ## fail if the committed capability manifest drifted from the live tree
	$(UV) run python tooling/gen_capability_manifest.py --check

examples-index:  ## regenerate docs/examples.md from the tracked examples/*.py docstrings
	$(UV) run python tooling/gen_examples_index.py

docs-linkcheck:  ## fail if a tracked Markdown file has a broken relative link (run after docs)
	$(UV) run python tooling/check_doc_links.py

disclaimer-check:  ## fail if an AI-authored doc is missing the rule-5 disclaimer frontmatter
	$(UV) run python tooling/check_disclaimers.py

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

golden:  ## re-pin the golden-render lock (after an intentional render change)
	$(UV) run python tooling/render_golden.py --update

golden-check:  ## fail if the b1/ oracle renders drift from the golden lock
	$(UV) run python tooling/render_golden.py

docker-build:  ## build the font-rich SDK/MCP image (ARGS='--build-arg FONTS_APT_WILDCARD=1')
	$(DOCKER) build -t $(IMAGE) \
		--build-arg BUILD_VERSION=$$(grep -m1 '^version' pyproject.toml | cut -d'"' -f2) \
		$(ARGS) .

docker-mcp:  ## run the MCP server (stdio) from the container
	$(DOCKER) run --rm -i -v framegraph-work:/work $(IMAGE)

docker-shell:  ## interactive shell inside the container toolchain
	$(DOCKER) run --rm -it -v framegraph-work:/work $(IMAGE) bash

docker-fonts:  ## list the font families baked into the image
	$(DOCKER) run --rm $(IMAGE) fonts

font-list:  ## fg-font: families this runtime resolves (reference these)
	$(UV) run python tooling/fg_font.py --list

font-check:  ## fg-font: fail if a content font in DOC substitutes (DOC=path.fg.yaml)
	$(UV) run python tooling/fg_font.py --check $(DOC)

font-pack:  ## fg-font: bundle DOC's fonts + manifest into a portable .fp (DOC=…, OUT=…, FETCH=1 pulls misses from Google Fonts)
	$(UV) run python tooling/fg_font.py --pack $(DOC) $(if $(OUT),--out $(OUT),) $(if $(FETCH),--fetch,)

font-install:  ## fg-font: extract a .fp pack into a scoped fontconfig (PACK=P.fp DIR=…)
	$(UV) run python tooling/fg_font.py --install $(PACK) --dir $(DIR)
