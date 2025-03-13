import asyncio
import logging
from fastapi import FastAPI
from auth.routes import router as auth_router
from automatizados.routes import router as auto_tasks_router
from routes.start_task import router as start_task_router
from routes.task_status import router as task_status_router
from routes.notifications import router as notifications_router  # ✅ Agregamos el módulo de notificaciones
from task_scheduler import verificar_tareas_programadas

# Configurar logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """
    Inicia el proceso de verificación de tareas al levantar FastAPI.
    """
    asyncio.create_task(verificar_tareas_programadas())

# Incluir rutas de autenticación y notificaciones
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(auto_tasks_router)
app.include_router(start_task_router)
app.include_router(task_status_router)
app.include_router(notifications_router)  # ✅ Se agrega la nueva ruta

