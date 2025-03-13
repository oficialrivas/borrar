import os
import pymongo
import requests
import json
from dotenv import load_dotenv
from bson import ObjectId

# Cargar variables de entorno
load_dotenv()

# Configuración de MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DATABASE_NAME = "osint_db"
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "https://triunoevolution.yosoytriuno.site")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
INSTANCE_ID = os.getenv("EVOLUTION_INSTANCE_ID")

# Conectar a MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
notifications_collection = db["notificaciones"]
users_collection = db["users"]

def format_message(datos_nuevos):
    """
    Formatea el contenido de 'datos_nuevos' en un mensaje legible.
    """
    mensaje = "📌 Nueva notificación:\n"
    for categoria, contenido in datos_nuevos.items():
        mensaje += f"➡ {categoria}:\n"
        for key in contenido:
            mensaje += f"  - {key}\n"
    return mensaje.strip()

def send_notification_to_evolution(user_uuid: str, message: str, phone_number: str):
    """
    Envía una notificación a Evolution API en el formato correcto.
    """
    if not EVOLUTION_API_KEY:
        print("❌ API Key no configurada correctamente.")
        return

    endpoint = f"{EVOLUTION_API_URL}/message/sendText/{INSTANCE_ID}"
    
    payload = {
        "number": phone_number,  # 📌 Número de WhatsApp destino
        "text": message,  # 📌 Mensaje formateado
        "delay": 1,  # Ajustar según necesidades
        "linkPreview": False,
        "mentionsEveryOne": False,
        "mentioned": []
    }

    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_API_KEY
    }

    # 🔹 Debug: Mostrar JSON que se enviará
    print(f"📤 Enviando notificación a Evolution API...")
    print(f"🔹 Endpoint: {endpoint}")
    print(f"🔹 Headers: {json.dumps(headers, indent=2)}")
    print(f"🔹 Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()  # Lanza error si la respuesta no es 200
        print(f"✅ Notificación enviada con éxito: {response.json()}")
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ Error HTTP al enviar notificación: {http_err}")
        print(f"🔹 Respuesta del servidor: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Error en la solicitud a Evolution API: {req_err}")

def get_user_phone_number(user_uuid: str):
    """
    Obtiene el número de teléfono del usuario a partir de su `user_uuid`.
    """
    print(f"🔎 Buscando número de teléfono para el usuario {user_uuid}...")
    user = users_collection.find_one({"uuid": user_uuid})
    if user and "numero" in user:
        phone_number = user["numero"]
        print(f"📞 Número de teléfono encontrado: {phone_number}")
        return phone_number
    print("⚠ No se encontró número de teléfono.")
    return None

def watch_notifications():
    """
    Monitorea la colección de notificaciones en MongoDB y envía la notificación a Evolution API cuando se inserta un nuevo documento.
    """
    print("🔄 Monitoreando nuevas notificaciones en MongoDB...")

    with notifications_collection.watch([{"$match": {"operationType": "insert"}}]) as stream:
        for change in stream:
            notification = change["fullDocument"]
            user_uuid = notification["user_uuid"]
            datos_nuevos = notification.get("datos_nuevos", {})

            print("\n🆕 Nueva notificación detectada en MongoDB:")
            print(json.dumps(notification, indent=2, default=str))

            message = format_message(datos_nuevos)

            phone_number = get_user_phone_number(user_uuid)

            if phone_number:
                print(f"📩 Enviando notificación a {phone_number}: {message}")
                send_notification_to_evolution(user_uuid, message, phone_number)
            else:
                print(f"⚠ No se encontró número de teléfono para user_uuid: {user_uuid}")

if __name__ == "__main__":
    watch_notifications()
