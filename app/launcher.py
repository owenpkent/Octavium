"""Octavium Launcher Window - Main entry point for selecting windows and keyboards."""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QGridLayout, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from pathlib import Path
from typing import Optional, List, Any
import sys


class LauncherWindow(QMainWindow):
    """Main launcher window for Octavium - allows opening multiple windows."""
    
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.opened_windows: List[Any] = []
        
        # Create a shared MIDI output for all windows to avoid port conflicts
        from .midi_io import MidiOut
        import mido
        
        # Show available MIDI ports
        try:
            ports = mido.get_output_names()  # type: ignore[attr-defined]
            if ports:
                print(f"Available MIDI ports: {', '.join(ports)}")
            else:
                print("No MIDI ports found")
        except Exception as e:
            print(f"Could not list MIDI ports: {e}")
        
        try:
            # Prefer loopMIDI Port 1 if available
            self.shared_midi = MidiOut(port_name_contains="loopMIDI Port 1", is_shared=True)
            backend = "pygame" if self.shared_midi.use_pygame else "mido"
            print(f"✓ Launcher initialized with {backend} MIDI backend")
        except Exception as e:
            print(f"✗ Warning: Could not initialize MIDI output: {e}")
            self.shared_midi = None
        
        self.setWindowTitle("Octavium Launcher")
        self.setMinimumSize(600, 500)
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Octavium")
        header.setStyleSheet("font-size: 32px; font-weight: bold; color: #fff;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel("Select windows and keyboards to open")
        subtitle.setStyleSheet("font-size: 14px; color: #aaa;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Keyboards section
        keyboards_group = QGroupBox("Keyboards")
        keyboards_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #fff;
                border: 2px solid #3b4148;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        keyboards_layout = QGridLayout()
        keyboards_layout.setSpacing(10)
        
        # Keyboard buttons
        self.btn_piano_25 = self._create_launch_button("25-Key Piano", self._launch_piano_25)
        self.btn_piano_49 = self._create_launch_button("49-Key Piano", self._launch_piano_49)
        self.btn_piano_61 = self._create_launch_button("61-Key Piano", self._launch_piano_61)
        self.btn_harmonic = self._create_launch_button("Harmonic Table", self._launch_harmonic_table)
        
        keyboards_layout.addWidget(self.btn_piano_25, 0, 0)
        keyboards_layout.addWidget(self.btn_piano_49, 0, 1)
        keyboards_layout.addWidget(self.btn_piano_61, 1, 0)
        keyboards_layout.addWidget(self.btn_harmonic, 1, 1)
        
        keyboards_group.setLayout(keyboards_layout)
        layout.addWidget(keyboards_group)
        
        # Windows section
        windows_group = QGroupBox("Windows")
        windows_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #fff;
                border: 2px solid #3b4148;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        windows_layout = QGridLayout()
        windows_layout.setSpacing(10)
        
        # Window buttons
        self.btn_chord_monitor = self._create_launch_button("Chord Monitor", self._launch_chord_monitor)
        self.btn_pad_grid = self._create_launch_button("Pad Grid", self._launch_pad_grid)
        self.btn_faders = self._create_launch_button("Faders", self._launch_faders)
        self.btn_xy_fader = self._create_launch_button("XY Fader", self._launch_xy_fader)
        
        windows_layout.addWidget(self.btn_chord_monitor, 0, 0)
        windows_layout.addWidget(self.btn_pad_grid, 0, 1)
        windows_layout.addWidget(self.btn_faders, 1, 0)
        windows_layout.addWidget(self.btn_xy_fader, 1, 1)
        
        windows_group.setLayout(windows_layout)
        layout.addWidget(windows_group)
        
        layout.addStretch()
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
            QWidget {
                background-color: #1e2127;
                color: #fff;
            }
        """)
    
    def _create_launch_button(self, text: str, callback) -> QPushButton:
        """Create a styled launch button."""
        btn = QPushButton(text)
        btn.setMinimumHeight(60)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 8px;
                padding: 12px;
                color: #fff;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 2px solid #2f82e6;
                background-color: #3a3f46;
            }
            QPushButton:pressed {
                background-color: #2f82e6;
            }
        """)
        btn.clicked.connect(callback)
        return btn
    
    def _launch_piano_25(self):
        """Launch 25-key piano window."""
        from .main import MainWindow
        if self.shared_midi:
            window = MainWindow(self.app, size=25, midi=self.shared_midi)
            window.show()
            self.opened_windows.append(window)
        else:
            print("Error: No MIDI output available")
    
    def _launch_piano_49(self):
        """Launch 49-key piano window."""
        from .main import MainWindow
        if self.shared_midi:
            window = MainWindow(self.app, size=49, midi=self.shared_midi)
            window.show()
            self.opened_windows.append(window)
        else:
            print("Error: No MIDI output available")
    
    def _launch_piano_61(self):
        """Launch 61-key piano window."""
        from .main import MainWindow
        if self.shared_midi:
            window = MainWindow(self.app, size=61, midi=self.shared_midi)
            window.show()
            self.opened_windows.append(window)
        else:
            print("Error: No MIDI output available")
    
    def _launch_harmonic_table(self):
        """Launch harmonic table window."""
        from .main import MainWindow
        if self.shared_midi:
            window = MainWindow(self.app, size=61, midi=self.shared_midi)
            # Switch to harmonic table view
            window.set_harmonic_table()
            window.show()
            self.opened_windows.append(window)
        else:
            print("Error: No MIDI output available")
    
    def _launch_chord_monitor(self):
        """Launch chord monitor window."""
        from .chord_monitor_window import ChordMonitorWindow
        if self.shared_midi:
            try:
                window = ChordMonitorWindow(self.shared_midi, 0, self)
                window.show()
                self.opened_windows.append(window)
            except Exception as e:
                print(f"Error launching Chord Monitor: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("Error: No MIDI output available")
    
    def _launch_pad_grid(self):
        """Launch pad grid window."""
        from .standalone_windows import PadGridWindow
        if self.shared_midi:
            try:
                window = PadGridWindow(self.shared_midi, 0, self)
                window.show()
                self.opened_windows.append(window)
            except Exception as e:
                print(f"Error launching Pad Grid: {e}")
        else:
            print("Error: No MIDI output available")
    
    def _launch_faders(self):
        """Launch faders window."""
        from .standalone_windows import FadersWindow
        if self.shared_midi:
            try:
                window = FadersWindow(self.shared_midi, 0, self)
                window.show()
                self.opened_windows.append(window)
            except Exception as e:
                print(f"Error launching Faders: {e}")
        else:
            print("Error: No MIDI output available")
    
    def _launch_xy_fader(self):
        """Launch XY fader window."""
        from .standalone_windows import XYFaderWindow
        if self.shared_midi:
            try:
                window = XYFaderWindow(self.shared_midi, 0, self)
                window.show()
                self.opened_windows.append(window)
            except Exception as e:
                print(f"Error launching XY Fader: {e}")
        else:
            print("Error: No MIDI output available")


def run():
    """Run the Octavium launcher."""
    app = QApplication(sys.argv)
    
    # Set application icon
    try:
        icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
        app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass
    
    launcher = LauncherWindow(app)
    launcher.show()
    
    # Keep reference to prevent garbage collection
    app._launcher = launcher  # type: ignore[attr-defined]
    
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
