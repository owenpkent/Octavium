# Octavium Directory Index

This document provides a map of all files and folders in the repository.

---

## Root Directory

The root is kept clean with only essential files:

| File | Description |
|------|-------------|
| `run.py` | **Entry point** — Launches the Octavium application |
| `requirements.txt` | Python dependencies (PySide6, mido, pygame) |
| `README.md` | Project overview, features, and documentation |
| `LICENSE` | MIT License |
| `pyrightconfig.json` | Pyright type-checking configuration |
| `.gitignore` | Git ignore rules |
| `.gitattributes` | Git attributes configuration |

---

## Core Application Folders

### `app/` — Main Application

The core Octavium application code.

| File | Description |
|------|-------------|
| `__init__.py` | Package init |
| `main.py` | Main window and application logic |
| `launcher.py` | Launcher window for opening multiple keyboards/windows |
| `keyboard_widget.py` | Piano keyboard widget (all sizes: 25-88 keys) |
| `harmonic_table.py` | Isomorphic hex layout keyboard |
| `chord_monitor_window.py` | 4×4 chord card grid for quick playback |
| `chord_selector.py` | Chord definitions, ReplayCard widget, chord detection |
| `chord_suggestions.py` | Chord suggestion engine for progressions |
| `chord_autofill.py` | Autofill dialog for populating chord cards by key/mode |
| `pad_grid.py` | 4×4 drum pad grid |
| `faders.py` | 8 CC fader controls |
| `xy_fader.py` | 2D XY pad for expressive CC control |
| `midi_io.py` | MIDI output abstraction (mido/pygame backend) |
| `scale.py` | Scale quantization utilities |
| `preferences.py` | User preferences handling |
| `standalone_windows.py` | Standalone window launchers |
| `piano_49.py` | 49-key piano layout |
| `piano_61.py` | 61-key piano layout |
| `piano_layout.py` | General piano layout utilities |
| `models.py` | Data models |
| `themes.py` | UI styling/themes |

### `modulune/` — Generative Engine

Algorithmic impressionistic piano generator.

| File | Description |
|------|-------------|
| `__init__.py` | Package init with exports |
| `main.py` | CLI entry point and orchestration |
| `window.py` | GUI window for Modulune controls |
| `engine.py` | Core generation engine |
| `harmony.py` | Harmonic progression generation |
| `melody.py` | Melodic pattern generation |
| `rhythm.py` | Rhythmic pattern generation |
| `requirements.txt` | Modulune-specific dependencies |

---

## Support Folders

### `assets/` — Branding & Icons

| File | Description |
|------|-------------|
| `Octavium logo.png` | Full logo image |
| `Octavium icon.png` | App icon (PNG) |
| `Octavium.ico` | App icon (Windows ICO) |

### `scripts/` — Build & Utility Scripts

| File | Description |
|------|-------------|
| `build_exe.ps1` | PowerShell script for building executable |
| `build_exe.bat` | Windows batch script for building |
| `Octavium.spec` | PyInstaller spec file |
| `convert_icon.py` | Icon conversion utility |
| `version_info.txt` | Windows version info for executable |

### `docs/` — Documentation

| File | Description |
|------|-------------|
| `DIRECTORY.md` | This file — repository map |
| `BUILD.md` | Build instructions for creating executables |
| `BRANCH_STRUCTURE.md` | Git branching strategy |
| `RELEASE_NOTES.md` | Version history and release notes |
| `TODO.md` | Feature roadmap and in-progress work |
| `MIDI_LIBRARY_PROPOSAL.md` | Proposal for MIDI library integration |
| `system_overview.md` | Mermaid diagram of application architecture |

### `resources/` — External Data (Untracked)

Contains MIDI chord and progression libraries.

#### `resources/free-midi-chords-20231004/`

**8,800+ MIDI chord files** from the SHLD Free MIDI Chord Pack project.

```
free-midi-chords-20231004/
├── 01 - C Major - A minor/
│   ├── 1 Triad/
│   │   ├── Major/     (7 chord files)
│   │   └── Minor/     (7 chord files)
│   ├── 2 7th and 9th/ (28 chord files)
│   ├── 3 All chords/  (136 chord files)
│   └── 4 Progression/ (560 progression files)
├── ... (12 key folders total)
└── README.md
```

#### `resources/free-midi-progressions-20231004/`

**6,700+ MIDI chord progression files** organized by mode.

```
free-midi-progressions-20231004/
├── Major/      (3,264 files)
├── Minor/      (3,456 files)
└── README.md
```

---

## Output Folders

| Folder | Description |
|--------|-------------|
| `releases/` | Pre-built executables and installers |
| `screenshots/` | UI screenshots for documentation |
| `video/` | Demo videos and related assets |
| `build/` | PyInstaller build artifacts (gitignored) |
| `dist/` | Distribution output (gitignored) |
| `venv/` | Python virtual environment (gitignored) |

---

## Key Integration Points

### Chord Monitor (`app/chord_monitor_window.py`)
- 4×4 grid of `ReplayCard` widgets
- Hold-to-play functionality
- Drag-and-drop card rearrangement
- Humanize controls for natural feel

### Chord Definitions (`app/chord_selector.py`)
- `CHORD_DEFINITIONS` dict: Maps chord names → intervals
- `NOTES` list: Note names C through B
- `ReplayCard` class: Draggable chord card widget
- Chord detection from MIDI notes

### Autofill System (`app/chord_autofill.py`)
- Dialog for auto-populating chord cards by key/mode
- Diatonic chord generation
- Scale preview

---

*Last updated: February 2026*
