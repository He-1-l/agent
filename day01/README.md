# Day 1 · 让 AI 开口说话，再给它装上手脚

> 目标：今天结束时，你能亲眼看到 AI 从"只会聊天"变成"会调用工具办事"。  
> 用时：约 3-4 小时（含注册和踩坑）  
> 产出：3 个能跑的脚本 + 一段能讲给面试官听的认知

---

## 第 0 步：拿到 API Key（约 15 分钟）

1. 打开 <https://bailian.console.aliyun.com/>
2. 用支付宝/淘宝账号登录（阿里云账号）
3. 实名认证（个人认证，几分钟）
4. 左侧菜单找 **API-KEY 管理** → **创建我的 API-KEY**
5. 复制那串 `sk-xxxxxxxx`

> 💡 **费用问题**：新用户有免费额度（通义千问系列通常送 100 万 token 左右）。  
> 我们今天这三个脚本全部跑完，消耗不到 1 万 token，**基本不花钱**。  
> 但要养成习惯：**不要把 Key 发给别人，也不要提交到 GitHub**。

**配置 Key：**

- 把 `.env.example` 复制一份，改名为 `.env`（注意前面有个点）
- 用记事本打开，把 `sk-在这里粘贴你的key` 换成你的真实 Key
- 保存

⚠️ 如果文件改名后看不见了，是因为 Windows 默认隐藏扩展名。  
在文件夹里点【查看】→ 勾选【文件扩展名】就能看到 `.env` 而不是 `.env.txt`。

---

## 第 1 步：让大模型开口（`run1.bat`）

双击 `run1.bat`。

**你会看到什么：**

- ✅ API Key 已加载
- 三个问题的回答

**重点看第 2、3 题：**

| 问题                | 预期表现          | 说明            |
| ----------------- | ------------- | ------------- |
| 用一句话解释大模型         | 答得很好          | 这是它的强项：语言组织   |
| 现在几点了？            | **答不出来 / 瞎编** | 它没有实时信息       |
| 123.456 × 789 = ? | **很可能算错**     | 它在"猜"数字，不是真计算 |

**这就是 Day 1 最重要的认知：**

> 大模型本质是"根据前文猜下一个词"的接龙机器。  
> 它的知识停在训练那一刻，它不会查、不会算、不会操作软件。

**理解了这个，你就理解了 Agent 为什么存在。**

---

## 第 2 步：给它装工具（`run2.bat`）

双击 `run2.bat`。同样的问题，这次它能答对了。

**打开 `02_tools_agent.py`，重点看这三段：**

**① `@tool` 装饰器**  
把普通 Python 函数变成"模型能调用的工具"。就这一行：

```python
@tool
def get_current_time(city: str = "北京") -> str:
    """获取当前时间。当用户询问"现在几点"时，必须调用此工具..."""
```

**② docstring 是给模型看的，不是给人看的** ⭐  
这是新手最容易忽略、面试最爱问的点。  
模型靠**这段文字**判断"什么时候该调用这个工具"。  
写得含糊 → 模型不知道该调 → Agent 就失效。

> 面试原题：「工具描述为什么不清晰会导致调用失败？」  
> 答案就在这：模型是靠自然语言描述来决策的，描述就是它的说明书。

**③ `create_agent` 的循环**

```python
agent = create_agent(model=llm, tools=TOOLS)
```

它自动实现了这个循环：

```
用户提问 → 模型思考 → 决定调用哪个工具 → 执行工具
    ↑                                      ↓
    └──────── 把结果喂回模型，继续思考 ←────┘
```

这叫 **ReAct 循环**（Reason + Act），面试高频考点。

**观察最后一题 `"你好，请介绍一下你自己"`**  
这题不需要工具。看它会不会乱调工具——如果乱调了，这叫**工具误调用**，  
是实际项目里要重点优化的问题（解决方案：把 docstring 写得更精确）。

---

## 第 3 步：让对话有记忆（`run3.bat`）

双击 `run3.bat`，看对比实验。

**实验 A**：不带历史 → 问"我叫什么"，它答不上来  
**实验 B**：把历史一起传 → 它记得住

**核心结论（面试必答）：**

> LLM 本身没有记忆。  
> 所谓"记忆"，本质是**每次请求都把历史消息重新发一遍**。  
> 代码里就是一个不断 append 的 `messages` 列表。

**由此推出成本问题：**

- 聊到第 50 轮，前 49 轮历史被重复计费几十次
- 所以真实项目必须做**记忆压缩**，三种做法：
  1. 滑动窗口（只留最近 N 轮）—— 简单，丢早期信息
  2. 摘要压缩（总结前文）—— 省 token，丢细节
  3. 持久化 + 检索（存数据库/向量库）—— 最强，最复杂

---

## 今日验收清单

全部打勾才算完成 Day 1：

- [ ] 成功拿到 API Key 并配置好 `.env`
- [ ] `run1.bat` 跑通，亲眼看到 AI 算错乘法
- [ ] `run2.bat` 跑通，看到 Agent 自动选择工具
- [ ] `run3.bat` 跑通，理解记忆 = 消息列表
- [ ] 能用自己的话回答下面 4 个问题

**自测题（答不上来就回去看代码）：**

1. 为什么大模型不知道"现在几点"？
2. `@tool` 的 docstring 是写给谁看的？为什么重要？
3. Agent 和普通调 API 的区别是什么？
4. 为什么长对话会很贵？怎么解决？

---

## 常见报错排查

| 报错                                          | 原因                          | 解决                            |
| ------------------------------------------- | --------------------------- | ----------------------------- |
| `没有找到 DASHSCOPE_API_KEY`                    | `.env` 没配好                  | 检查文件名是不是 `.env.txt`，等号两边有没有空格 |
| `InvalidApiKey`                             | Key 错误                      | 见下方专项说明                       |
| `'xxx' 不是内部或外部命令` 或中文乱码                     | bat 换行符是 LF / 混入 PYTHONUTF8 | 见下方专项说明                       |
| `UnicodeEncodeError: 'gbk' codec`           | 编码问题                        | **已修复**，脚本已强制 UTF-8           |
| `No time zone found with key Asia/Shanghai` | Windows 缺时区库                | **已修复**，改用固定 UTC+8            |
| `ModuleNotFoundError`                       | 依赖没装                        | 见下方命令                         |
| `python 不是内部或外部命令`                          | 用了 `python` 而非 `py`         | **一律用 `py`**，你的 `python` 是坏存根 |

### ⚠️ 不要往 .bat 里加 PYTHONUTF8=1（我们踩过）

实测报错：

```
Fatal Python error: preconfig_init_utf8_mode: invalid PYTHONUTF8 environment variable value
```

**原因**：`set PYTHONUTF8=1` 若行尾带空格，值就变成 `"1 "`，Python 判定非法并**直接崩溃**，  
脚本根本执行不到 API 调用。

**正确写法**（只用这两行就够）：

```bat
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
```

脚本内部已用 `sys.stdout.reconfigure(encoding="utf-8")` 处理编码。

📌 另外 `.bat` 必须是 **CRLF 换行**。若是 LF，会出现"不是内部或外部命令"或中文乱码。

### ⚠️ 关于 `InvalidApiKey` 的特别说明

**遇到 401 先别急着换 Key，按顺序排查：**

1. **先用原生 SDK 直接测 Key**，绕开 LangChain 定位真凶：

```
py -c "import dashscope; dashscope.api_key='你的Key'; r=dashscope.Generation.call(model='qwen-turbo', prompt='说你好'); print(r.status_code, r.output.choices[0].message.content if r.status_code==200 else r.message)"
```

- 返回 200 → **Key 没问题**，是代码/环境问题（优先查上面的 PYTHONUTF8）
- 返回 401 → Key 真的错了，去控制台重新创建

1. **两种 Key 格式都正常，别被吓到**：
   - 老格式：`sk-` 开头，约 35 字符
   - **新格式：`sk-ws-` 开头，约 116 字符** ← 我们用的就是这个
2. **最容易搞混**：别把「AccessKey ID / Secret」「APP ID」「工作空间 ID」当 API Key。
3. **`.env` 里只保留一行 Key**，多行会让后面的覆盖前面的。

**重装依赖命令（你的机器必须带镜像参数）：**

```
py -m pip install langchain langchain-community dashscope python-dotenv -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
```

> ⚠️ **重要：不要照抄课程文档里的 `langchain==1.2.10` 固定版本。**
>
> 我们实测发现：课程文档锁定的 `langchain==1.2.10` 会和它自己依赖的 `langgraph` 冲突，  
> 导致 `create_agent` 直接导入失败（报 `cannot import name 'ExecutionInfo'`）。  
> 原因是文档只锁了 langchain，没锁 langgraph，pip 自动装了不兼容的组合。
>
> **我们改用不锁版本的安装方式**，让 pip 自己求解兼容组合。  
> 你机器上已验证通过的版本组合（2026-XX 实测）：
>
> | 包                   | 版本     |
> | ------------------- | ------ |
> | langchain           | 1.4.4  |
> | langchain-core      | 1.6.9  |
> | langchain-community | 0.4.2  |
> | langgraph           | 1.2.14 |
> | dashscope           | 1.27.7 |
>
> **如果哪天代码突然跑不通了，先检查版本**，用上面这条命令重装一遍。
>
> 📌 顺带一提：`langchain-community` 官方已宣布停止维护（会提示 sunset 警告），  
> 未来会拆成独立的集成包。现阶段不影响学习使用，知道这件事即可。

---

## 今天要提交到 GitHub

**从第一天就养成习惯**，这是你简历上要放的链接。

```bash
cd C:\Users\He\Desktop\agent-30days
git init
git add .
git commit -m "Day 1: LLM 调用、工具调用、记忆管理"
```

⚠️ **提交前务必确认 `.env` 没有被提交**（里面有你的 Key）。  
新建一个 `.gitignore` 文件，写入：

```
.env
__pycache__/
*.pyc
```

---

## 明天的预告（Day 2）

今天你已经摸到了 Agent 的门。  
明天开始做**真正有价值的项目**：RAG 知识库问答——让 AI 基于你自己的文档回答问题。

**但今天先别急着往下。** 把这 3 个脚本跑通、把 4 个自测题答上来，  
比囫囵吞枣看 10 集视频有用得多。
