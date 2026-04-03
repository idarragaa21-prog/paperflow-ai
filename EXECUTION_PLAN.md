# 1. Prioritization principles
1. **Pragmatismo Despiadado:** Si no cierra un ciclo del flujo de trabajo o no diferencia visualmente el producto frente a Paperguide, se recorta o se pospone.
2. **La percepción es realidad:** Las funciones de IA deben verse *premium*. Una interfaz plana para la síntesis de IA en la búsqueda hace que parezca básica. El pulido visual es un requisito funcional, no un lujo.
3. **Cero Falsas Demos:** Los modos de demostración (como el `DEMO_MODE` en Deep Research) destruyen la confianza. Deben eliminarse y conectarse a la API real.
4. **Flujo sobre módulos aislados:** El usuario debe poder transitar de Búsqueda -> Comparación -> Investigación Profunda -> Redacción sin encontrarse con callejones sin salida.

# 2. Reorganized map of all pending work

* **Product / Demo / Go-to-market:**
  * Rediseño de la Landing Page (añadir sección de Deep Research y testimonios).
* **UX / Navigation / Workflow coherence:**
  * Destacar visualmente la "✨ Síntesis IA" en la página de búsqueda.
  * Nueva vista dedicada "Literature Review Matrix" (Matriz de Comparación).
  * Flujo de trabajo cruzado: Enviar papers desde la Matriz hacia los Borradores (Drafts).
  * Resúmenes IA en 1-clic dentro del Reference Manager.
* **Frontend:**
  * Remover lógica `DEMO_MODE` en `DeepResearchPage.tsx`.
  * Crear componente `LiteratureReviewMatrix` y su ruta.
  * Mejoras CSS para la exportación de Deep Research (tipografía de reporte, botón de impresión a PDF).
* **AI / LLM / Grounding:**
  * Conectar la UI de Deep Research al endpoint `/research/deep` existente.
  * Integrar Claude Sonnet 4 como opción premium para reducir placeholders en las fichas clínicas.
* **Quality / Testing / Hardening:**
  * Pruebas E2E (Playwright/Cypress) para el flujo completo.
  * Manejo de latencia/timeouts de Ollama en el backend para extracciones largas.

# 3. Critical blockers

1. **Modos de Demo Falsos:** `DeepResearchPage.tsx` está operando en `DEMO_MODE`. Esto es un bloqueo crítico para la credibilidad técnica del producto; debe conectarse al backend real inmediatamente.
2. **Callejones sin Salida en el Flujo:** La incapacidad de mover fácilmente un grupo seleccionado de papers desde la etapa de comparación (Matriz) directamente a la etapa de redacción (Drafts).
3. **Presentación Visual de la IA:** El bloque "Sintetizar Evidencia con IA" en la página de búsqueda parece texto estándar de la interfaz, fallando en comunicar que es la función estrella.

# 4. Roadmap by phases

**Phase 1: Stabilize (Impacto inmediato y confianza)**
* **Objective:** Hacer que la herramienta se vea y funcione como un SaaS premium para construir confianza inmediata.
* **Concrete tasks:**
  * Remover `DEMO_MODE` de Deep Research y conectar a `/research/deep`.
  * Pulir el diseño de la Síntesis IA en `SearchPage.tsx` (gradiente, tipografía clara, bordes).
  * Refactorizar `LandingPage.tsx` (sección Deep Research y testimonios).
* **Dependencies:** Ninguna.
* **Recommended order:** UI de Búsqueda IA -> Conexión de Deep Research -> Landing Page.
* **Expected outcome:** Un producto que se puede demostrar perfectamente y prueba que el backend funciona de principio a fin de forma privada.

**Phase 2: Close the core workflow (El salto competitivo)**
* **Objective:** Entregar la "Literature Review Matrix" (la función asesina de Paperguide) y conectar el flujo desde la investigación hasta la redacción.
* **Concrete tasks:**
  * Crear la ruta `/projects/:id/literature-review` y el componente `LiteratureReviewMatrix`.
  * Implementar la acción "Enviar a Drafts" desde la Matriz.
  * Añadir resúmenes IA de 1-clic al Reference Manager.
* **Dependencies:** Finalización de la Fase 1.
* **Recommended order:** Componente Matriz -> Flujo Matriz a Drafts -> Resúmenes de Referencias.
* **Expected outcome:** Un bucle cerrado donde el usuario busca, compara en una matriz y envía las selecciones directo al escritor IA sin "copiar y pegar".

**Phase 3: Make it competitive (Calidad Premium)**
* **Objective:** Elevar los formatos de salida y la calidad editorial del LLM.
* **Concrete tasks:**
  * Mejoras CSS de Deep Research para formato imprimible y botón "Exportar a PDF".
  * Integrar Claude Sonnet 4 como opción superior en Clinical PRO.
* **Dependencies:** Fase 2.
* **Recommended order:** CSS de Exportación de Deep Research -> Integración Claude.
* **Expected outcome:** Reportes y guías que rivalizan con contenido escrito por humanos y listo para uso clínico real.

**Phase 4: Polish and scale (Hardening)**
* **Objective:** Garantizar estabilidad bajo carga y en casos extremos locales.
* **Concrete tasks:**
  * Optimización de timeouts/latencia para modelos locales (Ollama).
  * Pruebas E2E (Playwright) para el core loop.
* **Dependencies:** Interfaz estable de Fases 1-3.
* **Recommended order:** Manejo de Timeouts -> Pruebas E2E.
* **Expected outcome:** Cero caídas en frontend por tiempo de espera y una experiencia LLM local robusta.

# 5. Ideal execution order

1. **Conectar Deep Research (Phase 1):** Remover el `DEMO_MODE`. Si esto no funciona de verdad, el resto del marketing no importa.
2. **Pulir UI de Búsqueda IA (Phase 1):** Victoria rápida (solo CSS) para que la IA resalte inmediatamente.
3. **Construir Literature Matrix UI (Phase 2):** Neutraliza la principal ventaja visual de Paperguide.
4. **Flujo Matriz -> Drafts (Phase 2):** Cierra la brecha en el flujo de trabajo. Transforma herramientas aisladas en un verdadero "pipeline".
5. **CSS de Exportación de Deep Research (Phase 3):** Hace que el output real sea profesional y utilizable en consultorio.
6. **Rediseño de Landing Page (Phase 1):** Actualizar el marketing *después* de que Deep Research y la Matriz existan y funcionen.
7. **Resúmenes en 1-clic (Phase 2):** Mejora sutil de UX para reducir la fricción de lectura.
8. **Integración Claude (Phase 3):** Función Premium para elevar redacción.
9. **Tuning de Timeouts Ollama (Phase 4):** Hardening técnico.
10. **Pruebas E2E (Phase 4):** Hardening funcional.

*Por qué este orden minimiza el retrabajo:* Prioriza la "verdad funcional" (que Deep Research deje de ser un demo) por encima del marketing. Luego ataca tu mayor brecha competitiva (la Matriz) y cierra el flujo para el usuario. La Landing Page se hace justo después para que tu demo en vivo coincida 100% con lo que promocionas.

# 6. Bottlenecks and false priorities

* **Bottlenecks:** `DeepResearchPage.tsx` fingiendo hacer el trabajo mina la credibilidad de todo el sistema.
* **Tasks that unlock many others:** La `LiteratureReviewMatrix` desbloquea la capacidad de curar y comparar papers *antes* de enviarlos al redactor.
* **False priorities (parecen importantes pero no lo son ahora):** Rediseño del Landing Page inmediato. Es fácil y luce bien, pero es marketing puro. Hay que arreglar el "core" primero.
* **Tasks that should be postponed:** Pruebas E2E completas con Playwright. Si el producto funciona bien manualmente en esta fase, lánzalo. Las pruebas escritas estrictas vienen en la fase 4.
* **Tasks that would be a waste of time right now:** Modificar el motor R para añadir más tests estadísticos o construir herramientas colaborativas. El motor clínico actual es brutalmente superior; el foco es hacerlo consumible.
* **Overbuilt modules with low current value:** La extracción profunda de metadatos no tiene "pegada" visual si no existe la *Literature Review Matrix* para mostrarlos en una tabla lado a lado.

# 7. Structured backlog

| ID | Task | Area | Priority | Phase | Dependencies | Impact | Difficulty | Suggested status | Definition of done |
|---|---|---|---|---|---|---|---|---|---|
| **T1** | Conectar Deep Research | Frontend/AI | Critical blocker | 1 | Ninguna | Alto | Medio | **Do Now** | `DEMO_MODE` eliminado; la vista llama a `/research/deep` y renderiza la respuesta real del LLM. |
| **T2** | ✨ Pulir UI Búsqueda IA | UX/Frontend | MVP | 1 | Ninguna | Alto | Bajo | **Do Now** | El bloque de síntesis en `SearchPage.tsx` tiene fondo degradado, bordes notorios y tipografía premium. |
| **T3** | Construir Literature Matrix | Frontend | V1 | 2 | T1 | Alto | Medio | **Do Now** | Ruta `/projects/:id/literature-review` renderiza tabla comparando Título, Autores, Métodos, Hallazgos y RoB. |
| **T4** | Flujo Matriz -> Drafts | Workflow | V1 | 2 | T3 | Alto | Medio | **Do Now** | Seleccionar papers en la Matriz y presionar "Enviar a Draft" puebla el contexto de `DraftsPage.tsx`. |
| **T5** | Exportación Deep Research | UX/Frontend | V1 | 3 | T1 | Medio | Bajo | Later | La página usa fuentes legibles de impresión, fondo blanco puro, e incluye botón "Exportar a PDF". |
| **T6** | Rediseño Landing Page | Demo/Producto| MVP | 1 | T1, T3 | Alto | Bajo | Delegate | `LandingPage.tsx` luce más corporativa e incluye sección "Deep Research" y testimonios. |
| **T7** | Resúmenes de Referencias | UX/AI | Nice to have | 2 | Ninguna | Bajo | Bajo | Later | Los items de la lista de referencias tienen un botón "Resumir" (abstract de 2 líneas vía LLM). |
| **T8** | Integración Claude Sonnet 4| AI/Modelos | V2 | 3 | Ninguna | Alto | Medio | Later | Fichas clínicas generan texto usando el provider de Claude sin fallos de esquema. |
| **T9** | Afinar Timeouts Ollama | Infra | Nice to have | 4 | Ninguna | Bajo | Medio | Postpone | Backend mantiene conexiones de frontend vivas cuando una inferencia local tarda >60s. |
| **T10**| Pruebas E2E Core Flow | Calidad | V2 | 4 | T1, T3, T4 | Medio | Alto | Postpone | Tests automatizados de Playwright cruzan exitosamente Búsqueda -> Matriz -> Draft. |

# 8. Conclusion: what I would do first if I could only attack 5 things

Si los recursos son limitados, mi recomendación despiadada para tumbar la ventaja de Paperguide hoy mismo es:

1. **T1: Conectar Deep Research al backend.** (Matar el humo de la demo).
2. **T2: Pulir la UI de Búsqueda IA.** (Hacer que la IA local se perciba como magia costosa).
3. **T3: Construir la Literature Review Matrix.** (Neutralizar la funcionalidad estrella visual de la competencia).
4. **T4: Construir el puente Matriz -> Drafts.** (Cerrar el ciclo total de investigación).
5. **T5: Añadir estilos de impresión/exportación a Deep Research.** (Para que los reportes sirvan de verdad).

**Respuestas directas:**
* **Qué debes hacer ahora:** Ejecutar T1, T2, T3 y T4. Esto convierte la aplicación de "una caja de herramientas desconectadas" a un **"Pipeline fluido de investigación"**.
* **Qué debes dejar para después:** Rediseño del Landing Page (T6) y Resúmenes en 1 clic (T7).
* **Qué debes cortar:** Pruebas E2E (T10) y tuning profundo de infraestructura (T9). Cero modificaciones al R Engine o a las bases de datos.
* **Qué te lleva al nivel competitivo más rápido:** Construir la **Literature Review Matrix (T3)**. Ya tienes los datos analíticos de mayor calidad (gracias al R engine y al análisis de riesgo de sesgo), el único paso restante es renderizarlos lado-a-lado como lo hace tu competencia.
