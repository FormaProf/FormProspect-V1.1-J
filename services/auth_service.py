from __future__ import annotations

import sqlite3
from core.sqlite_utils import connect_database
import shutil
import secrets
from datetime import datetime
from pathlib import Path

from core.paths import user_data_dir
from core.security import hash_password, verify_password
from core.session import AuthenticatedUser


class AuthService:
    ROLES = ("Administrateur", "Manager", "Commercial")

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = Path(database_path) if database_path else user_data_dir() / "accounts.db"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        conn = connect_database(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    first_name TEXT NOT NULL DEFAULT '',
                    last_name TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'Commercial',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    photo_path TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS license (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    license_key TEXT NOT NULL DEFAULT 'LOCAL-DEVELOPMENT',
                    plan TEXT NOT NULL DEFAULT 'Pro',
                    status TEXT NOT NULL DEFAULT 'Active',
                    expires_at TEXT,
                    max_users INTEGER NOT NULL DEFAULT 10,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT OR IGNORE INTO license (id, updated_at) VALUES (1, ?)",
                (datetime.now().isoformat(timespec="seconds"),),
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "photo_path" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN photo_path TEXT NOT NULL DEFAULT ''")
            if "cloud_user_id" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN cloud_user_id TEXT")
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_cloud_user_id ON users(cloud_user_id)")

    def has_users(self) -> bool:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]) > 0

    def create_user(
        self,
        username: str,
        password: str,
        *,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        role: str = "Commercial",
    ) -> int:
        username = username.strip()
        if len(username) < 3:
            raise ValueError("L'identifiant doit contenir au moins 3 caractères.")
        if role not in self.ROLES:
            raise ValueError("Rôle utilisateur invalide.")
        with self._connect() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO users (
                        username, first_name, last_name, email,
                        password_hash, role, active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        username,
                        first_name.strip(),
                        last_name.strip(),
                        email.strip(),
                        hash_password(password),
                        role,
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
                return int(cursor.lastrowid)
            except sqlite3.IntegrityError as exc:
                raise ValueError("Cet identifiant existe déjà.") from exc

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE AND active = 1",
                (username.strip(),),
            ).fetchone()
            if row is None or not verify_password(password, row["password_hash"]):
                return None
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), row["id"]),
            )
            return self._to_user(row)

    def sync_cloud_user(
        self,
        *,
        cloud_user_id: str,
        email: str,
        first_name: str,
        last_name: str,
        role: str,
    ) -> AuthenticatedUser:
        """Maintain an inert numeric shadow profile for legacy local relations."""
        now = datetime.now().isoformat(timespec="seconds")
        username = email.strip().lower()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE cloud_user_id = ? OR username = ? COLLATE NOCASE",
                (cloud_user_id, username),
            ).fetchone()
            if row:
                conn.execute(
                    """UPDATE users SET username = ?, first_name = ?, last_name = ?,
                       email = ?, role = ?, active = 1, last_login = ?, cloud_user_id = ? WHERE id = ?""",
                    (username, first_name, last_name, email, role, now, cloud_user_id, row["id"]),
                )
                user_id = int(row["id"])
            else:
                cursor = conn.execute(
                    """INSERT INTO users (username, first_name, last_name, email,
                       password_hash, role, active, created_at, last_login, cloud_user_id)
                       VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
                    (
                        username,
                        first_name,
                        last_name,
                        email,
                        hash_password(secrets.token_urlsafe(48)),
                        role,
                        now,
                        now,
                        cloud_user_id,
                    ),
                )
                user_id = int(cursor.lastrowid)
        user = self.get_user(user_id)
        if user is None:
            raise RuntimeError("Le profil local technique n'a pas pu être synchronisé.")
        return user

    def list_users(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, username, first_name, last_name, email, role, active, created_at, last_login, photo_path "
                "FROM users ORDER BY active DESC, username COLLATE NOCASE"
            ).fetchall()
        return [dict(row) for row in rows]

    def set_active(self, user_id: int, active: bool) -> None:
        with self._connect() as conn:
            row = conn.execute("SELECT role, active FROM users WHERE id = ?", (user_id,)).fetchone()
            if row is None:
                raise ValueError("Utilisateur introuvable.")
            if not active and row["role"] == "Administrateur":
                count = conn.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'Administrateur' AND active = 1"
                ).fetchone()[0]
                if int(count) <= 1:
                    raise ValueError("Le dernier administrateur actif ne peut pas être désactivé.")
            conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))

    def reset_password(self, user_id: int, new_password: str) -> None:
        with self._connect() as conn:
            if conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                raise ValueError("Utilisateur introuvable.")
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), user_id),
            )

    def change_password(self, user_id: int, current_password: str, new_password: str) -> None:
        with self._connect() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
            if row is None or not verify_password(current_password, row["password_hash"]):
                raise ValueError("Le mot de passe actuel est incorrect.")
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), user_id),
            )


    def get_user_record(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, first_name, last_name, email, role, active, created_at, last_login, photo_path FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_user(self, user_id: int) -> AuthenticatedUser | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._to_user(row) if row else None

    def update_profile_photo(self, user_id: int, source_path: str | Path) -> str:
        source = Path(source_path)
        if not source.is_file():
            raise ValueError("La photo sélectionnée est introuvable.")
        if source.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise ValueError("Seuls les fichiers JPG et PNG sont acceptés.")
        target_dir = user_data_dir() / "profile_photos"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"user_{user_id}{source.suffix.lower()}"
        for old in target_dir.glob(f"user_{user_id}.*"):
            try:
                old.unlink()
            except OSError:
                pass
        shutil.copy2(source, target)
        with self._connect() as conn:
            if conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                raise ValueError("Utilisateur introuvable.")
            conn.execute("UPDATE users SET photo_path = ? WHERE id = ?", (str(target), user_id))
        return str(target)

    def remove_profile_photo(self, user_id: int) -> None:
        record = self.get_user_record(user_id)
        if record and record.get("photo_path"):
            try:
                Path(record["photo_path"]).unlink(missing_ok=True)
            except OSError:
                pass
        with self._connect() as conn:
            conn.execute("UPDATE users SET photo_path = '' WHERE id = ?", (user_id,))

    def license_info(self) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM license WHERE id = 1").fetchone()
        return dict(row) if row else {}

    @staticmethod
    def _to_user(row: sqlite3.Row) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=int(row["id"]),
            username=row["username"],
            first_name=row["first_name"] or "",
            last_name=row["last_name"] or "",
            email=row["email"] or "",
            role=row["role"],
            photo_path=row["photo_path"] if "photo_path" in row.keys() else "",
            cloud_user_id=row["cloud_user_id"] if "cloud_user_id" in row.keys() and row["cloud_user_id"] else "",
        )
