from __future__ import annotations

import sys
from pathlib import Path

import psycopg2

from app.config import get_settings


def list_migration_files(mig_dir: Path) -> list[Path]:
    """Return migration SQL files sorted by filename (Go parity)."""
    return sorted(p for p in mig_dir.glob("*.sql") if p.is_file())


def pending_migrations(files: list[Path], applied: set[str]) -> list[Path]:
    """Return migration files not yet recorded in schema_migrations."""
    return [p for p in files if p.name not in applied]


def main() -> int:
    settings = get_settings()
    root = Path(__file__).resolve().parents[1]
    mig_dir = root / "migrations"
    conn = None
    try:
        conn = psycopg2.connect(settings.sync_dsn())
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("SELECT version FROM schema_migrations")
            applied = {r[0] for r in cur.fetchall()}
            files = list_migration_files(mig_dir)
            for path in files:
                name = path.name
                if name in applied:
                    print(f"  skipping {name} (already applied)")
                    continue
                sql = path.read_text(encoding="utf-8")
                print(f"  running {name} ...")
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (name,),
                )
                print("  done")
        conn.commit()
        print("migrate: all migrations complete")
        return 0
    except Exception as e:
        if conn is not None:
            conn.rollback()
        print(f"migrate failed: {e}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
