from pathlib import Path

from postgres_existing import connection_kwargs


ROOT = Path(__file__).resolve().parents[1]


def test_connection_uses_libpq_environment_without_embedded_secret(monkeypatch):
    monkeypatch.setenv("PGHOST", "localhost")
    monkeypatch.setenv("PGDATABASE", "aviation")
    monkeypatch.setenv("PGUSER", "reader")
    monkeypatch.setenv("PGPASSWORD", "not-a-real-secret")
    settings = connection_kwargs()
    assert settings["host"] == "localhost"
    assert settings["dbname"] == "aviation"
    assert settings["user"] == "reader"
    assert settings["password"] == "not-a-real-secret"


def test_integration_sql_targets_existing_tables_without_import():
    sql = (ROOT / "sql" / "integrate_existing.sql").read_text(encoding="utf-8")
    assert "flights_2019_new" in sql
    assert "flights_2020_new" in sql
    assert "\\copy" not in sql
    statements = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    assert "TRUNCATE" not in statements.upper()
    assert "DROP TABLE" not in statements.upper()
