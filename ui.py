# =============================================================================
# ui.py — Interfaz Gradio para CV Interactivo Ángel Nácar (Versión Avatar)
# =============================================================================

import gradio as gr
import os

# ── Configuración de Preguntas y Rutas ──────────────────────────────────────────

# SUGGESTED_QUESTIONS = [
#     "¿Cuál es tu experiencia con sistemas críticos?",
#     "¿Qué stack tecnológico dominas actualmente?",
#     "¿Cómo gestionas un equipo ágil como Scrum Master?",
#     "Cuéntame sobre tus proyectos de IA y automatización.",
#     "¿Qué certificaciones tienes en Cloud e IA?",
# ]

# Definimos la ruta del avatar (usando ruta absoluta para asegurar la carga en Gradio)
AVATAR_PATH = os.path.abspath(os.path.join("assets", "avatar.jpg"))
# Generic user avatar URL (Mystery Person de Gravatar)
AVATAR_USER = "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"

# Tu avatar local para el Bot
AVATAR_BOT = os.path.join("assets", "avatar.jpg")

# ── CSS Maestro (Responsivo, Estilo Matrix + Avatar) ───────────────────────

CUSTOM_CSS = """
/* Variables de Estilo */
:root {
    --matrix-green:     #00ff41;
    --matrix-green-dim: #00c832;
    --matrix-dark:      #0d0d0d;
    --matrix-panel:     #111411;
    --matrix-border:    #1a2e1a;
    --text-primary:     #e8f5e9;
    --text-secondary:   #4caf50;
    --accent-glow:      0 0 15px rgba(0,255,65,0.2);
    --avatar-size:      120px;
}

/* ─────────────────────────────────────────────────────────────────
   FIX CRÍTICO MOBILE #1 — Scroll global en iframe de HF Spaces
   El iframe de Hugging Face bloquea el scroll táctil si html/body
   tienen overflow implícito. Forzamos el modelo correcto.
───────────────────────────────────────────────────────────────── */
html {
    height: 100%;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch !important;
}
body {
    min-height: 100%;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch !important;
}

/* ─────────────────────────────────────────────────────────────────
   FIX CRÍTICO MOBILE #2 — Scroll táctil en el chatbot
   Gradio envuelve el historial en varios divs anidados.
   Cubrimos todos los selectores conocidos de Gradio 3.x / 4.x.
───────────────────────────────────────────────────────────────── */
#chatbot-container,
#chatbot-container > div,
#chatbot-container .wrap,
#chatbot-container .scroll-hide,
#chatbot-container [data-testid="bot"],
#chatbot-container .chatbot {
    overflow-y: auto !important;
    overflow-x: hidden !important;
    -webkit-overflow-scrolling: touch !important;  /* iOS momentum scroll */
    touch-action: pan-y !important;                /* Permite scroll vertical táctil */
    overscroll-behavior: contain !important;       /* Evita que el scroll se propague al iframe padre */
}

/* ─────────────────────────────────────────────────────────────────
   FIX CRÍTICO MOBILE #3 — Tablas en modo "espagueti"

   El problema: en móvil real, el contenedor del mensaje NO tiene
   overflow:auto, por lo que la tabla empuja el layout y se rompe.

   Solución en dos capas:
     a) El mensaje burbuja del bot se convierte en contenedor
        scrollable horizontal.
     b) La tabla se fuerza a bloque con overflow-x:auto propio.

   Usamos selectores amplios porque Gradio puede generar:
   .prose > table, .message > table, .bot > table, etc.
───────────────────────────────────────────────────────────────── */

/* Capa a: burbuja del bot como contenedor scrollable */
#chatbot-container .message.bot,
#chatbot-container .bot-row .message,
#chatbot-container [data-testid="bot"] .message,
#chatbot-container .bubble-wrap,
#chatbot-container .prose {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    max-width: 100% !important;
    /* Evita que el texto del bot empuje el layout */
    word-break: break-word !important;
    overflow-wrap: break-word !important;
}

/* Capa b: la tabla en sí, scrollable y con ancho mínimo por columna */
#chatbot-container table,
#chatbot-container .prose table,
#chatbot-container .message table,
#chatbot-container .bot table {
    display: block !important;
    width: max-content !important;   /* Se expande al ancho real de su contenido */
    max-width: 100% !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    touch-action: pan-x pan-y !important;
    border-collapse: collapse !important;
    margin: 12px 0 !important;
    /* Scrollbar Matrix-style */
    scrollbar-width: thin;
    scrollbar-color: var(--matrix-green) transparent;
}
#chatbot-container table::-webkit-scrollbar { height: 4px; }
#chatbot-container table::-webkit-scrollbar-thumb {
    background: var(--matrix-green-dim);
    border-radius: 10px;
}

/* Celdas: ancho mínimo para que el contenido respire */
#chatbot-container table th,
#chatbot-container table td {
    min-width: 120px !important;
    padding: 8px 12px !important;
    white-space: normal !important;
    word-break: normal !important;
    border: 1px solid var(--matrix-border) !important;
    vertical-align: top !important;
    font-size: 0.82rem !important;
    line-height: 1.4 !important;
}

#chatbot-container table th {
    background: rgba(0, 255, 65, 0.1) !important;
    color: var(--matrix-green) !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    white-space: nowrap !important;  /* Cabeceras en una línea para anclar el layout */
}

/* ─────────────────────────────────────────────────────────────────
   FIX MOBILE #4 — Input area y teclado virtual (iOS / Android)
   En móvil, el teclado virtual reduce el viewport y el input
   queda oculto. position:sticky lo mantiene visible.
───────────────────────────────────────────────────────────────── */
#input-area {
    background: var(--matrix-panel);
    padding: 20px;
    border: 1px solid var(--matrix-border);
    border-radius: 12px;
    /* Sticky para que el teclado no lo entierre */
    position: sticky !important;
    bottom: 0 !important;
    z-index: 10 !important;
}

/* Evitar zoom automático en iOS al hacer focus (font-size < 16px dispara zoom) */
#msg-input textarea {
    background: #000 !important;
    border: 1px solid var(--matrix-border) !important;
    color: var(--text-primary) !important;
    font-size: 16px !important;   /* ≥16px = sin zoom en iOS Safari */
    -webkit-text-size-adjust: 100% !important;
}

/* ─────────────────────────────────────────────────────────────────
   ESTILOS BASE (sin cambios respecto a la versión original)
───────────────────────────────────────────────────────────────── */
.gradio-container {
    background: var(--matrix-dark) !important;
    max-width: 1400px !important;
    width: 95% !important;
    margin: 0 auto !important;
    padding: 10px 0 !important;
    font-family: 'JetBrains Mono', monospace !important;
}

.contain { padding: 0 !important; }
.gap { gap: 15px !important; }

#cv-header {
    width: 100% !important;
    text-align: center;
    padding: 40px 20px;
    border: 1px solid var(--matrix-border);
    border-radius: 12px;
    background: var(--matrix-panel);
    box-shadow: var(--accent-glow);
    margin-bottom: 5px;
    box-sizing: border-box;
}

#header-avatar {
    width: var(--avatar-size);
    height: var(--avatar-size);
    border-radius: 50%;
    object-fit: cover;
    border: 3px solid var(--matrix-green);
    box-shadow: 0 0 25px rgba(0,255,65,0.5);
    margin-bottom: 20px;
}

#header-name {
    font-size: clamp(1.8rem, 5vw, 2.8rem);
    font-weight: 800;
    color: var(--matrix-green);
    letter-spacing: 4px;
    text-shadow: 0 0 20px rgba(0,255,65,0.4);
    margin: 0;
}

#header-title {
    font-size: clamp(0.9rem, 2.5vw, 1.2rem);
    color: var(--text-secondary);
    margin-top: 10px;
    margin-bottom: 20px;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.badge-container {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
}
.skill-badge {
    font-size: 0.75rem;
    padding: 4px 12px;
    border: 1px solid var(--matrix-green-dim);
    border-radius: 20px;
    color: var(--matrix-green);
    background: rgba(0,255,65,0.05);
}

#chatbot-container {
    background: var(--matrix-panel) !important;
    border: 1px solid var(--matrix-border) !important;
    border-radius: 12px !important;
}
#chatbot-container .message {
    font-size: 0.95rem !important;
    max-width: 100% !important;        /* Burbujas no se salen del contenedor */
    box-sizing: border-box !important;
}

#suggestions-row {
    display: flex !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    gap: 10px !important;
    padding: 5px 0 !important;
    scrollbar-width: none;
}
#suggestions-row::-webkit-scrollbar { display: none; }

.suggestion-btn {
    flex: 0 0 auto !important;
    background: #1a1a1a !important;
    border: 1px solid var(--matrix-border) !important;
    color: var(--text-secondary) !important;
    border-radius: 20px !important;
    padding: 5px 15px !important;
    transition: all 0.3s ease !important;
}
.suggestion-btn:hover {
    border-color: var(--matrix-green) !important;
    color: var(--matrix-green) !important;
    box-shadow: var(--accent-glow);
}

#send-btn {
    background: var(--matrix-green) !important;
    color: black !important;
    font-weight: bold !important;
    border-radius: 8px !important;
}
#clear-btn {
    background: transparent !important;
    color: #ff5555 !important;
    border: 1px solid #442222 !important;
    border-radius: 8px !important;
}

/* ─────────────────────────────────────────────────────────────────
   RESPONSIVE BREAKPOINTS
───────────────────────────────────────────────────────────────── */
@media (max-width: 600px) {
    :root { --avatar-size: 80px; }
    .gradio-container { width: 100% !important; padding: 0 !important; }
    #cv-header { padding: 20px 10px; border-radius: 0; }
    #input-area { border-radius: 0; padding: 12px; }

    /* En móvil las burbujas ocupan casi todo el ancho */
    #chatbot-container .message {
        max-width: 92% !important;
    }

    /* Reducir altura del chatbot en pantallas pequeñas
       para que el input quede siempre visible sin scroll de página */
    #chatbot-container {
        height: 55dvh !important;   /* dvh: dynamic viewport height, descuenta el teclado */
        min-height: 280px !important;
        border-radius: 0 !important;
    }

    /* Celdas aún más compactas en móvil */
    #chatbot-container table th,
    #chatbot-container table td {
        min-width: 90px !important;
        font-size: 0.75rem !important;
        padding: 6px 8px !important;
    }
}

@media (max-width: 380px) {
    :root { --avatar-size: 68px; }
    #header-name { letter-spacing: 2px; }
}
"""

# ── HTML de Componentes (Ahora con la imagen) ───────────────────────────

# Usamos file/ prefixed path para Gradio local.
HEADER_HTML = f"""
<div id="cv-header">
  <h1 id="header-name">ÁNGEL NÁCAR</h1>
  <p id="header-title">Senior Software Developer • Scrum Master • AI Engineer</p>
  <div class="badge-container">
    <span class="skill-badge">Java</span>
    <span class="skill-badge">Python</span>
    <span class="skill-badge">AWS</span>
    <span class="skill-badge">Oracle PL/SQL</span>
    <span class="skill-badge">LLM Agents</span>
    <span class="skill-badge">Madrid</span>
  </div>
</div>
"""

FOOTER_HTML = """
<div style="text-align: center; color: #333; font-size: 0.7rem; margin-top: 15px; font-family: sans-serif;">
  [ SYS ] CV INTERACTIVO v2.3 • GROQ + OLLAMA HYBRID PIPELINE
</div>
"""

# ── Construcción de la UI ──────────────────────────────────────────────────

def build_ui(chat_fn):
    # ── JS: Viewport meta + table-wrapper inyectados en runtime ────────────
    # Gradio en HF Spaces no expone el <head> directamente.
    # gr.HTML con <script> se ejecuta dentro del body pero es suficiente
    # para añadir el viewport meta (si no existe) y envolver tablas.
    MOBILE_FIX_JS = """
<script>
(function() {
  /* 1. Viewport meta — crítico para escala correcta en móvil real */
  if (!document.querySelector('meta[name="viewport"]')) {
    var m = document.createElement('meta');
    m.name    = 'viewport';
    m.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
    document.head.appendChild(m);
  }

  /* 2. Envolver tablas en un div scrollable.
     CSS puede hacer overflow:auto en la tabla, pero en algunos builds
     de Gradio el elemento padre tiene overflow:hidden implícito.
     Envolvemos cada tabla con un div dedicado que hace scroll. */
  function wrapTables() {
    var chatbot = document.getElementById('chatbot-container');
    if (!chatbot) return;
    chatbot.querySelectorAll('table').forEach(function(table) {
      if (table.parentElement.classList.contains('tbl-scroll-wrap')) return;
      var wrap = document.createElement('div');
      wrap.className = 'tbl-scroll-wrap';
      wrap.style.cssText = [
        'overflow-x:auto',
        '-webkit-overflow-scrolling:touch',
        'touch-action:pan-x pan-y',
        'max-width:100%',
        'margin:12px 0',
        'border-radius:4px'
      ].join(';');
      table.parentNode.insertBefore(wrap, table);
      wrap.appendChild(table);
      table.style.margin = '0';
    });
  }

  /* 3. Observer: detecta nuevas burbujas del bot y envuelve sus tablas */
  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(m) {
      if (m.addedNodes.length) wrapTables();
    });
  });

  /* Esperamos a que Gradio monte el DOM */
  document.addEventListener('DOMContentLoaded', function() {
    var target = document.getElementById('chatbot-container') || document.body;
    observer.observe(target, { childList: true, subtree: true });
    wrapTables();
  });

  /* Fallback por si DOMContentLoaded ya paso */
  if (document.readyState !== 'loading') {
    setTimeout(function() {
      var target = document.getElementById('chatbot-container') || document.body;
      observer.observe(target, { childList: true, subtree: true });
      wrapTables();
    }, 500);
  }
})();
</script>
"""

    with gr.Blocks(
        css=CUSTOM_CSS,
        title="Ángel Nácar — CV Interactivo",
        theme=gr.themes.Base()
    ) as app:

        # 0. JS de correcciones mobile (se inyecta primero, antes del DOM visible)
        gr.HTML(MOBILE_FIX_JS)

        # 1. Encabezado (con Avatar)
        gr.HTML(HEADER_HTML)

        # 2. Chatbot
        chatbot = gr.Chatbot(
            value=[{"role": "assistant", "content": "¡Hola! Soy Mebot, un proyecto agéntico de Ángel Nácar. ¿Qué te gustaría saber sobre él?"}],
            elem_id="chatbot-container",
            height=450,
            show_label=False,
            # avatar_images=(
            #      None,                         # usuario — sin avatar
            #     #  None,                         # bot — sin avatar (usamos ::before CSS)
            #     # Para habilitar tu foto real descomenta:
            #      "assets/avatar.jpg",
            # ),
            avatar_images=(AVATAR_USER, AVATAR_BOT), # Orden: (Usuario, Bot)
           # type="messages",
        )

        # # 3. Sugerencias
        # with gr.Row(elem_id="suggestions-row"):
        #     for q in SUGGESTED_QUESTIONS:
        #         btn = gr.Button(q, elem_classes=["suggestion-btn"], size="sm")
        #         # Lógica para autocompletar el textbox
        #         btn.click(fn=lambda x=q: x, outputs=[gr.State(q)]).then(
        #             fn=None, js=f"(q) => {{ document.querySelector('#msg-input textarea').value = '{q}'; }}"
        #         )

        # 4. Área de Entrada
        with gr.Column(elem_id="input-area"):
            msg = gr.Textbox(
                placeholder="Escribe tu pregunta aquí (ej. ¿Cuál es su experiencia en Java?)...",
                show_label=False,
                lines=1,
                elem_id="msg-input",
                max_lines=3,
                autofocus=True
            )
            with gr.Row():
                # clear_btn = gr.Button("↺ LIMPIAR", elem_id="clear-btn", scale=1)
                send_btn = gr.Button("ENVIAR", elem_id="send-btn", scale=4)

        gr.HTML(FOOTER_HTML)

        # ── Lógica de Interacción ──

        # def respond(message, history):
        #     if not message or message.strip() == "":
        #         return "", history
            
        #     # Obtener respuesta del agente
        #     reply = chat_fn(message, history)
            
        #     # Actualizar historial
        #     history.append({"role": "user", "content": message})
        #     history.append({"role": "assistant", "content": reply})
        #     return "", history

        def user_message(message, history):
            # Agrega el mensaje del usuario a la historia inmediatamente
            # y devuelve un string vacío para limpiar el input
            return "", history + [{"role": "user", "content": message}]

        def bot_message(history, chat_fn):
            # Toma el último mensaje del usuario (ya presente en history)
            user_query = history[-1]["content"]
            
            # Llama a tu función de IA
            bot_response = chat_fn(user_query, history[:-1])
            
            # Agrega la respuesta del bot a la historia
            history.append({"role": "assistant", "content": bot_response})
            return history

        # Eventos de envío
        # --- Lógica de Interacción Fluida ---
        
        # 1. Definimos qué pasa cuando el usuario envía
        submit_event = msg.submit(
            fn=user_message, 
            inputs=[msg, chatbot], 
            outputs=[msg, chatbot], 
            queue=False # Importante para que sea instantáneo
        ).then(
            fn=lambda h: bot_message(h, chat_fn),
            inputs=[chatbot],
            outputs=[chatbot]
        )

        # 2. Lo mismo para el botón de enviar
        send_btn.click(
            fn=user_message, 
            inputs=[msg, chatbot], 
            outputs=[msg, chatbot], 
            queue=False
        ).then(
            fn=lambda h: bot_message(h, chat_fn),
            inputs=[chatbot],
            outputs=[chatbot]
        )
        # msg.submit(respond, [msg, chatbot], [msg, chatbot])
        # send_btn.click(respond, [msg, chatbot], [msg, chatbot])

        # Evento de limpieza
        # clear_btn.click(
        #     lambda: (None, [{"role": "assistant", "content": "Conversación reiniciada. ¿En qué más puedo ayudarte?"}]),
        #     outputs=[msg, chatbot]
        # )

    return app

# Testing Standalone
if __name__ == "__main__":
    def mock_chat(msg, hist): return f"Has preguntado: **{msg}**. Esta es una respuesta de prueba simulando al agente."
    
    # # IMPORTANTE: AVISAR A GRADIO QUE PERMITA EL ACCESO A LA CARPETA 'assets'
    # build_ui(mock_chat).launch(allowed_paths=[os.path.dirname(AVATAR_PATH)])