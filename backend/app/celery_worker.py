from celery import Celery
from celery.schedules import crontab

celery_app = Celery("tasks")
celery_app.config_from_object("celeryconfig")

# 🔹 Programar la ejecución de tareas cada minuto
celery_app.conf.beat_schedule = {
    "execute_automatic_tasks_every_minute": {
        "task": "tasks.execute_automatic_tasks",
        "schedule": crontab(minute="*"),  # Ejecutar cada minuto
    },
}

celery_app.conf.timezone = "UTC"
