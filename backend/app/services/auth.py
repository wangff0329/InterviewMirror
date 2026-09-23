import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time

from app.config import Settings
from app.schemas import UserResponse


def init_auth_database(settings: Settings) -> None:
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"{salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split("$", 1)
    candidate = _password_hash(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
    return hmac.compare_digest(candidate, digest_hex)


def create_user(settings: Settings, email: str, password: str) -> UserResponse:
    normalized_email = email.strip().lower()
    try:
        with sqlite3.connect(settings.database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (normalized_email, _password_hash(password)),
            )
            return UserResponse(id=cursor.lastrowid, email=normalized_email)
    except sqlite3.IntegrityError as error:
        raise ValueError("该邮箱已经注册。") from error


def authenticate_user(settings: Settings, email: str, password: str) -> UserResponse | None:
    with sqlite3.connect(settings.database_path) as connection:
        row = connection.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip(),),
        ).fetchone()
    if not row or not _password_matches(password, row[2]):
        return None
    return UserResponse(id=row[0], email=row[1])


def create_access_token(settings: Settings, user: UserResponse) -> str:
    payload = {"sub": user.id, "email": user.email, "exp": int(time.time()) + settings.auth_token_expire_hours * 3600}
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(encoded_payload, settings.auth_secret)
    return f"{encoded_payload}.{signature}"


def decode_access_token(settings: Settings, token: str) -> UserResponse:
    try:
        encoded_payload, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _sign(encoded_payload, settings.auth_secret)):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload + "=="))
        if payload["exp"] < time.time():
            raise ValueError
        return UserResponse(id=int(payload["sub"]), email=payload["email"])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("登录状态无效或已过期。") from error


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _sign(value: str, secret: str) -> str:
    return _encode(hmac.new(secret.encode(), value.encode(), hashlib.sha256).digest())