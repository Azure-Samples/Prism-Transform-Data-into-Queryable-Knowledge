"""
Authentication API endpoints
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: str = None


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Simple password-based authentication"""
    auth_password = os.getenv("AUTH_PASSWORD")

    if request.password == auth_password:
        # In a real app, you'd generate a proper JWT token
        # For simplicity, we'll just return a basic token
        return LoginResponse(success=True, token="authenticated")
    else:
        raise HTTPException(status_code=401, detail="Invalid password")


@router.post("/verify")
async def verify():
    """Verify authentication token - for now just returns success"""
    return {"authenticated": True}
