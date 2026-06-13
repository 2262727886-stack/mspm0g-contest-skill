@echo off
chcp 936 >nul
setlocal enabledelayedexpansion

title MSPM0G PID Tuner Build Tool
color 0A

echo.
echo ========================================
echo   MSPM0G PID Tuner - Build Tool
echo ========================================
echo.

echo [1/5] Check Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Python not found!
    pause
    exit /b 1
)
echo       Python OK
echo.

echo [2/5] Install dependencies...
pip install pyserial openai pyinstaller -q 2>nul
echo       Dependencies OK
echo.

echo [3/5] Clean old files...
if exist dist rmdir /s /q dist 2>nul
if exist build rmdir /s /q build 2>nul
if exist release rmdir /s /q release 2>nul
echo       Clean OK
echo.

echo [4/5] Build EXE (1-3 minutes)...
echo.

pyinstaller --onefile --windowed --name MSPM0G_PID_Tuner --add-data "config.example.json;." --hidden-import serial --hidden-import serial.tools.list_ports --hidden-import openai --hidden-import queue --hidden-import tkinter --hidden-import tkinter.ttk --clean --noconfirm PID_DEMO/gui.py 2>nul

if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Build failed!
    pause
    exit /b 1
)
echo       Build OK
echo.

echo [5/5] Create release...
mkdir release 2>nul
copy /y "dist\MSPM0G_PID_Tuner.exe" "release\" >nul

copy /y "dist\config.json" "release\config.json" >nul 2>&1
if not exist "release\config.json" (
    echo {"LLM_API_KEY":"sk-your-key-here","LLM_API_BASE_URL":"https://api.deepseek.com","LLM_PROVIDER":"openai","LLM_MODEL_NAME":"deepseek-v4-pro","SERIAL_PORT":"AUTO","BAUD_RATE":115200} > "release\config.json"
)

echo MSPM0G PID Tuner v1.0 > "release\README.txt"
echo ==================== >> "release\README.txt"
echo. >> "release\README.txt"
echo 1. Run MSPM0G_PID_Tuner.exe >> "release\README.txt"
echo 2. Connect serial port >> "release\README.txt"
echo 3. Start tuning >> "release\README.txt"

echo       Release OK
echo.

echo ========================================
echo   BUILD SUCCESS!
echo.
echo   Output: release\
echo   Files:
echo     - MSPM0G_PID_Tuner.exe
echo     - config.json
echo     - README.txt
echo ========================================
echo.

start explorer release

pause
