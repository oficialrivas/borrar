from datetime import datetime, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from celery.result import AsyncResult
from typing import Optional
from auth.dependencies import get_current_user
from tasks import obtener_tarea_celery
from core.database import tasks_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Task Status"])


# 📌 Endpoint para consultar el estado de una tarea
@router.get("/task-status/{task_id}")
def get_task_status(task_id: str, current_user: dict = Depends(get_current_user)):
    user_uuid = current_user["uuid"]

    # 📌 Hacer la consulta a Celery para obtener la tarea desde MongoDB
    task = obtener_tarea_celery.apply_async(args=[user_uuid, task_id])
    result = task.get(timeout=5)  # Esperar hasta 5 segundos por la respuesta

    if "error" not in result:
        return result

    # 📌 Si no está en MongoDB, obtener el estado desde Celery
    task_result = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task_result.status,
        "message": "Tarea no encontrada en la base de datos, solo estado disponible."
    }


# 📌 **Nuevo endpoint para consultar tareas en un período específico y filtrar por lista**
@router.get("/tasks-history/")
def get_tasks_history(
    start_date: Optional[str] = Query(None, description="Fecha de inicio en formato YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Fecha de fin en formato YYYY-MM-DD"),
    lista: Optional[str] = Query(None, description="Filtrar por lista dentro de resultados"),
    current_user: dict = Depends(get_current_user)
):
    user_uuid = current_user["uuid"]

    # 📌 Construcción del filtro de búsqueda
    filtro = {"user_uuid": user_uuid}

    if start_date:
        filtro["fecha_creacion"] = {"$gte": datetime.strptime(start_date, "%Y-%m-%d")}
    
    if end_date:
        filtro.setdefault("fecha_creacion", {})["$lte"] = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

    # 📌 Consultar MongoDB con el filtro base
    tareas = list(tasks_collection.find(filtro, {"_id": 0}))

    return {"user_uuid": user_uuid, "tasks": tareas}
