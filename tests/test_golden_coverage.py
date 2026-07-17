"""drift-risk-map #3 — the golden SVG lock must not silently lose coverage.

The golden lock (`tests/golden/oracle.lock.json` via `render_golden.py`) pins the
SVG render of the `b1/` oracle — but only for the object types those fixtures
happen to use. A core object type NO `b1/` fixture exercises is invisible to the
lock: a regression in its render ships green. This meta-test makes that measurable
and *ratcheted*:

  * golden object-type coverage may never shrink (a removed fixture, or a type
    that stops appearing, fails the gate), and
  * a NEW core object type must be consciously accounted for — either exercised by
    a golden fixture, or added to ``KNOWN_UNCOVERED`` (which records the intent to
    add a coverage fixture and re-pin the lock).

It deliberately does NOT add fixtures to the sacred `b1/` oracle (real
authoritative documents, `.fg.json`, asserted by `test_head` and pinned exactly by
`test_golden_render`). Closing a ``KNOWN_UNCOVERED`` gap = add a coverage fixture
to a golden corpus and re-pin — surfaced here, never silently ignored.
"""
from __future__ import annotations

import glob
import os
import sys

import yaml

_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import validate as V  # noqa: E402  (tooling/, via conftest)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Core object types NO golden (b1/) fixture exercises yet — flagged, not hidden.
# Closing one = add a coverage fixture + re-pin the lock, then drop it from here.
KNOWN_UNCOVERED = frozenset({
    "circle", "polygon", "curve", "bezier", "icon", "dimension", "connector",
})


def _golden_covered_object_types() -> set[str]:
    core = set(V.CORE_OBJECT_TYPES)
    used: set[str] = set()
    for f in glob.glob(os.path.join(ROOT, "tests", "fixtures", "b1", "*.fg.*")):
        try:
            doc = yaml.safe_load(open(f, encoding="utf-8"))  # JSON is valid YAML
        except Exception:
            continue
        stack = [doc]
        while stack:
            n = stack.pop()
            if isinstance(n, dict):
                t = n.get("type")
                if isinstance(t, str):
                    used.add(t)
                stack.extend(n.values())
            elif isinstance(n, list):
                stack.extend(n)
    return used & core


def test_all_non_baselined_core_types_are_golden_covered():
    """Every core object type not on KNOWN_UNCOVERED must be exercised by a golden
    fixture. A regression (a fixture removed, or a type that stops appearing) trips
    this — the lock can no longer silently lose a type."""
    covered = _golden_covered_object_types()
    expected = set(V.CORE_OBJECT_TYPES) - KNOWN_UNCOVERED
    missing = expected - covered
    assert not missing, (
        f"golden object-type coverage regressed — no b1/ fixture exercises: "
        f"{sorted(missing)}")


def test_new_core_object_type_must_be_covered_or_explicitly_baselined():
    """A core object type added to the model that is neither golden-covered nor on
    KNOWN_UNCOVERED fails the gate — forcing a conscious 'add a fixture or baseline
    it' decision instead of shipping an unverified type."""
    core = set(V.CORE_OBJECT_TYPES)
    accounted = _golden_covered_object_types() | KNOWN_UNCOVERED
    unaccounted = core - accounted
    assert not unaccounted, (
        f"new core object type(s) neither golden-covered nor baselined: "
        f"{sorted(unaccounted)} — add a coverage fixture + re-pin, or add to "
        f"KNOWN_UNCOVERED with intent")


def test_known_uncovered_list_is_honest_not_stale():
    """A type listed as uncovered must actually be uncovered; once a fixture covers
    it, it must be removed from KNOWN_UNCOVERED so the baseline can only shrink."""
    stale = KNOWN_UNCOVERED & _golden_covered_object_types()
    assert not stale, (
        f"KNOWN_UNCOVERED lists types that ARE golden-covered now — remove them: "
        f"{sorted(stale)}")
