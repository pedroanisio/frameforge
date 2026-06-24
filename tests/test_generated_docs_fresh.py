#!/usr/bin/env python3
"""
test_generated_docs_fresh.py — P1 guard: committed generated docs must be fresh.

Closes drift-risk-map Finding #5. `docs/sdk.md` and `docs/sdk-api.md` are
*generated* by `tooling/gen_docs.py` yet are also *committed* (git-tracked
snapshots people read on GitHub). Nothing compared the committed copy against a
fresh build: the page could silently rot while the built site self-healed (CI
regenerates before `mkdocs build`). This asserts the committed bytes equal a
fresh generation, so SDK drift becomes a `test-failure` instead of a silent lie.

Mirrors `build_schema.py --check` / `gen_status.py --check`. The same equality is
now also enforced by `gen_docs.py --check` (the `docs-check` gate); this test puts
it in the blocking `pytest` suite too.

Runs under pytest or standalone (`uv run python tests/test_generated_docs_fresh.py`).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(ROOT, "models"), os.path.join(ROOT, "schema"), os.path.join(ROOT, "tooling")]
# gen_docs imports the rendering package as `framegraph`; evict a models-module
# shadow first so its sdk import resolves the package (mirror of test_head.py).
_shadow = sys.modules.get("framegraph")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    sys.modules.pop("framegraph", None)

import gen_docs as G  # noqa: E402


def test_committed_sdk_docs_match_fresh_build():
    stale = []
    for rel, builder in G._TRACKED_GENERATED.items():
        path = os.path.join(G.DOCS, rel)
        on_disk = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if on_disk != builder():
            stale.append(rel)
    assert not stale, (
        f"committed generated docs are stale vs a fresh build: {stale}. "
        f"Run `make docs` and commit the regenerated pages."
    )


def test_stale_tracked_pages_helper_is_clean_now():
    # The helper gen_docs.py --check relies on must agree: nothing stale right now.
    assert G.stale_tracked_pages() == []


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
                failed += 1
    print(f"\n{'OK' if not failed else 'FAILED'} ({failed} failure(s))")
    sys.exit(1 if failed else 0)
