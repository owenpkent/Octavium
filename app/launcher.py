"""Octavium Launcher Window - Main entry point for selecting windows and keyboards."""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QGridLayout, QApplication, QComboBox, QMessageBox
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
        self._available_ports: list[str] = []
        try:
            self._available_ports = list(mido.get_output_names())  # type: ignore[attr-defined]
            if self._available_ports:
                print(f"Available MIDI ports: {', '.join(self._available_ports)}")
            else:
                print("No MIDI ports found")
        except Exception as e:
            print(f"Could not list MIDI ports: {e}")
        
        # Choose initial port: prefer LoopBe/loopMIDI, then first available
        initial_port: str | None = None
        for preferred in ("loopbe", "loopmidi"):
            for p in self._available_ports:
                if preferred in p.lower():
                    initial_port = p
                    break
            if initial_port:
                break
        if initial_port is None and self._available_ports:
            initial_port = self._available_ports[0]
        
        self._current_port_name: str = initial_port or ""
        
        try:
            self.shared_midi = MidiOut(port_name_contains=self._current_port_name, is_shared=True)
            backend = "pygame" if self.shared_midi.use_pygame else "mido"
            print(f"✓ Launcher initialized with {backend} MIDI backend on port: {self._current_port_name}")
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
        
        layout.addSpacing(10)
        
        # MIDI port selector
        midi_port_row = QHBoxLayout()
        midi_port_row.setSpacing(8)
        midi_label = QLabel("MIDI Output:")
        midi_label.setStyleSheet("font-size: 13px; color: #aaa;")
        midi_port_row.addWidget(midi_label)
        self.midi_port_combo = QComboBox()
        self.midi_port_combo.setMinimumWidth(260)
        self.midi_port_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 6px;
                padding: 6px 32px 6px 10px;
                color: #fff;
                font-size: 13px;
            }
            QComboBox:hover { border: 2px solid #2f82e6; }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid #3b4148;
                border-radius: 0 6px 6px 0;
                background-color: #3b4148;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #aaa;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2f36;
                color: #fff;
                selection-background-color: #2f82e6;
                border: 1px solid #3b4148;
            }
        """)
        for p in self._available_ports:
            self.midi_port_combo.addItem(p)
        if self._current_port_name and self._current_port_name in self._available_ports:
            self.midi_port_combo.setCurrentIndex(self._available_ports.index(self._current_port_name))
        midi_port_row.addWidget(self.midi_port_combo, 1)
        btn_change_port = QPushButton("Change")
        btn_change_port.setMinimumHeight(34)
        btn_change_port.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_port.setStyleSheet("""
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #2f82e6;
                border-radius: 6px;
                padding: 4px 14px;
                color: #fff;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2f82e6; }
            QPushButton:pressed { background-color: #1a6fcf; }
        """)
        btn_change_port.clicked.connect(self._on_change_port_clicked)
        midi_port_row.addWidget(btn_change_port)
        btn_refresh_ports = QPushButton("Refresh")
        btn_refresh_ports.setMinimumHeight(34)
        btn_refresh_ports.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh_ports.setStyleSheet("""
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 6px;
                padding: 4px 14px;
                color: #aaa;
                font-size: 13px;
            }
            QPushButton:hover { border: 2px solid #2f82e6; color: #fff; }
            QPushButton:pressed { background-color: #3a3f46; }
        """)
        btn_refresh_ports.clicked.connect(self._refresh_port_list)
        midi_port_row.addWidget(btn_refresh_ports)
        layout.addLayout(midi_port_row)
        
        layout.addSpacing(10)
        
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
        
        # Generative section (Modulune) — roadmap, hidden for now
        
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
    
    def _create_modulune_button(self, text: str, callback) -> QPushButton:
        """Create a styled button for Modulune with distinct purple styling."""
        btn = QPushButton(text)
        btn.setMinimumHeight(60)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2a36;
                border: 2px solid #5b4a78;
                border-radius: 8px;
                padding: 12px;
                color: #d4c4f4;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 2px solid #9b7fd4;
                background-color: #3a3646;
            }
            QPushButton:pressed {
                background-color: #9b7fd4;
                color: #1e2127;
            }
        """)
        btn.clicked.connect(callback)
        return btn
    
    def _refresh_port_list(self):
        """Refresh the list of available MIDI output ports."""
        try:
            import mido
            ports = list(mido.get_output_names())  # type: ignore[attr-defined]
        except Exception:
            ports = []
        self._available_ports = ports
        self.midi_port_combo.blockSignals(True)
        self.midi_port_combo.clear()
        for p in ports:
            self.midi_port_combo.addItem(p)
        if self._current_port_name in ports:
            self.midi_port_combo.setCurrentIndex(ports.index(self._current_port_name))
        self.midi_port_combo.blockSignals(False)
    
    def _on_change_port_clicked(self):
        """Change the shared MIDI port to the selected one."""
        port_name = self.midi_port_combo.currentText()
        if not port_name:
            QMessageBox.warning(self, "MIDI Port", "No port selected.")
            return
        if port_name == self._current_port_name and self.shared_midi is not None:
            QMessageBox.information(self, "MIDI Port", f"Already using: {port_name}")
            return
        self._change_midi_port(port_name)
    
    def _change_midi_port(self, port_name: str):
        """Create a new shared MidiOut on port_name and propagate to all open windows."""
        from .midi_io import MidiOut
        try:
            new_midi = MidiOut(port_name_contains=port_name, is_shared=True)
        except Exception as e:
            QMessageBox.critical(self, "MIDI Port Error", f"Could not open port '{port_name}':\n{e}")
            return
        # Close the old shared port (it's shared so we must force-close)
        if self.shared_midi is not None:
            try:
                self.shared_midi.is_shared = False
                self.shared_midi.close()
            except Exception:
                pass
        self.shared_midi = new_midi
        self._current_port_name = port_name
        print(f"✓ MIDI port changed to: {port_name}")
        # Propagate to all open windows
        alive: list = []
        for win in self.opened_windows:
            try:
                if hasattr(win, 'isVisible') and win.isVisible():
                    if hasattr(win, 'update_midi_out'):
                        win.update_midi_out(new_midi)
                    alive.append(win)
            except Exception:
                pass
        self.opened_windows = alive
    
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
                window = ChordMonitorWindow(self.shared_midi, 0, None)
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
    
    def _launch_modulune(self):
        """Launch Modulune generative engine window."""
        from modulune.window import ModuluneWindow
        if self.shared_midi:
            try:
                window = ModuluneWindow(self.shared_midi, 0, self)
                window.show()
                self.opened_windows.append(window)
            except Exception as e:
                print(f"Error launching Modulune: {e}")
                import traceback
                traceback.print_exc()
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
