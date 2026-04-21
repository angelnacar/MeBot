# Mebot

Chatbot interactivo del CV de Ángel Nácar Jiménez — una aplicación Gradio desplegada en Hugging Face Spaces que utiliza un pipeline multi-agente LLM para responder preguntas sobre su perfil profesional.

## Inicio Rápido

```bash
# Clonar e instalar
git clone https://huggingface.co/spaces/angelnacar/Mebot
uv sync

# Configurar variables de entorno
export GROQ_API_KEY=tu_groq_key
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_API_KEY=tu_ollama_key
export PUSHOVER_USER=tu_pushover_user
export PUSHOVER_TOKEN=tu_pushover_token

# Ejecutar localmente
uv run python main.py
```

Accede a la aplicación en `http://localhost:7860`.

## Arquitectura

```
Usuario ──▶ TopicGuardrail ──▶ Toxicidad ──▶ Agente ──▶ Calidad ──▶ Sanitización ──▶ Respuesta
                    │            (Groq)       (Groq)    (Groq)         │
                    │               │                       │         │
                    ▼               ▼                       ▼         │
            Bloqueo off-topic   Bloqueo si           Rerun con       │
            (score > 0.7)       feedback            ▼
                                                   (Ollama)    Salida Final
```

### Componentes del Pipeline

| Componente | Propósito |
|-----------|---------|
| `TopicGuardrail` | Bloquea preguntas fuera de tema |
| `ToxicityPipeline` | Filtra entrada tóxica (umbral: 0.7) |
| `AgentPipeline` | Agente principal con llamada a herramientas |
| `QualityEvaluator` | Valida calidad de respuesta (umbral: 0.6) |
| `RerunPipeline` | Regenera respuestas de baja calidad |
| `OutputSanitizer` | Elimina UUIDs, nombres de herramientas, referencias a proveedores |

### Proveedores LLM

| Proveedor | Modelo | Caso de Uso |
|----------|-------|----------|
| Groq | `llama-3.1-8b-instant` | Toxicidad, Calidad, Agente |
| Ollama | `gpt-oss:120b-cloud` | Fallback y Rerun |

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
├── pushover.py       # Servicio de notificaciones
├── pipelines.py      # Orquestador del pipeline
└── main.py           # Punto de entrada Gradio

main.py               # Punto de entrada del proyecto
ui.py                 # Constructor de UI Gradio
tests/                # Tests unitarios y de integración
```

## Características Principales

- **Validación multi-etapa**: Filtrado por tema, detección de toxicidad, puntuación de calidad
- **Prevención de alucinaciones**: Verificación factual contra datos estructurados del perfil — cualquier invención detectada bloquea la respuesta (score ≤ 0.3)
- **Fallback automático**: Cambia a Ollama si Groq alcanza el límite de tasa
- **Seguridad por diseño**: OutputSanitizer previene fugas de detalles internos
- **Captura de contacto**: Registra email del usuario vía Pushover cuando lo proporciona
- **Registro de preguntas desconocidas**: Trackea preguntas para mejora futura

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
