"""SQLite-backed storage: user accounts and their saved trips.

Every trip row is owned by exactly one user, and every read/write is scoped by
user_id so one account can never reach another account's trips.
"""
import hashlib
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.environ.get(
    "TRAVELPLANNER_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "travelplanner.db"),
)

PBKDF2_ITERATIONS = 240_000
MIN_PASSWORD_LENGTH = 8
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


class AuthError(Exception):
    """Raised when a signup or login attempt is rejected."""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
                display_name  TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                created_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trips (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name       TEXT NOT NULL,
                data       TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, name)
            );

            CREATE INDEX IF NOT EXISTS idx_trips_user ON trips(user_id, updated_at DESC);
            """
        )


# ---------------------------------------------------------------- passwords


def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return digest.hex(), salt


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- accounts


def create_user(username, password, display_name=None):
    username = (username or "").strip()
    if not USERNAME_RE.match(username):
        raise AuthError(
            "Username must be 3-32 characters, letters/numbers/._- only."
        )
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    password_hash, salt = _hash_password(password)
    try:
        with connect() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, display_name, password_hash, salt, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (username, (display_name or username).strip(), password_hash, salt, _now()),
            )
            return {"id": cur.lastrowid, "username": username,
                    "display_name": (display_name or username).strip()}
    except sqlite3.IntegrityError:
        raise AuthError("That username is already taken.")


def verify_user(username, password):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", ((username or "").strip(),)
        ).fetchone()

    # Hash even when the user does not exist so timing does not leak existence.
    salt = row["salt"] if row else secrets.token_hex(16)
    candidate, _ = _hash_password(password or "", salt)
    if row and secrets.compare_digest(candidate, row["password_hash"]):
        return {"id": row["id"], "username": row["username"],
                "display_name": row["display_name"]}
    raise AuthError("Incorrect username or password.")


def change_password(user_id, current_password, new_password):
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise AuthError("Account not found.")
    candidate, _ = _hash_password(current_password or "", row["salt"])
    if not secrets.compare_digest(candidate, row["password_hash"]):
        raise AuthError("Current password is incorrect.")
    if len(new_password or "") < MIN_PASSWORD_LENGTH:
        raise AuthError(f"New password must be at least {MIN_PASSWORD_LENGTH} characters.")
    password_hash, salt = _hash_password(new_password)
    with connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (password_hash, salt, user_id),
        )


# ---------------------------------------------------------------- trips


def list_trips(user_id):
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name, updated_at FROM trips WHERE user_id = ?"
            " ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_trip(user_id, name, state):
    """Insert a trip, or overwrite the same user's trip of that name."""
    name = (name or "Untitled Trip").strip() or "Untitled Trip"
    payload = json.dumps(state, ensure_ascii=False)
    now = _now()
    with connect() as conn:
        conn.execute(
            "INSERT INTO trips (user_id, name, data, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(user_id, name) DO UPDATE SET data = excluded.data,"
            " updated_at = excluded.updated_at",
            (user_id, name, payload, now, now),
        )
        row = conn.execute(
            "SELECT id FROM trips WHERE user_id = ? AND name = ?", (user_id, name)
        ).fetchone()
    return row["id"]


def load_trip(user_id, trip_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT id, name, data FROM trips WHERE id = ? AND user_id = ?",
            (trip_id, user_id),
        ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"], "state": json.loads(row["data"])}


def delete_trip(user_id, trip_id):
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM trips WHERE id = ? AND user_id = ?", (trip_id, user_id)
        )
    return cur.rowcount > 0


def rename_trip(user_id, trip_id, new_name):
    new_name = (new_name or "").strip()
    if not new_name:
        raise ValueError("Trip name cannot be empty.")
    try:
        with connect() as conn:
            conn.execute(
                "UPDATE trips SET name = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (new_name, _now(), trip_id, user_id),
            )
    except sqlite3.IntegrityError:
        raise ValueError("You already have a trip with that name.")


def count_trips(user_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM trips WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row["n"]
