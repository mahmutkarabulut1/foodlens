from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
import re
from difflib import SequenceMatcher
import logging

# --- LOGLAMA AYARLARI ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FoodLens")

app = FastAPI()

# --- AYARLAR ---
DB_FILE = "foodlens_ai_completed.json"
MATCH_THRESHOLD = 0.85  # %85 Benzerlik (OCR hatalarını tolere eder)
database = []

def load_database():
    global database
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, DB_FILE)
        
        if not os.path.exists(file_path):
            logger.error(f"DOSYA BULUNAMADI: {DB_FILE}")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, dict) and "data" in content:
                database = content["data"]
            elif isinstance(content, list):
                database = content
            else:
                database = []
        
        logger.info(f"✅ VERİTABANI YÜKLENDİ: {len(database)} madde hazır.")
            
    except Exception as e:
        logger.error(f"Veritabanı Hatası: {e}")
        database = []

load_database()

class ImageRequest(BaseModel):
    ocr_text: str

def clean_text(text):
    if text is None: return ""
    text = re.sub(r'\([^)]*\)', '', text) # Parantezleri sil
    text = text.replace('\n', ' ')
    return text.strip().lower()

def similarity_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()

def search_robust_match(fragment):
    """
    3 Aşamalı Öncelik Sistemi: TR > EN > Keyword
    """
    fragment_clean = clean_text(fragment)
    
    if len(fragment_clean) < 3: return None

    best_match = None
    best_score = 0

    for item in database:
        name_tr = item.get("name_tr", "")
        name_en = item.get("name_en", "")
        keywords = item.get("keywords", [])
        risk = item.get("risk_level", "Unknown")
        desc = item.get("description_tr", "Açıklama bulunamadı.")

        candidates = [name_tr, name_en] + keywords
        
        for candidate in candidates:
            if not candidate: continue
            
            score = similarity_ratio(fragment_clean, clean_text(candidate))
            
            if score >= MATCH_THRESHOLD:
                if score > best_score:
                    best_score = score
                    # Her zaman Türkçe ismi tercih et
                    display_name = name_tr if name_tr else name_en
                    
                    best_match = {
                        "name": display_name,
                        "risk_level": risk,
                        "description": desc,
                        "score": int(score * 100)
                    }
                    if score == 1.0: return best_match

    return best_match

def extract_relevant_section(text):
    """
    MAHMUT'UN ALGORİTMASI:
    1. 'İçindekiler' veya 'Ingredients' kelimesini bul.
    2. O kelimeden sonraki ilk '.' (nokta) işaretine kadar al.
    3. Eğer nokta bulamazsa (OCR hatası), metnin sonuna kadar al.
    """
    text_lower = text.lower()
    
    # Başlangıç kelimeleri
    start_keywords = ["içindekiler", "ingredients", "icindekiler"]
    
    start_index = -1
    for kw in start_keywords:
        idx = text_lower.find(kw)
        if idx != -1:
            start_index = idx
            break
    
    # Eğer anahtar kelime bulunamazsa metnin tamamını döndür (Fallback)
    if start_index == -1:
        logger.warning("⚠️ 'İçindekiler' başlığı bulunamadı, tüm metin taranıyor.")
        return text

    # Başlangıçtan sonrasını al
    relevant_part = text[start_index:]
    
    # Nokta (.) kontrolü
    dot_index = relevant_part.find('.')
    
    if dot_index != -1:
        # Noktayı bulduk! Oraya kadar kes.
        logger.info("Metin nokta (.) işaretinden kesildi.")
        return relevant_part[:dot_index]
    else:
        # Nokta yoksa sonuna kadar devam
        return relevant_part

@app.post("/analyze")
def analyze_image(request: ImageRequest):
    original_text = request.ocr_text
    
    # 1. ADIM: İLGİLİ BÖLÜMÜ KESİP AL (NOKTA ALGORİTMASI)
    targeted_text = extract_relevant_section(original_text)
    
    logger.info(f"İŞLENECEK METİN: {targeted_text[:100]}...")

    # 2. ADIM: TEMİZLİK VE PARÇALAMA
    # Satır sonlarını, iki noktayı ve noktalı virgülü virgüle çevir
    clean_ocr = targeted_text.replace('\n', ',').replace(':', ',').replace(';', ',')
    
    raw_items = clean_ocr.split(',')
    
    results = []
    seen_names = set()
    
    # 3. ADIM: ANALİZ
    for item in raw_items:
        item = item.strip()
        if not item: continue
        
        # Kelime çok uzunsa (Örn: adres bilgisi karıştıysa) atla
        if len(item) > 50: continue 

        match = search_robust_match(item)
        
        if match:
            if match["name"] not in seen_names:
                results.append(match)
                seen_names.add(match["name"])
                logger.info(f"✅ BULUNDU: {match['name']}")

    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)