import re
SKILL='/home/user/paperflow-ai/.claude/skills/evidentia-carousel'
src = open(f'{SKILL}/build_deck.py').read()
prefix = src.split('SL=[]')[0]
prefix = prefix.replace('OUT=_os.path.join(HERE, "out"); TOTAL=13',
                        'OUT=_os.path.join(HERE, "riesgo_out"); TOTAL=11')
prefix = re.sub(r'# ---- CONTENT IMAGES.*?LIG  = data_uri\("example_assets/anat_ligaments.png"\)\n',
                'FIG = {}\n', prefix, flags=re.S)

content = r'''
import os as _o
_o.makedirs(OUT, exist_ok=True)
SL=[]
def add(body,dark=False,kind="content"): SL.append((body,dark,kind))

# ---------- components ----------
def bignum(txt, unit="", color=None):
    color = color or NAVY
    u = f'<span style="font-size:38px;color:{MUTE};font-weight:700;">{unit}</span>' if unit else ""
    return (f'<div style="font-family:{FSANS};font-weight:800;font-size:104px;line-height:1;letter-spacing:-3px;'
            f'color:{color};margin:2px 0;">{txt}&nbsp;{u}</div>')

def miniformula(inner, label="La fórmula, para curiosos"):
    return (f'<div style="display:inline-block;margin-top:16px;background:rgba(23,41,77,0.045);border-left:3px solid {GOLD};'
            f'padding:12px 22px;text-align:left;">'
            f'<div style="font-family:{FSANS};font-size:12px;letter-spacing:2px;text-transform:uppercase;color:{MUTE};margin-bottom:5px;">{label}</div>'
            f'<div style="font-family:{FBODY};font-size:24px;color:{BODY};">{inner}</div></div>')

def whyline(txt, lead="¿Por qué?"):
    return (f'<div style="font-family:{FBODY};font-size:24px;color:{BODY};line-height:1.34;max-width:840px;'
            f'margin:14px auto 0;text-align:center;"><b style="color:{NAVY};">{lead}</b> {txt}</div>')

def trow(a, b, hi=False):
    ac = GOLD if hi else NAVY
    return (f'<div style="display:grid;grid-template-columns:0.42fr 1.58fr;gap:22px;padding:15px 0;'
            f'border-bottom:1px solid rgba(23,41,77,0.12);align-items:baseline;">'
            f'<div style="font-family:{FSANS};font-weight:800;font-size:20px;color:{ac};letter-spacing:0.3px;">{a}</div>'
            f'<div style="font-family:{FBODY};font-size:24px;color:{BODY};line-height:1.32;">{b}</div></div>')

def guarda(txt="Guárdala · te va a servir siempre"):
    return (f'<div style="display:flex;justify-content:center;align-items:center;gap:14px;margin:14px 0 0;width:100%;">'
            f'<span style="width:40px;height:2px;background:{GOLD};"></span>'
            f'<span style="font-family:{FSANS};font-weight:700;font-size:14px;letter-spacing:3px;text-transform:uppercase;color:{GOLD};">{txt}</span>'
            f'<span style="width:40px;height:2px;background:{GOLD};"></span></div>')

# 100-person icon array. events = red dots; optional 'saved' = one gold-ringed dot among the events.
def persongrid(events, total=100, cols=20, d=30, gap=11, ev=RED, saved=0):
    base='rgba(23,41,77,0.12)'
    cells=[]
    for i in range(total):
        if i < saved:
            cells.append(f'<span style="width:{d}px;height:{d}px;border-radius:50%;background:{GOLD};box-shadow:0 0 0 3px {WHITE},0 0 0 6px {GOLD};"></span>')
        elif i < events:
            cells.append(f'<span style="width:{d}px;height:{d}px;border-radius:50%;background:{ev};"></span>')
        else:
            cells.append(f'<span style="width:{d}px;height:{d}px;border-radius:50%;background:{base};"></span>')
    return (f'<div style="display:grid;grid-template-columns:repeat({cols},{d}px);gap:{gap}px;justify-content:center;margin:6px auto;">'
            + "".join(cells) + "</div>")

def legend(items):
    # items: list of (color, label)
    chips=[]
    for c,l in items:
        chips.append(f'<span style="display:inline-flex;align-items:center;gap:9px;font-family:{FSANS};font-weight:600;font-size:17px;color:{BODY};">'
                     f'<span style="width:17px;height:17px;border-radius:50%;background:{c};"></span>{l}</span>')
    return f'<div style="display:flex;justify-content:center;gap:34px;margin-top:14px;flex-wrap:wrap;">' + "".join(chips) + "</div>"

# two side-by-side comparison cards (relative vs absolute)
def twocard(l_title, l_big, l_sub, r_title, r_big, r_sub):
    def card(title, big, sub, accent):
        return (f'<div style="flex:1;border-top:3px solid {accent};padding:18px 8px 4px;text-align:center;">'
                f'<div style="font-family:{FSANS};font-weight:700;font-size:15px;letter-spacing:2px;text-transform:uppercase;color:{accent};">{title}</div>'
                f'<div style="font-family:{FSANS};font-weight:800;font-size:66px;letter-spacing:-2px;color:{NAVY};margin:8px 0 2px;">{big}</div>'
                f'<div style="font-family:{FBODY};font-size:22px;color:{BODY};line-height:1.3;">{sub}</div></div>')
    return (f'<div style="display:flex;gap:34px;width:100%;max-width:900px;margin:6px auto 0;">'
            f'{card(l_title,l_big,l_sub,RED)}{card(r_title,r_big,r_sub,NAVY)}</div>')

# ============================================================
# 01 · COVER — myth/error hook + information gap
add(f"""
  <div style="position:absolute;inset:0;z-index:2;pointer-events:none;">
    <span style="position:absolute;top:250px;left:74px;font-family:{FSERIF};font-size:150px;color:{NAVY};opacity:0.05;">%</span>
    <span style="position:absolute;bottom:250px;right:88px;font-family:{FSERIF};font-size:130px;color:{GOLD};opacity:0.12;">?</span>
  </div>
  <div class="kick" style="margin-top:4px;">Lectura crítica · Bioestadística</div>
  <h1 class="h-md" style="margin-bottom:10px;line-height:1.08;">«Reduce el riesgo<br>un <span class="rd" style="color:{RED};">50%</span>».</h1>
  <p class="sub" style="max-width:760px;margin-bottom:20px;">La letra pequeña decía otra cosa:</p>
  <div style="display:flex;align-items:center;justify-content:center;gap:26px;margin:6px 0 10px;">
    <div style="font-family:{FSANS};font-weight:800;font-size:82px;letter-spacing:-2px;color:{NAVY};">1</div>
    <div style="font-family:{FBODY};font-size:30px;color:{BODY};line-height:1.15;text-align:left;">de cada<br><b style="color:{NAVY};font-weight:700;">100</b> pacientes.</div>
  </div>
  <div style="margin-top:22px;font-family:{FSANS};font-weight:700;font-size:15px;letter-spacing:3px;text-transform:uppercase;color:{GOLD};display:flex;align-items:center;gap:12px;justify-content:center;"><span style="width:46px;height:2px;background:{GOLD};"></span>El mismo dato, dos historias<span style="font-size:20px;">→</span></div>
""", kind="cover")

# 02 · SECOND COVER (standalone) — the stakes
add(f"""
  <div class="kick">El truco más usado en medicina</div>
  <h1 class="h-lg">Un estudio.<br>Dos <span class="gd" style="color:{GOLD};">números.</span></h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">El mismo resultado puede sonar <b>espectacular</b> o <b>trivial</b> según cómo se cuente. Titulares, laboratorios y hasta papers eligen el número que impresiona: el <b>riesgo relativo</b>.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">Aprende a pedir el otro número —el <b>absoluto</b>— y nadie te volverá a vender humo estadístico.</div>
""", kind="statement")

# 03 · THE MACHINE — one 2x2 gives two comparisons
add(f"""
  <div class="kick" style="text-align:center;width:100%;">De dónde salen los dos números</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Dos formas de <span class="gd" style="color:{GOLD};">comparar.</span></h1>
  <div style="display:flex;justify-content:center;margin:10px 0 22px;width:100%;">{dvd(300)}</div>
  <div style="width:100%;text-align:left;max-width:940px;margin:0 auto;">
    {trow('Punto de partida', 'el riesgo SIN tratamiento — el <b>riesgo basal</b> (ej. 2 de cada 100).')}
    {trow('Relativo &nbsp;÷', 'una <b>división</b>: ¿qué fracción del riesgo se quitó? Suena grande.', hi=True)}
    {trow('Absoluto &nbsp;−', 'una <b>resta</b>: ¿cuántos puntos bajó de verdad? Es lo que el paciente siente.')}
  </div>
  <p class="tieline">Misma tabla, misma verdad — pero la <b>división</b> y la <b>resta</b> cuentan historias distintas.</p>
""", kind="content")

# 04 · RRR hides the baseline — same -50%, opposite benefit
add(f"""
  <div class="kick" style="text-align:center;width:100%;">El número que impresiona</div>
  <h1 class="h-md" style="text-align:center;width:100%;">«−50%» puede ser casi<br>nada… o <span class="gd" style="color:{GOLD};">enorme.</span></h1>
  <div style="display:flex;justify-content:center;margin:10px 0 10px;width:100%;">{dvd(300)}</div>
  {twocard('Basal 2% → 1%','NNT 100','misma «−50%»','Basal 40% → 20%','NNT 5','misma «−50%»')}
  <p class="tieline">Idéntico titular relativo, <b>20× más</b> beneficio real. Sin el riesgo basal, «−50%» no significa nada.</p>
""", kind="content")

# 05 · ARR + the 100-person reveal (the money visual)
add(f"""
  <div class="kick" style="text-align:center;width:100%;">El número que importa</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:6px;">100 pacientes. <span class="gd" style="color:{GOLD};">1</span> se salva.</h1>
  {persongrid(events=2, saved=1)}
  {legend([(RED,'evento que ocurre'), (GOLD,'evento evitado por el tratamiento'), ('rgba(23,41,77,0.12)','sanos')])}
  {twocard('Riesgo relativo (÷)','−50%','1 de los 2 eventos','Riesgo absoluto (−)','−1%','1 de 100 pacientes')}
  <p class="checknote" style="text-align:center;width:100%;max-width:820px;margin-top:16px;">Los dos salen del MISMO dato (2% → 1%). El relativo grita; el absoluto dice la verdad clínica.</p>
""", kind="content")

# 06 · NNT
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Tradúcelo a pacientes reales</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Número necesario a <span class="gd" style="color:{GOLD};">tratar.</span></h1>
  <div style="display:flex;justify-content:center;margin:8px 0 4px;width:100%;">{dvd(300)}</div>
  {bignum('NNT = 100')}
  {whyline('Trato a <b>100</b> pacientes para evitar <b>1</b> evento. Es 1 ÷ riesgo absoluto (1 ÷ 0,01). Cuanto más bajo el NNT, más potente el tratamiento.', lead='En cristiano:')}
  {miniformula('NNT = 1 / RAR &nbsp;·&nbsp; RAR = riesgo absoluto reducido (la resta)')}
""", kind="content")

# 07 · REAL STUDY 1 — FIT alendronate, hip fracture (orthopedic / fragility)
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Caso real 1 · Ortopedia — fractura por fragilidad</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:6px;">«Alendronato baja la fractura<br>de cadera un <span class="gd" style="color:{GOLD};">50%».</span></h1>
  {twocard('Titular (relativo)','−51%','suena enorme','La realidad (absoluto)','−1,1%','NNT ≈ 91 · 3 años')}
  <p class="checknote" style="text-align:center;width:100%;max-width:880px;margin-top:16px;">Cadera ≈ 2,2% → 1,1% (HR 0,49). Tratas ~91 mujeres de alto riesgo durante 3 años para evitar UNA fractura de cadera. &nbsp;Black DM et al., <i>Lancet</i> 1996 · PMID 8950879.</p>
""", kind="content")

# 08 · REAL STUDY 2 — WOSCOPS pravastatin (general-medicine classic)
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Caso real 2 · Prevención primaria cardiovascular</div>
  <h1 class="h-md" style="text-align:center;width:100%;margin-bottom:6px;">«La estatina baja el infarto<br>un <span class="gd" style="color:{GOLD};">31%».</span></h1>
  {twocard('Titular (relativo)','−31%','portada de revista','La realidad (absoluto)','≈ −2%','NNT ≈ 44 · 5 años')}
  <p class="checknote" style="text-align:center;width:100%;max-width:880px;margin-top:16px;">≈ 7,5% → 5,3% de eventos coronarios (248 vs 174). Tratas ~44 hombres durante 5 años para evitar UNO. &nbsp;Shepherd J et al., <i>NEJM</i> 1995 · PMID 7566020.</p>
""", kind="content")

# 09 · FRAMING EFFECT
add(f"""
  <div class="kick">Por qué esto no es inocente</div>
  <h1 class="h-lg">El mismo dato<br><span class="gd" style="color:{GOLD};">cambia</span> tu decisión.</h1>
  {dvd(300)}
  <p class="lead" style="text-align:center;max-width:880px;">Ante dos fármacos <b>igual de eficaces</b>, el <b>57%</b> eligió el descrito en términos <b>relativos</b> y solo el <b>15%</b> el <b>absoluto</b>. Y los médicos somos igual de susceptibles.</p>
  <div class="flag" style="margin-left:auto;margin-right:auto;">No es estilo: el encuadre <b>sesga la decisión</b>. Por eso CONSORT (ítem 17b) exige reportar relativo <b>y</b> absoluto — y solo ~8% de los ensayos lo cumple.</div>
""", kind="statement")

# 10 · CHEAT-SHEET (save bait)
add(f"""
  <div class="kick" style="text-align:center;width:100%;">Tu defensa en 4 preguntas</div>
  <h1 class="h-md" style="text-align:center;width:100%;">Ante todo «reduce el <span class="gd" style="color:{GOLD};">riesgo X%».</span></h1>
  {guarda()}
  <div style="width:100%;text-align:left;max-width:940px;margin:14px auto 0;">
    {trow('1 · ¿Basal?', '¿de qué riesgo partíamos? (2% no es lo mismo que 40%)')}
    {trow('2 · ¿Absoluto?', '¿cuántos puntos bajó de verdad — la resta, no la división?', hi=True)}
    {trow('3 · ¿NNT?', '¿a cuántos trato para evitar UN evento?')}
    {trow('4 · ¿A quién?', '¿en qué población? ¿mi paciente se le parece?')}
  </div>
""", kind="content")

# 11 · CLOSE + debate
add(f"""
  <div class="kick" style="color:{GOLD};">Conclusión</div>
  <h1 class="h-lg">Exige el número<br><span class="gd" style="color:{GOLD};">absoluto.</span></h1>
  {dvd(300)}
  <p class="sub" style="max-width:840px;">El riesgo relativo vende; el absoluto y el NNT deciden. Misma evidencia — pero solo uno respeta a tu paciente.</p>
  <div class="qbox" style="margin-top:34px;max-width:900px;">
    <div class="qk">Para el debate</div>
    <p>¿Cuántas decisiones tomamos con el número que <b style="color:{GOLD};">impresiona</b>… en vez del que <b style="color:{GOLD};">importa?</b></p></div>
""", dark=True, kind="dark")

for i,(body,dark,kind) in enumerate(SL,1):
    open(f"{OUT}/slide-{i:02d}.html","w",encoding="utf-8").write(slide(i,body,dark,kind))
print("wrote", len(SL))
'''
open('/tmp/claude-0/-home-user-paperflow-ai/4f54a4a0-d991-5143-a8e1-7d66d4325c51/scratchpad/build_riesgo.py','w').write(prefix + content)
print("assembled build_riesgo.py")
