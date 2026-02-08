# =============================================================================
# Octavium Build & Sign Pipeline
# =============================================================================
# Builds the PyInstaller exe, signs it, compiles the InnoSetup installer,
# and signs the installer. Requires:
#   - Python venv with PyInstaller
#   - InnoSetup 6 installed (ISCC.exe on PATH or default location)
#   - Windows SDK signtool.exe on PATH
#   - EV certificate hardware token plugged in
#
# Usage:
#   .\scripts\build_installer.ps1                    # Full build + sign
#   .\scripts\build_installer.ps1 -SkipSign          # Build only, no signing
#   .\scripts\build_installer.ps1 -SkipBuild         # Sign + package only (reuse existing exe)
# =============================================================================

param(
    [switch]$SkipSign,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
$AppVersion = "1.1.1"

$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

$distDir       = Join-Path $projectRoot "dist"
$exePath       = Join-Path $distDir "Octavium.exe"
$installerName = "OctaviumSetup-$AppVersion.exe"
$installerPath = Join-Path $distDir $installerName
$issPath       = Join-Path $projectRoot "installer\octavium.iss"
$specPath      = Join-Path $projectRoot "scripts\Octavium.spec"

# Signing config — set OCTAVIUM_SIGN_THUMBPRINT env var or pass here
$thumbprint    = $env:OCTAVIUM_SIGN_THUMBPRINT
$timestampUrl  = "http://timestamp.digicert.com"

# InnoSetup compiler — check common install locations
$isccPaths = @(
    "ISCC.exe",  # On PATH
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
function Write-Step($msg) {
    Write-Host ""
    Write-Host "===== $msg =====" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success($msg) {
    Write-Host $msg -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host $msg -ForegroundColor Yellow
}

function Find-ISCC {
    foreach ($path in $isccPaths) {
        if (Get-Command $path -ErrorAction SilentlyContinue) {
            return $path
        }
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

function Sign-File($filePath) {
    if ($SkipSign) {
        Write-Warn "SKIP: Signing disabled (-SkipSign)"
        return
    }
    if (-not $thumbprint) {
        Write-Warn "WARNING: OCTAVIUM_SIGN_THUMBPRINT not set. Skipping signing."
        Write-Warn "  Set it with: `$env:OCTAVIUM_SIGN_THUMBPRINT = '<your-thumbprint>'"
        return
    }

    $fileName = Split-Path -Leaf $filePath
    Write-Host "Signing $fileName ..." -ForegroundColor Cyan
    Write-Host "  (Your hardware token will prompt for a PIN)" -ForegroundColor Yellow

    & signtool sign /tr $timestampUrl /td sha256 /fd sha256 /sha1 $thumbprint $filePath
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed for $fileName (exit code $LASTEXITCODE)"
    }

    Write-Host "Verifying signature on $fileName ..." -ForegroundColor Cyan
    & signtool verify /pa /v $filePath
    if ($LASTEXITCODE -ne 0) {
        throw "Signature verification failed for $fileName"
    }

    Write-Success "Signed and verified: $fileName"
}

# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
Set-Location $projectRoot
Write-Host ""
Write-Host "  Octavium Build Pipeline v$AppVersion" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host ""

# Step 1: Build exe with PyInstaller
if (-not $SkipBuild) {
    Write-Step "Step 1/4: Building Octavium.exe with PyInstaller"

    # Activate venv if not already
    if (-not $env:VIRTUAL_ENV) {
        Write-Host "Activating virtual environment..." -ForegroundColor Yellow
        & "$projectRoot\venv\Scripts\Activate.ps1"
    }

    # Check PyInstaller
    $pyinstaller = pip list 2>$null | Select-String "pyinstaller"
    if (-not $pyinstaller) {
        Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
        pip install pyinstaller
    }

    # Clean
    if (Test-Path (Join-Path $projectRoot "build")) {
        Remove-Item -Recurse -Force (Join-Path $projectRoot "build")
    }
    if (Test-Path $exePath) {
        Remove-Item -Force $exePath
    }

    # Build
    pyinstaller $specPath --clean --distpath $distDir --workpath (Join-Path $projectRoot "build")
    if (-not (Test-Path $exePath)) {
        throw "PyInstaller build failed — $exePath not found"
    }

    Write-Success "Built: $exePath"
} else {
    Write-Step "Step 1/4: Skipping build (-SkipBuild)"
    if (-not (Test-Path $exePath)) {
        throw "Cannot skip build — $exePath does not exist. Run without -SkipBuild first."
    }
    Write-Warn "Using existing: $exePath"
}

# Step 2: Sign the exe
Write-Step "Step 2/4: Signing Octavium.exe"
Sign-File $exePath

# Step 3: Fetch MIDI library, generate wizard images, compile installer
Write-Step "Step 3/4: Preparing assets & compiling installer"

# --- Fetch MIDI library if not present ---
$resourcesDir = Join-Path $projectRoot "resources"
$fetchScript  = Join-Path $projectRoot "scripts\fetch_midi_library.ps1"

$chordDirs = @()
$progDirs  = @()
if (Test-Path $resourcesDir) {
    $chordDirs = @(Get-ChildItem -Path $resourcesDir -Directory -Filter "free-midi-chords-*" -ErrorAction SilentlyContinue)
    $progDirs  = @(Get-ChildItem -Path $resourcesDir -Directory -Filter "free-midi-progressions-*" -ErrorAction SilentlyContinue)
}

if ($chordDirs.Count -eq 0) {
    Write-Host "MIDI chord library not found. Fetching from GitHub..." -ForegroundColor Yellow
    & $fetchScript
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "WARNING: Failed to fetch MIDI library. Installer will be built without it."
    }
    # Re-scan after fetch
    if (Test-Path $resourcesDir) {
        $chordDirs = @(Get-ChildItem -Path $resourcesDir -Directory -Filter "free-midi-chords-*" -ErrorAction SilentlyContinue)
        $progDirs  = @(Get-ChildItem -Path $resourcesDir -Directory -Filter "free-midi-progressions-*" -ErrorAction SilentlyContinue)
    }
} else {
    Write-Host "MIDI library found in resources/." -ForegroundColor Green
}

# Discover the actual directory names (use latest if multiple versions exist)
$midiChordsDir = ""
$midiProgressionsDir = ""
if ($chordDirs.Count -gt 0) {
    $midiChordsDir = ($chordDirs | Sort-Object Name -Descending | Select-Object -First 1).Name
    Write-Host "  Chords dir:       $midiChordsDir" -ForegroundColor Gray
}
if ($progDirs.Count -gt 0) {
    $midiProgressionsDir = ($progDirs | Sort-Object Name -Descending | Select-Object -First 1).Name
    Write-Host "  Progressions dir: $midiProgressionsDir" -ForegroundColor Gray
}

# --- Generate InnoSetup wizard branding bitmaps from the logo ---
$wizardLarge = Join-Path $projectRoot "installer\wizard_large.bmp"
$wizardSmall = Join-Path $projectRoot "installer\wizard_small.bmp"
if ((-not (Test-Path $wizardLarge)) -or (-not (Test-Path $wizardSmall))) {
    Write-Host "Generating wizard images from logo..." -ForegroundColor Cyan
    python (Join-Path $projectRoot "installer\generate_wizard_images.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to generate wizard images"
    }
} else {
    Write-Host "Wizard images already exist, skipping generation." -ForegroundColor Gray
}

# --- Compile installer with InnoSetup ---
$iscc = Find-ISCC
if (-not $iscc) {
    throw @"
InnoSetup 6 not found. Please install it from:
  https://jrsoftware.org/isdl.php

Expected locations:
  - ISCC.exe on PATH
  - ${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe
"@
}

Write-Host "Using ISCC: $iscc" -ForegroundColor Cyan

# Remove old installer if present
if (Test-Path $installerPath) {
    Remove-Item -Force $installerPath
}

# Build ISCC args — pass MIDI directory names as preprocessor defines
$isccArgs = @($issPath)
if ($midiChordsDir) {
    $isccArgs += "/DMidiChordsDir=$midiChordsDir"
}
if ($midiProgressionsDir) {
    $isccArgs += "/DMidiProgressionsDir=$midiProgressionsDir"
}

Write-Host "ISCC args: $($isccArgs -join ' ')" -ForegroundColor Gray
& $iscc @isccArgs
if ($LASTEXITCODE -ne 0) {
    throw "InnoSetup compilation failed (exit code $LASTEXITCODE)"
}

if (-not (Test-Path $installerPath)) {
    throw "Installer not found at expected path: $installerPath"
}

Write-Success "Built: $installerPath"

# Step 4: Sign the installer
Write-Step "Step 4/4: Signing installer"
Sign-File $installerPath

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  BUILD COMPLETE" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Executable:  $exePath" -ForegroundColor White
Write-Host "  Installer:   $installerPath" -ForegroundColor White
Write-Host ""

$exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
$installerSize = [math]::Round((Get-Item $installerPath).Length / 1MB, 1)
Write-Host "  Exe size:       $exeSize MB" -ForegroundColor Gray
Write-Host "  Installer size: $installerSize MB" -ForegroundColor Gray

if ($SkipSign) {
    Write-Warn ""
    Write-Warn "  WARNING: Files are NOT signed. Run without -SkipSign for release builds."
}

Write-Host ""
