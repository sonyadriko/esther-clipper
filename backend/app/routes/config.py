from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings

router = APIRouter(prefix="/api")


@router.get("/config")
async def get_config(request: Request):
    # Only serve token to localhost requests
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    return {
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "token": settings.API_TOKEN,
        "has_openai_key": bool(settings.OPENAI_API_KEY),
        "has_anthropic_key": bool(settings.ANTHROPIC_API_KEY),
    }
