"""reset_db.py – Reset the development database.

Usage:
    python scripts/reset_db.py [--seed]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from alembic import command
from alembic.config import Config
from app.core.config import settings


def reset_db(seed_data: bool = False) -> None:
    # 1. If SQLite, remove the database file(s)
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.replace("sqlite:///", "")
        # Resolve path relative to backend root if relative
        full_path = Path(db_path) if Path(db_path).is_absolute() else BACKEND_ROOT / db_path
        if full_path.exists():
            full_path.unlink()
            print(f"Removed SQLite database file: {full_path}")
        # Also remove root tuiro.db if it exists
        root_db = BACKEND_ROOT.parent / "tuiro.db"
        if root_db.exists():
            root_db.unlink()
            print(f"Removed root SQLite database file: {root_db}")
    else:
        # PostgreSQL / Neon: drop all tables via Base.metadata
        from app.db import Base, engine
        Base.metadata.drop_all(bind=engine)
        print("Dropped all tables from database.")

    # 2. Run alembic upgrade head to recreate clean schema
    ini_path = BACKEND_ROOT / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    command.upgrade(alembic_cfg, "head")
    print("Recreated schema: alembic upgrade head completed.")

    # 3. Optionally seed default development data
    if seed_data:
        from scripts.seed import seed
        seed()
        print("Database seeded with development data.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset the database")
    parser.add_argument("--seed", action="store_true", help="Seed default development data after reset")
    args = parser.parse_args()
    reset_db(seed_data=args.seed)
