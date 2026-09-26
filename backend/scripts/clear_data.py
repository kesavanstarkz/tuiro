"""Temporary script to clear all data from the database while preserving table schemas."""
from pathlib import Path
import sqlite3

def clear_database():
    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "tuiro.db"
    sql_path = base_dir / "clear_all_data.sql"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    if not sql_path.exists():
        print(f"SQL file not found at {sql_path}")
        return

    print(f"Clearing all data from: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        conn.executescript(sql_script)
        print("✓ All tables cleared successfully.")
        print("✓ Table structures and alembic migrations preserved.")
        print("✓ Default FREE subscription plan initialized.")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_database()
