"""MathJax SVG rendering adapter (infrastructure).

Renders TeX/MathML to a path-based SVG fragment by shelling out to the Node
MathJax helper (tooling/mathjax_tex_to_svg.mjs), with a deterministic SVG
fallback when Node/MathJax is unavailable. Extracted from the Renderer to move
the subprocess + repo-path concern into the infrastructure layer (DDD/DIP —
codebase-standards §13). The tex->text transform used by the fallback is
injected, so this adapter does not import the domain math-text module.
"""
from __future__ import annotations

import json
import os
import subprocess
import re
from typing import Callable

_REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")
)


def _strip_mathml(source):
    """Extract readable text from a small MathML fragment for fallback sizing."""
    text = re.sub(r"<[^>]+>", " ", str(source or ""))
    return re.sub(r"\s+", " ", text).strip() or "math"


class MathSvgRenderer:
    """Render math to an SVG fragment via the Node MathJax helper, with a
    deterministic fallback. Cache + failure state are per-instance."""

    def __init__(self, text_fn: Callable, repo_root: str = _REPO_ROOT):
        self._text_fn = text_fn
        self._repo_root = repo_root
        self._cache = {}
        self._failures = set()
        self._failed = False

    def render(self, source, input_kind="tex"):
        """Render TeX/MathML to a path-based SVG fragment using MathJax."""
        """Render TeX/MathML to a path-based SVG fragment using MathJax."""
        source = str(source or "")
        input_kind = "mathml" if input_kind == "mathml" else "tex"
        cache_key = (input_kind, source)
        if not source or self._failed:
            return None
        if cache_key in self._cache:
            return self._cache[cache_key]
        if cache_key in self._failures:
            return None
        # FRAMEGRAPH_MATH_SVG=fallback forces the deterministic fallback glyph.
        # The golden gate sets it so pinned hashes never depend on whether the
        # optional node + viewer/node_modules MathJax toolchain resolves.
        if os.environ.get("FRAMEGRAPH_MATH_SVG") == "fallback":
            result = self._fallback(source, input_kind)
            self._cache[cache_key] = result
            return result
        script = os.path.join(self._repo_root, "tooling", "mathjax_tex_to_svg.mjs")
        if not os.path.exists(script):
            result = self._fallback(source, input_kind)
            self._cache[cache_key] = result
            return result
        try:
            proc = subprocess.run(
                ["node", script],
                input=json.dumps([{"input": input_kind, "source": source}]),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._repo_root,
                check=True,
            )
            converted = json.loads(proc.stdout or "[]")
            result = converted[0] if converted else None
        except subprocess.CalledProcessError as exc:
            stderr = str(getattr(exc, "stderr", "") or "")
            if "ERR_MODULE_NOT_FOUND" in stderr or "Cannot find module" in stderr:
                result = self._fallback(source, input_kind)
                self._cache[cache_key] = result
                return result
            self._failures.add(cache_key)
            return None
        except OSError:
            result = self._fallback(source, input_kind)
            self._cache[cache_key] = result
            return result
        except (json.JSONDecodeError, IndexError, TypeError):
            self._failures.add(cache_key)
            return None
        if not isinstance(result, dict) or not result.get("body") or not result.get("viewBox"):
            self._failures.add(cache_key)
            return None
        self._cache[cache_key] = result
        return result

    def _fallback(self, source, input_kind="tex"):
        """Return a deterministic SVG fragment when MathJax is unavailable.

        The fallback is deliberately visual and non-normative: it avoids leaking
        raw TeX/MathML into rendered pages, preserves the math-a11y marker used by
        tests and consumers, and keeps the real MathJax path preferred whenever
        the viewer's JS dependencies are installed.
        """
        text = self._text_fn(_strip_mathml(source) if input_kind == "mathml" else source)
        width = max(48, min(360, 16 + len(text or "math") * 8))
        height = 24
        body = (
            '<g data-mml-node="math">'
            '<path d="M2 12 C 8 2, 16 2, 22 12 S 36 22, 44 12" '
            'fill="none" stroke="currentColor" stroke-width="2"/>'
            '<path d="M50 6 H 58 V 14 H 50 Z" fill="currentColor" stroke="currentColor"/>'
            '<path d="M4 19 H 44" fill="none" stroke="currentColor" stroke-width="1"/>'
            '</g>'
        )
        return {"input": input_kind, "source": str(source or ""), "viewBox": f"0 0 {width} {height}",
                "width": width, "height": height, "body": body}

    # ---- per-object dispatch ---------------------------------------------- #
