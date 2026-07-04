"""Android 16 · Material 3 Expressive — UI Guidelines.

A 64-page A4 reference, built with the FrameGraph SDK from PRIMITIVES ONLY
(rect · text · line · circle · path · group). Every Android component below is
drawn from those primitives — no widget helpers. Specs grounded in public
Material 3 / M3 Expressive guidance (see the closing colophon for sources).
"""
import os, math
from framegraph.sdk import DocumentBuilder, serialize

# ============================================================ A4 + type
W, H = 1000, 1414                      # A4 portrait ratio (1 : 1.414)
MX = 72                                # page margin
SANS = ["Roboto", "Roboto Flex", "DejaVu Sans", "Arial", "sans-serif"]
MONO = ["Roboto Mono", "DejaVu Sans Mono", "monospace"]

# ---- Material 3 baseline colour scheme (light) — grounded on the #6750A4 seed ----
PRIMARY="#6750A4"; ON_PRIMARY="#FFFFFF"; PRIMARY_C="#EADDFF"; ON_PRIMARY_C="#21005D"
SECONDARY="#625B71"; ON_SECONDARY="#FFFFFF"; SECONDARY_C="#E8DEF8"; ON_SECONDARY_C="#1D192B"
TERTIARY="#7D5260"; ON_TERTIARY="#FFFFFF"; TERTIARY_C="#FFD8E4"; ON_TERTIARY_C="#31111D"
ERROR="#B3261E"; ON_ERROR="#FFFFFF"; ERROR_C="#F9DEDC"; ON_ERROR_C="#410E0B"
SURFACE="#FEF7FF"; ON_SURFACE="#1D1B20"; SURFACE_V="#E7E0EC"; ON_SURFACE_V="#49454F"
SURF_DIM="#DED8E1"; SC_LOWEST="#FFFFFF"; SC_LOW="#F7F2FA"; SC="#F3EDF7"; SC_HIGH="#ECE6F0"; SC_HIGHEST="#E6E0E9"
OUTLINE="#79747E"; OUTLINE_V="#CAC4D0"; SCRIM="#000000"
# dark baseline (for the dark-scheme page)
D_PRIMARY="#D0BCFF"; D_ON_PRIMARY="#381E72"; D_PRIMARY_C="#4F378B"; D_ON_PRIMARY_C="#EADDFF"
D_SURFACE="#141218"; D_ON_SURFACE="#E6E0E9"; D_SURFACE_V="#49454F"; D_ON_SURFACE_V="#CAC4D0"
D_SECONDARY="#CCC2DC"; D_TERTIARY="#EFB8C8"; D_OUTLINE="#938F99"
INK=ON_SURFACE; MUTE=ON_SURFACE_V; FAINT="#8E8A94"; HAIR="#EDE8F0"

# ---- type scale: 5 roles × 3 sizes (Roboto Regular=400 / Medium=500) ----
TYPE={"display-large":(57,400),"display-medium":(45,400),"display-small":(36,400),
      "headline-large":(32,400),"headline-medium":(28,400),"headline-small":(24,400),
      "title-large":(22,400),"title-medium":(16,500),"title-small":(14,500),
      "body-large":(16,400),"body-medium":(14,400),"body-small":(12,400),
      "label-large":(14,500),"label-medium":(12,500),"label-small":(11,500)}
SHAPES=[("None",0),("Extra-small",4),("Small",8),("Medium",12),("Large",16),("Extra-large",28),("Full","pill")]
ELEV=[("Level 0",0),("Level 1",1),("Level 2",3),("Level 3",6),("Level 4",8),("Level 5",12)]

b=DocumentBuilder(title="Android 16 · Material 3 Expressive — UI Guidelines", profile="book", lang="en")
L=None; _N=[0]

# ============================================================ primitive helpers
def T(x,y,w,s,*,size=14,color=INK,weight=400,mono=False,align=None,spacing=None,lh=None):
    s=str(s); st={"font_family":(MONO if mono else SANS),"font_size":size,"color":color,"font_weight":weight}
    if align: st["text_align"]=align
    if spacing is not None: st["letter_spacing"]=spacing
    if lh: st["line_height"]=lh
    cw=max(size*0.56,1); est=0
    for seg in s.split(chr(10)): est+=max(1,math.ceil(len(seg)*cw/max(w,1)))
    L.text([x,y,w,size*(lh or 1.4)*max(s.count(chr(10))+1,est)+4], s, style=st)
def R(box,*,fill=None,stroke=None,sw=1.2,radius=0,dash=None,shadow=None,fo=None):
    f={}
    if fill is not None: f["fill"]=fill
    if stroke is not None:
        f["stroke"]=stroke; ss={"stroke_width":sw}
        if dash: ss["stroke_dasharray"]=dash
        f["stroke_style"]=ss
    if radius: f["radius"]=radius
    if fo is not None: f["fill_opacity"]=fo
    if shadow: f["shadow"]=shadow
    L.rect(list(box),**f)
def SH(box,*,fill=SURFACE,radius=12,elev=1):
    dy=[0,1,2,4,6,8][min(elev,5)]; bl=[0,3,6,10,14,18][min(elev,5)]
    R(box,fill=fill,radius=radius,shadow=({"dx":0,"dy":dy,"blur":bl,"color":"#00000026"} if elev else None))
def LN(p0,p1,*,stroke=OUTLINE_V,sw=1.2,dash=None,cap="round"):
    ss={"stroke_width":sw,"stroke_linecap":cap}
    if dash: ss["stroke_dasharray"]=dash
    L.line(list(p0),list(p1),stroke=stroke,stroke_style=ss)
def DOT(x,y,r,fill=None,stroke=None,sw=1.4):
    f={}
    if fill: f["fill"]=fill
    if stroke: f["stroke"]=stroke; f["stroke_style"]={"stroke_width":sw}
    if not fill: f["fill"]="none"
    L.circle([x,y],r,**f)
def PATH(d,*,stroke=None,fill=None,sw=2.0,cap="round",join="round"):
    f={}
    if fill is not None: f["fill"]=fill
    else: f["fill"]="none"
    if stroke is not None: f["stroke"]=stroke; f["stroke_style"]={"stroke_width":sw,"stroke_linecap":cap,"stroke_linejoin":join}
    L.path(d,**f)
def PILL(box,**k): R(box,radius=box[3]/2,**k)

# ---- geometric Material icons (24dp keyline; draw within a s×s box at x,y) ----
def icon(name,x,y,s=24,color=ON_SURFACE,sw=2.0):
    u=s/24.0; cx,cy=x+s/2,y+s/2
    def ln(a,bx,by,cxx,cyy=None):
        LN((x+a*u,y+bx*u),(x+by*u,y+cxx*u) if cyy is None else (x+cxx*u,y+cyy*u),stroke=color,sw=sw)
    if name=="menu":
        for yy in (7,12,17): LN((x+4*u,y+yy*u),(x+20*u,y+yy*u),stroke=color,sw=sw)
    elif name=="back": PATH(f"M {x+15*u} {y+5*u} L {x+8*u} {cy} L {x+15*u} {y+19*u}",stroke=color,sw=sw)
    elif name=="close":
        LN((x+6*u,y+6*u),(x+18*u,y+18*u),stroke=color,sw=sw); LN((x+18*u,y+6*u),(x+6*u,y+18*u),stroke=color,sw=sw)
    elif name=="search":
        DOT(x+10.5*u,y+10.5*u,5*u,stroke=color,sw=sw); LN((x+14.5*u,y+14.5*u),(x+19*u,y+19*u),stroke=color,sw=sw)
    elif name=="add":
        LN((cx,y+5*u),(cx,y+19*u),stroke=color,sw=sw); LN((x+5*u,cy),(x+19*u,cy),stroke=color,sw=sw)
    elif name=="check": PATH(f"M {x+5*u} {y+13*u} L {x+10*u} {y+18*u} L {x+19*u} {y+6*u}",stroke=color,sw=sw)
    elif name=="more":
        for yy in (6,12,18): DOT(cx,y+yy*u,1.6*u,fill=color)
    elif name=="more-h":
        for xx in (6,12,18): DOT(x+xx*u,cy,1.6*u,fill=color)
    elif name=="home": PATH(f"M {x+5*u} {y+12*u} L {cx} {y+4*u} L {x+19*u} {y+12*u} L {x+19*u} {y+20*u} L {x+5*u} {y+20*u} Z",stroke=color,sw=sw)
    elif name=="favorite": PATH(f"M {cx} {y+19*u} C {x+2*u} {y+11*u} {x+6*u} {y+5*u} {cx} {y+9.5*u} C {x+18*u} {y+5*u} {x+22*u} {y+11*u} {cx} {y+19*u} Z",stroke=color,sw=sw,fill="none")
    elif name=="settings":
        DOT(cx,cy,3*u,stroke=color,sw=sw)
        for k in range(8):
            a=k*math.pi/4; LN((cx+6*u*math.cos(a),cy+6*u*math.sin(a)),(cx+9*u*math.cos(a),cy+9*u*math.sin(a)),stroke=color,sw=sw)
    elif name=="person":
        DOT(cx,y+9*u,3.4*u,stroke=color,sw=sw); PATH(f"M {x+6*u} {y+20*u} C {x+6*u} {y+14*u} {x+18*u} {y+14*u} {x+18*u} {y+20*u}",stroke=color,sw=sw)
    elif name=="notifications": PATH(f"M {x+7*u} {y+17*u} L {x+17*u} {y+17*u} L {x+16*u} {y+11*u} C {x+16*u} {y+6*u} {x+8*u} {y+6*u} {x+8*u} {y+11*u} Z",stroke=color,sw=sw); LN((x+11*u,y+19.5*u),(x+13*u,y+19.5*u),stroke=color,sw=sw)
    elif name=="star":
        pts=[]
        for k in range(10):
            rr=(9 if k%2==0 else 3.7)*u; a=-math.pi/2+k*math.pi/5
            pts.append((cx+rr*math.cos(a),cy+rr*math.sin(a)))
        PATH("M "+" L ".join(f"{px} {py}" for px,py in pts)+" Z",stroke=color,sw=sw,fill="none")
    elif name=="edit": PATH(f"M {x+5*u} {y+19*u} L {x+5*u} {y+15*u} L {x+15*u} {y+5*u} L {x+19*u} {y+9*u} L {x+9*u} {y+19*u} Z",stroke=color,sw=sw)
    elif name=="share":
        DOT(x+7*u,cy,2.4*u,stroke=color,sw=sw); DOT(x+17*u,y+7*u,2.4*u,stroke=color,sw=sw); DOT(x+17*u,y+17*u,2.4*u,stroke=color,sw=sw)
        LN((x+9*u,y+11*u),(x+15*u,y+8*u),stroke=color,sw=sw); LN((x+9*u,y+13*u),(x+15*u,y+16*u),stroke=color,sw=sw)
    elif name=="chevron": PATH(f"M {x+9*u} {y+7*u} L {x+15*u} {cy} L {x+9*u} {y+17*u}",stroke=color,sw=sw)
    elif name=="chevron-d": PATH(f"M {x+7*u} {y+9*u} L {cx} {y+15*u} L {x+17*u} {y+9*u}",stroke=color,sw=sw)
    elif name=="mail": R([x+4*u,y+7*u,16*u,10*u],stroke=color,sw=sw,radius=1*u); PATH(f"M {x+4*u} {y+8*u} L {cx} {y+13*u} L {x+20*u} {y+8*u}",stroke=color,sw=sw)
    elif name=="calendar": R([x+5*u,y+6*u,14*u,14*u],stroke=color,sw=sw,radius=2*u); LN((x+5*u,y+10*u),(x+19*u,y+10*u),stroke=color,sw=sw); LN((x+9*u,y+4*u),(x+9*u,y+7*u),stroke=color,sw=sw); LN((x+15*u,y+4*u),(x+15*u,y+7*u),stroke=color,sw=sw)
    else: DOT(cx,cy,3*u,stroke=color,sw=sw)   # fallback dot

# ============================================================ page chrome
SECN=[""]
def newpage(section,title,*,bg=SC_LOW,tone=PRIMARY,dark=False):
    global L,_N; _N[0]+=1; n=_N[0]
    pg=b.page(f"p{n}", canvas={"size":[W,H],"units":"px"}, coordinate_mode="absolute")
    L=pg.layer("main"); R([0,0,W,H],fill=bg)
    if title is None: return pg   # bespoke page (cover) draws its own
    tink = D_ON_SURFACE if dark else INK; tsub = D_ON_SURFACE_V if dark else FAINT
    tacc = D_PRIMARY if dark else tone; trule = "#38343D" if dark else OUTLINE_V
    R([MX,58,26,4],fill=tacc,radius=2)
    T(MX,74,W-2*MX,section.upper(),size=11,color=tacc,weight=600,spacing=1.6)
    T(MX,92,W-2*MX-40,title,size=30,color=tink,weight=500,lh=1.05)
    LN((MX,150),(W-MX,150),stroke=trule,sw=1)
    LN((MX,H-52),(W-MX,H-52),stroke=("#2A272E" if dark else HAIR),sw=1)
    T(MX,H-42,600,"Android 16 · Material 3 Expressive",size=10,color=tsub,weight=500)
    T(W-MX-160,H-42,160,f"{n:02d} / 64",size=10,color=tsub,weight=600,align="right",mono=True)
    return pg
def bodytop(): return 176
def caption(x,y,w,t): T(x,y,w,t,size=11.5,color=MUTE,lh=1.45)
def spec_chip(x,y,t,c=PRIMARY):
    w=len(t)*6.6+22; PILL([x,y,w,20],fill="none",stroke=c,sw=1); T(x,y+4,w,t,size=10.5,color=c,weight=600,align="center",mono=True); return w

# ============================================================ Material component kit (primitives only)
def m_button(x,y,label,kind="filled",*,icon_name=None,w=None,tone=PRIMARY):
    tw=len(label)*8.4+ (30 if not icon_name else 52); w=w or tw; h=40
    if kind=="filled": R([x,y,w,h],fill=tone,radius=20)
    elif kind=="tonal": R([x,y,w,h],fill=SECONDARY_C,radius=20)
    elif kind=="elevated": SH([x,y,w,h],fill=SC_LOW,radius=20,elev=1)
    elif kind=="outlined": R([x,y,w,h],fill="none",stroke=OUTLINE,sw=1.2,radius=20)
    elif kind=="text": pass
    fg=ON_PRIMARY if kind=="filled" else (ON_SECONDARY_C if kind=="tonal" else tone)
    ix=x+18
    if icon_name: icon(icon_name,x+16,y+8,18,fg,sw=1.8); ix=x+40
    T(ix,y+12,w-(ix-x)-8,label,size=14,color=fg,weight=500)
    return w
def m_fab(x,y,icon_name="add",size="regular",*,label=None,tone=PRIMARY_C,fg=ON_PRIMARY_C):
    d={"small":40,"regular":56,"large":96}.get(size,56); r={"small":12,"regular":16,"large":28}.get(size,16)
    if label:
        w=len(label)*8.6+72; SH([x,y,w,56],fill=tone,radius=16,elev=3); icon(icon_name,x+18,y+16,24,fg); T(x+50,y+18,w-58,label,size=15,color=fg,weight=500); return w
    SH([x,y,d,d],fill=tone,radius=r,elev=3); icon(icon_name,x+(d-24)/2,y+(d-24)/2,24,fg); return d
def m_chip(x,y,label,kind="assist",*,selected=False,icon_name=None):
    w=len(label)*7.4+(26 if not icon_name else 46)+(20 if kind in("filter","input") else 0); h=32
    fill=SECONDARY_C if selected else "none"; st=None if selected else OUTLINE_V
    R([x,y,w,h],fill=(fill if selected else SURFACE),stroke=st,sw=1,radius=8)
    ix=x+12
    if kind=="filter" and selected: icon("check",x+8,y+7,18,ON_SECONDARY_C,1.8); ix=x+30
    elif icon_name: icon(icon_name,x+8,y+7,18,ON_SURFACE_V,1.8); ix=x+30
    T(ix,y+8,w-(ix-x)-8,label,size=13,color=(ON_SECONDARY_C if selected else ON_SURFACE),weight=500)
    if kind=="input": icon("close",x+w-24,y+7,18,ON_SURFACE_V,1.6)
    return w
def m_card(x,y,w,h,kind="elevated"):
    if kind=="elevated": SH([x,y,w,h],fill=SC_LOW,radius=12,elev=1)
    elif kind=="filled": R([x,y,w,h],fill=SC_HIGH,radius=12)
    else: R([x,y,w,h],fill=SURFACE,stroke=OUTLINE_V,sw=1,radius=12)
def m_textfield(x,y,w,label,kind="filled",*,value=None,state="enabled"):
    h=56; ac=PRIMARY if state=="focused" else (ERROR if state=="error" else OUTLINE)
    if kind=="filled":
        R([x,y,w,h],fill=SURFACE_V,radius=0); R([x,y,w,h],fill=SURFACE_V,radius=4)
        LN((x,y+h),(x+w,y+h),stroke=ac,sw=(2 if state=="focused" else 1.4))
        T(x+16,y+8,w-32,label,size=12,color=(ac if state in("focused","error") else ON_SURFACE_V))
        if value: T(x+16,y+26,w-32,value,size=16,color=ON_SURFACE)
    else:
        R([x,y,w,h],fill="none",stroke=ac,sw=(2 if state=="focused" else 1.2),radius=6)
        R([x+12,y-8,len(label)*6.8+8,16],fill=SURFACE)
        T(x+16,y-6,200,label,size=12,color=(ac if state in("focused","error") else ON_SURFACE_V))
        if value: T(x+16,y+18,w-32,value,size=16,color=ON_SURFACE)
    if state=="focused": DOT(x+w-22,y+28,3,fill=PRIMARY)
def m_switch(x,y,on=True):
    if on: PILL([x,y,52,32],fill=PRIMARY); DOT(x+36,y+16,11,fill=ON_PRIMARY)
    else: PILL([x,y,52,32],fill=SURFACE_V,stroke=OUTLINE,sw=2); DOT(x+16,y+16,7,fill=OUTLINE)
def m_checkbox(x,y,on=True):
    if on: R([x,y,20,20],fill=PRIMARY,radius=4); icon("check",x-1,y-1,22,ON_PRIMARY,2)
    else: R([x,y,20,20],fill="none",stroke=ON_SURFACE_V,sw=2,radius=4)
def m_radio(x,y,on=True):
    DOT(x+10,y+10,9,stroke=(PRIMARY if on else ON_SURFACE_V),sw=2)
    if on: DOT(x+10,y+10,5,fill=PRIMARY)
def m_slider(x,y,w,frac=0.4,discrete=False):
    LN((x,y),(x+w,y),stroke=SURFACE_V,sw=4); LN((x,y),(x+w*frac,y),stroke=PRIMARY,sw=4)
    DOT(x+w*frac,y,10,fill=PRIMARY)
    if discrete:
        for i in range(5): DOT(x+i*w/4,y,2,fill=(ON_PRIMARY if i/4<=frac else OUTLINE))
def m_topbar(x,y,w,title,*,center=False,nav="menu",actions=("search","more")):
    R([x,y,w,64],fill=SC)
    icon(nav,x+16,y+20,24,ON_SURFACE)
    if center: T(x,y+20,w,title,size=22,color=ON_SURFACE,weight=500,align="center")
    else: T(x+64,y+19,w-200,title,size=22,color=ON_SURFACE,weight=400)
    ax=x+w-48
    for a in reversed(actions): icon(a,ax,y+20,24,ON_SURFACE); ax-=48
def m_navbar(x,y,w,items,active=0):
    R([x,y,w,80],fill=SC); n=len(items); cw=w/n
    for i,(ic,lb) in enumerate(items):
        cxx=x+cw*i+cw/2
        if i==active: PILL([cxx-32,y+12,64,32],fill=SECONDARY_C)
        icon(ic,cxx-12,y+16,24,(ON_SECONDARY_C if i==active else ON_SURFACE_V))
        T(cxx-cw/2,y+50,cw,lb,size=12,color=(ON_SURFACE if i==active else ON_SURFACE_V),weight=500,align="center")
def m_listitem(x,y,w,title,sub=None,*,lead="person",trail=None,h=None):
    h=h or (72 if sub else 56)
    if lead: DOT(x+28,y+h/2,20,fill=PRIMARY_C); icon(lead,x+16,y+h/2-12,24,ON_PRIMARY_C,1.8)
    tx=x+(64 if lead else 16)
    T(tx,y+(16 if sub else h/2-10),w-tx+x-60,title,size=16,color=ON_SURFACE,weight=400)
    if sub: T(tx,y+38,w-tx+x-60,sub,size=14,color=ON_SURFACE_V)
    if trail: icon(trail,x+w-40,y+h/2-12,24,ON_SURFACE_V,1.8)
    return h
def m_phone(x,y,w,h):
    SH([x,y,w,h],fill=SURFACE,radius=34,elev=2); R([x,y,w,h],fill="none",stroke=OUTLINE_V,sw=1.4,radius=34)
    R([x+w/2-34,y+10,68,20],fill=INK,radius=10)  # status pill / camera
    return (x+8,y+40,w-16,h-56)  # inner content box
def swatch(x,y,w,h,fill,name,tone_label=None,*,text=ON_SURFACE,border=False):
    R([x,y,w,h],fill=fill,radius=8,stroke=(OUTLINE_V if border else None),sw=1)
    T(x+12,y+h-40,w-16,name,size=12,color=text,weight=600,lh=1.2)
    T(x+12,y+h-22,w-16,fill.upper(),size=10,color=text,mono=True)
    if tone_label: T(x+w-40,y+10,32,tone_label,size=10,color=text,mono=True,align="right")

# ============================================================ PAGES
def p_cover():
    newpage("","")
    R([0,0,W,H],fill=PRIMARY)
    R([0,0,W,H],fill=PRIMARY)
    # expressive shape cluster (primitive squircle-ish + circle + pill)
    # expressive shape cluster — kept in the upper-right, clear of the title and the meta strip
    R([W-350,-110,420,420],fill=D_PRIMARY_C,radius=210,fo=0.20)
    DOT(W-120,286,92,fill=TERTIARY_C)
    R([W-286,116,150,150],fill=SECONDARY_C,radius=54,fo=0.9)
    # wordmark bracket
    R([MX,150,6,150],fill=ON_PRIMARY); R([MX,150,44,6],fill=ON_PRIMARY); R([MX,294,44,6],fill=ON_PRIMARY)
    T(MX+64,150,300,"M3",size=88,color=ON_PRIMARY,weight=600)
    T(MX,430,W-2*MX,"Android 16",size=92,color=ON_PRIMARY,weight=600,lh=1.0)
    T(MX,540,W-2*MX,"Material 3 Expressive",size=54,color=PRIMARY_C,weight=300,lh=1.0)
    T(MX,632,W-2*MX-40,"A complete visual reference to the UI guidelines for building Android apps — "
      "foundations, colour, type, shape, motion, and the full component library, drawn entirely from primitives.",
      size=18,color="#EFE7FF",lh=1.5)
    # meta strip
    LN((MX,H-210),(W-MX,H-210),stroke="#FFFFFF55",sw=1)
    for i,(v,k) in enumerate([("64","A4 pages"),("15","type styles"),("26","colour roles"),("35","M3E shapes")]):
        xx=MX+i*200; T(xx,H-190,180,v,size=34,color=ON_PRIMARY,weight=600); T(xx,H-146,180,k.upper(),size=11,color=PRIMARY_C,weight=600,spacing=1.2)
    T(MX,H-90,W-2*MX,"Grounded in public Material 3 / M3 Expressive guidance · Generated with the FrameGraph SDK, primitives only · 2026-07",
      size=11,color="#D6C8F5",mono=True)

def p_contents():
    newpage("Reference","Contents")
    y=bodytop(); groups=[
        ("Foundations","03  Overview & principles   ·   05  Layout & grid   ·   07  Spacing   ·   08  Breakpoints   ·   09  Adaptive layout"),
        ("Colour","10  Roles   ·   11  Tonal palettes   ·   12  Baseline light   ·   13  Baseline dark   ·   14  Dynamic colour"),
        ("Typography","15  Type system   ·   16  Display & headline   ·   17  Title · body · label   ·   18  Emphasized (M3E)"),
        ("Shape · elevation · motion","19  Shape scale   ·   20  M3E shapes   ·   21  Elevation   ·   22  Motion springs"),
        ("Iconography","23  Icon system   ·   24  Icon anatomy"),
        ("Components","25  Overview   ·   26–34  Actions & selection   ·   35–42  Containment & communication   ·   43–54  Navigation & more"),
        ("Patterns","55–57  Composed screens   ·   58  Large screen   ·   59  Predictive back & edge-to-edge   ·   60  Live updates"),
        ("Accessibility & close","61–62  Accessibility   ·   63  Do & don't   ·   64  Colophon & sources")]
    for i,(g,items) in enumerate(groups):
        yy=y+i*138
        R([MX,yy,W-2*MX,120],fill=SURFACE,radius=12,stroke=OUTLINE_V,sw=1); R([MX,yy,5,120],fill=PRIMARY,radius=2)
        T(MX+22,yy+18,W-2*MX-40,g,size=20,color=INK,weight=500)
        T(MX+22,yy+54,W-2*MX-44,items,size=14,color=MUTE,lh=1.5)

def p_overview():
    newpage("Foundations","What is Material 3 Expressive?")
    y=bodytop()
    T(MX,y,W-2*MX-20,"Material 3 Expressive is the design language for Android 16 and Wear OS, introduced in "
      "May 2025. It extends Material 3 (“Material You”) with richer colour, a spring-based motion "
      "system, a larger shape library, emphasized typography, and an upgraded component suite — built to "
      "feel modern, emotive, and personal while remaining highly usable.",size=17,color=ON_SURFACE,lh=1.55)
    # three principle cards
    py=y+150; pw=(W-2*MX-2*20)/3
    for i,(t,d,c,cc) in enumerate([("Personal","Dynamic colour derives a full scheme from the user's wallpaper — every app adapts to the person.",PRIMARY,PRIMARY_C),
                                   ("Adaptive","One design system flexes across phones, foldables, tablets and Wear via window size classes.",TERTIARY,TERTIARY_C),
                                   ("Expressive","Deeper tones, spring motion, 35 shapes and emphasized type direct attention and add delight.",SECONDARY,SECONDARY_C)]):
        xx=MX+i*(pw+20); R([xx,py,pw,180],fill=cc,radius=16)
        DOT(xx+34,py+40,16,fill=c); T(xx+22,py+70,pw-40,t,size=22,color=INK,weight=500); T(xx+22,py+106,pw-40,d,size=13.5,color=ON_SURFACE_V,lh=1.45)
    # research + what's new
    ry=py+220
    SH([MX,ry,W-2*MX,150],fill=SURFACE,radius=16,elev=1)
    T(MX+24,ry+20,W-2*MX-48,"The most-researched update since Material launched in 2014",size=18,color=INK,weight=500)
    T(MX+24,ry+52,W-2*MX-48,"46 studies · 18,000+ participants informed the expressive system.",size=14,color=MUTE)
    for i,(v,k) in enumerate([("15","new / refreshed components"),("35","decorative shapes"),("2","motion spring types"),("15","type styles + 15 emphasized")]):
        xx=MX+24+i*((W-2*MX-48)/4); T(xx,ry+90,220,v,size=30,color=PRIMARY,weight=600); T(xx,ry+128,220,k,size=11.5,color=MUTE)
    T(MX,ry+180,W-2*MX,"This reference depicts every foundation and component below using FrameGraph primitives only — "
      "rectangles, text, lines, circles and paths — so each specimen is exact, inspectable geometry.",size=13,color=MUTE,lh=1.5)

def p_principles():
    newpage("Foundations","Design principles in practice")
    y=bodytop()
    rows=[("Make it personal","Lead with dynamic colour and user choice.","Let the scheme flow from the wallpaper; don't hard-code brand colour over system tone.",PRIMARY),
          ("Direct attention","Use emphasis, not clutter.","One high-emphasis action (a filled button or FAB) per view; everything else recedes in tone.",SECONDARY),
          ("Adapt, don't reflow","Design for size classes.","Bottom nav → navigation rail → drawer as width grows; content panes appear, they don't just stretch.",TERTIARY),
          ("Move with meaning","Spring, don't tween.","Spatial springs move position/size; effect springs handle colour/opacity — motion communicates state.",PRIMARY),
          ("Stay legible","Expression never costs usability.","Keep 48dp targets, 4.5:1 text contrast, and the type scale intact under all themes and scaling.",ERROR)]
    for i,(t,lead,d,c) in enumerate(rows):
        yy=y+i*196
        SH([MX,yy,W-2*MX,176],fill=SURFACE,radius=14,elev=1); R([MX,yy,6,176],fill=c,radius=3)
        T(MX+28,yy+22,60,f"{i+1:02d}",size=30,color=c,weight=600,mono=True)
        T(MX+108,yy+24,W-2*MX-140,t,size=22,color=INK,weight=500)
        T(MX+108,yy+60,W-2*MX-140,lead,size=15,color=c,weight=500)
        T(MX+108,yy+90,W-2*MX-140,d,size=14.5,color=MUTE,lh=1.5)

def p_layout():
    newpage("Foundations","Layout & the 4dp grid")
    y=bodytop()
    caption(MX,y,W-2*MX,"Material aligns everything to a 4dp base grid; 8dp is the default step for margins, padding and "
            "gaps. Columns, gutters and margins scale with the window size class.")
    # grid demo phone
    gx,gy,gw,gh=MX,y+70,300,560; cb=m_phone(gx,gy,gw,gh)
    R([cb[0]+16,cb[1]+16,cb[2]-32,cb[3]-32],fill=SC,radius=8)
    for i in range(4):
        col=cb[0]+28+i*((cb[2]-56)/4); R([col,cb[1]+28,(cb[2]-56)/4-10,cb[3]-56],fill=PRIMARY_C,fo=0.5,radius=4)
    T(gx,gy+gh+14,gw,"4-column compact grid · 16dp margins · 8dp gutters",size=12,color=MUTE,align="center")
    # spacing tokens
    sx=gx+gw+50
    T(sx,y+70,300,"Spacing steps (dp)",size=16,color=INK,weight=500)
    for i,v in enumerate([4,8,12,16,24,32,48]):
        yy=y+108+i*54; R([sx,yy+6,v*3,24],fill=PRIMARY,radius=4)
        T(sx+160,yy+10,120,f"{v} dp",size=15,color=INK,weight=500,mono=True)
        T(sx+230,yy+11,240,["hairline","default gap","compact pad","standard pad","section","large","xl"][i],size=12,color=MUTE)
    T(sx,y+108+7*54+8,380,"Touch targets stay ≥ 48dp regardless of the visual size of the element inside them.",size=13,color=MUTE,lh=1.5)

def p_spacing():
    newpage("Foundations","Density, alignment & keylines")
    y=bodytop()
    caption(MX,y,W-2*MX,"Keylines anchor content to consistent edges. The standard content keyline is 16dp from the screen "
            "edge; a 72dp keyline aligns text beside a leading 24dp icon or 40dp avatar.")
    gx,gy,gw,gh=MX,y+70,300,560; cb=m_phone(gx,gy,gw,gh)
    R([cb[0]+16,cb[1]+16,cb[2]-32,cb[3]-32],fill=SURFACE,radius=8)
    LN((cb[0]+16+16,cb[1]+16),(cb[0]+16+16,cb[1]+cb[3]-32),stroke=ERROR,sw=1,dash=[4,4])
    LN((cb[0]+16+72,cb[1]+16),(cb[0]+16+72,cb[1]+cb[3]-32),stroke=TERTIARY,sw=1,dash=[4,4])
    for i in range(3):
        yy=cb[1]+44+i*88; m_listitem(cb[0]+16,yy,cb[2]-32,"List item title","Supporting line of text")
    T(gx,gy+gh+14,gw,"16dp content keyline · 72dp text keyline",size=12,color=MUTE,align="center")
    sx=gx+gw+50
    for t,d in [("Comfortable","Default touch density for phones — 56–72dp list rows, 48dp targets."),
                ("Compact","Denser rows for information-dense or large-screen surfaces."),
                ("Alignment","Optical alignment beats mathematical when icons and text mix.")]:
        pass
    items=[("16 dp","standard content margin",PRIMARY),("24 dp","icon-to-text on the 72dp keyline",TERTIARY),
           ("8 dp","default gap between related elements",SECONDARY),("48 dp","minimum interactive target",ERROR)]
    for i,(v,d,c) in enumerate(items):
        yy=y+90+i*116; SH([sx,yy,380,96],fill=SURFACE,radius=12,elev=1); R([sx,yy,5,96],fill=c,radius=2)
        T(sx+22,yy+18,340,v,size=24,color=c,weight=600,mono=True); T(sx+22,yy+56,340,d,size=14,color=MUTE,lh=1.4)

def p_breakpoints():
    newpage("Foundations","Window size classes")
    y=bodytop()
    caption(MX,y,W-2*MX,"Size classes are breakpoints for the available window width (and height). They drive which "
            "navigation pattern and how many panes a layout uses — the core of adaptive design.")
    rows=[("Compact","< 600 dp","Phone portrait","Bottom navigation bar · single pane",PRIMARY,PRIMARY_C),
          ("Medium","600 – 839 dp","Foldable · phone landscape","Navigation rail · 1–2 panes",SECONDARY,SECONDARY_C),
          ("Expanded","840 – 1199 dp","Tablet · unfolded","Navigation rail or drawer · 2 panes",TERTIARY,TERTIARY_C),
          ("Large","1200 – 1599 dp","Desktop · large tablet","Navigation drawer · 2+ panes",PRIMARY,PRIMARY_C),
          ("Extra-large","≥ 1600 dp","Large desktop","Permanent drawer · multi-pane",SECONDARY,SECONDARY_C)]
    for i,(t,rng,dev,nav,c,cc) in enumerate(rows):
        yy=y+70+i*208
        SH([MX,yy,W-2*MX,188],fill=SURFACE,radius=14,elev=1)
        # mini device glyph scaled to class
        gw=90+i*46; R([MX+24,yy+40,gw,108],fill=cc,radius=8,stroke=c,sw=1)
        R([MX+34,yy+50,gw-20,20],fill=c,fo=0.5,radius=3)
        if i>=1: R([MX+34,yy+78,26,60],fill=c,fo=0.5,radius=3)
        T(MX+360,yy+24,300,t,size=24,color=INK,weight=500); T(MX+360,yy+60,300,rng,size=16,color=c,weight=600,mono=True)
        T(MX+360,yy+92,W-2*MX-390,"Typical: "+dev,size=14,color=MUTE)
        T(MX+360,yy+120,W-2*MX-390,"Navigation: "+nav,size=14,color=ON_SURFACE)

def p_adaptive():
    newpage("Foundations","Adaptive navigation & canonical layouts")
    y=bodytop()
    caption(MX,y,W-2*MX,"As width grows, navigation migrates from a bottom bar to a rail to a drawer, and content "
            "gains panes. Three canonical layouts cover most apps: list-detail, supporting pane, and feed.")
    # three device widths showing nav migration
    devs=[("Compact","Bottom bar",PRIMARY_C,PRIMARY),("Medium","Nav rail",TERTIARY_C,TERTIARY),("Expanded","Rail + 2 panes",SECONDARY_C,SECONDARY)]
    dw=[150,220,300]; dx=MX; yy=y+64
    for i,(t,nav,cc,c) in enumerate(devs):
        w=dw[i]; SH([dx,yy,w,300],fill=SURFACE,radius=12,elev=1)
        if i==0:
            R([dx,yy+270,w,30],fill=cc);
            for k in range(3): DOT(dx+w/6+k*w/3,yy+285,5,fill=c)
            R([dx+12,yy+12,w-24,246],fill=SC,radius=6)
        else:
            R([dx,yy,44,300],fill=cc)
            for k in range(4): DOT(dx+22,yy+40+k*46,6,fill=c)
            if i==1: R([dx+56,yy+12,w-68,276],fill=SC,radius=6)
            else: R([dx+56,yy+12,(w-72)*0.4,276],fill=SC,radius=6); R([dx+56+(w-72)*0.4+8,yy+12,(w-72)*0.6,276],fill=SC_HIGH,radius=6)
        T(dx,yy+314,w,t,size=14,color=INK,weight=500,align="center"); T(dx,yy+334,w,nav,size=12,color=c,weight=500,align="center")
        dx+=w+40
    ly=yy+380
    for i,(t,d) in enumerate([("List-detail","A list pane drives a detail pane (mail, settings, contacts)."),
                              ("Supporting pane","A primary pane with a secondary supporting pane (editor + tools)."),
                              ("Feed","A resizable grid of equal cards that reflows by column count.")]):
        xx=MX+i*((W-2*MX-2*20)/3+20); wpp=(W-2*MX-2*20)/3
        SH([xx,ly,wpp,150],fill=SURFACE,radius=12,elev=1)
        if i==0: R([xx+16,ly+16,wpp*0.32,118],fill=PRIMARY_C,radius=6); R([xx+16+wpp*0.32+8,ly+16,wpp-40-wpp*0.32,118],fill=SC,radius=6)
        elif i==1: R([xx+16,ly+16,wpp-70,118],fill=SC,radius=6); R([xx+wpp-46,ly+16,30,118],fill=TERTIARY_C,radius=6)
        else:
            for r in range(2):
                for cc2 in range(3): R([xx+16+cc2*((wpp-32)/3),ly+16+r*60,(wpp-32)/3-8,52],fill=SC_HIGH,radius=6)
        T(xx+16,ly+164,wpp,t,size=15,color=INK,weight=500); T(xx+16,ly+188,wpp,d,size=12,color=MUTE,lh=1.4)

def p_color_roles():
    newpage("Colour","Colour roles")
    y=bodytop()
    caption(MX,y,W-2*MX,"Material defines 26 semantic colour roles across six groups. Roles — not raw hex — connect UI "
            "elements to meaning. “On” roles pair text/icons onto a parent; “Container” roles fill components.")
    groups=[("Primary",PRIMARY,ON_PRIMARY,PRIMARY_C,ON_PRIMARY_C,"FAB · high-emphasis buttons · active states"),
            ("Secondary",SECONDARY,ON_SECONDARY,SECONDARY_C,ON_SECONDARY_C,"Filter chips · less-prominent components"),
            ("Tertiary",TERTIARY,ON_TERTIARY,TERTIARY_C,ON_TERTIARY_C,"Badges · contrasting accents"),
            ("Error",ERROR,ON_ERROR,ERROR_C,ON_ERROR_C,"Errors · destructive actions")]
    for i,(t,base,on,cont,oncont,use) in enumerate(groups):
        yy=y+70+i*118
        T(MX,yy,200,t,size=17,color=INK,weight=500); T(MX,yy+26,200,use,size=11.5,color=MUTE,lh=1.35)
        cx=MX+230; cw=(W-2*MX-230)/4-10
        for j,(lab,fl,tx) in enumerate([(t,base,on),("On "+t,on,base),(t+" cont.",cont,oncont),("On "+t+" c.",oncont,cont)]):
            xx=cx+j*(cw+10); R([xx,yy,cw,96],fill=fl,radius=8,stroke=(OUTLINE_V if fl in(ON_PRIMARY,ON_SECONDARY) else None),sw=1)
            T(xx+10,yy+62,cw-16,lab,size=11,color=tx,weight=600,lh=1.15); T(xx+10,yy+80,cw-16,fl.upper(),size=9,color=tx,mono=True)
    yy=y+70+4*118
    T(MX,yy,W-2*MX,"Surface & outline",size=17,color=INK,weight=500)
    surfs=[("Surface",SURFACE,ON_SURFACE),("Surf. variant",SURFACE_V,ON_SURFACE_V),("SC low",SC_LOW,ON_SURFACE),("SC high",SC_HIGH,ON_SURFACE),("Outline",OUTLINE,"#FFFFFF"),("Outline var.",OUTLINE_V,ON_SURFACE)]
    cw=(W-2*MX)/6-10
    for j,(lab,fl,tx) in enumerate(surfs):
        xx=MX+j*(cw+12); R([xx,yy+30,cw,80],fill=fl,radius=8,stroke=OUTLINE_V,sw=1)
        T(xx+8,yy+30+48,cw-12,lab,size=10.5,color=tx,weight=600,lh=1.1); T(xx+8,yy+30+64,cw-12,fl.upper(),size=8.5,color=tx,mono=True)

def p_tonal():
    newpage("Colour","Tonal palettes")
    y=bodytop()
    caption(MX,y,W-2*MX,"A seed colour generates six tonal palettes — Primary, Secondary, Tertiary, Error, Neutral, and "
            "Neutral Variant. Each holds 13 tones from 0 (black) to 100 (white). Roles map to specific tones.")
    tones=[0,10,20,30,40,50,60,70,80,90,95,99,100]
    def ramp(base,g,yy):
        T(MX,yy-2,150,g,size=14,color=INK,weight=500)
        cw=(W-2*MX-150)/len(tones)
        for i,tn in enumerate(tones):
            # approximate the tone by mixing base toward black/white
            xx=MX+150+i*cw; L.rect([xx,yy,cw-2,54],fill=_tone(base,tn),radius=(4 if i in(0,len(tones)-1) else 0))
            T(xx,yy+58,cw,str(tn),size=9,color=MUTE,align="center",mono=True)
    pals=[("Primary",PRIMARY),("Secondary",SECONDARY),("Tertiary",TERTIARY),("Error",ERROR),("Neutral","#605D62"),("Neutral variant",ON_SURFACE_V)]
    for i,(g,base) in enumerate(pals):
        ramp(base,g,y+80+i*104)
    T(MX,y+80+6*104,W-2*MX,"Role → tone (light / dark):  Primary = T40 / T80   ·   On Primary = T100 / T20   ·   "
      "Primary Container = T90 / T30   ·   Surface = N98 / N6.   Dark themes lift base roles to a higher tone.",
      size=12,color=MUTE,lh=1.5)

def _tone(hexc,tn):
    r=int(hexc[1:3],16);g=int(hexc[3:5],16);bb=int(hexc[5:7],16)
    if tn>=50:
        f=(tn-40)/60.0; r=int(r+(255-r)*f);g=int(g+(255-g)*f);bb=int(bb+(255-bb)*f)
    else:
        f=1-(tn/50.0); r=int(r*(1-f));g=int(g*(1-f));bb=int(bb*(1-f))
    return "#%02X%02X%02X"%(max(0,min(255,r)),max(0,min(255,g)),max(0,min(255,bb)))

def p_baseline_light():
    newpage("Colour","Baseline scheme — light")
    y=bodytop()
    caption(MX,y,W-2*MX,"When dynamic colour is unavailable, Material ships a baseline scheme seeded on #6750A4. "
            "These are the light-theme role values; dark inverts the tonal relationships.")
    rolesL=[("Primary",PRIMARY,ON_PRIMARY),("On Primary",ON_PRIMARY,PRIMARY),("Primary Container",PRIMARY_C,ON_PRIMARY_C),("On Primary Cont.",ON_PRIMARY_C,PRIMARY_C),
            ("Secondary",SECONDARY,ON_SECONDARY),("Secondary Cont.",SECONDARY_C,ON_SECONDARY_C),("Tertiary",TERTIARY,ON_TERTIARY),("Tertiary Cont.",TERTIARY_C,ON_TERTIARY_C),
            ("Error",ERROR,ON_ERROR),("Error Container",ERROR_C,ON_ERROR_C),("Surface",SURFACE,ON_SURFACE),("On Surface",ON_SURFACE,SURFACE),
            ("Surface Variant",SURFACE_V,ON_SURFACE_V),("On Surface Var.",ON_SURFACE_V,SURFACE_V),("Outline",OUTLINE,"#FFFFFF"),("Outline Variant",OUTLINE_V,ON_SURFACE)]
    cw=(W-2*MX-3*16)/4; ch=140
    for i,(lab,fl,tx) in enumerate(rolesL):
        xx=MX+(i%4)*(cw+16); yy=y+64+(i//4)*(ch+16)
        R([xx,yy,cw,ch],fill=fl,radius=10,stroke=(OUTLINE_V if fl in(ON_PRIMARY,SURFACE) else None),sw=1)
        T(xx+12,yy+ch-46,cw-18,lab,size=12,color=tx,weight=600,lh=1.15); T(xx+12,yy+ch-24,cw-18,fl.upper(),size=10,color=tx,mono=True)

def p_baseline_dark():
    newpage("Colour","Baseline scheme — dark",bg="#0F0D13",dark=True)
    global L
    y=bodytop()
    T(MX,y,W-2*MX,"Dark themes raise base roles to higher tones and lower surfaces to N6–N24, preserving contrast and "
      "hierarchy. Elevation is expressed by lighter surface-container tones rather than heavier shadow.",size=11.5,color=D_ON_SURFACE_V,lh=1.45)
    rolesD=[("Primary",D_PRIMARY,D_ON_PRIMARY),("On Primary",D_ON_PRIMARY,D_PRIMARY),("Primary Container",D_PRIMARY_C,D_ON_PRIMARY_C),("On Primary Cont.",D_ON_PRIMARY_C,D_PRIMARY_C),
            ("Secondary",D_SECONDARY,"#332D41"),("Tertiary",D_TERTIARY,"#492532"),("Error","#F2B8B5","#601410"),("Error Container","#8C1D18","#F9DEDC"),
            ("Surface",D_SURFACE,D_ON_SURFACE),("On Surface",D_ON_SURFACE,D_SURFACE),("Surface Variant",D_SURFACE_V,D_ON_SURFACE_V),("On Surface Var.",D_ON_SURFACE_V,D_SURFACE_V),
            ("Surf. Cont. High","#2B2930",D_ON_SURFACE),("Surf. Cont.","#211F26",D_ON_SURFACE),("Outline",D_OUTLINE,"#000000"),("Outline Variant","#49454F",D_ON_SURFACE)]
    cw=(W-2*MX-3*16)/4; ch=140
    for i,(lab,fl,tx) in enumerate(rolesD):
        xx=MX+(i%4)*(cw+16); yy=y+64+(i//4)*(ch+16)
        L.rect([xx,yy,cw,ch],fill=fl,radius=10,stroke="#38343D",stroke_style={"stroke_width":1})
        st={"font_family":SANS,"font_size":12,"color":tx,"font_weight":600}
        L.text([xx+12,yy+ch-46,cw-18,30],lab,style=st)
        L.text([xx+12,yy+ch-24,cw-18,16],fl.upper(),style={"font_family":MONO,"font_size":10,"color":tx})

def p_dynamic():
    newpage("Colour","Dynamic colour — Material You")
    y=bodytop()
    caption(MX,y,W-2*MX,"On Android 12+, the system extracts a seed from the wallpaper and generates the full scheme at "
            "runtime. Apps that use colour roles automatically personalise — no manual theming per device.")
    seeds=[("#4285F4","Blue wallpaper"),("#0F9D58","Green wallpaper"),("#DB4437","Warm wallpaper"),("#7D5260","Muted wallpaper")]
    cw=(W-2*MX-3*20)/4
    for i,(seed,lab) in enumerate(seeds):
        xx=MX+i*(cw+20); SH([xx,y+64,cw,360],fill=SURFACE,radius=16,elev=1)
        DOT(xx+cw/2,y+110,28,fill=seed); T(xx,y+150,cw,lab,size=12,color=MUTE,align="center")
        # generated mini-scheme
        for k,tn in enumerate([40,80,90,30]):
            R([xx+20,y+180+k*54,cw-40,44],fill=_tone(seed,tn),radius=8)
            T(xx+30,y+180+k*54+13,cw-50,["Primary","Secondary","Container","On-container"][k],size=11,color=(_tone(seed,90) if tn<50 else _tone(seed,20)),weight=600)
    yy=y+464
    SH([MX,yy,W-2*MX,120],fill=PRIMARY_C,radius=16,elev=0)
    T(MX+24,yy+22,W-2*MX-48,"Always theme with roles, never raw hex",size=18,color=ON_PRIMARY_C,weight=500)
    T(MX+24,yy+54,W-2*MX-48,"Reading MaterialTheme.colorScheme.primary (Compose) or ?attr/colorPrimary (Views) lets the same "
      "code render correctly under baseline, dynamic, light and dark — the role is the contract.",size=13.5,color=ON_PRIMARY_C,lh=1.5)

def p_color_usage():
    newpage("Colour","Applying colour")
    y=bodytop()
    # do / dont
    for i,(head,ok,pts,c) in enumerate([("Do",True,["One high-emphasis colour (primary) per view","Pair every colour with its “On” role for text","Use containers for fills, never for text","Let tertiary carry a single contrasting accent"],HAVE_GREEN),
                                        ("Don't",False,["Don't place on-surface text on primary","Don't use more than one FAB / primary action","Don't hard-code hex that ignores dark theme","Don't rely on colour alone to signal state"],ERROR)]):
        xx=MX+i*((W-2*MX-24)/2+24); wpp=(W-2*MX-24)/2
        SH([xx,y,wpp,300],fill=SURFACE,radius=14,elev=1); R([xx,y,wpp,6],fill=c,radius=3)
        icon("check" if ok else "close",xx+22,y+22,26,c,2.4); T(xx+58,y+24,wpp-70,head,size=22,color=INK,weight=500)
        for j,p in enumerate(pts): DOT(xx+30,y+82+j*46,3,fill=c); T(xx+46,y+74+j*46,wpp-70,p,size=14,color=ON_SURFACE,lh=1.35)
    yy=y+330
    T(MX,yy,W-2*MX,"Contrast floors (WCAG)",size=17,color=INK,weight=500)
    for i,(pair,ratio,ok) in enumerate([("On-surface / surface","15.8 : 1",True),("On-primary / primary","8.6 : 1",True),("Primary / surface","5.1 : 1",True),("Outline / surface","3.2 : 1",True)]):
        xx=MX+i*((W-2*MX)/4); T(xx,yy+34,240,pair,size=13,color=MUTE); T(xx,yy+56,240,ratio,size=22,color=PRIMARY,weight=600,mono=True)
        DOT(xx+150,yy+64,7,fill=HAVE_GREEN)
    T(MX,yy+110,W-2*MX,"Body text needs ≥ 4.5 : 1; large text and UI outlines ≥ 3 : 1. The baseline roles clear these floors "
      "by design — verify again for any custom or dynamic scheme.",size=13,color=MUTE,lh=1.5)

def p_type_system():
    newpage("Typography","The type system")
    y=bodytop()
    caption(MX,y,W-2*MX,"Roboto in Regular and Medium. Five roles — Display, Headline, Title, Body, Label — each in Large, "
            "Medium and Small: 15 baseline styles, plus 15 emphasized variants in M3 Expressive.")
    roles=[("Display","Short, high-impact text and numerals","57 / 45 / 36",PRIMARY),
           ("Headline","High-emphasis text on smaller screens","32 / 28 / 24",SECONDARY),
           ("Title","Medium-emphasis, relatively short","22 / 16 / 14",TERTIARY),
           ("Body","Longer passages of reading text","16 / 14 / 12",ON_SURFACE),
           ("Label","Text inside components; captions","14 / 12 / 11",OUTLINE)]
    for i,(t,d,sizes,c) in enumerate(roles):
        yy=y+70+i*112; SH([MX,yy,W-2*MX,96],fill=SURFACE,radius=12,elev=1); R([MX,yy,5,96],fill=c,radius=2)
        T(MX+24,yy+16,300,t,size={"Display":34,"Headline":28,"Title":22,"Body":18,"Label":14}[t],color=INK,weight=(500 if t in("Title","Label") else 400))
        T(MX+24,yy+62,400,d,size=13,color=MUTE)
        T(W-MX-260,yy+30,240,sizes+"  sp",size=18,color=c,weight=600,mono=True,align="right")
        T(W-MX-260,yy+62,240,"Large / Medium / Small",size=11,color=FAINT,align="right")

def p_specimen_display():
    newpage("Typography","Specimen — display & headline")
    y=bodytop()
    def row(yy,style,label):
        sz,wt=TYPE[style]; T(MX,yy,W-2*MX,"Expressive",size=min(sz,64),color=INK,weight=wt)
        T(W-MX-230,yy+min(sz,64)/2-16,230,label,size=12,color=MUTE,align="right"); T(W-MX-230,yy+min(sz,64)/2,230,f"{sz} sp · {'Medium' if wt==500 else 'Regular'}",size=11,color=FAINT,align="right",mono=True)
        LN((MX,yy+min(sz,64)+18),(W-MX,yy+min(sz,64)+18),stroke=HAIR,sw=1)
    yy=y+16
    for style,label in [("display-large","Display Large"),("display-medium","Display Medium"),("display-small","Display Small"),
                        ("headline-large","Headline Large"),("headline-medium","Headline Medium"),("headline-small","Headline Small")]:
        row(yy,style,label); sz=min(TYPE[style][0],64); yy+=sz+44

def p_specimen_body():
    newpage("Typography","Specimen — title · body · label")
    y=bodytop(); yy=y+8
    for style,label in [("title-large","Title Large"),("title-medium","Title Medium"),("title-small","Title Small")]:
        sz,wt=TYPE[style]; T(MX,yy,W-2*MX,"The quick brown fox jumps",size=sz,color=INK,weight=wt)
        T(W-MX-220,yy+2,220,f"{label} · {sz} sp",size=11,color=FAINT,align="right",mono=True); yy+=sz+30
    LN((MX,yy),(W-MX,yy),stroke=HAIR,sw=1); yy+=24
    for style,label in [("body-large","Body Large"),("body-medium","Body Medium"),("body-small","Body Small")]:
        sz,wt=TYPE[style]
        T(MX,yy,W-2*MX,"Body styles carry longer passages of reading text. Material recommends a comfortable measure and "
          "generous line height so paragraphs stay legible across sizes and themes.",size=sz,color=ON_SURFACE,lh=1.5)
        T(W-MX-220,yy,220,f"{label} · {sz} sp",size=11,color=FAINT,align="right",mono=True); yy+=sz*3.2+22
    LN((MX,yy),(W-MX,yy),stroke=HAIR,sw=1); yy+=24
    lx=MX
    for style,label in [("label-large","Label Large"),("label-medium","Label Medium"),("label-small","Label Small")]:
        sz,wt=TYPE[style]; w=len(label)*sz*0.62+40; PILL([lx,yy,w,40],fill=SECONDARY_C); T(lx,yy+12,w,label,size=sz,color=ON_SECONDARY_C,weight=wt,align="center"); lx+=w+16
    T(MX,yy+60,W-2*MX,"Label styles size the text inside components — buttons, tabs, chips — and small captions in content.",size=13,color=MUTE)

def p_emphasized():
    newpage("Typography","Emphasized type — M3 Expressive")
    y=bodytop()
    caption(MX,y,W-2*MX,"M3 Expressive adds emphasized styles: heavier weights, larger sizes, and tighter spacing that create "
            "editorial moments and pull the eye to what matters. Variable font axes make the transition fluid.")
    SH([MX,y+70,W-2*MX,220],fill=SC,radius=16,elev=0)
    T(MX+30,y+96,W-2*MX-60,"Today",size=20,color=MUTE,weight=500)
    T(MX+30,y+124,W-2*MX-60,"Good morning,",size=40,color=ON_SURFACE,weight=400)
    T(MX+30,y+176,W-2*MX-60,"Alex",size=64,color=PRIMARY,weight=700)
    T(MX+30,y+256,W-2*MX-60,"Emphasized display pulls a single word forward; the rest stays calm.",size=13,color=MUTE)
    yy=y+320
    for i,(t,d) in enumerate([("Baseline","Even weight; steady rhythm for dense, utilitarian screens."),
                              ("Emphasized","Selective heavy weight + scale for hero moments and key numbers.")]):
        xx=MX+i*((W-2*MX-24)/2+24); wpp=(W-2*MX-24)/2; SH([xx,yy,wpp,220],fill=SURFACE,radius=14,elev=1)
        T(xx+24,yy+24,wpp-48,("$1,240" ),size=(40 if i==0 else 40),color=INK,weight=(400 if i==0 else 700))
        T(xx+24,yy+84,wpp-48,"Balance",size=16,color=MUTE,weight=400)
        for k in range(3): R([xx+24,yy+124+k*24,wpp-48-(k*40),10],fill=(SURFACE_V if i==0 else PRIMARY_C),radius=5)
        T(xx+24,yy+200,wpp-48,t,size=14,color=(PRIMARY if i==1 else MUTE),weight=600); T(xx+140,yy+200,wpp-160,d,size=11.5,color=MUTE,lh=1.3)

def p_shape_scale():
    newpage("Shape · elevation · motion","The shape scale")
    y=bodytop()
    caption(MX,y,W-2*MX,"Corner radius is tokenized on a scale from None (0dp) to Full (a pill). Components pick a token so "
            "rounding stays consistent — cards use Medium, dialogs Extra-large, FABs Large, chips Small.")
    cw=(W-2*MX-6*16)/7
    for i,(name,val) in enumerate(SHAPES):
        xx=MX+i*(cw+16); r=(cw/2 if val=="pill" else val*1.4)
        R([xx,y+80,cw,cw],fill=PRIMARY_C,radius=min(r,cw/2),stroke=PRIMARY,sw=1.5)
        T(xx,y+80+cw+12,cw,name,size=11,color=INK,weight=600,align="center",lh=1.15)
        T(xx,y+80+cw+40,cw,(str(val)+" dp" if val!="pill" else "50%"),size=10,color=MUTE,align="center",mono=True)
    yy=y+80+cw+90
    T(MX,yy,W-2*MX,"Component defaults",size=17,color=INK,weight=500)
    defs=[("Chips · text fields","Small · 8dp"),("Cards · buttons(sm)","Medium · 12dp"),("FAB · buttons","Large · 16dp"),("Dialogs · sheets","Extra-large · 28dp"),("FAB pressed · pills","Full")]
    for i,(t,v) in enumerate(defs):
        xx=MX+i*((W-2*MX)/5); T(xx,yy+34,200,t,size=13,color=ON_SURFACE,lh=1.3); T(xx,yy+72,200,v,size=13,color=PRIMARY,weight=600,mono=True)
    T(MX,yy+130,W-2*MX,"Corners may be applied asymmetrically (e.g. a bottom sheet rounds only its top) and can differ per "
      "corner to signal direction or grouping.",size=13,color=MUTE,lh=1.5)

def p_m3e_shapes():
    newpage("Shape · elevation · motion","Expressive shapes & morphing")
    y=bodytop()
    caption(MX,y,W-2*MX,"M3 Expressive adds a library of 35 decorative shapes for avatars, image crops, loading indicators "
            "and hero moments — with built-in shape-morph animation (e.g. a square easing into a squircle).")
    # a grid of primitive-drawn expressive shapes
    shapes=["circle","squircle","pill","clover","flower","pentagon","hexagon","star","burst","diamond","arch","scallop"]
    cw=(W-2*MX-5*18)/6
    for i,name in enumerate(shapes):
        xx=MX+(i%6)*(cw+18); yy=y+80+(i//6)*(cw+56); cx,cy=xx+cw/2,yy+cw/2; rr=cw*0.42
        c=[PRIMARY_C,SECONDARY_C,TERTIARY_C][i%3]; sc=[PRIMARY,SECONDARY,TERTIARY][i%3]
        if name=="circle": DOT(cx,cy,rr,fill=c)
        elif name=="squircle": R([cx-rr,cy-rr,2*rr,2*rr],fill=c,radius=rr*0.55)
        elif name=="pill": R([cx-rr,cy-rr*0.7,2*rr,1.4*rr],fill=c,radius=rr*0.7)
        elif name=="diamond": PATH(f"M {cx} {cy-rr} L {cx+rr} {cy} L {cx} {cy+rr} L {cx-rr} {cy} Z",fill=c)
        elif name in("pentagon","hexagon"):
            nn=5 if name=="pentagon" else 6; pts=[(cx+rr*math.cos(-math.pi/2+k*2*math.pi/nn),cy+rr*math.sin(-math.pi/2+k*2*math.pi/nn)) for k in range(nn)]
            PATH("M "+" L ".join(f"{px} {py}" for px,py in pts)+" Z",fill=c)
        elif name in("clover","flower","scallop","burst","star"):
            nn={"clover":4,"flower":8,"scallop":10,"burst":12,"star":5}[name]; pts=[]
            for k in range(nn*2):
                out=(name in("star","burst")) and k%2==1
                rad=rr*(0.5 if out else 1.0) if name in("star","burst") else rr*(1.0 if k%2==0 else 0.62)
                a=-math.pi/2+k*math.pi/nn; pts.append((cx+rad*math.cos(a),cy+rad*math.sin(a)))
            PATH("M "+" L ".join(f"{px:.1f} {py:.1f}" for px,py in pts)+" Z",fill=c)
        elif name=="arch": R([cx-rr,cy-rr,2*rr,2*rr],fill=c,radius=rr); R([cx-rr,cy,2*rr,rr],fill=c)
        T(xx,yy+cw+8,cw,name,size=10.5,color=MUTE,align="center")
    # morph strip
    yy=y+80+2*(cw+56)+10
    T(MX,yy,300,"Shape morph",size=15,color=INK,weight=500)
    for k in range(5):
        xx=MX+40+k*((W-2*MX-80)/5); f=k/4.0; rr=42
        R([xx,yy+40,2*rr,2*rr],fill=PRIMARY,radius=rr*(0.15+0.85*f))
        if k<4: icon("chevron",xx+2*rr+2,yy+40+rr-12,24,OUTLINE)
    T(MX,yy+150,W-2*MX,"Square → squircle in five interpolated steps. On device this runs as a spring, not a linear tween.",size=12,color=MUTE)

def p_elevation():
    newpage("Shape · elevation · motion","Elevation")
    y=bodytop()
    caption(MX,y,W-2*MX,"Elevation separates surfaces along the z-axis. Material 3 expresses it with tonal surface-container "
            "colour first, and a soft shadow second. Six levels map dp height to surface tone and shadow.")
    cw=(W-2*MX-5*20)/6
    for i,(name,dp) in enumerate(ELEV):
        xx=MX+i*(cw+20); tone=[SC_LOWEST,SC_LOW,SC,SC_HIGH,SC_HIGHEST,SC_HIGHEST][i]
        SH([xx,y+90,cw,cw],fill=tone,radius=16,elev=i)
        T(xx,y+90+cw+14,cw,name,size=12,color=INK,weight=600,align="center")
        T(xx,y+90+cw+38,cw,f"{dp} dp",size=11,color=MUTE,align="center",mono=True)
    yy=y+90+cw+90
    for i,(comp,lvl) in enumerate([("Cards (resting) · search bar","Level 1 · 1dp"),("FAB · buttons(elevated)","Level 3 · 6dp"),("Nav drawer · menus","Level 2–3"),("Dialogs · modal sheets","Level 3 · 6dp"),("Dragged elements","Level 4–5")]):
        xx=MX+i*((W-2*MX)/5); T(xx,yy+10,200,comp,size=13,color=ON_SURFACE,lh=1.3); T(xx,yy+50,200,lvl,size=12,color=PRIMARY,weight=600,mono=True)
    T(MX,yy+100,W-2*MX,"In dark theme, higher elevation reads as a LIGHTER surface tone — shadows are subtle, so tonal "
      "elevation carries the hierarchy.",size=13,color=MUTE,lh=1.5)

def p_motion():
    newpage("Shape · elevation · motion","Motion — the spring system")
    y=bodytop()
    caption(MX,y,W-2*MX,"M3 Expressive replaces duration-and-easing curves with a physical spring model. Two spring types "
            "cover the system: spatial springs for movement and size, effect springs for colour and opacity.")
    for i,(t,d,c,cc) in enumerate([("Spatial springs","Position, size and layout. Slightly bouncy — objects settle like real matter.",PRIMARY,PRIMARY_C),
                                   ("Effect springs","Colour, opacity, elevation. Critically damped — no overshoot, no flicker.",TERTIARY,TERTIARY_C)]):
        xx=MX+i*((W-2*MX-24)/2+24); wpp=(W-2*MX-24)/2; SH([xx,y+70,wpp,300],fill=SURFACE,radius=16,elev=1); R([xx,y+70,wpp,6],fill=c,radius=3)
        T(xx+24,y+92,wpp-48,t,size=20,color=INK,weight=500); T(xx+24,y+128,wpp-48,d,size=13.5,color=MUTE,lh=1.45)
        # spring displacement curve, drawn from a path primitive
        bx,by,bw,bh=xx+24,y+200,wpp-48,132
        LN((bx,by+bh),(bx+bw,by+bh),stroke=OUTLINE_V,sw=1); LN((bx,by),(bx,by+bh),stroke=OUTLINE_V,sw=1)
        ty=by+bh-0.72*bh; LN((bx,ty),(bx+bw,ty),stroke=HAIR,sw=1,dash=[4,4])
        segs=[]
        for k in range(61):
            tt=k/60.0
            val=(1-math.exp(-5*tt)*math.cos(8.5*tt)) if i==0 else (1-math.exp(-7*tt))
            segs.append((bx+tt*bw, by+bh-val*0.72*bh))
        PATH("M "+" L ".join(f"{px:.1f} {py:.1f}" for px,py in segs),stroke=c,sw=2.5)
        T(bx,by+bh+10,bw,("displacement overshoots, then settles" if i==0 else "eases in — critically damped, no overshoot"),size=11,color=MUTE)
    T(MX,y+400,W-2*MX,"Springs are defined by stiffness and damping, not milliseconds — so interruptions and gestures stay "
      "physical: grab a moving element mid-flight and it responds from its current velocity.",size=13,color=MUTE,lh=1.5)

def p_icon_system():
    newpage("Iconography","The icon system")
    y=bodytop()
    caption(MX,y,W-2*MX,"Material Symbols are drawn on a 24dp grid and sized 20 / 24 / 40 / 48dp. Three styles — Outlined, "
            "Rounded, Sharp — plus four variable axes (weight, fill, grade, optical size).")
    names=["menu","search","home","favorite","settings","person","notifications","mail","calendar","star","share","edit","add","check","close","back","more","chevron"]
    cw=(W-2*MX-8*10)/9
    for i,n in enumerate(names):
        xx=MX+(i%9)*(cw+10); yy=y+80+(i//9)*(cw+40)
        R([xx,yy,cw,cw],fill=SURFACE,radius=10,stroke=OUTLINE_V,sw=1); icon(n,xx+(cw-30)/2,yy+(cw-30)/2,30,ON_SURFACE)
        T(xx,yy+cw+6,cw,n,size=9.5,color=MUTE,align="center")
    yy=y+80+2*(cw+40)+10
    for i,(t,d) in enumerate([("Outlined","Default — light, unfilled strokes for a clean interface."),
                              ("Rounded","Softer, friendlier terminals; pairs with expressive shapes."),
                              ("Sharp","Crisp corners for a technical, precise tone.")]):
        xx=MX+i*((W-2*MX-2*20)/3+20); wpp=(W-2*MX-2*20)/3; SH([xx,yy,wpp,120],fill=SURFACE,radius=12,elev=1)
        icon("favorite",xx+24,yy+24,40,PRIMARY,sw=(2.2 if i==0 else 3 if i==1 else 2))
        T(xx+84,yy+26,wpp-100,t,size=16,color=INK,weight=500); T(xx+84,yy+54,wpp-100,d,size=12.5,color=MUTE,lh=1.35)

def p_icon_anatomy():
    newpage("Iconography","Icon anatomy & keylines")
    y=bodytop()
    caption(MX,y,W-2*MX,"Every symbol lives in a 24dp bounding box with a 2dp padding, leaving a 20dp live area. Keyline "
            "shapes — square, circle, and two rectangles — keep visual weight consistent across the set.")
    # big keyline grid
    gx,gy,g=MX,y+70,420; s=g
    R([gx,gy,s,s],fill=SURFACE,radius=12,stroke=OUTLINE_V,sw=1)
    for k in range(1,24): LN((gx+k*s/24,gy),(gx+k*s/24,gy+s),stroke=HAIR,sw=0.6)
    for k in range(1,24): LN((gx,gy+k*s/24),(gx+s,gy+k*s/24),stroke=HAIR,sw=0.6)
    pad=2*s/24; live=s-2*pad
    R([gx+pad,gy+pad,live,live],fill="none",stroke=ERROR,sw=1.2,dash=[4,4])   # live area
    DOT(gx+s/2,gy+s/2,live/2,stroke=PRIMARY,sw=1.4)                            # circle keyline
    R([gx+s/2-live*0.44,gy+s/2-live*0.5,live*0.88,live],fill="none",stroke=TERTIARY,sw=1.2)  # tall rect
    R([gx+s/2-live*0.5,gy+s/2-live*0.44,live,live*0.88],fill="none",stroke=SECONDARY,sw=1.2)  # wide rect
    icon("favorite",gx+s/2-90,gy+s/2-90,180,ON_SURFACE,sw=8)
    sx=gx+g+50
    for c,t,d in [(ERROR,"20dp live area","2dp padding on every side of the 24dp box."),
                  (PRIMARY,"Circle keyline","Round shapes fill to the circle for equal weight."),
                  (TERTIARY,"Tall / wide rects","Portrait & landscape shapes align to these."),
                  (ON_SURFACE,"2dp stroke","Outlined default weight on the 24dp grid.")]:
        pass
    items=[("24 dp","bounding box",OUTLINE),("20 dp","live area",ERROR),("2 dp","default stroke",ON_SURFACE),("48 dp","touch target",PRIMARY)]
    for i,(v,d,c) in enumerate(items):
        yy=y+70+i*108; SH([sx,yy,W-MX-sx,92],fill=SURFACE,radius=12,elev=1); R([sx,yy,5,92],fill=c,radius=2)
        T(sx+20,yy+16,300,v,size=24,color=c,weight=600,mono=True); T(sx+20,yy+54,W-MX-sx-30,d,size=13,color=MUTE)

def sect(x,y,t,c=PRIMARY): R([x,y+3,4,16],fill=c,radius=2); T(x+14,y,600,t,size=15,color=INK,weight=600)
def note(x,y,w,t): T(x,y,w,t,size=12.5,color=MUTE,lh=1.45)
def specrow(x,y,pairs):
    cw=(W-2*MX)/len(pairs)
    for i,(k,v) in enumerate(pairs):
        xx=x+i*cw; T(xx,y,cw-20,k,size=11,color=FAINT,weight=600,spacing=0.4); T(xx,y+18,cw-20,v,size=15,color=PRIMARY,weight=600,mono=True)

def p_components_overview():
    newpage("Components","The component library")
    y=bodytop()
    caption(MX,y,W-2*MX,"Material 3 groups components by role: actions, communication, containment, navigation, selection, "
            "and text input. M3 Expressive adds 15 new or refreshed elements. Each is depicted ahead from primitives.")
    cats=[("Actions","Buttons · FAB · icon buttons · button groups · split buttons",PRIMARY,PRIMARY_C),
          ("Selection","Checkbox · radio · switch · chips · sliders · date pickers",SECONDARY,SECONDARY_C),
          ("Containment","Cards · dialogs · sheets · carousel · lists · tooltips",TERTIARY,TERTIARY_C),
          ("Navigation","App bars · nav bar · rail · drawer · tabs · toolbars",PRIMARY,PRIMARY_C),
          ("Communication","Snackbars · badges · progress · loading · banners",SECONDARY,SECONDARY_C),
          ("Text input","Text fields (filled / outlined) · search · menus",TERTIARY,TERTIARY_C)]
    cw=(W-2*MX-2*20)/3
    for i,(t,d,c,cc) in enumerate(cats):
        xx=MX+(i%3)*(cw+20); yy=y+70+(i//3)*200
        SH([xx,yy,cw,180],fill=SURFACE,radius=14,elev=1); R([xx,yy,cw,6],fill=c,radius=3)
        DOT(xx+30,yy+42,14,fill=c); T(xx+22,yy+68,cw-40,t,size=20,color=INK,weight=500); T(xx+22,yy+104,cw-40,d,size=13,color=MUTE,lh=1.45)
    yy=y+70+2*200
    SH([MX,yy,W-2*MX,110],fill=PRIMARY_C,radius=14)
    T(MX+24,yy+20,W-2*MX-48,"Anatomy is universal",size=17,color=ON_PRIMARY_C,weight=500)
    T(MX+24,yy+50,W-2*MX-48,"Every component = a container (shape + colour role + elevation) + content (icon / label on the "
      "matching “On” role) + states (enabled, hovered, focused, pressed, disabled) drawn as state-layer overlays.",size=13,color=ON_PRIMARY_C,lh=1.5)

def p_buttons():
    newpage("Components · Actions","Common buttons")
    y=bodytop()
    caption(MX,y,W-2*MX,"Five emphasis levels, all 40dp tall with a Full-rounded (pill) shape. Emphasis descends: filled → "
            "tonal → elevated → outlined → text. Use one high-emphasis button per view.")
    kinds=[("filled","Filled","Highest emphasis · primary action"),("tonal","Filled tonal","Secondary, still prominent"),
           ("elevated","Elevated","Needs separation from busy content"),("outlined","Outlined","Medium emphasis"),("text","Text","Lowest emphasis · inline")]
    yy=y+72
    for i,(k,lab,d) in enumerate(kinds):
        ry=yy+i*94; SH([MX,ry,W-2*MX,78],fill=SURFACE,radius=12,elev=1)
        m_button(MX+28,ry+19,lab,k); m_button(MX+260,ry+19,"Icon",k,icon_name="add")
        T(MX+470,ry+16,300,lab,size=17,color=INK,weight=500); T(MX+470,ry+44,W-2*MX-500,d,size=13,color=MUTE)
    ry=yy+5*94+6
    sect(MX,ry,"Anatomy & specs")
    specrow(MX,ry+30,[("Height","40 dp"),("Shape","Full (pill)"),("Label","Label Large · 14"),("Icon","18 dp"),("Min target","48 dp")])

def p_button_groups():
    newpage("Components · Actions","Button groups & segmented buttons",tone=SECONDARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"M3 Expressive introduces connected button groups — a row of related actions that share a "
            "container and reshape on press. Segmented buttons select one or several options in a single control.")
    sect(MX,y+64,"Connected button group (M3E)",SECONDARY)
    gx=MX; labs=["Reply","Forward","Archive","More"]; bx=gx
    for i,lb in enumerate(labs):
        w=len(lb)*8+40; R([bx,y+96,w,48],fill=SECONDARY_C,radius=(24 if i in(0,len(labs)-1) else 6));
        R([bx+ (0 if i==0 else 2),y+96,w-(2 if i>0 else 0),48],fill=SECONDARY_C,radius=(24 if i in(0,len(labs)-1) else 6))
        T(bx,y+110,w,lb,size=14,color=ON_SECONDARY_C,weight=500,align="center"); bx+=w+3
    note(MX,y+160,W-2*MX,"On press, the active button swells and neighbours compress — a spring-driven expressive detail.")
    sect(MX,y+210,"Segmented — single select",SECONDARY)
    segs=["Day","Week","Month"]; sx=MX; sw=140
    for i,lb in enumerate(segs):
        sel=(i==1); R([sx+i*sw,y+242,sw,44],fill=(SECONDARY_C if sel else SURFACE),stroke=OUTLINE,sw=1,radius=(22 if i==0 else 0))
        if sel: icon("check",sx+i*sw+18,y+253,20,ON_SECONDARY_C,1.8)
        T(sx+i*sw+(20 if sel else 0),y+254,sw-(20 if sel else 0),lb,size=14,color=(ON_SECONDARY_C if sel else ON_SURFACE),weight=500,align="center")
    sect(MX,y+320,"Segmented — multi select",SECONDARY)
    ms=[("$",True),("B",True),("I",False),("U",False)]; sx=MX; sw=110
    for i,(lb,sel) in enumerate(ms):
        R([sx+i*sw,y+352,sw,44],fill=(SECONDARY_C if sel else SURFACE),stroke=OUTLINE,sw=1,radius=(22 if i==0 else (22 if i==len(ms)-1 else 0)))
        T(sx+i*sw,y+362,sw,lb,size=15,color=(ON_SECONDARY_C if sel else ON_SURFACE),weight=600,align="center")
    specrow(MX,y+430,[("Height","48 dp"),("Outer shape","Full"),("Inner","4 dp"),("Divider","1 dp outline"),("Select","single / multi")])

def p_split_buttons():
    newpage("Components · Actions","Split buttons & toolbars",tone=SECONDARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"A split button pairs a primary action with an attached menu trigger. Toolbars (docked or floating) "
            "collect contextual actions above content — both new in M3 Expressive.")
    sect(MX,y+64,"Split button")
    R([MX,y+96,190,52],fill=PRIMARY,radius=26); T(MX,y+112,190,"Save",size=15,color=ON_PRIMARY,weight=500,align="center")
    LN((MX+196,y+100),(MX+196,y+140),stroke=ON_PRIMARY,sw=1)  # divider hint
    R([MX+200,y+96,56,52],fill=PRIMARY,radius=26); icon("chevron-d",MX+213,y+110,24,ON_PRIMARY)
    note(MX+290,y+108,W-2*MX-290,"Left = default action. Right = open a menu of related actions. The two halves share one "
         "container with a hairline divider.")
    sect(MX,y+200,"Docked toolbar")
    R([MX,y+232,W-2*MX,64],fill=SC,radius=32)
    for i,ic in enumerate(["favorite","share","edit","add","more-h"]): icon(ic,MX+30+i*70,y+252,24,ON_SURFACE)
    R([W-MX-120,y+240,100,48],fill=PRIMARY,radius=24); T(W-MX-120,y+254,100,"Done",size=14,color=ON_PRIMARY,weight=500,align="center")
    sect(MX,y+340,"Floating toolbar")
    SH([MX+120,y+372,W-2*MX-240,68],fill=PRIMARY,radius=34,elev=3)
    for i,ic in enumerate(["back","favorite","share","more-h"]): icon(ic,MX+160+i*90,y+394,24,ON_PRIMARY)
    R([W-MX-220,y+382,90,48],fill=ON_PRIMARY,radius=24); T(W-MX-220,y+396,90,"Edit",size=14,color=PRIMARY,weight=600,align="center")
    note(MX,y+470,W-2*MX,"Floating toolbars hover over scrolling content at Level 3 elevation; docked toolbars sit flush on a surface.")

def p_icon_buttons():
    newpage("Components · Actions","Icon buttons")
    y=bodytop()
    caption(MX,y,W-2*MX,"Icon buttons trigger a single action in a compact 40dp target (48dp interactive). M3 Expressive adds "
            "filled, tonal and outlined containers, plus width and shape variants.")
    kinds=[("Standard",None,None,ON_SURFACE),("Filled",PRIMARY,None,ON_PRIMARY),("Tonal",SECONDARY_C,None,ON_SECONDARY_C),("Outlined",None,OUTLINE,ON_SURFACE)]
    for i,(lab,fill,strk,fg) in enumerate(kinds):
        xx=MX+i*((W-2*MX)/4)
        if fill: R([xx,y+80,40,40],fill=fill,radius=20)
        elif strk: R([xx,y+80,40,40],fill="none",stroke=strk,sw=1.4,radius=20)
        icon("favorite",xx+8,y+88,24,fg,2)
        T(xx,y+132,160,lab,size=14,color=INK,weight=500)
    sect(MX,y+190,"Toggle state (unselected → selected)")
    for i,(fill,ic,fg) in enumerate([("none","favorite",ON_SURFACE_V),(TERTIARY,"favorite",ON_TERTIARY)]):
        xx=MX+i*140;
        if fill!="none": R([xx,y+222,44,44],fill=fill,radius=22)
        else: R([xx,y+222,44,44],fill="none",stroke=OUTLINE,sw=1.4,radius=22)
        icon(ic,xx+10,y+232,24,fg,2)
        if i==0: icon("chevron",xx+70,y+232,24,OUTLINE)
    sect(MX,y+310,"Sizes (M3E)")
    for i,(d,lab) in enumerate([(32,"XS"),(40,"S"),(56,"M"),(72,"L")]):
        xx=MX+i*160; R([xx,y+346,d,d],fill=PRIMARY_C,radius=d/2); icon("add",xx+(d-24)/2,y+346+(d-24)/2,24,ON_PRIMARY_C)
        T(xx,y+346+d+8,d+20,f"{lab} · {d}dp",size=12,color=MUTE)
    specrow(MX,y+470,[("Container","40 dp"),("Icon","24 dp"),("Target","48 dp"),("Shapes","round / square"),("States","toggle")])

def p_fab():
    newpage("Components · Actions","Floating action button",tone=TERTIARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"The FAB is the single most important action on a screen. Four sizes cover the range; colour comes from "
            "primary, secondary, tertiary or surface container roles. Elevation Level 3 lifts it above content.")
    sect(MX,y+64,"Sizes",TERTIARY)
    xs=MX
    for size,lab in [("small","Small · 40dp"),("regular","Regular · 56dp"),("large","Large · 96dp")]:
        d=m_fab(xs,y+96,"add",size,tone=TERTIARY_C,fg=ON_TERTIARY_C); T(xs,y+96+ {"small":40,"regular":56,"large":96}[size]+12,160,lab,size=12,color=MUTE); xs+=180
    sect(MX,y+240,"Colour roles",TERTIARY)
    for i,(tone,fg,lab) in enumerate([(PRIMARY_C,ON_PRIMARY_C,"Primary c."),(SECONDARY_C,ON_SECONDARY_C,"Secondary c."),(TERTIARY_C,ON_TERTIARY_C,"Tertiary c."),(SC_HIGH,ON_SURFACE,"Surface")]):
        xx=MX+i*150; m_fab(xx,y+272,"edit","regular",tone=tone,fg=fg); T(xx,y+272+68,150,lab,size=12,color=MUTE)
    sect(MX,y+390,"Extended FAB",TERTIARY)
    m_fab(MX,y+422,"add","regular",label="Compose",tone=TERTIARY_C,fg=ON_TERTIARY_C)
    note(MX+260,y+436,W-2*MX-260,"Adds a label beside the icon for a clear, high-emphasis action — collapses to a circular FAB on scroll.")
    specrow(MX,y+510,[("Regular","56 dp"),("Shape","Large · 16dp"),("Elevation","Level 3"),("Icon","24 dp"),("Per screen","one")])

def p_fab_menu():
    newpage("Components · Actions","FAB menu & speed dial",tone=TERTIARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"New in M3 Expressive: tapping the FAB expands a vertical menu of labelled actions (a modern speed "
            "dial). Each item is a small FAB with a leading label chip; a scrim dims the content behind.")
    # closed vs open
    gx,gy,gw,gh=MX,y+64,300,520; cb=m_phone(gx,gy,gw,gh)
    R([cb[0]+12,cb[1]+12,cb[2]-24,cb[3]-24],fill=SC,radius=8)
    m_fab(cb[0]+cb[2]-72,cb[1]+cb[3]-72,"add","regular",tone=TERTIARY_C,fg=ON_TERTIARY_C)
    T(gx,gy+gh+12,gw,"Closed",size=13,color=MUTE,align="center")
    gx2=gx+gw+60; cb=m_phone(gx2,gy,gw,gh)
    R([cb[0]+12,cb[1]+12,cb[2]-24,cb[3]-24],fill=SCRIM,fo=0.32,radius=8)
    acts=[("edit","Note"),("mail","Email"),("person","Contact"),("calendar","Event")]
    for i,(ic,lb) in enumerate(reversed(acts)):
        ry=cb[1]+cb[3]-150-i*70; lw=len(lb)*8+30
        R([cb[0]+cb[2]-72-lw-14,ry+8,lw,28],fill=SURFACE,radius=14); T(cb[0]+cb[2]-72-lw-14,ry+14,lw,lb,size=12,color=ON_SURFACE,weight=500,align="center")
        m_fab(cb[0]+cb[2]-56,ry,ic,"small",tone=SURFACE,fg=ON_SURFACE_V)
    m_fab(cb[0]+cb[2]-72,cb[1]+cb[3]-72,"close","regular",tone=TERTIARY,fg=ON_TERTIARY)
    T(gx2,gy+gh+12,gw,"Open — labelled actions + scrim",size=13,color=MUTE,align="center")
    sx=gx2+gw+50
    for t,d,c in [("Speed dial","3–6 related actions branch from one FAB.",TERTIARY),
                  ("Labels","Each action names itself in a chip — no guessing.",PRIMARY),
                  ("Scrim","Dims content and captures the dismiss tap.",SECONDARY),
                  ("Motion","Items spring out in sequence, not all at once.",TERTIARY)]:
        pass
    for i,(t,d,c) in enumerate([("Speed dial","3–6 related actions branch from one FAB.",TERTIARY),("Labels","Each action names itself in a chip.",PRIMARY),("Scrim","Dims content, captures dismiss.",SECONDARY),("Motion","Items spring out in sequence.",TERTIARY)]):
        yy=gy+i*118; SH([sx,yy,W-MX-sx,100],fill=SURFACE,radius=12,elev=1); R([sx,yy,5,100],fill=c,radius=2)
        T(sx+20,yy+18,W-MX-sx-30,t,size=16,color=INK,weight=500); T(sx+20,yy+48,W-MX-sx-36,d,size=13,color=MUTE,lh=1.4)

def p_cards():
    newpage("Components · Containment","Cards",tone=TERTIARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Cards group related content and actions about a single subject. Three container styles set emphasis: "
            "elevated (shadow), filled (tonal fill), and outlined (1dp outline). Corner: Medium · 12dp.")
    kinds=[("elevated","Elevated"),("filled","Filled"),("outlined","Outlined")]
    cw=(W-2*MX-2*24)/3
    for i,(k,lab) in enumerate(kinds):
        xx=MX+i*(cw+24); m_card(xx,y+70,cw,300,k)
        R([xx+16,y+86,cw-32,120],fill=SURFACE_V,radius=8)  # media
        icon("star",xx+cw/2-14,y+130,28,ON_SURFACE_V)
        T(xx+16,y+222,cw-32,"Card title",size=17,color=ON_SURFACE,weight=500)
        T(xx+16,y+248,cw-32,"Supporting text that describes the card's subject in a line or two.",size=12.5,color=ON_SURFACE_V,lh=1.4)
        m_button(xx+16,y+318,"Action","text"); T(xx+cw-90,y+70+300+0,80,lab,size=12,color=TERTIARY,weight=600)
        T(xx,y+70+310,cw,lab,size=12,color=MUTE,align="center")
    yy=y+420
    sect(MX,yy,"Anatomy",TERTIARY)
    note(MX,yy+26,W-2*MX,"Optional regions, top to bottom: media / header (with avatar + title + subhead) · supporting text · "
         "actions. Cards are containers, not buttons — put explicit buttons or an overflow menu inside for actions.")
    specrow(MX,yy+90,[("Shape","Medium · 12dp"),("Elevated","Level 1"),("Outline","1 dp"),("Padding","16 dp"),("Media","16:9 typical")])

def p_chips():
    newpage("Components · Selection","Chips",tone=SECONDARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Chips are compact, 32dp elements for input, attributes or actions in context. Four types: assist, "
            "filter, input, and suggestion. Selected filter/input chips fill with the secondary-container role.")
    types=[("Assist","assist",["Directions","Call","Share"]),("Filter","filter",["All","Photos","Videos","Docs"]),
           ("Input","input",["Alex","Jordan","Sam"]),("Suggestion","suggestion",["Add label","Snooze","Remind me"])]
    yy=y+70
    for ti,(lab,kind,items) in enumerate(types):
        sect(MX,yy,lab+" chips",SECONDARY); xx=MX;
        for j,it in enumerate(items):
            sel=(kind=="filter" and j in(1,2)) or (kind=="input")
            w=m_chip(xx,yy+26,it,kind,selected=sel,icon_name=("directions" if kind=="assist" else None)); xx+=w+12
        yy+=104
    specrow(MX,yy+6,[("Height","32 dp"),("Target","48 dp"),("Shape","Small · 8dp"),("Selected","Secondary c."),("Label","Label Large")])

def p_textfields():
    newpage("Components · Text input","Text fields")
    y=bodytop()
    caption(MX,y,W-2*MX,"Two styles: filled (tonal box, bottom line) and outlined (1dp border). Both 56dp tall with a floating "
            "label, optional leading/trailing icons, and supporting text below.")
    sect(MX,y+64,"Filled")
    m_textfield(MX,y+96,300,"Label",value="Input text"); m_textfield(MX+340,y+96,300,"Focused",value="Editing",state="focused")
    T(MX,y+162,300,"Supporting text",size=12,color=ON_SURFACE_V); T(MX+340,y+162,300,"Supporting text",size=12,color=PRIMARY)
    sect(MX,y+210,"Outlined")
    m_textfield(MX,y+250,300,"Label",kind="outlined",value="Input text"); m_textfield(MX+340,y+250,300,"Focused",kind="outlined",value="Editing",state="focused")
    sect(MX,y+340,"Anatomy")
    bx=MX+30; m_textfield(bx,y+380,360,"Email",kind="outlined",value="alex@")
    for lbl,px,py in [("Label",bx+6,y+362),("Container",bx-24,y+400),("Input text",bx+120,y+430),("Supporting",bx,y+446)]:
        pass
    icon("mail",bx-40,y+390,24,ON_SURFACE_V); icon("close",bx+366,y+390,20,ON_SURFACE_V)
    T(bx+400,y+372,300,"Leading icon · label · input · trailing icon",size=13,color=MUTE,lh=1.6)
    T(bx+400,y+412,300,"Supporting text / character counter sits below the container.",size=13,color=MUTE,lh=1.5)
    specrow(MX,y+500,[("Height","56 dp"),("Label","Body Small→float"),("Input","Body Large"),("Icon","24 dp"),("Radius","4 / 4 dp")])

def p_textfield_states():
    newpage("Components · Text input","Text-field states")
    y=bodytop()
    caption(MX,y,W-2*MX,"State is carried by the active colour: on-surface-variant (enabled), primary (focused), error, and a "
            "dimmed 38% (disabled). Supporting text and the label colour follow the state.")
    for i,(lab,st,help_) in enumerate([("Enabled","enabled",None),("Focused","focused","Cursor active"),("Error","error","Enter a valid email"),("Disabled","enabled","Not editable")]):
        yy=y+70+i*112
        m_textfield(MX,yy,340,lab,value=("alex@mail" if i!=0 else "Input"),state=("focused" if i==1 else ("error" if i==2 else "enabled")))
        cc=[ON_SURFACE_V,PRIMARY,ERROR,OUTLINE_V][i]
        if i==2: icon("close",MX+310,yy+18,20,ERROR)
        if help_: T(MX,yy+62,340,help_,size=12,color=cc)
        T(MX+400,yy+12,300,lab,size=18,color=INK,weight=500)
        T(MX+400,yy+42,300,["Resting; label sits inside.","Primary line + label lift; 2dp.","Error colour + assistive message.","38% opacity; non-interactive."][i],size=13,color=MUTE,lh=1.4)

def p_menus():
    newpage("Components · Text input","Menus & exposed dropdowns")
    y=bodytop()
    caption(MX,y,W-2*MX,"Menus display a list of choices on a temporary surface (Level 2). An exposed dropdown is a text field "
            "that opens a menu of options. Items are 48dp tall with optional leading icon and trailing state.")
    # dropdown field + open menu
    sect(MX,y+64,"Exposed dropdown menu")
    m_textfield(MX,y+96,300,"Country",kind="outlined",value="Brazil"); icon("chevron-d",MX+270,y+112,24,ON_SURFACE_V)
    SH([MX,y+160,300,240],fill=SC,radius=8,elev=2)
    for i,it in enumerate(["Argentina","Brazil","Chile","Colombia","Ecuador"]):
        iy=y+168+i*46
        if it=="Brazil": R([MX+6,iy,288,44],fill=SECONDARY_C,radius=6)
        T(MX+18,iy+13,260,it,size=15,color=ON_SURFACE)
        if it=="Brazil": icon("check",MX+264,iy+11,22,ON_SECONDARY_C,1.8)
    sect(MX+380,y+64,"Context menu")
    SH([MX+380,y+96,280,304],fill=SC,radius=8,elev=2)
    for i,(ic,it,tr) in enumerate([("person","Profile",None),("settings","Settings",None),("share","Share","chevron"),("star","Add to favourites",None),(None,"—",None),("close","Sign out",None)]):
        iy=y+108+i*46
        if it=="—": LN((MX+392,iy+10),(MX+648,iy+10),stroke=OUTLINE_V,sw=1); continue
        if ic: icon(ic,MX+396,iy+2,22,ON_SURFACE_V,1.8)
        T(MX+430,iy,220,it,size=15,color=ON_SURFACE)
        if tr: icon(tr,MX+626,iy,20,ON_SURFACE_V,1.6)
    specrow(MX,y+440,[("Item height","48 dp"),("Surface","Level 2"),("Shape","XS · 4dp"),("Leading icon","24 dp"),("Max width","280 dp")])

def p_selection():
    newpage("Components · Selection","Checkbox · radio · switch")
    y=bodytop()
    caption(MX,y,W-2*MX,"Three selection controls. Checkboxes select any number of items; radio buttons select exactly one; "
            "switches toggle a single setting on or off. All keep a 48dp target around an 18–24dp visual.")
    # checkbox column
    sect(MX,y+64,"Checkbox")
    for i,(lab,on) in enumerate([("Selected",True),("Unselected",False),("Indeterminate",True)]):
        yy=y+100+i*54
        if lab=="Indeterminate": R([MX,yy,20,20],fill=PRIMARY,radius=4); R([MX+4,yy+9,12,3],fill=ON_PRIMARY)
        else: m_checkbox(MX,yy,on)
        T(MX+36,yy+1,220,lab,size=15,color=ON_SURFACE)
    sect(MX+320,y+64,"Radio button")
    for i,(lab,on) in enumerate([("Selected",True),("Option two",False),("Option three",False)]):
        yy=y+100+i*54; m_radio(MX+320,yy,on); T(MX+356,yy+1,220,lab,size=15,color=ON_SURFACE)
    sect(MX+640,y+64,"Switch")
    for i,(lab,on) in enumerate([("On",True),("Off",False)]):
        yy=y+100+i*60; m_switch(MX+640,yy,on); T(MX+710,yy+6,180,lab,size=15,color=ON_SURFACE)
    yy=y+300
    sect(MX,yy,"Lists with controls")
    for i,(t,ctrl) in enumerate([("Wi-Fi","switch"),("Notifications","switch"),("Dark theme","check")]):
        ry=yy+40+i*64; R([MX,ry,W-2*MX,60],fill=SURFACE,radius=10,stroke=OUTLINE_V,sw=1)
        icon("settings",MX+18,ry+18,24,ON_SURFACE_V,1.8); T(MX+58,ry+20,400,t,size=16,color=ON_SURFACE)
        if ctrl=="switch": m_switch(W-MX-72,ry+14,i==0)
        else: m_checkbox(W-MX-44,ry+20,True)
    specrow(MX,yy+260,[("Target","48 dp"),("Checkbox","18 dp"),("Radio","20 dp"),("Switch","52×32 dp"),("Selected","Primary")])

def p_sliders():
    newpage("Components · Selection","Sliders")
    y=bodytop()
    caption(MX,y,W-2*MX,"Sliders select a value or range along a track. Continuous sliders move freely; discrete sliders snap to "
            "tick stops. The handle is primary; the active track is primary, the inactive track surface-variant.")
    sect(MX,y+64,"Continuous"); m_slider(MX,y+112,W-2*MX,0.35)
    sect(MX,y+170,"Discrete (tick stops)"); m_slider(MX,y+218,W-2*MX,0.5,discrete=True)
    sect(MX,y+276,"With value label")
    m_slider(MX,y+340,W-2*MX,0.6); R([MX+(W-2*MX)*0.6-24,y+300,48,30],fill=PRIMARY,radius=15); T(MX+(W-2*MX)*0.6-24,y+307,48,"60",size=13,color=ON_PRIMARY,weight=600,align="center")
    sect(MX,y+400,"Range slider")
    xx=MX; w=W-2*MX; LN((xx,y+448),(xx+w,y+448),stroke=SURFACE_V,sw=4); LN((xx+w*0.3,y+448),(xx+w*0.7,y+448),stroke=PRIMARY,sw=4)
    DOT(xx+w*0.3,y+448,10,fill=PRIMARY); DOT(xx+w*0.7,y+448,10,fill=PRIMARY)
    specrow(MX,y+510,[("Track","4 dp"),("Handle","20 dp"),("Active","Primary"),("Inactive","Surface variant"),("Target","48 dp")])

def p_dialogs():
    newpage("Components · Containment","Dialogs",tone=TERTIARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Dialogs interrupt with critical information or a decision. Basic dialogs float on a scrim at Level 3 "
            "with Extra-large (28dp) corners; full-screen dialogs handle complex, multi-field tasks.")
    # basic dialog
    sect(MX,y+64,"Basic dialog",TERTIARY)
    dx,dy,dw,dh=MX,y+96,420,300; R([dx-20,dy-16,dw+40,dh+40],fill=SCRIM,fo=0.16,radius=12)
    SH([dx,dy,dw,dh],fill=SC_HIGH,radius=28,elev=3)
    icon("notifications",dx+30,dy+28,28,PRIMARY,2)
    T(dx+30,dy+78,dw-60,"Reset settings?",size=22,color=ON_SURFACE,weight=500)
    T(dx+30,dy+120,dw-60,"This will restore all settings to their defaults. You can't undo this action.",size=14,color=ON_SURFACE_V,lh=1.5)
    m_button(dx+dw-200,dy+dh-58,"Cancel","text"); m_button(dx+dw-96,dy+dh-58,"Reset","text")
    # full-screen dialog
    sect(MX+470,y+64,"Full-screen",TERTIARY)
    fx=MX+470; fw=W-MX-fx; cb=m_phone(fx,y+96,fw,440)
    m_topbar(cb[0],cb[1],cb[2],"New event",nav="close",actions=("check",))
    for k in range(3): m_textfield(cb[0]+16,cb[1]+90+k*80,cb[2]-32,["Title","Location","Notes"][k],kind="outlined",value="")
    specrow(MX,y+560,[("Shape","XL · 28dp"),("Elevation","Level 3"),("Scrim","32% scrim"),("Actions","≤ 2 text btns"),("Full-screen","complex task")])

def p_sheets():
    newpage("Components · Containment","Bottom & side sheets",tone=TERTIARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Sheets are surfaces anchored to an edge. Bottom sheets rise from the bottom (modal with a scrim, or "
            "standard, persistent); side sheets slide from the side on larger windows. Top corners round to XL.")
    sect(MX,y+64,"Modal bottom sheet",TERTIARY)
    gx,gy,gw,gh=MX,y+96,300,460; cb=m_phone(gx,gy,gw,gh)
    R([cb[0]+8,cb[1]+8,cb[2]-16,cb[3]-16],fill=SCRIM,fo=0.32,radius=8)
    sy=cb[1]+cb[3]-300; R([cb[0]+8,sy,cb[2]-16,320],fill=SC,radius=0); R([cb[0]+8,sy,cb[2]-16,300],fill=SC,radius=28)
    R([cb[0]+cb[2]/2-16,sy+12,32,4],fill=OUTLINE,radius=2)  # drag handle
    T(cb[0]+28,sy+34,cb[2]-56,"Share to",size=18,color=ON_SURFACE,weight=500)
    for i in range(3): m_listitem(cb[0]+16,sy+72+i*64,cb[2]-32,["Messages","Email","Nearby"][i],lead=["mail","mail","share"][i])
    sect(MX+360,y+64,"Side sheet",TERTIARY)
    sx=MX+360; sw2=W-MX-sx; R([sx,y+96,sw2,460],fill=SC_LOW,radius=12,stroke=OUTLINE_V,sw=1)
    R([sx+sw2-280,y+96,280,460],fill=SC,radius=12)
    T(sx+sw2-280+24,y+120,240,"Filters",size=18,color=ON_SURFACE,weight=500); icon("close",sx+sw2-48,y+120,24,ON_SURFACE_V)
    for i in range(4):
        ry=y+170+i*70; T(sx+sw2-280+24,ry,200,["Price","Rating","Distance","Open now"][i],size=14,color=ON_SURFACE); m_switch(sx+sw2-72,ry-6,i%2==0)
    note(MX,y+580,W-2*MX,"Drag handle signals a draggable modal sheet · side sheets suit Medium+ windows for filters and details.")

def p_snackbars():
    newpage("Components · Communication","Snackbars & banners",tone=SECONDARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Snackbars show brief, transient feedback at the bottom, with at most one action. Banners are more "
            "prominent, persistent messages near the top that require acknowledgement.")
    sect(MX,y+64,"Snackbar",SECONDARY)
    R([MX,y+96,560,52],fill="#322F35",radius=8); T(MX+20,y+112,380,"Message archived",size=14,color="#F5EFF7")
    T(MX+440,y+112,100,"Undo",size=14,color=D_PRIMARY,weight=600)
    R([MX+600,y+96,W-MX-(MX+600),52],fill="#322F35",radius=8); T(MX+620,y+112,200,"1 item deleted",size=14,color="#F5EFF7"); icon("close",W-MX-40,y+108,20,"#CAC4D0",1.6)
    note(MX,y+164,W-2*MX,"One line preferred · single action (Undo) · auto-dismiss ~4–10s · never block critical flows.")
    sect(MX,y+230,"Banner",SECONDARY)
    R([MX,y+262,W-2*MX,120],fill=SECONDARY_C,radius=12)
    icon("notifications",MX+24,y+286,28,ON_SECONDARY_C,2)
    T(MX+70,y+284,W-2*MX-300,"You're offline. Changes will sync when a connection returns.",size=15,color=ON_SECONDARY_C,lh=1.4)
    m_button(W-MX-230,y+322,"Dismiss","text"); m_button(W-MX-120,y+322,"Retry","text")
    sect(MX,y+420,"Tooltips",SECONDARY)
    R([MX,y+470,120,32],fill="#322F35",radius=6); T(MX,y+478,120,"Bookmark",size=12,color="#F5EFF7",align="center")
    PATH(f"M {MX+54} {y+502} L {MX+60} {y+510} L {MX+66} {y+502} Z",fill="#322F35")
    R([MX+220,y+460,240,90],fill=SC_HIGH,radius=8,stroke=OUTLINE_V,sw=1)
    T(MX+236,y+474,210,"Rich tooltip",size=14,color=ON_SURFACE,weight=500); T(MX+236,y+498,210,"A short paragraph with an optional action.",size=12,color=ON_SURFACE_V,lh=1.35)
    specrow(MX,y+560,[("Snackbar","1 action"),("Auto-dismiss","4–10 s"),("Banner","persistent"),("Plain tip","≤ 1 line"),("Rich tip","+ action")])

def p_topbars():
    newpage("Components · Navigation","Top app bars",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"The top app bar hosts the screen title, a navigation icon and up to three actions. Four sizes: "
            "center-aligned, small (64dp), medium (112dp) and large (152dp) — larger bars collapse on scroll.")
    labs=["Center-aligned · 64dp","Small · 64dp"]
    m_topbar(MX,y+70,(W-2*MX-24)/2,"Title",center=True,actions=("more-h",))
    m_topbar(MX+(W-2*MX-24)/2+24,y+70,(W-2*MX-24)/2,"Title",actions=("search","more-h"))
    T(MX,y+142,300,labs[0],size=12,color=MUTE); T(MX+(W-2*MX-24)/2+24,y+142,300,labs[1],size=12,color=MUTE)
    # medium
    R([MX,y+186,W-2*MX,112],fill=SC); icon("back",MX+16,y+202,24,ON_SURFACE)
    for i,a in enumerate(["search","more-h"]): icon(a,W-MX-48-i*48,y+202,24,ON_SURFACE)
    T(MX+16,y+250,W-2*MX,"Headline",size=26,color=ON_SURFACE,weight=400); T(MX,y+306,300,"Medium · 112dp",size=12,color=MUTE)
    # large
    R([MX,y+340,W-2*MX,152],fill=PRIMARY_C); icon("back",MX+16,y+356,24,ON_PRIMARY_C)
    for i,a in enumerate(["favorite","more-h"]): icon(a,W-MX-48-i*48,y+356,24,ON_PRIMARY_C)
    T(MX+16,y+430,W-2*MX,"Large headline",size=32,color=ON_PRIMARY_C,weight=400); T(MX,y+500,300,"Large · 152dp",size=12,color=MUTE)
    specrow(MX,y+540,[("Small","64 dp"),("Medium","112 dp"),("Large","152 dp"),("Actions","≤ 3"),("On scroll","collapse")])

def p_bottombar():
    newpage("Components · Navigation","Bottom app bar & toolbar",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"A bottom app bar holds 2–4 primary actions plus an optional FAB, keeping reach within thumb range. "
            "It pairs with navigation on medium-emphasis screens.")
    R([MX,y+80,W-2*MX,80],fill=SC)
    for i,ic in enumerate(["check","edit","share","more-h"]): icon(ic,MX+30+i*70,y+108,24,ON_SURFACE_V)
    m_fab(W-MX-88,y+92,"add","regular",tone=PRIMARY_C,fg=ON_PRIMARY_C)
    note(MX,y+184,W-2*MX,"The FAB anchors to the end; actions align to the start. On scroll the bar can hide to reveal content.")
    sect(MX,y+240,"Placement")
    gx,gy,gw,gh=MX,y+280,290,340; cb=m_phone(gx,gy,gw,gh)
    R([cb[0]+10,cb[1]+10,cb[2]-20,cb[3]-90,],fill=SC_HIGH,radius=8)
    R([cb[0]+10,cb[1]+cb[3]-72,cb[2]-20,62],fill=SC)
    for i,ic in enumerate(["home","search","favorite"]): icon(ic,cb[0]+30+i*56,cb[1]+cb[3]-56,24,ON_SURFACE_V)
    m_fab(cb[0]+cb[2]-70,cb[1]+cb[3]-64,"add","small",tone=PRIMARY,fg=ON_PRIMARY)
    specrow(MX,y+650,[("Height","80 dp"),("Actions","2–4"),("FAB","optional"),("Elevation","Level 2"),("Reach","thumb zone")]) if False else None
    specrow(MX,gy+gh+30,[("Height","80 dp"),("Actions","2–4"),("FAB","optional"),("Icon","24 dp"),("Reach","thumb zone")])

def p_navbar():
    newpage("Components · Navigation","Navigation bar",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"The bottom navigation bar switches between 3–5 top-level destinations on compact widths. The active "
            "item shows a pill-shaped active indicator (secondary-container) behind a filled icon.")
    m_navbar(MX,y+80,W-2*MX,[("home","Home"),("search","Explore"),("favorite","Saved"),("mail","Inbox"),("person","You")],active=0)
    note(MX,y+180,W-2*MX,"Icons switch from outlined (inactive) to filled (active); labels may always show, or show only for the active item.")
    sect(MX,y+240,"In context")
    gx,gy,gw,gh=MX+ (W-2*MX-300)/2,y+280,300,420; cb=m_phone(gx,gy,gw,gh)
    m_topbar(cb[0],cb[1],cb[2],"Home",actions=("more-h",))
    for i in range(3): m_card(cb[0]+12,cb[1]+80+i*100,cb[2]-24,88,"filled")
    m_navbar(cb[0],cb[1]+cb[3]-80,cb[2],[("home","Home"),("search","Find"),("favorite","Saved"),("person","You")],active=0)
    specrow(MX,gy+gh+24,[("Height","80 dp"),("Items","3–5"),("Active","pill indicator"),("Icon","24 dp"),("Label","Label Medium")])

def p_navrail():
    newpage("Components · Navigation","Navigation rail",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"On medium widths the bar becomes a vertical rail (80dp wide) at the leading edge, optionally topped by "
            "a FAB or menu button. Same destinations, more horizontal room for content.")
    rx=MX; R([rx,y+80,88,480],fill=SC)
    m_fab(rx+16,y+104,"add","small",tone=PRIMARY_C,fg=ON_PRIMARY_C)
    for i,(ic,lb) in enumerate([("home","Home"),("search","Find"),("favorite","Saved"),("mail","Inbox"),("person","You")]):
        cyy=y+200+i*70
        if i==0: PILL([rx+16,cyy-6,56,32],fill=SECONDARY_C)
        icon(ic,rx+32,cyy-2,24,(ON_SECONDARY_C if i==0 else ON_SURFACE_V))
        T(rx,cyy+28,88,lb,size=11,color=(ON_SURFACE if i==0 else ON_SURFACE_V),weight=500,align="center")
    R([rx+108,y+80,W-MX-(rx+108),480],fill=SC_HIGH,radius=12)
    T(rx+130,y+104,300,"Content area",size=14,color=ON_SURFACE_V)
    specrow(MX,y+590,[("Width","80 dp"),("Items","3–7"),("Top","FAB / menu"),("Active","pill indicator"),("Use","Medium+")])

def p_navdrawer():
    newpage("Components · Navigation","Navigation drawer",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Drawers list destinations with labels and optional headlines/dividers. Modal on compact (over a scrim); "
            "standard/permanent on expanded widths. Items are 56dp with a pill active indicator.")
    dx=MX; dw=340; R([dx,y+80,dw,500],fill=SC,radius=0); R([dx,y+80,dw,500],fill=SC,radius=16)
    T(dx+28,y+104,dw-40,"Mail",size=13,color=ON_SURFACE_V,weight=600,spacing=1)
    dests=[("mail","Inbox","24",True),("star","Starred",None,False),("share","Sent",None,False),("edit","Drafts","3",False),(None,"—",None,False),("person","All labels",None,False),("settings","Settings",None,False)]
    for i,(ic,lb,badge,act) in enumerate(dests):
        iy=y+140+i*56
        if lb=="—": LN((dx+28,iy+14),(dx+dw-28,iy+14),stroke=OUTLINE_V,sw=1); continue
        if act: PILL([dx+12,iy,dw-24,48],fill=SECONDARY_C)
        icon(ic,dx+28,iy+12,24,(ON_SECONDARY_C if act else ON_SURFACE_V),1.8)
        T(dx+64,iy+14,dw-120,lb,size=15,color=(ON_SURFACE if act else ON_SURFACE),weight=(500 if act else 400))
        if badge: T(dx+dw-52,iy+14,40,badge,size=13,color=ON_SURFACE_V,weight=600,align="right")
    R([dx+dw+40,y+80,W-MX-(dx+dw+40),500],fill=SC_HIGH,radius=12); T(dx+dw+64,y+104,300,"Detail pane",size=14,color=ON_SURFACE_V)
    specrow(MX,y+608,[("Item","56 dp"),("Width","≤ 360 dp"),("Modal","compact"),("Standard","expanded"),("Active","pill")])

def p_tabs():
    newpage("Components · Navigation","Tabs",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Tabs organise content across parallel views at the same hierarchy. Primary tabs pair with a top app "
            "bar; secondary tabs sit within content. The active tab shows a 3dp indicator in the primary role.")
    sect(MX,y+64,"Primary tabs")
    tw=(W-2*MX)/3
    for i,(ic,lb) in enumerate([("home","Overview"),("star","Specs"),("share","Reviews")]):
        xx=MX+i*tw; icon(ic,xx+tw/2-40,y+100,22,(PRIMARY if i==0 else ON_SURFACE_V),1.8)
        T(xx+ (0 if not ic else 0),y+102,tw,lb,size=14,color=(PRIMARY if i==0 else ON_SURFACE_V),weight=500,align="center")
    LN((MX,y+140),(W-MX,y+140),stroke=SURFACE_V,sw=2); LN((MX,y+140),(MX+tw,y+140),stroke=PRIMARY,sw=3)
    sect(MX,y+200,"Secondary tabs")
    for i,lb in enumerate(["All","Photos","Videos","Albums"]):
        xx=MX+i*(W-2*MX)/4; T(xx,y+236,(W-2*MX)/4,lb,size=14,color=(ON_SURFACE if i==0 else ON_SURFACE_V),weight=500,align="center")
    LN((MX,y+270),(W-MX,y+270),stroke=SURFACE_V,sw=1.5); LN((MX,y+270),(MX+(W-2*MX)/4,y+270),stroke=ON_SURFACE,sw=2.5)
    sect(MX,y+330,"Scrollable tabs")
    xx=MX
    for lb in ["Trending","Music","Gaming","News","Sports","Movies"]:
        w=len(lb)*9+30; T(xx,y+366,w,lb,size=14,color=(PRIMARY if lb=="Trending" else ON_SURFACE_V),weight=500,align="center"); xx+=w+8
    LN((MX,y+400),(W-MX,y+400),stroke=SURFACE_V,sw=1.5); LN((MX,y+400),(MX+110,y+400),stroke=PRIMARY,sw=3)
    specrow(MX,y+460,[("Height","48 dp"),("Indicator","3 dp"),("Primary","+ icon"),("Secondary","text"),("Scroll","many tabs")])

def p_search():
    newpage("Components · Text input","Search")
    y=bodytop()
    caption(MX,y,W-2*MX,"A search bar is a persistent, rounded entry point (Full shape, Level 3). Tapping it opens the search "
            "view — a full-surface field with suggestions, recent queries and results.")
    sect(MX,y+64,"Search bar")
    SH([MX,y+96,W-2*MX,56],fill=SC_HIGH,radius=28,elev=1); icon("search",MX+18,y+112,24,ON_SURFACE_V)
    T(MX+56,y+114,400,"Search mail",size=16,color=ON_SURFACE_V); DOT(W-MX-34,y+124,16,fill=PRIMARY_C); icon("person",W-MX-42,y+116,20,ON_PRIMARY_C,1.6)
    sect(MX,y+190,"Search view")
    gx,gy,gw,gh=MX,y+222,320,380; cb=m_phone(gx,gy,gw,gh)
    R([cb[0]+8,cb[1]+8,cb[2]-16,56],fill=SC); icon("back",cb[0]+20,cb[1]+24,24,ON_SURFACE); T(cb[0]+56,cb[1]+26,200,"pho",size=16,color=ON_SURFACE); icon("close",cb[0]+cb[2]-40,cb[1]+24,20,ON_SURFACE_V,1.6)
    for i,(ic,t) in enumerate([("search","photos"),("search","phone number"),("calendar","photography club")]):
        iy=cb[1]+80+i*52; icon(ic,cb[0]+20,iy,22,ON_SURFACE_V,1.8); T(cb[0]+56,iy+2,cb[2]-90,t,size=15,color=ON_SURFACE)
    sx=gx+gw+50
    for i,(t,d) in enumerate([("Persistent bar","Sits atop content; scrolls with a docked variant."),("Suggestions","Recent + predicted queries as you type."),("Scope","Filter chips can narrow results within the view."),("Voice","Optional trailing mic / avatar action.")]):
        yy=gy+i*98; SH([sx,yy,W-MX-sx,80],fill=SURFACE,radius=12,elev=1); R([sx,yy,5,80],fill=PRIMARY,radius=2)
        T(sx+18,yy+14,W-MX-sx-30,t,size=15,color=INK,weight=500); T(sx+18,yy+40,W-MX-sx-30,d,size=12.5,color=MUTE,lh=1.35)

def p_lists():
    newpage("Components · Containment","Lists")
    y=bodytop()
    caption(MX,y,W-2*MX,"Lists are continuous, vertically stacked rows. One-, two- and three-line items combine a leading element "
            "(icon, avatar, image, control), primary + supporting text, and a trailing element.")
    sect(MX,y+64,"One-line · two-line · three-line")
    R([MX,y+96,W-2*MX,64],fill=SURFACE,radius=0); m_listitem(MX,y+96,W-2*MX,"Single-line item",lead="person",trail="chevron",h=64)
    LN((MX,y+160),(W-MX,y+160),stroke=OUTLINE_V,sw=1)
    m_listitem(MX,y+162,W-2*MX,"Two-line item","Supporting text on the second line",lead="mail",trail="star",h=76)
    LN((MX,y+238),(W-MX,y+238),stroke=OUTLINE_V,sw=1)
    R([MX+16,y+252,56,56],fill=SURFACE_V,radius=8); icon("star",MX+30,y+266,28,ON_SURFACE_V)
    T(MX+88,y+256,600,"Three-line item",size=16,color=ON_SURFACE); T(MX+88,y+280,W-2*MX-160,"Supporting text that can wrap onto a second line for more detail about this row.",size=13.5,color=ON_SURFACE_V,lh=1.35)
    icon("more",W-MX-40,y+266,24,ON_SURFACE_V,1.8)
    sect(MX,y+360,"Leading & trailing options")
    opts=[("Icon","person"),("Avatar","circle"),("Image","square"),("Control","switch")]
    for i,(t,k) in enumerate(opts):
        xx=MX+i*((W-2*MX)/4)
        if k=="person": DOT(xx+24,y+416,20,fill=PRIMARY_C); icon("person",xx+12,y+404,24,ON_PRIMARY_C,1.8)
        elif k=="circle": DOT(xx+24,y+416,20,fill=TERTIARY_C); T(xx+4,y+406,40,"A",size=16,color=ON_TERTIARY_C,weight=600,align="center")
        elif k=="square": R([xx+4,y+396,40,40],fill=SURFACE_V,radius=8)
        else: m_switch(xx,y+400,True)
        T(xx+56,y+406,140,t,size=14,color=ON_SURFACE)
    specrow(MX,y+490,[("One-line","56 dp"),("Two-line","72 dp"),("Three-line","88 dp"),("Keyline","16 / 72 dp"),("Divider","1 dp")])

def p_badges_progress():
    newpage("Components · Communication","Badges, progress & loading",tone=SECONDARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Badges mark an icon with a count or dot in the error/tertiary role. Progress indicators show ongoing "
            "work — linear or circular, determinate or indeterminate. M3E adds a distinctive contained loading indicator.")
    sect(MX,y+64,"Badges",SECONDARY)
    for i,(kind,) in enumerate([("dot",),("num",),("big",)]):
        xx=MX+i*140; icon("notifications",xx+8,y+100,32,ON_SURFACE)
        if kind=="dot": DOT(xx+34,y+100,5,fill=ERROR)
        elif kind=="num": R([xx+30,y+92,20,18],fill=ERROR,radius=9); T(xx+30,y+95,20,"3",size=11,color=ON_ERROR,weight=600,align="center")
        else: R([xx+30,y+92,30,18],fill=ERROR,radius=9); T(xx+30,y+95,30,"99+",size=10,color=ON_ERROR,weight=600,align="center")
        T(xx,y+146,120,["Dot","Count","Overflow"][i],size=12,color=MUTE)
    sect(MX,y+210,"Linear progress",SECONDARY)
    R([MX,y+250,W-2*MX,4],fill=SURFACE_V,radius=2); R([MX,y+250,(W-2*MX)*0.6,4],fill=PRIMARY,radius=2); DOT(MX+(W-2*MX)*0.62,y+252,2,fill=PRIMARY)
    T(MX,y+266,300,"Determinate · 60%",size=11,color=MUTE)
    R([MX,y+300,W-2*MX,4],fill=SURFACE_V,radius=2); R([MX+(W-2*MX)*0.35,y+300,(W-2*MX)*0.3,4],fill=PRIMARY,radius=2)
    T(MX,y+316,300,"Indeterminate",size=11,color=MUTE)
    sect(MX,y+360,"Circular & loading (M3E)",SECONDARY)
    DOT(MX+40,y+430,28,stroke=SURFACE_V,sw=4); PATH(f"M {MX+40} {y+402} A 28 28 0 0 1 {MX+68} {y+430}",stroke=PRIMARY,sw=4)
    R([MX+140,y+400,60,60],fill=PRIMARY_C,radius=16); PATH(f"M {MX+170} {y+414} A 16 16 0 1 1 {MX+156} {y+422}",stroke=PRIMARY,sw=4)
    T(MX+40-30,y+474,120,"Circular",size=11,color=MUTE,align="center"); T(MX+140,y+474,120,"Contained (M3E)",size=11,color=MUTE)
    specrow(MX,y+540,[("Badge","error role"),("Linear","4 dp"),("Circular","4 dp track"),("States","det / indet"),("Loading","M3E shape")])

def p_pickers():
    newpage("Components · Selection","Date & time pickers",tone=SECONDARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Pickers help enter a date or time via a calendar/clock (rich) or a compact input field. Modal dialogs "
            "use Extra-large corners and Level 3 elevation.")
    # date picker
    sect(MX,y+64,"Date picker",SECONDARY)
    dx,dw=MX,380; SH([dx,y+96,dw,420],fill=SC_HIGH,radius=28,elev=3)
    T(dx+24,y+116,dw-40,"Select date",size=12,color=ON_SURFACE_V); T(dx+24,y+138,dw-40,"Fri, Jul 3",size=28,color=ON_SURFACE,weight=400)
    LN((dx,y+192),(dx+dw,y+192),stroke=OUTLINE_V,sw=1)
    for i,d in enumerate(["S","M","T","W","T","F","S"]): T(dx+24+i*48,y+206,44,d,size=12,color=ON_SURFACE_V,align="center")
    for wk in range(4):
        for dd in range(7):
            n=wk*7+dd+1; cxx=dx+24+dd*48+22; cyy=y+248+wk*44
            if n==3: DOT(cxx,cyy,17,fill=PRIMARY); T(cxx-22,cyy-8,44,str(n),size=13,color=ON_PRIMARY,weight=600,align="center")
            else: T(cxx-22,cyy-8,44,str(n),size=13,color=ON_SURFACE,align="center")
    m_button(dx+dw-190,y+460,"Cancel","text"); m_button(dx+dw-90,y+460,"OK","text")
    # time picker
    sect(MX+430,y+64,"Time picker",SECONDARY)
    tx=MX+430; DOT(tx+140,y+280,120,fill=SC); DOT(tx+140,y+280,120,fill=SC)
    for hh in range(12):
        a=-math.pi/2+hh*math.pi/6; hx=tx+140+96*math.cos(a); hy=y+280+96*math.sin(a)
        if hh==2: DOT(hx,hy,20,fill=PRIMARY); T(hx-20,hy-8,40,"3",size=14,color=ON_PRIMARY,weight=600,align="center")
        else: T(hx-20,hy-8,40,str(hh if hh else 12),size=14,color=ON_SURFACE,align="center")
    LN((tx+140,y+280),(tx+140+80*math.cos(-math.pi/2+2*math.pi/6),y+280+80*math.sin(-math.pi/2+2*math.pi/6)),stroke=PRIMARY,sw=2.5)
    DOT(tx+140,y+280,4,fill=PRIMARY)
    R([tx+70,y+430,60,50],fill=PRIMARY_C,radius=8); T(tx+70,y+444,60,"10",size=24,color=ON_PRIMARY_C,align="center")
    T(tx+134,y+444,20,":",size=24,color=ON_SURFACE,align="center")
    R([tx+150,y+430,60,50],fill=SURFACE_V,radius=8); T(tx+150,y+444,60,"09",size=24,color=ON_SURFACE,align="center")
    specrow(MX,y+560,[("Shape","XL · 28dp"),("Elevation","Level 3"),("Modes","cal / input"),("Selected","Primary"),("Actions","2 text btns")])

def p_carousel():
    newpage("Components · Containment","Carousel",tone=TERTIARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Refreshed in M3 Expressive, the carousel lays out items that resize as they scroll — a large focal item, "
            "medium neighbours, and small edges — for browsing images and media with a sense of motion.")
    sect(MX,y+64,"Multi-browse layout",TERTIARY)
    widths=[70,120,300,120,70]; xx=MX
    for i,w in enumerate(widths):
        R([xx,y+96,w,220],fill=[TERTIARY_C,SECONDARY_C,PRIMARY_C,SECONDARY_C,TERTIARY_C][i],radius=[8,12,20,12,8][i])
        if i==2: icon("star",xx+w/2-16,y+180,32,ON_PRIMARY_C); T(xx+16,y+270,w-32,"Focal item",size=14,color=ON_PRIMARY_C,weight=500)
        xx+=w+12
    note(MX,y+340,W-2*MX,"Item size communicates focus: the centred item is largest, and corners round more as items grow. Scrolling "
         "runs on a spring so items settle into their sizes.")
    sect(MX,y+410,"Hero & full-screen layouts",TERTIARY)
    R([MX,y+442,(W-2*MX)*0.7,180],fill=PRIMARY_C,radius=20); R([MX+(W-2*MX)*0.7+12,y+442,(W-2*MX)*0.3-12,180],fill=SECONDARY_C,radius=12)
    icon("star",MX+(W-2*MX)*0.35-16,y+520,32,ON_PRIMARY_C)
    specrow(MX,y+660,[("Layouts","multi / hero / full"),("Focal","largest"),("Corners","grow with size"),("Motion","spring"),("Use","media browse")])

def p_screen_home():
    newpage("Patterns","Composed screen — home feed",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"A complete phone screen assembled entirely from the kit: top app bar, search, a feed of cards, a FAB, "
            "and a bottom navigation bar — every element drawn from primitives.")
    gx=MX+(W-2*MX-330)/2; gy=y+60; gw,gh=330,700; cb=m_phone(gx,gy,gw,gh)
    m_topbar(cb[0],cb[1],cb[2],"Discover",nav="menu",actions=("more-h",))
    SH([cb[0]+16,cb[1]+76,cb[2]-32,44,],fill=SC_HIGH,radius=22,elev=1); icon("search",cb[0]+30,cb[1]+88,22,ON_SURFACE_V); T(cb[0]+60,cb[1]+90,200,"Search",size=14,color=ON_SURFACE_V)
    xx=cb[0]+16
    for lb,sel in [("All",True),("News",False),("Music",False),("Art",False)]:
        w=m_chip(xx,cb[1]+134,lb,"filter",selected=sel); xx+=w+8
    cy=cb[1]+186
    for i in range(3):
        m_card(cb[0]+16,cy,cb[2]-32,150,"elevated"); R([cb[0]+28,cy+12,cb[2]-56,72],fill=[PRIMARY_C,TERTIARY_C,SECONDARY_C][i],radius=8)
        T(cb[0]+28,cy+94,cb[2]-56,["Morning briefing","New album released","Gallery opening"][i],size=15,color=ON_SURFACE,weight=500)
        T(cb[0]+28,cy+118,cb[2]-56,"Supporting detail line",size=12,color=ON_SURFACE_V); cy+=164
    m_fab(cb[0]+cb[2]-72,cb[1]+cb[3]-152,"add","regular",tone=PRIMARY,fg=ON_PRIMARY)
    m_navbar(cb[0],cb[1]+cb[3]-80,cb[2],[("home","Home"),("search","Find"),("favorite","Saved"),("person","You")],active=0)
    sx=gx+gw+50
    for i,(n,t) in enumerate([("1","Top app bar — title + overflow"),("2","Docked search bar"),("3","Filter chip row"),("4","Elevated content cards"),("5","Primary FAB — compose"),("6","Bottom navigation")]):
        yy=gy+i*70; DOT(sx+14,yy+14,13,fill=PRIMARY); T(sx+8,yy+6,20,n,size=13,color=ON_PRIMARY,weight=700,align="center"); T(sx+40,yy+6,W-MX-sx-40,t,size=14,color=ON_SURFACE,lh=1.3)

def p_screen_detail():
    newpage("Patterns","Composed screen — detail",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"A detail screen: a large collapsing app bar with hero media, title and metadata, body text, chips, and a "
            "pinned action bar — the read-and-act pattern.")
    gx=MX+(W-2*MX-330)/2; gy=y+60; gw,gh=330,700; cb=m_phone(gx,gy,gw,gh)
    R([cb[0],cb[1],cb[2],220],fill=PRIMARY_C,radius=0); R([cb[0],cb[1],cb[2],220],fill=PRIMARY_C)
    icon("back",cb[0]+16,cb[1]+20,24,ON_PRIMARY_C); icon("favorite",cb[0]+cb[2]-84,cb[1]+20,24,ON_PRIMARY_C); icon("share",cb[0]+cb[2]-44,cb[1]+20,24,ON_PRIMARY_C)
    icon("star",cb[0]+cb[2]/2-24,cb[1]+90,48,ON_PRIMARY_C)
    T(cb[0]+20,cb[1]+240,cb[2]-40,"Expressive by design",size=22,color=ON_SURFACE,weight=500)
    T(cb[0]+20,cb[1]+274,cb[2]-40,"Design system · 12 min read",size=13,color=ON_SURFACE_V)
    xx=cb[0]+20
    for lb in ["Design","Android","M3E"]:
        w=m_chip(xx,cb[1]+302,lb,"suggestion"); xx+=w+8
    for i in range(4): R([cb[0]+20,cb[1]+352+i*24,cb[2]-40-(i%2)*40,10],fill=SURFACE_V,radius=5)
    R([cb[0],cb[1]+cb[3]-72,cb[2],72],fill=SC)
    m_button(cb[0]+16,cb[1]+cb[3]-56,"Bookmark","outlined"); R([cb[0]+cb[2]-150,cb[1]+cb[3]-58,134,44],fill=PRIMARY,radius=22); T(cb[0]+cb[2]-150,cb[1]+cb[3]-46,134,"Read now",size=14,color=ON_PRIMARY,weight=500,align="center")
    sx=gx+gw+50
    for i,(n,t) in enumerate([("1","Collapsing hero app bar"),("2","Back + favourite + share"),("3","Title + metadata"),("4","Attribute chips"),("5","Body text"),("6","Pinned action bar")]):
        yy=gy+i*70; DOT(sx+14,yy+14,13,fill=PRIMARY); T(sx+8,yy+6,20,n,size=13,color=ON_PRIMARY,weight=700,align="center"); T(sx+40,yy+6,W-MX-sx-40,t,size=14,color=ON_SURFACE,lh=1.3)

def p_screen_settings():
    newpage("Patterns","Composed screen — settings",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"A settings screen: grouped list sections with icons, switches and disclosure arrows under a center "
            "app bar — the canonical list pattern with inline controls.")
    gx=MX+(W-2*MX-330)/2; gy=y+60; gw,gh=330,700; cb=m_phone(gx,gy,gw,gh)
    m_topbar(cb[0],cb[1],cb[2],"Settings",nav="back",center=True,actions=())
    cy=cb[1]+80
    T(cb[0]+20,cy,cb[2]-40,"ACCOUNT",size=11,color=PRIMARY,weight=600,spacing=1)
    for i,(ic,t,ctrl) in enumerate([("person","Profile","chevron"),("notifications","Notifications","switch"),("mail","Email sync","switch")]):
        ry=cy+28+i*60; icon(ic,cb[0]+20,ry+18,24,ON_SURFACE_V,1.8); T(cb[0]+60,ry+20,180,t,size=15,color=ON_SURFACE)
        if ctrl=="switch": m_switch(cb[0]+cb[2]-72,ry+14,i==1)
        else: icon("chevron",cb[0]+cb[2]-40,ry+18,22,ON_SURFACE_V,1.8)
    cy2=cy+28+3*60+20
    T(cb[0]+20,cy2,cb[2]-40,"DISPLAY",size=11,color=PRIMARY,weight=600,spacing=1)
    for i,(ic,t,ctrl) in enumerate([("star","Dark theme","switch"),("settings","Text size","chevron"),("home","Wallpaper colour","chevron")]):
        ry=cy2+28+i*60; icon(ic,cb[0]+20,ry+18,24,ON_SURFACE_V,1.8); T(cb[0]+60,ry+20,180,t,size=15,color=ON_SURFACE)
        if ctrl=="switch": m_switch(cb[0]+cb[2]-72,ry+14,True)
        else: icon("chevron",cb[0]+cb[2]-40,ry+18,22,ON_SURFACE_V,1.8)
    sx=gx+gw+50
    for i,(n,t) in enumerate([("1","Center app bar + back"),("2","Section overline (primary)"),("3","List rows · 56dp"),("4","Leading icons · 24dp"),("5","Inline switches"),("6","Disclosure chevrons")]):
        yy=gy+i*70; DOT(sx+14,yy+14,13,fill=PRIMARY); T(sx+8,yy+6,20,n,size=13,color=ON_PRIMARY,weight=700,align="center"); T(sx+40,yy+6,W-MX-sx-40,t,size=14,color=ON_SURFACE,lh=1.3)

def p_largescreen():
    newpage("Patterns","Large-screen · list-detail",tone=TERTIARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"On expanded widths, the same app becomes two panes: a navigation rail, a list pane, and a detail pane. "
            "Nothing is redesigned — the size class simply reveals more structure.")
    tx,ty,tw,th=MX,y+64,W-2*MX,540; SH([tx,ty,tw,th],fill=SURFACE,radius=16,elev=2); R([tx,ty,tw,th],fill="none",stroke=OUTLINE_V,sw=1.4,radius=16)
    # rail
    R([tx,ty,80,th],fill=SC); m_fab(tx+16,ty+20,"add","small",tone=PRIMARY_C,fg=ON_PRIMARY_C)
    for i,ic in enumerate(["mail","star","share","edit"]):
        cyy=ty+110+i*64
        if i==0: PILL([tx+16,cyy-6,48,32],fill=SECONDARY_C)
        icon(ic,tx+28,cyy-2,24,(ON_SECONDARY_C if i==0 else ON_SURFACE_V))
    # list pane
    lx=tx+80; lw2=360; R([lx,ty,lw2,th],fill=SC_LOW)
    m_topbar(lx,ty,lw2,"Inbox",nav="menu",actions=("search",))
    for i in range(6):
        ry=ty+72+i*74
        if i==1: R([lx,ry,lw2,72],fill=SECONDARY_C,fo=0.5)
        DOT(lx+34,ry+36,20,fill=[PRIMARY_C,TERTIARY_C,SECONDARY_C][i%3]); T(lx+8,ry+26,52,"AJ"[i%2],size=14,color=ON_PRIMARY_C,weight=600,align="center")
        T(lx+70,ry+16,lw2-90,["Alex Rivera","Jordan Kim","Sam Cole","Pat Lee","Robin Fox","Sky Nunes"][i],size=15,color=ON_SURFACE,weight=500)
        T(lx+70,ry+40,lw2-90,"Subject line preview text…",size=13,color=ON_SURFACE_V)
    # detail pane
    dx=lx+lw2; dw2=tx+tw-dx; R([dx,ty,dw2,th],fill=SURFACE)
    m_topbar(dx,ty,dw2,"",nav="back",actions=("favorite","share","more-h"))
    DOT(dx+50,ty+110,26,fill=PRIMARY_C); T(dx+92,ty+96,300,"Alex Rivera",size=18,color=ON_SURFACE,weight=500); T(dx+92,ty+124,300,"to me · 9:41 AM",size=13,color=ON_SURFACE_V)
    T(dx+30,ty+180,dw2-60,"Re: Material 3 Expressive rollout",size=20,color=ON_SURFACE,weight=400)
    for i in range(6): R([dx+30,ty+230+i*26,dw2-60-(i%3)*50,10],fill=SURFACE_V,radius=5)
    specrow(MX,y+630,[("Panes","rail + list + detail"),("Rail","80 dp"),("List","≤ 360 dp"),("Selected","secondary c."),("Class","Expanded")])

def p_predictive_back():
    newpage("Android 16 platform","Edge-to-edge & predictive back",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Android 16 enforces edge-to-edge for apps targeting SDK 36: content draws behind the system bars, "
            "which become transparent. Predictive back previews the destination as the user drags. (Platform behaviours — verify against current developer docs.)")
    # edge-to-edge
    sect(MX,y+70,"Edge-to-edge")
    for i,(lab,inset) in enumerate([("Legacy · opaque bars",True),("Edge-to-edge · transparent",False)]):
        gx=MX+i*300; gw,gh=250,420; cb=m_phone(gx,y+102,gw,gh)
        if inset:
            R([cb[0],cb[1],cb[2],40],fill=SURFACE_V); R([cb[0],cb[1]+cb[3]-40,cb[2],40],fill=SURFACE_V)
            R([cb[0],cb[1]+40,cb[2],cb[3]-80],fill=PRIMARY_C)
        else:
            R([cb[0],cb[1],cb[2],cb[3]],fill=PRIMARY_C)
            R([cb[0]+cb[2]/2-20,cb[1]+cb[3]-24,40,4],fill=ON_PRIMARY_C,radius=2)  # gesture handle
        T(gx,y+102+gh+10,gw,lab,size=12,color=MUTE,align="center")
    # predictive back
    sect(MX+620,y+70,"Predictive back")
    bx=MX+620; gw,gh=250,420; cb=m_phone(bx,y+102,gw,gh)
    R([cb[0]+40,cb[1],cb[2]-40,cb[3]],fill=SC_HIGH,radius=20)   # current, sliding out
    R([cb[0],cb[1],cb[2]-60,cb[3]],fill=PRIMARY_C,radius=20)    # destination peeking
    icon("home",cb[0]+cb[2]/2-40,cb[1]+cb[3]/2-24,48,ON_PRIMARY_C)
    PATH(f"M {cb[0]+cb[2]-30} {cb[1]+cb[3]/2-20} L {cb[0]+cb[2]-45} {cb[1]+cb[3]/2} L {cb[0]+cb[2]-30} {cb[1]+cb[3]/2+20}",stroke=ON_SURFACE_V,sw=2.5)
    T(bx,y+102+gh+10,gw,"Drag reveals the destination",size=12,color=MUTE,align="center")
    note(MX,y+570,W-2*MX,"Handle insets with WindowInsets so content isn't hidden behind bars; opt into predictive back and let the "
         "system animate cross-activity and cross-app transitions.")

def p_live_updates():
    newpage("Android 16 platform","Notifications & Live Updates",tone=PRIMARY)
    y=bodytop()
    caption(MX,y,W-2*MX,"Android 16 adds progress-centric “Live Updates” — ongoing notifications for rideshare, delivery and "
            "navigation that surface on the lock screen and status bar. Standard templates keep them consistent. (Platform feature — verify against current docs.)")
    # notification card
    sect(MX,y+70,"Live Update notification")
    R([MX,y+102,W-2*MX,160],fill=SC_HIGH,radius=24,stroke=OUTLINE_V,sw=1)
    DOT(MX+40,y+140,18,fill=PRIMARY); icon("home",MX+24,y+124,32,ON_PRIMARY)
    T(MX+80,y+124,400,"Order on the way",size=17,color=ON_SURFACE,weight=500); T(MX+80,y+150,400,"Arriving in 8 min · 3 stops away",size=14,color=ON_SURFACE_V)
    R([MX+80,y+186,W-2*MX-300,8],fill=SURFACE_V,radius=4); R([MX+80,y+186,(W-2*MX-300)*0.65,8],fill=PRIMARY,radius=4)
    R([W-MX-180,y+180,150,44],fill=PRIMARY_C,radius=22); T(W-MX-180,y+192,150,"Track",size=14,color=ON_PRIMARY_C,weight=500,align="center")
    # anatomy
    sect(MX,y+310,"What's new for UI")
    for i,(t,d) in enumerate([("Progress templates","Standard layouts for ongoing, time-bound tasks."),
                              ("Prominent chips","A compact status chip appears in the status bar."),
                              ("Richer previews","Notifications expand with imagery and actions."),
                              ("Adaptive apps","Large-screen resizability is expected by default.")]):
        xx=MX+(i%2)*((W-2*MX-24)/2+24); yy=y+346+(i//2)*130
        SH([xx,yy,(W-2*MX-24)/2,110],fill=SURFACE,radius=12,elev=1); R([xx,yy,5,110],fill=PRIMARY,radius=2)
        T(xx+20,yy+18,(W-2*MX-24)/2-36,t,size=17,color=INK,weight=500); T(xx+20,yy+48,(W-2*MX-24)/2-36,d,size=13.5,color=MUTE,lh=1.4)

def p_a11y_targets():
    newpage("Accessibility","Targets, contrast & focus",tone=ERROR)
    y=bodytop()
    caption(MX,y,W-2*MX,"Accessibility is a floor, not a feature. Keep interactive targets ≥ 48dp, text contrast ≥ 4.5:1 "
            "(3:1 for large text and UI outlines), and never signal state by colour alone.")
    sect(MX,y+64,"Touch targets ≥ 48dp",ERROR)
    R([MX,y+100,48,48],fill="none",stroke=ERROR,sw=1.4,dash=[4,4],radius=8); DOT(MX+24,y+124,10,fill=PRIMARY)
    T(MX+68,y+108,400,"A 20dp visual keeps a 48dp target — pad, don't shrink the hit area.",size=14,color=ON_SURFACE,lh=1.4)
    R([MX+560,y+100,48,48],fill="none",stroke=ERROR,sw=1.4,dash=[4,4],radius=8); m_checkbox(MX+574,y+114,True)
    sect(MX,y+190,"Contrast",ERROR)
    pairs=[("Aa","On-surface / surface","15.8:1",ON_SURFACE,SURFACE,True),("Aa","On-primary / primary","8.6:1",ON_PRIMARY,PRIMARY,True),
           ("Aa","Primary / surface","5.1:1",PRIMARY,SURFACE,True),("Aa","Faint grey / surface","1.9:1","#BBB6C0",SURFACE,False)]
    for i,(aa,lab,ratio,fg,bg,ok) in enumerate(pairs):
        xx=MX+i*((W-2*MX)/4); R([xx,y+226,110,70],fill=bg,radius=8,stroke=OUTLINE_V,sw=1); T(xx,y+242,110,aa,size=28,color=fg,weight=500,align="center")
        T(xx,y+306,150,lab,size=12,color=MUTE,lh=1.3); T(xx,y+340,150,ratio,size=18,color=(HAVE_GREEN if ok else ERROR),weight=600,mono=True)
        icon("check" if ok else "close",xx+70,y+338,20,(HAVE_GREEN if ok else ERROR),2)
    sect(MX,y+410,"Beyond colour",ERROR)
    note(MX,y+440,W-2*MX,"Pair colour with an icon, label or shape so state survives greyscale and colour-vision deficiency. Provide "
         "content descriptions for every non-text control, respect the system focus order, and support larger font scales.")
    for i,(ic,t) in enumerate([("check","Icon + colour"),("check","Text label"),("check","Focus ring"),("check","Content desc.")]):
        xx=MX+i*((W-2*MX)/4); icon(ic,xx,y+520,22,HAVE_GREEN,2); T(xx+32,y+522,200,t,size=13,color=ON_SURFACE)

def p_a11y_scaling():
    newpage("Accessibility","Text scaling & high contrast (M3E)",tone=ERROR)
    y=bodytop()
    caption(MX,y,W-2*MX,"M3 Expressive supports dynamic scaling of text and icons for low vision, plus a high-contrast mode. "
            "Layouts must reflow — never clip — as type grows to ~200%.")
    sect(MX,y+64,"Scaling",ERROR)
    for i,(scl,lab) in enumerate([(1.0,"100% · default"),(1.3,"130% · large"),(1.8,"180% · largest")]):
        xx=MX+i*((W-2*MX)/3); SH([xx,y+96,(W-2*MX)/3-20,200],fill=SURFACE,radius=12,elev=1)
        T(xx+16,y+114,(W-2*MX)/3-52,"Settings",size=int(16*scl),color=ON_SURFACE,weight=500)
        T(xx+16,y+114+int(28*scl),(W-2*MX)/3-52,"Adjust display",size=int(13*scl),color=ON_SURFACE_V,lh=1.3)
        m_switch(xx+16,y+240,True); T(xx,y+306,(W-2*MX)/3,lab,size=12,color=MUTE,align="center")
    sect(MX,y+360,"High-contrast mode",ERROR)
    for i,(lab,bg,fg,ol) in enumerate([("Standard",SURFACE,ON_SURFACE,OUTLINE_V),("High contrast","#FFFFFF","#000000","#000000")]):
        xx=MX+i*((W-2*MX-24)/2+24); wpp=(W-2*MX-24)/2
        R([xx,y+396,wpp,150],fill=bg,radius=12,stroke=ol,sw=(1 if i==0 else 2))
        R([xx+20,y+416,160,44],fill=(PRIMARY if i==0 else "#000000"),radius=22); T(xx+20,y+428,160,"Primary",size=14,color="#FFFFFF",weight=500,align="center")
        R([xx+20,y+476,160,44],fill="none",stroke=(OUTLINE if i==0 else "#000000"),sw=(1.2 if i==0 else 2),radius=22); T(xx+20,y+488,160,"Outlined",size=14,color=(ON_SURFACE if i==0 else "#000000"),weight=500,align="center")
        T(xx,y+556,wpp,lab,size=13,color=MUTE,align="center")
    note(MX,y+600,W-2*MX,"High contrast thickens outlines and darkens text/borders to maximise separation — driven by the same "
         "colour roles, so no bespoke theme is required.")

def p_dos_donts():
    newpage("Summary","Do & don't")
    y=bodytop()
    for i,(head,ok,c,pts) in enumerate([("Do",True,HAVE_GREEN,
        ["Theme with colour roles, not raw hex","One high-emphasis action (FAB / filled) per view","Adapt navigation to the window size class","Keep 48dp targets and 4.5:1 contrast","Use the type scale and 4dp spacing grid","Let motion communicate state with springs"]),
        ("Don't",False,ERROR,
        ["Don't hard-code colours that ignore dark theme","Don't stack multiple competing primary actions","Don't stretch a phone layout to fill a tablet","Don't shrink hit areas below 48dp","Don't invent one-off sizes off the scale","Don't signal state with colour alone"])]):
        xx=MX+i*((W-2*MX-24)/2+24); wpp=(W-2*MX-24)/2
        SH([xx,y,wpp,470],fill=SURFACE,radius=16,elev=1); R([xx,y,wpp,6],fill=c,radius=3)
        icon("check" if ok else "close",xx+24,y+24,30,c,2.6); T(xx+66,y+26,wpp-80,head,size=24,color=INK,weight=500)
        for j,p in enumerate(pts):
            ry=y+88+j*62; icon("check" if ok else "close",xx+24,ry,20,c,2.2); T(xx+56,ry-2,wpp-80,p,size=14.5,color=ON_SURFACE,lh=1.3)

def p_colophon():
    newpage("Reference","Colophon & sources",bg=PRIMARY)
    global L
    L.rect([0,0,W,H],fill=PRIMARY)
    T(MX,120,W-2*MX,"Colophon",size=44,color=ON_PRIMARY,weight=600)
    T(MX,190,W-2*MX-40,"This 64-page reference was composed with the FrameGraph SDK using primitives only — rectangles, text, "
      "lines, circles and paths. No pre-built widgets: every Android component here is exact, inspectable geometry.",size=17,color="#EFE7FF",lh=1.55)
    LN((MX,300),(W-MX,300),stroke="#FFFFFF44",sw=1)
    T(MX,320,W-2*MX,"Grounded in",size=13,color=PRIMARY_C,weight=600,spacing=1)
    for i,(t,u) in enumerate([("Material 3 — m3.material.io","styles: colour · typography · shape · components"),
                              ("Material 3 Expressive — m3.material.io/blog","new components · shapes · motion springs"),
                              ("Android Developers — developer.android.com","Compose Material 3 · adaptive layouts · platform"),
                              ("Type scale & colour roles","15 styles · 26 roles · 6 tonal palettes")]):
        yy=350+i*70; DOT(MX+8,yy+10,4,fill=PRIMARY_C); T(MX+28,yy,W-2*MX-40,t,size=17,color=ON_PRIMARY,weight=500); T(MX+28,yy+26,W-2*MX-40,u,size=13,color="#D6C8F5")
    LN((MX,660),(W-MX,660),stroke="#FFFFFF44",sw=1)
    R([MX,690,W-2*MX,200],fill="#4A3A82",radius=16)
    T(MX+24,y+540,W-2*MX-48,"Disclaimer",size=15,color=PRIMARY_C,weight=600) if False else T(MX+24,712,W-2*MX-48,"Disclaimer",size=15,color=PRIMARY_C,weight=600)
    T(MX+24,740,W-2*MX-48,"No statement here should be taken for granted. Specs reflect public Material 3 / M3 Expressive guidance "
      "at the time of writing; platform behaviours (Android 16 edge-to-edge, predictive back, Live Updates) are summarised "
      "and should be verified against current developer documentation. Dynamic colour values vary per device.",size=14,color="#EDE7FF",lh=1.6)
    T(MX,H-70,W-2*MX,"Android 16 · Material 3 Expressive — UI Guidelines   ·   Generated with the FrameGraph SDK, primitives only   ·   Claude Opus 4.8   ·   2026-07",
      size=11,color="#C9BAF0",mono=True)

def p_states():
    newpage("Components","Interaction states & state layers")
    y=bodytop()
    caption(MX,y,W-2*MX,"Every interactive element carries five states. Material expresses hover/focus/pressed as a translucent "
            "“state layer” of the content colour (the “On” role) over the container — so any component reacts consistently.")
    states=[("Enabled",0.0,"Resting"),("Hovered",0.08,"8% state layer"),("Focused",0.10,"10% + focus ring"),("Pressed",0.10,"10% + ripple"),("Dragged",0.16,"16% + Level 4")]
    cw=(W-2*MX-4*16)/5
    for i,(lab,op,d) in enumerate(states):
        xx=MX+i*(cw+16); R([xx,y+80,cw,cw],fill=PRIMARY,radius=cw/2)
        if op>0: L.circle([xx+cw/2,y+80+cw/2],cw/2,fill=ON_PRIMARY,fill_opacity=op)
        if lab=="Focused": DOT(xx+cw/2,y+80+cw/2,cw/2+4,stroke=PRIMARY,sw=2)
        icon("favorite",xx+cw/2-14,y+80+cw/2-14,28,ON_PRIMARY,2)
        T(xx,y+80+cw+12,cw,lab,size=13,color=INK,weight=600,align="center"); T(xx,y+80+cw+34,cw,d,size=10.5,color=MUTE,align="center",lh=1.15)
    yy=y+80+cw+90
    sect(MX,yy,"State-layer opacities")
    specrow(MX,yy+30,[("Hover","8%"),("Focus","10%"),("Press","10%"),("Drag","16%"),("Colour","the “On” role")])
    yy2=yy+110
    sect(MX,yy2,"Disabled")
    m_button(MX,yy2+34,"Enabled","filled"); L.rect([MX+180,yy2+34,120,40],fill=ON_SURFACE,fill_opacity=0.12,radius=20); T(MX+180,yy2+46,120,"Disabled",size=14,color=ON_SURFACE,weight=500,align="center")
    L.rect([MX+180,yy2+34,120,40],fill=ON_SURFACE,fill_opacity=0.0)
    note(MX+340,yy2+40,W-2*MX-340,"Disabled = 38% content opacity on a 12% container. It stays visible for context but is clearly inert; "
         "never remove a control silently.")

def p_motion_patterns():
    newpage("Shape · elevation · motion","Transition patterns")
    y=bodytop()
    caption(MX,y,W-2*MX,"Four transition patterns route the eye between UI states. All run on springs in M3 Expressive — the "
            "pattern chooses the spatial relationship; the spring supplies the physics.")
    pats=[("Container transform","An element grows into the next surface — a card becomes a detail page.",PRIMARY),
          ("Shared axis","Peers slide + fade along x, y, or z to show forward / back or hierarchy.",SECONDARY),
          ("Fade through","Unrelated content fades out, then the new content fades in.",TERTIARY),
          ("Fade","Elements enter/exit within the same surface (dialogs, menus).",ON_SURFACE)]
    cw=(W-2*MX-24)/2
    for i,(t,d,c) in enumerate(pats):
        xx=MX+(i%2)*(cw+24); yy=y+70+(i//2)*250
        SH([xx,yy,cw,230],fill=SURFACE,radius=14,elev=1); R([xx,yy,cw,6],fill=c,radius=3)
        T(xx+22,yy+20,cw-40,t,size=19,color=INK,weight=500); T(xx+22,yy+52,cw-40,d,size=13.5,color=MUTE,lh=1.4)
        bx,by=xx+22,yy+110
        if i==0:
            R([bx,by,60,80],fill=c,fo=0.3,radius=8); icon("chevron",bx+70,by+28,24,OUTLINE)
            R([bx+110,by-10,cw-160,100],fill=c,fo=0.3,radius=12)
        elif i==1:
            R([bx,by,90,80],fill=c,fo=0.3,radius=8); PATH(f"M {bx+100} {by+40} L {bx+150} {by+40}",stroke=c,sw=2.5); PATH(f"M {bx+140} {by+30} L {bx+152} {by+40} L {bx+140} {by+50}",stroke=c,sw=2.5)
            R([bx+170,by,90,80],fill=c,fo=0.6,radius=8)
        elif i==2:
            L.circle([bx+40,by+40],34,fill=c,fill_opacity=0.25); icon("chevron",bx+90,by+28,24,OUTLINE); L.circle([bx+150,by+40],34,fill=c,fill_opacity=0.6)
        else:
            for k in range(3): L.rect([bx+k*70,by,56,80],fill=c,fill_opacity=0.2+k*0.25,radius=8)
    T(MX,y+70+2*250,W-2*MX,"Choose by relationship: transform for “this becomes that”, shared axis for navigation, fade-through for "
      "swaps, fade for in-place. Keep durations short and interruptible.",size=13,color=MUTE,lh=1.5)

# ---- build ----
HAVE_GREEN="#146C2E"
PAGES=[p_cover,p_contents,p_overview,p_principles,p_layout,p_spacing,p_breakpoints,
       p_adaptive,p_color_roles,p_tonal,p_baseline_light,p_baseline_dark,p_dynamic,p_color_usage,
       p_type_system,p_specimen_display,p_specimen_body,p_emphasized,
       p_shape_scale,p_m3e_shapes,p_elevation,p_motion,p_icon_system,p_icon_anatomy,
       p_components_overview,p_buttons,p_button_groups,p_split_buttons,p_icon_buttons,p_fab,p_fab_menu,
       p_cards,p_chips,p_textfields,p_textfield_states,p_menus,p_selection,p_sliders,p_dialogs,p_sheets,p_snackbars,
       p_topbars,p_bottombar,p_navbar,p_navrail,p_navdrawer,p_tabs,p_search,p_lists,p_badges_progress,p_pickers,p_carousel,
       p_states,p_motion_patterns,p_screen_home,p_screen_detail,p_screen_settings,p_largescreen,
       p_predictive_back,p_live_updates,p_a11y_targets,p_a11y_scaling,p_dos_donts,p_colophon]
# === END PAGES ===
for fn in PAGES: fn()
if __name__=="__main__":
    out=os.environ.get("OUTPUT_YAML_PATH","android16_material3_guidelines.fg.yaml")
    open(out,"w").write(serialize(b.build(), format="yaml")); print("wrote",out,"pages:",_N[0])
