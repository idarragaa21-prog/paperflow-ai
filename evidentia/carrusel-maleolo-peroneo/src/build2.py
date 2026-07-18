# -*- coding: utf-8 -*-
import os
from svg import MOTIFS
from figb64 import FIG

OUT = "carousel2"
TOTAL = 11
os.makedirs(OUT, exist_ok=True)

# Brand palette sampled from the real @evidentia_co logo (forest green + cream + brass)
PAPER="#F3F2EE"; INK="#1B2A1D"; PETROL="#162216"; GOLD="#A9884F"
TEAL="#425F38"; CLAY="#9C4A38"; MUTE="#66735F"; CHARCOAL="#0E170E"
FONT_SERIF="'Playfair Display', serif"; FONT_BODY="'EB Garamond', serif"; FONT_SANS="'Libre Franklin', sans-serif"

CSS = f"""
@page {{ margin:0; size:1080px 1350px; }}
* {{ margin:0; padding:0; box-sizing:border-box; -webkit-font-smoothing:antialiased; text-rendering:geometricPrecision; }}
html,body {{ width:1080px; height:1350px; }}
.slide {{ position:relative; width:1080px; height:1350px; overflow:hidden; background:{PAPER}; color:{INK};
  padding:82px 92px 90px; display:flex; flex-direction:column; }}
.slide.dark {{ background:{PETROL}; color:{PAPER}; }}
.grain {{ position:absolute; inset:0; pointer-events:none; opacity:0.5;
  background-image:radial-gradient(rgba(0,0,0,0.05) 0.5px, transparent 0.5px); background-size:4px 4px; }}
.slide.dark .grain {{ background-image:radial-gradient(rgba(255,255,255,0.045) 0.5px, transparent 0.5px); }}
.top {{ display:flex; justify-content:space-between; align-items:center; z-index:3; }}
.brand {{ display:flex; align-items:center; gap:15px; }}
.emblem {{ width:36px; height:36px; }}
.wordmark {{ font-family:{FONT_SERIF}; font-weight:700; font-size:26px; letter-spacing:5px; }}
.wordmark .co {{ color:inherit; }}
.top-right {{ font-family:{FONT_SANS}; font-size:12px; letter-spacing:3px; font-weight:600; text-transform:uppercase; color:{MUTE}; }}
.slide.dark .top-right {{ color:#9DAB90; }}
.rule {{ height:1px; background:currentColor; opacity:0.16; margin:22px 0 0; z-index:3; }}
.body {{ flex:1; display:flex; flex-direction:column; z-index:3; position:relative; }}
.body.center {{ justify-content:center; }}
.body.top {{ justify-content:flex-start; padding-top:30px; }}
.kicker {{ font-family:{FONT_SANS}; font-weight:700; font-size:14px; letter-spacing:4px; text-transform:uppercase;
  color:{TEAL}; margin-bottom:22px; display:flex; align-items:center; gap:16px; }}
.slide.dark .kicker {{ color:{GOLD}; }}
.kicker::before {{ content:""; width:40px; height:2px; background:currentColor; opacity:0.85; }}
h1 {{ font-family:{FONT_SERIF}; font-weight:800; line-height:1.06; letter-spacing:-0.5px; }}
.t-hero{{font-size:72px;}} .t-xl{{font-size:58px;}} .t-lg{{font-size:48px;}} .t-md{{font-size:40px;}}
h1 em {{ font-style:italic; color:{TEAL}; }}
.slide.dark h1 em {{ color:{GOLD}; }}
.lead {{ font-family:{FONT_BODY}; font-size:33px; line-height:1.46; color:{INK}; margin-top:28px; max-width:840px; }}
.slide.dark .lead {{ color:#E7E1D4; }}
.lead b {{ font-weight:600; color:{TEAL}; }} .slide.dark .lead b {{ color:{GOLD}; }}
.muted {{ color:{MUTE}; }} .slide.dark .muted {{ color:#C3CBB6; }}
.flag {{ margin-top:30px; border-left:3px solid {GOLD}; padding:6px 0 6px 20px; font-family:{FONT_SANS};
  font-size:18px; line-height:1.5; font-weight:500; color:{INK}; max-width:780px; }}
.slide.dark .flag {{ color:#E7E1D4; }}

/* ---- capture card ---- */
.cap {{ margin-top:26px; }}
.capframe {{ background:#FFFFFF; border:1px solid rgba(27,40,48,0.14); border-radius:3px; padding:16px;
  box-shadow:0 24px 60px -28px rgba(12,30,37,0.45), 0 2px 8px rgba(12,30,37,0.06); }}
.capframe.rad {{ background:{CHARCOAL}; border-color:rgba(255,255,255,0.10); }}
.capframe img {{ display:block; width:100%; height:auto; border-radius:1px; }}
.capbar {{ display:flex; justify-content:space-between; align-items:baseline; margin-top:16px; gap:20px; }}
.capbar .cf {{ font-family:{FONT_SANS}; font-size:14.5px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{TEAL}; }}
.capbar .src {{ font-family:{FONT_SANS}; font-size:12.5px; color:{MUTE}; letter-spacing:0.4px; text-align:right; }}
.capnote {{ font-family:{FONT_BODY}; font-size:29px; line-height:1.36; margin-top:20px; color:{INK}; max-width:860px; }}
.capnote b {{ font-weight:600; color:{TEAL}; }}

/* ---- article identity card ---- */
.idcard {{ background:#FFFFFF; border:1px solid rgba(27,40,48,0.14); border-radius:3px; padding:44px 46px;
  box-shadow:0 26px 64px -30px rgba(12,30,37,0.5); position:relative; }}
.idcard .jrnl {{ font-family:{FONT_SANS}; font-size:13px; letter-spacing:2.5px; text-transform:uppercase; color:{TEAL}; font-weight:700; }}
.idcard .jrnl .oa {{ color:{GOLD}; }}
.idcard h2 {{ font-family:{FONT_SERIF}; font-weight:800; font-size:47px; line-height:1.1; letter-spacing:-0.5px; color:{INK}; margin:20px 0 22px; }}
.idcard .auth {{ font-family:{FONT_BODY}; font-size:26px; line-height:1.4; color:#3C4A36; }}
.idcard .meta {{ font-family:{FONT_SANS}; font-size:15px; line-height:1.7; color:{MUTE}; letter-spacing:0.3px; margin-top:16px; }}
.idcard .divider {{ height:1px; background:rgba(27,40,48,0.12); margin:26px 0; }}
.idcard .badge {{ display:inline-flex; align-items:center; gap:10px; background:{PETROL}; color:{PAPER};
  font-family:{FONT_SANS}; font-size:14px; font-weight:700; letter-spacing:2px; text-transform:uppercase; padding:11px 18px; border-radius:2px; }}
.idcard .badge .dot {{ width:7px; height:7px; border-radius:50%; background:{GOLD}; }}
.idcard .tag {{ font-family:{FONT_BODY}; font-style:italic; font-size:23px; color:{MUTE}; margin-left:18px; }}

/* stat */
.stat {{ font-family:{FONT_SERIF}; font-weight:800; font-size:150px; line-height:0.9; letter-spacing:-3px; color:{CLAY}; }}
.slide.dark .stat {{ color:{GOLD}; }}
.stat-row {{ display:flex; align-items:center; gap:34px; margin-top:8px; }}
.stat-label {{ font-family:{FONT_BODY}; font-size:29px; line-height:1.36; max-width:470px; }}

/* clinical checklist rows */
.rows {{ margin-top:20px; }}
.row {{ display:flex; gap:22px; align-items:flex-start; padding:19px 0; border-bottom:1px solid rgba(27,40,48,0.12); }}
.row:last-child {{ border-bottom:none; }}
.row .n {{ font-family:{FONT_SANS}; font-weight:700; font-size:15px; color:{GOLD}; min-width:30px; padding-top:8px; letter-spacing:1px; }}
.row p {{ font-family:{FONT_BODY}; font-size:30px; line-height:1.3; }}
.row p b {{ font-weight:600; color:{TEAL}; }}
.checknote {{ font-family:{FONT_SANS}; font-size:17px; line-height:1.5; color:{MUTE}; margin-top:24px; letter-spacing:0.3px; max-width:820px; }}

.qbox {{ margin-top:34px; border:1px solid rgba(244,241,234,0.28); border-radius:2px; padding:30px 32px; }}
.qbox .qk {{ font-family:{FONT_SANS}; font-size:13px; letter-spacing:3px; font-weight:700; text-transform:uppercase; color:{GOLD}; margin-bottom:14px; }}
.qbox p {{ font-family:{FONT_BODY}; font-style:italic; font-size:32px; line-height:1.42; color:{PAPER}; }}

.foot {{ display:flex; justify-content:space-between; align-items:flex-end; z-index:3;
  font-family:{FONT_SANS}; font-size:12.5px; letter-spacing:2px; text-transform:uppercase; }}
.foot .l {{ color:{MUTE}; font-weight:500; }} .slide.dark .foot .l {{ color:#9DAB90; }}
.foot .handle {{ text-transform:none; letter-spacing:0.5px; font-weight:600; color:{TEAL}; }}
.slide.dark .foot .handle {{ color:{GOLD}; }}
.foot .r {{ display:flex; align-items:center; gap:12px; color:{INK}; font-weight:700; }}
.slide.dark .foot .r {{ color:{PAPER}; }}
.foot .r .num {{ font-family:{FONT_SERIF}; font-size:18px; letter-spacing:1px; }}
.foot .r .of {{ color:{GOLD}; }}
.motif {{ position:absolute; z-index:1; color:{INK}; }} .slide.dark .motif {{ color:{PAPER}; }}
.motif.br {{ right:-30px; bottom:96px; width:300px; }} .motif.tr {{ right:60px; top:130px; width:260px; }}

/* progress bar */
.progress {{ display:flex; gap:6px; margin-bottom:18px; z-index:3; }}
.seg {{ height:3px; flex:1; background:currentColor; opacity:0.15; border-radius:3px; }}
.seg.on {{ opacity:1; background:{GOLD}; }}
.slide.dark .seg.on {{ background:{GOLD}; }}

/* capture frame: clinical-viewer refinement */
.capframe {{ position:relative; }}
.capframe.rad {{ box-shadow:0 24px 60px -28px rgba(12,30,37,0.55), inset 0 0 0 1px rgba(176,138,79,0.30); }}
.capframe.rad::after {{ content:""; position:absolute; inset:16px; pointer-events:none;
  background:linear-gradient(155deg, rgba(22,34,22,0.60), rgba(66,95,56,0.10) 45%, rgba(169,136,79,0.30));
  mix-blend-mode:soft-light; }}
.capframe.lite {{ box-shadow:0 22px 56px -30px rgba(12,30,37,0.42), inset 0 0 0 1px rgba(176,138,79,0.28); }}
.tick {{ position:absolute; width:18px; height:18px; z-index:4; border-color:{GOLD}; opacity:0.9; }}
.tick.tl {{ top:7px; left:7px; border-top:2px solid; border-left:2px solid; }}
.tick.tr {{ top:7px; right:7px; border-top:2px solid; border-right:2px solid; }}
.tick.bl {{ bottom:7px; left:7px; border-bottom:2px solid; border-left:2px solid; }}
.tick.br {{ bottom:7px; right:7px; border-bottom:2px solid; border-right:2px solid; }}

/* corner brackets for cover / closing */
.bracket {{ position:absolute; width:64px; height:64px; z-index:3; border-color:{GOLD}; opacity:0.8; }}
.bracket.tl {{ top:60px; left:64px; border-top:2px solid; border-left:2px solid; }}
.bracket.br {{ bottom:64px; right:64px; border-bottom:2px solid; border-right:2px solid; }}

/* cover-specific */
.edition {{ font-family:{FONT_SANS}; font-size:13px; letter-spacing:4px; text-transform:uppercase;
  color:{GOLD}; font-weight:700; }}
.swipe {{ display:flex; align-items:center; gap:12px; margin-top:40px; font-family:{FONT_SANS};
  font-size:14px; letter-spacing:3px; text-transform:uppercase; font-weight:700; color:{PAPER}; }}
.swipe .arrow {{ font-size:20px; color:{GOLD}; }}
.swipe .ln {{ width:52px; height:2px; background:{GOLD}; opacity:0.8; }}

/* sign-off lockup (closing) */
.signoff {{ margin-top:34px; display:flex; align-items:center; gap:16px; }}
.signoff .so-mark {{ width:34px; height:34px; }}
.signoff .so-txt {{ font-family:{FONT_SERIF}; font-weight:700; font-size:22px; letter-spacing:4px; color:{PAPER}; }}
.signoff .so-txt .co {{ color:inherit; }}
.signoff .so-sub {{ font-family:{FONT_SANS}; font-size:13px; letter-spacing:2px; color:#9DAB90; margin-left:2px; }}
"""

# Column-E monogram echoing the real EVIDENTIA badge
EMBLEM = '''<svg class="emblem" viewBox="0 0 44 44" fill="none" stroke="currentColor" stroke-linecap="square">
  <circle cx="22" cy="22" r="19" stroke-width="1.4" opacity="0.9"/>
  <path d="M14.5 13 H30 M14.5 22 H26 M14.5 31 H30" stroke-width="2.4"/>
  <path d="M16 13.5 V30.5 M18.6 13.5 V30.5" stroke-width="1.15" opacity="0.85"/>
  <path d="M13 13 h6 M13 31 h6" stroke-width="2.4"/></svg>'''

def header():
    return f'''<div class="top"><div class="brand">{EMBLEM}<span class="wordmark">EVIDEN<span class="co">TIA</span></span></div>
      <div class="top-right">Pie&nbsp;&amp;&nbsp;Tobillo · Lectura Crítica</div></div><div class="rule"></div>'''

def footer(n):
    segs = "".join(f'<span class="seg{" on" if i==n else ""}"></span>' for i in range(1, TOTAL+1))
    return f'''<div class="progress">{segs}</div><div class="foot">
      <div class="l">Medicina Basada en Evidencia&nbsp; ·&nbsp; <span class="handle">@evidentia_co</span></div>
      <div class="r"><span class="num">{n:02d}</span><span class="of">/ {TOTAL}</span></div></div>'''

def motif(name, cls="br", op=0.09, sw=2.2):
    return f'<div class="motif {cls}" style="opacity:{op}">{MOTIFS[name](1.0, sw)}</div>'

def slide(n, inner, dark=False, layout="center", motif_html=""):
    cls = "slide dark" if dark else "slide"
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}</style></head>
<body><div class="{cls}"><div class="grain"></div>{motif_html}{header()}
<div class="body {layout}">{inner}</div>{footer(n)}</div></body></html>'''

def capture(figkey, cf, note, rad=True):
    matcls = "capframe rad" if rad else "capframe lite"
    ticks = '<span class="tick tl"></span><span class="tick tr"></span><span class="tick bl"></span><span class="tick br"></span>'
    return f'''<div class="cap"><div class="{matcls}"><img src="{FIG[figkey]}" alt="">{ticks}</div>
      <div class="capbar"><span class="cf">{cf}</span>
      <span class="src">Tomada de Olías-López et&nbsp;al.<br>Rev Esp Cir Ortop Traumatol · RECOT 2024</span></div></div>
      <p class="capnote">{note}</p>'''

S = {}

# 01 HOOK / COVER
S[1] = slide(1, f'''
  <span class="bracket tl"></span><span class="bracket br"></span>
  <div class="kicker" style="margin-bottom:20px;">Lectura crítica · Pie y tobillo</div>
  <h1 class="t-hero">Operamos el peroné.<br>Pero el peroné<br><em>casi nunca decide.</em></h1>
  <p class="lead">Lo que decide la cirugía es la <b>estabilidad del anillo</b> — y eso no siempre se ve en la primera radiografía.</p>
  <div class="swipe"><span class="ln"></span>Desliza el análisis<span class="arrow">→</span></div>
''', dark=True, motif_html=motif("mortise","br",0.16,2.0))

# 02 IDENTITY CARD (real title)
S[2] = slide(2, f'''
  <div class="kicker">El artículo bajo análisis</div>
  <p class="lead" style="margin-top:0; margin-bottom:30px; font-size:31px;">Antes de opinar, fijemos qué publicación estamos leyendo.</p>
  <div class="idcard">
    <div class="jrnl">Revista Española de Cirugía Ortopédica y Traumatología &nbsp;·&nbsp; <span class="oa">Open Access</span></div>
    <h2>Fracturas del maléolo peroneo: conceptos actuales</h2>
    <div class="auth">Olías-López B, Boluda-Mengod J, Rendón-Díaz D, et&nbsp;al.</div>
    <div class="meta">RECOT · 2024;68(5):502–512 &nbsp;·&nbsp; DOI 10.1016/j.recot.2024.06.008 &nbsp;·&nbsp; CC BY-NC-ND</div>
    <div class="divider"></div>
    <div><span class="badge"><span class="dot"></span>Nivel de evidencia II</span><span class="tag">…así lo declara. Volveremos a esto.</span></div>
  </div>
  <p class="capnote muted" style="font-size:18px; font-family:{FONT_SANS}; margin-top:26px; letter-spacing:0.3px;">
    Identificado vía PubMed · PMID 38 885 878 &nbsp;·&nbsp; Traducción y lectura crítica: EVIDENTIA</p>
''', layout="center")

# 03 DISEÑO (epidemiólogo)
S[3] = slide(3, f'''
  <div class="kicker">Paso 1 · El diseño</div>
  <h1 class="t-xl">¿Qué estoy leyendo<br><em>en realidad?</em></h1>
  <p class="lead">Una <b>revisión narrativa</b> de «conceptos actuales». Sin PRISMA, sin búsqueda sistemática, sin metaanálisis.</p>
  <div class="flag">Declara Nivel II, pero una revisión narrativa aporta certeza de <b>Nivel V</b>. Léela como opinión experta estructurada — un mapa, no una prueba.</div>
''', motif_html=motif("pyramid","tr",0.08,2.2))

# 04 CAPTURE fig1 — algorithm
S[4] = slide(4, f'''
  <div class="kicker">Figura 1 · El núcleo del artículo</div>
  <h1 class="t-md" style="margin-bottom:4px;">Todo el artículo cabe en <em>un algoritmo.</em></h1>
  {capture("fig1", "Figura 1 — Algoritmo de manejo", "Un árbol de decisión claro y bien construido. Pero recuerda: es <b>consenso de expertos</b>, no evidencia agregada de ensayos.", rad=False)}
''', layout="top")

# 05 MENSAJE central
S[5] = slide(5, f'''
  <div class="kicker">Paso 2 · El mensaje</div>
  <h1 class="t-xl">La <em>estabilidad</em> manda,<br>no el trazo del peroné.</h1>
  <p class="lead">Anillo roto en <b>un punto</b> → estable. En <b>≥2</b> → inestable. Y el juez de la estabilidad es la <b>columna medial</b>: el deltoideo profundo (LTTPP).</p>
''', motif_html=motif("ring","tr",0.09,2.2))

# 06 CAPTURE fig4 — weight-bearing
S[6] = slide(6, f'''
  <div class="kicker">Figura 4 · El giro conceptual</div>
  <h1 class="t-md" style="margin-bottom:4px;">La carga <em>reclasifica</em> la fractura.</h1>
  {capture("fig4", "Figura 4 — Rx en carga: SER II / IV-A / IV-B", "En descarga parecen iguales. En carga, la SER IV-B abre el espacio medial: <b>inestable → cirugía</b>. La IV-A, no.", rad=True)}
''', layout="top")

# 07 CAPTURE fig3 — CT impaction
S[7] = slide(7, f'''
  <div class="kicker">Figura 3 · Lo que la radiografía esconde</div>
  <h1 class="t-md" style="margin-bottom:4px;">La imagen simple <em>subestima.</em></h1>
  {capture("fig3", "Figura 3 — SAD II: la TC revela impactación medial", "Impactación articular oculta en el <b>61–73%</b> de las SAD II. Antes de decidir, pide una <b>TC</b>.", rad=True)}
''', layout="top")

# 08 CAPTURE fig5 — fixation
S[8] = slide(8, f'''
  <div class="kicker">Figura 5 · Opciones de fijación</div>
  <h1 class="t-md" style="margin-bottom:4px;">A veces gana el implante <em>que menos agrede.</em></h1>
  {capture("fig5", "Figura 5 — Fijación endomedular del peroné", "La placa 1/3 de caña sigue siendo el patrón oro. Pero en <b>partes blandas de riesgo</b>, lo endomedular reduce complicaciones.", rad=True)}
  <p class="checknote">En fractura conminuta u osteoporosis severa: doble placa, placa bloqueada o «tibia pro-fíbula». El implante se elige por el paciente, no por costumbre.</p>
''', layout="top")

# 09 EPIDEMIÓLOGO + stat
S[9] = slide(9, f'''
  <div class="kicker">Paso 3 · El epidemiólogo</div>
  <h1 class="t-lg">Buen mapa,<br><em>certeza modesta.</em></h1>
  <p class="lead" style="margin-top:22px;">Base: estudios nivel III–IV, biomecánica y cadáver. Sin GRADE ni evaluación de sesgo. Algoritmo <b>unicéntrico</b> → validez externa limitada.</p>
  <div class="stat-row"><div class="stat">40%</div>
    <div class="stat-label">de <b>malreducción sindesmal</b> en TC postoperatoria. El reto no es el implante — es la reducción.</div></div>
''', layout="center")

# 10 APLICACIÓN CLÍNICA — como ortopedista (síntesis accionable)
S[10] = slide(10, f'''
  <div class="kicker">Paso 4 · Como ortopedista</div>
  <h1 class="t-lg" style="margin-bottom:2px;">Qué aplico <em>mañana.</em></h1>
  <div class="rows">
    <div class="row"><span class="n">01</span><p>Decido por <b>estabilidad</b>, no por el trazo del peroné: descarto lesión medial, posterior y sindesmal.</p></div>
    <div class="row"><span class="n">02</span><p><b>Rx en carga</b> en toda SER aparentemente aislada. Jubilo el «gravity test».</p></div>
    <div class="row"><span class="n">03</span><p>SER II → carga. SER IV-A → <b>yeso en carga a 90°</b>. SER IV-B y bi/trimaleolar → cirugía.</p></div>
    <div class="row"><span class="n">04</span><p><b>TC</b> ante SAD II, maléolo posterior o duda sindesmal.</p></div>
    <div class="row"><span class="n">05</span><p>La <b>reducción anatómica</b> manda sobre el implante. Placa 1/3 de caña, estándar.</p></div>
  </div>
''', layout="top")

# 11 CONCLUSIÓN + pregunta
S[11] = slide(11, f'''
  <span class="bracket tl"></span><span class="bracket br"></span>
  <div class="kicker">Conclusión</div>
  <h1 class="t-lg">El mensaje real:<br>un mapa excelente,<br><em>no una prueba.</em></h1>
  <p class="lead">Consenso experto, actualizado y clínicamente útil. Un marco para decidir mejor — no evidencia de alto nivel.</p>
  <div class="qbox"><div class="qk">Para el debate</div>
    <p>¿Cuántas osteosíntesis de peroné indicamos por la radiografía… y cuántas por una inestabilidad realmente demostrada en carga?</p></div>
  <div class="signoff">{EMBLEM.replace('class="emblem"','class="so-mark"')}
    <div><div class="so-txt">EVIDEN<span class="co">TIA</span></div><div class="so-sub">Medicina basada en evidencia · @evidentia_co</div></div></div>
''', dark=True, motif_html=motif("ring","br",0.09,2.2))

for n, h in S.items():
    open(f"{OUT}/slide-{n:02d}.html","w",encoding="utf-8").write(h)
print("wrote", len(S), "slides")
