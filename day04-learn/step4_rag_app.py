# -*- coding: utf-8 -*-
"""
第 4 步：把 RAG 逻辑接进界面（最后一步）

════════════════════════════════════════════════════════════
  前 3 步你学会了：
    ① 代码 = 网页（st.title / st.write）
    ② 输入控件（text_input / slider / button）
    ③ session_state 保存历史

  这一步把它们组合起来，接上真正的 RAG 逻辑。

  ⚠️ 这一步代码较长，但都是一步步拼起来的。
     我给了完整的"检索+生成"函数，你需要补的是"界面怎么调它们"。

  运行：双击 run_step4.bat
════════════════════════════════════════════════════════════
"""
import sys
import os
import time

sys.stdout.reconfigure(encoding="utf-8")

# ---- 清除代理（否则 API 请求会走死代理）----
for _v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(_v, None)
os.environ["NO_PROXY"] = "*"

import streamlit as st
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"), override=True)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate

# ==================================================================
# 下面这段是"逻辑层"，你不用改，理解即可
# ==================================================================
API_KEY = os.getenv("DASHSCOPE_API_KEY")
DOCS_DIR = os.path.join(BASE, "docs")


@st.cache_resource(show_spinner=False)
def load_models():
    """加载模型（@st.cache_resource 让它们只初始化一次，不重复加载）"""
    emb = DashScopeEmbeddings(model="text-embedding-v3", dashscope_api_key=API_KEY)
    llm = ChatTongyi(model_name="qwen-turbo", dashscope_api_key=API_KEY, temperature=0)
    return emb, llm


def load_documents():
    """读取 docs 目录下所有文档"""
    docs = {}
    if os.path.exists(DOCS_DIR):
        for f in sorted(os.listdir(DOCS_DIR)):
            if f.endswith((".md", ".txt")):
                with open(os.path.join(DOCS_DIR, f), encoding="utf-8") as fh:
                    docs[f] = fh.read()
    return docs


def build_vectorstore(docs, chunk_size, chunk_overlap, embeddings):
    """切分文档并向量化"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
    )
    texts, metas = [], []
    for fn, content in docs.items():
        for i, c in enumerate(splitter.split_text(content)):
            texts.append(c)
            metas.append({"source": fn, "chunk_id": i})
    if not texts:
        return None, 0
    vs = Chroma.from_texts(texts=texts, embedding=embeddings, metadatas=metas)
    return vs, len(texts)


PROMPT = ChatPromptTemplate.from_template("""请严格根据下面提供的资料回答问题。

【资料】
{context}

【问题】
{question}

【要求】
1. 只根据资料回答，不要用你自己的知识
2. 资料里没有就说"根据现有资料无法回答这个问题"
3. 200 字以内，直接给答案
""")


# ==================================================================
# 页面标题
# ==================================================================
st.set_page_config(page_title="我的 RAG 问答", page_icon="📚", layout="wide")
st.title("📚 我的知识库问答系统")

if not API_KEY:
    st.error("未配置 DASHSCOPE_API_KEY")
    st.stop()


# ==================================================================
# 侧边栏：参数
# ==================================================================
with st.sidebar:
    st.header("⚙️ 参数")

    # ------------------------------------------------------------------
    # TODO 1: 创建两个滑块，控制切分参数
    #   提示：st.slider("标签", 最小值, 最大值, 默认值)
    #   chunk_size     : 范围 100-1000，默认 300
    #   chunk_overlap  : 范围 0-200，  默认 50
    # ------------------------------------------------------------------
    chunk_size = 300          # ← 改成 st.slider(...)
    chunk_overlap = 50        # ← 改成 st.slider(...)

    st.divider()

    # ------------------------------------------------------------------
    # TODO 2: 创建相似度阈值滑块
    #   提示：范围 0.5 - 1.5，默认 1.0，步长 0.05
    # ------------------------------------------------------------------
    threshold = 1.0           # ← 改成 st.slider(...)

    # ------------------------------------------------------------------
    # TODO 3: 创建"清空对话"按钮
    #   提示：st.button("文字") 返回 True/False
    #   点击后应该把 st.session_state["messages"] 设为空列表
    # ------------------------------------------------------------------
    if False:                 # ← 改成 st.button("🗑️ 清空对话")
        st.session_state["messages"] = []
        st.rerun()


# ==================================================================
# 初始化
# ==================================================================
docs = load_documents()
if not docs:
    st.warning("docs 目录里没有文档")
    st.stop()

with st.spinner("正在构建知识库..."):
    embeddings, llm = load_models()
    # 参数变了就重建向量库
    key = (tuple(docs.keys()), chunk_size, chunk_overlap)
    if st.session_state.get("vs_key") != key:
        vs, n_chunks = build_vectorstore(docs, chunk_size, chunk_overlap, embeddings)
        st.session_state["vs"] = vs
        st.session_state["vs_key"] = key
        st.session_state["n_chunks"] = n_chunks
        st.session_state["messages"] = []
    else:
        vs = st.session_state["vs"]
        n_chunks = st.session_state["n_chunks"]

# ------------------------------------------------------------------
# TODO 4: 初始化对话历史（如果 session_state 里还没有 messages）
#   提示：参考第3步学过的判断写法
# ------------------------------------------------------------------
# 在这里写你的代码：


col1, col2 = st.columns(2)
col1.metric("文档数", len(docs))
col2.metric("文本块数", n_chunks)
st.divider()


# ==================================================================
# 显示历史消息
# ==================================================================
for m in st.session_state.get("messages", []):
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if m.get("meta"):
            with st.expander("🔍 检索详情"):
                st.markdown(m["meta"])


# ==================================================================
# 提问区
# ==================================================================
# ------------------------------------------------------------------
# TODO 5: 用 st.chat_input 创建输入框
#   提示：question = st.chat_input("请输入问题...")
#   注意：chat_input 会在用户按回车时返回输入内容，否则返回 None
# ------------------------------------------------------------------
question = None               # ← 改成 st.chat_input(...)

if question:
    # ---- 显示用户消息 ----
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    # ---- 处理并显示回答 ----
    with st.chat_message("assistant"):
        t0 = time.time()

        # 检索
        results = vs.similarity_search_with_score(question, k=5)
        # 阈值过滤
        valid = [(d, s) for d, s in results if s <= threshold]

        if not valid:
            # 没有相关资料 → 拒答
            answer = "根据现有资料无法回答这个问题。"
            st.warning(f"⚠️ 未找到相关资料（最相似距离 {results[0][1]:.4f} > 阈值 {threshold}）")
            st.write(answer)
            meta = None
        else:
            # 有资料 → 拼上下文 + 生成
            context = "\n\n---\n\n".join(
                f"【来源：{d.metadata['source']}】\n{d.page_content}" for d, _ in valid
            )
            resp = llm.invoke(PROMPT.format_messages(context=context, question=question))
            answer = resp.content.strip()
            st.write(answer)

            # 显示出处
            sources = sorted({d.metadata["source"] for d, _ in valid})
            st.caption(f"📎 出处：{'、'.join(sources)}　|　耗时 {time.time()-t0:.2f}s")

            # 检索详情表格
            lines = ["| 排名 | 来源 | 片段 | 距离 |", "|---|---|---|---|"]
            for i, (d, s) in enumerate(valid, 1):
                preview = d.page_content.replace("\n", " ")[:40]
                lines.append(f"| {i} | {d.metadata['source']} | {preview}... | {s:.4f} |")
            meta = "\n".join(lines)
            with st.expander("🔍 检索详情"):
                st.markdown(meta)

    # 保存 AI 回复到历史
    st.session_state["messages"].append(
        {"role": "assistant", "content": answer, "meta": meta}
    )
    st.rerun()


# ==================================================================
# 完成检查
# ==================================================================
st.divider()
with st.expander("📋 完成检查（填完 TODO 再看）"):
    st.markdown("""
    **你应该填了 7 个 TODO：**

    1. `chunk_size = st.slider("chunk_size", 100, 1000, 300, 50)`
    2. `chunk_overlap = st.slider("chunk_overlap", 0, 200, 50, 10)`
    3. `threshold = st.slider("相似度阈值", 0.5, 1.5, 1.0, 0.05)`
    4. `if st.button("🗑️ 清空对话"):`
    5. 初始化 messages：
       ```python
       if "messages" not in st.session_state:
           st.session_state["messages"] = []
       ```
    6. （上面 TODO 4 的位置）
    7. `question = st.chat_input("请输入问题...")`

    **全部填对后，你应该能：**
    - 提问 → 看到答案 + 出处
    - 问无关问题 → 看到拒答警告
    - 展开"检索详情" → 看到每个片段的距离
    - 点"清空对话" → 历史清空
    """)
