# Usa una imagen base de Python
FROM python:3.10-slim

# Instala FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia los archivos del proyecto al contenedor
COPY . /app

# Instala las dependencias del proyecto
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto en el que se ejecutará tu aplicación
EXPOSE 8000

# Comando por defecto para ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
