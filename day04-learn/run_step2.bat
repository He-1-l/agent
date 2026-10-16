@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set NO_PROXY=*
set HTTP_PROXY=
set HTTPS_PROXY=
echo ============================================================
echo  第2步 - 输入与响应（端口8502）
echo ============================================================
echo.
echo  浏览器会自动打开，或手动访问 http://localhost:8502
echo  停止服务：在这个窗口按 Ctrl+C
echo.
echo ============================================================
py "%~dp0_run.py" step2_input.py 8502
pause
