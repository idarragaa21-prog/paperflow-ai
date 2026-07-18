# -*- coding: utf-8 -*-
import os, html
from svg import MOTIFS

OUT = "carousel"
os.makedirs(OUT, exist_ok=True)

# ---------- Brand tokens ----------
PAPER   = "#F4F1EA"   # bone paper
INK     = "#1B2830"   # deep ink
PETROL  = "#0E3541"   # brand petrol (inverted bg)
PETROL2 = "#0A2A34"
GOLD    = "#B08A4F"   # antique gold accent
TEAL    = "#1E5A66"   # secondary accent
CLAY    = "#9C4A38"   # restrained warning red (cuestiona)
MUTE    = "#5E6E74"   # muted ink for captions

FONT_SERIF   = "'Playfair Display', serif"
FONT_BODY    = "'EB Garamond', serif"
FONT_SANS    = "'Libre Franklin', sans-serif"

CSS = f"""
@page {{ margin:0; size:1080px 1350px; }}
* {{ margin:0; padding:0; box-sizing:border-box; -webkit-font-smoothing:antialiased; text-rendering:geometricPrecision; }}
html,body {{ width:1080px; height:1350px; }}
.slide {{
  position:relative; width:1080px; height:1350px; overflow:hidden;
  background:{PAPER}; color:{INK};
  padding:92px 96px 84px;
  display:flex; flex-direction:column;
}}
.slide.dark {{ background:{PETROL}; color:{PAPER}; }}
.slide.dark .muted {{ color:#B9C6C9; }}
.grain {{ position:absolute; inset:0; pointer-events:none; opacity:0.5;
  background-image:radial-gradient(rgba(0,0,0,0.05) 0.5px, transparent 0.5px);
  background-size:4px 4px; }}
.slide.dark .grain {{ background-image:radial-gradient(rgba(255,255,255,0.045) 0.5px, transparent 0.5px); }}

/* header */
.top {{ display:flex; justify-content:space-between; align-items:center; z-index:3; }}
.brand {{ display:flex; align-items:center; gap:16px; }}
.emblem {{ width:38px; height:38px; }}
.wordmark {{ font-family:{FONT_SERIF}; font-weight:700; font-size:27px; letter-spacing:5px; }}
.wordmark .co {{ color:{GOLD}; }}
.slide.dark .wordmark .co {{ color:{GOLD}; }}
.top-right {{ font-family:{FONT_SANS}; font-size:12.5px; letter-spacing:3px; font-weight:600;
  text-transform:uppercase; color:{MUTE}; }}
.slide.dark .top-right {{ color:#8FA3A7; }}
.rule {{ height:1px; background:currentColor; opacity:0.16; margin:26px 0 0; z-index:3; }}
.rule.gold {{ background:{GOLD}; opacity:0.9; height:2px; width:64px; margin:0; }}

/* body area */
.body {{ flex:1; display:flex; flex-direction:column; justify-content:center; z-index:3; position:relative; }}
.kicker {{ font-family:{FONT_SANS}; font-weight:700; font-size:15px; letter-spacing:4.5px;
  text-transform:uppercase; color:{TEAL}; margin-bottom:30px; display:flex; align-items:center; gap:18px; }}
.slide.dark .kicker {{ color:{GOLD}; }}
.kicker::before {{ content:""; width:44px; height:2px; background:currentColor; opacity:0.85; }}

h1 {{ font-family:{FONT_SERIF}; font-weight:800; line-height:1.06; letter-spacing:-0.5px; }}
.t-hero  {{ font-size:76px; }}
.t-xl    {{ font-size:62px; }}
.t-lg    {{ font-size:52px; }}
h1 em {{ font-style:italic; color:{TEAL}; }}
.slide.dark h1 em {{ color:{GOLD}; }}

.lead {{ font-family:{FONT_BODY}; font-size:34px; line-height:1.48; color:{INK}; margin-top:34px; max-width:820px; }}
.slide.dark .lead {{ color:#E7E1D4; }}
.lead b {{ font-weight:600; color:{TEAL}; }}
.slide.dark .lead b {{ color:{GOLD}; }}
.muted {{ color:{MUTE}; }}

.flag {{ margin-top:40px; border-left:3px solid {GOLD}; padding:6px 0 6px 22px;
  font-family:{FONT_SANS}; font-size:19px; line-height:1.5; font-weight:500; color:{INK}; max-width:760px; }}
.slide.dark .flag {{ color:#E7E1D4; }}

/* two column confirm/challenge */
.cols {{ display:grid; grid-template-columns:1fr 1fr; gap:34px; margin-top:44px; }}
.card {{ border-top:2px solid currentColor; padding-top:20px; }}
.card .lbl {{ font-family:{FONT_SANS}; font-size:14px; font-weight:700; letter-spacing:3px;
  text-transform:uppercase; margin-bottom:14px; }}
.card.ok  {{ color:{TEAL}; }}
.card.no  {{ color:{CLAY}; }}
.card p {{ font-family:{FONT_BODY}; font-size:27px; line-height:1.4; color:{INK}; }}

/* stat */
.stat {{ font-family:{FONT_SERIF}; font-weight:800; font-size:210px; line-height:0.9;
  letter-spacing:-4px; color:{CLAY}; }}
.slide.dark .stat {{ color:{GOLD}; }}
.stat-label {{ font-family:{FONT_BODY}; font-size:34px; line-height:1.4; margin-top:18px; max-width:720px; }}

/* checklist rows */
.rows {{ margin-top:20px; }}
.row {{ display:flex; gap:20px; align-items:flex-start; padding:22px 0; border-bottom:1px solid rgba(27,40,48,0.12); }}
.row:last-child {{ border-bottom:none; }}
.row .n {{ font-family:{FONT_SANS}; font-weight:700; font-size:16px; color:{GOLD}; min-width:34px; padding-top:6px; letter-spacing:1px; }}
.row p {{ font-family:{FONT_BODY}; font-size:29px; line-height:1.32; }}
.row p b {{ font-weight:600; color:{TEAL}; }}

/* question box (final) */
.qbox {{ margin-top:40px; border:1px solid rgba(244,241,234,0.28); border-radius:2px;
  padding:32px 34px; }}
.qbox .qk {{ font-family:{FONT_SANS}; font-size:13px; letter-spacing:3px; font-weight:700;
  text-transform:uppercase; color:{GOLD}; margin-bottom:16px; }}
.qbox p {{ font-family:{FONT_BODY}; font-style:italic; font-size:33px; line-height:1.42; color:{PAPER}; }}

/* footer */
.foot {{ display:flex; justify-content:space-between; align-items:flex-end; z-index:3;
  font-family:{FONT_SANS}; font-size:13px; letter-spacing:2px; text-transform:uppercase; }}
.foot .l {{ color:{MUTE}; font-weight:500; }}
.foot .handle {{ text-transform:none; letter-spacing:0.5px; font-weight:600; color:{TEAL}; }}
.slide.dark .foot .handle {{ color:{GOLD}; }}
.slide.dark .foot .l {{ color:#8FA3A7; }}
.foot .r {{ display:flex; align-items:center; gap:12px; color:{INK}; font-weight:700; }}
.slide.dark .foot .r {{ color:{PAPER}; }}
.foot .r .num {{ font-family:{FONT_SERIF}; font-size:19px; letter-spacing:1px; }}
.foot .r .of {{ color:{GOLD}; }}

/* decorative motif */
.motif {{ position:absolute; z-index:1; color:{INK}; }}
.slide.dark .motif {{ color:{PAPER}; }}
.motif.br {{ right:-40px; bottom:78px; width:360px; }}
.motif.tr {{ right:70px; top:150px; width:300px; }}
.src {{ position:absolute; left:96px; bottom:150px; font-family:{FONT_SANS}; font-size:11.5px;
  letter-spacing:1.5px; color:{MUTE}; text-transform:uppercase; z-index:3; opacity:0.85; }}
"""

EMBLEM = f'''<svg class="emblem" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.6">
  <rect x="3" y="3" width="34" height="34" rx="2" opacity="0.9"/>
  <path d="M13 12 h14 M13 20 h10 M13 28 h14" stroke-width="2.2"/>
  <line x1="20" y1="3" x2="20" y2="0.5" opacity="0"/>
</svg>'''

def wordmark():
    return f'<span class="wordmark">EVIDEN<span class="co">TIA</span></span>'

def header(dark=False):
    return f'''<div class="top">
      <div class="brand">{EMBLEM}{wordmark()}</div>
      <div class="top-right">Pie&nbsp;&amp;&nbsp;Tobillo · Lectura Crítica</div>
    </div>
    <div class="rule"></div>'''

def footer(n):
    return f'''<div class="rule" style="margin-bottom:22px;"></div>
    <div class="foot">
      <div class="l">Medicina Basada en Evidencia&nbsp; ·&nbsp; <span class="handle">@evidentia_co</span></div>
      <div class="r"><span class="num">{n:02d}</span><span class="of">/ 10</span></div>
    </div>'''

def motif(name, cls="br", op=0.09, sw=2.2):
    return f'<div class="motif {cls}" style="opacity:{op}">{MOTIFS[name](1.0, sw)}</div>'

def slide(n, inner, dark=False, motif_html=""):
    cls = "slide dark" if dark else "slide"
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<style>{CSS}</style></head>
<body><div class="{cls}">
<div class="grain"></div>
{motif_html}
{header(dark)}
<div class="body">{inner}</div>
{footer(n)}
</div></body></html>'''

# ---------------- SLIDES ----------------
slides = {}

# 01 — HOOK
slides[1] = slide(1, f'''
  <div class="kicker">Análisis crítico</div>
  <h1 class="t-hero">Operamos el peroné.<br>Pero el peroné<br><em>casi nunca decide.</em></h1>
  <p class="lead">Lo que decide la cirugía es la <b>estabilidad del anillo</b> del tobillo — y eso no siempre se ve en la primera radiografía.</p>
''', dark=True, motif_html=motif("mortise","br",0.14,2.0))

# 02 — Qué tipo de artículo
slides[2] = slide(2, f'''
  <div class="kicker">Paso 1 — El diseño</div>
  <h1 class="t-xl">«Conceptos actuales»<br>es una <em>revisión narrativa.</em></h1>
  <p class="lead">Sin PRISMA. Sin búsqueda sistemática. Sin metaanálisis. Es <b>síntesis experta</b>: un mapa razonado, no una prueba.</p>
  <div class="flag">Declara «Nivel de evidencia II». En rigor, una revisión narrativa aporta certeza de <b>Nivel V</b>: la etiqueta promete más de lo que el diseño entrega.</div>
''', motif_html=motif("pyramid","tr",0.08,2.2))

# 03 — Mensaje clínico central
slides[3] = slide(3, f'''
  <div class="kicker">Paso 2 — El mensaje</div>
  <h1 class="t-xl">La <em>estabilidad</em> —no el trazo del peroné— dicta el tratamiento.</h1>
  <p class="lead">El tobillo es un anillo. Roto en <b>un punto</b> → estable, la mayoría conservador. Roto en <b>dos o más</b> → inestable, valora cirugía.</p>
''', motif_html=motif("ring","tr",0.09,2.2))

# 04 — Concepto: columna medial
slides[4] = slide(4, f'''
  <div class="kicker">El concepto clave</div>
  <h1 class="t-xl">El protagonista<br>no es lateral. <em>Es medial.</em></h1>
  <p class="lead">La integridad del <b>deltoideo profundo</b> (fascículo posterior, LTTPP) define la estabilidad. El peroné solo cuenta la mitad de la historia.</p>
''', motif_html=motif("deltoid","br",0.10,2.2))

# 05 — Cambio de paradigma (ortopedista)
slides[5] = slide(5, f'''
  <div class="kicker">Qué cambia — ortopedista</div>
  <h1 class="t-lg">La radiografía <em>en carga</em> sustituye al «gravity test».</h1>
  <p class="lead"><b>SER IV-A</b> (LTTPP íntegro): conservador con yeso en carga a 90°.<br><b>SER IV-B</b> (deltoideo roto): quirúrgico. La misma fractura, dos caminos.</p>
''', motif_html=motif("stress","tr",0.12,2.2))

# 06 — Confirma / cuestiona
slides[6] = slide(6, f'''
  <div class="kicker">Confirma · Cuestiona</div>
  <h1 class="t-lg">Menos hierro<br>del que creíamos.</h1>
  <div class="cols">
    <div class="card ok">
      <div class="lbl">Confirma</div>
      <p>La placa de tercio de caña lateral sigue siendo el patrón oro. Lo nuevo casi nunca lo supera.</p>
    </div>
    <div class="card no">
      <div class="lbl">Cuestiona</div>
      <p>Muchas unimaleolares «aisladas» y estables no necesitan osteosíntesis.</p>
    </div>
  </div>
''', motif_html=motif("plate","br",0.09,2.2))

# 07 — Epidemiólogo
slides[7] = slide(7, f'''
  <div class="kicker">Paso 3 — El epidemiólogo</div>
  <h1 class="t-xl">Buen algoritmo,<br><em>certeza modesta.</em></h1>
  <p class="lead">Recomendaciones apoyadas en estudios nivel III–IV, biomecánica y cadáver. Sin GRADE ni evaluación de sesgo; validez externa limitada (algoritmo <b>unicéntrico</b>).</p>
''', motif_html=motif("pyramid","tr",0.08,2.2))

# 08 — Dato incómodo
slides[8] = slide(8, f'''
  <div class="kicker">Evidencia vs. práctica</div>
  <div style="display:flex;align-items:center;gap:8px;">
    <div class="stat">40%</div>
  </div>
  <p class="stat-label">de <b>malreducciones de la sindesmosis</b> en TC postoperatoria. El problema no suele ser qué implante elegimos — es la reducción que logramos.</p>
''', motif_html=motif("mortise","tr",0.07,2.0))

# 09 — Aplicación clínica
slides[9] = slide(9, f'''
  <div class="kicker">Paso 4 — Mañana en la consulta</div>
  <h1 class="t-lg" style="margin-bottom:6px;">Qué cambia mañana.</h1>
  <div class="rows">
    <div class="row"><span class="n">01</span><p>Radiografía <b>en carga</b> en toda SER aparentemente aislada.</p></div>
    <div class="row"><span class="n">02</span><p>No inmovilizar la <b>SER II</b>: carga inmediata según tolerancia.</p></div>
    <div class="row"><span class="n">03</span><p><b>TC</b> ante SAD II: impactación medial en el 61–73%.</p></div>
    <div class="row"><span class="n">04</span><p>Placa lateral como estándar; implantes de rescate, <b>individualizados</b>.</p></div>
  </div>
''', motif_html="")

# 10 — Conclusión + pregunta
slides[10] = slide(10, f'''
  <div class="kicker">Conclusión</div>
  <h1 class="t-lg">El mensaje real:<br>un mapa excelente,<br><em>no una prueba.</em></h1>
  <p class="lead">Consenso experto, actualizado y clínicamente útil. Un marco para decidir mejor — no evidencia de alto nivel. Cámbielo cuando ésta exista.</p>
  <div class="qbox">
    <div class="qk">Para el debate</div>
    <p>¿Cuántas osteosíntesis de peroné indicamos por la radiografía… y cuántas por una inestabilidad realmente demostrada en carga?</p>
  </div>
''', dark=True, motif_html=motif("ring","br",0.10,2.2))

# source line only on slide 2 (design furniture, discreet)
for n, htmlc in slides.items():
    with open(f"{OUT}/slide-{n:02d}.html", "w", encoding="utf-8") as f:
        f.write(htmlc)

print("wrote", len(slides), "slides")
