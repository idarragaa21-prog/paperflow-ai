import re
SKILL='/home/user/paperflow-ai/.claude/skills/evidentia-carousel'
src = open(f'{SKILL}/build_deck.py').read()
prefix = src.split('SL=[]')[0]
prefix = prefix.replace('OUT=_os.path.join(HERE, "out"); TOTAL=13',
                        'OUT=_os.path.join(HERE, "sleep_out"); TOTAL=11')
prefix = re.sub(r'# ---- CONTENT IMAGES.*?LIG  = data_uri\("example_assets/anat_ligaments.png"\)\n',
                'FIG = {}\n', prefix, flags=re.S)

content = r'''
import os as _o, math
_o.makedirs(OUT, exist_ok=True)
SL=[]
def add(body,dark=False,kind="content"): SL.append((body,dark,kind))

def whyline(txt, lead="¿Por qué?"):
    return (f'<div style="font-family:{FBODY};font-size:24px;color:{BODY};line-height:1.35;max-width:850px;'
            f'margin:14px auto 0;text-align:center;"><b style="color:{NAVY};">{lead}</b> {txt}</div>')

def trow(a, b, hi=False):
    ac = GOLD if hi else NAVY
    return (f'<div style="display:grid;grid-template-columns:0.62fr 1.38fr;gap:22px;padding:15px 0;'
            f'border-bottom:1px solid rgba(23,41,77,0.12);align-items:baseline;">'
            f'<div style="font-family:{FSANS};font-weight:800;font-size:19px;color:{ac};letter-spacing:0.3px;">{a}</div>'
            f'<div style="font-family:{FBODY};font-size:23px;color:{BODY};line-height:1.32;">{b}</div></div>')

def twocard(l_title,l_big,l_sub,r_title,r_big,r_sub,l_accent=None,r_accent=None):
    l_accent=l_accent or RED; r_accent=r_accent or NAVY
    def card(t,b,s,a):
        return (f'<div style="flex:1;border-top:3px solid {a};padding:18px 8px 4px;text-align:center;">'
                f'<div style="font-family:{FSANS};font-weight:700;font-size:15px;letter-spacing:2px;text-transform:uppercase;color:{a};">{t}</div>'
                f'<div style="font-family:{FSANS};font-weight:800;font-size:62px;letter-spacing:-2px;color:{NAVY};margin:8px 0 2px;">{b}</div>'
                f'<div style="font-family:{FBODY};font-size:22px;color:{BODY};line-height:1.3;">{s}</div></div>')
    return (f'<div style="display:flex;gap:34px;width:100%;max-width:900px;margin:6px auto 0;">'
            f'{card(l_title,l_big,l_sub,l_accent)}{card(r_title,r_big,r_sub,r_accent)}</div>')

# clock face pointing to 10:00
def clock(R=150):
    cx=cy=160; r=120
    ticks=""
    for h in range(12):
        a=math.radians(h*30)
        x1=cx+math.sin(a)*(r-6); y1=cy-math.cos(a)*(r-6)
        x2=cx+math.sin(a)*(r-18); y2=cy-math.cos(a)*(r-18)
        ticks+=f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{NAVY}" stroke-width="3"/>'
    ah=math.radians(300)  # 10 o'clock
    hx=cx+math.sin(ah)*68; hy=cy-math.cos(ah)*68
    mx=cx; my=cy-92
    return (f'<svg viewBox="0 0 320 320" width="{R}" height="{R}">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{NAVY}" stroke-width="5"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r+14}" fill="none" stroke="{GOLD}" stroke-width="2" opacity="0.6"/>'
            f'{ticks}'
            f'<line x1="{cx}" y1="{cy}" x2="{hx:.1f}" y2="{hy:.1f}" stroke="{GOLD}" stroke-width="7" stroke-linecap="round"/>'
            f'<line x1="{cx}" y1="{cy}" x2="{mx}" y2="{my}" stroke="{NAVY}" stroke-width="5" stroke-linecap="round"/>'
            f'<circle cx="{cx}" cy="{cy}" r="8" fill="{NAVY}"/></svg>')

# U-shaped HR-by-bedtime curve (EVIDENTIA redraw of the article data)
def ucurve(W=920, H=440):
    pad_l,pad_r,pad_t,pad_b = 74,46,54,64
    x0,x1=pad_l,W-pad_r; y0,y1=H-pad_b,pad_t
    ymin,ymax=0.9,1.62
    xs=[x0+i*(x1-x0)/3 for i in range(4)]
    def Y(v): return y0-(v-ymin)/(ymax-ymin)*(y0-y1)
    hr=[1.24,1.00,1.12,1.25]; lo=[1.10,None,1.01,1.02]; hi=[1.39,None,1.25,1.52]
    labs=['antes 10pm','10–11pm','11–12pm','≥12am']
    s=[f'<svg viewBox="0 0 {W} {H}" width="{W}" style="display:block;margin:0 auto;max-width:100%;height:auto;">']
    # faint "more risk" band above HR=1
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
  <div class="kick" style="margin-top:6px;">Lectura crítica · Sueño &amp; corazón</div>
  <h1 class="h-md" style="margin-bottom:6px;line-height:1.08;">«Duérmete a las 10 pm<br>por tu <span class="rd" style="color:{RED};">corazón</span>».</h1>
  <div style="margin:14px 0 6px;">{clock(190)}</div>
  <p class="sub" style="max-width:820px;">Un titular viral de un estudio del <b style="color:{NAVY};font-weight:700;">UK Biobank</b>. ¿Ciencia… o una correlación disfrazada de consejo?</p>
  <div style="margin-top:18px;font-family:{FSANS};font-weight:700;font-size:15px;letter-spacing:3px;text-transform:uppercase;color:{GOLD};display:flex;align-items:center;gap:12px;justify-content:center;"><span style="width:46px;height:2px;background:{GOLD};"></span>Léelo como epidemiólogo<span style="font-size:20px;">→</span></div>
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
    <div><span class="badge"><span class="d"></span>Cohorte OBSERVACIONAL</span><span class="tg">UK Biobank · n = 103.712 · acelerómetro 7 días.</span></div>
  </div>
""", kind="content")

# 03 THE FINDING — U curve
add(f"""
  <div class="kick" style="text-align:center;width:100%;">El hallazgo · la curva en U</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Las 10–11 pm: el <span class="gd" style="color:{GOLD};">«punto dulce».</span></h1>
  <div style="max-width:920px;margin:8px auto 0;">{ucurve()}</div>
  <p class="tieline">Dormirse <b>antes de las 10</b> o <b>después de medianoche</b> se asoció a más enfermedad cardiovascular. El valle: 10–11 pm.</p>
  <p class="checknote" style="text-align:center;width:100%;">HR ajustados vs 10–11 pm · 103.712 personas, 3.172 casos, 5,7 años · gráfico original EVIDENTIA (datos: Nikbakhtian 2021).</p>
""", kind="content")

# 04 THE DESIGN — association not causation
add(f"""
  <div class="kick">El diseño lo cambia todo</div>
  <h1 class="h-lg">Es una cohorte:<br>mide <span class="gd" style="color:{GOLD};">asociación</span>, no causa.</h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">Nadie asignó una hora de dormir: solo <b>observaron</b> quién se acuesta cuándo y quién enferma. Una asociación puede ser real y, aun así, no significar que <b>cambiar</b> tu hora cambie tu riesgo.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;"><b>Asociación ≠ causalidad.</b> La primera pregunta ante cualquier titular de salud.</div>
""", kind="statement")

# 05 CONFOUNDING
add(f"""
  <div class="kick">Sospechoso #1 · confusión</div>
  <h1 class="h-lg">¿Y si no es la hora…<br>sino <span class="gd" style="color:{GOLD};">quién</span> duerme a esa hora?</h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">Quien se acuesta muy tarde (o muy temprano) suele diferir en muchas cosas: <b>turnos, depresión, alcohol, sedentarismo, enfermedad previa, nivel socioeconómico</b>. Eso —no la hora— podría explicar el riesgo.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">Ajustaron varios factores, pero <b>siempre</b> queda confusión residual: nunca se mide todo.</div>
""", kind="statement")

# 06 REVERSE CAUSALITY
add(f"""
  <div class="kick">Sospechoso #2 · causalidad inversa</div>
  <h1 class="h-lg">¿La hora daña el corazón…<br>o el corazón <span class="gd" style="color:{GOLD};">cambia</span> la hora?</h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">Una enfermedad aún <b>no diagnosticada</b> puede alterar el sueño. Y aquí el sueño se midió <b>una sola semana</b>, al inicio — no durante los 5,7 años de seguimiento.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">En un observacional, la flecha causal puede ir <b>al revés</b>.</div>
""", kind="statement")

# 07 NUMBERS IN PERSPECTIVE
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Pon el número en perspectiva</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Modesto, y con el IC <span class="gd" style="color:{GOLD};">rozando el 1.</span></h1>
  <div style="display:flex;justify-content:center;margin:8px 0 6px;width:100%;">{dvd(300)}</div>
  <div style="width:100%;text-align:left;max-width:900px;margin:0 auto;">
    {trow('Antes de 10 pm', 'HR 1,24 &nbsp;(IC 1,10–1,39) &nbsp;· p&lt;0,005', hi=True)}
    {trow('11 – 12 pm', 'HR 1,12 &nbsp;(IC 1,01–1,25) &nbsp;· p=0,04')}
    {trow('≥ 12 am', 'HR 1,25 &nbsp;(IC 1,02–1,52) &nbsp;· p=0,03')}
  </div>
  {whyline('Dos de los tres IC casi <b>tocan el 1</b>. Y en absoluto: solo ~3 de cada 100 desarrollaron ECV en 5,7 años. Señal modesta.', lead='Léelo así:')}
""", kind="content")

# 08 CONFLICT OF INTEREST
add(f"""
  <div class="kick">Sospechoso #3 · ¿quién lo firma?</div>
  <h1 class="h-lg">Casi todos los autores<br>venden <span class="gd" style="color:{GOLD};">wearables.</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">La mayoría son de <b>Huma Therapeutics</b>, una empresa de salud digital. ¿Su conclusión? Que los relojes «pueden servir como <b>indicador de riesgo cardiovascular</b>».</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">No invalida el dato — pero el <b>encuadre comercial</b> pide leerlo con más cautela. Revisa siempre conflictos y financiación.</div>
""", kind="statement")

# 09 SEX SUBGROUP
add(f"""
  <div class="kick">El matiz del subgrupo</div>
  <h1 class="h-lg">Más fuerte en <span class="gd" style="color:{GOLD};">mujeres.</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">La asociación fue clara en mujeres; en hombres solo «antes de las 10» alcanzó significación. Interesante — pero es un <b>análisis de subgrupo</b>: hipótesis a confirmar, no conclusión.</p>
""", kind="statement")

# 10 APPLY / VERDICT
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Qué me llevo</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Interesante, no una <span class="gd" style="color:{GOLD};">receta.</span></h1>
  <div style="display:flex;justify-content:center;margin:8px 0 6px;width:100%;">{dvd(300)}</div>
  <div style="width:100%;text-align:left;max-width:940px;margin:0 auto;">
    {trow('1', 'Es una <b>asociación observacional</b>: no prueba que mover tu hora mueva tu riesgo.')}
    {trow('2', 'Dormir <b>regular y suficiente</b> sí tiene evidencia; la hora exacta, mucho menos.')}
    {trow('3', 'Confusión + causalidad inversa + conflicto de interés: tres frenos al titular «causa».')}
    {trow('4', 'Útil como <b>hipótesis</b> y demo de wearables — no como consejo médico.', hi=True)}
  </div>
""", kind="content")

# 11 CLOSE
add(f"""
  <div class="kick" style="color:{GOLD};">Conclusión</div>
  <h1 class="h-lg">¿Causa… o<br><span class="gd" style="color:{GOLD};">costumbre?</span></h1>
  {dvd(300)}
  <p class="sub" style="max-width:840px;">Un dato llamativo del UK Biobank — pero el titular corrió más rápido que la evidencia.</p>
  <div class="qbox" style="margin-top:32px;max-width:900px;">
    <div class="qk">Para el debate</div>
    <p>¿Cuántos «consejos de salud» virales son, en realidad, estudios <b style="color:{GOLD};">observacionales</b> disfrazados de causa?</p></div>
""", dark=True, kind="dark")

for i,(body,dark,kind) in enumerate(SL,1):
    open(f"{OUT}/slide-{i:02d}.html","w",encoding="utf-8").write(slide(i,body,dark,kind))
print("wrote", len(SL))
'''
open('/tmp/claude-0/-home-user-paperflow-ai/4f54a4a0-d991-5143-a8e1-7d66d4325c51/scratchpad/build_sleep.py','w').write(prefix + content)
print("assembled build_sleep.py")
