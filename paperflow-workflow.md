# PaperFlow Hybrid Workflow

Este Mac queda pensado para un flujo hibrido simple:

- OpenClaw manda cuando la tarea necesita criterio, arquitectura o revision fuerte.
- Ollama abarata trabajo largo, mecanico o repetitivo.
- PaperFlow puede arrancar en dos perfiles: `local_only` y `hybrid`.

## Modelos recomendados

### Premium / OpenClaw

- `openai-codex/gpt-5.4`: arquitectura, decisiones de producto, refactors delicados, PR review, debugging dificil.
- `openai-codex/gpt-5.3-codex`: subagentes de codigo dentro de OpenClaw.

### Local / Ollama

- `qwen2.5-coder:7b`: coder local barato por defecto para scaffolding, cleanup, transformaciones mecanicas y pruebas baratas.
- `gpt-oss:20b`: opcion local fuerte para trabajo puntual cuando quieres mas calidad sin subir todo a premium.
- `nomic-embed-text:latest`: embeddings locales para PaperFlow.

### Opcionales cloud en Ollama

- `glm-4.7:cloud`
- `minimax-m2.1:cloud`

Solo merecen la pena si `ollama signin` queda activo y quieres una opcion intermedia adicional.

## Que usar para cada tipo de tarea

- Arquitectura, decisiones importantes, revision final: OpenClaw premium.
- Boilerplate, archivos largos, renombres, limpieza masiva, scaffolding: `qwen2.5-coder:7b`.
- Generacion local mas fuerte o exploracion puntual: `gpt-oss:20b`.
- Vectorizacion / retrieval local: `nomic-embed-text:latest`.

## Perfiles de PaperFlow

### `local_only`

Usa Ollama directo.

- `PAPERFLOW_CHAT_MODEL=qwen2.5-coder:7b`
- `PAPERFLOW_EXTRACTION_MODEL=qwen2.5-coder:7b`
- `PAPERFLOW_WRITING_MODEL=qwen2.5-coder:7b`
- `PAPERFLOW_EMBEDDING_MODEL=nomic-embed-text:latest`

### `hybrid`

Usa OpenClaw como puerta unica para chat y escritura.

- `PAPERFLOW_*_MODEL=default`
- `OPENCLAW_MODEL=default`
- embeddings siguen locales con `nomic-embed-text:latest`

Con este perfil el backend enruta `hybrid` y `cloud_enabled` a OpenClaw, mientras `local_only` queda en Ollama.

## Helpers del sistema

Se instalan estos helpers fuera del repo:

- `paperflow-session`
- `paperflow-local`
- `paperflow-premium`
- `paperflow-status`

## Flujo diario recomendado

1. `paperflow-status`
2. `paperflow-local` para trabajo barato de volumen
3. `paperflow-premium` para revisiones o decisiones
4. Dentro del repo usa ramas normales (`git checkout -b codex/<tema>` cuando toque)
5. Haz primero cambios mecanicos en local y luego pasa la revision final por OpenClaw premium

## Como ahorrar creditos

- Haz en local todo lo que sea repetitivo o facil de verificar.
- Usa premium cuando una mala decision te haga perder mas tiempo que los creditos.
- En PRs, deja a OpenClaw la revision profunda y el criterio final.
- Evita pedir al modelo premium que genere grandes bloques mecanicos si el local puede hacerlo.

## Validacion rapida

- `paperflow-status`
- `paperflow-local python -c "import os; print(os.getenv('PROJECT_DEFAULT_RUNTIME_MODE'))"`
- `paperflow-premium python -c "import os; print(os.getenv('PROJECT_DEFAULT_RUNTIME_MODE'))"`

## Nota sobre `qwen3-coder`

No se instala aqui porque hoy no es razonable para este hardware. El sistema queda optimizado para estabilidad real en este Mac, no para perseguir un modelo imposible.
