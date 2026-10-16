@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set NO_PROXY=*
set HTTP_PROXY=
set HTTPS_PROXY=
echo ============================================================
echo  第1步 - Streamlit 最小示例（端口8501）
echo ============================================================
echo.
echo  浏览器会自动打开，或手动访问 http://localhost:8501
echo  停止服务：在这个窗口按 Ctrl+C
echo.
echo ============================================================
py "%~dp0_run.py" step1_hello.py 8501
pause
