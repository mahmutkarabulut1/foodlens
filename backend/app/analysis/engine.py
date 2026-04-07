"""
FoodLens Analysis Engine — main orchestrator for the analysis pipeline.

Pipeline:
  1. OCR cleanup (noise removal, keyword repair, line merging)
  2. Block splitting (section classification)
  3. Candidate extraction (ingredient parsing, claim parsing)
  4. Exact matching against lexicon
  5. Fuzzy recovery for OCR-corrupted text
  6. Deduplication and result assembly
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple

from .. import config as app_config
from .schemas import CandidateSpan, MatchedEntity, StructuredAnalysis, TextBlock
from .preprocessing.ocr_cleanup import cleanup_ocr_text
from .segmentation.block_splitter import split_into_blocks
from .extraction.ingredient_parser import extract_from_ingredient_block
from .extraction.claim_parser import extract_claim_spans
from .matching.lexicon import MasterLexicon
from .matching.exact_matcher import ExactRuleMatcher
from .matching.fuzzy_recovery import FuzzyRecoveryMatcher

logger = logging.getLogger("FoodLens")

INLINE_FREE_FROM_CUES = [
    "içermez", "icermez", "yoktur", "bulunmaz",
    "does not contain", "contains no", "free from",
]
INLINE_MAY_CONTAIN_CUES = [
    "eser miktarda", "iz miktarda", "may contain",
    "iz içerebilir", "iz icerebilir", "traces of",
]
INLINE_ALLERGEN_TERMS = [
    "alerjen", "allergen", "gluten", "süt", "sut", "soya",
    "fındık", "findik", "yumurta", "yer fıstığı", "yer fistigi",
    "susam", "ceviz", "badem", "milk", "soy", "hazelnut",
    "egg", "sesame", "peanut", "wheat", "balık", "balik",
]
INLINE_PRESENCE_VERBS = [
    "içerir", "icerir", "içermektedir", "icermektedir", "contains",
]


def _resolve_db_file() -> Path:
    csv_path = getattr(app_config, "MASTER_CSV_FILE", None)
    if csv_path:
        return Path(csv_path)
    return Path(app_config.DB_FILE)


class FoodLensAnalysisEngine:
    def __init__(self):
        self.db_file = _resolve_db_file()
        logger.info("Rule-based analysis engine yükleniyor: %s", self.db_file)
        self.lexicon = MasterLexicon(self.db_file)
        self.matcher = ExactRuleMatcher(self.lexicon)
        self.fuzzy_matcher = FuzzyRecoveryMatcher(self.lexicon)

    def _extract_inline_claims(self, block: TextBlock) -> List[CandidateSpan]:
        """Extract inline claims (free-from, may-contain, allergen) from non-claim blocks."""
        if block.section_type in {"free_from_section", "may_contain_section", "allergen_section"}:
            return []

        lowered = block.raw_text.lower()
        spans: List[CandidateSpan] = []

        if any(cue in lowered for cue in INLINE_FREE_FROM_CUES):
            pseudo = TextBlock(
                section_type="free_from_section",
                raw_text=block.raw_text,
                normalized_text=block.normalized_text,
                source_lines=block.source_lines,
                anchor="inline_free_from",
            )
            spans.extend(extract_claim_spans(pseudo))

        if any(cue in lowered for cue in INLINE_MAY_CONTAIN_CUES):
            pseudo = TextBlock(
                section_type="may_contain_section",
                raw_text=block.raw_text,
                normalized_text=block.normalized_text,
                source_lines=block.source_lines,
                anchor="inline_may_contain",
            )
            spans.extend(extract_claim_spans(pseudo))

        has_presence = any(verb in lowered for verb in INLINE_PRESENCE_VERBS)
        has_allergen_term = any(term in lowered for term in INLINE_ALLERGEN_TERMS)
        if has_presence and has_allergen_term:
            pseudo = TextBlock(
                section_type="allergen_section",
                raw_text=block.raw_text,
                normalized_text=block.normalized_text,
                source_lines=block.source_lines,
                anchor="inline_allergen",
            )
            spans.extend(extract_claim_spans(pseudo))

        return spans

    def _extract_candidates(self, text: str) -> Tuple[List[CandidateSpan], StructuredAnalysis]:
        """Run the full extraction pipeline on input text."""
        _, lines = cleanup_ocr_text(text)
        blocks = split_into_blocks(lines)

        analysis = StructuredAnalysis(blocks=blocks)
        spans: List[CandidateSpan] = []

        for block in blocks:
            # Always check for inline claims regardless of block type
            spans.extend(self._extract_inline_claims(block))

            if block.section_type == "ingredient_section":
                spans.extend(extract_from_ingredient_block(block))
            elif block.section_type in {"allergen_section", "may_contain_section", "free_from_section"}:
                spans.extend(extract_claim_spans(block))
            else:
                analysis.ignored_blocks.append(block)

        return spans, analysis

    def _dedupe(self, entities: List[MatchedEntity]) -> List[MatchedEntity]:
        """Deduplicate matched entities, keeping the highest-confidence match per item."""
        unique: Dict[tuple, MatchedEntity] = {}
        for entity in entities:
            key = (entity.item_id, entity.polarity, entity.source_section)
            if key not in unique or entity.match_score > unique[key].match_score:
                unique[key] = entity
        return list(unique.values())

    def _dedupe_unmatched(self, spans: List[CandidateSpan]) -> List[CandidateSpan]:
        unique: Dict[tuple, CandidateSpan] = {}
        for span in spans:
            key = (span.normalized_text, span.polarity, span.section_type)
            if key not in unique:
                unique[key] = span
        return list(unique.values())

    def _dedupe_spans(self, spans: List[CandidateSpan]) -> List[CandidateSpan]:
        """Deduplicate candidate spans before matching to avoid redundant fuzzy calls."""
        unique: Dict[str, CandidateSpan] = {}
        for span in spans:
            key = f"{span.normalized_text}|{span.polarity}|{span.section_type}"
            if key not in unique:
                unique[key] = span
        return list(unique.values())

    def _is_fuzzy_worthy(self, span: CandidateSpan) -> bool:
        """Quick check if a span is worth sending to fuzzy matching."""
        text = span.normalized_text or ""
        # Too short
        if len(text) < 3:
            return False
        # Too long (probably a sentence, not an ingredient)
        if len(text) > 50:
            return False
        # Mostly numbers
        alpha = sum(1 for c in text if c.isalpha())
        if alpha < 2:
            return False
        return True

    def analyze_structured(self, text: str) -> StructuredAnalysis:
        """Full structured analysis with all sections."""
        spans, analysis = self._extract_candidates(text)

        # Deduplicate spans before matching
        spans = self._dedupe_spans(spans)

        matched_present: List[MatchedEntity] = []
        matched_may: List[MatchedEntity] = []
        matched_absent: List[MatchedEntity] = []

        for span in spans:
            # Try exact match first
            entity = self.matcher.match_span(span)

            # Fall back to fuzzy recovery (only for worthy candidates)
            if entity is None and self._is_fuzzy_worthy(span):
                entity = self.fuzzy_matcher.match_span(span)

            if entity is None:
                analysis.unmatched_spans.append(span)
                continue

            if entity.polarity == "may_contain":
                matched_may.append(entity)
            elif entity.polarity == "absent":
                matched_absent.append(entity)
            else:
                matched_present.append(entity)

        analysis.present = self._dedupe(matched_present)
        analysis.may_contain = self._dedupe(matched_may)
        analysis.free_from = self._dedupe(matched_absent)
        analysis.unmatched_spans = self._dedupe_unmatched(analysis.unmatched_spans)
        return analysis

    def analyze_for_api(self, text: str) -> List[Dict[str, object]]:
        """Flat list of matched entities for the API response."""
        analysis = self.analyze_structured(text)
        flattened: List[MatchedEntity] = []
        flattened.extend(analysis.present)
        flattened.extend(analysis.may_contain)

        flattened = sorted(
            flattened,
            key=lambda item: (
                0 if item.source_section == "ingredient_section" else 1,
                0 if item.polarity == "present" else 1,
                item.name.lower(),
            ),
        )
        return [item.to_api_dict() for item in flattened]

    def health(self) -> Dict[str, object]:
        return {
            "status": "ok",
            "db_file": str(self.db_file),
            "item_count": len(self.lexicon.records),
            "exact_alias_count": len(self.lexicon.alias_map),
            "search_alias_count": len(self.lexicon.alias_map),
            "semantic_enabled": False,
            "analysis_mode": "rule_based_sections_v3_pro",
        }
