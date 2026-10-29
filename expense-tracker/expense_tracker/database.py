"""Data layer: owns the SQLite connection and schema."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL CHECK (amount > 0),
    category TEXT NOT NULL,
    note TEXT DEFAULT '',
    spent_on TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(spent_on);
"""


def connect(path: str = "expenses.db") -> sqlite3.Connection:
    """Open a connection (use ':memory:' for tests) and make sure the schema exists."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
