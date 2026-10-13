# -*- coding: utf-8 -*-
"""
Day 3 · 第 3 步：召回质量评估（量化 Rerank 的真实价值）

════════════════════════════════════════════════════════════
  上一步我们发现：只看"答对/答错"，两个方案都是 90%。

  但真正的差异在【答案质量】：
    - 无 Rerank 时，答案可能不完整、跑偏
    - 有 Rerank 时，答案更精准、更全面

  这个脚本用【关键词命中率】来量化这个差异。
  这是更可靠、更客观的评估方式。
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

from dashscope import TextReRank

API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE, "docs_large")   # 大知识库（40个文档）
DB_DIR = os.path.join(BASE, "chroma_db_large")

COARSE_K = 30            # 大知识库下召回更多候选
FINE_K = 4


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
        metadatas.append({"source": filename, "chunk_id": i, "uid": f"{filename}::{i}"})

embeddings = DashScopeEmbeddings(model="text-embedding-v3", dashscope_api_key=API_KEY)
if os.path.exists(DB_DIR):
    shutil.rmtree(DB_DIR)
vectorstore = Chroma.from_texts(texts=texts, embedding=embeddings,
                                metadatas=metadatas, persist_directory=DB_DIR)
print(f"  ✅ 知识库就绪：{len(texts)} 个块")

llm = ChatTongyi(model_name="qwen-turbo", dashscope_api_key=API_KEY, temperature=0)

PROMPT = ChatPromptTemplate.from_template("""请严格根据下面提供的资料回答问题。

【资料】
{context}

【问题】
{question}

【回答要求】
1. 只根据资料回答，不要使用你自己的知识
2. 资料中没有相关信息就说"无法回答"
3. 回答简洁，150 字以内
""")


# ==================================================================
def retrieve(question: str, use_rerank: bool):
    coarse = vectorstore.similarity_search_with_score(question, k=COARSE_K)
    if not use_rerank:
        return coarse[:FINE_K]
    docs = [d.page_content for d, _ in coarse]
    resp = TextReRank.call(model="gte-rerank-v2", query=question, documents=docs,
                           top_n=min(FINE_K, len(docs)), return_documents=False,
                           api_key=API_KEY)
    if resp.status_code != 200:
        return coarse[:FINE_K]
    return [(coarse[it.index][0], coarse[it.index][1]) for it in resp.output.results]


def ask(question: str, use_rerank: bool):
    results = retrieve(question, use_rerank)
    valid = [(d, s) for d, s in results if s <= 1.0]
    if not valid:
        return "根据现有资料无法回答这个问题。"
    context = "\n\n---\n\n".join(f"【{d.metadata['source']}】\n{d.page_content}"
                                 for d, _ in valid)
    return llm.invoke(PROMPT.format_messages(context=context, question=question)).content.strip()


# ==================================================================
# 测试集：每题标注"标准答案必须包含的关键词"
# 命中率 = 答案里出现了几个关键词 / 总关键词数
# ==================================================================
TEST_SET = [
    ("连续打卡天数怎么计算？",
     ["往前推算", "重新计算"]),

    ("如果用户断了一天没打卡，连续记录会怎样？",
     ["往前推算", "重新计算"]),

    ("检索出来的结果不够准，有什么办法改进？",
     ["Rerank", "chunk_size"]),

    ("怎么让回答不瞎编？",
     ["提示词", "出处", "阈值"]),

    ("为什么要用 Rerank？",
     ["精度", "慢"]),

    ("chunk_size 太大会有什么问题？",
     ["主题", "精度"]),

    ("用户登录是怎么实现的？",
     ["openid", "微信"]),

    ("排行榜多久刷新一次？",
     ["10"]),
]

print()
print("=" * 64)
print("  召回质量评估（关键词命中率）")
print("=" * 64)
print("  评估方式：标准答案的关键词，在生成答案里出现了几个")

summary = {"no_rerank": [], "rerank": []}

for q, keywords in TEST_SET:
    print()
    print("─" * 64)
    print(f"  【问题】{q}")
    print(f"  【关键点】{'、'.join(keywords)}")

    row = {}
    for label, use in (("无 Rerank", False), ("有 Rerank", True)):
        ans = ask(q, use)
        hit = [k for k in keywords if k.lower() in ans.lower()]
        rate = len(hit) / len(keywords)
        row[label] = rate
        key = "no_rerank" if label == "无 Rerank" else "rerank"
        summary[key].append(rate)
        mark = "✅" if rate == 1.0 else ("⚠️" if rate > 0 else "❌")
        print(f"\n    [{label}] 命中 {len(hit)}/{len(keywords)} {mark}")
        print(f"       提到：{'、'.join(hit) if hit else '（无）'}")
        print(f"       答案：{ans[:70].replace(chr(10), ' ')}...")

print()
print("=" * 64)
print("  📊 最终评估结果")
print("=" * 64)
n = len(TEST_SET)
print(f"\n  {'方案':<12} {'平均关键词命中率':<18} {'完全命中题数'}")
print(f"  {'-'*52}")
for key, label in (("no_rerank", "无 Rerank"), ("rerank", "有 Rerank")):
    rates = summary[key]
    avg = sum(rates) / len(rates) * 100
    full = sum(1 for r in rates if r == 1.0)
    print(f"  {label:<12} {avg:>14.1f}%   {full:>10}/{n}")

improve = (sum(summary["rerank"]) - sum(summary["no_rerank"])) / len(summary["no_rerank"]) * 100

print()
print("=" * 64)
print(f"  ⭐ Rerank 带来的提升：{improve:+.1f} 个百分点")
print("=" * 64)
print(f"""
  【如何写进简历】

  如果提升为正：
    "构建 {n} 题评估集，以标准答案关键词命中率衡量：
      向量检索平均命中率 {sum(summary['no_rerank'])/n*100:.1f}%，
      引入 Rerank 后提升至 {sum(summary['rerank'])/n*100:.1f}%，
      提升 {improve:.1f} 个百分点"

  如果提升为 0 或负：
    如实写：
    "实测发现小规模知识库（{len(texts)} 块）下 Rerank 增益有限，
      粗排已能满足需求；Rerank 的价值在更大规模候选集上体现"

  ⚠️ 两个都是好答案。
     工程上"知道什么时候不需要某个技术"比"无脑堆技术"更专业。
""")
