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

# ---------- SVG: forest plot / confidence-interval chart ----------
def _fx(v, xmin, xmax, x0, x1):
    return x0 + (v - xmin) / (xmax - xmin) * (x1 - x0)

def forest(rows, xmin, xmax, mcid=None, w=940, rowh=150, pad_l=310, pad_r=60, pad_t=92, pad_b=86, tick=5):
    x0, x1 = pad_l, w - pad_r
    H = pad_t + rowh * len(rows) + pad_b
    axis_y = H - pad_b
    def X(v): return _fx(v, xmin, xmax, x0, x1)
    s = [f'<svg viewBox="0 0 {w} {H}" width="{w}" style="display:block;margin:0 auto;max-width:100%;height:auto;">']
    s.append(f'<line x1="{x0}" y1="{axis_y}" x2="{x1}" y2="{axis_y}" stroke="{NAVY}" stroke-width="2"/>')
    t = xmin
    while t <= xmax + 0.001:
        tx = X(t); lab = '0' if abs(t) < 0.01 else f'{int(t):+d}'
        s.append(f'<line x1="{tx:.1f}" y1="{axis_y}" x2="{tx:.1f}" y2="{axis_y+7}" stroke="{NAVY}" stroke-width="1.4"/>')
        s.append(f'<text x="{tx:.1f}" y="{axis_y+31}" font-family="{FSANS}" font-size="17" fill="{MUTE}" text-anchor="middle">{lab}</text>')
        t += tick
    nx = X(0)
    if mcid is not None:
        mx = X(mcid)
        s.append(f'<rect x="{nx:.1f}" y="{pad_t-2:.1f}" width="{mx-nx:.1f}" height="{axis_y-pad_t+2:.1f}" fill="{GOLD}" opacity="0.08"/>')
        s.append(f'<line x1="{mx:.1f}" y1="{pad_t-4:.1f}" x2="{mx:.1f}" y2="{axis_y}" stroke="{GOLD}" stroke-width="2.2" stroke-dasharray="3 5"/>')
        s.append(f'<text x="{mx:.1f}" y="{pad_t-14:.1f}" font-family="{FSANS}" font-size="15" font-weight="700" fill="#8A6D2A" text-anchor="middle">MCID · se percibe</text>')
    s.append(f'<line x1="{nx:.1f}" y1="{pad_t-4:.1f}" x2="{nx:.1f}" y2="{axis_y}" stroke="{RED}" stroke-width="2.2" stroke-dasharray="5 5"/>')
    s.append(f'<text x="{nx:.1f}" y="{pad_t-14:.1f}" font-family="{FSANS}" font-size="15" font-weight="700" fill="{RED}" text-anchor="middle">0 · sin diferencia</text>')
    for i, r in enumerate(rows):
        label, lo, pt, hi, crosses = r
        cy = pad_t + rowh * i + rowh/2
        col = RED if crosses else NAVY
        s.append(f'<text x="{x0-24}" y="{cy-3:.1f}" font-family="{FSANS}" font-size="21" font-weight="800" fill="{NAVY}" text-anchor="end">{label}</text>')
        s.append(f'<text x="{x0-24}" y="{cy+23:.1f}" font-family="{FSANS}" font-size="15" fill="{MUTE}" text-anchor="end">IC95% {lo:+.1f} a {hi:+.1f}</text>')
        s.append(f'<line x1="{X(lo):.1f}" y1="{cy:.1f}" x2="{X(hi):.1f}" y2="{cy:.1f}" stroke="{col}" stroke-width="4"/>')
        for xv in (lo, hi):
            s.append(f'<line x1="{X(xv):.1f}" y1="{cy-11:.1f}" x2="{X(xv):.1f}" y2="{cy+11:.1f}" stroke="{col}" stroke-width="3.4"/>')
        s.append(f'<circle cx="{X(pt):.1f}" cy="{cy:.1f}" r="10" fill="{col}"/>')
    s.append('</svg>')
    return "".join(s)

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

# 06 · THE PRIMARY CONFIDENCE INTERVAL (la p no basta)
add(f"""
  <div class="kick" style="text-align:center;width:100%;">La «p» no basta · mira el intervalo</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:4px;">¿Cuánto mejor, <span class="gd" style="color:{GOLD};">de verdad?</span></h1>
  <div style="max-width:900px;margin:8px auto 0;">{forest([("FJS · func. vs mec.", -1.3, 5.7, 12.7, True)], -4, 18, mcid=14)}</div>
  {whyline('La diferencia fue <b>+5,7</b> puntos, pero su intervalo <b>cruza el 0</b> (podría no existir) y <b>todo</b> queda por debajo de la MCID (~14): ni en su mejor caso el paciente lo notaría.', lead='Léelo así:')}
  <p class="checknote" style="text-align:center;width:100%;max-width:840px;">IC 95% reconstruido de las medias y DE publicadas (aprox.).</p>
""", kind="content")

# 07 · FOREST PLOT — all outcomes with their CIs
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Todos los desenlaces, con su intervalo</div>
  <h1 class="h-md" style="text-align:center;width:100%;">El <span class="gd" style="color:{GOLD};">bosque</span> de intervalos.</h1>
  <div style="max-width:930px;margin:10px auto 0;">{forest([("FJS · primario", -1.3, 5.7, 12.7, True), ("KOOS síntomas", 0.7, 4.1, 7.5, False), ("KOOS calidad vida", 0.0, 5.4, 10.8, False)], -4, 14)}</div>
  <p class="tieline">Solo el <b>primario</b> (FJS) cruza el 0. Los secundarios lo excluyen <b>por poco</b> — y sin ajustar por comparaciones múltiples.</p>
  <p class="checknote" style="text-align:center;width:100%;">IC 95% reconstruidos (aprox.) · escalas 0–100 · a favor de FA →</p>
""", kind="content")

# 07 · THE ONE ROBUST WIN — soft-tissue releases
add(f"""
  <div class="kick" style="text-align:center;width:100%;">El hallazgo que SÍ es sólido</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:2px;">Menos cortes en<br>partes <span class="gd" style="color:{GOLD};">blandas.</span></h1>
  {twocard('Mecánica','65%','liberaciones','Funcional','16%','liberaciones', l_accent=RED, r_accent=GOLD)}
  <div style="font-family:{FSANS};font-weight:800;font-size:26px;color:{NAVY};text-align:center;margin-top:16px;">P &lt; 0,001</div>
  {whyline('Diferencia absoluta <b>49%</b> (IC95% ≈ 38–60%): <b>lejos del 0</b>, grande y coherente con la mecánica de FA. Esta sí es creíble: FA equilibra la rodilla cortando menos tejido.', lead='Aquí sí:')}
""", kind="content")

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
  <div class="kick" style="text-align:center;width:100%;">Cómo lo leo yo · epidemiólogo + cirujano</div>
  <h1 class="h-md" style="text-align:center;width:100%;">La lupa: 5 preguntas <span class="gd" style="color:{GOLD};">duras.</span></h1>
  <div style="display:flex;justify-content:center;margin:6px 0 14px;width:100%;">{dvd(300)}</div>
  <div style="width:100%;text-align:left;max-width:948px;margin:0 auto;">
    {trow('¿Cegamiento?', 'los «triunfos» son PROMs <b>subjetivos</b>: cabe sesgo de expectativa.', hi=True)}
    {trow('¿Poder?', '«no significativo» ≠ «igual»: el IC no descarta un beneficio pequeño (error β).')}
    {trow('¿Subgrupo?', 'CPAK tipo I: si es <b>post-hoc</b>, genera hipótesis — no las prueba.')}
    {trow('¿Desenlace duro?', 'FJS/KOOS a 2 años son <b>subrogados</b>; falta revisión y supervivencia.')}
    {trow('¿Financiación?', 'cirugía robótica: revisa <b>patrocinio y conflictos</b> de interés.')}
  </div>
  <p class="tieline">Buen ECA — pero el titular exige más prueba que la que da. Certeza <b>moderada</b> (GRADE).</p>
""", kind="content")

# 11 · APPLY — what you take to the OR
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Qué me llevo al quirófano</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Cuatro <span class="gd" style="color:{GOLD};">conclusiones.</span></h1>
  {guarda()}
  <div style="width:100%;text-align:left;max-width:940px;margin:14px auto 0;">
    {trow('1', 'Mira el <b>IC 95%</b>, no solo la «p»: el del FJS cruza el 0 y queda bajo la MCID.')}
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
