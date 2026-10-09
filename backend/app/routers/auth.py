"""Password login with revocable, opaque bearer sessions."""
import hashlib
import hmac
import secrets
import sqlite3
import time
from contextlib import closing

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from app.database import get_connection

router = APIRouter(prefix="/api/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
SESSION_SECONDS = 24 * 60 * 60
PASSWORD_ITERATIONS = 600_000


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class User(BaseModel):
    id: int
    username: str
    created_at: int


class LoginResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = SESSION_SECONDS
    user: User


def hash_password(password: str, salt: str = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PASSWORD_ITERATIONS
    ).hex()
    return f"{salt}${digest}"


# Unknown users still incur the same password verification work.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def unauthorized():
    return HTTPException(401, "Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})


def token_digest(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    if credentials is None:
        raise unauthorized()
    return hashlib.sha256(credentials.credentials.encode()).hexdigest()


def get_current_user(digest: str = Depends(token_digest)) -> User:
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT u.id, u.username, u.created_at FROM users u "
            "JOIN user_sessions s ON s.user_id = u.id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (digest, int(time.time())),
        ).fetchone()
    if row is None:
        raise unauthorized()
    return User(**dict(row))


@router.post("/register", response_model=User, status_code=201)
def register(payload: Credentials):
    password_hash = hash_password(payload.password)
    created_at = int(time.time())
    with closing(get_connection()) as conn:
        try:
            with conn:
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (payload.username, password_hash, created_at),
                )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Username already registered") from None
    return User(id=cursor.lastrowid, username=payload.username, created_at=created_at)


@router.post("/login", response_model=LoginResult)
def login(payload: Credentials, response: Response):
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (payload.username,)).fetchone()
        stored = row["password_hash"] if row else DUMMY_PASSWORD_HASH
        candidate = hash_password(payload.password, stored.split("$", 1)[0])
        if not hmac.compare_digest(stored, candidate) or row is None:
            raise unauthorized()
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with conn:
            conn.execute("DELETE FROM user_sessions WHERE expires_at <= ?", (now,))
            conn.execute(
                "INSERT INTO user_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (hashlib.sha256(token.encode()).hexdigest(), row["id"], now + SESSION_SECONDS),
            )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return LoginResult(access_token=token, user=User(**dict(row)))


@router.get("/me", response_model=User)
def me(response: Response, user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user


@router.post("/logout", status_code=204)
def logout(digest: str = Depends(token_digest), user: User = Depends(get_current_user)):
    with closing(get_connection()) as conn, conn:
        conn.execute("DELETE FROM user_sessions WHERE token_hash = ?", (digest,))
    return Response(status_code=204)
