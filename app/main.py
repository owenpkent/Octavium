import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QInputDialog, QMessageBox
)
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import Qt
from .keyboard_widget import KeyboardWidget
from .midi_io import MidiOut, list_output_names
from .themes import APP_STYLES
from .piano_layout import create_piano_by_size


class MainWindow(QMainWindow):
    def __init__(self, app_ref: QApplication, size: int = 61, port_hint: str = "loopMIDI Port 1", midi: MidiOut | None = None):
        super().__init__()
        self.app_ref = app_ref
        self.current_size = size
        self.current_channel = 1  # 1-16
        # Create or reuse MIDI and keyboard
        if midi is None:
            try:
                midi = MidiOut(port_name_contains=port_hint)
            except Exception as e:
                QMessageBox.critical(self, "MIDI Error", f"Failed to open MIDI output (hint '{port_hint}'):\n{e}")
                raise
        layout = create_piano_by_size(size)
        self.keyboard = KeyboardWidget(layout, midi, title=f"Piano {size}-Key -> {port_hint}")
        self.keyboard.port_name = port_hint
        self.keyboard.set_channel(self.current_channel)
        self.setCentralWidget(self.keyboard)
        self.resize(1400, 340)
        self._build_menus()

    def _build_menus(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        new_action = QAction("New Keyboard Window", self)
        new_action.triggered.connect(self.new_keyboard_window)
        file_menu.addAction(new_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Keyboard menu
        kb_menu = menubar.addMenu("&Keyboard")
        for size in [25, 49, 61, 73, 76, 88]:
            act = QAction(f"{size} Keys", self)
            act.setCheckable(True)
            if size == self.current_size:
                act.setChecked(True)
            act.triggered.connect(lambda checked, s=size: self.set_keyboard_size(s))
            kb_menu.addAction(act)

        # MIDI menu
        midi_menu = menubar.addMenu("&MIDI")
        select_port = QAction("Select Output Port...", self)
        select_port.triggered.connect(self.select_midi_port)
        midi_menu.addAction(select_port)
        all_off = QAction("All Notes Off", self)
        all_off.triggered.connect(self.keyboard.all_notes_off_clicked)
        midi_menu.addAction(all_off)

        # Channel submenu 1-16
        chan_menu = midi_menu.addMenu("Channel")
        self.channel_group = QActionGroup(self)
        self.channel_group.setExclusive(True)
        self.channel_actions = []
        for ch in range(1, 17):
            act = QAction(f"{ch}", self)
            act.setCheckable(True)
            if ch == self.current_channel:
                act.setChecked(True)
            act.triggered.connect(lambda checked, c=ch: self.set_channel(c))
            self.channel_group.addAction(act)
            chan_menu.addAction(act)
            self.channel_actions.append(act)

    def set_keyboard_size(self, size: int):
        if size == self.current_size:
            return
        self.current_size = size
        # Rebuild keyboard with same MIDI out
        layout = create_piano_by_size(size)
        new_keyboard = KeyboardWidget(layout, self.keyboard.midi)
        new_keyboard.port_name = self.keyboard.port_name
        new_keyboard.update_window_title()
        self.setCentralWidget(new_keyboard)
        self.keyboard.deleteLater()
        self.keyboard = new_keyboard
        self.keyboard.set_channel(self.current_channel)

        # Update checkmarks in menu
        kb_menu: QMenu = self.menuBar().findChild(QMenu, None)
        # Not strictly necessary to update checks programmatically; actions will visually toggle by selection.

    def select_midi_port(self):
        ports = list_output_names()
        if not ports:
            QMessageBox.warning(self, "MIDI", "No MIDI output ports found.")
            return
        current = self.keyboard.port_name or (ports[0] if ports else "")
        port, ok = QInputDialog.getItem(self, "Select MIDI Output", "Port:", ports, ports.index(current) if current in ports else 0, False)
        if not ok:
            return
        midi = MidiOut(port_name_contains=port)
        self.keyboard.set_midi_out(midi, port_name=port)

    def new_keyboard_window(self):
        win = MainWindow(self.app_ref, size=self.current_size, port_hint=self.keyboard.port_name or "", midi=self.keyboard.midi)
        win.set_channel(self.current_channel)
        # Keep reference on QApplication to prevent GC
        if not hasattr(self.app_ref, "_windows"):
            self.app_ref._windows = []  # type: ignore[attr-defined]
        self.app_ref._windows.append(win)  # type: ignore[attr-defined]
        win.show()

    def set_channel(self, channel_1_based: int):
        channel_1_based = max(1, min(16, channel_1_based))
        self.current_channel = channel_1_based
        # Update UI check marks
        if hasattr(self, 'channel_actions'):
            for idx, act in enumerate(self.channel_actions, start=1):
                act.setChecked(idx == channel_1_based)
        # Apply to keyboard
        if hasattr(self, 'keyboard') and self.keyboard is not None:
            self.keyboard.set_channel(channel_1_based)


def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLES)
    main = MainWindow(app)
    # Keep a ref so it isn't GC'd
    app._windows = [main]  # type: ignore[attr-defined]
    main.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
