"""
Hybrid search with MMR reranking and temporal decay.
Inspired by OpenClaw's search architecture.
"""

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import math

from config.defaults import (
    MMR_LAMBDA,
    TEMPORAL_DECAY_ENABLED,
    TEMPORAL_HALF_LIFE_DAYS,
)


@dataclass
class SearchResult:
    id: str
    content: str
    score: float
    tier: str
    created_at: Optional[str] = None


def mmr_rerank(
    results: List[SearchResult],
    lambda_param: float = MMR_LAMBDA
) -> List[SearchResult]:
    """
    Maximal Marginal Relevance reranking.

    Balances relevance vs diversity:
    MMR = λ * relevance - (1 - λ) * max_similarity_to_selected

    Inspired by OpenClaw's MMR implementation.
    """
    if not results:
        return results

    selected = []
    remaining = results.copy()

    for _ in range(len(results)):
        if not remaining:
            break

        best_score = -float('inf')
        best_item = None
        best_idx = 0

        for idx, item in enumerate(remaining):
            relevance = item.score
            max_sim = 0.0

            # Calculate max similarity to already selected items
            for sel in selected:
                sim = _jaccard_similarity(item.content, sel.content)
                max_sim = max(max_sim, sim)

            # MMR formula
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

            if mmr_score > best_score:
                best_score = mmr_score
                best_item = item
                best_idx = idx

        if best_item:
            selected.append(best_item)
            remaining.pop(best_idx)

    return selected


def temporal_decay(
    results: List[SearchResult],
    half_life_days: float = TEMPORAL_HALF_LIFE_DAYS,
    enabled: bool = TEMPORAL_DECAY_ENABLED
) -> List[SearchResult]:
    """
    Apply temporal decay to search results.

    Recent memories get higher weight:
    decayed_score = score * e^(-λ * age_in_days)

    Inspired by OpenClaw's temporal decay.
    """
    if not enabled or not half_life_days:
        return results

    lambda_decay = math.log(2) / half_life_days
    now = datetime.now().timestamp()

    for result in results:
        if result.created_at:
            try:
                created = datetime.fromisoformat(
                    result.created_at.replace('Z', '+00:00')
                ).timestamp()
                age_days = (now - created) / (24 * 3600)
                decay_factor = math.exp(-lambda_decay * age_days)
                result.score *= decay_factor
            except (ValueError, TypeError):
                pass  # Keep original score if parsing fails

    return sorted(results, key=lambda x: x.score, reverse=True)


def _jaccard_similarity(text1: str, text2: str) -> float:
    """
    Calculate Jaccard similarity between two texts.

    Used for MMR to ensure diversity in results.
    """
    # Tokenize (simplified version)
    tokens1 = set(_tokenize(text1))
    tokens2 = set(_tokenize(text2))

    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)

    return intersection / union if union > 0 else 0.0


def _tokenize(text: str) -> List[str]:
    """
    Tokenize text for similarity calculation.

    Handles CJK characters (from OpenClaw implementation).
    """
    import re

    # Extract alphanumeric tokens
    tokens = re.findall(r'[a-zA-Z0-9]+', text.lower())

    # Add CJK characters as unigrams
    cjk_chars = re.findall(r'[\u4e00-\u9fff]', text)

    # Add CJK bigrams
    cjk_bigrams = [
        text[i] + text[i+1]
        for i in range(len(text) - 1)
        if '\u4e00' <= text[i] <= '\u9fff' and '\u4e00' <= text[i+1] <= '\u9fff'
    ]

    return tokens + cjk_chars + cjk_bigrams


def hybrid_search(
    vector_results: List[SearchResult],
    keyword_results: List[SearchResult],
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    apply_mmr: bool = True,
    apply_temporal_decay: bool = True
) -> List[SearchResult]:
    """
    Combine vector and keyword search results.

    Formula: combined_score = vector_weight * vector + keyword_weight * keyword

    Inspired by OpenClaw's hybrid search.
    """
    # Create score lookup
    scores: dict[str, float] = {}

    for r in vector_results:
        scores[r.id] = scores.get(r.id, 0) + vector_weight * r.score

    for r in keyword_results:
        scores[r.id] = scores.get(r.id, 0) + keyword_weight * r.score

    # Merge results
    id_to_result = {r.id: r for r in vector_results + keyword_results}
    combined = [
        SearchResult(
            id=rid,
            content=id_to_result[rid].content,
            score=score,
            tier=id_to_result[rid].tier,
            created_at=id_to_result[rid].created_at
        )
        for rid, score in scores.items()
    ]

    # Sort by combined score
    combined.sort(key=lambda x: x.score, reverse=True)

    # Apply MMR for diversity
    if apply_mmr:
        combined = mmr_rerank(combined)

    # Apply temporal decay for recency
    if apply_temporal_decay:
        combined = temporal_decay(combined)

    return combined
"""
Hybrid search with MMR reranking and temporal decay.
Inspired by OpenClaw's search architecture.
"""

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import math

from config.defaults import (
    MMR_LAMBDA,
    TEMPORAL_DECAY_ENABLED,
    TEMPORAL_HALF_LIFE_DAYS,
)


@dataclass
class SearchResult:
    id: str
    content: str
    score: float
    tier: str
    created_at: Optional[str] = None


def mmr_rerank(
    results: List[SearchResult],
    lambda_param: float = MMR_LAMBDA
) -> List[SearchResult]:
    """
    Maximal Marginal Relevance reranking.

    Balances relevance vs diversity:
    MMR = λ * relevance - (1 - λ) * max_similarity_to_selected

    Inspired by OpenClaw's MMR implementation.
    """
    if not results:
        return results

    selected = []
    remaining = results.copy()

    for _ in range(len(results)):
        if not remaining:
            break

        best_score = -float('inf')
        best_item = None
        best_idx = 0

        for idx, item in enumerate(remaining):
            relevance = item.score
            max_sim = 0.0

            # Calculate max similarity to already selected items
            for sel in selected:
                sim = _jaccard_similarity(item.content, sel.content)
                max_sim = max(max_sim, sim)

            # MMR formula
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

            if mmr_score > best_score:
                best_score = mmr_score
                best_item = item
                best_idx = idx

        if best_item:
            selected.append(best_item)
            remaining.pop(best_idx)

    return selected


def temporal_decay(
    results: List[SearchResult],
    half_life_days: float = TEMPORAL_HALF_LIFE_DAYS,
    enabled: bool = TEMPORAL_DECAY_ENABLED
) -> List[SearchResult]:
    """
    Apply temporal decay to search results.

    Recent memories get higher weight:
    decayed_score = score * e^(-λ * age_in_days)

    Inspired by OpenClaw's temporal decay.
    """
    if not enabled or not half_life_days:
        return results

    lambda_decay = math.log(2) / half_life_days
    now = datetime.now().timestamp()

    for result in results:
        if result.created_at:
            try:
                created = datetime.fromisoformat(
                    result.created_at.replace('Z', '+00:00')
                ).timestamp()
                age_days = (now - created) / (24 * 3600)
                decay_factor = math.exp(-lambda_decay * age_days)
                result.score *= decay_factor
            except (ValueError, TypeError):
                pass  # Keep original score if parsing fails

    return sorted(results, key=lambda x: x.score, reverse=True)


def _jaccard_similarity(text1: str, text2: str) -> float:
    """
    Calculate Jaccard similarity between two texts.

    Used for MMR to ensure diversity in results.
    """
    # Tokenize (simplified version)
    tokens1 = set(_tokenize(text1))
    tokens2 = set(_tokenize(text2))

    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)

    return intersection / union if union > 0 else 0.0


def _tokenize(text: str) -> List[str]:
    """
    Tokenize text for similarity calculation.

    Handles CJK characters (from OpenClaw implementation).
    """
    import re

    # Extract alphanumeric tokens
    tokens = re.findall(r'[a-zA-Z0-9]+', text.lower())

    # Add CJK characters as unigrams
    cjk_chars = re.findall(r'[\u4e00-\u9fff]', text)

    # Add CJK bigrams
    cjk_bigrams = [
        text[i] + text[i+1]
        for i in range(len(text) - 1)
        if '\u4e00' <= text[i] <= '\u9fff' and '\u4e00' <= text[i+1] <= '\u9fff'
    ]

    return tokens + cjk_chars + cjk_bigrams


def hybrid_search(
    vector_results: List[SearchResult],
    keyword_results: List[SearchResult],
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    apply_mmr: bool = True,
    apply_temporal_decay: bool = True
) -> List[SearchResult]:
    """
    Combine vector and keyword search results.

    Formula: combined_score = vector_weight * vector + keyword_weight * keyword

    Inspired by OpenClaw's hybrid search.
    """
    # Create score lookup
    scores: dict[str, float] = {}

    for r in vector_results:
        scores[r.id] = scores.get(r.id, 0) + vector_weight * r.score

    for r in keyword_results:
        scores[r.id] = scores.get(r.id, 0) + keyword_weight * r.score

    # Merge results
    id_to_result = {r.id: r for r in vector_results + keyword_results}
    combined = [
        SearchResult(
            id=rid,
            content=id_to_result[rid].content,
            score=score,
            tier=id_to_result[rid].tier,
            created_at=id_to_result[rid].created_at
        )
        for rid, score in scores.items()
    ]

    # Sort by combined score
    combined.sort(key=lambda x: x.score, reverse=True)

    # Apply MMR for diversity
    if apply_mmr:
        combined = mmr_rerank(combined)

    # Apply temporal decay for recency
    if apply_temporal_decay:
        combined = temporal_decay(combined)

    return combined
