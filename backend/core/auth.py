# Smart Wardrobe - Auth
# Single shared-secret header check for write endpoints. No user accounts:
# this is a single-tenant kiosk app, a full auth system would be YAGNI.

from fastapi import Header, HTTPException, status

from backend.core.config import settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Reject write requests unless X-API-Key matches settings.API_KEY.

    If API_KEY is unset (local/dev default), this is a no-op — matches prior
    behavior. Set API_KEY in .env for any deployment reachable off localhost.
    """
    if not settings.API_KEY:
        return
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
