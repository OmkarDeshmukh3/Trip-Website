from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "smart_travel.db"


def get_connection():
    connection = sqlite3.connect(str(DATABASE))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
