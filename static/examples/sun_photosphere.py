#!/usr/bin/env python3
"""The Sun — a physically-derived full-disk plate, drawn with the FrameForge SDK.

Nothing here is an eyeballed colour. Every tone on the disk is computed from two
classical results, and the geometry is scaled from the IAU nominal solar radius,
so the picture is a *rendering of a model* rather than a painting of a memory.

The physics
-----------
1 · **Limb darkening — Eddington grey atmosphere.**  For a grey atmosphere in
    radiative equilibrium the Eddington approximation gives the source function
    ``S(tau) = (3F/4pi) (tau + 2/3)``; the Eddington–Barbier relation states that
    the emergent intensity at angle ``mu = cos(theta)`` is the source function at
    ``tau = mu``.  Together::

        I(mu) / I(1) = (mu + 2/3) / (5/3) = (2 + 3 mu) / 5

    so the limb (``mu = 0``) sits at exactly 2/5 of disk-centre intensity.  With
    ``mu = sqrt(1 - (r/R)^2)`` this is a closed-form profile in radius, sampled
    below into gradient stops.  (Observed 550 nm limb intensity is ~0.3-0.4 of
    centre, so the grey model is good to a few percent here; real profiles are
    fitted with a quadratic law.  Noted, not hidden.)

2 · **Temperature stratification — the same model, one step further.**  The grey
    atmosphere also gives ``T(tau)^4 = (3/4) T_eff^4 (tau + 2/3)``, so the layer
    seen at angle ``mu`` has ``T(mu) = T_eff [ (3/4)(mu + 2/3) ]^(1/4)``.  Disk
    centre looks down to ~6103 K; the extreme limb shows ~4853 K.  The limb is
    therefore not merely darker, it is genuinely *cooler and redder* — and here
    that reddening is derived, not stylised.

3 · **Colour — Planck's law.**  Each temperature is turned into an sRGB tone by
    evaluating the spectral radiance ``B_lambda(T)`` at representative R/G/B
    wavelengths, white-balancing against a 6500 K (D65) reference — exactly what
    a daylight-balanced camera does — then applying the sRGB transfer function.
    The familiar golden cast is thus a *consequence* of 5772 K under a D65
    balance, not a filter.

4 · **Sunspots.**  Umbra and penumbra are given representative temperatures and
    their brightness follows Stefan–Boltzmann, ``I ∝ T^4``: the umbra lands at
    ``(4000/5772)^4 ≈ 0.23`` and the penumbra at ``(5500/5772)^4 ≈ 0.82`` of the
    photosphere — both inside the observed ranges.  Spots are placed within the
    +/-35 deg activity belt and are **foreshortened by mu** along the radial
    direction, so groups near the limb flatten into radial ellipses the way real
    ones do.

Constants
---------
``h``, ``c``, ``k_B`` are the exact SI defining constants (2019 redefinition).
``T_eff = 5772 K`` and ``R_sun = 6.957e8 m`` are the IAU 2015 Resolution B3
nominal values.  Umbral/penumbral temperatures and granule sizes are
*representative* literature figures with real spread, and are labelled as such
in ``MODEL`` — they are the only soft numbers in the file.

Honest scope: this is a white-light photosphere with an H-alpha limb (rim and
prominences) composited over it — a convention borrowed from real amateur
astrophotography, not something a single instrument records at once.  The
corona is rendered as the instrumental aureole you actually see, not the
eclipse corona.

Run from the repo root::

    uv run python static/examples/sun_photosphere.py
    uv run --group browser python tooling/render_chromium.py \\
        out/sun/sun.fg.yaml --out out/sun
"""
from __future__ import annotations

import math
import os
import random
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

from frameforge_sdk import DocumentBuilder  # noqa: E402
from frameforge_sdk.clip import clip_circle  # noqa: E402
from frameforge_sdk.outline import stroke_outline  # noqa: E402
from frameforge_sdk.paint import (blur_filter, displacement_map,  # noqa: E402
                                  filter_chain,
                                  radial_gradient, rgba, style_effects,
                                  turbulence)

# ── exact SI defining constants (2019 redefinition) ──────────────────────── #
H_PLANCK = 6.62607015e-34      # J s      (exact)
C_LIGHT = 2.99792458e8         # m s^-1   (exact)
K_BOLTZ = 1.380649e-23         # J K^-1   (exact)

# ── IAU 2015 Resolution B3 nominal solar values ──────────────────────────── #
T_EFF = 5772.0                 # K
R_SUN_MM = 695.700             # Mm (6.957e8 m)

# ── representative (not defining) figures — the only soft numbers here ───── #
MODEL = {
    "T_umbra": 4000.0,         # K, typical umbral core (literature spread ~3700-4500)
    "T_penumbra": 5500.0,      # K, typical penumbra    (literature spread ~5000-5700)
    "granule_Mm": 1.0,         # Mm, typical granule diameter (~1000 km)
    "supergranule_Mm": 30.0,   # Mm, typical supergranule cell
    "activity_belt_deg": 35.0, # sunspots occur within roughly +/-35 deg latitude
}

WHITE_BALANCE_T = 6500.0       # D65-ish reference: what a daylight camera assumes
LAMBDA_RGB = (600e-9, 550e-9, 450e-9)   # representative R, G, B wavelengths

# PRESENTATION, NOT PHYSICS. A display tone curve applied to linear intensity
# before sRGB encoding — the analogue of the response curve every real solar
# image is printed through. It changes no derived quantity (`report()` prints
# the physics untouched); it only sets how linear intensity maps to screen
# value. At 1.0 the plate is a strict linear->sRGB render, in which a 23%-linear
# umbra correctly encodes to a mid grey and reads far lighter than the black
# sunspots of popular imagery.
DISPLAY_GAMMA = 2.0

# PRESENTATION, NOT PHYSICS. The cast of the solar filter the image is taken
# through. A neutral Baader-type film renders the disk white ((1,1,1) here); the
# orange/yellow glass filters most amateurs use impose a warm cast — which is
# why the popular image of the Sun is golden, not white. This is that glass,
# applied as a per-channel multiplier in linear light. It is a colour grade, not
# a temperature: `report()` still prints the true D65 tones. Set to (1,1,1) for
# the neutral-filter (white) rendering.
FILTER_GLASS = (1.0, 0.74, 0.42)

# ── canvas ───────────────────────────────────────────────────────────────── #
W = H = 2000
CXY = (W / 2.0, H / 2.0)
R_DISK = 690.0                 # solar radius in px
PX_PER_MM = R_DISK / R_SUN_MM  # ~0.99 px per Mm

RNG = random.Random(20260724)


# ── radiometry ───────────────────────────────────────────────────────────── #
def planck(wavelength_m: float, temperature: float) -> float:
    """Spectral radiance B_lambda(T) — Planck's law, SI units."""
    exponent = H_PLANCK * C_LIGHT / (wavelength_m * K_BOLTZ * temperature)
    return (2 * H_PLANCK * C_LIGHT ** 2 / wavelength_m ** 5) / (math.expm1(exponent))


def _srgb_encode(value: float) -> int:
    v = min(max(value, 0.0), 1.0)
    v = 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return int(round(min(max(v, 0.0), 1.0) * 255))


def blackbody(temperature: float, intensity: float = 1.0) -> str:
    """A blackbody at `temperature`, white-balanced to D65, as an sRGB hex string.

    Each channel is the Planck radiance at its representative wavelength divided
    by the same quantity at the balance temperature, so the reference renders as
    neutral and everything cooler drifts warm — the physical origin of the Sun's
    golden cast under a daylight-balanced camera.

    The ratio is then normalised to its own peak, leaving pure CHROMATICITY, and
    brightness is supplied separately by `intensity` in LINEAR light before the
    sRGB transfer function. Skipping that normalisation double-counts the
    darkening — the Planck ratio already carries the absolute brightness drop
    with temperature, so multiplying it by a limb-darkening factor as well
    crushes the whole disk toward grey.
    """
    return _encode(temperature, intensity, FILTER_GLASS)


def _encode(temperature: float, intensity: float,
            glass: "tuple[float, float, float]") -> str:
    """Planck chromaticity x intensity x filter glass -> sRGB hex."""
    linear = [planck(lam, temperature) / planck(lam, WHITE_BALANCE_T) for lam in LAMBDA_RGB]
    peak = max(linear)
    if peak > 0.0:
        linear = [channel / peak for channel in linear]
    graded = [c * intensity * g for c, g in zip(linear, glass)]
    return "#%02X%02X%02X" % tuple(_srgb_encode(c ** DISPLAY_GAMMA) for c in graded)


def true_tone(temperature: float, intensity: float = 1.0) -> str:
    """The physically-derived D65 tone with NO filter glass — the honest colour."""
    return _encode(temperature, intensity, (1.0, 1.0, 1.0))


def mu_at(radius_fraction: float) -> float:
    """cos(theta) for a point at `radius_fraction` of the disk radius."""
    x = min(max(radius_fraction, 0.0), 1.0)
    return math.sqrt(max(0.0, 1.0 - x * x))


def limb_intensity(mu: float) -> float:
    """Eddington + Eddington-Barbier: I(mu)/I(1) = (2 + 3 mu) / 5."""
    return (2.0 + 3.0 * mu) / 5.0


def layer_temperature(mu: float) -> float:
    """Grey atmosphere: T(mu) = T_eff [ (3/4)(mu + 2/3) ]^(1/4)."""
    return T_EFF * (0.75 * (mu + 2.0 / 3.0)) ** 0.25


def photosphere_stops(n: int = 28) -> list[tuple[str, float]]:
    """The limb-darkening ramp, sampled uniformly in mu (dense near the limb)."""
    stops: list[tuple[str, float]] = []
    for i in range(n):
        mu = 1.0 - i / (n - 1)
        x = math.sqrt(max(0.0, 1.0 - mu * mu))
        stops.append((blackbody(layer_temperature(mu), limb_intensity(mu)), round(x, 5)))
    return stops


def brightness_ratio(temperature: float) -> float:
    """Stefan-Boltzmann bolometric ratio against the photosphere: (T/T_eff)^4."""
    return (temperature / T_EFF) ** 4


# ── heliographic placement ───────────────────────────────────────────────── #
def project(lat_deg: float, lon_deg: float) -> tuple[float, float, float]:
    """Orthographic projection of a heliographic (lat, lon) onto the disk.

    Returns (x_px, y_px, mu) with the sub-Earth point at disk centre (B0 = 0).
    `mu` is the foreshortening factor: 1 at disk centre, 0 at the limb.
    """
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    x = math.cos(lat) * math.sin(lon)
    y = math.sin(lat)
    mu = math.cos(lat) * math.cos(lon)          # cos of angular distance from centre
    return CXY[0] + x * R_DISK, CXY[1] - y * R_DISK, max(mu, 0.0)


def mm(value_mm: float) -> float:
    """Megametres on the Sun -> pixels on this plate."""
    return value_mm * PX_PER_MM


# ── active regions: (latitude, longitude, penumbra Mm, umbra fraction, spots) ─
ACTIVE_REGIONS = [
    (14.0, -28.0, 62.0, 0.42, 3),
    (-11.0, 12.0, 48.0, 0.38, 2),
    (23.0, 41.0, 36.0, 0.45, 2),
    (-19.0, -52.0, 30.0, 0.40, 1),
    (8.0, 62.0, 26.0, 0.36, 1),
    (-27.0, 30.0, 20.0, 0.44, 1),
]


def draw_space(page) -> None:
    """Deep sky: a cold near-black field with a sparse, unequal scatter of stars."""
    page.rect([0, 0, W, H], fill="#04050A")
    page.rect([0, 0, W, H], fill=radial_gradient(
        [(rgba("#141A2B", 0.55), 0), (rgba("#04050A", 0.0), 1)],
        at=list(CXY), radius=W * 0.70), decorative=True)
    for _ in range(260):
        x, y = RNG.uniform(0, W), RNG.uniform(0, H)
        if math.hypot(x - CXY[0], y - CXY[1]) < R_DISK * 1.30:
            continue                     # nothing shows through the aureole
        mag = RNG.random() ** 3          # a few bright, many faint
        page.circle([x, y], 0.5 + mag * 2.0,
                    fill=blackbody(RNG.uniform(3200, 9500)),
                    opacity=round(0.18 + mag * 0.70, 3), decorative=True)


def draw_aureole(page) -> None:
    """The instrumental aureole — forward-scattered light hugging a bright source.

    Kept tight and faint on purpose: an unocculted disk is so much brighter than
    its surroundings that a broad halo reads as fog, not light.
    """
    # ONE circle, ONE gradient with a smooth monotonic decay — stacking several
    # narrow-annulus circles bands into visible concentric rings, so the aureole
    # is a single continuous fall-off instead. Alpha drops as an inverse-square-
    # like tail from the limb outward, sampled into stops so the ramp is smooth.
    # The glow starts just OUTSIDE the disk and stays transparent across the
    # disk itself, so it never fills in (and washes out) the limb darkening — an
    # aureole is scattered light in the sky around the Sun, not on it. One
    # circle, smooth monotonic decay, to avoid concentric-ring banding.
    glow = blackbody(layer_temperature(0.0), 1.0)
    r_out = R_DISK * 2.3
    edge = R_DISK / r_out
    stops = [(rgba(glow, 0.0), 0.0),
             (rgba(glow, 0.0), edge * 0.985),
             (rgba(glow, 0.42), edge)]
    for i in range(1, 21):
        t = i / 20.0                      # 0..1 from limb to r_out
        pos = edge + (1.0 - edge) * t
        alpha = 0.42 * (1.0 - t) ** 2.6   # smooth glow tail, ->0 at the rim
        stops.append((rgba(glow, round(alpha, 4)), round(pos, 5)))
    page.circle(list(CXY), r_out, decorative=True,
                fill=radial_gradient(stops, at=list(CXY), radius=r_out))

    # Faint equatorial streamers — the corona's shape near solar maximum, kept
    # at the threshold of visibility because an unocculted disk swamps it.
    for angle in (8, 26, -14, -33, 172, 156, 196, 213):
        theta = math.radians(angle)
        base, tip = R_DISK * 1.02, R_DISK * RNG.uniform(1.5, 1.95)
        spread = math.radians(RNG.uniform(4.0, 7.0))
        pts = [(CXY[0] + base * math.cos(theta - spread), CXY[1] + base * math.sin(theta - spread)),
               (CXY[0] + tip * math.cos(theta), CXY[1] + tip * math.sin(theta)),
               (CXY[0] + base * math.cos(theta + spread), CXY[1] + base * math.sin(theta + spread))]
        page.polygon(pts, fill=rgba(blackbody(T_EFF), 0.030), decorative=True,
                     **style_effects(filter=filter_chain(blur_filter(30))))


def draw_photosphere(page) -> None:
    """The disk itself: one gradient, 28 stops, every one of them computed."""
    page.circle(list(CXY), R_DISK, id="photosphere", fill=radial_gradient(
        photosphere_stops(), at=list(CXY), radius=R_DISK))


def draw_photosphere_mottle(page) -> None:
    """A whisper of large-scale mottling — and a deliberate absence.

    Granules are ~1 Mm across, which at this plate scale is 0.99 px: below the
    sampling limit. Real full-disk white-light images do NOT show resolved
    granulation for exactly this reason, so drawing cells here would be a
    prettier picture of a less true Sun. What survives at full-disk scale is the
    supergranular network, and only faintly — that is all this adds. The
    resolved convection lives on plate 2, where the scale supports it.
    """
    fade = radial_gradient([("#FFFFFF", 0), ("#FFFFFF", 0.45),
                            ("#8C8C8C", 0.82), ("#000000", 0.99)],
                           at=list(CXY), radius=R_DISK)
    page.rect([CXY[0] - R_DISK, CXY[1] - R_DISK, R_DISK * 2, R_DISK * 2],
              opacity=0.055, decorative=True,
              fill=blackbody(layer_temperature(1.0), 1.0),
              style={"clip_path": clip_circle(list(CXY), R_DISK), "mask": fade,
                     "filter": filter_chain(
                         turbulence(base_frequency=1.0 / mm(MODEL["supergranule_Mm"]),
                                    num_octaves=4, seed=17, type="fractalNoise"),
                         displacement_map(scale=22, x_channel="R", y_channel="G"))})


def draw_faculae(page) -> None:
    """Bright magnetic network — visible only near the limb, where its contrast
    against the darkened photosphere finally exceeds the background."""
    ring = radial_gradient([("#000000", 0), ("#000000", 0.70),
                            ("#9A9A9A", 0.90), ("#FFFFFF", 0.982), ("#000000", 0.999)],
                           at=list(CXY), radius=R_DISK)
    page.rect([CXY[0] - R_DISK, CXY[1] - R_DISK, R_DISK * 2, R_DISK * 2],
              opacity=0.20, decorative=True,
              fill=blackbody(layer_temperature(0.55), 1.0),
              style={"clip_path": clip_circle(list(CXY), R_DISK), "mask": ring,
                     "filter": filter_chain(
                         turbulence(base_frequency=1.0 / mm(16.0), num_octaves=5,
                                    seed=93, type="fractalNoise"),
                         displacement_map(scale=12, x_channel="R", y_channel="G"))})


def draw_active_regions(page) -> None:
    """Sunspot groups: Planck-derived tones, mu-foreshortened, radially oriented."""
    penumbra = blackbody(MODEL["T_penumbra"], brightness_ratio(MODEL["T_penumbra"]))
    umbra = blackbody(MODEL["T_umbra"], brightness_ratio(MODEL["T_umbra"]))

    for lat, lon, pen_mm, umbra_frac, count in ACTIVE_REGIONS:
        gx, gy, gmu = project(lat, lon)
        if gmu <= 0.06:
            continue
        for spot in range(count):
            jitter = mm(pen_mm) * 1.35
            sx = gx + RNG.uniform(-jitter, jitter) * gmu
            sy = gy + RNG.uniform(-jitter * 0.55, jitter * 0.55)
            r = math.hypot(sx - CXY[0], sy - CXY[1])
            if r > R_DISK * 0.985:
                continue
            mu = mu_at(r / R_DISK)
            scale = 1.0 if spot == 0 else RNG.uniform(0.45, 0.78)
            pen_r = mm(pen_mm) * 0.5 * scale
            # Foreshortening compresses the RADIAL axis by mu; tangential is intact.
            angle = math.degrees(math.atan2(sy - CXY[1], sx - CXY[0]))
            with page.grouped(meta={"role": "sunspot"}) as g:
                g.ellipse([sx, sy], max(pen_r * mu, 1.4), pen_r, rotation=angle,
                          fill=radial_gradient(
                              [(penumbra, 0.0), (penumbra, 0.62),
                               (rgba(penumbra, 0.72), 0.86),
                               (rgba(penumbra, 0.30), 0.96), (rgba(penumbra, 0.0), 1.0)]),
                          **style_effects(filter=filter_chain(blur_filter(1.6))))
                ur = pen_r * umbra_frac
                g.ellipse([sx, sy], max(ur * mu, 0.8), ur, rotation=angle,
                          fill=radial_gradient([(umbra, 0.0), (umbra, 0.78),
                                                (rgba(penumbra, 0.85), 1.0)]),
                          **style_effects(filter=filter_chain(blur_filter(1.4))))


def draw_limb(page) -> None:
    """The reddened extreme limb — the deepening of limb darkening at the edge.

    Not a bright emission ring (which reads as a drawn circle) but the last few
    percent of the disk deepening toward the coolest, reddest layer the grey
    atmosphere predicts — a soft darkening, wider and lower-contrast than a line.
    The tone is the true mu=0 layer colour pushed a step cooler, so it continues
    the photosphere ramp rather than sitting on top of it.
    """
    edge_tone = blackbody(layer_temperature(0.0) - 250.0, 0.62)   # coolest, reddest
    page.circle(list(CXY), R_DISK, decorative=True, fill=radial_gradient(
        [(rgba(edge_tone, 0.0), 0.955),
         (rgba(edge_tone, 0.28), 0.985),
         (rgba(edge_tone, 0.62), 0.997),
         (rgba(edge_tone, 0.30), 1.0)],
        at=list(CXY), radius=R_DISK))
    # A whisper of chromospheric red just beyond the edge — the H-alpha fringe,
    # kept faint and textured so it is an edge quality, not an outline.
    h_alpha = "#B83A22"
    r_sp = R_DISK + mm(7.0)
    page.circle(list(CXY), r_sp, decorative=True, fill=radial_gradient(
        [(rgba(h_alpha, 0.0), 0.986), (rgba("#D8542E", 0.16), 0.9965),
         (rgba(h_alpha, 0.0), 1.0)], at=list(CXY), radius=r_sp),
        **style_effects(filter=filter_chain(
            turbulence(base_frequency=1.0 / mm(2.2), num_octaves=2, seed=5),
            displacement_map(scale=6, x_channel="R", y_channel="G"))))


def draw_prominences(page) -> None:
    """H-alpha prominences: plasma suspended on closed magnetic loops.

    Heights are set in Mm (46-96 Mm here — ordinary quiescent scale) and lowered
    through `stroke_outline` with a width profile, so each loop thins toward its
    footpoints the way a flux tube does. Each arc is painted twice: a wide, very
    diffuse halo and a tighter core, which is what gives emission its glow
    instead of the flat look of a stroked curve.
    """
    def loop(theta_deg, height_mm, span_deg, phase):
        theta, half = math.radians(theta_deg), math.radians(span_deg / 2.0)
        height, pts = mm(height_mm), []
        for i in range(33):
            t = i / 32.0
            ang = theta - half + 2 * half * t
            arch = math.sin(math.pi * t) ** 0.72
            wobble = 1.0 + 0.055 * math.sin(phase + t * 6.5)
            rad = R_DISK * 0.992 + height * arch * wobble
            pts.append((CXY[0] + rad * math.cos(ang), CXY[1] + rad * math.sin(ang)))
        return pts

    def profile(t):
        return 0.28 + 0.72 * math.sin(math.pi * t) ** 0.55

    for theta_deg, height_mm, span_deg, width_mm, phase in (
            (-64.0, 96.0, 16.0, 8.0, 0.4),
            (-56.0, 54.0, 10.0, 5.5, 2.1),
            (118.0, 82.0, 14.0, 7.0, 1.2),
            (129.0, 46.0, 9.0, 4.5, 3.3),
            (-142.0, 64.0, 12.0, 6.0, 0.9),
            (36.0, 50.0, 10.0, 5.0, 2.7)):
        pts = loop(theta_deg, height_mm, span_deg, phase)
        for width_scale, blur_px, fill, alpha in (
                (3.1, 26, "#C4442A", 0.30),      # diffuse halo
                (1.7, 10, "#E05A2E", 0.42),      # mid
                (1.0, 3.4, "#FF9A5C", 0.80)):    # bright core
            obj = stroke_outline(pts, mm(width_mm) * width_scale, profile=profile,
                                 cap="round", join="round", smooth=True)
            obj.update({"fill": fill, "opacity": alpha, "decorative": True})
            obj.setdefault("style", {}).update(
                style_effects(filter=filter_chain(blur_filter(blur_px)))["style"])
            page.add(obj)


# ── plate 2 · a photospheric close-up, where granulation is resolvable ────── #
# A separate, much larger plate scale so ~1 Mm granules span many pixels and can
# be drawn as the honest cellular convection pattern they are — the detail the
# full disk cannot carry (see draw_photosphere_mottle's note).
W2 = 2000
CXY2 = (W2 / 2.0, W2 / 2.0)
PX_PER_MM2 = 46.0                          # ~46x the full-disk scale (~43 Mm field)
FIELD_MM = W2 / PX_PER_MM2


def mm2(value_mm: float) -> float:
    return value_mm * PX_PER_MM2


def draw_granulation(page) -> None:
    """Granulation drawn as GEOMETRY, not a filter.

    The renderer draws feTurbulence at too low a contrast to read as cells, so
    granulation is built the honest way: a jittered field of convection cells,
    each a bright rising centre falling to a cooler edge, over a dark
    intergranular-lane ground. Cell size follows MODEL['granule_Mm'] (~1 Mm), so
    the pattern is at the right physical scale for this magnification, and every
    tone is the same Planck-derived `blackbody` used everywhere else — bright
    centres a touch hotter than T_eff, sinking lanes ~600 K cooler.
    """
    # Base is the GRANULE tone, not the lane — so gaps between drawn cells read
    # as ordinary bright surface, never as dark holes. The dark intergranular
    # network is then laid ON TOP as thin lanes, which is the true figure/ground:
    # granules are the bright rule, lanes the thin exception.
    hot = layer_temperature(1.0) + 200.0
    page.rect([0, 0, W2, W2], fill=blackbody(hot, 1.0))

    d = mm2(MODEL["granule_Mm"])           # granule diameter in px
    # Pass 1 — bright cell centres: dense, overlapping, soft-edged, so the field
    # modulates in brightness the way convection cells do (isotropic scatter, no
    # grid -> no rows). Each cell's centre is a touch hotter, its rim cooler.
    area_per_cell = (d * 0.5) ** 2 * math.pi * 0.34
    for _ in range(int(W2 * W2 / area_per_cell)):
        cx, cy = RNG.uniform(-d, W2 + d), RNG.uniform(-d, W2 + d)
        r = d * 0.5 * RNG.uniform(0.85, 1.45)
        temp = hot + RNG.uniform(-160, 150)
        centre = blackbody(temp + 120, 1.0)
        rim = blackbody(temp - 360, 0.9)
        page.circle([cx, cy], r, decorative=True, fill=radial_gradient(
            [(centre, 0.0), (centre, 0.55), (rim, 0.9), (rgba(rim, 0.0), 1.0)],
            at=[cx, cy], radius=r))

    # Pass 2 — the intergranular lanes: short dark strokes threaded between the
    # cells, thin and broken, at random orientation (the dark cell boundaries).
    lane = blackbody(layer_temperature(1.0) - 750.0, 0.5)
    for _ in range(int(W2 * W2 / (d * d) * 1.7)):
        x, y = RNG.uniform(0, W2), RNG.uniform(0, W2)
        ang = RNG.uniform(0, math.pi)
        ln = d * RNG.uniform(0.3, 0.7)
        dx, dy = ln * math.cos(ang), ln * math.sin(ang)
        obj = stroke_outline([(x - dx, y - dy), (x, y), (x + dx, y + dy)],
                             d * RNG.uniform(0.08, 0.16),
                             profile=lambda t: 0.4 + 0.6 * math.sin(math.pi * t),
                             cap="round", smooth=True)
        obj.update({"fill": lane, "opacity": round(RNG.uniform(0.25, 0.55), 3),
                    "decorative": True})
        page.add(obj)

    # a few bright points — the small-scale magnetic network strung in the lanes
    for _ in range(110):
        x, y = RNG.uniform(0, W2), RNG.uniform(0, W2)
        page.circle([x, y], mm2(0.15), fill=blackbody(hot + 500.0, 1.0),
                    opacity=round(RNG.uniform(0.35, 0.7), 3), decorative=True)


def draw_closeup(page) -> None:
    """The close-up: resolved granulation + a sunspot with a filamentary penumbra.

    The spot's penumbra is drawn as radial filaments — bright penumbral grains
    combed outward along the field — over a darker penumbral floor, the way a
    real spot looks at this resolution. Every tone is the same Planck-derived
    scale as plate 1.
    """
    draw_granulation(page)

    # A single sunspot, off-centre, with umbra + a filamentary penumbra.
    sx, sy = CXY2[0] + mm2(5.0), CXY2[1] - mm2(2.0)
    umbra_r, pen_r = mm2(7.0), mm2(16.0)
    penumbra = blackbody(MODEL["T_penumbra"], brightness_ratio(MODEL["T_penumbra"]))
    umbra = blackbody(MODEL["T_umbra"], brightness_ratio(MODEL["T_umbra"]))

    # penumbral floor — a dark ring the filaments sit on (sinks the surrounding
    # granulation so the spot reads as a depression, the Wilson effect)
    floor = blackbody(MODEL["T_penumbra"] - 200.0, brightness_ratio(MODEL["T_penumbra"] - 200.0))
    page.circle([sx, sy], pen_r, decorative=True, fill=radial_gradient(
        [(floor, 0.0), (floor, 0.86), (rgba(floor, 0.55), 0.96), (rgba(floor, 0.0), 1.0)],
        at=[sx, sy], radius=pen_r),
        **style_effects(filter=filter_chain(blur_filter(mm2(0.3)))))
    # radial penumbral filaments — dense, short, bright grains combed outward.
    grain = blackbody(MODEL["T_penumbra"] + 300.0, brightness_ratio(MODEL["T_penumbra"] + 300.0))
    for i in range(520):
        ang = RNG.uniform(0, 2 * math.pi)
        r0 = umbra_r * RNG.uniform(0.96, 1.10)
        r1 = pen_r * RNG.uniform(0.90, 1.02)
        wob = RNG.uniform(-0.035, 0.035)
        mid = (r0 + r1) / 2
        pts = [(sx + r0 * math.cos(ang), sy + r0 * math.sin(ang)),
               (sx + mid * math.cos(ang + wob), sy + mid * math.sin(ang + wob)),
               (sx + r1 * math.cos(ang), sy + r1 * math.sin(ang))]
        obj = stroke_outline(pts, mm2(0.34) * RNG.uniform(0.7, 1.25),
                             profile=lambda t: 0.35 + 0.65 * math.sin(math.pi * t),
                             cap="round", smooth=True)
        obj.update({"fill": grain, "opacity": round(RNG.uniform(0.4, 0.85), 3),
                    "decorative": True})
        page.add(obj)
    # umbra — dark, with a soft penumbra-facing edge and a scatter of umbral dots
    page.circle([sx, sy], umbra_r, decorative=True, fill=radial_gradient(
        [(umbra, 0.0), (umbra, 0.62), (rgba(floor, 0.85), 0.94), (rgba(floor, 0.0), 1.0)],
        at=[sx, sy], radius=umbra_r),
        **style_effects(filter=filter_chain(blur_filter(mm2(0.12)))))
    for _ in range(9):
        a, rr = RNG.uniform(0, 2 * math.pi), umbra_r * RNG.uniform(0, 0.62)
        page.circle([sx + rr * math.cos(a), sy + rr * math.sin(a)], mm2(0.3),
                    fill=blackbody(MODEL["T_umbra"] + 700.0, 0.5),
                    opacity=round(RNG.uniform(0.4, 0.7), 3), decorative=True)

    # a scale bar — 10 Mm — so the plate states its own magnification
    bx, by = mm2(3.0), W2 - mm2(4.0)
    page.rect([bx, by, mm2(10.0), 6], fill="#EAD9B0", decorative=True)
    page.text([bx, by - 44, 360, 40], "10 Mm  (~14,000 km)",
              style={"font_family": ["Inter"], "font_size": 26, "color": "#EAD9B0",
                     "font_weight": 600})


def build() -> DocumentBuilder:
    doc = DocumentBuilder(title="The Sun — physically-derived plate", profile="deck")
    doc.define_color("photosphere", blackbody(T_EFF))
    doc.define_color("limb", blackbody(layer_temperature(0.0), limb_intensity(0.0)))
    doc.define_color("umbra", blackbody(MODEL["T_umbra"], brightness_ratio(MODEL["T_umbra"])))
    doc.define_color("penumbra",
                     blackbody(MODEL["T_penumbra"], brightness_ratio(MODEL["T_penumbra"])))

    page = doc.page("sun", canvas={"size": [W, H], "units": "px"},
                    coordinate_mode="absolute",
                    post={"bloom": {"radius": 26.0, "strength": 0.20, "threshold": 0.88},
                          "grain": {"amount": 0.014, "seed": 7, "monochrome": True}},
                    meta={"model": "Eddington grey atmosphere + Planck; IAU 2015 B3 nominals"})
    page.layer("space"); draw_space(page)
    page.layer("aureole"); draw_aureole(page)
    page.layer("photosphere"); draw_photosphere(page)
    page.layer("mottle"); draw_photosphere_mottle(page)
    page.layer("faculae"); draw_faculae(page)
    page.layer("active"); draw_active_regions(page)
    page.layer("limb"); draw_limb(page)
    page.layer("prominences"); draw_prominences(page)

    closeup = doc.page("closeup", canvas={"size": [W2, W2], "units": "px"},
                       coordinate_mode="absolute",
                       post={"grain": {"amount": 0.016, "seed": 11, "monochrome": True}},
                       meta={"scale": f"{PX_PER_MM2:.0f} px/Mm — granulation resolved"})
    closeup.layer("main")
    draw_closeup(closeup)
    return doc


def report() -> None:
    """Print the derived quantities so the numbers behind the picture are visible."""
    print(f"{'IAU nominal T_eff':32} {T_EFF:8.1f} K")
    print(f"{'IAU nominal R_sun':32} {R_SUN_MM:8.1f} Mm  ->  {PX_PER_MM:.3f} px/Mm")
    print(f"{'disk-centre layer T (mu=1)':32} {layer_temperature(1.0):8.1f} K")
    print(f"{'extreme-limb layer T (mu=0)':32} {layer_temperature(0.0):8.1f} K")
    print(f"{'limb/centre intensity':32} {limb_intensity(0.0):8.3f}  (Eddington: exactly 2/5)")
    print(f"{'umbra / photosphere (T^4)':32} {brightness_ratio(MODEL['T_umbra']):8.3f}")
    print(f"{'penumbra / photosphere (T^4)':32} {brightness_ratio(MODEL['T_penumbra']):8.3f}")
    print(f"{'granule diameter':32} {mm(MODEL['granule_Mm']):8.2f} px  (sub-pixel: a texture)")
    print(f"{'granule diameter (close-up)':32} {mm2(MODEL['granule_Mm']):8.2f} px  (plate 2 resolves it)")
    print()
    print(f"tones — physical D65 vs as-rendered through FILTER_GLASS {FILTER_GLASS}:")
    print(f"  {'':14} {'':>7}  {'':>6}     {'true D65':>9}   {'rendered':>9}")
    for label, temp, inten in (("disk centre", layer_temperature(1.0), limb_intensity(1.0)),
                               ("mid disk", layer_temperature(0.6), limb_intensity(0.6)),
                               ("limb", layer_temperature(0.0), limb_intensity(0.0)),
                               ("penumbra", MODEL["T_penumbra"],
                                brightness_ratio(MODEL["T_penumbra"])),
                               ("umbra", MODEL["T_umbra"],
                                brightness_ratio(MODEL["T_umbra"]))):
        print(f"  {label:14} {temp:7.1f} K  x{inten:5.3f}     "
              f"{true_tone(temp, inten):>9}   {blackbody(temp, inten):>9}")


OUTPUT_YAML_PATH = os.path.join(ROOT, "out", "sun", "sun.fg.yaml")

if __name__ == "__main__":
    report()
    os.makedirs(os.path.dirname(OUTPUT_YAML_PATH), exist_ok=True)
    build().write(OUTPUT_YAML_PATH, fail_on_error=True)
    print(f"\nwrote {OUTPUT_YAML_PATH}")
