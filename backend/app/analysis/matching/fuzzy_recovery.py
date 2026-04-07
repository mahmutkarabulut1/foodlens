"""
Fuzzy Recovery Matcher — matches OCR-corrupted ingredient text to database entries.

Performance optimizations:
  - Aliases bucketed by token count (1-token queries only search 1-token aliases)
  - Max alias length cap (40 chars — real ingredient names are short)
  - Reduced rapidfuzz candidate limits
  - N-gram sub-matching capped at 6 tokens

Anti-hallucination:
  - Ambiguous matches (close scores to different items) are rejected
  - Length-proportional thresholds (short words need near-exact match)
  - First-character guard for short tokens
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from rapidfuzz import fuzz, process

from ..preprocessing.normalize import ascii_fold, normalize_for_matching
from ..schemas import CandidateSpan, MatchedEntity
from .lexicon import MasterLexicon, TYPE_PRIORITY_BY_SECTION, TYPE_PRIORITY_DEFAULT

STOP_TOKENS = {
    "ve", "veya", "ile", "icin", "için", "olan", "olarak", "from", "with",
    "icindekiler", "içindekiler", "ingredients", "ingredient",
    "eser", "iz", "miktarda", "contains", "free", "from",
    "the", "and", "or", "of", "bir", "bu", "ise", "ama",
}

ECODE_RE = re.compile(r"^e[\s\-]?(\d{3,4})([a-z]?)$", re.IGNORECASE)
MAX_FUZZY_ALIAS_LEN = 25


class FuzzyRecoveryMatcher:
    def __init__(self, lexicon: MasterLexicon):
        self.lexicon = lexicon

        # Build bucketed alias lists for fast lookup
        self._single_aliases: List[str] = []
        self._single_folded: List[str] = []
        self._multi_aliases: List[str] = []
        self._multi_folded: List[str] = []

        for alias in self.lexicon.alias_map.keys():
            if len(alias) > MAX_FUZZY_ALIAS_LEN or len(alias) < 2:
                continue
            folded = ascii_fold(alias)
            token_count = len(folded.split())
            if token_count <= 1:
                self._single_aliases.append(alias)
                self._single_folded.append(folded)
            else:
                self._multi_aliases.append(alias)
                self._multi_folded.append(folded)

        # Combined list for multi-token queries (search both buckets)
        self._all_aliases = self._single_aliases + self._multi_aliases
        self._all_folded = self._single_folded + self._multi_folded

    def _normalize(self, text: str) -> str:
        return normalize_for_matching(text or "")

    def _fold(self, text: str) -> str:
        return ascii_fold(text or "")

    def _tokens(self, text: str) -> List[str]:
        normalized = self._fold(self._normalize(text))
        return [t for t in normalized.split() if len(t) >= 2 and t not in STOP_TOKENS]

    # ── E-code matching ─────────────────────────────────────────────────────

    def _try_ecode_match(self, span: CandidateSpan) -> Optional[MatchedEntity]:
        raw = (span.normalized_text or span.raw_text).strip()
        raw_clean = raw.upper().replace(" ", "").replace("-", "")
        m = ECODE_RE.match(raw_clean)
        if not m:
            m = ECODE_RE.match(raw)
            if not m:
                return None

        ecode = f"e{m.group(1)}{m.group(2)}".lower()
        record = self.lexicon.exact_lookup(ecode, span.section_type)
        if record:
            return MatchedEntity(
                item_id=record["id"], name=record["name"],
                item_type=record["item_type"], risk_level=record["risk_level"],
                description=record["description"], matched_key=ecode,
                raw_query=span.raw_text, match_type="ecode_recovery",
                match_score=98, polarity=span.polarity,
                source_section=span.section_type, source_text=span.evidence,
            )
        return None

    # ── Token scoring ───────────────────────────────────────────────────────

    def _common_prefix_len(self, a: str, b: str) -> int:
        return sum(1 for x, y in zip(a, b) if x == y)

    def _common_suffix_len(self, a: str, b: str) -> int:
        return sum(1 for x, y in zip(reversed(a), reversed(b)) if x == y)

    def _token_match_score(self, query_token: str, alias_token: str) -> float:
        q, a = self._fold(query_token), self._fold(alias_token)
        if not q or not a:
            return 0.0
        if q == a:
            return 1.0

        wr = fuzz.WRatio(q, a) / 100.0
        ratio = fuzz.ratio(q, a) / 100.0
        prefix_score = min(self._common_prefix_len(q, a), 4) / 4.0
        suffix_score = min(self._common_suffix_len(q, a), 3) / 3.0

        score = 0.55 * wr + 0.25 * ratio + 0.12 * prefix_score + 0.08 * suffix_score
        score -= 0.12 * abs(len(q) - len(a)) / max(len(q), len(a), 1)

        if q[0] != a[0]:
            score -= 0.25 if min(len(q), len(a)) <= 6 else 0.10

        return max(0.0, min(score, 1.0))

    def _best_token_alignment(self, query_tokens: List[str], alias_tokens: List[str]):
        if not query_tokens or not alias_tokens:
            return 0.0, 0.0, 0.0, 0.0

        q_scores = [max((self._token_match_score(q, a) for a in alias_tokens), default=0.0) for q in query_tokens]
        a_scores = [max((self._token_match_score(q, a) for q in query_tokens), default=0.0) for a in alias_tokens]

        return (
            sum(q_scores) / len(q_scores),
            sum(a_scores) / len(a_scores),
            sum(1 for s in q_scores if s >= 0.97) / len(q_scores),
            min(q_scores) if q_scores else 0.0,
        )

    def _candidate_priority(self, record: Dict[str, str], section_type: str) -> int:
        return TYPE_PRIORITY_BY_SECTION.get(section_type, TYPE_PRIORITY_DEFAULT).get(record.get("item_type", ""), 0)

    # ── Thresholds ──────────────────────────────────────────────────────────

    def _single_token_thresholds(self, token_len: int) -> Dict[str, float]:
        if token_len <= 3:
            return {"min_token_score": 0.99, "min_fuzzy_score": 98.0, "ambiguity_gap": 5.0}
        if token_len == 4:
            return {"min_token_score": 0.96, "min_fuzzy_score": 96.0, "ambiguity_gap": 4.0}
        if token_len <= 6:
            return {"min_token_score": 0.90, "min_fuzzy_score": 90.0, "ambiguity_gap": 3.0}
        if token_len <= 9:
            return {"min_token_score": 0.87, "min_fuzzy_score": 87.0, "ambiguity_gap": 2.5}
        return {"min_token_score": 0.84, "min_fuzzy_score": 84.0, "ambiguity_gap": 2.0}

    def _multi_token_thresholds(self, item_type: str, qtc: int) -> Dict[str, float]:
        if item_type == "ingredient":
            if qtc == 2:
                return {"min_qc": 0.87, "min_ap": 0.76, "min_fs": 82.0, "ag": 1.5}
            return {"min_qc": 0.83, "min_ap": 0.70, "min_fs": 79.0, "ag": 1.5}
        if item_type in {"additive", "allergen"}:
            if qtc == 2:
                return {"min_qc": 0.89, "min_ap": 0.79, "min_fs": 83.0, "ag": 1.8}
            return {"min_qc": 0.86, "min_ap": 0.73, "min_fs": 81.0, "ag": 1.8}
        return {"min_qc": 0.90, "min_ap": 0.83, "min_fs": 86.0, "ag": 2.0}

    # ── Anti-hallucination check ────────────────────────────────────────────

    def _passes_ambiguity_check(self, accepted: list, key_fields: list) -> bool:
        """Return True if best match is sufficiently better than second-best."""
        if len(accepted) < 2:
            return True
        best, second = accepted[0], accepted[1]
        if best["record"].get("id", "") == second["record"].get("id", ""):
            return True
        fuzzy_gap = best["fuzzy_score"] - second["fuzzy_score"]
        if fuzzy_gap >= best.get("ambiguity_gap", 2.0):
            return True
        for field in key_fields:
            if best.get(field, 0) - second.get(field, 0) >= 0.05:
                return True
        return False

    # ── Single-token matching ───────────────────────────────────────────────

    def _match_single_token(self, span: CandidateSpan, query_token: str) -> Optional[MatchedEntity]:
        if len(query_token) < 3:
            return None

        th = self._single_token_thresholds(len(query_token))
        folded_q = self._fold(query_token)

        # Search only single-token aliases
        raw_matches = process.extract(
            folded_q, self._single_folded,
            scorer=fuzz.WRatio, processor=None, limit=15,
        )

        accepted = []
        for _choice, fuzzy_score, index in raw_matches:
            alias = self._single_aliases[index]
            alias_tokens = self._tokens(alias)
            if len(alias_tokens) != 1:
                continue

            token_score = self._token_match_score(query_token, alias_tokens[0])
            if token_score < th["min_token_score"] or fuzzy_score < th["min_fuzzy_score"]:
                continue
            if len(query_token) <= 6 and folded_q[0] != self._fold(alias_tokens[0])[0]:
                continue

            for record in self.lexicon.alias_map.get(alias, []):
                accepted.append({
                    "record": record, "alias": alias,
                    "token_score": float(token_score), "fuzzy_score": float(fuzzy_score),
                    "priority": self._candidate_priority(record, span.section_type),
                    "ambiguity_gap": float(th["ambiguity_gap"]),
                })

        if not accepted:
            return None

        accepted.sort(key=lambda x: (x["token_score"], x["priority"], x["fuzzy_score"]), reverse=True)

        if not self._passes_ambiguity_check(accepted, ["token_score"]):
            return None

        rec = accepted[0]["record"]
        return MatchedEntity(
            item_id=rec["id"], name=rec["name"], item_type=rec["item_type"],
            risk_level=rec["risk_level"], description=rec["description"],
            matched_key=accepted[0]["alias"], raw_query=span.raw_text,
            match_type="fuzzy_recovery", match_score=int(round(accepted[0]["fuzzy_score"])),
            polarity=span.polarity, source_section=span.section_type,
            source_text=span.evidence,
        )

    # ── Multi-token matching ────────────────────────────────────────────────

    def _match_multi_token(self, span: CandidateSpan, query: str, query_tokens: List[str]) -> Optional[MatchedEntity]:
        folded_q = self._fold(query)

        raw_matches = process.extract(
            folded_q, self._all_folded,
            scorer=fuzz.WRatio, processor=None, limit=20,
        )

        accepted = []
        for _choice, fuzzy_score, index in raw_matches:
            alias = self._all_aliases[index]
            alias_tokens = self._tokens(alias)
            if not alias_tokens:
                continue

            for record in self.lexicon.alias_map.get(alias, []):
                item_type = record.get("item_type", "")
                th = self._multi_token_thresholds(item_type, len(query_tokens))

                qc, ap, sar, mqts = self._best_token_alignment(query_tokens, alias_tokens)

                special_ok = (
                    len(query_tokens) == 2 and qc >= 0.86 and ap >= 0.86
                    and sar >= 0.50 and mqts >= 0.76
                )
                if not special_ok:
                    if qc < th["min_qc"] or ap < th["min_ap"]:
                        continue
                if fuzzy_score < th["min_fs"]:
                    continue
                if sar == 0.0 and qc < 0.93:
                    continue

                accepted.append({
                    "record": record, "alias": alias,
                    "fuzzy_score": float(fuzzy_score),
                    "query_coverage": float(qc), "alias_precision": float(ap),
                    "strong_anchor_ratio": float(sar),
                    "min_query_token_score": float(mqts),
                    "priority": self._candidate_priority(record, span.section_type),
                    "ambiguity_gap": float(th["ag"]),
                })

        if not accepted:
            return None

        accepted.sort(
            key=lambda x: (x["query_coverage"], x["alias_precision"],
                           x["min_query_token_score"], x["priority"], x["fuzzy_score"]),
            reverse=True,
        )

        if not self._passes_ambiguity_check(accepted, ["query_coverage", "alias_precision", "min_query_token_score"]):
            return None

        rec = accepted[0]["record"]
        return MatchedEntity(
            item_id=rec["id"], name=rec["name"], item_type=rec["item_type"],
            risk_level=rec["risk_level"], description=rec["description"],
            matched_key=accepted[0]["alias"], raw_query=span.raw_text,
            match_type="fuzzy_recovery", match_score=int(round(accepted[0]["fuzzy_score"])),
            polarity=span.polarity, source_section=span.section_type,
            source_text=span.evidence,
        )

    # ── N-gram sub-matching ─────────────────────────────────────────────────

    def _try_ngram_sub_matches(self, span: CandidateSpan, query_tokens: List[str]) -> Optional[MatchedEntity]:
        if len(query_tokens) < 3 or len(query_tokens) > 6:
            return None

        best_entity: Optional[MatchedEntity] = None
        best_score = 0.0

        for window_size in [2, 1]:
            for start in range(len(query_tokens) - window_size + 1):
                sub_tokens = query_tokens[start:start + window_size]
                sub_query = " ".join(sub_tokens)
                sub_span = CandidateSpan(
                    raw_text=sub_query, normalized_text=sub_query,
                    section_type=span.section_type, polarity=span.polarity,
                    category_hint=span.category_hint, evidence=span.evidence,
                )
                if window_size == 1:
                    entity = self._match_single_token(sub_span, sub_tokens[0])
                else:
                    entity = self._match_multi_token(sub_span, sub_query, sub_tokens)
                if entity and entity.match_score > best_score:
                    best_entity = entity
                    best_score = entity.match_score

        return best_entity

    # ── Main entry ──────────────────────────────────────────────────────────

    def match_span(self, span: CandidateSpan) -> Optional[MatchedEntity]:
        query = self._normalize(span.normalized_text or span.raw_text)
        query_tokens = self._tokens(query)
        if not query or not query_tokens:
            return None

        ecode = self._try_ecode_match(span)
        if ecode:
            return ecode

        if len(query_tokens) == 1:
            return self._match_single_token(span, query_tokens[0])

        result = self._match_multi_token(span, query, query_tokens)
        if result:
            return result

        return self._try_ngram_sub_matches(span, query_tokens)
