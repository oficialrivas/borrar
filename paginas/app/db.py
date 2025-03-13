from datetime import datetime
from database.database import db

collection = db["tareas"]

def guardar_tarea(user_uuid: str, task_id: str, datos: dict, solo_asociar=False):
    consulta_filtro = {"user_uuid": user_uuid, "consulta.parametros": datos["consulta"]["parametros"]}
    tarea_existente = collection.find_one(consulta_filtro)

    if tarea_existente:
        if solo_asociar:
            collection.update_one(
                consulta_filtro,
                {"$addToSet": {"task_ids": task_id}}
            )
        else:
            collection.update_one(
                consulta_filtro,
                {
                    "$set": {
                        "resultados": datos["resultados"],
                        "fecha_actualizacion": datetime.utcnow()
                    },
                    "$addToSet": {"task_ids": task_id}
                }
            )
    else:
        datos["task_ids"] = [task_id]
        datos["user_uuid"] = user_uuid
        collection.insert_one(datos)

def obtener_tarea(user_uuid: str, parametros):
    return collection.find_one({"user_uuid": user_uuid, "consulta.parametros": parametros})

def obtener_tarea_por_id(user_uuid: str, task_id: str):
    return collection.find_one({"user_uuid": user_uuid, "task_ids": task_id}, {"_id": 0})
