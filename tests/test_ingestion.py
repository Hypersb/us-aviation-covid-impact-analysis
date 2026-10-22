import json
from pathlib import Path

from ingest_bts import acquire, read_manifest


def test_ingestion_is_idempotent(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text("fl_date,cancelled\n2018-01-01,0\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{
        "year": 2018,
        "month": 1,
        "source_url": source.as_uri(),
    }]), encoding="utf-8")
    output = tmp_path / "bronze"
    state = output / "state.json"
    first = acquire(manifest, output, state)
    second = acquire(manifest, output, state)
    assert first["results"][0]["status"] == "acquired"
    assert second["results"][0]["status"] == "already_verified"
    assert (output / "flights_2018-01.csv").read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_manifest_rejects_duplicate_partition(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([
        {"year": 2018, "month": 1, "source_url": "file:///a"},
        {"year": 2018, "month": 1, "source_url": "file:///b"},
    ]), encoding="utf-8")
    try:
        read_manifest(manifest)
    except ValueError as error:
        assert "duplicate" in str(error).lower()
    else:
        raise AssertionError("duplicate partition was accepted")
