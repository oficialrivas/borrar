import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from auth.dependencies import get_current_user
from tasks import ejecutar_scraper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# 📌 Modelos de datos
class TaskRequestAll(BaseModel):
    nombre: str
    apellido: str


class TaskRequestSelected(BaseModel):
    nombre: str
    apellido: str
    listas: List[str]


class TaskRequestNationality(BaseModel):
    nacionalidad: str
    numero: str


# 📌 Endpoint para iniciar una búsqueda en todas las listas
@router.post("/start-task/")
def start_task(request: TaskRequestAll, current_user: dict = Depends(get_current_user)):
    user_uuid = current_user["uuid"]
    logger.info(f"📨 Enviando tarea para usuario {user_uuid}: {request.nombre} {request.apellido}")

    task = ejecutar_scraper.apply_async(args=[user_uuid, request.nombre, request.apellido, None])
    return {"task_id": task.id, "status": "Task started", "uuid": user_uuid}


# 📌 Endpoint para iniciar una búsqueda en listas seleccionadas
@router.post("/start-task-list/")
def start_task_list(request: TaskRequestSelected, current_user: dict = Depends(get_current_user)):
    user_uuid = current_user["uuid"]
    listas_validas = {"roja", "amarilla", "ramajudicial", "ventanavirtual"}

    listas_seleccionadas = [lista for lista in request.listas if lista in listas_validas]

    if not listas_seleccionadas:
        raise HTTPException(status_code=400, detail="No se seleccionaron listas válidas.")

    logger.info(f"📨 Enviando tarea para usuario {user_uuid}: {request.nombre} {request.apellido}, Listas: {listas_seleccionadas}")

    task = ejecutar_scraper.apply_async(args=[user_uuid, request.nombre, request.apellido, listas_seleccionadas])

    return {"task_id": task.id, "status": "Task started", "uuid": user_uuid, "listas": listas_seleccionadas}


# 📌 Endpoint para iniciar una búsqueda por número y nacionalidad
@router.post("/start-task-nationality/")
def start_task_nationality(request: TaskRequestNationality, current_user: dict = Depends(get_current_user)):
    user_uuid = current_user["uuid"]
    logger.info(f"📨 Enviando tarea para usuario {user_uuid}: {request.nacionalidad} - {request.numero}")

    task = ejecutar_scraper.apply_async(args=[user_uuid, request.nacionalidad, request.numero])

    return {"task_id": task.id, "status": "Task started", "uuid": user_uuid}
