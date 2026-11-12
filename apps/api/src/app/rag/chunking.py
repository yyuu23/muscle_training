"""
Chunking (plan §7.9)

- Target ~600 Chinese chars, cap ~1000; prefer action/topic boundaries.
- Overlap the final sentence of the previous chunk.
- Preserve negation, conditions, limits; timestamps are ms integers.
- Reviewer additions are stored separately from original transcript text.
"""

import hashlib
import re
from dataclasses import dataclass, field

TARGET_CHARS = 600
MAX_CHARS = 1000

_SENTENCE_END = re.compile(r"(?<=[。！？!?.；;])\s*")


@dataclass
class TextChunk:
    ordinal: int
    text: str
    start_ms: int | None = None
    end_ms: int | None = None
    tags: list[str] = field(default_factory=list)
    is_annotation: bool = False

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def _hard_wrap(sentence: str) -> list[str]:
    """Wrap a single over-long sentence at MAX_CHARS boundaries."""
    return [sentence[i : i + MAX_CHARS] for i in range(0, len(sentence), MAX_CHARS)]


def chunk_transcript(segments: list[dict]) -> list[TextChunk]:
    """Chunk timed transcript segments (each: start_ms/end_ms/text)."""
    chunks: list[TextChunk] = []
    buffer: list[dict] = []
    buffer_chars = 0
    overlap_sentence: str | None = None
    ordinal = 0

    def flush() -> None:
        nonlocal buffer, buffer_chars, overlap_sentence, ordinal
        if not buffer:
            return
        texts = []
        if overlap_sentence:
            texts.append(overlap_sentence)
        texts.extend(seg["text"] for seg in buffer)
        text = "\n".join(t for t in texts if t)

        if len(text) <= MAX_CHARS:
            chunks.append(
                TextChunk(
                    ordinal=ordinal,
                    text=text,
                    start_ms=buffer[0].get("start_ms"),
                    end_ms=buffer[-1].get("end_ms"),
                )
            )
            ordinal += 1
            overlap_sentence = _last_sentence(buffer)
        else:
            # Over capacity even with boundary preference: split hard
            for piece in _hard_wrap(text):
                chunks.append(
                    TextChunk(
                        ordinal=ordinal,
                        text=piece,
                        start_ms=buffer[0].get("start_ms"),
                        end_ms=buffer[-1].get("end_ms"),
                    )
                )
                ordinal += 1
            overlap_sentence = _last_sentence(buffer)

        buffer = []
        buffer_chars = 0

    for seg in segments:
        seg_len = len(seg.get("text", ""))
        if buffer_chars + seg_len > TARGET_CHARS:
            flush()
        buffer.append(seg)
        buffer_chars += seg_len

    flush()
    return chunks


def chunk_document(text: str, *, annotations: list[dict] | None = None) -> list[TextChunk]:
    """Chunk an untimed document into topic chunks with sentence overlap."""
    sentences = _split_sentences(text)
    chunks: list[TextChunk] = []
    current: list[str] = []
    current_chars = 0
    ordinal = 0

    for sentence in sentences:
        if current_chars + len(sentence) > TARGET_CHARS and current:
            chunks.append(TextChunk(ordinal=ordinal, text="\n".join(current)))
            ordinal += 1
            current = [current[-1]] if current else []  # overlap last sentence
            current_chars = len(current[0]) if current else 0
        for piece in _hard_wrap(sentence) if len(sentence) > MAX_CHARS else [sentence]:
            current.append(piece)
            current_chars += len(piece)

    if current:
        chunks.append(TextChunk(ordinal=ordinal, text="\n".join(current)))

    # Reviewer annotations are separate chunks, never merged into original
    for annotation in annotations or []:
        ann_text = annotation.get("text", "").strip()
        if ann_text:
            chunks.append(
                TextChunk(
                    ordinal=len(chunks),
                    text=ann_text,
                    tags=annotation.get("tags", []),
                    is_annotation=True,
                )
            )

    return chunks


def _last_sentence(buffer: list[dict]) -> str | None:
    last_text = buffer[-1].get("text", "") if buffer else ""
    sentences = _split_sentences(last_text)
    return sentences[-1] if sentences else (last_text or None)
