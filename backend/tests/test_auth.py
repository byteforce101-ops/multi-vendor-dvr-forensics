"""backend/tests/test_auth.py — Tests for Supabase server-side authentication and JWT verification."""

import pytest
import jwt
from fastapi import HTTPException

from backend.api.auth import get_current_user, AuthenticatedUser
from backend.config.settings import get_settings


def test_auth_disabled_returns_none(monkeypatch):
    """When AUTH_REQUIRED is false, all requests pass through without requiring tokens."""
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    get_settings.cache_clear()

    user = get_current_user(authorization=None)
    assert user is None


def test_auth_required_missing_header(monkeypatch):
    """When AUTH_REQUIRED is true, missing authorization header raises 401."""
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


def test_auth_required_valid_jwt(monkeypatch):
    """When AUTH_REQUIRED is true, valid Supabase JWT decodes into AuthenticatedUser."""
    secret = "test-supabase-jwt-secret-key-12345"
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)
    get_settings.cache_clear()

    token = jwt.encode(
        {"sub": "usr_998877", "email": "examiner@agency.gov", "aud": "authenticated"},
        secret,
        algorithm="HS256",
    )

    user = get_current_user(authorization=f"Bearer {token}")
    assert isinstance(user, AuthenticatedUser)
    assert user.user_id == "usr_998877"
    assert user.email == "examiner@agency.gov"
