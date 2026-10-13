# -*- coding: utf-8 -*-
"""
Day 3 · 第 1 步：给 RAG 加上 Rerank 重排

════════════════════════════════════════════════════════════
  今天要解决的问题：
    向量检索（粗排）有时不准。
    它能找到"字面相似"的内容，但抓不住"语义真正相关"的内容。

  Rerank 的作用：
    用更精细的模型，对粗排召回的候选重新打分排序。

  两阶段检索：
    粗排（向量）：快，从全库召回 20 个候选
    精排（Rerank）：慢但准，从 20 个里精选 5 个
════════════════════════════════════════════════════════════
"""
import sys
import os
import shutil
import time

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(override=True)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate

import dashscope
from dashscope import TextReRank

API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE, "docs")
DB_DIR = os.path.join(BASE, "chroma_db")

# 两阶段检索的参数
COARSE_K = 15          # 粗排：从向量库召回 15 个候选
FINE_K = 5             # 精排：Rerank 后保留 5 个
SCORE_THRESHOLD = 1.0  # 向量距离阈值（粗排用）


# ==================================================================
# 初始化知识库
# ==================================================================
print("=" * 64)
print("  初始化知识库")
print("=" * 64)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300, chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
)

texts, metadatas = [], []
for filename in sorted(os.listdir(DOCS_DIR)):
    if not filename.endswith(".md"):
        continue
    with open(os.path.join(DOCS_DIR, filename), encoding="utf-8") as f:
        content = f.read()
    for i, c in enumerate(splitter.split_text(content)):
        texts.append(c)
        # uid 保证全局唯一，避免不同文件的 chunk_id 冲突
        metadatas.append({
            "source": filename,
            "chunk_id": i,
            "uid": f"{filename}::{i}",
        })

embeddings = DashScopeEmbeddings(model="text-embedding-v3", dashscope_api_key=API_KEY)

if os.path.exists(DB_DIR):
    shutil.rmtree(DB_DIR)

vectorstore = Chroma.from_texts(
    texts=texts, embedding=embeddings,
    metadatas=metadatas, persist_directory=DB_DIR,
)
print(f"  ✅ 知识库就绪：{len(texts)} 个块")


# ==================================================================
# Rerank 函数
# ==================================================================
def rerank(question: str, candidates: list, top_n: int = FINE_K):
    """
    对候选文档重新打分排序

    candidates: [(document, vector_score), ...]
    返回: [(document, vector_score, rerank_score), ...] 按 rerank 分降序
    """
    if not candidates:
        return []

    docs = [doc.page_content for doc, _ in candidates]

    resp = TextReRank.call(
        model="gte-rerank-v2",
        query=question,
        documents=docs,
        top_n=min(top_n, len(docs)),
        return_documents=False,
        api_key=API_KEY,
    )

    if resp.status_code != 200:
        print(f"  ⚠️ Rerank 调用失败 ({resp.status_code})，降级为只用向量检索")
        return [(doc, score, None) for doc, score in candidates[:top_n]]

    # DashScope 返回的 results 已按 relevance_score 降序
    results = []
    for item in resp.output.results:
        idx = item.index
        doc, vscore = candidates[idx]
        results.append((doc, vscore, item.relevance_score))
    return results


# ==================================================================
# 对比测试
# ==================================================================
questions = [
    "连续打卡天数怎么计算？",
    "chunk_overlap 设成多少合适？",
    "勋章有哪几种？",
    "为什么要防止模型编造答案？",
    "数据库表是怎么设计的？",
]

print()
print("=" * 64)
print("  粗排 vs 精排 对比实验")
print("=" * 64)
print(f"  粗排参数：向量库召回首 {COARSE_K} 个")
print(f"  精排参数：Rerank 精选前 {FINE_K} 个")

for q in questions:
    print()
    print("─" * 64)
    print(f"  【问题】{q}")
    print("─" * 64)

    # ---------- 粗排：向量检索 ----------
    t0 = time.time()
    coarse = vectorstore.similarity_search_with_score(q, k=COARSE_K)
    t_coarse = time.time() - t0

    print(f"\n  ▸ 粗排（向量检索，耗时 {t_coarse*1000:.0f}ms）Top-5：")
    for i, (doc, score) in enumerate(coarse[:5], 1):
        preview = doc.page_content.replace("\n", " ")[:52]
        print(f"      {i}. [距离 {score:.4f}] {doc.metadata['source'][:12]}")
        print(f"         {preview}...")

    # ---------- 精排：Rerank ----------
    t0 = time.time()
    fine = rerank(q, coarse, top_n=FINE_K)
    t_fine = time.time() - t0

    print(f"\n  ▸ 精排（Rerank，耗时 {t_fine*1000:.0f}ms）Top-5：")
    for i, (doc, vscore, rscore) in enumerate(fine, 1):
        r = f"{rscore:.4f}" if rscore is not None else "N/A"
        preview = doc.page_content.replace("\n", " ")[:52]
        print(f"      {i}. [重排分 {r}] (原距离 {vscore:.4f}) {doc.metadata['source'][:12]}")
        print(f"         {preview}...")

    # ---------- 排序差异分析 ----------
    # 用 uid 做比较，避免不同文件的 chunk_id 混淆
    coarse_order = [doc.metadata["uid"].split("::")[1] for doc, _ in coarse[:FINE_K]]
    fine_order = [doc.metadata["uid"].split("::")[1] for doc, _, _ in fine]
    if coarse_order != fine_order:
        print(f"\n  ⚡ 排序发生变化：粗排 {coarse_order} → 精排 {fine_order}")
    else:
        print(f"\n  ✓ 排序一致")

print()
print("=" * 64)
print("  ✅ 观察重点")
print("=" * 64)
print("""
  1. 粗排和精排的排序一样吗？
     - 不一样的地方，就是 Rerank 发挥价值的地方
     - 向量检索看"字面/语义相似"，Rerank 看"真正能不能回答问题"

  2. 耗时对比
     - Rerank 明显更慢（几百毫秒 vs 几十毫秒）
     - 所以不能全库都用 Rerank，只能"粗排召回 + 精排精选"

  3. 这就是工业界的标准做法
     粗排（快、召回多）→ 精排（慢、精度高）→ Top-K 喂给模型

  ⭐ 简历可以这样写：
     "设计两阶段检索：向量粗排召回 15 个候选，
      Rerank 精排精选 5 个，提升检索精度"
""")
