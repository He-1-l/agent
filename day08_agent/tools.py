import json
import os
import re
import sqlite3

from rag import retrieve

_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.db")

_ROWS = [
    ("张伟", "A-01", "morning", "violated"),
    ("张伟", "A-02", "morning", "violated"),
    ("张伟", "A-03", "morning", "violated"),
    ("李娜", "B-01", "evening", "violated"),
    ("李娜", "B-02", "evening", "violated"),
    ("王强", "C-01", "afternoon", "violated"),
    ("赵敏", "A-05", "morning", "completed"),
    ("赵敏", "A-06", "morning", "completed"),
    ("孙磊", "B-03", "afternoon", "completed"),
    ("孙磊", "B-04", "evening", "completed"),
    ("周婷", "C-02", "afternoon", "completed"),
    ("周婷", "C-03", "afternoon", "completed"),
    ("吴昊", "A-07", "evening", "completed"),
    ("吴昊", "A-08", "morning", "cancelled"),
    ("郑爽", "B-05", "afternoon", "completed"),
    ("郑爽", "B-06", "evening", "completed"),
]

_METRIC_SQL = {
    "violation_by_slot": """
        SELECT slot, COUNT(*) AS cnt FROM reservation
        WHERE status = 'violated'
        GROUP BY slot ORDER BY cnt DESC
    """,
    "violator_ranking": """
        SELECT user_name, COUNT(*) AS cnt FROM reservation
        WHERE status = 'violated'
        GROUP BY user_name ORDER BY cnt DESC
    """,
    "usage_by_slot": """
        SELECT slot, COUNT(*) AS cnt FROM reservation
        GROUP BY slot ORDER BY cnt DESC
    """,
}


def _ensure_db():
    if os.path.exists(_DB):
        return
    conn = sqlite3.connect(_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reservation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            seat_id TEXT NOT NULL,
            slot TEXT NOT NULL,
            status TEXT NOT NULL
        );
    """)
    conn.executemany(
        "INSERT INTO reservation (user_name, seat_id, slot, status) VALUES (?,?,?,?)",
        _ROWS,
    )
    conn.commit()
    conn.close()


def search_rules(query):
    hits = [(text, dist) for text, dist in retrieve(query) if dist < 0.85]

    if not hits:
        return json.dumps({"found": False, "hint": "知识库无相关内容"}, ensure_ascii=False)

    docs = [{"content": t, "score": round(1 - d, 3)} for t, d in hits]
    return json.dumps({"found": True, "docs": docs}, ensure_ascii=False)


def query_stats(metric):
    sql = _METRIC_SQL.get(metric)
    if sql is None:
        return json.dumps(
            {"error": f"不支持的 metric: {metric}", "available": list(_METRIC_SQL)},
            ensure_ascii=False,
        )

    _ensure_db()
    conn = sqlite3.connect(_DB)
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return json.dumps({"found": False, "metric": metric}, ensure_ascii=False)

    data = [dict(zip(cols, row)) for row in rows]
    return json.dumps({"found": True, "metric": metric, "rows": data}, ensure_ascii=False)


def calculate(expression):
    if not re.fullmatch(r"[0-9+\-*/(). ]+", expression):
        return json.dumps({"error": "表达式只允许数字与 + - * / ( )"}, ensure_ascii=False)
    try:
        value = eval(expression, {"__builtins__": {}}, {})
    except Exception as exc:
        return json.dumps({"error": f"无法计算: {exc}"}, ensure_ascii=False)
    return json.dumps({"expression": expression, "result": value}, ensure_ascii=False)


REGISTRY = {
    "search_rules": search_rules,
    "query_stats": query_stats,
    "calculate": calculate,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_rules",
            "description": (
                "在自习室预约规则文档中做语义检索。用于回答制度、条款、流程类问题，"
                "例如签到时限、信用分规则、违约扣分、取消规则。"
                "不用于查询统计数字，也不用于算术计算。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "检索用的短句，尽量贴近规则原文用词",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_stats",
            "description": (
                "查询预约数据库的结构化统计，返回精确数字。"
                "用于回答违约次数、违约排名、各时段预约量这类聚合问题。"
                "不用于回答规则条款。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": list(_METRIC_SQL.keys()),
                        "description": (
                            "violation_by_slot=各时段违约次数；"
                            "violator_ranking=违约用户排名；"
                            "usage_by_slot=各时段预约总量"
                        ),
                    }
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "执行精确算术运算。任何涉及数字加减乘除的问题都必须调用本工具，不要心算。"
                "只支持数字与 + - * / ( )。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "只含数字与 + - * / ( ) 的表达式，例如 100-3*5",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]
