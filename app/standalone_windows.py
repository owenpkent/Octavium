"""Standalone window wrappers for Octavium widgets."""
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from pathlib import Path
from typing import Optional
from .midi_io import MidiOut


class ChordSelectorWindow(QMainWindow):
    """Standalone window for Chord Selector."""
    
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        from .chord_selector import ChordSelectorWidget
        
        self.setWindowTitle("Chord Selector")
        self.setMinimumSize(400, 600)
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create central widget
        self.chord_selector = ChordSelectorWidget(midi_out, midi_channel, self)
        self.setCentralWidget(self.chord_selector)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
        """)


class PadGridWindow(QMainWindow):
    """Standalone window for Pad Grid."""
    
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        from .pad_grid import PadGridWidget, create_pad_grid_layout
        
        self.setWindowTitle("Pad Grid")
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create a 4x4 pad grid layout with MIDI notes starting at C2 (36)
        # Use the create_pad_grid_layout function to ensure consistent ordering
        layout_model = create_pad_grid_layout(rows=4, cols=4, start_note=36)
        
        self.pad_grid = PadGridWidget(layout_model, midi_out, title="Pad Grid", scale=1.0)
        self.setCentralWidget(self.pad_grid)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
        """)


class FadersWindow(QMainWindow):
    """Standalone window for Faders."""
    
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        from .faders import FadersWidget
        
        self.setWindowTitle("Faders")
        self.setMinimumSize(400, 500)
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create central widget
        self.faders = FadersWidget(midi_out, scale=1.0)
        self.setCentralWidget(self.faders)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
        """)


class XYFaderWindow(QMainWindow):
    """Standalone window for XY Fader."""
    
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        from .xy_fader import XYFaderWidget
        
        self.setWindowTitle("XY Fader")
        self.setMinimumSize(400, 400)
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create central widget
        self.xy_fader = XYFaderWidget(midi_out, scale=1.0)
        self.setCentralWidget(self.xy_fader)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
        """)
