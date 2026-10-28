"""Resumable, manifest-driven BTS monthly acquisition.

The BTS download interface is interactive, so this tool deliberately requires
an input manifest containing the exact source URL for each requested month.
It never invents URLs and never overwrites an existing verified partition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse


YEARS = range(2018, 2024)


@dataclass(frozen=True)
class Partition:
    year: int
    month: int
    source_url: str
    expected_sha256: str = ""

    @property
    def key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path: Path) -> list[Partition]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    partitions = [Partition(int(row["year"]), int(row["month"]), row["source_url"],
                            row.get("expected_sha256", "")) for row in rows]
    keys = [partition.key for partition in partitions]
    if len(keys) != len(set(keys)):
        raise ValueError("Manifest contains duplicate year-month partitions")
    invalid = [partition.key for partition in partitions
               if partition.year not in YEARS or not 1 <= partition.month <= 12]
    if invalid:
        raise ValueError(f"Manifest contains invalid partitions: {invalid}")
    return partitions


def acquire(manifest: Path, output_dir: Path, state_path: Path) -> dict:
    partitions = read_manifest(manifest)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for partition in partitions:
        destination = output_dir / f"flights_{partition.key}.csv"
        prior = state.get(partition.key, {})
        if destination.exists() and prior.get("sha256") == sha256_file(destination):
            results.append({"partition": partition.key, "status": "already_verified",
                            "sha256": prior["sha256"]})
            continue
        temporary = destination.with_suffix(".part")
        if partition.source_url.startswith("file://"):
            parsed = urlparse(partition.source_url)
            parsed_path = unquote(parsed.path)
            if os.name == "nt" and len(parsed_path) >= 3 and parsed_path[0] == "/" and parsed_path[2] == ":":
                parsed_path = parsed_path[1:]
            source_path = Path(parsed_path)
            if parsed.netloc and parsed.netloc.lower() not in ("localhost",):
                source_path = Path(f"//{parsed.netloc}{unquote(parsed.path)}")
            shutil.copyfile(source_path, temporary)
        else:
            request = urllib.request.Request(partition.source_url, headers={"User-Agent": "aviation-analysis/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        digest = sha256_file(temporary)
        if partition.expected_sha256 and digest != partition.expected_sha256:
            temporary.unlink()
            raise ValueError(f"Checksum mismatch for {partition.key}")
        temporary.replace(destination)
        state[partition.key] = {"source_url": partition.source_url, "sha256": digest,
                                "status": "acquired"}
        results.append({"partition": partition.key, "status": "acquired", "sha256": digest})
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return {"requested": len(partitions), "results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data_bronze"))
    parser.add_argument("--state", type=Path, default=Path("data_bronze/ingestion_state.json"))
    args = parser.parse_args()
    print(json.dumps(acquire(args.manifest, args.output_dir, args.state), indent=2))


if __name__ == "__main__":
    main()
