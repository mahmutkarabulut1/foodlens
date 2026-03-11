from rapidfuzz import process, fuzz

from .config import DB_FILE
from .data_loader import load_master_records

database = []
SEARCH_KEYS = []
KEY_TO_ITEM_MAP = {}


def clean_text(text):
    if not text:
        return ""
    return " ".join(str(text).lower().split()).strip()


def load_database():
    global database
    database = load_master_records()


def build_index():
    SEARCH_KEYS.clear()
    KEY_TO_ITEM_MAP.clear()

    seen = set()
    for item in database:
        candidates = {
            item.get("id"),
            item.get("name_tr"),
            item.get("name_en"),
            item.get("name"),
        }

        keywords = item.get("keywords") or []
        if isinstance(keywords, list):
            candidates.update(keywords)

        for candidate in candidates:
            key = clean_text(candidate)
            if len(key) < 2 or key in seen:
                continue
            seen.add(key)
            SEARCH_KEYS.append(key)
            KEY_TO_ITEM_MAP[key] = item


def search(query, limit=5):
    query = clean_text(query)
    matches = process.extract(query, SEARCH_KEYS, scorer=fuzz.token_sort_ratio, limit=limit)

    results = []
    for match_key, score, _ in matches:
        item = KEY_TO_ITEM_MAP[match_key]
        results.append({
            "id": item.get("id"),
            "name": item.get("name_tr") or item.get("name_en") or item.get("name"),
            "score": score,
            "matched_key": match_key,
            "type": item.get("type"),
            "risk_level": item.get("risk_level"),
        })
    return results


load_database()
build_index()


if __name__ == "__main__":
    print(f"Matcher veritabanı yüklendi: {DB_FILE}")
    while True:
        q = input("Arama sorgusu (çıkış için q): ").strip()
        if q.lower() == "q":
            break
        for row in search(q):
            print(row)
        print("-" * 40)
