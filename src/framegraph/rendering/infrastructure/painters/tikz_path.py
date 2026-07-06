"""SVG path-data -> TikZ path geometry conversion.

Pure functions (no backend/state dependency) shared by the LaTeX `FigureTikz`
transpiler and the `TikzPainter` adapter, so the converter survives the fork's
removal (ADR 0001 slice 3b-5c). Extracted verbatim from `FigureTikz._path_d`/
`_path_segments`/`_arc_to_cubics` (behaviour byte-identical).
"""
from __future__ import annotations

import math
import re

from framegraph.rendering.domain.geometry import fnum, num


def path_data(d):
    if isinstance(d, list):
        return path_segments(d)
    if not isinstance(d, str):
        return ""
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", d.replace(",", " "))
    out, cmd, cur, start, i = [], None, (0.0, 0.0), (0.0, 0.0), 0
    last_cubic_ctrl = None
    last_quad_ctrl = None

    def point(relative=False):
        nonlocal i, cur
        if i + 1 >= len(tokens):
            return None
        x, y = num(tokens[i], None), num(tokens[i + 1], None)
        i += 2
        if x is None or y is None:
            return None
        if relative:
            x, y = cur[0] + x, cur[1] + y
        cur = (x, y)
        return cur

    def cubic(c1, c2, end):
        return (
            f".. controls ({fnum(c1[0])},{fnum(c1[1])}) and ({fnum(c2[0])},{fnum(c2[1])}) .. "
            f"({fnum(end[0])},{fnum(end[1])})"
        )

    def quad(c, end, start_point):
        c1 = (start_point[0] + 2 / 3 * (c[0] - start_point[0]), start_point[1] + 2 / 3 * (c[1] - start_point[1]))
        c2 = (end[0] + 2 / 3 * (c[0] - end[0]), end[1] + 2 / 3 * (c[1] - end[1]))
        return cubic(c1, c2, end)

    while i < len(tokens):
        if re.match(r"^[A-Za-z]$", tokens[i]):
            cmd = tokens[i]
            i += 1
        if cmd is None:
            break
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            p = point(rel)
            if p is None:
                break
            start = p
            out.append(f"({fnum(p[0])},{fnum(p[1])})")
            cmd = "l" if rel else "L"
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif c == "L":
            p = point(rel)
            if p is None:
                break
            out.append(f"-- ({fnum(p[0])},{fnum(p[1])})")
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif c == "H":
            x = num(tokens[i], None) if i < len(tokens) else None
            i += 1
            if x is None:
                break
            cur = ((cur[0] + x) if rel else x, cur[1])
            out.append(f"-- ({fnum(cur[0])},{fnum(cur[1])})")
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif c == "V":
            y = num(tokens[i], None) if i < len(tokens) else None
            i += 1
            if y is None:
                break
            cur = (cur[0], (cur[1] + y) if rel else y)
            out.append(f"-- ({fnum(cur[0])},{fnum(cur[1])})")
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif c == "C":
            vals = [num(tokens[i + j], None) for j in range(6)] if i + 5 < len(tokens) else []
            i += 6
            if len(vals) != 6 or any(v is None for v in vals):
                break
            x1, y1, x2, y2, x, y = vals
            if rel:
                x1, y1, x2, y2, x, y = cur[0] + x1, cur[1] + y1, cur[0] + x2, cur[1] + y2, cur[0] + x, cur[1] + y
            cur = (x, y)
            last_cubic_ctrl = (x2, y2)
            last_quad_ctrl = None
            out.append(cubic((x1, y1), (x2, y2), cur))
        elif c == "S":
            vals = [num(tokens[i + j], None) for j in range(4)] if i + 3 < len(tokens) else []
            i += 4
            if len(vals) != 4 or any(v is None for v in vals):
                break
            x2, y2, x, y = vals
            if rel:
                x2, y2, x, y = cur[0] + x2, cur[1] + y2, cur[0] + x, cur[1] + y
            c1 = (2 * cur[0] - last_cubic_ctrl[0], 2 * cur[1] - last_cubic_ctrl[1]) if last_cubic_ctrl else cur
            cur = (x, y)
            last_cubic_ctrl = (x2, y2)
            last_quad_ctrl = None
            out.append(cubic(c1, (x2, y2), cur))
        elif c == "Q":
            vals = [num(tokens[i + j], None) for j in range(4)] if i + 3 < len(tokens) else []
            i += 4
            if len(vals) != 4 or any(v is None for v in vals):
                break
            x1, y1, x, y = vals
            if rel:
                x1, y1, x, y = cur[0] + x1, cur[1] + y1, cur[0] + x, cur[1] + y
            start_point = cur
            cur = (x, y)
            last_cubic_ctrl = None
            last_quad_ctrl = (x1, y1)
            out.append(quad(last_quad_ctrl, cur, start_point))
        elif c == "T":
            x = num(tokens[i], None) if i < len(tokens) else None
            y = num(tokens[i + 1], None) if i + 1 < len(tokens) else None
            i += 2
            if x is None or y is None:
                break
            p = (cur[0] + x, cur[1] + y) if rel else (x, y)
            control = (2 * cur[0] - last_quad_ctrl[0], 2 * cur[1] - last_quad_ctrl[1]) if last_quad_ctrl else cur
            start_point = cur
            cur = p
            last_cubic_ctrl = None
            last_quad_ctrl = control
            out.append(quad(control, cur, start_point))
        elif c == "A":
            vals = [num(tokens[i + j], None) for j in range(7)] if i + 6 < len(tokens) else []
            i += 7
            if len(vals) != 7 or any(v is None for v in vals):
                break
            rx, ry, rot, large, sweep, x, y = vals
            end = (cur[0] + x, cur[1] + y) if rel else (x, y)
            segments = arc_to_cubics(cur, rx, ry, rot, large, sweep, end)
            if not segments:
                out.append(f"-- ({fnum(end[0])},{fnum(end[1])})")
            else:
                out.extend(cubic(c1, c2, p) for c1, c2, p in segments)
            cur = end
            last_cubic_ctrl = segments[-1][1] if segments else None
            last_quad_ctrl = None
        elif c == "Z":
            cur = start
            out.append("-- cycle")
            last_cubic_ctrl = None
            last_quad_ctrl = None
        else:
            break
    return " ".join(out)

def path_segments(segments):
    out = []
    cur = start = (0.0, 0.0)
    last_cubic_ctrl = None
    last_quad_ctrl = None

    def cubic(c1, c2, end):
        return (
            f".. controls ({fnum(c1[0])},{fnum(c1[1])}) and ({fnum(c2[0])},{fnum(c2[1])}) "
            f".. ({fnum(end[0])},{fnum(end[1])})"
        )

    def quad(c, end, start_point):
        c1 = (start_point[0] + 2 / 3 * (c[0] - start_point[0]), start_point[1] + 2 / 3 * (c[1] - start_point[1]))
        c2 = (end[0] + 2 / 3 * (c[0] - end[0]), end[1] + 2 / 3 * (c[1] - end[1]))
        return cubic(c1, c2, end)

    for seg in segments:
        rel = isinstance(seg[0], str) and seg[0].islower() if isinstance(seg, (list, tuple)) and seg else False
        if not isinstance(seg, (list, tuple)) or not seg:
            continue
        cmd = str(seg[0]).upper()
        vals = [num(v, None) for v in seg[1:]]
        if cmd == "M" and len(vals) >= 2:
            cur = ((cur[0] + vals[0], cur[1] + vals[1]) if rel else (vals[0], vals[1]))
            start = cur
            out.append(f"({fnum(cur[0])},{fnum(cur[1])})")
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif cmd == "L" and len(vals) >= 2:
            cur = ((cur[0] + vals[0], cur[1] + vals[1]) if rel else (vals[0], vals[1]))
            out.append(f"-- ({fnum(cur[0])},{fnum(cur[1])})")
            last_cubic_ctrl = None
            last_quad_ctrl = None
        elif cmd == "C" and len(vals) >= 6:
            c1 = ((cur[0] + vals[0], cur[1] + vals[1]) if rel else (vals[0], vals[1]))
            c2 = ((cur[0] + vals[2], cur[1] + vals[3]) if rel else (vals[2], vals[3]))
            cur = ((cur[0] + vals[4], cur[1] + vals[5]) if rel else (vals[4], vals[5]))
            last_cubic_ctrl = c2
            last_quad_ctrl = None
            out.append(cubic(c1, c2, cur))
        elif cmd == "S" and len(vals) >= 4:
            c1 = (2 * cur[0] - last_cubic_ctrl[0], 2 * cur[1] - last_cubic_ctrl[1]) if last_cubic_ctrl else cur
            c2 = ((cur[0] + vals[0], cur[1] + vals[1]) if rel else (vals[0], vals[1]))
            cur = ((cur[0] + vals[2], cur[1] + vals[3]) if rel else (vals[2], vals[3]))
            last_cubic_ctrl = c2
            last_quad_ctrl = None
            out.append(cubic(c1, c2, cur))
        elif cmd == "Q" and len(vals) >= 4:
            control = ((cur[0] + vals[0], cur[1] + vals[1]) if rel else (vals[0], vals[1]))
            start_point = cur
            cur = ((cur[0] + vals[2], cur[1] + vals[3]) if rel else (vals[2], vals[3]))
            last_cubic_ctrl = None
            last_quad_ctrl = control
            out.append(quad(control, cur, start_point))
        elif cmd == "T" and len(vals) >= 2:
            control = (2 * cur[0] - last_quad_ctrl[0], 2 * cur[1] - last_quad_ctrl[1]) if last_quad_ctrl else cur
            start_point = cur
            cur = ((cur[0] + vals[0], cur[1] + vals[1]) if rel else (vals[0], vals[1]))
            last_cubic_ctrl = None
            last_quad_ctrl = control
            out.append(quad(control, cur, start_point))
        elif cmd == "A" and len(vals) >= 7:
            end = ((cur[0] + vals[5], cur[1] + vals[6]) if rel else (vals[5], vals[6]))
            segments = arc_to_cubics(cur, vals[0], vals[1], vals[2], vals[3], vals[4], end)
            if not segments:
                out.append(f"-- ({fnum(end[0])},{fnum(end[1])})")
            else:
                out.extend(cubic(c1, c2, p) for c1, c2, p in segments)
            cur = end
            last_cubic_ctrl = segments[-1][1] if segments else None
            last_quad_ctrl = None
        elif cmd == "Z":
            cur = start
            last_cubic_ctrl = None
            last_quad_ctrl = None
            out.append("-- cycle")
    return " ".join(out)

def arc_to_cubics(start, rx, ry, rotation, large_arc, sweep, end):
    """Convert one SVG elliptical arc segment to cubic Bezier segments."""
    x1, y1 = start
    x2, y2 = end
    if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
        return []
    rx, ry = abs(num(rx, 0) or 0), abs(num(ry, 0) or 0)
    if rx <= 0 or ry <= 0:
        return []

    phi = math.radians(num(rotation, 0) or 0)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    dx2, dy2 = (x1 - x2) / 2, (y1 - y2) / 2
    x1p = cos_phi * dx2 + sin_phi * dy2
    y1p = -sin_phi * dx2 + cos_phi * dy2

    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale

    rx2, ry2 = rx * rx, ry * ry
    x1p2, y1p2 = x1p * x1p, y1p * y1p
    denom = rx2 * y1p2 + ry2 * x1p2
    if denom <= 0:
        return []
    sign = -1 if bool(int(num(large_arc, 0) or 0)) == bool(int(num(sweep, 0) or 0)) else 1
    factor = sign * math.sqrt(max(0, (rx2 * ry2 - rx2 * y1p2 - ry2 * x1p2) / denom))
    cxp = factor * rx * y1p / ry
    cyp = factor * -ry * x1p / rx
    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x2) / 2
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y2) / 2

    def angle_between(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        length = math.hypot(ux, uy) * math.hypot(vx, vy)
        if length <= 0:
            return 0.0
        ang = math.acos(max(-1, min(1, dot / length)))
        return -ang if ux * vy - uy * vx < 0 else ang

    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    vx, vy = (-x1p - cxp) / rx, (-y1p - cyp) / ry
    theta1 = angle_between(1, 0, ux, uy)
    delta = angle_between(ux, uy, vx, vy)
    if not bool(int(num(sweep, 0) or 0)) and delta > 0:
        delta -= 2 * math.pi
    elif bool(int(num(sweep, 0) or 0)) and delta < 0:
        delta += 2 * math.pi

    count = max(1, int(math.ceil(abs(delta) / (math.pi / 2))))
    step = delta / count
    segments = []
    for idx in range(count):
        t1 = theta1 + idx * step
        t2 = t1 + step
        alpha = 4 / 3 * math.tan((t2 - t1) / 4)
        p1 = (math.cos(t1), math.sin(t1))
        p2 = (math.cos(t2), math.sin(t2))
        c1 = (p1[0] - alpha * p1[1], p1[1] + alpha * p1[0])
        c2 = (p2[0] + alpha * p2[1], p2[1] - alpha * p2[0])

        def map_point(p):
            px, py = p[0] * rx, p[1] * ry
            return (
                cos_phi * px - sin_phi * py + cx,
                sin_phi * px + cos_phi * py + cy,
            )

        segments.append((map_point(c1), map_point(c2), map_point(p2)))
    if segments:
        c1, c2, _p = segments[-1]
        segments[-1] = (c1, c2, end)
    return segments

# -- text -------------------------------------------------------------- #
