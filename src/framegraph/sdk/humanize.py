"""The humanize *hand* — a seeded, bounded imperfection pass.

Rationale
---------
A mechanically-perfect layout reads as machine-made. Real hands vary: they tilt a
shape a hair, press a little harder here, lay ink a shade denser there — and no
two repeats of the "same" mark ever coincide. This pass reproduces that, borrowing
the vocabulary of audio-sampler humanization (round-robin, velocity, pitch drift).

Determinism (the load-bearing constraint)
-----------------------------------------
FrameGraph renders against gated golden fixtures. Randomness that varied per run
would break every golden on every run. So every perturbation here is drawn from a
per-object RNG seeded from ``Humanize.seed`` + the object's identity — exactly the
discipline :func:`framegraph.sdk.macros.greeble`/``lorem`` already keep. Same
document + same seed → byte-identical output. Bump the seed to re-perform the page
like a fresh take.

Our frame (what makes this more than per-vertex jitter)
-------------------------------------------------------
1. **Correlated channels.** A hand has one state, not four dice. We draw a small
   2-D latent per object and *project* it onto the channels, so tilt, pressure and
   ink density co-vary the way a real hand's do — not as independent noise.
2. **Bell-shaped, tension-controlled excursions.** Human error is mostly tiny with
   the occasional larger slip; we draw Gaussian latents (clamped), with ``grain``
   setting the hand's tension, rather than the flat uniform noise that reads as
   mechanical-random.
3. **Topology-preserving.** The scalar channels never move geometry; the ``roughen``
   channel *does* — but its wobble is endpoint-anchored (the displacement tapers to
   zero at each segment end, ``sin(pi t)**0.8``), so lines still meet and closed
   shapes still close. An object a connector attaches to is exempt entirely.
4. **Round-robin for free.** The per-object key means two identical shapes at
   different positions never perturb identically — repeats never look stamped —
   and, unlike a single draw-order RNG stream, reordering objects does not reshuffle
   the whole page.

Scalar deltas are hard-clamped to their declared amplitude, so those channels are
*provably bounded*: a property test can assert "no rotation exceeds ``drift_deg``".

Channels: ``roughen`` (geometry wobble), ``drift_deg`` (tilt), ``weight`` (stroke),
``opacity`` (ink). The coherent-noise geometry model is ported from the operator's
own ``build_a6.py`` book. Scope: page-mode layer objects (and group children);
flow-story content is a later slice.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from hashlib import sha256
from random import Random
from typing import Any


def _stable_seed(*parts: Any) -> int:
    """A process-independent integer seed.

    Deliberately not Python's :func:`hash`, which salts ``str``/``bytes`` per
    process (``PYTHONHASHSEED``) and would make golden hashes drift across runs.
    """
    key = "\x1f".join(str(p) for p in parts)
    return int.from_bytes(sha256(key.encode("utf-8")).digest()[:8], "big")


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def _round(x: float) -> float:
    """Pin perturbed values to a stable precision so golden hashes are reproducible."""
    return round(float(x), 4)


@dataclass(frozen=True)
class Hand:
    """A resolved humanize spec: the perturbation source for one subtree."""

    enabled: bool = True
    seed: int = 0
    weight: float = 0.0
    opacity: float = 0.0
    drift_deg: float = 0.0
    roughen: float = 0.0
    grain: float = 1.0

    @classmethod
    def from_spec(cls, spec: Any) -> "Hand | None":
        """Build a :class:`Hand` from a document/object ``humanize`` dict (or ``None``)."""
        if not isinstance(spec, dict):
            return None
        grain = spec.get("grain")
        return cls(
            enabled=bool(spec.get("enabled", True)),
            seed=int(spec.get("seed", 0) or 0),
            weight=float(spec.get("weight", 0.0) or 0.0),
            opacity=float(spec.get("opacity", 0.0) or 0.0),
            drift_deg=float(spec.get("drift_deg", 0.0) or 0.0),
            roughen=float(spec.get("roughen", 0.0) or 0.0),
            grain=1.0 if grain is None else float(grain),
        )

    @property
    def active(self) -> bool:
        """True when this hand would change something."""
        return self.enabled and bool(
            self.weight or self.opacity or self.drift_deg or self.roughen)

    def channels(self, key: str) -> dict[str, float]:
        """Correlated, bell-shaped, clamped deltas for the object identified by ``key``.

        One 2-D latent (``h1``, ``h2``) is drawn from the keyed RNG and projected
        onto every channel, so the channels move together like a single hand.
        ``grain`` tightens the latent's spread. Each returned delta lies within
        ``[-amplitude, +amplitude]`` for its channel.
        """
        rng = Random(_stable_seed(self.seed, key))
        # Tension: grain 1.0 → sigma 0.5 (excursions hug zero); grain 0.0 → sigma 1.0.
        sigma = 1.0 - 0.5 * _clamp(self.grain, 0.0, 1.0)
        h1 = _clamp(rng.gauss(0.0, sigma))
        h2 = _clamp(rng.gauss(0.0, sigma))
        return {
            "rotation": self.drift_deg * _clamp(h1),
            # Pressure couples to tilt and ink; the mixing matrix is the "hand".
            "weight": self.weight * _clamp(-0.7 * h1 + 0.7 * h2),
            "opacity": self.opacity * _clamp(h2),
        }


def apply_humanize(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``data`` with the humanize hand applied; identity if off.

    Pure and deterministic. Walks page-mode layer objects (and their group
    children), perturbing whole-object rotation / opacity / inline stroke weight.
    When neither the document nor any object opts in, the input is returned
    unchanged (no copy) — so documents without a ``humanize`` spec render exactly
    as before and existing golden fixtures cannot move.
    """
    if not isinstance(data, dict):
        return data
    doc_hand = Hand.from_spec(data.get("humanize"))
    if doc_hand is None and not _contains_key(data.get("pages"), "humanize"):
        return data
    out = copy.deepcopy(data)
    for pi, page in enumerate(out.get("pages") or []):
        if not isinstance(page, dict):
            continue
        exempt = _connector_endpoint_ids(page)
        for li, layer in enumerate(page.get("layers") or []):
            if not isinstance(layer, dict) or not isinstance(layer.get("objects"), list):
                continue
            for oi, obj in enumerate(layer["objects"]):
                _walk(obj, doc_hand, f"p{pi}/l{li}/o{oi}", exempt)
    return out


def _walk(obj: Any, inherited: "Hand | None", key: str, exempt: set[str]) -> None:
    if not isinstance(obj, dict):
        return
    hand = inherited
    own = Hand.from_spec(obj.get("humanize"))
    if own is not None:
        hand = own
    if hand is not None and hand.active:
        _perturb(obj, hand, obj.get("id") or key, exempt)
    children = obj.get("children")
    if isinstance(children, list):
        for ci, child in enumerate(children):
            _walk(child, hand, f"{key}.c{ci}", exempt)


# Typographic objects are left entirely crisp: legibility is the type gates' domain,
# not the imperfection hand's (matches build_a6, which only ever wobbles geometry).
_TYPO_TYPES = frozenset({
    "text", "heading", "paragraph", "list", "bullet_list", "table",
    "code", "math", "icon", "toc", "bibliography",
})


def _perturb(obj: dict[str, Any], hand: "Hand", obj_key: str, exempt: set[str]) -> None:
    if obj.get("type") in _TYPO_TYPES:
        return
    is_connector = obj.get("type") == "connector"
    is_endpoint = str(obj.get("id") or "") in exempt
    # Roughen — the effect channel: convert straight primitives into hand-drawn
    # wobbly ones (coherent noise, endpoint-anchored). Runs first so the scalar
    # channels below apply to the converted object. Connectors and any object a
    # connector attaches to keep crisp geometry so anchors meet.
    if hand.roughen and not is_connector and not is_endpoint:
        _roughen(obj, hand, str(obj_key))
    ch = hand.channels(str(obj_key))
    # Opacity — ink density: scale the base (default full) and clamp back to 0..1.
    if hand.opacity:
        base = obj.get("opacity")
        base = 1.0 if base is None else float(base)
        obj["opacity"] = _round(_clamp(base * (1.0 + ch["opacity"]), 0.0, 1.0))
    # Rotation — pitch drift: a small tilt about the box centre, emitted as a CSS
    # transform (the field the renderer honours). Skip connectors and any object a
    # connector attaches to, so anchored geometry keeps meeting (topology-preserving).
    if hand.drift_deg and not is_connector and not is_endpoint:
        _apply_tilt(obj, ch["rotation"])
    # Weight — velocity: only an *inline* stroke_style carrying a numeric width; a
    # token-ref stroke style is shared and must not be mutated in place.
    if hand.weight:
        _perturb_weight(obj, ch["weight"])


def _tilt_center(obj: dict[str, Any]) -> list[float] | None:
    """The object's geometric centre in page space — the pitch-drift pivot.

    The renderer derives a rotation's origin from an object's ``box``. Centre-,
    endpoint- and point-based geometry (ellipse/circle, line, polyline/polygon)
    carries no ``box``, so without an explicit origin the tilt would pivot about
    the SVG origin (0, 0) and *orbit* the object across the page instead of
    tilting it in place. Derive the centre from whatever geometry the object holds
    (post-roughen, so a converted shape is measured by its points).
    """
    box = obj.get("box")
    if isinstance(box, (list, tuple)) and len(box) == 4 \
            and all(isinstance(v, (int, float)) for v in box):
        return [box[0] + box[2] / 2.0, box[1] + box[3] / 2.0]
    if _is_xy(obj.get("center")):
        c = obj["center"]
        return [float(c[0]), float(c[1])]
    a, b = obj.get("from"), obj.get("to")
    if _is_xy(a) and _is_xy(b):
        return [(a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0]
    pts = obj.get("points")
    if isinstance(pts, list) and pts:
        xs = [p[0] for p in pts if _is_xy(p)]
        ys = [p[1] for p in pts if _is_xy(p)]
        if xs and ys:
            return [(min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0]
    return None


def _apply_tilt(obj: dict[str, Any], degrees: float) -> None:
    """Compose a small ``rotate(...)`` about the object's centre onto its CSS transform.

    The pitch-drift "tilt". The pivot is the object's geometric centre, supplied
    explicitly as ``transform_origin`` so centre/point geometry tilts in place
    rather than orbiting the SVG origin. An object whose ``style`` is a shared
    token reference, or already carries a structured transform op-list, is left
    unperturbed rather than clobbered.
    """
    if not degrees:
        return
    rot = f"rotate({_round(degrees)}deg)"
    style = obj.get("style")
    if style is None:
        style = {}
    elif not isinstance(style, dict):
        return  # token-ref style: shared, do not clobber
    existing = style.get("transform")
    if isinstance(existing, list):
        return  # structured transform op-list: leave as authored
    style = dict(style)
    if isinstance(existing, str) and existing.strip() and existing.strip() != "none":
        style["transform"] = f"{existing} {rot}"
    else:
        style["transform"] = rot
    center = _tilt_center(obj)
    if center is not None and style.get("transform_origin") is None:
        style["transform_origin"] = center
    obj["style"] = style


# --------------------------------------------------------------------------- #
#  roughen — geometry-level coherent wobble (ported from build_a6.py, but      #
#  driven by our per-object keyed RNG so it is reorder-stable + round-robin)   #
# --------------------------------------------------------------------------- #
_TWO_PI = 2.0 * math.pi
# Per-primitive amplitude ratios (mirror build_a6's A_LINE:A_CIRC:A_PATH ≈ 1:1.5:1.3).
_AMP_LINE, _AMP_CLOSED, _AMP_POLY = 1.0, 1.5, 1.3
_ROUND2 = 2  # geometry precision: stable golden hashes, sub-pixel wobble


def _r2(x: float) -> float:
    return round(float(x), _ROUND2)


def _is_xy(v: Any) -> bool:
    return isinstance(v, (list, tuple)) and len(v) == 2 \
        and all(isinstance(c, (int, float)) for c in v)


def _noise(rng: Random, n: int, amp: float, closed: bool = False) -> list[float]:
    """A coherent 1-D wobble: two sinusoids of random frequency + phase.

    Band-limited (not white noise), so the displacement varies smoothly along the
    stroke the way a hand's does. ``closed`` picks integer harmonics so the series
    is periodic and a closed outline meets itself seamlessly.
    """
    if closed:
        k1, k2 = rng.choice([2, 3]), rng.choice([5, 6, 7])
    else:
        k1, k2 = rng.uniform(0.8, 1.6), rng.uniform(2.5, 4.5)
    p1, p2 = rng.uniform(0, _TWO_PI), rng.uniform(0, _TWO_PI)
    return [amp * math.sin(_TWO_PI * k1 * i / n + p1)
            + amp * 0.45 * math.sin(_TWO_PI * k2 * i / n + p2)
            for i in range(n + 1)]


def _edge(rng: Random, p, q, amp: float) -> list[tuple[float, float]]:
    """Sample the segment p→q, displaced perpendicular by coherent noise that
    tapers to zero at both endpoints (``sin(pi t)**0.8``) — so the endpoints stay
    pinned (topology-preserving) while the middle wanders. Amplitude scales with
    length, so short edges wobble less."""
    length = math.hypot(q[0] - p[0], q[1] - p[1]) or 1.0
    n = max(6, int(length / 18))
    nx, ny = -(q[1] - p[1]) / length, (q[0] - p[0]) / length
    ns = _noise(rng, n, amp * min(1.0, length / 60.0))
    out = []
    for i in range(n + 1):
        t = i / n
        taper = max(0.0, math.sin(math.pi * t)) ** 0.8
        out.append((p[0] + (q[0] - p[0]) * t + nx * ns[i] * taper,
                    p[1] + (q[1] - p[1]) * t + ny * ns[i] * taper))
    return out


def _set_polyline(obj: dict[str, Any], drop: tuple[str, ...],
                  pts: list, closed: bool) -> None:
    for key in drop:
        obj.pop(key, None)
    obj["type"] = "polyline"
    obj["points"] = [[_r2(x), _r2(y)] for x, y in pts]
    if closed:
        obj["closed"] = True
    else:
        obj.pop("closed", None)


def _roughen(obj: dict[str, Any], hand: "Hand", key: str) -> None:
    """Convert a straight primitive into its hand-drawn wobbly equivalent.

    Straight edges become endpoint-anchored polylines; closed shapes become
    organic closed polylines. Text/image/group/path and anchored/token-ref
    geometry are left untouched. The RNG is keyed on the object (not draw order),
    so identical shapes wobble differently (round-robin) and reordering objects
    does not reshuffle the whole page.
    """
    kind = obj.get("type")
    rng = Random(_stable_seed(hand.seed, key, "roughen"))
    base = hand.roughen
    if kind == "line":
        a, b = obj.get("from"), obj.get("to")
        if _is_xy(a) and _is_xy(b):
            _set_polyline(obj, ("from", "to"), _edge(rng, a, b, base * _AMP_LINE), False)
    elif kind == "rect":
        box = obj.get("box")
        if isinstance(box, (list, tuple)) and len(box) == 4 and not obj.get("radius"):
            _roughen_rect(obj, rng, box, base * _AMP_CLOSED)
    elif kind == "ellipse":
        _roughen_ellipse(obj, rng, ("center", "rx", "ry"), base * _AMP_CLOSED)
    elif kind == "circle":
        _roughen_ellipse(obj, rng, ("center", "r"), base * _AMP_CLOSED)
    elif kind in ("polyline", "polygon"):
        _roughen_points(obj, rng, base * _AMP_POLY)


def _roughen_rect(obj, rng, box, amp: float) -> None:
    x, y, w, h = (float(v) for v in box)
    jitter = amp * 0.6
    corners = [(x + rng.uniform(-jitter, jitter), y + rng.uniform(-jitter, jitter)),
               (x + w + rng.uniform(-jitter, jitter), y + rng.uniform(-jitter, jitter)),
               (x + w + rng.uniform(-jitter, jitter), y + h + rng.uniform(-jitter, jitter)),
               (x + rng.uniform(-jitter, jitter), y + h + rng.uniform(-jitter, jitter))]
    pts: list = []
    for i in range(4):
        pts.extend(_edge(rng, corners[i], corners[(i + 1) % 4], amp)[:-1])
    _set_polyline(obj, ("box", "radius"), pts, closed=True)


def _roughen_ellipse(obj, rng, keys: tuple[str, ...], amp: float) -> None:
    center = obj.get("center")
    if not _is_xy(center):
        return
    if keys[-1] == "r":
        rx = ry = float(obj.get("r", 0.0))
    else:
        rx, ry = float(obj.get("rx", 0.0)), float(obj.get("ry", 0.0))
    if rx <= 0 or ry <= 0:
        return
    n = 44
    a = min(amp, min(rx, ry) * 0.22)
    ns = _noise(rng, n, a, closed=True)
    ns[-1] = ns[0]
    cx = center[0] + rng.uniform(-a, a) * 0.4
    cy = center[1] + rng.uniform(-a, a) * 0.4
    mr = max(rx, ry)
    pts = [(cx + rx * (1 + ns[i] / mr) * math.cos(_TWO_PI * i / n),
            cy + ry * (1 + ns[i] / mr) * math.sin(_TWO_PI * i / n)) for i in range(n + 1)]
    _set_polyline(obj, keys, pts, closed=True)


def _roughen_points(obj, rng, amp: float) -> None:
    raw = obj.get("points")
    if not isinstance(raw, list) or len(raw) < 3:
        return  # need an interior vertex to wander; a 2-point chain has none
    pts = [(float(p[0]), float(p[1])) for p in raw]
    m = len(pts)
    ns = _noise(rng, m - 1, amp)
    out = [pts[0]]
    for i in range(1, m - 1):
        dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        length = math.hypot(dx, dy) or 1.0
        taper = max(0.0, math.sin(math.pi * i / (m - 1))) ** 0.7
        out.append((pts[i][0] - dy / length * ns[i] * taper,
                    pts[i][1] + dx / length * ns[i] * taper))
    out.append(pts[-1])
    obj["points"] = [[_r2(x), _r2(y)] for x, y in out]


def _perturb_weight(obj: dict[str, Any], delta: float) -> None:
    ss = obj.get("stroke_style")
    if not isinstance(ss, dict):
        return
    width = ss.get("stroke_width")
    if not isinstance(width, (int, float)):
        return
    ss = dict(ss)
    ss["stroke_width"] = _round(max(0.0, float(width) * (1.0 + delta)))
    obj["stroke_style"] = ss


def _connector_endpoint_ids(page: dict[str, Any]) -> set[str]:
    """Ids of objects a connector attaches to (exempt from rotation)."""
    ids: set[str] = set()
    for layer in page.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        for obj in layer.get("objects") or []:
            _collect_connector_ids(obj, ids)
    return ids


def _collect_connector_ids(obj: Any, ids: set[str]) -> None:
    if not isinstance(obj, dict):
        return
    if obj.get("type") == "connector":
        for endpoint in (obj.get("from"), obj.get("to")):
            ref = _anchor_ref(endpoint)
            if ref:
                ids.add(ref)
    for child in obj.get("children") or []:
        _collect_connector_ids(child, ids)


def _anchor_ref(endpoint: Any) -> str | None:
    if isinstance(endpoint, dict):
        ref = endpoint.get("ref") or endpoint.get("object")
        return str(ref) if ref else None
    if isinstance(endpoint, str):
        return endpoint.split(".", 1)[0]
    return None


def _contains_key(node: Any, key: str) -> bool:
    if isinstance(node, dict):
        if key in node:
            return True
        return any(_contains_key(v, key) for v in node.values())
    if isinstance(node, list):
        return any(_contains_key(v, key) for v in node)
    return False


__all__ = ["Hand", "apply_humanize"]
