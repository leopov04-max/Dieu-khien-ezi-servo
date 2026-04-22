@echo off
title Dual Serial Monitor
echo ============================================
echo   Dual Serial Monitor - STM32 + Arduino
echo ============================================
echo.

:: Cai thu vien neu chua co
echo [1/2] Kiem tra thu vien Python...
pip install pyserial matplotlib --quiet

echo [2/2] Khoi chay giao dien...
echo.
python "%~dp0dual_monitor.py"

if %errorlevel% neq 0 (
    echo.
    echo [LOI] Khong chay duoc. Kiem tra lai Python da duoc cai chua.
    echo       Tai Python tai: https://www.python.org/downloads/
    pause
)
