# -*- coding: utf-8 -*-
"""WebSocket：座位状态实时推送。

浏览器订阅 /ws/rooms/{room_id}，服务端在预约、签到、释放时
推送 {event, seat_id, date, slot_id}，前端只重绘该座位，不整页刷新。
"""
import asyncio
from typing import Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["实时推送"])


class ConnectionManager:
    def __init__(self) -> None:
        self.active: Dict[int, Set[WebSocket]] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def connect(self, room_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self.active.setdefault(room_id, set()).add(ws)

    def disconnect(self, room_id: int, ws: WebSocket) -> None:
        conns = self.active.get(room_id)
        if conns:
            conns.discard(ws)
            if not conns:
                self.active.pop(room_id, None)

    async def broadcast(self, room_id: int, payload: dict) -> None:
        for ws in list(self.active.get(room_id, ())):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                self.disconnect(room_id, ws)

    def broadcast_threadsafe(self, room_id: int, payload: dict) -> None:
        """供同步的业务代码调用：投递到事件循环执行。"""
        if self.loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(room_id, payload), self.loop)


manager = ConnectionManager()


@router.websocket("/ws/rooms/{room_id}")
async def room_socket(ws: WebSocket, room_id: int):
    await manager.connect(room_id, ws)
    try:
        await ws.send_json({"event": "connected", "room_id": room_id})
        while True:
            # 客户端心跳，服务端原样回传；无消息时阻塞等待
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(room_id, ws)
    except Exception:  # noqa: BLE001
        manager.disconnect(room_id, ws)
