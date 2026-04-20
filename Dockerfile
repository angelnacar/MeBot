# Partimos de la imagen ligera de Python
FROM python:3.11-slim

# Creamos un usuario para evitar ejecutar como root (Requisito de HF)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Definimos el directorio de trabajo en la carpeta personal del usuario
WORKDIR /app

# Instalamos dependencias
# Copiamos primero para aprovechar la caché de Docker
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copiamos el resto del código
COPY --chown=user . .

# Puerto obligatorio para Hugging Face
EXPOSE 7860

# Comando para iniciar la aplicación
CMD ["python", "chat_optimized_Hybrid.py"]
