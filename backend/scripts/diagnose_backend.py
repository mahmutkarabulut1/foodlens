from pathlib import Path
from collections import defaultdict, Counter
import json
import time
import statistics
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from backend.app.main import (
    DB_FILE,
    clean_text,
    analyze_image,
    ImageRequest,
    SEARCH_KEYS,
    database,
)

def safe_type(item):
    return item.get("type", "UNKNOWN")

def build_collision_report(items):
    key_to_items = defaultdict(list)
    short_keys = []
    generic_keys = []

    for item in items:
        candidates = {
            item.get("id"),
            item.get("name_tr"),
            item.get("name_en"),
            item.get("name"),
        }

        keywords = item.get("keywords") or []
        if isinstance(keywords, list):
            candidates.update(keywords)

        for c in candidates:
            if not c:
                continue
            ck = clean_text(c)
            if len(ck) < 2:
                continue

            key_to_items[ck].append({
                "id": item.get("id"),
                "name": item.get("name_tr") or item.get("name_en") or item.get("name"),
                "type": item.get("type"),
            })

            if len(ck) <= 3:
                short_keys.append(ck)

            if len(ck.split()) == 1 and len(ck) <= 5:
                generic_keys.append(ck)

    collisions = {
        k: v for k, v in key_to_items.items()
        if len({(x["id"], x["name"]) for x in v}) > 1
    }

    return key_to_items, collisions, Counter(short_keys), Counter(generic_keys)

def benchmark():
    scenarios = [
        "İçindekiler: Mısır irmiği, palm yağı, aroma verici, E621, E627, E631, peynir altı suyu tozu, tuz, E160c.",
        "Ingredients: Water, Carbon Dioxide, Renklendirici (E150d), Phosphoric Acid, Tatlandırıcılar (Aspartam, Asesülfam K), E330, Cafein.",
        "Buğday unu, şeker, bitkisel yağ, kabartıcılar (amonyum hidrojen karbonat, sodyum hidrojen karbonat), yağsız süt tozu, emülgatör (soya lesitini), tuz.",
        "icindekiler: misir surubu, potesyum sorbat, sodyum benzoet, sitrik asid, e-102 tartrazin.",
        "İçindekiler: su, şeker, asitlik düzenleyici sitrik asit, koruyucu potasyum sorbat, sodyum benzoat, aroma vericiler."
    ]

    times = []
    details = []

    for text in scenarios:
        run_times = []
        result_count = None

        for _ in range(3):
            t0 = time.perf_counter()
            result = analyze_image(ImageRequest(ocr_text=text))
            dt = (time.perf_counter() - t0) * 1000
            run_times.append(dt)
            result_count = len(result.get("results", []))

        avg_ms = statistics.mean(run_times)
        max_ms = max(run_times)
        min_ms = min(run_times)

        details.append({
            "text": text[:90],
            "avg_ms": round(avg_ms, 2),
            "min_ms": round(min_ms, 2),
            "max_ms": round(max_ms, 2),
            "result_count": result_count,
        })
        times.append(avg_ms)

    return details, times

def main():
    print("===== DIAGNOSE BACKEND =====")
    print(f"DB_FILE: {DB_FILE}")
    print(f"DATABASE_ITEMS: {len(database)}")
    print(f"SEARCH_KEYS: {len(SEARCH_KEYS)}")

    type_counter = Counter(safe_type(item) for item in database)
    print("\n===== ITEM TYPES =====")
    for k, v in sorted(type_counter.items()):
        print(f"{k}: {v}")

    key_to_items, collisions, short_keys, generic_keys = build_collision_report(database)

    print("\n===== KEY STATS =====")
    print(f"RAW_UNIQUE_CLEAN_KEYS: {len(key_to_items)}")
    print(f"COLLISION_KEY_COUNT: {len(collisions)}")
    print(f"SHORT_KEYS_LEN_LE_3_COUNT: {sum(short_keys.values())}")
    print(f"GENERIC_ONEWORD_LEN_LE_5_COUNT: {sum(generic_keys.values())}")

    print("\n===== TOP 20 COLLISIONS =====")
    shown = 0
    for key, items in sorted(collisions.items(), key=lambda x: len(x[1]), reverse=True):
        uniq = []
        seen = set()
        for item in items:
            sig = (item["id"], item["name"], item["type"])
            if sig not in seen:
                uniq.append(item)
                seen.add(sig)
        print(f"\nKEY: {key}")
        for item in uniq[:8]:
            print(f"  - id={item['id']} | type={item['type']} | name={item['name']}")
        shown += 1
        if shown >= 20:
            break

    print("\n===== TOP 20 SHORT KEYS =====")
    for k, v in short_keys.most_common(20):
        print(f"{k}: {v}")

    print("\n===== TOP 20 GENERIC KEYS =====")
    for k, v in generic_keys.most_common(20):
        print(f"{k}: {v}")

    print("\n===== BENCHMARK =====")
    details, times = benchmark()
    for row in details:
        print(f"\nTEXT: {row['text']}")
        print(f"AVG_MS={row['avg_ms']} | MIN_MS={row['min_ms']} | MAX_MS={row['max_ms']} | RESULTS={row['result_count']}")

    print("\n===== BENCHMARK SUMMARY =====")
    print(f"OVERALL_AVG_MS: {round(statistics.mean(times), 2)}")
    print(f"OVERALL_MAX_MS: {round(max(times), 2)}")
    print(f"OVERALL_MIN_MS: {round(min(times), 2)}")

if __name__ == "__main__":
    main()
