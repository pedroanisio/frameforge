"""Text-fitting domain service: measure / wrap / ellipsize to a pixel width.

Pure text-layout logic extracted from the monolithic ``Renderer`` (DDD step:
decompose the god-object toward SRP — codebase-standards.md §13). Font metrics
are supplied through an injected provider callable rather than imported here, so
the domain layer stays free of the infrastructure font-metrics implementation
(dependency inversion):

    provider(family_primary: str, bold: bool) -> metrics | None

When the provider is absent, or returns ``None`` for a given style, measurement
falls back to a character-count estimate (``len * size * avg``) — exactly the
renderer's estimate mode. Behaviour is identical to the methods it replaces.
"""
from __future__ import annotations

from typing import Callable, Optional


class TextFitter:
    """Fit text to a pixel width, using real glyph advances when a font-metrics
    provider is supplied, else a character-count estimate."""

    def __init__(self, font_metrics_provider: Optional[Callable] = None):
        self._provider = font_metrics_provider

    def _fm(self, st):
        if self._provider is None or not st:
            return None
        return self._provider(st.get("family_primary") or st.get("family", ""), bool(st.get("bold")))

    def measure(self, s, size, avg, st=None):
        fm = self._fm(st)
        if fm is not None:
            return fm.width(str(s), size)
        return len(s) * size * avg

    def wrap_words(self, text, w, size, avg, st=None):
        fm = self._fm(st)
        if fm is not None:
            return self._wrap_real(str(text), w, size, fm)
        maxc = max(1, int(w / (size * avg)))
        out, cur = [], ""
        for word in str(text).split():
            while len(word) > maxc:                  # hard-break an over-long token
                if cur:
                    out.append(cur); cur = ""
                out.append(word[:maxc]); word = word[maxc:]
            if cur and len(cur) + 1 + len(word) > maxc:
                out.append(cur); cur = word
            else:
                cur = (cur + " " + word).strip()
        if cur:
            out.append(cur)
        return out or [""]

    def ellipsize(self, s, w, size, avg, st=None):
        fm = self._fm(st)
        if fm is not None:
            return self._ellipsize_real(str(s), w, size, fm)
        maxc = max(0, int(w / (size * avg)))
        if len(s) <= maxc:
            return s
        return (s[: max(0, maxc - 1)].rstrip() + "…") if maxc else "…"

    @staticmethod
    def _wrap_real(text, w, size, fm):
        """Greedy word-wrap to pixel width `w` using real glyph advances."""
        out, cur = [], ""
        for word in text.split():
            while fm.width(word, size) > w:          # hard-break an over-long token
                take = 1
                while take < len(word) and fm.width(word[: take + 1], size) <= w:
                    take += 1
                if cur:
                    out.append(cur); cur = ""
                out.append(word[:take]); word = word[take:]
                if not word:
                    break
            if not word:
                continue
            cand = (cur + " " + word).strip()
            if cur and fm.width(cand, size) > w:
                out.append(cur); cur = word
            else:
                cur = cand
        if cur:
            out.append(cur)
        return out or [""]

    @staticmethod
    def _ellipsize_real(s, w, size, fm):
        """Trim `s` to pixel width `w` (real advances), appending an ellipsis."""
        if fm.width(s, size) <= w:
            return s
        ell = fm.width("…", size)
        take = 0
        while take < len(s) and fm.width(s[: take + 1], size) + ell <= w:
            take += 1
        return (s[:take].rstrip() + "…") if take else "…"
