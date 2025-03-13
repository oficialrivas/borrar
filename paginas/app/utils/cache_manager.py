import redis
import json

class CacheManager:
    def __init__(self, host="redis", port=6379, db=1, ttl=3600):
        self.cache = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.ttl = ttl  # Tiempo de vida de la caché en segundos

    def get(self, key):
        """Obtiene un valor del caché en formato JSON"""
        if self.cache.exists(key):
            return json.loads(self.cache.get(key))
        return None

    def set(self, key, value):
        """Guarda un valor en la caché con TTL"""
        self.cache.setex(key, self.ttl, json.dumps(value))

    def exists(self, key):
        """Verifica si la clave existe en la caché"""
        return self.cache.exists(key)
