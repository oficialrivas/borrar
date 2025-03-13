from fastapi import APIRouter, Depends
from bson import ObjectId  # 🔹 Importar ObjectId
from auth.dependencies import get_current_user
from core.database import notifications_collection
from typing import List

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# 📌 Endpoint para obtener las notificaciones del usuario
@router.get("/")
def get_notifications(current_user: dict = Depends(get_current_user)):
    user_uuid = current_user["uuid"]
    notifications = list(notifications_collection.find({"user_uuid": user_uuid, "estado": "pendiente"}))

    # Convertir ObjectId a string
    for notification in notifications:
        notification["_id"] = str(notification["_id"])

    return {"notifications": notifications}

# 📌 Endpoint para marcar una notificación como vista
@router.post("/mark-as-read/{notification_id}")
def mark_notification_as_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    user_uuid = current_user["uuid"]

    # Buscar la notificación en la base de datos
    notification = notifications_collection.find_one({"_id": ObjectId(notification_id), "user_uuid": user_uuid})

    if not notification:
        return {"message": "Notificación no encontrada o no pertenece al usuario"}

    # Marcar la notificación como leída
    notifications_collection.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"estado": "leído"}}
    )

    return {"message": "Notificación marcada como leída", "notification_id": notification_id}
