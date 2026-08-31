from pathlib import Path

from scripts.migrate import list_migration_files, pending_migrations


def test_list_migration_files_sorted(tmp_path: Path):
    (tmp_path / "002_b.sql").write_text("SELECT 1;")
    (tmp_path / "001_a.sql").write_text("SELECT 1;")
    (tmp_path / "readme.txt").write_text("nope")
    (tmp_path / "subdir").mkdir()
    names = [p.name for p in list_migration_files(tmp_path)]
    assert names == ["001_a.sql", "002_b.sql"]


def test_pending_migrations_skips_applied(tmp_path: Path):
    a = tmp_path / "001_a.sql"
    b = tmp_path / "002_b.sql"
    a.write_text("SELECT 1;")
    b.write_text("SELECT 1;")
    files = list_migration_files(tmp_path)
    pending = pending_migrations(files, {"001_a.sql"})
    assert [p.name for p in pending] == ["002_b.sql"]


def test_pending_migrations_all_new(tmp_path: Path):
    a = tmp_path / "001_a.sql"
    a.write_text("SELECT 1;")
    files = list_migration_files(tmp_path)
    pending = pending_migrations(files, set())
    assert [p.name for p in pending] == ["001_a.sql"]
