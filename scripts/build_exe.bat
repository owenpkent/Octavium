@echo off
REM Build script for Octavium executable

echo Building Octavium executable...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install PyInstaller if needed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build the executable
echo Building executable with PyInstaller...
pyinstaller Octavium.spec --clean

REM Check if build was successful
if exist dist\Octavium.exe (
    echo.
    echo Build successful!
    echo Executable location: dist\Octavium.exe
    echo.
    echo You can now run the application by double-clicking dist\Octavium.exe
) else (
    echo.
    echo Build failed. Please check the output above for errors.
    exit /b 1
)

pause
