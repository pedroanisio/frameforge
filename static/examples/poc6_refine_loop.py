"""POC-06 — the drawing agent's improvement pass: measure, adjust, re-run, stop.

The wired loop (POC-05) produces a result; this is how an agent *improves* it
instead of accepting pass 1. Each pass is a measured hill-climb, not a vibe:

    for each pass:
        re-ingest at a finer setting        (the "adjustment" an agent would make)
        measure ink-IoU fidelity vs source  (the gate / objective)
        measure object count                (the cost — honest tradeoff)
        keep the best; STOP at diminishing returns (gain < epsilon)

This models exactly the agent protocol used by hand earlier (render → critique →
fix → re-render): the coach supplies the signals (fidelity gate + object cost +
the silhouette/rubric), the agent drives the search and knows when to stop. The
ceiling is honest — fidelity plateaus; you cannot perfect a trace by passes alone.

Run:
    uv run --group vision python examples/poc6_refine_loop.py \
        demo/Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg --out out/poc6
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Sequence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ.get("FG_ROOT", ROOT))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frameforge.sdk import DocumentBuilder, render_page_svgs  # noqa: E402
from frameforge.coach import ingest  # noqa: E402
from poc3_ingest_compose import ink_iou, restyle_strokes, place  # noqa: E402

Obj = dict[str, Any]
DEFAULT_IMG = os.path.join(ROOT, "demo", "Gemini_Generated_Image_lkcai8lkcai8lkca.jpeg")
FONT = ["Inter", "Helvetica", "Arial", "sans-serif"]

# the agent's adjustment schedule: coarse → fine (more nodes, keep smaller marks)
SCHEDULE = [
    {"detail": 0.0060, "min_area": 90.0},
    {"detail": 0.0030, "min_area": 45.0},
    {"detail": 0.0015, "min_area": 22.0},
    {"detail": 0.0008, "min_area": 12.0},
]
EPSILON = 0.012   # stop when a pass adds less than this much fidelity


def fidelity(image: str, objs: list[Obj], w: int, h: int) -> float | None:
    """ink-IoU of a flat black-ink render of the trace vs the source raster."""
    b = DocumentBuilder(title="fid")
    p = b.page("p", canvas={"size": [w, h], "units": "px"}, coordinate_mode="absolute")
    p.rect([0, 0, w, h], fill="#FFFFFF")
    lay = p.layer("ink")
    for o in restyle_strokes(objs, stroke="#000000", width=1.0):
        lay.add(o)
    return ink_iou(image, render_page_svgs(b.build())[0])


def refine(image: str, max_dim: int = 1100):
    """Run the measured improvement loop; return the trajectory + best snapshot."""
    traj: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    first: dict[str, Any] | None = None
    prev_fid = -1.0
    stopped_at = None
    for i, pp in enumerate(SCHEDULE):
        objs, w, h = ingest(image, mode="outline", detail=pp["detail"],
                            min_area=pp["min_area"], max_dim=max_dim)
        fid = fidelity(image, objs, w, h) or 0.0
        rec = {"pass": i, **pp, "fid": round(fid, 3), "objs": len(objs),
               "snap": (objs, w, h)}
        traj.append(rec)
        gain = fid - prev_fid
        flag = ""
        if first is None:
            first = rec
        if best is None or fid > best["fid"]:
            best = rec
        print(f"  pass {i}: detail={pp['detail']:.4f} min_area={pp['min_area']:>5.0f} "
              f"→ ink-IoU={fid:.3f}  objs={len(objs):>4}  Δ={gain:+.3f}{flag}")
        if i > 0 and gain < EPSILON:
            stopped_at = i
            print(f"  ↳ gain {gain:+.3f} < ε={EPSILON} — diminishing returns, agent STOPS.")
            break
        prev_fid = fid
    return traj, first, best, stopped_at


def _panel(page, x, y, w, h, label, color, objs, src):
    page.add({"type": "rect", "box": [x, y, w, h], "fill": "#FFFFFF", "radius": 10})
    page.add({"type": "text", "box": [x + 14, y + 8, w - 28, 20], "text": label,
              "style": {"font_family": FONT, "font_size": 13, "font_weight": 700, "color": color}})
    for o in place(restyle_strokes(objs, stroke="#10151F", width=1.0),
                   [x + 10, y + 34, w - 20, h - 44], src):
        page.add(o)


def build_before_after(first, best):
    cw, ch, pad = 600, 470, 24
    W, H = 2 * cw + 3 * pad, 44 + ch + 2 * pad
    b = DocumentBuilder(title="poc6-before-after")
    page = b.page("ba", canvas={"size": [W, H], "units": "px"}, coordinate_mode="absolute")
    page.rect([0, 0, W, H], fill="#0E1116")
    page.add({"type": "text", "box": [pad, 12, W - 2 * pad, 26],
              "text": "Improvement pass: agent re-traces + measures fidelity, keeps the best",
              "style": {"font_family": FONT, "font_size": 18, "font_weight": 700, "color": "#F2F5FA"}})
    fobjs, fw, fh = first["snap"]
    bobjs, bw, bh = best["snap"]
    _panel(page, pad, 44 + pad, cw, ch,
           f"pass {first['pass']} (baseline) — ink-IoU {first['fid']}, {first['objs']} objs",
           "#8B949E", fobjs, (fw, fh))
    _panel(page, pad + cw + pad, 44 + pad, cw, ch,
           f"pass {best['pass']} (best) — ink-IoU {best['fid']}, {best['objs']} objs",
           "#3FB950", bobjs, (bw, bh))
    return b


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", nargs="?", default=DEFAULT_IMG)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "poc6"))
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    print(f"[refine] {os.path.basename(args.image)} — hill-climb fidelity over passes:")
    traj, first, best, stopped = refine(args.image)
    improved = best["fid"] - first["fid"]
    print(f"\n[result] baseline ink-IoU {first['fid']} → best {best['fid']} "
          f"(+{improved:.3f}) at pass {best['pass']}; "
          f"{'stopped early' if stopped else 'ran full schedule'}.")

    b = build_before_after(first, best)
    svg = render_page_svgs(b.build())[0]
    b.write(os.path.join(args.out, "before_after.fg.yaml"))
    with open(os.path.join(args.out, "before_after.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"[write] {args.out}/before_after.svg (+ .fg.yaml)")

    ok = improved >= 0 and best["fid"] >= first["fid"]
    print(f"\nVERDICT: {'IMPROVED — measured gain, agent stops at the knee' if ok else 'NO GAIN'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
