@echo off
title JobSnap AI - Graphical Launcher
cd /d "%~dp0"

if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" launcher.pyw
) else if exist "venv\Scripts\python.exe" (
    start "" "venv\Scripts\python.exe" launcher.py
) else (
    start "" pythonw launcher.pyw
)

