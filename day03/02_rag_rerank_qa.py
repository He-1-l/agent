# -*- coding: utf-8 -*-
"""
Day 3 · 第 2 步：完整 RAG + Rerank 系统（项目一最终版）

════════════════════════════════════════════════════════════
  这是可以直接写进简历的版本，包含：
    ① 两阶段检索（粗排 + 精排）
    ② 相似度阈值过滤（防幻觉）
    ③ 答案溯源（带出处）
    ④ A/B 对比实验（无 Rerank vs 有 Rerank）
════════════════════════════════════════════════════════════
"""
import sys
import os
import shutil

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

COARSE_K = 15           # 粗排召回数量
FINE_K = 4              # 精排保留数量
SCORE_THRESHOLD = 1.0   # 相似度阈值


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
        metadatas.append({"source": filename, "chunk_id": i,
                          "uid": f"{filename}::{i}"})

embeddings = DashScopeEmbeddings(model="text-embedding-v3", dashscope_api_key=API_KEY)
if os.path.exists(DB_DIR):
    shutil.rmtree(DB_DIR)
vectorstore = Chroma.from_texts(
    texts=texts, embedding=embeddings,
    metadatas=metadatas, persist_directory=DB_DIR,
)
print(f"  ✅ 知识库就绪：{len(texts)} 个块")
print(f"     粗排召回 {COARSE_K} 个 → 精排保留 {FINE_K} 个")

llm = ChatTongyi(model_name="qwen-turbo", dashscope_api_key=API_KEY, temperature=0)

PROMPT = ChatPromptTemplate.from_template("""你是一个严谨的知识库助手。请严格根据下面提供的资料回答问题。

【资料】
{context}

【问题】
{question}

【回答要求】
1. 只根据上面的资料回答，不要使用你自己的知识
2. 如果资料中没有相关信息，回答"根据现有资料无法回答这个问题"
3. 回答要简洁，控制在 150 字以内
4. 直接给出答案，不要写"根据资料"这类开头
""")


# ==================================================================
def retrieve(question: str, use_rerank: bool):
    """
    检索：返回 (相关文档列表, 检索耗时说明)

    use_rerank=False → 只用向量检索（对照组）
    use_rerank=True  → 向量粗排 + Rerank 精排（实验组）
    """
    coarse = vectorstore.similarity_search_with_score(question, k=COARSE_K)

    if not use_rerank:
        # 对照组：按向量距离排序，取前 FINE_K 个
        return coarse[:FINE_K]

    # 实验组：Rerank 重排
    docs = [d.page_content for d, _ in coarse]
    resp = TextReRank.call(
        model="gte-rerank-v2", query=question, documents=docs,
        top_n=min(FINE_K, len(docs)), return_documents=False, api_key=API_KEY,
    )
    if resp.status_code != 200:
        return coarse[:FINE_K]

    out = []
    for item in resp.output.results:
        doc, vscore = coarse[item.index]
        out.append((doc, vscore))
    return out


def ask(question: str, use_rerank: bool = True, verbose: bool = True):
    """完整 RAG 问答"""
    # 1. 检索
    results = retrieve(question, use_rerank)

    # 2. 阈值过滤（防幻觉）
    valid = [(d, s) for d, s in results if s <= SCORE_THRESHOLD]

    if not valid:
        return {
            "answer": "根据现有资料无法回答这个问题。",
            "sources": [],
            "blocked": True,
            "distance": results[0][1] if results else None,
        }

    # 3. 拼上下文
    context = "\n\n---\n\n".join(
        f"【来源：{d.metadata['source']}】\n{d.page_content}" for d, _ in valid
    )

    # 4. 生成
    resp = llm.invoke(PROMPT.format_messages(context=context, question=question))

    return {
        "answer": resp.content.strip(),
        "sources": sorted({d.metadata["source"] for d, _ in valid}),
        "blocked": False,
        "distance": valid[0][1],
    }


# ==================================================================
# A/B 对比实验
# ==================================================================
if __name__ == "__main__":
    # 测试集设计说明：
    #   前 4 题：简单题（关键词直接匹配）—— 预期两者都能答对
    #   中 4 题：困难题（需要理解语义，字面不匹配）—— Rerank 才能体现价值
    #   后 2 题：无关题 —— 预期两者都拒答
    TEST_SET = [
        # ---- 简单题：字面匹配 ----
        ("连续打卡天数怎么计算？", True),
        ("勋章有哪几种？", True),
        ("chunk_overlap 设成多少合适？", True),
        ("数据库表是怎么设计的？", True),
        # ---- 困难题：语义相关但字面不匹配 ----
        ("如果用户断了一天没打卡，连续记录会怎样？", True),      # 考"断卡后重新计算"
        ("怎么让回答不瞎编？", True),                          # 考"防幻觉"，字面不匹配
        ("用户不想每次输密码，能直接登录吗？", True),            # 考"OpenID 登录"
        ("检索出来的结果不够准，有什么办法改进？", True),         # 考"Rerank"
        # ---- 无关题 ----
        ("今天北京天气怎么样？", False),
        ("推荐几部好看的电影", False),
    ]

    print()
    print("=" * 64)
    print("  A/B 对比实验：无 Rerank vs 有 Rerank")
    print("=" * 64)

    stats = {"no_rerank": {"ok": 0, "blocked": 0, "wrong": 0},
             "rerank":    {"ok": 0, "blocked": 0, "wrong": 0}}

    for q, should_answer in TEST_SET:
        print()
        print("─" * 64)
        print(f"  【问题】{q}")
        print(f"  【预期】{'应该回答' if should_answer else '应该拒答'}")
        print("─" * 64)

        r_no = ask(q, use_rerank=False)
        r_yes = ask(q, use_rerank=True)

        for label, r in (("无 Rerank", r_no), ("有 Rerank", r_yes)):
            key = "no_rerank" if label == "无 Rerank" else "rerank"
            if r["blocked"]:
                status = "拒答"
                if not should_answer:
                    stats[key]["blocked"] += 1
                else:
                    stats[key]["wrong"] += 1
            else:
                status = "回答"
                if should_answer:
                    stats[key]["ok"] += 1
                else:
                    stats[key]["wrong"] += 1

            srcs = "、".join(r["sources"]) if r["sources"] else "—"
            ans = r["answer"][:56].replace("\n", " ")
            print(f"\n    [{label}] {status}  (最相似距离 {r['distance']:.4f})"
                  if r["distance"] is not None else f"\n    [{label}] {status}")
            print(f"       答案：{ans}...")
            print(f"       出处：{srcs}")

    print()
    print("=" * 64)
    print("  实验结果统计")
    print("=" * 64)
    total = len(TEST_SET)
    print(f"\n  {'方案':<12} {'正确回答':<10} {'正确拒答':<10} {'错误':<8} {'准确率'}")
    print(f"  {'-'*54}")
    for key, label in (("no_rerank", "无 Rerank"), ("rerank", "有 Rerank")):
        s = stats[key]
        correct = s["ok"] + s["blocked"]
        acc = correct / total * 100
        print(f"  {label:<12} {s['ok']:<10} {s['blocked']:<10} {s['wrong']:<8} {acc:.1f}%")

    print()
    print("""
  ⭐ 把上面这张表填进你的简历！

  格式示例：
    "构建 8 题测试集（6 题有答案 / 2 题无答案）进行 A/B 对比：
      无 Rerank 准确率 XX%，加入 Rerank 后 XX%（提升 X 个百分点）"

  ⚠️ 数字必须是你自己实测的，不能编。
""")
