from __future__ import annotations

import logging

from .analysis.engine import FoodLensAnalysisEngine
from .input_normalization import canonicalize_analysis_text
from .sensitivity import enrich_results_with_sensitivities

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FoodLens")


class FoodLensMatcher:
    def __init__(self):
        logger.info("Rule-based FoodLens matcher başlatılıyor")
        self.engine = FoodLensAnalysisEngine()
        self.database = self.engine.lexicon.records
        self.exact_map = self.engine.lexicon.alias_map
        self.search_aliases = list(self.engine.lexicon.alias_map.keys())

    def health(self):
        return self.engine.health()

    def analyze_structured(self, text: str, selected_allergens: list[str] | None = None):
        normalized_text = canonicalize_analysis_text(text)
        data = self.engine.analyze_structured(normalized_text).to_debug_dict()

        for section_name in ("present", "may_contain", "free_from"):
            section_items = data.get(section_name, [])
            if isinstance(section_items, list):
                data[section_name] = enrich_results_with_sensitivities(
                    section_items,
                    selected_allergens or [],
                )

        return data

    def analyze_text(self, text: str, selected_allergens: list[str] | None = None):
        normalized_text = canonicalize_analysis_text(text)
        results = self.engine.analyze_for_api(normalized_text)
        return enrich_results_with_sensitivities(results, selected_allergens or [])
