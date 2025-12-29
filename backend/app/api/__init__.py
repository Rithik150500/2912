from fastapi import APIRouter
from app.api import auth, client, advocate, websocket

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(client.router, prefix="/client", tags=["Client"])
api_router.include_router(advocate.router, prefix="/advocate", tags=["Advocate"])
