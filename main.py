from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
import re
import logging
import torch # Vektör hesaplamaları için
from rapidfuzz import process, fuzz
from sentence_transformers import SentenceTransformer, util

# --- LOGLAMA ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FoodLens")

app = FastAPI()

# --- AYARLAR ---
DB_FILE = "foodlens_ai_completed.json"
FUZZY_THRESHOLD = 85.0    # RapidFuzz için
SEMANTIC_THRESHOLD = 0.75  # Cosine Similarity için (0 ile 1 arası)

# Modeli yükle (Hafif ve hızlı bir model seçtik)
logger.info("NLP Modeli yükleniyor (all-MiniLM-L6-v2)...")
model = SentenceTransformer('all-MiniLM-L6-v2')

database = []
SEARCH_KEYS = []
KEY_TO_ITEM_MAP = {}
DB_EMBEDDINGS = None # Vektörler burada saklanacak

def clean_text(text):
    if text is None: return ""
    text = str(text)
    text = text.replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ö', 'ö').replace('Ç', 'ç')
    text = text.lower()
    text = text.replace('\n', ' ').replace(':', '').replace('.', '').replace(',', '')
    return text.strip()

def load_database():
    global database, SEARCH_KEYS, KEY_TO_ITEM_MAP, DB_EMBEDDINGS
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, DB_FILE)
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            database = content.get("data", content)

        SEARCH_KEYS = []
        KEY_TO_ITEM_MAP = {}
        
        for item in database:
            candidates = {item.get("id"), item.get("name_tr"), item.get("name_en")}
            if item.get("keywords"):
                candidates.update(item["keywords"])
            
            for candidate in candidates:
                if not candidate: continue
                clean_key = clean_text(candidate)
                if len(clean_key) < 2: continue
                
                SEARCH_KEYS.append(clean_key)
                KEY_TO_ITEM_MAP[clean_key] = item
        
        # SEMANTİK İNDEKSLEME: Tüm anahtarları vektöre çevir
        logger.info(f"{len(SEARCH_KEYS)} anahtar kelime vektörleştiriliyor...")
        DB_EMBEDDINGS = model.encode(SEARCH_KEYS, convert_to_tensor=True)
        
        logger.info("✅ Hibrit Veritabanı Hazır.")
            
    except Exception as e:
        logger.error(f"Veritabanı Hatası: {e}")

load_database()

class ImageRequest(BaseModel):
    ocr_text: str

def extract_relevant_section(text):
    text_lower = text.lower()
    start_keywords = ["içindekiler", "ingredients", "icindekiler", "bileşenler"]
    start_index = -1
    for kw in start_keywords:
        idx = text_lower.find(kw)
        if idx != -1: start_index = idx; break
    
    if start_index == -1: return text 
    relevant_part = text[start_index:]
    
    # 4 Nokta Kuralı
    current_pos = 0
    found_index = -1
    for _ in range(4):
        dot_idx = relevant_part.find('.', current_pos)
        if dot_idx != -1: found_index = dot_idx; current_pos = dot_idx + 1
        else: break
            
    return relevant_part[:found_index] if found_index != -1 else relevant_part

@app.post("/analyze")
def analyze_image(request: ImageRequest):
    targeted_text = extract_relevant_section(request.ocr_text)
    
    # Parantezleri virgüle çevir
    clean_ocr = targeted_text.replace('\n', ',').replace(':', ',').replace(';', ',')
    clean_ocr = clean_ocr.replace('(', ',').replace(')', ',').replace('[', ',').replace(']', ',')
    
    raw_items = [x.strip() for x in clean_ocr.split(',')]
    results = []
    seen_ids = set()
    
    for item_text in raw_items:
        if len(item_text) < 3: continue
        query = clean_text(item_text)
        
        # --- HİBRİT ARAMA ADIMLARI ---
        
        # 1. Adım: RapidFuzz (Harf Benzerliği)
        fuzzy_match = process.extractOne(query, SEARCH_KEYS, scorer=fuzz.token_sort_ratio)
        
        # 2. Adım: Semantik (Anlam Benzerliği)
        query_embedding = model.encode(query, convert_to_tensor=True)
        cos_scores = util.cos_sim(query_embedding, DB_EMBEDDINGS)[0]
        best_semantic_idx = torch.argmax(cos_scores).item()
        semantic_score = cos_scores[best_semantic_idx].item()
        
        # Karar Mekanizması
        found_item = None
        final_score = 0
        
        # Eğer RapidFuzz çok eminse (%90+) onu al
        if fuzzy_match and fuzzy_match[1] >= 90:
            found_item = KEY_TO_ITEM_MAP[fuzzy_match[0]]
            final_score = fuzzy_match[1]
        # Değilse, Semantik skora bak
        elif semantic_score >= SEMANTIC_THRESHOLD:
            found_item = KEY_TO_ITEM_MAP[SEARCH_KEYS[best_semantic_idx]]
            final_score = semantic_score * 100
        # Son çare orta şekerli Fuzzy
        elif fuzzy_match and fuzzy_match[1] >= FUZZY_THRESHOLD:
            found_item = KEY_TO_ITEM_MAP[fuzzy_match[0]]
            final_score = fuzzy_match[1]

        if found_item and found_item["id"] not in seen_ids:
            results.append({
                "id": found_item["id"],
                "name": found_item.get("name_tr") or found_item.get("name_en"),
                "risk_level": found_item.get("risk_level", "Unknown"),
                "description": found_item.get("description_tr", ""),
                "match_score": int(final_score),
                "match_type": "semantic" if final_score == semantic_score*100 else "fuzzy"
            })
            seen_ids.add(found_item["id"])

    return {"results": results}