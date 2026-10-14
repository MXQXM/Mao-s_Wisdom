import os
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from graphs.state import SourceRetrievalInput, SourceRetrievalOutput

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "bge-m3"
RRF_K = 60          # RRF 融合常数
TOP_N = 10

# 模块级缓存: Chroma collection + 全部分块 (id -> text)
_collection = None
_chunks: Dict[str, str] = {}


def _project_root() -> Path:
    workspace_path = os.getenv("COZE_WORKSPACE_PATH")
    if workspace_path:
        return Path(workspace_path)
    return Path(__file__).resolve().parents[3]


def _tokenize(text: str) -> List[str]:
    terms = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", text)
    return list(dict.fromkeys(terms))


def _load_db() -> Tuple[object, Dict[str, str]]:
    """懒加载 Chroma 集合与全部分块文本(模块级缓存)"""
    global _collection, _chunks
    if _collection is None:
        import chromadb
        db_dir = _project_root() / "assets" / "mao_xuan_db"
        _collection = chromadb.PersistentClient(path=str(db_dir)).get_collection("mao_xuan")
        res = _collection.get(include=["documents"])
        _chunks = dict(zip(res["ids"], res["documents"]))
    return _collection, _chunks


def _embed(text: str) -> Optional[List[float]]:
    """Ollama bge-m3 向量化, 502 冷加载重试(3次退避)"""
    import httpx
    last_err = None
    for attempt in range(3):
        try:
            r = httpx.post(f"{OLLAMA_URL}/api/embed",
                           json={"model": EMBED_MODEL, "input": text}, timeout=180,
                           trust_env=False)   # 不走系统代理(Windows代理会拦localhost->502)
            r.raise_for_status()
            return r.json()["embeddings"][0]
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    print(f"[source_node] embedding 失败: {last_err}")
    return None


def _score_chunk(chunk: str, query_terms: List[str]) -> float:
    """稀疏打分(简化BM25): 命中词 + 词频, 按查询词数归一化"""
    if not query_terms:
        return 0.0
    score = 0.0
    for term in query_terms:
        if term in chunk:
            score += 1.0 + min(chunk.count(term), 3) * 0.2
    return score / len(query_terms)


def _rrf(ranked_lists: List[List[str]], k: int = RRF_K) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion: 多个检索结果按排名融合"""
    scores: Dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


async def source_retrieval_node(state: SourceRetrievalInput) -> SourceRetrievalOutput:
    """
    title: 混合知识库检索
    desc: 用户问题 -> 向量检索(bge-m3+Chroma) + 稀疏检索(词频) -> RRF融合 -> 四卷原文片段
    integrations: 知识库(毛选四卷92万字)
    """
    query_parts: List[str] = [state.user_question]
    if state.selected_themes:
        for theme in state.selected_themes:
            if isinstance(theme, dict):
                name: str = theme.get("name", "")
                if name:
                    query_parts.append(name)
    search_query: str = " ".join(query_parts)
    query_terms = _tokenize(search_query)

    try:
        collection, chunks = _load_db()
    except Exception as e:
        print(f"[source_node] 向量库加载失败: {e}")
        return SourceRetrievalOutput(retrieval_results="知识库加载失败，请确认已运行 scripts/build_knowledge.py 构建向量库。")

    # ---- 1. 向量检索 (bge-m3 + Chroma, 余弦距离) ----
    vec_ranked: List[str] = []
    emb = _embed(search_query)
    if emb:
        try:
            res = collection.query(query_embeddings=[emb], n_results=TOP_N)
            vec_ranked = list(res["ids"][0])
        except Exception as e:
            print(f"[source_node] 向量查询失败: {e}")

    # ---- 2. 稀疏检索 (简化BM25 全量扫描, 排序取前20) ----
    scored: List[Tuple[str, float]] = []
    for doc_id, chunk in chunks.items():
        score = _score_chunk(chunk, query_terms)
        if score > 0:
            scored.append((doc_id, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    sparse_ranked = [doc_id for doc_id, _ in scored[:20]]

    # ---- 3. RRF 融合 ----
    if not vec_ranked and not sparse_ranked:
        return SourceRetrievalOutput(retrieval_results="未在知识库中找到相关检索结果。")

    fused = _rrf([vec_ranked, sparse_ranked])[:TOP_N]

    # ---- 4. 格式化输出 ----
    formatted_parts = []
    for i, (doc_id, score) in enumerate(fused):
        content = _chunks.get(doc_id, "")
        if not content:
            continue
        formatted_parts.append(
            f"--- 检索结果 {i + 1} (相关度: {score:.3f}) ---\n"
            f"{content}\n"
            f"[文档ID: {doc_id}]"
        )
    results_text = "\n\n".join(formatted_parts) if formatted_parts else "未在知识库中找到相关检索结果。"

    return SourceRetrievalOutput(retrieval_results=results_text)
