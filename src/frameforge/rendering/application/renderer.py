"""Application-layer rendering orchestrator (the `Renderer` use-case).

Turns a FrameForge document (a plain dict, already YAML/JSON-parsed) into the
per-page SVG output, by walking it in z-order and driving the domain resolvers
(colour/paint/stroke/effect/text-style/canvas), the layout engine, and the
`SvgPainter` adapter. Relocated out of the monolithic `tooling/render_fixtures.py`
(DDD step: populate the application layer); behaviour and byte output are
unchanged.

Decomposition in progress (codebase-standards.md §13): text fitting, CSS/SVG
value building, and math->SVG rendering are extracted to injected services
(`TextFitter`, `StyleValues`, `MathSvgRenderer`). The remaining concrete
infrastructure coupling is the directly-constructed `SvgPainter`, slated to
become backend-neutral. `tooling/render_fixtures.py` re-exports `Renderer` for
backward compatibility.
"""
from __future__ import annotations

import copy
import math
import os
import re
import sys

from frameforge.rendering.domain.geometry import (
    fnum, fnum_precise, is_point, num,
)
from frameforge.rendering.domain.services.canvas_resolver import CanvasResolver
from frameforge.rendering.domain.services.paint_resolver import ColorResolver
from frameforge.rendering.domain.services.effect_resolver import EffectResolver
from frameforge.rendering.domain.services.stroke_resolver import Markers, Stroke, StrokeResolver
from frameforge.rendering.domain.services.layout_engine import LayoutEngine
from frameforge.rendering.domain.services import flow_layout
from frameforge.rendering.domain.services.math_text import math_text
from frameforge.rendering.domain.services.style_values import StyleValues
from frameforge.rendering.domain.services.text_fitter import TextFitter
from frameforge.rendering.domain.services.text_style_resolver import TextStyleResolver
from frameforge.rendering.application.dimension_renderer import DimensionRenderer
from frameforge.rendering.application.render_context import RendererContext
from frameforge.rendering.application.table_renderer import TableRenderer
from frameforge.rendering.application.uml_renderer import UmlRenderer
from frameforge.rendering.infrastructure.math_svg import MathSvgRenderer
from frameforge.rendering.infrastructure.painters.svg import SvgPainter


# --------------------------------------------------------------------------- #
#  the renderer                                                               #
# --------------------------------------------------------------------------- #
class Renderer:

    def __init__(self, doc, base_dir, *, real_metrics=None, painter_factory=None,
                 layout_report=False):
        self.doc = doc if isinstance(doc, dict) else {}
        self.base_dir = base_dir
        # Opt-in: when True (and fontTools resolves the family) text width comes
        # from real glyph advances instead of the per-char `avg` estimate. OFF by
        # default so render_page()/golden output stays byte-identical (§8).
        # `None` (the default) consults FRAMEFORGE_REAL_METRICS so the flag is
        # reachable through every public entry point (sdk.render_page_svgs, the
        # MCP pipeline, the CLI) without a signature change; an explicit bool —
        # e.g. the golden harness passing False — always wins over the env.
        if real_metrics is None:
            real_metrics = os.environ.get("FRAMEFORGE_REAL_METRICS", "").strip().lower() in (
                "1", "true", "yes", "on")
        self.real_metrics = bool(real_metrics)
        # Text fitting (measure/wrap/ellipsize) is a domain service; inject the
        # infra font-metrics provider only when real_metrics is on (estimate mode
        # otherwise), keeping the domain free of the infra import.
        if self.real_metrics:
            from frameforge.rendering.infrastructure.font_metrics import get_font_metrics
            self._fit = TextFitter(get_font_metrics)
        else:
            self._fit = TextFitter(None)
        defs = self.doc.get("defs") or {}
        tok = defs.get("tokens") or {}
        self.colors = tok.get("colors") or {}
        self.fill_styles = tok.get("fill_styles") or {}
        self.text_styles = tok.get("text_styles") or {}
        self.styles = tok.get("styles") or {}
        self.stroke_styles = tok.get("stroke_styles") or {}
        self.assets = defs.get("assets") or {}
        self.masters = defs.get("masters") or {}
        self.doc_contract = self.doc.get("text_contract") or {}
        self.contract = {}       # effective per-page text contract (set in render_page)
        self.skipped = 0
        # text-fit telemetry (asserted by --check-overflow)
        self.tstats = dict(total=0, naive_overflow=0, shrunk=0, wrapped=0,
                           clipped=0, contained=0, visible_overflow=0, uncontained=0)
        # ---- structured render feedback (additive; never alters SVG bytes) -- #
        # `warnings`         — structured events (kind/message/details) from the
        #                      renderer AND the painter (conic fallback, unknown
        #                      mask refs, unsupported toc kinds, ...).
        # `skipped_objects`  — every object swallowed by the per-object safety
        #                      net, with type/id and the exception message.
        # `skipped_flowables`— per-type counts of flow blocks the SVG proxy
        #                      drops (no more silent passes).
        # `font_fallbacks`   — requested->resolved family substitutions, filled
        #                      by `font_report()` (fc-match; empty until called).
        # `layout`           — opt-in (`layout_report=True`): per-object final
        #                      boxes + fitted font sizes, keyed by object id.
        # `truncations`       — every text object that LOST content to the
        #                      containment net: id/page/box, lines kept+dropped,
        #                      the head of the dropped text, and whether the
        #                      clip was explicitly authored (`acknowledged`) or
        #                      the silent containment default (issue #44).
        self.layout_report = bool(layout_report)
        self.diagnostics = {"warnings": [], "skipped_objects": [],
                            "skipped_flowables": {}, "font_fallbacks": [],
                            "layout": [], "truncations": []}
        # headings placed by the LAST flow page render: {level, text, id, page}
        # (page is 1-based within that flow). Read by the PDF outline builder.
        self.flow_headings = []
        # clickable link regions from the LAST flow render (TOC entries → target
        # page): {page, rect [x,y,w,h] in svg px, target}. Read by the PDF linker.
        self.flow_links = []
        # running-string log from the LAST flow page render: (page, name, value)
        # tuples in page order, one per heading `set_string` entry — the dry
        # pass populates this so the real pass can resolve a running
        # header/footer Text whose `field` is {string: <name>} to whatever was
        # most recently set as of each page (PageMaster.running / StringSet /
        # Text.field — schema-declared but unread by the renderer until now).
        self.running_log = []
        self._families_seen = set()
        # ---- domain resolvers + SVG painter (DDD steps 3–4) ----------------- #
        # Token/style/canvas resolution are pure domain services. ALL SVG string
        # construction + the per-page <defs>/gradient-id state now lives in the
        # SvgPainter (a ScenePainter adapter); this Renderer is the *builder*
        # that walks the document in z-order and emits via the painter. The
        # stroke resolver is handed `self.paint` so a gradient stroke still
        # allocates its <defs> entry in document order (byte-identical ids).
        self._color = ColorResolver(self.colors)
        # The backend is injectable: `painter_factory(color_resolver) -> ScenePainter`
        # lets the same builder drive a non-SVG backend (e.g. TikzPainter). Defaults
        # to the SVG adapter so existing callers and golden output are unchanged.
        self._painter = (painter_factory(self._color) if painter_factory
                         else SvgPainter(self._color, warn=self.warn))
        self._text_style = TextStyleResolver(self.text_styles, self.styles, self._color)
        self._global_page = 0                 # document-global leaf page number (flow recto/verso)
        self._font_warned: set[str] = set()   # families already screamed about (warn-once)
        self._canvas = CanvasResolver(self.masters, warn=self.warn)
        self._stroke = StrokeResolver(self.stroke_styles, self._color, self.paint)
        self._effect = EffectResolver(self._color)
        self._css = StyleValues(self.color)   # CSS/SVG value builder (filter/shadow/transform)
        self._math = MathSvgRenderer(math_text)   # math -> SVG adapter (node MathJax + fallback)
        self._uml = UmlRenderer(RendererContext(self))   # out-of-core UML sub-renderer
        self._dim = DimensionRenderer(RendererContext(self))   # dimension-annotation sub-renderer
        self._table_r = TableRenderer(RendererContext(self))   # table sub-renderer
        self._layout = LayoutEngine()
        self._object_index = {}

    # ---- colour / paint ---------------------------------------------------- #
    def color(self, c, depth=0):
        return self._color.resolve(c, depth)

    def paint(self, p, depth=0):
        """Return an SVG fill/stroke value: a colour, 'none', or url(#grad/#pat).

        Gradient/pattern *emission* (the <defs> entry + id) lives on the painter;
        this routes a gradient or pattern paint to it and a colour to the
        resolver. Backends without a `pattern()` port (e.g. the TikZ adapter)
        keep the legacy background-colour flattening via ColorResolver."""
        if isinstance(p, str) and depth <= 8 and p in self.fill_styles:
            # tokens.fill_styles key (model-declared; previously never read —
            # a named gradient/pattern fill silently emitted an invalid paint)
            return self.paint(self.fill_styles[p], depth + 1)
        if isinstance(p, dict) and p.get("stops") and p.get("kind") in ("linear", "radial", "conic"):
            return self._painter.gradient(p)
        if isinstance(p, dict) and p.get("kind") == "pattern":
            emit = getattr(self._painter, "pattern", None)
            if emit is not None:
                return emit(p)
            self.warn("pattern_unsupported_backend",
                      "pattern paint flattened to its background colour "
                      "(backend has no pattern port)")
        return self.color(p, depth)

    # ---- structured render feedback ----------------------------------------- #
    def warn(self, kind, message, **details):
        """Record a structured render warning (never raises, never mutates SVG)."""
        event = {"kind": kind, "message": message}
        if details:
            event.update(details)
        self.diagnostics["warnings"].append(event)

    def _note_flow_skip(self, flow_type):
        key = str(flow_type or "unknown")
        counts = self.diagnostics["skipped_flowables"]
        counts[key] = counts.get(key, 0) + 1

    def font_report(self):
        """Resolve every concrete font family seen during render via fc-match and
        return `[{requested, resolved, substituted}]` (empty when fc-match is
        unavailable). Substituted families — the raster will draw a different
        face than the author asked for — are also copied into
        `diagnostics["font_fallbacks"]` so agents see the requested->resolved
        pairs without pixel-diffing. Generic-only chains (sans-serif/serif/
        monospace/...) resolve to a system default by design and are skipped."""
        from frameforge.rendering.infrastructure.font_metrics import (
            first_concrete_family, resolve_family_name,
        )
        report = []
        for chain in sorted(f for f in self._families_seen if f):
            requested = first_concrete_family(chain)
            if requested is None:
                continue
            resolved = resolve_family_name(chain)
            if resolved is None:
                continue
            offered = [p.strip().lower() for p in str(resolved).split(",")]
            report.append({"requested": requested, "resolved": resolved,
                           "substituted": requested.lower() not in offered})
        self.diagnostics["font_fallbacks"] = [e for e in report if e["substituted"]]
        return report

    # ---- stroke (HEAD P3: paint in `stroke`, geometry in `stroke_style`) --- #
    def stroke(self, o):
        return self._stroke.fields(o)

    def _arrow_markers(self, o):
        """Resolve an open shape's arrowheads to a neutral `Markers` (or None).

        Reads `arrow_start`/`arrow_end` off the resolved `stroke_style`; the backend
        draws/registers its own arrowheads from the returned value object. Additive:
        returns None unless the stroke requests an arrow."""
        spec = self._stroke.arrow_spec(o)
        if not spec:
            return None
        return Markers(color=spec["color"], start=spec["start"], end=spec["end"])

    # ---- text style resolution -------------------------------------------- #
    def text_style(self, ref):
        return self._text_style.resolve(ref)

    # ---- text measurement / fitting --------------------------------------- #
    # Default path: a per-character `avg` estimate (no font metrics). When the
    # `real_metrics` opt-in is set AND fontTools resolves the family, width is
    # taken from real glyph advances instead. The opt-in is OFF by default, so
    # the estimate path below is reached unchanged and output is byte-identical.
    # Text fitting is delegated to the TextFitter domain service (SRP). These
    # thin wrappers preserve the call sites and the tested `Renderer.measure`/
    # `wrap_words` surface (tests/test_font_metrics.py).
    def measure(self, s, size, avg, st=None):
        if self.real_metrics and st:
            self._check_font_substitution(st)
        return self._fit.measure(s, size, avg, st)

    def _check_font_substitution(self, st):
        """SCREAM when the layout font ≠ the font the rasterizer will draw.

        With real metrics on, advances come from `font_metrics` (fontTools via
        fc-match) while the rasterizer (Chromium/cairo) resolves the family
        independently. If the requested concrete family is not actually installed,
        the two disagree and justified/wrapped text is wrong — the measure-time ≠
        render-time hazard. This is not a soft caveat: warn loudly, once per family.
        (The real fix is single-engine layout; see ADR-0004.)"""
        family = str(st.get("family") or "")
        if not family or family in self._font_warned:
            return
        self._font_warned.add(family)
        from frameforge.rendering.infrastructure.font_metrics import resolve_report
        resolved, matched, requested = resolve_report(family, bool(st.get("bold")))
        if requested and not matched:
            msg = (f"FONT SUBSTITUTION: requested '{requested}' is not installed — "
                   f"layout measured '{resolved or 'average-glyph estimate'}', but the "
                   f"rasterizer resolves the family itself, so justified/wrapped text "
                   f"WILL diverge. Render in the frameforge Docker image (baked fonts) "
                   f"or embed the face; do not trust host fonts.")
            self.warn("font_substitution", msg, requested=requested, resolved=resolved)
            print("⚠  " + msg, file=sys.stderr)

    def wrap_words(self, text, w, size, avg, st=None):
        return self._fit.wrap_words(text, w, size, avg, st)

    def ellipsize(self, s, w, size, avg, st=None):
        return self._fit.ellipsize(s, w, size, avg, st)

    # anchor() / text_tag() / clip_rect() emission moved to the SvgPainter
    # (step 4); the builder calls self._painter.* for them.

    def _span_runs(self, spans, base_st):
        """Resolve `text.spans` to (text, run_style_dict) pairs for one styled line.

        Mirrors the flatten used for fit (str | dict's `text`), so the run texts
        concatenate to the fitted line; each run's style is the neutral style dict
        from the span's own `style` (else the base) — the backend formats it at the
        fitted size."""
        runs = []
        for sp in spans:
            if isinstance(sp, dict):
                if sp.get("kind") == "math" and (sp.get("tex") is not None or sp.get("latex") is not None):
                    text = math_text(sp.get("tex") if sp.get("tex") is not None else sp.get("latex"))
                elif sp.get("kind") == "link":
                    # LinkInline: flatten the inline content to the run text and
                    # carry the href on the style dict under the reserved
                    # `link_href` key — the SVG backend wraps the run in <a>;
                    # backends that don't know the key ignore it (additive).
                    text = self._flatten_span_text(sp)
                    sty = {**(self.text_style(sp["style"]) if sp.get("style") else base_st),
                           "link_href": sp.get("href")}
                    runs.append((self._transform_text(str(text), base_st.get("text_transform")), sty))
                    continue
                else:
                    text = sp.get("text", "")
                sty = self.text_style(sp["style"]) if sp.get("style") else base_st
            else:
                text, sty = (sp if isinstance(sp, str) else str(sp)), base_st
            text = self._transform_text(str(text), base_st.get("text_transform"))
            runs.append((text, sty))
        return runs

    @classmethod
    def _flatten_span_text(cls, sp):
        """The plain text of one `text.spans` entry (str, Span dict, or an inline
        like LinkInline whose `content` nests further inlines)."""
        if isinstance(sp, str):
            return sp
        if not isinstance(sp, dict):
            return str(sp)
        if sp.get("text") is not None:
            return str(sp.get("text"))
        content = sp.get("content")
        if isinstance(content, list):
            return "".join(cls._flatten_span_text(item) for item in content)
        return ""

    def render_text(self, x, y, w, h, content, st, spans=None, oid=None):
        """Render a text object honouring the FrameForge text-fit contract:
        wrap-to-box (default), `shrink_to_fit` (down to min_font_size), `clip`/
        `hidden`, `text_overflow: ellipsis`, `line_clamp`/`max_lines`, plus a
        hard clip-path safety net so contained text can never spill its box."""
        self.tstats["total"] += 1
        self._families_seen.add(str(st.get("family") or ""))
        if content is None or content == "":
            return ""
        content = self._transform_text(str(content), st.get("text_transform"))
        size, avg, lh = st["size"], st["avg"], st["lh"]
        # Default unspecified text to `clip`: no fixture ever requests `visible`,
        # and an authoring box is a containment constraint, so the proxy contains
        # by default (wrap first, then clip the remainder) rather than spilling.
        overflow = st["overflow"] or self.contract.get("overflow") or "clip"
        min_fs = st["min_font_size"] or num(self.contract.get("min_font_size")) or size * 0.5
        text_ovf = st["text_overflow"] or self.contract.get("text_overflow")
        max_lines = st["max_lines"] or self.contract.get("line_clamp")
        do_wrap = w > 0 and not st["nowrap"]
        contained_policy = overflow in ("clip", "hidden", "scroll", "auto", "shrink_to_fit")

        # would the naive (single-line, no fit) render have spilled? (the reported bug)
        if self.measure(content, size, avg, st) > w + 0.5 or size * lh > h + 0.5:
            self.tstats["naive_overflow"] += 1

        # `align: justify` routes wrapping through the backend-neutral flow engine
        # (Knuth–Plass + hyphenation, ADR-0003) so page-mode prose justifies like
        # flow-mode prose — the old path silently mapped justify → left.
        justify = do_wrap and st["align"] == "justify"

        def layout(sz):
            if not do_wrap:
                return [content]
            if justify:
                para = flow_layout.layout_paragraph(
                    content, size=sz, avg=avg, lh=lh, width=w,
                    measure=lambda s, z, a: self.measure(s, z, a, st), align="justify")
                return [ln.text for ln in para.lines] or [content]
            return self.wrap_words(content, w, sz, avg, st)

        lines = layout(size)
        if len(lines) > 1:
            self.tstats["wrapped"] += 1
        if overflow == "shrink_to_fit":
            start = size
            while size > min_fs:
                lines = layout(size)
                too_tall = len(lines) * size * lh > h + 0.5
                if justify:
                    # justified lines render to exactly `w` via textLength, so only
                    # the last (ragged) line can actually overflow the column width.
                    too_wide = bool(lines) and self.measure(lines[-1], size, avg, st) > w + 0.5
                else:
                    too_wide = max((self.measure(ln, size, avg, st) for ln in lines), default=0) > w + 0.5
                if not too_tall and not too_wide:
                    break
                size = max(min_fs, size - 1)
            lines = layout(size)
            if size < start:
                self.tstats["shrunk"] += 1

        clipped = False
        dropped_lines: list[str] = []
        # clamp number of lines to box height (non-visible policies) and/or max_lines
        caps = [n for n in (max_lines, (int(h // (size * lh)) if (h > 0 and contained_policy) else None)) if n]
        cap = min(caps) if caps else None
        if cap is not None and len(lines) > max(1, cap):
            dropped_lines = lines[max(1, cap):]
            lines = lines[: max(1, cap)]
            clipped = True
            if text_ovf == "ellipsis":
                lines[-1] = self.ellipsize(lines[-1], w, size, avg, st)
        # single unwrapped line wider than the box
        if not do_wrap and self.measure(lines[0], size, avg, st) > w + 0.5:
            if text_ovf == "ellipsis":
                lines[0] = self.ellipsize(lines[0], w, size, avg, st)
            clipped = True

        # vertical placement
        total_h = len(lines) * size * lh
        va = st["valign"]
        if va in ("top", "text-top", "super"):
            top, centered = y, False
        elif va in ("bottom", "text-bottom", "sub"):
            top, centered = y + max(0, h - total_h), False
        elif va in ("middle", "central", "center", "baseline"):
            top, centered = y + max(0, (h - total_h) / 2), True
        else:
            # No explicit vertical-align: a lone line centres in its box; multi-line
            # prose top-anchors. (Was: a single line in a box taller than 2.4x the
            # font top-anchored — which threw a badge number to the top of the shape.)
            centered = len(lines) == 1
            top = y + max(0, (h - total_h) / 2) if centered else y
        base = top + size * 0.82
        # Optical vertical centring: hand a single centred line to the SVG's own
        # baseline metrics instead of a fixed 0.82 line-box ratio. We emit the box
        # centre as y and `dominant-baseline: central`, so the renderer seats the
        # line on the font's real asc/desc midpoint at draw time — symmetric with
        # how `text-anchor: middle` centres horizontally without a hardcoded width.
        # The y is deterministic geometry (golden-stable); no per-font metric leaks
        # into the SVG string.
        dom_baseline = None
        if centered and len(lines) == 1 and h > 0:
            base, dom_baseline = y + h / 2, "central"

        a = self._painter.anchor(st["align"])
        tx = x + (w / 2 if a == "middle" else (w if a == "end" else 0))
        single_span_line = spans and len(lines) == 1 and lines[0] == content
        # Pass the neutral style dict + fitted size; the backend formats the font.
        # Rich `text.spans`: when the fitted text is a single, untruncated line,
        # emit per-run styled tspans (the common inline-emphasis case). Wrapped or
        # truncated span text falls back to the flattened single-style line.
        if justify and spans and not single_span_line and not clipped:
            # Span-aware justification: re-lay the flattened run text, slice the
            # styled runs onto each line by char offset, and flush each line to the
            # column with textLength — inline emphasis survives justification.
            runs = self._span_runs(spans, st)
            flat = "".join(t for t, _ in runs)
            para = flow_layout.layout_paragraph(
                flat, size=size, avg=avg, lh=lh, width=w,
                measure=lambda s, z, a: self.measure(s, z, a, st), align="justify")
            segs = []
            for i, ln in enumerate(para.lines):
                lruns = flow_layout.slice_runs(runs, ln.start, ln.end) or [(ln.text, st)]
                if ln.text.endswith("-"):            # carry the soft hyphen on the last run
                    lruns = [*lruns[:-1], (lruns[-1][0] + "-", lruns[-1][1])]
                segs.append(self._painter.text_runs(
                    base + i * (size * lh), "start", x, st, size, lruns,
                    text_len=(w if ln.justify else None)))
            el = "".join(segs)
        elif justify and not single_span_line:
            # Plain justified prose: flush each line via textLength EXCEPT lone or
            # underfull lines (no interior gap, or < half the column) — those stay
            # ragged, never stretched into cavernous letterspacing. Last line ragged.
            justs = [(k < len(lines) - 1 and (" " in ln.strip())
                      and self.measure(ln, size, avg, st) >= 0.5 * w)
                     for k, ln in enumerate(lines)]
            el = self._painter.text_block(base, "start", st, size, lines, x, size * lh,
                                          justify_width=w, justifies=justs)
        elif single_span_line:
            el = self._painter.text_runs(base, a, tx, st, size, self._span_runs(spans, st),
                                         baseline=dom_baseline)
        else:
            el = self._painter.text_block(base, a, st, size, lines, tx, size * lh,
                                          baseline=dom_baseline)

        # telemetry: is it visually contained?
        widest = max((self.measure(ln, size, avg, st) for ln in lines), default=0)
        fits = widest <= w + 0.5 and len(lines) * size * lh <= h + 0.5
        if contained_policy:
            if clipped or not fits:                  # clip only when something exceeds the box
                self.tstats["clipped"] += 1
                el = self._painter.clip_wrap(el, self._painter.clip_rect(x, y, w, h))
                # Name the loss (issue #44): an aggregate count is not a
                # diagnostic. Records cover MATERIAL loss only — dropped lines,
                # a glyph run cut beyond rounding tolerance, or more than half a
                # line clipped vertically. A sub-pixel descender trim keeps the
                # clip-path (and the aggregate count) but is not content loss.
                # `acknowledged` = the author explicitly chose a containment
                # behaviour; the bare default is a silent clip.
                kind = "lines" if dropped_lines else None
                if kind is None and widest > w + 2:
                    kind = "width"
                elif kind is None and len(lines) * size * lh > h + max(2.0, size * lh * 0.5):
                    kind = "height"
                if kind is not None:
                    acknowledged = bool(st["overflow"] or self.contract.get("overflow")
                                        or text_ovf or max_lines)
                    head = " ".join(dropped_lines)[:80]
                    self.diagnostics["truncations"].append({
                        "id": oid, "page": getattr(self, "_current_page_id", None),
                        "kind": kind, "box": [x, y, w, h],
                        "lines_kept": len(lines), "lines_dropped": len(dropped_lines),
                        "dropped_text": head, "acknowledged": acknowledged,
                    })
            else:
                self.tstats["contained"] += 1
        elif fits:
            self.tstats["contained"] += 1
        else:
            # explicit overflow:visible long text — permitted to spill, but flagged
            self.tstats["visible_overflow"] += 1
            self.tstats["uncontained"] += 1
        if self.layout_report:
            self.diagnostics["layout"].append({
                "id": oid, "type": "text", "box": [x, y, w, h],
                "font_size": size, "lines": len(lines), "clipped": clipped,
            })
        return el

    @staticmethod
    def _transform_text(content, transform):
        if transform == "uppercase":
            return content.upper()
        if transform == "lowercase":
            return content.lower()
        if transform == "capitalize":
            return content.title()
        return content

    def obj(self, o):
        if not isinstance(o, dict):
            return ""
        try:
            passes = o.get("appearance")
            if isinstance(passes, (list, tuple)) and passes:
                inner = self._appearance_stack(o, passes)
            else:
                inner = self._obj(o)
            if inner:
                inner = self._with_side_borders(o, self._style_dict(o.get("style")), inner)
                inner = self._with_outline(o, self._style_dict(o.get("style")), inner)
                inner = self._with_style_clip(o, self._style_dict(o.get("style")), inner)
                inner = self._with_effects(o, self._style_dict(o.get("style")), inner)
                inner = self._with_transform(o, self._style_dict(o.get("style")), inner)
                inner = self._with_rotation(o, inner)
                inner = self._with_style_compositing(o, self._style_dict(o.get("style")), inner)
            opacity = o.get("opacity")
            if inner and opacity not in (None, 1):
                inner = self._painter.opacity_group(inner, num(opacity, 1))
            if inner and self.layout_report and o.get("type") != "text":
                box = o.get("box")
                if isinstance(box, list) and len(box) >= 4:
                    # authored/local frame (pre-transform); text objects record
                    # their richer entry (fitted size, lines) in render_text.
                    self.diagnostics["layout"].append({
                        "id": o.get("id"), "type": o.get("type"),
                        "box": [num(v, 0) for v in box[:4]],
                    })
            svg = self._painter.a11y_wrap(inner, o)
            # dict-level `href` pass-through: any visual object carrying a link
            # target is wrapped in <a href> (outermost, so the whole semantic
            # group is the hit area). The model field is owned by the schema
            # layer; the renderer honours the normalized dict either way.
            href = o.get("href")
            if svg and isinstance(href, str) and href.strip():
                wrap = getattr(self._painter, "link_wrap", None)
                svg = wrap(svg, href.strip(), o.get("link_title")) if wrap else svg
            return svg
        except Exception as exc:                       # never let one object kill a page
            self.skipped += 1
            self.diagnostics["skipped_objects"].append({
                "type": o.get("type"), "id": o.get("id"),
                "error": f"{type(exc).__name__}: {exc}",
            })
            return ""

    def _with_side_borders(self, o, style, svg):
        box = o.get("box")
        if not isinstance(box, list) or len(box) < 4:
            return svg
        x, y, w, h = (num(v, 0) for v in box[:4])
        sides = (
            ("border_top", (x, y, x + w, y)),
            ("border_right", (x + w, y, x + w, y + h)),
            ("border_bottom", (x, y + h, x + w, y + h)),
            ("border_left", (x, y, x, y + h)),
        )
        lines = []
        for key, (x1, y1, x2, y2) in sides:
            border = style.get(key)
            if isinstance(border, dict):
                stroke = self._border_stroke(border)
                if stroke:
                    lines.append(self._painter.line(x1, y1, x2, y2, stroke))
        return svg + "".join(lines)

    def _with_outline(self, o, style, svg):
        outline = style.get("outline")
        box = o.get("box")
        if not isinstance(outline, dict) or not isinstance(box, list) or len(box) < 4:
            return svg
        stroke = self._border_stroke(outline)
        if not stroke:
            return svg
        x, y, w, h = (num(v, 0) for v in box[:4])
        offset = num(style.get("outline_offset"), 0) or 0
        radius = max(0, self._shape_radius(o, style) + offset)
        outline_rect = self._painter.rect(
            x - offset, y - offset, w + 2 * offset, h + 2 * offset, None, stroke, radius=radius
        )
        return svg + outline_rect

    def _appearance_stack(self, o, passes):
        """The appearance stack (2.4.0, W4/#48): paint the object's geometry
        once per pass, bottom→top in list order. Each pass paints ONLY what
        it declares (a stroke-only pass fills nothing); clones drop identity
        fields so ids/binds appear once, and effects/opacity stay on the
        outer chain, wrapping the whole stack."""
        parts = []
        for p in passes:
            if not isinstance(p, dict):
                continue
            clone = {k: v for k, v in o.items()
                     if k not in ("appearance", "id", "bind", "effects",
                                  "shadow", "glow", "opacity",
                                  "fill", "stroke", "stroke_style")}
            clone["fill"] = p.get("fill") if p.get("fill") is not None else "none"
            if p.get("stroke") is not None:
                clone["stroke"] = p["stroke"]
            if p.get("stroke_style") is not None:
                clone["stroke_style"] = p["stroke_style"]
            part = self._obj(clone)
            if part and p.get("opacity") not in (None, 1):
                part = self._painter.opacity_group(part, num(p["opacity"], 1))
            if part:
                parts.append(part)
        return "".join(parts)

    def _effect_kinds(self, o, style):
        """The effect kinds an object declares (object shadow/glow, the ordered
        `effects` stack, and style box-shadow/filter) — for the unsupported-
        backend warning."""
        kinds = [k for k in ("shadow", "glow")
                 if self._effect.resolve(o.get(k), k) is not None]
        for entry in (o.get("effects") or []):
            if isinstance(entry, dict) and entry.get("kind") in ("shadow", "glow"):
                kinds.append(entry["kind"])
        kinds.extend(kind for kind, _ in self._effect.style_effects(style))
        return kinds

    def _with_effects(self, o, style, svg):
        """Wrap an object's SVG in effect filter group(s) if it declares them.

        Additive: emits nothing unless `shadow`/`glow` is present, so effect-free
        fixtures are byte-identical. Object effects wrap before supported style
        effects so authored style filters apply to the fully drawn primitive.

        On a backend that cannot composite filters (e.g. TikZ, `supports_filters`
        False) a declared effect is DROPPED — so warn once per effect, naming the
        kind and object, rather than losing it silently (#44 / #53)."""
        if not getattr(self._painter, "supports_filters", True):
            kinds = self._effect_kinds(o, style)
            for kind in kinds:
                self.warn("unsupported_effect",
                          f"{kind} effect dropped: this backend cannot "
                          f"composite filters",
                          object_id=o.get("id"), effect=kind)
            return svg
        for kind in ("glow", "shadow"):
            params = self._effect.resolve(o.get(kind), kind)
            if params is not None:
                svg = self._painter.filter_wrap(svg, self._painter.filter_effect(kind, params))
        # the ORDERED effect stack (2.4.0, W4/#48): entries apply first→last
        # (each wrap nests the previous, so the last entry sits outermost);
        # kinds may repeat, presets seed the params and explicit keys override
        stack = o.get("effects")
        if isinstance(stack, (list, tuple)):
            for entry in stack:
                if not isinstance(entry, dict):
                    continue
                kind = entry.get("kind")
                if kind not in ("shadow", "glow"):
                    continue
                base = (self._effect.resolve(entry["preset"], kind) or {}
                        if entry.get("preset") else {})
                merged = {k: entry[k] if entry.get(k) is not None else base.get(k)
                          for k in ("color", "blur", "dx", "dy", "opacity")}
                merged = {k: v for k, v in merged.items() if v is not None}
                params = self._effect.resolve(merged or True, kind)
                if params is not None:
                    svg = self._painter.filter_wrap(
                        svg, self._painter.filter_effect(kind, params))
        for kind, params in self._effect.style_effects(style):
            svg = self._painter.filter_wrap(svg, self._painter.filter_effect(kind, params))
        return svg

    def _with_transform(self, o, style, svg):
        # `o` rides along so a box-less object (circle/line/points geometry)
        # still gets the §3.6b centre-default pivot (StyleValues.geometry_center).
        ops = self._css.transform_ops(style.get("transform"), style.get("transform_origin"),
                                      o.get("box"), o)
        return self._painter.transform_group(svg, ops) if ops else svg

    def _with_rotation(self, o, svg):
        """ObjBase.rotation (§3.6b): degrees clockwise (+y down), or an
        explicit `{angle, center}`. The pivot defaults to the box centre —
        the geometry centre for box-less objects. Composes onto the subtree
        AFTER `style.transform` (this wrapper nests outside the transform
        group), so the already-transformed object turns as one unit."""
        rot = o.get("rotation")
        if rot is None:
            return svg
        if isinstance(rot, dict):
            angle = num(rot.get("angle"), 0) or 0
            center = rot.get("center")
        else:
            angle = num(rot, 0) or 0
            center = None
        if not angle:
            return svg
        if isinstance(center, (list, tuple)) and len(center) >= 2:
            cx, cy = num(center[0], 0), num(center[1], 0)
        else:
            cx, cy = self._css.transform_origin(None, o.get("box"), o)
        # angle stays on fnum: δθ ≤ 5e-4° displaces ≤ ~0.04 px at the 4K
        # diagonal (see StyleValues._PRECISE_FNS rationale)
        ops = ([("rotate", [fnum(angle), fnum(cx), fnum(cy)])]
               if cx is not None else [("rotate", [fnum(angle)])])
        return self._painter.transform_group(svg, ops)

    def _with_style_compositing(self, o, style, svg):
        attrs = {}
        visibility = style.get("visibility")
        if visibility in ("hidden", "collapse"):
            attrs["visibility"] = visibility
        blend = style.get("mix_blend_mode")
        if blend and blend != "normal":
            attrs["mix-blend-mode"] = blend
        isolation = style.get("isolation")
        if isolation and isolation != "auto":
            attrs["isolation"] = isolation
        opacity = style.get("opacity")
        if opacity not in (None, 1):
            attrs["opacity"] = fnum(num(opacity, 1))
        clip = style.get("clip_path")
        if isinstance(clip, str) and clip.strip():
            attrs["clip-path"] = clip.strip()
        backdrop = self._css.filter_value(style.get("backdrop_filter"))
        if backdrop:
            attrs["backdrop-filter"] = backdrop
        css_filter = self._css.filter_value(style.get("filter"), svg_only=False)
        if css_filter:
            attrs["filter"] = css_filter
        bg_blend = style.get("background_blend_mode")
        if bg_blend and bg_blend != "normal":
            attrs["background-blend-mode"] = bg_blend
        for key, css_name in (
            ("background_position", "background-position"),
            ("background_repeat", "background-repeat"),
            ("background_clip", "background-clip"),
            ("background_origin", "background-origin"),
        ):
            val = style.get(key)
            if val:
                attrs[css_name] = str(val)
        mask = style.get("mask")
        if isinstance(mask, dict):
            mid = self._style_mask_id(mask, o.get("box"))
            if mid:
                attrs["mask"] = f"url(#{mid})"
        elif isinstance(mask, str) and mask.strip() and mask.strip() != "none":
            attrs["mask"] = mask.strip()
            ref = re.fullmatch(r"url\(#([^)]+)\)", mask.strip())
            if ref and not self._painter_has_def(ref.group(1)):
                self.warn("mask_unresolved_ref",
                          f"style.mask references '#{ref.group(1)}' but no def with "
                          "that id exists on this page — the mask is a no-op",
                          id=o.get("id"))
        z_index = style.get("z_index")
        if z_index is not None:
            attrs["z-index"] = str(z_index)
        transform_box = style.get("transform_box")
        if transform_box:
            attrs["transform-box"] = transform_box
        perspective = style.get("perspective")
        if perspective and perspective != "none":
            attrs["perspective"] = self._css.length(perspective)
        # The bounded `css` escape (§8.4) on a non-text object: text emits its css
        # inline via font_style(); shapes carry it on the compositing <g> wrapper.
        css = style.get("css")
        raw = css if (css and o.get("type") != "text") else ""
        return self._painter.style_group(svg, attrs, raw)

    def _painter_has_def(self, def_id):
        has = getattr(self._painter, "has_def_id", None)
        return bool(has(def_id)) if has else True    # backends without a registry: trust

    def _style_mask_id(self, mask, box):
        """Lower a Style.mask *value* (Gradient or UrlImage dict) into a generated
        `<mask>` def sized to the object's box; returns the mask id or None
        (with a structured warning) when it cannot be built."""
        emit = getattr(self._painter, "mask_def", None)
        if emit is None:
            self.warn("mask_unsupported_backend", "backend has no mask port; mask dropped")
            return None
        if not (isinstance(box, list) and len(box) >= 4):
            self.warn("mask_needs_box", "an Image/Gradient style.mask needs the "
                      "object's box to size the mask content; mask dropped")
            return None
        x, y, w, h = (num(v, 0) for v in box[:4])
        if mask.get("stops") and mask.get("kind") in ("linear", "radial", "conic"):
            fill = self.paint(mask)                  # allocates the gradient def first
            return emit(self._painter.rect(x, y, w, h, fill, None))
        href = self._background_image_href(mask)
        if href:
            return emit(self._painter.image(x, y, w, h, href, "xMidYMid slice"))
        self.warn("mask_unresolvable_value",
                  "style.mask dict is neither a gradient nor a resolvable image; mask dropped")
        return None

    def _with_style_clip(self, o, style, svg):
        """LOAD-BEARING composition order (TX-8): the clip wraps INSIDE the
        object's transform/rotation groups (`obj()` applies this before
        `_with_transform`), so a `style.clip_path` authored in absolute
        coordinates rides along with the object's transform 1:1 — CSS
        local-clip composition. Committed examples rely on it
        (static/examples/ski_rebuilt_composition.py: a page-space mask is
        built by nesting the clip on a static parent group instead). Do not
        swap this order; document, don't "fix"."""
        clip = style.get("clip_path")
        if not isinstance(clip, dict):
            return svg
        cid = self._style_clip_id(clip, o.get("box"))
        return self._painter.clip_wrap(svg, cid) if cid else svg

    def _style_clip_id(self, clip, box):
        shape = clip.get("shape")
        args = clip.get("args") or {}
        if shape == "inset" and isinstance(box, list) and len(box) >= 4:
            x, y, w, h = (num(v, 0) for v in box[:4])
            if isinstance(args.get("box"), list) and len(args["box"]) >= 4:
                x, y, w, h = (num(v, 0) for v in args["box"][:4])
            else:
                top = num(args.get("top"), 0) or 0
                right = num(args.get("right"), top) or 0
                bottom = num(args.get("bottom"), top) or 0
                left = num(args.get("left"), right) or 0
                x, y, w, h = x + left, y + top, max(0, w - left - right), max(0, h - top - bottom)
            return self._painter.clip_rect(x, y, w, h)
        if shape == "circle":
            center = args.get("center")
            radius = num(args.get("r", args.get("radius")), None)
            if center is None and isinstance(box, list) and len(box) >= 4:
                x, y, w, h = (num(v, 0) for v in box[:4])
                center = [x + w / 2, y + h / 2]
                radius = min(w, h) / 2 if radius is None else radius
            if is_point(center) and radius is not None:
                return self._painter.clip_ellipse(center[0], center[1], radius, radius)
        if shape == "ellipse":
            center = args.get("center")
            rx = num(args.get("rx"), None)
            ry = num(args.get("ry"), None)
            if center is None and isinstance(box, list) and len(box) >= 4:
                x, y, w, h = (num(v, 0) for v in box[:4])
                center = [x + w / 2, y + h / 2]
                rx = w / 2 if rx is None else rx
                ry = h / 2 if ry is None else ry
            if is_point(center) and rx is not None and ry is not None:
                return self._painter.clip_ellipse(center[0], center[1], rx, ry)
        if shape == "polygon":
            pts = [tuple(num(v, 0) for v in pt[:2]) for pt in args.get("points", []) if is_point(pt)]
            return self._painter.clip_polygon(pts) if pts else None
        if shape == "path":
            d = args.get("d")
            if isinstance(d, str) and d.strip():
                return self._painter.clip_path_d(d)
        return None

    def _group_children(self, o):
        """Render a group's children, arranging them when the group declares a
        row/column/grid `layout` (else children keep their authored boxes).

        Arrangement repositions each child via a translate group. Children with
        fill sizing get their direct box extent overridden for this render pass;
        the source document is not mutated. Children render in the group's local
        frame; the group's own box-origin translate is applied by the caller."""
        children = o.get("children") or []
        layout = o.get("layout") or {}
        box = o.get("box")
        if not (layout.get("kind") in ("row", "column", "grid", "wrap")
                and isinstance(box, list) and len(box) >= 4):
            # Free/authored-box children: same stable z_index paint order as a
            # layer's top level (z_index affects paint order, never placement).
            return "".join(self.obj(ch) for ch in self._paint_ordered(children))
        p = self._painter
        # Arranged children: slots come from DOCUMENT order (z_index must not
        # move a child to a different row/column cell) — only emission sorts.
        positions = self._layout.arrange(num(box[2], 0), num(box[3], 0), children, layout)
        parts = []
        for ch, (tx, ty, tw, th) in sorted(
                zip(children, positions), key=lambda cp: self._z_of(cp[0])):
            child = self._layout_child(ch, tw, th)
            csvg = self.obj(child)
            if not csvg:
                continue
            cb = ch.get("box") if isinstance(ch, dict) else None
            ox = num(cb[0], 0) or 0 if isinstance(cb, list) and len(cb) >= 2 else 0
            oy = num(cb[1], 0) or 0 if isinstance(cb, list) and len(cb) >= 2 else 0
            dx, dy = tx - ox, ty - oy
            parts.append(p.group(csvg, translate=(dx, dy)) if (dx or dy) else csvg)
        return "".join(parts)

    @staticmethod
    def _layout_child(ch, width, height):
        if not isinstance(ch, dict):
            return ch
        box = ch.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            return ch
        if (num(box[2], 0), num(box[3], 0)) == (width, height):
            return ch
        child = copy.deepcopy(ch)
        child["box"] = [box[0], box[1], width, height]
        return child

    def _obj(self, o):
        p = self._painter
        t = o.get("type")
        box = o.get("box")
        style = self._style_dict(o.get("style"))
        # Resolve fill up-front for every object (even box-less ones): a gradient
        # fill must allocate its <defs> id here, before stroke, to keep ids stable.
        fill = self._shape_fill(o, style)
        fill_opacity = o.get("fill_opacity", style.get("fill_opacity"))
        fill_rule = o.get("fill_rule", style.get("fill_rule"))

        if t == "rect" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            r = self._shape_radius(o, style)
            return p.rect(x, y, w, h, fill, self._shape_stroke(o, style), radius=r, fill_opacity=fill_opacity)

        if t == "ellipse":
            c = o.get("center") or [0, 0]
            cx, cy = num(c[0], 0), num(c[1], 0)
            rx, ry = num(o.get("rx"), 0), num(o.get("ry"), 0)
            if not rx and box:
                cx, cy, rx, ry = box[0] + box[2] / 2, box[1] + box[3] / 2, box[2] / 2, box[3] / 2
            return p.ellipse(cx, cy, rx, ry, fill, self._shape_stroke(o, style), fill_opacity=fill_opacity)

        if t == "circle":
            c = o.get("center") or [0, 0]
            r = num(o.get("r"), 0)
            return p.circle(num(c[0], 0), num(c[1], 0), r, fill, self._shape_stroke(o, style), fill_opacity=fill_opacity)

        if t == "line":
            fr, to = o.get("from"), o.get("to")
            if is_point(fr) and is_point(to):
                stk = self._shape_stroke(o, style) or Stroke(color="#000", width=1)
                return p.line(fr[0], fr[1], to[0], to[1], stk, markers=self._arrow_markers(o))
            return ""

        if t in ("polyline", "polygon"):
            pts = o.get("points") or []
            ptstr = " ".join(f"{fnum(num(pt[0],0))},{fnum(num(pt[1],0))}" for pt in pts if is_point(pt))
            if not ptstr:
                return ""
            closed = t == "polygon" or o.get("closed")
            tag = "polygon" if closed else "polyline"
            return p.poly(tag, ptstr, fill if closed else None,
                          self._shape_stroke(o, style),
                          fill_opacity=fill_opacity if closed else None,
                          fill_rule=fill_rule if closed else None,
                          markers=self._arrow_markers(o))

        if t == "path":
            d = o.get("d")
            if isinstance(d, (list, tuple)):
                # Lower structured segments `[[cmd, *coords], ...]` (G-1) to a path-data
                # string. A no-arg segment (Z) must emit just its command — no trailing
                # space — so the structured form lowers identically to the string form.
                # Segments arrive as lists from YAML/JSON but as TUPLES from a pydantic
                # model_dump (the SDK render path) — both are the structured form.
                parts = []
                for seg in d:
                    if isinstance(seg, (list, tuple)) and seg:
                        parts.append(" ".join([str(seg[0]),
                                               *(fnum(num(n, 0)) for n in seg[1:])]))
                    elif not isinstance(seg, (list, tuple)):
                        parts.append(str(seg))
                d = " ".join(parts)
            if not isinstance(d, str) or not d.strip():
                return ""
            return p.path(d, fill, self._shape_stroke(o, style),
                          fill_opacity=fill_opacity, fill_rule=fill_rule,
                          markers=self._arrow_markers(o))

        if t in ("curve", "bezier"):
            fr, to = o.get("from"), o.get("to")
            c1 = o.get("control1") or o.get("c1") or fr
            c2 = o.get("control2") or o.get("c2") or c1
            if not (is_point(fr) and is_point(to) and is_point(c1) and is_point(c2)):
                return ""
            d = (
                f"M {fnum(num(fr[0], 0))} {fnum(num(fr[1], 0))} "
                f"C {fnum(num(c1[0], 0))} {fnum(num(c1[1], 0))} "
                f"{fnum(num(c2[0], 0))} {fnum(num(c2[1], 0))} "
                f"{fnum(num(to[0], 0))} {fnum(num(to[1], 0))}"
            )
            return p.path(d, fill, self._shape_stroke(o, style),
                          fill_opacity=fill_opacity, fill_rule=fill_rule,
                          markers=self._arrow_markers(o))

        if t == "dimension":
            if o.get("kind") == "angular":
                return self._angular_dimension(o, style)
            return self._dim.draw(o, style)

        if t == "connector":
            return self._connector(o, style)

        if t == "text" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            content = o.get("text")
            spans = o.get("spans")
            if content is None and spans:
                content = "".join(self._flatten_span_text(s) for s in spans)
            return self.render_text(x, y, w, h, content, self.text_style(o.get("style")),
                                    spans=spans, oid=o.get("id"))

        if t == "bullet_list" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            st = self.text_style(o.get("style"))
            marker = o.get("marker", "•")
            gap = num(o.get("gap"), None) or st["size"] * 1.5
            mc = self.color(o.get("marker_color")) or st["color"]
            indent = st["size"] * 1.1
            line_h = st["size"] * st["lh"]
            # Wrap each item to the width remaining right of the marker so long
            # items don't run off the box; `nowrap` keeps the legacy single-line
            # behaviour. The text width must stay positive for narrow boxes.
            text_w = max(1.0, w - indent)
            do_wrap = text_w > 0 and not st.get("nowrap")
            out = []
            cy = y + st["size"]
            for it in o.get("items", []):
                txt = it if isinstance(it, str) else (it.get("text", "") if isinstance(it, dict) else str(it))
                lines = self.wrap_words(txt, text_w, st["size"], st["avg"], st) if do_wrap else [txt]
                out.append(p.text_tag(x, cy - st["size"], st["size"] + 4, st["size"] + 4,
                                      marker, {**st, "color": mc}, vcenter=False))
                for i, ln in enumerate(lines):
                    out.append(p.text_tag(x + indent, cy - st["size"] + i * line_h, w, st["size"] + 4,
                                          ln, st, vcenter=False))
                # Advance past every wrapped line, and never less than one line —
                # `gap` is the inter-item pitch (default a comfortable 1.5x), but a
                # too-small authored gap must not let items overlap, so floor the
                # single-line step at the line height.
                cy += max(gap, line_h) + (len(lines) - 1) * line_h
            return "".join(out)

        if t == "chip_row":
            return self._uml.chip_row(o)

        if t == "uml.marker_glyph":
            return self._uml.marker_glyph(o)

        if t == "component" and box:
            return self._component(o, style)

        if t == "container" and box:
            return self._group_children(o)

        if t == "legend" and box:
            return self._uml.legend(o)

        if t in ("uml.actor", "uml.socket", "uml.lollipop", "uml.activity_node", "uml.pseudostate") and box:
            return self._uml.glyph_box(o, style)

        if t == "uml.lifeline" and box:
            return self._uml.lifeline(o, style)

        if t == "uml.activation_bar" and box:
            return self._uml.activation_bar(o, style, fill)

        if t in {
            "uml.classifier_box",
            "uml.component_box",
            "uml.state_box",
            "uml.action",
            "uml.artifact_box",
            "uml.node_box",
        } and box:
            return self._uml.box(o, style, fill)

        if t == "icon" and box:
            x, y, w, h = (num(v, 0) for v in box[:4])
            col = self.color(o.get("color")) or "#444"
            sz = num(o.get("size"), None) or min(w, h) * 0.8
            st = {"family": "sans-serif", "size": sz, "weight": "normal",
                  "italic": False, "color": col, "align": "center", "lh": 1.2}
            return p.text_tag(x, y, w, h, o.get("glyph", "▢"), st, vcenter=True)

        if t == "image" and box:
            return self._image(o, box)

        if t == "table" and box:
            return self._table_r.draw(o, box)

        if t == "group":
            inner = self._group_children(o)
            bx = o.get("box")
            if is_point(bx[:2]) if isinstance(bx, list) and len(bx) >= 2 else False:
                # only translate when the group declares an origin box (P1 nesting)
                return p.group(inner, translate=(num(bx[0], 0), num(bx[1], 0)))
            return p.group(inner)

        # unknown / out-of-profile object → labelled placeholder iff it has a box
        if box and all(isinstance(v, (int, float)) for v in box[:4]):
            x, y, w, h = box[:4]
            st = {"family": "monospace", "size": 11, "weight": "normal",
                  "italic": True, "color": "#999", "align": "center", "lh": 1.2}
            return (p.rect(x, y, w, h, "#f3f3f3", Stroke(color="#ccc", dash="3 3"))
                    + p.text_tag(x, y, w, h, f"?{t}", st, vcenter=True))
        self.skipped += 1
        return ""

    def _index_objects(self, page):
        """id → object copy with `box` composed into PAGE space.

        Anchors must hit the RENDERED position, so the composition mirrors the
        paint path exactly: ancestor group box origins AND row/column/grid/wrap
        arrangement — `self._layout.arrange` is the single source of truth for
        slot placement, the same call `_group_children` paints with (TX-6).
        Each boxed entry also carries `_anchor_dxy`, the total authored→rendered
        shift, so port anchors (authored in the box's frame) ride along (TX-7).
        """
        index = {}

        def visit(o, offset=(0, 0), arranged=None):
            if not isinstance(o, dict):
                return
            local = dict(o)
            box = local.get("box")
            boxed = isinstance(box, list) and len(box) >= 4
            if boxed:
                if arranged is not None:
                    # arranged slot replaces the authored x/y; _layout_child
                    # overrides the extents for the paint pass identically
                    ax, ay, aw, ah = arranged
                    local["box"] = [offset[0] + ax, offset[1] + ay, aw, ah]
                else:
                    local["box"] = [num(box[0], 0) + offset[0], num(box[1], 0) + offset[1],
                                    num(box[2], 0), num(box[3], 0)]
                local["_anchor_dxy"] = (local["box"][0] - num(box[0], 0),
                                        local["box"][1] - num(box[1], 0))
            if local.get("id") and local.get("id") not in index:
                index[local["id"]] = local
            children = o.get("children") or []
            if not children:
                return
            child_offset = offset
            if o.get("type") == "group" and isinstance(box, list) and len(box) >= 2:
                # children live in the group-local frame anchored at the group's
                # RENDERED origin (the arranged slot when the group was laid out)
                if arranged is not None:
                    child_offset = (offset[0] + arranged[0], offset[1] + arranged[1])
                else:
                    child_offset = (offset[0] + num(box[0], 0), offset[1] + num(box[1], 0))
            layout = o.get("layout") or {}
            if layout.get("kind") in ("row", "column", "grid", "wrap") and boxed:
                w, h = (arranged[2], arranged[3]) if arranged is not None \
                    else (num(box[2], 0), num(box[3], 0))
                for child, pos in zip(children, self._layout.arrange(w, h, children, layout)):
                    visit(child, child_offset, arranged=pos)
            else:
                for child in children:
                    visit(child, child_offset)

        for layer in page.get("layers") or []:
            for obj in layer.get("objects") or []:
                visit(obj)
        return index

    def _anchor_ref(self, ref):
        if is_point(ref):
            return num(ref[0], 0), num(ref[1], 0)
        if not isinstance(ref, dict):
            return None
        if is_point(ref.get("point")):
            p = ref.get("point")
            return num(p[0], 0), num(p[1], 0)
        obj_id = ref.get("object") or ref.get("ref")
        obj = self._object_index.get(obj_id)
        box = obj.get("box") if isinstance(obj, dict) else None
        if not (isinstance(box, list) and len(box) >= 4):
            return None
        ports = obj.get("ports") or {}
        port = ref.get("port")
        if port in ports and is_point(ports[port]):
            # Ports are authored in the same frame as the object's box (the
            # committed connectors fixture pins page space at top level), so
            # they ride the object's full authored→rendered shift — ancestor
            # group origins + layout arrangement (TX-7).
            p = ports[port]
            dx, dy = obj.get("_anchor_dxy") or (0, 0)
            return num(p[0], 0) + dx, num(p[1], 0) + dy
        x, y, w, h = (num(v, 0) for v in box[:4])
        side = ref.get("side") or port
        offset = num(ref.get("offset"), 0) or 0
        if side == "north":
            return x + w / 2 + offset, y
        if side == "south":
            return x + w / 2 + offset, y + h
        if side == "east":
            return x + w, y + h / 2 + offset
        if side == "west":
            return x, y + h / 2 + offset
        return x + w / 2, y + h / 2

    def _connector(self, o, style):
        p = self._painter
        start = self._anchor_ref(o.get("from"))
        end = self._anchor_ref(o.get("to"))
        if start is None or end is None:
            self.skipped += 1
            return ""
        route = o.get("route") or {}
        points = route.get("points") if isinstance(route, dict) else None
        pts = [start] + [(num(pt[0], 0), num(pt[1], 0)) for pt in (points or []) if is_point(pt)] + [end]
        stroke = self._shape_stroke(o, style) or Stroke(color="#000", width=1)
        markers = self._arrow_markers(o)
        if len(pts) == 2:
            body = p.line(pts[0][0], pts[0][1], pts[1][0], pts[1][1], stroke, markers=markers)
        else:
            ptstr = " ".join(f"{fnum(x)},{fnum(y)}" for x, y in pts)
            body = p.poly("polyline", ptstr, None, stroke, markers=markers)
        label = o.get("label")
        if isinstance(label, dict) and isinstance(label.get("box"), list):
            bx = label["box"]
            st = self.text_style(label.get("style"))
            body += self.render_text(num(bx[0], 0), num(bx[1], 0), num(bx[2], 0), num(bx[3], 0),
                                     label.get("text", ""), st)
        return body

    def _angular_dimension(self, o, style):
        """Draw a `kind: angular` dimension — the arc between two anchor rays.

        The model gives two anchors (`from`/`to`) but an angle needs a vertex;
        the documented convention is: **`box[0], box[1]` is the vertex** and
        `from`/`to` are points on the two rays. The measure arc is drawn at the
        nearer ray-point's radius (override with `offset`), always along the
        minor arc, with arrowheads per `arrows` and an auto label in degrees
        (`value: auto`/omitted measures; `suffix` defaults to the degree sign).
        A missing vertex is a structured skip, not a silent drop."""
        p = self._painter
        fr = self._dim.point_anchor(o.get("from"))
        to = self._dim.point_anchor(o.get("to"))
        box = o.get("box")
        vertex = (num(box[0], 0), num(box[1], 0)) if (
            isinstance(box, list) and len(box) >= 2) else None
        if fr is None or to is None or vertex is None:
            self.warn("dimension_angular_vertex",
                      "angular dimension needs point `from`/`to` anchors and a "
                      "`box` whose origin is the vertex of the measured angle",
                      id=o.get("id"))
            self.skipped += 1
            return ""
        vx, vy = vertex
        a1 = math.atan2(fr[1] - vy, fr[0] - vx)
        a2 = math.atan2(to[1] - vy, to[0] - vx)
        d1 = math.hypot(fr[0] - vx, fr[1] - vy)
        d2 = math.hypot(to[0] - vx, to[1] - vy)
        if d1 <= 0 or d2 <= 0:
            self.warn("dimension_angular_vertex",
                      "angular dimension ray coincides with its vertex", id=o.get("id"))
            self.skipped += 1
            return ""
        sweep = (a2 - a1) % (2 * math.pi)
        if sweep > math.pi:                      # always dimension the minor arc
            a1, a2 = a2, a1
            sweep = 2 * math.pi - sweep
        degrees = math.degrees(sweep)
        # `offset` is a shift FROM the measured feature (the shorter ray's
        # reach), matching the model field doc — not an absolute radius; 0 and
        # negative (inside) offsets are honored.
        base = min(d1, d2)
        off = num(o.get("offset"), 0.0) if o.get("offset") is not None else 0.0
        r = max(base + off, 1.0)
        sx, sy = vx + r * math.cos(a1), vy + r * math.sin(a1)
        ex, ey = vx + r * math.cos(a2), vy + r * math.sin(a2)
        stroke = self._dim.stroke(o, style)
        arc = (f"M {fnum(sx)} {fnum(sy)} "
               f"A {fnum(r)} {fnum(r)} 0 0 1 {fnum(ex)} {fnum(ey)}")
        body = [
            p.line(vx, vy, fr[0], fr[1], stroke),         # the two rays
            p.line(vx, vy, to[0], to[1], stroke),
            p.path(arc, None, stroke, markers=self._dim.arrows(o)),
        ]
        if o.get("text") is not None:
            label = str(o.get("text"))
        else:
            value = o.get("value")
            measured = degrees if value in (None, "auto") else num(value, degrees)
            suffix = o.get("suffix")
            label = (f"{o.get('prefix') or ''}{fnum(round(measured, 1))}"
                     f"{suffix if suffix is not None else '°'}")
        st = self._dim.text(o)
        mid = a1 + sweep / 2
        lx, ly = vx + (r + 12) * math.cos(mid), vy + (r + 12) * math.sin(mid)
        body.append(p.text_tag(lx - 40, ly - st["size"] * 0.7, 80, st["size"] * 1.4,
                               label, st, vcenter=True))
        return p.group("".join(body))

    def _style_dict(self, ref, _seen=None):
        _seen = set() if _seen is None else set(_seen)
        if isinstance(ref, str):
            if ref in _seen:
                return {}
            _seen.add(ref)
            return self._style_dict(self.text_styles.get(ref) or self.styles.get(ref) or {}, _seen)
        if not isinstance(ref, dict):
            return {}
        cls = ref.get("class") or ref.get("class_")
        merged = {}
        for name in ([cls] if isinstance(cls, str) else (cls or [])):
            merged.update(self._style_dict(name, _seen))
        merged.update(ref)
        return merged

    def _shape_fill(self, o, style):
        if "fill" in o:
            return self.paint(o.get("fill"))
        if "fill" in style:
            return self.paint(style.get("fill"))
        if "background_image" in style:
            paint = self._background_paint(style.get("background_image"), o.get("box"), style)
            if paint is not None:
                return paint
        if "background" in style:
            paint = self._background_paint(style.get("background"), o.get("box"), style)
            if paint is not None:
                return paint
        if "background_color" in style:
            return self.paint(style.get("background_color"))
        return None

    def _background_paint(self, value, box=None, style=None):
        if isinstance(value, list):
            for item in value:
                paint = self._background_paint(item, box, style)
                if paint is not None:
                    return paint
            return None
        if isinstance(value, dict):
            image = value.get("image")
            if image is not None:
                paint = self._background_paint(image, box, {**(style or {}), **value})
                if paint is not None:
                    return paint
            if value.get("stops") and value.get("kind") in ("linear", "radial", "conic"):
                return self.paint(value)
            if "url" in value:
                return self._background_image_pattern(value.get("url"), box, style or {})
            if "color" in value:
                return self.paint(value.get("color"))
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith(("url(", "http://", "https://", "data:")):
                return self._background_image_pattern(stripped, box, style or {})
            if stripped in self.assets:
                return self._background_image_pattern(stripped, box, style or {})
            return self.paint(stripped)
        return None

    def _background_image_pattern(self, src, box, style):
        if not isinstance(box, list) or len(box) < 4:
            return None
        href = self._background_image_href(src)
        if not href:
            return None
        x, y, w, h = (num(v, 0) for v in box[:4])
        preserve = self._background_preserve_aspect_ratio(style.get("background_size"))
        return self._painter.image_pattern(href, x, y, w, h, preserve)

    def _background_image_href(self, src):
        if isinstance(src, dict):
            src = src.get("url") or src.get("src") or src.get("path")
        if not isinstance(src, str):
            return None
        s = src.strip()
        if s.startswith("url(") and s.endswith(")"):
            s = s[4:-1].strip().strip("'\"")
        if s.startswith(("data:", "http://", "https://", "file://")):
            return s
        return self._image_href(s)

    @staticmethod
    def _background_preserve_aspect_ratio(size):
        if size == "contain":
            return "xMidYMid meet"
        if size in (None, "auto", "cover"):
            return "xMidYMid slice"
        return "none"

    def _shape_radius(self, o, style):
        val = o.get("radius", o.get("rx", style.get("border_radius", style.get("radius"))))
        if isinstance(val, list):
            val = val[0] if val else 0
        return num(val, 0) or 0

    def _shape_stroke(self, o, style):
        """Resolve an object's stroke to a neutral `Stroke` (or None)."""
        if any(k in o for k in ("stroke", "stroke_style")):
            return self.stroke(o)
        border = style.get("border")
        if isinstance(border, (dict, str)):
            return self._border_stroke(border)
        if any(k in style for k in ("stroke", "stroke_width", "stroke_dasharray", "stroke_linecap", "stroke_linejoin")):
            return self.stroke({"stroke": style.get("stroke"), "stroke_style": style})
        return None

    def _component(self, o, style):
        box = o.get("box")
        if not (isinstance(box, list) and len(box) >= 4):
            self.skipped += 1
            return ""
        x, y, w, h = (num(v, 0) for v in box[:4])
        p = self._painter
        spec = self._component_spec(o)
        render_o = {**spec, **o}
        comp_style = self._style_dict(render_o.get("style"))
        comp_style.update(style or {})
        geometry = spec.get("geometry") if isinstance(spec.get("geometry"), dict) else {}
        radius = num(render_o.get("radius", geometry.get("radius")), 0) or 0
        fill = self._shape_fill(render_o, comp_style) or "#fff"
        stroke = self._shape_stroke(render_o, comp_style) or Stroke(color="#bbb", width=1)
        out = [p.rect(x, y, w, h, fill, stroke, radius=radius)]

        layout = spec.get("internal_layout") if isinstance(spec.get("internal_layout"), dict) else {}
        slots = (
            ("title", o.get("title"), {"box_offset": [0, 6, "100%", 18], "style": "heading"}),
            ("body", o.get("body"), {"box_offset": [8, 26, "calc(100% - 16)", "calc(100% - 30)"], "style": "body"}),
        )
        for slot, value, fallback in slots:
            if value is None or value == "":
                continue
            slot_layout = layout.get(slot) if isinstance(layout.get(slot), dict) else {}
            slot_layout = {**fallback, **slot_layout}
            sx, sy, sw, sh = self._component_slot_box(x, y, w, h, slot_layout.get("box_offset"))
            if sw <= 0 or sh <= 0:
                continue
            text_style = self.text_style(slot_layout.get("style"))
            out.append(self.render_text(sx, sy, sw, sh, value, text_style))
        return p.group("".join(out))

    def _component_spec(self, o):
        comps = (self.doc.get("defs") or {}).get("components") or {}
        spec = comps.get(o.get("component"))
        if not isinstance(spec, dict):
            return {}
        merged = {
            k: v for k, v in spec.items()
            if k not in ("variants", "slots")
        }
        variants = spec.get("variants") if isinstance(spec.get("variants"), dict) else {}
        variant = variants.get(o.get("variant"))
        if isinstance(variant, dict):
            merged.update(variant)
        return merged

    def _component_slot_box(self, x, y, w, h, offset):
        if not (isinstance(offset, list) and len(offset) >= 4):
            offset = [0, 0, w, h]
        ox = self._component_length(offset[0], w)
        oy = self._component_length(offset[1], h)
        ow = self._component_length(offset[2], w)
        oh = self._component_length(offset[3], h)
        return x + ox, y + oy, ow, oh

    def _component_length(self, value, total):
        if isinstance(value, (int, float)):
            return num(value, 0)
        if not isinstance(value, str):
            return num(value, 0)
        s = value.strip()
        if s.endswith("%"):
            return total * (num(s[:-1], 0) / 100)
        if s.startswith("calc(") and s.endswith(")"):
            inner = s[5:-1].strip()
            if inner.startswith("100%"):
                rest = inner[4:].strip()
                if rest.startswith("-"):
                    return total - num(rest[1:].strip(), 0)
                if rest.startswith("+"):
                    return total + num(rest[1:].strip(), 0)
                return total
        return num(s, 0)

    def _border_stroke(self, border):
        border = self._border_dict(border)
        if not border:
            return None
        if border.get("style") in ("none", "hidden"):
            return None
        col = self.color(border.get("color")) or "#000"
        width = num(border.get("width"), 1) or 1
        dash = None
        if border.get("style") in ("dashed", "dotted"):
            dash = "4 4" if border.get("style") == "dashed" else "1 3"
        return Stroke(color=col, width=width, dash=dash)

    @staticmethod
    def _border_dict(border):
        if isinstance(border, dict):
            return border
        if not isinstance(border, str):
            return {}
        styles = {"none", "hidden", "solid", "dashed", "dotted", "double", "groove", "ridge", "inset", "outset"}
        out = {}
        colors = []
        for part in border.split():
            if part in styles:
                out["style"] = part
            elif num(part, None) is not None:
                out["width"] = part
            else:
                colors.append(part)
        if colors:
            out["color"] = " ".join(colors)
        return out

    def _image(self, o, box):
        p = self._painter
        x, y, w, h = (num(v, 0) for v in box[:4])
        src = o.get("src", "")
        href = self._image_href(src)
        clip_id = self._image_clip_id(o.get("clip"), x, y, w, h)
        preserve = self._image_preserve_aspect_ratio(o.get("preserve_aspect_ratio"))

        if href:
            image = p.image(x, y, w, h, href, preserve)
            return p.clip_wrap(image, clip_id) if clip_id else image
        label = o.get("label") or os.path.basename(str(src)) or "image"
        st = {"family": "sans-serif", "size": 11, "weight": "normal", "italic": False,
              "color": "#888", "align": "center", "lh": 1.2}
        placeholder = (p.rect(x, y, w, h, "#eee", Stroke(color="#bbb"))
                       + p.line(x, y, x + w, y + h, Stroke(color="#ccc"))
                       + p.line(x + w, y, x, y + h, Stroke(color="#ccc"))
                       + p.text_tag(x, y + h / 2 - 8, w, 16, "▣ " + str(label), st, vcenter=True))
        return p.clip_wrap(placeholder, clip_id) if clip_id else placeholder

    def _image_href(self, src):
        asset = self.assets.get(src)
        href = None
        if isinstance(asset, dict):
            href = asset.get("data") or asset.get("url")
            path = asset.get("src") or asset.get("path")
        else:
            path = asset if asset else src

        if href:
            return str(href)
        if not path:
            return None
        path = str(path)
        if path.startswith(("data:", "http://", "https://", "file://")):
            return path
        if not os.path.isabs(path):
            path = os.path.normpath(os.path.join(self.base_dir, path))
        if os.path.exists(path):
            return "file://" + path
        return None

    def _image_clip_id(self, clip, x, y, w, h):
        shape = clip
        if isinstance(clip, dict):
            shape = clip.get("shape") or clip.get("type")
        if isinstance(shape, str) and shape.lower() in ("ellipse", "circle", "oval"):
            return self._painter.clip_ellipse(x + w / 2, y + h / 2, w / 2, h / 2)
        return None

    @staticmethod
    def _image_preserve_aspect_ratio(value):
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "xMidYMid meet"

    def canvas_wh(self, page):
        return self._canvas.resolve(page)

    def canvas_background(self, page):
        """The page's authored canvas background, colour-token resolved; None
        when unauthored (the painter then applies its documented default)."""
        bg = self._canvas.background(page)
        return (self._color.resolve(bg) or bg) if bg else None

    def render_page(self, page):
        """Return a list of SVG strings (1 for page-mode, N for paginated flow)."""
        self._painter.new_page()
        self._global_page += 1                # this producer's first leaf page
        self.flow_headings = []
        self.flow_links = []
        self.running_log = []
        self._current_page_id = page.get("id")
        self.contract = {**self.doc_contract, **((page.get("rendering") or {}).get("text") or {})}
        w, h = self.canvas_wh(page)
        if page.get("mode") == "flow":
            return self._render_flow(page, w, h)
        self._object_index = self._index_objects(page)
        body = self._render_page_body(page)
        return [self._painter.document(w, h, body,
                                       lang=self.doc.get("lang"), title=self.doc.get("title"),
                                       desc=self.doc.get("description"),
                                       background=self.canvas_background(page))]

    def _render_page_body(self, page):
        body = []
        for layer in sorted(page.get("layers") or [], key=lambda L: L.get("z", 0)):
            lo = layer.get("opacity")
            inner = "".join(self.obj(o) for o in self._paint_ordered(layer.get("objects") or []))
            body.append(self._painter.opacity_group(inner, lo) if lo not in (None, 1) else inner)
        rendered = "".join(body)

        # `reading_order` is accessibility STRUCTURE, never z-order. Reordering
        # emission to match it painted listed objects first — beneath any
        # unlisted background (2026-07-02 regression). Paint order stays
        # layer/z/document order; the authored order rides along as metadata
        # for a future tagged export / assistive-technology mapping.
        ordered = page.get("reading_order")
        if isinstance(ordered, list) and ordered:
            ids = " ".join(str(oid) for oid in ordered)
            rendered = self._painter.metadata_group(rendered, {"data-reading-order": ids})
        return rendered

    def _paint_ordered(self, objects):
        """Objects in paint order: `style.z_index` is a STABLE sort key among
        siblings (layer top level and group children alike; default 0), so
        siblings without one keep document order and the
        emitted bytes are unchanged. SVG paints in document order — CSS z-index
        is inert inside inline SVG — so ordering emission is the only honest
        implementation. The inert `z-index` style attribute is still emitted for
        HTML-embedding consumers."""
        return sorted(objects, key=self._z_of)

    def _z_of(self, o):
        """Stable z_index sort key (default 0) shared by every paint-order site."""
        if not isinstance(o, dict):
            return 0.0
        z = self._style_dict(o.get("style")).get("z_index")
        return num(z, 0) or 0.0

    @classmethod
    def _story_headings(cls, story):
        """Static walk of a story's headings in emission order (descending into
        block/keep_together containers) — the entry list a `toc` renders."""
        out = []
        for fl in story or []:
            if not isinstance(fl, dict):
                continue
            if fl.get("type") == "heading":
                out.append({"level": int(fl.get("level", 1) or 1),
                            "text": str(fl.get("text") or ""), "id": fl.get("id")})
            elif fl.get("type") in ("block", "keep_together"):
                out.extend(cls._story_headings(fl.get("children") or []))
        return out

    @classmethod
    def _story_has_toc(cls, story):
        for fl in story or []:
            if not isinstance(fl, dict):
                continue
            if fl.get("type") == "toc":
                return True
            if fl.get("type") in ("block", "keep_together") and cls._story_has_toc(fl.get("children")):
                return True
        return False

    def _render_flow(self, page, w, h):
        """Paginate a flow page. A story containing a `toc`, or a master with
        `fixed`/`running` furniture, renders twice: a dry first pass records
        which page each heading lands on (and, for running furniture, the
        section's total page count + the `set_string` log), then the real
        pass emits the toc entries / running header-footer-page-number with
        that telemetry. Both features reserve identical space in both passes
        (the toc's page-number column; running furniture paints outside the
        content box entirely), so pagination is identical across passes; the
        dry pass's telemetry is rolled back so nothing is double-counted."""
        master = self.masters.get(page.get("master")) if page.get("master") else None
        needs_running = bool(master and (master.get("fixed") or master.get("running")))
        if self._story_has_toc(page.get("story") or []) or needs_running:
            saved = (dict(self.tstats), self.skipped, copy.deepcopy(self.diagnostics),
                     self._global_page)
            try:
                dry_pages = self._render_flow_pages(page, w, h, toc_pages=None)
                toc_pages = [hd["page"] for hd in self.flow_headings]
                running_log = list(self.running_log)
                total_pages = len(dry_pages)
            finally:
                self.tstats, self.skipped, self.diagnostics, self._global_page = saved
            self._painter.new_page()
            self.flow_headings = []
            self.flow_links = []
            self.running_log = []
            return self._render_flow_pages(page, w, h, toc_pages=toc_pages,
                                           running_log=running_log, total_pages=total_pages)
        return self._render_flow_pages(page, w, h, toc_pages=None)

    def _render_flow_pages(self, page, w, h, toc_pages=None, running_log=None, total_pages=None):
        p = self._painter
        # Content geometry is resolved by the backend-neutral flow layout engine
        # (ADR-0003) from the page master — explicit region box → master margin →
        # the Johnston canon (mirrored recto/verso) — instead of a hard-coded
        # symmetric margin. Recomputed per page so odd/even pages mirror; width is
        # parity-independent, so a paragraph's line breaks stay valid across a break.
        master = self.masters.get(page.get("master")) if page.get("master") else None
        page_bg = self.canvas_background(page)  # authored canvas background (ADR-0006)

        def geom(page_index):                   # page_index = document-global leaf number
            gx, gy, gw, gh = flow_layout.content_box(master, w, h, page_index)
            return gx, gy, gw, gy + gh          # x, top, usable(width), bottom

        # Recto/verso parity follows the document-global page number (not a section
        # -local counter) so a flow that does not begin on an odd global page still
        # mirrors correctly. render_page already counted this section's first page.
        x, top, usable, bottom = geom(self._global_page)
        prev_kind = None                        # previous flowable, for indent policy
        pages, body, cy = [], [], top
        open_blocks = []          # decorated block/keep_together containers being filled
        measuring = False         # true during a trial layout pass (keep_together fit)

        def _resolve_field(field):
            """Resolve a Text object's `field` (src/frameforge/model.py
            Text.field — 'the grammar's {string: <name>} form for named
            strings', or the literal 'page'/'pages' counters). This is the
            REAL, already-declared mechanism (and already authored into
            committed b1/ oracle fixtures: chroma-styling-showcase.fg.json,
            ieee-reference-guide.fg.json use {string: name}/'page'), not a
            template-string convention invented for this change. `page_no`
            is this section's own (1-based, matching `hp`'s convention)
            current count; `name` resolves against `running_log`'s
            (page, name, value) entries set by a heading's `set_string` —
            the LAST one at or before this page, so a running header shows
            whichever chapter/section title most recently "fired" as of the
            page being painted. Returns None (leave `text` alone) when
            `field` is absent or unrecognized."""
            page_no = len(pages) + 1
            if field == "page":
                return str(page_no)
            if field == "pages":
                return str(total_pages if total_pages is not None else page_no)
            if isinstance(field, dict) and "string" in field:
                name = field["string"]
                value = None
                for pg, slot, val in (running_log or ()):
                    if slot != name:
                        continue
                    if pg <= page_no:
                        value = val
                    else:
                        break
                return value or ""
            return None

        def _with_fields_resolved(o):
            """Deep-clone a VisualObject tree, overriding any Text object's
            `text` with its resolved `field` value (leaves the authored
            placeholder alone when `field` is absent, e.g. static fixed
            chrome like a logo)."""
            if isinstance(o, dict):
                out = {k: _with_fields_resolved(v) for k, v in o.items()}
                if out.get("type") == "text" and out.get("field") is not None:
                    resolved = _resolve_field(out["field"])
                    if resolved is not None:
                        out["text"] = resolved
                return out
            if isinstance(o, list):
                return [_with_fields_resolved(v) for v in o]
            return o

        def paint_furniture():
            """Paint master.fixed + running.header/footer/page_number onto the
            CURRENT page's body. Only in the real pass (`running_log` is a
            list, not None — the dry pass never paints, only measures) and
            only when a master actually configures any of them — so a
            document with neither is byte-identical to before this feature
            existed (PageMaster.running / StringSet were schema-only until
            this change; grep across src/frameforge/rendering found zero
            reads of "running" or "fixed" prior to it)."""
            if not master or running_log is None:
                return
            for obj in (master.get("fixed") or []):
                body.append(self.obj(_with_fields_resolved(obj)))
            running = master.get("running") or {}
            for obj in (running.get("header") or []):
                body.append(self.obj(_with_fields_resolved(obj)))
            for obj in (running.get("footer") or []):
                body.append(self.obj(_with_fields_resolved(obj)))
            pn = running.get("page_number")
            if pn:
                style = pn if isinstance(pn, dict) else {
                    "font_size": 9, "color": "#666666", "align": "center"}
                body.append(self.obj({"type": "text", "box": [x, bottom + 12, usable, 16],
                                      "text": str(len(pages) + 1), "style": style}))

        def flush():
            if body:
                paint_furniture()
                pages.append(p.document(w, h, "".join(body), background=page_bg))

        def newpage():
            nonlocal body, cy, x, top, usable, bottom
            # A decorated container that straddles the break paints its fragment on
            # the page being flushed (inner-first so z-order/insert indices hold),
            # then re-opens on the fresh page from the top with its padding re-inset.
            for blk in reversed(open_blocks):
                _insert_block_rect(blk, bottom)
            flush()
            p.new_page()
            self._global_page += 1
            x, top, usable, bottom = geom(self._global_page)
            body, cy = [], top
            for blk in open_blocks:
                blk["idx"], blk["top"] = len(body), top
                blk["rect_x"], blk["rect_w"] = x, usable
                _pt, _pr, _pb, _pl = blk["pad"]
                x += _pl
                usable -= _pl + _pr

        def _pad4(pad):
            """Normalize a padding value to (top, right, bottom, left)."""
            if pad is None:
                return (0.0, 0.0, 0.0, 0.0)
            if isinstance(pad, (int, float, str)):
                v = num(pad, 0.0)
                return (v, v, v, v)
            vals = [num(v, 0.0) for v in pad]
            if len(vals) == 2:
                return (vals[0], vals[1], vals[0], vals[1])
            if len(vals) == 4:
                return tuple(vals)
            v = vals[0] if vals else 0.0
            return (v, v, v, v)

        def _container_decor(fl, style):
            """Resolve a block/keep_together's fill, border stroke, radius and
            padding — reusing the shape fill/stroke resolvers so gradients and
            border dicts behave exactly as they do for an absolute rect. Returns
            (fill, stroke, radius, pad4); fill/stroke are None when unset so an
            undecorated container stays byte-identical to before."""
            fill = self._shape_fill(fl, style)
            stroke = self._shape_stroke(fl, style)
            radius = num(fl.get("radius", style.get("radius",
                         style.get("border_radius", 0))), 0.0)
            pad = fl.get("padding")
            if pad is None:
                pad = style.get("padding")
            return fill, stroke, radius, _pad4(pad)

        def _insert_block_rect(blk, frag_bottom):
            """Insert a container's background/border rect behind its children (at
            the index captured when the container opened), spanning this page's
            fragment. No-op when the container carries neither fill nor border."""
            if not (blk["fill"] or blk["stroke"]):
                return
            rh = frag_bottom - blk["top"]
            if rh <= 0:
                return
            body.insert(blk["idx"], p.rect(blk["rect_x"], blk["top"], blk["rect_w"],
                                           rh, blk["fill"], blk["stroke"],
                                           radius=blk["radius"]))

        def emit_container(fl, children):
            """A `block`/`keep_together` container: paint its own fill/border/padding
            (the proxy used to drop these), then emit its children inset by the
            padding. Backgrounds split correctly across page breaks via
            `open_blocks` (see newpage)."""
            nonlocal cy, x, usable
            style = self._style_dict(fl.get("style")) if fl.get("style") else {}
            fill, stroke, radius, pad = _container_decor(fl, style)
            pt, pr, pb, pl = pad
            decorated = bool(fill or stroke or pt or pr or pb or pl)
            blk = {"idx": len(body), "top": cy, "rect_x": x, "rect_w": usable,
                   "fill": fill, "stroke": stroke, "radius": radius, "pad": pad}
            if decorated:
                open_blocks.append(blk)
                cy += pt
                x += pl
                usable -= pl + pr
            for child in children:
                if isinstance(child, dict):
                    emit_flow(child)
            if decorated:
                cy += pb
                _insert_block_rect(blk, cy)
                if open_blocks and open_blocks[-1] is blk:
                    open_blocks.pop()
                x -= pl
                usable += pl + pr
            cy += 4

        def measure_flow(children):
            """Trial-lay children into a throwaway buffer with no page bottom, to
            learn their height — used to decide whether a `keep_together` block fits
            in the remaining space before committing to it. Side effects (paint,
            page breaks, toc/skip telemetry) are suppressed via `measuring`."""
            nonlocal body, cy, bottom, measuring
            save = (body, cy, bottom, measuring)
            body, cy, bottom, measuring = [], 0.0, float("inf"), True
            for child in children:
                if isinstance(child, dict):
                    emit_flow(child)
            height = cy
            body, cy, bottom, measuring = save
            return height

        def wrap(text, size):
            cpl = max(8, int(usable / (size * 0.52)))
            words, lines, cur = str(text).split(), [], ""
            for word in words:
                if cur and len(cur) + 1 + len(word) > cpl:
                    lines.append(cur); cur = word
                else:
                    cur = (cur + " " + word).strip()
            if cur:
                lines.append(cur)
            return lines or [""]

        def text_of(value):
            if value is None:
                return ""
            if isinstance(value, (str, int, float)):
                return str(value)
            if isinstance(value, list):
                return "".join(text_of(item) for item in value)
            if not isinstance(value, dict):
                return str(value)
            if value.get("text") is not None:
                return str(value.get("text"))
            if isinstance(value.get("content"), list):      # LinkInline / FootnoteInline inline content
                return "".join(text_of(item) for item in value.get("content") or [])
            if value.get("tex") is not None:                # inline math fallback
                return math_text(value.get("tex"))
            if value.get("latex") is not None:
                return math_text(value.get("latex"))
            if isinstance(value.get("spans"), list):
                return "".join(text_of(span) for span in value.get("spans") or [])
            if isinstance(value.get("children"), list):
                return "\n".join(text_of(child) for child in value.get("children") or [])
            return ""

        def emit(text, st, indent=0, gap_after=6):
            nonlocal cy
            for ln in wrap(text, st["size"]):
                if cy + st["size"] > bottom:
                    newpage()
                body.append(p.text_tag(x + indent, cy, usable - indent, st["size"] * st["lh"],
                                       ln, st, vcenter=False))
                cy += st["size"] * st["lh"]
            cy += gap_after

        def emit_para(fl, st, first_indent):
            """A prose paragraph set through the backend-neutral flow engine
            (ADR-0003): Knuth–Plass line breaks + Liang hyphenation, a first-line
            indent, no inter-paragraph gap. The engine owns the breaks; each line
            is emitted as ONE text element, justified to its column width via SVG
            textLength so a real shaper distributes the slack with its own metrics
            (flush on browser/PDF; tight, hyphenated rag on the cairosvg proxy) —
            never hand-placed words fighting the rasterizer's advances."""
            nonlocal cy
            size = float(st.get("size", 12))
            lh = float(st.get("lh", 1.4))
            align = st.get("align") or "justify"
            line_st = {**st, "align": "left"}
            # An explicit `text_indent` in the paragraph's style wins over the
            # positional default (first-line indent on every paragraph after the
            # first) — so `text_indent: 0` yields the modern space-between look,
            # not a forced book indent the author never asked for.
            ti = st.get("text_indent")
            indent = num(ti) if ti is not None else (size if first_indent else 0.0)
            # Per-span inline styles (bold/colour/italic runs) survive flow layout:
            # lay out the flattened run text, then re-slice the styled runs onto each
            # line by char offset (LaidLine.start/end) and emit per-run tspans — the
            # SAME machinery the absolute text renderer uses (render_text). Only taken
            # when a span actually carries its own style, so plain paragraphs stay on
            # the single-`text_tag` fast path (byte-identical, no golden churn).
            spans = fl.get("spans") if isinstance(fl.get("spans"), list) else None
            styled = spans and any(
                isinstance(s, dict) and (s.get("style") or s.get("kind") == "math")
                for s in spans)
            if styled:
                runs = self._span_runs(spans, line_st)
                flat = "".join(t for t, _ in runs)
                para = flow_layout.layout_paragraph(
                    flat, size=size, avg=0.52, lh=lh, width=usable,
                    measure=lambda s, z, a: self.measure(s, z, a, st), align=align,
                    first_line_indent=indent)
                for line in para.lines:
                    if cy + size > bottom:
                        newpage()
                    lruns = flow_layout.slice_runs(runs, line.start, line.end) \
                        or [(line.text, line_st)]
                    if line.text.endswith("-"):     # carry the soft hyphen onto the last run
                        lruns = [*lruns[:-1], (lruns[-1][0] + "-", lruns[-1][1])]
                    body.append(p.text_runs(
                        cy + size * 0.92, "start", x + line.indent, line_st, size, lruns,
                        text_len=(line.width if line.justify else None)))
                    cy += line.advance
                cy += para.space_after
                return
            para = flow_layout.layout_paragraph(
                text_of(fl), size=size, avg=0.52, lh=lh, width=usable,
                measure=self.measure, align=align,
                first_line_indent=indent)
            for line in para.lines:
                if cy + size > bottom:
                    newpage()
                body.append(p.text_tag(
                    x + line.indent, cy, line.width, size * lh, line.text,
                    line_st, vcenter=False,
                    text_len=(line.width if line.justify else None)))
                cy += line.advance
            cy += para.space_after

        def emit_table(fl):
            nonlocal cy
            header = fl.get("header") if isinstance(fl.get("header"), list) else []
            rows = fl.get("rows") if isinstance(fl.get("rows"), list) else []
            if not header and not rows:
                return
            specs = fl.get("columns") if isinstance(fl.get("columns"), list) else []
            col_count = max(len(header), len(specs),
                            *(len(r) for r in rows if isinstance(r, list)), 1)

            def _spec(i):
                return specs[i] if i < len(specs) and isinstance(specs[i], dict) else {}

            # Per-column widths: honour explicit `width` specs, split the remainder
            # equally among unsized columns, then scale to fill the column exactly.
            widths, unsized, fixed = [], [], 0.0
            for i in range(col_count):
                wv = num(_spec(i).get("width"), None) if _spec(i).get("width") is not None else None
                widths.append(wv)
                (unsized.append(i) if wv is None else None)
                fixed += wv or 0.0
            if unsized:
                share = max(1.0, (usable - fixed) / len(unsized))
                for i in unsized:
                    widths[i] = share
            span = sum(widths) or 1.0
            widths = [w * usable / span for w in widths]
            xs = [x + sum(widths[:i]) for i in range(col_count)]

            # Honor the table's authored `style` (header_fill/header_text/
            # cell_text/zebra_fill/cell_size) instead of hardcoded greys — else the
            # table ignores the brand and leaks off-scale sizes/colours.
            sty = fl.get("style") if isinstance(fl.get("style"), dict) else {}

            def _c(v, d):
                return (self._color.resolve(v) or v) if v else d

            # Sizes/colours come only from the table's `style` (falling back to
            # the document-defined `base`); no fill/grid/size literal is injected.
            # Geometry follows the same contract (GH #61): grid_width /
            # cell_padding / header_weight / cell_line_height are style keys
            # whose documented fallbacks (0.5 / 4.0 / 700 / 1.25) keep
            # style-silent tables byte-identical. 0 is authorable — None-check,
            # never truthiness.
            font_size = num(sty.get("cell_size")) or base["size"]
            head_fill = _c(sty.get("header_fill"), None)
            zebra_fill = _c(sty.get("zebra_fill"), None)
            grid = _c(sty.get("grid_color"), None)
            grid_w = num(sty.get("grid_width"))
            grid_stroke = Stroke(color=grid, width=0.5 if grid_w is None else grid_w) if grid else None
            cell_lh = num(sty.get("cell_line_height"))
            cell_lh = 1.25 if cell_lh is None else cell_lh
            cell_st = {**base, "size": font_size, "lh": cell_lh,
                       "color": _c(sty.get("cell_text"), base["color"])}
            head_w = sty.get("header_weight")
            head_st = {**cell_st, "weight": 700 if head_w is None else head_w,
                       "color": _c(sty.get("header_text"), base["color"])}
            pad = num(fl.get("cell_padding"))            # the element's own field wins
            if pad is None:
                pad = num(sty.get("cell_padding"))       # then the style/theme key
            pad = 4.0 if pad is None else pad
            line_h = font_size * cell_lh

            def _wrap_cell(value, w):
                cpl = max(3, int((w - 2 * pad) / (font_size * 0.52)))
                out = []
                for seg in str(text_of(value)).split("\n"):
                    cur = ""
                    for wd in seg.split():
                        if cur and len(cur) + 1 + len(wd) > cpl:
                            out.append(cur); cur = wd
                        else:
                            cur = (cur + " " + wd).strip()
                    out.append(cur)
                return out or [""]

            def emit_row(values, st, fill):
                # Wrapping cells: row height follows the tallest cell (no more
                # single-line clipping); the cell background/grid box spans it.
                nonlocal cy
                cells = [_wrap_cell(values[i] if i < len(values) else "", widths[i])
                         for i in range(col_count)]
                rh = max((len(c) for c in cells), default=1) * line_h + 2 * pad
                if cy + rh > bottom and cy > top:
                    newpage()
                    if header and st is not head_st and repeat_header:
                        emit_row(header, head_st, head_fill)     # repeatRows
                for i in range(col_count):
                    body.append(p.rect(xs[i], cy, widths[i], rh, fill, grid_stroke))
                    cst = {**st, "align": _spec(i).get("align") or st.get("align") or "left"}
                    ty = cy + pad
                    for ln in cells[i]:
                        body.append(p.text_tag(xs[i] + pad, ty, widths[i] - 2 * pad,
                                               line_h, ln, cst, vcenter=False))
                        ty += line_h
                cy += rh

            repeat_header = header and bool(fl.get("repeat_header", True))
            caption = text_of(fl.get("caption"))
            if caption:
                emit(caption, {**named("caption"), "weight": 700}, gap_after=4)
            if header:
                emit_row(header, head_st, head_fill)
            for idx, row in enumerate(rows):
                emit_row(row if isinstance(row, list) else [row], cell_st,
                         None if idx % 2 == 0 else zebra_fill)
            cy += 10

        def emit_math(fl):
            nonlocal cy
            input_kind = "tex" if fl.get("tex") is not None else "mathml" if fl.get("mathml") is not None else "tex"
            source = fl.get("tex") if fl.get("tex") is not None else fl.get("mathml") if fl.get("mathml") is not None else text_of(fl)
            rendered = self._math.render(source, input_kind)
            if rendered:
                math_color = "#111"
                math_body = str(rendered.get("body")).replace("currentColor", math_color)
                natural_w = max(1.0, num(rendered.get("width"), 120))
                natural_h = max(1.0, num(rendered.get("height"), 24))
                scale = min(1.0, usable / natural_w)
                draw_w = natural_w * scale
                draw_h = natural_h * scale
                if cy + draw_h > bottom:
                    newpage()
                mx = x + (usable - draw_w) / 2
                title = fl.get("alt") or fl.get("aria_label") or "math expression"
                body.append(p.embedded_svg(
                    mx, cy, draw_w, draw_h,
                    viewbox=rendered.get("viewBox"), color=math_color,
                    title=title, body=math_body,
                ))
                cy += draw_h + 12
                return

            text = math_text(source)
            st = {**base, "family": "serif", "size": 13, "color": "#111", "align": "center", "lh": 1.25}
            for ln in str(text).splitlines() or [""]:
                emit(ln, st, gap_after=1)
            cy += 8

        def emit_linked(spans, st, gap_after=6):
            """Paragraph spans containing LinkInline runs: wrap at word level with
            the SAME greedy char-count rule as wrap(), then emit each line as
            href-aware runs so `<a href>` survives wrapping. Link-free lines go
            through the plain text_tag path (byte-identical to emit())."""
            nonlocal cy
            runs = []
            for sp in spans:
                href = sp.get("href") if (isinstance(sp, dict) and sp.get("kind") == "link") else None
                for word in str(text_of(sp)).split():
                    runs.append((word, href))
            cpl = max(8, int(usable / (st["size"] * 0.52)))
            lines, cur, cur_len = [], [], 0
            for word, href in runs:
                if cur and cur_len + 1 + len(word) > cpl:
                    lines.append(cur)
                    cur, cur_len = [(word, href)], len(word)
                else:
                    cur.append((word, href))
                    cur_len = (cur_len + 1 + len(word)) if cur_len else len(word)
            if cur:
                lines.append(cur)
            for line in lines or [[]]:
                if cy + st["size"] > bottom:
                    newpage()
                groups = []
                for word, href in line:                 # consecutive same-href words
                    if groups and groups[-1][1] == href:
                        groups[-1][0] += " " + word
                    else:
                        if groups:
                            groups[-1][0] += " "         # separator stays in-text
                        groups.append([word, href])
                if any(href for _, href in groups):
                    body.append(p.text_line_runs(x, cy, usable, st["size"] * st["lh"],
                                                 [tuple(g) for g in groups], st))
                else:
                    body.append(p.text_tag(x, cy, usable, st["size"] * st["lh"],
                                           " ".join(word for word, _ in line), st, vcenter=False))
                cy += st["size"] * st["lh"]
            cy += gap_after

        def emit_image(fl):
            """ImageFlow: reuse the page-mode image renderer (real file, data URI,
            or the labelled placeholder) centred in the column. Width defaults to
            the column; a missing height falls back to a 16:9 frame — the proxy
            has no raster decoder to read the intrinsic size (honest default,
            documented here)."""
            nonlocal cy
            iw = num(fl.get("width"), None) or usable
            iw = min(iw, usable)
            ih = num(fl.get("height"), None) or iw * 9 / 16
            if cy + ih > bottom and cy > top:            # keep the plate whole
                newpage()
            par = fl.get("preserve_aspect_ratio")
            o = {"type": "image", "src": fl.get("src"), "label": fl.get("alt")}
            if isinstance(par, str):
                o["preserve_aspect_ratio"] = par
            elif par is False:
                o["preserve_aspect_ratio"] = "none"
            body.append(self._image(o, [x + (usable - iw) / 2, cy, iw, ih]))
            cy += ih + 6
            captxt = text_of(fl.get("caption"))
            if captxt:
                emit(captxt, {**named("caption"), "italic": True, "align": "center"},
                     gap_after=12)
            else:
                cy += 8

        def emit_toc(fl):
            """TocFlow (v1: single-column `of: headings`): title + one line per
            heading with leader dots and a right-anchored page number. Page
            numbers come from the dry pass (`toc_pages`, aligned by heading
            order); the dry pass itself renders the same line structure without
            numbers, so pagination is stable across the two passes."""
            nonlocal cy
            if fl.get("of") not in (None, "headings"):
                self.warn("flow_toc_unsupported",
                          f"toc of={fl.get('of')!r} is not supported by the SVG flow "
                          "proxy (headings only); use the pdf-tex backend for it")
                self._note_flow_skip("toc")
                return
            headings = self._story_headings(page.get("story") or [])
            tocst = self.text_style(fl.get("style")) if fl.get("style") else None
            fam = (tocst or {}).get("family") or "sans-serif"
            col = (tocst or {}).get("color") or base["color"]
            esz = (tocst or {}).get("size") or 11
            title = fl.get("title")
            if title:
                # TOC title follows the toc's own style face/colour (a step up in
                # size), not a hardcoded serif/size/colour that escapes the scale.
                emit(title, {**base, "family": fam, "color": col,
                             "size": esz * 1.5, "weight": "bold"}, gap_after=8)
            levels = fl.get("levels")
            leader = (str(fl.get("leader") or ".") or ".")[:1]
            st = {**base, "family": fam, "color": col, "size": esz,
                  "lh": (tocst or {}).get("lh") or 1.5}
            num_w = 24                                   # right column for page numbers
            line_h = st["size"] * st["lh"]
            for i, hd in enumerate(headings):
                if levels and hd["level"] not in levels:
                    continue
                if cy + line_h > bottom:
                    newpage()
                indent = 14 * max(0, hd["level"] - 1)
                body.append(p.text_tag(x + indent, cy, usable - indent - num_w, line_h,
                                       hd["text"], st, vcenter=False))
                title_w = self.measure(hd["text"], st["size"], 0.52)
                dots_x = x + indent + title_w + 6
                dots_w = x + usable - num_w - dots_x
                unit = max(0.1, self.measure(" " + leader, st["size"], 0.52))
                if dots_w > unit:
                    body.append(p.text_tag(dots_x, cy, dots_w, line_h,
                                           (" " + leader) * int(dots_w / unit), st,
                                           vcenter=False))
                if toc_pages is not None and i < len(toc_pages):
                    # a clickable region over the whole entry line → its target page,
                    # so the TOC navigates in the PDF (was a dead list of numbers).
                    self.flow_links.append({"page": len(pages) + 1,
                                            "rect": [x + indent, cy, usable - indent, line_h],
                                            "target": toc_pages[i]})
                    body.append(p.text_tag(x, cy, usable, line_h, str(toc_pages[i]),
                                           {**st, "align": "right"}, vcenter=False))
                cy += line_h
            cy += 10

        def emit_flow(fl):
            nonlocal cy, prev_kind
            ft = fl.get("type")
            stref = self.text_style(fl.get("style")) if fl.get("style") else None
            if ft == "heading":
                sz = max(15, 30 - 3 * (fl.get("level", 1) - 1))
                # record which flow page this heading lands on (1-based) — read
                # by the toc pass and the PDF outline builder. Mirrors emit()'s
                # page-break check for the first line.
                hp = len(pages) + (2 if cy + sz > bottom else 1)
                if not measuring:       # a trial (keep_together fit) records nothing
                    self.flow_headings.append({"level": int(fl.get("level", 1) or 1),
                                               "text": text_of(fl), "id": fl.get("id"),
                                               "page": hp})
                # `{{page}}`/running-header resolution use the SAME section-local
                # numbering as `hp` (a "page N of TOTAL" reads as this flow
                # section's own pagination, matching author expectation — not a
                # document-global leaf index that would be confusing if this
                # section doesn't start the document).
                for ss in (fl.get("set_string") or []):
                    if isinstance(ss, dict) and ss.get("name"):
                        value = ss.get("value")
                        if value is None:
                            value = text_of(fl)
                        self.running_log.append((hp, str(ss["name"]), str(value)))
                hst = {**base, "size": sz, "weight": "bold"}
                if stref:
                    # Honor the resolved heading style's typography — face, weight,
                    # leading, tracking, case, alignment, colour — not only its
                    # colour. Previously only `color` was carried, so a styled
                    # heading silently fell back to the serif `base` and ignored the
                    # document's typeface (the flow proxy's "headings are serif" bug).
                    for k in ("family", "family_primary", "weight", "italic", "lh",
                              "align", "letter_spacing", "text_transform", "color"):
                        if stref.get(k) is not None:
                            hst[k] = stref[k]
                    raw = self._style_dict(fl.get("style"))
                    if raw.get("font_size") is not None or raw.get("size") is not None:
                        hst["size"] = stref["size"]     # explicit style size wins over the level heuristic
                emit(text_of(fl), hst, gap_after=10)
            elif ft == "paragraph":
                spans = fl.get("spans")
                st = stref or base
                if isinstance(spans, list) and any(
                        isinstance(s, dict) and s.get("kind") == "link" for s in spans):
                    emit_linked(spans, st)       # linked runs stay left (slice-1 limit)
                elif (st.get("align") or "justify") in ("center", "right"):
                    emit(text_of(fl), st)        # painter handles center/right alignment
                else:
                    emit_para(fl, st, first_indent=prev_kind not in (None, "heading"))
            elif ft == "list":
                ordered = bool(fl.get("ordered"))
                list_st = stref or base                  # honor the list's face, not serif base
                for idx, it in enumerate(fl.get("items", []), start=1):
                    bullet = f"{idx}. " if ordered else "• "
                    emit(bullet + text_of(it), list_st, indent=16, gap_after=2)
                cy += 6
            elif ft in ("block", "keep_together"):
                children = fl.get("children") if isinstance(fl.get("children"), list) else []
                # keep_together: if the whole block fits in the remaining space, keep
                # it atomic by starting it on the next page; if it is taller than a
                # full page it necessarily splits (its fill/border then paints per
                # page fragment). A trial measure decides — suppressed telemetry.
                if ft == "keep_together" and not measuring and cy > top:
                    if cy + measure_flow(children) > bottom:
                        newpage()
                emit_container(fl, children)
            elif ft == "table":
                emit_table(fl)
            elif ft == "math":
                emit_math(fl)
            elif ft == "code":
                text = fl.get("code") or fl.get("source") or text_of(fl)
                # Reserved `code` style, resolved like `caption` (ADR-0006 /
                # GH #62); only a document without one gets the documented
                # monospace/10/#333 fallback.
                if "code" in (self.text_styles or {}) or "code" in (self.styles or {}):
                    mono = named("code")
                else:
                    mono = {**base, "family": "monospace", "size": 10, "color": "#333"}
                for ln in str(text).splitlines() or [""]:
                    emit(ln, mono, gap_after=1)
                cy += 8
            elif ft == "spacer":
                cy += num(fl.get("height"), 12) or 12
            elif ft in ("page_break", "column_break"):
                newpage()
            elif ft == "figure" and isinstance(fl.get("object"), dict):
                emit_figure(fl)
            elif ft == "image":
                emit_image(fl)
            elif ft == "toc":
                emit_toc(fl)
            else:
                text = text_of(fl)
                if text:
                    emit(text, stref or base)
                elif not measuring:
                    # the proxy dropped this block: COUNT it by type — a document
                    # that validates but loses content must say so (no silence).
                    self._note_flow_skip(ft)
            if ft not in ("block", "keep_together"):
                prev_kind = ft                   # blocks keep their last child's kind

        def emit_figure(fl):
            nonlocal cy
            # Draw the figure's actual geometry (the "drawing"), not a stub.
            ob = fl["object"]
            obox = ob.get("box") if isinstance(ob.get("box"), list) else None
            size = fl.get("size") if isinstance(fl.get("size"), list) else None
            fw = (num(size[0], 0) if size and len(size) >= 2
                  else num(obox[2], usable) if obox and len(obox) >= 4 else usable)
            fh = (num(size[1], 0) if size and len(size) >= 2
                  else num(obox[3], 0) if obox and len(obox) >= 4 else 0)
            scale = min(1.0, usable / fw) if fw else 1.0
            # Quantize the fit scale ONCE at emitted precision, then derive
            # draw_h / tx / ty from that same value, so paint (the scale()
            # attr) and layout (the flow-cursor advance) agree exactly. fnum's
            # 3 decimals cost up to fw·5e-4 px at the figure's far edge
            # (1.0 px at usable=3600, fw=6100); fnum_precise keeps the
            # residual below 1e-5 px.
            if scale != 1.0:
                scale = float(fnum_precise(scale))
            draw_h = (fh or 0) * scale
            if cy + draw_h > bottom and cy > top:        # keep a figure whole
                newpage()
            inner = self.obj(ob)
            if inner:
                ox = num(obox[0], 0) if obox and len(obox) >= 2 else 0
                oy = num(obox[1], 0) if obox and len(obox) >= 2 else 0
                tx, ty = x - ox * scale, cy - oy * scale
                if scale != 1.0:
                    body.append(p.transform_group(
                        inner, [("translate", [fnum(tx), fnum(ty)]),
                                ("scale", [fnum_precise(scale)])]))
                else:
                    body.append(p.group(inner, translate=(tx, ty)) if (tx or ty) else inner)
                cy += draw_h + 6
            cap = fl.get("caption")
            captxt = cap if isinstance(cap, str) else (cap.get("text", "") if isinstance(cap, dict) else "")
            if captxt:
                emit(captxt, {**named("caption"), "italic": True, "align": "center"},
                     gap_after=12)
            else:
                cy += 8

        # `base` is the flow renderer's SINGLE default text style, and it is
        # DOCUMENT-DEFINED: it is the document's reserved `body` style when
        # present (resolved through the same style resolver as everything else).
        # Only when the document defines no `body` style does a lone documented
        # engine fallback apply. Every flow element inherits `base` and overrides
        # it per-object (`style`) or via reserved style tokens resolved by
        # `named()`. The flow renderer holds NO other font/size/colour literal —
        # so it cannot inject a style the document did not define (the `--to
        # audit` target proves it).
        if "body" in (self.styles or {}) or "body" in (self.text_styles or {}):
            base = self.text_style("body")
        else:
            base = {"family": "serif", "size": 12, "weight": "normal", "italic": False,
                    "color": "#1c1c1c", "align": "left", "lh": 1.4}

        def named(name):
            """Resolve a reserved style the DOCUMENT may define (e.g. 'caption');
            falls back to the single `base` default so nothing undefined is
            injected."""
            if name in (self.text_styles or {}) or name in (self.styles or {}):
                return self.text_style(name)
            return base
        for fl in page.get("story") or []:
            if not isinstance(fl, dict):
                continue
            emit_flow(fl)
        flush()
        return pages or [p.document(w, h, "", background=page_bg)]


# --------------------------------------------------------------------------- #
#  driver                                                                     #
# --------------------------------------------------------------------------- #
