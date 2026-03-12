from __future__ import annotations

from .analysis.engine import FoodLensAnalysisEngine

_engine = FoodLensAnalysisEngine()


def search(query: str, limit: int = 5):
    record = _engine.lexicon.exact_lookup(query, "ingredient_section")
    if not record:
        return []
    return [{
        "id": record["id"],
        "name": record["name"],
        "score": 100,
        "matched_key": query,
        "type": record["item_type"],
        "risk_level": record["risk_level"],
    }]


if __name__ == "__main__":
    print(f"Matcher veritabanı yüklendi: {_engine.db_file}")
    while True:
        q = input("Arama sorgusu (çıkış için q): ").strip()
        if q.lower() == "q":
            break
        for row in search(q):
            print(row)
        print("-" * 40)
