@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
echo ============================================================
echo  Day 3 第2步 - RAG+Rerank 完整版（AB对比）
echo ============================================================
echo.
py "%~dp002_rag_rerank_qa.py"
echo.
echo ============================================================
pause
