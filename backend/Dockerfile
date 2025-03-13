# Usa Python 3.9 como base
FROM python:3.9

# Define el directorio de trabajo en el contenedor
WORKDIR /app

# Copia el archivo de dependencias primero
COPY requirements.txt /app/requirements.txt

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Luego copia el resto de la aplicación
COPY ./app /app

# Expone el puerto de FastAPI
EXPOSE 8000

# Comando por defecto para iniciar FastAPI (se sobreescribirá en docker-compose.yml para otros servicios)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
