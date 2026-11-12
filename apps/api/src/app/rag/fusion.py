"""
RRF fusion and dedup (plan §7.9)

Reciprocal Rank Fusion with k=60, then near-duplicate removal driven
by a caller-supplied text accessor + similarity function.
"""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class FusedItem:
    chunk_id: str
    rrf_score: float
    best_rank: int
    sources: list[str] = field(default_factory=list)


def rrf_fuse(
    rankings: dict[str, list[str]],
    *,
    k: int = 60,
) -> list[FusedItem]:
    """Fuse multiple ranked chunk-id lists with RRF.

    rankings: {"keyword": [id...best-first], "vector": [...]}
    """
    scores: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    sources: dict[str, list[str]] = {}

    for source, ranking in rankings.items():
        for rank, chunk_id in enumerate(ranking, start=1):
            contribution = 1.0 / (k + rank)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + contribution
            if chunk_id not in best_rank or rank < best_rank[chunk_id]:
                best_rank[chunk_id] = rank
            if source not in sources.setdefault(chunk_id, []):
                sources[chunk_id].append(source)

    fused = [
        FusedItem(
            chunk_id=chunk_id,
            rrf_score=score,
            best_rank=best_rank[chunk_id],
            sources=sources[chunk_id],
        )
        for chunk_id, score in scores.items()
    ]
    fused.sort(key=lambda f: (-f.rrf_score, f.best_rank))
    return fused


def jaccard_similarity(a: str, b: str) -> float:
    """Character-bigram Jaccard similarity for near-duplicate detection."""
    def bigrams(text: str) -> set[str]:
        normalized = "".join(text.split())
        return {normalized[i : i + 2] for i in range(len(normalized) - 1)} or {normalized}

    ga, gb = bigrams(a), bigrams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def dedupe_chunks(
    items: list[FusedItem],
    get_text: Callable[[str], str | None],
    *,
    similarity: Callable[[str, str], float] = jaccard_similarity,
    threshold: float = 0.85,
) -> list[FusedItem]:
    """Drop highly-overlapping chunks, keeping the higher-ranked one."""
    kept: list[FusedItem] = []
    kept_texts: list[str] = []

    for item in items:
        text = get_text(item.chunk_id)
        if text is None:
            kept.append(item)
            continue
        if any(similarity(text, existing) >= threshold for existing in kept_texts):
            continue
        kept.append(item)
        kept_texts.append(text)

    return kept
