from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .catalog import get_aliases_for_allergen
from .normalize import alias_matches_text


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _primary_candidate_texts(item: Dict[str, Any]) -> list[str]:
    values: list[str] = []

    for key in ("name", "raw_query", "matched_key"):
        value = _safe_text(item.get(key))
        if value:
            values.append(value)

    return values


def _context_candidate_texts(item: Dict[str, Any]) -> list[str]:
    value = _safe_text(item.get("source_text"))
    return [value] if value else []


def _find_matching_alias(allergen_name: str, texts: Iterable[str]) -> str | None:
    aliases = get_aliases_for_allergen(allergen_name)

    for alias in aliases:
        for text in texts:
            if alias_matches_text(alias, text):
                return alias

    return None


def _match_allergen_for_item(item: Dict[str, Any], selected: list[str]) -> tuple[str | None, str | None]:
    source_section = _safe_text(item.get("source_section")).lower()
    polarity = _safe_text(item.get("polarity")).lower()

    primary_texts = _primary_candidate_texts(item)

    for allergen_name in selected:
        alias = _find_matching_alias(allergen_name, primary_texts)
        if alias:
            return allergen_name, alias

    # Context fallback sadece ingredient dışı / claim benzeri alanlarda kullanılsın
    allow_context_fallback = not (
        source_section == "ingredient_section" and polarity in {"present", ""}
    )

    if allow_context_fallback:
        context_texts = _context_candidate_texts(item)
        for allergen_name in selected:
            alias = _find_matching_alias(allergen_name, context_texts)
            if alias:
                return allergen_name, alias

    return None, None


def enrich_results_with_sensitivities(
    results: List[Dict[str, Any]],
    selected_allergens: List[str] | None = None,
) -> List[Dict[str, Any]]:
    selected = [str(item).strip() for item in (selected_allergens or []) if str(item).strip()]
    enriched: list[dict[str, Any]] = []

    for raw_item in results:
        item = dict(raw_item)

        matched_user_allergen = None
        matched_user_alias = None

        if selected:
            matched_user_allergen, matched_user_alias = _match_allergen_for_item(
                item,
                selected,
            )

        item["user_sensitive_match"] = matched_user_allergen is not None
        item["matched_user_allergen"] = matched_user_allergen
        item["matched_user_alias"] = matched_user_alias
        enriched.append(item)

    return enriched
