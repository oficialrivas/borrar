from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

# Crear la instancia de la aplicación FastAPI
app = FastAPI()

# Definir la ruta de la carpeta `static/`
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

# Asegurar que la carpeta existe
os.makedirs(STATIC_DIR, exist_ok=True)

# Montar la carpeta `static/` en la ruta `/static`
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    return {"message": "Servicio de archivos estáticos funcionando correctamente"}
