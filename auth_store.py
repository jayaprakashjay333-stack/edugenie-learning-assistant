import hashlib
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

PROJECT_DIR = Path(__file__).resolve().parent
_SCRYPT_N = 1 << 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SESSION_TOKEN_BYTES = 32
_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7


def _database_path() -> Path:
    configured_path = os.getenv("EDUGENIE_DB_PATH", "").strip()
    return (
        Path(configured_path)
        if configured_path
        else PROJECT_DIR / "data" / "edugenie.sqlite3"
    )


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    database_path = _database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                display_name TEXT NOT NULL,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash BLOB PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS sessions_expires_at_idx
                ON sessions(expires_at);
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=32,
    )


def _hash_session_token(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def create_user(
    email: str, display_name: str, password: str
) -> dict[str, object] | None:
    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)
    try:
        with _connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (email, display_name, password_salt, password_hash, created_at)
                VALUES (?, ?, ?, ?, unixepoch())
                """,
                (email.strip().lower(), display_name.strip(), salt, password_hash),
            )
            row = connection.execute(
                "SELECT id, email, display_name FROM users WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
    except sqlite3.IntegrityError:
        return None
    return dict(row) if row is not None else None


def authenticate_user(email: str, password: str) -> dict[str, object] | None:
    with _connection() as connection:
        row = connection.execute(
            """
            SELECT id, email, display_name, password_salt, password_hash
            FROM users WHERE email = ? COLLATE NOCASE
            """,
            (email.strip().lower(),),
        ).fetchone()

    if row is None:
        return None
    candidate_hash = _hash_password(password, row["password_salt"])
    if not secrets.compare_digest(candidate_hash, row["password_hash"]):
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
    }


def create_session(user_id: int) -> tuple[str, int]:
    token = secrets.token_urlsafe(_SESSION_TOKEN_BYTES)
    expires_at = int(time.time()) + _SESSION_MAX_AGE_SECONDS
    with _connection() as connection:
        connection.execute(
            "DELETE FROM sessions WHERE expires_at <= unixepoch()"
        )
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_hash_session_token(token), user_id, expires_at),
        )
    return token, _SESSION_MAX_AGE_SECONDS


def get_user_for_session(token: str) -> dict[str, object] | None:
    with _connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.email, users.display_name
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > unixepoch()
            """,
            (_hash_session_token(token),),
        ).fetchone()
    return dict(row) if row is not None else None


def delete_session(token: str) -> None:
    with _connection() as connection:
        connection.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (_hash_session_token(token),),
        )
