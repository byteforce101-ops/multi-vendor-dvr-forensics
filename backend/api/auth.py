"""Optional server-side verification of Supabase-issued access tokens."""

from dataclasses import dataclass

from fastapi import Header, HTTPException

from backend.config.settings import get_settings


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser | None:
    settings = get_settings()
    if not settings.auth_required:
        return None
    if not settings.supabase_jwt_secret:
        raise RuntimeError("AUTH_REQUIRED needs SUPABASE_JWT_SECRET on the backend")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="A Supabase access token is required")
    try:
        import jwt

        claims = jwt.decode(
            authorization.split(" ", 1)[1],
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return AuthenticatedUser(user_id=claims["sub"], email=claims.get("email"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Supabase access token") from exc
