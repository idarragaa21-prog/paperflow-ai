import re
SKILL='/home/user/paperflow-ai/.claude/skills/evidentia-carousel'
src = open(f'{SKILL}/build_deck.py').read()
prefix = src.split('SL=[]')[0]
prefix = prefix.replace('OUT=_os.path.join(HERE, "out"); TOTAL=13',
                        'OUT=_os.path.join(HERE, "sleep_out"); TOTAL=12')
prefix = re.sub(r'# ---- CONTENT IMAGES.*?LIG  = data_uri\("example_assets/anat_ligaments.png"\)\n',
                'FIG = {}\n', prefix, flags=re.S)

content = r'''
import os as _o, math
_o.makedirs(OUT, exist_ok=True)
SL=[]
def add(body,dark=False,kind="content"): SL.append((body,dark,kind))

def whyline(txt, lead="¿Por qué?"):
    return (f'<div style="font-family:{FBODY};font-size:24px;color:{BODY};line-height:1.35;max-width:860px;'
            f'margin:14px auto 0;text-align:center;"><b style="color:{NAVY};">{lead}</b> {txt}</div>')

def trow(a, b, hi=False):
    ac = GOLD if hi else NAVY
    return (f'<div style="display:grid;grid-template-columns:0.55fr 1.45fr;gap:22px;padding:14px 0;'
            f'border-bottom:1px solid rgba(23,41,77,0.12);align-items:baseline;">'
            f'<div style="font-family:{FSANS};font-weight:800;font-size:18px;color:{ac};letter-spacing:0.2px;">{a}</div>'
            f'<div style="font-family:{FBODY};font-size:22px;color:{BODY};line-height:1.32;">{b}</div></div>')

def clock(R=150):
    cx=cy=160; r=120; ticks=""
    for h in range(12):
        a=math.radians(h*30)
        x1=cx+math.sin(a)*(r-6); y1=cy-math.cos(a)*(r-6)
        x2=cx+math.sin(a)*(r-18); y2=cy-math.cos(a)*(r-18)
        ticks+=f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{NAVY}" stroke-width="3"/>'
    ah=math.radians(300); hx=cx+math.sin(ah)*68; hy=cy-math.cos(ah)*68; mx=cx; my=cy-92
    return (f'<svg viewBox="0 0 320 320" width="{R}" height="{R}">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{NAVY}" stroke-width="5"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r+14}" fill="none" stroke="{GOLD}" stroke-width="2" opacity="0.6"/>{ticks}'
            f'<line x1="{cx}" y1="{cy}" x2="{hx:.1f}" y2="{hy:.1f}" stroke="{GOLD}" stroke-width="7" stroke-linecap="round"/>'
            f'<line x1="{cx}" y1="{cy}" x2="{mx}" y2="{my}" stroke="{NAVY}" stroke-width="5" stroke-linecap="round"/>'
            f'<circle cx="{cx}" cy="{cy}" r="8" fill="{NAVY}"/></svg>')

def ucurve(W=920, H=440):
    pad_l,pad_r,pad_t,pad_b = 74,46,54,64
    x0,x1=pad_l,W-pad_r; y0,y1=H-pad_b,pad_t
    ymin,ymax=0.9,1.62
    xs=[x0+i*(x1-x0)/3 for i in range(4)]
    def Y(v): return y0-(v-ymin)/(ymax-ymin)*(y0-y1)
    hr=[1.24,1.00,1.12,1.25]; lo=[1.10,None,1.01,1.02]; hi=[1.39,None,1.25,1.52]
    labs=['antes 10pm','10–11pm','11–12pm','≥12am']
    s=[f'<svg viewBox="0 0 {W} {H}" width="{W}" style="display:block;margin:0 auto;max-width:100%;height:auto;">']
    s.append(f'<rect x="{x0}" y="{y1}" width="{x1-x0}" height="{Y(1.0)-y1:.1f}" fill="{RED}" opacity="0.05"/>')
    for v in [1.0,1.2,1.4,1.6]:
        yy=Y(v)
        s.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="{NAVY}" stroke-width="1" opacity="0.10"/>')
        s.append(f'<text x="{x0-12}" y="{yy+5:.1f}" font-family="{FSANS}" font-size="17" fill="{MUTE}" text-anchor="end">{("%.1f"%v).replace(".",",")}</text>')
    yref=Y(1.0)
    s.append(f'<line x1="{x0}" y1="{yref:.1f}" x2="{x1}" y2="{yref:.1f}" stroke="{MUTE}" stroke-width="2" stroke-dasharray="6 5"/>')
    s.append(f'<text x="{x1}" y="{yref+24:.1f}" font-family="{FSANS}" font-size="15" font-weight="700" fill="{MUTE}" text-anchor="end">HR 1,0 · referencia</text>')
    pts=" ".join(f"{xs[i]:.1f},{Y(hr[i]):.1f}" for i in range(4))
    s.append(f'<polyline points="{pts}" fill="none" stroke="{NAVY}" stroke-width="3" opacity="0.5"/>')
    for i in range(4):
        col = GOLD if i==1 else NAVY
        if lo[i] is not None:
            s.append(f'<line x1="{xs[i]:.1f}" y1="{Y(lo[i]):.1f}" x2="{xs[i]:.1f}" y2="{Y(hi[i]):.1f}" stroke="{NAVY}" stroke-width="3"/>')
            for vv in (lo[i],hi[i]):
                s.append(f'<line x1="{xs[i]-8:.1f}" y1="{Y(vv):.1f}" x2="{xs[i]+8:.1f}" y2="{Y(vv):.1f}" stroke="{NAVY}" stroke-width="3"/>')
        rr = 13 if i==1 else 9
        s.append(f'<circle cx="{xs[i]:.1f}" cy="{Y(hr[i]):.1f}" r="{rr}" fill="{col}"/>')
        lab = 'valle' if i==1 else ("%.2f"%hr[i]).replace(".",",")
        ytop = Y(hi[i]) if lo[i] is not None else Y(hr[i])
        s.append(f'<text x="{xs[i]:.1f}" y="{ytop-14:.1f}" font-family="{FSANS}" font-size="18" font-weight="800" fill="{col}" text-anchor="middle">{lab}</text>')
    s.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="{NAVY}" stroke-width="1.8"/>')
    for i in range(4):
        s.append(f'<text x="{xs[i]:.1f}" y="{y0+30:.1f}" font-family="{FSANS}" font-size="17" font-weight="700" fill="{BODY}" text-anchor="middle">{labs[i]}</text>')
    s.append('</svg>')
    return "".join(s)

# ============================================================
# 01 COVER
add(f"""
  <div class="kick" style="margin-top:6px;">Lectura crítica · qué dice el estudio</div>
  <h1 class="h-md" style="margin-bottom:6px;line-height:1.08;">«Duérmete a las 10 pm<br>por tu <span class="rd" style="color:{RED};">corazón</span>».</h1>
  <div style="margin:14px 0 6px;">{clock(184)}</div>
  <p class="sub" style="max-width:840px;">El titular salió de este estudio del <b style="color:{NAVY};font-weight:700;">UK Biobank</b>. Veamos qué dice —y qué <b>no</b>— el propio artículo.</p>
  <div style="margin-top:18px;font-family:{FSANS};font-weight:700;font-size:15px;letter-spacing:3px;text-transform:uppercase;color:{GOLD};display:flex;align-items:center;gap:12px;justify-content:center;"><span style="width:46px;height:2px;background:{GOLD};"></span>Método y resultados<span style="font-size:20px;">→</span></div>
""", kind="cover")

# 02 ARTICLE CARD
add(f"""
  <div class="idcard">
    <span class="corner c1"></span><span class="corner c2"></span><span class="corner c3"></span><span class="corner c4"></span>
    <div class="jr">El artículo bajo análisis · Open Access</div>
    <h2>Accelerometer-derived sleep onset timing and cardiovascular disease incidence: a UK Biobank cohort study</h2>
    <div class="au">Nikbakhtian S, Reed AB, Obika BD, Morelli D, Cunningham AC, Aral M, Plans D.</div>
    <div class="mt">Eur Heart J Digital Health · 2021;2(4):658–666 &nbsp;·&nbsp; DOI 10.1093/ehjdh/ztab088 &nbsp;·&nbsp; PMID 36713092</div>
    <div class="rule"></div>
    <div><span class="badge"><span class="d"></span>Cohorte prospectiva</span><span class="tg">UK Biobank · 88.026 analizados (de 103.712 con acelerómetro).</span></div>
  </div>
""", kind="content")

# 03 METHOD — exposure
add(f"""
  <div class="kick">El método · cómo midieron el sueño</div>
  <h1 class="h-lg">Un acelerómetro,<br><span class="gd" style="color:{GOLD};">7 días.</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">Acelerómetro de muñeca (Axivity AX3) durante <b>7 días</b>. La «hora de dormir» se definió como el punto medio del mayor periodo sin movimiento, calculado con el algoritmo GGIR / HDCZA.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">Medición <b>objetiva</b> (no cuestionario): una fortaleza real del estudio. El propio artículo advierte que 7 días no equivalen al hábito de años.</div>
""", kind="statement")

# 04 METHOD — outcome & model
add(f"""
  <div class="kick" style="text-align:center;width:100%;">El método · desenlace y modelo</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Qué contaron y cómo lo <span class="gd" style="color:{GOLD};">ajustaron.</span></h1>
  <div style="display:flex;justify-content:center;margin:8px 0 6px;width:100%;">{dvd(300)}</div>
  <div style="width:100%;text-align:left;max-width:940px;margin:0 auto;">
    {trow('Desenlace', 'ECV incidente: infarto, insuficiencia cardiaca, cardiopatía isquémica, ictus y AIT. <b>No</b> incluye muertes cardiovasculares.')}
    {trow('Análisis', 'Riesgos proporcionales de Cox. Referencia = dormir 10–11 pm.')}
    {trow('Modelo 2', 'ajusta por duración e irregularidad del sueño + IMC, diabetes, HTA, tabaco, colesterol, cronotipo, privación social y presión arterial.', hi=True)}
  </div>
  <p class="tieline">3.172 casos de ECV en un seguimiento medio de 5,7 años.</p>
""", kind="content")

# 05 THE FINDING — U curve
add(f"""
  <div class="kick" style="text-align:center;width:100%;">El resultado · la curva en U</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Menor incidencia entre las <span class="gd" style="color:{GOLD};">10 y 11 pm.</span></h1>
  <div style="max-width:920px;margin:6px auto 0;">{ucurve()}</div>
  <p class="tieline">El estudio reporta una relación en <b>U</b>: dormirse antes de las 10 o después de medianoche se asoció a más ECV.</p>
  <p class="checknote" style="text-align:center;width:100%;">HR del Modelo 2 (totalmente ajustado) vs 10–11 pm · redibujo EVIDENTIA de los datos (Nikbakhtian 2021).</p>
""", kind="content")

# 06 CONFOUNDING (neutral, anchored)
add(f"""
  <div class="kick">¿Qué ajustaron… y qué no?</div>
  <h1 class="h-lg">El ajuste llega hasta<br>donde llegan los <span class="gd" style="color:{GOLD};">datos.</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">La asociación <b>persistió</b> tras ajustar por duración e irregularidad del sueño y los factores de riesgo clásicos. Pero un modelo solo controla lo que se mide — y los autores señalan que <b>no pudieron incluir antecedentes familiares</b>.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">En un estudio observacional, siempre puede quedar <b>confusión residual</b> por lo no medido.</div>
""", kind="statement")

# 07 REVERSE CAUSALITY (credit their sensitivity analysis)
add(f"""
  <div class="kick">Causalidad inversa · lo que hicieron</div>
  <h1 class="h-lg">¿Y si la enfermedad<br>cambia el <span class="gd" style="color:{GOLD};">sueño?</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">Para descartar que una ECV aún no diagnosticada alterara el sueño, los autores <b>repitieron el análisis excluyendo los primeros 12–18 meses</b> de seguimiento. La asociación se mantuvo.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">Un control razonable — aunque medir el sueño <b>una sola semana</b> sigue siendo una limitación del diseño.</div>
""", kind="statement")

# 08 NUMBERS IN PERSPECTIVE
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Los números, en perspectiva</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Modesto, y con el IC <span class="gd" style="color:{GOLD};">cerca del 1.</span></h1>
  <div style="display:flex;justify-content:center;margin:8px 0 6px;width:100%;">{dvd(300)}</div>
  <div style="width:100%;text-align:left;max-width:900px;margin:0 auto;">
    {trow('Antes de 10 pm', 'HR 1,24 &nbsp;(IC 1,10–1,39) · p&lt;0,005', hi=True)}
    {trow('11 – 12 pm', 'HR 1,12 &nbsp;(IC 1,01–1,25) · p=0,04')}
    {trow('≥ 12 am', 'HR 1,25 &nbsp;(IC 1,02–1,52) · p=0,03')}
  </div>
  {whyline('Dos de los tres IC casi tocan el 1. En incidencia: 2,78 (10–11 pm) frente a 4,29 (≥12 am) por 100 personas-año; 3,58% en 5,7 años.', lead='En contexto:')}
""", kind="content")

# 09 SEX SUBGROUP (pre-planned sensitivity)
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Análisis por sexo · sensibilidad</div>
  <h1 class="h-md" style="text-align:center;width:100%;">La asociación fue mayor en <span class="gd" style="color:{GOLD};">mujeres.</span></h1>
  <div style="display:flex;justify-content:center;margin:8px 0 6px;width:100%;">{dvd(300)}</div>
  <div style="width:100%;text-align:left;max-width:920px;margin:0 auto;">
    {trow('Mujeres', 'ECV: ≥12 am HR 1,63 (1,20–2,21); &lt;10 pm HR 1,34 (1,11–1,61).', hi=True)}
    {trow('Hombres', 'solo &lt;10 pm alcanzó significación: HR 1,17 (1,01–1,35).')}
  </div>
  <p class="tieline">Análisis estratificado por sexo (Modelo 2). Un patrón interesante — a confirmar en otras poblaciones.</p>
""", kind="content")

# 10 THE ARTICLE'S OWN LIMITATIONS
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Lo que reconoce el propio estudio</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Sus límites, en sus <span class="gd" style="color:{GOLD};">palabras.</span></h1>
  <div style="display:flex;justify-content:center;margin:8px 0 6px;width:100%;">{dvd(300)}</div>
  <div style="width:100%;text-align:left;max-width:940px;margin:0 auto;">
    {trow('Población', 'UK Biobank es «más sana y acomodada» (mayormente británica blanca): puede no generalizar.')}
    {trow('Grupo &lt;10 pm', 'pequeño → los autores dicen que «debilita» la conclusión de la curva en U.', hi=True)}
    {trow('Medición', '7 días no representan el hábito; sin antecedentes familiares; actigrafía imperfecta (c=0,83).')}
  </div>
""", kind="content")

# 11 FUNDING / COI + authors' own conclusion
add(f"""
  <div class="kick">Financiación y conflicto · declarado</div>
  <h1 class="h-lg">Quién lo financia<br>(y qué <span class="gd" style="color:{GOLD};">concluyen).</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">Financiado por <b>Huma Therapeutics</b>; los 7 autores son empleados de Huma. El artículo declara que el financiador <b>no participó</b> en el análisis ni en la redacción.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">Los propios autores concluyen que los hallazgos <b>«no muestran causalidad»</b> y «sugieren la posibilidad» de una relación; los wearables «podrían servir» como indicador de riesgo.</div>
""", kind="statement")

# 12 CLOSE
add(f"""
  <div class="kick" style="color:{GOLD};">Conclusión</div>
  <h1 class="h-lg">Asociación sólida.<br>Causa, <span class="gd" style="color:{GOLD};">no probada.</span></h1>
  {dvd(300)}
  <p class="sub" style="max-width:850px;">Resistió el ajuste y los análisis de sensibilidad — pero es observacional. Genera hipótesis; los propios autores piden más investigación.</p>
  <div class="qbox" style="margin-top:30px;max-width:900px;">
    <div class="qk">Para el debate</div>
    <p>¿Cómo distingues una asociación que <b style="color:{GOLD};">resiste el ajuste</b>… de una recomendación <b style="color:{GOLD};">causal?</b></p></div>
""", dark=True, kind="dark")

for i,(body,dark,kind) in enumerate(SL,1):
    open(f"{OUT}/slide-{i:02d}.html","w",encoding="utf-8").write(slide(i,body,dark,kind))
print("wrote", len(SL))
'''
open('/tmp/claude-0/-home-user-paperflow-ai/4f54a4a0-d991-5143-a8e1-7d66d4325c51/scratchpad/build_sleep.py','w').write(prefix + content)
print("assembled neutral article-anchored build_sleep.py")
