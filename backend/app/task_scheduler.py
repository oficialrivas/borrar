import logging
import asyncio
from datetime import datetime, timedelta, timezone
from core.database import auto_tasks_collection
from routes.start_task import start_task_list, start_task_nationality
from routes.start_task import TaskRequestNationality, TaskRequestSelected  # ✅ Importamos los modelos Pydantic

# 🔹 Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def verificar_tareas_programadas():
    """
    Verifica y ejecuta automáticamente las tareas programadas cada minuto sin Celery.
    """
    while True:
        now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
        logger.info(f"🔄 Verificando tareas programadas en UTC: {now_utc}")

        consultas = list(auto_tasks_collection.find({
            "proxima_ejecucion": {"$lte": now_utc},
            "activa": True
        }))

        if not consultas:
            logger.info("⚠ No hay tareas programadas para ejecutar en este momento.")
        else:
            logger.info(f"📌 Se encontraron {len(consultas)} tareas programadas para ejecutar.")

        executed_tasks = []

        for consulta in consultas:
            user_uuid = consulta["user_uuid"]
            nacionalidad = consulta.get("nacionalidad")
            numero = consulta.get("numero")
            nombre = consulta.get("nombre")
            apellido = consulta.get("apellido")
            listas = consulta.get("listas", [])
            intervalo = consulta.get("intervalo", 1)

            try:
                if numero and nacionalidad:
                    logger.info(f"📌 Ejecutando tarea automática para nacionalidad {nacionalidad} y número {numero}")
                    
                    # ✅ Convertimos el diccionario en un modelo Pydantic
                    request_obj = TaskRequestNationality(nacionalidad=nacionalidad, numero=numero)
                    response = start_task_nationality(request=request_obj, current_user={"uuid": user_uuid})

                elif nombre and apellido:
                    logger.info(f"📌 Ejecutando tarea automática para {nombre} {apellido} en listas {listas}")

                    # ✅ Convertimos el diccionario en un modelo Pydantic
                    request_obj = TaskRequestSelected(nombre=nombre, apellido=apellido, listas=listas)
                    response = start_task_list(request=request_obj, current_user={"uuid": user_uuid})

                else:
                    raise Exception("❌ Datos insuficientes para ejecutar la tarea.")

                task_id = response.get("task_id", "desconocido")

                # 🔄 Reprogramar la próxima ejecución
                nueva_fecha = now_utc + timedelta(hours=intervalo)
                auto_tasks_collection.update_one(
                    {"_id": consulta["_id"]},
                    {"$set": {
                        "task_id": task_id,
                        "fecha_ejecucion_real": now_utc,
                        "proxima_ejecucion": nueva_fecha,  
                        "activa": True  
                    }}
                )

                executed_tasks.append({
                    "consulta_id": str(consulta["_id"]),
                    "task_id": task_id,
                    "fecha_ejecucion_real": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "proxima_ejecucion": nueva_fecha.strftime("%Y-%m-%d %H:%M:%S UTC")
                })

            except Exception as e:
                logger.error(f"❌ Error ejecutando tarea automática: {e}")
                auto_tasks_collection.update_one(
                    {"_id": consulta["_id"]},
                    {"$set": {"activa": False}}
                )

        if executed_tasks:
            logger.info(f"✅ Tareas ejecutadas correctamente: {executed_tasks}")

        await asyncio.sleep(60)  # Esperar 60 segundos antes de volver a verificar
