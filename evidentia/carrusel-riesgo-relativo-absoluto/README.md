# EVIDENTIA · Carrusel — Riesgo relativo vs. riesgo absoluto

Carrusel de Instagram (1080×1350, exportado 2× = 2160×2700) para **@evidentia_co**:
lectura crítica de bioestadística que enseña, con ejemplos reales citados, por qué el
**riesgo relativo** engaña y por qué el **absoluto + NNT** son los números que deciden.

Tema elegido por su alto potencial de alcance/compartido y porque demuestra el nivel de
análisis crítico de la marca. Producido con la skill `evidentia-carousel` + investigación
en vivo de tres frentes (estrategia Instagram 2026, storytelling/perfiles del nicho,
columna de evidencia en PubMed).

## Arco (11 láminas)

| # | Lámina | Función |
|---|--------|---------|
| 1 | «Reduce el riesgo un 50%». La letra pequeña: 1 de cada 100 | Portada · gancho de error + brecha de curiosidad |
| 2 | Un estudio. Dos números | Segunda portada autónoma (el algoritmo la re-sirve) |
| 3 | Dos formas de comparar (÷ vs −) | De dónde salen los dos números |
| 4 | «−50%» puede ser casi nada… o enorme | Misma RRR, NNT 100 vs NNT 5 — la prueba |
| 5 | 100 pacientes. 1 se salva | **Visual estrella**: rejilla de 100 personas |
| 6 | Número necesario a tratar (NNT = 100) | Traducción a pacientes reales |
| 7 | Alendronato y fractura de cadera | Caso real ortopédico (RRR 51% / ARR 1,1% / NNT 91) |
| 8 | Estatina en prevención primaria | Caso real clásico (RRR 31% / ARR ~2% / NNT 44) |
| 9 | El mismo dato cambia tu decisión | Efecto de encuadre + CONSORT 17b |
| 10 | Tu defensa en 4 preguntas | Chuleta · «Guárdala» |
| 11 | Exige el número absoluto | Cierre + pregunta de debate |

## Fuentes (verificadas contra la literatura primaria)

- Black DM, et al. *Alendronate and risk of fracture (FIT).* **Lancet** 1996;348:1535–41 · PMID 8950879 · DOI 10.1016/s0140-6736(96)07088-2
- Shepherd J, et al. *Prevention of CHD with pravastatin (WOSCOPS).* **NEJM** 1995;333:1301–7 · PMID 7566020 · DOI 10.1056/NEJM199511163332001
- Malenka DJ, et al. *The framing effect of relative and absolute risk.* **J Gen Intern Med** 1993;8:543–8 · PMID 8271086 · DOI 10.1007/BF02599636
- Akl EA, et al. *Alternative statistical formats for presenting risks.* **Cochrane** 2011;(3):CD006776 · PMID 21412897
- Schulz KF, Altman DG, Moher D. *CONSORT 2010*, ítem 17b (reportar efecto relativo **y** absoluto).

Nota de verificación: para FIT, el HR de cadera (0,49) está verificado en el abstract; ARR≈1,1% / NNT≈91
provienen de las tablas del texto completo (fuente docente CMAJ). Para WOSCOPS, RRR 31% y los conteos
248 vs 174 están verificados en el abstract; ARR≈2% / NNT≈44 dependen de los denominadores de grupo
(se presentan con «≈»).

## Reproducir

```bash
# 1) genera el build a partir de la skill evidentia-carousel
python3 src/assemble_riesgo.py           # escribe build_riesgo.py en scratchpad
python3 <scratchpad>/build_riesgo.py     # escribe riesgo_out/slide-01..11.html
# 2) captura con Chromium headless a 1080×1350 @2×  (ver .claude/skills/evidentia-carousel/render.sh)
```

El caption listo para publicar está en `CAPTION_INSTAGRAM.md`.
