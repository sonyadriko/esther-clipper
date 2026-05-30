from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    if credentials.credentials != settings.API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials


def get_token_from_query(request: Request) -> str:
    """Allow token as query param for video streaming endpoints."""
    token = request.query_params.get("token")
    if token != settings.API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token
