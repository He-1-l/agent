# -*- coding: utf-8 -*-
"""
Day 1 第二步：给模型装上手和脚（工具调用）

对比 01_hello_llm.py，你会看到关键变化：
  - 01：模型只会"说"，问它几点它答不上来
  - 02：我们给它装上工具，它就能"做"了

这就是 Agent 的本质：LLM（决策）+ Tools（执行）+ 循环。

运行：双击 run2.bat 或 py 02_tools_agent.py
"""
import os
import sys

# 强制用 UTF-8 输出，避免 Windows 的 GBK 编码导致 emoji/中文报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_community.chat_models import ChatTongyi

load_dotenv(override=True)   # override=True：让 .env 永远优先于系统环境变量
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("❌ 请先配置 .env 里的 DASHSCOPE_API_KEY")
    raise SystemExit(1)


# ==================================================================
# 定义工具
# ------------------------------------------------------------------
# @tool 装饰器把普通 Python 函数变成"模型能调用的工具"。
#
# 三条最重要的规则（面试会问，务必理解）：
#   1. docstring 必须写清楚"这个工具干什么用的"
#      —— 模型靠这段文字判断"什么时候该调用它"
#   2. 参数类型必须标注（query: str）
#      —— 模型靠这个知道"要传什么参数"
#   3. 返回值要稳定（统一返回字符串）
#      —— 返回格式变来变去，模型就没法总结结果
# ==================================================================

@tool
def get_current_time(city: str = "北京") -> str:
    """获取当前时间。

    当用户询问"现在几点""今天几号""当前时间"等实时时间问题时，
    必须调用此工具，不要凭记忆回答。

    Args:
        city: 城市名，默认为北京
    """
    # 用固定 UTC+8 偏移，避免依赖系统时区数据库（Windows 上可能缺失）
    now = datetime.now(timezone(timedelta(hours=8)))
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return f"{city}当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}（星期{weekdays[now.weekday()]}）"


@tool
def calculator(expression: str) -> str:
    """执行数学计算。

    当用户需要进行算术运算（加减乘除、乘方、取余）时调用此工具。
    不要自己心算，大模型的心算经常出错。

    Args:
        expression: 数学表达式，例如 "123.456 * 789" 或 "(2+3)**10"
    """
    # 安全校验：只允许数字和运算符，防止执行恶意代码
    allowed = set("0123456789+-*/().% ")
    if not set(expression) <= allowed:
        return f"表达式包含不允许的字符，只能使用数字和 + - * / ( ) . % 运算符"

    try:
        # 禁用内置函数，只做纯数学求值
        result = eval(expression, {"__builtins__": {}}, {})
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算失败：{e}"


@tool
def count_text(text: str) -> str:
    """统计文本的字符数和词数。

    当用户问"这段话有多少字""统计一下字数"时调用。

    Args:
        text: 需要统计的文本内容
    """
    chars = len(text)
    # 中文按字符算，英文按空格分词
    words = len([w for w in text.replace("\n", " ").split(" ") if w.strip()])
    return f"字符数：{chars}，词数：{words}"


TOOLS = [get_current_time, calculator, count_text]


# ==================================================================
# 创建 Agent
# ==================================================================
llm = ChatTongyi(model_name="qwen-turbo", dashscope_api_key=api_key, temperature=0)

# create_agent 把模型和工具绑定在一起
# 它会自动进入"思考 → 调用工具 → 观察结果 → 再思考"的循环
agent = create_agent(model=llm, tools=TOOLS)


def ask(question: str):
    """向 Agent 提问并打印结果"""
    print(f"\n【提问】{question}")
    print("-" * 60)
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": question}]})
        # 最后一条消息就是最终回答
        final = result["messages"][-1]
        print(final.content)

        # 打印中间过程，让你看到 Agent 到底调了哪些工具
        tool_calls = []
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(f"{tc['name']}({tc.get('args', {})})")
        if tool_calls:
            print(f"\n  🔧 实际调用的工具：{' → '.join(tool_calls)}")
        else:
            print("\n  （没有调用任何工具）")
    except Exception as e:
        print("❌ 出错:", e)


if __name__ == "__main__":
    print("=" * 60)
    print("Agent 已就绪，工具清单：", [t.name for t in TOOLS])
    print("=" * 60)

    # 这些问题，01 里的模型全都答不上来
    ask("现在几点了？")
    ask("帮我算一下 123.456 乘以 789 等于多少")
    ask("'人工智能正在改变世界'这句话有多少个字？")
    # 这个问题不需要工具，看 Agent 会不会乱调
    ask("你好，请介绍一下你自己")

    print("\n" + "=" * 60)
    print("重点观察：")
    print("  1. 每个问题它调用了哪个工具？")
    print("  2. 最后一个问题它有没有乱调工具？（这叫工具误调用）")
    print("  3. 如果它没调工具就答错了，想想为什么？")
    print("=" * 60)
