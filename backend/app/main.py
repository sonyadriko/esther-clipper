from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes.config import router as config_router
from app.routes.pipeline import router as pipeline_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router)
app.include_router(pipeline_router)

app.mount("/", StaticFiles(directory=str(settings.BASE_DIR / "frontend"), html=True), name="frontend")
