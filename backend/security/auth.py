"""Authentication manager — JWT creation and verification."""

import httpx
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.config import settings

_bearer = HTTPBearer(auto_error=False)


class AuthManager:
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def create_access_token(self, user_id: str, extra: dict | None = None) -> str:
        payload = {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            **(extra or {}),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    def verify_token_raw(self, token: str) -> dict | None:
        """Decode a JWT and return the payload, or None on failure."""
        try:
            return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except JWTError:
            return None

    def verify_token(
        self,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> dict | None:
        if not credentials:
            return None
        return self.verify_token_raw(credentials.credentials)

    async def verify_supabase_token(self, supabase_token: str) -> dict | None:
        """Verify a Supabase JWT by calling the Supabase user endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.supabase_url}/auth/v1/user",
                    headers={"Authorization": f"Bearer {supabase_token}",
                             "apikey": settings.supabase_key},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None


auth_manager = AuthManager()
