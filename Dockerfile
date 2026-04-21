# Partimos de la imagen ligera de Python
FROM python:3.12-slim

# Creamos un usuario para evitar ejecutar como root (Requisito de HF)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Definimos el directorio de trabajo en la carpeta personal del usuario
WORKDIR /app

# Copiamos todos los archivos primero
COPY --chown=user . .

# Instalamos el paquete y sus dependencias
RUN pip install --no-cache-dir --user .

# Puerto obligatorio para Hugging Face
EXPOSE 7860

# Comando para iniciar la aplicación
CMD ["python", "main.py"]
