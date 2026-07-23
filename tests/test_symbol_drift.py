"""Prose-vs-live symbol drift gate — regression suite.

A gate that cannot fail is decoration. Most of these tests inject synthetic
drift and assert the checker reports it; only the first asserts the live tree is
clean. The injected cases are the ones that actually shipped:

- ``docs/roadmap.md`` claiming "25 MCP tools" while the registry had 31;
- ``docs/adr-0001`` naming ``arrow_attrs`` after the protocol member became
  ``arrow_markers``.

The false-negative direction matters just as much: a tutorial discussing a
variable it defines in its own code block must stay green, or the gate gets
switched off within a week.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))

import check_symbol_drift as CSD  # noqa: E402


@pytest.fixture
def fake_doc(monkeypatch):
    """Feed the checker one synthetic document instead of the tracked tree."""

    def _install(text: str, rel: str = "docs/fake.md"):
        monkeypatch.setattr(CSD, "doc_files", lambda: [rel])
        monkeypatch.setattr(
            CSD.tracked_files, "read_tracked", lambda root, path, **kw: text
        )
        return rel

    return _install


# ── the live tree ─────────────────────────────────────────────────────────


def test_live_tree_is_clean() -> None:
    problems, _ = CSD.evaluate()
    assert not problems, "prose drifted from the live tree:\n" + "\n".join(problems)


def test_every_allowance_carries_a_reason() -> None:
    """ALLOWED is an audit record, not a mute button."""
    for name, reason in CSD.ALLOWED.items():
        assert len(reason) > 20, f"ALLOWED[{name}] needs a real justification"


# ── it catches what shipped ───────────────────────────────────────────────


def test_detects_a_stale_tool_count(fake_doc) -> None:
    fake_doc("FrameForge offers machine authoring (25 MCP tools) today.\n")
    problems, _ = CSD.evaluate()
    assert any("claims 25 MCP tools" in p for p in problems)


def test_accepts_the_true_tool_count(fake_doc) -> None:
    _, tools = CSD.live_symbols()
    fake_doc(f"FrameForge exposes {len(tools)} MCP tools.\n")
    problems, _ = CSD.evaluate()
    assert not problems


def test_detects_a_renamed_symbol(fake_doc) -> None:
    fake_doc("The protocol names `arrow_attrs` among its members.\n")
    problems, _ = CSD.evaluate()
    assert any("`arrow_attrs`" in p for p in problems)


def test_accepts_the_current_symbol_name(fake_doc) -> None:
    fake_doc("The protocol names `arrow_markers` among its members.\n")
    problems, _ = CSD.evaluate()
    assert not problems


def test_detects_a_tool_that_was_never_built(fake_doc) -> None:
    fake_doc("Call `summon_unicorn` to render the deck.\n")
    problems, _ = CSD.evaluate()
    assert any("`summon_unicorn`" in p for p in problems)


# ── it does not cry wolf ──────────────────────────────────────────────────


def test_a_documents_own_example_names_are_in_scope(fake_doc) -> None:
    """The tutorial case: defined in a fence, discussed in the next paragraph."""
    fake_doc(
        "```python\n"
        "ink_left = solve(x0)\n"
        "```\n"
        "Solve `x0` so `ink_left` hits the left margin.\n"
    )
    problems, _ = CSD.evaluate()
    assert not problems


def test_fenced_payloads_are_not_policed(fake_doc) -> None:
    """Authored object ids inside examples are data, not API references."""
    fake_doc("```yaml\nid: totally_made_up_id\nkind: `also_not_a_symbol`\n```\n")
    problems, _ = CSD.evaluate()
    assert not problems


def test_front_matter_keys_are_in_scope(fake_doc) -> None:
    fake_doc("---\nappendix_references: [a, b]\n---\n\nSee `appendix_references`.\n")
    problems, _ = CSD.evaluate()
    assert not problems


def test_live_mcp_tool_names_pass(fake_doc) -> None:
    _, tools = CSD.live_symbols()
    fake_doc(" ".join(f"`{t}`" for t in tools) + "\n")
    problems, _ = CSD.evaluate()
    assert not problems


def test_single_word_spans_are_ignored(fake_doc) -> None:
    """`render`, `docs`, `main` are prose, not API symbols."""
    fake_doc("Run `render` from `docs` on `main`.\n")
    problems, _ = CSD.evaluate()
    assert not problems


# ── the allowlist prunes itself ───────────────────────────────────────────


def test_unused_allowance_is_reported(fake_doc, monkeypatch) -> None:
    monkeypatch.setitem(CSD.ALLOWED, "ghost_symbol_xyz", "a" * 30)
    fake_doc("Nothing references it.\n")
    _, notes = CSD.evaluate()
    assert any("ghost_symbol_xyz" in n and "no longer appears" in n for n in notes)


def test_allowance_that_the_tree_now_defines_is_reported(fake_doc, monkeypatch) -> None:
    """An allowance outliving its gap is exactly how these lists rot."""
    monkeypatch.setitem(CSD.ALLOWED, "run_sdk_code", "a" * 30)
    fake_doc("The tool is `run_sdk_code`.\n")
    _, notes = CSD.evaluate()
    assert any("run_sdk_code" in n and "now resolves" in n for n in notes)
