"""Human-legibility signals — "the render succeeded, but nobody can read it".

FrameForge already reports what a render *lost*: clipped text (``truncations``),
provable layout overflow (``overflow``), accidental ink overlap (``collisions``).
This module reports the other failure mode — content that was rendered
faithfully and is still unreadable:

  * ``type-too-small``          type below the legible floor for the page;
  * ``low-contrast``            text fails WCAG 2.1 SC 1.4.3 against the ink
                                actually painted behind it;
  * ``contrast-unverified``     a backdrop the pass refuses to guess at;
  * ``measure-too-long/short``  line length outside the trackable range;
  * ``leading-too-tight``       successive baselines too close to separate;
  * ``print-scale-mismatch``    the canvas exports at a different physical size
                                than its name suggests.

DRIFT-PROOF BY CONSTRUCTION
---------------------------
Every check reads the **emitted SVG**, not the model — the same sink the design
audit uses (``rendering.application.audit``). A feature added later that draws
text is measured with no new instrumentation here, because it must pass through
``<text>``/``<tspan>`` to be seen at all.

THE UNIT PROBLEM (why type size is judged as a fraction of the page)
-------------------------------------------------------------------
A canvas unit has no fixed physical meaning. The same "10" is 10 pt on a
595x842 points-based canvas and 7.5 pt on a 794x1123 CSS-pixel canvas — and an
authoring agent that conflates the two ships a document ~25% smaller than
intended. The only dpi-independent statement is proportional: *this glyph is
1/N of the page width*. That is the gate. The pt equivalent is reported in
``basis`` for the SVG->PDF export path, where one canvas unit is 0.75 pt
(CairoSVG ``svg2pdf(dpi=96)``, pinned in ``frameforge.mcp.pipeline._export_pdf``;
measured: a 595x842 canvas yields a 446.2x631.5 pt page).

NO GUESSING (PALS's Law)
------------------------
A backdrop that cannot be resolved — a transform in scope, a gradient/pattern
paint, an unknown colour keyword — is never assumed to be white. It is counted
and reported as ``contrast-unverified`` so the gap is visible rather than
silently scored as a pass.

The wire form is ``to_dict()`` (JSON-safe dicts inside
``diagnostics["legibility"]``); ``from_dict`` restores the typed value.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

__all__ = ["LegibilitySignal", "LegibilityPolicy", "assess_pages"]


# --------------------------------------------------------------------------- #
#  Policy — every threshold explicit, sourced, and overridable                #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LegibilityPolicy:
    """Thresholds for the legibility gate.

    The contrast numbers are normative (W3C WCAG 2.1 SC 1.4.3,
    https://www.w3.org/TR/WCAG21/#contrast-minimum). The measure range follows
    Bringhurst, *The Elements of Typographic Style*, 2.1.2 (45-75 characters,
    66 as the satisfactory single-column line); the gate's bounds are set wider
    than the ideal so only genuinely untrackable lines are flagged.

    The type-size fractions are a FrameForge convention, not a standard: 1/70
    of the page width reproduces ~8.5 pt on ISO A4 and ~27 px on a 1920-wide
    deck, which are the conventional floors for those media. Operators who set
    a house minimum should override them rather than argue with the default.
    """

    #: warn below this fraction of the page width
    min_size_fraction: float = 1 / 70
    #: escalate to error below this fraction of the page width
    hard_size_fraction: float = 1 / 95
    #: WCAG 2.1 SC 1.4.3 minimum for normal text
    contrast_normal: float = 4.5
    #: WCAG 2.1 SC 1.4.3 minimum for large text
    contrast_large: float = 3.0
    #: WCAG "large text" floor in CSS px (18 pt = 24 px)
    large_px: float = 24.0
    #: WCAG "large text" floor in CSS px when bold (14 pt = 18.66 px)
    large_bold_px: float = 18.66
    #: font-weight at or above which text counts as bold
    bold_weight: int = 700
    #: warn above this many characters per line (multi-line text only)
    max_measure_ch: float = 100.0
    #: warn below this many characters per line (multi-line text only)
    min_measure_ch: float = 25.0
    #: warn below this baseline-to-baseline distance, in ems
    min_leading_em: float = 1.15
    #: SVG canvas unit -> PostScript point, on the CairoSVG dpi=96 export path
    pt_per_unit: float = 0.75


DEFAULT_POLICY = LegibilityPolicy()


# --------------------------------------------------------------------------- #
#  Signal                                                                     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LegibilitySignal:
    """One provable readability failure, measured on the emitted SVG.

    Fields:
      * ``page``      — 1-based page index within the rendered set.
      * ``code``      — the failing check (see the module docstring).
      * ``level``     — ``"error"`` (unreadable), ``"warn"`` (below the floor),
        or ``"info"`` (worth knowing; never nags the render warning).
      * ``value`` / ``threshold`` / ``unit`` — the measurement, what it had to
        beat, and the scale it is stated in.
      * ``count``     — how many text runs share this exact signal (signals are
        aggregated per page and per offending value, so a page of 400 captions
        is one line of feedback, not 400).
      * ``detail``    — a short head of an offending run, for locating it.
      * ``basis``     — how the number was arrived at, including the physical
        equivalent where one is defensible.
    """

    page: Optional[int]
    code: str
    level: str
    value: float
    threshold: float
    unit: str
    count: int = 1
    detail: str = ""
    basis: str = ""

    def to_dict(self) -> dict[str, Any]:
        """The JSON-safe wire form used in ``diagnostics["legibility"]``."""
        return {
            "page": self.page,
            "code": self.code,
            "level": self.level,
            "value": float(self.value),
            "threshold": float(self.threshold),
            "unit": self.unit,
            "count": int(self.count),
            "detail": self.detail,
            "basis": self.basis,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LegibilitySignal":
        """Restore a typed signal from its ``to_dict`` wire form."""
        return cls(
            page=data.get("page"),
            code=str(data.get("code", "")),
            level=str(data.get("level", "")),
            value=float(data.get("value", 0.0)),
            threshold=float(data.get("threshold", 0.0)),
            unit=str(data.get("unit", "")),
            count=int(data.get("count", 1)),
            detail=str(data.get("detail", "")),
            basis=str(data.get("basis", "")),
        )


# --------------------------------------------------------------------------- #
#  SVG reading (the drift-proof sink)                                         #
# --------------------------------------------------------------------------- #
_TOKEN = re.compile(r"<(/?)([A-Za-z][\w:-]*)\b([^>]*?)(/?)>", re.S)
_ATTR = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')
_NUM = re.compile(r"-?(?:\d+\.?\d*|\.\d+)")
_ENTITY = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'"}

# The colour keywords the renderer itself emits (page ground, default inks) plus
# the CSS basic set. Anything outside this map is UNRESOLVED, never guessed.
_KEYWORDS = {
    "white": "#ffffff", "black": "#000000", "silver": "#c0c0c0",
    "gray": "#808080", "grey": "#808080", "red": "#ff0000", "maroon": "#800000",
    "yellow": "#ffff00", "olive": "#808000", "lime": "#00ff00",
    "green": "#008000", "aqua": "#00ffff", "cyan": "#00ffff", "teal": "#008080",
    "blue": "#0000ff", "navy": "#000080", "fuchsia": "#ff00ff",
    "magenta": "#ff00ff", "purple": "#800080", "orange": "#ffa500",
}
# Inherited presentation properties this pass cares about.
_INHERITED = ("font-size", "fill", "font-weight", "fill-opacity", "opacity")


def _decls(attr_str: str) -> dict[str, str]:
    """Presentation attributes and ``style=""`` declarations as one map
    (style wins, mirroring CSS)."""
    props: dict[str, str] = {}
    for key, value in _ATTR.findall(attr_str):
        if key == "style":
            for decl in value.split(";"):
                if ":" in decl:
                    pk, pv = decl.split(":", 1)
                    props[pk.strip().lower()] = pv.strip()
        else:
            props[key.strip().lower()] = value.strip()
    return props


def _num(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    match = _NUM.search(str(value))
    return float(match.group()) if match else default


def _unescape(text: str) -> str:
    for entity, char in _ENTITY.items():
        text = text.replace(entity, char)
    return text


def _rgb(color: Optional[str]) -> Optional[tuple[int, int, int]]:
    """``#rgb`` / ``#rrggbb`` / ``#rrggbbaa`` / basic keyword -> RGB, else None.

    ``None`` means *unresolved*, and every caller must treat it as unknown
    rather than substituting a default (PALS's Law)."""
    if not color:
        return None
    value = color.strip().lower()
    value = _KEYWORDS.get(value, value)
    if not value.startswith("#"):
        return None
    digits = value[1:]
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    if len(digits) == 8:  # #rrggbbaa — alpha handled via opacity compositing
        digits = digits[:6]
    if len(digits) != 6 or any(c not in "0123456789abcdef" for c in digits):
        return None
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def _luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG 2.1 relative luminance
    (https://www.w3.org/TR/WCAG21/#dfn-relative-luminance)."""
    def linear(channel: int) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)


def _contrast(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    """WCAG 2.1 contrast ratio, 1.0-21.0
    (https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio)."""
    lf, lb = _luminance(fg), _luminance(bg)
    lighter, darker = max(lf, lb), min(lf, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _over(fg: tuple[int, int, int], bg: tuple[int, int, int],
          alpha: float) -> tuple[int, int, int]:
    """Source-over composite — a translucent ink is judged at the colour the
    reader actually sees, not at its nominal value."""
    if alpha >= 1.0:
        return fg
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))  # type: ignore[return-value]


@dataclass(frozen=True)
class _Rect:
    x: float
    y: float
    w: float
    h: float
    rgb: Optional[tuple[int, int, int]]
    resolved: bool

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x <= self.x + self.w and self.y <= y <= self.y + self.h


@dataclass(frozen=True)
class _Line:
    text: str
    x: float
    y: float
    dy: Optional[float]


@dataclass(frozen=True)
class _Run:
    """One ``<text>`` element as read off the SVG."""
    size: float
    fill: Optional[str]
    weight: str
    opacity: float
    lines: tuple[_Line, ...]
    transformed: bool
    backdrops: tuple[_Rect, ...]


def _parse_page(svg: str) -> tuple[float, float, list[_Run]]:
    """Read a page SVG into (width, height, text runs), with each run carrying
    the rects painted before it (painter's order = document order)."""
    width = height = 0.0
    rects: list[_Rect] = []
    runs: list[_Run] = []
    stack: list[dict[str, str]] = [{}]
    transform_depth = 0
    in_text: Optional[dict[str, Any]] = None
    pos = 0

    for token in _TOKEN.finditer(svg):
        closing, tag, attrs, self_closing = (
            token.group(1), token.group(2).lower(), token.group(3), token.group(4))

        # text content of the element that just closed / the span we are inside
        if in_text is not None and in_text.get("open_span") is not None:
            chunk = _unescape(svg[pos:token.start()]).strip()
            if chunk:
                span = in_text["open_span"]
                in_text["lines"].append(_Line(chunk, span["x"], span["y"], span["dy"]))
            in_text["open_span"] = None
        pos = token.end()

        if closing:
            if tag in ("g", "svg", "a", "defs", "clippath", "mask", "pattern",
                       "lineargradient", "radialgradient", "symbol", "marker"):
                if stack[-1].get("_transform"):
                    transform_depth -= 1
                if len(stack) > 1:
                    stack.pop()
            elif tag == "text" and in_text is not None:
                runs.append(_Run(
                    size=in_text["size"],
                    fill=in_text["fill"],
                    weight=in_text["weight"],
                    opacity=in_text["opacity"],
                    lines=tuple(in_text["lines"]),
                    transformed=in_text["transformed"],
                    backdrops=tuple(rects),
                ))
                in_text = None
            continue

        props = _decls(attrs)
        inherited = dict(stack[-1])
        for key in _INHERITED:
            if key in props:
                inherited[key] = props[key]

        if tag == "svg" and width == 0.0:
            width = _num(props.get("width"), 0.0) or 0.0
            height = _num(props.get("height"), 0.0) or 0.0
            if not width:
                box = [float(v) for v in _NUM.findall(props.get("viewbox", ""))]
                if len(box) == 4:
                    width, height = box[2], box[3]

        if tag == "text":
            in_text = {
                "size": _num(inherited.get("font-size"), 16.0) or 16.0,
                "fill": inherited.get("fill", "#000000"),
                "weight": str(inherited.get("font-weight", "400")),
                "opacity": _opacity(inherited),
                "lines": [],
                "transformed": bool(transform_depth) or "transform" in props,
                "open_span": {"x": _num(props.get("x"), 0.0) or 0.0,
                              "y": _num(props.get("y"), 0.0) or 0.0,
                              "dy": _num(props.get("dy"))},
                "y": _num(props.get("y"), 0.0) or 0.0,
                "x": _num(props.get("x"), 0.0) or 0.0,
            }
        elif tag == "tspan" and in_text is not None:
            dy = _num(props.get("dy"))
            base_y = in_text["lines"][-1].y if in_text["lines"] else in_text["y"]
            in_text["open_span"] = {
                "x": _num(props.get("x"), in_text["x"]) or 0.0,
                "y": (base_y + dy) if dy is not None else _num(props.get("y"), base_y),
                "dy": dy,
            }
            if "font-size" in props:
                in_text["size"] = _num(props["font-size"], in_text["size"])
            if "fill" in props:
                in_text["fill"] = props["fill"]
        elif tag == "rect" and in_text is None:
            rects.append(_rect_of(props, inherited, width, height, transform_depth))

        if tag in ("g", "svg", "a", "defs", "clippath", "mask", "pattern",
                   "lineargradient", "radialgradient", "symbol", "marker") \
                and not self_closing:
            if "transform" in props:
                inherited["_transform"] = "1"
                transform_depth += 1
            stack.append(inherited)

    return width, height, runs


def _opacity(props: dict[str, str]) -> float:
    alpha = 1.0
    for key in ("opacity", "fill-opacity"):
        value = _num(props.get(key))
        if value is not None:
            alpha *= max(0.0, min(1.0, value))
    return alpha


def _rect_of(props: dict[str, str], inherited: dict[str, str],
             page_w: float, page_h: float, transform_depth: int) -> _Rect:
    """A painted rect as a candidate backdrop. ``100%`` sizing (the renderer's
    page-ground rect) resolves against the canvas."""
    def dim(key: str, full: float) -> float:
        raw = props.get(key, "0")
        if raw.strip().endswith("%"):
            return full * (_num(raw, 0.0) or 0.0) / 100.0
        return _num(raw, 0.0) or 0.0

    fill = props.get("fill", inherited.get("fill"))
    rgb = _rgb(fill)
    unpaintable = (
        fill in (None, "none", "")
        or (fill is not None and fill.strip().lower().startswith("url("))
        or transform_depth > 0
        or "transform" in props
        or _opacity({**inherited, **props}) < 1.0
    )
    return _Rect(
        x=dim("x", page_w), y=dim("y", page_h),
        w=dim("width", page_w), h=dim("height", page_h),
        rgb=None if unpaintable else rgb,
        # a fill that exists but does not resolve to a colour still OCCLUDES:
        # it must stop the search, or the pass would score against a ground
        # that is not visible (a gradient page ground judged as white).
        resolved=not unpaintable and rgb is not None,
    )


def _backdrop(run: _Run, line: _Line) -> tuple[Optional[tuple[int, int, int]], bool]:
    """The ink behind a line: the topmost rect painted before this text whose
    box contains the baseline anchor. Returns ``(rgb, resolved)`` — an occluding
    but unresolvable ground yields ``(None, False)``, never a substituted white.
    """
    if run.transformed:
        return None, False
    for rect in reversed(run.backdrops):
        if rect.w <= 0 or rect.h <= 0:
            continue
        if rect.rgb is None and not rect.resolved:
            # An unpaintable/unresolved rect only blocks when it covers the
            # point; a `fill="none"` frame must not hide the ground beneath it.
            if rect.contains(line.x, line.y) and _occludes(rect):
                return None, False
            continue
        if rect.contains(line.x, line.y):
            return rect.rgb, True
    return None, False


def _occludes(rect: _Rect) -> bool:
    """An unresolved rect hides what is under it unless it paints nothing."""
    return rect.rgb is None and rect.resolved is False


# --------------------------------------------------------------------------- #
#  Standard sheets (for the physical-scale note)                              #
# --------------------------------------------------------------------------- #
#: nominal trim sizes in inches, for naming a canvas' real export size
_SHEETS_IN = {
    "ISO A3": (11.693, 16.535), "ISO A4": (8.268, 11.693), "ISO A5": (5.827, 8.268),
    "US Letter": (8.5, 11.0), "US Legal": (8.5, 14.0), "US Tabloid": (11.0, 17.0),
}
#: canvas sizes FrameForge presets emit in POINTS, with the paper they are named
#: after — the source of the "my body text is 25% too small" class of bug.
_POINT_PRESETS = {
    (842.0, 1191.0): "ISO A3", (595.0, 842.0): "ISO A4", (419.5, 595.3): "ISO A5",
    (612.0, 792.0): "US Letter", (612.0, 1008.0): "US Legal",
    (792.0, 1224.0): "US Tabloid",
}


def _sheet_note(w: float, h: float, policy: LegibilityPolicy) -> Optional[LegibilitySignal]:
    """Name the page's real export size when the canvas is a points-based paper
    preset — those export ~25% smaller than the paper they are named after."""
    key = next((k for k in _POINT_PRESETS
                if abs(k[0] - w) < 0.6 and abs(k[1] - h) < 0.6), None)
    if key is None:
        return None
    named = _POINT_PRESETS[key]
    in_w = w * policy.pt_per_unit / 72.0
    in_h = h * policy.pt_per_unit / 72.0
    sheet_w, sheet_h = _SHEETS_IN[named]
    if abs(in_w - sheet_w) < sheet_w * 0.01:
        return None
    ratio = sheet_w / in_w if in_w else 0.0
    return LegibilitySignal(
        page=None,
        code="print-scale-mismatch",
        level="info",
        value=round(in_w, 2),
        threshold=round(sheet_w, 2),
        unit="in",
        detail=named,
        basis=(f"canvas {_g(w)}x{_g(h)} units exports to {in_w:.2f}x{in_h:.2f} in "
               f"through the SVG->PDF path (1 unit = {policy.pt_per_unit} pt), not "
               f"{named} ({sheet_w:.2f}x{sheet_h:.2f} in) — every size on this page "
               f"prints {ratio:.2f}x smaller than its number suggests; author the "
               f"canvas as {_g(w / policy.pt_per_unit)}x{_g(h / policy.pt_per_unit)} "
               f"units (or with explicit `units`) for true {named}"),
    )


def _g(value: float) -> str:
    return f"{value:g}"


# --------------------------------------------------------------------------- #
#  The gate                                                                   #
# --------------------------------------------------------------------------- #
def assess_pages(svg_pages: Iterable[str],
                 *, policy: Optional[LegibilityPolicy] = None) -> list[LegibilitySignal]:
    """Assess rendered page SVGs for human legibility.

    Returns the signals, most severe first, aggregated per page and per
    offending value so a page of 400 small captions is one line of feedback.
    An empty list means every readable-content check passed.
    """
    pol = policy or DEFAULT_POLICY
    signals: list[LegibilitySignal] = []
    seen_scale: set[tuple[float, float]] = set()

    for index, svg in enumerate(svg_pages, start=1):
        width, height, runs = _parse_page(svg)
        if width <= 0:
            continue
        if (width, height) not in seen_scale:
            seen_scale.add((width, height))
            note = _sheet_note(width, height, pol)
            if note is not None:
                signals.append(note)
        signals.extend(_assess_page(index, width, runs, pol))

    order = {"error": 0, "warn": 1, "info": 2}
    signals.sort(key=lambda s: (order.get(s.level, 3), s.code, s.page or 0))
    return signals


def _assess_page(page: int, width: float, runs: list[_Run],
                 pol: LegibilityPolicy) -> list[LegibilitySignal]:
    small: dict[float, list[str]] = {}
    low: dict[tuple[float, float], list[str]] = {}
    unverified: list[str] = []
    long_measure: list[tuple[float, str]] = []
    short_measure: list[tuple[float, str]] = []
    tight: list[tuple[float, str]] = []

    for run in runs:
        text = " ".join(line.text for line in run.lines).strip()
        if not text:
            continue
        head = text[:48]

        # --- type size (proportional; dpi-independent) ---
        if run.size / width < pol.min_size_fraction:
            small.setdefault(round(run.size, 3), []).append(head)

        # --- contrast (WCAG 2.1 SC 1.4.3) ---
        fg = _rgb(run.fill)
        need = (pol.contrast_large if _is_large(run, pol) else pol.contrast_normal)
        worst: Optional[float] = None
        for line in run.lines:
            if not line.text.strip():
                continue
            bg, resolved = _backdrop(run, line)
            if fg is None or bg is None or not resolved:
                if head not in unverified:
                    unverified.append(head)
                continue
            ratio = _contrast(_over(fg, bg, run.opacity), bg)
            worst = ratio if worst is None else min(worst, ratio)
        if worst is not None and worst < need:
            low.setdefault((round(worst, 2), need), []).append(head)

        # --- measure and leading (multi-line text only) ---
        lines = [line for line in run.lines if line.text.strip()]
        if len(lines) >= 2:
            lengths = sorted(len(line.text) for line in lines)
            median = lengths[len(lengths) // 2]
            if median > pol.max_measure_ch:
                long_measure.append((float(median), head))
            elif median < pol.min_measure_ch:
                short_measure.append((float(median), head))
            leads = [line.dy for line in lines[1:] if line.dy]
            if leads and run.size > 0:
                em = min(leads) / run.size
                if em < pol.min_leading_em:
                    tight.append((round(em, 3), head))

    out: list[LegibilitySignal] = []
    for size, heads in sorted(small.items()):
        fraction = size / width
        level = "error" if fraction < pol.hard_size_fraction else "warn"
        out.append(LegibilitySignal(
            page=page, code="type-too-small", level=level,
            value=round(size, 3), threshold=round(width * pol.min_size_fraction, 2),
            unit="canvas units", count=len(heads), detail=heads[0],
            basis=(f"{_g(size)} units on a {_g(width)}-unit-wide page = 1/{1/fraction:.0f} "
                   f"of the measure ({size * pol.pt_per_unit:.1f} pt if this page "
                   f"exports at {pol.pt_per_unit} pt/unit); the floor is "
                   f"1/{1/pol.min_size_fraction:.0f} "
                   f"(>= {width * pol.min_size_fraction:.1f} units)"),
        ))
    for (ratio, need), heads in sorted(low.items()):
        out.append(LegibilitySignal(
            page=page, code="low-contrast",
            level="error" if ratio < need / 1.5 else "warn",
            value=ratio, threshold=need, unit="contrast ratio",
            count=len(heads), detail=heads[0],
            basis=(f"{ratio:.2f}:1 against the ink painted behind it; WCAG 2.1 "
                   f"SC 1.4.3 requires {need}:1 "
                   f"({'large' if need == pol.contrast_large else 'normal'} text)"),
        ))
    if unverified:
        out.append(LegibilitySignal(
            page=page, code="contrast-unverified", level="info",
            value=float(len(unverified)), threshold=0.0, unit="runs",
            count=len(unverified), detail=unverified[0],
            basis=("backdrop not resolvable from the emitted SVG (transform in "
                   "scope, gradient/pattern/image ground, or an unknown colour "
                   "keyword); NOT scored as a pass — verify these by eye or "
                   "against the raster"),
        ))
    for values, code, unit, note in (
        (long_measure, "measure-too-long", "characters",
         f"longer than {pol.max_measure_ch:g} characters; the eye loses the "
         f"line return (Bringhurst 2.1.2 puts the satisfactory range at 45-75)"),
        (short_measure, "measure-too-short", "characters",
         f"shorter than {pol.min_measure_ch:g} characters; the rhythm breaks up "
         f"(Bringhurst 2.1.2 puts the satisfactory range at 45-75)"),
        (tight, "leading-too-tight", "em",
         f"baseline-to-baseline below {pol.min_leading_em:g} em; ascenders and "
         f"descenders of adjacent lines collide"),
    ):
        if not values:
            continue
        worst_value, head = (max(values) if code == "measure-too-long" else min(values))
        threshold = (pol.max_measure_ch if code == "measure-too-long"
                     else pol.min_measure_ch if code == "measure-too-short"
                     else pol.min_leading_em)
        out.append(LegibilitySignal(
            page=page, code=code, level="warn", value=float(worst_value),
            threshold=float(threshold), unit=unit, count=len(values),
            detail=head, basis=f"{worst_value:g} {unit} — {note}",
        ))
    return out


def _is_large(run: _Run, pol: LegibilityPolicy) -> bool:
    """WCAG 2.1 "large scale" text: >= 18 pt, or >= 14 pt bold — expressed in
    CSS px, which is what a canvas unit is on the SVG path."""
    weight = _num(run.weight)
    bold = (weight is not None and weight >= pol.bold_weight) or \
        run.weight.strip().lower() in ("bold", "bolder")
    return run.size >= (pol.large_bold_px if bold else pol.large_px)
