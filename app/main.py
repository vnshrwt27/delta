from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.routes.auth import router as auth_router
from app.routes.ws import ws_router

app = FastAPI()

app.include_router(auth_router, prefix="/api/v1")
app.include_router(ws_router)
