# -*- coding: utf-8 -*-
"""
Day 4 · RAG 知识库问答系统 · Web 界面

════════════════════════════════════════════════════════════
  用 Streamlit 给 RAG 做一个可视化界面，功能包括：
    ① 上传文档（txt / md）
    ② 参数调节（chunk_size、Top-K、阈值）
    ③ 对话式问答
    ④ 显示检索到的原文片段（可溯源）
    ⑤ 显示相似度距离（可解释）
════════════════════════════════════════════════════════════

运行：双击 run_app.bat
浏览器会自动打开 http://localhost:8501
"""
import sys
import os
import time

sys.stdout.reconfigure(encoding="utf-8")

import streamlit as st

from dotenv import load_dotenv

# ⚠️ 关键：显式指定 .env 的绝对路径
# load_dotenv() 默认只找【当前工作目录】，如果从别处启动脚本就找不到配置。
# 用 __file__ 定位到 app.py 所在目录，保证在任何位置启动都能读到 .env。
BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"), override=True)

# ⚠️ 关键：禁用系统代理
# Python 的 requests 库会自动读取 Windows 系统代理设置。
# 如果系统里残留了一个失效的代理（比如代理软件关闭后没关掉开关），
# 所有 API 请求都会发到那个死代理上，报 ProxyError。
# 这里强制清空代理相关环境变量，让请求直连。
for _var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
             "ALL_PROXY", "all_proxy"):
    os.environ.pop(_var, None)
os.environ["NO_PROXY"] = "*"

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate

from dashscope import TextReRank

# ==================================================================
# 页面配置
# ==================================================================
st.set_page_config(
    page_title="智能知识库问答",
    page_icon="📚",
    layout="wide",
)

DOCS_DIR = os.path.join(BASE, "docs")
API_KEY = os.getenv("DASHSCOPE_API_KEY")


# ==================================================================
# 核心逻辑（带缓存，避免每次交互都重新初始化）
# ==================================================================
@st.cache_resource(show_spinner=False)
def load_models():
    """加载 Embedding 和 LLM 模型（只初始化一次）"""
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v3", dashscope_api_key=API_KEY
    )
    llm = ChatTongyi(model_name="qwen-turbo", dashscope_api_key=API_KEY, temperature=0)
    return embeddings, llm


def build_vectorstore(docs: dict, chunk_size: int, chunk_overlap: int, embeddings):
    """根据文档和参数构建向量库"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
    )
    texts, metadatas = [], []
    for filename, content in docs.items():
        for i, c in enumerate(splitter.split_text(content)):
            texts.append(c)
            metadatas.append({"source": filename, "chunk_id": i})

    if not texts:
        return None, 0

    vs = Chroma.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)
    return vs, len(texts)


def rerank(question: str, candidates: list, top_n: int):
    """Rerank 精排"""
    if not candidates:
        return []
    docs = [d.page_content for d, _ in candidates]
    resp = TextReRank.call(
        model="gte-rerank-v2", query=question, documents=docs,
        top_n=min(top_n, len(docs)), return_documents=False, api_key=API_KEY,
    )
    if resp.status_code != 200:
        return [(d, s, None) for d, s in candidates[:top_n]]
    return [(candidates[it.index][0], candidates[it.index][1], it.relevance_score)
            for it in resp.output.results]


PROMPT = ChatPromptTemplate.from_template("""你是一个严谨的知识库助手。请严格根据下面提供的资料回答问题。

【资料】
{context}

【问题】
{question}

【回答要求】
1. 只根据上面的资料回答，不要使用你自己的知识
2. 如果资料中没有相关信息，回答"根据现有资料无法回答这个问题"
3. 回答简洁，200 字以内
4. 直接给出答案，不要写"根据资料"这类开头
""")


# ==================================================================
# 侧边栏：参数配置
# ==================================================================
with st.sidebar:
    st.header("⚙️ 参数配置")

    st.subheader("文档切分")
    chunk_size = st.slider("chunk_size", 100, 1000, 300, 50,
                           help="每块最大字符数。太大则一块混多主题，太小则语义不完整")
    chunk_overlap = st.slider("chunk_overlap", 0, 200, 50, 10,
                              help="相邻块重叠字符数，防止句子被切断")

    st.subheader("检索")
    coarse_k = st.slider("粗排召回数 (K)", 5, 50, 15, 5,
                         help="向量检索先召回多少个候选")
    fine_k = st.slider("精排保留数", 1, 10, 4, 1,
                       help="Rerank 后保留多少个给模型")
    threshold = st.slider("相似度阈值", 0.5, 1.5, 1.0, 0.05,
                          help="距离超过此值判定为不相关，直接拒答")

    use_rerank = st.toggle("启用 Rerank 精排", value=True,
                           help="两阶段检索：粗排召回 + 精排精选")

    st.divider()
    st.subheader("📄 文档管理")

    uploaded = st.file_uploader(
        "上传文档（txt / md）", type=["txt", "md"], accept_multiple_files=True
    )

    st.caption(f"内置文档：{', '.join(os.listdir(DOCS_DIR)) if os.path.exists(DOCS_DIR) else '无'}")


# ==================================================================
# 主区域
# ==================================================================
st.title("📚 智能知识库问答系统")
st.caption("基于 LangChain + 通义千问 + ChromaDB，支持答案溯源与无关问题拒答")

if not API_KEY:
    st.error("❌ 未配置 DASHSCOPE_API_KEY，请检查 .env 文件")
    st.stop()

# ---------- 组装文档 ----------
docs = {}

# 内置文档
if os.path.exists(DOCS_DIR):
    for f in sorted(os.listdir(DOCS_DIR)):
        if f.endswith((".md", ".txt")):
            with open(os.path.join(DOCS_DIR, f), encoding="utf-8") as fh:
                docs[f] = fh.read()

# 用户上传的文档
if uploaded:
    for uf in uploaded:
        try:
            docs[uf.name] = uf.read().decode("utf-8")
        except Exception as e:
            st.warning(f"读取 {uf.name} 失败：{e}")

if not docs:
    st.warning("⚠️ 没有可用文档，请上传或在 docs 目录放入文档")
    st.stop()

# ---------- 构建向量库 ----------
with st.spinner("正在构建知识库..."):
    embeddings, llm = load_models()
    # 参数变化时重建
    cache_key = (tuple(docs.keys()), chunk_size, chunk_overlap)
    if st.session_state.get("vs_key") != cache_key:
        vs, n_chunks = build_vectorstore(docs, chunk_size, chunk_overlap, embeddings)
        st.session_state["vs"] = vs
        st.session_state["vs_key"] = cache_key
        st.session_state["n_chunks"] = n_chunks
        st.session_state["messages"] = []
    else:
        vs = st.session_state["vs"]
        n_chunks = st.session_state["n_chunks"]

# ---------- 状态展示 ----------
c1, c2, c3 = st.columns(3)
c1.metric("文档数", len(docs))
c2.metric("文本块数", n_chunks)
c3.metric("检索模式", "粗排+精排" if use_rerank else "仅粗排")

st.divider()

# ---------- 对话历史 ----------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("meta"):
            with st.expander("🔍 查看检索详情"):
                st.markdown(msg["meta"])


# ---------- 提问 ----------
question = st.chat_input("请输入你的问题...")

if question:
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        t0 = time.time()

        # 1. 粗排
        coarse = vs.similarity_search_with_score(question, k=coarse_k)
        t_coarse = time.time() - t0

        # 2. 精排
        if use_rerank:
            t1 = time.time()
            ranked = rerank(question, coarse, fine_k)
            t_fine = time.time() - t1
        else:
            ranked = [(d, s, None) for d, s in coarse[:fine_k]]
            t_fine = 0

        # 3. 阈值过滤
        valid = [(d, s, r) for d, s, r in ranked if s <= threshold]

        if not valid:
            answer = "根据现有资料无法回答这个问题。"
            st.warning(f"⚠️ 未找到相关资料（最相似距离 {ranked[0][1]:.4f} > 阈值 {threshold}）")
            st.write(answer)
            meta = None
        else:
            # 4. 生成
            context = "\n\n---\n\n".join(
                f"【来源：{d.metadata['source']}】\n{d.page_content}"
                for d, _, _ in valid
            )
            resp = llm.invoke(PROMPT.format_messages(context=context, question=question))
            answer = resp.content.strip()
            st.write(answer)

            # 5. 出处
            sources = sorted({d.metadata["source"] for d, _, _ in valid})
            st.caption(f"📎 出处：{'、'.join(sources)}　|　"
                       f"检索耗时 {t_coarse*1000:.0f}ms + {t_fine*1000:.0f}ms")

            # 6. 检索详情（可展开）
            lines = [f"**粗排召回 {len(coarse)} 个，精排保留 {len(valid)} 个**\n"]
            lines.append("| 排名 | 来源 | 片段 | 向量距离 | Rerank分 |")
            lines.append("|---|---|---|---|---|")
            for i, (d, s, r) in enumerate(valid, 1):
                preview = d.page_content.replace("\n", " ")[:36]
                rs = f"{r:.4f}" if r is not None else "—"
                lines.append(f"| {i} | {d.metadata['source']} | {preview}... | {s:.4f} | {rs} |")
            meta = "\n".join(lines)
            with st.expander("🔍 查看检索详情"):
                st.markdown(meta)

    st.session_state["messages"].append(
        {"role": "assistant", "content": answer, "meta": meta}
    )

# ---------- 侧边栏底部：清空 ----------
with st.sidebar:
    st.divider()
    if st.button("🗑️ 清空对话"):
        st.session_state["messages"] = []
        st.rerun()
