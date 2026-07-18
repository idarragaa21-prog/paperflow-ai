# -*- coding: utf-8 -*-
import os
from figb64 import FIG
from anat_b64 import ANAT, LIG
from orn import dotgrid, bulb_magnifier, diamond_rule, laurel_crest, ankle_anatomy, NAVY, NAVY2, GOLD, GOLD2

OUT="carousel3"; TOTAL=13
os.makedirs(OUT, exist_ok=True)
FACES=open('montserrat_faces.txt').read()

WHITE="#F8F6F1"; RED="#C0272D"; BODY="#2B3A57"; MUTE="#6E7789"; CREAM="#F1ECE0"
FSANS="'Montserrat', sans-serif"; FSERIF="'Playfair Display', serif"; FBODY="'EB Garamond', serif"

CSS=f"""{FACES}
@page {{ margin:0; size:1080px 1350px; }}
* {{ margin:0; padding:0; box-sizing:border-box; -webkit-font-smoothing:antialiased; text-rendering:geometricPrecision; }}
html,body {{ width:1080px; height:1350px; }}
.slide {{ position:relative; width:1080px; height:1350px; overflow:hidden; background:{WHITE}; color:{NAVY};
  display:flex; flex-direction:column; }}
.slide.dark {{ background:{NAVY}; color:{WHITE}; }}
.pad {{ position:relative; z-index:5; flex:1; display:flex; flex-direction:column; padding:70px 86px 66px; }}

/* ornaments layer */
.orn {{ position:absolute; inset:0; z-index:1; pointer-events:none; overflow:hidden; }}
.orn .abs {{ position:absolute; }}

/* top lockup */
.toplock {{ display:flex; align-items:center; justify-content:center; gap:20px; z-index:5; }}
.toplock .ln {{ height:1px; width:74px; background:{GOLD}; opacity:0.9; }}
.toplock .wm {{ font-family:{FSANS}; font-weight:600; font-size:22px; letter-spacing:11px; color:{NAVY}; padding-left:11px; }}
.slide.dark .toplock .wm {{ color:{WHITE}; }}
.toplock .dot {{ width:4px; height:4px; border-radius:50%; background:{GOLD}; }}

/* body */
.body {{ flex:1; display:flex; flex-direction:column; z-index:5; }}
.body.center {{ justify-content:center; align-items:center; text-align:center; }}
.body.tl {{ justify-content:center; }}
.kick {{ font-family:{FSANS}; font-weight:700; font-size:15px; letter-spacing:5px; text-transform:uppercase;
  color:{GOLD}; margin-bottom:26px; }}
h1 {{ font-family:{FSANS}; font-weight:800; line-height:1.02; letter-spacing:-1px; color:{NAVY}; }}
.slide.dark h1 {{ color:{WHITE}; }}
.h-hero{{ font-size:96px; }} .h-xl{{ font-size:78px; }} .h-lg{{ font-size:60px; }} .h-md{{ font-size:50px; }}
h1 .rd {{ color:{RED}; }} h1 .gd {{ color:{GOLD}; }}
.sub {{ font-family:{FBODY}; font-size:36px; line-height:1.4; color:{BODY}; margin-top:0; max-width:840px; }}
.slide.dark .sub {{ color:#DCE3EE; }}
.sub.gold {{ color:{GOLD}; font-style:italic; }}
.dvd {{ margin:34px 0; }}
.body.center .dvd {{ display:flex; justify-content:center; }}
.lead {{ font-family:{FBODY}; font-size:33px; line-height:1.46; color:{BODY}; max-width:850px; }}
.lead b {{ color:{NAVY}; font-weight:700; }} .slide.dark .lead b {{ color:{GOLD}; }}
.flag {{ margin-top:30px; border-left:3px solid {GOLD}; padding:6px 0 6px 20px; font-family:{FSANS};
  font-size:18px; font-weight:500; line-height:1.5; color:{BODY}; max-width:800px; }}

/* article id card */
.idcard {{ background:#FFFFFF; border:1.5px solid {NAVY}; position:relative; padding:46px 48px; width:100%;
  box-shadow:0 26px 60px -34px rgba(23,41,77,0.5); }}
.idcard .corner {{ position:absolute; width:18px; height:18px; border-color:{GOLD}; }}
.idcard .c1 {{ top:9px; left:9px; border-top:2px solid; border-left:2px solid; }}
.idcard .c2 {{ top:9px; right:9px; border-top:2px solid; border-right:2px solid; }}
.idcard .c3 {{ bottom:9px; left:9px; border-bottom:2px solid; border-left:2px solid; }}
.idcard .c4 {{ bottom:9px; right:9px; border-bottom:2px solid; border-right:2px solid; }}
.idcard .jr {{ font-family:{FSANS}; font-weight:700; font-size:13px; letter-spacing:2.5px; text-transform:uppercase; color:{GOLD}; }}
.idcard h2 {{ font-family:{FSERIF}; font-weight:800; font-size:46px; line-height:1.12; color:{NAVY}; margin:18px 0 20px; }}
.idcard .au {{ font-family:{FBODY}; font-size:26px; color:{BODY}; }}
.idcard .mt {{ font-family:{FSANS}; font-size:14.5px; letter-spacing:0.3px; color:{MUTE}; line-height:1.7; margin-top:14px; }}
.idcard .rule {{ height:1px; background:rgba(23,41,77,0.14); margin:24px 0; }}
.idcard .badge {{ display:inline-flex; align-items:center; gap:10px; background:{NAVY}; color:{WHITE};
  font-family:{FSANS}; font-weight:700; font-size:14px; letter-spacing:2px; text-transform:uppercase; padding:11px 18px; }}
.idcard .badge .d {{ width:7px; height:7px; background:{GOLD}; transform:rotate(45deg); }}
.idcard .tg {{ font-family:{FBODY}; font-style:italic; font-size:22px; color:{MUTE}; margin-left:16px; }}

/* figure capture */
.cap {{ width:100%; }}
.capf {{ position:relative; background:{NAVY}; padding:15px; box-shadow:0 24px 56px -30px rgba(23,41,77,0.6); }}
.capf img {{ display:block; width:100%; height:auto; }}
.capf.lite {{ background:#FFFFFF; border:1.5px solid {NAVY}; }}
.capf .tick {{ position:absolute; width:17px; height:17px; border-color:{GOLD}; z-index:3; }}
.capf .t1{{top:6px;left:6px;border-top:2px solid;border-left:2px solid;}}
.capf .t2{{top:6px;right:6px;border-top:2px solid;border-right:2px solid;}}
.capf .t3{{bottom:6px;left:6px;border-bottom:2px solid;border-left:2px solid;}}
.capf .t4{{bottom:6px;right:6px;border-bottom:2px solid;border-right:2px solid;}}
.capf.rad::after {{ content:""; position:absolute; inset:15px; pointer-events:none;
  background:linear-gradient(155deg, rgba(23,41,77,0.42), rgba(34,64,110,0.05) 50%, rgba(190,155,73,0.20));
  mix-blend-mode:soft-light; }}
.capbar {{ display:flex; justify-content:space-between; align-items:baseline; margin-top:16px; gap:20px; }}
.capbar .cf {{ font-family:{FSANS}; font-weight:700; font-size:14px; letter-spacing:1.5px; text-transform:uppercase; color:{NAVY}; }}
.capbar .src {{ font-family:{FSANS}; font-size:12px; color:{MUTE}; text-align:right; line-height:1.4; }}
.capnote {{ font-family:{FBODY}; font-size:29px; line-height:1.36; margin-top:20px; color:{BODY}; max-width:880px; }}
.capnote b {{ color:{NAVY}; font-weight:700; }}
.checknote {{ font-family:{FSANS}; font-size:16.5px; line-height:1.5; color:{MUTE}; margin-top:22px; max-width:820px; }}

/* stat */
.stat {{ font-family:{FSANS}; font-weight:800; font-size:170px; line-height:0.86; letter-spacing:-4px; color:{RED}; }}
.slide.dark .stat {{ color:{GOLD}; }}
.stat-row {{ display:flex; align-items:center; gap:34px; }}
.stat-lb {{ font-family:{FBODY}; font-size:30px; line-height:1.36; color:{BODY}; max-width:460px; }}

/* checklist */
.rows {{ width:100%; }}
.row {{ display:flex; gap:22px; align-items:flex-start; padding:18px 0; border-bottom:1px solid rgba(23,41,77,0.12); }}
.row:last-child {{ border-bottom:none; }}
.row .n {{ font-family:{FSANS}; font-weight:800; font-size:20px; color:{GOLD}; min-width:38px; padding-top:4px; }}
.row p {{ font-family:{FBODY}; font-size:30px; line-height:1.3; color:{BODY}; }}
.row p b {{ color:{NAVY}; font-weight:700; }}

/* two-column biomechanics dossier */
.cols2 {{ display:grid; grid-template-columns:1fr 1fr; gap:36px; width:100%; text-align:left; }}
.col .ct {{ font-family:{FSANS}; font-weight:800; font-size:19px; letter-spacing:1px; color:{NAVY}; text-transform:uppercase; }}
.col .cs {{ font-family:{FBODY}; font-style:italic; font-size:20px; color:{GOLD}; margin:2px 0 14px; }}
.col .cr {{ border-top:2px solid {GOLD}; padding-top:16px; }}
.col p {{ font-family:{FBODY}; font-size:25px; line-height:1.34; color:{BODY}; margin-bottom:11px; }}
.col p b {{ color:{NAVY}; font-weight:700; }}
.tieline {{ font-family:{FBODY}; font-size:28px; line-height:1.42; color:{NAVY}; text-align:center; margin:30px auto 0; max-width:900px; }}
.tieline b {{ color:{GOLD}; font-weight:700; }}
.anatrow {{ display:grid; grid-template-columns:300px 1fr; gap:34px; align-items:center; width:100%; text-align:left; }}
.anatrow .lead {{ margin:0; }}

/* question box */
.qbox {{ border:1px solid rgba(248,246,241,0.3); padding:30px 34px; width:100%; position:relative; }}
.qbox .qk {{ font-family:{FSANS}; font-weight:700; font-size:13px; letter-spacing:3px; text-transform:uppercase; color:{GOLD}; margin-bottom:14px; }}
.qbox p {{ font-family:{FBODY}; font-style:italic; font-size:33px; line-height:1.42; color:{WHITE}; }}

/* bottom lockup */
.foot {{ z-index:5; display:flex; flex-direction:column; align-items:center; gap:16px; }}
.foot .logo {{ display:flex; flex-direction:column; align-items:center; gap:7px; }}
.foot .lw {{ font-family:{FSERIF}; font-weight:700; font-size:27px; letter-spacing:8px; color:{NAVY}; padding-left:8px; }}
.slide.dark .foot .lw {{ color:{WHITE}; }}
.foot .ul {{ width:150px; height:2px; background:{GOLD}; }}
.foot .row2 {{ display:flex; justify-content:space-between; align-items:center; width:100%;
  font-family:{FSANS}; font-size:12.5px; letter-spacing:2px; text-transform:uppercase; margin-top:4px; }}
.foot .row2 .hl {{ color:{GOLD}; font-weight:700; text-transform:none; letter-spacing:0.5px; }}
.foot .row2 .pg {{ color:{MUTE}; font-weight:600; }} .slide.dark .foot .row2 .pg {{ color:#9FB0C8; }}
.progress {{ display:flex; gap:6px; width:100%; margin-top:2px; }}
.progress .seg {{ height:3px; flex:1; background:{NAVY}; opacity:0.14; border-radius:3px; }}
.slide.dark .progress .seg {{ background:{WHITE}; opacity:0.16; }}
.progress .seg.on {{ background:{GOLD}; opacity:1; }}
"""

def orn_layer(kind, dark=False):
    navy = WHITE if dark else NAVY
    blob = "#20365E" if not dark else "#24406C"
    L=[]
    if kind=="cover":
        L.append(f'<div class="abs" style="top:-160px;left:-160px"><svg width="440" height="440" viewBox="0 0 440 440" fill="none"><circle cx="220" cy="220" r="200" fill="{blob}"/><circle cx="220" cy="220" r="216" stroke="{GOLD}" stroke-width="2" opacity="0.8"/></svg></div>')
        L.append(f'<div class="abs" style="top:180px;left:150px">{dotgrid(5,5,15,3,GOLD,0.8)}</div>')
        L.append(f'<div class="abs" style="top:-130px;right:-120px"><svg width="360" height="360" viewBox="0 0 360 360" fill="none"><circle cx="180" cy="180" r="150" stroke="{GOLD}" stroke-width="1.6" opacity="0.55"/><circle cx="180" cy="180" r="120" stroke="{GOLD}" stroke-width="1.6" opacity="0.35"/></svg></div>')
        L.append(f'<div class="abs" style="top:80px;right:70px">{dotgrid(6,4,14,2.6,GOLD,0.75)}</div>')
        L.append(f'<div class="abs" style="bottom:0;left:0"><svg width="360" height="380" viewBox="0 0 360 380" fill="none"><path d="M0 60 L0 380 L360 380 Z" fill="{blob}"/></svg></div>')
        L.append(f'<div class="abs" style="bottom:150px;left:60px"><svg width="150" height="150" viewBox="0 0 150 150" fill="none"><circle cx="75" cy="75" r="70" stroke="{GOLD}" stroke-width="1.6" opacity="0.55"/></svg></div>')
        L.append(f'<div class="abs" style="bottom:120px;left:34px">{dotgrid(5,5,14,2.6,GOLD,0.7)}</div>')
    elif kind=="dark":
        L.append(f'<div class="abs" style="top:-150px;right:-150px"><svg width="420" height="420" viewBox="0 0 420 420" fill="none"><circle cx="210" cy="210" r="180" stroke="{GOLD}" stroke-width="1.6" opacity="0.4"/><circle cx="210" cy="210" r="140" stroke="{GOLD}" stroke-width="1.6" opacity="0.25"/></svg></div>')
        L.append(f'<div class="abs" style="top:90px;right:70px">{dotgrid(6,4,14,2.6,GOLD,0.55)}</div>')
        L.append(f'<div class="abs" style="bottom:120px;left:40px">{dotgrid(5,5,14,2.6,GOLD,0.5)}</div>')
        L.append(f'<div class="abs" style="bottom:150px;left:70px"><svg width="150" height="150" viewBox="0 0 150 150" fill="none"><circle cx="75" cy="75" r="70" stroke="{GOLD}" stroke-width="1.6" opacity="0.4"/></svg></div>')
    else:  # content — light corner accents
        L.append(f'<div class="abs" style="top:-90px;left:-90px"><svg width="230" height="230" viewBox="0 0 230 230" fill="none"><circle cx="115" cy="115" r="100" fill="{blob}"/><circle cx="115" cy="115" r="112" stroke="{GOLD}" stroke-width="1.6" opacity="0.7"/></svg></div>')
        L.append(f'<div class="abs" style="top:104px;left:108px">{dotgrid(4,3,13,2.4,GOLD,0.7)}</div>')
        L.append(f'<div class="abs" style="bottom:56px;right:60px">{dotgrid(5,3,13,2.3,GOLD,0.55)}</div>')
        L.append(f'<div class="abs" style="top:-70px;right:-70px"><svg width="180" height="180" viewBox="0 0 180 180" fill="none"><circle cx="90" cy="90" r="78" stroke="{GOLD}" stroke-width="1.4" opacity="0.4"/></svg></div>')
    return f'<div class="orn">{"".join(L)}</div>'

def toplock():
    return f'<div class="toplock"><span class="ln"></span><span class="dot"></span><span class="wm">EVIDENTIA</span><span class="dot"></span><span class="ln"></span></div>'

def footer(n, dark=False):
    segs="".join(f'<span class="seg{" on" if i==n else ""}"></span>' for i in range(1,TOTAL+1))
    return f'''<div class="foot">
      <div class="logo"><span class="lw">EVIDENTIA</span><span class="ul"></span></div>
      <div class="row2"><span class="hl">@evidentia_co</span><span class="pg">{n:02d} / {TOTAL}</span></div>
      <div class="progress">{segs}</div></div>'''

def slide(n, body, dark=False, kind="content"):
    cls="slide dark" if dark else "slide"
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}</style></head>
<body><div class="{cls}">{orn_layer(kind,dark)}
<div class="pad">{toplock()}
<div class="body {'center' if kind in ('cover','statement','stat','closing') else 'tl'}" style="margin:34px 0;">{body}</div>
{footer(n,dark)}</div></div></body></html>'''

def dvd(w=360): return f'<div class="dvd">{diamond_rule(GOLD,w)}</div>'
def cap(figkey,cf,note,rad=True):
    fc="capf rad" if rad else "capf lite"
    ticks='<span class="tick t1"></span><span class="tick t2"></span><span class="tick t3"></span><span class="tick t4"></span>'
    return f'''<div class="cap"><div class="{fc}"><img src="{FIG[figkey]}">{ticks}</div>
      <div class="capbar"><span class="cf">{cf}</span><span class="src">Tomada de Olías-López et&nbsp;al.<br>Rev Esp Cir Ortop Traumatol · RECOT 2024</span></div></div>
      <p class="capnote">{note}</p>'''

SL=[]
def add(body,dark=False,kind="content"): SL.append((body,dark,kind))
# 01 COVER
add(f'''
  <div class="kick" style="margin-top:20px;">Pie &amp; Tobillo · Lectura Crítica</div>
  <h1 class="h-hero">Operamos<br>el peroné.</h1>
  <h1 class="h-md" style="margin-top:18px;font-weight:700;color:{BODY};">Pero casi nunca <span class="rd" style="color:{RED};font-weight:800;">decide.</span></h1>
  {dvd(300)}
  <p class="sub" style="max-width:760px;">Lo que decide la cirugía es la <b style="color:{NAVY};font-weight:700;">estabilidad del anillo</b> del tobillo.</p>
  <div style="margin-top:34px;width:96px;">{bulb_magnifier(GOLD,3.2)}</div>
''', kind="cover")

# 02 IDENTITY
add(f'''
  <div class="idcard">
    <span class="corner c1"></span><span class="corner c2"></span><span class="corner c3"></span><span class="corner c4"></span>
    <div class="jr">El artículo bajo análisis · Open Access</div>
    <h2>Fracturas del maléolo peroneo: conceptos actuales</h2>
    <div class="au">Olías-López B, Boluda-Mengod J, Rendón-Díaz D, et&nbsp;al.</div>
    <div class="mt">Rev Esp Cir Ortop Traumatol (RECOT) · 2024;68(5):502–512 &nbsp;·&nbsp; DOI 10.1016/j.recot.2024.06.008</div>
    <div class="rule"></div>
    <div><span class="badge"><span class="d"></span>Nivel de evidencia II</span><span class="tg">…así lo declara. Volveremos a esto.</span></div>
  </div>
''', kind="content")

# 03 ANATOMY — the ring
add(f'''
  <div class="kick" style="text-align:center;width:100%;">Anatomía · La mortaja del tobillo</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:24px;">El tobillo es un <span class="gd" style="color:{GOLD};">anillo.</span></h1>
  <div class="anatrow">
    <div class="capf lite" style="width:300px;">
      <img src="{ANAT}">
      <span class="tick t1"></span><span class="tick t2"></span><span class="tick t3"></span><span class="tick t4"></span>
    </div>
    <div>
      <p style="font-family:{FBODY};font-size:27px;line-height:1.4;color:{BODY};">La <b style="color:{NAVY};font-weight:700;">mortaja</b>: tibia, peroné y astrágalo encajados como un anillo.</p>
      <p style="font-family:{FBODY};font-size:27px;line-height:1.4;color:{BODY};margin-top:15px;">Tres columnas lo sostienen — <b style="color:{NAVY};font-weight:700;">lateral</b> (peroné), <b style="color:{NAVY};font-weight:700;">medial</b> (deltoideo) y <b style="color:{NAVY};font-weight:700;">posterior</b>.</p>
      <p style="font-family:{FBODY};font-size:27px;line-height:1.4;color:{BODY};margin-top:15px;">Roto en <b style="color:{NAVY};font-weight:700;">1 punto</b> → estable. En <b style="color:{NAVY};font-weight:700;">≥2</b> → inestable.</p>
    </div>
  </div>
''', kind="content")

# 04 BIOMECHANICS — the two stabilizers
add(f'''
  <div class="kick" style="text-align:center;width:100%;">Biomecánica · Por qué se vuelve inestable</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:24px;">Dos <span class="gd" style="color:{GOLD};">guardianes</span> de la estabilidad.</h1>
  <div class="anatrow" style="grid-template-columns:236px 1fr;">
    <div class="capf lite" style="width:236px;"><img src="{LIG}"><span class="tick t1"></span><span class="tick t2"></span><span class="tick t3"></span><span class="tick t4"></span></div>
    <div>
      <div style="font-family:{FSANS};font-weight:800;font-size:19px;letter-spacing:1px;color:{NAVY};text-transform:uppercase;">Deltoideo profundo <span style="color:{GOLD};">· LTTPP</span></div>
      <p style="font-family:{FBODY};font-size:25px;line-height:1.34;color:{BODY};margin-top:6px;">Se <b style="color:{NAVY};font-weight:700;">tensa en carga</b> (pie plantígrado); frena la rotación externa y la traslación del astrágalo.</p>
      <div style="font-family:{FSANS};font-weight:800;font-size:19px;letter-spacing:1px;color:{NAVY};text-transform:uppercase;margin-top:22px;">Sindesmosis <span style="color:{GOLD};">· 3 puntos</span></div>
      <p style="font-family:{FBODY};font-size:25px;line-height:1.34;color:{BODY};margin-top:6px;">Anclaje de 3 ligamentos: <b style="color:{NAVY};font-weight:700;">LTPAI → interóseo → LTPPI</b>. Rotura completa = <b style="color:{NAVY};font-weight:700;">diástasis</b>.</p>
    </div>
  </div>
  <p class="tieline" style="margin-top:28px;">Por eso la radiografía <b>en carga</b> desenmascara lo que la de descarga esconde.</p>
''', kind="content")

# 04 STATEMENT — diseño
add(f'''
  <div class="kick">Paso 1 · El diseño</div>
  <h1 class="h-lg">¿Qué estoy leyendo<br><span class="gd" style="color:{GOLD};">en realidad?</span></h1>
  {dvd(300)}
  <p class="sub gold" style="color:{GOLD};font-style:italic;">Una revisión narrativa de «conceptos actuales».</p>
  <p class="lead" style="text-align:center;max-width:800px;margin-top:26px;">Sin PRISMA, sin búsqueda sistemática, sin metaanálisis. Declara Nivel II, pero una narrativa aporta certeza de <b>Nivel V</b>: un mapa, no una prueba.</p>
''', kind="statement")

# 04 FIGURE 1
add(f'''
  <div class="kick" style="text-align:center;width:100%;">Figura 1 · El núcleo del artículo</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:20px;">Todo cabe en <span class="gd" style="color:{GOLD};">un algoritmo.</span></h1>
  {cap("fig1","Figura 1 — Algoritmo de manejo","Un árbol de decisión claro. Pero recuerda: es <b>consenso de expertos</b>, no evidencia agregada de ensayos.", rad=False)}
''', kind="content")

# 05 STATEMENT — mensaje
add(f'''
  <div class="kick">Paso 2 · El mensaje</div>
  <h1 class="h-lg">La <span class="gd" style="color:{GOLD};">estabilidad</span> manda,<br>no el trazo del peroné.</h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:800px;">Anillo roto en <b>un punto</b> → estable. En <b>≥2</b> → inestable. El juez es la <b>columna medial</b>: el deltoideo profundo (LTTPP).</p>
''', kind="statement")

# 06 FIGURE 4
add(f'''
  <div class="kick" style="text-align:center;width:100%;">Figura 4 · El giro conceptual</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:20px;">La carga <span class="gd" style="color:{GOLD};">reclasifica.</span></h1>
  {cap("fig4","Figura 4 — Rx en carga: SER II / IV-A / IV-B","En descarga parecen iguales. En carga, la SER IV-B abre el espacio medial: <b>inestable → cirugía</b>. La IV-A, no.")}
''', kind="content")

# 07 FIGURE 3
add(f'''
  <div class="kick" style="text-align:center;width:100%;">Figura 3 · Lo que la radiografía esconde</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:20px;">La imagen simple <span class="rd" style="color:{RED};">subestima.</span></h1>
  {cap("fig3","Figura 3 — SAD II: la TC revela impactación medial","Impactación articular oculta en el <b>61–73%</b> de las SAD II. Antes de decidir, pide una <b>TC</b>.")}
''', kind="content")

# 08 FIGURE 5
add(f'''
  <div class="kick" style="text-align:center;width:100%;">Figura 5 · Opciones de fijación</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:20px;">Gana el implante <span class="gd" style="color:{GOLD};">que menos agrede.</span></h1>
  {cap("fig5","Figura 5 — Fijación endomedular del peroné","La placa 1/3 de caña sigue siendo el patrón oro. En <b>partes blandas de riesgo</b>, lo endomedular reduce complicaciones.")}
  <p class="checknote" style="text-align:center;width:100%;">Conminución u osteoporosis severa: doble placa, placa bloqueada o «tibia pro-fíbula».</p>
''', kind="content")

# 09 STAT — epidemiólogo
add(f'''
  <div class="kick">Paso 3 · El epidemiólogo</div>
  <h1 class="h-lg" style="margin-bottom:10px;">Buen mapa,<br><span class="gd" style="color:{GOLD};">certeza modesta.</span></h1>
  <p class="lead" style="text-align:center;max-width:820px;margin-bottom:30px;">Base: nivel III–IV, biomecánica y cadáver. Sin GRADE ni evaluación de sesgo. Algoritmo <b>unicéntrico</b>.</p>
  <div class="stat-row"><div class="stat">40%</div>
    <div class="stat-lb" style="text-align:left;">de <b style="color:{NAVY};font-weight:700;">malreducción sindesmal</b> en TC postoperatoria. El reto no es el implante — es la reducción.</div></div>
''', kind="stat")

# 10 CHECKLIST
add(f'''
  <div class="kick" style="text-align:center;width:100%;">Paso 4 · Como ortopedista</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Qué aplico <span class="gd" style="color:{GOLD};">mañana.</span></h1>
  <div style="display:flex;justify-content:center;margin:18px 0 6px;">{diamond_rule(GOLD,300)}</div>
  <div class="rows">
    <div class="row"><span class="n">01</span><p>Decido por <b>estabilidad</b>, no por el trazo: descarto lesión medial, posterior y sindesmal.</p></div>
    <div class="row"><span class="n">02</span><p><b>Rx en carga</b> en toda SER aislada. Jubilo el «gravity test».</p></div>
    <div class="row"><span class="n">03</span><p>SER II → carga. IV-A → <b>yeso en carga a 90°</b>. IV-B y bi/trimaleolar → cirugía.</p></div>
    <div class="row"><span class="n">04</span><p><b>TC</b> ante SAD II, maléolo posterior o duda sindesmal.</p></div>
    <div class="row"><span class="n">05</span><p>La <b>reducción anatómica</b> manda sobre el implante. Placa 1/3 de caña, estándar.</p></div>
  </div>
''', kind="content")

# 11 CLOSING (dark)
add(f'''
  <div class="kick" style="color:{GOLD};">Conclusión</div>
  <h1 class="h-lg">Un mapa excelente,<br><span class="gd" style="color:{GOLD};">no una prueba.</span></h1>
  {dvd(300)}
  <p class="sub" style="max-width:820px;">Consenso experto, actualizado y clínicamente útil. Un marco para decidir mejor — no evidencia de alto nivel.</p>
  <div class="qbox" style="margin-top:34px;max-width:900px;">
    <div class="qk">Para el debate</div>
    <p>¿Cuántas osteosíntesis de peroné indicamos por la radiografía… y cuántas por una inestabilidad realmente demostrada en carga?</p></div>
''', dark=True, kind="dark")

for i,(body,dark,kind) in enumerate(SL,1):
    open(f"{OUT}/slide-{i:02d}.html","w",encoding="utf-8").write(slide(i,body,dark,kind))
print("wrote", len(SL))
