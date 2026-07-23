from __future__ import annotations

import sqlite3
from core.sqlite_utils import connect_database
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class SequenceStats:
    sequences: int
    enrolled: int
    active: int
    due_today: int
    completed: int


class SequenceService:
    """Centre local de séquences commerciales."""

    STEP_TYPES = ("E-mail", "Appel", "Relance", "Cas client", "Rendez-vous", "Tâche")

    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self._ensure_tables()

    def _connect(self):
        conn = connect_database(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sequences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Brouillon',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sequence_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sequence_id INTEGER NOT NULL,
                    step_order INTEGER NOT NULL,
                    day_offset INTEGER NOT NULL DEFAULT 0,
                    step_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    instructions TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(sequence_id) REFERENCES sequences(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS sequence_enrollments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sequence_id INTEGER NOT NULL,
                    prospect_id INTEGER NOT NULL,
                    current_step INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'Active',
                    started_at TEXT NOT NULL,
                    next_action_at TEXT,
                    completed_at TEXT,
                    UNIQUE(sequence_id, prospect_id),
                    FOREIGN KEY(sequence_id) REFERENCES sequences(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS sequence_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enrollment_id INTEGER NOT NULL,
                    step_id INTEGER,
                    event_type TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(enrollment_id) REFERENCES sequence_enrollments(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_sequence_enrollments_due
                ON sequence_enrollments(status, next_action_at);
            """)
            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def create_sequence(self, name: str, description: str = "") -> int:
        name = str(name or "").strip()
        if not name:
            raise ValueError("Le nom de la séquence est obligatoire.")
        now = self._now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO sequences(name, description, status, created_at, updated_at) VALUES (?, ?, 'Brouillon', ?, ?)",
                (name, str(description or "").strip(), now, now),
            )
            conn.commit()
            return int(cur.lastrowid)

    def add_step(self, sequence_id: int, day_offset: int, step_type: str, title: str, instructions: str = "") -> int:
        title = str(title or "").strip()
        if not title:
            raise ValueError("Le titre de l'étape est obligatoire.")
        with self._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM sequence_steps WHERE sequence_id=?",
                (int(sequence_id),),
            ).fetchone()[0]
            cur = conn.execute(
                """
                INSERT INTO sequence_steps(sequence_id, step_order, day_offset, step_type, title, instructions)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (int(sequence_id), int(count) + 1, max(0, int(day_offset)), step_type, title, str(instructions or "").strip()),
            )
            conn.execute(
                "UPDATE sequences SET updated_at=? WHERE id=?",
                (self._now(), int(sequence_id)),
            )
            conn.commit()
            return int(cur.lastrowid)

    def sequences(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT s.*,
                       COUNT(DISTINCT st.id) AS step_count,
                       COUNT(DISTINCT e.id) AS enrollment_count,
                       SUM(CASE WHEN e.status='Active' THEN 1 ELSE 0 END) AS active_count
                FROM sequences s
                LEFT JOIN sequence_steps st ON st.sequence_id=s.id
                LEFT JOIN sequence_enrollments e ON e.sequence_id=s.id
                GROUP BY s.id
                ORDER BY s.id DESC
            """).fetchall()
        return [dict(r) for r in rows]

    def steps(self, sequence_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sequence_steps WHERE sequence_id=? ORDER BY step_order",
                (int(sequence_id),),
            ).fetchall()
        return [dict(r) for r in rows]

    def activate(self, sequence_id: int) -> None:
        if not self.steps(sequence_id):
            raise ValueError("Ajoutez au moins une étape avant d'activer la séquence.")
        with self._connect() as conn:
            conn.execute(
                "UPDATE sequences SET status='Active', updated_at=? WHERE id=?",
                (self._now(), int(sequence_id)),
            )
            conn.commit()

    def enroll_eligible_prospects(self, sequence_id: int, min_score: int = 45, limit: int = 500) -> int:
        steps = self.steps(sequence_id)
        if not steps:
            raise ValueError("La séquence ne contient aucune étape.")
        first = steps[0]
        with self._connect() as conn:
            prospects = conn.execute("""
                SELECT id FROM prospects
                WHERE COALESCE(score_prospect,0) >= ?
                  AND COALESCE(pipeline,'') NOT LIKE '%Perdu%'
                  AND COALESCE(pipeline,'') NOT LIKE '%Client%'
                  AND (COALESCE(TRIM(email),'') != '' OR COALESCE(TRIM(telephone),'') != '')
                ORDER BY COALESCE(score_prospect,0) DESC
                LIMIT ?
            """, (max(0, min(int(min_score), 100)), max(1, min(int(limit), 5000)))).fetchall()
            now = datetime.now()
            due = now + timedelta(days=int(first["day_offset"]))
            added = 0
            for row in prospects:
                cur = conn.execute("""
                    INSERT OR IGNORE INTO sequence_enrollments(
                        sequence_id, prospect_id, current_step, status, started_at, next_action_at
                    ) VALUES (?, ?, 1, 'Active', ?, ?)
                """, (int(sequence_id), int(row["id"]), now.isoformat(timespec="seconds"), due.isoformat(timespec="seconds")))
                added += cur.rowcount
            conn.commit()
        return added

    def enrollments(self, sequence_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT e.*, p.entreprise, p.telephone, p.email, p.score_prospect,
                       st.title AS current_title, st.step_type, st.day_offset
                FROM sequence_enrollments e
                JOIN prospects p ON p.id=e.prospect_id
                LEFT JOIN sequence_steps st
                  ON st.sequence_id=e.sequence_id AND st.step_order=e.current_step
                WHERE e.sequence_id=?
                ORDER BY CASE WHEN e.status='Active' THEN 0 ELSE 1 END,
                         e.next_action_at ASC, p.entreprise
            """, (int(sequence_id),)).fetchall()
        return [dict(r) for r in rows]

    def complete_current_step(self, enrollment_id: int, notes: str = "") -> None:
        with self._connect() as conn:
            enrollment = conn.execute(
                "SELECT * FROM sequence_enrollments WHERE id=?",
                (int(enrollment_id),),
            ).fetchone()
            if enrollment is None:
                raise ValueError("Inscription introuvable.")
            current = conn.execute("""
                SELECT * FROM sequence_steps
                WHERE sequence_id=? AND step_order=?
            """, (enrollment["sequence_id"], enrollment["current_step"])).fetchone()
            conn.execute("""
                INSERT INTO sequence_events(enrollment_id, step_id, event_type, notes, created_at)
                VALUES (?, ?, 'Étape terminée', ?, ?)
            """, (int(enrollment_id), current["id"] if current else None, str(notes or "").strip(), self._now()))

            next_step = conn.execute("""
                SELECT * FROM sequence_steps
                WHERE sequence_id=? AND step_order=?
            """, (enrollment["sequence_id"], int(enrollment["current_step"]) + 1)).fetchone()
            if next_step is None:
                conn.execute("""
                    UPDATE sequence_enrollments
                    SET status='Terminée', completed_at=?, next_action_at=NULL
                    WHERE id=?
                """, (self._now(), int(enrollment_id)))
            else:
                started = datetime.fromisoformat(enrollment["started_at"])
                due = started + timedelta(days=int(next_step["day_offset"]))
                conn.execute("""
                    UPDATE sequence_enrollments
                    SET current_step=current_step+1, next_action_at=?
                    WHERE id=?
                """, (due.isoformat(timespec="seconds"), int(enrollment_id)))
            conn.commit()

    def stats(self) -> SequenceStats:
        today = date.today().isoformat()
        with self._connect() as conn:
            sequences = conn.execute("SELECT COUNT(*) FROM sequences").fetchone()[0]
            row = conn.execute("""
                SELECT COUNT(*) AS enrolled,
                       SUM(CASE WHEN status='Active' THEN 1 ELSE 0 END) AS active,
                       SUM(CASE WHEN status='Terminée' THEN 1 ELSE 0 END) AS completed,
                       SUM(CASE WHEN status='Active' AND substr(next_action_at,1,10) <= ? THEN 1 ELSE 0 END) AS due_today
                FROM sequence_enrollments
            """, (today,)).fetchone()
        return SequenceStats(
            int(sequences or 0),
            int(row["enrolled"] or 0),
            int(row["active"] or 0),
            int(row["due_today"] or 0),
            int(row["completed"] or 0),
        )
