# -*- coding: utf-8 -*-
"""
第 1 课：Python 基础，一行一行带你写

════════════════════════════════════════════════════════════
  怎么用这个文件
════════════════════════════════════════════════════════════
  1. 先双击运行一次 run5.bat，看看输出长什么样
  2. 然后打开这个文件，看每一行的【注释】
  3. 最后自己新建一个文件，把代码默写出来（不需要注释）
  4. 写不出来就回来看，看懂了再默写

  ⚠️ 不要跳步。这一课很基础，但跳过它后面全是坎。
════════════════════════════════════════════════════════════
"""

print("=" * 60)
print("  第 1 部分：变量 —— 给数据起个名字")
print("=" * 60)

# 变量就是"给一个值起名字"，等号 = 是赋值
age = 21                    # 整数
name = "何焕"               # 字符串（文字）
score = 95.5                # 小数
is_student = True           # 布尔值（真/假，注意首字母大写）

print("age =", age)
print("name =", name)
print("score =", score)
print("is_student =", is_student)
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  第 2 部分：f-string —— 把变量塞进文字里（最常用！）")
print("=" * 60)

# f 开头 + {} 里放变量名，这是 Python 最常用的拼接方式
print(f"我叫{name}，今年{age}岁，考了{score}分")
print(f"明年我就 {age + 1} 岁了")          # {} 里可以直接算数
print(f"姓名大写：{name.upper()}")         # 也可以调用方法
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  第 3 部分：列表 —— 装一串东西")
print("=" * 60)

# 列表用 [] 包起来，元素用逗号分隔
tools = ["calculator", "get_time", "count_text"]

print("整个列表：", tools)
print("第1个（索引0）：", tools[0])         # ⚠️ 索引从 0 开始！
print("第2个（索引1）：", tools[1])
print("最后一个（用-1）：", tools[-1])      # -1 表示倒数第一个
print("一共几个：", len(tools))            # len() 算长度
print()

# 遍历：把列表里每个元素依次拿出来
print("遍历列表：")
for t in tools:
    print(f"  -> {t}")
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  第 4 部分：字典 —— 键值对，Agent 返回值就是这个结构")
print("=" * 60)

# 字典用 {} 包起来，格式是 "键": 值
message = {
    "role": "user",
    "content": "现在几点了",
}

print("整个字典：", message)
print("取 role：", message["role"])        # 用键取值
print("取 content：", message["content"])
print()

# 字典里可以套列表，列表里可以套字典 —— 这就是 Agent 的返回结构
result = {
    "messages": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮你"},
        {"role": "assistant", "content": "现在是 10 点"},
    ]
}

print("嵌套结构：")
print("  所有消息：", result["messages"])
print("  第一条内容：", result["messages"][0]["content"])
print("  最后一条内容：", result["messages"][-1]["content"])
print()
print("  ↑ 记住这个写法：result['messages'][-1]['content']")
print("    它的意思是：先取出 messages 列表 → 再取最后一个 → 再取 content")
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  第 5 部分：函数 —— 把一段代码打包起来反复用")
print("=" * 60)

# def 是 define（定义）的缩写
def greet(person):
    """这是文档字符串，说明这个函数干什么（可以省略）"""
    return f"你好，{person}！"

# 定义完要"调用"才会执行
print(greet("何焕"))
print(greet("张三"))
print()

# 函数可以有默认值
def greet2(person, city="北京"):
    return f"{person}来自{city}"

print(greet2("何焕"))            # 不传 city，用默认值
print(greet2("李四", "上海"))     # 传了就用传的
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  第 6 部分：类型标注 —— 给参数和返回值贴标签")
print("=" * 60)

# 冒号后面写参数类型，箭头后面写返回值类型
# ⚠️ 这只是"标注"，Python 不会强制检查，但工具和框架要靠它
def add(a: int, b: int) -> int:
    return a + b

def make_greeting(person: str) -> str:
    return f"你好，{person}"

print("add(3, 5) =", add(3, 5))
print(make_greeting("何焕"))
print()
print("  ↑ LangChain 的 @tool 必须写类型标注，就是因为要生成 JSON Schema")
print("    让模型知道'这个工具要传什么参数'")
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  第 7 部分：列表推导式 —— 一步生成新列表")
print("=" * 60)

tools = ["calculator", "get_time", "count_text"]

# 普通写法（用它理解逻辑）
upper_old = []
for t in tools:
    upper_old.append(t.upper())
print("普通写法：", upper_old)

# 推导式写法（更短，但要理解意思）
upper_new = [t.upper() for t in tools]
print("推导式写法：", upper_new)
print()
print("  读法：[对每个 t 做什么  for t in 列表]")
print("        [t.upper()        for t in tools]")
print()

# 带条件的推导式
long_tools = [t for t in tools if len(t) > 9]
print("只要长度>9的：", long_tools)
print("  读法：[保留 t  for t in 列表  if 条件]")
print()

# 实际用法：取出所有工具的名字
class FakeTool:
    def __init__(self, name):
        self.name = name

tool_objs = [FakeTool("计算器"), FakeTool("时间")]
names = [t.name for t in tool_objs]
print("从对象列表取名字：", names)
print("  ↑ 这就是 LangChain 里 [t.name for t in tools] 的由来")
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  第 8 部分：try/except —— 出错时不崩溃")
print("=" * 60)

# 10 / 0 会报错，程序会直接崩溃
print("尝试 10 / 0 ...")
try:
    result = 10 / 0
    print("这行不会执行")
except ZeroDivisionError:
    print("  捕获到了：不能除以 0")
print("程序继续往下走了 ✅")
print()

# 多个 except，按顺序匹配
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return "不能除以0"
    except Exception as e:
        return f"未知错误: {e}"

print("safe_divide(10, 2) =", safe_divide(10, 2))
print("safe_divide(10, 0) =", safe_divide(10, 0))
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  第 9 部分：类 —— 把数据和操作打包（fitness 项目的核心）")
print("=" * 60)

class ApiClient:
    # __init__ 是构造方法，创建对象时自动执行（前后各两个下划线）
    def __init__(self, api_key):
        self.api_key = api_key      # self 是"对象自己"
        self.call_count = 0         # 每个对象都有自己的 call_count

    # 普通方法，第一个参数必须是 self
    def call(self, prompt):
        self.call_count += 1        # 计数 +1
        return f"[第{self.call_count}次] {prompt}"

# 创建对象（会自动调用 __init__）
client = ApiClient("sk-test123")

print("第1次调用：", client.call("你好"))
print("第2次调用：", client.call("再见"))
print("总共调用了", client.call_count, "次")
print()
print("  对照你在 fitness 项目里看到的 Java 写法：")
print("    @Service")
print("    public class UserServiceImpl extends ServiceImpl<...> {")
print("        public UserServiceImpl(UserMapper mapper) { ... }")
print("    }")
print("  Java 的构造函数 ↔ Python 的 __init__")
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  第 10 部分：装饰器 —— 理解 @tool 的关键")
print("=" * 60)

# 装饰器本质：接收一个函数，返回一个新函数
def log_calls(func):
    def wrapper(*args, **kwargs):
        print(f"    [日志] 准备调用 {func.__name__}")
        result = func(*args, **kwargs)      # 真正调用原函数
        print(f"    [日志] 结果是 {result}")
        return result
    return wrapper

# 用 @ 语法"装饰"函数，等价于 add = log_calls(add)
@log_calls
def add(a, b):
    return a + b

print("调用 add(3, 5)：")
print("  返回值：", add(3, 5))
print()
print("  ↑ 你看到了吗？add 函数本身没改，但调用时自动打印了日志")
print("    这就是装饰器：在不改原函数的前提下，给它加功能")
print()
print("  @tool 也是这样：")
print("    普通函数 -> 加上 @tool -> 变成'模型能调用的工具'")
print()

# ---------------------------------------------------------------
print("=" * 60)
print("  ✅ 第 1 课完成")
print("=" * 60)
print("""
接下来你要做的（很重要）：

  1. 新建一个空文件 05_mypractice.py
  2. 不看上面，凭记忆把这些写一遍：
       - 定义一个变量、用 f-string 输出
       - 建一个列表，取第一个和最后一个
       - 建一个嵌套字典，取出 result["messages"][-1]["content"]
       - 定义带类型标注的函数
       - 写一个列表推导式
       - 写 try/except
       - 写一个带 __init__ 的类
  3. 写不出来就回来看，然后再写

  ⚠️ 这一步不能省。看会 ≠ 写会。
  你能默写出来，才算真的掌握了。
""")
