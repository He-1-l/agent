# -*- coding: utf-8 -*-
"""
Day 2 · 第 1 步：文档切分（Split）

════════════════════════════════════════════════════════════
  今天的目标：把一个知识库问答系统跑起来
  这一步只做"切分"，先搞懂文档是怎么被切成小块的
════════════════════════════════════════════════════════════

运行：双击 run1.bat

【先跑通，后理解】这个脚本不调用大模型，纯本地运行，不会花钱。
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

from langchain_text_splitters import RecursiveCharacterTextSplitter

# ==================================================================
# 第 1 步：加载文档
# ==================================================================
# docs 目录里放我们的知识库文件

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")

print("=" * 60)
print("  第 1 步：加载文档")
print("=" * 60)

documents = []          # 用来存放 (文件名, 内容) 的列表

for filename in os.listdir(DOCS_DIR):
    if not filename.endswith(".md"):
        continue
    filepath = os.path.join(DOCS_DIR, filename)
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    documents.append((filename, content))
    print(f"  已加载: {filename}  ({len(content)} 字符)")

print(f"\n  共加载 {len(documents)} 个文档")


# ==================================================================
# 第 2 步：切分
# ==================================================================
print()
print("=" * 60)
print("  第 2 步：把长文档切成小块")
print("=" * 60)

# RecursiveCharacterTextSplitter 是最常用的切分器
# 它会尽量按语义边界切：先按段落切，太长再按句子，再按字符
splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,        # 每块最多 300 字符
    chunk_overlap=50,      # 相邻块重叠 50 字符，防止句子被切断
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],  # 切分优先级
)

all_chunks = []             # 所有块

for filename, content in documents:
    chunks = splitter.split_text(content)
    print(f"\n  {filename}")
    print(f"    原文 {len(content)} 字符 -> 切成 {len(chunks)} 块")
    for i, c in enumerate(chunks):
        # 每块都记录来源，这是"答案可溯源"的基础
        all_chunks.append({
            "content": c,
            "source": filename,
            "chunk_id": i,
        })
    # 展示前 2 块长什么样
    for i, c in enumerate(chunks[:2]):
        preview = c.replace("\n", " ")[:80]
        print(f"      块{i}: [{len(c):>3}字符] {preview}...")

print()
print(f"  切分完成，共得到 {len(all_chunks)} 个块")


# ==================================================================
# 第 3 步：看看切分效果
# ==================================================================
print()
print("=" * 60)
print("  第 3 步：观察切分质量")
print("=" * 60)

# 展示一个完整的块，让你看清"块"到底长什么样
sample = all_chunks[0]
print(f"""
  示例块（来自 {sample['source']}，第 {sample['chunk_id']} 块）：

  ┌{'─' * 56}┐""")
for line in sample["content"].split("\n"):
    print(f"  │ {line[:54]:<54} │")
print(f"  └{'─' * 56}┘")

print()
print("""
  【要理解的三个点】

  1. 为什么要切分？
     模型一次能处理的文字有限，而且整篇文档塞进去，检索时
     无法定位到具体哪一段相关。切成小块才能精准检索。

  2. chunk_size 怎么定？
     太大 → 一块里混了很多主题，检索不准
     太小 → 语义不完整，模型看不懂
     经验值：300-1000 字符

  3. chunk_overlap 为什么要重叠？
     防止句子被从中间切断。比如一句话跨在两块之间，
     有重叠就能保证至少有一块包含完整语义。

  ⚠️ 注意每个块都带了 source（来自哪个文件）
     这是后面"答案带出处"的基础，非常重要。
""")

print("=" * 60)
print("  ✅ 第 1 步完成，下一步：把块转成向量存进数据库")
print("=" * 60)
