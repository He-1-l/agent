import json
import os
import sys

from openai import OpenAI

from tools import REGISTRY, TOOLS

MODEL = os.getenv("AGENT_MODEL", "qwen-plus")
BASE_URL = os.getenv("AGENT_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

MAX_STEPS = 8
MAX_TOOL_CHARS = 2000
MAX_TOTAL_TOKENS = 20000

SYSTEM_PROMPT = """你是自习室管理助手，可以调用工具获取信息后回答用户问题。

工作方式：
1. 先判断问题需不需要工具。闲聊、常识、你已确定的内容直接回答，不要为了用工具而用工具。
2. 需要多个信息时按顺序多步调用：拿到上一步结果，再决定下一步调什么。
3. 制度、条款、流程类问题 -> search_rules
4. 违约次数、违约排名、各时段预约量等统计数字 -> query_stats
5. 任何加减乘除 -> calculate，禁止心算
6. 工具返回 found=false 或 error 时，如实告诉用户资料不足或查询失败，严禁编造数字。
7. 最终回答要说明数据来源（引用了哪条规则、哪张表的统计）。"""


def _client():
    key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "缺少 DASHSCOPE_API_KEY。\n"
            "  Windows: set DASHSCOPE_API_KEY=sk-xxx\n"
            "  PowerShell: $env:DASHSCOPE_API_KEY=\"sk-xxx\""
        )
    return OpenAI(api_key=key, base_url=BASE_URL)


def _safe_call(name, args):
    fn = REGISTRY.get(name)
    if fn is None:
        return json.dumps(
            {"error": f"未知工具 {name}", "available": list(REGISTRY)},
            ensure_ascii=False,
        )
    try:
        return str(fn(**args))[:MAX_TOOL_CHARS]
    except TypeError as exc:
        return json.dumps({"error": f"参数不匹配: {exc}"}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False)


def run_agent(query, verbose=False):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    client = _client()
    trace = []
    total_tokens = 0
    last_sig = None

    for step in range(1, MAX_STEPS + 1):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0,
        )
        total_tokens += resp.usage.total_tokens
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return {
                "answer": msg.content or "",
                "steps": step,
                "tokens": total_tokens,
                "trace": trace,
                "stopped": "final",
            }

        messages.append(msg.model_dump(exclude_none=True))

        for call in msg.tool_calls:
            name = call.function.name
            raw = call.function.arguments or "{}"
            try:
                args = json.loads(raw)
            except json.JSONDecodeError:
                args = {}
                result = json.dumps({"error": "参数不是合法 JSON"}, ensure_ascii=False)
            else:
                sig = (name, json.dumps(args, sort_keys=True, ensure_ascii=False))
                if sig == last_sig:
                    result = json.dumps(
                        {"error": "你刚刚用完全相同的参数调用过该工具，请换参数或直接回答"},
                        ensure_ascii=False,
                    )
                else:
                    last_sig = sig
                    result = _safe_call(name, args)

            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
            trace.append({"step": step, "tool": name, "args": args, "result": result[:300]})
            if verbose:
                print(f"  [step {step}] {name}({json.dumps(args, ensure_ascii=False)})")
                print(f"           -> {result[:160]}")

        if total_tokens > MAX_TOTAL_TOKENS:
            return {
                "answer": "本次对话消耗已超过上限，请把问题拆小一些再问。",
                "steps": step,
                "tokens": total_tokens,
                "trace": trace,
                "stopped": "token_limit",
            }

    return {
        "answer": "已达到最大推理步数仍未得出结论，建议把问题拆成几个小问题。",
        "steps": MAX_STEPS,
        "tokens": total_tokens,
        "trace": trace,
        "stopped": "max_steps",
    }


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "2026年10月违约最多的是谁？按规则他的信用分还剩多少？"
    print(f"Q: {q}\n")
    out = run_agent(q, verbose=True)
    print(f"\nA: {out['answer']}")
    print(f"\n[步数 {out['steps']} | tokens {out['tokens']} | 结束原因 {out['stopped']}]")
