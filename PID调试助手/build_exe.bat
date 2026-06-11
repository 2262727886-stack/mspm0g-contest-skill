@echo off
echo ========================================
echo  MSPM0G PID Tuner - PyInstaller Build
echo ========================================
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
pyinstaller --onefile --windowed --name mspm0g-pid-tuner --add-data "config.example.json;." --hidden-import serial --hidden-import serial.tools.list_ports --hidden-import openai --hidden-import queue PID_DEMO/gui.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: dist\mspm0g-pid-tuner.exe
    echo Copy config.example.json to config.json and fill in your API key
) else (
    echo.
    echo FAILED. Install PyInstaller: pip install pyinstaller
)
pause
