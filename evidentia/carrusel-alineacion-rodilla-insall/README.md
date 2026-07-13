# EVIDENTIA · Carrusel — Alineación funcional vs. mecánica en PTR (Premio Insall 2025)

Carrusel de Instagram (1080×1350, exportado 2× = 2160×2700) para **@evidentia_co**:
lectura crítica de un ECA de alto impacto y muy reciente en artroplastia de rodilla.
Enseña a distinguir el **desenlace primario** (negativo) de los **secundarios/subgrupo**
que alimentan el titular — el corazón de la lectura crítica.

## El artículo

Según PubMed — Young SW, Tay ML, Kawaguchi K, et al. *The John N. Insall Award: Functional
Versus Mechanical Alignment in Total Knee Arthroplasty: A Randomized Controlled Trial.*
**The Journal of Arthroplasty** 2025;40:S20-S30. DOI 10.1016/j.arth.2025.02.065 · PMID 40023458.

Datos clave (ECA asistido por robot, MA n=121 vs FA n=123, 2 años):
- **Primario — Forgotten Joint Score:** 64,4 vs 70,1 · **P=0,10 (NS)**.
- Liberaciones de partes blandas: **65% vs 16% · P<0,001** (el hallazgo robusto).
- Secundarios a favor de FA: KOOS síntomas (P=0,01), KOOS-CdV (P=0,03), «lo recomendaría» 94% vs 82%.
- Subgrupo CPAK tipo I: FJS 71,3 vs 56,8 (P=0,02) — hipótesis, no confirmación.

## Arco (12 láminas)

1 Portada (hook «gold standard ¿en duda?») · 2 Ficha del artículo · 3 Concepto MA vs FA (esquema del eje) ·
4 El diseño (desenlace primario = FJS) · 5 **El giro: primario NS (P=0,10)** · 6 De dónde sale el titular (secundarios) ·
7 El hallazgo sólido (menos liberaciones) · 8 Significativo ≠ importante (MCID del FJS ~14) ·
9 La trampa del subgrupo (CPAK I) · 10 La lectura del epidemiólogo · 11 Cuatro conclusiones (chuleta) ·
12 Cierre + pregunta de debate.

## Imaginería

Los gráficos son **SVG editoriales** originales (implante de rodilla con eje de alineación; esquema
mecánica vs funcional). Se intentó generar un *hero* con **nano_banana_pro** (Higgsfield) pero el
workspace estaba **sin créditos**; se degradó con elegancia a SVG. Al recargar créditos puede
regenerarse un hero foto-realista e insertarse en la portada.

## Reproducir

```bash
python3 src/assemble_insall.py      # escribe build_insall.py en scratchpad
python3 <scratchpad>/build_insall.py
# render con Chromium headless 1080×1350 @2× (ver .claude/skills/evidentia-carousel/render.sh)
```

Caption listo en `CAPTION_INSTAGRAM.md`.
