"""
Chunking and subtitle tests (plan §7.9): SRT/VTT parsing with
millisecond timestamps, ~600/1000-char targets, sentence overlap,
negation/condition preservation, annotation separation.
"""

from app.media.subtitles import cues_to_plain_text, parse_srt, parse_vtt
from app.rag.chunking import MAX_CHARS, chunk_document, chunk_transcript

SRT_SAMPLE = """1
00:00:01,000 --> 00:00:04,500
大家好，今天讲胸部热身

2
00:00:04,600 --> 00:00:09,200
热身的时候不要直接上大重量

3
00:00:09,300 --> 00:00:14,000
如果你是新手，先用弹力带找感觉
"""


def test_parse_srt_millisecond_timestamps():
    cues = parse_srt(SRT_SAMPLE)
    assert len(cues) == 3
    assert cues[0].start_ms == 1000
    assert cues[0].end_ms == 4500
    assert cues[2].start_ms == 9300


def test_parse_srt_tolerates_crlf_and_bom():
    bom_sample = "﻿" + SRT_SAMPLE.replace("\n", "\r\n")
    cues = parse_srt(bom_sample)
    assert len(cues) == 3


def test_parse_vtt():
    vtt = """WEBVTT

00:01.000 --> 00:04.500
第一段

00:04.600 --> 00:09.000
第二段
"""
    cues = parse_vtt(vtt)
    assert len(cues) == 2
    assert cues[0].start_ms == 1000
    assert cues[1].end_ms == 9000


def test_negation_and_condition_preserved_verbatim():
    cues = parse_srt(SRT_SAMPLE)
    text = cues_to_plain_text(cues)
    assert "不要直接上大重量" in text
    assert "如果你是新手" in text
    # Chunking must not rewrite the original text
    chunks = chunk_transcript(
        [{"start_ms": c.start_ms, "end_ms": c.end_ms, "text": c.text} for c in cues]
    )
    combined = "\n".join(c.text for c in chunks)
    assert "不要直接上大重量" in combined


def test_transcript_chunks_carry_timestamps():
    chunks = chunk_transcript(
        [{"start_ms": c.start_ms, "end_ms": c.end_ms, "text": c.text} for c in parse_srt(SRT_SAMPLE)]
    )
    assert chunks[0].start_ms == 1000
    assert chunks[-1].end_ms == 14000


def test_chunk_target_size():
    """Chunks aim at ~600 chars and never exceed ~1000 (+overlap)."""
    sentence = "这是一个关于深蹲技术的句子，讲解膝盖轨迹与髋部发力的配合关系。" * 2  # ~60 chars
    segments = [{"start_ms": i * 1000, "end_ms": (i + 1) * 1000, "text": sentence} for i in range(30)]
    chunks = chunk_transcript(segments)
    assert len(chunks) > 1
    for chunk in chunks:
        # overlap sentence may push slightly over target but cap holds
        assert len(chunk.text) <= MAX_CHARS + 200


def test_document_chunks_overlap_last_sentence():
    sentence_group = "第一句话。第二句话内容稍微长一些用来积累字符。第三句话继续增加内容达到分段条件。"
    text = sentence_group * 30  # ~1100 chars → well past the 600-char target
    chunks = chunk_document(text)
    assert len(chunks) > 1
    # The second chunk starts with the previous chunk's last sentence
    assert chunks[1].text.split("\n")[0] in chunks[0].text


def test_annotations_stored_separately():
    chunks = chunk_document(
        "博主讲解了卧推要点。",
        annotations=[{"text": "整理者注：此处应结合自身情况", "tags": ["review"]}],
    )
    annotation_chunks = [c for c in chunks if c.is_annotation]
    assert len(annotation_chunks) == 1
    assert "整理者注" in annotation_chunks[0].text
    assert "整理者注" not in chunks[0].text  # never merged into original


def test_short_transcript_single_chunk():
    chunks = chunk_transcript([{"start_ms": 0, "end_ms": 5000, "text": "短内容"}])
    assert len(chunks) == 1
