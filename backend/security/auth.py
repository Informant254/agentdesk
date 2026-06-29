"""Authentication and JWT token management."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthManager:
    """Handle JWT token creation, validation, and user authentication."""

    def __init__(self):
        self.secret_key = settings.jwt_secret
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = settings.access_token_expire_minutes

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: str, extra_claims: dict | None = None) -> str:
        to_encode = {"sub": user_id, "iat": datetime.now(timezone.utc)}
        if extra_claims:
            to_encode.update(extra_claims)
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)
        to_encode["exp"] = expire
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict | None:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None

    def get_user_id_from_token(self, token: str) -> str | None:
        payload = self.verify_token(token)
        if payload is None:
            return None
        return payload.get("sub")


auth_manager = AuthManager()
