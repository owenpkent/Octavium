<p align="center">
  <img src="Octavium%20logo.png" alt="Octavium Logo" width="360" />
</p>

# Octavium 🎹

A powerful Python desktop MIDI tool that creates multiple customizable on-screen keyboards for sending MIDI to your DAW. Built with PySide6, mido, and pygame for reliable cross-platform MIDI output.

## Features

- **Multiple Keyboard Layouts**: Piano keyboards, drum pads, and custom layouts
- **Real-time MIDI Output**: Send MIDI to any DAW (Ableton Live, FL Studio, etc.)
- **Flexible Routing**: Route different keyboards to different MIDI ports/channels
- **Velocity Control**: Adjustable velocity with multiple curve options
- **Scale Quantization**: Snap notes to musical scales (major, minor, pentatonic, custom)
- **Sustain Mode**: Hold notes for continuous playback
- **Octave Shifting**: Quick octave changes with keyboard shortcuts
- **Customizable Layouts**: JSON-based layout system for easy customization

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

### Keyboard Controls

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

### Interface Elements

- **Velocity Slider**: Adjust note velocity (20-127)
- **Octave Display**: Shows current octave offset
- **Sustain Indicator**: Shows sustain on/off status
- **Velocity Curve**: Shows current velocity response curve

## MIDI Setup

### Windows (Recommended: loopMIDI)

1. Download and install [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)
2. Create virtual MIDI ports:
   - "loopMIDI Port 1" (for piano keyboard)
   - "loopMIDI Port 2" (for drum pads)
3. Configure your DAW to receive MIDI from these ports

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Happy music making! 🎵**
