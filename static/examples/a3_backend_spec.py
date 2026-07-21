import math
from frameforge.sdk import DocumentBuilder
from frameforge.sdk.paint import stroke

def S(w, c):
    return stroke(w, color=c)

# ---------- canvas ----------
W, H = 1123, 1587          # A3 @ 96dpi, portrait
M = 52
CW = W - 2 * M

# ---------- closed palette ----------
PAPER  = "#F6F2EA"
INK    = "#2A2620"
GREY   = "#6B6459"
FAINT  = "#9A9184"
LINE   = "#DCD4C4"
GUIDE  = "#C9C0AE"
CARDBG = "#FBF8F1"
RED    = "#A63D2F"
REDTINT= "#F0E0DA"
AMBER  = "#C9A227"

SERIF = "EB Garamond"
SANS  = "Fira Sans"
SANSM = "Fira Sans Medium"
SANSSB= "Fira Sans SemiBold"
MONO  = "Fira Mono"
MONOM = "Fira Mono Medium"

doc = DocumentBuilder(title="Adequate Backend Specification v2.0.0 - A3 infographic", profile="diagram")

def ts(name, **kw):
    return doc.define_text_style(name, **kw)

LNUM = {"font_variant_numeric": "lining-nums"}
st_kicker  = ts("kicker",  font_family=SANSSB, font_size=9.5, color=RED,  letter_spacing=2.2, text_transform="uppercase")
st_title   = ts("title",   font_family=SERIF,  font_size=60,  color=INK)
st_sub     = ts("sub",     font_family=SANS,   font_size=12.5,color=GREY, line_height=1.45)
st_slug_ink= ts("slugink", font_family=SANSSB, font_size=9.5, color=INK,  letter_spacing=1.6, text_transform="uppercase")
st_slug_red= ts("slugred", font_family=SANSSB, font_size=9.5, color=RED,  letter_spacing=1.6, text_transform="uppercase")
st_body    = ts("body",    font_family=SANS,   font_size=9.5, color=GREY, line_height=1.45)
st_body_ink= ts("bodyink", font_family=SANS,   font_size=9.5, color=INK,  line_height=1.45)
st_cardline= ts("cardline",font_family=SANS,   font_size=9.5, color=INK,  line_height=1.3)
st_marker  = ts("marker",  font_family=SANSSB, font_size=9.5, color=RED)
st_mono    = ts("mono",    font_family=MONO,   font_size=10.5,color=INK)
st_mono_med= ts("monomed", font_family=MONOM,  font_size=12.5,color=INK)
st_formula = ts("formula", font_family=MONOM,  font_size=14,  color=INK)
st_enum    = ts("enum",    font_family=MONO,   font_size=6.5, color=GREY, line_height=1.3)
st_stat    = ts("stat",    font_family=SERIF,  font_size=26,  color=INK,  text_align="center", **LNUM)
st_stat_red= ts("statred", font_family=SERIF,  font_size=26,  color=RED,  text_align="center", **LNUM)
st_statlab = ts("statlab", font_family=SANSM,  font_size=6.5, color=GREY, letter_spacing=1.0, text_transform="uppercase", text_align="center")
st_num     = ts("num",     font_family=SERIF,  font_size=22,  color=RED,  **LNUM)
st_authtl  = ts("authtl",  font_family=SANSSB, font_size=10.5,color=INK,  letter_spacing=1.0, text_transform="uppercase")
st_authdt  = ts("authdt",  font_family=SANS,   font_size=8.5, color=GREY, line_height=1.35)
st_nodelet = ts("nodelet", font_family=SERIF,  font_size=22,  color=INK,  text_align="center")
st_nodelab = ts("nodelab", font_family=MONO,   font_size=8.5, color=INK,  text_align="center")
st_count   = ts("count",   font_family=SANSM,  font_size=6.5, color=FAINT, letter_spacing=0.8, text_transform="uppercase", text_align="center")
st_ctr     = ts("ctr",     font_family=SERIF,  font_size=39,  color=PAPER,text_align="center")
st_ctrcap  = ts("ctrcap",  font_family=SANSM,  font_size=7.5, color=PAPER,letter_spacing=1.2, text_transform="uppercase", text_align="center")
st_cardlet = ts("cardlet", font_family=SERIF,  font_size=26,  color=INK)
st_chip_id_l = ts("chipidl", font_family=SANSSB, font_size=10.5, color=PAPER, text_align="center")
st_chip_id_d = ts("chipidd", font_family=SANSSB, font_size=10.5, color=INK,   text_align="center")
st_chip_kw_l = ts("chipkwl", font_family=SANS,   font_size=6.5, color="#D9D2C6", text_align="center")
st_chip_kw_d = ts("chipkwd", font_family=SANS,   font_size=6.5, color="#54503F", text_align="center")
st_chip_mono = ts("chipmono",font_family=MONO,   font_size=8.5,  color=INK,  text_align="center")
st_chip_mono_red = ts("chipmonored", font_family=MONOM, font_size=8.5, color=RED, text_align="center")
st_panel_tl= ts("paneltl", font_family=SANSSB, font_size=9.5, color=INK)
st_panel_bd= ts("panelbd", font_family=SANS,   font_size=8.5, color=GREY, line_height=1.3)
st_state   = ts("state",   font_family=MONO,   font_size=8.5, color=INK,  text_align="center")
st_state_t = ts("statet",  font_family=MONOM,  font_size=8.5, color=INK,  text_align="center")
st_edge    = ts("edge",    font_family=SANS,   font_size=7.5, color=GREY)
st_edge_c  = ts("edgec",   font_family=SANS,   font_size=7.5, color=GREY, text_align="center")
st_edge_red= ts("edgered", font_family=SANSSB, font_size=7.5, color=RED)
st_tlver   = ts("tlver",   font_family=SANSSB, font_size=10.5,color=INK,  text_align="center")
st_tlver_r = ts("tlverr",  font_family=SANSSB, font_size=10.5,color=RED,  text_align="center")
st_tldate  = ts("tldate",  font_family=SANSM,  font_size=6.5, color=FAINT,letter_spacing=0.8, text_transform="uppercase", text_align="center")
st_tlnote  = ts("tlnote",  font_family=SANS,   font_size=7.5, color=GREY, line_height=1.3, text_align="center")
st_bar_lab = ts("barlab",  font_family=SANS,   font_size=6.5, color=GREY)
st_foot    = ts("foot",    font_family=SANS,   font_size=7.5, color=GREY)
st_footr   = ts("footr",   font_family=SANS,   font_size=7.5, color=GREY, text_align="right")
st_legend  = ts("legend",  font_family=SANS,   font_size=7.5, color=GREY)
st_ruler   = ts("ruler",   font_family=MONO,   font_size=6.5, color=FAINT)
st_sect_num= ts("sectnum", font_family=SANSSB, font_size=10.5,color=PAPER, text_align="center")
st_sect_tl = ts("secttl",  font_family=SANSSB, font_size=12.5,color=INK,  letter_spacing=1.5, text_transform="uppercase")
st_seal_v  = ts("sealv",   font_family=SERIF,  font_size=26,  color=RED,  text_align="center", **LNUM)
st_seal_s  = ts("seals",   font_family=SANSSB, font_size=6.5, color=INK,  letter_spacing=1.1, text_transform="uppercase", text_align="center")
st_hk      = ts("hk",      font_family=MONO,   font_size=8.5, color=INK)
st_hv_ok   = ts("hvok",    font_family=SANSM,  font_size=7.5, color=GREY, text_align="right")
st_hv_no   = ts("hvno",    font_family=SANSSB, font_size=7.5, color=RED,  text_align="right")
st_era     = ts("era",     font_family=SANSM,  font_size=7.5, color=FAINT, letter_spacing=0.8, text_transform="uppercase", text_align="right", line_height=1.3)
st_swatch  = ts("swatch",  font_family=MONO,   font_size=6.5, color=FAINT, text_align="center")

page = doc.page("poster", canvas={"size": [W, H], "units": "px", "background": PAPER}, coordinate_mode="absolute")
bg  = page.layer("bg")
art = page.layer("art")
txt = page.layer("txt")

def hline(y, x1=M, x2=W - M, color=LINE, w=1):
    art.line([x1, y], [x2, y], **S(w, color))

def arrow(p1, p2, color=INK, w=1.1, dash=None):
    if dash:
        art.line([p1[0], p1[1]], [p2[0], p2[1]], style={"stroke_dasharray": dash}, **S(w, color))
    else:
        art.line([p1[0], p1[1]], [p2[0], p2[1]], **S(w, color))
    ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    L = 5.5
    a1, a2 = ang + math.radians(153), ang - math.radians(153)
    art.polygon([[p2[0], p2[1]],
                 [p2[0] + L * math.cos(a1), p2[1] + L * math.sin(a1)],
                 [p2[0] + L * math.cos(a2), p2[1] + L * math.sin(a2)]], fill=color)

def sect(y, num, title, extra=None, ex_x=380):
    art.rect([M, y, 18, 18], fill=RED)
    txt.text([M, y + 3, 18, 12], num, style=st_sect_num)
    txt.text([M + 26, y + 4, 340, 14], title, style=st_sect_tl)
    if extra:
        txt.text([M + ex_x, y + 5, W - M - (M + ex_x), 12], extra, style=st_body)
    art.line([M, y + 26], [W - M, y + 26], **S(1, LINE))

# =========================================================== drafting chrome
for cx, cy, dx, dy in [(M, 20, 0, 1), (20, M, 1, 0), (W - M, 20, 0, 1), (W - 20, M, 1, 0),
                       (M, H - 20, 0, -1), (20, H - M, 1, 0), (W - M, H - 20, 0, -1), (W - 20, H - M, 1, 0)]:
    if dx:
        art.line([cx, cy], [cx + dx * 14, cy], **S(0.8, INK))
    else:
        art.line([cx, cy], [cx, cy + dy * 14], **S(0.8, INK))
for x in range(M, W - M + 1, 25):
    big = (x - M) % 100 == 0
    art.line([x, 34], [x, 34 + (7 if big else 3)], **S(0.7, GUIDE))
    if big:
        txt.text([x - 14, 24, 28, 8], str(x - M), style=st_ruler)
for y in range(M, 1536, 25):
    big = (y - M) % 100 == 0
    art.line([34, y], [34 + (7 if big else 3), y], **S(0.7, GUIDE))
    if big:
        txt.text([8, y - 4, 24, 8], str(y - M), style=st_ruler)

# =========================================================== masthead
hexr = 7
hx, hy = M + hexr, 51
hpts = [[hx + hexr * math.cos(math.radians(-90 + i * 60)), hy + hexr * math.sin(math.radians(-90 + i * 60))] for i in range(6)]
art.polygon(hpts, fill=RED)
txt.text([M + 22, 46, 780, 16], "An adequate specification set for general backend generation", style=st_kicker)
txt.text([M, 64, 850, 78], "Adequate Backend Specification", style=st_title)
txt.text([M, 150, 520, 58],
         "A spec instance is adequate when every choice a generator must make is fixed "
         "by the spec (contract) or by the profile (convention). The generator may add "
         "nothing observable. v2.0.0 makes the corpus platform declarable.", style=st_sub)

SCX, SCY = 982, 106
art.circle([SCX, SCY], 55, fill=CARDBG, **S(1.6, RED))
art.circle([SCX, SCY], 44, fill=CARDBG, **S(1, RED))
for i in range(24):
    a = math.radians(i * 15)
    art.line([SCX + 47 * math.cos(a), SCY + 47 * math.sin(a)],
             [SCX + 52 * math.cos(a), SCY + 52 * math.sin(a)], **S(1, RED))
txt.text([SCX - 40, SCY - 32, 80, 10], "Schema on disk", style=st_seal_s)
txt.text([SCX - 44, SCY - 17, 88, 30], "v2.0.0", style=st_seal_v)
txt.text([SCX - 42, SCY + 12, 84, 9], "Release candidate", style=st_seal_s)
txt.text([SCX - 42, SCY + 23, 84, 9], "Ajv-verified", style=st_seal_s)

# =========================================================== authority chain
AY = 212
auth = [
    ("1", "The schema", "backend_spec.schema.v2.0.0.json — JSON Schema 2020-12, additionalProperties: false, Ajv-verified. Where prose disagrees, the schema wins."),
    ("2", "The framework", "This document — axis semantics, closure laws L1-L42, the severity model, and 31 breaking-change recipes."),
    ("3", "The fixture", "doc_ray.v2_0_0.spec.json — the attached adequate example, exercising the v2.0.0 surface end to end."),
]
colw = (CW - 2 * 40) / 3.0
for i, (n, t, d) in enumerate(auth):
    x = M + i * (colw + 40)
    txt.text([x, AY, 20, 26], n, style=st_num)
    txt.text([x + 26, AY + 3, colw - 26, 14], t, style=st_authtl)
    txt.text([x + 26, AY + 18, colw - 26, 40], d, style=st_authdt)
    if i > 0:
        arrow([x - 32, AY + 12], [x - 8, AY + 12], color=GUIDE, w=1.1)
hline(276)

# =========================================================== conjecture + stats
CJY = 290
art.rect([M, CJY, 620, 96], fill=CARDBG, **S(1.5, INK))
txt.text([M + 18, CJY + 11, 580, 14], "The completeness conjecture", style=st_slug_red)
txt.text([M + 18, CJY + 32, 590, 20], "adequate(S)  =  D O B I X N populated  +  laws L1-L42 hold", style=st_formula)
txt.text([M + 18, CJY + 58, 586, 32],
         "Still a conjecture, still falsifiable. The doc-ray audit was the first systematic "
         "falsification attempt against a production system — it succeeded, and v2.0.0 is the repair.",
         style=st_body)

stats = [("6", "axes", st_stat), ("42", "closure laws", st_stat), ("35", "fatal laws", st_stat), ("31", "breaking changes", st_stat),
         ("12", "primitive types", st_stat), ("16", "operation kinds", st_stat), ("16", "wire formats", st_stat), ("17%", "faithful coverage", st_stat_red)]
sx0, sy0, scw, sch = 694, CJY + 2, (W - M - 694) / 4.0, 47
for i, (n, lab, sty) in enumerate(stats):
    x = sx0 + (i % 4) * scw
    y = sy0 + (i // 4) * sch
    txt.text([x, y, scw, 28], n, style=sty)
    txt.text([x, y + 30, scw, 10], lab, style=st_statlab)
art.line([sx0 + 8, sy0 + sch - 2], [W - M - 8, sy0 + sch - 2], **S(1, LINE))

# =========================================================== 01 - instance shape
sect(402, "01", "The instance shape", "seven required properties · six axes · one closure web")

CX, CY, R = 238, 682, 128
axes6 = [("D", "data_model", 21), ("O", "operations", 31), ("B", "behavior", 15),
         ("I", "interface", 18), ("X", "cross_cutting", 14), ("N", "non_functional", 14)]
pts = []
for i in range(6):
    a = math.radians(-90 + i * 60)
    pts.append((CX + R * math.cos(a), CY + R * math.sin(a)))
for i in range(6):
    for j in range(i + 1, 6):
        art.line([pts[i][0], pts[i][1]], [pts[j][0], pts[j][1]], **S(1, LINE))
for p in pts:
    art.line([CX, CY], [p[0], p[1]], **S(1, GUIDE))
art.circle([CX, CY], 52, fill=INK)
txt.text([CX - 40, CY - 30, 80, 44], "S", style=st_ctr)
txt.text([CX - 48, CY + 12, 96, 12], "spec instance", style=st_ctrcap)
NR = 26
for k, (letter, name, cnt) in enumerate(axes6):
    px, py = pts[k]
    art.circle([px, py], NR, fill=CARDBG, **S(1.5, INK))
    txt.text([px - 30, py - 15, 60, 32], letter, style=st_nodelet)
    a = math.radians(-90 + k * 60)
    lx = CX + (R + NR + 15) * math.cos(a)
    ly = CY + (R + NR + 15) * math.sin(a)
    txt.text([lx - 60, ly - 7, 120, 12], name, style=st_nodelab)
    txt.text([lx - 60, ly + 6, 120, 10], "%d laws" % cnt, style=st_count)

txt.text([M, 876, 358, 30],
         "Six axes + spec_meta = the seven required top-level properties. The web is the "
         "closure: laws bind every cross-axis reference — nothing dangles, nothing is silent.",
         style=st_body)
txt.text([M, 914, 358, 26],
         "spec_meta: framework_version \"2.0.0\" (const) · generated_by required · predecessor -> migration_notes · rule_grammar.computability{terminates, bounded_inputs}",
         style=st_enum)

# ---- axis cards ----
cards = [
    ("D", "data_model",
     [("+", "vector · json · blob_ref primitives (12 base types)"),
      ("+", "indexes: hnsw · ivfflat, with declared distance"),
      ("+", "derived_relations · graphs: tree / dag / reentrant"),
      ("+", "trust tiers — model_asserted needs a verification gate")],
     "base: decimal integer string boolean binary datetime date time duration vector json blob_ref"),
    ("O", "operations",
     [("D", "target{aggregate·corpus·system·none} ends target_aggregate"),
      ("+", "async_job -> job + eventual_effect (anti-degenerate, L37)"),
      ("+", "job_contracts · pipelines · tools (MCP) · schedules"),
      ("+", "ModelCall — pinned, budgeted, gated (L40) · batch semantics")],
     "kind: command query subscription event scheduled_job webhook_receiver internal_task migration_operation administrative_operation tool pipeline_stage batch job_control synthesis export render"),
    ("B", "behavior",
     [("D", "terminal_states + cancel{legal_from} now required"),
      ("+", "timed triggers: timer · elapsed_since_heartbeat · schedule"),
      ("+", "lease_contracts — claim · heartbeat · reap · drain (L41)"),
      ("+", "dual_writes with orphan_policy · compensation required")],
     "dual_write: outbox change_data_capture two_phase_commit best_effort compensating_action · compensation: none_by_design idempotent_replacement reaper_requeue failure_as_record"),
    ("I", "interface",
     [("+", "transports: mcp · stdio · db_channel (11 kinds)"),
      ("+", "16 wire formats · per-direction bindings (L36)"),
      ("D", "error_envelopes — plural, one per transport"),
      ("·", "auth_topology · impersonation · 10 validation phases")],
     "wire: json xml avro protobuf msgpack cbor yaml multipart_form_data form_urlencoded octet_stream csv text_plain event_stream image gzip custom"),
    ("X", "cross_cutting",
     [("D", "models[] composed · enforcement_locus: database_rls"),
      ("+", "model_governance — output trust const \"untrusted\""),
      ("+", "embedding_spaces · verification_gates · budgets"),
      ("+", "provenance ledger · extraction-aware PII (L39)")],
     "authz: rbac abac rebac policy_engine · trust: deterministic reproducible model_asserted · gate on_fail: reject route_to_review"),
    ("N", "non_functional",
     [("D", "stores[] — one polystore, declared roles (L35)"),
      ("+", "role_partitioned_monolith + deployables[]"),
      ("+", "accelerators — VRAM budgets, CDI · model_serving"),
      ("+", "SLOs with epistemic_status · timeout_budgets")],
     "roles: relational vector_index full_text_search queue event_bus object_store model_weights cache session_store · engines: postgres s3_compatible filesystem in_memory custom"),
]
CDX, CDY, CDW, CDH, CGX, CGY2 = 432, 430, 312, 152, 15, 14
for idx, (letter, name, lines, enum) in enumerate(cards):
    col, row = idx % 2, idx // 2
    x = CDX + col * (CDW + CGX)
    y = CDY + row * (CDH + CGY2)
    art.rect([x, y, CDW, CDH], fill=CARDBG, **S(1, LINE))
    art.rect([x, y, 3, CDH], fill=INK)
    txt.text([x + 14, y + 6, 30, 32], letter, style=st_cardlet)
    txt.text([x + 44, y + 15, CDW - 60, 18], name, style=st_mono_med)
    art.line([x + 14, y + 40], [x + CDW - 14, y + 40], **S(1, LINE))
    for li, (mk, line) in enumerate(lines):
        ly = y + 47 + li * 19
        mchar = {"+": "+", "D": "Δ", "·": "·"}[mk]
        txt.text([x + 14, ly, 12, 12], mchar, style=(st_marker if mk != "·" else st_body))
        txt.text([x + 27, ly + 1, CDW - 41, 19], line, style=st_cardline)
    art.line([x + 14, y + 119], [x + CDW - 14, y + 119], **S(0.8, LINE))
    txt.text([x + 14, y + 122, CDW - 28, 28], enum, style=st_enum)

txt.text([CDX, 934, 640, 14],
         "+ new in v2.0.0     Δ breaking change (31 in all, each with a recipe — §11)     · carried from v1.1.0",
         style=st_legend)

# =========================================================== 02 - time in the model
sect(960, "02", "Time is in the model", "the Job machine, fully declared — triggers, guards, leases, reapers")

def state(x, y, w, label, terminal=False):
    art.rect([x, y, w, 24], fill=CARDBG, **S(1.3, INK))
    if terminal:
        art.rect([x + 3, y + 3, w - 6, 18], fill="none", **S(0.8, INK))
    txt.text([x, y + 6, w, 12], label, style=(st_state_t if terminal else st_state))
    return (x, y, w, 24)

Q = state(64, 1046, 72, "queued")
Rn = state(236, 1046, 76, "running")
Sc = state(430, 1004, 96, "succeeded", terminal=True)
F = state(430, 1088, 72, "failed")
C = state(600, 1046, 90, "canceled", terminal=True)

arrow([136, 1058], [236, 1058])
txt.text([140, 1044, 96, 10], "claim · skip_locked", style=st_edge)
arrow([312, 1052], [430, 1022])
txt.text([352, 1018, 80, 10], "done", style=st_edge)
arrow([312, 1064], [430, 1094])
txt.text([340, 1090, 92, 10], "error / timeout", style=st_edge)
art.line([466, 1112], [466, 1128], **S(1.1, INK))
art.line([466, 1128], [100, 1128], **S(1.1, INK))
arrow([100, 1128], [100, 1072], color=INK)
txt.text([150, 1132, 220, 10], "retry · guard: attempts < max_attempts", style=st_edge)
art.line([274, 1046], [274, 1016], style={"stroke_dasharray": [5, 4]}, **S(1.4, RED))
art.line([274, 1016], [100, 1016], style={"stroke_dasharray": [5, 4]}, **S(1.4, RED))
arrow([100, 1016], [100, 1044], color=RED, w=1.4, dash=[5, 4])
txt.text([112, 1002, 260, 10], "reaper · elapsed_since_heartbeat > stale_after (L38 · L41)", style=st_edge_red)
art.circle([190, 1016], 7, fill=PAPER, **S(1.2, RED))
art.line([190, 1016], [190, 1011.5], **S(1.1, RED))
art.line([190, 1016], [193.5, 1017.5], **S(1.1, RED))
arrow([312, 1058], [600, 1058])
txt.text([408, 1044, 190, 10], "cancel · legal_from declared", style=st_edge_c)

TXC = 726
txt.text([TXC, 992, 200, 12], "transition.trigger.kind", style=st_slug_ink)
trig = [("command", False, 76), ("event", False, 56), ("timer", True, 56),
        ("schedule", True, 76), ("elapsed_since_heartbeat", True, 156)]
tx, tyy = TXC, 1012
for name, is_new, wch in trig:
    if tx + wch > W - M:
        tx = TXC
        tyy += 30
    fill = REDTINT if is_new else PAPER
    border = RED if is_new else GUIDE
    style = st_chip_mono_red if is_new else st_chip_mono
    art.rect([tx, tyy, wch, 22], fill=fill, **S(1, border))
    txt.text([tx, tyy + 5, wch, 12], name, style=style)
    tx += wch + 8
txt.text([TXC, 1076, 330, 14], "guard = { rule · counters · lease_condition }", style=st_mono)
txt.text([TXC, 1094, 330, 26],
         "Every clock-driven edge names its clock_field (L42). Heartbeats get a dedicated connection — shared ones deadlock under long transactions.",
         style=st_panel_bd)

# =========================================================== 03 - law wall
sect(1152, "03", "Closure laws L1-L42", "adequacy = well-formedness + the laws, at declared severities")

SEV = {}
for i in range(1, 16): SEV[i] = "fatal"
SEV[16] = "advisory"; SEV[17] = "fatal"; SEV[18] = "unsafe"
for i in range(19, 26): SEV[i] = "fatal"
SEV[26] = "unsafe"; SEV[27] = "unsafe"
for i in range(28, 34): SEV[i] = "fatal"
SEV[34] = "unsafe"
for i in range(35, 41): SEV[i] = "fatal"
SEV[41] = "unsafe"; SEV[42] = "unsafe"
KW = {1:"unique names",2:"typeref",3:"cmd target",4:"query target",5:"triggers",6:"state values",
      7:"rule grammar",8:"op bound",9:"errors known",10:"http codes",11:"authz refs",12:"tenancy",
      13:"saga refs",14:"events known",15:"config keys",16:"dialect",17:"pii redaction",18:"versioning",
      19:"synth errors",20:"unsupported",21:"4xx/5xx only",22:"webhook evts",23:"valid. phases",24:"dual-write",
      25:"presence",26:"index closure",27:"slo metrics",28:"secrets",29:"breaking mig",30:"tenant filter",
      31:"money fields",32:"vector space",33:"trust gates",34:"derived rels",35:"store roles",36:"media types",
      37:"eventual fx",38:"machines",39:"pii extract",40:"model budget",41:"lease closure",42:"clock closure"}
DEFECT = {37, 38, 39, 40}

GX0, GY0, CHW, CHH, GGX, GGY = 134, 1188, 64, 34, 4, 4
rows = [("v1.0.0", list(range(1, 10))), ("", list(range(10, 19))),
        ("v1.1.0 + shipped", list(range(19, 23))), ("v1.2.0 shifted", list(range(23, 32))),
        ("v2.0.0", list(range(32, 41))), ("", [41, 42])]
for r, (era, ids) in enumerate(rows):
    y = GY0 + r * (CHH + GGY)
    if era:
        txt.text([M - 6, y + 4, 80, 28], era, style=st_era)
    for c, lid in enumerate(ids):
        x = GX0 + c * (CHW + GGX)
        sev = SEV[lid]
        if sev == "fatal":
            art.rect([x, y, CHW, CHH], fill=INK)
            i_st, k_st = st_chip_id_l, st_chip_kw_l
        elif sev == "unsafe":
            art.rect([x, y, CHW, CHH], fill=AMBER)
            i_st, k_st = st_chip_id_d, st_chip_kw_d
        else:
            art.rect([x, y, CHW, CHH], fill=PAPER, **S(1, "#B9B09E"))
            i_st, k_st = st_chip_id_d, st_chip_kw_d
        if lid in DEFECT:
            art.rect([x - 2.5, y - 2.5, CHW + 5, CHH + 5], fill="none", **S(1.8, RED))
        txt.text([x, y + 4, CHW, 12], "L%d" % lid, style=i_st)
        txt.text([x, y + 19, CHW, 10], KW[lid], style=k_st)

LGY = GY0 + 5 * (CHH + GGY)
lx = GX0 + 2 * (CHW + GGX) + 14
art.rect([lx, LGY, 13, 9], fill=INK)
txt.text([lx + 17, LGY, 200, 10], "fatal (35) — generation stops", style=st_legend)
art.rect([lx, LGY + 13, 13, 9], fill=AMBER)
txt.text([lx + 17, LGY + 13, 260, 10], "unsafe (6) — accept_unsafe + UNSAFE_VIOLATIONS.md", style=st_legend)
lx2 = lx + 268
art.rect([lx2, LGY, 13, 9], fill=PAPER, **S(1, "#B9B09E"))
txt.text([lx2 + 17, LGY, 160, 10], "advisory (1) — reported", style=st_legend)
art.rect([lx2, LGY + 13, 13, 9], fill="none", **S(1.8, RED))
txt.text([lx2 + 17, LGY + 13, 280, 10], "red ring — written against a defect that shipped", style=st_legend)
txt.text([lx, LGY + 27, 470, 10],
         "A profile may never downgrade fatal. Sole exception: L17 (PII redaction), only under regulated_context: none.",
         style=st_legend)

PX, PY, PW, PH = 760, 1188, 311, 5 * (34 + 4) + 34
art.rect([PX, PY, PW, PH], fill=CARDBG, **S(1, LINE))
art.rect([PX, PY, PW, 3], fill=RED)
txt.text([PX + 14, PY + 10, PW - 28, 14], "Born from shipped defects", style=st_slug_red)
panel = [
    ("L37 — the eventual effect", "An async command must name its domain effect. “create Job” is the mechanism — a green check that erases the domain."),
    ("L38 — complete machines", "Every status column binds to one machine; reaper and retry edges declared. SQL-string transitions are undeclared behaviour."),
    ("L39 — phantom redaction", "implemented_by: UNIMPLEMENTED is legal syntax that fails the law — the missing operation surfaces, it cannot hide."),
    ("L40 — model-call closure", "Pinned version, timeout, retry, budget. Unbudgeted calls mean unbounded spend on a flat subscription."),
]
py = PY + 30
for t, d in panel:
    txt.text([PX + 14, py, PW - 28, 12], t, style=st_panel_tl)
    txt.text([PX + 14, py + 12, PW - 28, 24], d, style=st_panel_bd)
    py += 38
txt.text([PX + 14, py + 2, PW - 28, 30], "All four are fatal by design — each corresponds to a defect that shipped.", style=st_body_ink)

# =========================================================== 04 - lineage, scope, posture
hline(1418)

TLX, TLY, TLW = M, 1428, 480
tl_y = TLY + 52
art.line([TLX + 14, tl_y], [TLX + TLW - 6, tl_y], **S(1.5, GUIDE))
timeline = [
    ("v1.0.0", "", "six axes, L1-L18", False, False),
    ("v1.1.0", "2026-04-25", "schema authored; L19-L21", False, False),
    ("v1.2.0", "2026-04-28", "draft only — schema never authored", False, False),
    ("audit", "2026-07-20", "", True, False),
    ("v2.0.0", "2026-07-20", "RC — Ajv-verified; L32-L42", False, True),
]
n = len(timeline)
for i, (ver, date, note, is_audit, is_now) in enumerate(timeline):
    x = TLX + 40 + i * ((TLW - 80) / (n - 1.0))
    if is_audit:
        art.circle([x, tl_y], 6, fill=RED)
    elif is_now:
        art.circle([x, tl_y], 6, fill=INK)
    else:
        art.circle([x, tl_y], 4.5, fill=PAPER, **S(1.5, INK))
    above = (i % 2 == 0)
    if is_audit:
        # ver+date below, coverage bars above (kept inside this stop's own lane)
        txt.text([x - 52, tl_y + 11, 104, 12], ver, style=st_tlver_r)
        txt.text([x - 52, tl_y + 24, 104, 9], date, style=st_tldate)
        txt.text([x - 52, tl_y - 44, 104, 10], "doc-ray coverage", style=st_bar_lab)
        art.rect([x - 50, tl_y - 30, 46, 4], fill=LINE)
        art.rect([x - 50, tl_y - 30, 18.4, 4], fill=AMBER)
        txt.text([x - 1, tl_y - 33, 56, 9], "40% descr.", style=st_bar_lab)
        art.rect([x - 50, tl_y - 19, 46, 4], fill=LINE)
        art.rect([x - 50, tl_y - 19, 7.8, 4], fill=RED)
        txt.text([x - 1, tl_y - 22, 56, 9], "17% faithful", style=st_bar_lab)
    elif above:
        txt.text([x - 52, tl_y - 44, 104, 12], ver, style=st_tlver)
        txt.text([x - 52, tl_y - 31, 104, 9], date, style=st_tldate)
        txt.text([x - 52, tl_y + 11, 104, 30], note, style=st_tlnote)
    else:
        txt.text([x - 52, tl_y + 11, 104, 12], ver, style=st_tlver)
        txt.text([x - 52, tl_y + 24, 104, 9], date, style=st_tldate)
        txt.text([x - 52, tl_y - 44, 104, 30], note, style=st_tlnote)
txt.text([TLX, TLY + 98, TLW, 12],
         "A framework version is not real until its schema is on disk and loads under the validator.",
         style=st_legend)

SPX, SPY, SPW = 564, 1428, 240
txt.text([SPX, SPY, SPW, 12], "Scope — now declarable", style=st_slug_ink)
scope_lines = ["vector search & embedding spaces",
               "NLP annotation graphs — trees, DAGs, reentrancy",
               "job pipelines — leases, heartbeats, reapers",
               "model-calling ops — pinned, budgeted, gated"]
for i, s in enumerate(scope_lines):
    yy = SPY + 18 + i * 17
    art.rect([SPX, yy + 4, 6, 6], fill=RED)
    txt.text([SPX + 13, yy, SPW - 13, 16], s, style=st_cardline)
txt.text([SPX, SPY + 90, SPW, 28],
         "Still out: game servers, embedded firmware, HPC, distributed databases as systems-under-construction.",
         style=st_panel_bd)

HPX, HPY, HPW = 826, 1428, 245
txt.text([HPX, HPY, HPW, 12], "Silence is not an option", style=st_slug_ink)
honest = [("compensation: none_by_design", "legal + rationale"),
          ("token accounting: none_declared", "legal"),
          ("content_rights: none", "legal"),
          ("redaction: UNIMPLEMENTED", "fails L39")]
for i, (k, v) in enumerate(honest):
    yy = HPY + 18 + i * 17
    txt.text([HPX, yy + 1, HPW - 84, 12], k, style=st_hk)
    txt.text([HPX + HPW - 92, yy + 1, 92, 12], v, style=(st_hv_no if "fails" in v else st_hv_ok))
    art.line([HPX, yy + 13, ], [HPX + HPW, yy + 13], **S(0.6, LINE))
txt.text([HPX, HPY + 90, HPW, 28],
         "The framework mandates the declaration, never the mechanism. Declared nothing is legal; silence is not.",
         style=st_panel_bd)

# =========================================================== footer + colophon
hline(1550, color=LINE)
txt.text([56, 1558, 420, 12],
         "backend_spec_v2_0_0.md · super-services-belt · schema: static/schemas/backend_spec.schema.v2.0.0.json",
         style=st_foot)
sw_x = 512
for i, (c, name) in enumerate([(PAPER, "F6F2EA"), (INK, "2A2620"), (GREY, "6B6459"), (RED, "A63D2F"), (AMBER, "C9A227")]):
    x = sw_x + i * 42
    art.rect([x + 8, 1556, 10, 10], fill=c, **S(0.7, GUIDE))
    txt.text([x, 1568, 26, 9], name, style=st_swatch)
txt.text([736, 1558, 331, 12],
         "Generated by Claude via Claude Code · 2026-07-20 · LLM output is unverified by default",
         style=st_footr)

doc.write(OUTPUT_YAML_PATH, fail_on_error=True)
