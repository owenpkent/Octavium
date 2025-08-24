import sys
from PySide6.QtWidgets import QApplication
from .keyboard_widget import KeyboardWidget
from .midi_io import MidiOut
from .themes import APP_STYLES
from .piano_61 import create_61_key_piano

def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLES)
    
    # Create piano layout programmatically
    piano_layout = create_61_key_piano()
    piano_out = MidiOut(port_name_contains="loopMIDI Port 1")
    keyboard = KeyboardWidget(piano_layout, piano_out, title="Piano 61-Key -> loopMIDI Port 1")
    keyboard.resize(1400, 300)
    keyboard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
