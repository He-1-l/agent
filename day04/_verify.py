# -*- coding: utf-8 -*-
"""核心逻辑验证脚本（放在 day04 目录下运行）"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"), override=True)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from dashscope import TextReRank

key = os.getenv("DASHSCOPE_API_KEY")
print("1. API Key:", ("OK " + key[:10] + "..." + key[-4:]) if key else "缺失")
if not key:
    raise SystemExit(1)

docs = {}
docs_dir = os.path.join(BASE, "docs")
for f in os.listdir(docs_dir):
    if f.endswith((".md", ".txt")):
        docs[f] = open(os.path.join(docs_dir, f), encoding="utf-8").read()
print(f"2. 加载文档: {len(docs)} 个")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=300, chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
)
texts, metas = [], []
for fn, c in docs.items():
    for i, ch in enumerate(splitter.split_text(c)):
        texts.append(ch)
        metas.append({"source": fn, "chunk_id": i})
print(f"3. 切分: {len(texts)} 块")

emb = DashScopeEmbeddings(model="text-embedding-v3", dashscope_api_key=key)
vs = Chroma.from_texts(texts=texts, embedding=emb, metadatas=metas)
print(f"4. 向量库: {vs._collection.count()} 条")

for q in ["勋章有哪几种？", "今天天气怎么样？"]:
    print(f"\n--- 问题: {q} ---")
    coarse = vs.similarity_search_with_score(q, k=15)
    resp = TextReRank.call(
        model="gte-rerank-v2", query=q,
        documents=[d.page_content for d, _ in coarse],
        top_n=4, return_documents=False, api_key=key,
    )
    valid = [(coarse[it.index][0], coarse[it.index][1]) for it in resp.output.results]
    valid = [(d, s) for d, s in valid if s <= 1.0]

    if not valid:
        print("   → 拒答（超过阈值）")
        continue

    ctx = "\n\n---\n\n".join(f"【{d.metadata['source']}】\n{d.page_content}"
                             for d, _ in valid)
    llm = ChatTongyi(model_name="qwen-turbo", dashscope_api_key=key, temperature=0)
    P = ChatPromptTemplate.from_template(
        "只根据资料回答，200字内，直接给答案。\n资料:{context}\n问题:{question}")
    ans = llm.invoke(P.format_messages(context=ctx, question=q))
    print(f"   → {ans.content.strip()[:70]}")

print("\n✅ 应用核心逻辑全部正常")
