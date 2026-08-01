"""Derived accessibility semantics — what an object implies but does not state.

An authored object may carry `decorative`, `role`, `alt` or `actual_text`, and
those always win: they are the author speaking. Most objects carry none of them,
and a backend that stops there emits a page of anonymous shapes — technically
valid, practically unusable with a screen reader.

This module states, once, what an object's *type* implies when the author said
nothing:

* a `group` is a grouping (`role="group"`),
* bare geometry — a line, a connector, a curve — carries no information a
  screen reader can convey, so it is hidden rather than announced as an unnamed
  graphic,
* an `icon` whose glyph is a *word* ("calendar-check") has a usable name; an
  icon whose glyph is a raw symbol ("★") does not, and announcing the symbol
  helps nobody, so it is hidden instead of mislabelled.

The inference used to live inside the standalone HTML renderer. It lives here so
it is stated once and any backend may consume it — the HTML backend does today.

Why the SVG backend does not
----------------------------
`SvgPainter.a11y_wrap` deliberately emits authored semantics only. Consuming
these derived ones would be an improvement, but it changes the bytes of every
golden fixture, and the oracle is the project's regression floor. Opting SVG in
is therefore an explicit decision with an oracle re-pin attached, not a side
effect of a backend port. Nothing here is SVG-specific; the day that decision is
taken, the change is one call site.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Optional

#: Object types that are pure geometry: they carry no text and no meaning a
#: screen reader can convey, so an unnamed graphic announcement is noise.
GEOMETRY_TYPES = frozenset({
    "line", "polyline", "polygon", "path", "curve", "bezier", "connector",
})

#: A glyph name is usable as an accessible name only when it reads as words.
#: "calendar-check" does; "★" and "7" do not.
_WORD_GLYPH = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:[-_ ][A-Za-z0-9]+)*$")


def icon_label(glyph: Any) -> Optional[str]:
    """A human-readable name for an icon glyph, or None when there isn't one.

    Separator characters become spaces so "calendar-check" is announced as
    "calendar check" rather than spelled out. A single character is rejected:
    it is a symbol, not a word, and announcing it is noise. (The standalone HTML
    renderer required three characters; two-letter words like "ok" and "up" are
    legitimate names, so the floor is deliberately lower here.)
    """
    if not isinstance(glyph, str):
        return None
    name = glyph.strip()
    if len(name) < 2 or not _WORD_GLYPH.match(name):
        return None
    return re.sub(r"[-_]+", " ", name)


def derive_semantics(obj: Mapping[str, Any]) -> Optional[dict]:
    """Accessibility semantics implied by `obj`'s type, or None.

    Returns either ``{"hidden": True}`` or ``{"role": str, "label": str | None}``.
    The caller applies AUTHORED semantics first — this is only consulted when the
    author stated nothing, so it can never override an explicit intent.
    """
    if not isinstance(obj, dict):
        return None
    otype = obj.get("type")
    if not isinstance(otype, str):
        return None

    if otype == "icon":
        label = icon_label(obj.get("glyph"))
        return {"role": "img", "label": label} if label else {"hidden": True}

    if otype == "image":
        # The model spells an image's name `label`, not `alt`, so the authored
        # -field path in the painters never sees it. An image with no name gets
        # no opinion: it may be meaningful content the author has not named yet,
        # and hiding real content is worse than leaving it unlabelled.
        label = obj.get("label")
        if isinstance(label, str) and label.strip():
            return {"role": "img", "label": label.strip()}
        return None

    if otype in GEOMETRY_TYPES:
        return {"hidden": True}

    if otype == "group":
        return {"role": "group", "label": None}

    return None
