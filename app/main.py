import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QInputDialog, QMessageBox
)
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import Qt, QTimer
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
        self.keyboard = KeyboardWidget(layout, midi, title=f"Piano {size}-Key -> {port_hint}", show_header=False)
        self.keyboard.port_name = port_hint
        self.keyboard.set_channel(self.current_channel)
        self.setCentralWidget(self.keyboard)
        self._resize_for_layout(self.keyboard.layout_model)
        # Ensure one more resize after layout settles
        QTimer.singleShot(0, lambda: (
            self.keyboard.adjustSize(),
            self._resize_for_layout(self.keyboard.layout_model),
            self.adjustSize()
        ))
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

        # Keyboard menu (exclusive size selection)
        kb_menu = menubar.addMenu("&Keyboard")
        self.size_group = QActionGroup(self)
        self.size_group.setExclusive(True)
        self.size_actions = {}
        for size in [25, 49, 61, 73, 76, 88]:
            act = QAction(f"{size} Keys", self)
            act.setCheckable(True)
            if size == self.current_size:
                act.setChecked(True)
            act.triggered.connect(lambda checked, s=size: self.set_keyboard_size(s))
            self.size_group.addAction(act)
            kb_menu.addAction(act)
            self.size_actions[size] = act

        # MIDI menu
        midi_menu = menubar.addMenu("&MIDI")
        select_port = QAction("Select Output Port...", self)
        select_port.triggered.connect(self.select_midi_port)
        midi_menu.addAction(select_port)
        # Sustain toggle (since header is hidden by default)
        sustain_toggle = QAction("Sustain", self)
        sustain_toggle.setCheckable(True)
        sustain_toggle.setChecked(False)
        def _toggle_sustain(checked: bool):
            try:
                self.keyboard.set_sustain(checked)
            except Exception:
                pass
        sustain_toggle.toggled.connect(_toggle_sustain)
        midi_menu.addAction(sustain_toggle)
        # Latch toggle (behaves like sustain but press toggles note off if already on)
        latch_toggle = QAction("Latch", self)
        latch_toggle.setCheckable(True)
        latch_toggle.setChecked(False)
        def _toggle_latch(checked: bool):
            try:
                self.keyboard.set_latch(checked)
            except Exception:
                pass
        latch_toggle.toggled.connect(_toggle_latch)
        midi_menu.addAction(latch_toggle)
        # Visual hold on sustain
        visual_hold = QAction("Hold Visual on Sustain", self)
        visual_hold.setCheckable(True)
        visual_hold.setChecked(True)
        def _toggle_visual_hold(checked: bool):
            try:
                self.keyboard.visual_hold_on_sustain = checked
                if not checked and self.keyboard.sustain:
                    # If disabling while sustaining, clear any stuck visuals
                    for btn in self.keyboard.key_buttons.values():
                        try:
                            btn.setDown(False)
                            btn.setProperty('held', 'false')
                            st = btn.style()
                            if st is not None:
                                st.unpolish(btn)
                                st.polish(btn)
                            btn.update()
                        except Exception:
                            pass
            except Exception:
                pass
        visual_hold.triggered.connect(_toggle_visual_hold)
        midi_menu.addAction(visual_hold)
        # Keep references for persistence across keyboard rebuilds
        self.menu_actions = getattr(self, 'menu_actions', {})
        self.menu_actions['sustain'] = sustain_toggle
        self.menu_actions['visual_hold'] = visual_hold
        self.menu_actions['latch'] = latch_toggle
        # Initialize keyboard flags from menu
        try:
            self.keyboard.visual_hold_on_sustain = visual_hold.isChecked()
            self.keyboard.set_latch(self.menu_actions['latch'].isChecked())
        except Exception:
            pass
        all_off = QAction("All Notes Off", self)
        all_off.triggered.connect(self.keyboard.all_notes_off_clicked)
        midi_menu.addAction(all_off)

        # Voices (polyphony) menu
        voices_menu = menubar.addMenu("&Voices")
        voices_enable = QAction("Enable Limit", self)
        voices_enable.setCheckable(True)
        voices_enable.setChecked(False)
        def _toggle_voices_enabled(checked: bool):
            try:
                self.keyboard.set_polyphony_enabled(checked)
                # Enable/disable numeric actions
                if hasattr(self, 'voices_actions'):
                    for act in self.voices_actions:
                        act.setEnabled(checked)
            except Exception:
                pass
        voices_enable.toggled.connect(_toggle_voices_enabled)
        voices_menu.addAction(voices_enable)
        voices_menu.addSeparator()
        # 1-8 options, exclusive
        self.voices_group = QActionGroup(self)
        self.voices_group.setExclusive(True)
        self.voices_actions = []
        def _set_polyphony(n: int):
            try:
                self.keyboard.set_polyphony_max(n)
                # If user selects a number, implicitly enable limit
                if not voices_enable.isChecked():
                    voices_enable.setChecked(True)
            except Exception:
                pass
        for n in range(1, 9):
            act = QAction(f"{n}", self)
            act.setCheckable(True)
            if n == 8:
                act.setChecked(True)
            act.triggered.connect(lambda checked, val=n: _set_polyphony(val))
            act.setEnabled(False)  # disabled until enabled checkbox is on
            self.voices_group.addAction(act)
            voices_menu.addAction(act)
            self.voices_actions.append(act)
        # Persist menu refs
        self.menu_actions = getattr(self, 'menu_actions', {})
        self.menu_actions['voices_enable'] = voices_enable
        self.menu_actions['voices_actions'] = self.voices_actions

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

        # Help menu
        help_menu = menubar.addMenu("&Help")
        kb_shortcuts = QAction("Keyboard Shortcuts", self)
        kb_shortcuts.triggered.connect(self.show_keyboard_shortcuts)
        help_menu.addAction(kb_shortcuts)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def set_keyboard_size(self, size: int):
        if size == self.current_size:
            return
        self.current_size = size
        # Rebuild keyboard with same MIDI out
        layout = create_piano_by_size(size)
        new_keyboard = KeyboardWidget(layout, self.keyboard.midi, show_header=False)
        new_keyboard.port_name = self.keyboard.port_name
        new_keyboard.update_window_title()
        self.setCentralWidget(new_keyboard)
        self.keyboard.deleteLater()
        self.keyboard = new_keyboard
        self.keyboard.set_channel(self.current_channel)
        # Preserve sustain and visual hold preferences
        try:
            if hasattr(self, 'menu_actions'):
                # Visual hold
                if 'visual_hold' in self.menu_actions:
                    self.keyboard.visual_hold_on_sustain = self.menu_actions['visual_hold'].isChecked()
                # Sustain state
                if 'sustain' in self.menu_actions:
                    sustain_checked = self.menu_actions['sustain'].isChecked()
                    self.keyboard.sustain_btn.setChecked(sustain_checked)
                    self.keyboard.toggle_sustain()
                # Voices (polyphony)
                if 'voices_enable' in self.menu_actions:
                    enabled = self.menu_actions['voices_enable'].isChecked()
                    try:
                        voices = 8
                        if 'voices_actions' in self.menu_actions:
                            for act in self.menu_actions['voices_actions']:
                                if act.isChecked():
                                    try:
                                        voices = int(act.text())
                                    except Exception:
                                        voices = 8
                                    break
                        self.keyboard.set_polyphony_max(voices)
                        self.keyboard.set_polyphony_enabled(enabled)
                    except Exception:
                        pass
        except Exception:
            pass
        # Exclusive check is handled by QActionGroup, ensure correct one is checked
        if hasattr(self, 'size_actions') and size in self.size_actions:
            self.size_actions[size].setChecked(True)
        # Resize window for the new layout (immediate + deferred)
        self._resize_for_layout(layout)
        self.keyboard.adjustSize()
        self.adjustSize()
        QTimer.singleShot(0, lambda: (
            self.keyboard.adjustSize(),
            self._resize_for_layout(layout),
            self.adjustSize()
        ))

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

    def _resize_for_layout(self, layout):
        """Resize the window to fit current keyboard content width.
        Prefers the actual `piano_container.width()`; falls back to `columns * 44`.
        """
        # Compute content width from piano and controls (whichever is wider)
        content_width = None
        if hasattr(self, 'keyboard') and hasattr(self.keyboard, 'piano_container'):
            try:
                w_piano = int(self.keyboard.piano_container.width())
            except Exception:
                w_piano = None
            try:
                controls_widget = getattr(self.keyboard, 'controls_widget', None)
                w_controls = int(controls_widget.width()) if controls_widget is not None else 0
            except Exception:
                w_controls = 0
            if w_piano is not None:
                content_width = max(w_piano, w_controls)
        if content_width is None:
            try:
                columns = getattr(layout, 'columns', 36) or 36
            except Exception:
                columns = 36
            content_width = columns * 44  # matches KeyboardWidget white key width

        side_padding = 56  # modest side padding for window chrome
        target_width = content_width + side_padding
        # Height: central widget (keyboard) hint + menubar height
        try:
            kb_h = max(self.keyboard.minimumSizeHint().height(), self.keyboard.sizeHint().height())
        except Exception:
            kb_h = 180
        try:
            menu_h = self.menuBar().sizeHint().height()
        except Exception:
            menu_h = 0
        target_height = int(kb_h + menu_h)
        # Ensure we can shrink down (e.g., 25 keys)
        target_width = int(target_width)
        # Update child geometry first
        try:
            self.keyboard.piano_container.updateGeometry()
            self.keyboard.updateGeometry()
        except Exception:
            pass
        # Force central widget width to exactly the content width (no internal padding)
        try:
            self.keyboard.setMinimumWidth(int(content_width))
            self.keyboard.setMaximumWidth(int(content_width))
            self.keyboard.setFixedWidth(int(content_width))
        except Exception:
            pass
        # Temporarily drop min/max to allow shrinking, then resize, then release
        self.setMinimumSize(0, 0)
        self.setMaximumSize(target_width, target_height)
        self.resize(target_width, target_height)
        self.setMaximumSize(16777215, 16777215)

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

    def show_keyboard_shortcuts(self):
        text = (
            "Keyboard shortcuts:\n\n"
            "- Z / X: Octave Down / Up\n"
            "- 1 / 2 / 3: Velocity curve (soft / linear / hard)\n"
            "- Q: Toggle quantize to scale\n"
            "- Esc: All Notes Off\n\n"
            "Mouse:\n"
            "- Click keys to play\n"
            "- Click and drag across keys to glide\n"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", text)

    def show_about_dialog(self):
        text = (
            "Octavium - Virtual MIDI Keyboard\n\n"
            "A lightweight Qt-based piano keyboard with MIDI output and velocity curves.\n"
            "Select different key counts, channels, and output ports from the menu.\n\n"
            f"MIDI Port: {self.keyboard.port_name or 'N/A'}\n"
        )
        QMessageBox.information(self, "About Octavium", text)


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
