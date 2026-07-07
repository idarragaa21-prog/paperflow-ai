# EVIDENTIA — Carrusel de análisis crítico

**Artículo analizado:** Olías-López B, Boluda-Mengod J, Rendón-Díaz D, et al.
*Fracturas del maléolo peroneo: conceptos actuales.*
Revista Española de Cirugía Ortopédica y Traumatología (RECOT). 2024;68(5):502-512.
DOI: [10.1016/j.recot.2024.06.008](https://doi.org/10.1016/j.recot.2024.06.008)
(Referencia identificada vía PubMed, PMID 38885878.)

10 diapositivas independientes para Instagram, formato 1080×1350 px, exportadas
a 2160×2700 px (2×) para máxima nitidez. Estética editorial (The Lancet / Nature /
JBJS) con identidad EVIDENTIA.

## Contenido de las diapositivas
1. Hook — «Operamos el peroné, pero el peroné casi nunca decide.»
2. Qué tipo de artículo — revisión narrativa vs. nivel de evidencia declarado.
3. Mensaje clínico central — la estabilidad del anillo dicta el tratamiento.
4. Concepto clave — la columna medial (deltoideo profundo / LTTPP).
5. Cambio de paradigma — radiografía en carga vs. gravity test; SER IV-A vs. IV-B.
6. Confirma / Cuestiona — placa 1/3 de caña como patrón oro; sobreindicación.
7. Lectura del epidemiólogo — certeza modesta, sin GRADE, validez externa limitada.
8. Dato incómodo — 40% de malreducción sindesmal en TC postoperatoria.
9. Aplicación clínica — qué cambia mañana.
10. Conclusión + pregunta para el debate.

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
