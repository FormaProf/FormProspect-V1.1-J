import sqlite3
from pathlib import Path

from core.sqlite_utils import connect_database
from services.training_case_service import TrainingCaseService


def _seed(db: Path):
    with connect_database(db) as conn:
        conn.executescript(
            """
            CREATE TABLE clients(
                id INTEGER PRIMARY KEY, company_name TEXT, contact_name TEXT,
                commercial_name TEXT, folder_path TEXT
            );
            CREATE TABLE trainings(id INTEGER PRIMARY KEY, reference TEXT, name TEXT);
            CREATE TABLE training_sessions(
                id INTEGER PRIMARY KEY, client_id INTEGER, training_id INTEGER,
                start_date TEXT, end_date TEXT, modality TEXT, duration_hours REAL,
                price_cents INTEGER, participant_count INTEGER, trainer_name TEXT,
                funder TEXT, status TEXT
            );
            CREATE TABLE client_workflows(
                id INTEGER PRIMARY KEY, session_id INTEGER, current_step TEXT,
                progress_percent INTEGER, updated_at TEXT
            );
            """
        )
        conn.execute("INSERT INTO clients VALUES (1,'Client Test','Contact','Commercial','%s')" % str(db.parent).replace("'", "''"))
        conn.execute("INSERT INTO trainings VALUES (1,'T-001','Formation Test')")
        conn.execute("INSERT INTO training_sessions VALUES (1,1,1,'2026-07-20','2026-07-21','Distance',14,150000,1,'Mélanie','FAFCEA','Planifiée')")
        conn.execute("INSERT INTO client_workflows VALUES (1,1,'Client créé',10,'2026-07-20')")


def test_case_exposes_latest_quote_file_and_can_delete(tmp_path):
    db = tmp_path / "project.db"
    _seed(db)
    service = TrainingCaseService(db)
    request_id = service.create_quote_request(1, "Commercial")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4 test")
    archived = service.import_quote_pdf(request_id, source)

    case = service.list_cases()[0]
    assert case["quote_request_id"] == request_id
    assert Path(case["quote_file_path"]) == archived
    assert service.get_quote_file(request_id) == archived

    service.delete_training_case(1)
    with connect_database(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM training_sessions").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM quote_requests").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 1
