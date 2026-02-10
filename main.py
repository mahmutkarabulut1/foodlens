from fastapi import FastAPI
from pydantic import BaseModel
import json
import os

app = FastAPI()

# --- AYARLAR ---
DB_FILE = "foodlens_ai_completed.json"
database = []

def load_database():
    """
    Yeni veri setini yükler.
    """
    global database
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, DB_FILE)
        
        if not os.path.exists(file_path):
            print(f"UYARI: {DB_FILE} bulunamadı! Lütfen dosya adını kontrol et.")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            
            # JSON yapısını kontrol et (Liste mi? Sözlük mü?)
            if isinstance(content, dict) and "data" in content:
                database = content["data"]
            elif isinstance(content, list):
                database = content
            else:
                database = []
                
        print(f"✅ BEYİN YÜKLENDİ: {len(database)} adet madde hafızada.")
            
    except Exception as e:
        print(f"Veritabanı Hatası: {e}")
        database = []

# Uygulama başlarken veriyi yükle
load_database()

class ImageRequest(BaseModel):
    ocr_text: str

def search_in_db(fragment):
    """
    OCR'dan gelen parçayı (örn: 'Glikoz Şurubu') veritabanında arar.
    Sadece EŞLEŞEN sonuç döner.
    """
    fragment_clean = fragment.lower().strip()
    
    # Veritabanındaki her maddeye bak
    for item in database:
        # Keywords listesinde gez
        if "keywords" in item:
            for kw in item["keywords"]:
                keyword = kw.lower().strip()
                
                # MANTIK: 
                # OCR parçası içinde anahtar kelime geçiyor mu?
                # Örn: OCR="Mısır bazlı Glikoz Şurubu" -> Keyword="glikoz şurubu" -> EŞLEŞTİ
                if keyword in fragment_clean:
                    return {
                        "name": item.get("name", keyword.title()),
                        "risk_level": item.get("risk_level", "Unknown"),
                        "description": item.get("description", "Açıklama bulunamadı.")
                    }
    return None

@app.post("/analyze")
def analyze_image(request: ImageRequest):
    text = request.ocr_text
    
    # 1. TEMİZLİK: Satır sonlarını virgüle çevir
    clean_text = text.replace('\n', ',').replace(';', ',')
    
    # 2. PARÇALA: Virgülden böl
    raw_items = clean_text.split(',')
    
    results = []
    seen_names = set() # Aynı maddeyi iki kere yazmamak için
    
    for item in raw_items:
        item = item.strip()
        
        # Çok kısa (1-2 harfli) şeyleri atla
        if len(item) < 2:
            continue
            
        # 3. ARA: Veritabanında var mı?
        match = search_in_db(item)
        
        # 4. FİLTRELE: Sadece veritabanında VARSA ekle.
        # (Yoksa bu bir çöp metindir, görmezden gel)
        if match:
            # Daha önce eklemediysek listeye al
            if match["name"] not in seen_names:
                results.append({
                    "name": match["name"],
                    "risk_level": match["risk_level"],
                    "description": match["description"],
                    "match_score": 100
                })
                seen_names.add(match["name"])

    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)