from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="WhatsApp AI Bot",
    description="FastAPI app to chat and detect crop diseases",
    version="1.0.0"
)

app.include_router(router)
