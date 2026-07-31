"""Pure sRGB, CIE, and OKLab colour conversions and perceptual interpolation.

The sRGB transfer constants and D65 RGB/XYZ matrices follow IEC 61966-2-1 as
published in the W3C sRGB material and CSS Color 4 conversion reference:
https://www.w3.org/Graphics/Color/sRGB and
https://www.w3.org/TR/css-color-4/#color-conversion-code. CIELab uses the
piecewise transform and ``delta = 6/29`` from CIE 15:2004, *Colorimetry*, with
the D65 reference white used by this module's sRGB/XYZ conversion. OKLab uses
Björn Ottosson's 2020 published matrices and cube-root nonlinearity:
https://bottosson.github.io/posts/oklab/.

All functions are deterministic, standard-library-only author-time helpers.
Hex output is clipped per sRGB channel when a converted colour falls outside
the display gamut; chroma-preserving gamut mapping is deliberately not
performed. New :func:`mix` and :func:`ramp` calls default to perceptual OKLab.
Legacy Chevreul helpers retain their historical sRGB default.
"""
from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import TypeAlias

Color: TypeAlias = str

# IEC 61966-2-1 / CSS Color 4: linear-light sRGB (D65) -> CIE XYZ.
_SRGB_TO_XYZ = (
    (0.4123907992659595, 0.35758433938387796, 0.1804807884018343),
    (0.21263900587151036, 0.7151686787677559, 0.07219231536073371),
    (0.01933081871559185, 0.11919477979462599, 0.9505321522496607),
)
_XYZ_TO_SRGB = (
    (3.2409699419045226, -1.537383177570094, -0.4986107602930034),
    (-0.9692436362808796, 1.8759675015077202, 0.04155505740717559),
    (0.05563007969699366, -0.20397695888897652, 1.0569715142428786),
)
_D65 = tuple(sum(row) for row in _SRGB_TO_XYZ)

# Ottosson 2020, updated 2021-01-25: linear sRGB -> LMS -> OKLab.
_OKLAB_LINEAR_TO_LMS = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005),
)
_OKLAB_LMS_TO_LAB = (
    (0.2104542553, 0.7936177850, -0.0040720468),
    (1.9779984951, -2.4285922050, 0.4505937099),
    (0.0259040371, 0.7827717662, -0.8086757660),
)
_OKLAB_LAB_TO_LMS = (
    (1.0, 0.3963377774, 0.2158037573),
    (1.0, -0.1055613458, -0.0638541728),
    (1.0, -0.0894841775, -1.2914855480),
)
_OKLAB_LMS_TO_LINEAR = (
    (4.0767416621, -3.3077115913, 0.2309699292),
    (-1.2684380046, 2.6097574011, -0.3413193965),
    (-0.0041960863, -0.7034186147, 1.7076147010),
)

_HEX_RE = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\Z")
_SPACES = ("srgb", "linear", "lab", "lch", "oklab", "oklch")
_DELTA_E_METHODS = ("oklab", "cie76")
_LAB_DELTA = 6.0 / 29.0


def _matrix_vector(
    matrix: tuple[tuple[float, float, float], ...],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    x, y, z = vector
    return tuple(row[0] * x + row[1] * y + row[2] * z for row in matrix)  # type: ignore[return-value]


def _parse_color(color: Color) -> tuple[float, float, float]:
    if not isinstance(color, str) or _HEX_RE.fullmatch(color) is None:
        raise ValueError(f"color must be #rgb or #rrggbb hexadecimal, got {color!r}")
    value = color[1:]
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    return tuple(int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4))  # type: ignore[return-value]


def _triplet(value: Sequence[float], parameter: str) -> tuple[float, float, float]:
    if isinstance(value, (str, bytes)) or len(value) != 3:
        raise ValueError(f"{parameter} must contain exactly three numeric components")
    try:
        result = tuple(float(component) for component in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{parameter} must contain exactly three numeric components") from exc
    if not all(math.isfinite(component) for component in result):
        raise ValueError(f"{parameter} components must be finite")
    return result  # type: ignore[return-value]


def _to_hex(rgb: tuple[float, float, float]) -> Color:
    return "#" + "".join(
        f"{round(max(0.0, min(1.0, channel)) * 255.0):02x}" for channel in rgb
    )


def _cbrt(value: float) -> float:
    return math.copysign(abs(value) ** (1.0 / 3.0), value)


def srgb_to_linear(c: float) -> float:
    """Decode one gamma-encoded sRGB channel, conventionally in ``[0, 1]``."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    """Encode one linear-light sRGB channel without clipping its value."""
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1.0 / 2.4) - 0.055


def to_xyz(color: Color) -> tuple[float, float, float]:
    """Convert an sRGB hex colour to CIE XYZ using the D65 white point."""
    linear = tuple(srgb_to_linear(channel) for channel in _parse_color(color))
    return _matrix_vector(_SRGB_TO_XYZ, linear)  # type: ignore[arg-type]


def from_xyz(xyz: Sequence[float]) -> Color:
    """Convert D65 CIE XYZ to clipped, lowercase six-digit sRGB hex."""
    linear = _matrix_vector(_XYZ_TO_SRGB, _triplet(xyz, "xyz"))
    return _to_hex(tuple(linear_to_srgb(channel) for channel in linear))  # type: ignore[arg-type]


def _lab_curve(value: float) -> float:
    threshold = _LAB_DELTA ** 3
    return _cbrt(value) if value > threshold else value / (3.0 * _LAB_DELTA ** 2) + 4.0 / 29.0


def _lab_curve_inverse(value: float) -> float:
    return value ** 3 if value > _LAB_DELTA else 3.0 * _LAB_DELTA ** 2 * (value - 4.0 / 29.0)


def to_lab(color: Color) -> tuple[float, float, float]:
    """Convert an sRGB hex colour to CIELab relative to D65."""
    x, y, z = to_xyz(color)
    fx, fy, fz = (
        _lab_curve(x / _D65[0]),
        _lab_curve(y / _D65[1]),
        _lab_curve(z / _D65[2]),
    )
    return 116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)


def from_lab(lab: Sequence[float]) -> Color:
    """Convert D65 CIELab to clipped, lowercase six-digit sRGB hex."""
    lightness, a_axis, b_axis = _triplet(lab, "lab")
    fy = (lightness + 16.0) / 116.0
    fx = fy + a_axis / 500.0
    fz = fy - b_axis / 200.0
    return from_xyz((
        _D65[0] * _lab_curve_inverse(fx),
        _D65[1] * _lab_curve_inverse(fy),
        _D65[2] * _lab_curve_inverse(fz),
    ))


def _to_cylindrical(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    lightness, a_axis, b_axis = lab
    chroma = math.hypot(a_axis, b_axis)
    hue = math.degrees(math.atan2(b_axis, a_axis)) % 360.0 if chroma > 1e-15 else 0.0
    return lightness, chroma, hue


def _from_cylindrical(lch: Sequence[float], parameter: str) -> tuple[float, float, float]:
    lightness, chroma, hue = _triplet(lch, parameter)
    angle = math.radians(hue % 360.0)
    return lightness, chroma * math.cos(angle), chroma * math.sin(angle)


def to_lch(color: Color) -> tuple[float, float, float]:
    """Convert an sRGB hex colour to cylindrical D65 CIELCh."""
    return _to_cylindrical(to_lab(color))


def from_lch(lch: Sequence[float]) -> Color:
    """Convert D65 CIELCh to clipped, lowercase six-digit sRGB hex."""
    return from_lab(_from_cylindrical(lch, "lch"))


def to_oklab(color: Color) -> tuple[float, float, float]:
    """Convert an sRGB hex colour to Ottosson's D65 OKLab coordinates."""
    linear = tuple(srgb_to_linear(channel) for channel in _parse_color(color))
    lms = _matrix_vector(_OKLAB_LINEAR_TO_LMS, linear)  # type: ignore[arg-type]
    return _matrix_vector(_OKLAB_LMS_TO_LAB, tuple(_cbrt(channel) for channel in lms))  # type: ignore[arg-type]


def from_oklab(lab: Sequence[float]) -> Color:
    """Convert OKLab to lowercase sRGB hex, clipping out-of-gamut channels."""
    lms_root = _matrix_vector(_OKLAB_LAB_TO_LMS, _triplet(lab, "lab"))
    linear = _matrix_vector(_OKLAB_LMS_TO_LINEAR, tuple(channel ** 3 for channel in lms_root))  # type: ignore[arg-type]
    return _to_hex(tuple(linear_to_srgb(channel) for channel in linear))  # type: ignore[arg-type]


def to_oklch(color: Color) -> tuple[float, float, float]:
    """Convert an sRGB hex colour to cylindrical OKLCh."""
    return _to_cylindrical(to_oklab(color))


def from_oklch(lch: Sequence[float]) -> Color:
    """Convert OKLCh to lowercase sRGB hex, clipping out-of-gamut channels."""
    return from_oklab(_from_cylindrical(lch, "lch"))


def _validate_choice(value: str, parameter: str, accepted: tuple[str, ...]) -> str:
    if value not in accepted:
        choices = ", ".join(repr(choice) for choice in accepted)
        raise ValueError(f"{parameter} must be one of {choices}; got {value!r}")
    return value


def _mix_hue(a: float, b: float, t: float) -> float:
    delta = (b - a + 180.0) % 360.0 - 180.0
    return (a + delta * t) % 360.0


def mix(a: Color, b: Color, t: float, *, space: str = "oklab") -> Color:
    """Interpolate two colours in ``space``; new calls default to OKLab.

    ``lch`` and ``oklch`` hue follows the shorter circular arc. Conversion
    back to sRGB clips out-of-gamut channels. Exact endpoints preserve the
    caller's original hex spelling.
    """
    selected = _validate_choice(space, "space", _SPACES)
    rgb_a, rgb_b = _parse_color(a), _parse_color(b)
    if not 0.0 <= t <= 1.0:
        raise ValueError(f"t must be within [0, 1], got {t!r}")
    if t == 0.0:
        return a
    if t == 1.0:
        return b
    if selected == "srgb":
        return _to_hex(tuple(x + (y - x) * t for x, y in zip(rgb_a, rgb_b)))  # type: ignore[arg-type]
    if selected == "linear":
        linear_a = tuple(srgb_to_linear(channel) for channel in rgb_a)
        linear_b = tuple(srgb_to_linear(channel) for channel in rgb_b)
        linear = tuple(x + (y - x) * t for x, y in zip(linear_a, linear_b))
        return _to_hex(tuple(linear_to_srgb(channel) for channel in linear))  # type: ignore[arg-type]

    converters = {
        "lab": (to_lab, from_lab),
        "lch": (to_lch, from_lch),
        "oklab": (to_oklab, from_oklab),
        "oklch": (to_oklch, from_oklch),
    }
    forward, reverse = converters[selected]
    left, right = forward(a), forward(b)
    if selected in {"lch", "oklch"}:
        interpolated = (
            left[0] + (right[0] - left[0]) * t,
            left[1] + (right[1] - left[1]) * t,
            _mix_hue(left[2], right[2], t),
        )
    else:
        interpolated = tuple(x + (y - x) * t for x, y in zip(left, right))
    return reverse(interpolated)


def ramp(stops: Sequence[Color], n: int, *, space: str = "oklab") -> list[Color]:
    """Return ``n`` evenly positioned colours through two or more ``stops``."""
    selected = _validate_choice(space, "space", _SPACES)
    colors = tuple(stops)
    if len(colors) < 2:
        raise ValueError("stops must contain at least two colors")
    for color in colors:
        _parse_color(color)
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError(f"n must be an integer of at least 2, got {n!r}")
    last_segment = len(colors) - 1
    result: list[Color] = []
    for index in range(n):
        position = index * last_segment / (n - 1)
        segment = min(int(position), last_segment - 1)
        result.append(mix(colors[segment], colors[segment + 1], position - segment, space=selected))
    return result


def delta_e(a: Color, b: Color, *, method: str = "oklab") -> float:
    """Return perceptual distance using Euclidean OKLab or CIE76 CIELab."""
    selected = _validate_choice(method, "method", _DELTA_E_METHODS)
    left, right = (to_oklab(a), to_oklab(b)) if selected == "oklab" else (to_lab(a), to_lab(b))
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(left, right)))


__all__ = [
    "delta_e",
    "from_lab",
    "from_lch",
    "from_oklab",
    "from_oklch",
    "from_xyz",
    "linear_to_srgb",
    "mix",
    "ramp",
    "srgb_to_linear",
    "to_lab",
    "to_lch",
    "to_oklab",
    "to_oklch",
    "to_xyz",
]
