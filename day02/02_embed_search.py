# -*- coding: utf-8 -*-
"""
Day 2 · 第 2 步：向量化 + 入库 + 检索

════════════════════════════════════════════════════════════
  这一步是 RAG 的核心：
    把文本变成向量 → 存进数据库 → 用问题去检索

  会调用 Embedding 接口（阿里云），有少量费用，但很便宜。
════════════════════════════════════════════════════════════
"""
import sys
import os
import shutil

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv(override=True)          # ⚠️ override=True 很重要，别去掉

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings

API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not API_KEY:
    print("❌ 没有配置 DASHSCOPE_API_KEY")
    raise SystemExit(1)

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE, "docs")
DB_DIR = os.path.join(BASE, "chroma_db")

print("=" * 60)
print("  第 1 步：加载并切分文档")
print("=" * 60)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
)

texts = []          # 所有文本块
metadatas = []      # 每块对应的元数据（来源、块号）

for filename in sorted(os.listdir(DOCS_DIR)):
    if not filename.endswith(".md"):
        continue
    with open(os.path.join(DOCS_DIR, filename), encoding="utf-8") as f:
        content = f.read()
    chunks = splitter.split_text(content)
    for i, c in enumerate(chunks):
        texts.append(c)
        metadatas.append({"source": filename, "chunk_id": i})
    print(f"  {filename}: {len(chunks)} 块")

print(f"\n  合计 {len(texts)} 个块待入库")


# ==================================================================
print()
print("=" * 60)
print("  第 2 步：把文本向量化并存入数据库")
print("=" * 60)

# Embedding 模型：负责把文字转成向量
print("  正在初始化 Embedding 模型...")
embeddings = DashScopeEmbeddings(
    model="text-embedding-v3",          # 阿里云的向量模型
    dashscope_api_key=API_KEY,
)

# 每次写入前清空旧库，保证可重复运行
if os.path.exists(DB_DIR):
    shutil.rmtree(DB_DIR)
    print("  已清空旧的向量库")

print(f"  正在向量化 {len(texts)} 个块（需要联网，约 10-30 秒）...")

# Chroma 是向量数据库，负责存储和检索
vectorstore = Chroma.from_texts(
    texts=texts,
    embedding=embeddings,
    metadatas=metadatas,
    persist_directory=DB_DIR,
)

print(f"  ✅ 入库完成，库中共 {vectorstore._collection.count()} 条向量")


# ==================================================================
print()
print("=" * 60)
print("  第 3 步：检索测试（RAG 的灵魂）")
print("=" * 60)

questions = [
    "连续打卡天数怎么计算？",           # 应该命中「健身小程序需求文档」
    "什么是 RAG？",                     # 应该命中「RAG技术手册」
    "chunk_size 应该设多大？",          # 应该命中「RAG技术手册」
    "勋章有哪些？",                     # 应该命中「健身小程序需求文档」
    "今天股市怎么样？",                 # 应该检索不到（测试无关问题）
]

for q in questions:
    print(f"\n  【问题】{q}")
    print("  " + "-" * 56)
    results = vectorstore.similarity_search_with_score(q, k=3)
    for i, (doc, score) in enumerate(results, 1):
        # Chroma 返回的是"距离"，越小越相似
        preview = doc.page_content.replace("\n", " ")[:70]
        print(f"    {i}. [距离 {score:.4f}] 来源={doc.metadata['source']}")
        print(f"       {preview}...")

print()
print("""
  【要理解的三件事】

  1. 向量是什么？
     一串数字，比如 [0.12, -0.35, 0.88, ...]（通常 1024 个数字）。
     语义相近的文字，它们的向量也相近。
     所以"苹果手机"和"iPhone"的向量距离很近，即使字面上完全不同。

  2. 距离（score）是什么？
     数字越小 = 越相似。上面每条结果都带了距离。
     看第 5 个问题（股市），它的距离明显更大 —— 说明确实不相关。
     这就是"相似度阈值"的依据：距离太大就判定为"没找到相关资料"。

  3. 为什么要带 source？
     每块都记了来自哪个文件。这样答案才能标注出处。
     企业 RAG 的最低要求就是"答案可溯源"。
""")

print("=" * 60)
print("  ✅ 第 2 步完成，下一步：把检索结果喂给大模型生成答案")
print("=" * 60)
