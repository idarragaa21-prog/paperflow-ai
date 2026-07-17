# EVIDENTIA · Carrusel — Hora de dormir y enfermedad cardiovascular (UK Biobank)

Carrusel de Instagram (1080×1350 → 2160×2700) de lectura crítica sobre un estudio
**observacional** muy compartido. Enseña el pilar de la epidemiología observacional:
**asociación ≠ causalidad**, más confusión, causalidad inversa y conflicto de interés.

## El artículo

Según PubMed — Nikbakhtian S, Reed AB, Obika BD, Morelli D, Cunningham AC, Aral M, Plans D.
*Accelerometer-derived sleep onset timing and cardiovascular disease incidence: a UK Biobank
cohort study.* **European Heart Journal – Digital Health** 2021;2(4):658–666.
DOI 10.1093/ehjdh/ztab088 · PMID 36713092 · PMC9708010.

Datos clave (cohorte, UK Biobank, acelerómetro de muñeca 7 días):
- **n = 103.712**; **3.172** casos de ECV en **5,7 años** (media) de seguimiento.
- Referencia (menor incidencia): **sueño 10:00–10:59 pm**.
- HR ajustados (sueño, irregularidad y factores de riesgo clásicos) vs 10–11 pm:
  - **< 10 pm:** HR **1,24** (IC 1,10–1,39; p<0,005)
  - **11:00–11:59 pm:** HR **1,12** (IC 1,01–1,25; p=0,04)
  - **≥ 12 am:** HR **1,25** (IC 1,02–1,52; p=0,03)
- Asociación **más fuerte en mujeres**; en hombres solo «<10 pm» significativo.

## Arco (11 láminas)

1 Portada (hook «duérmete a las 10 pm por tu corazón») · 2 Ficha del artículo ·
3 **La curva en U** (HR por hora de dormir, redibujo original) · 4 El diseño: cohorte → asociación, no causa ·
5 Confusión (sospechoso #1) · 6 Causalidad inversa (sospechoso #2) · 7 Los HR en perspectiva (IC rozando el 1) ·
8 Conflicto de interés (autores de Huma Therapeutics, wearables) · 9 Subgrupo por sexo ·
10 Qué me llevo (4 conclusiones) · 11 Cierre + pregunta de debate.

**Nota sobre figuras:** la curva en U (lámina 3) es un **redibujo original de EVIDENTIA a partir de
los HR publicados**; no se reproduce ninguna figura con copyright del artículo.

## Reproducir
```bash
python3 src/assemble_sleep.py   # escribe build_sleep.py en scratchpad
python3 <scratchpad>/build_sleep.py
# render con Chromium headless 1080×1350 @2× (ver .claude/skills/evidentia-carousel/render.sh)
```
Caption listo en `CAPTION_INSTAGRAM.md`.
