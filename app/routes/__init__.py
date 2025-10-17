from fastapi import APIRouter
from .chat_routes import router as chat_router
from .image_routes import router as image_router
from .treatment_routes import router as treatment_router
from .whatsapp_routes import router as whatsapp_router
from .session_routes import router as session_router
from .debug_routes import router as debug_router
from .after_call import router as transcript_router

# Create main router
main_router = APIRouter()

# Include all sub-routers
main_router.include_router(chat_router, tags=["chat"])
main_router.include_router(image_router, tags=["image"])
main_router.include_router(treatment_router, tags=["treatment"])
main_router.include_router(whatsapp_router, tags=["whatsapp"])
main_router.include_router(session_router, tags=["session"])
main_router.include_router(debug_router, tags=["debug"])
main_router.include_router(transcript_router, tags=["transcript"])