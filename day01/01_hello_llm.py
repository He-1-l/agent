# -*- coding: utf-8 -*-
"""
Day 1 第一步：让大模型开口说话

这是最小可运行示例。跑通它，你就完成了从 0 到 1。

运行前准备：
  1. 去 https://bailian.console.aliyun.com/ 注册，开通后获取 API Key
  2. 在 day01 目录下创建 .env 文件，写入：DASHSCOPE_API_KEY=sk-你的key
  3. 双击运行 run.bat（或命令行 py 01_hello_llm.py）
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

# ⚠️ override=True 很关键！
# 默认情况下，如果系统里已经有 DASHSCOPE_API_KEY 环境变量，
# load_dotenv 会【忽略】.env 里的值，导致你改了 .env 也不生效。
# 加上 override=True 后，.env 的配置永远优先。
load_dotenv(override=True)

api_key = os.getenv("DASHSCOPE_API_KEY")

# 先检查 Key 有没有配上，避免报一堆看不懂的错
if not api_key:
    print("=" * 60)
    print("❌ 没有找到 DASHSCOPE_API_KEY")
    print("=" * 60)
    print("请检查：")
    print("  1. day01 目录下有没有 .env 文件")
    print("  2. .env 文件里是否写了 DASHSCOPE_API_KEY=sk-xxxxxx")
    print("  3. 注意等号两边不要有空格，不要加引号")
    raise SystemExit(1)

print("=" * 60)
print("✅ API Key 已加载:", api_key[:8] + "..." + api_key[-4:])
print("=" * 60)

# ------------------------------------------------------------------
# 调用大模型
# ------------------------------------------------------------------
from langchain_community.chat_models import ChatTongyi

# temperature=0 表示输出尽量稳定，同样的输入给同样的答案
# 写代码、做数据处理时都用 0；写文案创意时才调高
llm = ChatTongyi(
    model_name="qwen-turbo",
    dashscope_api_key=api_key,
    temperature=0,
)

questions = [
    "用一句话解释什么是大模型",
    "现在几点了？",              # 故意问它答不上来的问题
    "123.456 乘以 789 等于多少？",  # 故意问它算不准的问题
]

for i, q in enumerate(questions, 1):
    print(f"\n【问题 {i}】{q}")
    print("-" * 60)
    try:
        resp = llm.invoke(q)
        print(resp.content)
    except Exception as e:
        print("❌ 调用失败:", e)

print("\n" + "=" * 60)
print("观察上面 3 个回答，重点看第 2、3 题：")
print("  - 它知道现在几点吗？")
print("  - 它的乘法算对了吗？")
print("这就是 Day 1 要理解的核心：大模型只会'接龙'，不会查时间、不会真算数。")
print("=" * 60)
