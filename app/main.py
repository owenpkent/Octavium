import json, sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from .models import Layout
from .keyboard_widget import KeyboardWidget
from .midi_io import MidiOut
from .themes import APP_STYLES

def load_layout(path: Path) -> Layout:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Layout(**data)

def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLES)
    base = Path(__file__).parent.parent / "layouts"
    piano_layout = load_layout(base / "piano_49.json")
    piano_out = MidiOut(port_name_contains="loopMIDI Port 1")
    w1 = KeyboardWidget(piano_layout, piano_out, title="Piano 49 -> loopMIDI Port 1")
    w1.resize(900, 420)
    w1.show()
    drum_layout = load_layout(base / "drum_4x4.json")
    drum_out = MidiOut(port_name_contains="loopMIDI Port 2")
    w2 = KeyboardWidget(drum_layout, drum_out, title="Drum 4x4 -> loopMIDI Port 2")
    w2.move(100, 480)
    w2.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
