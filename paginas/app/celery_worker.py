from datetime import datetime
from utils.cache_manager import CacheManager
from utils.executor import ejecutar_script
from utils.name_utils import agrupar_nombres_por_similitud
from database.database import (
    db, celery_app, redis_client,
    tasks_collection, auto_tasks_collection, notifications_collection
)
from db import guardar_tarea, obtener_tarea, obtener_tarea_por_id

cache = CacheManager()

listas_disponibles = {
    "roja": "archivos/interpolroja.py",
    "amarilla": "archivos/interpolamarilla.py",
    "ramajudicial": "archivos/judicial.py",
    "ventanavirtual": "archivos/ventanavirtual.py"
}

nacionalidades_disponibles = {
    "CO": ["colombia/RUES.py", "colombia/tarjetamilitar.py", "colombia/judicialcorrespon.py", "colombia/ventanavirtualnit.py", "colombia/comercio.py"]
}

@celery_app.task(name="paginas.ejecutar_scraper")
def ejecutar_scraper(user_uuid, *args):
    resultados = {}
    nombres_encontrados = []

    if len(args) == 2:
        nacionalidad, numero = args
        if nacionalidad in nacionalidades_disponibles:
            archivos = nacionalidades_disponibles[nacionalidad]
            parametro_busqueda = numero
        else:
            return {"error": f"Nacionalidad '{nacionalidad}' no soportada."}
    elif len(args) == 3:
        nombre, apellido, listas = args
        listas = listas or list(listas_disponibles.keys())
        archivos = [listas_disponibles[lista] for lista in listas if lista in listas_disponibles]
        parametro_busqueda = f"{nombre} {apellido}"
    else:
        return {"error": "Parámetros incorrectos"}

    if not archivos:
        return {"error": "No se encontraron archivos a procesar."}

    for archivo in archivos:
        cache_key = f"{archivo}:{parametro_busqueda}"
        if cache.exists(cache_key):
            resultados[archivo] = cache.get(cache_key)
        else:
            resultados[archivo] = ejecutar_script(archivo, parametro_busqueda)
            cache.set(cache_key, resultados[archivo])

        nombre_extraido = resultados[archivo].get("nombre") or resultados[archivo].get("datos", {}).get("nombre")
        if nombre_extraido:
            nombres_encontrados.append(nombre_extraido)

    if nombres_encontrados:
        nombres_agrupados = agrupar_nombres_por_similitud(nombres_encontrados)
        primer_nombre_equivalente = list(nombres_agrupados.values())[0][0]

        partes_nombre = primer_nombre_equivalente.split()
        nombre_interpol = partes_nombre[0] if len(partes_nombre) > 1 else primer_nombre_equivalente
        apellido_interpol = " ".join(partes_nombre[1:]) if len(partes_nombre) > 1 else ""

        for lista, archivo in listas_disponibles.items():
            cache_key = f"{archivo}:{apellido_interpol}"
            if cache.exists(cache_key):
                resultados[archivo] = cache.get(cache_key)
            else:
                resultados[archivo] = ejecutar_script(archivo, apellido_interpol)
                cache.set(cache_key, resultados[archivo])

    task_id = ejecutar_scraper.request.id

    tarea_guardada = obtener_tarea(user_uuid, args)

    if tarea_guardada:
        datos_previos = tarea_guardada.get("resultados", {})
        nuevos_datos = {k: v for k, v in resultados.items() if k not in datos_previos or datos_previos[k] != v}

        if nuevos_datos:
            nueva_notificacion = {
                "user_uuid": user_uuid,
                "task_id": task_id,
                "timestamp": datetime.utcnow(),
                "datos_nuevos": nuevos_datos,
                "estado": "pendiente"
            }
            notifications_collection.insert_one(nueva_notificacion)

            tarea_guardada["fecha_actualizacion"] = datetime.utcnow()
            tarea_guardada["resultados"].update(nuevos_datos)
            tarea_guardada["task_ids"].append(task_id)
            guardar_tarea(user_uuid, task_id, tarea_guardada)

            return {"mensaje": "Nuevos datos detectados", "nuevos_datos": nuevos_datos}
        else:
            tarea_guardada["task_ids"].append(task_id)
            guardar_tarea(user_uuid, task_id, tarea_guardada, solo_asociar=True)
            return {"mensaje": "No hay información nueva, tarea asociada."}
    else:
        nueva_tarea = {
            "task_id": task_id,
            "task_ids": [task_id],
            "fecha_creacion": datetime.utcnow(),
            "user_uuid": user_uuid,
            "consulta": {"parametros": args},
            "resultados": resultados
        }
        guardar_tarea(user_uuid, task_id, nueva_tarea)

        nueva_notificacion = {
            "user_uuid": user_uuid,
            "task_id": task_id,
            "timestamp": datetime.utcnow(),
            "datos_nuevos": resultados,
            "estado": "pendiente"
        }
        notifications_collection.insert_one(nueva_notificacion)

        return {"mensaje": "Tarea registrada y notificación generada", "nuevos_datos": resultados}


@celery_app.task(name="paginas.obtener_tarea")
def obtener_tarea_celery(user_uuid, task_id):
    """
    Obtiene una tarea específica desde MongoDB por su `task_id`.
    """
    try:
        tarea = obtener_tarea_por_id(user_uuid, task_id)
        if tarea:
            return tarea
        return {"error": "Tarea no encontrada en MongoDB"}
    except Exception as e:
        return {"error": f"Error al recuperar la tarea: {str(e)}"}
