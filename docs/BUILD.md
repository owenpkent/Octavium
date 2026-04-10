# Building & Releasing Octavium

This guide covers everything needed to build Octavium from source, sign it with an EV certificate, create the Windows installer, and publish a release.

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Building the Executable](#building-the-executable)
3. [Building a Signed Installer (Full Release)](#building-a-signed-installer-full-release)
4. [Manual Build Steps](#manual-build-steps)
5. [Release Checklist](#release-checklist)
6. [Version Bumping](#version-bumping)
7. [Troubleshooting](#troubleshooting)

---

## Development Setup

### Prerequisites

- **Python 3.9+** (tested with Python 3.13)
- **Windows 10/11**
- **Git**

### First-Time Setup

```powershell
git clone https://github.com/owenpkent/Octavium.git
cd Octavium
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Fetching the MIDI Chord Library

The MIDI chord library (~30 MB, ~15,000 files) is **not** stored in the git repository. It must be downloaded separately for local development:

```powershell
.\scripts\fetch_midi_library.ps1
```

This downloads the latest release from [ldrolez/free-midi-chords](https://github.com/ldrolez/free-midi-chords) and extracts it into `resources/`. The library is MIT-licensed (see `THIRD_PARTY_LICENSES.md`).

The application works without the MIDI library — the "MIDI Library" autofill source will simply be unavailable in the Chord Pad.

To re-download or update to a newer version:
```powershell
.\scripts\fetch_midi_library.ps1 -Force
```

### Running from Source

```powershell
.\venv\Scripts\Activate.ps1
python run.py
```

---

## Building the Executable

For development/testing builds (no signing, no installer).

### Quick Build (PowerShell)

```powershell
.\scripts\build_exe.ps1
```

### Quick Build (Batch)

```cmd
scripts\build_exe.bat
```

**Output:** `dist\Octavium.exe` — standalone executable with all dependencies bundled (~100-150 MB).

---

## Building a Signed Installer (Full Release)

This is the process for creating a production release with code signing and the Windows installer.

### Additional Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **InnoSetup 6** | Compiles the installer | [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php) |
| **Windows SDK** | Provides `signtool.exe` for code signing | [Windows SDK download](https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/) — select "Signing Tools" only |
| **EV Certificate + Hardware Token** | Signs the executable and installer | See [CODE_SIGNING.md](CODE_SIGNING.md) |
| **Pillow** | Generates installer wizard images (already in requirements.txt) | `pip install Pillow` |

### Environment Setup

1. Copy `.env.example` to `.env` in the project root:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Edit `.env` and fill in your signing thumbprint:
   ```ini
   OCTAVIUM_SIGN_THUMBPRINT=A1B2C3D4E5F6...
   OCTAVIUM_TIMESTAMP_URL=http://timestamp.digicert.com
   ```
   Find your thumbprint with:
   ```powershell
   certutil -user -store My
   ```

3. Load the environment variables into your PowerShell session:
   ```powershell
   Get-Content .env | ForEach-Object {
       if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
           [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
       }
   }
   ```

4. Plug in your EV hardware token (SafeNet eToken, YubiKey, etc.)

### One-Command Release Build

```powershell
.\scripts\build_installer.ps1
```

This runs the full pipeline:

1. **Builds** `Octavium.exe` with PyInstaller
2. **Signs** `Octavium.exe` with your EV certificate (token PIN prompt)
3. **Generates** installer wizard branding images from the logo
4. **Compiles** the installer with InnoSetup (bundles exe + MIDI library)
5. **Signs** the installer (second token PIN prompt)

**Output:** `dist\OctaviumSetup-<version>.exe`

### Build Script Options

| Flag | Effect |
|------|--------|
| `-SkipSign` | Build without signing (for testing the installer locally) |
| `-SkipBuild` | Skip PyInstaller, reuse existing `dist\Octavium.exe` |

```powershell
# Test build without signing (no hardware token needed)
.\scripts\build_installer.ps1 -SkipSign

# Re-package an already-built exe into a new installer
.\scripts\build_installer.ps1 -SkipBuild
```

---

## Manual Build Steps

If you prefer to run each step individually instead of using the pipeline script.

### Step 1: Build the Executable

```powershell
.\venv\Scripts\Activate.ps1
pyinstaller scripts\Octavium.spec --clean
```

### Step 2: Sign the Executable

```powershell
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /sha1 $env:OCTAVIUM_SIGN_THUMBPRINT dist\Octavium.exe
signtool verify /pa /v dist\Octavium.exe
```

### Step 3: Generate Wizard Images

```powershell
python installer\generate_wizard_images.py
```

### Step 4: Compile the Installer

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" installer\octavium.iss
```

### Step 5: Sign the Installer

```powershell
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /sha1 $env:OCTAVIUM_SIGN_THUMBPRINT dist\OctaviumSetup-1.1.1.exe
signtool verify /pa /v dist\OctaviumSetup-1.1.1.exe
```

---

## Release Checklist

Follow this checklist for every public release:

### Before Building

- [ ] All changes committed and pushed
- [ ] Version number bumped in all locations (see [Version Bumping](#version-bumping))
- [ ] CHANGELOG.md updated with new entries
- [ ] Release notes written in `releases/v<version>.md`
- [ ] Tested the application from source (`python run.py`)

### Build & Sign

- [ ] Run `.\scripts\build_installer.ps1`
- [ ] Verify the exe launches correctly from `dist\Octavium.exe`
- [ ] Verify the installer works end-to-end:
  - [ ] Fresh install on a clean machine (or VM)
  - [ ] Upgrade over a previous version
  - [ ] Uninstall via Add/Remove Programs
  - [ ] Desktop and Start Menu shortcuts work
  - [ ] MIDI library files are present in install directory
- [ ] Verify signatures: right-click both `.exe` files → Properties → Digital Signatures

### Publish

- [ ] Create a GitHub release tag: `git tag v<version> && git push --tags`
- [ ] Upload `OctaviumSetup-<version>.exe` to the GitHub release
- [ ] Update the release description with notes from `releases/v<version>.md`

---

## Version Bumping

When preparing a new release, update the version in **all** of these locations:

| File | What to change |
|------|---------------|
| `installer/octavium.iss` | `#define MyAppVersion "X.Y.Z"` |
| `scripts/version_info.txt` | `filevers`, `prodvers`, `FileVersion`, `ProductVersion` |
| `scripts/build_installer.ps1` | `$AppVersion = "X.Y.Z"` |
| `docs/CHANGELOG.md` | Add a new section header |
| `releases/vX.Y.Z.md` | Create the release notes file |

---

## Troubleshooting

### PyInstaller Build Fails

1. Ensure all dependencies are installed:
   ```powershell
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. Clean and retry:
   ```powershell
   Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
   pyinstaller scripts\Octavium.spec --clean
   ```

3. If the exe crashes silently, rebuild with console enabled for debugging:
   Edit `scripts/Octavium.spec` → set `console=True`, rebuild, and run from a terminal.

### Signing Fails

| Error | Fix |
|-------|-----|
| "No certificates were found" | Plug in your hardware token; verify thumbprint with `certutil -user -store My` |
| "Timestamp server could not be reached" | Check internet; try a different timestamp URL |
| PIN prompt doesn't appear | Restart SafeNet/YubiKey service; re-insert token |
| "An unexpected internal error" | Update Windows SDK; use the `x64` signtool |

See [CODE_SIGNING.md](CODE_SIGNING.md) for detailed signing instructions.

### InnoSetup Compilation Fails

1. Verify InnoSetup 6 is installed and `ISCC.exe` is accessible:
   ```powershell
   & "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /?
   ```

2. Ensure wizard images exist (run `python installer\generate_wizard_images.py`)

3. Ensure `dist\Octavium.exe` exists (build it first)

### Installer Doesn't Detect Previous Version

The installer uses the registry key `HKLM\Software\Owen Kent\Octavium` for version detection. If you installed a version before this registry key was added, uninstall it manually from Add/Remove Programs first.

### Large File Size

The executable is ~100-150 MB due to bundled dependencies (PySide6, pygame, mido, python-rtmidi). The installer adds the MIDI chord library (~30 MB). UPX compression is enabled by default in the spec file (`upx=True`).

---

*Last updated: February 7, 2026*
