"""The oracle lock covers HTML too, not just SVG (GH #85).

The SVG golden lock (``tests/golden/oracle.lock.json``) pins 87 SVG pages. It
pins nothing about the HTML backend — so the per-span-style flattening that
rendered the brand wordmark and every ``fan()`` label invisible (GH #83), and
the dropped links (GH #84), both shipped with ``make check`` fully green and were
found by eye weeks later.

This is the guard that would have caught them in the same run that produced them:
a per-fixture SHA-256 of the HTML render of every oracle document, checked like
the SVG lock. The HTML backend is a pure, dependency-free
``render_document(doc) -> str`` transform, so it joins the lock unconditionally —
no optional deps, no headless browser, deterministic across machines.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for p in (ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs"),
          os.path.join(ROOT, "tooling")):
    if p not in sys.path:
        sys.path.insert(0, p)

_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

import render_golden as RG  # noqa: E402


def test_html_oracle_lock_exists():
    """A committed HTML lock must exist alongside the SVG one."""
    assert os.path.exists(RG.HTML_LOCK), (
        "no HTML oracle lock — run `python tooling/render_golden.py --update`")


def test_html_lock_matches_current_render():
    """Every oracle fixture's HTML render must match its committed hash."""
    locked = RG.load_html_lock()
    assert locked, "HTML lock is empty"
    current = RG.build_html_hashes()
    assert set(current) == set(locked), "oracle fixture set drifted from the HTML lock"
    drift = [k for k in current if current[k] != locked.get(k)]
    assert not drift, f"HTML render drifted for: {drift} — review, then --update"


def test_html_lock_covers_the_same_fixtures_as_svg():
    """The two backends pin the SAME corpus — no fixture is HTML-only or SVG-only."""
    svg = RG.load_lock() or {}
    html = RG.load_html_lock() or {}
    assert set(svg) == set(html), (
        "SVG and HTML locks cover different fixtures; both must pin the whole oracle")


def test_html_hash_is_content_sensitive():
    """A changed document must change its HTML hash (the lock actually bites)."""
    import copy
    fixtures = RG.oracle_fixtures()
    spans = [f for f in fixtures if "spans-and-links" in f]
    doc = RG._load_doc(spans[0] if spans else fixtures[0])
    base = RG._html_hash_of(doc)
    mutated = copy.deepcopy(doc)
    # flip a title — a visible, content-level change
    mutated["title"] = (mutated.get("title") or "") + " (edited)"
    assert RG._html_hash_of(mutated) != base, "HTML hash ignored a content change"


def test_html_lock_catches_flattened_spans_regression():
    """The lock must bite on the exact bug it exists for (GH #83).

    Reintroduce the old behaviour — flatten styled runs into one unstyled run,
    dropping per-span colour — and confirm the fixture's HTML hash changes.
    Without a fixture that USES coloured spans this lock would be theater;
    `spans-and-links` is that fixture.

    The injection point moved with the architecture: the bug used to live in the
    standalone backend's `_render_text`, and now the equivalent seam is the
    painter's `text_runs`, which is where per-run styles become markup. Patching
    the painter also proves the lock covers the shared render path rather than a
    backend-private one.
    """
    from frameforge_render.infrastructure.painters.html import HtmlPainter
    spans = [f for f in RG.oracle_fixtures() if "spans-and-links" in f]
    assert spans, "the spans-and-links oracle fixture must exist to guard #83"
    doc = RG._load_doc(spans[0])
    good = RG._html_hash_of(doc)

    def flattened(self, base_y, anchor, tx, base_st, size, runs,
                  text_len=None, baseline=None):
        """The #83 defect: concatenate the runs and paint them all in the base
        style, so every per-span colour/weight is silently lost."""
        merged = "".join(text for text, _run_style in runs)
        return HtmlPainter.text_block(self, base_y, anchor, base_st, size,
                                      [merged], tx, 0, baseline=baseline)

    orig = HtmlPainter.text_runs
    HtmlPainter.text_runs = flattened
    try:
        broken = RG._html_hash_of(doc)
    finally:
        HtmlPainter.text_runs = orig
    assert broken != good, "the HTML lock did not catch a flattened-spans regression"
