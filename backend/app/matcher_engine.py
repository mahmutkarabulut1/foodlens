from __future__ import annotations

from sentence_transformers import SentenceTransformer, util
from rapidfuzz import process, fuzz
import torch
import json
import logging
import re

from .config import (
    DB_FILE,
    STOP_ALIASES_RAW,
    ROLE_TERMS_RAW,
    ROLE_PREFIXES_RAW,
    TYPE_PRIORITY,
    QUERY_SYNONYMS,
    START_KEYWORDS,
    FUZZY_MIN_FOR_SEMANTIC,
    thresholds_for_type,
)
from .data_loader import load_master_records

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FoodLens")

ECODE_PATTERN = re.compile(r"\be[\s\-]?\d{3,4}[a-z]?\b", re.IGNORECASE)

TRANSLATION_TABLE = str.maketrans({
    "İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü", "Ş": "ş", "Ö": "ö", "Ç": "ç",
    "\n": " ", "\t": " ",
    ":": " ", ";": " ", ",": " ", ".": " ",
    "(": " ", ")": " ", "[": " ", "]": " ",
    "{": " ", "}": " ", "/": " ", "\\": " ",
    "\"": " ", "'": " ", "•": " ", "|": " ", "+": " ", "*": " "
})

ASCII_TABLE = str.maketrans({
    "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"
})


class FoodLensMatcher:
    def __init__(self):
        logger.info("NLP modeli yükleniyor: all-MiniLM-L6-v2")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        self.database = []
        self.exact_map = {}
        self.search_alias_map = {}
        self.search_aliases = []
        self.search_embeddings = None
        self._query_embedding_cache = {}

        self.stop_aliases = self._build_term_variants(STOP_ALIASES_RAW)
        self.role_terms = self._build_term_variants(ROLE_TERMS_RAW)
        self.role_prefixes = self._prepare_role_prefixes(ROLE_PREFIXES_RAW)

        self.load_database()

    def _normalize_text(self, text: str) -> str:
        if text is None:
            return ""
        text = str(text).translate(TRANSLATION_TABLE).lower()
        text = re.sub(r"[^0-9a-zçğıöşü\-\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _ascii_fold(self, text: str) -> str:
        return self._normalize_text(text).translate(ASCII_TABLE)

    def _canonicalize_ecode(self, text: str):
        raw = self._normalize_text(text)
        match = re.search(r"e[\s\-]?(\d{3,4})([a-z]?)", raw, re.IGNORECASE)
        if not match:
            return None
        digits = match.group(1)
        suffix = (match.group(2) or "").lower()
        return f"e{digits}{suffix}"

    def _display_name(self, item: dict) -> str:
        return item.get("name_tr") or item.get("name_en") or item.get("name") or ""

    def _build_term_variants(self, terms):
        result = set()
        for term in terms:
            n = self._normalize_text(term)
            a = self._ascii_fold(term)
            if n:
                result.add(n)
            if a:
                result.add(a)
        return result

    def _prepare_role_prefixes(self, prefixes):
        prepared = set()
        for prefix in prefixes:
            n = self._normalize_text(prefix)
            a = self._ascii_fold(prefix)
            if n:
                prepared.add(n)
            if a:
                prepared.add(a)
        return sorted(prepared, key=len, reverse=True)

    def _is_stop_alias(self, alias: str) -> bool:
        n = self._normalize_text(alias)
        a = self._ascii_fold(alias)
        return n in self.stop_aliases or a in self.stop_aliases or n in self.role_terms or a in self.role_terms

    def _should_index_exact(self, alias: str, item_type: str) -> bool:
        if not alias or self._is_stop_alias(alias):
            return False
        if len(alias) < 2:
            return False
        return True

    def _should_index_search(self, alias: str, item_type: str) -> bool:
        if not self._should_index_exact(alias, item_type):
            return False
        if self._canonicalize_ecode(alias):
            return True
        if len(alias) <= 2:
            return False
        if len(alias.split()) == 1 and len(alias) <= 4:
            return False
        return True

    def _expand_exact_aliases(self, raw_alias: str):
        variants = set()
        if raw_alias is None:
            return variants

        norm = self._normalize_text(raw_alias)
        ascii_norm = self._ascii_fold(raw_alias)
        ecode = self._canonicalize_ecode(raw_alias)

        if norm:
            variants.add(norm)
        if ascii_norm and ascii_norm != norm:
            variants.add(ascii_norm)
        if ecode:
            variants.add(ecode)
            variants.add(ecode.replace("e", "e "))
            variants.add(ecode.replace("e", "e-"))

        return {v.strip() for v in variants if v.strip()}

    def _expand_search_aliases(self, raw_alias: str):
        variants = set()
        if raw_alias is None:
            return variants

        norm = self._normalize_text(raw_alias)
        ecode = self._canonicalize_ecode(raw_alias)

        if norm:
            variants.add(norm)
        if ecode:
            variants.add(ecode)
            variants.add(ecode.replace("e", "e "))
            variants.add(ecode.replace("e", "e-"))

        return {v.strip() for v in variants if v.strip()}

    def _register_alias(self, target_map: dict, alias: str, record: dict):
        records = target_map.setdefault(alias, [])
        rec_id = str(record["item"].get("id", "")).strip()
        rec_type = str(record["item"].get("type", "")).strip()
        rec_name = self._display_name(record["item"]).strip()

        for existing in records:
            ex_id = str(existing["item"].get("id", "")).strip()
            ex_type = str(existing["item"].get("type", "")).strip()
            ex_name = self._display_name(existing["item"]).strip()
            if (rec_id, rec_type, rec_name) == (ex_id, ex_type, ex_name):
                return

        records.append(record)

    def _normalized_tokens(self, text: str):
        tokens = []
        for tok in self._normalize_text(text).split():
            if tok in self.stop_aliases or tok in self.role_terms:
                continue
            if len(tok) < 2:
                continue
            tokens.append(tok)
        return tokens

    def _token_match(self, qtok: str, atok: str) -> bool:
        if qtok == atok:
            return True
        if self._ascii_fold(qtok) == self._ascii_fold(atok):
            return True
        if len(qtok) >= 4 and len(atok) >= 4 and fuzz.WRatio(qtok, atok) >= 86:
            return True
        return False

    def _token_coverage(self, query: str, alias: str):
        q_tokens = self._normalized_tokens(query)
        a_tokens = self._normalized_tokens(alias)

        if not q_tokens or not a_tokens:
            return 0.0, 0.0, q_tokens, a_tokens

        matched = 0
        for qtok in q_tokens:
            if any(self._token_match(qtok, atok) for atok in a_tokens):
                matched += 1

        query_coverage = matched / len(q_tokens)
        alias_precision = matched / len(a_tokens) if a_tokens else 0.0
        return query_coverage, alias_precision, q_tokens, a_tokens

    def _is_query_alias_compatible(self, query: str, alias: str, item_type: str) -> bool:
        query_coverage, alias_precision, q_tokens, _ = self._token_coverage(query, alias)

        if not q_tokens:
            return False

        if item_type == "ingredient":
            return query_coverage >= 1.0 and alias_precision >= 0.50

        return query_coverage >= 1.0

    def _candidate_score(self, query: str, record: dict):
        item = record["item"]
        alias = record["alias"]
        item_type = item.get("type", "")
        item_id = self._normalize_text(item.get("id", ""))
        item_name = self._normalize_text(self._display_name(item))
        query_ecode = self._canonicalize_ecode(query)
        item_ecode = self._canonicalize_ecode(item.get("id", ""))

        query_coverage, alias_precision, _, _ = self._token_coverage(query, alias)

        exact_id = 1 if (item_id == query or (query_ecode and item_ecode == query_ecode)) else 0
        exact_name = 1 if (item_name == query or self._ascii_fold(item_name) == self._ascii_fold(query)) else 0
        exact_alias = 1 if (alias == query or self._ascii_fold(alias) == self._ascii_fold(query)) else 0
        known_name = 0 if item_name in self.stop_aliases else 1
        type_priority = TYPE_PRIORITY.get(item_type, 0)
        generic_penalty = -1 if (len(alias.split()) == 1 and len(alias) <= 4 and not self._canonicalize_ecode(alias)) else 0
        length_fit = -abs(len(alias) - len(query))

        return (
            exact_id,
            exact_name,
            exact_alias,
            known_name,
            type_priority,
            round(query_coverage, 4),
            round(alias_precision, 4),
            generic_penalty,
            length_fit,
        )

    def _select_best_candidate(self, query: str, candidates: list):
        unique_candidates = []
        seen = set()

        for record in candidates:
            item = record["item"]
            signature = (
                str(item.get("id", "")).strip(),
                self._display_name(item).strip(),
                str(item.get("type", "")).strip(),
            )
            if signature in seen:
                continue
            seen.add(signature)
            unique_candidates.append(record)

        return max(unique_candidates, key=lambda rec: self._candidate_score(query, rec))

    def _is_descriptor_record(self, record: dict) -> bool:
        item = record["item"]
        alias = record["alias"]

        name_norm = self._normalize_text(self._display_name(item))
        alias_norm = self._normalize_text(alias)
        name_ascii = self._ascii_fold(self._display_name(item))
        alias_ascii = self._ascii_fold(alias)

        if name_norm in self.role_terms or alias_norm in self.role_terms:
            return True
        if name_ascii in self.role_terms or alias_ascii in self.role_terms:
            return True
        return False

    def _alias_is_generic(self, alias: str) -> bool:
        return len(alias.split()) == 1 and len(alias) <= 5 and not self._canonicalize_ecode(alias)

    def _encode_query(self, query: str):
        if query not in self._query_embedding_cache:
            self._query_embedding_cache[query] = self.model.encode(
                query,
                convert_to_tensor=True,
                show_progress_bar=False,
            )
        return self._query_embedding_cache[query]

    def build_indices(self):
        self.exact_map = {}
        self.search_alias_map = {}

        for item in self.database:
            item_type = item.get("type", "ingredient")
            candidates = {
                item.get("id"),
                item.get("name_tr"),
                item.get("name_en"),
                item.get("name"),
            }

            keywords = item.get("keywords") or []
            if isinstance(keywords, list):
                candidates.update(keywords)

            for raw_alias in candidates:
                for alias in self._expand_exact_aliases(raw_alias):
                    if self._should_index_exact(alias, item_type):
                        self._register_alias(self.exact_map, alias, {"item": item, "alias": alias})

                for alias in self._expand_search_aliases(raw_alias):
                    if self._should_index_search(alias, item_type):
                        self._register_alias(self.search_alias_map, alias, {"item": item, "alias": alias})

        self.search_aliases = list(self.search_alias_map.keys())

        if self.search_aliases:
            logger.info("%s arama alias'ı vektörleştiriliyor...", len(self.search_aliases))
            self.search_embeddings = self.model.encode(
                self.search_aliases,
                convert_to_tensor=True,
                show_progress_bar=False,
            )
        else:
            self.search_embeddings = None

    def load_database(self):
        logger.info("Veritabanı yükleniyor: %s", DB_FILE)

        if not DB_FILE.exists():
            raise FileNotFoundError(f"Veritabanı dosyası bulunamadı: {DB_FILE}")

        self.database = load_master_records()

        self.build_indices()
        logger.info(
            "İndeks hazır. Kayıt: %s | Exact alias: %s | Search alias: %s",
            len(self.database), len(self.exact_map), len(self.search_aliases)
        )

    def exact_lookup(self, query: str):
        if query in self.exact_map:
            record = self._select_best_candidate(query, self.exact_map[query])
            if not self._is_descriptor_record(record):
                return record, "exact", query, 100

        folded = self._ascii_fold(query)
        if folded and folded in self.exact_map:
            record = self._select_best_candidate(query, self.exact_map[folded])
            if not self._is_descriptor_record(record):
                return record, "exact_ascii", folded, 99

        ecode = self._canonicalize_ecode(query)
        if ecode:
            for alias in (ecode, ecode.replace("e", "e "), ecode.replace("e", "e-")):
                if alias in self.exact_map:
                    record = self._select_best_candidate(query, self.exact_map[alias])
                    if not self._is_descriptor_record(record):
                        return record, "ecode_exact", alias, 100

        return None

    def _regulated_recovery(self, query: str, prepared_matches: list):
        regulated = [m for m in prepared_matches if m["item_type"] in {"additive", "allergen"}]
        if not regulated:
            return None

        regulated.sort(
            key=lambda x: (
                x["query_coverage"],
                x["alias_precision"],
                x["score"],
                TYPE_PRIORITY.get(x["item_type"], 0),
            ),
            reverse=True,
        )

        best = regulated[0]
        q_tokens = self._normalized_tokens(query)

        if not q_tokens:
            return None

        if len(q_tokens) >= 2:
            if best["query_coverage"] >= 1.0 and best["alias_precision"] >= 1.0 and best["score"] >= 72:
                return best["record"], "regulated_typo_recovery", best["alias"], int(round(best["score"]))

            if best["query_coverage"] >= 1.0 and best["alias_precision"] >= 0.67 and best["score"] >= 78:
                return best["record"], "regulated_typo_recovery", best["alias"], int(round(best["score"]))

            if best["query_coverage"] >= 1.0 and best["alias_precision"] >= 0.50 and best["score"] >= 74:
                return best["record"], "regulated_typo_recovery", best["alias"], int(round(best["score"]))

        if len(q_tokens) == 1 and self._canonicalize_ecode(query):
            if best["score"] >= 85:
                return best["record"], "regulated_typo_recovery", best["alias"], int(round(best["score"]))

        return None

    def search_lookup(self, query: str):
        if not query or self._is_stop_alias(query):
            return None

        exact = self.exact_lookup(query)
        if exact:
            return exact

        if len(query.split()) == 1 and len(query) <= 4 and not self._canonicalize_ecode(query):
            return None

        raw_matches = process.extract(
            query,
            self.search_aliases,
            scorer=fuzz.WRatio,
            limit=12,
        )
        raw_matches = [m for m in raw_matches if m[1] >= 68]

        if not raw_matches:
            return None

        prepared_matches = []
        for alias, score, idx in raw_matches:
            record = self._select_best_candidate(query, self.search_alias_map[alias])
            item_type = record["item"].get("type", "ingredient")

            if self._is_descriptor_record(record):
                continue
            if not self._is_query_alias_compatible(query, alias, item_type):
                continue

            qcov, aprec, _, _ = self._token_coverage(query, alias)

            prepared_matches.append({
                "alias": alias,
                "score": float(score),
                "idx": idx,
                "record": record,
                "item_type": item_type,
                "thresholds": thresholds_for_type(item_type),
                "query_coverage": qcov,
                "alias_precision": aprec,
            })

        if not prepared_matches:
            return None

        prepared_matches.sort(
            key=lambda x: (
                x["score"],
                TYPE_PRIORITY.get(x["item_type"], 0),
                x["query_coverage"],
                x["alias_precision"],
            ),
            reverse=True,
        )

        best = prepared_matches[0]

        if best["score"] >= best["thresholds"]["fuzzy_strong"] and not self._alias_is_generic(best["alias"]):
            return best["record"], "fuzzy_strong", best["alias"], int(best["score"])

        regulated_hit = self._regulated_recovery(query, prepared_matches)
        if regulated_hit:
            return regulated_hit

        if self.search_embeddings is not None:
            shortlist = prepared_matches[:8]
            shortlist_indices = [m["idx"] for m in shortlist]
            shortlist_aliases = [m["alias"] for m in shortlist]

            query_embedding = self._encode_query(query)
            subset_embeddings = self.search_embeddings[shortlist_indices]
            cos_scores = util.cos_sim(query_embedding, subset_embeddings)[0]

            best_semantic_local_idx = torch.argmax(cos_scores).item()
            best_semantic_score = float(cos_scores[best_semantic_local_idx].item())
            best_semantic_alias = shortlist_aliases[best_semantic_local_idx]
            best_semantic_match = shortlist[best_semantic_local_idx]

            paired_fuzzy = float(best_semantic_match["score"])
            combined_score = 0.55 * (best_semantic_score * 100.0) + 0.45 * paired_fuzzy
            semantic_threshold = best_semantic_match["thresholds"]["semantic"]

            if best_semantic_score >= semantic_threshold and paired_fuzzy >= FUZZY_MIN_FOR_SEMANTIC:
                return (
                    best_semantic_match["record"],
                    "semantic_rerank",
                    best_semantic_alias,
                    int(round(combined_score)),
                )

        if best["score"] >= best["thresholds"]["fuzzy_fallback"] and not self._alias_is_generic(best["alias"]):
            return best["record"], "fuzzy_fallback", best["alias"], int(best["score"])

        return None

    def _strip_role_prefixes(self, query: str) -> str:
        current = self._normalize_text(query)

        changed = True
        while changed:
            changed = False
            for prefix in self.role_prefixes:
                if current.startswith(prefix + " "):
                    current = current[len(prefix):].strip()
                    changed = True

        return current

    def preprocess_query_variants(self, raw_text: str):
        variants = []
        seen = set()

        base = self._normalize_text(raw_text)
        stripped = self._strip_role_prefixes(raw_text)
        folded_base = self._ascii_fold(raw_text)
        folded_stripped = self._ascii_fold(stripped)

        candidates = [base, stripped, folded_base, folded_stripped]

        for candidate in list(candidates):
            if candidate in QUERY_SYNONYMS:
                candidates.extend(QUERY_SYNONYMS[candidate])

        for candidate in candidates:
            if not candidate:
                continue
            candidate = self._normalize_text(candidate)
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            variants.append(candidate)

        return variants

    def extract_relevant_section(self, text: str):
        text_lower = text.lower()
        start_index = -1

        for kw in START_KEYWORDS:
            idx = text_lower.find(kw)
            if idx != -1:
                start_index = idx
                break

        if start_index == -1:
            return text

        relevant_part = text[start_index:]
        current_pos = 0
        found_index = -1

        for _ in range(4):
            dot_idx = relevant_part.find(".", current_pos)
            if dot_idx != -1:
                found_index = dot_idx
                current_pos = dot_idx + 1
            else:
                break

        return relevant_part[:found_index] if found_index != -1 else relevant_part

    def extract_ecodes(self, text: str):
        found = []
        seen = set()

        for match in ECODE_PATTERN.finditer(text):
            code = self._canonicalize_ecode(match.group(0))
            if code and code not in seen:
                seen.add(code)
                found.append(code)

        return found

    def split_ocr_items(self, text: str):
        prepared = text.replace("\n", ",").replace(";", ",").replace(":", ",")
        prepared = prepared.replace("(", ",").replace(")", ",").replace("[", ",").replace("]", ",")
        raw_items = [x.strip() for x in prepared.split(",")]

        queries = []
        seen = set()

        for raw_item in raw_items:
            if len(raw_item.strip()) < 2:
                continue
            for variant in self.preprocess_query_variants(raw_item):
                if variant and variant not in seen:
                    seen.add(variant)
                    queries.append(variant)

        return queries

    def _validation_flags(self, raw_query: str, matched_key: str, match_type: str, score: int, item_type: str):
        reasons = []

        if match_type == "semantic_rerank":
            reasons.append("semantic_match")
        if match_type == "fuzzy_fallback":
            reasons.append("fallback_fuzzy_match")
        if match_type == "regulated_typo_recovery":
            reasons.append("regulated_typo_recovery")
        if match_type == "fuzzy_strong" and score < 94:
            reasons.append("non_exact_fuzzy_match")

        qcov, aprec, q_tokens, a_tokens = self._token_coverage(raw_query, matched_key)

        if item_type == "ingredient" and aprec < 0.67:
            reasons.append("ingredient_extra_alias_tokens")
        if q_tokens and a_tokens and qcov < 1.0:
            reasons.append("partial_token_coverage")
        if item_type in {"additive", "allergen"} and score < 90 and match_type != "exact":
            reasons.append("low_confidence_regulated_item")

        needs_validation = len(reasons) > 0
        return needs_validation, reasons, qcov, aprec

    def _append_result(self, results: list, seen_ids: set, raw_query: str, full_context: str, record: dict, match_type: str, matched_key: str, score: int):
        if self._is_descriptor_record(record):
            return

        item = record["item"]
        item_id = str(item.get("id", "")).strip()
        item_name = self._display_name(item).strip()
        item_type = str(item.get("type", "")).strip()
        dedupe_key = item_id or item_name

        if not dedupe_key or dedupe_key in seen_ids:
            return

        needs_validation, validation_reason, qcov, aprec = self._validation_flags(
            raw_query=raw_query,
            matched_key=matched_key,
            match_type=match_type,
            score=score,
            item_type=item_type,
        )

        results.append({
            "id": item_id,
            "name": item_name,
            "item_type": item_type,
            "risk_level": item.get("risk_level", "Unknown"),
            "description": item.get("description_tr") or item.get("note", ""),
            "raw_query": raw_query,
            "matched_key": matched_key,
            "match_type": match_type,
            "match_score": int(score),
            "needs_validation": needs_validation,
            "validation_reason": validation_reason,
            "verifier_payload": {
                "ocr_fragment": raw_query,
                "matched_key": matched_key,
                "candidate_id": item_id,
                "candidate_name": item_name,
                "candidate_type": item_type,
                "context": full_context,
                "query_coverage": round(qcov, 3),
                "alias_precision": round(aprec, 3),
            },
        })
        seen_ids.add(dedupe_key)

    def analyze_text(self, ocr_text: str):
        targeted_text = self.extract_relevant_section(ocr_text)
        results = []
        seen_ids = set()

        for code in self.extract_ecodes(targeted_text):
            match = self.exact_lookup(code)
            if match:
                record, match_type, matched_key, score = match
                self._append_result(results, seen_ids, code, targeted_text, record, match_type, matched_key, score)

        for query in self.split_ocr_items(targeted_text):
            if len(query) < 2:
                continue
            match = self.search_lookup(query)
            if match:
                record, match_type, matched_key, score = match
                self._append_result(results, seen_ids, query, targeted_text, record, match_type, matched_key, score)

        return results

    def health(self):
        return {
            "status": "ok",
            "db_file": str(DB_FILE),
            "item_count": len(self.database),
            "exact_alias_count": len(self.exact_map),
            "search_alias_count": len(self.search_aliases),
        }
