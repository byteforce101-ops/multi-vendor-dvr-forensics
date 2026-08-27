"""Optional server-side verification of Supabase-issued access tokens."""

from dataclasses import dataclass
from functools import lru_cache

from fastapi import Header, HTTPException

from backend.config.settings import get_settings


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None


@lru_cache
def _jwks_client(supabase_url: str):
    import jwt

    return jwt.PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser | None:
    settings = get_settings()
    if not settings.auth_required:
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="A Supabase access token is required")
    try:
        import jwt

        token = authorization.split(" ", 1)[1]
        if settings.supabase_jwt_secret:
            claims = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
        elif settings.supabase_url:
            key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=["RS256", "ES256"], audience="authenticated")
        else:
            raise RuntimeError("AUTH_REQUIRED needs SUPABASE_URL or SUPABASE_JWT_SECRET")
        return AuthenticatedUser(user_id=claims["sub"], email=claims.get("email"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Supabase access token") from exc
