from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from auth.services import register_user, authenticate_user
from auth.dependencies import get_current_user
from core.database import users_collection  # ✅ Asegurarse de importar correctamente la colección

router = APIRouter()

# 📌 Esquemas de Pydantic para la validación de datos
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ActivateUserRequest(BaseModel):
    uuid: str
    email: str

class PhoneNumberRequest(BaseModel):
    phone_number: str

class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    phone_numbers: Optional[List[str]] = None

# ✅ Endpoint para registrar usuarios
@router.post("/register/")
def register(user: UserCreate):
    return register_user(user.username, user.email, user.password)

# ✅ Endpoint para login y obtención de token
@router.post("/token/")
def login(user: LoginRequest):
    return authenticate_user(user.username, user.password)

# ✅ Endpoint para obtener información del usuario autenticado
@router.get("/me/")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"], 
        "uuid": current_user["uuid"],
        "is_active": current_user["is_active"]
    }

# ✅ Endpoint para activar usuario sin autenticación
@router.post("/activate/")
def activate_user(request: ActivateUserRequest):
    user = users_collection.find_one({"uuid": str(request.uuid), "email": request.email})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("is_active", False):
        return {"message": "User is already active"}

    users_collection.update_one({"uuid": str(request.uuid)}, {"$set": {"is_active": True}})
    return {"message": "User activated successfully"}

# ✅ Endpoint para agregar un número de teléfono a un usuario autenticado
@router.post("/phone_numbers/")
def add_phone_number(request: PhoneNumberRequest, current_user: dict = Depends(get_current_user)):
    user = users_collection.find_one({"uuid": current_user["uuid"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    users_collection.update_one(
        {"uuid": current_user["uuid"]},
        {"$addToSet": {"phone_numbers": request.phone_number}}
    )
    
    return {"message": "Phone number added successfully"}

# ✅ Endpoint para obtener los números telefónicos asociados a un usuario
@router.get("/phone_numbers/", response_model=List[str])
def get_phone_numbers(current_user: dict = Depends(get_current_user)):
    user = users_collection.find_one({"uuid": current_user["uuid"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user.get("phone_numbers", [])

# ✅ Endpoint para actualizar la información del usuario
@router.put("/users/update/")
def update_user(request: UserUpdateRequest, current_user: dict = Depends(get_current_user)):
    user = users_collection.find_one({"uuid": current_user["uuid"]})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {}

    if request.username:
        update_data["username"] = request.username
    if request.email:
        update_data["email"] = request.email
    if request.password:
        update_data["password"] = request.password  # 🔒 Recuerda encriptar la contraseña antes de almacenarla
    if request.phone_numbers is not None:
        update_data["phone_numbers"] = request.phone_numbers

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    users_collection.update_one({"uuid": current_user["uuid"]}, {"$set": update_data})

    return {"message": "User updated successfully"}
