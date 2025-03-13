import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from bson import ObjectId  # ✅ Para manejar `_id` en MongoDB
from auth.dependencies import get_current_user
from core.database import auto_tasks_collection
from routes.start_task import start_task_list, start_task_nationality  # ✅ Importación correcta

# 🔹 Configurar logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automatic-tasks", tags=["Automatic Tasks"])

# 📌 Modelos de datos
class AutomaticTaskRequest(BaseModel):
    fecha_programada: Optional[str] = None  # 📌 Formato: "YYYY-MM-DD HH:MM:SS"
    nacionalidad: Optional[str] = None
    numero: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    listas: Optional[List[str]] = None
    intervalo: Optional[int] = None  # Intervalo en horas para ejecución recurrente
    ciclo_2h: Optional[bool] = False  # 📌 Si es `True`, ejecuta la tarea cada 2 horas
    
    
class AutomaticTask(BaseModel):
    nacionalidad: Optional[str] = None
    numero: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    listas: Optional[List[str]] = None
    ciclo_2h: Optional[bool] = False  # 📌 Si es `True`, ejecuta la tarea cada 2 horas
    

# 📌 **1️⃣ Endpoint para registrar tareas automatizadas normales**
@router.post("/register")
def register_automatic_task(request: AutomaticTaskRequest, current_user: dict = Depends(get_current_user)):
    user_uuid = current_user["uuid"]

    # 📌 Validar parámetros
    if not request.numero and not request.nombre:
        raise HTTPException(status_code=400, detail="Debe proporcionar 'nacionalidad y numero' o 'nombre y apellido'.")

    if request.fecha_programada:
        try:
            fecha_programada = datetime.strptime(request.fecha_programada, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha incorrecto. Use 'YYYY-MM-DD HH:MM:SS'.")
    elif request.intervalo:
        if request.intervalo not in [1, 2]:
            raise HTTPException(status_code=400, detail="El intervalo solo puede ser 1 o 2 horas.")
        fecha_programada = datetime.utcnow() + timedelta(hours=request.intervalo)
    else:
        raise HTTPException(status_code=400, detail="Debe proporcionar 'fecha_programada' o 'intervalo'.")

    # 📌 Guardar en la base de datos
    consulta = {
        "user_uuid": user_uuid,
        "nacionalidad": request.nacionalidad,
        "numero": request.numero,
        "nombre": request.nombre,
        "apellido": request.apellido,
        "listas": request.listas,
        "proxima_ejecucion": fecha_programada,
        "activa": True,
    }
    result = auto_tasks_collection.insert_one(consulta)

    return {"message": "Consulta automática registrada", "proxima_ejecucion": fecha_programada, "task_id": str(result.inserted_id)}

# 📌 **2️⃣ Nuevo Endpoint para registrar tareas automatizadas cada 2 horas**
@router.post("/register-ciclo-2h")
def register_automatic_task_2h(request: AutomaticTask, current_user: dict = Depends(get_current_user)):
    user_uuid = current_user["uuid"]

    # 📌 Validar parámetros obligatorios
    if not request.numero and not request.nombre:
        raise HTTPException(status_code=400, detail="Debe proporcionar 'nacionalidad y numero' o 'nombre y apellido'.")

    now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)

    # 📌 Determinar la próxima ejecución en ciclos de 2 horas
    fecha_programada = now_utc + timedelta(hours=2)

    # 📌 Guardar en la base de datos
    consulta = {
        "user_uuid": user_uuid,
        "nacionalidad": request.nacionalidad,
        "numero": request.numero,
        "nombre": request.nombre,
        "apellido": request.apellido,
        "listas": request.listas,
        "proxima_ejecucion": fecha_programada,
        "activa": True,
        "ciclo_2h": True,  # ✅ Se guarda si es cíclica
    }
    result = auto_tasks_collection.insert_one(consulta)

    return {"message": "Consulta automática registrada en ciclo de 2 horas", "proxima_ejecucion": fecha_programada, "task_id": str(result.inserted_id)}

# 📌 **3️⃣ Ejecutar tareas automáticamente**
def execute_automatic_tasks():
    """
    Ejecuta automáticamente todas las tareas programadas.
    """
    now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)

    consultas = list(auto_tasks_collection.find({
        "proxima_ejecucion": {"$lte": now_utc},
        "activa": True
    }))

    if not consultas:
        logger.info("⚠ No hay tareas programadas para ejecutar en este momento.")
        return "No hay tareas programadas para ejecutar en este momento."

    executed_tasks = []

    for consulta in consultas:
        user_uuid = consulta["user_uuid"]
        nacionalidad = consulta.get("nacionalidad")
        numero = consulta.get("numero")
        nombre = consulta.get("nombre")
        apellido = consulta.get("apellido")
        listas = consulta.get("listas")

        try:
            if numero and nacionalidad:
                logger.info(f"📌 Ejecutando tarea automática para nacionalidad {nacionalidad} y número {numero}")
                response = start_task_nationality(
                    request=AutomaticTaskRequest(nacionalidad=nacionalidad, numero=numero),
                    current_user={"uuid": user_uuid}
                )

            elif nombre and apellido:
                logger.info(f"📌 Ejecutando tarea automática para {nombre} {apellido} en listas {listas}")
                response = start_task_list(
                    request=AutomaticTaskRequest(nombre=nombre, apellido=apellido, listas=listas),
                    current_user={"uuid": user_uuid}
                )

            else:
                raise Exception("❌ Datos insuficientes para ejecutar la tarea.")

            task_id = response.get("task_id", "desconocido")

            # 📌 Si la tarea es cíclica, programarla de nuevo en 2 horas
            nueva_fecha = now_utc + timedelta(hours=2) if consulta.get("ciclo_2h") else None

        except Exception as e:
            task_id = "error"
            logger.error(f"❌ Error ejecutando tarea automática: {e}")

        auto_tasks_collection.update_one(
            {"_id": consulta["_id"]},
            {"$set": {
                "task_id": task_id,
                "fecha_ejecucion_real": now_utc,
                "activa": False if not consulta.get("ciclo_2h") else True,
                "proxima_ejecucion": nueva_fecha if nueva_fecha else None
            }}
        )

        executed_tasks.append({
            "consulta_id": str(consulta["_id"]),
            "task_id": task_id,
            "fecha_ejecucion_real": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        })

    logger.info(f"✅ Tareas ejecutadas correctamente: {executed_tasks}")
    return {"message": "Tareas ejecutadas automáticamente", "executed_tasks": executed_tasks}

# 📌 **4️⃣ Endpoint para ejecutar tareas manualmente**
@router.post("/execute-manual")
def execute_tasks_manually():
    result = execute_automatic_tasks()
    return result

# 📌 **5️⃣ Nuevo Endpoint para eliminar una automatización**
@router.delete("/delete/{task_id}")
def delete_automatic_task(task_id: str, current_user: dict = Depends(get_current_user)):
    user_uuid = current_user["uuid"]

    # 📌 Verificar si la tarea existe
    consulta = auto_tasks_collection.find_one({"_id": ObjectId(task_id), "user_uuid": user_uuid})

    if not consulta:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o no autorizada para eliminar.")

    # 📌 Eliminar la tarea
    auto_tasks_collection.delete_one({"_id": ObjectId(task_id)})

    return {"message": f"Tarea con ID {task_id} eliminada correctamente."}
