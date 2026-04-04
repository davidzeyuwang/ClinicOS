"""FastAPI auth dependencies."""
from typing import TypedDict

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.auth.jwt_utils import decode_token

_bearer = HTTPBearer(auto_error=False)


class CurrentUser(TypedDict):
    user_id: str
    clinic_id: str
    role: str
    display_name: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(credentials.credentials)
        return CurrentUser(
            user_id=payload["sub"],
            clinic_id=payload["clinic_id"],
            role=payload["role"],
            display_name=payload.get("display_name", ""),
        )
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_role(*roles: str):
    """Dependency factory that checks the user has one of the given roles."""
    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check
