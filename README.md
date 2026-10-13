# LLM Agent 学习实践

> 从零开始学习大模型应用开发的学习记录与实践代码。
> 涵盖 LLM 调用、工具调用、对话记忆、RAG 检索增强、Rerank 重排。

**当前进度：Day 1 - Day 3 已完成**

---

## 目录结构

```
agent/
├── day01/                  LLM 基础：调用、工具、记忆
│   ├── 01_hello_llm.py         调用大模型，观察它的能力边界
│   ├── 02_tools_agent.py       给模型装工具（Agent 核心）
│   ├── 03_memory.py            多轮对话与记忆管理
│   ├── 04_practice.py          Python 语法填空练习
│   └── 05_basics.py            Python 基础（变量/列表/字典/类/装饰器）
│
├── day02/                  RAG 知识库问答系统
│   ├── 01_split.py             文档切分
│   ├── 02_embed_search.py      向量化 + 入库 + 检索
│   ├── 03_rag_qa.py            完整 RAG（带出处、防幻觉）
│   └── docs/                   知识库文档
│
├── day03/                  Rerank 两阶段检索
│   ├── 01_rerank.py            粗排 vs 精排 排序对比
│   ├── 02_rag_rerank_qa.py     RAG + Rerank 完整版 + A/B 对比
│   ├── 03_evaluate.py          召回质量评估（小知识库）
│   └── 04_evaluate_large.py    召回质量评估（大知识库）
│
├── GIT教程.md              Git 入门笔记
└── .gitignore              排除 .env 与临时文件
```

---

## 技术栈

| 类别 | 技术 |
|---|---|
| 语言 | Python 3.12 |
| 框架 | LangChain 1.4.4 / LangGraph 1.2.14 |
| 模型 | 通义千问（qwen-turbo） |
| 向量化 | DashScope text-embedding-v3 |
| 向量库 | ChromaDB |
| 重排 | DashScope gte-rerank-v2 |

---

## 学习内容

### Day 1 · LLM 基础

**核心认知：大模型是"接龙机器"**

通过对比实验理解大模型的两个硬伤：

| 问题 | 无工具 | 有工具 |
|---|---|---|
| 现在几点了？ | 编造"2025年4月5日" | 准确返回真实时间 |
| 123.456 × 789 = ? | 靠逐步试凑，冗长易错 | 调用计算器工具，精确 |

**结论**：大模型不会查实时信息、不会真算数。
给它装上**工具**（`@tool`），它才能"办事"——这就是 Agent。

**记忆的本质**：LLM 本身没有记忆，所谓"记忆"就是每次请求把历史 `messages` 列表一起发送。

### Day 2 · RAG 知识库问答

**核心认知：先查资料，再回答问题**

完整流程：
```
提问 → 向量化 → 向量库检索 Top-K → 拼上下文 → 喂给模型 → 生成答案
```

**三个关键设计：**

1. **文档切分**：`chunk_size=300`，`chunk_overlap=50`
   - 太大 → 一块混多主题，检索不准
   - 太小 → 语义不完整
   - 重叠 → 防止句子被从中间切断

2. **相似度阈值过滤（防幻觉）**
   - 实测：相关问题的距离在 0.55-0.90，无关问题在 1.25+
   - 设阈值 1.0，超过则判定"无相关资料"，**直接拒答，不调用大模型**

3. **答案可溯源**
   - 每个文本块携带 `source` 元数据
   - 回答时附上出处，便于人工核查

### Day 3 · Rerank 两阶段检索

**核心认知：粗排求快，精排求准**

```
向量检索（粗排，召回 15 个）→ Rerank（精排，精选 4 个）→ 喂给模型
```

**实测排序变化**（问题："chunk_overlap 设成多少合适？"）：

| 排名 | 粗排 | 精排 |
|---|---|---|
| 1 | 经验值：chunk_size 500-1000... | 经验值：chunk_size 500-1000... |
| 2 | 阶段二：检索与生成... | **常见踩坑点...** ← 从第3升上来 |
| 3 | 常见踩坑点... | 阶段二：检索与生成... ← 降到第3 |

**Rerank 纠正了向量检索的排序错误。**

---

## 实验数据

### Rerank 增益实验（A/B 对比）

**评估方法**：构建 8 题测试集，每题标注标准答案的关键词，
统计生成答案的关键词命中率。

| 知识库规模 | 无 Rerank | 有 Rerank | 提升 |
|---|---|---|---|
| **14 块**（小） | 81.2% | 81.2% | **+0.0 个百分点** |
| **272 块**（大） | 72.9% | 75.0% | **+2.1 个百分点** |

### 为什么小知识库上 Rerank 没有增益？

**因为粗排召回数已经接近知识库总量。**

```python
COARSE_K = 15        # 粗排召回 15 个
知识库总量 = 14 块    # ← 候选集等于全集
```

当候选集等于全集时，Rerank 无论怎么排，可选的就那些，无法体现差异。

**扩大到 272 块后，增益开始显现（+2.1 个百分点）。**

**结论**：Rerank 的价值随候选集规模增大而提升，
小规模知识库下向量粗排已经足够，不应无脑堆技术。

---

## 遇到的问题与解决（踩坑记录）

这些都是实际调试中遇到的真实问题：

### 1. LangChain 版本冲突导致 `create_agent` 无法导入

**报错**：
```
cannot import name 'ExecutionInfo' from 'langgraph.runtime'
```

**原因**：教程文档锁定了 `langchain==1.2.10`，但未锁定其依赖 `langgraph`，
pip 自动安装了不兼容的组合。

**解决**：不锁定版本，让 pip 自行求解兼容组合。
最终验证通过的版本：langchain 1.4.4 / langgraph 1.2.14。

### 2. `.env` 配置被系统环境变量覆盖

**现象**：修改 `.env` 中的 API Key 后仍报 `401 InvalidApiKey`。

**原因**：`load_dotenv()` 默认**不覆盖**已存在的环境变量。
系统中残留了一个旧的 `DASHSCOPE_API_KEY`，优先级更高，
导致 `.env` 里正确的 Key 被静默忽略。

**解决**：改为 `load_dotenv(override=True)`，让 `.env` 永远优先。

### 3. Windows cmd 编码问题

**报错**：
```
UnicodeEncodeError: 'gbk' codec can't encode character '\u2705'
```

**原因**：Windows cmd 默认 GBK 编码，遇到 emoji 直接崩溃，脚本中途退出。

**解决**：脚本内 `sys.stdout.reconfigure(encoding="utf-8")`，
`.bat` 中设置 `set PYTHONIOENCODING=utf-8`。

### 4. `.bat` 文件换行符导致命令解析失败

**现象**：双击 bat 报 `'xxx' 不是内部或外部命令`，中文显示乱码。

**原因**：文件被存为 LF 换行（Unix 格式），Windows cmd 需要 CRLF。

**解决**：以 CRLF + GBK 重新保存。

### 5. 时区库缺失

**报错**：`No time zone found with key Asia/Shanghai`

**解决**：改用固定 UTC+8 偏移 `timezone(timedelta(hours=8))`，
不依赖系统时区数据库。

---

## 如何运行

### 1. 安装依赖

```bash
pip install langchain langchain-community langchain-chroma \
    langchain-text-splitters chromadb dashscope python-dotenv
```

> 国内网络建议加镜像：
> `-i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com`

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的阿里云百炼 API Key：

```
DASHSCOPE_API_KEY=sk-xxxxxxxx
```

获取地址：https://bailian.console.aliyun.com/ → API-KEY 管理

### 3. 运行

每个 `dayXX` 目录下都有 `runN.bat`，双击即可运行对应脚本。

---

## 待办

- [ ] 为 RAG 系统添加 Streamlit 可视化界面
- [ ] 支持 PDF 文档上传
- [ ] 尝试混合检索（向量 + BM25 关键词）
- [ ] Query 改写优化
- [ ] Agent 项目（工具调用 + 多步推理）

---

## 说明

本项目为个人学习实践，参考了线上课程的内容框架，
代码在学习过程中逐步理解、调试、修改，
踩坑记录均为实际遇到并解决的问题。
