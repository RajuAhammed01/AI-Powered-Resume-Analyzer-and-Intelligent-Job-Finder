@echo off
setlocal enabledelayedexpansion
title JobSnap AI - Automatic One-Click Launcher
color 0B

echo ========================================================================
echo        JobSnap AI: Resume Analyzer and Intelligent Job Finder
echo                    Automatic One-Click Launcher
echo ========================================================================
echo.

cd /d "%~dp0"

:: 1. Detect Python / Virtual Environment
if exist "venv\Scripts\python.exe" (
    echo [*] Found existing virtual environment in .\venv
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    echo [!] Virtual environment not found. Checking system Python...
    where py >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=py -3.12"
    ) else (
        where python >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            set "PYTHON_EXE=python"
        ) else (
            color 0C
            echo [X] ERROR: Python was not found on your system PATH!
            echo     Please install Python 3.10, 3.11, or 3.12 from python.org
            echo     and ensure "Add Python to PATH" is checked during setup.
            echo.
            pause
            exit /b 1
        )
    )
)

:: 2. Launch start_app.py
echo [*] Initializing automated bootstrapper...
echo.
%PYTHON_EXE% start_app.py

if %ERRORLEVEL% neq 0 (
    color 0C
    echo.
    echo [X] JobSnap stopped with an exit code: %ERRORLEVEL%
    pause
)

exit /b %ERRORLEVEL%

