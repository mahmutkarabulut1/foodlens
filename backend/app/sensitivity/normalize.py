from __future__ import annotations

import re

_TRANSLATION_TABLE = str.maketrans({
    "ç": "c", "Ç": "c",
    "ğ": "g", "Ğ": "g",
    "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o",
    "ş": "s", "Ş": "s",
    "ü": "u", "Ü": "u",
})

_SUFFIXES = sorted([
    "lerinden", "larından", "lerinden", "larindan",
    "lerinin", "larinin", "lerinin", "larinin",
    "lerimiz", "larimiz", "lariniz", "leriniz",
    "leri", "lari", "ların", "lerin", "larin", "lerin",
    "si", "sı", "su", "sü", "ni", "nı", "nu", "nü",
    "yi", "yı", "yu", "yü", "in", "ın", "un", "ün",
    "i", "ı", "u", "ü", "e", "a",
    "ler", "lar", "den", "dan", "ten", "tan", "de", "da", "te", "ta",
], key=len, reverse=True)


def normalize_text(text: str) -> str:
    lowered = str(text or "").strip().lower().translate(_TRANSLATION_TABLE)
    lowered = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return [token for token in normalized.split(" ") if token]


def _strip_suffixes(token: str) -> str:
    current = token
    changed = True

    while changed and len(current) >= 5:
        changed = False
        for suffix in _SUFFIXES:
            if len(current) - len(suffix) < 4:
                continue
            if current.endswith(suffix):
                current = current[: -len(suffix)]
                changed = True
                break

    return current


def token_variants(token: str) -> set[str]:
    base = normalize_text(token).replace(" ", "")
    if not base:
        return set()

    stripped = _strip_suffixes(base)
    variants = {base, stripped}

    expanded = set()
    for value in list(variants):
        expanded.add(value)
        if len(value) >= 4 and value.endswith("g"):
            expanded.add(value[:-1] + "k")
        if len(value) >= 4 and value.endswith("d"):
            expanded.add(value[:-1] + "t")
        if len(value) >= 4 and value.endswith("b"):
            expanded.add(value[:-1] + "p")

    return {item for item in expanded if item}


def tokens_loose_equal(left: str, right: str) -> bool:
    left_variants = token_variants(left)
    right_variants = token_variants(right)

    if left_variants & right_variants:
        return True

    for l_value in left_variants:
        for r_value in right_variants:
            if min(len(l_value), len(r_value)) >= 5 and (
                l_value.startswith(r_value) or r_value.startswith(l_value)
            ):
                return True

    return False


def ordered_alias_match(alias_tokens: list[str], text_tokens: list[str]) -> bool:
    if not alias_tokens or not text_tokens:
        return False

    if len(alias_tokens) == 1:
        return any(tokens_loose_equal(alias_tokens[0], token) for token in text_tokens)

    start_indexes = [
        idx for idx, token in enumerate(text_tokens)
        if tokens_loose_equal(alias_tokens[0], token)
    ]

    for start in start_indexes:
        alias_index = 1
        gap_count = 0

        for j in range(start + 1, len(text_tokens)):
            if alias_index < len(alias_tokens) and tokens_loose_equal(alias_tokens[alias_index], text_tokens[j]):
                alias_index += 1
                if alias_index == len(alias_tokens):
                    return True
            else:
                gap_count += 1
                if gap_count > 2:
                    break

    return False


def alias_matches_text(alias: str, text: str) -> bool:
    normalized_alias = normalize_text(alias)
    normalized_text = normalize_text(text)

    if not normalized_alias or not normalized_text:
        return False

    if normalized_alias in normalized_text:
        return True

    alias_tokens = tokenize(alias)
    text_tokens = tokenize(text)

    return ordered_alias_match(alias_tokens, text_tokens)
