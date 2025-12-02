# Build script for Octavium executable
# This script builds a standalone Windows executable using PyInstaller

Write-Host "Building Octavium executable..." -ForegroundColor Green
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
}

# Install PyInstaller if not already installed
Write-Host "Checking for PyInstaller..." -ForegroundColor Cyan
$pyinstaller = pip list | Select-String "pyinstaller"
if (-not $pyinstaller) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Cyan
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
}

# Build the executable
Write-Host "Building executable with PyInstaller..." -ForegroundColor Cyan
pyinstaller Octavium.spec --clean

# Check if build was successful
if (Test-Path "dist\Octavium.exe") {
    Write-Host ""
    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host "Executable location: dist\Octavium.exe" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run the application by double-clicking dist\Octavium.exe" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Build failed. Please check the output above for errors." -ForegroundColor Red
    exit 1
}
