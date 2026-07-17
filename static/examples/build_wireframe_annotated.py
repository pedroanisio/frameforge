"""FrameForge authoring-IDE wireframe — on ruler paper. FrameForge SDK widgets."""
import math as m, os
from frameforge.sdk import (DocumentBuilder, PageBuilder, Mat3, serialize, default_theme,
                            register_theme, card, tabs, checkbox, avatar, image_placeholder,
                            field, badge, button, pill, measure_text)
from frameforge.sdk.validate import validate_static_rules

OUT="/home/admin/github-mirror/_apis/api-pdf2text/research/fg"
TH=default_theme(); gt=lambda n,d: getattr(TH,n,d)
INK=TH.ink; MUTE=TH.muted; ACC=TH.accent; LN=TH.line; SURF=TH.surface; ALT=TH.surface_alt
GOOD=gt("good","#2E9E5B"); WARN=gt("warn","#C98A2B"); RED="#E5484D"
LINE="#CBD2DC"; LINE2="#DDE2EA"; ACCSOFT="#EAF1FF"; SEL="#EEF3FE"
DESK="#262019"; RUL="#EDE7DA"; TICK="#9A9282"; TICKN="#8B8373"; GRIDF="#3341550D"
# --- The Letter & the Hue: closed palette + modular scale ---
PAPER="#FCFBF8"; BINK="#22211C"; MUTE="#6E685E"; FAINT="#8E8879"; RULE="#E4E0D6"; RUST="#A8432E"; CREAM="#B7AF9F"
SERIF=["Charter","Bitstream Charter","Georgia","serif"]
def sz(k,base=10.5,r=1.25): return round(base*(r**k),1)
W,H=1440,900                     # wireframe (measured) size
RM=30                            # ruler thickness (top + left)
PADR,PADB=16,16                  # cream margin between app and paper edge
BX=BY=46                         # warm-dark desk frame around the ruler paper
PW,PH=RM+W+PADR, RM+H+PADB       # ruler-paper block
OX,OY=BX+RM,BY+RM                # app origin, on the paper
W2,H2=BX*2+PW, BY*2+PH           # full canvas incl. desk

b=DocumentBuilder(title="FrameForge IDE — annotated wireframe + spec", profile="deck", lang="en")
register_theme(b)
pg=b.page("ide", canvas={"size":[W2,H2],"units":"px"}, coordinate_mode="absolute")
p=pg.layer("paper")
p.rect([0,0,W2,H2], fill=DESK)                                   # warm-dark desk (echoes the book cover ground)
p.rect([BX,BY,PW,PH], fill=RUL, radius=3, shadow={"dx":0,"dy":6,"blur":26,"color":"#00000055"})  # ruler paper floats on the desk
p.rect([OX,OY,W,H], fill=ALT, shadow={"dx":0,"dy":2,"blur":12,"color":"#0F172A1E"})              # wireframe page on the ruler paper

# ---- all app drawing goes into this detached group, later translated onto the paper ----
G=PageBuilder({"layers":[]}).layer("_app"); ui=G

def txt(x,y,w,s,*,size=13,color=INK,weight=None,mono=False,align=None):
    st={"font_family":(TH.mono if mono else TH.font),"font_size":size,"color":color}
    if weight: st["font_weight"]=weight
    if align: st["text_align"]=align
    ui.text([x,y,w,size*1.5], s, style=st)
def lines(x,y,w,n,*,gap=13,h=5,widths=None,col=LINE):
    for i in range(n): ui.rect([x,y+i*gap,max(8,w*(widths[i] if widths else 1.0)),h], fill=col, radius=2)
def panel(box,title=None,action=None):
    pn=card(box,title=title,action=action,theme=TH); ui.add(pn.object); return pn.content
def sh(box,r=12): ui.rect(box, fill=SURF, stroke=LN, stroke_style={"stroke_width":1}, radius=r,
                          shadow={"dx":0,"dy":2,"blur":10,"color":"#0F172A14"})
def check(cx,cy,col=GOOD):
    ui.circle([cx,cy],8,fill=col)
    ui.path([("M",cx-3.4,cy),("L",cx-1,cy+2.6),("L",cx+3.6,cy-2.8)],
            stroke=SURF, stroke_style={"stroke_width":1.6,"stroke_linecap":"round"}, fill="none")
def lock(x,y,col=MUTE):
    ui.circle([x+4,y+1.5],3.2,fill="none",stroke=col,stroke_style={"stroke_width":1.3})
    ui.rect([x,y+2,8,7],fill=col,radius=1.5)
def squiggle(x,y,w,col=RED):
    st=4; n=int(w//st)
    pts=[(x+i*st, y+(2.4 if i%2 else 0)) for i in range(n+1)]
    ui.path([("M",pts[0][0],pts[0][1])]+[("L",q[0],q[1]) for q in pts[1:]],
            stroke=col, stroke_style={"stroke_width":1.2}, fill="none")
def mtabs(x,y,items,active,*,lock_idx=None,warn_idx=None):
    ui.rect([x,y+24,W-0,0], fill=LN)  # placeholder (baseline drawn by caller if needed)
    tx=x
    for i,lbl in enumerate(items):
        lw=measure_text(lbl, font_family=TH.font, font_size=13, bold=True)+5  # over-measure: labels draw semibold, markers must clear the last glyph
        col=INK if i==active else MUTE; wt=800 if i==active else 600
        txt(tx,y,lw+8,lbl,size=13,color=col,weight=wt)
        ext=tx+lw+4
        if lock_idx==i: lock(ext,y+2); ext+=16
        if warn_idx==i: ui.circle([ext+13,y+7],3,fill=WARN); ext+=24
        if i==active: ui.rect([tx-2,y+23,lw+6,2.2], fill=ACC, radius=1)
        tx=ext+22
    return tx

# ================= TOP APP BAR =================
ui.rect([0,0,W,46], fill=SURF); ui.rect([0,46,W,1], fill=LN)
ui.rect([16,11,24,24], fill=INK, radius=6); txt(22,15,16,"F", size=15, color=SURF, weight=800)
txt(50,14,160,"FrameForge", size=15, weight=700); txt(210,16,60,"Studio", size=12, color=MUTE, weight=600)
ui.add(pill([500,10,452,26], "FrameForge  ›  docs  ›  illustrator_vs_frameforge.fg.yaml", stroke=LN, theme=TH))
ui.circle([936,23],3,fill=WARN)
ui.add(pill([1048,11,84,24], "History", stroke=LN, theme=TH)); ui.add(pill([1144,11,62,24], "Share", stroke=LN, theme=TH))
ui.add(button([1250,9,110,28], "Render", kind="primary", theme=TH))
ui.rect([1372,9,1,28], fill=LN); ui.add(avatar([1388,9,28,28], "R", tone="accent", theme=TH))
TB=58

# ================= LEFT: FrameForge outline =================
cx,cy,cw,ch=panel([12,TB,352,442], title="FrameForge", action="+ add")
rows=[("g","Metadata","+"),("g","Snippets","+"),("g","Imports","+"),("g","Canvas","–"),
      ("s","Page 1 — cover","sel"),("s","Page 2 — teardown",None),("s","Page 3 — verdict",None),
      ("g","SDK","+"),("g","Fonts","+")]
yy=cy+4
for r in rows:
    kind=r[0]; rh=32 if kind=="g" else 28
    if kind=="s" and r[2]=="sel": ui.rect([cx-6,yy,cw+12,rh], fill=SEL, radius=6)
    if kind=="g":
        txt(cx,yy+7,14,r[2], size=11, color=MUTE)
        ui.rect([cx+18,yy+9,13,13], fill=LINE2, radius=3)
        txt(cx+40,yy+7,cw-70,r[1].upper(), size=13, weight=700)
        if r[1]=="Canvas": ui.add(badge([cx+cw-30,yy+6,26,18],"3", tone="muted", theme=TH))
    else:
        selq=r[2]=="sel"; ui.circle([cx+30,yy+14],2.5, fill=(ACC if selq else LINE))
        txt(cx+44,yy+5,cw-60,r[1], size=13, color=(ACC if selq else INK), weight=(700 if selq else 500))
    yy+=rh
ui.rect([cx,cy+ch-30,cw,1], fill=LN)
txt(cx,cy+ch-22,cw,"6 groups · 51 nodes · valid", size=11, color=MUTE)

# ================= LEFT: Chat =================
ccx,ccy,ccw,cch=panel([12,512,352,376], title="Chat")
ui.add(avatar([ccx,ccy,22,22],"AI", tone="accent", theme=TH))
txt(ccx+30,ccy+3,120,"Assistant", size=13, weight=700); ui.circle([ccx+108,ccy+11],3,fill=GOOD)
txt(ccx+118,ccy+3,80,"online", size=11, color=MUTE)
ui.rect([ccx,ccy+34,ccw*0.8,54], fill=ALT, radius=10); lines(ccx+12,ccy+46,ccw*0.66,3,widths=[1,0.85,0.5])
ub=ccw*0.72; ux=ccx+ccw-ub-30
ui.rect([ux,ccy+104,ub,42], fill=ACCSOFT, radius=10); lines(ux+12,ccy+116,ub-24,2,widths=[0.9,0.6],col="#B9CDF2")
ui.add(avatar([ccx+ccw-24,ccy+104,24,24],"R", tone="muted", theme=TH))
ui.rect([ccx,ccy+162,ccw*0.86,66], fill=ALT, radius=10)
ui.rect([ccx+12,ccy+174,34,42], fill=SURF, stroke=LN, stroke_style={"stroke_width":1}, radius=4)
for k in range(4): ui.rect([ccx+18,ccy+180+k*8,22,3], fill=LINE, radius=1)
lines(ccx+56,ccy+176,ccw*0.55,3,widths=[0.95,0.8,0.5])
ui.rect([ccx,ccy+cch-44,30,38], fill=SURF, stroke=LN, stroke_style={"stroke_width":1}, radius=8)
txt(ccx+9,ccy+cch-33,14,"+", size=15, color=MUTE)
ui.add(field([ccx+38,ccy+cch-44,ccw-110,38], "", placeholder="Ask the assistant…", theme=TH))
ui.add(button([ccx+ccw-64,ccy+cch-44,64,38], "Send", kind="primary", theme=TH))

# ================= CENTER: Editor (PY → YAML, YAML locked) =================
ex,ey,ew,eh=376,TB,520,498
ed=card([ex,ey,ew,eh], theme=TH); ui.add(ed.object); ecx,ecy,ecw,ech=ed.content
mtabs(ecx,ecy,["PY","YAML"],0,lock_idx=1); ui.rect([ecx,ecy+25,ecw,1], fill=LN)
# generated-from indicator
txt(ecx,ecy+38,300,"compose_deck.py", size=12, color=MUTE, mono=True); ui.circle([ecx+126,ecy+45],3,fill=WARN)
lock(ecx+ecw-150,ecy+37); txt(ecx+ecw-132,ecy+36,132,"YAML generated · locked", size=11, color=MUTE, align="right")
code_y=ecy+64; codex=ecx+36; LINT=12
ui.rect([codex-8, code_y+5*20-4, ecw-30-(codex-ecx), 20], fill=SEL, radius=3)          # current line
ui.rect([codex-8, code_y+LINT*20-4, ecw-30-(codex-ecx), 20], fill="#FDEBEC", radius=3) # error line bg
for i in range(15):
    yy=code_y+i*20
    if i==LINT: ui.circle([ecx+8,yy+8],5,fill=RED); txt(ecx+5.4,yy+2.5,7,"!",size=9,color=SURF,weight=800)
    else: txt(ecx, yy, 22, str(i+1), size=11, color=MUTE, align="right", mono=True)
    indent=[0,0,18,18,36,18,0,0,18,36,36,18,0,18,0][i]; kw=i in (2,5,9,13)
    ui.rect([codex+indent, yy+3, 22, 6], fill=(RED if i==LINT else (ACC if kw else LINE)), radius=2)
    cwid=(ecw-118-indent)*[0.7,0.5,0.62,0.4,0.55,0.66,0.48,0.6,0.5,0.44,0.58,0.52,0.66,0.4,0.5][i]
    ui.rect([codex+indent+28, yy+3, cwid, 6], fill=LINE, radius=2)
    if i==LINT: squiggle(codex+indent, yy+12, 28+cwid)
mmx=ecx+ecw-16
for i in range(30): ui.rect([mmx, code_y+i*8, 12*[0.6,0.8,0.5,0.7,0.9,0.4][i%6], 3], fill=(RED if i==LINT else LINE2), radius=1)
txt(codex, code_y+LINT*20, mmx-codex-8, "SyntaxError · unknown arg 'fil'", size=10, color=RED, align="right")
# autocomplete popup
px,py=codex+120, code_y+6*20+12; sh([px,py,214,100],8)
ui.rect([px,py,214,24], fill=SEL, radius=8); ui.rect([px+9,py+8,15,10], fill=ACC, radius=2)
txt(px+30,py+7,160,"page.rect(box, fill…)", size=11, mono=True)
for r in range(1,4):
    ui.rect([px+9,py+6+r*24,15,10], fill=LINE2, radius=2); ui.rect([px+30,py+9+r*24,150*[0.7,0.9,0.6][r-1],6], fill=LINE, radius=2)
# status bar (with lint count)
sby=ecy+ech-22; ui.rect([ecx,sby,ecw,1], fill=LN)
ui.circle([ecx+6,sby+8],4,fill=RED); txt(ecx+16,sby+5,120,"1 error", size=11, color=RED, weight=700, mono=True)
txt(ecx+96,sby+5,220,"Ln 6, Col 12 · Spaces: 4", size=11, color=MUTE, mono=True)
txt(ecx,sby+5,ecw,"PY › YAML · in sync", size=11, color=MUTE, align="right", mono=True)

# ================= CENTER: MCP Tools =================
mcx,mcy,mcw,mch=panel([376,570,254,318], title="MCP Tools", action="25 tools")
for i,(lbl,on) in enumerate([("Vision",True),("Measure",False),("Vectorize",False),
                             ("Propose",True),("Reconstruct",False),("Compare",False)]):
    ui.add(checkbox([mcx, mcy+6+i*40, mcw, 20], checked=on, label=lbl, theme=TH))

# ================= CENTER: Gates =================
gcx,gcy,gcw,gch=panel([642,570,254,318], title="Gates")
ui.rect([gcx,gcy,gcw,34], fill="#E9F6EE", radius=8); check(gcx+16,gcy+17)
txt(gcx+32,gcy+9,gcw,"All gates passing", size=13, color="#1E7B47", weight=700)
for i,(lbl,tag) in enumerate([("100% pass","PASS"),("OK fonts","OK"),("0 collisions","0"),("Golden lock","PIN")]):
    yy=gcy+48+i*40; check(gcx+9,yy+9)
    txt(gcx+26,yy+2,gcw-84,lbl, size=13, weight=600)
    ui.add(badge([gcx+gcw-52,yy,52,20], tag, tone="good" if tag!="PIN" else "muted", theme=TH))
ui.rect([gcx,gcy+48+4*40+2,gcw,1], fill=LN)
txt(gcx,gcy+48+4*40+12,gcw,"render · hash · gate", size=11, color=MUTE, mono=True)

# ================= RIGHT: WYSIWYG | Render pair =================
rc=card([908,TB,520,830], theme=TH); ui.add(rc.object); rcx,rcy,rcw,rch=rc.content
mtabs(rcx,rcy,["WYSIWYG","Render"],1,warn_idx=0)
txt(rcx,rcy+3,rcw,"export", size=11, color=ACC, weight=600, align="right"); ui.rect([rcx,rcy+25,rcw,1], fill=LN)
ui.rect([rcx,rcy+32,rcw,22], fill="#FBF3E6", radius=6); ui.circle([rcx+13,rcy+43],3,fill=WARN)
txt(rcx+24,rcy+36,rcw-30,"Editing WYSIWYG breaks sync with PY", size=11, color="#8A6516", weight=600)
ui.add(pill([rcx,rcy+64,86,24],"Page 1 / 13", stroke=LN, theme=TH))
ui.add(pill([rcx+96,rcy+64,64,24],"100%", stroke=LN, theme=TH))
txt(rcx+rcw-70,rcy+68,70,"fit", size=12, color=MUTE, align="right")
pgx,pgy,pgw,pgh=rcx, rcy+100, rcw, rch-106; sh([pgx,pgy,pgw,pgh],6)
ix,iy,iw=pgx+30,pgy+28,pgw-60
ui.rect([ix,iy,64,78], fill=INK, radius=3); txt(ix+13,iy+9,44,"F", size=50, color=SURF, weight=800)
lines(ix+80,iy+6,iw-80,6,gap=13,widths=[1,0.96,0.99,0.94,0.9,0.68]); lines(ix,iy+94,iw,3,gap=13,widths=[0.98,0.93,0.6])
ui.add(image_placeholder([ix,iy+146,iw,148], label="figure 1 · teardown", theme=TH))
cw2=(iw-24)/2
for c in range(2):
    x0=ix+c*(cw2+24); pts=[(x0+j*(cw2/6), iy+322+(8 if j%2 else 0)) for j in range(7)]
    ui.path([("M",pts[0][0],pts[0][1])]+[("L",q[0],q[1]) for q in pts[1:]], stroke=ACC, stroke_style={"stroke_width":1.6}, fill="none")
    lines(x0,iy+338,cw2,6,gap=12,widths=[1,0.9,0.96,0.8,0.92,0.6])
pcx,pcy,pr=ix+118,iy+464,56; ui.circle([pcx,pcy],pr, fill=SURF, stroke=LN, stroke_style={"stroke_width":1.4})
for a in (90,210,330):
    rr=m.radians(a); ui.line([pcx,pcy],[pcx+pr*m.cos(rr),pcy-pr*m.sin(rr)], stroke=LN, stroke_style={"stroke_width":1.2})
w0,w1=m.radians(90),m.radians(210)
ui.path([("M",pcx,pcy),("L",pcx+pr*m.cos(w0),pcy-pr*m.sin(w0)),("A",pr,pr,0,0,0,pcx+pr*m.cos(w1),pcy-pr*m.sin(w1)),("Z",)],
        fill=ACC, fill_opacity=0.16, stroke="none")
lines(ix+214,iy+426,iw-214,6,gap=12,widths=[0.9,1,0.85,0.95,0.7,0.5]); lines(ix,iy+556,iw,2,widths=[0.95,0.55])
for d in range(5): ui.circle([pgx+pgw/2-28+d*14, pgy+pgh-18],3, fill=(ACC if d==0 else LINE2))

# ================= ANNOTATION IDS (page 1) =================
FEATURES=[
 (1,"Top bar","Brand · workspace","Identify app + switch workspace","Click for home; name switches project","Navigation",185,22),
 (2,"Top bar","Document tab","Show current file + save state","Path shown; amber dot = unsaved","Save-state signal",905,24),
 (3,"Top bar","Render action","Run the full render pipeline","Click runs SDK to SVG/PDF, all gates","Produces output",1226,23),
 (4,"Top bar","Account","Signed-in user menu","Opens profile, settings, sign-out","Opens menu",1418,23),
 (5,"Left rail","Outline tree","Structural map of the document","Expand or collapse; plus-add inserts a node","Author + navigate",340,92),
 (6,"Left rail","Page selection","Choose the page shown in Render","Click a page to select; highlight = active","Drives the preview",372,300),
 (7,"Left rail","Doc stats","Live node count + validity","Reflects nodes and validation result","Trust signal",205,500),
 (8,"Chat","Assistant status","Show AI presence","Green dot = available","Availability",255,548),
 (9,"Chat","Message thread","Converse with the authoring AI","Assistant left/grey, user right/accent","Context",372,700),
 (10,"Chat","Artifact chip","A document referenced in chat","Click to open or insert","Grounding",60,760),
 (11,"Chat","Composer","Send a prompt to the assistant","Type and Send; AI edits or answers","Drives AI authoring",60,838),
 (12,"Editor","PY · YAML tabs","Source views; PY is the source of truth","YAML is generated + locked (read-only)","Sync integrity",552,118),
 (13,"Editor","Locked indicator","Show YAML is derived from PY","Lock; editing needs breaking sync","Prevents drift",836,128),
 (14,"Editor","Code surface","The PY authoring surface","Current line highlighted; typing completes","Editing",430,258),
 (15,"Editor","Lint diagnostic","Inline error (Error-Lens)","Gutter !, squiggle, message; click = jump","Correctness",432,417),
 (16,"Editor","Autocomplete","SDK-aware completion","Suggests page.rect(...) and args","Faster authoring",762,342),
 (17,"Editor","Minimap","Document overview","Red ticks mark error lines","Navigation",866,150),
 (18,"Editor","Status bar","Cursor · indent · lint · sync","1 error · Ln/Col · PY-YAML in sync","At-a-glance state",478,540),
 (19,"Center","MCP tools","Toggle agent MCP capabilities","Checkbox on/off (vision, measure...)","Controls agent tools",502,600),
 (20,"Center","Quality gates","Gates that must pass to ship","All-passing banner; per-gate badges","Release gate",760,600),
 (21,"Render","WYSIWYG · Render","Output views of the document","WYSIWYG editable but breaks PY sync","Parity vs control",1176,118),
 (22,"Render","Preview toolbar","Page nav · zoom · fit","Page 1/13, 100%, fit","Inspection",1130,162),
 (23,"Render","Rendered page","The composed output","Reflects PY; dots = multi-page","The deliverable",1420,320),
 (24,"Ruler","Ruler paper","Measurement frame around the wire","Rulers + accent bands = selection bounds","Spatial reference",8,8),
]
# interaction category per feature id, and the palette
CAT={1:"click",2:"click",3:"click",4:"click",5:"select",6:"select",7:"static",8:"static",
     9:"click",10:"click",11:"type",12:"select",13:"guarded",14:"type",15:"hover",16:"select",
     17:"click",18:"static",19:"toggle",20:"static",21:"guarded",22:"click",23:"static",24:"static"}
CATSTY={"click":("CLICK",ACC),"select":("SELECT","#7C5CD6"),"type":("TYPE","#0E9AA0"),
        "toggle":("TOGGLE",GOOD),"hover":("HOVER",WARN),"guarded":("GUARDED","#E0742B"),
        "static":("READ-ONLY","#8A97A8")}
def _badge(draw_c,draw_t,n,x,y,r=8.6):
    cat=CAT[n]; _,col=CATSTY[cat]
    # colour fill at 20% opacity (80% transparent); crisp coloured ring + coloured number keep it legible
    draw_c([x,y],r, fill=col, fill_opacity=0.2, stroke=col, stroke_style={"stroke_width":1.7}, shadow={"dx":0,"dy":1,"blur":2.5,"color":"#0000001C"})
    draw_t([x-9,y-6.6,18,13], str(n), style={"font_family":TH.font,"font_size":(10 if n<10 else 8.5),"color":col,"font_weight":800,"text_align":"center"})
def ann(n,x,y):
    _badge(ui.circle, ui.text, n, x, y)
for f in FEATURES: ann(f[0], f[6], f[7])

# ---- collect the app group, translate it onto the paper ----
kids=G._current_layer.get("objects",[])
# faint graph-paper grid, under the app, aligned to the ruler (drawn first in the group)
grid=[]
for gx in range(0,W+1,50): grid.append({"type":"rect","box":[gx,0,0.5,H],"fill":GRIDF,"decorative":True})
for gy in range(0,H+1,50): grid.append({"type":"rect","box":[0,gy,W,0.5],"fill":GRIDF,"decorative":True})
p.rect([OX,OY,W,H], fill="none")  # (paper already drawn)
p.group(grid+kids, transform=Mat3.translate(OX,OY), decorative=True)

# ================= OUTER RULER FRAME (measures the wireframe) =================
def ptext(x,y,w,s,size=7.5,color=TICKN,align=None):
    st={"font_family":TH.mono,"font_size":size,"color":color}
    if align: st["text_align"]=align
    p.text([x,y,w,size*1.4], s, style=st)
p.rect([BX,BY,PW,RM], fill=RUL); p.rect([BX,BY,RM,PH], fill=RUL); p.rect([BX,BY,RM,RM], fill="#E4E8EF")
p.rect([BX,BY+RM-0.7,PW,0.7], fill="#CBD3DC"); p.rect([BX+RM-0.7,BY,0.7,PH], fill="#CBD3DC")
ptext(BX+5,BY+RM/2-5,RM-8,"px",7,TICKN)
for ax in range(0,W+1,10):
    cxx=OX+ax; hh=11 if ax%100==0 else (6 if ax%50==0 else 3)
    p.rect([cxx,BY+RM-hh,0.7,hh], fill=TICK)
    if ax%100==0 and abs(ax-908)>46 and abs(ax-1428)>46: ptext(cxx+2,BY+4,36,str(ax),7.5)  # yield to selection labels
for ay in range(0,H+1,10):
    cyy=OY+ay; hh=11 if ay%100==0 else (6 if ay%50==0 else 3)
    p.rect([BX+RM-hh,cyy,hh,0.7], fill=TICK)
    if ay%100==0 and abs(ay-888)>42: ptext(BX+2,cyy+2,RM-3,str(ay),7)  # yield to the 888 selection label
# selection extent (Render panel) highlighted on both rulers
selx0,selx1,sely0,sely1=908,1428,58,888
p.rect([OX+selx0,BY+RM-4,selx1-selx0,4], fill=ACC)
p.rect([BX+RM-4,OY+sely0,4,sely1-sely0], fill=ACC)
ptext(OX+selx0+1,BY+4,40,str(selx0),7,ACC); ptext(OX+selx1-32,BY+4,30,str(selx1),7,ACC,align='right')
ptext(BX+1,OY+sely0+2,RM-4,str(sely0),6.5,ACC,align='right'); ptext(BX+1,OY+sely1-9,RM-4,str(sely1),6.5,ACC,align='right')
# colophon caption on the dark desk, below the paper (rust + cream = book-cover palette)
capy=BY+PH+16
ptext(BX+2,capy,150,"FRAMEFORGE STUDIO",7.5,RUST); ptext(BX+120,capy,220,f"·  wireframe  {W} × {H} px",8,CREAM)
lx=BX+300; ptext(lx,capy,90,"INTERACTION",7,CREAM); lx+=88
for _cat in ["click","select","type","toggle","hover","guarded","static"]:
    _lab,_col=CATSTY[_cat]
    p.circle([lx+4,capy+4],3.6, fill=_col, fill_opacity=(0.0 if _cat=="static" else 1.0), stroke=_col, stroke_style={"stroke_width":1.3})
    ptext(lx+12,capy,90,_lab.title(),7.2,CREAM); lx+=12+len(_lab)*5.6+16

# ================= PAGE 2 — SITEMAP & JOURNEY (present the sitemap) =================
SW,SH=1440,900; MX=104; CWD=SW-2*MX
pgS=b.page("sitemap", canvas={"size":[SW,SH],"units":"px"}, coordinate_mode="absolute")
sM=pgS.layer("bg"); sM.rect([0,0,SW,SH], fill=PAPER)
def dt(x,y,w,ss,size=11,color=BINK,weight=None,align=None,mono=False,serif=False,italic=False,spacing=None,caps=False,lay=None):
    L=lay if lay is not None else sM
    st={"font_family":(SERIF if serif else (TH.mono if mono else TH.font)),"font_size":size,"color":color}
    if weight is not None: st["font_weight"]=weight
    if align: st["text_align"]=align
    if italic: st["font_style"]="italic"
    if spacing is not None: st["letter_spacing"]=spacing
    if caps: st["text_transform"]="uppercase"
    L.text([x,y,w,size*1.6], ss, style=st)
dt(MX,40,600,"FrameForge Studio",8.5,MUTE,spacing=2.6,caps=True)
dt(MX,40,CWD,"Sitemap & Journey",8.5,MUTE,spacing=2.6,caps=True,align="right")
sM.rect([MX,57,CWD,0.8], fill=RULE)
dt(MX,70,600,"§ Information Architecture",sz(-1),RUST,weight=800,spacing=2.6,caps=True)
dt(MX,86,CWD,"One primary surface, a few satellites",sz(4),BINK,weight=600,serif=True)
dt(MX,126,CWD,"The whole product around the wireframe — seven views, one persona, three journeys from lint to sign-off.",sz(1),MUTE,serif=True,italic=True)
sM.rect([MX,150,60,3], fill=RUST)
# persona strip
py=178
sM.rect([MX,py,CWD,64], fill=SURF, stroke=RULE, stroke_style={"stroke_width":1}, radius=10)
sM.circle([MX+34,py+32],18, fill=RUST); dt(MX+26,py+23,22,"R",14,PAPER,weight=800,align="center")
dt(MX+64,py+13,420,"R · design engineer / technical author",sz(0.5),BINK,weight=700,serif=True)
dt(MX+64,py+34,520,"“decks-as-code”  ·  signed in · workspace FrameForge · project docs",sz(-1),MUTE,serif=True,italic=True)
gw=460; dt(MX+CWD-gw-16,py+13,gw,"OVERALL GOAL",7,FAINT,caps=True,spacing=1.2,align="right")
dt(MX+CWD-gw-16,py+30,gw,"fix lint → gates → render → export / share · undo safely",sz(0),RUST,weight=700,serif=True,align="right")
# the journey: sign-in → home → STUDIO → render-run
fy,fh=300,150; xs=[MX,MX+297,MX+594,MX+1022]; ws=[210,210,340,210]
VIEWS=[("Sign in","Sign in","reach the workspace, zero friction","p3 · auth · SSO",False),
       ("Home","FrameForge","resume the last open file in one click","p4 · projects · recent · switch",False),
       ("Studio","FrameForge › docs › …fg.yaml","fix error → gates green → render → export","p1 · editor · MCP · gates · render",True),
       ("Render run","… › Render","a shippable artifact, or the failure","p5 · pipeline · gates · SVG/PDF",False)]
midy=fy+fh/2
for i in range(3):
    x0=xs[i]+ws[i]; x1=xs[i+1]
    sM.line([x0+6,midy],[x1-12,midy], stroke=RUST, stroke_style={"stroke_width":1.6})
    sM.path([("M",x1-12,midy),("L",x1-20,midy-4.2),("L",x1-20,midy+4.2),("Z",)], fill=RUST, stroke="none")
for (name,bc,goal,detail,primary),x,w in zip(VIEWS,xs,ws):
    yy=fy-(8 if primary else 0); hh=fh+(16 if primary else 0)
    sM.rect([x,yy,w,hh], fill=("#FBF6EC" if primary else SURF), stroke=(RUST if primary else RULE),
            stroke_style={"stroke_width":(1.7 if primary else 1)}, radius=12,
            shadow=({"dx":0,"dy":3,"blur":14,"color":"#0000001A"} if primary else None))
    ty=yy+14
    if primary: dt(x+16,ty,w-32,"PRIMARY SURFACE",7,RUST,weight=800,spacing=1.6,caps=True); ty+=17
    dt(x+16,ty,w-32,name,sz(1.5 if primary else 0.5),BINK,weight=700,serif=True); ty+=(27 if primary else 21)
    dt(x+16,ty,w-32,bc,7.5,MUTE,mono=True); ty+=15
    dt(x+16,ty,w-32,goal,sz(-1),MUTE,serif=True,italic=True)
    dt(x+16,yy+hh-22,w-32,detail,7,FAINT,mono=True)
# lower branches: history + viewer + settings, with journey paths radiating from Studio
J_AUTH=RUST; J_REC="#7C5CD6"; J_REV=GOOD; J_ACC="#B7AF9F"
scx,sby=MX+594+170,fy+fh; ly,lh,lw=fy+fh+56,104,230
# each journey carries a distinct DASH pattern as well as a hue — so rank survives
# the grey test and red-green deficiency (never rank by hue alone).
for name,bc,g,detail,x,col,dash,acct in [
    ("History","… › History","recover a bad AI edit / sync-break","p6 · snapshots · diff · restore",MX+238,J_REC,[9,5],False),
    ("Viewer","Shared › …","stakeholder review + sign-off, no account","p7 · pages · comments · share",MX+580,J_REV,[2,5],False),
    ("Settings","FrameForge › Settings","rare admin — in and out fast","p8 · fonts/SDK · golden PIN · sharing",MX+922,J_ACC,[3,4],True)]:
    nx=x+lw/2
    sM.line([scx,sby],[nx,ly], stroke=col, stroke_style={"stroke_width":(1.2 if acct else 1.9),"stroke_dasharray":dash,"stroke_linecap":"round"})
    bs={"stroke_width":1.2}
    if acct: bs["stroke_dasharray"]=[4,3]
    sM.rect([x,ly,lw,lh], fill=SURF, stroke=(RULE if acct else col), stroke_style=bs, radius=12)
    dt(x+14,ly+12,lw-28,name,sz(0.5),BINK,weight=700,serif=True)
    dt(x+14,ly+33,lw-28,bc,7.5,MUTE,mono=True)
    dt(x+14,ly+48,lw-28,g,sz(-1),MUTE,serif=True,italic=True)
    dt(x+14,ly+lh-20,lw-28,detail,7,FAINT,mono=True)
# three-journey legend — line SAMPLE carries the same pattern, so the key reads in greyscale too
jy=ly+lh+28; dt(MX,jy,180,"THREE JOURNEYS",7.5,FAINT,caps=True,spacing=1.4); jx=MX+152
for lbl,col,dash in [("Author & export",J_AUTH,None),("Recover a bad edit",J_REC,[9,5]),("Stakeholder review",J_REV,[2,5])]:
    st={"stroke_width":2.6,"stroke_linecap":"round"}
    if dash: st["stroke_dasharray"]=dash
    sM.line([jx,jy+6],[jx+34,jy+6], stroke=col, stroke_style=st)
    dt(jx+42,jy,260,lbl,sz(-1),BINK,serif=True); jx+=42+len(lbl)*6.6+34
dt(MX,jy+26,CWD,"Guarded — a WYSIWYG edit confirms & auto-snapshots first · YAML is read-only (derived) · the golden lock needs a PIN.",sz(-1),FAINT,serif=True,italic=True)
# decisions (r2 defaults) — fills the lower band, records what was decided
dcy=jy+72; dt(MX,dcy,200,"DECISIONS · defaults",7.5,FAINT,caps=True,spacing=1.4)
sM.rect([MX,dcy+16,CWD,0.7], fill=RULE)
for i,(k,v) in enumerate([("render-run","a deep-linkable route — gate failures are shareable (CI, review)"),
    ("home","a dashboard page — brand click goes home, not a popover"),
    ("history","git-backed + auto-snapshots on AI-accept / render / sync-break"),
    ("collaboration","v1 single-player + async review (viewer link + comments); live multiplayer deferred"),
    ("journey end","a shareable read-only viewer — the journey ends at sign-off, not download")]):
    yy=dcy+26+i*23
    dt(MX,yy,160,k,sz(-1),RUST,weight=700,serif=True); dt(MX+168,yy,CWD-168,v,sz(-1),MUTE,serif=True)
sM.rect([MX,SH-56,CWD,0.8], fill=RULE)
dt(MX,SH-44,980,"Principle — PY is the source of truth; YAML is generated. One primary surface (Studio), few satellites.",8.5,FAINT,italic=True,serif=True)
dt(MX,SH-44,CWD,"2",sz(-1),FAINT,align="right",mono=True)

# ================= SATELLITE VIEWS (pages 3–6) — the missing views, same wireframe surface =========
def newview(pid):
    global p, ui, G
    pgv=b.page(pid, canvas={"size":[W2,H2],"units":"px"}, coordinate_mode="absolute")
    p=pgv.layer("paper")
    p.rect([0,0,W2,H2], fill=DESK)
    p.rect([BX,BY,PW,PH], fill=RUL, radius=3, shadow={"dx":0,"dy":6,"blur":26,"color":"#00000055"})
    p.rect([OX,OY,W,H], fill=ALT, shadow={"dx":0,"dy":2,"blur":12,"color":"#0F172A1E"})
    G=PageBuilder({"layers":[]}).layer("_app"); ui=G
def endview(folio, kicker, sub):
    kids=G._current_layer.get("objects",[])
    p.group(kids, transform=Mat3.translate(OX,OY), decorative=True)
    p.rect([BX,BY,PW,RM], fill=RUL); p.rect([BX,BY,RM,PH], fill=RUL); p.rect([BX,BY,RM,RM], fill="#E4E8EF")
    p.rect([BX,BY+RM-0.7,PW,0.7], fill="#CBD3DC"); p.rect([BX+RM-0.7,BY,0.7,PH], fill="#CBD3DC")
    ptext(BX+5,BY+RM/2-5,RM-8,"px",7,TICKN)
    for ax in range(0,W+1,50):
        cxx=OX+ax; hh=9 if ax%100==0 else 5; p.rect([cxx,BY+RM-hh,0.7,hh], fill=TICK)
        if ax%100==0: ptext(cxx+2,BY+4,36,str(ax),7,TICKN)
    for ay in range(0,H+1,50):
        cyy=OY+ay; hh=9 if ay%100==0 else 5; p.rect([BX+RM-hh,cyy,hh,0.7], fill=TICK)
        if ay%100==0: ptext(BX+2,cyy+2,RM-3,str(ay),6.5,TICKN)
    capy=BY+PH+16
    ptext(BX+2,capy,300,kicker,7.5,RUST); ptext(BX+2+len(kicker)*5.6+16,capy,600,sub,8,CREAM)
    ptext(BX+2,capy,PW,folio,8,CREAM,align="right")
def vbar(breadcrumb, *, render=True, app="Studio", ws_pill=False):
    ui.rect([0,0,W,46], fill=SURF); ui.rect([0,46,W,1], fill=LN)
    ui.rect([16,11,24,24], fill=INK, radius=6); txt(22,15,16,"F", size=15, color=SURF, weight=800)
    txt(50,14,160,"FrameForge", size=15, weight=700)
    if ws_pill: ui.add(pill([200,11,150,24], "FrameForge  ▾", stroke=LN, theme=TH))
    elif app: txt(210,16,60,app, size=12, color=MUTE, weight=600)
    if breadcrumb: ui.add(pill([500,10,452,26], breadcrumb, stroke=LN, theme=TH))
    if render: ui.add(button([1250,9,110,28], "Render", kind="primary", theme=TH))
    ui.rect([1372,9,1,28], fill=LN); ui.add(avatar([1388,9,28,28], "R", tone="accent", theme=TH))
def secbtn(box,label,color=None):
    ui.rect(box, fill=SURF, stroke=LN, stroke_style={"stroke_width":1}, radius=8)
    txt(box[0],box[1]+box[3]/2-8,box[2],label, size=13, weight=600, align="center", color=color or INK)
def goal(g): txt(40,H-38,700,"Goal — "+g, size=12, color=MUTE)

# ---- PAGE 3 — SIGN IN ----
newview("signin"); ui.rect([0,0,W,H], fill=ALT)
cwd,chd=380,404; cX=(W-cwd)/2; cY=(H-chd)/2-24; sh([cX,cY,cwd,chd],16)
ui.rect([cX+cwd/2-24,cY+40,48,48], fill=INK, radius=12); txt(cX+cwd/2-24,cY+50,48,"F",size=28,color=SURF,weight=800,align="center")
txt(cX,cY+104,cwd,"Sign in to FrameForge", size=19, weight=700, align="center")
txt(cX,cY+134,cwd,"Author decks as code.", size=13, color=MUTE, align="center")
ui.add(button([cX+40,cY+174,cwd-80,42],"Continue with SSO", kind="primary", theme=TH))
half=(cwd-80)/2-18; ui.rect([cX+40,cY+240,half,1], fill=LN); ui.rect([cX+cwd-40-half,cY+240,half,1], fill=LN)
txt(cX,cY+233,cwd,"or", size=11, color=MUTE, align="center")
ui.add(field([cX+40,cY+258,cwd-80,38],"", placeholder="you@company.com", theme=TH))
secbtn([cX+40,cY+306,cwd-80,40],"Continue with email")
txt(cX,cY+360,cwd,"No account?   Create workspace", size=12, color=ACC, weight=600, align="center")
goal("reach the workspace with zero friction."); endview("3","SIGN IN","·  reach the workspace, zero friction")

# ---- PAGE 4 — HOME (workspace dashboard) ----
newview("home"); ui.rect([0,46,W,H-46], fill=ALT); vbar(None, render=False, ws_pill=True)
ui.rect([0,46,220,H-46], fill=SURF); ui.rect([220,46,1,H-46], fill=LN)
txt(20,68,180,"WORKSPACES", size=10, color=MUTE, weight=700)
for i,(nm,act) in enumerate([("FrameForge",True),("Personal",False)]):
    yy=90+i*40
    if act: ui.rect([12,yy-6,196,34], fill=SEL, radius=8)
    ui.rect([20,yy,18,18], fill=(ACC if act else LINE2), radius=5)
    txt(48,yy+2,150,nm, size=13, weight=(700 if act else 500), color=(ACC if act else INK))
txt(20,182,180,"+ New workspace", size=12, color=ACC, weight=600)
mxx=252; txt(mxx,72,400,"docs", size=22, weight=700); txt(mxx,106,500,"3 files · last opened just now", size=12, color=MUTE)
secbtn([W-320,74,132,34],"Import"); ui.add(button([W-176,74,136,34],"New project", kind="primary", theme=TH))
cw3=(W-mxx-40-40)/3
for i,(nm,st,uns) in enumerate([("illustrator_vs_frameforge","unsaved",True),("brand_book","saved",False),("syrus_proposal","saved",False)]):
    x0=mxx+i*(cw3+20); y0=152; sh([x0,y0,cw3,224],12)
    ui.add(image_placeholder([x0+14,y0+14,cw3-28,120], label="", theme=TH))
    txt(x0+16,y0+148,cw3-46,nm+".fg.yaml", size=13, weight=600, mono=True)
    if uns: ui.circle([x0+cw3-22,y0+154],4,fill=WARN)
    txt(x0+16,y0+172,cw3-30,"edited "+("just now" if uns else "2 days ago"), size=11, color=MUTE)
    ui.add(pill([x0+16,y0+192,74,22], st, stroke=LN, theme=TH))
goal("resume the last open file in one click."); endview("4","HOME","·  workspace dashboard")

# ---- PAGE 5 — RENDER RUN ----
newview("render"); ui.rect([0,46,W,H-46], fill=ALT); vbar("FrameForge  ›  docs  ›  …fg.yaml  ›  Render", render=False)
pX,pY,pWi,pHi=(W-760)/2,86,760,H-150; sh([pX,pY,pWi,pHi],14)
txt(pX+28,pY+22,400,"Render run", size=18, weight=700)
ui.add(badge([pX+pWi-180,pY+20,168,26],"COMPLETE · 8.4s", tone="good", theme=TH))
ui.rect([pX+28,pY+56,pWi-56,1], fill=LN)
for i,(nm) in enumerate(["Parse PY","Validate model","Render pages (13)","Run gates","Export SVG · PDF"]):
    yy=pY+74+i*44; check(pX+42,yy+9); txt(pX+64,yy+2,320,nm, size=14, weight=600)
    ui.rect([pX+330,yy+7,pWi-470,5], fill=GOOD, radius=2); txt(pX+pWi-108,yy+2,90,"done", size=12, color=GOOD, weight=700, align="right", mono=True)
gyy=pY+74+5*44+8; ui.rect([pX+28,gyy,pWi-56,1], fill=LN)
check(pX+42,gyy+22); txt(pX+64,gyy+15,400,"12 / 12 gates passing", size=14, weight=700, color="#1E7B47")
ayy=gyy+52
for i,(nm,fs) in enumerate([("deck.svg","1.2 MB"),("deck.pdf","840 KB")]):
    x0=pX+28+i*((pWi-56)/2+8); bw=(pWi-56)/2-8
    ui.rect([x0,ayy,bw,66], fill=ALT, stroke=LN, stroke_style={"stroke_width":1}, radius=10)
    ui.rect([x0+14,ayy+16,34,34], fill=INK, radius=6); txt(x0+14,ayy+22,34,fs[:0] or nm.split(".")[-1].upper(), size=10, color=SURF, weight=800, align="center")
    txt(x0+58,ayy+13,220,nm, size=13, weight=600, mono=True); txt(x0+58,ayy+34,220,fs, size=11, color=MUTE)
    ui.add(button([x0+bw-104,ayy+17,92,32],"Download", kind="primary", theme=TH))
txt(pX+28,pY+pHi-32,200,"↻  Re-run", size=13, color=ACC, weight=600)
goal("a shippable artifact, or the exact failure location."); endview("5","RENDER RUN","·  pipeline · gates · artifacts")

# ---- PAGE 6 — HISTORY (git-backed snapshots · diff · restore) ----
newview("history"); ui.rect([0,46,W,H-46], fill=ALT); vbar("FrameForge  ›  docs  ›  …fg.yaml  ›  History", render=False, app=None)
ui.rect([0,46,304,H-46], fill=SURF); ui.rect([304,46,1,H-46], fill=LN)
txt(24,68,200,"SNAPSHOTS", size=10, color=MUTE, weight=700); txt(120,66,164,"auto + manual", size=10, color=GOOD, weight=700, align="right")
snaps=[("now","working copy","current",False),("2m","render · 13 pages","auto · golden",True),
       ("14m","AI edit · recolor pass","auto",False),("31m","manual save","manual",False),
       ("1h","sync break resolved","auto",False),("2h","import compose_deck.py","manual",False)]
ui.rect([45,104,2,len(snaps)*64-34], fill=LINE2)
for i,(t,lbl,tag,gold) in enumerate(snaps):
    yy=100+i*64; cur=(tag=="current")
    if cur: ui.rect([16,yy-4,276,46], fill=SEL, radius=8)
    ui.circle([46,yy+8],(6 if cur else 4.5), fill=(ACC if cur else (WARN if gold else SURF)), stroke=(ACC if cur else LINE), stroke_style={"stroke_width":1.6})
    txt(66,yy,190,lbl, size=13, weight=(700 if cur else 600), color=(ACC if cur else INK))
    txt(66,yy+18,200,t+" ago · "+tag, size=11, color=MUTE, mono=True)
    if gold: lock(276,yy+2,col=WARN)
dx=328; txt(dx,72,500,"Diff — AI edit · recolor pass", size=16, weight=700); txt(dx,102,500,"vs current working copy", size=12, color=MUTE, mono=True)
secbtn([W-322,70,132,34],"Pin as golden"); ui.add(button([W-178,70,138,34],"Restore", kind="primary", theme=TH))
dgx,dgy,dgw,dgh=dx,132,W-dx-40,H-192; sh([dgx,dgy,dgw,dgh],10)
diff=[(" ","def cover(page):",None),(" ","    page.rect(box, fill=INK)",None),
      ("-","    page.recolor(fig, ramp='warm')","del"),("+","    page.recolor(fig, ramp='cool')","add"),
      ("-","    title(size=42, weight=900)","del"),("+","    title(size=36, weight=700)","add"),
      (" ","    return page",None)]
for i,(mk,code,kind) in enumerate(diff):
    yy=dgy+18+i*28; bg={"del":"#FDECEC","add":"#E9F6EE"}.get(kind)
    if bg: ui.rect([dgx+10,yy-4,dgw-20,26], fill=bg, radius=3)
    txt(dgx+18,yy,16,mk, size=13, color=(RED if kind=="del" else (GOOD if kind=="add" else MUTE)), mono=True, weight=800)
    txt(dgx+44,yy,dgw-64,code, size=13, color=(INK if kind else MUTE), mono=True)
txt(dgx+18,dgy+dgh-26,400,"⧉  Copy snippet from this version", size=12, color=ACC, weight=600)
goal("undo a bad AI edit or sync-break without losing later work."); endview("6","HISTORY","·  git-backed snapshots · PY diff · restore")

# ---- PAGE 7 — VIEWER (public, read-only — closes the review loop) ----
newview("viewer"); ui.rect([0,0,W,H], fill="#F1EFEA")
ui.rect([0,0,W,46], fill=SURF); ui.rect([0,46,W,1], fill=LN)
ui.rect([16,11,24,24], fill=INK, radius=6); txt(16,15,24,"F", size=15, color=SURF, weight=800, align="center")
txt(52,14,320,"illustrator_vs_frameforge", size=14, weight=700)
ui.add(pill([322,12,130,24], "Shared · read-only", stroke=LN, theme=TH))
secbtn([W-306,9,120,28],"Download"); ui.add(button([W-174,9,134,28],"Open in Studio", kind="primary", theme=TH))
vpx,vpy,vpw,vph=104,88,560,H-150; sh([vpx,vpy,vpw,vph],6)
ix,iy,iw=vpx+40,vpy+34,vpw-80
ui.rect([ix,iy,58,72], fill=INK, radius=3); txt(ix,iy+8,58,"F",size=44,color=SURF,weight=800,align="center")
lines(ix+74,iy+6,iw-74,5,gap=13,widths=[1,0.95,0.9,0.85,0.6]); ui.add(image_placeholder([ix,iy+104,iw,150],label="figure 1 · teardown",theme=TH))
lines(ix,iy+270,iw,4,gap=13,widths=[0.98,0.92,0.96,0.6])
ui.add(pill([vpx+16,vpy+vph-40,86,24],"Page 1 / 13", stroke=LN, theme=TH)); ui.add(pill([vpx+112,vpy+vph-40,58,24],"100%", stroke=LN, theme=TH))
for d in range(5): ui.circle([vpx+vpw/2-28+d*14, vpy+vph-16],3, fill=(ACC if d==0 else LINE2))
cpx=vpx+vpw+40; cpw=W-cpx-40
txt(cpx,vpy,cpw,"Comments", size=15, weight=700); ui.add(badge([cpx+cpw-52,vpy-2,52,22],"3", tone="muted", theme=TH)); ui.rect([cpx,vpy+26,cpw,1], fill=LN)
comments=[("JD","Jordan · reviewer","Can the teardown figure be higher-contrast?","p1 · 2h",False),
          ("PM","Priya · PM","Approve once the title fits one line.","p1 · 1h",False),
          ("R","You","Fixed the ramp + title — re-rendered.","p1 · just now",True)]
for i,(av,who,msg,meta,me) in enumerate(comments):
    yy=vpy+44+i*104; ui.add(avatar([cpx,yy,26,26], av, tone=("accent" if me else "muted"), theme=TH))
    txt(cpx+36,yy+1,cpw-46,who, size=13, weight=700); txt(cpx+36,yy+18,cpw-46,meta, size=11, color=MUTE, mono=True)
    ui.rect([cpx+36,yy+36,cpw-46,50], fill=(ACCSOFT if me else ALT), radius=8); txt(cpx+48,yy+46,cpw-70,msg, size=12, color=INK)
ui.add(field([cpx,H-96,cpw-74,38],"", placeholder="Add a comment…", theme=TH)); ui.add(button([cpx+cpw-66,H-96,66,38],"Send", kind="primary", theme=TH))
goal("(stakeholder) review + sign off — no account, no install."); endview("7","VIEWER","·  public read-only · comments · sign-off")

# ---- PAGE 8 — SETTINGS ----
newview("settings"); ui.rect([0,46,W,H-46], fill=ALT); vbar("FrameForge  ›  Settings", render=False, app=None)
ui.rect([0,46,240,H-46], fill=SURF); ui.rect([240,46,1,H-46], fill=LN)
txt(20,68,200,"SETTINGS", size=10, color=MUTE, weight=700)
for i,(nm,act) in enumerate([("Profile",True),("Workspace members",False),("SDK & fonts",False),("Golden lock",False),("Sharing & git",False),("Billing",False)]):
    yy=96+i*40
    if act: ui.rect([12,yy-6,216,32], fill=SEL, radius=8)
    txt(24,yy,204,nm, size=13, weight=(700 if act else 500), color=(ACC if act else INK))
txt(24,H-72,200,"Sign out", size=13, color=RED, weight=600)
mxx=280; txt(mxx,74,400,"Profile", size=20, weight=700); ui.rect([mxx,110,W-mxx-40,1], fill=LN)
ui.circle([mxx+34,164],32, fill=ACC); txt(mxx+2,152,64,"R",size=24,color=SURF,weight=800,align="center")
txt(mxx+82,152,200,"Change photo", size=12, color=ACC, weight=600)
for i,(lbl,val) in enumerate([("Name","R. Author"),("Email","r@frameforge.dev"),("Role","Design engineer")]):
    yy=212+i*58; txt(mxx,yy,200,lbl, size=11, color=MUTE, weight=700)
    ui.rect([mxx,yy+18,360,34], fill=SURF, stroke=LN, stroke_style={"stroke_width":1}, radius=8)
    txt(mxx+13,yy+27,340,val, size=13, color=INK)  # value in real case, not the field-label caps
rxx=mxx+436; rw=W-rxx-40
sh([rxx,150,rw,150],12); txt(rxx+16,166,300,"SDK & fonts", size=14, weight=700)
txt(rxx+16,194,rw-30,"SDK 2.4.0  ·  4,986 font families", size=12, color=MUTE, mono=True)
secbtn([rxx+16,230,150,32],"Manage")
sh([rxx,322,rw,158],12); txt(rxx+16,338,240,"Golden lock", size=14, weight=700)
ui.add(badge([rxx+rw-88,338,72,22],"PINNED", tone="good", theme=TH))
lock(rxx+16,372); txt(rxx+34,368,rw-40,"a PIN protects render·hash·gate re-baselining", size=12, color=MUTE)
secbtn([rxx+16,414,150,32],"Change PIN")
# sharing defaults + git remote (r2 settings additions)
sh([rxx,502,rw,158],12); txt(rxx+16,518,300,"Sharing & git remote", size=14, weight=700)
txt(rxx+16,552,180,"Default share link", size=12, color=MUTE)
ui.add(pill([rxx+196,548,rw-212,24], "anyone with link · comment", stroke=LN, theme=TH))
txt(rxx+16,588,180,"Git remote", size=12, color=MUTE)
txt(rxx+196,588,rw-212,"github.com/frameforge/docs", size=12, color=INK, mono=True)
secbtn([rxx+16,620,150,32],"Configure")
goal("rare admin task; in and out fast."); endview("8","SETTINGS","·  profile · members · SDK/fonts · golden PIN · sharing")

# ================= PAGE 7 — FEATURE REFERENCE (after The Letter & the Hue) =================
SW,SH=1440,900
pg2=b.page("spec", canvas={"size":[SW,SH],"units":"px"}, coordinate_mode="absolute")
s2=pg2.layer("bg"); s2.rect([0,0,SW,SH], fill=PAPER)
def s2t(x,y,w,ss,size=11,color=BINK,weight=None,align=None,mono=False,serif=False,italic=False,spacing=None,caps=False):
    st={"font_family":(SERIF if serif else (TH.mono if mono else TH.font)),"font_size":size,"color":color}
    if weight is not None: st["font_weight"]=weight
    if align: st["text_align"]=align
    if italic: st["font_style"]="italic"
    if spacing is not None: st["letter_spacing"]=spacing
    if caps: st["text_transform"]="uppercase"
    s2.text([x,y,w,size*1.6], ss, style=st)
MX=104; CWD=SW-2*MX
# running head + hairline
s2t(MX,40,600,"The Studio Wireframe",8.5,MUTE,spacing=2.6,caps=True)
s2t(MX,40,CWD,"Feature Reference",8.5,MUTE,spacing=2.6,caps=True,align="right")
s2.rect([MX,57,CWD,0.8], fill=RULE)
# masthead: rust kicker · serif title · italic deck · the red rule
s2t(MX,70,600,"§ Annotation Key",sz(-1),RUST,weight=800,spacing=2.6,caps=True)
s2t(MX,86,CWD,"FrameForge Studio, annotated",sz(4),BINK,weight=600,serif=True)
s2t(MX,126,CWD,"Twenty-four features of the authoring surface — placement, purpose, mechanics, and how each answers the hand.",sz(1),MUTE,serif=True,italic=True)
s2.rect([MX,150,60,3], fill=RUST)
# column heads
Xn=MX+8; Xf=MX+32; Xo=MX+320; Xb=MX+650; Xe=MX+986
Wf,Wo,Wb,We=284,326,332,CWD-(Xe-MX)
hy=160
for xx,ww,hh in [(Xf,Wf,"Feature"),(Xo,Wo,"Objective"),(Xb,Wb,"Behaviour"),(Xe,We,"Effect")]:
    s2t(xx,hy,ww,hh,sz(-1),MUTE,weight=700,spacing=1.4,caps=True)
s2.rect([MX,hy+18,CWD,1.2], fill=BINK)
ry=hy+26; zone=None
for f in FEATURES:
    n,zn,name,obj,beh,eff,bx,by=f
    if zn!=zone:
        zone=zn; cnt=sum(1 for x in FEATURES if x[1]==zn); ry+=4
        s2t(Xf,ry,300,zn,sz(-1),RUST,weight=800,spacing=2.0,caps=True)
        s2t(MX,ry,CWD,(f"{cnt} features" if cnt!=1 else "1 feature"),sz(-2),FAINT,italic=True,serif=True,align="right")
        s2.rect([MX,ry+14,CWD,0.7], fill=RULE); ry+=20
    _badge(s2.circle,s2.text,n,Xn,ry+7)
    _lab,_col=CATSTY[CAT[n]]; _cwp=len(_lab)*5.1+13
    s2t(Xf,ry,Wf-_cwp-10,name,sz(0.5),BINK,weight=700,serif=True)
    s2.rect([Xf+Wf-_cwp-4,ry+1,_cwp,13],fill=_col,fill_opacity=0.16,stroke=_col,stroke_style={"stroke_width":0.9},radius=6.5)
    s2t(Xf+Wf-_cwp-4,ry+2,_cwp,_lab,6.7,_col,800,align="center")
    s2t(Xo,ry+1.5,Wo-12,obj,sz(0),BINK,serif=True)
    s2t(Xb,ry+1.5,Wb-12,beh,sz(0),MUTE,serif=True)
    s2t(Xe,ry+1.5,We-6,eff,sz(0),RUST,weight=600,serif=True)
    ry+=19
    s2.rect([MX,ry-4,CWD,0.5], fill=RULE)
# foot: rule · colophon · folio
s2.rect([MX,SH-56,CWD,0.8], fill=RULE)
s2t(MX,SH-44,700,"Typeset after The Letter & the Hue — one ink, one accent, a modular scale.",8.5,FAINT,italic=True,serif=True)
s2t(MX,SH-44,CWD,"9",sz(-1),FAINT,align="right",mono=True)

doc=b.build()
rep=validate_static_rules(doc); errs=[x for x in rep.issues if x.severity=="error"]
print(f"ok={rep.ok} errors={len(errs)} warns={len(rep.issues)-len(errs)} canvas={W2}x{H2}")
for x in errs[:12]: print("  ERR:",x.rule_id,x.path,x.message)
if __name__ == "__main__":
    out = os.environ.get("OUTPUT_YAML_PATH", "frameforge-ide-annotated.fg.yaml")
    b.write(out, fail_on_error=True)
    print("wrote", out)
