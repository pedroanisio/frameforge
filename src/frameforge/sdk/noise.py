"""Deterministic, sampleable coherent noise for author-time computation.

The functions in this module are ordinary CPU calculations: they return values
to Python and have no relationship to :func:`frameforge.sdk.paint.turbulence`,
which constructs a renderer-side SVG ``feTurbulence`` filter.  They are
non-cryptographic and intended for procedural geometry, colour, density, and
displacement at author time.

The Perlin implementation uses the quintic interpolation described by Ken
Perlin, "Improving Noise", SIGGRAPH 2002
(https://mrl.cs.nyu.edu/~perlin/paper445.pdf).  The 2D simplex implementation
uses Stefan Gustavson's skew/unskew construction, "Simplex noise demystified",
2005 (https://www.itn.liu.se/~stegu76/aqsis/aqsis-newnoise/simplexnoise/).

Patent record: simplex noise in three or more dimensions was covered by US
6,867,776, which claims ``n >= 3``.  The application has a 2001 priority date,
was filed in 2002, and is recorded as expired in 2022.  This module implements
only the 2D construction.  The wording is intentionally precise because the
issue's draft described the priority date as the filing date.

Permutation tables are derived through :func:`stable_seed`, cached with a
bounded 64-seed LRU, and never rebuilt per sample.  Primitive calls are pure;
they perform no I/O and mutate no global or caller-owned state.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from frameforge.sdk._seed import stable_seed

__all__ = [
    "Noise",
    "domain_warp",
    "fbm",
    "perlin_2d",
    "remap",
    "simplex_2d",
    "to_unit",
    "value_noise_2d",
]

NoiseBasis = Callable[..., float]

_SQRT_HALF = math.sqrt(0.5)
_PERLIN_GRADIENTS = (
    (1.0, 0.0),
    (-1.0, 0.0),
    (0.0, 1.0),
    (0.0, -1.0),
    (_SQRT_HALF, _SQRT_HALF),
    (-_SQRT_HALF, _SQRT_HALF),
    (_SQRT_HALF, -_SQRT_HALF),
    (-_SQRT_HALF, -_SQRT_HALF),
)
_SIMPLEX_GRADIENTS = (
    (1.0, 1.0),
    (-1.0, 1.0),
    (1.0, -1.0),
    (-1.0, -1.0),
    (1.0, 0.0),
    (-1.0, 0.0),
    (1.0, 0.0),
    (-1.0, 0.0),
    (0.0, 1.0),
    (0.0, -1.0),
    (0.0, 1.0),
    (0.0, -1.0),
)
_F2 = 0.5 * (math.sqrt(3.0) - 1.0)
_G2 = (3.0 - math.sqrt(3.0)) / 6.0


def _positive(name: str, value: float) -> float:
    resolved = float(value)
    if not math.isfinite(resolved) or resolved <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return resolved


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _fade(value: float) -> float:
    """Return Perlin's quintic ``6t^5 - 15t^4 + 10t^3`` interpolant."""
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def _lerp(start: float, end: float, amount: float) -> float:
    return start + amount * (end - start)


@lru_cache(maxsize=64)
def _permutation(seed: int) -> tuple[int, ...]:
    """Return a process-stable doubled permutation table for ``seed``."""
    resolved = stable_seed("frameforge-noise-permutation", seed)
    values = sorted(range(256), key=lambda value: stable_seed(resolved, value))
    return tuple(values + values)


def _hash(table: tuple[int, ...], x: int, y: int) -> int:
    return table[(x & 255) + table[y & 255]]


def value_noise_2d(x: float, y: float, *, seed: int = 0) -> float:
    """Return smooth deterministic value noise in ``[0, 1]``.

    This is sampleable author-time noise; :func:`paint.turbulence` is a
    declarative renderer-side filter.  Runtime is O(1).
    """
    x0 = math.floor(x)
    y0 = math.floor(y)
    xf = x - x0
    yf = y - y0
    table = _permutation(seed)
    bottom = _lerp(_hash(table, x0, y0) / 255.0, _hash(table, x0 + 1, y0) / 255.0, _fade(xf))
    top = _lerp(
        _hash(table, x0, y0 + 1) / 255.0,
        _hash(table, x0 + 1, y0 + 1) / 255.0,
        _fade(xf),
    )
    return _lerp(bottom, top, _fade(yf))


def _perlin_dot(table: tuple[int, ...], ix: int, iy: int, x: float, y: float) -> float:
    gradient = _PERLIN_GRADIENTS[_hash(table, ix, iy) & 7]
    return gradient[0] * x + gradient[1] * y


def perlin_2d(x: float, y: float, *, seed: int = 0) -> float:
    """Return classic improved Perlin gradient noise in ``[-1, 1]``.

    This is sampleable author-time noise; :func:`paint.turbulence` is a
    declarative renderer-side filter.  Runtime is O(1), with a cached table.
    """
    x0 = math.floor(x)
    y0 = math.floor(y)
    xf = x - x0
    yf = y - y0
    table = _permutation(seed)
    fade_x = _fade(xf)
    fade_y = _fade(yf)
    bottom = _lerp(
        _perlin_dot(table, x0, y0, xf, yf),
        _perlin_dot(table, x0 + 1, y0, xf - 1.0, yf),
        fade_x,
    )
    top = _lerp(
        _perlin_dot(table, x0, y0 + 1, xf, yf - 1.0),
        _perlin_dot(table, x0 + 1, y0 + 1, xf - 1.0, yf - 1.0),
        fade_x,
    )
    return _lerp(bottom, top, fade_y)


def _simplex_contribution(gradient: tuple[float, float], x: float, y: float) -> float:
    attenuation = 0.5 - x * x - y * y
    if attenuation <= 0.0:
        return 0.0
    attenuation *= attenuation
    return attenuation * attenuation * (gradient[0] * x + gradient[1] * y)


def simplex_2d(x: float, y: float, *, seed: int = 0) -> float:
    """Return Gustavson-style 2D simplex gradient noise in ``[-1, 1]``.

    This is sampleable author-time noise; :func:`paint.turbulence` is a
    declarative renderer-side filter.  Runtime is O(1), with a cached table.
    """
    skew = (x + y) * _F2
    i = math.floor(x + skew)
    j = math.floor(y + skew)
    unskew = (i + j) * _G2
    x0 = x - (i - unskew)
    y0 = y - (j - unskew)
    i1, j1 = ((1, 0) if x0 > y0 else (0, 1))
    x1 = x0 - i1 + _G2
    y1 = y0 - j1 + _G2
    x2 = x0 - 1.0 + 2.0 * _G2
    y2 = y0 - 1.0 + 2.0 * _G2

    table = _permutation(seed)
    ii = i & 255
    jj = j & 255
    gradient0 = _SIMPLEX_GRADIENTS[table[ii + table[jj]] % 12]
    gradient1 = _SIMPLEX_GRADIENTS[table[ii + i1 + table[jj + j1]] % 12]
    gradient2 = _SIMPLEX_GRADIENTS[table[ii + 1 + table[jj + 1]] % 12]
    return 70.0 * (
        _simplex_contribution(gradient0, x0, y0)
        + _simplex_contribution(gradient1, x1, y1)
        + _simplex_contribution(gradient2, x2, y2)
    )


def fbm(
    x: float,
    y: float,
    *,
    seed: int = 0,
    octaves: int = 4,
    lacunarity: float = 2.0,
    gain: float = 0.5,
    basis: NoiseBasis = perlin_2d,
) -> float:
    """Return normalised fractional Brownian motion over ``basis`` in O(octaves).

    Positive amplitude weights are divided by their sum, so the result remains
    in the basis range.  This is sampleable author-time noise;
    :func:`paint.turbulence` is a declarative renderer-side filter.
    """
    count = _positive_int("octaves", octaves)
    frequency_step = _positive("lacunarity", lacunarity)
    amplitude_step = _positive("gain", gain)
    frequency = 1.0
    amplitude = 1.0
    total = 0.0
    amplitude_sum = 0.0
    for octave in range(count):
        octave_seed = stable_seed(seed, "fbm", octave)
        total += amplitude * basis(x * frequency, y * frequency, seed=octave_seed)
        amplitude_sum += amplitude
        frequency *= frequency_step
        amplitude *= amplitude_step
    return total / amplitude_sum


def domain_warp(
    x: float,
    y: float,
    *,
    seed: int = 0,
    strength: float = 1.0,
    basis: NoiseBasis = fbm,
) -> tuple[float, float]:
    """Return coordinates warped by two independent samples of ``basis``.

    Callers re-sample their chosen basis at the returned point.  This is
    sampleable author-time noise; :func:`paint.turbulence` is a declarative
    renderer-side filter.  Runtime is twice the selected basis cost.
    """
    resolved_strength = float(strength)
    if not math.isfinite(resolved_strength):
        raise ValueError("strength must be finite")
    if resolved_strength == 0.0:
        return float(x), float(y)
    warp_x = basis(x + 5.2, y + 1.3, seed=stable_seed(seed, "domain-warp-x"))
    warp_y = basis(x + 8.3, y + 2.8, seed=stable_seed(seed, "domain-warp-y"))
    return x + resolved_strength * warp_x, y + resolved_strength * warp_y


def to_unit(value: float) -> float:
    """Map gradient-noise ``[-1, 1]`` to ``[0, 1]`` without clamping.

    This transforms sampleable values and does not configure
    :func:`paint.turbulence`, the renderer-side filter.
    """
    return (float(value) + 1.0) / 2.0


def remap(value: float, lo: float, hi: float) -> float:
    """Map a gradient-noise value from ``[-1, 1]`` into ``[lo, hi]``.

    This transforms sampleable values and does not configure
    :func:`paint.turbulence`, the renderer-side filter.
    """
    return float(lo) + to_unit(value) * (float(hi) - float(lo))


_BASIS_BY_NAME: dict[str, NoiseBasis] = {
    "perlin": perlin_2d,
    "simplex": simplex_2d,
    "value": value_noise_2d,
}


class Noise:
    """Bind a stable seed, frequency, and primitive basis for clean authoring.

    The class is deterministic and non-cryptographic.  It evaluates sampleable
    CPU noise at author time; :func:`paint.turbulence` is a separate declarative
    renderer-side filter.
    """

    def __init__(self, seed: Any = 0, *, frequency: float = 0.01, basis: str = "perlin") -> None:
        self.seed = stable_seed(seed)
        self.frequency = _positive("frequency", frequency)
        if basis not in _BASIS_BY_NAME:
            choices = ", ".join(sorted(_BASIS_BY_NAME))
            raise ValueError(f"basis must be one of: {choices}")
        self.basis = basis
        self._basis = _BASIS_BY_NAME[basis]

    def at(self, x: float, y: float) -> float:
        """Sample the bound primitive at frequency-scaled coordinates."""
        return self._basis(x * self.frequency, y * self.frequency, seed=self.seed)

    def fbm_at(self, x: float, y: float, *, octaves: int = 4) -> float:
        """Sample normalised fBm using the bound seed, frequency, and basis."""
        return fbm(
            x * self.frequency,
            y * self.frequency,
            seed=self.seed,
            octaves=octaves,
            basis=self._basis,
        )

    def field(self) -> Callable[[float, float], float]:
        """Return a callable ready for :class:`frameforge.sdk.fields.ScalarField`."""
        return self.at

    def derive(self, *parts: Any) -> Noise:
        """Return an order-stable named noise source independent of sibling use."""
        return Noise(
            stable_seed(self.seed, *parts),
            frequency=self.frequency,
            basis=self.basis,
        )
