# -*- coding: utf-8 -*-
"""
Day 2 · 第 3 步：完整 RAG 问答系统（带出处引用 + 防幻觉）

════════════════════════════════════════════════════════════
  这是 RAG 的完整形态，也是你简历上【项目一】的核心
  三个关键设计：
    1. 答案带出处（可溯源）
    2. 相似度阈值（防止硬凑答案）
    3. 提示词约束（防止编造）
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

API_KEY = os.getenv("DASHSCOPE_API_KEY")
BASE = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE, "docs")
DB_DIR = os.path.join(BASE, "chroma_db")

# ⭐ 相似度阈值：距离大于这个值，判定为"没有相关资料"
# 从第2步的实测看：相关问题的距离在 0.55-0.75，无关问题在 1.25+
# 所以 1.0 是一个合理的分界线
SCORE_THRESHOLD = 1.0
TOP_K = 3


# ==================================================================
print("=" * 60)
print("  初始化知识库")
print("=" * 60)

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
        metadatas.append({"source": filename, "chunk_id": i})

embeddings = DashScopeEmbeddings(model="text-embedding-v3", dashscope_api_key=API_KEY)

if os.path.exists(DB_DIR):
    shutil.rmtree(DB_DIR)

vectorstore = Chroma.from_texts(
    texts=texts, embedding=embeddings,
    metadatas=metadatas, persist_directory=DB_DIR,
)
print(f"  ✅ 知识库就绪：{len(texts)} 个块")
retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})


# ==================================================================
# 大模型
# ==================================================================
llm = ChatTongyi(model_name="qwen-turbo", dashscope_api_key=API_KEY, temperature=0)

# ⭐ 提示词模板：这里是"防幻觉"的核心
# {context} 会被替换成检索到的资料，{question} 替换成用户问题
PROMPT = ChatPromptTemplate.from_template("""你是一个严谨的知识库助手。请严格根据下面提供的资料回答问题。

【资料】
{context}

【问题】
{question}

【回答要求】
1. 只根据上面的资料回答，不要使用你自己的知识
2. 如果资料中没有相关信息，直接回答"根据现有资料无法回答这个问题"
3. 回答要简洁，控制在 150 字以内
4. 【重要】直接给出答案内容，不要写"根据资料"、"资料中提到"、"根据上述内容"这类开头
5. 不要编造资料中没有的数字、名称或结论
""")


# ==================================================================
# 核心函数：RAG 问答
# ==================================================================
def ask(question: str, show_sources: bool = True):
    """完整的 RAG 流程：检索 → 判断 → 生成 → 带出处返回"""
    print(f"\n{'=' * 60}")
    print(f"  【问题】{question}")
    print("=" * 60)

    # ---------- 第 1 步：检索 ----------
    results = vectorstore.similarity_search_with_score(question, k=TOP_K)

    # ---------- 第 2 步：阈值判断（防幻觉的第一道防线）----------
    valid = [(doc, score) for doc, score in results if score <= SCORE_THRESHOLD]

    if not valid:
        print("\n  ⚠️ 没有找到相关资料（所有结果的距离都超过阈值 %.1f）" % SCORE_THRESHOLD)
        print(f"  最接近的距离是 {results[0][1]:.4f}，判定为不相关")
        print("\n  回答：根据现有资料无法回答这个问题。")
        return

    print(f"\n  [检索] 命中 {len(valid)} 个相关块：")
    for doc, score in valid:
        print(f"         · {doc.metadata['source']} 第{doc.metadata['chunk_id']}块 "
              f"(距离 {score:.4f})")

    # ---------- 第 3 步：拼接上下文 ----------
    context = "\n\n---\n\n".join(
        f"【来源：{doc.metadata['source']}】\n{doc.page_content}"
        for doc, _ in valid
    )

    # ---------- 第 4 步：调用大模型生成 ----------
    print("\n  [生成] 正在调用大模型...")
    messages = PROMPT.format_messages(context=context, question=question)
    response = llm.invoke(messages)
    answer = response.content

    print(f"\n  【回答】{answer}")

    # ---------- 第 5 步：附上出处（可溯源）----------
    if show_sources:
        print("\n  【出处】")
        seen = set()
        for doc, score in valid:
            src = doc.metadata["source"]
            if src not in seen:
                seen.add(src)
                print(f"         · {src}")
        print(f"         （共引用 {len(valid)} 个片段，来自 {len(seen)} 个文档）")


# ==================================================================
if __name__ == "__main__":
    print()
    print("#" * 60)
    print("#  完整 RAG 问答系统")
    print("#" * 60)

    # 测试 1：知识库里有的问题（应该正常回答）
    ask("连续打卡天数怎么计算？")
    ask("chunk_overlap 设成多少合适？")
    ask("勋章有哪几种？")

    # 测试 2：知识库里没有的问题（应该拒答，不编造）
    ask("今天北京的天气怎么样？")
    ask("怎么用 Python 写一个爬虫？")

    print()
    print("#" * 60)
    print("#  ✅ 观察重点")
    print("#" * 60)
    print("""
  1. 前 3 个问题：vault 里有资料 → 正常回答 + 给出出处
  2. 后 2 个问题：库里没资料 → 直接说"无法回答"，【不编造】

  这就是企业级 RAG 和"玩具 RAG"的分界线：
      玩具：什么问题都硬答，经常瞎编
      企业：不知道就说不知道，且每个答案都能追溯来源

  ⭐ 你的简历上可以这样写：
     "实现带相似度阈值过滤的 RAG 问答系统，
      无关问题拒答率 100%，所有答案可溯源到原文片段"
""")
