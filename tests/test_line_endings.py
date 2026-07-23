"""Line-ending contract — regression gate.

A CRLF checkout breaks this repository in two ways that never name their own
cause. A shebang script picked up by Git for Windows arrives as
``#!/usr/bin/env bash\\r``, and the Linux kernel then looks for an interpreter
literally named ``bash\\r`` — which is how a clean Windows clone failed the image
build at ``docker/collect-google-fonts.sh`` with
``/usr/bin/env: 'bash\\r': No such file or directory``. The same corruption in
``docker/entrypoint.sh`` breaks the container at start rather than at build,
after everything appeared to work.

The second way is quieter: golden-check pins b1/ oracle SVG output by SHA-256,
so a platform-dependent line ending makes a byte-exact gate platform-dependent.

``.gitattributes`` fixes both by normalising to LF everywhere. This gate exists
because deleting that file, or adding a script it does not cover, reproduces a
failure that only Windows users ever see — which is exactly the kind of defect a
Linux-only test suite lets through.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))

import tracked_files  # noqa: E402

ATTRIBUTES = ROOT / ".gitattributes"


def test_gitattributes_exists() -> None:
    assert ATTRIBUTES.is_file(), (
        "no .gitattributes means Git for Windows checks out CRLF by default and "
        "every shebang script in this repo becomes unexecutable in the container"
    )


def test_repository_pins_lf_in_the_working_tree() -> None:
    text = ATTRIBUTES.read_text(encoding="utf-8")
    assert "* text=auto eol=lf" in text, (
        "the default rule must force LF in the working tree, not merely normalise "
        "on commit — `text=auto` alone still hands Windows a CRLF checkout"
    )


def test_no_tracked_shebang_script_contains_crlf() -> None:
    """The failure mode itself, asserted directly against the bytes."""
    offenders = []
    for rel in tracked_files.tracked_on_disk(ROOT):
        path = ROOT / rel
        try:
            head = path.read_bytes()[:2]
        except OSError:
            continue
        if head != b"#!":
            continue
        if b"\r\n" in path.read_bytes():
            offenders.append(rel)
    assert not offenders, f"shebang scripts with CRLF line endings: {offenders}"


def test_container_critical_scripts_are_covered() -> None:
    """The two whose corruption kills the build and the runtime."""
    text = ATTRIBUTES.read_text(encoding="utf-8")
    for pattern in ("*.sh", "docker/*", "bin/*", "plugin/bin/*"):
        assert f"{pattern}" in text, f"{pattern} must be pinned to LF explicitly"
    for critical in ("docker/entrypoint.sh", "docker/collect-google-fonts.sh"):
        assert (ROOT / critical).is_file(), f"{critical} moved — update this gate"


def test_dockerfile_strips_cr_before_running_scripts() -> None:
    """Defence in depth: the build must not depend on how the source arrived.

    ``.gitattributes`` stops git from producing CRLF, but a clone taken before
    it landed, a GitHub source ZIP, or a host with its own ``core.autocrlf``
    still delivers CRLF. Both COPY sites therefore normalise before executing —
    the fonts stage (build-time failure) and the app stage, which owns
    ``entrypoint.sh`` and fails at ``docker run`` instead.
    """
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    strips = [ln for ln in dockerfile.splitlines() if "sed -i 's/\\r$//'" in ln]
    assert len(strips) >= 2, (
        "both the fonts stage and the app stage must strip CR before chmod/exec; "
        f"found {len(strips)} such line(s)"
    )
    assert any("collect-google-fonts.sh" in ln for ln in strips)
    assert any("docker/*.sh" in ln for ln in strips)
