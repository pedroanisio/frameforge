"""FrameForge v2 — AS-IS Architecture & Evolution Paths.

A publication-grade architecture deck, authored in the FrameForge SDK and
rendered through the FrameForge MCP. Every architectural claim is grounded in
the live tree (HEAD 2.4.1); see the closing evidence appendix for file-level
provenance. Blueprint-analytical visual system: cool paper, ink, one blue
accent + a subdued rust for gaps.
"""
import os
import math
from frameforge.sdk import DocumentBuilder, serialize

# ---------------------------------------------------------------- palette (closed)
PAPER="#F5F6F8"; CARD="#FFFFFF"; INK="#14171E"; SUB="#39404E"; MUTE="#5E6675"
FAINT="#98A0AD"; RULE="#E2E6EC"; HAIR="#ECEEF2"
ACC="#2E5BE6"; ACC2="#5B7EF0"; ACC_SOFT="#E7EDFD"; ACC_INK="#1B3C9E"
SIGNAL="#C25733"; SIGNAL_SOFT="#F7E7DF"           # subdued complement — gaps/warnings
BAND="#12151C"; BAND2="#1B1F29"                    # dark ground: title + dividers
PAPER_ON_BAND="#EDEFF3"; MUTE_ON_BAND="#9AA2B2"; FAINT_ON_BAND="#6B7385"
HAVE="#2E9E5B"; PARTIAL="#C08A2B"; GAP="#C0492E"; NA="#AAB0BB"
SANS=["Inter","DejaVu Sans","Helvetica Neue","Arial","sans-serif"]
MONO=["DejaVu Sans Mono","JetBrains Mono","Menlo","monospace"]
W,H=1600,900; MX=92
def fs(k): return round(15*(1.28**k),1)   # modular scale, base 15
# named steps
CAP,SML,BODY,LEAD,H3,H2,H1,HERO = 11,12.5,15,18.5,23,30,46,66

b=DocumentBuilder(title="FrameForge v2 — AS-IS Architecture & Evolution Paths",
                  profile="deck", lang="en")
L=None  # current layer (set per slide)

# ---------------------------------------------------------------- primitives
def T(x,y,w,s,*,size=BODY,color=INK,weight=None,mono=False,align=None,spacing=None,italic=False,lh=None):
    s=str(s); st={"font_family":(MONO if mono else SANS),"font_size":size,"color":color}
    if weight: st["font_weight"]=weight
    if align: st["text_align"]=align
    if spacing is not None: st["letter_spacing"]=spacing
    if italic: st["font_style"]="italic"
    if lh: st["line_height"]=lh
    # size the box for auto-wrapped lines too (avg glyph advance ≈ 0.53·size for this sans),
    # so a long line without explicit \n is never clipped to a single-line box height.
    cw=max(size*0.60,1); est=0
    for seg in s.split(chr(10)): est+=max(1, math.ceil(len(seg)*cw/max(w,1)))
    lines=max(s.count(chr(10))+1, est)
    L.text([x,y,w,size*(lh or 1.42)*lines+4], s, style=st)
def R(box,*,fill=None,stroke=None,sw=1.2,radius=0,dash=None,shadow=False,fo=None):
    f={}
    if fill is not None: f["fill"]=fill
    if stroke is not None:
        f["stroke"]=stroke; ss={"stroke_width":sw}
        if dash: ss["stroke_dasharray"]=dash
        f["stroke_style"]=ss
    if radius: f["radius"]=radius
    if fo is not None: f["fill_opacity"]=fo
    if shadow: f["shadow"]={"dx":0,"dy":3,"blur":16,"color":"#0E121C14"}
    L.rect(list(box), **f)
def LN(p0,p1,*,stroke=MUTE,sw=1.3,dash=None):
    ss={"stroke_width":sw,"stroke_linecap":"round"}
    if dash: ss["stroke_dasharray"]=dash
    L.line(list(p0),list(p1),stroke=stroke,stroke_style=ss)
def DOT(x,y,r,fill): L.circle([x,y],r,fill=fill)
def arrow(x1,y1,x2,y2,*,stroke=ACC,sw=1.6,dash=None,head=7):
    LN((x1,y1),(x2,y2),stroke=stroke,sw=sw,dash=dash)
    a=math.atan2(y2-y1,x2-x1); h=head
    p=[(x2,y2),(x2-h*math.cos(a-0.42),y2-h*math.sin(a-0.42)),(x2-h*math.cos(a+0.42),y2-h*math.sin(a+0.42))]
    L.path("M %.1f %.1f L %.1f %.1f L %.1f %.1f Z"%(p[0][0],p[0][1],p[1][0],p[1][1],p[2][0],p[2][1]), fill=stroke)
def chevron_arrow(x1,y1,x2,y2,**k): arrow(x1,y1,x2,y2,**k)

def node(x,y,w,h,title,sub=None,*,accent=ACC,fill=CARD,tint=None,tstroke=None,title_sz=SML,mono_sub=True):
    R([x,y,w,h],fill=(tint or fill),stroke=(tstroke or RULE),sw=1.2,radius=9,shadow=(tint is None))
    R([x,y,4,h],fill=accent,radius=2)
    T(x+15,y+11,w-24,title,size=title_sz,weight=700,color=INK)
    if sub: T(x+15,y+11+title_sz+7,w-26,sub,size=CAP,color=MUTE,mono=mono_sub,lh=1.32)
def kicker_dot(x,y,c=ACC): DOT(x,y,3.2,c)

# ---------------------------------------------------------------- slide chrome
FOLIO=[0]
def slide(kicker,title="",*,dark=False,sub=None):
    global L,FOLIO
    FOLIO[0]+=1; n=FOLIO[0]
    pg=b.page(f"s{n}", canvas={"size":[W,H],"units":"px"}, coordinate_mode="absolute")
    L=pg.layer("main")
    if dark:
        R([0,0,W,H],fill=BAND)
        return pg
    R([0,0,W,H],fill=PAPER)
    # top chrome
    R([MX,54,3,15],fill=ACC)
    T(MX+13,52,900,kicker.upper(),size=CAP,color=ACC_INK,weight=800,spacing=2.0)
    T(MX,72,W-2*MX-70,title,size=H2,weight=800,color=INK,lh=1.04)
    if sub: T(MX,72+H2*1.12,W-2*MX,sub,size=SML,color=MUTE,italic=True)
    LN((MX,72+H2*1.12+(22 if sub else 6)),(W-MX,72+H2*1.12+(22 if sub else 6)),stroke=RULE,sw=1.2)
    # footer
    LN((MX,H-40),(W-MX,H-40),stroke=HAIR,sw=1)
    T(MX,H-32,600,"FrameForge v2  ·  AS-IS Architecture",size=CAP,color=FAINT,weight=600,spacing=0.4)
    T(W-MX-120,H-32,120,f"{n:02d}",size=CAP,color=FAINT,weight=700,align="right")
    return pg
def body_top(): return 176   # y where slide body content begins

# ================================================================ SLIDES
def s_title():
    global L
    pg=b.page("title", canvas={"size":[W,H],"units":"px"}, coordinate_mode="absolute")
    L=pg.layer("main")
    R([0,0,W,H],fill=BAND)
    R([0,0,W,6],fill=ACC)
    # framed-derivation glyph (the FrameForge brackets) top-left
    gx,gy=MX,150
    for dx in (0,208):
        LN((gx+dx,gy),(gx+dx+(26 if dx==0 else -26),gy),stroke=ACC2,sw=3)
        LN((gx+dx,gy),(gx+dx,gy+150 if dx==0 else gy),stroke=ACC2,sw=3) if dx==0 else None
    # simpler bracket pair
    R([gx-2,gy-2,4,150],fill=ACC); R([gx-2,gy-2,30,4],fill=ACC); R([gx-2,gy+144,30,4],fill=ACC)
    R([gx+206,gy-2,4,150],fill=ACC); R([gx+180,gy-2,30,4],fill=ACC); R([gx+180,gy+144,30,4],fill=ACC)
    T(gx+52,gy+52,140,"FG",size=54,weight=800,color=PAPER_ON_BAND)
    # title block
    T(MX,382,1200,"FrameForge v2",size=HERO,weight=800,color="#FFFFFF",lh=1.0)
    T(MX,382+HERO*1.05,1300,"AS-IS Architecture & Evolution Paths",size=H1,weight=300,color=ACC2,lh=1.0)
    T(MX,382+HERO*1.05+H1*1.15+8,1080,
      "A declarative, multi-target document & vector-graphics intermediate representation — "
      "explained as it exists today, then measured against imperative live-DOM toolkits (SVG.js / Snap.svg).",
      size=LEAD,color=MUTE_ON_BAND,lh=1.5)
    # metric strip
    metrics=[("2.4.1","HEAD spec"),("1,804","model LOC"),("290","capabilities"),
             ("24","MCP tools"),("6","render targets"),("33","SDK modules")]
    mw=(W-2*MX)/len(metrics); my=760
    LN((MX,my-18),(W-MX,my-18),stroke="#2A2F3B",sw=1)
    for i,(v,k) in enumerate(metrics):
        x=MX+i*mw
        T(x,my,mw-20,v,size=H2,weight=800,color="#FFFFFF")
        T(x,my+H2*1.05,mw-20,k.upper(),size=CAP,color=FAINT_ON_BAND,weight=700,spacing=1.2)
    T(MX,H-52,1200,"Grounded in the live repository — not memory.   Generated by Claude Opus 4.8 via FrameForge MCP · 2026-07-03.",
      size=CAP,color=FAINT_ON_BAND,mono=True)

def s_exec():
    slide("Executive summary","What FrameForge is — and is not")
    y=body_top()
    # left: purpose + invariant
    T(MX,y,720,"Core purpose",size=SML,weight=800,color=ACC_INK,spacing=0.5)
    T(MX,y+24,730,"A Pydantic-typed document model is the single source of truth. Authors emit it "
      "through an SDK or 24 MCP tools; a hexagonal renderer walks it in z-order and lowers it to "
      "SVG, PNG, PDF, typeset PDF (LaTeX/TikZ), HTML, or TikZ.",
      size=BODY,color=SUB,lh=1.5)
    T(MX,y+130,730,"Architectural invariant",size=SML,weight=800,color=ACC_INK,spacing=0.5)
    T(MX,y+154,730,"Schema, EBNF grammar, validator, fixtures, docs and the 290-entry capability "
      "manifest are all generated from or checked against the model. The IR is the contract; "
      "renderers are replaceable adapters behind two ports.",
      size=BODY,color=SUB,lh=1.5)
    # is / is-not panels
    iy=y+272
    R([MX,iy,352,150],fill=CARD,stroke=RULE,radius=10,shadow=True)
    R([MX,iy,4,150],fill=HAVE,radius=2)
    T(MX+16,iy+13,320,"IT IS",size=CAP,weight=800,color=HAVE,spacing=1.4)
    for i,t in enumerate(["A declarative, verifiable render IR","Headless & backend-neutral (multi-target)",
                          "Reproducible — gated by golden hashes"]):
        DOT(MX+22,iy+46+i*30,2.6,HAVE); T(MX+34,iy+40+i*30,300,t,size=SML,color=SUB)
    R([MX+378,iy,352,150],fill=CARD,stroke=RULE,radius=10,shadow=True)
    R([MX+378,iy,4,150],fill=SIGNAL,radius=2)
    T(MX+394,iy+13,320,"IT IS NOT",size=CAP,weight=800,color=SIGNAL,spacing=1.4)
    for i,t in enumerate(["A live-DOM manipulation toolkit","An in-browser event/animation runtime",
                          "A single-target (SVG-only) library"]):
        DOT(MX+400,iy+46+i*30,2.6,SIGNAL); T(MX+412,iy+40+i*30,300,t,size=SML,color=SUB)
    # right: the 4-layer stack
    sx=MX+790; sw=W-MX-sx
    T(sx,y,sw,"The stack (top → bottom)",size=SML,weight=800,color=ACC_INK,spacing=0.5)
    layers=[("AUTHORING","SDK builders · 24 MCP tools · Markdown/SVG ingest",ACC),
            ("DOCUMENT IR","Pydantic model — Document → Page → Layer → Object",INK),
            ("RENDERING","Hexagonal: domain ports → application walk → adapters",SUB),
            ("TARGETS","SVG · PNG · PDF · PDF-TeX · HTML · TikZ",MUTE)]
    ly=y+30
    for i,(t,d,c) in enumerate(layers):
        yy=ly+i*88
        R([sx,yy,sw,74],fill=CARD,stroke=RULE,radius=9,shadow=True)
        R([sx,yy,6,74],fill=c,radius=3)
        T(sx+18,yy+13,sw-30,t,size=LEAD,weight=800,color=INK)
        T(sx+18,yy+42,sw-30,d,size=SML,color=MUTE,mono=True)
        if i<3: DOT(sx+sw/2,yy+81,3.2,FAINT)

def s_context():
    slide("System context","From intent to verified artifact")
    y=body_top()+8; LH=432
    cols=[MX, MX+300, MX+300+332, MX+300+332+300]
    for lx,lw,label in [(cols[0],252,"Producers"),(cols[1],284,"Interface surface"),(cols[2],252,"Core"),(cols[3],236,"Artifacts")]:
        R([lx,y,lw,LH],fill="#FBFBFC",stroke=HAIR,radius=10)
        T(lx+16,y+14,lw-24,label.upper(),size=CAP,weight=800,color=ACC_INK,spacing=1.2)
    def n3(cx,cw,items):
        for i,(t,d,a) in enumerate(items):
            node(cx+14,y+50+i*128,cw,110,t,d,accent=a)
    n3(cols[0],224,[("Author / Engineer","writes an SDK client\n(frameforge.sdk · Python)",ACC),
                    ("AI agent","emits MCP tool calls\nrun_sdk_code · render_*",ACC),
                    ("Existing artwork","Markdown · SVG · raster\n— to be ingested",MUTE)])
    n3(cols[1],256,[("SDK · frameforge.sdk","DocumentBuilder / PageBuilder\npage · layer · shapes",ACC),
                    ("MCP server · 24 tools","author · vision · QA\ndiscovery · sessions",ACC),
                    ("Ingest","svg_to_objects\npropose_from_image/svg/doc",MUTE)])
    node(cols[2]+14,y+50,224,150,"Document IR","the typed source of truth\nvalidate() → JSON-pointer\nDocument·Page·Layer·Obj",title_sz=SML,accent=INK,tint=ACC_SOFT,tstroke="#C9D6F7")
    node(cols[2]+14,y+228,224,150,"Renderer walk","z-order walk of the graph\nScenePainter (fine)  +\nDocumentRenderer (coarse)",accent=INK)
    n3(cols[3],208,[("SVG  /  PNG","display list · raster",HAVE),
                    ("PDF  /  PDF-TeX","SVG→PDF · typeset (TeX)",HAVE),
                    ("HTML  /  TikZ","semantic web · LaTeX",HAVE)])
    for i in range(3):                                   # producers → interface (row-aligned)
        yy=y+50+i*128+55; arrow(cols[0]+238,yy,cols[1]+13,yy,sw=1.4)
    for i in range(3):                                   # interface → Document IR
        arrow(cols[1]+270,y+50+i*128+55,cols[2]+13,y+125,sw=1.4,dash=([4,3] if i==2 else None))
    arrow(cols[2]+126,y+200,cols[2]+126,y+226,sw=1.6,stroke=SUB)   # IR → renderer walk
    for i in range(3):                                   # renderer walk → artifacts
        arrow(cols[2]+238,y+303,cols[3]+13,y+50+i*128+55,sw=1.4)
    # PALS verify loop (below the lanes)
    ly=y+LH+30
    arrow(cols[3]+118,y+LH,cols[3]+118,ly,sw=1.5,stroke=SIGNAL)
    arrow(cols[3]+118,ly,cols[1]+150,ly,sw=1.5,stroke=SIGNAL,dash=[5,3])
    arrow(cols[1]+150,ly,cols[1]+150,y+LH,sw=1.5,stroke=SIGNAL)
    T(cols[1]+160,ly-19,980,"PALS-verify loop:  render → compare_images / score_reconstruction → refine   (LLM & CV output is untrusted by default)",
      size=CAP,color=SIGNAL,mono=True)
    T(MX,ly+28,W-2*MX,"External runtime dependencies (availability-gated):  fontconfig font runtime (Docker frameforge image)  ·  headless Chromium (raster)  ·  CairoSVG (raster fallback)  ·  TeX engine (pdf-tex).",
      size=CAP,color=MUTE,mono=True)

def s_components():
    slide("Component map","Modules & responsibilities")
    y=body_top()
    def box(x,yy,w,h,t,items,c=ACC,tint=None):
        R([x,yy,w,h],fill=(tint or CARD),stroke=RULE,radius=9,shadow=(tint is None))
        R([x,yy,w,4],fill=c,radius=2)
        T(x+14,yy+12,w-24,t,size=SML,weight=800,color=INK)
        T(x+14,yy+34,w-24,items,size=CAP,color=MUTE,mono=True,lh=1.42)
    g=24; cw=(W-2*MX-3*g)/4
    box(MX,y,cw,118,"model  (source of truth)","src/frameforge/model.py\n1,804 LOC · Pydantic\nDocument·Page·Layer·Obj\nStyle·Paint·Layout·Defs",c=INK,tint=ACC_SOFT)
    box(MX+(cw+g),y,cw,118,"sdk  (33 modules)","author·expand·geometry\nplanar·manifold·topology\nflow·book·chart·widgets\ncanon·chevreul·humanize")
    box(MX+2*(cw+g),y,cw,118,"rendering  (hexagonal)","domain/ports · services\napplication/renderer walk\ninfrastructure/painters\n…/backends · cairo · latex")
    box(MX+3*(cw+g),y,cw,118,"mcp  (24 tools)","author→render · ingest\nvision reconstruction\nvisual QA · discovery\nsessions/resources")
    y2=y+146
    box(MX,y2,cw,110,"vision  (raster→vector)","measure·detect·vectorize\nmark·overlay·workspace\nconstruct·map·score\ndomain: coordinates·fitting",c=SIGNAL)
    box(MX+(cw+g),y2,cw,110,"validate + gates","sdk/validate.py\nPydantic + static rules\nmake check · golden b1/\ncapability-manifest.json",c=HAVE)
    box(MX+2*(cw+g),y2,cw,110,"live  +  viewer","live/server.py (sessions)\nviewer/*.jsx (React)\nzoom·pan·page-nav\n(interactivity lives here)",c=MUTE)
    box(MX+3*(cw+g),y2,cw,110,"coach  +  tooling","coach/ construction\ntooling/ render_* · codemod\ngen_* generators\nbump_version · fixtures",c=MUTE)
    # dependency spine
    y3=y2+134
    R([MX,y3,W-2*MX,64],fill=BAND,radius=10)
    T(MX+18,y3+11,600,"THE GENERATION SPINE",size=CAP,weight=800,color=ACC2,spacing=1.4)
    T(MX+18,y3+32,W-2*MX-30,"model  →  build_schema.py → schema.json   ·   grammar EBNF   ·   gen_capability_manifest.py → manifest   ·   gen_docs → site.   Edit the source, rerun the gate — generated artifacts are never hand-edited.",
      size=SML,color=PAPER_ON_BAND,mono=True)

def s_objectmodel():
    slide("Document object model","Document → Page → Layer → Object")
    y=body_top()+6; PH=452; tw=290
    # --- containment tree (left) with clean elbow connectors drawn UNDER the nodes ---
    tnodes=[(MX,     y,     "Document","dsl · version · profile · defs · pages",INK,ACC_SOFT),
            (MX+30,  y+86,  "defs","tokens · masters · counters · assets · data",MUTE,CARD),
            (MX+30,  y+162, "Page  (mode: page | flow)","master · canvas · rendering · links",ACC,CARD),
            (MX+62,  y+248, "Layer","z · opacity · objects[]",ACC,CARD),
            (MX+94,  y+334, "Visual object","ObjBase + discriminated type",SIGNAL,CARD)]
    def elbow(sx,y0,cx,cmid):
        LN((sx,y0),(sx,cmid),stroke=FAINT,sw=1.4); LN((sx,cmid),(cx,cmid),stroke=FAINT,sw=1.4)
    elbow(MX+18,y+50,MX+30,y+86+25)      # Document → defs
    elbow(MX+18,y+50,MX+30,y+162+25)     # Document → Page
    elbow(MX+48,y+212,MX+62,y+248+25)    # Page → Layer
    elbow(MX+80,y+298,MX+94,y+334+25)    # Layer → Visual object
    for x,yy,t,sub,c,tint in tnodes:
        R([x,yy,tw,50],fill=tint,stroke=RULE,radius=8,shadow=(tint==CARD)); R([x,yy,4,50],fill=c,radius=2)
        T(x+14,yy+8,tw-22,t,size=SML,weight=800,color=INK); T(x+14,yy+27,tw-22,sub,size=CAP,color=MUTE,mono=True)
    T(MX,y+410,tw+120,"Paint order = layer z (then list order),\nthen object z within the layer.",size=CAP,color=SUB,lh=1.4)
    # --- ObjBase fields panel (middle) ---
    ox=MX+402; ow=384
    R([ox,y,ow,PH],fill=CARD,stroke=RULE,radius=10,shadow=True); R([ox,y,5,PH],fill=INK,radius=2)
    T(ox+18,y+15,ow-30,"ObjBase — shared object fields",size=SML,weight=800,color=INK)
    T(ox+18,y+38,ow-30,"the extension surface every object inherits",size=CAP,color=MUTE,italic=True)
    fields=[("box","[x,y,w,h] · parent-local · +y down"),("rotation","deg | {angle,center} · onto subtree"),
            ("z","stacking within the layer"),("ports","named attach points → anchors"),
            ("bind","data-binding, resolved at expand"),("style","CSS bag · tokens · class merge"),
            ("stroke_style","P3 geometry bundle (paint apart)"),("opacity ×3","object · fill · stroke"),
            ("shadow·glow·effects","+ appearance stack (2.4.0)"),("sizing·grid_span","fixed|hug|fill · grid cell span"),
            ("humanize","seeded imperfection 'hand'")]
    for i,(k,v) in enumerate(fields):
        yy=y+68+i*34
        T(ox+18,yy,150,k,size=CAP,weight=800,color=ACC_INK,mono=True); T(ox+186,yy,ow-198,v,size=CAP,color=SUB)
    # --- visual object union (right) ---
    ux=MX+806; uw=W-MX-ux
    R([ux,y,uw,PH],fill=CARD,stroke=RULE,radius=10,shadow=True); R([ux,y,5,PH],fill=SIGNAL,radius=2)
    T(ux+18,y+15,uw-30,"Visual object union  (discriminated by  type)",size=SML,weight=800,color=INK)
    prim=[("rect","ellipse","circle"),("line","polyline","polygon"),("path","text","image"),
          ("group","table","connector"),("dimension","use","component")]
    cellw=(uw-36-2*10)/3
    for r,row in enumerate(prim):
        for c,name in enumerate(row):
            xx=ux+18+c*(cellw+10); yy=y+50+r*44
            R([xx,yy,cellw,34],fill=ACC_SOFT,stroke="#CBD8F8",radius=7)
            T(xx,yy+9,cellw,name,size=SML,weight=700,color=ACC_INK,mono=True,align="center")
    T(ux+18,y+50+5*44+6,uw-34,"+ flow variants — BlockFlow · FigureFlow · ListFlow · flow-table / flow-image — for reflowable pagination.\n"
      "+ scene3d / mark3d (3D via Mat4 / Camera).   + AnchorObject.",size=CAP,color=MUTE,lh=1.5)
    T(ux+18,y+PH-58,uw-34,"Containers (group) compose rotation, opacity and transform onto their whole subtree — nested transforms are inherent to the model.",
      size=CAP,color=SUB,italic=True,lh=1.4)

def s_pipeline():
    slide("Rendering pipeline & data flow","Intent → document graph → artifact")
    y=body_top()+4
    stages=[("Intent","author / agent decides",ACC,"prose"),
            ("SDK / MCP","DocumentBuilder · run_sdk_code",ACC,"call"),
            ("Document IR","Pydantic validate\nJSON-pointer errors",INK,"graph"),
            ("Renderer walk","z-order traversal\nrender_context",SUB,"walk"),
            ("Painter / backend","two ports",SIGNAL,"seam"),
            ("Artifact","SVG·PNG·PDF·HTML·TikZ",HAVE,"out")]
    n=len(stages); gap=18; sw=(W-2*MX-(n-1)*gap)/n
    for i,(t,d,c,_) in enumerate(stages):
        x=MX+i*(sw+gap)
        R([x,y,sw,96],fill=CARD,stroke=RULE,radius=9,shadow=True); R([x,y,sw,4],fill=c,radius=2)
        T(x+13,y+14,sw-20,t,size=BODY,weight=800,color=INK)
        T(x+13,y+40,sw-20,d,size=CAP,color=MUTE,mono=True,lh=1.35)
        if i<n-1: arrow(x+sw+2,y+48,x+sw+gap-2,y+48,sw=1.8)
    # the two seams, expanded
    y2=y+150
    T(MX,y2,900,"Two rendering seams (hexagonal ports)",size=SML,weight=800,color=ACC_INK,spacing=0.5)
    R([MX,y2+28,715,206],fill=CARD,stroke=RULE,radius=10,shadow=True); R([MX,y2+28,5,206],fill=ACC,radius=2)
    T(MX+18,y2+40,700,"ScenePainter   —   fine, per-primitive",size=BODY,weight=800,color=INK)
    T(MX+18,y2+66,690,"An immediate-mode display list. The builder walks the document in z-order and "
      "calls rect / ellipse / path / text_block / group; each returns a backend fragment. Manages "
      "per-page defs (gradients, clips, filters, markers).",size=SML,color=SUB,lh=1.46)
    T(MX+18,y2+150,680,"Implemented by:  SvgPainter   ·   TikzPainter",size=SML,weight=700,color=ACC_INK,mono=True)
    T(MX+18,y2+178,680,"neutral value objects (Stroke, Markers) + a residual `extra` escape hatch",size=CAP,color=MUTE,italic=True)
    x3=MX+745
    R([x3,y2+28,W-MX-x3,206],fill=CARD,stroke=RULE,radius=10,shadow=True); R([x3,y2+28,5,206],fill=SIGNAL,radius=2)
    T(x3+18,y2+40,600,"DocumentRenderer   —   coarse, whole-document",size=BODY,weight=800,color=INK)
    T(x3+18,y2+66,W-MX-x3-40,"One FrameForge document in → one RenderedArtifact out. The right seam for backends "
      "whose output is a document-level transform rather than a display list of geometry.",size=SML,color=SUB,lh=1.46)
    T(x3+18,y2+134,600,"Implemented by:  HtmlDocumentRenderer   ·   PdfTexDocumentRenderer",size=SML,weight=700,color=ACC_INK,mono=True)
    T(x3+18,y2+162,W-MX-x3-40,"HTML lowers layout(free/column/row/wrap/grid)→CSS;  pdf-tex hands pagination + math to TeX.  "
      "Rasterizers (Chromium, Cairo) sit downstream of SVG.",size=CAP,color=MUTE,lh=1.4)

def s_coord():
    slide("Spatial model","Coordinate · layer · transform · layout")
    y=body_top()
    cw=(W-2*MX-3*24)/4
    def panel(i,t,rows,c=ACC):
        x=MX+i*(cw+24)
        R([x,y,cw,300],fill=CARD,stroke=RULE,radius=10,shadow=True); R([x,y,cw,4],fill=c,radius=2)
        T(x+15,y+13,cw-26,t,size=SML,weight=800,color=INK)
        for j,(k,v) in enumerate(rows):
            yy=y+42+j*54
            T(x+15,yy,cw-28,k,size=CAP,weight=800,color=ACC_INK,mono=True)
            T(x+15,yy+16,cw-28,v,size=CAP,color=SUB,lh=1.34)
    panel(0,"Coordinate system",[("box [x,y,w,h]","parent-local origin, +y down; page space at the root"),
        ("coordinate_mode","absolute | flow (per page/section)"),
        ("units","px/pt/mm/…; w/h may be % or fr inside a layout")],c=INK)
    panel(1,"Layer & z-order",[("layer.z","layers paint low→high, then list order"),
        ("object.z","stacking within a layer (higher paints later)"),
        ("opacity","per-layer + per-object; groups composite as one")])
    panel(2,"Transform model",[("Style.transform","CSS transform-function list (rotate/scale/…)"),
        ("Mat3 (SDK)","2×3 affine: translate·scale·rotate·inverse·@"),
        ("Mat4 · Camera","3D projection for scene3d / mark3d")],c=SUB)
    panel(3,"Layout & sizing",[("Layout.kind","row · column · grid · wrap · free (default)"),
        ("gap · justify","row/column gap; start…space-evenly"),
        ("Sizing","fixed | hug | fill  (grow/min/max, fr units)")],c=HAVE)
    T(MX,y+320,W-2*MX,"“free” is the only kind that reads authored child x/y; row/column/grid/wrap compute positions. "
      "Rotation on a container composes onto its whole subtree — nested transforms are inherent to the group model.",
      size=SML,color=SUB)

def s_style():
    slide("Styling & paint model","CSS-aligned, token-composed, paint-rich")
    y=body_top()
    # left: Style
    R([MX,y,540,326],fill=CARD,stroke=RULE,radius=10,shadow=True); R([MX,y,5,326],fill=ACC,radius=2)
    T(MX+18,y+13,500,"Style  —  CSS Text L3 + Fonts L3/L4  (extra = forbid)",size=SML,weight=800,color=INK)
    rows=[("composition","class → tokens.styles merge, then own props"),
          ("escape hatch","css: bounded raw-CSS string, passed through"),
          ("shorthand sugar","font/size/weight/italic/align/radius/wrap"),
          ("typography","kerning · variant-caps · features · variation · tracking"),
          ("text fit","wrap · shrink_to_fit · line_clamp · ellipsis (TextContract)"),
          ("transform / clip","transform-fn list · clip box + basic-shape clip_path"),
          ("stroke (P3)","stroke = paint only; geometry → stroke_style bundle")]
    for i,(k,v) in enumerate(rows):
        yy=y+46+i*39; T(MX+18,yy,180,k,size=CAP,weight=800,color=ACC_INK); T(MX+150,yy,380,v,size=CAP,color=SUB,mono=True)
    # right: Paint + effects
    px=MX+568; pw=W-MX-px
    R([px,y,pw,156],fill=CARD,stroke=RULE,radius=10,shadow=True); R([px,y,5,156],fill=SIGNAL,radius=2)
    T(px+18,y+13,pw-30,"Paint  =  color | gradient | pattern | image",size=SML,weight=800,color=INK)
    chips=[("solid / token",ACC_SOFT,ACC_INK),("linear / radial gradient",ACC_SOFT,ACC_INK),
           ("pattern: hatch·cross·dots·grid",SIGNAL_SOFT,SIGNAL),("image (UrlImage)",HAIR,MUTE)]
    for i,(t,bg,fg) in enumerate(chips):
        xx=px+18+(i%2)*((pw-40)/2); yy=y+44+(i//2)*38
        R([xx,yy,(pw-52)/2,28],fill=bg,radius=7); T(xx,yy+7,(pw-52)/2,t,size=CAP,weight=700,color=fg,align="center",mono=True)
    T(px+18,y+124,pw-30,"fill · stroke · both accept any Paint; fill_rule evenodd for holes.",size=CAP,color=MUTE,italic=True)
    R([px,y+172,pw,154],fill=CARD,stroke=RULE,radius=10,shadow=True); R([px,y+172,5,154],fill=ACC,radius=2)
    T(px+18,y+185,pw-30,"Effects & appearance (2.4.0)",size=SML,weight=800,color=INK)
    for i,(k,v) in enumerate([("shadow · glow","preset · bool · object"),
                              ("effects[]","ordered stack; a kind may repeat"),
                              ("appearance[]","multi-pass paint, bottom→top"),
                              ("outer_ring · text_shadow","decorative extras")]):
        yy=y+214+i*27; T(px+18,yy,190,k,size=CAP,weight=800,color=ACC_INK,mono=True); T(px+210,yy,pw-220,v,size=CAP,color=SUB)
    T(MX,y+338,W-2*MX,"Caveat: the CairoSVG raster path ignores SVG filter primitives — effects that rely on them read correctly only in the browser/HTML path.",
      size=CAP,color=SIGNAL,mono=True)

def s_capmap():
    slide("Capability map","290 manifest-tracked capabilities, by subsystem")
    y=body_top()
    groups=[("Authoring & shapes","rect·ellipse·circle·line·poly·path·arc·sector·ring·star·text·image·table·group·connector·dimension",ACC),
            ("Geometry kernel","planar booleans (union/intersect/difference·fill_regions) · manifold · topology · lattices · offset · draw",ACC),
            ("Layout & pagination","row/column/grid/wrap/free · Sizing fixed|hug|fill · flow sections · masters · counters · running furniture",ACC),
            ("Text & typography","real-metric fit · wrap · justify · shrink_to_fit · line_clamp · math (MathJax) · kerned spans · outline emitter",ACC),
            ("Colour & craft","Chevreul harmonies · closed_palette · contrast_ratio · Johnston margins · modular_scale · recolor · grey_document",SIGNAL),
            ("Figures · charts · widgets","Chart/Panel · card·button·badge·field·checkbox·avatar·breadcrumb · book composition · from_markdown",ACC),
            ("Vision / reconstruction","measure·detect·vectorize·mark·overlay·workspace·construct·map·score — raster → precise vectors",SIGNAL),
            ("Humanize & variance","seeded imperfection 'hand' (roughen·drift·weight·grain) — absence = mechanically exact identity",ACC)]
    g=22; cw=(W-2*MX-g)/2
    for i,(t,d,c) in enumerate(groups):
        x=MX+(i%2)*(cw+g); yy=y+(i//2)*88
        R([x,yy,cw,76],fill=CARD,stroke=RULE,radius=9,shadow=True); R([x,yy,4,76],fill=c,radius=2)
        T(x+15,yy+11,cw-24,t,size=BODY,weight=800,color=INK)
        T(x+15,yy+37,cw-28,d,size=CAP,color=MUTE,mono=True,lh=1.36)
    T(MX,y+366,W-2*MX,"Source: docs/capability-manifest.json (generated by tooling/gen_capability_manifest.py, gated by tests/test_capability_manifest.py). "
      "Grouping is by subsystem for readability; the manifest tracks 290 individual capability entries with core/sdk/mcp flags.",
      size=CAP,color=MUTE,italic=True)

def s_mcp():
    slide("MCP & SDK surface","24 tools · one builder API")
    y=body_top()
    groups=[("Author → render",ACC,["run_sdk_code","run_sdk_client","render_frameforge_yaml","write/read/list_sdk_clients"]),
            ("Image → draft",MUTE,["propose_from_image","propose_from_svg","propose_from_document"]),
            ("Visual QA",HAVE,["compare_images","score_reconstruction"]),
            ("Coordinate reconstruction",SIGNAL,["measure_image","detect_regions","vectorize_image","mark_points","overlay_images","workspace","construct_vectors","map_coordinates"]),
            ("Discovery",ACC,["describe_capabilities","get_guide","list_fonts"]),
            ("Sessions & resources",MUTE,["list_sessions","cleanup_sessions","get_session_resource"])]
    g=20; cw=(W-2*MX-2*g)/3
    for i,(t,c,tools) in enumerate(groups):
        x=MX+(i%3)*(cw+g); yy=y+(i//3)*172
        R([x,yy,cw,156],fill=CARD,stroke=RULE,radius=9,shadow=True); R([x,yy,4,156],fill=c,radius=2)
        T(x+15,yy+11,cw-24,t,size=SML,weight=800,color=INK)
        T(x+15,yy+30,cw-24,f"{len(tools)} tools",size=CAP,color=FAINT,weight=700)
        for j,tool in enumerate(tools):
            yy2=yy+48+j*(13 if len(tools)>5 else 17)
            DOT(x+20,yy2+5,2.2,c); T(x+28,yy2,cw-36,tool,size=CAP,color=SUB,mono=True)
    T(MX,y+360,W-2*MX,"SDK builder API:  page · section · layer · add · (rect…star) · text · image · table · group · connector · dimension · use · component  "
      "+ colour-theory & widget helpers.  MCP agents also reach every session-connected tool via ToolSearch.",
      size=CAP,color=MUTE,mono=True)

def s_export():
    slide("Export & import","Multi-target output, ingest & round-trip")
    y=body_top()
    # targets table
    T(MX,y,700,"Render targets  (frameforge-render --to)",size=SML,weight=800,color=ACC_INK,spacing=0.5)
    rows=[("svg","ScenePainter / SvgPainter","display list","always"),
          ("png","SVG → Chromium or Cairo raster","raster","Chromium/Cairo"),
          ("pdf","SVG pages → combined PDF","vector","CairoSVG"),
          ("pdf-tex","DocumentRenderer → LaTeX/TikZ","typeset","TeX engine"),
          ("html","DocumentRenderer → semantic HTML/CSS","web (flow limits)","always"),
          ("tikz","TikzPainter","LaTeX source","LaTeX")]
    ty=y+30; rw=770
    R([MX,ty,rw,28],fill=BAND,radius=6)
    for c,(lab,wx) in enumerate([("target",60),("path",250),("kind",150),("needs",120)]):
        T(MX+14+[0,80,360,540][c],ty+7,wx+60,lab.upper(),size=CAP,weight=800,color=ACC2,spacing=1)
    for i,(t,p,k,need) in enumerate(rows):
        yy=ty+34+i*34
        if i%2: R([MX,yy-4,rw,32],fill="#FBFBFC")
        T(MX+14,yy,80,t,size=SML,weight=800,color=ACC_INK,mono=True)
        T(MX+94,yy,290,p,size=CAP,color=SUB,mono=True)
        T(MX+374,yy,160,k,size=CAP,color=SUB)
        c=HAVE if need=="always" else PARTIAL
        DOT(MX+554,yy+7,3,c); T(MX+566,yy,150,need,size=CAP,color=SUB)
    # import
    ix=MX+820; iw=W-MX-ix
    T(ix,y,iw,"Import / ingest",size=SML,weight=800,color=ACC_INK,spacing=0.5)
    for i,(t,d,c) in enumerate([("svg_to_objects","existing SVG → FrameForge objects (round-trips through render)",ACC),
                                ("propose_from_image","raster → UNVERIFIED FrameForge draft",SIGNAL),
                                ("propose_from_svg / _document","vector / doc → draft",SIGNAL),
                                ("from_markdown","Markdown → flow document",ACC),
                                ("serialize()","Document ↔ YAML / JSON (round-trip)",HAVE)]):
        yy=y+32+i*58
        R([ix,yy,iw,48],fill=CARD,stroke=RULE,radius=8,shadow=True); R([ix,yy,4,48],fill=c,radius=2)
        T(ix+14,yy+8,iw-22,t,size=SML,weight=800,color=INK,mono=True); T(ix+14,yy+27,iw-22,d,size=CAP,color=MUTE)
    T(MX,y+336,W-2*MX,"All propose_* drafts are explicitly UNVERIFIED (PALS's Law) — round-tripped through render and meant to be diffed against the source before trust.",
      size=CAP,color=SIGNAL,italic=True)

def s_constraints():
    slide("Known constraints & limitations","Grounded — and where uncertain, labelled")
    y=body_top()
    items=[("Static IR — no interaction in-model","CONFIRMED","Grep of model + rendering + sdk finds no event / pointer / animation / hit-test primitive. Navigation is limited to PageLink & LinkInline hyperlinks.",GAP),
           ("Interactivity lives outside the document","CONFIRMED","Zoom/pan/page-nav are in the React viewer + live/server.py, not encoded in the IR. The document is a rest-state snapshot.",PARTIAL),
           ("HTML backend: flow-mode limits","CONFIRMED","The backend's own blurb: “HTML/CSS (semantic; flow-mode limits)”. Absolute pages map cleanly; complex flow does not fully.",PARTIAL),
           ("Cairo raster ignores filter primitives","CONFIRMED","Filter-based effects render only via the browser/HTML path; the Cairo fallback drops them.",PARTIAL),
           ("Font fidelity needs the font runtime","CONFIRMED","Display faces collapse in a fontless raster; canonical runtime is the Docker frameforge image (~4,986 families).",PARTIAL),
           ("Availability-gated backends","CONFIRMED","pdf-tex needs a TeX engine; png needs Chromium or Cairo — each DocumentRenderer.available() returns a reason when it cannot run.",PARTIAL),
           ("planar boolean robustness","UNCERTAIN","Boolean atoms are bounded (≈≤8 regions per note) and some parity is decision-gated — verify against tests/ before relying on complex cases.",SIGNAL)]
    for i,(t,tag,d,c) in enumerate(items):
        yy=y+i*76
        R([MX,yy,W-2*MX,66],fill=CARD,stroke=RULE,radius=8,shadow=True); R([MX,yy,4,66],fill=c,radius=2)
        T(MX+16,yy+11,760,t,size=BODY,weight=800,color=INK)
        tagc=HAVE if tag=="CONFIRMED" else SIGNAL
        R([MX+16,yy+40,96,18],fill=(SIGNAL_SOFT if tag=="UNCERTAIN" else "#E7F5EC"),radius=5)
        T(MX+16,yy+42,96,tag,size=9,weight=800,color=tagc,align="center",spacing=1)
        T(MX+130,yy+40,W-2*MX-150,d,size=CAP,color=SUB,lh=1.32)

def s_part2():
    slide("PART II","Evolution toward SVG.js / Snap.svg parity",dark=True)
    T(MX,150,300,"PART II",size=CAP,weight=800,color=ACC2,spacing=3)
    T(MX,180,1300,"Not an incomplete SVG.js —",size=H1,weight=800,color="#FFFFFF",lh=1.05)
    T(MX,180+H1*1.02,1300,"a different architecture.",size=H1,weight=300,color=ACC2,lh=1.05)
    # two-column framing
    y=430
    R([MX,y,700,300],fill=BAND2,stroke="#2A2F3B",radius=12); R([MX,y,5,300],fill=ACC,radius=2)
    T(MX+22,y+18,660,"FrameForge  —  declarative render IR",size=LEAD,weight=800,color="#FFFFFF")
    for i,t in enumerate(["Headless; no live DOM, no runtime scene graph","One typed IR → many targets (SVG·PDF·HTML·TikZ)",
                          "Optimised for reproducibility & verification","Golden hashes, compare_images, static gates",
                          "Interaction is a consumer concern (viewer)"]):
        DOT(MX+26,y+58+i*40,2.8,ACC2); T(MX+40,y+51+i*40,640,t,size=BODY,color=PAPER_ON_BAND,lh=1.3)
    x2=MX+740
    R([x2,y,W-MX-x2,300],fill=BAND2,stroke="#2A2F3B",radius=12); R([x2,y,5,300],fill=SIGNAL,radius=2)
    T(x2+22,y+18,660,"SVG.js / Snap.svg  —  imperative DOM toolkits",size=LEAD,weight=800,color="#FFFFFF")
    for i,t in enumerate(["Bind to and mutate a live SVG DOM","Single target: the browser's SVG","Query/select, animate, drag, hit-test",
                          "Events & plugins on real element nodes","No verification model — the DOM is the truth"]):
        DOT(x2+26,y+58+i*40,2.8,SIGNAL); T(x2+40,y+51+i*40,640,t,size=BODY,color=PAPER_ON_BAND,lh=1.3)
    T(MX,y+322,W-2*MX,"The parity question is therefore not “add missing SVG features” — most vector primitives already exist declaratively. "
      "It is: can a runtime/interaction layer be added WITHOUT dissolving the verifiable static core that the gates depend on?",
      size=BODY,color=MUTE_ON_BAND,italic=True,lh=1.4)

def s_compare():
    slide("Capability comparison","FrameForge vs SVG.js vs Snap.svg")
    y=body_top()-6
    dims=[("Shape creation API","have","have","have","full primitive set both sides"),
          ("Groups & nested transforms","have","have","have","group composes onto subtree"),
          ("Matrix transforms","have","have","have","Mat3/Mat4 (SDK) vs live matrix"),
          ("Gradients · clip · patterns","have","have","have","declarative defs vs DOM defs"),
          ("Symbols / reuse","have","have","have","use / component vs <use>/<symbol>"),
          ("Serialization / round-trip","have","part","part","IR is the native format; ingest+serialize"),
          ("Path data & geometry ops","have","part","have","planar booleans exceed both"),
          ("Filters / effects","part","have","have","effects stack; Cairo drops SVG filters"),
          ("DOM-like query / selection","gap","have","have","no id-indexed scene query yet"),
          ("Animation / timeline","gap","have","have","no time axis in the IR"),
          ("Event handling","gap","have","have","no event model anywhere"),
          ("Drag / interactive editing","gap","have","have","viewer is view-only"),
          ("Hit testing / point-in-shape","gap","have","have","no runtime scene graph"),
          ("Plugin / extension system","part","have","have","SDK modules, no runtime plugin bus"),
          ("Raster→vector reconstruction","have","na","na","FrameForge-only (vision MCP)"),
          ("Multi-target / print fidelity","have","na","na","FrameForge-only (PDF/TeX/HTML)")]
    cols=[("Dimension",470),("FrameForge",150),("SVG.js",130),("Snap.svg",130),("Note",0)]
    rw=W-2*MX
    R([MX,y,rw,26],fill=BAND,radius=6)
    cx=[MX+16,MX+486,MX+636,MX+766,MX+900]
    for i,(c,_) in enumerate(cols):
        T(cx[i],y+6,200,c.upper(),size=9.5,weight=800,color=ACC2,spacing=0.8)
    def badge(x,yy,state):
        col={"have":HAVE,"part":PARTIAL,"gap":GAP,"na":NA}[state]
        lab={"have":"●  full","part":"◐  partial","gap":"○  gap","na":"—  n/a"}[state]
        DOT(x+5,yy+7,4,col); T(x+14,yy,110,{"have":"full","part":"partial","gap":"gap","na":"n/a"}[state],size=9.5,weight=700,color=col)
    rh=(H-40-y-30)/len(dims)
    for i,(d,a,bb,cc,note) in enumerate(dims):
        yy=y+30+i*rh
        if i%2: R([MX,yy-2,rw,rh],fill="#FBFBFC")
        T(cx[0],yy+2,460,d,size=CAP,weight=700,color=INK)
        for j,st in enumerate((a,bb,cc)): badge(cx[1+j],yy+2,st)
        T(cx[4],yy+2,rw-(cx[4]-MX)-16,note,size=CAP,color=MUTE,italic=True)
    # legend
    T(MX,H-58,900,"● full     ◐ partial / present-but-narrow     ○ gap     — not applicable (category difference)",size=CAP,color=MUTE,mono=True)

def gapcard(x,y,w,h,title,rows,*,prio,cx="M"):
    R([x,y,w,h],fill=CARD,stroke=RULE,radius=10,shadow=True); R([x,y,5,h],fill=SIGNAL,radius=2)
    T(x+18,y+13,w-120,title,size=BODY,weight=800,color=INK)
    pc={"P0":GAP,"P1":PARTIAL,"P2":ACC}[prio]
    R([x+w-92,y+13,74,20],fill="#F2F4F8",stroke=RULE,radius=6); T(x+w-92,y+16,74,prio+" · "+cx,size=9.5,weight=800,color=pc,align="center")
    for i,(k,v) in enumerate(rows):
        yy=y+44+i*25
        T(x+18,yy,120,k,size=CAP,weight=800,color=ACC_INK); T(x+128,yy,w-146,v,size=CAP,color=SUB,lh=1.3)

def s_gap1():
    slide("Gap deep-dive I","Scene query · animation")
    y=body_top()
    gapcard(MX,y,(W-2*MX-24)/2,330,"DOM-like query & selection",
        [("AS-IS","objects carry stable id + ports, but there is no selector/query engine over the graph"),
         ("Target","doc.find('#id') / .select('rect[fill=accent]') returning live handles"),
         ("Why","every editing, animation and event feature needs addressable nodes first"),
         ("Path","build an id/type index during expand; a small CSS-ish matcher over the Pydantic tree"),
         ("Deps","low — reuses existing ids; pure-Python, no new runtime"),
         ("Example","sel = doc.query('layer#ui > rect.card'); sel.set(fill='accent')")],prio="P0",cx="S")
    gapcard(MX+(W-2*MX-24)/2+24,y,(W-2*MX-24)/2,330,"Animation / timeline",
        [("AS-IS","no time axis; motion = render N documents → ffmpeg (animate_svg.py)"),
         ("Target","declarative keyframes/transition block, lowered per backend"),
         ("Why","the single biggest expressive gap vs both toolkits"),
         ("Path","add optional `animate` to ObjBase → SMIL (SVG) / CSS @keyframes (HTML) / frames (raster)"),
         ("Deps","HIGH — must not break golden gates; needs a 'time=0' canonical snapshot for hashing"),
         ("Example","rect.animate(dur=600).to(box=[..]).ease('out')  → SMIL/CSS")],prio="P2",cx="L")
    T(MX,y+348,W-2*MX,"Order matters: selection (P0) is the substrate. Animation (P2) is gated on preserving a deterministic t=0 render so the golden-hash and compare_images gates still hold.",
      size=SML,color=SUB,italic=True)

def s_gap2():
    slide("Gap deep-dive II","Events · hit-testing · interactive editing · plugins")
    y=body_top()
    w=(W-2*MX-2*20)/3
    gapcard(MX,y,w,332,"Events & hit-testing",
        [("AS-IS","none in IR; viewer has raw pointer but no shape-level dispatch"),
         ("Target",".on('click') / point-in-shape against the scene graph"),
         ("Why","precondition for any interaction; also powers collision tooling"),
         ("Path","runtime scene graph in the viewer: bbox + path point-in-poly + an event bus"),
         ("Deps","MED — lives in the viewer, not the IR (keeps core static)"),
         ("Example","node.on('click', e => select(e.target))")],prio="P1",cx="M")
    gapcard(MX+w+20,y,w,332,"Interactive editing",
        [("AS-IS","view-only (zoom/pan/page-nav); edits happen in code"),
         ("Target","drag / resize / handle-edit that writes back to the IR"),
         ("Why","closes the round-trip: canvas edit → serialize → same doc"),
         ("Path","editor overlay on the scene graph; mutations re-emit Pydantic objects"),
         ("Deps","MED-HIGH — depends on query (P0) + events (P1)"),
         ("Example","drag(handle) → obj.box mutate → serialize()")],prio="P1",cx="L")
    gapcard(MX+2*(w+20),y,w,332,"Plugin / extension bus",
        [("AS-IS","extend by adding SDK modules (compile-time), no runtime plugins"),
         ("Target","register custom element / tool at runtime, like SVG.js plugins"),
         ("Why","third-party shapes, exporters, behaviours without forking"),
         ("Path","entry-point registry for object types + painters + MCP tools"),
         ("Deps","LOW-MED — the port Protocols already define the seams"),
         ("Example","register_element('gauge', GaugePainter)")],prio="P2",cx="M")
    T(MX,y+350,W-2*MX,"Design rule for all of Part II: interaction is added as a layer that CONSUMES the IR (in the viewer/runtime), so the document stays a verifiable, backend-neutral snapshot.",
      size=SML,color=SIGNAL,italic=True)

def s_roadmap():
    slide("Prioritised roadmap","Sequenced so the verifiable core survives")
    y=body_top()
    phases=[("P0","Substrate — low risk, high leverage",ACC,
             ["Scene query / selection over the IR (id + type index)","Serialization round-trip hardening (edit → serialize → identical)","Runtime scene-graph model in the viewer (bbox + geometry)"],"S–M"),
            ("P1","Interaction layer — in the viewer, not the IR",PARTIAL,
             ["Event bus + shape-level hit-testing","Drag / resize / handle editing → writes back to IR","Plugin registry over the existing port Protocols"],"M"),
            ("P2","Expressive parity — gated on verification",GAP,
             ["Declarative animation/timeline block on ObjBase","Backend lowering: SMIL (SVG) · CSS @keyframes (HTML)","Filter-effect parity on the raster path (or document the split)"],"L–XL")]
    colw=(W-2*MX-2*24)/3
    for i,(p,t,c,items,cx) in enumerate(phases):
        x=MX+i*(colw+24)
        R([x,y,colw,364],fill=CARD,stroke=RULE,radius=11,shadow=True); R([x,y,colw,6],fill=c,radius=3)
        R([x+16,y+20,52,52],fill=c,radius=10); T(x+16,y+32,52,p,size=H3,weight=800,color="#FFFFFF",align="center")
        T(x+80,y+22,colw-92,t,size=SML,weight=800,color=INK,lh=1.2)
        T(x+80,y+56,colw-92,"complexity  "+cx,size=CAP,color=FAINT,weight=700,mono=True)
        LN((x+16,y+92),(x+colw-16,y+92),stroke=HAIR,sw=1)
        for j,it in enumerate(items):
            yy=y+108+j*76
            DOT(x+24,yy+7,3,c); T(x+38,yy,colw-52,it,size=SML,color=SUB,weight=600,lh=1.3)
        if i<2: arrow(x+colw+2,y+182,x+colw+22,y+182,sw=2)
    T(MX,y+380,W-2*MX,"The invariant that orders everything:  a deterministic t=0 / neutral-state render must remain hashable, or the golden-oracle and compare_images gates cannot certify a build.",
      size=SML,color=SUB,italic=True)

def s_risks():
    slide("Risks","Architecture risks & recommended next steps")
    y=body_top()
    T(MX,y,700,"Risks",size=SML,weight=800,color=SIGNAL,spacing=0.6)
    risks=[("Verifiability ↔ interactivity tension","An animation/event runtime can erode the deterministic snapshot the gates depend on. Keep interaction in a consuming layer."),
           ("Multi-backend divergence","SVG · HTML · TikZ · PDF already differ (filters, flow-mode). Each new feature multiplies the parity matrix to keep honest."),
           ("Font-runtime coupling","Fidelity depends on the Docker font runtime; features that assume browser paint widen the gap from the raster path."),
           ("Scope creep toward a DOM toolkit","Chasing SVG.js feature-for-feature would trade FrameForge's differentiators (verification, multi-target, vision) for parity that browsers already own.")]
    for i,(t,d) in enumerate(risks):
        yy=y+28+i*74
        R([MX,yy,760,64],fill=CARD,stroke=RULE,radius=8,shadow=True); R([MX,yy,4,64],fill=SIGNAL,radius=2)
        T(MX+16,yy+10,730,t,size=SML,weight=800,color=INK); T(MX+16,yy+32,730,d,size=CAP,color=SUB,lh=1.32)
    nx=MX+800; nw=W-MX-nx
    T(nx,y,nw,"Recommended next steps",size=SML,weight=800,color=ACC_INK,spacing=0.6)
    steps=[("1","Ship P0 scene-query over the IR — small, pure-Python, unlocks everything downstream."),
           ("2","Prototype the viewer runtime scene-graph (hit-test + event bus) against one real deck."),
           ("3","Write an ADR for the animation model that pins the t=0 hashing contract before any code."),
           ("4","Publish the FrameForge-vs-toolkit comparison as living docs so parity claims stay honest."),
           ("5","Keep interaction OUT of the IR — every step above consumes the document, never mutates its static contract.")]
    for i,(n,d) in enumerate(steps):
        yy=y+28+i*66
        R([nx,yy,nw,56],fill=ACC_SOFT,stroke="#CBD8F8",radius=8)
        R([nx+12,yy+12,30,30],fill=ACC,radius=8); T(nx+12,yy+18,30,n,size=SML,weight=800,color="#FFFFFF",align="center")
        T(nx+54,yy+11,nw-66,d,size=CAP,color=SUB,lh=1.34,weight=600)

def s_appendix():
    slide("Appendix","Evidence inventory — grounded in the live tree")
    y=body_top()
    cols=[("Inspected (file : what it grounds)",[
              "src/frameforge/model.py — model, 1,804 LOC, HEAD 2.4.1",
              "…Document/Page/Layer/ObjBase/Style/Paint/Layout/Defs",
              "src/frameforge/sdk/*.py — 33 modules (author…planar)",
              "…author.py — page/layer/shapes/use/component",
              "rendering/domain/ports.py — ScenePainter, DocumentRenderer",
              "rendering/infrastructure/painters/{svg,tikz}.py",
              "…/backends/{html,pdf_tex}.py — target/kind/available",
              "src/frameforge/mcp/ — 24 tool defs",
              "docs/capability-manifest.json — 290 caps, 6 renderers",
              "docs/grammar/*.ebnf · docs/schema/*.schema.json",
              "pyproject.toml — scripts, virtual project"]),
          ("Confirmed",[
              "24 MCP tools; 6 render entry points",
              "Two rendering ports (fine + coarse)",
              "Targets: svg·png·pdf·pdf-tex·html·tikz",
              "Shapes union + use/component reuse",
              "Layout row/col/grid/wrap/free + Sizing",
              "Paint: color|gradient|pattern|image",
              "Effects + appearance stacks (2.4.0)",
              "Mat3/Mat4 + CSS transform list",
              "NO event/animation/hit-test in IR (grep-verified)"]),
          ("Uncertain / verify",[
              "planar boolean robustness & region cap",
              "  (from a note; confirm against tests/)",
              "per-category capability counts",
              "  (manifest total = 290; groups are editorial)",
              "exact HTML flow-mode coverage",
              "  (blurb says 'flow-mode limits')",
              "TikZ painter feature completeness vs SVG",
              "",
              "Method: direct grep/read of source;",
              "no claim rests on memory or assumption."])]
    cw=(W-2*MX-2*24)/3
    for i,(t,items) in enumerate(cols):
        x=MX+i*(cw+24)
        c=[ACC,HAVE,SIGNAL][i]
        R([x,y,cw,470],fill=CARD,stroke=RULE,radius=10,shadow=True); R([x,y,cw,4],fill=c,radius=2)
        T(x+15,y+13,cw-24,t,size=SML,weight=800,color=INK)
        for j,it in enumerate(items):
            yy=y+42+j*38
            mono = not it.startswith("  ")
            T(x+15,yy,cw-26,it,size=CAP,color=(MUTE if it.startswith("  ") else SUB),mono=(":" in it or "/" in it or "." in it),lh=1.2,italic=it.startswith("  "))
    T(MX,y+484,W-2*MX,"Disclaimer: no statement here should be taken for granted — claims are grounded in the cited source at the stated version (HEAD 2.4.1); anything not verifiable in-tree is labelled uncertain.  Generated by Claude Opus 4.8 via the FrameForge MCP · 2026-07-03.",
      size=9.5,color=FAINT,italic=True)

# ---------------------------------------------------------------- build
s_title(); s_exec(); s_context(); s_components(); s_objectmodel(); s_pipeline()
s_coord(); s_style(); s_capmap(); s_mcp(); s_export(); s_constraints()
s_part2(); s_compare(); s_gap1(); s_gap2(); s_roadmap(); s_risks(); s_appendix()

if __name__=="__main__":
    out=os.environ.get("OUTPUT_YAML_PATH","architecture_deck.fg.yaml")
    open(out,"w").write(serialize(b.build(), format="yaml"))
    print("wrote",out,"pages:",FOLIO[0]+1)
