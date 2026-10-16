@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set NO_PROXY=*
set HTTP_PROXY=
set HTTPS_PROXY=
echo ============================================================
echo  第4步 - 完整 RAG 问答界面（端口8504）
echo ============================================================
echo.
echo  浏览器访问 http://localhost:8504
echo  停止：Ctrl+C
echo.
echo ============================================================
py "%~dp0_run.py" step4_rag_app.py 8504
pause
