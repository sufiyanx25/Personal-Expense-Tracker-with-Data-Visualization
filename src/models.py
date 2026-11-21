"""
models.py - Database Models, Schema Definitions, and Connection Factory
========================================================================
Implements SQLite schema creation, foreign key enforcement, default category seeding,
and transaction persistence with duplicate detection.
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "expenses.db"
)

# Required Default Categories specified in Requirements
DEFAULT_CATEGORIES = [
    {"name": "Groceries", "parent": "Expense"},
    {"name": "Food & Dining", "parent": "Expense"},
    {"name": "Transport", "parent": "Expense"},
    {"name": "Bills & Utilities", "parent": "Expense"},
    {"name": "Shopping", "parent": "Expense"},
    {"name": "Entertainment", "parent": "Expense"},
    {"name": "Healthcare", "parent": "Expense"},
    {"name": "Education", "parent": "Expense"},
    {"name": "Rent", "parent": "Expense"},
    {"name": "Travel", "parent": "Expense"},
    {"name": "Income", "parent": "Income"},
    {"name": "Uncategorized", "parent": "Other"},
]

CREATE_CATEGORIES_TABLE = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    parent TEXT DEFAULT NULL
);
"""

CREATE_TRANSACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_date TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'INR',
    account TEXT NOT NULL,
    category_id INTEGER,
    raw_source TEXT DEFAULT 'MANUAL',
    tags TEXT DEFAULT '',
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);
"""

CREATE_BUDGETS_TABLE = """
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,
    category_name TEXT NOT NULL,
    limit_amount REAL NOT NULL,
    UNIQUE(month, category_name)
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(tx_date);",
    "CREATE INDEX IF NOT EXISTS idx_tx_category_id ON transactions(category_id);",
    "CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account);",
    "CREATE INDEX IF NOT EXISTS idx_budget_month ON budgets(month);"
]


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Establish and return a SQLite connection with Row factory enabled and foreign keys activated.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Create tables, indexes, and seed default categories if not already present.
    Preserves all existing data upon restart.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(CREATE_CATEGORIES_TABLE)
        cursor.execute(CREATE_TRANSACTIONS_TABLE)
        cursor.execute(CREATE_BUDGETS_TABLE)
        for idx_sql in CREATE_INDEXES:
            cursor.execute(idx_sql)

        # Seed categories if table is empty
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT OR IGNORE INTO categories (name, parent) VALUES (?, ?)",
                [(cat["name"], cat["parent"]) for cat in DEFAULT_CATEGORIES]
            )
        conn.commit()
    finally:
        conn.close()


def get_categories(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Fetch all categories as dictionaries."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT id, name, parent FROM categories ORDER BY name ASC").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_category_id_by_name(name: str, db_path: str = DEFAULT_DB_PATH) -> Optional[int]:
    """Retrieve category id given category name (case-insensitive)."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (name.strip(),)
        ).fetchone()
        if row:
            return row["id"]
        # Fallback to Uncategorized if available
        fallback = conn.execute(
            "SELECT id FROM categories WHERE LOWER(name) = 'uncategorized'"
        ).fetchone()
        return fallback["id"] if fallback else None
    finally:
        conn.close()


def get_category_name_by_id(cat_id: Optional[int], db_path: str = DEFAULT_DB_PATH) -> str:
    """Retrieve category name by its ID."""
    if cat_id is None:
        return "Uncategorized"
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT name FROM categories WHERE id = ?", (cat_id,)).fetchone()
        return row["name"] if row else "Uncategorized"
    finally:
        conn.close()


def is_duplicate_transaction(
    tx_date: str,
    description: str,
    amount: float,
    account: str,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    """
    Check if a matching transaction already exists to avoid duplicate entries.
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT id FROM transactions
            WHERE tx_date = ? AND description = ? AND ABS(amount - ?) < 0.001 AND account = ?
            LIMIT 1
            """,
            (tx_date.strip(), description.strip(), float(amount), account.strip())
        ).fetchone()
        return row is not None
    finally:
        conn.close()
