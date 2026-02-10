import json
import os

# --- AYARLAR ---
RAW_DIR = "raw_data"
OUTPUT_FILE = "foodlens_comprehensive_db.json"

# --- MANUAL RISK LISTESI (Seninle oluşturduğumuz) ---
# Buraya uzun listeyi yapıştırırsın, örnek olarak kısa tutuyorum:
RISK_MAP = {
    "E102": {"level": "High", "note": "Hiperaktivite riski (Tartrazin)."},
    "E202": {"level": "Low", "note": "Genellikle güvenli."},
    # ...
}

def load_json(filename):
    path = os.path.join(RAW_DIR, filename)
    print(f"📂 Okunuyor: {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_text(text):
    """Metni temizler: küçük harf, gereksiz boşluklar."""
    if not text: return ""
    return text.lower().strip()

def process_item(key, val, item_type):
    """
    Herhangi bir maddeyi işleyip standart formata sokar.
    Mantık: TR varsa al, yoksa EN al, ikisini de keyword'e ekle.
    """
    # 1. ID Temizliği (en:e202 -> E202)
    clean_id = key.replace("en:", "").replace("-", " ").strip()
    if item_type == "additive" and clean_id.startswith("e"):
        clean_id = clean_id.replace(" ", "").upper() # E 202 -> E202
    
    # 2. İsim Çıkarma (TR öncelikli, EN yedek)
    names = val.get("name", {})
    name_tr = names.get("tr", "")
    name_en = names.get("en", "")
    
    # Görünen isim (UI'da kullanıcıya ne göstereceğiz?)
    display_name = name_tr if name_tr else name_en
    
    # Eğer ne Türkçe ne İngilizce isim yoksa, bu veriyi atla (Çöp veri)
    if not display_name:
        return None

    # 3. Akıllı Keyword Listesi (Fuzzy Match için)
    # OCR'ın yakalayabileceği tüm varyasyonları buraya dolduruyoruz.
    keywords = set()
    keywords.add(clean_id.lower())           # örn: e202
    if name_tr: keywords.add(clean_text(name_tr)) # örn: potasyum sorbat
    if name_en: keywords.add(clean_text(name_en)) # örn: potassium sorbate
    
    # Ekstra: E-kodları için varyasyonlar (E-202, E 202)
    if item_type == "additive":
        keywords.add(clean_id.lower().replace("e", "e-"))
        keywords.add(clean_id.lower().replace("e", "e "))

    # 4. Risk Analizi (Sadece Katkı Maddeleri için)
    risk_data = {"level": "Unknown", "note": ""}
    if item_type == "additive":
        risk_data = RISK_MAP.get(clean_id, risk_data)

    return {
        "id": clean_id,
        "name": display_name,
        "type": item_type,
        "risk_level": risk_data["level"], # Sadece additives için dolu gelir
        "note": risk_data["note"],
        "keywords": list(keywords) # Python set'i JSON olmaz, listeye çevir
    }

def main():
    try:
        raw_additives = load_json("additives.json")
        raw_allergens = load_json("allergens.json")
        raw_ingredients = load_json("ingredients.json")
    except FileNotFoundError:
        print("❌ HATA: Dosyalar bulunamadı.")
        return

    print("🚀 Veri işleme başladı (Kapsayıcı Mod)...")
    
    final_list = []

    # 1. Katkı Maddeleri
    print("...Katkı Maddeleri taranıyor")
    for k, v in raw_additives.items():
        if k.startswith("en:e"): # Sadece E kodları
            item = process_item(k, v, "additive")
            if item: final_list.append(item)

    # 2. Alerjenler
    print("...Alerjenler taranıyor")
    for k, v in raw_allergens.items():
        item = process_item(k, v, "allergen")
        if item: final_list.append(item)

    # 3. İçerikler (Ingredients)
    print("...Genel İçerikler taranıyor")
    for k, v in raw_ingredients.items():
        # Burada çok fazla veri olduğu için yine de bir kalite filtresi koyalım:
        # Sadece ismi 3 karakterden uzun olanları al (Gürültüyü azaltır)
        item = process_item(k, v, "ingredient")
        if item and len(item["name"]) > 2:
            final_list.append(item)

    # 4. JSON Olarak Kaydet
    output_data = {
        "metadata": {"count": len(final_list), "strategy": "Multi-Language Fallback"},
        "data": final_list
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ İŞLEM TAMAM! Toplam {len(final_list)} madde veritabanına eklendi.")
    print(f"📂 Çıktı dosyası: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
