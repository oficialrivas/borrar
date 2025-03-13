import uuid
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from core.database import users_collection
from fastapi import HTTPException

# 📌 Configuración de seguridad
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 📌 Función para hashear contraseñas
def get_password_hash(password: str):
    return pwd_context.hash(password)

# 📌 Función para verificar contraseñas
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# 📌 Función para crear tokens de acceso
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 📌 Registro de usuario con `is_active=False` por defecto
def register_user(username: str, email: str, password: str):
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    user_uuid = str(uuid.uuid4())  # Asegurar que UUID sea string
    hashed_password = get_password_hash(password)

    user = {
        "uuid": user_uuid,
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "is_active": False  # 🚀 Usuario inactivo por defecto
    }
    
    users_collection.insert_one(user)
    return {"message": "User registered successfully", "uuid": user_uuid}

# 📌 Autenticación de usuario (permite loguearse aunque no esté activado)
def authenticate_user(username: str, password: str):
    user = users_collection.find_one({"username": username})
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # 🚀 Ahora permite loguearse aunque el usuario esté inactivo
    token = create_access_token({"sub": user["username"], "uuid": user["uuid"], "is_active": user["is_active"]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_active": user["is_active"]  # 🔴 Para que el frontend sepa si debe activarse
    }

# 📌 Función para verificar el token JWT
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # Retorna el payload del token si es válido
    except JWTError:
        return None
