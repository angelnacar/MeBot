# Input Guard — Mebot

Evalúa el siguiente mensaje del usuario en dos dimensiones simultáneas: **tópico** y **toxicidad**.

## Ámbito permitido (topic: ACCEPTABLE)

**Perfil profesional de Ángel Nácar Jiménez:**
- Experiencia laboral, empresas, proyectos
- Habilidades técnicas, stack tecnológico
- Formación, certificaciones, metodologías

**Contacto:**
- Cómo contactar, disponibilidad para oportunidades

**Saludos y cortesía:**
- "Hola", "buenos días", "gracias", "¿quién eres?", "¿qué haces?"

**IA y automatización:**
- Proyectos de IA (SiliconMind, agentes), arquitectura de sistemas autónomos, automatización

## Ámbito NO permitido (topic: OFF_TOPIC)

- Matemáticas u operaciones aritméticas (a menos que sea sobre proyectos reales de Ángel)
- Tecnología general no relacionada con la experiencia de Ángel
- Política, religión, temas personales ajenos al perfil
- Juegos, entretenimiento, ocio
- Consejos profesionales genéricos no específicos de Ángel
- Preguntas sobre el funcionamiento interno del asistente

## Criterios de toxicidad

- toxicity_score 0.0–0.3: Mensaje completamente aceptable
- toxicity_score 0.3–0.7: Potencialmente problemático (contexto dependiente)
- toxicity_score 0.7–1.0: Claramente tóxico o inapropiado (debe bloquearse)

---

**Mensaje del usuario:**
{{ message }}

**Historial de conversación:**
{{ history }}

---

Responde ÚNICAMENTE con JSON válido, sin texto adicional:

```json
{
  "topic": "ACCEPTABLE | OFF_TOPIC",
  "topic_confidence": 0.0,
  "toxicity": "ACCEPTABLE | NOT_ACCEPTABLE",
  "toxicity_score": 0.0,
  "reason": "Explicación breve de ambas evaluaciones",
  "suggested_redirect": "Mensaje de reconducción si es OFF_TOPIC, cadena vacía si no aplica"
}
```

Criterios de confianza de tópico:
- topic_confidence ≥ 0.5 con topic OFF_TOPIC → bloquear y reconducir
- topic_confidence < 0.5 → duda razonable, permitir
