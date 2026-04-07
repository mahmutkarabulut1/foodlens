import os
import requests
import time

API_URL = os.getenv("FOODLENS_API_URL", "http://127.0.0.1:8000/analyze")

scenarios = [
    {
        "name": "TEST 1: Baharatlı Cips (Bol E-Kodlu)",
        "text": "İçindekiler: Mısır irmiği, palm yağı, aroma verici, E621, E627, E631, peynir altı suyu tozu, tuz, E160c.",
        "expected": ["E621", "E627", "E631", "E160c"],
    },
    {
        "name": "TEST 2: Diyet Kola (İngilizce/TR Karışık)",
        "text": "Ingredients: Water, Carbon Dioxide, Renklendirici (E150d), Phosphoric Acid, Tatlandırıcılar (Aspartam, Asesülfam K), E330, Cafein.",
        "expected": ["E150d", "aspartam", "asesülfam k", "E330"],
    },
    {
        "name": "TEST 3: Paket Bisküvi (E-Kodsuz İsimler)",
        "text": "Buğday unu, şeker, bitkisel yağ, kabartıcılar (amonyum hidrojen karbonat, sodyum hidrojen karbonat), yağsız süt tozu, emülgatör (soya lesitini), tuz.",
        "expected": ["amonyum hidrojen karbonat", "sodyum hidrojen karbonat", "soya lesitini", "süt"],
    },
    {
        "name": "TEST 4: Kötü OCR (Yazım Hataları)",
        "text": "icindekiler: misir surubu, potesyum sorbat, sodyum benzoet, sitrik asid, e-102 tartrazin.",
        "expected": ["potasyum sorbat", "sodyum benzoat", "sitrik asit", "E102"],
    },
]


def result_candidates(item):
    return [
        str(item.get("id", "")).lower(),
        str(item.get("name", "")).lower(),
        str(item.get("description", "")).lower(),
        str(item.get("matched_key", "")).lower(),
    ]


def expected_found(expected_item, results):
    exp = expected_item.lower()

    for item in results:
        for candidate in result_candidates(item):
            if not candidate:
                continue
            if exp in candidate or candidate in exp:
                return True
    return False


def run_tests():
    print("🚀 FOODLENS KAPSAMLI TEST BAŞLIYOR...\n")
    print(f"Hedef API: {API_URL}")
    print("-" * 60)

    total_score = 0

    for test in scenarios:
        print(f"\n📂 {test['name']}")
        print(f"📄 Girdi: {test['text'][:80]}...")

        try:
            start_time = time.time()
            response = requests.post(API_URL, json={"ocr_text": test["text"]}, timeout=120)
            duration = (time.time() - start_time) * 1000

            if response.status_code != 200:
                print(f"❌ HATA: API {response.status_code} döndü.")
                print(response.text)
                continue

            data = response.json()
            results = data.get("results", [])

            missing = []
            for expected_item in test["expected"]:
                if not expected_found(expected_item, results):
                    missing.append(expected_item)

            print(f"⏱️  Süre: {int(duration)} ms")
            print(f"✅ Tespit Edilen: {len(results)} madde")

            if len(missing) == 0:
                print("🌟 SONUÇ: BAŞARILI")
                total_score += 1
            else:
                print(f"⚠️  EKSİK: {missing}")
                print("   -> Bulunanlar:", [r.get("name") for r in results])

        except Exception as e:
            print(f"❌ BAĞLANTI HATASI: {e}")

        print("-" * 60)

    print(f"\n🏁 TEST BİTTİ. BAŞARI ORANI: {total_score}/{len(scenarios)}")


if __name__ == "__main__":
    run_tests()
