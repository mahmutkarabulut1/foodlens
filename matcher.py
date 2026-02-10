import json
from rapidfuzz import process, fuzz

# 1. Veritabanını Yükle
print("⏳ Veritabanı yükleniyor...")
with open("foodlens_comprehensive_db.json", "r", encoding="utf-8") as f:
    db_data = json.load(f)["data"]

# Hız için: Sadece keyword'leri ve ID'leri bir sözlüğe alalım
# { "potasyum sorbat": "E202", "e202": "E202", "potassium sorbate": "E202" ... }
keyword_map = {}
for item in db_data:
    for keyword in item["keywords"]:
        keyword_map[keyword] = item # Tüm item objesini referans al

# Sadece aranacak kelimeler listesi (Fuzzy search havuzu)
all_keywords = list(keyword_map.keys())

print(f"✅ Hazır! {len(all_keywords)} farklı anahtar kelime taranacak.")

def analyze_text(ocr_text):
    """
    OCR'dan gelen bozuk metni alır, veritabanındaki maddeleri bulur.
    """
    found_items = {} # Aynı maddeyi tekrar eklememek için dict kullanıyoruz
    
    # 1. Metni Temizle ve Parçala (Tokenization)
    # Satır satır veya virgülle ayrılmışsa ona göre bölebilirsin.
    # Basitçe kelime gruplarına ayıralım.
    ocr_text = ocr_text.lower().replace("\n", " ")
    
    # RAPIDFUZZ İLE SİHİR BURADA BAŞLIYOR 🪄
    # extract_iter: Metindeki kelimeleri bizim keyword listemizle karşılaştırır.
    # score_cutoff=85: %85 ve üzeri benzerlik yoksa hiç getirme (Hata önleyici)
    
    # Yöntem: Tüm metin içinde bizim keywordleri aratmak yerine,
    # Veritabanındaki keywordleri metnin içinde var mı diye kontrol edelim.
    # Ancak veritabanı büyük olduğu için bu yavaş olabilir.
    
    # DAHA İYİ YÖNTEM: OCR metnini 'n-gram'lara bölüp aratmak.
    # Ama şimdilik basit bir yaklaşım yapalım:
    
    results = process.extract(
        query=ocr_text, 
        choices=all_keywords, 
        scorer=fuzz.partial_ratio, # "Metnin bir parçası eşleşiyor mu?"
        score_cutoff=85, # Benzerlik eşiği (Senin ayarın)
        limit=10 # En iyi 10 eşleşmeyi getir
    )
    
    for match in results:
        keyword_found = match[0]
        score = match[1]
        
        # Bulunan keyword hangi maddeye ait?
        item = keyword_map[keyword_found]
        item_id = item["id"]
        
        # Daha önce eklenmemişse listeye ekle
        if item_id not in found_items:
            found_items[item_id] = {
                "id": item["id"],
                "name": item["name"], # Türkçe isim
                "risk": item.get("risk_level", "Unknown"),
                "match_score": score,
                "detected_keyword": keyword_found
            }

    return list(found_items.values())

# --- TEST ---
# Diyelim ki OCR kameradan şöyle bozuk ve İngilizce karışık bir metin okudu:
bozuk_ocr_metni = """
indigients: water, sugar, potasum sorbte, 
e-102 tartrazin, citric asid.
"""

print("\n🔍 Analiz Sonucu:")
sonuclar = analyze_text(bozuk_ocr_metni)
print(json.dumps(sonuclar, indent=2, ensure_ascii=False))
