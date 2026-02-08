# =============================================================================
# Fetch MIDI Chord Library for Octavium
# =============================================================================
# Downloads the free-midi-chords library from GitHub into the resources/ folder.
# Used for both development setup and the installer build pipeline.
#
# Source: https://github.com/ldrolez/free-midi-chords
# License: MIT (Ludovic Drolez)
#
# Usage:
#   .\scripts\fetch_midi_library.ps1             # Download latest release
#   .\scripts\fetch_midi_library.ps1 -Force      # Re-download even if present
# =============================================================================

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
$repoOwner = "ldrolez"
$repoName  = "free-midi-chords"
$apiUrl    = "https://api.github.com/repos/$repoOwner/$repoName/releases/latest"

$scriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot  = Split-Path -Parent $scriptDir
$resourcesDir = Join-Path $projectRoot "resources"

# ---------------------------------------------------------------------------
# Check if already present
# ---------------------------------------------------------------------------
function Test-MidiLibraryPresent {
    if (-not (Test-Path $resourcesDir)) { return $false }
    $chordDirs = Get-ChildItem -Path $resourcesDir -Directory -Filter "free-midi-chords-*" -ErrorAction SilentlyContinue
    $progDirs  = Get-ChildItem -Path $resourcesDir -Directory -Filter "free-midi-progressions-*" -ErrorAction SilentlyContinue
    return ($chordDirs.Count -gt 0) -and ($progDirs.Count -gt 0)
}

if ((Test-MidiLibraryPresent) -and (-not $Force)) {
    Write-Host "MIDI chord library already present in resources/. Use -Force to re-download." -ForegroundColor Green
    exit 0
}

# ---------------------------------------------------------------------------
# Fetch latest release info from GitHub API
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Fetching MIDI Chord Library" -ForegroundColor Cyan
Write-Host "Source: https://github.com/$repoOwner/$repoName" -ForegroundColor Gray
Write-Host ""

Write-Host "Querying GitHub for latest release..." -ForegroundColor Yellow
try {
    $headers = @{ "User-Agent" = "Octavium-Build" }
    $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 30
} catch {
    Write-Host "ERROR: Failed to query GitHub API." -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "You can manually download from:" -ForegroundColor Yellow
    Write-Host "  https://github.com/$repoOwner/$repoName/releases" -ForegroundColor Yellow
    Write-Host "Extract the zip files into: $resourcesDir" -ForegroundColor Yellow
    exit 1
}

$tagName = $release.tag_name
Write-Host "Latest release: $tagName ($($release.name))" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Find the zip assets (chords + progressions)
# ---------------------------------------------------------------------------
$chordsAsset = $release.assets | Where-Object { $_.name -like "free-midi-chords-*.zip" } | Select-Object -First 1
$progressionsAsset = $release.assets | Where-Object { $_.name -like "free-midi-progressions-*.zip" } | Select-Object -First 1

if (-not $chordsAsset) {
    Write-Host "ERROR: Could not find chords zip asset in release $tagName" -ForegroundColor Red
    Write-Host "Available assets:" -ForegroundColor Yellow
    $release.assets | ForEach-Object { Write-Host "  - $($_.name)" -ForegroundColor Gray }
    exit 1
}

# ---------------------------------------------------------------------------
# Download and extract
# ---------------------------------------------------------------------------
if (-not (Test-Path $resourcesDir)) {
    New-Item -ItemType Directory -Path $resourcesDir -Force | Out-Null
}

$tempDir = Join-Path $env:TEMP "octavium-midi-download"
if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

function Download-AndExtract($asset, $label) {
    if (-not $asset) {
        Write-Host "SKIP: No $label asset found in this release." -ForegroundColor Yellow
        return
    }

    $zipPath = Join-Path $tempDir $asset.name
    $sizeMB  = [math]::Round($asset.size / 1MB, 1)

    Write-Host "Downloading $($asset.name) ($sizeMB MB)..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -TimeoutSec 300

    Write-Host "Extracting to resources/..." -ForegroundColor Cyan
    Expand-Archive -Path $zipPath -DestinationPath $resourcesDir -Force

    Write-Host "  Done: $label" -ForegroundColor Green
}

Download-AndExtract $chordsAsset "Chords"
Download-AndExtract $progressionsAsset "Progressions"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
Write-Host ""
if (Test-MidiLibraryPresent) {
    $dirs = Get-ChildItem -Path $resourcesDir -Directory | ForEach-Object { $_.Name }
    Write-Host "MIDI library installed successfully:" -ForegroundColor Green
    foreach ($d in $dirs) {
        $count = (Get-ChildItem -Path (Join-Path $resourcesDir $d) -Recurse -File).Count
        Write-Host "  $d ($count files)" -ForegroundColor White
    }
} else {
    Write-Host "WARNING: MIDI library may not have extracted correctly." -ForegroundColor Yellow
    Write-Host "Check the contents of: $resourcesDir" -ForegroundColor Yellow
}

Write-Host ""
