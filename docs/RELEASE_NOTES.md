# Octavium - Initial Release

## What's New

### Features Removed
- **25-key keyboard option** - Removed from keyboard size menu and preferences
- **Harmonic Table layout** - Removed from keyboard menu

### Available Keyboard Sizes
- 49 Keys (4 Octaves)
- 61 Keys (5 Octaves)
- 73 Keys (6 Octaves)
- 76 Keys (6+ Octaves)
- 88 Keys (Full Piano)

### Additional Layouts
- 4x4 Beat Grid
- Faders (8 CC controllers)
- XY Fader (2D controller)

## Installation

### Running from Source
1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python run.py
   ```

### Running the Executable
Simply double-click `Octavium.exe` - no installation required!

## Building the Executable

To build your own executable:

```powershell
.\build_exe.ps1
```

Or manually:
```powershell
pip install pyinstaller
pyinstaller Octavium.spec --clean
```

See `BUILD.md` for detailed build instructions.

## Git Configuration

The `.gitattributes` file has been configured to prevent line ending issues:
- Python files use LF endings
- Windows scripts use CRLF endings
- Binary files are properly marked

## System Requirements

- **OS**: Windows 10 or higher
- **RAM**: 512 MB minimum
- **Disk**: 100 MB for executable
- **MIDI**: MIDI output device (hardware or virtual like loopMIDI)

## Known Issues

None currently reported.

## Support

For issues or questions, please refer to the project documentation.

---

**Version**: Initial Release  
**Date**: October 30, 2025  
**Branch**: initial-release
