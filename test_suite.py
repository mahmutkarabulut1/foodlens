import requests
import json
import time

# API Adresi
API_URL = "http://127.0.0.1:8000/analyze"

# --- TEST SENARYOLARI ---
scenarios = [
    {
        "name": "TEST 1: Baharatlı Cips (Bol E-Kodlu)",
        "text": "İçindekiler: Mısır irmiği, palm yağı, aroma verici, E621, E627, E631, peynir altı suyu tozu, tuz, E160c.",
        "expected": ["E621", "E627", "E631", "E160c"]
    },
    {
        "name": "TEST 2: Diyet Kola (İngilizce/TR Karışık)",
        "text": "Ingredients: Water, Carbon Dioxide, Renklendirici (E150d), Phosphoric Acid, Tatlandırıcılar (Aspartam, Asesülfam K), E330, Cafein.",
        "expected": ["E150d", "aspartam", "asesülfam k", "E330"]
    },
    {
        "name": "TEST 3: Paket Bisküvi (E-Kodsuz İsimler)",
        "text": "Buğday unu, şeker, bitkisel yağ, kabartıcılar (amonyum hidrojen karbonat, sodyum hidrojen karbonat), yağsız süt tozu, emülgatör (soya lesitini), tuz.",
        "expected": ["amonyum hidrojen karbonat", "sodyum hidrojen karbonat", "soya lesitini", "süt"]
    },
    {
        "name": "TEST 4: Kötü OCR (Yazım Hataları)",
        "text": "icindekiler: misir surubu, potesyum sorbat, sodyum benzoet, sitrik asid, e-102 tartrazin.",
        "expected": ["potasyum sorbat", "sodyum benzoat", "sitrik asit", "E102"]
    }
]

def run_tests():
    print("🚀 FOODLENS KAPSAMLI TEST BAŞLIYOR...\n")
    print(f"Hedef API: {API_URL}")
    print("-" * 60)
    
    total_score = 0
    
    for test in scenarios:
        print(f"\n📂 {test['name']}")
        print(f"📄 Girdi: {test['text'][:60]}...")
        
        try:
            start_time = time.time()
            response = requests.post(API_URL, json={"ocr_text": test['text']})
            duration = (time.time() - start_time) * 1000 # ms cinsinden
            
            if response.status_code != 200:
                print(f"❌ HATA: API {response.status_code} döndü.")
                continue
                
            data = response.json()
            results = data.get("results", [])
            
            # Sonuçları ID ve İsim listesine dök
            detected_ids = [item['id'].lower() for item in results]
            detected_names = [item['name'].lower() for item in results]
            detected_keywords = [item['detected_keyword'].lower() for item in results]
            
            # Tüm aramalar (ID, Name, Keyword) içinde var mı diye bak
            missing = []
            for expected_item in test['expected']:
                exp = expected_item.lower()
                found = False
                
                # Basit arama: ID'de, İsimde veya Keyword'de geçiyor mu?
                for res in results:
                    r_id = res['id'].lower()
                    r_name = res['name'].lower()
                    r_key = res['detected_keyword'].lower()
                    
                    if exp in r_id or exp in r_name or exp in r_key:
                        found = True
                        break
                    # Tersine kontrol (E621 id'si 'e621 - msg' beklenen değerini kapsar mı? vs.)
                    if r_id in exp: 
                        found = True
                        break
                
                if not found:
                    missing.append(expected_item)
            
            # RAPORLAMA
            print(f"⏱️  Süre: {int(duration)} ms")
            print(f"✅ Tespit Edilen: {len(results)} madde")
            
            if len(missing) == 0:
                print("🌟 SONUÇ: BAŞARILI (Tüm beklenenler bulundu)")
                total_score += 1
            else:
                print(f"⚠️  EKSİK: {missing}")
                print("   -> Bulunanlar:", [r['name'] for r in results])
                
        except Exception as e:
            print(f"❌ BAĞLANTI HATASI: {e}")
            
        print("-" * 60)

    print(f"\n🏁 TEST BİTTİ. BAŞARI ORANI: {total_score}/{len(scenarios)}")

if __name__ == "__main__":
    run_tests()
