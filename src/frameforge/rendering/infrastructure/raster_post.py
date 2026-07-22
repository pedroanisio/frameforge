"""Raster-stage post effects (Gap A3): blur → bloom → grain over a rendered PNG.

The vector pipeline stays untouched — these effects model *media* qualities a
crisp vector render cannot carry (JPEG/photographic bloom around bright edges,
sensor/film grain, soft focus), which is exactly the residual measured between
a reconstruction and a soft-media reference. Application order is FIXED
(blur, then bloom, then grain) so a `post` spec means one thing everywhere.

Radii are canvas px; ``scale`` multiplies them so a 2× raster gets a 2× halo.
Grain is strictly deterministic: a seeded ``numpy.random.RandomState``, never
wall-clock entropy — same spec, same bytes, on every run.

Pure and lazy: PIL + NumPy import only when an effect actually runs, so the
dependency-free vector path never pays for this module.
"""
from __future__ import annotations

from typing import Any

#: Fixed application order — also the vocabulary of effect names reported by
#: callers (e.g. the MCP raster lane's ``post_effects`` annotation).
EFFECT_ORDER = ("blur", "bloom", "grain")


def effect_names(post: "dict[str, Any] | None") -> list[str]:
    """The effects a ``post`` spec will actually apply, in application order."""
    if not isinstance(post, dict):
        return []
    return [name for name in EFFECT_ORDER if post.get(name)]


def apply_post_effects(image, post: "dict[str, Any] | None", *, scale: float = 1.0):
    """Apply a ``Page.post`` spec to a PIL image; return the processed image.

    ``post`` is the plain-dict form of the model's ``PostEffects`` (the raster
    lane works on parsed documents). A falsy/empty spec returns the input
    unchanged (identity — pinned by test).
    """
    if not post or not isinstance(post, dict):
        return image
    names = effect_names(post)
    if not names:
        return image
    from PIL import Image, ImageFilter
    import numpy as np

    img = image.convert("RGB")

    blur = post.get("blur")
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(float(blur) * scale))

    bloom = post.get("bloom")
    if bloom:
        radius = float(bloom.get("radius", 8.0)) * scale
        strength = float(bloom.get("strength", 0.5))
        threshold = float(bloom.get("threshold", 0.75))
        a = np.asarray(img, dtype=np.float32) / 255.0
        lum = a @ np.asarray((0.2126, 0.7152, 0.0722), dtype=np.float32)
        bright = a * (lum >= threshold).astype(np.float32)[..., None]
        halo_src = Image.fromarray((bright * 255.0 + 0.5).astype("uint8"))
        halo = np.asarray(halo_src.filter(ImageFilter.GaussianBlur(radius)),
                          dtype=np.float32) / 255.0 * strength
        out = 1.0 - (1.0 - a) * (1.0 - halo)          # screen composite
        img = Image.fromarray((np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype("uint8"))

    grain = post.get("grain")
    if grain:
        amount = float(grain.get("amount", 0.0))
        if amount > 0.0:
            rng = np.random.RandomState(int(grain.get("seed", 0)))
            a = np.asarray(img, dtype=np.float32)
            mono = grain.get("monochrome")
            if mono is None or mono:
                noise = rng.normal(0.0, amount * 255.0, a.shape[:2])[..., None]
            else:
                noise = rng.normal(0.0, amount * 255.0, a.shape)
            img = Image.fromarray(np.clip(a + noise, 0.0, 255.0).astype("uint8"))

    return img


__all__ = ["EFFECT_ORDER", "apply_post_effects", "effect_names"]
