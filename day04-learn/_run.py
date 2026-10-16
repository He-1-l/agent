# -*- coding: utf-8 -*-
"""Streamlit 启动器（带代理清除）"""
import sys
import os
import subprocess

# 清除代理（重要：否则 Streamlit 启动后 API 调用会走死代理）
for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
            "ALL_PROXY", "all_proxy"):
    os.environ.pop(var, None)
os.environ["NO_PROXY"] = "*"
os.environ["PYTHONIOENCODING"] = "utf-8"

if len(sys.argv) < 2:
    print("用法: py _run.py <脚本名> [端口]")
    print("例如: py _run.py step1_hello.py")
    sys.exit(1)

script = sys.argv[1]
port = sys.argv[2] if len(sys.argv) > 2 else "8501"
base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, script)

if not os.path.exists(path):
    print(f"❌ 找不到脚本: {path}")
    sys.exit(1)

print(f"启动: {script}")
print(f"地址: http://localhost:{port}")
print("停止: 按 Ctrl+C")
print("-" * 50)

try:
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", path,
         "--server.port", port, "--server.headless", "true"],
        cwd=base,
    )
except KeyboardInterrupt:
    print("\n已停止")
