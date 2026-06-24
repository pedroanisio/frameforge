#!/usr/bin/env python3
"""
test_golden_render.py — coverage + contract for tooling/render_golden.py, the
golden-render harness over the b1/ authoritative oracle (roadmap item 4).

Asserts (1) the committed lock matches the current renders (the live gate),
(2) the lock covers every oracle fixture, and (3) the drift detector actually
fires on a changed page and a changed page count (so the gate can't pass blind).
"""
import copy
import glob
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tooling"))

import render_golden as G  # noqa: E402


def test_oracle_manifest_builds():
    current = G.build()
    assert current, "golden render harness must render the b1/ oracle"
    assert all(v for v in current.values()), "every oracle fixture must render at least one page"


def test_lock_matches_current_renders():
    """The live gate: the committed lock must match the current b1/ oracle renders.
    Re-pin with `make golden` after an intentional render change."""
    drift = G.diff(G.build(), G.load_lock())
    assert drift == [], "golden drift (run `make golden` if intentional):\n" + "\n".join(drift)


def test_lock_covers_every_oracle_fixture():
    locked = G.load_lock()
    assert locked is not None
    fixtures = {os.path.relpath(p, ROOT) for p in glob.glob(G.ORACLE_GLOB)}
    assert set(locked) == fixtures and fixtures, "lock must cover exactly the b1/ oracle"
    assert all(len(v) >= 1 for v in locked.values()), "every fixture must render >=1 page"


def test_diff_detects_changed_page():
    locked = G.load_lock()
    current = copy.deepcopy(locked)
    k = sorted(current)[0]
    current[k] = ["0" * 64] + current[k][1:]      # tamper page 1's hash
    assert any("page 1: render changed" in line for line in G.diff(current, locked))


def test_diff_detects_page_count_change():
    locked = G.load_lock()
    current = copy.deepcopy(locked)
    k = sorted(current)[0]
    current[k] = current[k][:-1]                   # drop a page
    assert any("page count" in line for line in G.diff(current, locked))


def test_diff_clean_when_identical():
    locked = G.load_lock()
    assert G.diff(copy.deepcopy(locked), locked) == []
