from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List

from ..preprocessing.normalize import ascii_fold, normalize_for_matching


TYPE_PRIORITY_DEFAULT = {
    "allergen": 3,
    "additive": 2,
    "ingredient": 1,
}

TYPE_PRIORITY_BY_SECTION = {
    "ingredient_section": {"additive": 3, "ingredient": 2, "allergen": 1},
    "allergen_section": {"allergen": 3, "ingredient": 2, "additive": 1},
    "may_contain_section": {"allergen": 3, "ingredient": 2, "additive": 1},
    "free_from_section": {"allergen": 3, "ingredient": 2, "additive": 1},
}

COPULA_SUFFIX_RE = re.compile(r"(dir|dır|dur|dür|tir|tır|tur|tür)$", re.IGNORECASE)


def _display_name(item: Dict[str, str]) -> str:
    return item.get("name_tr") or item.get("name_en") or item.get("name") or item.get("id") or ""


def _parse_keywords(value: str) -> List[str]:
    if not value:
        return []
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        try:
            data = json.loads(value)
            if isinstance(data, list):
                return [str(x) for x in data if str(x).strip()]
        except Exception:
            pass
    return [chunk.strip() for chunk in value.split(",") if chunk.strip()]


def _candidate_aliases(row: Dict[str, str]) -> List[str]:
    aliases = {
        row.get("id", ""),
        row.get("name_tr", ""),
        row.get("name_en", ""),
        row.get("name", ""),
    }
    aliases.update(_parse_keywords(row.get("keywords", "")))
    return [alias for alias in aliases if alias and str(alias).strip()]


def _alias_variants(alias: str) -> List[str]:
    variants = []
    norm = normalize_for_matching(alias)
    folded = ascii_fold(alias)
    for item in [norm, folded]:
        if item and item not in variants:
            variants.append(item)
        if item:
            parts = item.split()
            if parts:
                stripped = COPULA_SUFFIX_RE.sub("", parts[-1]).strip()
                if stripped and stripped != parts[-1]:
                    alt = " ".join(parts[:-1] + [stripped]).strip()
                    if alt and alt not in variants:
                        variants.append(alt)
    return variants


class MasterLexicon:
    def __init__(self, csv_path: Path):
        self.csv_path = Path(csv_path)
        self.records: List[Dict[str, str]] = []
        self.alias_map: Dict[str, List[Dict[str, str]]] = {}
        self.load()

    def load(self) -> None:
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                display_name = _display_name(row)
                item_type = (row.get("type") or "").strip().lower()
                if not display_name or not item_type:
                    continue

                record = {
                    "id": row.get("id", "").strip(),
                    "name": display_name.strip(),
                    "item_type": item_type,
                    "risk_level": (row.get("risk_level") or "Unknown").strip() or "Unknown",
                    "description": (row.get("description_tr") or row.get("note") or "").strip(),
                }
                self.records.append(record)

                for alias in _candidate_aliases(row):
                    for variant in _alias_variants(alias):
                        self.alias_map.setdefault(variant, []).append(record)

    def _pick_best(self, matches: List[Dict[str, str]], section_type: str) -> Dict[str, str]:
        section_priority = TYPE_PRIORITY_BY_SECTION.get(section_type, TYPE_PRIORITY_DEFAULT)
        return max(
            matches,
            key=lambda rec: (
                section_priority.get(rec["item_type"], 0),
                TYPE_PRIORITY_DEFAULT.get(rec["item_type"], 0),
                len(rec["name"]),
            ),
        )

    def exact_lookup(self, alias: str, section_type: str) -> Dict[str, str] | None:
        for variant in _alias_variants(alias):
            if variant in self.alias_map:
                return self._pick_best(self.alias_map[variant], section_type)
        return None
