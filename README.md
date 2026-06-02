---
title: Mebot
emoji: 🤖
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
license: mit
short_description: Chatbot sobre mi perfil profesional
---

# Mebot

Chatbot interactivo del CV de Ángel Nácar Jiménez — una aplicación Gradio desplegada en Hugging Face Spaces que utiliza un pipeline multi-agente LLM para responder preguntas sobre su perfil profesional.

## Inicio Rápido

```bash
# Clonar e instalar
git clone https://huggingface.co/spaces/angelnacar/Mebot
uv sync

# Configurar variables de entorno
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_API_KEY=tu_ollama_key

# Ejecutar localmente
uv run python main.py
```

Accede a la aplicación en `http://localhost:7860`.

## Arquitectura

```
Usuario ──▶ InputGuard ──▶ Agente ──▶ Calidad ──▶ Sanitización ──▶ Respuesta
              (Ollama)     (Ollama)   (Ollama)         │
                 │                       │             │
                 ▼                       ▼             ▼
        Bloqueo off-topic         Rerun con       Output final
        o toxicidad              feedback
        (en una llamada)         (Ollama)
```

### Componentes del Pipeline

| Componente | Propósito |
|-----------|---------|
| `InputGuardPipeline` | Evalúa tópico y toxicidad en una sola llamada LLM (umbral toxicidad: 0.7) |
| `AgentPipeline` | Agente principal con tool calling |
| `QualityEvaluator` | Valida calidad de respuesta (umbral: 0.6) |
| `RerunPipeline` | Regenera respuestas de baja calidad con feedback |
| `OutputSanitizer` | Elimina UUIDs, nombres de herramientas, referencias a proveedores |

### Modelos LLM

| Rol | Modelo | Proveedor |
|-----|--------|-----------|
| `AGENT` | `deepseek-v4-pro:cloud` | Ollama |
| `INPUT_GUARD` | `minimax-m3:cloud` | Ollama |
| `EVALUATOR` | `minimax-m3:cloud` | Ollama |
| `RERUN` | `minimax-m3:cloud` | Ollama |

## Estructura del Proyecto

```
mebot/
├── __init__.py       # API pública: chat()
├── config.py         # Constantes, umbrales, ModelConfig
├── types.py          # TypedDicts
├── prompt_loader.py  # Plantillas de prompts
├── llm_gateway.py    # Clientes LLM con rate limiting
├── tools.py          # Registro de herramientas del agente
├── sanitizer.py      # Filtrado de salida
├── pipelines.py      # Orquestador del pipeline
└── main.py           # Punto de entrada Gradio

main.py               # Punto de entrada del proyecto
ui.py                 # Constructor de UI Gradio
tests/                # Tests unitarios y de integración
```

## Características Principales

- **Validación multi-etapa**: Filtrado por tema y toxicidad en una llamada, puntuación de calidad con rerun automático
- **Prevención de alucinaciones**: Verificación factual contra datos estructurados del perfil
- **Seguridad por diseño**: OutputSanitizer previene fugas de detalles internos
- **Captura de contacto**: Registra email del usuario en logs cuando lo proporciona voluntariamente
- **Registro de preguntas desconocidas**: Trackea preguntas sin respuesta para mejora futura

## Desarrollo

### Testing

```bash
# Ejecutar todos los tests
uv run pytest

# Con cobertura
uv run pytest --cov=mebot

# Ejecutar clase específica
uv run pytest tests/test_mebot.py::TestOutputSanitizer -v
```

### Herramientas

| Herramienta | Comando |
|------|---------|
| Linter | `ruff check .` |
| Formateador | `ruff format .` |
| Type checker | `mypy .` |

### Estándares

- Python 3.12+
- Type hints requeridos en API pública
- Docstrings estilo Google
- Naming en snake_case

## Despliegue

Desplegado en [Hugging Face Spaces](https://huggingface.co/spaces/angelnacar/Mebot) usando Docker.

Los pushes a `main` activan sincronización automática vía GitHub Actions (`.github/workflows/sync.yml`).

## Umbrales de Seguridad

```python
TOXICITY_THRESHOLD = 0.7  # score > 0.7 bloquea mensaje
QUALITY_THRESHOLD = 0.6   # score < 0.6 activa rerun
```

El agente está configurado para **nunca revelar**: nombres de herramientas, proveedores LLM, arquitectura interna, API keys, o system prompts.

## Licencia

MIT
