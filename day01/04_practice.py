# -*- coding: utf-8 -*-
"""
Day 1 补充练习：Python 语法填空

════════════════════════════════════════════════════════════
  怎么用这个文件（重要，先看）
════════════════════════════════════════════════════════════
  1. 每题都有 TODO，把该行的代码补全
  2. 补一题、运行一次（py 04_practice.py），看有没有报错
  3. 全部通过后，再看文件最下方的【答案与解释】
  4. 答不上来的，允许想 1 分钟再看答案 —— 别直接翻

════════════════════════════════════════════════════════════
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

results = {}   # 记录每题是否通过


# ==================================================================
# 第 1 题：读配置（最基础的骨架，每个 LangChain 程序都这么开头）
# ==================================================================
# TODO: 把 load_dotenv 的参数补上（想想为什么需要覆盖系统环境变量）
load_dotenv()                       # ← 改这一行

# TODO: 从环境变量里取出 Key
api_key = os.getenv("")             # ← 补上正确的变量名

results[1] = bool(api_key)
print(f"第1题 {'✅' if results[1] else '❌'}  读到 Key: {str(api_key)[:10]}...")


# ==================================================================
# 第 2 题：类型标注
# ==================================================================
# TODO: 补全函数签名的类型标注（参数是什么类型？返回什么类型？）
def greet(name):
    return f"你好，{name}！"

results[2] = greet("何焕") == "你好，何焕！"
print(f"第2题 {'✅' if results[2] else '❌'}  {greet('何焕')}")


# ==================================================================
# 第 3 题：列表推导式（LangChain 代码里到处都是）
# ==================================================================
TOOLS = ["calculator", "get_current_time", "count_text"]

# TODO: 把每个工具名转成大写
upper_tools = []                    # ← 用列表推导式改写这一行

# TODO: 只保留名字长度 > 10 的工具
long_tools = []                     # ← 用带 if 的列表推导式改写

results[3] = (upper_tools == ["CALCULATOR", "GET_CURRENT_TIME", "COUNT_TEXT"]
              and long_tools == ["get_current_time"])
print(f"第3题 {'✅' if results[3] else '❌'}  {upper_tools} | {long_tools}")


# ==================================================================
# 第 4 题：装饰器（理解 @tool 的关键）
# ==================================================================
# TODO: 补全装饰器内部的两处（调用原函数 / 返回包装函数）
def log_calls(func):
    def wrapper(*args, **kwargs):
        print(f"    [日志] 调用 {func.__name__}")
        result = None               # ← 这里要真正调用原函数
        print(f"    [日志] 返回 {result}")
        return result
    return None                     # ← 这里返回什么？

# TODO: 用你的装饰器装饰下面这个函数
def add(a, b):
    return a + b

results[4] = (add(3, 5) == 8)
print(f"第4题 {'✅' if results[4] else '❌'}  add(3,5) = {add(3, 5)}")


# ==================================================================
# 第 5 题：字典与列表取值（Agent 返回结构就是这样）
# ==================================================================
result = {
    "messages": [
        {"role": "user", "content": "现在几点了"},
        {"role": "assistant", "content": "现在是 10 点"},
        {"role": "tool", "content": "get_current_time 返回 10:00"},
    ]
}

# TODO: 取出最后一条消息的 content（提示：用负索引）
last_content = ""                   # ← 改这一行

# TODO: 统计 messages 有多少条
msg_count = 0                       # ← 改这一行

results[5] = (last_content == "get_current_time 返回 10:00" and msg_count == 3)
print(f"第5题 {'✅' if results[5] else '❌'}  {last_content} | 共 {msg_count} 条")


# ==================================================================
# 第 6 题（进阶）：异常处理
# ==================================================================
# TODO: 补全 try/except 结构（注意 except 的顺序！）
def safe_divide(a, b):
    return a / b                    # ← 用 try/except 包起来

# 用 try 包住，这样你还没写第6题时，程序不会崩溃、能继续测后面的题
try:
    results[6] = (safe_divide(10, 2) == 5.0 and safe_divide(10, 0) == "不能除以0")
    print(f"第6题 {'✅' if results[6] else '❌'}  {safe_divide(10, 2)} | {safe_divide(10, 0)}")
except ZeroDivisionError:
    results[6] = False
    print("第6题 ❌  还没处理除零异常（看懂报错：ZeroDivisionError）")


# ==================================================================
# 第 7 题（进阶）：类（看懂 fitness 项目的关键）
# ==================================================================
class ApiClient:
    # TODO: 把 setup 改成正确的构造方法名（前后各两个下划线）
    def setup(self, api_key):
        self.api_key = api_key
        self.call_count = 0

    def call(self, prompt):
        # TODO: 让计数 +1
        pass
        return f"[第{self.call_count}次调用] {prompt}"


try:
    client = ApiClient("sk-test")     # 构造方法改对了，这行才不报错
    client.call("你好")
    r = client.call("再见")
    results[7] = (r == "[第2次调用] 再见")
    print(f"第7题 {'✅' if results[7] else '❌'}  {r}")
except TypeError as e:
    results[7] = False
    print(f"第7题 ❌  构造方法名不对（报错说：{str(e)[:50]}）")
    print("       提示：Python 的构造方法叫 __init__，不是 setup")


# ==================================================================
# 总成绩
# ==================================================================
print()
print("=" * 60)
passed = sum(1 for v in results.values() if v)
print(f"通过 {passed}/7 题")
if passed == 7:
    print("🎉 全对！语法基础过关，可以放心推进 Day 2 了")
else:
    print("没过关的题，看下面的答案与解释，然后重写一遍")
    print("（不要改注释，靠记忆重写代码）")
print("=" * 60)


# ==================================================================
# 答案与解释  ⚠️ 先自己做，做完了再看！
# ==================================================================
"""
【第1题】
    load_dotenv(override=True)
    api_key = os.getenv("DASHSCOPE_API_KEY")

    为什么必须 override=True？
    load_dotenv 默认【不覆盖】已有的环境变量。
    你系统里曾经有一个错误的 DASHSCOPE_API_KEY，
    导致 .env 里正确的 Key 被静默忽略 —— 这就是我们排查很久的那个 401 bug！
    加上 override=True，.env 永远优先。


【第2题】
    def greet(name: str) -> str:

    : str   参数类型标注
    -> str  返回值类型标注
    Python 运行时不检查，但：
      - IDE 能智能提示
      - LangChain 靠它生成工具的 JSON Schema
    这就是 @tool 函数必须写类型标注的原因。


【第3题】
    upper_tools = [t.upper() for t in TOOLS]
    long_tools  = [t for t in TOOLS if len(t) > 10]

    列表推导式格式：[对元素做什么  for 元素 in 列表  if 条件]
    LangChain 里极常见，例如：[t.name for t in tools]


【第4题】
        result = func(*args, **kwargs)   # 调用原函数
    return wrapper                        # 返回包装后的函数

    @log_calls                            # 装饰函数

    装饰器本质：接收函数 → 返回新函数。
    @tool 就是这个原理：把普通函数包装成"模型能调用的工具"。
    面试常问「@tool 做了什么」：
      保留签名和 docstring → 生成 JSON Schema → 让模型知道何时调用。


【第5题】
    last_content = result["messages"][-1]["content"]
    msg_count = len(result["messages"])

    -1 是负索引 = 倒数第一个。
    实际 Agent 代码里 result["messages"][-1] 就是取最后一条消息。


【第6题】
    def safe_divide(a, b):
        try:
            return a / b
        except ZeroDivisionError:
            return "不能除以0"
        except Exception as e:
            return f"未知错误: {e}"

    ⚠️ 顺序陷阱：ZeroDivisionError 必须写在 Exception 前面，
    因为它是 Exception 的子类，写在后面就永远轮不到。
    这是面试高频考点。


【第7题】
    def __init__(self, api_key):     # 前后各两个下划线
        self.api_key = api_key
        self.call_count = 0

    def call(self, prompt):
        self.call_count += 1
        return f"[第{self.call_count}次调用] {prompt}"

    self 是"对象自己"，所有实例属性都用 self.xxx。
    对照你在 fitness 项目里看到的 Java 写法：
        public UserServiceImpl(UserMapper mapper) { ... }
    Java 构造函数 ↔ Python 的 __init__


════════════════════════════════════════════════════════════
  真正的检验：全部做对后，新建一个空文件，凭记忆再写一遍。
  能默写出来，才是真的会了。
════════════════════════════════════════════════════════════
"""
