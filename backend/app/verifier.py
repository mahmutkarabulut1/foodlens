from __future__ import annotations

import os
from typing import Any, Dict, Optional


class MatchVerifier:
    """
    Küçük verifier iskeleti.
    Şu an default olarak rule-based çalışır.
    İleride DeepSeek / başka küçük bir LLM ile sadece needs_validation=True sonuçlarında kullanılabilir.
    """

    def __init__(self):
        self.provider = os.getenv("FOODLENS_VERIFIER_PROVIDER", "rule_based")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    def verify(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.provider == "deepseek":
            return self._verify_with_deepseek_stub(payload)
        return self._verify_rule_based(payload)

    def _verify_rule_based(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        reasons = []
        score = 0.85

        query_coverage = float(payload.get("query_coverage", 0.0))
        alias_precision = float(payload.get("alias_precision", 0.0))
        candidate_type = str(payload.get("candidate_type", "")).strip()
        ocr_fragment = str(payload.get("ocr_fragment", "")).strip()
        matched_key = str(payload.get("matched_key", "")).strip()

        if query_coverage < 1.0:
            reasons.append("query_coverage_below_1")
            score -= 0.20

        if candidate_type == "ingredient" and alias_precision < 0.67:
            reasons.append("ingredient_alias_precision_low")
            score -= 0.15

        if candidate_type in {"additive", "allergen"} and alias_precision < 1.0:
            reasons.append("regulated_alias_precision_not_full")
            score -= 0.10

        if not ocr_fragment or not matched_key:
            reasons.append("missing_core_fields")
            score -= 0.25

        accepted = score >= 0.60

        return {
            "provider": "rule_based",
            "accepted": accepted,
            "confidence": round(max(0.0, min(1.0, score)), 3),
            "reasons": reasons,
            "normalized_name": payload.get("candidate_name"),
            "candidate_id": payload.get("candidate_id"),
            "candidate_type": candidate_type,
        }

    def _verify_with_deepseek_stub(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        İskelet bırakıldı.
        Buraya daha sonra requests/httpx ile DeepSeek API çağrısı eklenebilir.
        Şimdilik güvenli fallback olarak rule_based verifier dönüyor.
        """
        result = self._verify_rule_based(payload)
        result["provider"] = "deepseek_stub_fallback"
        result["reasons"] = result.get("reasons", []) + ["deepseek_not_implemented_yet"]
        return result


def verify_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    verifier = MatchVerifier()
    return verifier.verify(payload)
