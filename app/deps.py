from fastapi import Header, HTTPException

from app.core.security import decode_access_token


async def get_current_business_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")

    token = authorization.removeprefix("Bearer ")
    try:
        return decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Token invalido") from exc
