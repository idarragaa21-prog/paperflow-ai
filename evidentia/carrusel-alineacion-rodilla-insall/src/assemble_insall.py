import re
SKILL='/home/user/paperflow-ai/.claude/skills/evidentia-carousel'
src = open(f'{SKILL}/build_deck.py').read()
prefix = src.split('SL=[]')[0]
prefix = prefix.replace('OUT=_os.path.join(HERE, "out"); TOTAL=13',
                        'OUT=_os.path.join(HERE, "insall_out"); TOTAL=12')
prefix = re.sub(r'# ---- CONTENT IMAGES.*?LIG  = data_uri\("example_assets/anat_ligaments.png"\)\n',
                'FIG = {}\n', prefix, flags=re.S)

content = r'''
import os as _o
_o.makedirs(OUT, exist_ok=True)
SL=[]
def add(body,dark=False,kind="content"): SL.append((body,dark,kind))

# ---------- shared components ----------
def bignum(txt, unit="", color=None):
    color = color or NAVY
    u = f'<span style="font-size:36px;color:{MUTE};font-weight:700;">{unit}</span>' if unit else ""
    return (f'<div style="font-family:{FSANS};font-weight:800;font-size:96px;line-height:1;letter-spacing:-3px;'
            f'color:{color};margin:2px 0;">{txt}&nbsp;{u}</div>')

def whyline(txt, lead="¿Por qué?"):
    return (f'<div style="font-family:{FBODY};font-size:24px;color:{BODY};line-height:1.35;max-width:850px;'
            f'margin:14px auto 0;text-align:center;"><b style="color:{NAVY};">{lead}</b> {txt}</div>')

def trow(a, b, hi=False):
    ac = GOLD if hi else NAVY
    return (f'<div style="display:grid;grid-template-columns:0.5fr 1.5fr;gap:22px;padding:15px 0;'
            f'border-bottom:1px solid rgba(23,41,77,0.12);align-items:baseline;">'
            f'<div style="font-family:{FSANS};font-weight:800;font-size:19px;color:{ac};letter-spacing:0.3px;">{a}</div>'
            f'<div style="font-family:{FBODY};font-size:23px;color:{BODY};line-height:1.32;">{b}</div></div>')

def guarda(txt="Guárdala para tu próxima sesión bibliográfica"):
    return (f'<div style="display:flex;justify-content:center;align-items:center;gap:14px;margin:14px 0 0;width:100%;">'
            f'<span style="width:40px;height:2px;background:{GOLD};"></span>'
            f'<span style="font-family:{FSANS};font-weight:700;font-size:13.5px;letter-spacing:2.5px;text-transform:uppercase;color:{GOLD};">{txt}</span>'
            f'<span style="width:40px;height:2px;background:{GOLD};"></span></div>')

def twocard(l_title, l_big, l_sub, r_title, r_big, r_sub, l_accent=None, r_accent=None):
    l_accent = l_accent or NAVY; r_accent = r_accent or GOLD
    def card(title, big, sub, accent):
        return (f'<div style="flex:1;border-top:3px solid {accent};padding:18px 8px 4px;text-align:center;">'
                f'<div style="font-family:{FSANS};font-weight:700;font-size:15px;letter-spacing:2px;text-transform:uppercase;color:{accent};">{title}</div>'
                f'<div style="font-family:{FSANS};font-weight:800;font-size:60px;letter-spacing:-2px;color:{NAVY};margin:8px 0 2px;">{big}</div>'
                f'<div style="font-family:{FBODY};font-size:22px;color:{BODY};line-height:1.3;">{sub}</div></div>')
    return (f'<div style="display:flex;gap:34px;width:100%;max-width:900px;margin:6px auto 0;">'
            f'{card(l_title,l_big,l_sub,l_accent)}{card(r_title,r_big,r_sub,r_accent)}</div>')

# ---------- SVG: knee-implant hero with mechanical axis ----------
def knee_hero(h=470):
    return f"""<svg viewBox="0 0 300 460" width="{int(h*300/460)}" height="{h}" fill="none">
      <!-- gold mechanical axis -->
      <line x1="150" y1="18" x2="150" y2="442" stroke="{GOLD}" stroke-width="2.4" stroke-dasharray="2 9" opacity="0.9"/>
      <circle cx="150" cy="18" r="6" fill="{GOLD}"/>
      <circle cx="150" cy="442" r="6" fill="{GOLD}"/>
      <!-- femur -->
      <path d="M150 40 C150 40 138 120 136 175 L164 175 C162 120 150 40 150 40 Z" fill="{NAVY}" opacity="0.10"/>
      <rect x="120" y="34" width="60" height="150" rx="26" fill="none" stroke="{NAVY}" stroke-width="3"/>
      <!-- femoral component (implant) -->
      <path d="M116 196 C116 232 128 250 150 250 C172 250 184 232 184 196 C184 188 178 184 170 184 L130 184 C122 184 116 188 116 196 Z" fill="{NAVY}"/>
      <path d="M126 224 C126 224 138 236 150 236 C162 236 174 224 174 224" stroke="{GOLD}" stroke-width="2.4" fill="none" opacity="0.9"/>
      <!-- tibial tray -->
      <rect x="118" y="258" width="64" height="15" rx="4" fill="{GOLD}"/>
      <rect x="126" y="273" width="48" height="12" rx="3" fill="{NAVY}"/>
      <!-- tibia -->
      <rect x="122" y="286" width="56" height="150" rx="24" fill="none" stroke="{NAVY}" stroke-width="3"/>
      <path d="M150 286 L150 430" stroke="{NAVY}" stroke-width="1.4" opacity="0.25"/>
    </svg>"""

# ---------- SVG: mechanical vs functional alignment schematic ----------
def leg_axis(mode, w=250):
    # mode: 'mech' straight axis + perpendicular joint line + soft-tissue release marks
    #       'func' axis + tilted native joint line, fewer releases
    tilt = 0 if mode=='mech' else 9
    jl_color = NAVY if mode=='mech' else GOLD
    # joint line endpoints (tilted)
    import math
    cx, cy = 100, 230
    dx = 52*math.cos(math.radians(tilt)); dy = 52*math.sin(math.radians(tilt))
    x1,y1 = cx-dx, cy-dy; x2,y2 = cx+dx, cy+dy
    releases = ''
    if mode=='mech':
        releases = (f'<path d="M44 205 q-10 25 0 50" stroke="{RED}" stroke-width="3" fill="none"/>'
                    f'<path d="M156 205 q10 25 0 50" stroke="{RED}" stroke-width="3" fill="none"/>')
    return f"""<svg viewBox="0 0 200 470" width="{w}" height="{int(w*470/200)}" fill="none">
      <line x1="100" y1="20" x2="100" y2="450" stroke="{GOLD}" stroke-width="2.2" stroke-dasharray="2 8"/>
      <circle cx="100" cy="20" r="6" fill="{GOLD}"/><circle cx="100" cy="450" r="6" fill="{GOLD}"/>
      <rect x="74" y="40" width="52" height="150" rx="22" fill="none" stroke="{NAVY}" stroke-width="3"/>
      <rect x="76" y="278" width="48" height="150" rx="22" fill="none" stroke="{NAVY}" stroke-width="3"/>
      {releases}
      <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{jl_color}" stroke-width="6" stroke-linecap="round"/>
      <circle cx="100" cy="230" r="4" fill="{NAVY}"/>
    </svg>"""

# ============================================================
# 01 · COVER
add(f"""
  <div style="position:absolute;inset:0;z-index:2;pointer-events:none;">
    <span style="position:absolute;top:250px;right:70px;font-family:{FSERIF};font-size:150px;color:{NAVY};opacity:0.05;">°</span>
  </div>
  <div class="kick" style="margin-top:2px;">Lectura crítica · Artroplastia · Premio Insall 2025</div>
  <h1 class="h-md" style="margin-bottom:8px;line-height:1.08;">El «gold standard»<br>de tu rodilla, <span class="rd" style="color:{RED};">¿en duda?</span></h1>
  <div style="margin:10px 0 6px;">{knee_hero(360)}</div>
  <p class="sub" style="max-width:820px;">Alineación <b style="color:{NAVY};font-weight:700;">funcional</b> vs. <b style="color:{NAVY};font-weight:700;">mecánica</b> en prótesis de rodilla: quién ganó el titular… y qué dijo el desenlace primario.</p>
  <div style="margin-top:18px;font-family:{FSANS};font-weight:700;font-size:15px;letter-spacing:3px;text-transform:uppercase;color:{GOLD};display:flex;align-items:center;gap:12px;justify-content:center;"><span style="width:46px;height:2px;background:{GOLD};"></span>La letra pequeña<span style="font-size:20px;">→</span></div>
""", kind="cover")

# 02 · THE ARTICLE (identity card)
add(f"""
  <div class="idcard">
    <span class="corner c1"></span><span class="corner c2"></span><span class="corner c3"></span><span class="corner c4"></span>
    <div class="jr">El artículo bajo análisis · Premio John N. Insall 2025</div>
    <h2>Functional Versus Mechanical Alignment in Total Knee Arthroplasty: A Randomized Controlled Trial</h2>
    <div class="au">Young SW, Tay ML, Kawaguchi K, et&nbsp;al.</div>
    <div class="mt">The Journal of Arthroplasty · 2025;40:S20-S30 &nbsp;·&nbsp; DOI 10.1016/j.arth.2025.02.065 &nbsp;·&nbsp; PMID 40023458</div>
    <div class="rule"></div>
    <div><span class="badge"><span class="d"></span>ECA · asistido por robot</span><span class="tg">MA n=121 · FA n=123 · 2 años · unicéntrico.</span></div>
  </div>
""", kind="content")

# 03 · THE CONCEPT (mechanical vs functional)
add(f"""
  <div class="kick" style="text-align:center;width:100%;">El debate en 1 lámina</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:6px;">Dos formas de <span class="gd" style="color:{GOLD};">alinear.</span></h1>
  <div style="display:flex;justify-content:center;gap:60px;width:100%;margin-top:6px;">
    <div style="text-align:center;">{leg_axis('mech',188)}
      <div style="font-family:{FSANS};font-weight:800;font-size:20px;color:{NAVY};margin-top:6px;">Mecánica (MA)</div>
      <div style="font-family:{FBODY};font-size:20px;color:{BODY};max-width:230px;line-height:1.3;">Eje recto perfecto; se <b style="color:{RED};">liberan partes blandas</b> para encajar.</div></div>
    <div style="text-align:center;">{leg_axis('func',188)}
      <div style="font-family:{FSANS};font-weight:800;font-size:20px;color:{NAVY};margin-top:6px;">Funcional (FA)</div>
      <div style="font-family:{FBODY};font-size:20px;color:{BODY};max-width:230px;line-height:1.3;">Se respeta la <b style="color:{GOLD};">línea articular nativa</b>; menos liberaciones.</div></div>
  </div>
  <p class="tieline" style="margin-top:14px;">MA fuerza la anatomía al eje; FA adapta la prótesis al paciente. ¿Cuál rinde mejor?</p>
""", kind="content")

# 04 · THE DESIGN (epidemiologist) — primary outcome = FJS
add(f"""
  <div class="kick">El diseño · qué midieron</div>
  <h1 class="h-lg">Un ECA <span class="gd" style="color:{GOLD};">limpio…</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">244 rodillas, aleatorizadas, cirugía asistida por robot. Desenlace <b>primario</b>: el <b>Forgotten Joint Score</b> (FJS) a 2 años — cuánto «olvidas» que tienes una prótesis (0–100, más alto = mejor).</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">El <b>desenlace primario</b> es el que se declara ANTES y con el que se juzga el estudio. Todo lo demás es secundario.</div>
""", kind="statement")

# 05 · THE PRIMARY RESULT (the twist)
add(f"""
  <div class="kick" style="text-align:center;width:100%;">El desenlace primario</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:2px;">Empate técnico.</h1>
  {twocard('Mecánica (FJS)','64,4','de 100','Funcional (FJS)','70,1','de 100')}
  <div style="font-family:{FSANS};font-weight:800;font-size:30px;color:{RED};text-align:center;margin-top:20px;">P = 0,10 · sin diferencia significativa</div>
  {whyline('En el desenlace que el propio estudio eligió para juzgarse, las dos alineaciones fueron <b>estadísticamente iguales</b>. El titular «FA es mejor» NO sale de aquí.', lead='Ojo:')}
""", kind="content")

# 06 · WHERE DID "FA WINS" COME FROM?
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Entonces, ¿de dónde sale el titular?</div>
  <h1 class="h-md" style="text-align:center;width:100%;">De lo <span class="gd" style="color:{GOLD};">secundario.</span></h1>
  <div style="display:flex;justify-content:center;margin:6px 0 12px;width:100%;">{dvd(300)}</div>
  <div style="width:100%;text-align:left;max-width:920px;margin:0 auto;">
    {trow('KOOS síntomas', '86,6 vs 82,5 &nbsp;<b>(P=0,01)</b>')}
    {trow('KOOS calidad de vida', '76,1 vs 70,7 &nbsp;<b>(P=0,03)</b>')}
    {trow('«Lo recomendaría»', '94% vs 82% &nbsp;<b>(P&lt;0,01)</b>', hi=True)}
  </div>
  <p class="tieline">Reales y a favor de FA — pero son <b>secundarios</b>. Con muchas comparaciones, algunas salen «p&lt;0,05» por azar.</p>
""", kind="content")

# 07 · THE ONE ROBUST WIN — soft-tissue releases
add(f"""
  <div class="kick" style="text-align:center;width:100%;">El hallazgo que SÍ es sólido</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:2px;">Menos cortes en<br>partes <span class="gd" style="color:{GOLD};">blandas.</span></h1>
  {twocard('Mecánica','65%','liberaciones','Funcional','16%','liberaciones', l_accent=RED, r_accent=GOLD)}
  <div style="font-family:{FSANS};font-weight:800;font-size:26px;color:{NAVY};text-align:center;margin-top:16px;">P &lt; 0,001</div>
  {whyline('Efecto <b>grande</b>, <b>coherente</b> con la mecánica de FA y en la misma dirección que su hipótesis. Esta diferencia sí es creíble: FA logra el balance cortando menos tejido.', lead='Aquí sí:')}
""", kind="content")

# 08 · SIGNIFICANCE != RELEVANCE (MCID on FJS)
add(f"""
  <div class="kick">Aunque hubiera «ganado»…</div>
  <h1 class="h-lg">¿6 puntos se <span class="gd" style="color:{GOLD};">notan?</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">La diferencia de FJS fue de ~6 puntos. La <b>mínima diferencia que un paciente percibe</b> (MCID) del FJS ronda los <b>14 puntos</b>. Aunque hubiera dado significativa, quizá no la sentiría.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">Significativo ≠ importante. Pregunta siempre por la <b>MCID</b>, no solo por la «p».</div>
""", kind="statement")

# 09 · THE SUBGROUP TRAP (CPAK Type I)
add(f"""
  <div class="kick">La trampa del subgrupo</div>
  <h1 class="h-lg">El subgrupo que<br><span class="gd" style="color:{GOLD};">brilla.</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">En rodillas <b>CPAK tipo I</b>, FA sí superó a MA (FJS 71,3 vs 56,8; P=0,02). Tentador… pero es un <b>análisis de subgrupo</b> tras un primario negativo.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">Los subgrupos <b>generan hipótesis</b>, no las confirman: a más cortes de datos, más falsos positivos. Es una pista, no una prueba.</div>
""", kind="statement")

# 10 · THE EPIDEMIOLOGIST'S VERDICT
add(f"""
  <div class="kick" style="text-align:center;width:100%;">La lectura del epidemiólogo</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Sólido, pero <span class="gd" style="color:{GOLD};">leído con lupa.</span></h1>
  <div style="display:flex;justify-content:center;margin:6px 0 20px;width:100%;">{dvd(300)}</div>
  <div class="cols2">
    <div class="col"><div class="cr">
      <div class="ct" style="color:{NAVY};">Fortalezas</div>
      <div class="cs">por qué creerle</div>
      <p>ECA aleatorizado, precisión robótica.</p>
      <p>Menos liberaciones: efecto grande y consistente.</p>
    </div></div>
    <div class="col"><div class="cr">
      <div class="ct" style="color:{RED};">Límites</div>
      <div class="cs">por qué dudar</div>
      <p>Primario <b>negativo</b>; el «triunfo» es secundario/subgrupo.</p>
      <p>2 años: corto para durabilidad; unicéntrico.</p>
    </div></div>
  </div>
  <p class="tieline">Certeza <b>moderada</b>: FA no es «mejor», pero equilibra la rodilla cortando menos tejido.</p>
""", kind="content")

# 11 · APPLY — what you take to the OR
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Qué me llevo al quirófano</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Cuatro <span class="gd" style="color:{GOLD};">conclusiones.</span></h1>
  {guarda()}
  <div style="width:100%;text-align:left;max-width:940px;margin:14px auto 0;">
    {trow('1', 'FA <b>no superó</b> a MA en el desenlace que importaba (FJS a 2 años).')}
    {trow('2', 'Sí logra el balance con <b>menos liberaciones</b> de partes blandas.', hi=True)}
    {trow('3', 'El beneficio en CPAK tipo I es una <b>hipótesis</b>, no una indicación.')}
    {trow('4', 'Faltan datos de <b>durabilidad</b> (>10 años) antes de cambiar tu estándar.')}
  </div>
""", kind="content")

# 12 · CLOSE + debate
add(f"""
  <div class="kick" style="color:{GOLD};">Conclusión</div>
  <h1 class="h-lg">¿Mejor… o<br>solo <span class="gd" style="color:{GOLD};">distinto?</span></h1>
  {dvd(300)}
  <p class="sub" style="max-width:840px;">Un primario negativo con hallazgos secundarios prometedores. Ciencia honesta — pero aún no un cambio de paradigma.</p>
  <div class="qbox" style="margin-top:32px;max-width:900px;">
    <div class="qk">Para el debate</div>
    <p>Si el desenlace primario no separa, ¿adoptarías la alineación <b style="color:{GOLD};">funcional</b> por «cortar menos»… o esperarías 10 años de supervivencia?</p></div>
""", dark=True, kind="dark")

for i,(body,dark,kind) in enumerate(SL,1):
    open(f"{OUT}/slide-{i:02d}.html","w",encoding="utf-8").write(slide(i,body,dark,kind))
print("wrote", len(SL))
'''
open('/tmp/claude-0/-home-user-paperflow-ai/4f54a4a0-d991-5143-a8e1-7d66d4325c51/scratchpad/build_insall.py','w').write(prefix + content)
print("assembled build_insall.py")
