"""CairoSVG rasterization — a browser-free PNG fallback for page SVGs.

When headless Chromium is unavailable, FrameGraph SVG can still be rasterized to
PNG with CairoSVG (pure-Python bindings over libcairo), so a vision model can
*see* — and therefore verify — a render without a browser. Fidelity for the
vector/text/gradient core is faithful; browser-only paint (some CSS filters,
blend modes, backdrop filters) is the trade-off for not needing Chromium.
"""
from __future__ import annotations

import os
from pathlib import Path


class CairoRendererUnavailable(RuntimeError):
    """Raised when the optional CairoSVG renderer is unavailable."""


def available() -> bool:
    """Return True when CairoSVG can be imported."""
    try:
        import cairosvg  # noqa: F401
    except Exception:
        return False
    return True


def rasterize_svg_cairo(
    svg: str,
    out_path: str | Path,
    *,
    base_dir: str | Path | None = None,
    scale: float = 1.0,
) -> Path:
    """Rasterize one SVG string to a PNG file with CairoSVG.

    ``base_dir`` is used as the URL base so relative asset references resolve.
    Raises :class:`CairoRendererUnavailable` when CairoSVG is not installed.
    """
    try:
        import cairosvg
    except ImportError as exc:  # pragma: no cover - exercised via the unavailable path
        raise CairoRendererUnavailable(
            "CairoSVG is not installed; install the `mcp` or `pdfout` dependency group."
        ) from exc

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    url = os.path.join(str(base_dir), "") if base_dir is not None else None
    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=str(out),
        scale=float(scale),
        url=url,
        unsafe=True,
    )
    return out
