from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.services import verify_token
from core.database import users_collection

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = users_collection.find_one({"uuid": payload["uuid"]})  
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "username": user["username"], 
        "uuid": user["uuid"], 
        "is_active": user.get("is_active", False)  # 🔴 Devuelve `is_active` pero no bloquea aquí
    }
