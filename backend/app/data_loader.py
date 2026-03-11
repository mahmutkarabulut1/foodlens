from __future__ import annotations

import csv
import json
from functools import lru_cache
from typing import Any, Dict, List

from .config import (
    MASTER_CSV_FILE,
    REFERENCE_ADDITIVES_CSV,
    REFERENCE_ALLERGENS_CSV,
    REFERENCE_INGREDIENTS_CSV,
)

Record = Dict[str, Any]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_keywords(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    s = str(value).strip()
    if not s:
        return []

    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass

    return [part.strip() for part in s.split(",") if part.strip()]


def get_display_name(record: Record) -> str:
    return (
        _clean(record.get("name_tr"))
        or _clean(record.get("name_en"))
        or _clean(record.get("name"))
        or _clean(record.get("id"))
    )


def _read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _is_valid_master_row(row: Record) -> bool:
    has_name = any(
        _clean(row.get(k))
        for k in ("name_tr", "name_en", "name")
    )
    has_type = _clean(row.get("type"))
    return bool(has_name and has_type)


@lru_cache(maxsize=1)
def load_master_records() -> List[Record]:
    rows = _read_csv(MASTER_CSV_FILE)
    cleaned_rows: List[Record] = []

    for row in rows:
        if not _is_valid_master_row(row):
            continue

        row = dict(row)
        row["keywords_raw"] = row.get("keywords", "")
        row["keywords"] = parse_keywords(row.get("keywords"))
        row["display_name"] = get_display_name(row)
        row["search_text"] = " ".join(
            part for part in [
                _clean(row.get("id")),
                _clean(row.get("name_tr")),
                _clean(row.get("name_en")),
                _clean(row.get("name")),
                _clean(row.get("type")),
                _clean(row.get("description_tr")),
                " ".join(row["keywords"]),
            ] if part
        ).lower()
        cleaned_rows.append(row)

    return cleaned_rows


@lru_cache(maxsize=1)
def load_reference_additives() -> List[Record]:
    return _read_csv(REFERENCE_ADDITIVES_CSV)


@lru_cache(maxsize=1)
def load_reference_allergens() -> List[Record]:
    return _read_csv(REFERENCE_ALLERGENS_CSV)


@lru_cache(maxsize=1)
def load_reference_ingredients() -> List[Record]:
    return _read_csv(REFERENCE_INGREDIENTS_CSV)
