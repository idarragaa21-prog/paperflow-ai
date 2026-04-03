# Revisión a Profundidad: Paperflow AI vs. Paperguide.ai

## Estado Actual del Proyecto (Paperflow AI)

Paperflow AI está **muy avanzado y ya cuenta con una arquitectura Full-Stack sólida**. Funciona como un entorno de investigación "local-first" y privado por diseño (FastAPI + React 19 + PostgreSQL + Redis + Qdrant).

### Qué hace MUY BIEN Paperflow AI (Mejor que o Igual a Paperguide):
1. **Motor de Meta-Análisis Completo (R Engine):** Paperflow extrae tamaños de efecto, riesgos de sesgo y ejecuta análisis estadísticos con R. Esto es un nivel clínico/académico superior. Paperguide solo hace "Extracción de datos" básica.
2. **Fichas Clínicas (Clinical Sheets):** Generación de evidencia estilo "UpToDate" con LLMs en múltiples pasadas y exportación a DOCX/PDF. Paperguide no ofrece esto enfocado a medicina.
3. **Drafts / Escritor de Literatura IA:** Paperflow cuenta con edición en línea y resolución automática de citas para redactar manuscritos, muy similar al "AI Writer" de Paperguide.
4. **Búsqueda Federada:** Busca en PubMed, Europe PMC y DOAJ, con resolución de Open Access (Unpaywall).
5. **Screening (PRISMA):** Un flujo de tamizaje de títulos/resúmenes integrado. Paperguide no menciona flujos PRISMA estructurados.
6. **Privacidad Total:** Al correr en local (Ollama) o mediante APIs directas (OpenClaw/Claude), no subes tus datos a servidores de terceros, lo cual es el mayor diferenciador contra Paperguide (SaaS en la nube).

### Qué le FALTA a Paperflow AI para igualar o superar a Paperguide.ai:
1. **"Deep Research" automatizado más pulido (Investigación Profunda):** Paperguide publicita una función donde la IA investiga a profundidad y escribe un reporte. Paperflow tiene `DeepResearchPage.tsx`, pero actualmente la UI está en modo demostración (`DEMO_MODE`) y necesita mejoras visuales (fuentes estilo reporte, botón de impresión, diseño de exportación) para sentirse como un producto final premium.
2. **"AI Search" en el buscador:** Paperguide responde a preguntas directamente extrayendo información de los "Top 10" papers. Paperflow tiene un botón "Sintetizar Evidencia con IA" en la búsqueda, pero su diseño es plano. Hay que hacerlo destacar visualmente como la función estrella ("✨ AI Search").
3. **Matriz de Revisión de Literatura Comparativa (Literature Review Matrix):** Paperguide vende fuertemente una tabla donde comparas metodologías y hallazgos lado a lado. Aunque Paperflow extrae esta data en `MetaPage`, le falta una vista dedicada ("Literature Comparison Matrix") puramente enfocada en la comparación cualitativa de los textos, simple y fácil de leer.
4. **Marketing y Pulido del Landing Page:** El landing page de Paperguide tiene "Testimonios" falsos/reales, insignias de confianza y secciones muy claras ("Deep Research", "AI Writer"). La página de inicio de Paperflow es funcional pero puede verse más corporativa.

---

## Plan "End-to-End" para Terminar y Superar a Paperguide.ai

Para llevar a Paperflow AI al 100% y dejarlo visual y funcionalmente superior a Paperguide, ejecutaremos este plan de 5 fases. Las bases (backend y servicios) ya existen; el trabajo es 90% **Frontend, UX y orquestación LLM**.

### FASE 1: Pulido Visual Extremo (Landing Page y UI Core)
**Objetivo:** Vender la herramienta con la misma calidad comercial de un SaaS de $24/mes.
- **Acción 1:** Rediseñar `LandingPage.tsx` agregando la sección "Investigación Profunda" (Deep Research) y una cuadrícula de Testimonios ("Por qué lo amamos").
- **Acción 2:** Mejorar el componente `SearchPage.tsx`. El bloque de "✨ Síntesis IA" debe tener un fondo en gradiente sutil, bordes destacados y tipografía de mayor lectura para que se sienta como la función principal al buscar (igual al "AI Search" de Paperguide).

### FASE 2: Matriz de Revisión de Literatura (Literature Comparison)
**Objetivo:** Igualar la funcionalidad estrella de Paperguide para comparar papers.
- **Acción 1:** Crear una nueva ruta `/projects/:id/literature-review`.
- **Acción 2:** Construir una tabla dinámica (Componente `LiteratureReviewMatrix`) que consuma los datos de los "Estudios Extraídos" del proyecto.
- **Acción 3:** Mostrar lado a lado: *Título, Autores, Metodología (extraída por IA), Hallazgos Clave (extraídos por IA) y Riesgo de Sesgo*.

### FASE 3: Refactorización de "Deep Research"
**Objetivo:** Convertir el módulo de "Deep Research" de una demo a un generador de reportes listo para imprimir.
- **Acción 1:** Eliminar la lógica de `DEMO_MODE` en `DeepResearchPage.tsx` para que siempre conecte con el endpoint real `/research/deep` (que ya funciona en el backend con OpenClaw/Ollama).
- **Acción 2:** Modificar el CSS del reporte generado para que use tipografías serias (ej. `Georgia` o `Merriweather`), fondo blanco puro, márgenes de documento, y agregar un botón de "🖨️ Exportar a PDF / Imprimir".

### FASE 4: Integración del "Reference Manager" con "AI Writer"
**Objetivo:** Superar la fricción de escribir.
- **Acción 1:** Asegurar que desde la "Matriz de Literatura" (Fase 2) el usuario pueda seleccionar 3 papers y enviarlos directamente al módulo de "Drafts" (Borradores).
- **Acción 2:** El "Reference Manager" actual (que exporta a BibTeX/APA) debe tener un botón de "Resumir con IA" individual para generar un *abstract* rápido en 1 clic desde la lista.

### FASE 5: Pruebas End-to-End y QA
**Objetivo:** Garantizar que no hay "dead-ends" (callejones sin salida).
- **Acción 1:** Crear scripts de verificación (Playwright/Cypress) para el flujo completo: Búsqueda -> Selección -> Deep Research -> Borrador.
- **Acción 2:** Ejecutar la suite de pruebas del backend (`pytest`) asegurando que los LLMs locales (Ollama) responden a las extracciones sin timeouts (controlando la latencia).

### Conclusión del Plan
Siguiendo estos pasos, **Paperflow AI no solo igualará a Paperguide, sino que lo superará**. Tendrá el mismo nivel de "magia IA" en la interfaz (búsqueda sintetizada, reportes generados solos, matrices de comparación), pero respaldado por un **motor clínico real (R, Riesgo de Sesgo) y privacidad total**, algo que Paperguide no puede ofrecer por su naturaleza comercial.
