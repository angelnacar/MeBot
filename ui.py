"""
CV Interactivo — Interfaz Terminal Matrix (RESPONSIVE)
Ángel Nácar Jiménez — AI Agent Profile

Optimizado para mobile-first: tablas con scroll horizontal,
header adaptativo, input zone apilada en móvil, media queries
completos para xs/sm/md/lg.
"""

import gradio as gr

# ── Paleta y variables CSS ──────────────────────────────────────────────────

_CSS = """
/* ══════════════════════════════════════════════════════════════
   IMPORTS & RESET
══════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');

:root {
    --matrix-black:    #000000;
    --matrix-dark:     #050f05;
    --matrix-mid:      #0a1a0a;
    --matrix-panel:    #0d1f0d;
    --matrix-border:   #1a4a1a;
    --matrix-green:    #00ff41;
    --matrix-green-2:  #00cc33;
    --matrix-green-3:  #008f11;
    --matrix-green-dim:#003b00;
    --matrix-amber:    #ffaa00;
    --matrix-red:      #ff3333;
    --matrix-white:    #e0ffe0;
    --font-mono:       'Share Tech Mono', 'Courier New', monospace;
    --font-display:    'Orbitron', monospace;
    --scanline-opacity: 0.03;
    --glow-sm: 0 0 6px var(--matrix-green), 0 0 12px rgba(0,255,65,0.3);
    --glow-md: 0 0 10px var(--matrix-green), 0 0 25px rgba(0,255,65,0.4), 0 0 50px rgba(0,255,65,0.1);
    --glow-lg: 0 0 15px var(--matrix-green), 0 0 40px rgba(0,255,65,0.5), 0 0 80px rgba(0,255,65,0.2);
    /* Responsive font scale */
    --fs-xs:   0.6rem;
    --fs-sm:   0.7rem;
    --fs-base: 0.85rem;
    --fs-lg:   1.0rem;
    --fs-xl:   1.25rem;
}

/* ══════════════════════════════════════════════════════════════
   BASE
══════════════════════════════════════════════════════════════ */

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body, .gradio-container, #root {
    background: var(--matrix-black) !important;
    color: var(--matrix-green) !important;
    font-family: var(--font-mono) !important;
    min-height: 100vh;
    overflow-x: hidden; /* evita scroll horizontal en body */
}

/* Scanlines overlay */
.gradio-container::before {
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,255,65, var(--scanline-opacity)) 2px,
        rgba(0,255,65, var(--scanline-opacity)) 4px
    );
    pointer-events: none;
    z-index: 9999;
    animation: scanRoll 8s linear infinite;
}

@keyframes scanRoll {
    from { background-position: 0 0; }
    to   { background-position: 0 400px; }
}

/* Vignette */
.gradio-container::after {
    content: '';
    position: fixed;
    inset: 0;
    background: radial-gradient(ellipse at center,
        transparent 50%,
        rgba(0,0,0,0.7) 100%
    );
    pointer-events: none;
    z-index: 9998;
}

/* ══════════════════════════════════════════════════════════════
   LAYOUT PRINCIPAL — mobile-first
══════════════════════════════════════════════════════════════ */

.main-container {
    width: 100%;
    max-width: 960px;
    margin: 0 auto;
    padding: 12px 8px;
    position: relative;
}

@media (min-width: 480px) {
    .main-container { padding: 16px 12px; }
}

@media (min-width: 768px) {
    .main-container { padding: 24px 16px; }
}

/* ══════════════════════════════════════════════════════════════
   HEADER — responsivo
══════════════════════════════════════════════════════════════ */

.terminal-header {
    border: 1px solid var(--matrix-border);
    background: var(--matrix-panel);
    padding: 12px;
    margin-bottom: 0;
    position: relative;
    overflow: hidden;
}

@media (min-width: 480px) {
    .terminal-header { padding: 16px; }
}

@media (min-width: 768px) {
    .terminal-header { padding: 20px 24px; }
}

.terminal-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg,
        transparent, var(--matrix-green), var(--matrix-green-2), transparent
    );
    animation: borderScan 3s ease-in-out infinite;
}

@keyframes borderScan {
    0%, 100% { opacity: 0.3; }
    50%       { opacity: 1; box-shadow: var(--glow-sm); }
}

/* En móvil el header se apila verticalmente */
.header-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    text-align: center;
}

@media (min-width: 480px) {
    .header-inner {
        flex-direction: row;
        align-items: center;
        text-align: left;
        gap: 16px;
    }
}

@media (min-width: 768px) {
    .header-inner { gap: 24px; }
}

/* Avatar */
.avatar-frame {
    flex-shrink: 0;
    width: 64px;
    height: 64px;
    border: 2px solid var(--matrix-green-3);
    position: relative;
    box-shadow: var(--glow-sm);
    background: var(--matrix-dark);
    overflow: hidden;
}

@media (min-width: 480px) {
    .avatar-frame { width: 72px; height: 72px; }
}

@media (min-width: 768px) {
    .avatar-frame { width: 90px; height: 90px; }
}

.avatar-frame::before,
.avatar-frame::after {
    content: '';
    position: absolute;
    width: 10px; height: 10px;
    border-color: var(--matrix-green);
    border-style: solid;
    z-index: 2;
}
.avatar-frame::before { top: -1px; left: -1px; border-width: 2px 0 0 2px; }
.avatar-frame::after  { bottom: -1px; right: -1px; border-width: 0 2px 2px 0; }

.avatar-placeholder {
    width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-display);
    font-size: 22px;
    font-weight: 900;
    color: var(--matrix-green);
    text-shadow: var(--glow-md);
    background: linear-gradient(135deg, var(--matrix-dark), var(--matrix-mid));
    letter-spacing: 2px;
    animation: avatarPulse 4s ease-in-out infinite;
}

@media (min-width: 768px) {
    .avatar-placeholder { font-size: 28px; }
}

@keyframes avatarPulse {
    0%, 100% { text-shadow: var(--glow-sm); }
    50%       { text-shadow: var(--glow-lg); }
}

.avatar-frame img {
    width: 100%; height: 100%;
    object-fit: cover;
    object-position: center top;
    filter: sepia(0.2) hue-rotate(80deg) saturate(1.5) brightness(0.9);
    display: none;
}

/* Info del header */
.header-info { flex: 1; min-width: 0; }

.header-title {
    font-family: var(--font-display);
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--matrix-green);
    text-shadow: var(--glow-sm);
    letter-spacing: 2px;
    text-transform: uppercase;
    line-height: 1.2;
    word-break: break-word;
}

@media (min-width: 480px) {
    .header-title { font-size: 1.05rem; letter-spacing: 2px; }
}

@media (min-width: 768px) {
    .header-title { font-size: 1.25rem; letter-spacing: 3px; }
}

.header-subtitle {
    font-family: var(--font-mono);
    font-size: 0.62rem;
    color: var(--matrix-green-3);
    letter-spacing: 1px;
    margin-top: 4px;
    text-transform: uppercase;
    word-break: break-word;
}

@media (min-width: 480px) {
    .header-subtitle { font-size: 0.68rem; letter-spacing: 1.5px; }
}

@media (min-width: 768px) {
    .header-subtitle { font-size: 0.75rem; letter-spacing: 2px; }
}

.header-status {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
    font-size: 0.6rem;
    color: var(--matrix-green-3);
    letter-spacing: 1px;
}

@media (min-width: 480px) {
    .header-status { justify-content: flex-start; }
}

.status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--matrix-green);
    box-shadow: var(--glow-sm);
    animation: blink 1.2s step-start infinite;
    flex-shrink: 0;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
}

/* Meta (tech stack) — oculto en xs, visible desde sm */
.header-meta {
    display: none;
    text-align: right;
    font-size: 0.6rem;
    color: var(--matrix-green-dim);
    letter-spacing: 1px;
    line-height: 1.8;
    flex-shrink: 0;
}

@media (min-width: 560px) {
    .header-meta { display: block; font-size: 0.62rem; }
}

@media (min-width: 768px) {
    .header-meta { font-size: 0.65rem; }
}

/* ══════════════════════════════════════════════════════════════
   BARRA TERMINAL
══════════════════════════════════════════════════════════════ */

.terminal-bar {
    background: var(--matrix-panel);
    border: 1px solid var(--matrix-border);
    border-top: none;
    padding: 6px 10px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.58rem;
    color: var(--matrix-green-3);
    letter-spacing: 1px;
    text-transform: uppercase;
    overflow: hidden;
}

@media (min-width: 480px) {
    .terminal-bar { padding: 7px 14px; letter-spacing: 2px; font-size: 0.62rem; }
}

.terminal-bar-dots { display: flex; gap: 5px; flex-shrink: 0; }
.terminal-bar-dot  { width: 8px; height: 8px; border-radius: 50%; }
.dot-red    { background: var(--matrix-red);   box-shadow: 0 0 4px var(--matrix-red); }
.dot-amber  { background: var(--matrix-amber); box-shadow: 0 0 4px var(--matrix-amber); }
.dot-green  { background: var(--matrix-green); box-shadow: 0 0 4px var(--matrix-green); }

.terminal-bar-title {
    flex: 1;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* En móvil muy pequeño abreviamos el título vía CSS */
.terminal-bar-title .title-short { display: inline; }
.terminal-bar-title .title-full  { display: none; }

@media (min-width: 560px) {
    .terminal-bar-title .title-short { display: none; }
    .terminal-bar-title .title-full  { display: inline; }
}

/* ══════════════════════════════════════════════════════════════
   VENTANA DE CHAT
══════════════════════════════════════════════════════════════ */

.chat-wrapper {
    border: 1px solid var(--matrix-border);
    border-top: none;
    background: var(--matrix-dark);
    position: relative;
    overflow: hidden;
}

#angel-chat {
    background: var(--matrix-dark) !important;
    border: none !important;
    border-radius: 0 !important;
}

#angel-chat .message-wrap,
#angel-chat > div:first-child {
    background: transparent !important;
    padding: 12px !important;
}

@media (min-width: 480px) {
    #angel-chat .message-wrap,
    #angel-chat > div:first-child { padding: 16px !important; }
}

/* Scrollbar */
#angel-chat ::-webkit-scrollbar { width: 4px; }
#angel-chat ::-webkit-scrollbar-track { background: var(--matrix-dark); }
#angel-chat ::-webkit-scrollbar-thumb {
    background: var(--matrix-green-3);
    box-shadow: var(--glow-sm);
}

/* ── Burbujas ── */

#angel-chat .user {
    background: transparent !important;
    border: 1px solid var(--matrix-green-3) !important;
    border-radius: 0 !important;
    color: var(--matrix-green-2) !important;
    font-family: var(--font-mono) !important;
    font-size: var(--fs-base) !important;
    padding: 8px 10px !important;
    margin-bottom: 10px !important;
    position: relative;
    word-break: break-word;
    overflow-wrap: break-word;
}

@media (min-width: 480px) {
    #angel-chat .user { padding: 10px 14px !important; }
}

#angel-chat .user::before {
    content: '> USER:';
    display: block;
    font-size: var(--fs-xs);
    color: var(--matrix-green-3);
    letter-spacing: 2px;
    margin-bottom: 4px;
}

#angel-chat .bot {
    background: var(--matrix-panel) !important;
    border: 1px solid var(--matrix-green-dim) !important;
    border-left: 3px solid var(--matrix-green) !important;
    border-radius: 0 !important;
    color: var(--matrix-white) !important;
    font-family: var(--font-mono) !important;
    font-size: var(--fs-base) !important;
    padding: 8px 10px !important;
    margin-bottom: 10px !important;
    box-shadow: inset 0 0 20px rgba(0,255,65,0.02);
    line-height: 1.7;
    word-break: break-word;
    overflow-wrap: break-word;
    /* Importante: permite que el contenido interno gestione su overflow */
    overflow: hidden;
}

@media (min-width: 480px) {
    #angel-chat .bot { padding: 10px 14px !important; }
}

#angel-chat .bot::before {
    content: '> Angel.dev:';
    display: block;
    font-size: var(--fs-xs);
    color: var(--matrix-green);
    letter-spacing: 2px;
    margin-bottom: 4px;
    text-shadow: var(--glow-sm);
}

/* ── TABLAS RESPONSIVE — solución clave para móvil ── */

/*
   Gradio renderiza markdown dentro de .bot > .prose (o similar).
   Envolvemos las tablas en un contenedor con scroll horizontal.
   El truco: hacer que el elemento table no fuerce el ancho del padre.
*/

#angel-chat .bot table,
#angel-chat .message-wrap table,
.gradio-container table {
    display: block !important;          /* table → block para poder aplicar overflow */
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;  /* scroll suave en iOS */
    max-width: 100% !important;
    width: max-content !important;      /* toma el ancho natural del contenido */
    min-width: 100%;                    /* al menos ocupa todo el ancho disponible */
    border-collapse: collapse !important;
    font-size: 0.75rem !important;
    margin: 8px 0 !important;
    /* Scrollbar visible y estilizada */
    scrollbar-width: thin;
    scrollbar-color: var(--matrix-green-3) var(--matrix-dark);
}

#angel-chat .bot table::-webkit-scrollbar {
    height: 4px;
}
#angel-chat .bot table::-webkit-scrollbar-track {
    background: var(--matrix-dark);
}
#angel-chat .bot table::-webkit-scrollbar-thumb {
    background: var(--matrix-green-3);
}

#angel-chat .bot th,
#angel-chat .message-wrap th,
.gradio-container th {
    background: var(--matrix-panel) !important;
    color: var(--matrix-green) !important;
    border: 1px solid var(--matrix-border) !important;
    padding: 5px 8px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.7rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    white-space: nowrap !important;  /* cabeceras no rompen */
    text-shadow: var(--glow-sm);
}

#angel-chat .bot td,
#angel-chat .message-wrap td,
.gradio-container td {
    border: 1px solid var(--matrix-green-dim) !important;
    padding: 4px 8px !important;
    color: var(--matrix-white) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.72rem !important;
    vertical-align: top;
}

/* Filas alternas */
#angel-chat .bot tr:nth-child(even) td {
    background: rgba(0,255,65,0.03) !important;
}

/* ── Código inline y bloques ── */

#angel-chat .bot code,
#angel-chat .bot pre {
    font-family: var(--font-mono) !important;
    font-size: 0.8rem !important;
    background: var(--matrix-mid) !important;
    color: var(--matrix-green-2) !important;
    border: 1px solid var(--matrix-green-dim) !important;
    border-radius: 0 !important;
}

#angel-chat .bot pre {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    padding: 8px 10px !important;
    max-width: 100% !important;
    white-space: pre !important;
    scrollbar-width: thin;
    scrollbar-color: var(--matrix-green-3) var(--matrix-dark);
}

#angel-chat .bot code {
    padding: 1px 4px !important;
}

/* Typing indicator */
#angel-chat .thinking,
#angel-chat .generating {
    color: var(--matrix-green-3) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.8rem !important;
    animation: cursorBlink 0.8s step-start infinite;
}

@keyframes cursorBlink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
}

/* ══════════════════════════════════════════════════════════════
   INPUT ZONE — apilada en móvil
══════════════════════════════════════════════════════════════ */

.input-zone {
    border: 1px solid var(--matrix-border);
    border-top: none;
    background: var(--matrix-panel);
    padding: 8px !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 6px !important;
    align-items: stretch !important;
}

@media (min-width: 600px) {
    .input-zone {
        flex-direction: row !important;
        align-items: flex-end !important;
        gap: 8px !important;
        padding: 10px 12px !important;
    }
}

/* Prompt label: oculto en móvil muy pequeño, visible en sm+ */
.input-prompt-label {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--matrix-green);
    text-shadow: var(--glow-sm);
    white-space: nowrap;
    flex-shrink: 0;
    /* En móvil lo ponemos inline encima del input */
    padding-bottom: 0;
    display: none;
}

@media (min-width: 600px) {
    .input-prompt-label {
        display: block;
        padding-bottom: 12px;
    }
}

/* Contenedor de botones en móvil: fila horizontal */
.btn-row {
    display: flex;
    gap: 6px;
}

@media (min-width: 600px) {
    .btn-row {
        flex-direction: column;
        gap: 6px;
    }
}

/* Textarea */
#angel-input textarea,
#angel-input input {
    background: var(--matrix-dark) !important;
    border: 1px solid var(--matrix-green-3) !important;
    border-radius: 0 !important;
    color: var(--matrix-green) !important;
    font-family: var(--font-mono) !important;
    font-size: var(--fs-base) !important;
    caret-color: var(--matrix-green);
    padding: 10px 12px !important;
    resize: none !important;
    outline: none !important;
    transition: border-color 0.2s, box-shadow 0.2s;
    width: 100% !important;
    /* Mejora touch en iOS */
    -webkit-appearance: none;
}

#angel-input textarea:focus,
#angel-input input:focus {
    border-color: var(--matrix-green) !important;
    box-shadow: var(--glow-sm) !important;
}

#angel-input textarea::placeholder,
#angel-input input::placeholder {
    color: var(--matrix-green-dim) !important;
    font-style: italic;
}

/* Botón SEND */
#angel-submit {
    background: transparent !important;
    border: 1px solid var(--matrix-green) !important;
    border-radius: 0 !important;
    color: var(--matrix-green) !important;
    font-family: var(--font-display) !important;
    font-size: 0.62rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 10px 14px !important;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
    min-width: 0;
    flex: 1;        /* en móvil ocupa el espacio disponible */
    /* min-height para área táctil cómoda */
    min-height: 44px;
}

@media (min-width: 600px) {
    #angel-submit {
        flex: none;
        min-width: 80px;
        min-height: auto;
    }
}

#angel-submit:hover {
    background: var(--matrix-green-dim) !important;
    box-shadow: var(--glow-sm) !important;
    color: var(--matrix-green) !important;
}

#angel-submit:active {
    background: rgba(0,255,65,0.2) !important;
}

/* Botón CLR */
#angel-clear {
    background: transparent !important;
    border: 1px solid var(--matrix-green-dim) !important;
    border-radius: 0 !important;
    color: var(--matrix-green-3) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.62rem !important;
    letter-spacing: 2px !important;
    padding: 8px 12px !important;
    cursor: pointer;
    transition: all 0.15s;
    min-height: 44px;
    white-space: nowrap;
}

@media (min-width: 600px) {
    #angel-clear { min-height: auto; }
}

#angel-clear:hover {
    border-color: var(--matrix-red) !important;
    color: var(--matrix-red) !important;
}

/* ══════════════════════════════════════════════════════════════
   FOOTER
══════════════════════════════════════════════════════════════ */

.terminal-footer {
    display: flex;
    flex-wrap: wrap;               /* evita overflow en xs */
    justify-content: space-between;
    align-items: center;
    gap: 4px;
    padding: 6px 0;
    font-size: 0.55rem;
    color: var(--matrix-green-dim);
    letter-spacing: 1px;
    border-top: 1px solid var(--matrix-green-dim);
    margin-top: 8px;
}

@media (min-width: 480px) {
    .terminal-footer { font-size: 0.6rem; letter-spacing: 1.5px; }
}

.footer-left {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

@media (min-width: 480px) {
    .footer-left { gap: 16px; }
}

.footer-pulse { animation: blink 2s step-start infinite; }

/* ══════════════════════════════════════════════════════════════
   RAIN CANVAS
══════════════════════════════════════════════════════════════ */

#matrix-rain {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    z-index: -1;
    opacity: 0.08;
    pointer-events: none;
}

/* ══════════════════════════════════════════════════════════════
   HIDE GRADIO CHROME innecesario
══════════════════════════════════════════════════════════════ */

.gradio-container .prose h1,
footer.svelte-1rjryqp,
.built-with { display: none !important; }

.gradio-container button,
.gradio-container input,
.gradio-container textarea {
    font-family: var(--font-mono) !important;
}

.gradio-container .block,
.gradio-container .form {
    border-radius: 0 !important;
    border-color: var(--matrix-border) !important;
    background: transparent !important;
}

/* Eliminar padding extra de Gradio en el wrapper de columnas */
.gradio-container .gap,
.gradio-container .padding {
    gap: 0 !important;
}
"""

# ── HTML extra (canvas rain + JS) ──────────────────────────────────────────

_HEADER_HTML = """
<canvas id="matrix-rain"></canvas>

<div class="main-container">
  <div class="terminal-header">
    <div class="header-inner">

      <div class="avatar-frame" id="avatar-frame">
        <img src="/file=assets/avatar.jpg" id="avatar-img" alt="Ángel Nácar">
        <div class="avatar-placeholder" id="avatar-placeholder">ÁN</div>
      </div>

      <div class="header-info">
        <div class="header-title">Ángel Nácar Jiménez</div>
        <div class="header-subtitle">Senior Software Developer &amp; Scrum Master</div>
        <div class="header-status">
          <span class="status-dot"></span>
          <span>SYSTEM ONLINE</span>
          <span style="margin-left:8px; color:var(--matrix-green-dim)">|</span>
          <span style="margin-left:8px">MADRID, ES</span>
        </div>
      </div>

      <div class="header-meta">
        <div>Java · Python · Cloud · IA</div>
        <div style="color:var(--matrix-green-3); margin-top:4px">AWS CERTIFIED</div>
      </div>

    </div>
  </div>
</div>

<script>
// ── Matrix rain — columnas adaptadas al viewport ─────────────
(function(){
  const canvas = document.getElementById('matrix-rain');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()アイウエオカキクケコサシスセソ';
  let cols, drops, fontSize;

  function resize(){
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
    // Tamaño de fuente adaptado: más pequeño en móvil
    fontSize = window.innerWidth < 480 ? 11 : (window.innerWidth < 768 ? 13 : 15);
    cols  = Math.floor(canvas.width / (fontSize + 2));
    drops = Array(cols).fill(1);
  }

  function draw(){
    ctx.fillStyle = 'rgba(0,0,0,0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const step = fontSize + 2;
    for (let i = 0; i < cols; i++){
      const ch = chars[Math.floor(Math.random() * chars.length)];
      const isHead = drops[i] * step < step * 2;
      ctx.fillStyle = isHead ? '#ffffff' : (Math.random() > 0.1 ? '#00ff41' : '#00cc33');
      ctx.font = fontSize + 'px "Share Tech Mono", monospace';
      ctx.fillText(ch, i * step, drops[i] * step);
      if (drops[i] * step > canvas.height && Math.random() > 0.975){
        drops[i] = 0;
      }
      drops[i]++;
    }
  }

  resize();
  // Debounce resize para evitar recalculos excesivos
  let resizeTimer;
  window.addEventListener('resize', function(){
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 200);
  });
  setInterval(draw, 45);
})();

// ── Avatar ─────────────────────────────────────────────────────
(function(){
  const img = document.getElementById('avatar-img');
  const placeholder = document.getElementById('avatar-placeholder');
  if (!img || !placeholder) return;
  img.onload  = () => { img.style.display = 'block'; placeholder.style.display = 'none'; };
  img.onerror = () => { img.style.display = 'none';  placeholder.style.display = 'flex'; };
})();
</script>
"""

_TERMINAL_BAR_HTML = """
<div class="terminal-bar">
  <div class="terminal-bar-dots">
    <div class="terminal-bar-dot dot-red"></div>
    <div class="terminal-bar-dot dot-amber"></div>
    <div class="terminal-bar-dot dot-green"></div>
  </div>
  <div class="terminal-bar-title">
    <span class="title-short">TERMINAL v2.0</span>
    <span class="title-full">angel_cv.dev — INTERACTIVE TERMINAL v2.0</span>
  </div>
</div>
"""

_FOOTER_HTML = """
<div class="terminal-footer">
  <div class="footer-left">
    <span>SYS: ACTIVE</span>
    <span>MODEL: KIMI-K2</span>
    <span>EVAL: ON</span>
  </div>
  <div>
    <span class="footer-pulse">█</span>
    <span style="margin-left:6px">AGUARDANDO INPUT...</span>
  </div>
</div>
"""

# ── Construcción de la interfaz ─────────────────────────────────────────────

def build_ui(chat_fn):
    """
    Construye y retorna el gr.Blocks con la interfaz Matrix responsive.

    Uso:
        from ui import build_ui
        from chat_optimized import chat
        app = build_ui(chat)
        app.launch()
    """
    with gr.Blocks(
        css=_CSS,
        title="Ángel Nácar — CV Interactivo",
        theme=gr.themes.Base(
            primary_hue="green",
            neutral_hue="green",
            font=gr.themes.GoogleFont("Share Tech Mono"),
        ),
    ) as demo:

        # Header con canvas y rain
        gr.HTML(_HEADER_HTML)

        # Barra de título estilo terminal
        gr.HTML(_TERMINAL_BAR_HTML)

        # Ventana de chat
        chatbot = gr.Chatbot(
            elem_id="angel-chat",
            height=420,
            show_label=False,
            avatar_images=(
                None,
                "assets/avatar.jpg",
            ),
            placeholder=(
                "<div style='text-align:center; color:var(--matrix-green-3); "
                "font-family:var(--font-mono); padding:40px; letter-spacing:2px;'>"
                "[ SISTEMA LISTO — INICIANDO SESIÓN... ]<br><br>"
                "Pregúntame sobre mi experiencia, proyectos o stack tecnológico."
                "</div>"
            ),
        )

        # Zona de input — Row sin gap para control total vía CSS
        with gr.Row(elem_classes=["input-zone"]):
            gr.HTML("<div class='input-prompt-label'>$&gt;&nbsp;</div>")

            msg_input = gr.Textbox(
                elem_id="angel-input",
                placeholder="Escribe tu mensaje y pulsa ENTER o SEND...",
                show_label=False,
                lines=1,
                max_lines=4,
                scale=10,
                submit_btn=False,
                autofocus=True,
            )

            send_btn = gr.Button(
                "SEND",
                elem_id="angel-submit",
                scale=1,
                min_width=70,
            )

            clear_btn = gr.Button(
                "CLR",
                elem_id="angel-clear",
                scale=1,
                min_width=50,
            )

        # Footer
        gr.HTML(_FOOTER_HTML)

        # ── Lógica de interacción ──────────────────────────────

        def respond(message: str, history: list):
            if not message or not message.strip():
                return history, ""
            history = history or []
            history.append({"role": "user", "content": message})
            reply = chat_fn(message, history[:-1])
            history.append({"role": "assistant", "content": reply})
            return history, ""

        send_btn.click(
            fn=respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        )

        msg_input.submit(
            fn=respond,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
        )

        clear_btn.click(
            fn=lambda: ([], ""),
            outputs=[chatbot, msg_input],
        )

    return demo


# ── Ejecución directa ───────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from chat_optimized_Hybrid import chat
    except ImportError:
        def chat(message: str, history: list) -> str:
            return (
                f"[STUB] Recibido: {message!r}\n"
                "Conecta chat_optimized_Hybrid.py para activar el agente real."
            )

    app = build_ui(chat)
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_api=False,
    )
