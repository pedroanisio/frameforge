#!/usr/bin/env python3
"""
test_spec_sync.py — P1 guard: the normative spec names every model type.

Closes drift-risk-map Finding #4. `spec/framegraph-v2-spec.md` calls itself the
normative reference but had no model-sync gate (only its example documents were
validated). `tooling/check_spec_sync.py` asserts every core object `type`, flow
`type`, and inline `kind` the models define is named somewhere in the spec prose
(ERROR), and surfaces unnamed field names as advisory WARNs. This puts the gate
in the blocking pytest suite alongside the CI `spec-check` step.

Runs under pytest or standalone (`uv run python tests/test_spec_sync.py`).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path[:0] = [os.path.join(ROOT, "tooling")]
_shadow = sys.modules.get("framegraph")
if _shadow is not None and hasattr(_shadow, "__path__"):
    del sys.modules["framegraph"]

import check_spec_sync as S  # noqa: E402

SPEC = open(S.SPEC, encoding="utf-8").read()


def test_spec_names_every_model_type():
    errors = [f for f in S.run_checks(SPEC) if f.sev == "ERROR"]
    assert not errors, "spec prose is missing model type discriminators:\n" + "\n".join(
        f"  {f.msg}" for f in errors
    )


def test_guard_catches_an_undocumented_type():
    """Prove the gate is not vacuous: stripping a type from the spec must ERROR."""
    # 'dimension' is an unusual enough token that removing it leaves no incidental
    # mention — a clean stand-in for a newly-added, undocumented type.
    mutilated = SPEC.replace("dimension", "XXXX")
    errors = [f for f in S.run_checks(mutilated) if f.sev == "ERROR"]
    assert any("dimension" in f.msg for f in errors), \
        "guard failed to flag a type discriminator removed from the spec"


def test_field_gaps_are_warnings_not_errors():
    """Field-name absence is advisory (the spec is prose, not a field reference)."""
    findings = S.run_checks(SPEC)
    assert all(f.sev != "ERROR" for f in findings if f.code == "field-undocumented")


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
