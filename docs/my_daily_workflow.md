# Mi flujo diario con PaperFlow AI

> **Objetivo:** este documento es la ruta completa —de principio a fin— para producir
> un artículo o revisión clínica desde mi PC, en modo local-first, sin perder
> trazabilidad ni tiempo en herramientas dispersas. Todo corre con mis propios
> servicios (Ollama, Postgres, Qdrant, MinIO, R).

---

## 0. Antes de empezar (una sola vez)

```bash
./scripts/first_time_setup.sh
```

El script:

1. Verifica Docker + Python 3.11 + Node 20+
2. Copia `.env.example → .env` si no existe
3. Genera `SECRET_KEY` aleatoria
4. Instala Ollama si falta y descarga los modelos base:
   - `qwen2.5-coder:7b` → chat / writing / extracción
   - `nomic-embed-text:latest` → embeddings (Qdrant)
   - opcional: `qwen3-vl:8b` → visión para figuras y tablas

Para prender todo:

```bash
./scripts/dev_up.sh          # Postgres + Redis + Qdrant + MinIO + API + worker
cd frontend && npm run dev   # UI en http://localhost:5173
```

---

## 1. Perfil personal (Settings)

Antes del primer proyecto, abro **Settings → Profile** y lleno:

- **Full name**, **Affiliation**, **ORCID**: aparecen en exports DOCX/PDF y en la cover letter.
- **Signature (markdown)**: se inyecta al final de letters-to-editor y cover letters.
- **Default language**: `es` / `en` / `pt`. También cambia el idioma de la UI.

Con esto ya no tengo que escribir mis datos cada vez que exporto.

---

## 2. Crear proyecto y buscar literatura

1. `Dashboard → Nuevo proyecto` (título, descripción, pregunta clínica).
2. `Research → Búsqueda`
   - Uso AI Search (botón `✨ Síntesis IA`) cuando quiero una síntesis rápida con citas.
   - Refino con filtros (años, tipo de estudio) y **Add to Library** lo relevante.
3. `Library` procesa PDFs (Grobid + PyMuPDF + OCR para tablas si hace falta).

> Si más tarde quiero una síntesis extendida, entro a `/deep-research`. El reporte
> incluye Print, Download PDF y **Send to Writing** que crea un documento
> `systematic_review` con el reporte ya pegado en las secciones correctas.

---

## 3. Extracción estructurada + Matrix

1. `Extraction` → selecciono papers y lanzo extracción (el worker usa Ollama).
2. Reviso los campos sugeridos, corrijo inline y confirmo.
3. `Matrix → Build new matrix version` → nace una versión `current` trazada.
4. En la Matrix uso la pestaña **Comparison** para ver estudios como tabla
   (Diseño, Población, Intervención, Comparador, Outcomes, N, Follow-up,
   Efecto principal, Risk of bias, Limitaciones) — perfecto para auditar antes
   de meta-analizar.

---

## 4. Meta-análisis (opcional)

`Meta Runs → New run` → el servicio R plumber corre el modelo de efectos aleatorios,
heterogeneidad, sesgo de publicación y devuelve forest/funnel plots. Los resultados
quedan atados al `matrix_version_id` para rastreo.

---

## 5. Writing Assistant

Aquí vive la escritura final:

1. `Writing → Nuevo documento`
   - `narrative` → artículos clínicos/revisiones narrativas
   - `systematic_review` → secciones PRISMA con Search strategy + Risk of bias
   - `meta_analysis` → añade Statistical analysis, Forest plot, Heterogeneity
   - `letter_to_editor` → Opening / Comment / Closing
   - `cover_letter` → 5 secciones fijas con firma automática
2. Para cada sección:
   - **Generate** → el modelo redacta con grounding en Matrix + Meta runs.
   - Insertar citas con `[M1]` (matriz), `[R2]` (meta-run), `[C3]` (referencia).
   - Auto-save cada 2 s mientras edito.
3. **Exports** (botonera arriba a la derecha):
   - `DOCX` (python-docx) — estilo Times/Calibri, bold/italic/superíndice citas
   - `PDF` (reportlab) — serif, márgenes 2.54 cm, ListFlowable para bullets
   - `MD` — markdown crudo con bibliografía
4. Estilo de cita: APA / Vancouver / AMA (selector en el header).

---

## 6. Referencias y bibliografía

`References` lista todos los papers importados al proyecto (via Library, extracción
o Deep Research). Los exports del Writing Assistant construyen la sección
`## References` en el estilo elegido, truncando autores >6 como `et al.` en Vancouver.

---

## 7. Copia de seguridad diaria

```bash
./scripts/backup_everything.sh
```

Crea `tmp/backups/full/paperflow_backup_YYYYMMDD_HHMMSS.tar.gz` con:

- Dump Postgres (`pg_dump`)
- Mirror del bucket MinIO (`mc mirror`)
- `~/PaperFlowAIData` completo (matrices, exports, R outputs)
- Archivos `.env` (con `--redact` para ocultar secretos)
- `MANIFEST.txt` con commit y rama actuales

Para restaurar en otra máquina:

```bash
tar -xzf paperflow_backup_*.tar.gz -C /tmp
./scripts/restore_postgres.sh /tmp/paperflow_backup_*/postgres/paperflow_ai.sql
./scripts/restore_minio.sh    /tmp/paperflow_backup_*/minio/paperflow-artifacts
```

---

## 8. Atajos que uso todos los días

| Acción | Dónde | Resultado |
|---|---|---|
| Síntesis rápida desde resultados de búsqueda | `Research → Síntesis IA` | Resumen con citas guardable en Writing |
| Reporte de estado del arte | `/deep-research` + **Send to Writing** | Writing doc `systematic_review` pre-poblado |
| Comparación visual de estudios | `Matrix → Comparison` | Tabla horizontal sticky |
| Guardar trabajo rápidamente | `Writing` auto-save 2 s | No existe "Save" manual |
| Insertar cita trazada | Panel `Claim links` en Writing | `[M1]`, `[R2]`, `[C3]` en el cursor |
| Exportar artículo final | `Writing → DOCX/PDF/MD` | Descarga con nombre limpio |

---

## 9. Flujo de un día real

> _Ejemplo: "Aspirina en prevención secundaria de ictus — revisión 2026"_

1. `Research`: búsqueda PubMed → Add to Library (15 papers).
2. `Library`: espero 2–5 min a que Grobid extraiga full text.
3. `Extraction`: lanzo extracción → reviso la tabla de campos.
4. `Matrix → Build`: versión v1 creada. Abro **Comparison** para auditar.
5. `Meta Runs`: efecto combinado sobre eventos CV → forest plot.
6. `Writing → New document` (modo `meta_analysis`, estilo Vancouver).
7. Generate en cada sección, pego citas `[M2]`, `[R1]` donde toca.
8. Exporto DOCX → reviso en Word → listo para el co-autor.
9. `./scripts/backup_everything.sh` antes de cerrar el portátil.

---

**Todo lo anterior corre en mi disco. No se escapa un dato a la nube.**
