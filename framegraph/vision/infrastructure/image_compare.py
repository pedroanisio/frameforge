"""Side-by-side visual comparison of a reference image against a candidate render.

The forward pipeline verifies that a document *renders*; it cannot tell whether the
render *looks like* the thing it was meant to reproduce. A vision model can judge
that — but only if it is shown the two images **close up and aligned**, not as two
separately-downscaled thumbnails where a wrong wordmark or an inverted gradient is
sub-pixel. This adapter crops matching regions from both images, scales each region
up to a legible cell, and lays them out reference | candidate | difference with a
per-region pixel-match score baked onto the panel — so the agent literally sees
where the recreation is off.

⚠ ARCHITECTURAL CONTRACT (PALS's LAW): the pixel-match score is a *naive* metric
(mean absolute luminance difference), not a perceptual or semantic one. It is a
cheap hint, not a verdict — a low score reliably means "these differ", a high score
does **not** prove correctness. The image panels, judged by a vision model, are the
real signal; the number only routes attention.

Pillow is imported lazily so ``import framegraph.vision`` stays dependency-free; the
backend is only touched when a comparison is actually built.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Sequence


@dataclass(frozen=True)
class Region:
    """A named crop, in normalized coordinates (fractions of width/height, 0..1).

    Normalized boxes make the crop resolution-independent: the same ``box`` selects
    the same *relative* area of the reference and of a candidate rendered at a
    different pixel size, so the two crops line up without resampling either whole
    image first (both keep the same aspect ratio, which the recreation should).
    """

    name: str
    box: tuple[float, float, float, float]  # x, y, w, h — all in [0, 1]


@dataclass(frozen=True)
class Panel:
    """One composed comparison image plus its (naive) pixel-match score."""

    name: str
    image: Any            # PIL.Image.Image
    match_pct: float | None


_PIL_HINT = (
    "Image comparison needs Pillow. Install it with `uv sync --group vision` "
    "(or the `render` group), or `pip install pillow`."
)


def _pil():
    try:
        from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat
    except ImportError as exc:  # pragma: no cover - exercised only without Pillow
        raise RuntimeError(_PIL_HINT) from exc
    return Image, ImageChops, ImageDraw, ImageOps, ImageStat


def _font(size: int, *, bold: bool = False):
    """A TrueType face at ``size`` if one is resolvable, else Pillow's default.

    Text is drawn onto the *panel* by Pillow (not the FrameGraph renderer), so it
    renders as real glyphs regardless of the render environment's font situation.
    """
    from PIL import ImageFont

    names = (
        ["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold else
        ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - very old Pillow
        return ImageFont.load_default()


def load_rgb(data: bytes):
    """Decode image bytes to an RGB image (alpha flattened onto white)."""
    Image, *_ = _pil()
    img = Image.open(BytesIO(data))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img).convert("RGB")
        return img
    return img.convert("RGB")


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


def _crop_norm(img, box: Sequence[float]):
    x, y, w, h = box
    W, H = img.size
    left = _clamp01(x) * W
    top = _clamp01(y) * H
    right = _clamp01(x + w) * W
    bottom = _clamp01(y + h) * H
    if right - left < 1:
        right = min(W, left + 1)
    if bottom - top < 1:
        bottom = min(H, top + 1)
    return img.crop((int(left), int(top), int(round(right)), int(round(bottom))))


def pixel_match(a, b, *, size: int = 256) -> float:
    """A naive 0..100 match: 100 minus mean absolute luminance difference (rescaled).

    Both crops are resized to ``size``×``size`` grayscale first so images at
    different resolutions are comparable. This is deliberately simple and *not*
    perceptual (see the module contract); it is only meant to flag "clearly off".
    """
    _, ImageChops, _, _, ImageStat = _pil()
    ga = a.convert("L").resize((size, size))
    gb = b.convert("L").resize((size, size))
    mean = ImageStat.Stat(ImageChops.difference(ga, gb)).mean[0]  # 0..255
    return round(100.0 * (1.0 - mean / 255.0), 1)


def _diff_cell(a, b, size: tuple[int, int]):
    """A colourised difference image (bright red = mismatch) at ``size``."""
    _, ImageChops, _, ImageOps, _ = _pil()
    ga = a.convert("L").resize(size)
    gb = b.convert("L").resize(size)
    d = ImageOps.autocontrast(ImageChops.difference(ga, gb), cutoff=1)
    return ImageOps.colorize(d, black=(14, 14, 18), white=(255, 74, 74))


def _match_color(pct: float | None) -> tuple[int, int, int]:
    if pct is None:
        return (60, 60, 66)
    if pct >= 85:
        return (24, 132, 68)
    if pct >= 65:
        return (196, 132, 20)
    return (196, 44, 44)


# palette for the composed sheet (neutral so both dark- and light-ground crops read)
_SHEET_BG = (236, 236, 234)
_HEADER_BG = (24, 26, 32)
_CELL_BG = (250, 250, 249)
_CELL_BORDER = (206, 206, 202)
_CAP_FG = (70, 72, 78)


def _fit_cell(img, cell: int):
    """Thumbnail ``img`` into a ``cell``×``cell`` box, centred on the cell ground."""
    Image, *_ = _pil()
    thumb = img.copy()
    thumb.thumbnail((cell, cell), Image.LANCZOS)
    canvas = Image.new("RGB", (cell, cell), _CELL_BG)
    canvas.paste(thumb, ((cell - thumb.width) // 2, (cell - thumb.height) // 2))
    return canvas


def region_panel(reference, candidate, region: Region, *, diff: bool = True,
                 labels: tuple[str, str] = ("reference", "recreation"),
                 cell: int = 470) -> Panel:
    """Compose one ``reference | candidate [| difference]`` strip for ``region``."""
    Image, _, ImageDraw, _, _ = _pil()
    ref_crop = _crop_norm(reference, region.box)
    cand_crop = _crop_norm(candidate, region.box)
    match = pixel_match(ref_crop, cand_crop)

    cells = [(_fit_cell(ref_crop, cell), labels[0]),
             (_fit_cell(cand_crop, cell), labels[1])]
    if diff:
        cells.append((_fit_cell(_diff_cell(ref_crop, cand_crop, (cell, cell)), cell),
                      "difference (bright = mismatch)"))

    margin, gap, header, caption = 20, 16, 52, 34
    n = len(cells)
    width = margin * 2 + n * cell + (n - 1) * gap
    height = margin + header + cell + caption + margin
    sheet = Image.new("RGB", (width, height), _SHEET_BG)
    draw = ImageDraw.Draw(sheet)

    # header bar: region name (left) + pixel-match chip (right)
    draw.rectangle([0, 0, width, header], fill=_HEADER_BG)
    draw.text((margin, header // 2), region.name.upper(), font=_font(24, bold=True),
              fill=(240, 240, 238), anchor="lm")
    chip = f"pixel-match {match:.0f}%"
    draw.text((width - margin, header // 2), chip, font=_font(21, bold=True),
              fill=_match_color(match), anchor="rm")

    y = header + margin - 10
    for i, (img, cap) in enumerate(cells):
        x = margin + i * (cell + gap)
        sheet.paste(img, (x, y))
        draw.rectangle([x, y, x + cell - 1, y + cell - 1], outline=_CELL_BORDER, width=1)
        draw.text((x + cell // 2, y + cell + 8), cap, font=_font(18),
                  fill=_CAP_FG, anchor="ma")
    return Panel(region.name, sheet, match)


def overview_panel(reference, candidate, *,
                   labels: tuple[str, str] = ("reference", "recreation"),
                   height: int = 560) -> Panel:
    """A whole-image ``reference | candidate`` overview for context."""
    Image, _, ImageDraw, _, _ = _pil()

    def scaled(img):
        w = max(1, round(img.width * height / img.height))
        return img.resize((w, height), Image.LANCZOS)

    ri, ci = scaled(reference), scaled(candidate)
    match = pixel_match(reference, candidate)
    margin, gap, header, caption = 20, 18, 52, 34
    width = margin * 2 + ri.width + ci.width + gap
    total_h = margin + header + height + caption + margin
    sheet = Image.new("RGB", (width, total_h), _SHEET_BG)
    draw = ImageDraw.Draw(sheet)
    draw.rectangle([0, 0, width, header], fill=_HEADER_BG)
    draw.text((margin, header // 2), "OVERVIEW", font=_font(24, bold=True),
              fill=(240, 240, 238), anchor="lm")
    draw.text((width - margin, header // 2), f"pixel-match {match:.0f}%",
              font=_font(21, bold=True), fill=_match_color(match), anchor="rm")
    y = header + margin - 10
    for img, cap, x in ((ri, labels[0], margin),
                        (ci, labels[1], margin + ri.width + gap)):
        sheet.paste(img, (x, y))
        draw.rectangle([x, y, x + img.width - 1, y + img.height - 1],
                       outline=_CELL_BORDER, width=1)
        draw.text((x + img.width // 2, y + height + 8), cap, font=_font(18),
                  fill=_CAP_FG, anchor="ma")
    return Panel("overview", sheet, match)


def auto_regions(cols: int, rows: int) -> list[Region]:
    """A uniform ``cols``×``rows`` grid of regions covering the whole image."""
    cols = max(1, int(cols))
    rows = max(1, int(rows))
    out: list[Region] = []
    for r in range(rows):
        for c in range(cols):
            out.append(Region(
                name=f"r{r + 1}c{c + 1}",
                box=(c / cols, r / rows, 1.0 / cols, 1.0 / rows),
            ))
    return out


def build_panels(reference: bytes, candidate: bytes, *,
                 regions: Sequence[Region],
                 diff: bool = True,
                 labels: tuple[str, str] = ("reference", "recreation"),
                 include_overview: bool = True) -> list[Panel]:
    """Decode both images and compose an overview + one panel per region."""
    ref = load_rgb(reference)
    cand = load_rgb(candidate)
    panels: list[Panel] = []
    if include_overview:
        panels.append(overview_panel(ref, cand, labels=labels))
    for region in regions:
        panels.append(region_panel(ref, cand, region, diff=diff, labels=labels))
    return panels
