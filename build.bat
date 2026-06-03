@echo off
echo =============================================
echo AutoKey Windows Standalone Executable Builder
echo =============================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python is not installed or not in your system PATH.
    echo Please install Python and check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Install PyInstaller
echo [1/3] Checking and installing PyInstaller...
python -m pip install --upgrade pip
python -m pip install pyinstaller

:: Compile the executable
echo [2/3] Compiling standalone app using PyInstaller...
:: On Windows, PyInstaller expects a semicolon (;) separator for --add-data
python -m PyInstaller --onefile --noconsole --add-data "web;web" --name "AutoKey" app.py

if %errorlevel% neq 0 (
    echo ❌ Error: PyInstaller build failed!
    pause
    exit /b 1
)

echo [3/3] Build completed successfully!
echo 👉 The executable is located at: dist\AutoKey.exe
echo 👉 Double-click it to start the background process and launch the browser control page!
echo =============================================
pause
