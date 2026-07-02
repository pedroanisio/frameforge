"""Chevreul colour canon — the painter's wheel, the six harmonies, tone, and the grey test.

Codifies the working rules of M. E. Chevreul, *De la loi du contraste simultané
des couleurs* (Paris, 1839; read in its English translations, *The Principles of
Harmony and Contrast of Colours*): the 12-station red–yellow–blue painter's
wheel, complementaries as wheel opposites, tone scales ("the assemblage of tones
of the same colour"), and the **six harmonies** — three of analogy (scale, hues,
dominant light) and three of contrast (scale, hues, colours).

Two numeric primitives are *not* Chevreul's but WCAG 2.1's, cited because they
are the verifiable modern formulation of his tone axis
(https://www.w3.org/TR/WCAG21/#dfn-relative-luminance):
:func:`relative_luminance` and :func:`contrast_ratio`. They also back
:func:`to_grey` / :func:`grey_document` — the "grey test": strip the hue from a
composition and its skeleton of light and dark remains, or is revealed to be
missing.

Design intent: give document authors (human or agent) *decided* colour systems
instead of ad-hoc picks — a :func:`closed_palette` assigns every colour a duty
(ground / ink / accent / quiet steps) with an area guide, and emits a ready
``defs.tokens.colors`` fragment::

    from framegraph.sdk import chevreul

    palette = chevreul.closed_palette(ground="#fbf8f1", ink="#1d1e22",
                                      accent="#b5402c")
    doc.tokens(colors=palette.tokens())
    accents = chevreul.harmony_of_hues("blue", n=3)     # analogous accents
    light, dark = chevreul.contrast_of_scale("#33689c")  # one scale, awake

The station hexes in :data:`WHEEL` are canonical *defaults* (a design choice,
not a derived constant); every function accepts explicit colours, so any other
wheel realisation composes the same way.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

Color = str

# The 12 stations of the painter's (RYB) wheel, in wheel order. Neighbours
# share pigment; opposites (6 stations apart) share nothing — Chevreul's map
# for every harmony below. Hexes are canonical defaults, override at will.
WHEEL: dict[str, Color] = {
    "red": "#d7332f",
    "red-orange": "#e2612c",
    "orange": "#eb8b2d",
    "yellow-orange": "#f0b32e",
    "yellow": "#eecf3a",
    "yellow-green": "#a9c04a",
    "green": "#5d9e52",
    "blue-green": "#3d8f7c",
    "blue": "#33689c",
    "blue-violet": "#4a4e8f",
    "violet": "#6d4a86",
    "red-violet": "#a03d69",
}

# Area duties of a closed palette (the book-design register: ground ~62%,
# text & structure ~30%, accent ~8%). Guidance, not a validator rule.
AREA_GUIDE: dict[str, float] = {"ground": 0.62, "text_structure": 0.30, "accent": 0.08}

_STATIONS = list(WHEEL)


def _norm_station(name: str) -> str:
    key = name.strip().lower().replace("_", "-")
    if key not in WHEEL:
        raise ValueError(f"unknown wheel station {name!r}; expected one of {_STATIONS}")
    return key


def _parse_hex(color: Color) -> tuple[int, int, int]:
    value = color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) != 6:
        raise ValueError(f"expected a #rrggbb colour, got {color!r}")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _to_hex(rgb: Sequence[float]) -> Color:
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def _mix(a: Color, b: Color, t: float) -> Color:
    ra, ga, ba = _parse_hex(a)
    rb, gb, bb = _parse_hex(b)
    return _to_hex((ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t))


def _rgb_distance(a: Color, b: Color) -> float:
    return sum((x - y) ** 2 for x, y in zip(_parse_hex(a), _parse_hex(b))) ** 0.5


# ── tone: the WCAG numerics ───────────────────────────────────────────────


def relative_luminance(color: Color) -> float:
    """WCAG 2.1 relative luminance of an ``#rrggbb`` colour (0.0 – 1.0).

    ``L = 0.2126 R + 0.7152 G + 0.0722 B`` over linearised sRGB channels
    (https://www.w3.org/TR/WCAG21/#dfn-relative-luminance).
    """
    def linear(channel: int) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _parse_hex(color)
    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)


def contrast_ratio(a: Color, b: Color) -> float:
    """WCAG 2.1 contrast ratio between two colours (1.0 – 21.0), symmetric.

    ``(L_lighter + 0.05) / (L_darker + 0.05)``
    (https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio). This is the numeric
    form of Chevreul's contrast of tone — and the primitive a text-on-ground
    legibility check needs.
    """
    la, lb = relative_luminance(a), relative_luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def tone_scale(color: Color, steps: int = 9) -> list[Color]:
    """A Chevreul tone ladder: light tones → the pure colour → deep tones.

    "The assemblage of tones of the same colour … the pure colour is the
    normal tone of the scale." Returns ``steps`` colours from near-white to
    near-black with ``color`` as the middle (normal) tone. Mixes are sRGB
    lerps — a pragmatic ladder, not a perceptually uniform ramp. (In pigment
    the normal tone's rank varies by scale — yellow reaches full intensity
    while still light; parameterise by slicing if that matters.)
    """
    if steps < 3:
        raise ValueError("a tone scale needs at least 3 steps")
    half = steps // 2
    light = [_mix("#ffffff", color, (i + 1) / (half + 1)) for i in range(half)]
    dark = [_mix(color, "#000000", (i + 1) / (steps - half)) for i in range(steps - half - 1)]
    return light + [color] + dark


def to_grey(color: Color) -> Color:
    """The luminance-matched grey of a colour (hue stripped, tone kept)."""
    lum = relative_luminance(color)
    # invert the sRGB transfer so the grey's relative luminance matches
    c = lum * 12.92 if lum <= 0.0031308 else 1.055 * lum ** (1 / 2.4) - 0.055
    return _to_hex((c * 255,) * 3)


# ── the wheel ─────────────────────────────────────────────────────────────


def complement_name(station: str) -> str:
    """The opposite station's name — six stations away on the wheel."""
    idx = _STATIONS.index(_norm_station(station))
    return _STATIONS[(idx + 6) % 12]


def complement(station: str) -> Color:
    """The complementary colour of a wheel station (its afterimage and its
    loudest neighbour)."""
    return WHEEL[complement_name(station)]


def nearest_station(color: Color) -> str:
    """The wheel station nearest to a colour (RGB distance — approximate;
    good for classifying palette members, not for colour science)."""
    return min(WHEEL, key=lambda name: _rgb_distance(color, WHEEL[name]))


# ── the six harmonies ────────────────────────────────────────────────────


def harmony_of_scale(color: Color, n: int = 5) -> list[Color]:
    """Analogy 1 — tones of one scale, read in order (the monochrome)."""
    if n < 2:
        raise ValueError("a harmony needs at least 2 colours")
    ladder = tone_scale(color, steps=max(n, 5))
    step = (len(ladder) - 1) / (n - 1)
    return [ladder[round(i * step)] for i in range(n)]


def harmony_of_hues(station: str, n: int = 3, tone: int | None = None) -> list[Color]:
    """Analogy 2 — like tones of neighbouring scales (the analogous palette:
    a walk along the wheel without crossing it)."""
    if n < 2:
        raise ValueError("a harmony needs at least 2 colours")
    centre = _STATIONS.index(_norm_station(station))
    offsets = range(-(n // 2), -(n // 2) + n)
    colours = [WHEEL[_STATIONS[(centre + off) % 12]] for off in offsets]
    if tone is not None:
        colours = [tone_scale(c)[tone] for c in colours]
    return colours


def dominant_light(colors: Sequence[Color], tint: Color, strength: float = 0.35) -> list[Color]:
    """Analogy 3 — many colours seen through one tint ("as would result from
    the view of these colours through a slightly-coloured glass")."""
    if not 0.0 <= strength <= 1.0:
        raise ValueError("strength must be within [0, 1]")
    return [_mix(c, tint, strength) for c in colors]


def contrast_of_scale(color: Color) -> tuple[Color, Color]:
    """Contrast 1 — two very distant tones of one scale (the monochrome,
    awake). The safest strong statement in colour."""
    ladder = tone_scale(color, steps=9)
    return ladder[1], ladder[-2]


def contrast_of_hues(station: str) -> tuple[Color, Color]:
    """Contrast 2 — neighbouring scales at unequal depths (kinship in hue,
    opposition in tone)."""
    centre = _norm_station(station)
    neighbour = _STATIONS[(_STATIONS.index(centre) + 1) % 12]
    return tone_scale(WHEEL[centre])[1], tone_scale(WHEEL[neighbour])[-2]


def contrast_of_colours(station: str) -> tuple[Color, Color]:
    """Contrast 3 — very distant scales: the complementary pair, colour's
    strongest chord. Unbalance them in use (one rules, the other visits)."""
    return WHEEL[_norm_station(station)], complement(station)


# ── the closed palette ───────────────────────────────────────────────────


@dataclass(frozen=True)
class ClosedPalette:
    """A small palette with assigned duties — 'the impossibility of strangers'."""

    duties: dict[str, Color]
    quiet_steps: list[Color] = field(default_factory=list)

    def tokens(self) -> dict[str, Color]:
        """A ``defs.tokens.colors`` fragment: duties plus ``quiet1..N``."""
        out = dict(self.duties)
        for i, step in enumerate(self.quiet_steps, start=1):
            out[f"quiet{i}"] = step
        return out


def closed_palette(*, ground: Color, ink: Color, accent: Color,
                   quiet_steps: int = 3) -> ClosedPalette:
    """Build a closed palette with assigned duties.

    One ground (never two), one near-black ink, one accent with one duty, and
    ``quiet_steps`` greys drawn from the ink's own scale for the second rank.
    Pair with :data:`AREA_GUIDE` for the dose (ground ≈62%, text & structure
    ≈30%, accent ≈8%). A colour outside the set should *mean* something —
    exactly as an italic does.
    """
    ladder = tone_scale(ink, steps=9)
    quiet = [to_grey(tone) for tone in ladder[1:1 + quiet_steps]]
    return ClosedPalette(duties={"ground": ground, "ink": ink, "accent": accent},
                         quiet_steps=quiet)


# ── the grey test ────────────────────────────────────────────────────────

_COLOR_KEYS = frozenset({"fill", "color", "stroke", "background", "marker_color",
                         "header_fill", "header_text", "cell_text"})


def _grey_value(value: Any) -> Any:
    if isinstance(value, str) and value.strip().startswith("#"):
        try:
            return to_grey(value)
        except ValueError:
            return value
    return value


def _grey_walk(node: Any) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _COLOR_KEYS:
                node[key] = _grey_value(value)
                if isinstance(node[key], (dict, list)):
                    _grey_walk(node[key])
            elif key == "stops" and isinstance(value, list):
                for stop in value:
                    if isinstance(stop, dict) and "color" in stop:
                        stop["color"] = _grey_value(stop["color"])
            elif key == "colors" and isinstance(value, dict):
                # a token table: grey every definition so references follow
                for token in value:
                    value[token] = _grey_value(value[token])
            elif isinstance(value, (dict, list)):
                _grey_walk(value)
    elif isinstance(node, list):
        for item in node:
            _grey_walk(item)


def grey_document(doc: Mapping[str, Any]) -> dict[str, Any]:
    """The grey test (best effort): a deep copy of a document with every
    literal ``#hex`` colour replaced by its luminance-matched grey.

    "Strip the hue from a design and its skeleton of light and dark remains —
    or is revealed to be missing." Render the result next to the original to
    audit whether hierarchy survives without hue (tone is the axis the eye
    trusts first, and the only one every reader receives).

    Covers colour-bearing fields (``fill``/``color``/``stroke``/…, gradient
    stops) and token tables. Token *references* stay references — they grey
    via their token definition. Pattern paints and image fills are untouched.
    """
    out = copy.deepcopy(dict(doc))
    _grey_walk(out)
    return out


__all__ = [
    "AREA_GUIDE",
    "WHEEL",
    "ClosedPalette",
    "closed_palette",
    "complement",
    "complement_name",
    "contrast_of_colours",
    "contrast_of_hues",
    "contrast_of_scale",
    "contrast_ratio",
    "dominant_light",
    "grey_document",
    "harmony_of_hues",
    "harmony_of_scale",
    "nearest_station",
    "relative_luminance",
    "to_grey",
    "tone_scale",
]
