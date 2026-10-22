from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sql_uses_valid_delay_threshold():
    sql = (ROOT / "sql" / "business_questions.sql").read_text(encoding="utf-8")
    assert "COUNT(arr_delay) FILTER" in sql
    assert "arr_delay IS NOT NULL" in sql


def test_sql_reason_grouping_has_unknown_bucket():
    sql = (ROOT / "sql" / "analytical_queries.sql").read_text(encoding="utf-8")
    assert "ELSE 'Unknown'" in sql
    assert "WHEN 'D' THEN 'Security'" in sql
