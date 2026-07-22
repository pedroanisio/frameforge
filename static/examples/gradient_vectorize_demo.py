"""Gradient paint extraction — raster→vector with fitted gradient fills.

The vectorize lane's gradient recipe end to end, self-contained: synthesize a
small "shaded emblem" raster (a linear-ramp lozenge + a radial-glow disc on
black), trace it, and re-paint the traced shapes from the source pixels with
``apply_gradient_fills`` — flat/linear/radial candidates ranked per shape by
colour rms (``frameforge.vision.domain.gradient_fit``). The same capability is
one argument over MCP: ``vectorize_image(fill_mode='gradient')``, plus
``thresholds=[30, 110, 190]`` in trace mode to stack darkest-first luminance
layers for glossy multi-level art.

Going further (the proven glossy-emblem recipe, NCC 0.976 → 0.994 on the
lotus reference): ``fill_mode='shading'`` decomposes deep shapes into
contour-following rim bands (``apply_gradient_fills(bands=3)`` at the engine
level), then the ``refine_reconstruction`` tool refits every paint on its
VISIBLE pixels against the source (``vision.infrastructure.refine``), and
``Page.post`` ({blur, bloom, grain}) adds raster-stage media finishing.

Run: ``uv run python static/examples/gradient_vectorize_demo.py``
(needs the ``vision`` group; writes to ``_tmp/gradient-vectorize-demo/``).
"""
from __future__ import annotations

import pathlib
import tempfile

from PIL import Image, ImageDraw


def _synthesize_source(path: pathlib.Path) -> None:
    """A gradient-art stand-in: ramp lozenge + radial disc, both on black."""
    img = Image.new("RGB", (360, 220), "black")
    draw = ImageDraw.Draw(img)
    for i in range(180):
        t = i / 179.0
        col = (int(30 + 60 * t), int(70 + 170 * t), int(210 + 40 * t))
        draw.line([(30 + i, 60), (30 + i, 170)], fill=col)
    px = img.load()
    for y in range(220):
        for x in range(240, 360):
            r = ((x - 295) ** 2 + (y - 110) ** 2) ** 0.5
            if r <= 52:
                t = r / 52.0
                px[x, y] = (int(250 - 60 * t), int(240 - 190 * t), int(250 - 30 * t))
    img.save(path)


def build():
    from frameforge.sdk import DocumentBuilder
    from frameforge.vision.infrastructure.vectorize import (
        apply_gradient_fills,
        raster_to_objects,
    )

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="fg-gradient-demo-"))
    source = tmp / "source.png"
    _synthesize_source(source)

    objects, w, h = raster_to_objects(source, mode="region", colors=6, max_dim=0)
    summary = apply_gradient_fills(objects, Image.open(source).convert("RGB"))
    print(f"paint summary: {summary}")

    builder = DocumentBuilder(title="Gradient vectorize demo", lang="en")
    page = builder.page("demo", canvas={"size": [w, h], "units": "px"},
                        coordinate_mode="absolute")
    page.rect([0, 0, w, h], fill="#000000")
    layer = page.layer("fitted")
    for obj in objects:
        layer.add(obj)
    return builder


if __name__ == "__main__":
    out = pathlib.Path(__file__).resolve().parents[2] / "_tmp" / "gradient-vectorize-demo"
    out.mkdir(parents=True, exist_ok=True)
    from frameforge.sdk.io import serialize

    doc = build().build()
    (out / "gradient-vectorize-demo.fg.yaml").write_text(
        serialize(doc, format="yaml"), encoding="utf-8")
    print(f"wrote {out / 'gradient-vectorize-demo.fg.yaml'}")
