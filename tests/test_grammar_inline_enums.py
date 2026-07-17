#!/usr/bin/env python3
"""
test_grammar_inline_enums.py — P1 guard: inline style enums match the models.

Closes drift-risk-map Finding #3. The named style enums (FontStyle, BlendMode, …)
were already diffed by check_grammar_sync.check_enums, but the *inline* enums on
style fields — ``[ "text_align" , ":" , ( "left" | … ) ]`` — were never compared to
the models' inline ``Literal`` fields, so the grammar could offer a value the model
rejects with no gating signal.

`check_grammar_sync.check_inline_enums` now lines the two up by field name and
ERRORs when the grammar offers a value no closed model field accepts. The repo-wide
"no ERROR" assertion lives in test_grammar_sync.py; this file proves the new
machinery actually extracts the inline enums and actually fails on a planted lie
(so the gate can't silently regress to a no-op).

Runs under pytest or standalone (`uv run python tests/test_grammar_inline_enums.py`).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(ROOT, "tooling"), ]

import check_grammar_sync as C  # noqa: E402


def test_extractor_finds_real_inline_enums():
    """The slot extractor must actually pick up the inline text-style enums — else
    the gate would be vacuously green."""
    slots = C.style_inline_enum_slots()
    assert slots.get("text_align") == {"left", "right", "center", "justify", "start", "end"}
    assert slots.get("white_space") == {"normal", "nowrap", "pre", "pre-wrap", "pre-line", "break-spaces"}
    assert slots.get("word_break") == {"normal", "break-all", "keep-all", "break-word"}


def test_models_expose_those_fields_as_closed_enums():
    model = C.model_closed_field_enums()
    assert model.get("text_align") == {"left", "right", "center", "justify", "start", "end"}
    assert "white_space" in model and "word_break" in model


def test_inline_enums_in_sync_on_real_grammar():
    out = []
    C.check_inline_enums(out)
    assert not out, "inline style enum drift:\n" + "\n".join(str(f) for f in out)


def test_gate_catches_a_grammar_lie():
    """A grammar that offers text_align: "middle" (rejected by the model) must ERROR."""
    out = []
    C.check_inline_enums(out, slots={"text_align": {"left", "middle"}})
    assert any(f.code == "inline-enum-drift" and "middle" in f.msg for f in out), \
        "inline-enum gate failed to flag a value the model rejects"


def test_open_str_fields_are_not_flagged():
    """A field whose model annotation admits a free str must not be flagged even if
    the grammar lists 'extra' sample values (no closed contract to violate)."""
    model = C.model_closed_field_enums()
    # text_overflow is Union[Literal["clip","ellipsis"], str] -> open -> excluded.
    assert "text_overflow" not in model
    out = []
    C.check_inline_enums(out, slots={"text_overflow": {"clip", "ellipsis", "fade"}})
    assert not out


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
