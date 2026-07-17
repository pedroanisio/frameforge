"""A small UI-widget vocabulary that lowers to FrameForge primitives.

These helpers assemble the components an application or dashboard author repeats
on every screen — cards, KPI tiles, badges, pills, buttons, avatars, form
fields, toggles, tabs, progress bars and data tables — out of the core object
set the model already validates. They are the UI analogue of
:mod:`frameforge.sdk.chart`: pure functions that emit plain object ``dict`` s for
:meth:`frameforge.sdk.PageBuilder.add` / ``extend``.

How widgets lower (and why):

* Every multi-part widget returns ONE ``group`` whose ``box`` is the absolute
  widget box and whose children are authored in the group's *local* frame
  (origin ``0,0``). A group with a box translates its children by that origin in
  the renderer, so the author always passes absolute page coordinates and the
  widget's internals stay self-contained. This also means a widget contributes a
  single box to the ``containment`` check and hides its text from the
  ``tabular-box-model`` heuristic (which does not recurse into groups) — so a
  page built from widgets validates cleanly instead of tripping a warning per
  label.
* :func:`table` emits a real ``TableObject`` (``type: "table"``), the model's
  first-class tabular primitive — column widths/alignment, an optional header
  and zebra striping, with cells clipped to the grid. This is the structured
  path the validator recommends.

**Honest scope (§13).** This is a *lowering* layer, not a UI framework. It does
no theming engine beyond a flat :class:`Theme` of literal values.
Widgets emit inline styles built from the theme, so they render with zero
document setup; :func:`register_theme` is optional sugar for authors who also
want to reference the same tokens by name elsewhere. ``table`` cells are text
only — for rich cells (a badge or progress bar inside a row) compose the atoms
inside a :func:`card` or a layout-native builder stack instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from frameforge.sdk.metrics import measure_text

Box = Sequence[float]
Obj = dict[str, Any]

__all__ = [
    "Theme",
    "Panel",
    "default_theme",
    "register_theme",
    "badge",
    "badge_width",
    "breadcrumb",
    "pill",
    "button",
    "avatar",
    "checkbox",
    "dropdown",
    "image_placeholder",
    "kpi",
    "field",
    "navbar",
    "radio",
    "slider",
    "sticky_note",
    "toggle",
    "tabs",
    "progress",
    "divider",
    "card",
    "table",
]


# --------------------------------------------------------------------------- #
#  Theme
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Theme:
    """A flat palette + type scale of *literal* values widgets emit inline.

    Restyle by passing a modified copy (``replace(default_theme(), accent="#16A34A")``)
    to any widget's ``theme=`` argument. Colours are ``#rrggbb``; ``font``/``mono``
    are CSS family stacks. Nothing here references document tokens, so widgets
    work without any :class:`~frameforge.sdk.DocumentBuilder` setup.
    """

    # surfaces & ink
    surface: str = "#FFFFFF"
    surface_alt: str = "#F4F6F9"
    ink: str = "#1D2430"
    sub: str = "#56607A"
    muted: str = "#8A93A3"
    line: str = "#D7DCE4"
    fill: str = "#EEF1F5"
    fill_alt: str = "#E3E7EE"
    # accent + status (solid / soft pairs)
    accent: str = "#2563EB"
    accent_soft: str = "#E6EEFC"
    good: str = "#1F9254"
    good_soft: str = "#E2F3E9"
    warn: str = "#B7791F"
    warn_soft: str = "#FBF0DA"
    bad: str = "#C23B3B"
    bad_soft: str = "#FBE6E6"
    # type
    font: tuple[str, ...] = ("Inter", "Helvetica", "Arial", "sans-serif")
    mono: tuple[str, ...] = ("SFMono-Regular", "Menlo", "monospace")
    # geometry
    radius: float = 10.0
    pad: float = 16.0
    control_h: float = 36.0


def default_theme() -> Theme:
    """Return the stock theme. Copy-and-tweak with :func:`dataclasses.replace`."""
    return Theme()


def register_theme(builder, theme: Theme | None = None, *, prefix: str = "") -> dict:
    """Optionally register a theme's colours as document tokens, by name.

    Widgets do **not** need this — they emit literal colours. It exists so an
    author can reference the same palette (``fill="<prefix>accent"``) from
    hand-authored primitives. Returns the ``{name: Handle}`` map.
    """
    th = theme or default_theme()
    handles: dict[str, Any] = {}
    for name in (
        "surface", "surface_alt", "ink", "sub", "muted", "line", "fill", "fill_alt",
        "accent", "accent_soft", "good", "good_soft", "warn", "warn_soft", "bad",
        "bad_soft",
    ):
        handles[name] = builder.define_color(prefix + name, getattr(th, name))
    return handles


# --------------------------------------------------------------------------- #
#  internals
# --------------------------------------------------------------------------- #
_TONES = {
    "muted": ("fill", "sub"),
    "neutral": ("fill", "sub"),
    "accent": ("accent_soft", "accent"),
    "good": ("good_soft", "good"),
    "warn": ("warn_soft", "warn"),
    "bad": ("bad_soft", "bad"),
}


def _tone(th: Theme, tone: str) -> tuple[str, str]:
    bg, fg = _TONES.get(tone, _TONES["muted"])
    return getattr(th, bg), getattr(th, fg)


def _wh(box: Box) -> tuple[float, float, float, float]:
    x, y, w, h = float(box[0]), float(box[1]), float(box[2]), float(box[3])
    return x, y, w, h


def _style(
    th: Theme,
    size: float,
    *,
    weight: int = 400,
    color: str | None = None,
    align: str = "left",
    valign: str = "middle",
    nowrap: bool = True,
    fit: str = "clip",
    mono: bool = False,
    **extra: Any,
) -> dict:
    """Build an inline text style with author-friendly fit defaults.

    Defaults to vertically-centred, single-line, clip-to-box text — so callers
    place a label in a box and never hand-compute a baseline offset.
    """
    st: dict[str, Any] = {
        "font_family": list(th.mono if mono else th.font),
        "font_size": size,
        "font_weight": weight,
        "color": color or th.ink,
        "align": align,
        "vertical_align": valign,
        "overflow": fit,
    }
    if nowrap:
        st["white_space"] = "nowrap"
    st.update(extra)
    return st


def _group(box: Box, children: list[Obj], name: str, **fields: Any) -> Obj:
    """Wrap locally-authored children in a group carrying the absolute box."""
    x, y, w, h = _wh(box)
    obj: Obj = {"type": "group", "box": [x, y, w, h], "children": children,
                "meta": {"widget": name}}
    obj.update(fields)
    return obj


def _rect(box: Box, **fields: Any) -> Obj:
    return {"type": "rect", "box": [float(b) for b in box], **fields}


def _bg(box: Box, **fields: Any) -> Obj:
    """A structural/background rect. Marked ``decorative`` so it is correctly
    excluded from a11y reading order and from the ``overlap`` audit that runs on
    a group's children (the label text on top is the real content)."""
    return {"type": "rect", "box": [float(b) for b in box], "decorative": True, **fields}


def _text(box: Box, text: str, style: dict) -> Obj:
    return {"type": "text", "box": [float(b) for b in box], "text": str(text),
            "style": style}


def _initials(name: str) -> str:
    parts = [p for p in str(name).replace("·", " ").split() if p[:1].isalnum()]
    if not parts:
        return "•"
    return (parts[0][:1] + (parts[1][:1] if len(parts) > 1 else "")).upper()


def _is_box(value: Any) -> bool:
    if isinstance(value, (str, bytes)) or value is None:
        return False
    try:
        return len(value) >= 4
    except TypeError:
        return False


# --------------------------------------------------------------------------- #
#  atoms
# --------------------------------------------------------------------------- #
def badge_width(text: str, *, theme: Theme | None = None, size: float = 11.0,
                pad: float = 20.0) -> float:
    """Measured pixel width for a :func:`badge`/:func:`pill` snug around ``text``."""
    th = theme or default_theme()
    return measure_text(str(text), font_family=th.font, font_size=size, bold=True) + pad


def badge(box: Box | str, text: str | None = None, *, tone: str = "muted",
          theme: Theme | None = None) -> Obj:
    """A small status chip: a soft rounded fill with centred, toned label."""
    th = theme or default_theme()
    if text is None:
        text = str(box)
        box = [0, 0, badge_width(text, theme=th), 24]
    _, _, w, h = _wh(box)
    bg, fg = _tone(th, tone)
    children = [
        _bg([0, 0, w, h], fill=bg, radius=h / 2),
        _text([0, 0, w, h], text, _style(th, 11, weight=700, color=fg, align="center")),
    ]
    return _group(box, children, "badge")


def pill(
    box: Box | str | None = None,
    text: str | None = None,
    *,
    fill: str | None = None,
    text_color: str | None = None,
    stroke: str | None = None,
    radius: float | None = None,
    theme: Theme | None = None,
) -> Obj:
    """A rounded container with optional outline and centred-left label."""
    th = theme or default_theme()
    if not _is_box(box):
        text = str(box) if text is None and box is not None else text
        label = "" if text is None else str(text)
        box = [0, 0, max(48, badge_width(label, theme=th, size=12, pad=28)), th.control_h]
    _, _, w, h = _wh(box)
    r = radius if radius is not None else h / 2
    rect_fields: dict[str, Any] = {"fill": fill or th.fill, "radius": r}
    if stroke:
        rect_fields["stroke"] = stroke
        rect_fields["stroke_style"] = {"stroke_width": 1.0}
    children: list[Obj] = [_bg([0, 0, w, h], **rect_fields)]
    if text is not None:
        children.append(_text([12, 0, w - 24, h], text,
                              _style(th, 12, weight=600, color=text_color or th.sub)))
    return _group(box, children, "pill")


def button(box: Box | str, label: str | None = None, *, kind: str = "primary",
           theme: Theme | None = None, w: float | None = None, h: float | None = None,
           grow: float | None = None) -> Obj:
    """A button. ``kind`` is ``primary`` (accent), ``ghost`` (outline) or ``subtle``."""
    th = theme or default_theme()
    if label is None:
        label = str(box)
        bw = w if w is not None else measure_text(label, font_family=th.font, font_size=13, bold=True) + 32
        bh = h if h is not None else th.control_h
        box = [0, 0, bw, bh]
    _, _, w, h = _wh(box)
    if kind == "primary":
        rect_fields = {"fill": th.accent, "radius": 8}
        color = th.surface
    elif kind == "ghost":
        rect_fields = {"fill": th.surface, "stroke": th.line,
                       "stroke_style": {"stroke_width": 1.0}, "radius": 8}
        color = th.sub
    else:
        rect_fields = {"fill": th.fill, "radius": 8}
        color = th.sub
    children = [
        _bg([0, 0, w, h], **rect_fields),
        _text([0, 0, w, h], label, _style(th, 13, weight=700, color=color, align="center")),
    ]
    fields: dict[str, Any] = {}
    if grow is not None:
        fields["sizing"] = {"width": "fill", "grow": grow}
    return _group(box, children, "button", **fields)


def avatar(box: Box | str | None = None, initials: str | None = None, *, tone: str = "muted",
           theme: Theme | None = None, size: float | None = None) -> Obj:
    """A circular avatar placeholder with optional initials (auto-derived if a name)."""
    th = theme or default_theme()
    if not _is_box(box):
        initials = str(box) if initials is None and box is not None else initials
        d = size if size is not None else th.control_h
        box = [0, 0, d, d]
    _, _, w, h = _wh(box)
    d = min(w, h)
    bg, fg = _tone(th, tone)
    init = initials if (initials and len(initials) <= 2) else (
        _initials(initials) if initials else None)
    children: list[Obj] = [{
        "type": "ellipse", "center": [w / 2, h / 2], "rx": d / 2, "ry": d / 2,
        "fill": bg, "stroke": th.line, "stroke_style": {"stroke_width": 1.0},
    }]
    if init:
        children.append(_text([0, 0, w, h], init,
                              _style(th, max(10.0, d * 0.36), weight=700, color=fg,
                                     align="center")))
    return _group(box, children, "avatar")


def kpi(box: Box | str, label: str, value: str | None = None, *, delta: str | None = None,
        down: bool = False, theme: Theme | None = None) -> Obj:
    """A metric tile: card surface, uppercase label, large value, optional delta."""
    th = theme or default_theme()
    if value is None:
        value = str(label)
        label = str(box)
        box = [0, 0, 180, 108]
    _, _, w, h = _wh(box)
    pad = th.pad
    children = [
        _bg([0, 0, w, h], fill=th.surface, stroke=th.line,
            stroke_style={"stroke_width": 1.0}, radius=12),
        _text([pad, pad, w - 2 * pad, 14], label.upper(),
              _style(th, 11, weight=700, color=th.muted, letter_spacing=0.6,
                     valign="top")),
        _text([pad, pad + 18, w - 2 * pad, 36], value,
              _style(th, 30, weight=800, color=th.ink, letter_spacing=-1,
                     fit="shrink_to_fit", min_font_size=18, valign="top")),
    ]
    if delta is not None:
        children.append(_text([pad, h - pad - 16, w - 2 * pad, 16], delta,
                              _style(th, 12, weight=700,
                                     color=th.bad if down else th.good, valign="top")))
    return _group(box, children, "kpi")


def field(box: Box | str, label: str | None = None, *, value: str = "", placeholder: str = "",
          kind: str = "input", theme: Theme | None = None, w: float | None = None,
          h: float | None = None) -> Obj:
    """A form field: uppercase label over an input/select/textarea control."""
    th = theme or default_theme()
    if label is None:
        label = str(box)
        box = [0, 0, w if w is not None else 220, h if h is not None else (96 if kind == "area" else 58)]
    _, _, w, h = _wh(box)
    top = 18.0
    ih = h - top
    children: list[Obj] = [
        _text([0, 0, w, 14], label.upper(),
              _style(th, 11, weight=700, color=th.muted, letter_spacing=0.6)),
        _bg([0, top, w, ih], fill=th.surface, stroke=th.line,
            stroke_style={"stroke_width": 1.0}, radius=8),
    ]
    if kind == "area":
        children.append(_text([12, top + 12, w - 24, 16],
                              placeholder or value or "", _style(
                                  th, 13, color=th.ink if value else th.muted, valign="top")))
    elif kind == "select":
        children.append(_text([12, top, w - 40, ih], value or placeholder or "Select…",
                              _style(th, 13, color=th.ink if value else th.muted)))
        children.append(_text([w - 26, top, 16, ih], "▾",
                              _style(th, 13, color=th.muted, align="center")))
    else:
        children.append(_text([12, top, w - 24, ih], value or placeholder or "",
                              _style(th, 13, color=th.ink if value else th.muted)))
    return _group(box, children, "field")


def toggle(box: Box | None = None, *, on: bool = True, theme: Theme | None = None,
           w: float | None = None, h: float | None = None) -> Obj:
    """A switch sized to ``box`` (the track). Knob sits left (off) or right (on)."""
    th = theme or default_theme()
    if box is None:
        box = [0, 0, w if w is not None else 46, h if h is not None else 26]
    _, _, w, h = _wh(box)
    knob_r = h / 2 - 3
    cx = (w - h / 2) if on else (h / 2)
    children = [
        _bg([0, 0, w, h], fill=th.accent if on else th.fill_alt, radius=h / 2),
        {"type": "ellipse", "center": [cx, h / 2], "rx": knob_r, "ry": knob_r,
         "fill": th.surface},
    ]
    return _group(box, children, "toggle")


def tabs(box: Box | Sequence[str], items: Sequence[str] | None = None, *, active: int = 0,
         theme: Theme | None = None, h: float | None = None) -> Obj:
    """A horizontal tab strip with a baseline rule and an accent underline."""
    th = theme or default_theme()
    if items is None:
        items = [str(item) for item in box]  # type: ignore[union-attr]
        width = sum(measure_text(str(item), font_family=th.font, font_size=13, bold=True) + 30 for item in items)
        box = [0, 0, width, h if h is not None else 36]
    _, _, w, h = _wh(box)
    children: list[Obj] = [_bg([0, h - 1, w, 1], fill=th.line)]
    cx = 0.0
    for i, label in enumerate(items):
        tw = measure_text(str(label), font_family=th.font, font_size=13,
                          bold=True) + 22
        active_tab = i == active
        children.append(_text([cx, 0, tw, h], label,
                              _style(th, 13, weight=700 if active_tab else 600,
                                     color=th.ink if active_tab else th.muted)))
        if active_tab:
            children.append(_bg([cx, h - 2, tw - 18, 2], fill=th.accent, radius=1))
        cx += tw + 8
    return _group(box, children, "tabs")


def progress(box: Box | float, frac: float | None = None, *, tone: str = "accent",
             theme: Theme | None = None, w: float | None = None, h: float | None = None) -> Obj:
    """A progress / meter bar filled to ``frac`` (0..1) in the toned colour."""
    th = theme or default_theme()
    if frac is None:
        frac = float(box)
        box = [0, 0, w if w is not None else 160, h if h is not None else 10]
    _, _, w, h = _wh(box)
    f = max(0.0, min(1.0, float(frac)))
    fg = th.accent if tone == "accent" else _tone(th, tone)[1]
    children = [
        _bg([0, 0, w, h], fill=th.fill, radius=h / 2),
        _rect([0, 0, w * f, h], fill=fg, radius=h / 2),
    ]
    return _group(box, children, "progress")


def divider(box: Box | None = None, *, theme: Theme | None = None,
            w: float | None = None, h: float | None = None) -> Obj:
    """A 1px hairline rule spanning ``box`` (drawn at its vertical centre)."""
    th = theme or default_theme()
    if box is None:
        box = [0, 0, w if w is not None else 160, h if h is not None else 1]
    _, _, w, h = _wh(box)
    return _group(box, [_rect([0, h / 2, w, 1], fill=th.line)], "divider")


def checkbox(box: Box | None = None, *, checked: bool = True,
             label: str | None = None, theme: Theme | None = None) -> Obj:
    """A checkbox with an optional trailing label; the mark is a polyline tick."""
    th = theme or default_theme()
    s = 18.0
    if box is None:
        lw = measure_text(label, font_family=th.font, font_size=13) + 8 if label else 0
        box = [0, 0, s + lw, 20]
    _, _, w, h = _wh(box)
    top = (h - s) / 2
    if checked:
        control = _bg([0, top, s, s], fill=th.accent, radius=4)
    else:
        control = _bg([0, top, s, s], fill=th.surface, stroke=th.line,
                      stroke_style={"stroke_width": 1.0}, radius=4)
    children: list[Obj] = [control]
    if checked:
        children.append({
            "type": "polyline",
            "points": [[4, top + s * 0.52], [s * 0.42, top + s - 5], [s - 4, top + 5]],
            "fill": "none",
            "stroke": th.surface,
            "stroke_style": {"stroke_width": 2.0, "stroke_linecap": "round",
                             "stroke_linejoin": "round"},
            "decorative": True,
        })
    if label:
        children.append(_text([s + 8, 0, w - s - 8, h], label, _style(th, 13)))
    return _group(box, children, "checkbox")


def radio(box: Box | None = None, *, selected: bool = True,
          label: str | None = None, theme: Theme | None = None) -> Obj:
    """A radio button with an optional trailing label; selection is an inner dot."""
    th = theme or default_theme()
    d = 18.0
    if box is None:
        lw = measure_text(label, font_family=th.font, font_size=13) + 8 if label else 0
        box = [0, 0, d + lw, 20]
    _, _, w, h = _wh(box)
    cy = h / 2
    children: list[Obj] = [{
        "type": "ellipse", "center": [d / 2, cy], "rx": d / 2, "ry": d / 2,
        "fill": th.surface, "stroke": th.accent if selected else th.line,
        "stroke_style": {"stroke_width": 1.5 if selected else 1.0},
        "decorative": True,
    }]
    if selected:
        children.append({
            "type": "ellipse", "center": [d / 2, cy], "rx": d * 0.28, "ry": d * 0.28,
            "fill": th.accent, "decorative": True,
        })
    if label:
        children.append(_text([d + 8, 0, w - d - 8, h], label, _style(th, 13)))
    return _group(box, children, "radio")


def slider(box: Box | float, frac: float | None = None, *, tone: str = "accent",
           theme: Theme | None = None, w: float | None = None,
           h: float | None = None) -> Obj:
    """A slider: a track filled to ``frac`` (0..1) with a knob at the value."""
    th = theme or default_theme()
    if frac is None:
        frac = float(box)
        box = [0, 0, w if w is not None else 160, h if h is not None else 20]
    _, _, w, h = _wh(box)
    f = max(0.0, min(1.0, float(frac)))
    fg = th.accent if tone == "accent" else _tone(th, tone)[1]
    track_h = 6.0
    top = (h - track_h) / 2
    knob_r = min(8.0, h / 2)
    kx = knob_r + f * (w - 2 * knob_r)
    children = [
        _bg([0, top, w, track_h], fill=th.fill, radius=track_h / 2),
        _rect([0, top, max(kx, track_h), track_h], fill=fg, radius=track_h / 2,
              decorative=True),
        {"type": "ellipse", "center": [kx, h / 2], "rx": knob_r, "ry": knob_r,
         "fill": th.surface, "stroke": fg, "stroke_style": {"stroke_width": 2.0}},
    ]
    return _group(box, children, "slider")


def breadcrumb(box: Box | Sequence[str], items: Sequence[str] | None = None, *,
               separator: str = "›", theme: Theme | None = None,
               h: float | None = None) -> Obj:
    """A breadcrumb trail; earlier crumbs are muted, the current one is ink."""
    th = theme or default_theme()
    if items is None:
        items = [str(item) for item in box]  # type: ignore[union-attr]
        width = sum(measure_text(str(item), font_family=th.font, font_size=12) + 22
                    for item in items)
        box = [0, 0, width, h if h is not None else 20]
    _, _, w, h = _wh(box)
    children: list[Obj] = []
    cx = 0.0
    last = len(items) - 1
    for i, label in enumerate(items):
        tw = measure_text(str(label), font_family=th.font, font_size=12) + 6
        current = i == last
        children.append(_text([cx, 0, tw, h], label,
                              _style(th, 12, weight=700 if current else 500,
                                     color=th.ink if current else th.muted)))
        cx += tw
        if not current:
            children.append(_text([cx, 0, 12, h], separator,
                                  _style(th, 12, color=th.muted, align="center")))
            cx += 16
    return _group(box, children, "breadcrumb")


def navbar(box: Box, items: Sequence[str], *, brand: str | None = None,
           active: int = 0, theme: Theme | None = None) -> Obj:
    """A top navigation bar: optional brand, link items, accent-underlined active."""
    th = theme or default_theme()
    _, _, w, h = _wh(box)
    children: list[Obj] = [
        _bg([0, 0, w, h], fill=th.surface),
        _bg([0, h - 1, w, 1], fill=th.line),
    ]
    cx = th.pad
    if brand is not None:
        bw = measure_text(str(brand), font_family=th.font, font_size=15, bold=True) + 8
        children.append(_text([cx, 0, bw, h], brand,
                              _style(th, 15, weight=800, color=th.ink)))
        cx += bw + 24
    for i, label in enumerate(items):
        tw = measure_text(str(label), font_family=th.font, font_size=13, bold=True) + 8
        active_item = i == active
        children.append(_text([cx, 0, tw, h], label,
                              _style(th, 13, weight=700 if active_item else 600,
                                     color=th.ink if active_item else th.sub)))
        if active_item:
            children.append(_bg([cx, h - 3, tw - 6, 3], fill=th.accent, radius=1.5))
        cx += tw + 20
    return _group(box, children, "navbar")


def dropdown(box: Box, items: Sequence[str], *, selected: int = 0,
             theme: Theme | None = None) -> Obj:
    """An *open* select: the control on top, the menu panel expanded below it.

    ``box`` spans control **and** menu; the selected option row is highlighted.
    This is the wireframe companion to ``field(kind="select")`` (the closed
    control).
    """
    if items and not (0 <= selected < len(items)):
        raise ValueError(
            f"dropdown selected={selected} is out of range for {len(items)} item(s)")
    th = theme or default_theme()
    _, _, w, h = _wh(box)
    ch = min(th.control_h, h / 2)
    value = str(items[selected]) if items else ""
    children: list[Obj] = [
        _bg([0, 0, w, ch], fill=th.surface, stroke=th.accent,
            stroke_style={"stroke_width": 1.0}, radius=8),
        _text([12, 0, w - 40, ch], value, _style(th, 13, color=th.ink)),
        _text([w - 26, 0, 16, ch], "▴", _style(th, 13, color=th.muted, align="center")),
    ]
    menu_top = ch + 4
    menu_h = h - menu_top
    children.append(_bg([0, menu_top, w, menu_h], fill=th.surface, stroke=th.line,
                        stroke_style={"stroke_width": 1.0}, radius=8))
    if items:
        option_h = menu_h / len(items)
        for i, label in enumerate(items):
            oy = menu_top + i * option_h
            option = i == selected
            if option:
                children.append(_rect([2, oy + 1, w - 4, option_h - 2],
                                      fill=th.accent_soft, radius=6, decorative=True))
            children.append(_text([12, oy, w - 24, option_h], label,
                                  _style(th, 13, weight=600 if option else 400,
                                         color=th.accent if option else th.ink)))
    return _group(box, children, "dropdown")


def image_placeholder(box: Box, *, label: str | None = None,
                      theme: Theme | None = None) -> Obj:
    """A wireframe image slot: a bordered box crossed corner-to-corner, with an
    optional centred label."""
    th = theme or default_theme()
    _, _, w, h = _wh(box)
    line_style = {"stroke": th.line, "stroke_style": {"stroke_width": 1.0},
                  "decorative": True}
    children: list[Obj] = [
        _bg([0, 0, w, h], fill=th.fill, stroke=th.line,
            stroke_style={"stroke_width": 1.0}, radius=4),
        {"type": "line", "from": [0, 0], "to": [w, h], **line_style},
        {"type": "line", "from": [0, h], "to": [w, 0], **line_style},
    ]
    if label:
        children.append(_text([0, 0, w, h], label,
                              _style(th, 12, weight=600, color=th.muted,
                                     align="center")))
    return _group(box, children, "image_placeholder")


def sticky_note(box: Box, text: str, *, tone: str = "warn",
                theme: Theme | None = None, **fields: Any) -> Obj:
    """An annotation note with a folded corner, marked ``decorative`` so it is
    excluded from a11y/reading order and the overlap audit (a review artefact,
    not content). Give it an ``id`` and hide it per render target
    (``define_target(..., hide=[id])``) to keep notes out of print output.
    """
    th = theme or default_theme()
    _, _, w, h = _wh(box)
    bg, fg = _tone(th, tone)
    fold = min(14.0, w / 4, h / 4)
    children: list[Obj] = [
        {"type": "polyline", "closed": True, "fill": bg, "decorative": True,
         "points": [[0, 0], [w, 0], [w, h - fold], [w - fold, h], [0, h]]},
        {"type": "polyline", "closed": True, "fill": fg, "fill_opacity": 0.3,
         "decorative": True,
         "points": [[w - fold, h], [w, h - fold], [w - fold, h - fold]]},
        _text([10, 8, w - 20, h - fold - 12], text,
              _style(th, 12, color=th.ink, valign="top", nowrap=False, fit="clip")),
    ]
    return _group(box, children, "sticky_note", decorative=True, **fields)


# --------------------------------------------------------------------------- #
#  containers
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Panel:
    """A container widget's result: the chrome ``object`` and an absolute
    ``content`` box (``[x, y, w, h]``) to author the body into."""

    object: Obj
    content: list[float]


def card(box: Box, *, title: str | None = None, action: str | None = None,
         pad: float | None = None, fill: str | None = None,
         theme: Theme | None = None) -> Panel:
    """A surface card with optional title row and a right-aligned action link.

    Returns a :class:`Panel`; add ``panel.object`` then author into
    ``panel.content`` (absolute coordinates), e.g. with :func:`table` or atoms.
    """
    th = theme or default_theme()
    x, y, w, h = _wh(box)
    p = th.pad if pad is None else pad
    children: list[Obj] = [
        _bg([0, 0, w, h], fill=fill or th.surface, stroke=th.line,
            stroke_style={"stroke_width": 1.0}, radius=12),
    ]
    body_top = p
    if title is not None:
        children.append(_text([p, p, w - 2 * p - 120, 18], title,
                              _style(th, 15, weight=700, color=th.ink, valign="top")))
        if action is not None:
            children.append(_text([w - p - 90, p + 1, 90, 16], action,
                                  _style(th, 12, weight=700, color=th.accent,
                                         align="right", valign="top")))
        body_top = p + 30
    content = [x + p, y + body_top, w - 2 * p, h - body_top - p]
    return Panel(_group(box, children, "card"), content)


def table(
    box: Box,
    columns: Sequence[Any],
    rows: Sequence[Sequence[Any]],
    *,
    header: bool = True,
    zebra: bool = True,
    row_height: float = 44.0,
    header_height: float = 40.0,
    theme: Theme | None = None,
) -> Obj:
    """A data table that lowers to a first-class ``TableObject``.

    ``columns`` items are either a label string or a mapping
    ``{"label", "width", "align"}`` (``width`` may be a number, ``"<n>%"``,
    ``"<n>fr"`` or ``"auto"``). ``rows`` are lists of cell values (strings or
    numbers). Emitting a real table — rather than positioned text — silences the
    ``tabular-box-model`` warning and clips every cell to its column.
    """
    x, y, w, h = _wh(box)
    labels: list[str] = []
    specs: list[Any] = []
    for col in columns:
        if isinstance(col, dict):
            labels.append(str(col.get("label", "")))
            spec = {k: col[k] for k in ("label", "width", "align") if k in col}
            specs.append(spec or "")
        else:
            labels.append(str(col))
            specs.append(str(col))
    th = theme or default_theme()
    obj: Obj = {
        "type": "table",
        "box": [x, y, w, h],
        "rows": [list(r) for r in rows],
        "columns": specs,
        "zebra": zebra,
        "row_height": row_height,
        "meta": {"widget": "table"},
        # Theme the header through `style` so `theme=` reaches the rendered table
        # (the renderer reads style.header_fill / header_text; without this it falls
        # back to a fixed blue, silently ignoring the theme).
        "style": {
            "header_fill": th.ink,
            "header_text": {"color": th.surface, "font_weight": 700},
        },
    }
    if header:
        obj["header"] = labels
        obj["header_height"] = header_height
    return obj
