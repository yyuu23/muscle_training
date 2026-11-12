"""
RRF fusion tests (plan §7.9): k=60 math, multi-source ranking,
near-duplicate removal, empty inputs.
"""

from app.rag.fusion import FusedItem, dedupe_chunks, jaccard_similarity, rrf_fuse


def test_rrf_math_single_source():
    items = rrf_fuse({"keyword": ["a", "b", "c"]})
    # Only source: rank 1 → 1/(60+1), rank 2 → 1/62, rank 3 → 1/63
    scores = {i.chunk_id: i.rrf_score for i in items}
    assert abs(scores["a"] - 1 / 61) < 1e-9
    assert abs(scores["b"] - 1 / 62) < 1e-9
    assert items[0].chunk_id == "a"  # best first


def test_rrf_both_sources_beats_single():
    items = rrf_fuse({"keyword": ["a", "b"], "vector": ["b", "a"]})
    # both found by both sources → higher than a single-source hit
    single = rrf_fuse({"keyword": ["a", "b", "x"], "vector": ["b", "a", "y"]})
    both_ids = [i.chunk_id for i in items]
    x_score = next(i.rrf_score for i in single if i.chunk_id == "x")
    ab_scores = [i.rrf_score for i in single if i.chunk_id in ("a", "b")]
    assert all(score > x_score for score in ab_scores)
    assert both_ids == ["a", "b"]


def test_rrf_best_rank_tracked():
    items = rrf_fuse({"keyword": ["a", "b", "c"], "vector": ["c", "a"]})
    by_id = {i.chunk_id: i for i in items}
    assert by_id["a"].best_rank == 1  # rank1 keyword, rank2 vector
    assert by_id["a"].sources == ["keyword", "vector"]


def test_rrf_empty_inputs():
    assert rrf_fuse({}) == []
    assert rrf_fuse({"keyword": []}) == []


def test_dedupe_keeps_higher_ranked():
    items = [
        FusedItem(chunk_id="t1", rrf_score=0.03, best_rank=1),
        FusedItem(chunk_id="t2", rrf_score=0.02, best_rank=2),
    ]
    kept = dedupe_chunks(
        items,
        lambda cid: {"t1": "深蹲时膝盖不要内扣，保持与脚尖方向一致", "t2": "深蹲时膝盖不要内扣，保持与脚尖方向一致"}[cid],
        threshold=0.5,
    )
    assert [k.chunk_id for k in kept] == ["t1"]


def test_deduke_different_texts_kept():
    items = [
        FusedItem(chunk_id="t1", rrf_score=0.03, best_rank=1),
        FusedItem(chunk_id="t2", rrf_score=0.02, best_rank=2),
    ]
    kept = dedupe_chunks(
        items,
        lambda cid: {"t1": "卧推的握距与杠铃轨迹", "t2": "硬拉的起始位置与髋部铰链"}[cid],
        threshold=0.5,
    )
    assert len(kept) == 2


def test_jaccard_similarity_bounds():
    assert jaccard_similarity("完全相同的文本", "完全相同的文本") == 1.0
    assert jaccard_similarity("甲乙丙丁", "子丑寅卯") == 0.0
