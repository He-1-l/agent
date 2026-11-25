# 自习室座位预约系统（毕业设计）

> 高校自习室座位预约系统 · 后端 FastAPI + SQLAlchemy + Redis + WebSocket，前端 Vue3 + Vite + Element Plus
> 这是本仓库中唯一一个**完整业务项目**，其余 `dayXX/` 目录是学习练习。

---

## 一、这个项目解决什么问题

高校自习室座位靠抢，典型问题是**超卖**：同一时刻大量学生抢同一个座位，系统判断"还有空位"、大家都写库成功，结果一个座位被多人预约。

本项目围绕这个问题做了三层防护，并用压测脚本做了对照实验验证效果。

---

## 二、三层防超卖（核心设计）

```
第 1 层：业务前置校验（services.py reserve()）
        挡掉本来就不该成功的请求：座位维修中、信用分不足、每日超限、时段已过

第 2 层：Redis Lua 原子占位（cache.py）
        Bitmap 存座位状态，seat_id 当比特偏移，100 座位仅 13 字节
        查 + 占 在同一个 Lua 脚本里完成，中间不会插入其他请求

第 3 层：数据库四字段联合唯一索引（models.py Reservation）
        UniqueConstraint(seat_id, reserve_date, slot_id, is_active)
        前两层都可能失效，唯一索引不会 —— 这是最终兜底
```

**关键细节：`is_active` 取消时置 NULL 而不是 0。**

因为唯一索引对 NULL 不判重、对 0 会判重。置 0 的话，同一座位同一时段取消两次，第二条就撞 1062 错误。置 NULL 才能既保留历史记录，又允许重新预约。

**降级机制：** Redis 未配置或连接失败时，`acquire()` 返回 `None`（不是报错），业务层自动走纯数据库路径，功能不受影响。

---

## 三、压测数据（对照实验）

| 场景 | 座位数 | 并发 | 成功 | 超卖 |
|---|---|---|---|---|
| nolock（无唯一索引） | 100 | 200 | 186 | **86** |
| db（有唯一索引） | 40 | 500 | 40 | **0**（460 个被正确拒绝） |

复现方式：

```bash
cd backend
python -m scripts.benchmark --mode nolock --concurrency 200 --seats 100
python -m scripts.benchmark --mode db --users 200 --seats 100
```

---

## 四、数据模型（11 张表）

按 2-3-1-3-2 分组：

| 层 | 张数 | 表 |
|---|---|---|
| 主体层 | 2 | Student、Admin |
| 空间层 | 3 | Building → Room → Seat |
| 时间层 | 1 | TimeSlot |
| 交易层 | 3 | Reservation、CheckinRecord、CreditLog |
| 辅助层 | 2 | Waitlist、Announcement |

**预约状态机（5 态）：** 0 待签到 / 1 已签到 / 2 已完成 / 3 已取消 / 4 违约

---

## 五、快速启动

### 后端（零配置可跑，默认 SQLite）

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m scripts.init_db
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000/demo 是零依赖演示页，http://127.0.0.1:8000/docs 是 Swagger 接口文档。

**演示账号：**

| 角色 | 账号 | 密码 |
|---|---|---|
| 学生 | 2022010101 | 123456 |
| 管理员 | admin | 123456 |

### 前端（可选）

```bash
cd frontend
npm install
npm run dev
```

> 如果 `npm run build` 报 `esbuild ... Access is denied`，把 TEMP 指到别处再构建：
> ```powershell
> $env:TEMP = "D:\tmp-esbuild"; $env:TMP = $env:TEMP
> npm run build
> ```

### 启用 Redis（可选，用于演示降级）

```bash
set REDIS_URL=redis://127.0.0.1:6379/0
uvicorn app.main:app --reload
```

不配 `REDIS_URL` 时启动日志会打印「缓存层关闭，使用数据库乐观锁降级」，系统照样能预约。

---

## 六、目录结构

```
graduation-project/
├── backend/
│   ├── app/
│   │   ├── main.py           应用入口、CORS、后台清理任务
│   │   ├── models.py         11 张表的 ORM 定义
│   │   ├── services.py       核心业务：reserve / cancel / checkin / checkout
│   │   ├── cache.py          Redis Bitmap + Lua 原子占位
│   │   ├── security.py       手写 JWT + PBKDF2（不依赖 PyJWT/bcrypt）
│   │   ├── db.py             连接池与会话管理
│   │   ├── config.py         全部配置走环境变量
│   │   ├── routers/          auth / rooms / reservations / admin / ws
│   │   └── static/demo.html  零依赖演示页（单文件，631 行）
│   ├── scripts/
│   │   ├── init_db.py        建表 + 种子数据
│   │   └── benchmark.py      并发对照实验脚本
│   └── requirements.txt
└── frontend/
    └── src/                  Vue3 页面：登录、选座、我的预约、管理端大屏
```

---

## 七、已知缺陷（4 处，未修复）

| # | 缺陷 | 影响 |
|---|---|---|
| 1 | 超时清理任务 60 秒轮询，中间有死窗口 | 窗口内签到会报「座位已释放」但实际还没释放 |
| 2 | `expire_no_show()` 的 `db.commit()` 在循环外 | 失败会导致缓存与数据库不一致 |
| 3 | `CANCEL_PENALTY` 默认 0 | 取消预约无惩罚，等于没有约束 |
| 4 | 缺少自动签退 | `expire_no_show()` 只筛 `status == 0`，已签到未签退的记录永远停在 `status=1`，锁住该座位该时段、占用当日额度、`duration_minutes` 永远 NULL |

---

## 八、关于代码来源

本项目是本人毕业设计，需求、表结构、核心业务逻辑由本人确定。

开发过程中使用了 AI 编程工具辅助编写，**每一段核心逻辑都经过阅读、复现与验证**——例如三层防超卖的 Lua 脚本、唯一索引的 `is_active` 设计、压测脚本的对照实验，都能从设计动机讲到实现细节。

---

## 九、相关文档

- 论文与答辩材料在毕设目录的 `05-毕业论文/`、`06-答辩PPT/`
- 技术名词手册在 `07-技术名词手册/`
