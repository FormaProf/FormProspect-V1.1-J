import sqlite3
from core.sqlite_utils import connect_database


class BaseRepository:
    def __init__(self, database_path):
        self.database_path = database_path

    def get_connection(self):
        return connect_database(self.database_path)