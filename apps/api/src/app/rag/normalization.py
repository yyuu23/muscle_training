"""
Query and text normalization (plan §7.9)

jieba tokenization + exercise alias dictionary + query standardization.
Alias mapping is data-driven so admins can extend it via content.
"""

import re

import jieba

# Exercise alias dictionary: canonical name ← variants (seed set;
# extended at runtime via register_aliases from the exercise catalog).
_ALIAS_MAP: dict[str, str] = {
    "卧推": "卧推",
    "平板卧推": "卧推",
    "bench press": "卧推",
    "benchpress": "卧推",
    "深蹲": "深蹲",
    "squat": "深蹲",
    "颈后深蹲": "深蹲",
    "硬拉": "硬拉",
    "deadlift": "硬拉",
    "推举": "推举",
    "肩推": "推举",
    "站姿推举": "推举",
    "overhead press": "推举",
    "划船": "划船",
    "杠铃划船": "划船",
    "row": "划船",
    "引体": "引体向上",
    "引体向上": "引体向上",
    "pull up": "引体向上",
    "pullup": "引体向上",
    "双杠": "双杠臂屈伸",
    "双杠臂屈伸": "双杠臂屈伸",
    "dip": "双杠臂屈伸",
}

_WHITESPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[，。！？；：、""''（）()\\[\\]【】,!?;:\"']")


def register_aliases(aliases: dict[str, str]) -> None:
    """Extend the alias map from catalog data (variant → canonical)."""
    _ALIAS_MAP.update(aliases)


def normalize_text(text: str) -> str:
    """Whitespace/punctuation cleanup preserving content words."""
    cleaned = _PUNCT.sub(" ", text)
    return _WHITESPACE.sub(" ", cleaned).strip()


def canonicalize_terms(text: str) -> str:
    """Replace known alias variants with canonical exercise names."""
    result = text
    # Longest-first so 平板卧推 beats 卧推
    for alias in sorted(_ALIAS_MAP, key=len, reverse=True):
        if alias in result:
            result = result.replace(alias, _ALIAS_MAP[alias])
    return result


def tokenize(text: str) -> list[str]:
    """jieba tokens for keyword retrieval, lowercased, deduplicated order-kept."""
    normalized = canonicalize_terms(normalize_text(text))
    tokens = [t.strip().lower() for t in jieba.cut_for_search(normalized) if t.strip()]
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def normalize_query(query: str) -> dict:
    """Standardized query: canonical text + tokens + tsquery string."""
    tokens = tokenize(query)
    return {
        "original": query,
        "normalized": normalize_text(query),
        "canonical": canonicalize_terms(normalize_text(query)),
        "tokens": tokens,
        # PostgreSQL 'simple' config: AND all tokens for precision
        "tsquery": " & ".join(tokens),
    }
