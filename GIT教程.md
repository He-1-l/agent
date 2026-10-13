# Git 入门 · 今晚 20 分钟学会

> 目标：理解 Git 在干什么，能独立完成「提交 + 上传」。
> 面试会问 Git，这是硬技能。

---

## 零、先搞清楚三个概念

**别急着敲命令，先把这三个分清楚。分不清，后面全是懵的。**

```
工作区（Working Directory）
    ↓  git add
暂存区（Staging Area）
    ↓  git commit
本地仓库（Local Repository）
    ↓  git push
远程仓库（Remote，就是 GitHub）
```

**用生活例子类比：**

| Git 概念 | 类比 | 说明 |
|---|---|---|
| **工作区** | 你桌上的草稿 | 正在改的文件 |
| **`git add`** | 把要交的作业挑出来 | **选择**哪些改动要提交 |
| **暂存区** | 挑好的那一摞 | 待提交的内容 |
| **`git commit`** | 装订成册 + 写标题 | 存档，形成历史记录 |
| **`git push`** | 交到老师办公室 | 上传到 GitHub |

**关键理解**：
- `add` ≠ 提交，它只是**挑选**
- `commit` 是**存到本地**，还没上传
- `push` 才**上传到 GitHub**

---

## 一、为什么要分区？（面试会问）

**因为一次改动可能包含多件事。**

比如你今天改了三个文件：
- `01_split.py`（修了个 bug）
- `README.md`（写了文档）
- `03_rag.py`（加了新功能）

**这三件事应该分三次提交**，而不是混在一起。这样以后回溯历史时，能清楚看到"哪次改了什么"。

**`git add` 就是让你能"挑着提交"。**

---

## 二、常用命令（就这 8 个）

### 1. 查看状态（最常用，每次操作前先看）

```bash
git status
```

**输出示例：**
```
On branch main
Untracked files:
        day01/
        day02/
nothing added to commit
```

- `Untracked` = Git 还没管理的文件（新文件）
- `Modified` = 改过的文件
- `Changes to be committed` = 已 add，待提交

### 2. 添加文件到暂存区

```bash
git add 文件名          # 添加单个文件
git add .              # 添加所有改动（最常用）
git add day01/         # 添加整个目录
```

### 3. 提交（形成一次记录）

```bash
git commit -m "提交说明"
```

**`-m` 后面是提交说明，必须写清楚做了什么。**

**好的说明 vs 坏的说明：**

```bash
❌ git commit -m "更新"
❌ git commit -m "改了一下"
✅ git commit -m "Day 2: 实现 RAG 知识库问答，含阈值过滤防幻觉"
```

**面试官会看你的提交记录，说明写得好 = 有协作意识。**

### 4. 查看提交历史

```bash
git log --oneline          # 简洁版
git log                    # 详细版
```

### 5. 查看改了什么

```bash
git diff                   # 工作区 vs 暂存区
git diff --staged          # 暂存区 vs 上次提交
```

### 6. 初始化仓库（每个项目只做一次）

```bash
git init
```

### 7. 关联远程仓库

```bash
git remote add origin https://github.com/你的用户名/仓库名.git
```

### 8. 上传

```bash
git push -u origin main    # 第一次（-u 记住关联）
git push                   # 之后简写
```

---

## 三、完整流程（照着做）

### 前提：先在 GitHub 网页上建仓库

1. 打开 https://github.com/new
2. Repository name 填：`agent-30days`
3. **选 Public**（公开，面试官才能看）
4. **不要勾** "Add a README file"（我们本地已经有了，勾了会冲突）
5. 点 Create repository

### 然后在本地执行

```bash
# 1. 进入项目目录
cd C:\Users\He\Desktop\agent-30days

# 2. 初始化（只做一次）
git init

# 3. ⚠️ 关键：先确认 .env 不会被提交
git status
#    检查输出里【没有】.env 文件

# 4. 添加所有文件
git add .

# 5. 提交
git commit -m "Day 1-3: LLM调用 / RAG / Rerank 学习实践"

# 6. 关联远程仓库（换成你的用户名）
git remote add origin https://github.com/你的用户名/agent-30days.git

# 7. 上传
git push -u origin main
```

---

## 四、⚠️ 最重要的一步：别把 Key 传上去

**`.env` 里有你的 API Key，一旦传到 GitHub，会被爬虫扫到并盗用。**

**你的项目里已经有 `.gitignore`，内容是：**
```
.env
__pycache__/
*.pyc
.venv/
```

**但是！`.gitignore` 只对"还没被 Git 跟踪的文件"生效。**

### 必须在 `git add` 之前检查

```bash
git status
```

**看输出里有没有 `.env`：**

```
✅ 正确（.env 不在列表里）：
    Untracked files:
            day01/
            day02/
            day03/
            .gitignore

❌ 危险（.env 在列表里）：
    Untracked files:
            .env          ← 这个必须处理！
```

**如果 `.env` 出现了，执行：**
```bash
git rm --cached .env        # 从 Git 移除（不删本地文件）
```
然后确认 `.gitignore` 里有 `.env`。

### 如果已经误传了怎么办

1. 立刻去阿里云百炼**删除那个 Key**，重新生成一个
2. 更新本地 `.env`
3. 用 `git rm --cached .env` 移除，再提交

**Key 泄露是真实事故**，每年都有人因此被扣光余额。

---

## 五、常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| `not a git repository` | 没初始化 | 先 `git init` |
| `Please tell me who you are` | 没配用户名邮箱 | `git config --global user.name "名字"` |
| `failed to push some refs` | 远程有本地没有的内容 | `git pull --rebase origin main` 再 push |
| `Authentication failed` | 密码错 | GitHub 现在要用 **Token**，不是密码 |
| `src refspec main does not match any` | 还没提交过 | 先 `git commit` |
| `git: command not found` | PATH 没生效 | **关掉窗口重新打开** |

### 关于 GitHub 认证（重要）

**GitHub 2021 年起不再支持密码推送，必须用 Personal Access Token。**

**生成步骤：**
1. GitHub → 右上角头像 → Settings
2. 左侧最下 → Developer settings
3. Personal access tokens → **Tokens (classic)**
4. Generate new token (classic)
5. 勾选 **`repo`** 权限
6. 生成后**立刻复制**（只显示一次）
7. push 时用户名填 GitHub 用户名，**密码位置粘贴这个 Token**

---

## 六、今晚的练习任务

**目标：把 agent-30days 传上 GitHub。**

**步骤：**

1. **在 GitHub 网页建仓库** `agent-30days`（Public，不勾 README）
2. **打开 PowerShell**（Win+R 输入 `powershell`）
3. **依次执行：**

```powershell
cd C:\Users\He\Desktop\agent-30days
git init
git status
```

**在这里停下来，把 `git status` 的输出发给我。**

我要确认：
- `.env` 有没有被包含
- `chroma_db` 这些大文件要不要排除（向量库不该传）

**确认无误后，再继续 add / commit / push。**

---

## 七、面试会问的 Git 问题

**Q1：`git add` 和 `git commit` 的区别？**
> `add` 把改动放进暂存区（挑选），`commit` 把暂存区的内容存成一次历史记录（存档）。分开是为了能把不同性质的改动分开提交。

**Q2：怎么撤销一次提交？**
> 如果还没 push：`git reset --soft HEAD~1`（撤销提交但保留改动）。
> 如果已 push：用 `git revert` 生成一个反向提交，不要用 reset 改写已推送的历史。

**Q3：分支是干什么的？**
> 分支让多人并行开发互不干扰。每个人在自己的分支上改，完成后合并到主分支。

**Q4：合并冲突怎么解决？**
> Git 会在冲突文件里标出 `<<<<<<<` 和 `>>>>>>>`，手动选择保留哪部分，然后 `git add` 标记为已解决，再 commit。

---

## 八、你现在做

**先在 GitHub 网页建好仓库，然后执行 `git init` 和 `git status`，把输出发我。**

我帮你检查有没有踩坑（尤其是 `.env` 泄露）。
