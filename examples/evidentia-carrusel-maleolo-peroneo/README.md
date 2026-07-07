# EVIDENTIA — Carrusel de análisis crítico

**Artículo analizado:** Olías-López B, Boluda-Mengod J, Rendón-Díaz D, et al.
*Fracturas del maléolo peroneo: conceptos actuales.*
Revista Española de Cirugía Ortopédica y Traumatología (RECOT). 2024;68(5):502-512.
DOI: [10.1016/j.recot.2024.06.008](https://doi.org/10.1016/j.recot.2024.06.008)
(Referencia identificada vía PubMed, PMID 38885878.)

10 diapositivas independientes para Instagram, formato 1080×1350 px, exportadas
a 2160×2700 px (2×) para máxima nitidez. Estética editorial (The Lancet / Nature /
JBJS) con identidad EVIDENTIA.

Variantes:
- **`slide-01…11.png` (versión final):** replica la **plantilla real de los carruseles
  de @evidentia_co** (azul marino + blanco + oro + rojo, ornamentos geométricos, lockups
  EVIDENTIA, ícono bombilla-lupa), con el título real del artículo y **capturas de 4
  figuras** (1, 4, 3 y 5). Generada con `src/build3.py` + `src/orn.py`.
- **`variante-B-verde/`:** versión con el verde del badge del logo.
- **`variante-A-editorial/`:** primera versión, solo tipografía + ilustración vectorial.

La marca real (paleta, tipografía, referencias de sus carruseles) está en
`assets/marca/BRAND.md`.

## Contenido de las diapositivas (versión final — 11 slides)
1. Hook — «Operamos el peroné, pero el peroné casi nunca decide.»
2. El artículo — tarjeta con el **título real**, autores, RECOT 2024, DOI, CC BY-NC-ND, «Nivel II».
3. El diseño (epidemiólogo) — revisión narrativa; Nivel II declarado vs. Nivel V real.
4. **Figura 1 (captura)** — el algoritmo de manejo: consenso, no evidencia agregada.
5. Mensaje central — la estabilidad del anillo y la columna medial (deltoideo profundo).
6. **Figura 4 (captura)** — Rx en carga: SER II / IV-A / IV-B; la carga reclasifica.
7. **Figura 3 (captura)** — la TC revela impactación medial oculta (61–73%).
8. **Figura 5 (captura)** — opciones de fijación; menos agresión de partes blandas.
9. El epidemiólogo — certeza modesta, sin GRADE; 40% de malreducción sindesmal.
10. **Aplicación clínica (como ortopedista)** — checklist accionable «Qué aplico mañana».
11. Conclusión + pregunta para el debate.

Figuras usadas con atribución (Open Access CC BY-NC-ND); ver
`assets/figuras-articulo/ATTRIBUTION.md`.

## Notas del análisis crítico (resumen)
- **Diseño:** revisión narrativa de «conceptos actuales» — sin PRISMA, sin
  búsqueda sistemática ni evaluación de sesgo. El «Nivel II» declarado sobreestima
  la certeza real de una narrativa (nivel V).
- **Fortalezas:** algoritmo claro y clínicamente útil; integra el giro conceptual
  hacia la columna medial y la radiografía en carga.
- **Limitaciones:** recomendaciones apoyadas en estudios nivel III–IV, biomecánica
  y cadáver; algoritmo unicéntrico (validez externa limitada).
- **Aplicabilidad:** alta como marco de decisión; baja como prueba de eficacia.

## Reproducir
Fuentes editoriales: Playfair Display, EB Garamond, Libre Franklin (OFL).

```bash
python3 src/build.py           # genera src/slide-*.html
# render (Chromium headless), 2x:
for i in $(seq -w 1 10); do \
  chromium --headless=new --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=1080,1350 --screenshot=slide-$i.png src/slide-$i.html; done
```

> Diseño y análisis con fines divulgativos (educación médica). Las imágenes son
> ilustraciones vectoriales originales, no fotografías de pacientes.
