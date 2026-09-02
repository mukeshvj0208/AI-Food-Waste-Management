import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "foodbridge.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with get_connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity REAL NOT NULL CHECK(quantity >= 0),
                unit TEXT NOT NULL DEFAULT 'kg',
                expiry_date TEXT NOT NULL,
                donor TEXT NOT NULL,
                barcode TEXT UNIQUE,
                notes TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'available',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                action TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(item_id) REFERENCES inventory_items(id) ON DELETE SET NULL
            );
            """
        )


def log_activity(db: sqlite3.Connection, item_id: int | None, action: str, detail: str) -> None:
    db.execute(
        "INSERT INTO activity_log (item_id, action, detail) VALUES (?, ?, ?)",
        (item_id, action, detail),
    )
