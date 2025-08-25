import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QInputDialog, QMessageBox
)
from PySide6.QtGui import QAction, QActionGroup, QIcon, QPixmap
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl
from .keyboard_widget import KeyboardWidget
from .midi_io import MidiOut, list_output_names
from .themes import APP_STYLES
from .piano_layout import create_piano_by_size


class MainWindow(QMainWindow):
    def __init__(self, app_ref: QApplication, size: int = 49, port_hint: str = "loopMIDI Port 1", midi: MidiOut | None = None):
        super().__init__()
        self.app_ref = app_ref
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
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
        self._update_window_title()
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

        # View menu (Mod/Pitch wheels) — place right after File
        view_menu = menubar.addMenu("&View")
        self.menu_actions = getattr(self, 'menu_actions', {})
        show_mod = QAction("Show Mod Wheel", self)
        show_mod.setCheckable(True)
        show_mod.setChecked(bool(self.menu_actions.get('show_mod', False)))
        show_mod.toggled.connect(lambda checked: (
            setattr(self.menu_actions, 'show_mod', checked) if False else None,
            self.keyboard.set_show_mod_wheel(checked),
            self._resize_for_layout(self.keyboard.layout_model),
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(self.keyboard.layout_model),
                self.adjustSize()
            ))
        ))
        view_menu.addAction(show_mod)
        show_pitch = QAction("Show Pitch Wheel", self)
        show_pitch.setCheckable(True)
        show_pitch.setChecked(bool(self.menu_actions.get('show_pitch', False)))
        show_pitch.toggled.connect(lambda checked: (
            setattr(self.menu_actions, 'show_pitch', checked) if False else None,
            self.keyboard.set_show_pitch_wheel(checked),
            self._resize_for_layout(self.keyboard.layout_model),
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(self.keyboard.layout_model),
                self.adjustSize()
            ))
        ))
        view_menu.addAction(show_pitch)
        # Visual hold preference (keep visuals pressed during sustain): moved here; default unchecked
        visual_hold = QAction("Hold Visuals During Sustain", self)
        visual_hold.setCheckable(True)
        # default unchecked unless previously set
        visual_hold.setChecked(bool(self.menu_actions.get('visual_hold_checked', False)))
        def _toggle_visual_hold(checked: bool):
            try:
                self.keyboard.visual_hold_on_sustain = checked
                # Persist the checked state
                self.menu_actions['visual_hold_checked'] = checked
                # Re-sync visuals when toggled, without touching notes
                try:
                    st = self.keyboard.style()
                    for btn in self.keyboard.key_buttons.values():
                        st.unpolish(btn)
                        st.polish(btn)
                        btn.update()
                except Exception:
                    pass
            except Exception:
                pass
        visual_hold.triggered.connect(_toggle_visual_hold)
        view_menu.addAction(visual_hold)
        # Persist
        self.menu_actions['show_mod'] = show_mod.isChecked()
        self.menu_actions['show_pitch'] = show_pitch.isChecked()
        self.menu_actions['view_show_mod'] = show_mod
        self.menu_actions['view_show_pitch'] = show_pitch
        self.menu_actions['visual_hold'] = visual_hold
        # Apply current selections
        try:
            self.keyboard.set_show_mod_wheel(show_mod.isChecked())
            self.keyboard.set_show_pitch_wheel(show_pitch.isChecked())
            # Apply visual hold default (unchecked) or previous
            self.keyboard.visual_hold_on_sustain = visual_hold.isChecked()
            # Ensure styles reflect any change
            try:
                st = self.keyboard.style()
                for btn in self.keyboard.key_buttons.values():
                    st.unpolish(btn)
                    st.polish(btn)
                    btn.update()
            except Exception:
                pass
            # Ensure window reflects current selection after menus are built
            self._resize_for_layout(self.keyboard.layout_model)
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(self.keyboard.layout_model),
                self.adjustSize()
            ))
        except Exception:
            pass

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

        # Voices (polyphony) menu: Unlimited or 1-8 (exclusive)
        voices_menu = menubar.addMenu("&Voices")
        self.voices_group = QActionGroup(self)
        self.voices_group.setExclusive(True)
        self.voices_actions = []
        # Previous selection, default Unlimited
        self.menu_actions = getattr(self, 'menu_actions', {})
        prev_sel = self.menu_actions.get('voices_selected', 'Unlimited')
        # Unlimited action
        unlimited_act = QAction("Unlimited", self)
        unlimited_act.setCheckable(True)
        unlimited_act.setChecked(prev_sel == 'Unlimited')
        def _select_unlimited():
            try:
                self.keyboard.set_polyphony_enabled(False)
            except Exception:
                pass
            # persist
            self.menu_actions['voices_selected'] = 'Unlimited'
        unlimited_act.triggered.connect(lambda checked: _select_unlimited())
        self.voices_group.addAction(unlimited_act)
        voices_menu.addAction(unlimited_act)
        # Numeric actions 1-8
        def _select_limited(n: int):
            try:
                self.keyboard.set_polyphony_enabled(True)
                self.keyboard.set_polyphony_max(n)
            except Exception:
                pass
            self.menu_actions['voices_selected'] = str(n)
        for n in range(1, 9):
            act = QAction(f"{n}", self)
            act.setCheckable(True)
            act.setChecked(prev_sel == str(n))
            act.triggered.connect(lambda checked, val=n: _select_limited(val))
            self.voices_group.addAction(act)
            voices_menu.addAction(act)
            self.voices_actions.append(act)
        # If nothing matched previous selection, ensure Unlimited is applied now
        try:
            labels = [a.text() for a in self.voices_group.actions() if a.isChecked()]
            if not labels:
                unlimited_act.setChecked(True)
                _select_unlimited()
            else:
                sel = labels[0]
                if sel == 'Unlimited':
                    _select_unlimited()
                else:
                    try:
                        _select_limited(int(sel))
                    except Exception:
                        _select_unlimited()
        except Exception:
            pass
        # Persist menu refs
        self.menu_actions['voices_actions'] = self.voices_actions
        self.menu_actions['voices_group'] = self.voices_group

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
        self._update_window_title()
        # Preserve sustain and visual hold preferences
        try:
            if hasattr(self, 'menu_actions'):
                # Visual hold
                if 'visual_hold' in self.menu_actions:
                    self.keyboard.visual_hold_on_sustain = self.menu_actions['visual_hold'].isChecked()
                # Voices (polyphony): apply current selection (Unlimited or 1-8)
                sel = self.menu_actions.get('voices_selected', 'Unlimited')
                try:
                    if sel == 'Unlimited':
                        self.keyboard.set_polyphony_enabled(False)
                    else:
                        self.keyboard.set_polyphony_enabled(True)
                        try:
                            self.keyboard.set_polyphony_max(int(sel))
                        except Exception:
                            self.keyboard.set_polyphony_max(8)
                except Exception:
                    pass
                # View menu: wheels visibility
                try:
                    self.keyboard.set_show_mod_wheel(bool(self.menu_actions.get('show_mod', False)))
                    self.keyboard.set_show_pitch_wheel(bool(self.menu_actions.get('show_pitch', False)))
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
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Select MIDI Output")
        dlg.setLabelText("Port:")
        try:
            dlg.setComboBoxItems(ports)
        except Exception:
            pass
        # preselect current
        try:
            idx = ports.index(current) if current in ports else 0
            dlg.setComboBoxEditable(False)
            dlg.setTextValue(ports[idx])
        except Exception:
            pass
        # Blue bounding box around OK and Cancel
        dlg.setStyleSheet(
            "QPushButton { border: 2px solid #3399ff; border-radius: 4px; padding: 4px 10px; }"
        )
        if dlg.exec() != QMessageBox.Accepted:
            return
        port = dlg.textValue()
        if not port:
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
        # Compute content width from piano + optional left panel and controls (whichever is wider)
        content_width = None
        if hasattr(self, 'keyboard') and hasattr(self.keyboard, 'piano_container'):
            try:
                w_piano = int(self.keyboard.piano_container.width())
            except Exception:
                w_piano = None
            # Include left panel (wheels) width when visible
            try:
                left_panel = getattr(self.keyboard, 'left_panel', None)
                w_left = int(left_panel.width()) if (left_panel is not None and left_panel.isVisible()) else 0
            except Exception:
                w_left = 0
            try:
                controls_widget = getattr(self.keyboard, 'controls_widget', None)
                w_controls = int(controls_widget.width()) if controls_widget is not None else 0
            except Exception:
                w_controls = 0
            if w_piano is not None:
                content_width = max(w_piano + w_left, w_controls)
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
        year = datetime.now().year
        # Build logo HTML at the top, centered
        logo_html = ""
        try:
            logo_path = Path(__file__).resolve().parent.parent / "Octavium logo.png"
            if logo_path.exists():
                logo_url = QUrl.fromLocalFile(str(logo_path)).toString()
                logo_html = f"<div style='text-align:center; margin-bottom:10px'><img src='{logo_url}' width='320'></div>"
        except Exception:
            pass
        text = (
            f"{logo_html}"
            "<b>Octavium - Virtual MIDI Keyboard</b><br><br>"
            f"(c) {year} Owen Kent<br><br>"
            "Octavium is a virtual on-screen MIDI keyboard designed to be played with the mouse.<br>"
            "It focuses on simple, precise mouse input—no computer keyboard required.<br><br>"
            "<b>Features</b>:<br>"
            "- Multiple keyboard sizes (25/49/61/73/76/88) with realistic black/white key layout<br>"
            "- MIDI output (rtmidi if available, otherwise pygame backend)<br>"
            "- Velocity control with selectable curves (linear/soft/hard)<br>"
            "- Sustain and Latch modes<br>"
            "- Channel selection and quick All Notes Off<br><br>"
            f"Current MIDI Port: {self.keyboard.port_name or 'N/A'}"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("About Octavium")
        msg.setTextFormat(Qt.RichText)
        msg.setText(text)
        # Blue bounding box around the OK button
        msg.setStyleSheet(
            "QPushButton { border: 2px solid #3399ff; border-radius: 4px; padding: 4px 10px; }"
        )
        msg.exec()

    def _update_window_title(self):
        try:
            kb_name = getattr(self.keyboard.layout_model, 'name', '') or 'Keyboard'
            self.setWindowTitle(f"Octavium - {kb_name}")
        except Exception:
            self.setWindowTitle("Octavium")


def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLES)
    # Set application icon as well (project-relative)
    try:
        icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
        app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass
    main = MainWindow(app)
    # Keep a ref so it isn't GC'd
    app._windows = [main]  # type: ignore[attr-defined]
    main.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
