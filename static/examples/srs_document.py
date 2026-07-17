#!/usr/bin/env python3
"""SRS → FrameForge — render an FDPM Software-Requirements export as a full,
typeset document (SVG/PDF) in the Ginga One house style.

This client is a *thin story* over the Ginga One house style
(:mod:`gingaone_house_style`): it reuses that template's design tokens
(``PAL``/``SCALE``/``WEIGHT``/``SPACE``/``INTER``), page geometry, primitives
(``T``/``R``/``LN``/``PATH``/``wordmark``) and running-furniture masters, and
adds only the SRS-specific styles, cover, and content generators.

Input is an FDPM ``current-state`` export (``$schema_note`` = "Requirement ID
prefix = axis (BR/FR/UX/PII)") holding a Specification, a Requirement corpus,
Stakeholders, and typed trace relations. The document renders, in order:

    cover · document control · introduction · scope · stakeholders ·
    requirements-at-a-glance (metrics + vector bar charts) ·
    the full requirement catalogue grouped by axis then capability domain
    (every requirement verbatim: statement, rationale, acceptance criteria,
     open issues, and its resolved trace edges) · traceability · provenance

Nothing is paraphrased: requirement text is emitted through the flow engine as
authored (CLAUDE.md rule 2). Realization state is encoded by the colour of each
requirement's ID label (green = implemented · blue = partial · grey = target-only).

────────────────────────────────────────────────────────────────────────────
PROVENANCE (CLAUDE.md rules 2 & 5). Content is a mechanical projection of the
committed FDPM export ``srs-plataforma-atendimento-srs.json`` (workbook
``plataforma-atendimento-srs``); the requirements it carries are themselves
AI-derived and PENDING operator ratification, as the Specification states. This
generator adds layout only — it invents no requirement. Design system audited
by ``frameforge_render.py <doc> --to audit``.
AI-generated — Claude Opus 4.8 (1M context) via Claude Code.

Run from the repository root::

    uv run python static/examples/srs_document.py                # default JSON → out/srs-atendimento-go
    uv run python static/examples/srs_document.py path/to/export.json out/dir
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "src"), os.path.join(ROOT, "docs"),
                os.path.dirname(os.path.abspath(__file__))]
_shadow = sys.modules.get("frameforge")
if _shadow is not None and not hasattr(_shadow, "__path__"):
    del sys.modules["frameforge"]

import gingaone_house_style as G  # noqa: E402  — the house style we build on
from frameforge.sdk import DocumentBuilder, serialize  # noqa: E402
from frameforge.sdk.paint import linear_gradient  # noqa: E402
from frameforge.sdk.validate import validate_static_rules  # noqa: E402

# ── borrow the house design system verbatim (one swap point) ────────────────
PAL, SCALE, WEIGHT, SPACE, INTER = G.PAL, G.SCALE, G.WEIGHT, G.SPACE, G.INTER
W, H, ML, MR, CW = G.W, G.H, G.ML, G.MR, G.CW
T, R, LN, PATH, wordmark = G.T, G.R, G.LN, G.PATH, G.wordmark

# ═══════════════════════════════════════════════════════════════════════════
#  data model — read the FDPM export, index it, resolve the trace graph
# ═══════════════════════════════════════════════════════════════════════════
AXIS = {
    "BR": ("Business Requirements",
           "The goals the platform must serve — the “why”, anchored in "
           "PURPOSE.md and the product specification."),
    "FR": ("Functional Requirements",
           "What the system shall do — behaviour decomposed from the business "
           "goals and corroborated against the codebase."),
    "UX": ("User-Experience Requirements",
           "How the surfaces behave — the embeddable widget, the supervisor "
           "dashboard, the operator console, and cross-cutting UI."),
    "PII": ("Privacy & Data-Protection Requirements",
            "Customer-data protection, access discipline, and LGPD obligations."),
}
AXIS_ORDER = ["BR", "FR", "UX", "PII"]
STATE_STYLE = {"implemented": "req_id_impl", "partial": "req_id_partial",
               "target-only": "req_id_target"}
STATE_COLOR = {"implemented": "green", "partial": "blue", "target-only": "faint"}
# colour-coded inline meta chips (per-span colour now survives flow layout)
PRIO_COLOR = {"must": "green_dk", "should": "blue", "could": "mute"}
STATE_META = {"implemented": "green_dk", "partial": "blue", "target-only": "mute"}
_ACRO = {"pii": "PII", "lgpd": "LGPD", "ui": "UI", "go": "GO", "llm": "LLM",
         "kb": "KB", "crm": "CRM"}


def pretty(slug: str) -> str:
    return " ".join(_ACRO.get(w, w.capitalize()) for w in str(slug).split("-"))


def short_id(pid: str) -> str:
    return pid.split(":")[-1]


class SRS:
    """A parsed FDPM software-requirements export with a resolved trace graph."""

    def __init__(self, data: dict):
        self.data = data
        self.workbook = data.get("workbook", {})
        self.source = data.get("source", {})
        prims = data.get("primitives", [])
        self.spec = next((p["field_values"] for p in prims
                          if p.get("type_id") == "srs:Specification"), {})
        self.reqs = [p for p in prims if p.get("type_id") == "srs:Requirement"]
        self.stakeholders = [p for p in prims if p.get("type_id") == "srs:Stakeholder"]
        self.relations = data.get("relations", [])

        self.by_id = {short_id(p["id"]): p for p in prims}
        self.title_of = {short_id(r["id"]): r["field_values"]["title"] for r in self.reqs}
        self.stk_name = {short_id(s["id"]): s["field_values"]["name"]
                         for s in self.stakeholders}

        # directed adjacency per relation type (source → [targets])
        self.out = defaultdict(lambda: defaultdict(list))
        for rel in self.relations:
            self.out[rel["type_id"]][short_id(rel["source_id"])].append(
                short_id(rel["target_id"]))
        # symmetric closure for peer relations
        self.peer = {"srs:ConflictsWith": defaultdict(set),
                     "srs:RelatedTo": defaultdict(set)}
        for rel in self.relations:
            if rel["type_id"] in self.peer:
                a, b = short_id(rel["source_id"]), short_id(rel["target_id"])
                self.peer[rel["type_id"]][a].add(b)
                self.peer[rel["type_id"]][b].add(a)
        # requirements each stakeholder elicited (reverse of ElicitedFrom)
        self.elicits = defaultdict(list)
        for req, stks in self.out["srs:ElicitedFrom"].items():
            for stk in stks:
                self.elicits[stk].append(req)

    @staticmethod
    def axis_of(rid: str) -> str:
        return rid.split("-")[1]

    @staticmethod
    def num_of(rid: str) -> int:
        try:
            return int(rid.split("-")[2])
        except (IndexError, ValueError):
            return 0

    def axis_reqs(self, axis: str):
        return [r for r in self.reqs if self.axis_of(short_id(r["id"])) == axis]

    def by_domain(self, reqs):
        """Group requirements by capability domain in first-appearance order,
        sorted by id within a group."""
        order, buckets = [], defaultdict(list)
        for r in reqs:
            dom = r["field_values"]["attributes"].get("domain", "general")
            if dom not in buckets:
                order.append(dom)
            buckets[dom].append(r)
        return [(dom, sorted(buckets[dom], key=lambda r: self.num_of(short_id(r["id"]))))
                for dom in order]


# ═══════════════════════════════════════════════════════════════════════════
#  house style — reuse the Ginga One scales, add the SRS-specific styles
# ═══════════════════════════════════════════════════════════════════════════
def srs_document(title: str) -> DocumentBuilder:
    b = DocumentBuilder(title=title, lang="en", profile="book")
    b.describe(f"Ginga One — {title}")
    b.meta(brand="Ginga One", template="gingaone-house-style",
           document_kind="Software Requirements Specification",
           generated_by="Claude Opus 4.8 (1M context) via Claude Code")
    b.text_contract(overflow="shrink_to_fit", min_font_size=6.0)
    for name, hexv in PAL.items():
        b.define_color(name, hexv)

    def style(name, *, size, color, weight=None, lh=None, track=None,
              upper=False, italic=False, align=None, indent=None):
        kw = {"font_family": INTER, "font_size": SCALE[size], "color": PAL[color]}
        if weight:  kw["font_weight"] = WEIGHT[weight]
        if lh is not None:  kw["line_height"] = lh
        if track is not None:  kw["letter_spacing"] = track
        if upper:  kw["text_transform"] = "uppercase"
        if italic:  kw["font_style"] = "italic"
        if align:  kw["text_align"] = align
        if indent is not None:  kw["text_indent"] = indent
        b.define_style(name, **kw)

    # shared house styles (mirror gingaone_house_style)
    style("kicker", size="small", color="green_dk", weight="bold", track=1.8, upper=True)
    style("h1", size="h1", color="ink", weight="heavy", lh=1.15, track=-0.4)
    style("h2", size="h2", color="ink", weight="bold", lh=1.3)
    style("h3", size="body", color="green_dk", weight="bold", lh=1.3, track=0.2)
    style("lead", size="body", color="ink", weight="med", lh=1.6, align="left", indent=0)
    style("body", size="body", color="body", weight="reg", lh=1.6, align="left", indent=0)
    style("callout", size="h2", color="green_dk", weight="med", lh=1.45, indent=0)
    style("caption", size="small", color="body", weight="reg", lh=1.4, indent=0)
    style("toc", size="small", color="mute", weight="reg", lh=1.7)
    # SRS-specific styles — every size/weight/colour still from the house scales
    style("req_id_impl", size="small", color="green_dk", weight="heavy", track=1.4, upper=True)
    style("req_id_partial", size="small", color="blue", weight="heavy", track=1.4, upper=True)
    style("req_id_target", size="small", color="mute", weight="heavy", track=1.4, upper=True)
    style("req_title", size="h2", color="ink", weight="bold", lh=1.25, indent=0)
    style("req_meta", size="small", color="mute", weight="med", lh=1.4, track=0.2, indent=0)
    style("req_label", size="micro", color="green_dk", weight="bold", track=1.2, upper=True)
    style("req_note", size="small", color="mute", weight="reg", lh=1.45, indent=0)
    style("req_conflict", size="small", color="blue", weight="bold", lh=1.4, indent=0)
    style("trace", size="micro", color="mute", weight="reg", lh=1.45, indent=0)
    style("evidence", size="micro", color="faint", weight="reg", lh=1.45, indent=0)
    style("stk_name", size="h2", color="ink", weight="bold", lh=1.25)
    style("stk_role", size="small", color="green_dk", weight="med", italic=True, lh=1.4)
    style("stk_note", size="small", color="mute", weight="reg", lh=1.45, indent=0)
    # carded-requirement styles (spans set their own weight/colour on top)
    style("card_bar", size="body", color="white", weight="reg", lh=1.2, indent=0)
    style("card_meta", size="small", color="mute", weight="med", lh=1.4, indent=0)
    style("card_stmt", size="body", color="ink", weight="reg", lh=1.5, indent=0)
    return b


# ═══════════════════════════════════════════════════════════════════════════
#  cover — olive masthead + hero gradient (the site's identity), SRS metadata
# ═══════════════════════════════════════════════════════════════════════════
def cover_page(b: DocumentBuilder, srs: SRS):
    spec = srs.spec
    project = str(spec.get("project", "")).replace(" (Ginga One)", "").strip()
    version = str(spec.get("version", "—"))
    date = str(spec.get("date", ""))[:10]
    revision = srs.workbook.get("revision", srs.source.get("revision", "—"))
    n_req, n_stk = len(srs.reqs), len(srs.stakeholders)
    n_rel = len(srs.relations)

    # subtitle: verbatim platform description from the Specification purpose
    purpose = str(spec.get("purpose", ""))
    subtitle = purpose.split("—", 1)[1].split(". ")[0].strip() if "—" in purpose else purpose
    subtitle = (subtitle[:1].upper() + subtitle[1:] + ".") if subtitle else ""

    # title over ≤2 display lines
    words = project.split()
    if len(words) > 2:
        mid = (len(words) + 1) // 2
        title_lines = [" ".join(words[:mid]), " ".join(words[mid:])]
    else:
        title_lines = [project] if project else ["Software Requirements"]

    L = b.page("cover", canvas={"size": [W, H], "units": "px"},
               coordinate_mode="absolute").layer("cover")
    L.add(R(0, 0, W, 84, fill=PAL["green"], decorative=True))
    L.add(wordmark(ML, 28, on_dark=True))
    L.add(T(W - MR - 200, 34, 200, 20, "gingaone.com", size="small", color="white",
            weight="med", align="right"))
    L.add(R(0, 84, W, 556, decorative=True,
            fill=linear_gradient([(PAL["wash"], "0%"), (PAL["blue_pale"], "100%")], angle=90)))
    L.add(T(ML, 150, CW, 16, "SOFTWARE REQUIREMENTS SPECIFICATION · GINGA ONE",
            size="small", color="green_dk", weight="bold", track=2, upper=True))
    ty = 192
    for i, line in enumerate(title_lines):
        L.add(T(ML, ty + i * 44, CW - 20, 48, line, size="display", color="ink",
                weight="heavy", lh=1.05, track=-0.6))
    ty += len(title_lines) * 44 + 22
    L.add(R(ML, ty, 56, 4, fill=PAL["green"], decorative=True))
    L.add(T(ML, ty + 20, CW - 40, 72, subtitle, size="h2", color="body", lh=1.5))

    # status pills
    cy = 486
    L.add(R(ML, cy, 132, 36, radius=8, fill=PAL["green"], decorative=True))
    L.add(T(ML, cy + 11, 132, 16, f"VERSION {version}", size="small", color="white",
            weight="bold", align="center", track=0.5))
    L.add(R(ML + 146, cy, 214, 36, radius=8, fill=PAL["white"], stroke=PAL["green"],
            stroke_style={"stroke_width": 1.4}, decorative=True))
    L.add(T(ML + 146, cy + 11, 214, 16, "PROPOSED · OPERATOR REVIEW PENDING",
            size="small", color="green_dk", weight="bold", align="center", track=0.4))

    # metadata rows
    my = 566
    authors = spec.get("authors", [])
    rows = [
        ("REFERENCE", srs.workbook.get("id", "—")),
        ("EDITION", f"{date} · revision {revision}"),
        ("PROFILE", srs.workbook.get("profile_id", "—")),
        ("CLASSIFICATION", "Internal — AI-derived, operator review pending"),
        ("PREPARED BY", " · ".join(str(a) for a in authors) or "—"),
    ]
    for lab, val in rows:
        L.add(T(ML, my, 132, 14, lab, size="small", color="green_dk", weight="bold", track=1.2))
        L.add(T(ML + 140, my - 2, CW - 140, 30, str(val), size="body", color="ink", weight="med"))
        my += 30

    # count strip (three stat cells)
    sy = 748
    L.add(LN(ML, sy - 16, W - MR, sy - 16, width=1))
    cells = [(str(n_req), "REQUIREMENTS"), (str(n_stk), "STAKEHOLDERS"),
             (str(n_rel), "TRACE LINKS")]
    cw3 = CW / 3
    for i, (num, lab) in enumerate(cells):
        cx = ML + i * cw3
        L.add(T(cx, sy, cw3 - 12, 44, num, size="display", color="green_dk", weight="heavy"))
        L.add(T(cx, sy + 46, cw3 - 12, 14, lab, size="small", color="mute", weight="bold", track=1.4))

    # institutional footer + disclaimer
    L.add(LN(ML, H - 96, W - MR, H - 96, width=1))
    L.add(T(ML, H - 80, CW, 16, "Ginga One · Desenvolvimento Mobile e Software · "
            "Especialistas em Varejo — desde 2011", size="small", color="mute"))
    L.add(T(ML, H - 60, CW, 28, "Generated from the FrameForge Ginga One house style over the "
            "FDPM SRS export. Requirements are AI-derived and pending operator ratification; "
            "no statement should be taken for granted without a verifiable source.",
            size="micro", color="faint", italic=True, lh=1.4))


# ═══════════════════════════════════════════════════════════════════════════
#  vector figures — dependency-free bar charts drawn in the document
# ═══════════════════════════════════════════════════════════════════════════
def bar_chart(pairs, colors, *, width=CW, row_h=30, label_w=196, val_w=52) -> dict:
    n = len(pairs)
    total_h = n * row_h + 4
    maxv = max((v for _, v in pairs), default=1) or 1
    track_w = width - label_w - val_w
    children = []
    for i, (lab, val) in enumerate(pairs):
        y = i * row_h + 4
        children.append(T(0, y + row_h / 2 - 8, label_w - 12, 16, lab, size="small",
                          color="body", weight="med", fit=False))
        children.append(R(label_w, y + 5, track_w, row_h - 15, radius=3,
                          fill=PAL["soft"], decorative=True))
        bw = max(3.0, track_w * val / maxv)
        children.append(R(label_w, y + 5, bw, row_h - 15, radius=3,
                          fill=PAL[colors[i]], decorative=True))
        children.append(T(label_w + track_w + 8, y + row_h / 2 - 8, val_w - 8, 16,
                          str(val), size="small", color="ink", weight="bold", fit=False))
    return {"type": "group", "box": [0, 0, width, total_h], "children": children}


def hrule(fl, *, color="line", w=0.8):
    fl.figure({"type": "group", "box": [0, 0, CW, 2],
               "children": [R(0, 0, CW, w, fill=PAL[color], decorative=True)]},
              size=[CW, 2], align="center")


# ═══════════════════════════════════════════════════════════════════════════
#  content generators
# ═══════════════════════════════════════════════════════════════════════════
def P(fl, text, style):
    """A verbatim paragraph (bypasses Markdown lowering — source text is
    rendered as authored, CLAUDE.md rule 2)."""
    return fl.para([str(text)], style=style)


def BULLET(fl, items, style):
    return fl.bullet([{"spans": [str(i)]} for i in items], style=style)


def sspan(text, *, color, weight=None, track=None):
    """A styled inline run that always carries the house face — omitting
    ``font_family`` makes the flow renderer fall back to a generic sans (a second
    face; the audit flags it). Colour is a PAL key."""
    st = {"font_family": INTER, "color": PAL[color]}
    if weight is not None:
        st["font_weight"] = WEIGHT[weight]
    if track is not None:
        st["letter_spacing"] = track
    return {"text": text, "style": st}


def label(fl, text):
    P(fl, text, "req_label")


def section_head(fl, n, title, running):
    fl.heading(1, f"{n} · {title}", id=f"sec-{n}", style="h1",
               set_string=[{"name": "running", "value": running}])
    fl.spacer(height=SPACE["sm"])


def requirement_card(fl, srs: SRS, req: dict):
    """One requirement as a professional 'spec card': a green ID/title header bar
    over a bordered, padded body box — drawn natively by the flow engine (block
    fills/borders/padding + per-span inline colour + keep_together)."""
    fv = req["field_values"]
    attrs = fv.get("attributes", {})
    rid = short_id(req["id"])
    state = attrs.get("realization_state", "target-only")
    verify = str(fv.get("verification", "")).replace("_", " + ")
    priority = str(fv.get("priority", "")).lower()

    with fl.keep_together() as kt:
        # header bar: white ID + title on the institutional green
        with kt.block(fill=PAL["green"], padding=[6, 12]) as bar:
            bar.para([
                sspan(rid + "   ", color="white", weight="heavy", track=0.4),
                sspan(fv["title"], color="white", weight="bold"),
            ], style="card_bar")
        # body box: soft fill + hairline border, everything padded inside
        with kt.block(fill=PAL["soft"], stroke=PAL["line"],
                      stroke_style={"stroke_width": 0.8},
                      padding=[SPACE["sm"], 12]) as bd:
            # colour-coded inline meta chips
            bd.para([
                sspan(priority.upper(), color=PRIO_COLOR.get(priority, "mute"), weight="bold"),
                sspan("   ·   " + state, color=STATE_META.get(state, "mute"), weight="med"),
                sspan(f"   ·   {fv.get('kind','')}"
                      + (f"   ·   NFR: {fv['nfr_category']}" if fv.get("nfr_category") else "")
                      + f"   ·   verify: {verify}", color="mute"),
            ], style="card_meta")
            bd.spacer(height=SPACE["xs"])
            P(bd, fv["statement"], "card_stmt")
            if fv.get("rationale"):
                bd.spacer(height=SPACE["xs"])
                bd.para([sspan("Rationale.  ", color="body", weight="bold"),
                         fv["rationale"]], style="req_note")
            if fv.get("acceptance_criteria"):
                bd.spacer(height=SPACE["xs"])
                label(bd, "Acceptance criteria")
                BULLET(bd, fv["acceptance_criteria"], "caption")
            if fv.get("open_issues"):
                bd.spacer(height=SPACE["xs"])
                bd.para([sspan("Open issues.  ", color="blue", weight="bold"),
                         "  ".join(fv["open_issues"])], style="req_note")

            trace = []
            for label_txt, key in (("Elicited from", "srs:ElicitedFrom"),
                                   ("Derived from", "srs:DerivedFrom"),
                                   ("Refines", "srs:Refines"),
                                   ("Depends on", "srs:DependsOn")):
                tgt = srs.out[key].get(rid, [])
                if tgt:
                    trace.append(f"{label_txt} " + ", ".join(tgt))
            related = sorted(srs.peer["srs:RelatedTo"].get(rid, ()))
            if related:
                trace.append("Related to " + ", ".join(related))
            if trace:
                bd.spacer(height=SPACE["xs"])
                bd.para([sspan("Trace.  ", color="mute", weight="bold"),
                         "   ·   ".join(trace)], style="trace")

            conflicts = sorted(srs.peer["srs:ConflictsWith"].get(rid, ()))
            if conflicts:
                note = next((f"  {nt}" for nt in (fv.get("notes") or [])
                             if "CONFLICT" in nt.upper()), "")
                bd.para([sspan("Conflict.  ", color="blue", weight="bold"),
                         "Conflicts with " + ", ".join(conflicts) + note], style="req_conflict")

            src = str(fv.get("source_reference", "")).strip()
            ev = attrs.get("source_evidence", [])
            line = f"Source — {src}" if src else ""
            if ev:
                line += ("   ·   " if line else "") + "Evidence — " + " · ".join(str(e) for e in ev)
            if line:
                P(bd, line, "evidence")


# ═══════════════════════════════════════════════════════════════════════════
#  build the document
# ═══════════════════════════════════════════════════════════════════════════
def build(srs: SRS) -> DocumentBuilder:
    spec = srs.spec
    project = str(spec.get("project", "Software Requirements Specification"))
    b = srs_document(f"{project} — SRS")
    cover_page(b, srs)
    body = G.body_master(b)

    with b.section("srs", master=body, media="paged") as fl:
        # ── contents ────────────────────────────────────────────────────────
        P(fl, "Contents", "h2")
        fl.spacer(height=SPACE["sm"])
        fl.toc(levels=[1, 2], leader=".", style="toc")

        # ── 1 · Introduction ────────────────────────────────────────────────
        fl.page_break()
        section_head(fl, 1, "Introduction", "01 · Introduction")

        # document control table
        control = [
            ["Project", project],
            ["Version", str(spec.get("version", "—"))],
            ["Date", str(spec.get("date", ""))[:10]],
            ["Workbook", f"{srs.workbook.get('id','—')} · rev {srs.workbook.get('revision','—')}"],
            ["Profile", str(srs.workbook.get("profile_id", "—"))],
            ["Status", "Proposed — operator review pending"],
            ["Prepared by", " · ".join(str(a) for a in spec.get("authors", [])) or "—"],
            ["Source export", str(srs.data.get("source", {}).get("workbook_id", "—"))
                + " @ " + str(srs.data.get("exported_at", ""))[:19]],
        ]
        fl.table(columns=[{"label": "Field", "width": 150}, "Value"], rows=control,
                 header=True, caption="Table 1 — Document control.",
                 style={"header_fill": PAL["green"], "header_text": PAL["white"],
                        "cell_text": PAL["ink"], "zebra_fill": PAL["soft"],
                        "grid_color": PAL["line"], "cell_size": SCALE["small"]})
        fl.spacer(height=SPACE["md"])

        if spec.get("purpose"):
            P(fl, spec["purpose"], "lead")
            fl.spacer(height=SPACE["sm"])
        if spec.get("overview"):
            P(fl, spec["overview"], "body")
            fl.spacer(height=SPACE["sm"])
        if spec.get("intended_audience"):
            label(fl, "Intended audience")
            BULLET(fl, spec["intended_audience"], "body")
            fl.spacer(height=SPACE["sm"])
        if spec.get("references"):
            label(fl, "References")
            fl.numbered([{"spans": [str(r)]} for r in spec["references"]], style="caption")
            fl.spacer(height=SPACE["sm"])
        if spec.get("assumptions"):
            label(fl, "Assumptions")
            BULLET(fl, spec["assumptions"], "caption")

        # ── 2 · Scope & Non-Goals ───────────────────────────────────────────
        fl.page_break()
        section_head(fl, 2, "Scope & Non-Goals", "02 · Scope")
        if spec.get("scope"):
            P(fl, spec["scope"], "body")
            fl.spacer(height=SPACE["sm"])
        if spec.get("out_of_scope"):
            label(fl, "Out of scope")
            BULLET(fl, spec["out_of_scope"], "body")
            fl.spacer(height=SPACE["sm"])
        if spec.get("non_goals"):
            label(fl, "Non-goals")
            BULLET(fl, spec["non_goals"], "body")

        # ── 3 · Stakeholders ────────────────────────────────────────────────
        fl.page_break()
        section_head(fl, 3, "Stakeholders", "03 · Stakeholders")
        P(fl, "Eight stakeholder roles were modelled; every requirement records the "
              "role it was elicited from (§9). One anti-persona (a threat actor) frames "
              "the adversarial concerns of the security axis.", "body")
        fl.spacer(height=SPACE["md"])
        for i, s in enumerate(srs.stakeholders):
            fv = s["field_values"]
            sid = short_id(s["id"])
            if i > 0:
                fl.spacer(height=SPACE["sm"]); hrule(fl); fl.spacer(height=SPACE["sm"])
            P(fl, f"{sid} — {fv['name']}", "stk_name")
            P(fl, fv.get("role", ""), "stk_role")
            n_drives = len(srs.elicits.get(sid, []))
            P(fl, f"Elicits {n_drives} requirement(s).", "req_meta")
            fl.spacer(height=SPACE["xs"])
            if fv.get("concerns"):
                label(fl, "Concerns")
                BULLET(fl, fv["concerns"], "caption")
            if fv.get("tacit_knowledge_notes"):
                fl.spacer(height=SPACE["xs"])
                P(fl, fv["tacit_knowledge_notes"], "stk_note")

        # ── 4 · Requirements at a Glance ────────────────────────────────────
        fl.page_break()
        section_head(fl, 4, "Requirements at a Glance", "04 · Metrics")
        pri = Counter(r["field_values"]["priority"] for r in srs.reqs)
        state = Counter(r["field_values"]["attributes"].get("realization_state") for r in srs.reqs)
        dom = Counter(r["field_values"]["attributes"].get("domain") for r in srs.reqs)
        P(fl, f"The corpus holds {len(srs.reqs)} requirements across four axes, "
              f"{len(srs.stakeholders)} stakeholders and {len(srs.relations)} typed trace "
              f"links. Priority splits {pri.get('must',0)} must / {pri.get('should',0)} "
              f"should / {pri.get('could',0)} could; realization is "
              f"{state.get('implemented',0)} implemented, {state.get('partial',0)} partial, "
              f"{state.get('target-only',0)} target-only.", "body")
        fl.spacer(height=SPACE["md"])

        axis_pairs = [(f"{a} — {AXIS[a][0].split(' Requirements')[0]}", len(srs.axis_reqs(a)))
                      for a in AXIS_ORDER]
        fl.figure(bar_chart(axis_pairs, ["green", "green", "green", "green"]),
                  size=[CW, len(axis_pairs) * 30 + 4], align="center",
                  caption="Figure 1 — Requirements by axis.", id="fig-axis")
        fl.spacer(height=SPACE["sm"])
        state_pairs = [("Implemented", state.get("implemented", 0)),
                       ("Partial", state.get("partial", 0)),
                       ("Target-only", state.get("target-only", 0))]
        fl.figure(bar_chart(state_pairs, ["green", "blue", "faint"]),
                  size=[CW, len(state_pairs) * 30 + 4], align="center",
                  caption="Figure 2 — Realization state.", id="fig-state")
        fl.spacer(height=SPACE["sm"])
        pri_pairs = [("Must", pri.get("must", 0)), ("Should", pri.get("should", 0)),
                     ("Could", pri.get("could", 0))]
        fl.figure(bar_chart(pri_pairs, ["green", "blue", "faint"]),
                  size=[CW, len(pri_pairs) * 30 + 4], align="center",
                  caption="Figure 3 — Priority (MoSCoW).", id="fig-pri")
        fl.spacer(height=SPACE["md"])

        # realization × axis matrix
        states = ["implemented", "partial", "target-only"]
        matrix_rows = []
        for st in states:
            row = [st.capitalize()]
            tot = 0
            for a in AXIS_ORDER:
                c = sum(1 for r in srs.axis_reqs(a)
                        if r["field_values"]["attributes"].get("realization_state") == st)
                row.append(str(c)); tot += c
            row.append(str(tot))
            matrix_rows.append(row)
        totals = ["Total"]
        for a in AXIS_ORDER:
            totals.append(str(len(srs.axis_reqs(a))))
        totals.append(str(len(srs.reqs)))
        matrix_rows.append(totals)
        fl.table(columns=["Realization"] + AXIS_ORDER + ["Total"], rows=matrix_rows,
                 header=True, caption="Table 2 — Realization state by axis.",
                 style={"header_fill": PAL["green"], "header_text": PAL["white"],
                        "cell_text": PAL["ink"], "zebra_fill": PAL["soft"],
                        "grid_color": PAL["line"], "cell_size": SCALE["small"]})
        fl.spacer(height=SPACE["md"])

        dom_rows = [[pretty(d), str(c), f"{100*c/len(srs.reqs):.0f}%"]
                    for d, c in dom.most_common()]
        fl.table(columns=[{"label": "Capability domain", "width": 260}, "Count", "Share"],
                 rows=dom_rows, header=True,
                 caption="Table 3 — Requirements by capability domain.",
                 style={"header_fill": PAL["green"], "header_text": PAL["white"],
                        "cell_text": PAL["ink"], "zebra_fill": PAL["soft"],
                        "grid_color": PAL["line"], "cell_size": SCALE["small"]})

        # ── 5–8 · the requirement catalogue, by axis then capability domain ──
        for n, axis in enumerate(AXIS_ORDER, start=5):
            full, blurb = AXIS[axis]
            fl.page_break()
            section_head(fl, n, full, f"{n:02d} · {full}")
            P(fl, blurb, "lead")
            fl.spacer(height=SPACE["sm"])
            for dom_slug, reqs in srs.by_domain(srs.axis_reqs(axis)):
                fl.heading(2, pretty(dom_slug), id=f"dom-{axis}-{dom_slug}", style="h3")
                fl.spacer(height=SPACE["sm"])
                for req in reqs:
                    requirement_card(fl, srs, req)
                    fl.spacer(height=SPACE["sm"])
                fl.spacer(height=SPACE["xs"])

        # ── 9 · Traceability ────────────────────────────────────────────────
        fl.page_break()
        section_head(fl, 9, "Traceability", "09 · Traceability")
        P(fl, "Requirements are linked by typed relations folded from the FDPM event "
              "log: every requirement is elicited from a stakeholder and (for the "
              "functional axes) derived from a business requirement; dependency, "
              "refinement, related-to and conflict edges connect requirements to each "
              "other. Counts below are exact.", "body")
        fl.spacer(height=SPACE["sm"])
        rel_counts = Counter(r["type_id"] for r in srs.relations)
        BULLET(fl, [f"{short_id(t).replace('srs:','')}: {c}"
                    for t, c in rel_counts.most_common()], "caption")
        fl.spacer(height=SPACE["md"])

        def trace_title(rid):       # cells wrap now — no need to truncate the title
            t = srs.title_of.get(rid, "")
            return f"{rid} — {t}" if t else rid

        # conflicts (highlighted callout)
        conflicts = [(short_id(r["source_id"]), short_id(r["target_id"]))
                     for r in srs.relations if r["type_id"] == "srs:ConflictsWith"]
        if conflicts:
            label(fl, "Conflicts")
            for a, c in conflicts:
                P(fl, f"{trace_title(a)}   ⟷   {trace_title(c)}", "req_conflict")
            fl.spacer(height=SPACE["md"])

        def edge_table(type_id, col_a, col_b, caption):
            edges = [(short_id(r["source_id"]), short_id(r["target_id"]))
                     for r in srs.relations if r["type_id"] == type_id]
            edges.sort(key=lambda e: (SRS.axis_of(e[0]), SRS.num_of(e[0])))
            rows = [[trace_title(a), trace_title(b)] for a, b in edges]
            if rows:
                fl.table(columns=[col_a, col_b], rows=rows, header=True, caption=caption,
                         style={"header_fill": PAL["green"], "header_text": PAL["white"],
                                "cell_text": PAL["ink"], "zebra_fill": PAL["soft"],
                                "grid_color": PAL["line"], "cell_size": SCALE["micro"]})
                fl.spacer(height=SPACE["md"])

        edge_table("srs:DependsOn", "Requirement", "Depends on",
                   "Table 4 — Dependency edges.")
        edge_table("srs:Refines", "Refines (specific)", "Refined requirement (general)",
                   "Table 5 — Refinement edges.")
        edge_table("srs:RelatedTo", "Requirement", "Related to",
                   "Table 6 — Related-to edges.")

        # ── 10 · Provenance & Method ────────────────────────────────────────
        fl.page_break()
        section_head(fl, 10, "Provenance & Method", "10 · Provenance")
        P(fl, "This document is a mechanical projection of the committed FDPM export "
              f"{srs.workbook.get('id','')} (revision {srs.workbook.get('revision','—')}), "
              "typeset with the FrameForge Ginga One house style. The layout invents no "
              "requirement: every statement, criterion, and trace edge is rendered as "
              "authored in the source export.", "body")
        fl.spacer(height=SPACE["sm"])
        P(fl, "The requirements themselves are AI-derived (Claude Opus 4.8 via Claude "
              "Code) from PURPOSE.md, the product specification, and codebase evidence, "
              "and are PENDING operator ratification — as the Specification's own "
              "assumptions state. Realization state (implemented / partial / target-only) "
              "records where current code and the target state diverge; it does not alter "
              "a requirement's validity as a goal.", "req_note")
        fl.spacer(height=SPACE["sm"])
        fl.add({"type": "block", "role": "note", "style": "callout",
                "fill": PAL["wash"], "padding": [SPACE["md"], 20],
                "children": [{"type": "paragraph", "style": "callout",
                              "text": "PALS's Law — LLM output is unverified by default. "
                              "Absence of a verification layer is a design defect, not a "
                              "runtime bug. No statement here should be taken for granted "
                              "without a verifiable source."}]})
        fl.spacer(height=SPACE["sm"])
        P(fl, "Methodological disclaimer: no information in this document should be taken "
              "for granted. Any statement not backed by a real logical definition or "
              "verifiable reference may be invalid, erroneous, or a hallucination. "
              "Generated by Claude Opus 4.8 (1M context) via Claude Code on "
              f"{str(srs.data.get('exported_at',''))[:10]}.", "evidence")
    return b


# ═══════════════════════════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════════════════════════
def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    json_path = argv[0] if argv else os.path.join(ROOT, "srs-plataforma-atendimento-srs.json")
    out_dir = argv[1] if len(argv) > 1 else os.path.join(ROOT, "out", "srs-atendimento-go")

    with open(json_path, encoding="utf-8") as fh:
        srs = SRS(json.load(fh))
    print(f"Loaded {json_path}: {len(srs.reqs)} requirements, "
          f"{len(srs.stakeholders)} stakeholders, {len(srs.relations)} relations")

    b = build(srs)
    doc = b.build()
    report = validate_static_rules(doc)
    errors = [i for i in report.issues if i.severity == "error"]
    print(f"Built SRS document — pages={len(doc.pages)} ok={report.ok} "
          f"errors={len(errors)} warnings={len(report.issues) - len(errors)}")
    for i in report.issues[:20]:
        print(f"  [{i.severity}] [{i.rule_id}] {i.path}: {i.message}")

    os.makedirs(out_dir, exist_ok=True)
    yaml_out = os.path.join(out_dir, "srs-atendimento-go.fg.yaml")
    with open(yaml_out, "w", encoding="utf-8") as fh:
        fh.write(serialize(doc, format="yaml"))
    print(f"Wrote {yaml_out}")

    if errors:
        return 1

    # render the full PDF through the front-door (vector, CairoSVG)
    from frameforge.cli import main as render_cli
    rc = render_cli([yaml_out, "--to", "pdf", "--out", out_dir])
    print(f"PDF render exit={rc} → {out_dir}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
