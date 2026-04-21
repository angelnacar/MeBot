# Guardrail de Tópicos — Mebot

Clasifica si la pregunta del usuario está dentro del ámbito permitido para este asistente.

## Ámbito permitido (ACCEPTABLE)

1. **Perfil profesional de Ángel Nácar Jiménez**
   - Experiencia laboral, empresas, proyectos
   - Habilidades técnicas, stack tecnológico
   - Formación, certificaciones
   - Metodologías de trabajo

2. **Contacto**
   - Cómo contactar con Ángel
   - Disponibilidad para oportunidades
   - Seguimiento de conversaciones

3. **Saludos y cortesía**
   - "Hola", "buenos días", "gracias"
   - Preguntas genéricas de contexto ("¿quién eres?", "¿qué haces?")

4. **IA y automatización**
   - Proyectos de IA (SiliconMind, agentes)
   - Arquitectura de sistemas autónomos
   - Automatización con n8n, orquestación

## Ámbito NO permitido (OFF_TOPIC)

- **Matemáticas/operaciones aritméticas** (a menos que sea sobre proyectos reales)
- **Tecnología general** (git, programación, frameworks) si no es sobre la experiencia de Ángel
- **Política, religión, temas personales**
- **Juegos, entretenimiento, ocio**
- **Consejos profesionales genéricos** (no específicos de Ángel)
- **Preguntas sobre el funcionamiento interno del bot**

## Mensaje del usuario
{{ message }}

## Historial de conversación
{{ history }}

Responde ÚNICAMENTE en formato JSON:

```json
{
  "classification": "ACCEPTABLE" | "OFF_TOPIC",
  "confidence": 0.0-1.0,
  "reason": "Breve explicación de por qué está dentro o fuera del ámbito",
  "suggested_redirect": "Mensaje opcional para reconducir si es OFF_TOPIC"
}
```

Criterios:
- confidence > 0.8 → clasificación segura
- confidence 0.5-0.8 → dudoso, permitir pero monitorizar
- confidence < 0.5 → bloquear y reconducir
