from __future__ import annotations

import re

CUE_RE = re.compile(
    r'^\s*(içindekiler|icindekiler|ingredients|ingredient list|bileşenler|bilesenler)\s*[:：]',
    re.IGNORECASE,
)

def canonicalize_analysis_text(text: str) -> str:
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()

    if not value:
        return ""

    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{2,}", "\n", value).strip()

    if not CUE_RE.search(value):
        # Manuel giriş ile OCR çıktısını aynı analiz hattına daha yakın hale getir.
        # Bu lexical replacement değil; yalnızca parser'ın ingredient section'ı
        # güvenilir biçimde görmesi için yapısal bir işaretleme.
        if "," in value or ";" in value or "\n" in value or len(value.split()) <= 8:
            value = f"İçindekiler: {value}"

    return value
