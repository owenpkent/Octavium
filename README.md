<p align="center">
  <img src="Octavium%20logo.png" alt="Octavium Logo" width="360" />
</p>

# Octavium 🎹

An accessibility-first, mouse‑driven virtual MIDI keyboard for making music without a physical keyboard. Octavium is designed for creators who primarily use a mouse (including users with motor disabilities). It focuses on clear visuals, reliable mouse interactions (click and drag), and features like sustain and latch that make performance and composition possible without traditional keybeds. Built with PySide6, mido, and pygame.

## Features

- **Accessibility & mouse-first**: Optimized for mouse input; every playing action works via click or click‑and‑drag.
- **Virtual keyboard focus**: On‑screen piano with clear press/held states and strong visual feedback.
- **Sustain and Latch**:
  - Sustain keeps notes sounding; visuals clear on click release so you always see what you touched.
  - Latch toggles notes on press; pressing again releases. When changing octaves, visuals shift position while the sounding notes do not change.
- **Velocity control**: Slider with linear/soft/hard response curves.
- **Scale quantization**: Optionally snap to scales (chromatic by default) to avoid wrong notes.
- **Octave controls**: Buttons and shortcuts for quick visual range shifts.
- **Polyphony options**: Limit voices or run unlimited.
- **MIDI routing**: Choose output port and channel.
- **Layouts**: JSON-based; start with a 61‑key piano.

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
   python -m app.main
   ```

## Usage

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

- **`layouts/`**
  - JSON layout definitions (e.g., `layouts/piano_61.json`). You can create custom layouts.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Happy music making! 🎵**
