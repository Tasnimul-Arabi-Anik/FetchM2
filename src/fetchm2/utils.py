from __future__ import annotations

import csv
import json
from importlib import resources
from pathlib import Path
from typing import Any, Iterable


def data_path(filename: str) -> Path:
    return Path(str(resources.files("fetchm2.data").joinpath(filename)))


def read_package_csv(filename: str) -> list[dict[str, str]]:
    path = data_path(filename)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_package_json(filename: str) -> Any:
    return json.loads(data_path(filename).read_text(encoding="utf-8"))


def first_present(row: dict[str, Any], names: Iterable[str]) -> str:
    lower_lookup = {str(key).strip().lower(): key for key in row}
    for name in names:
        key = lower_lookup.get(name.strip().lower())
        if key is None:
            continue
        value = row.get(key)
        text = "" if value is None else str(value).strip()
        if text:
            return text
    return ""


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_fieldnames: list[str] = list(fieldnames or [])
    seen: set[str] = set()
    for key in resolved_fieldnames:
        seen.add(key)
    for row in rows:
        for key in row:
            if key not in seen:
                resolved_fieldnames.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=resolved_fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
