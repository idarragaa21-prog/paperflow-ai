# EVIDENTIA · Carrusel — Hora de dormir y enfermedad cardiovascular (UK Biobank)

Carrusel de Instagram (1080×1350 → 2160×2700): **análisis del artículo** (voz neutra de
revisor), no opinión. Describe qué hizo el estudio, qué encontró y **qué reconoce el propio
artículo** en sus limitaciones y declaración de conflicto. Basado en el **texto completo**
(open access, PMC9708010).

## El artículo

Según PubMed — Nikbakhtian S, Reed AB, Obika BD, Morelli D, Cunningham AC, Aral M, Plans D.
*Accelerometer-derived sleep onset timing and cardiovascular disease incidence: a UK Biobank
cohort study.* **European Heart Journal – Digital Health** 2021;2(4):658–666.
DOI 10.1093/ehjdh/ztab088 · PMID 36713092 · PMC9708010.

Datos clave (cohorte prospectiva, UK Biobank, acelerómetro de muñeca 7 días):
- **88.026 analizados** (de 103.712 con acelerómetro; tras excluir datos de baja calidad,
  covariables faltantes y ECV/insomnio/apnea previos). **3.172** casos de ECV en **5,7 años** (media).
- Desenlace: ECV incidente (IAM, IC, cardiopatía isquémica, ictus, AIT; sin muertes CV).
- Modelo 2 (totalmente ajustado) vs 10–11 pm: **<10 pm** HR 1,24 (1,10–1,39); **11–12 pm** HR 1,12 (1,01–1,25);
  **≥12 am** HR 1,25 (1,02–1,52). Incidencia: 2,78 (10–11 pm) vs 4,29 (≥12 am) por 100 personas-año.
- Sensibilidad por sexo: mujeres ≥12 am HR 1,63 (1,20–2,21), <10 pm 1,34; hombres solo <10 pm 1,17.
- Los autores excluyeron los primeros 12–18 meses (causalidad inversa) → asociación persistió.
- COI declarado: financiado por Huma Therapeutics; 7 autores empleados de Huma; funder «sin rol».

## Arco (12 láminas · voz neutra, anclada al artículo)

1 Portada · 2 Ficha del artículo · 3 Método: cómo midieron el sueño (acelerómetro 7 d, GGIR) ·
4 Método: desenlace y modelo de ajuste · 5 **La curva en U** (HR Modelo 2, redibujo original) ·
6 Qué ajustaron / qué no (confusión residual; sin antecedentes familiares) ·
7 Causalidad inversa: el análisis de sensibilidad que hicieron · 8 Los HR en perspectiva (IC cerca del 1) ·
9 Análisis por sexo · 10 **Las limitaciones que reconoce el propio estudio** ·
11 Financiación / conflicto declarado + conclusión de los autores · 12 Cierre + debate.

**Enfoque:** análisis del artículo en voz neutra de revisor (qué hizo / qué encontró / qué reconoce),
no editorial. **Figuras:** la curva en U es un redibujo original de los HR publicados; no se reproduce
ninguna figura con copyright.

## Reproducir
```bash
python3 src/assemble_sleep.py   # escribe build_sleep.py en scratchpad
python3 <scratchpad>/build_sleep.py
# render con Chromium headless 1080×1350 @2× (ver .claude/skills/evidentia-carousel/render.sh)
```
Caption listo en `CAPTION_INSTAGRAM.md`.
