from __future__ import annotations

import re
import unicodedata


TRANSLATION_TABLE = str.maketrans({
    "İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü", "Ş": "ş", "Ö": "ö", "Ç": "ç",
    "\u00a0": " ",
    "\t": " ",
    "|": " ",
    "•": " ",
    "·": " ",
    "“": '"',
    "”": '"',
    "’": "'",
    "‘": "'",
})


ASCII_TABLE = str.maketrans({
    "ı": "i",
    "ğ": "g",
    "ü": "u",
    "ş": "s",
    "ö": "o",
    "ç": "c",
})


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    if text is None:
        return ""
    text = str(text).translate(TRANSLATION_TABLE)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_for_matching(text: str) -> str:
    text = normalize_text(text).lower()
    text = text.replace("/", " ")
    text = text.replace("\\", " ")
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = text.replace("[", " ")
    text = text.replace("]", " ")
    text = text.replace("{", " ")
    text = text.replace("}", " ")
    text = re.sub(r"[%_]", " ", text)
    text = re.sub(r"[^0-9a-zçğıöşü\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ascii_fold(text: str) -> str:
    return strip_accents(normalize_for_matching(text)).translate(ASCII_TABLE)


def build_line_candidates(text: str) -> list[str]:
    raw_lines = [line.strip(" -:;,.") for line in normalize_text(text).split("\n")]
    lines = []
    for line in raw_lines:
        if not line:
            continue
        if len(line) == 1:
            continue
        lines.append(re.sub(r"\s+", " ", line).strip())
    return lines
