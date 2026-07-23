import sqlite3
from core.sqlite_utils import connect_database
from services.training_case_service import TrainingCaseService

def test_schema_creation(tmp_path):
    db=tmp_path / "project.db"
    with connect_database(db) as c:
        c.executescript("CREATE TABLE clients(id INTEGER PRIMARY KEY); CREATE TABLE training_sessions(id INTEGER PRIMARY KEY);")
    TrainingCaseService(db)
    with connect_database(db) as c:
        assert c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quote_requests'").fetchone()
