<p align="center">
  <img src="Octavium%20logo.png" alt="Octavium Logo" width="360" />
</p>

# Octavium 🎹

An accessibility-first, mouse‑driven virtual MIDI keyboard for making music without a physical keyboard. Octavium is designed for creators who primarily use a mouse (including users with motor disabilities). It focuses on clear visuals, reliable mouse interactions (click and drag), and features like sustain and latch that make performance and composition possible without traditional keybeds. Built with PySide6, mido, and pygame.

## Features

- **Launcher Window**: Central hub to open multiple keyboards and windows simultaneously
- **Multiple Keyboards**: 25-key, 49-key, 61-key pianos, and Harmonic Table
- **Standalone Windows**: Chord Monitor, Pad Grid, Faders, and XY Fader can be opened independently
- **Accessibility & mouse-first**: Optimized for mouse input; every playing action works via click or click‑and‑drag
- **Virtual keyboard focus**: On‑screen piano with clear press/held states and strong visual feedback
- **Sustain and Latch**:
  - Sustain keeps notes sounding; visuals clear on click release so you always see what you touched
  - Latch toggles notes on press; pressing again releases. When changing octaves, visuals shift position while the sounding notes do not change
  - **Right-Click Latch**: Enabled by default - right-click any key to toggle latch on that note while using regular clicks for normal notes
- **Velocity control**: Slider with linear/soft/hard response curves
- **Scale quantization**: Optionally snap to scales (chromatic by default) to avoid wrong notes
- **Octave controls**: Buttons and shortcuts for quick visual range shifts
- **Polyphony options**: Limit voices or run unlimited
- **MIDI routing**: Choose output port and channel
- **Chord Monitor**: 
  - Hold-to-play chord cards with humanize controls (velocity and drift randomization)
  - **Drag-and-drop rearranging**: Drag cards to swap positions or move to empty slots
  - **Drag-to-edit**: Drag a card to the keyboard's chord display area to load and edit the chord, then drag back to save

## Quick Start

### Prerequisites

- Python 3.9+ (tested with Python 3.13)
- Windows, macOS, or Linux
- MIDI output device or virtual MIDI ports (like loopMIDI on Windows)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/owenpkent/Octavium.git
   cd Octavium
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run Octavium:**
   ```bash
   python run.py
   ```

## Usage

### Launcher Window

When you run Octavium, a launcher window appears with options to open:

**Keyboards:**
- 25-Key Piano
- 49-Key Piano
- 61-Key Piano
- Harmonic Table

**Windows:**
- Chord Monitor - Hold-to-play chord cards with humanize controls
- Pad Grid - 4x4 drum pad grid
- Faders - 8-channel MIDI CC faders
- XY Fader - 2D XY pad for expressive control

You can open multiple keyboards and windows simultaneously. The launcher stays open for easy access.

### Mouse interactions

- **Click** a key to play it. With sustain on, audio continues; visual clears on release for clarity.
- **Click and drag** across keys to glide; releasing ends the gesture (unless latched).
- **Latch mode**: Clicking a key toggles it on/off. Changing octave shifts the highlighted keys so their visual position follows the range, while sounding notes remain unchanged.
- **All Notes Off**: Panic button to stop everything.

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Z` | Octave down |
| `X` | Octave up |
| `S` | Toggle sustain |
| `1` | Linear velocity curve |
| `2` | Soft velocity curve |
| `3` | Hard velocity curve |
| `Q` | Toggle quantize scale |
| `Esc` | All notes off |

### Interface elements

- **Velocity slider**: Adjust note velocity (20–127) and choose curve.
- **Octave controls**: “- / Octave / +” buttons and Z/X shortcuts.
- **Sustain & Latch**: Toggle buttons with clear on/off states.
- **All Notes Off**: Stops all sounding notes.

### Layouts and surfaces

- **Piano (default)**: Choose sizes in `Keyboard` menu (25/49/61/73/76/88).
- **4x4 Beat Grid**: `Keyboard` → `4x4 Beat Grid`. Sends 16 notes (row-major).
- **Faders**: `Keyboard` → `Faders`. Eight CC faders; configure CCs via `MIDI` → `Configure Faders CCs…`.
- **XY Fader**: `Keyboard` → `XY Fader`. Drag to send two CCs (X and Y). Configure via `MIDI` → `Configure XY CCs…`. Clicking sets a reference point and dragging moves relatively.
- **Harmonic Table (WIP)**: `Keyboard` → `Harmonic Table`.
  - Blue hex honeycomb with isomorphic mapping (horizontal = fifths, diagonals thirds).
  - Default base is C2 at the lower-left. Orientation and mapping are still being tuned.
  - Zoom works from `View` → `Zoom`.

## MIDI Setup

### Windows (Recommended: loopMIDI)

1. Download and install [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)
2. Create virtual MIDI ports:
   - "loopMIDI Port 1" (for piano keyboard)
   - "loopMIDI Port 2" (for drum pads)
3. Configure your DAW to receive MIDI from these ports

On first run, Octavium attempts to use `mido` with `python-rtmidi`. If unavailable, it falls back to a pygame MIDI backend and selects the first available output (e.g., loopMIDI Port 1).

## How it works (modules & key functions)

- **`app/main.py`**
  - `MainWindow`: Builds the window, menus, and swaps keyboard sizes while preserving state (channel, sustain/latch preferences, etc.).
  - `set_keyboard_size(size)`: Rebuilds the keyboard widget for 25/49/61 keys while keeping the same MIDI out and settings.
  - `set_pad_grid()` / `set_faders()` / `set_xy_fader()` / `set_harmonic_table()`: Switch to alternate surfaces.
  - `set_zoom(scale)`: Rebuilds current surface at the chosen UI scale, preserving state where possible.

- **`app/keyboard_widget.py`**
  - `KeyboardWidget`: Core widget that renders the piano, handles mouse input, and sends MIDI.
  - `on_key_press(key)` / `on_key_release(key)`: Handle mouse press/release. Respect sustain and latch; keep visuals in sync with the actual state.
  - `change_octave(delta)`: Shifts the visible range. In latch mode, moves held visuals to the new positions without changing the sounding notes.
  - `effective_note(base_note)`: Computes the output MIDI note using current octave, base layout octave, and quantization.
  - `_apply_btn_visual(btn, active, held)`: Applies visual state for a key (pressed vs held).
  - `_clear_other_actives(except_btn)`, `_sync_visuals_if_needed()`: Ensure visuals remain consistent after complex gestures.
  - `set_channel(ch)`, `set_polyphony_enabled(enabled)`: Configure routing and voice limiting.

- **`app/midi_io.py`**
  - `MidiOut`: Simple abstraction for MIDI output. Tries mido/rtmidi, falls back to pygame if needed. Methods: `note_on`, `note_off`, `cc`, `panic`.

- **`app/harmonic_table.py` (WIP)**
  - `HarmonicTableWidget`: Flat‑top hex honeycomb surface, absolute‑positioned with axial coordinates. Defaults to C2 at the lower-left. Orientation and range are subject to change.
  - `HexButton`: Custom-painted hexagonal buttons in the blue theme.



---

# Modulune 🌙

**Generative Impressionistic Piano Engine**

Modulune is Octavium's generative counterpart. While Octavium gives users direct expressive control over MIDI performance, Modulune creates musical intention autonomously—generating continuously evolving piano textures in real time.

## Inspiration

Modulune draws inspiration from the expressive, impressionistic qualities of pieces like Debussy's *Clair de Lune* and the flowing, harmonically rich improvisations of Bill Evans. The goal is not to clone Debussy, nor to produce deterministic compositions, but to create a system that generates music which:

- **Feels alive** — Subtle rubato, velocity variation, and humanized timing
- **Flows organically** — Harmonic progressions that move smoothly with modal interchange
- **Never exactly repeats** — Controlled randomness within musical rules
- **Evokes impressionism** — Extended chords, whole-tone colors, and shimmering textures

## Philosophy: Octavium + Modulune

Together, Octavium and Modulune form a unified ecosystem for musical exploration:

| Octavium | Modulune |
|----------|----------|
| The **instrument** | The **player** |
| Translates human intention into performance | Creates intention on its own |
| Direct expressive control | Algorithmic creativity |
| User-driven | System-driven |

Both share the same underlying philosophy: **accessibility**, **experimentation**, and **musical exploration**—allowing anyone, regardless of physical ability or musical training, to produce rich, evolving piano textures either interactively or fully autonomously.

## Features

- **Rule-based generation** — Scales, chords, phrase contours, arpeggios, and harmonic motion
- **Multiple texture types**:
  - `impressionist_wash` — Combined flowing textures (default)
  - `flowing_arpeggios` — Continuous arpeggio patterns
  - `melodic_fragments` — Melodic lines with sparse accompaniment
  - `shimmering_chords` — Sustained chord textures
  - `sparse_meditation` — Contemplative, minimal textures
  - `layered_voices` — Multiple independent melodic voices
- **Live MIDI streaming** — Output to any virtual MIDI port (like loopMIDI)
- **Expressive timing** — Rubato, swing, and humanization
- **Dynamic modulation** — Automatic key and mode changes
- **Configurable parameters** — Tempo, density, tension, expressiveness

## Quick Start

### Prerequisites

- Python 3.9+
- Virtual MIDI port (loopMIDI on Windows, IAC Driver on macOS)
- DAW configured to receive MIDI input

### Installation

Modulune uses the same environment as Octavium:

```bash
# From the Octavium directory
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### Running Modulune

```bash
# Basic usage (default settings)
python -m modulune.main

# With custom parameters
python -m modulune.main --tempo 60 --key Db --mode lydian --texture flowing_arpeggios

# List available MIDI ports
python -m modulune.main --list-ports

# Full example
python -m modulune.main --tempo 72 --key C --mode major --density 0.5 --tension 0.3 --texture impressionist_wash
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--tempo` | Tempo in BPM | 72 |
| `--key` | Key root (C, Db, F#, etc.) | C |
| `--mode` | Scale mode | major |
| `--density` | Note density (0.0-1.0) | 0.5 |
| `--tension` | Harmonic tension (0.0-1.0) | 0.3 |
| `--texture` | Texture type | impressionist_wash |
| `--expressiveness` | Expression level (0.0-1.0) | 0.6 |
| `--port` | MIDI port name | auto |
| `--list-ports` | List available MIDI ports | — |

### Available Modes

`major`, `natural_minor`, `harmonic_minor`, `melodic_minor`, `dorian`, `phrygian`, `lydian`, `mixolydian`, `aeolian`, `locrian`, `whole_tone`, `pentatonic_major`, `pentatonic_minor`, `blues`

## Routing Modulune into a DAW

### Step 1: Create a Virtual MIDI Port

**Windows (loopMIDI):**
1. Download [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)
2. Install and run loopMIDI
3. Create a new port (e.g., "Modulune Output")

**macOS (IAC Driver):**
1. Open Audio MIDI Setup
2. Window → Show MIDI Studio
3. Double-click IAC Driver
4. Enable "Device is online"
5. Add a port named "Modulune Output"

### Step 2: Configure Your DAW

**Ableton Live:**
1. Preferences → Link/Tempo/MIDI
2. Enable Track and Remote for "Modulune Output" (or loopMIDI port)
3. Create a MIDI track
4. Set "MIDI From" to "Modulune Output"
5. Arm the track for recording
6. Add a piano VST (e.g., Piano One, Keyscape, Addictive Keys)

**FL Studio:**
1. Options → MIDI Settings
2. Enable the loopMIDI/IAC port as input
3. Add a piano VST to a channel
4. Set the channel's MIDI input to the port

**Logic Pro:**
1. Open Preferences → MIDI
2. The IAC port should appear automatically
3. Create a Software Instrument track with a piano
4. Click the "R" button to record-enable

**Reaper:**
1. Options → Preferences → MIDI Devices
2. Enable the virtual MIDI port as input
3. Create a track with a piano VSTi
4. Arm for recording and set input to the MIDI port

### Step 3: Start Modulune

```bash
# Specify the port if needed
python -m modulune.main --port "loopMIDI Port 1"
```

The generated MIDI will stream directly into your DAW in real time.

## Programmatic Usage

```python
from modulune import ModuluneEngine, EngineConfig, TextureType
from modulune.harmony import ScaleType

# Create custom configuration
config = EngineConfig(
    tempo=66.0,
    key_root=61,  # Db
    scale_type=ScaleType.LYDIAN,
    density=0.4,
    tension=0.2,
    texture=TextureType.FLOWING_ARPEGGIOS,
)

# Initialize and start
engine = ModuluneEngine(config, midi_port="loopMIDI Port 1")

# Register callbacks (optional)
engine.on_chord_change(lambda chord: print(f"New chord: {chord}"))

engine.start()

# Adjust parameters in real-time
engine.set_tempo(80)
engine.set_density(0.7)
engine.set_texture(TextureType.SPARSE_MEDITATION)

# Stop when done
engine.stop()
```

## Architecture

```
modulune/
├── __init__.py      # Package exports
├── main.py          # CLI entry point
├── engine.py        # Main orchestration engine
├── harmony.py       # Scales, chords, progressions
├── melody.py        # Phrase and motif generation
├── rhythm.py        # Timing and rhythmic patterns
└── requirements.txt # Dependencies
```

### Module Overview

- **`engine.py`** — `ModuluneEngine` orchestrates all generation, schedules MIDI events, and streams output
- **`harmony.py`** — `Scale`, `Chord`, `ChordProgression`, `HarmonyEngine` for harmonic content
- **`melody.py`** — `Note`, `Phrase`, `MelodyEngine` for melodic lines and arpeggios
- **`rhythm.py`** — `RhythmEngine`, `RhythmPattern` for timing, rubato, and humanization

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Happy music making! 🎵**
