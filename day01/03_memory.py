# -*- coding: utf-8 -*-
"""
Day 1 第三步：让对话记住上文（记忆管理）

前两步每次提问都是"失忆"的——你问完"我叫什么"，下一句它就忘了。
这一步解决多轮对话。

核心原理（面试高频）：
  LLM 本身没有记忆！所谓"记忆"，本质是【每次请求都把历史消息一起发过去】。
  你发得越多，它"记得"越多，但 token 消耗也越大、也越贵。

运行：双击 run3.bat 或 py 03_memory.py
"""
import os
import sys

# 强制用 UTF-8 输出，避免 Windows 的 GBK 编码导致 emoji/中文报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv(override=True)   # override=True：让 .env 永远优先于系统环境变量
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("❌ 请先配置 .env 里的 DASHSCOPE_API_KEY")
    raise SystemExit(1)

llm = ChatTongyi(model_name="qwen-turbo", dashscope_api_key=api_key, temperature=0)


def demo_without_memory():
    """演示：不做记忆管理会怎样"""
    print("\n" + "=" * 60)
    print("【对比实验 A】不做记忆管理")
    print("=" * 60)

    print("\n用户：我叫何焕，正在学 Agent 开发")
    r1 = llm.invoke("我叫何焕，正在学 Agent 开发")
    print("AI：", r1.content[:60], "...")

    print("\n用户：我叫什么名字？")
    r2 = llm.invoke("我叫什么名字？")     # 注意：这次没带上一轮的历史
    print("AI：", r2.content[:120])
    print("\n👆 它不记得了。因为每次调用都是独立的，历史没有传进去。")


def demo_with_memory():
    """演示：正确的记忆管理"""
    print("\n" + "=" * 60)
    print("【对比实验 B】把历史消息一起传进去")
    print("=" * 60)

    # messages 列表就是"记忆"——每轮对话后把提问和回答都追加进去
    messages = [
        SystemMessage(content="你是一个耐心的技术导师，回答简洁，多打比方。"),
    ]

    def chat(user_input: str):
        messages.append(HumanMessage(content=user_input))
        resp = llm.invoke(messages)
        # 关键：把 AI 的回答也存进历史，下一轮才能"记得"
        messages.append(AIMessage(content=resp.content))
        return resp.content

    print("\n用户：我叫何焕，正在学 Agent 开发")
    print("AI：", chat("我叫何焕，正在学 Agent 开发")[:80], "...")

    print("\n用户：我叫什么名字？我在学什么？")
    print("AI：", chat("我叫什么名字？我在学什么？"))

    print(f"\n📊 当前 messages 列表里有 {len(messages)} 条消息")
    print("   这就是'记忆'的全部秘密：一个不断增长的列表。")


def demo_token_growth():
    """演示：为什么长对话会很贵"""
    print("\n" + "=" * 60)
    print("【现象观察】历史越长，消耗越大")
    print("=" * 60)
    print("""
    每轮对话，你都要把【全部历史】重新发给模型一次。
    假设历史有 1000 token，聊到第 50 轮：
        第 50 轮实际发送 = 1000(历史) + 本轮问题
    而且前 49 轮的历史被重复计费了几十次。

    所以真实项目必须做【记忆压缩】，常见三种做法：
      1. 只保留最近 N 轮（滑动窗口）—— 简单，但会丢早期信息
      2. 超过阈值就总结前文，用摘要替代原文 —— 省 token，会丢细节
      3. 存进数据库/向量库，需要时检索回来 —— 最强，也最复杂

    👉 这就是你要学的 RAG 和 LangGraph 要解决的问题。
    """)


if __name__ == "__main__":
    demo_without_memory()
    demo_with_memory()
    demo_token_growth()

    print("\n" + "=" * 60)
    print("Day 1 完成！你现在理解了：")
    print("  ✅ 怎么调用大模型")
    print("  ✅ 大模型的两个硬伤（不知道实时信息、算不准）")
    print("  ✅ 用工具补上这两个硬伤 → 这就是 Agent")
    print("  ✅ 记忆的本质是消息列表")
    print("=" * 60)
