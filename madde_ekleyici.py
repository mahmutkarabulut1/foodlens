import requests
from bs4 import BeautifulSoup
import json
import os
import re

# --- AYARLAR ---
URL = "https://www.gursahakman.com/e-kodu-listesi/"
JSON_FILE = "foodlens_ai_completed.json"

def clean_text(text):
    return text.strip()

def load_database():
    if not os.path.exists(JSON_FILE):
        return []
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, dict) and "data" in content:
                return content["data"]
            return content
    except:
        return []

def main():
    print("🚀 Gürşah Akman Listesi Taranıyor ve Formatlanıyor...")
    
    # 1. Mevcut Veritabanını Yükle
    database = load_database()
    existing_ids = set()
    for item in database:
        if "id" in item:
            existing_ids.add(item["id"])
            
    print(f"📂 Mevcut kayıt sayısı: {len(database)}")

    # 2. Siteyi Çek
    try:
        response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_div = soup.find("div", class_="entry-content")
        
        if not content_div:
            print("❌ İçerik bulunamadı!")
            return

        lines = content_div.get_text(separator="\n").split("\n")
        
        added_count = 0
        pattern = re.compile(r"^(E\s?[\d]+[a-z]?)\s+(.*)")

        for line in lines:
            line = line.strip()
            if not line: continue
            if " - " in line and "Renklendiriciler" in line: continue

            match = pattern.match(line)
            if match:
                raw_code = match.group(1).replace(" ", "")
                name = match.group(2).strip()
                
                # Zaten varsa atla
                if raw_code in existing_ids:
                    continue

                # --- GÜNCELLENMİŞ FORMAT (SENİN ŞEMANLA %100 UYUMLU) ---
                new_item = {
                    "id": raw_code,
                    "name_tr": name,
                    "name_en": "",               # Boş bırakıyoruz (DeepSeek dolduracak)
                    "type": "additive",          # Bu liste katkı maddesi olduğu için sabit
                    "wikidata_ref": "",          # Boş (Sonra doldurulabilir)
                    "risk_level": "Unknown",     # Bilmiyoruz
                    "source_category": "additives", # Senin formatına uygun kategori
                    "keywords": [
                        raw_code, 
                        raw_code.lower(), 
                        raw_code.replace("E", "E-").lower(),
                        name.lower()
                    ],
                    "dietary_status": "Unknown", # Vegan mı değil mi şu an bilmiyoruz
                    "description_tr": "Gıda katkı maddesi.", 
                    "ai_processed": False,       # False yapıyoruz ki sonra AI ile tarayıp dolduralım
                    "source": "gursahakman.com"  # Takip için (Opsiyonel ama yararlı)
                }
                
                database.append(new_item)
                existing_ids.add(raw_code)
                added_count += 1
                print(f"✅ Eklendi: {raw_code} - {name}")

        # 3. Kaydet
        if added_count > 0:
            # "data" key'i altına kaydediyoruz
            output_data = {"data": database}
            
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            print(f"\n🎉 İşlem Tamam! {added_count} yeni madde eklendi.")
        else:
            print("\n✅ Veritabanı zaten güncel.")

    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    main()
