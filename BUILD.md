# Building Octavium Executable

This guide explains how to build a standalone Windows executable for Octavium.

## Prerequisites

- Python 3.8 or higher
- Virtual environment with all dependencies installed (see `requirements.txt`)
- PyInstaller (will be installed automatically by the build script)

## Quick Build

### Option 1: PowerShell Script (Recommended)

```powershell
.\build_exe.ps1
```

### Option 2: Batch File

```cmd
build_exe.bat
```

### Option 3: Manual Build

1. Activate the virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. Install PyInstaller (if not already installed):
   ```powershell
   pip install pyinstaller
   ```

3. Build the executable:
   ```powershell
   pyinstaller Octavium.spec --clean
   ```

## Output

The executable will be created in the `dist` folder:
- **Location**: `dist\Octavium.exe`
- **Type**: Standalone executable (all dependencies bundled)
- **Console**: Disabled (windowed application)

## Distribution

The `Octavium.exe` file in the `dist` folder is a standalone executable that can be:
- Copied to any Windows machine
- Run without installing Python or any dependencies
- Distributed to users

## Troubleshooting

### Build Fails

1. Make sure all dependencies are installed:
   ```powershell
   pip install -r requirements.txt
   ```

2. Clean build artifacts and try again:
   ```powershell
   Remove-Item -Recurse -Force build, dist
   pyinstaller Octavium.spec --clean
   ```

### Missing Icon

If the icon is missing, ensure `Octavium icon.png` exists in the project root.

### Runtime Errors

If the executable fails to run:
1. Try building with console enabled (set `console=True` in `Octavium.spec`)
2. Check for missing hidden imports in the spec file
3. Verify all data files are included in the `datas` section

## Customization

Edit `Octavium.spec` to customize:
- **Icon**: Change the `icon` parameter
- **Console**: Set `console=True` to show console window
- **Name**: Change the `name` parameter
- **Additional files**: Add to the `datas` list
- **Hidden imports**: Add to the `hiddenimports` list

## File Size

The executable will be approximately 100-150 MB due to bundled dependencies:
- PySide6 (Qt framework)
- pygame
- mido
- python-rtmidi

To reduce size, consider using UPX compression (enabled by default with `upx=True`).
