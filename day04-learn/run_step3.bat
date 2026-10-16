@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set NO_PROXY=*
set HTTP_PROXY=
set HTTPS_PROXY=
echo ============================================================
echo  第3步 - session_state（端口8503）
echo ============================================================
echo.
echo  浏览器访问 http://localhost:8503
echo  停止：Ctrl+C
echo.
echo ============================================================
py "%~dp0_run.py" step3_state.py 8503
pause
