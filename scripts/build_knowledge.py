#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
毛选四卷知识库构建脚本
用法: python build_knowledge.py

流程: 四卷 TXT(92万字) -> 按空行段落分块(700字/120重叠, 与 source_node 对齐)
      -> Ollama bge-m3 embedding -> Chroma 持久化 (assets/mao_xuan_db)
"""
import re
import sys
import time
import httpx
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "bge-m3"
CHUNK_SIZE = 700
OVERLAP = 120
DB_DIR = Path(__file__).resolve().parent.parent / "assets" / "mao_xuan_db"
COLLECTION = "mao_xuan"

VOLUMES = [
    ("第一卷", r"C:\Users\12935\.hermes\output\毛泽东选集第一卷_文字版.txt"),
    ("第二卷", r"C:\Users\12935\.hermes\output\毛泽东选集第二卷_文字版.txt"),
    ("第三卷", r"C:\Users\12935\.hermes\output\毛泽东选集第三卷_文字版.txt"),
    ("第四卷", r"C:\Users\12935\.hermes\output\毛泽东选集第四卷_文字版.txt"),
]


def split_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list:
    """与 Jy_demo source_node._split_chunks 对齐: 按空行分段, 700字/120重叠"""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) <= chunk_size:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            current = paragraph[-chunk_size:] if len(paragraph) > chunk_size else paragraph
    if current:
        chunks.append(current)
    # 超长段滑动展开(与 source_node 一致)
    expanded = []
    for chunk in chunks:
        if len(chunk) <= chunk_size:
            expanded.append(chunk)
            continue
        start = 0
        while start < len(chunk):
            expanded.append(chunk[start:start + chunk_size])
            start += max(1, chunk_size - overlap)
    return expanded


def embed_batch(client: httpx.Client, texts: list) -> list:
    """调用 Ollama /api/embed 批量向量化 (bge-m3, 1024维), 502冷加载重试"""
    last_err = None
    for attempt in range(3):
        try:
            r = client.post(f"{OLLAMA_URL}/api/embed",
                            json={"model": EMBED_MODEL, "input": texts}, timeout=600)
            r.raise_for_status()
            return r.json()["embeddings"]
        except Exception as e:
            last_err = e
            time.sleep(3 * (attempt + 1))   # 3s/6s 退避(模型冷加载资源竞争)
    raise RuntimeError(f"embedding 失败: {last_err}")


def main():
    # 1. 读取并分块
    all_chunks, all_meta = [], []
    for vol, path in VOLUMES:
        p = Path(path)
        if not p.exists():
            print(f"跳过: {path} 不存在")
            continue
        text = p.read_text(encoding="utf-8")
        chunks = split_chunks(text)
        all_chunks.extend(chunks)
        all_meta.extend([{"卷": vol, "序号": i} for i in range(len(chunks))])
        print(f"[{vol}] {len(chunks)} 块")
    print(f"合计 {len(all_chunks)} 块")

    # 2. 批量 embedding
    client = httpx.Client(trust_env=False)   # 不走系统代理(Windows代理会拦localhost->502)
    embeddings, B = [], 16
    t0 = time.time()
    for i in range(0, len(all_chunks), B):
        batch = all_chunks[i:i + B]
        emb = embed_batch(client, batch)
        embeddings.extend(emb)
        print(f"  embedding {min(i + B, len(all_chunks))}/{len(all_chunks)} "
              f"({time.time() - t0:.0f}s)", flush=True)
    print(f"embedding 完成, 共 {len(embeddings)} 条, 维度 {len(embeddings[0])}")

    # 3. 写入 Chroma
    import chromadb
    client_db = chromadb.PersistentClient(path=str(DB_DIR))
    try:
        client_db.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client_db.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    # 按卷生成 ids (v1..v4)
    vol_ids = []
    idx = 0
    for vi, (vol, path) in enumerate(VOLUMES):
        p = Path(path)
        if not p.exists():
            continue
        n = len(split_chunks(p.read_text(encoding="utf-8")))
        vol_ids.extend(f"v{vi + 1}_c{j}" for j in range(n))
        idx += n
    ids = vol_ids[:len(all_chunks)]
    col.add(ids=ids, documents=all_chunks, metadatas=all_meta, embeddings=embeddings)
    print(f"Chroma 写入完成: {col.count()} 条 -> {DB_DIR}")
    print("知识库构建完成 ✅")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
