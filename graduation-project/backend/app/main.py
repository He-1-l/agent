# -*- coding: utf-8 -*-
"""应用入口：FastAPI 实例、路由注册、启动初始化、后台清理任务。"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from . import services
from .cache import cache
from .config import settings
from .db import SessionLocal, init_db
from .routers import admin, auth, reservations, rooms, ws

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表、连缓存、绑定事件循环、拉起清理任务
    init_db()
    cache.connect()
    ws.manager.bind_loop(asyncio.get_running_loop())

    async def cleaner():
        """每 60 秒扫描一次超时未签到的预约并释放座位。"""
        while True:
            try:
                await asyncio.sleep(60)
                db = SessionLocal()
                try:
                    n = services.expire_no_show(db)
                    if n:
                        print(f"[cleaner] 释放超时座位 {n} 个 @ {datetime.now():%H:%M:%S}")
                finally:
                    db.close()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                print(f"[cleaner] 异常：{exc}")

    task = asyncio.create_task(cleaner())
    yield
    task.cancel()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="高校自习室座位预约系统 —— 毕业设计演示后端",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(reservations.router)
app.include_router(admin.router)
app.include_router(ws.router)


@app.get("/", include_in_schema=False)
def index():
    # 打开根路径直接进入演示页面，方便非技术用户查看效果
    return RedirectResponse(url="/demo")


@app.get("/demo", include_in_schema=False)
def demo_page():
    """零依赖的演示页面：不需要 Node.js 与前端构建，直接由后端返回单个 HTML。"""
    page = Path(__file__).resolve().parent / "static" / "demo.html"
    if not page.exists():
        return RedirectResponse(url="/docs")
    return FileResponse(page, media_type="text/html; charset=utf-8")


@app.get("/api/health", tags=["系统"], summary="健康检查")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "cache": "redis" if cache.available else "degraded",
        "time": datetime.now().isoformat(timespec="seconds"),
    }
