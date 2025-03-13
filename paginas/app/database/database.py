import os
import pymongo
import redis
from dotenv import load_dotenv
from celery import Celery

# Cargar variables de entorno desde .env
load_dotenv()

# 📌 Configuración de MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://bpoway:79b89d2b2ce97ce8c36adca015bbcc66@mongodb:27017/osint_db")
DATABASE_NAME = "osint_db"

# Conectar a MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client[DATABASE_NAME]

# Definir colecciones
users_collection = db["users"]  
tasks_collection = db["tareas"]  
auto_tasks_collection = db["consultas_automatizadas"]
notifications_collection = db["notificaciones"]

# 📌 Configuración de Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# 📌 Configuración de Celery
celery_app = Celery(
    "paginas",
    broker=REDIS_URL,
    backend=REDIS_URL
)

print("✅ Conexión a MongoDB y Redis establecida correctamente")
